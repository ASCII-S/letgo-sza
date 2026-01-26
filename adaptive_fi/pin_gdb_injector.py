#!/usr/bin/env python3
"""
Pin+GDB联合注错模块
使用Pin进行故障注入，GDB进行崩溃修复
"""

import os
import sys
import time
import subprocess
import pexpect
from typing import Optional

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import configure
import sdcjudger
from letgo_recovery import InjectionInfo, LetGoRecovery


class PinGdbInjector:
    """Pin+GDB联合注错器"""

    def __init__(self, log_index: int, verbose: bool = False):
        """
        初始化注错器

        Args:
            log_index: 日志序号
            verbose: 是否显示详细GDB交互信息
        """
        self.log_index = log_index
        self.verbose = verbose

        # 文件路径
        self.log_folder = configure.log_folder
        self.log_path = os.path.join(self.log_folder, f"log_{log_index}")

        # 进程句柄
        self.pin_process: Optional[subprocess.Popen] = None
        self.gdb_process: Optional[pexpect.spawn] = None
        self.gdb_port: int = 0

        # 恢复框架
        self.recovery: Optional[LetGoRecovery] = None

        # 注错信息
        self.inject_info: Optional[InjectionInfo] = None

        # 日志文件
        self.log = None

    def inject_and_recover(self, target_pc: int, target_reg: str,
                          target_kth: int, inject_bit: int = -1) -> str:
        """
        执行Pin注错 + GDB修复的完整流程

        Args:
            target_pc: 目标指令地址（绝对地址）
            target_reg: 目标寄存器
            target_kth: 第K次执行时注错
            inject_bit: 翻转的比特位（-1=随机）

        Returns:
            结果类型：Crash, C-Masked, C-SDC, Recrash, Masked, SDC
        """
        # 打开日志文件
        os.makedirs(self.log_folder, exist_ok=True)
        self.log = open(self.log_path, "w", buffering=1)

        # 重定向stdout/stderr到日志
        original_stdout = sys.__stdout__
        original_stderr = sys.__stderr__
        sys.stdout = self.log
        sys.stderr = self.log

        try:
            print("="*60)
            print(f"Pin+GDB联合注错实验 #{self.log_index}")
            print("="*60)
            print(f"目标指令: 0x{target_pc:x}")
            print(f"目标寄存器: {target_reg}")
            print(f"注错次数: {target_kth}")
            print(f"注错位: {inject_bit}")
            print()

            # Step 1: 启动Pin进程
            inject_info_path = self._start_pin_process(
                target_pc, target_reg, target_kth, inject_bit
            )

            # Step 2: 启动GDB并连接到Pin
            self._start_gdb_and_connect()

            # Step 3: 配置信号处理
            self._configure_signal_handling()

            # Step 4: 继续执行，等待注错和可能的崩溃
            crashed = self._wait_for_injection_and_crash()

            # Step 5: 根据是否崩溃选择处理流程
            if crashed:
                result = self._handle_crash_recovery(inject_info_path)
            else:
                result = self._handle_normal_completion()

            print("="*60)
            print(f"实验结果: {result}")
            print("="*60)

            return result

        except Exception as e:
            print(f"[异常] 注错过程出错: {e}")
            import traceback
            traceback.print_exc()
            return "error"

        finally:
            # 清理资源
            self._cleanup()

            # 恢复stdout/stderr
            sys.stdout = original_stdout
            sys.stderr = original_stderr

            if self.log:
                self.log.close()

    def _start_pin_process(self, target_pc: int, target_reg: str,
                          target_kth: int, inject_bit: int) -> str:
        """启动Pin进程"""
        print("[Pin] 启动Pin注错进程...")

        # 生成inject_info文件路径
        inject_info_path = os.path.join(
            self.log_folder, f"inject_info_{self.log_index}.txt"
        )

        # GDB调试端口（避免冲突）
        import adaptive_fi_config as afi_config
        gdb_port = afi_config.gdb_port_base + (self.log_index % 1000)
        self.gdb_port = gdb_port

        # 构建Pin命令
        pin_cmd = [
            configure.pin_home,
            "-appdebug",                            # 启用GDB调试
            "-appdebug_server_port", str(gdb_port), # GDB调试端口
            "-t", afi_config.targeted_fi_lib_path,  # Pin工具路径
            "-target_pc", hex(target_pc),           # 目标PC
            "-target_reg", target_reg,              # 目标寄存器
            "-target_kth", str(target_kth),         # 第K次执行
            "-inject_bit", str(inject_bit),         # 翻转位
            "-o", inject_info_path,                 # 输出文件
            "--",
            configure.benchmark                     # 被测程序
        ] + configure.args

        print(f"[Pin] 命令: {' '.join(pin_cmd)}")
        print(f"[Pin] GDB端口: {gdb_port}")
        print(f"[Pin] 注错信息输出: {inject_info_path}")

        # 设置环境变量（确保程序输出文件）
        env = os.environ.copy()
        env['OUTPUT'] = '1'  # nn 等程序需要此环境变量才会输出文件

        print(f"[Pin] 设置环境变量: OUTPUT=1")

        # 启动Pin进程（后台）
        self.pin_process = subprocess.Popen(
            pin_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env
        )

        print(f"[Pin] 进程已启动 (PID: {self.pin_process.pid})")

        # 等待GDB服务器就绪（增加到5秒）
        print(f"[Pin] 等待GDB服务器就绪（5秒）...")
        time.sleep(5)

        # 检查 Pin 进程是否仍在运行
        poll_result = self.pin_process.poll()
        if poll_result is not None:
            # Pin 进程已退出
            stdout, stderr = self.pin_process.communicate(timeout=1)
            print(f"[Pin] 错误: Pin进程已退出 (返回码: {poll_result})")
            print(f"[Pin] stdout: {stdout}")
            print(f"[Pin] stderr: {stderr}")
            raise RuntimeError(f"Pin进程启动失败，返回码: {poll_result}")

        print(f"[Pin] Pin进程运行正常")

        return inject_info_path

    def _start_gdb_and_connect(self):
        """启动GDB并连接到Pin"""
        print("[GDB] 启动GDB并连接到Pin...")

        # 启动GDB
        gdb_cmd = f"gdb {configure.benchmark}"
        self.gdb_process = pexpect.spawn(gdb_cmd, timeout=30)

        if self.verbose:
            self.gdb_process.logfile = sys.stdout.buffer

        # 等待GDB提示符
        self.gdb_process.expect("\(gdb\)")
        print("[GDB] GDB已启动")

        # 连接到Pin的调试端口（带重试）
        connect_cmd = f"target remote :{self.gdb_port}"
        max_retries = 3
        connected = False

        for attempt in range(max_retries):
            print(f"[GDB] 尝试连接到Pin: {connect_cmd} (尝试 {attempt + 1}/{max_retries})")
            self.gdb_process.sendline(connect_cmd)

            # 等待连接结果
            patterns = [
                "Remote debugging using",   # 成功
                "Connection timed out",     # 超时
                "Connection refused",       # 拒绝
                "\(gdb\)"                   # GDB提示符
            ]

            try:
                i = self.gdb_process.expect(patterns, timeout=15)
                output = self.gdb_process.before.decode('utf-8', errors='ignore')

                if i == 0:
                    # 连接成功
                    self.gdb_process.expect("\(gdb\)")
                    connected = True
                    print("[GDB] 已成功连接到Pin")
                    break
                elif i == 1 or i == 2:
                    # 连接失败
                    print(f"[GDB] 连接失败: {patterns[i]}")
                    self.gdb_process.expect("\(gdb\)")
                    if attempt < max_retries - 1:
                        print("[GDB] 等待2秒后重试...")
                        time.sleep(2)
                else:
                    # GDB 提示符，检查输出
                    if "Remote debugging" in output:
                        connected = True
                        print("[GDB] 已连接到Pin")
                        break
                    else:
                        print(f"[GDB] 连接状态不明，输出: {output}")
                        if attempt < max_retries - 1:
                            time.sleep(2)

            except pexpect.TIMEOUT:
                print(f"[GDB] 连接超时")
                if attempt < max_retries - 1:
                    time.sleep(2)

        if not connected:
            # 尝试检查 Pin 进程状态
            poll_result = self.pin_process.poll()
            if poll_result is not None:
                stdout, stderr = self.pin_process.communicate(timeout=1)
                print(f"[GDB] Pin进程已退出 (返回码: {poll_result})")
                print(f"[Pin] stderr: {stderr}")
            raise RuntimeError("无法连接到Pin调试端口")

    def _configure_signal_handling(self):
        """配置GDB信号处理"""
        print("[GDB] 配置信号处理...")

        signals = [
            ("SIGSEGV", "段错误"),
            ("SIGBUS", "总线错误"),
            ("SIGFPE", "浮点异常"),
            ("SIGABRT", "终止信号")
        ]

        for sig, desc in signals:
            cmd = f"handle {sig} nopass"
            self.gdb_process.sendline(cmd)
            self.gdb_process.expect("\(gdb\)")
            print(f"[GDB] 配置信号 {sig} (nopass) - {desc}")

        # 其他GDB配置
        self.gdb_process.sendline("set pagination off")
        self.gdb_process.expect("\(gdb\)")

        self.gdb_process.sendline("set confirm off")
        self.gdb_process.expect("\(gdb\)")

        print("[GDB] 信号处理配置完成")

    def _wait_for_injection_and_crash(self) -> bool:
        """
        等待Pin注错和可能的崩溃

        Returns:
            True if crashed, False if completed normally
        """
        print("[GDB] 继续执行程序，等待注错...")

        self.gdb_process.sendline("continue")

        # 等待以下几种情况：
        # 1. 崩溃信号 ("Program received signal")
        # 2. 正常退出 ("exited normally" 或 "exited with code")
        # 3. GDB提示符（其他情况）
        # 4. 超时

        patterns = [
            "Program received signal",    # 0: 崩溃
            "exited normally",            # 1: 正常退出
            "exited with code",           # 2: 非零退出
            "\(gdb\)",                    # 3: GDB提示符
            pexpect.TIMEOUT               # 4: 超时
        ]

        timeout = 300  # 5分钟超时
        i = self.gdb_process.expect(patterns, timeout=timeout)

        output = self.gdb_process.before.decode('utf-8', errors='ignore')

        if i == 0:
            # 崩溃
            print(f"[GDB] 检测到崩溃信号!")
            print(output)

            # 继续expect直到GDB提示符
            self.gdb_process.expect("\(gdb\)")
            return True

        elif i == 1 or i == 2:
            # 正常退出
            exit_type = "正常退出" if i == 1 else "非零退出"
            print(f"[GDB] 程序{exit_type}，未崩溃")

            # 继续expect直到GDB提示符
            self.gdb_process.expect("\(gdb\)")
            return False

        elif i == 3:
            # GDB提示符，检查输出中是否有崩溃信息
            if "Program received signal" in output:
                print(f"[GDB] 检测到崩溃信号!")
                print(output)
                return True
            else:
                print(f"[GDB] 程序正常结束")
                return False

        else:
            # 超时
            print(f"[GDB] 超时 ({timeout}秒)")
            print(output)
            return False

    def _handle_crash_recovery(self, inject_info_path: str) -> str:
        """
        处理崩溃恢复

        Args:
            inject_info_path: inject_info.txt文件路径

        Returns:
            结果类型：C-Masked, C-SDC, Recrash, 或 Crash
        """
        print("\n" + "="*60)
        print("LetGo崩溃恢复框架启动")
        print("="*60)

        # Step 1: 读取inject_info.txt
        if not os.path.exists(inject_info_path):
            print(f"[错误] inject_info.txt不存在: {inject_info_path}")
            return "Crash"

        self.inject_info = self._parse_inject_info(inject_info_path)
        print(f"[注错信息] PC: {self.inject_info.inject_pc}")
        print(f"[注错信息] 寄存器: {self.inject_info.inject_reg}")
        print(f"[注错信息] 原值: {self.inject_info.original_value}")
        print(f"[注错信息] 注错值: {self.inject_info.injected_value}")
        print(f"[注错信息] 下一条指令: {self.inject_info.next_pc}")
        print(f"[注错信息] 写寄存器: {self.inject_info.regw_list}")

        # Step 2: 创建LetGo恢复框架实例
        self.recovery = LetGoRecovery(
            gdb_process=self.gdb_process,
            inject_info=self.inject_info,
            verbose=self.verbose
        )

        # Step 3: 执行修复
        try:
            recovery_success = self.recovery.letgo_frame()

            if not recovery_success:
                print("[修复失败] LetGo修复失败")
                return "Crash"

            print("[修复成功] LetGo修复完成")

        except Exception as e:
            print(f"[修复异常] {e}")
            import traceback
            traceback.print_exc()
            return "Crash"

        # Step 4: 检测错误传播
        print("\n[错误传播检测] 单步执行检测错误传播...")
        recrash = self.recovery.check_error_propagation()

        if recrash:
            print("[错误传播] 检测到二次崩溃 (Recrash)")
            return "Recrash"

        print("[错误传播] 未检测到二次崩溃，继续执行")

        # Step 5: 继续执行到结束
        print("\n[GDB] 继续执行到程序结束...")
        self.gdb_process.sendline("continue")

        patterns = [
            "exited normally",
            "exited with code",
            "Program received signal",
            pexpect.TIMEOUT
        ]

        i = self.gdb_process.expect(patterns, timeout=180)

        if i == 2:
            # 再次崩溃
            print("[GDB] 再次检测到崩溃信号 (Recrash)")
            self.gdb_process.expect("\(gdb\)")
            return "Recrash"

        # 等待GDB提示符
        if i != 3:
            try:
                self.gdb_process.expect("\(gdb\)", timeout=5)
            except:
                pass

        # Step 6: SDC检测
        print("\n[SDC检测] 检查程序输出...")
        has_sdc = self._check_sdc()

        if has_sdc:
            print("[SDC检测] 检测到静默数据损坏 (C-SDC)")
            return "C-SDC"
        else:
            print("[SDC检测] 未检测到数据损坏 (C-Masked)")
            return "C-Masked"

    def _handle_normal_completion(self) -> str:
        """
        处理正常完成（未崩溃）

        Returns:
            结果类型：Masked 或 SDC
        """
        print("\n[正常完成] 程序未崩溃，进行SDC检测...")

        # SDC检测
        has_sdc = self._check_sdc()

        if has_sdc:
            print("[SDC检测] 检测到静默数据损坏 (SDC)")
            return "SDC"
        else:
            print("[SDC检测] 未检测到数据损坏 (Masked)")
            return "Masked"

    def _parse_inject_info(self, inject_info_path: str) -> InjectionInfo:
        """解析inject_info.txt文件"""
        with open(inject_info_path, 'r') as f:
            content = f.read()

        # 解析键值对
        info_dict = {}
        for line in content.strip().split('\n'):
            if ':' in line:
                key, value = line.split(':', 1)
                info_dict[key.strip()] = value.strip()

        # 创建InjectionInfo对象
        return InjectionInfo(
            inject_pc=info_dict.get('inject_pc', ''),
            inject_inst=info_dict.get('inject_inst', ''),
            inject_reg=info_dict.get('inject_reg', ''),
            inject_kth=int(info_dict.get('inject_kth', 0)),
            original_value=info_dict.get('original_value', ''),
            injected_value=info_dict.get('injected_value', ''),
            inject_bit=int(info_dict.get('inject_bit', -1)),
            next_pc=info_dict.get('next_pc', ''),
            regw_list=info_dict.get('regw_list', ''),
            stackw=info_dict.get('stackw', 'no'),
            base=info_dict.get('base', ''),
            index=info_dict.get('index', 'none'),
            displacement=info_dict.get('displacement', '0'),
            scale=info_dict.get('scale', '0')
        )

    def _check_sdc(self) -> bool:
        """
        检查SDC（静默数据损坏）

        Returns:
            True if SDC detected, False otherwise
        """
        # 调用sdcjudger进行SDC检测
        try:
            # 保存SDC检测结果
            sdcjudger.SDC_saver(index=str(self.log_index))

            # 读取日志判断SDC
            with open(self.log_path, 'r') as f:
                log_content = f.read()

            if "Compare within tolerance" in log_content:
                # 检查最后一行的SDC判断结果
                sdc_lines = [line for line in log_content.split('\n')
                            if "Compare within tolerance" in line]
                if sdc_lines:
                    last_sdc_line = sdc_lines[-1]
                    # True表示在容差内（无SDC），False表示SDC
                    if "False" in last_sdc_line:
                        return True  # SDC
                    elif "True" in last_sdc_line:
                        return False  # No SDC

            # 默认无SDC
            return False

        except Exception as e:
            print(f"[SDC检测异常] {e}")
            import traceback
            traceback.print_exc()
            return False

    def _cleanup(self):
        """清理资源"""
        print("\n[清理] 清理资源...")

        # 关闭GDB
        if self.gdb_process:
            try:
                self.gdb_process.sendline("quit")
                self.gdb_process.close(force=True)
                print("[清理] GDB进程已关闭")
            except:
                pass

        # 终止Pin进程
        if self.pin_process:
            try:
                self.pin_process.terminate()
                self.pin_process.wait(timeout=5)
                print("[清理] Pin进程已终止")
            except:
                try:
                    self.pin_process.kill()
                except:
                    pass


def inject_once(target_pc: int, target_reg: str, target_kth: int,
               log_index: int, verbose: bool = False) -> str:
    """
    便捷函数：执行一次Pin+GDB联合注错

    Args:
        target_pc: 目标指令地址
        target_reg: 目标寄存器
        target_kth: 第K次执行时注错
        log_index: 日志序号
        verbose: 是否显示详细信息

    Returns:
        结果类型字符串
    """
    injector = PinGdbInjector(log_index=log_index, verbose=verbose)
    return injector.inject_and_recover(target_pc, target_reg, target_kth)
