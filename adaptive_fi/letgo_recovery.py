#!/usr/bin/env python3
"""
LetGo修复逻辑模块
从sighandler.py提取h_1/h_2/h_3修复逻辑，提供独立的修复功能
"""

import sys
import os
from dataclasses import dataclass
import pexpect

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import faultinject


@dataclass
class InjectionInfo:
    """从inject_info.txt解析的注错信息"""
    inject_pc: str          # 注错指令地址
    inject_inst: str        # 注错指令反汇编
    inject_reg: str         # 注错寄存器
    inject_kth: int         # 第几次执行
    original_value: str     # 原始值
    injected_value: str     # 注错后值
    inject_bit: int         # 翻转的位
    next_pc: str            # 下一条指令地址
    regw_list: str          # 写寄存器列表
    stackw: str             # 是否栈写
    base: str               # 基址寄存器
    index: str              # 索引寄存器
    displacement: str       # 偏移
    scale: str              # 缩放因子


class LetGoRecovery:
    """LetGo崩溃修复框架"""

    def __init__(self, gdb_process, inject_info: InjectionInfo, verbose: bool = False):
        """
        初始化修复框架

        Args:
            gdb_process: pexpect GDB进程对象
            inject_info: 注错信息
            verbose: 是否显示详细信息
        """
        self.gdb_process = gdb_process
        self.inject_info = inject_info
        self.verbose = verbose

        # 从inject_info提取关键信息
        self.next_pc = inject_info.next_pc
        self.regw_list = self._parse_regw_list(inject_info.regw_list)
        self.stackw = inject_info.stackw
        self.base = inject_info.base
        self.index = inject_info.index
        self.displacement = inject_info.displacement
        self.scale = inject_info.scale

        # 判断flag
        self.flag = self._determine_flag()

        # FaultInjector实例（用于获取stack_size）
        self.fi = faultinject.FaultInjector(insts=1000000)

    def _parse_regw_list(self, regw_str: str) -> list:
        """解析写寄存器列表"""
        if not regw_str or regw_str == "none":
            return []
        return [r.strip() for r in regw_str.split(',') if r.strip()]

    def _determine_flag(self) -> int:
        """
        确定指令类型flag

        Returns:
            1: stackw (栈写)
            2: stackr (栈读)
            3: nostack (非栈操作)
        """
        stackw = self.stackw.lower()

        if stackw == "yes":
            return 1  # stackw
        elif self.base in ["rbp", "rsp"] or self.index in ["rbp", "rsp"]:
            return 2  # stackr
        else:
            return 3  # nostack

    def letgo_frame(self) -> bool:
        """
        LetGo修复框架主流程

        Returns:
            True if recovery succeeded, False otherwise
        """
        print("\n" + "="*60)
        print("LetGo修复框架")
        print("="*60)
        print(f"Flag: {self.flag} ({'栈写' if self.flag == 1 else '栈读' if self.flag == 2 else '非栈'})")
        print(f"下一条指令: {self.next_pc}")
        print(f"写寄存器列表: {self.regw_list}")
        print()

        try:
            # Step 1: 获取崩溃点PC
            thispc = self._get_current_pc()
            print(f"Step 1: 崩溃点PC = {thispc}")

            # Step 2: 修复寄存器
            self._recover_registers()

            # Step 3: 修复栈指针（h_3）
            if self.flag in [1, 2]:
                self._recover_stack_pointers()

            # Step 4: 设置PC到下一条指令
            self._set_next_pc()

            print("\n" + "="*60)
            print("LetGo修复完成")
            print("="*60)

            return True

        except Exception as e:
            print(f"修复失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _get_current_pc(self) -> str:
        """获取当前PC值"""
        self.gdb_process.sendline("print $pc")
        self.gdb_process.expect("\(gdb\)")

        output = self.gdb_process.before.decode('utf-8')

        # 解析PC值
        if "0x" in output:
            for item in output.split():
                if "0x" in item:
                    return item

        return "0x0"

    def _recover_registers(self):
        """Step 2: 恢复寄存器"""
        print("\nStep 2: 恢复寄存器")

        if not self.regw_list:
            print("  无需恢复寄存器")
            return

        for regw in self.regw_list:
            if self.flag == 2:
                # h_1: 栈读取指令修复（地址计算）
                self._h1_stack_read_recovery(regw)
            elif self.flag == 3:
                # h_2: 默认值修复
                self._h2_default_value_recovery(regw)
            elif self.flag == 1:
                # 栈写指令，可能也需要修复（根据具体情况）
                self._h2_default_value_recovery(regw)

    def _h1_stack_read_recovery(self, regw: str):
        """h_1: 栈读取指令修复 - 地址计算"""
        print(f"\n  [h_1] 栈读取修复: {regw}")

        # 获取基址寄存器值
        final_b = 0
        if self.base and self.base != "none":
            self.gdb_process.sendline(f"print ${self.base}")
            self.gdb_process.expect("\(gdb\)")
            output = self.gdb_process.before.decode('utf-8')

            for item in output.split():
                if "0x" in item or item.isdigit():
                    try:
                        final_b = int(item, 16) if "0x" in item else int(item)
                        print(f"    Base ({self.base}) = {hex(final_b)}")
                        break
                    except:
                        pass

        # 获取索引寄存器值
        final_i = 0
        if self.index and self.index != "none" and self.index != "null":
            self.gdb_process.sendline(f"print ${self.index}")
            self.gdb_process.expect("\(gdb\)")
            output = self.gdb_process.before.decode('utf-8')

            for item in output.split():
                if "0x" in item or item.isdigit():
                    try:
                        final_i = int(item, 16) if "0x" in item else int(item)
                        print(f"    Index ({self.index}) = {hex(final_i)}")
                        break
                    except:
                        pass

        # 获取偏移和缩放因子
        try:
            final_d = int(self.displacement) if self.displacement else 0
            final_s = int(self.scale) if self.scale else 0
        except:
            final_d = 0
            final_s = 0

        # 计算有效地址: address = base + displacement + index * scale
        address = final_b + final_d + final_i * final_s
        print(f"    计算地址 = {hex(final_b)} + {final_d} + {hex(final_i)} * {final_s} = {hex(address)}")

        # 读取该地址的值
        self.gdb_process.sendline(f"print *{address}")
        self.gdb_process.expect("\(gdb\)")
        output = self.gdb_process.before.decode('utf-8')

        value = "0"
        for item in output.split():
            if "0x" in item or item.lstrip('-').isdigit():
                value = item
                break

        print(f"    内存值 = {value}")

        # 恢复到目标寄存器
        self.gdb_process.sendline(f"set ${regw} = {value}")
        self.gdb_process.expect("\(gdb\)")

        print(f"    [h_1完成] {regw} = {value}")

    def _h2_default_value_recovery(self, regw: str):
        """h_2: 默认值修复"""
        print(f"\n  [h_2] 默认值修复: {regw}")

        # 处理XMM寄存器
        if "xmm" in regw.lower():
            regw_full = regw + ".uint128"
            print(f"    检测到XMM寄存器，修改为 {regw_full}")
        else:
            regw_full = regw

        # 设置为0
        self.gdb_process.sendline(f"set ${regw_full} = 0")
        self.gdb_process.expect("\(gdb\)")

        print(f"    [h_2完成] {regw} = 0")

    def _recover_stack_pointers(self):
        """Step 3: h_3 - 栈指针修复"""
        print("\nStep 3: [h_3] 栈指针修复")

        # 获取栈帧大小
        stack_size_hex = self.fi.get_stack_size()
        try:
            stack_size = int(stack_size_hex, 16) if "0x" in stack_size_hex else int(stack_size_hex)
        except:
            print("  无法获取栈帧大小，跳过h_3")
            return

        print(f"  栈帧大小 = {hex(stack_size)}")

        # 确定栈操作寄存器
        stackinfo = ["rbp", "rsp"]
        stack_reg = None

        # 从inject_info判断哪个栈寄存器被操作
        if self.stackw == "yes":
            # 栈写操作，判断哪个寄存器被写
            if "rbp" in self.inject_info.regw_list:
                stack_reg = "rbp"
            elif "rsp" in self.inject_info.regw_list:
                stack_reg = "rsp"

        if not stack_reg:
            # 根据base/index判断
            if self.base in stackinfo:
                stack_reg = self.base
            elif self.index in stackinfo:
                stack_reg = self.index

        if not stack_reg:
            print("  无法确定栈操作寄存器，跳过h_3")
            return

        # 获取另一个栈指针
        stackinfo.remove(stack_reg)
        other_sp = stackinfo[0]

        print(f"  栈操作寄存器: {stack_reg}, 参考寄存器: {other_sp}")

        # 获取两个栈指针的值
        self.gdb_process.sendline(f"print ${other_sp}")
        self.gdb_process.expect("\(gdb\)")
        output = self.gdb_process.before.decode('utf-8')

        size_other = 0
        for item in output.split():
            if "0x" in item:
                try:
                    size_other = int(item, 16)
                    break
                except:
                    pass

        self.gdb_process.sendline(f"print ${stack_reg}")
        self.gdb_process.expect("\(gdb\)")
        output = self.gdb_process.before.decode('utf-8')

        size_stack = 0
        for item in output.split():
            if "0x" in item:
                try:
                    size_stack = int(item, 16)
                    break
                except:
                    pass

        print(f"  {other_sp} = {hex(size_other)}")
        print(f"  {stack_reg} = {hex(size_stack)}")

        # 栈溢出检测
        condition1 = (abs(size_other - size_stack) > stack_size and
                     size_stack > stack_size and size_other > stack_size)
        condition2 = (size_other - size_stack > 0) if other_sp == "rsp" else (size_stack - size_other > 0)

        if condition1 or condition2:
            print("  [检测] 栈溢出！开始修复...")

            # 计算修复值
            if stack_reg == "rbp":
                # rbp = rsp + stack_size
                setback = size_other + stack_size
                print(f"  计算: rbp = {hex(size_other)} + {hex(stack_size)} = {hex(setback)}")
            elif stack_reg == "rsp":
                # rsp = rbp - stack_size
                setback = size_other - stack_size
                print(f"  计算: rsp = {hex(size_other)} - {hex(stack_size)} = {hex(setback)}")
            else:
                print("  未知栈寄存器，跳过修复")
                return

            # 应用修复
            self.gdb_process.sendline(f"set ${stack_reg} = {setback}")
            self.gdb_process.expect("\(gdb\)")

            print(f"  [h_3完成] {stack_reg} = {hex(setback)}")
        else:
            print("  未检测到栈溢出，跳过h_3")

    def _set_next_pc(self):
        """Step 4: 设置PC到下一条指令"""
        print("\nStep 4: 设置PC到下一条指令")

        # next_pc可能是十六进制字符串
        if not self.next_pc.startswith("0x"):
            try:
                pc_value = hex(int(self.next_pc))
            except:
                pc_value = self.next_pc
        else:
            pc_value = self.next_pc

        print(f"  设置 $pc = {pc_value}")

        self.gdb_process.sendline(f"set $pc = {pc_value}")
        self.gdb_process.expect("\(gdb\)")

        print(f"  [完成] PC已设置到下一条指令")

    def check_error_propagation(self, max_steps: int = 50) -> bool:
        """
        检测错误传播

        Args:
            max_steps: 最大单步执行次数

        Returns:
            True if crashed again (Recrash), False otherwise
        """
        print(f"\n错误传播检测（最多{max_steps}步）")

        for step in range(max_steps):
            # 单步执行
            self.gdb_process.sendline("stepi")

            patterns = [
                "Program received signal",  # 0: 崩溃
                "\(gdb\)",                  # 1: 正常
                pexpect.TIMEOUT             # 2: 超时
            ]

            i = self.gdb_process.expect(patterns, timeout=5)

            if i == 0:
                # 检测到信号
                print(f"  Step {step+1}: 检测到崩溃信号！")
                self.gdb_process.expect("\(gdb\)")
                return True  # Recrash

            elif i == 1:
                # 正常单步
                if self.verbose and step < 10:
                    print(f"  Step {step+1}: OK")

            else:
                # 超时
                print(f"  Step {step+1}: 超时")
                break

        print(f"  {max_steps}步内未检测到错误传播")
        return False  # No recrash
