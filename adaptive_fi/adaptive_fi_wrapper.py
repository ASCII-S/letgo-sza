#!/usr/bin/env python3
"""
adaptive_fi_wrapper.py - 自适应故障注入主控脚本

基于 unified_tracer.so 输出的易崩溃指令及溯源链，实现自适应故障注入。
通过迭代测试和崩溃率筛选，找出高效的注错点。

作者: Claude Code
日期: 2026-01-20
"""

import sys
import os
import json
import random
import argparse
import subprocess
import re
from collections import defaultdict
from typing import List, Dict, Set, Tuple, Optional

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import configure
import sighandler
import InstPoolMaker
from trace_parser import TraceParser, InjectionTarget, CrashScenario
import adaptive_fi_config as afi_config
import pin_gdb_injector


class AdaptiveFaultInjector:
    """自适应故障注入器"""

    def __init__(self):
        self.parser: Optional[TraceParser] = None
        self.scenarios: List[CrashScenario] = []
        self.completed_targets: Set[Tuple[int, str]] = set()
        self.high_efficiency_targets: List[InjectionTarget] = []
        self.all_targets: List[InjectionTarget] = []
        self.log_count = 0
        self.total_insts = 0

        # 深度统计
        self.depth_stats: Dict[int, dict] = defaultdict(lambda: {
            "tested": 0, "high_eff": 0, "total_crashes": 0
        })

    def run_tracer(self, output_path: str = None) -> str:
        """运行 unified_tracer.so 生成溯源 JSON"""
        if output_path is None:
            output_path = afi_config.trace_json_path

        tracer_lib = afi_config.tracer_lib_path
        if not os.path.exists(tracer_lib):
            raise FileNotFoundError(f"unified_tracer.so 不存在: {tracer_lib}")

        execlist = [
            configure.pin_home,
            "-t", tracer_lib,
            "-o", output_path,
            "-depth", str(afi_config.max_depth),
            "--",
            configure.benchmark
        ] + configure.args

        print(f"\n{'='*60}")
        print("运行 unified_tracer.so 生成易崩溃指令溯源...")
        print(f"{'='*60}")
        print(f"命令: {' '.join(execlist)}")
        print(f"输出: {output_path}")
        print(f"超时: {afi_config.tracer_timeout}s")

        try:
            result = subprocess.run(
                execlist,
                capture_output=True,
                text=True,
                timeout=afi_config.tracer_timeout
            )

            if result.returncode != 0:
                print(f"\n错误: unified_tracer.so 执行失败")
                print(f"返回码: {result.returncode}")
                print(f"stderr: {result.stderr}")
                raise RuntimeError("unified_tracer.so 执行失败")

            print(f"✓ 溯源 JSON 生成成功: {output_path}")
            return output_path

        except subprocess.TimeoutExpired:
            print(f"\n错误: unified_tracer.so 执行超时 ({afi_config.tracer_timeout}s)")
            raise

    def load_trace_json(self, json_path: str):
        """加载并解析溯源 JSON"""
        print(f"\n{'='*60}")
        print("加载溯源 JSON...")
        print(f"{'='*60}")

        self.parser = TraceParser(json_path)
        all_scenarios = self.parser.parse()

        # 过滤类型
        if afi_config.filter_cp_types:
            all_scenarios = [s for s in all_scenarios if s.cp_type in afi_config.filter_cp_types]
            print(f"过滤类型: {afi_config.filter_cp_types}")

        # 过滤最小执行次数
        all_scenarios = [s for s in all_scenarios if s.exec_count >= afi_config.min_exec_count]

        # TopP 筛选
        all_scenarios.sort(key=lambda s: s.exec_count, reverse=True)
        self.scenarios = all_scenarios[:afi_config.topp_initial]

        print(self.parser.summary())
        print(f"TopP 筛选后: {len(self.scenarios)} %的崩溃场景")

    def get_total_insts(self) -> int:
        """获取程序总指令数"""
        if not os.path.exists(configure.instcount):
            print(f"警告: instcount 文件不存在: {configure.instcount}")
            return 1000000  # 默认值

        with open(configure.instcount, 'r') as f:
            line = f.readline()
            if ':' in line:
                return int(line.split(':')[1].strip())
        return 1000000

    def _get_start_log_count(self) -> int:
        """获取起始日志序号"""
        if not os.path.exists(afi_config.log_folder):
            os.makedirs(afi_config.log_folder)
            return 0

        max_num = -1
        pattern = re.compile(r"log_(\d+)")
        for f in os.listdir(afi_config.log_folder):
            match = pattern.match(f)
            if match:
                max_num = max(max_num, int(match.group(1)))
        return max_num + 1

    def determine_reg_type(self, register: str, disasm: str) -> Tuple[str, str]:
        """判断寄存器类型：(regmm, reg)"""
        # 简化处理：根据指令是否包含内存操作判断
        disasm_lower = disasm.lower()

        # 如果指令包含内存操作符号 [...]
        if '[' in disasm_lower and ']' in disasm_lower:
            # 提取方括号内容
            mem_part = disasm_lower.split('[')[1].split(']')[0]
            # 如果寄存器在内存操作中
            if register.lower() in mem_part:
                return (register, "")  # regmm 类型

        # 默认为普通寄存器
        return ("", register)

    def create_temp_pool(self, target: InjectionTarget, iteration: int):
        """创建临时 pool 文件供 sighandler 读取"""
        regmm, reg = self.determine_reg_type(target.register, target.disasm)

        # 生成随机数（用于兼容性）
        randomnum = random.randint(1, self.total_insts)

        # 将相对偏移转换为绝对地址
        # 如果 offset 小于基址，假定它是相对偏移量，需要加上基址
        base_addr = afi_config.program_base_address
        absolute_address = target.offset
        if target.offset < base_addr:
            # 这是相对偏移量，加上基址
            absolute_address = base_addr + target.offset
            if afi_config.verbose and afi_config.print_each_injection:
                print(f"  [地址转换] 偏移 0x{target.offset:x} -> 绝对地址 0x{absolute_address:x}")

        # 写入 pool 文件（格式与 InstPoolMaker 一致）
        pool_path = afi_config.temp_pool_path
        with open(pool_path, 'w') as f:
            # 格式: regmm,reg,pc(十进制),iteration,randomnum
            f.write(f"{regmm},{reg},{absolute_address},{iteration},{randomnum}\n")

        if afi_config.print_each_injection:
            print(f"  Pool: {regmm},{reg},{absolute_address},{iteration},{randomnum}")

    def _convert_to_absolute_address(self, offset: int) -> int:
        """将相对偏移转换为绝对地址"""
        base_addr = afi_config.program_base_address

        if offset < base_addr:
            # 这是相对偏移，加上基址
            return base_addr + offset
        else:
            # 已经是绝对地址
            return offset

    def inject_once(self, target: InjectionTarget, iteration: int) -> str:
        """执行一次注错，返回结果类型"""
        # 判断使用哪种注错方式
        if afi_config.use_pin_injection:
            # 使用Pin注错
            return self._inject_with_pin(target, iteration)
        else:
            # 使用GDB注错（原方式）
            return self._inject_with_gdb(target, iteration)

    def _inject_with_pin(self, target: InjectionTarget, iteration: int) -> str:
        """使用Pin工具进行注错"""
        # 转换为绝对地址
        absolute_address = self._convert_to_absolute_address(target.offset)

        # 调用Pin+GDB注错器
        try:
            result = pin_gdb_injector.inject_once(
                target_pc=absolute_address,
                target_reg=target.register,
                target_kth=iteration,
                log_index=self.log_count,
                verbose=afi_config.verbose
            )

            self.log_count += 1
            return result

        except Exception as e:
            print(f"  Pin注错失败: {e}")
            import traceback
            traceback.print_exc()
            self.log_count += 1
            return "error"

    def _inject_with_gdb(self, target: InjectionTarget, iteration: int) -> str:
        """使用GDB进行注错（原方式）"""
        # 创建临时 pool
        self.create_temp_pool(target, iteration)

        # 保存原始 stdout/stderr（SigHandler 会重定向它们）
        original_stdout = sys.__stdout__
        original_stderr = sys.__stderr__

        sig = None
        # 调用 sighandler 执行完整注错流程
        try:
            # 确保 configure.inject_random_or_targeted = "targeted"
            original_mode = configure.inject_random_or_targeted
            configure.inject_random_or_targeted = "targeted"

            sig = sighandler.SigHandler(self.total_insts, self.log_count)
            sig.executeProgram(sig.process)

            # 恢复原模式
            configure.inject_random_or_targeted = original_mode

            self.log_count += 1

            # 解析日志判断结果
            return self.parse_log_result(self.log_count - 1)

        except Exception as e:
            # 先恢复 stdout 再打印错误
            sys.stdout = original_stdout
            sys.stderr = original_stderr
            import traceback
            print(f"  GDB注错失败: {e}")
            traceback.print_exc()
            self.log_count += 1
            return "error"

        finally:
            # 确保关闭日志文件和进程
            if sig is not None:
                try:
                    if hasattr(sig, 'log') and sig.log and not sig.log.closed:
                        sig.log.close()
                    if hasattr(sig, 'process') and sig.process:
                        sig.process.terminate()
                        sig.process.close()
                except:
                    pass
            # 确保恢复 stdout/stderr
            sys.stdout = original_stdout
            sys.stderr = original_stderr

    def parse_log_result(self, log_index: int) -> str:
        """解析日志文件，返回结果类型"""
        log_path = os.path.join(afi_config.log_folder, f"log_{log_index}")

        if not os.path.exists(log_path):
            return "error"

        with open(log_path, 'r') as f:
            content = f.read()

        # 计算崩溃次数
        crash_count = content.count("Program received signal")

        if crash_count == 0:
            # 无崩溃
            if "Compare within tolerance" in content:
                # 检查 SDC
                sdc_line = [line for line in content.split('\n') if "Compare within tolerance" in line]
                if sdc_line and "False" in sdc_line[-1]:
                    return "SDC"
            return "Masked"

        elif crash_count == 1:
            # 一次崩溃
            if "Letgo in!" in content:
                # 进入修复
                if "Compare within tolerance" in content:
                    sdc_line = [line for line in content.split('\n') if "Compare within tolerance" in line]
                    if sdc_line and "False" in sdc_line[-1]:
                        return "C-SDC"
                return "C-Masked"
            else:
                # 崩溃但未进入修复
                return "Crash"

        else:
            # 二次崩溃
            return "Recrash"

    def process_target(self, target: InjectionTarget, scenario: CrashScenario) -> bool:
        """处理单个注错目标，返回是否需要继续溯源"""
        if target.key in self.completed_targets:
            return False

        if afi_config.verbose:
            print(f"\n[Depth {target.depth}] 测试: 0x{target.offset:x} ({target.register})")
            print(f"  指令: {target.disasm}")
            print(f"  执行次数: {target.exec_count}")

        # 执行 N 次注错
        for i in range(afi_config.injections_per_target):
            # 随机选择 iteration
            max_iter = min(target.exec_count, afi_config.max_exec_count_for_iteration)
            iteration = random.randint(1, max_iter) if max_iter > 1 else 1

            result = self.inject_once(target, iteration)
            target.injection_count += 1
            target.results.append(result)

            # 统计结果
            if result in ["Crash", "Recrash"]:
                target.crash_count += 1
            elif result in ["C-Masked", "C-SDC"]:
                target.crash_count += 1  # 修复后也算崩溃
            elif result == "Masked":
                target.masked_count += 1
            elif result == "SDC":
                target.sdc_count += 1

            if afi_config.print_each_injection:
                print(f"    [{i+1}/{afi_config.injections_per_target}] iter={iteration} -> {result}")

        crash_rate = target.crash_rate
        if afi_config.verbose:
            print(f"  崩溃率: {crash_rate:.1%} ({target.crash_count}/{target.injection_count})")
            print(f"  结果: Masked={target.masked_count}, SDC={target.sdc_count}, Crash={target.crash_count}")

        # 记录统计
        self.completed_targets.add(target.key)
        self.all_targets.append(target)
        self.depth_stats[target.depth]["tested"] += 1
        self.depth_stats[target.depth]["total_crashes"] += target.crash_count

        # 判断是否为高效注错点
        if crash_rate >= afi_config.crash_threshold:
            self.high_efficiency_targets.append(target)
            self.depth_stats[target.depth]["high_eff"] += 1
            if afi_config.verbose:
                print(f"  ✓ 高效注错点！")
            return True  # 需要继续溯源

        return False

    def get_next_depth_targets(self, target: InjectionTarget,
                               scenario: CrashScenario) -> List[InjectionTarget]:
        """获取下一深度的溯源目标"""
        next_targets = []
        next_depth = target.depth + 1

        # 获取该寄存器的溯源指令
        sources = scenario.get_sources_at_depth(target.register, next_depth)

        for src in sources:
            # 创建新的注错目标
            new_target = InjectionTarget(
                offset=src.offset,
                register=target.register,  # 继承寄存器
                disasm=src.disasm,
                depth=src.depth,
                exec_count=src.hit_count,
                parent_offset=target.offset
            )
            next_targets.append(new_target)

        # TopP 筛选（按 exec_count 排序）
        next_targets.sort(key=lambda t: t.exec_count, reverse=True)
        return next_targets[:afi_config.topp_trace]

    def run(self, json_path: str = None):
        """运行自适应注错"""
        print(f"\n{'='*60}")
        print("自适应故障注入 - 启动")
        print(f"{'='*60}")
        afi_config.print_config()

        # 0. 如果 JSON 不存在，自动生成
        if json_path is None:
            json_path = afi_config.trace_json_path

        if not os.path.exists(json_path):
            if afi_config.auto_run_tracer:
                print(f"溯源 JSON 不存在，自动运行 unified_tracer.so...")
                json_path = self.run_tracer(json_path)
            else:
                raise FileNotFoundError(f"溯源 JSON 不存在: {json_path}")

        # 1. 加载溯源 JSON
        self.load_trace_json(json_path)

        # 2. 获取总指令数
        self.total_insts = self.get_total_insts()
        print(f"程序总指令数: {self.total_insts}")

        # 3. 初始化日志序号
        self.log_count = self._get_start_log_count()
        print(f"日志起始序号: {self.log_count}")

        # 4. 构建分层队列 (BFS by depth, DFS by registers)
        depth_queues: Dict[int, List[Tuple[InjectionTarget, CrashScenario]]] = defaultdict(list)

        # 初始化 depth=0 队列（DFS处理同一指令的所有寄存器）
        for scenario in self.scenarios:
            for reg in scenario.crash_regs:
                target = scenario.create_target(reg, depth=0)
                depth_queues[0].append((target, scenario))

        print(f"\n初始队列: {len(depth_queues[0])} 个目标 (depth=0)")

        # 5. BFS 按深度处理
        current_depth = 0
        while current_depth <= afi_config.max_depth:
            if not depth_queues[current_depth]:
                if afi_config.verbose:
                    print(f"\n[Depth {current_depth}] 队列为空，停止")
                break

            print(f"\n{'='*60}")
            print(f"处理深度 {current_depth} ({len(depth_queues[current_depth])} 个目标)")
            print(f"{'='*60}")

            # 处理当前深度的所有目标
            for idx, (target, scenario) in enumerate(depth_queues[current_depth]):
                if afi_config.verbose:
                    print(f"\n进度: [{idx+1}/{len(depth_queues[current_depth])}]")

                need_trace = self.process_target(target, scenario)

                # 如果是高效注错点，添加下一深度的溯源目标（TopP筛选）
                if need_trace and current_depth < afi_config.max_depth:
                    next_targets = self.get_next_depth_targets(target, scenario)
                    for nt in next_targets:
                        if nt.key not in self.completed_targets:
                            depth_queues[current_depth + 1].append((nt, scenario))

            # 深度统计
            stats = self.depth_stats[current_depth]
            print(f"\n[Depth {current_depth}] 统计:")
            print(f"  测试目标: {stats['tested']}")
            print(f"  高效注错点: {stats['high_eff']}")
            print(f"  总崩溃: {stats['total_crashes']}")

            # 生成中间报告
            if afi_config.generate_intermediate_reports:
                self._save_intermediate_report(current_depth)

            current_depth += 1

        # 6. 生成最终结果
        print(f"\n{'='*60}")
        print("保存结果...")
        print(f"{'='*60}")
        self.save_results()

    def _save_intermediate_report(self, depth: int):
        """保存中间统计报告"""
        report_dir = os.path.dirname(afi_config.output_json_path)
        report_path = os.path.join(
            report_dir if report_dir else ".",
            f"adaptive_fi_depth{depth}_report.json"
        )

        # 确保目录存在
        if report_dir and not os.path.exists(report_dir):
            os.makedirs(report_dir)

        report = {
            "depth": depth,
            "tested": self.depth_stats[depth]["tested"],
            "high_eff": self.depth_stats[depth]["high_eff"],
            "total_crashes": self.depth_stats[depth]["total_crashes"],
            "targets": [t.to_dict() for t in self.all_targets if t.depth == depth]
        }

        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)

        if afi_config.verbose:
            print(f"  中间报告已保存: {report_path}")

    def save_results(self):
        """保存统计结果到 JSON"""
        total_injections = sum(t.injection_count for t in self.all_targets)
        total_crashes = sum(t.crash_count for t in self.all_targets)

        result = {
            "config": {
                "crash_threshold": afi_config.crash_threshold,
                "injections_per_target": afi_config.injections_per_target,
                "topp_initial": afi_config.topp_initial,
                "topp_trace": afi_config.topp_trace,
                "max_depth": afi_config.max_depth,
                "program": configure.progname,
                "benchmark": configure.benchmark
            },
            "summary": {
                "total_targets_tested": len(self.all_targets),
                "high_efficiency_targets": len(self.high_efficiency_targets),
                "total_injections": total_injections,
                "total_crashes": total_crashes,
                "overall_crash_rate": total_crashes / max(1, total_injections),
                "log_start": self.log_count - total_injections,
                "log_end": self.log_count - 1
            },
            "depth_statistics": {
                str(depth): stats for depth, stats in self.depth_stats.items()
            },
            "high_efficiency_targets": [
                t.to_dict() for t in self.high_efficiency_targets
            ],
            "all_targets": [
                t.to_dict() for t in self.all_targets
            ]
        }

        # 确保输出目录存在
        output_dir = os.path.dirname(afi_config.output_json_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
            print(f"创建输出目录: {output_dir}")

        with open(afi_config.output_json_path, 'w') as f:
            json.dump(result, f, indent=2)

        # 打印摘要
        print(f"\n{'='*60}")
        print("实验结果摘要")
        print(f"{'='*60}")
        print(f"测试目标总数:       {len(self.all_targets)}")
        print(f"高效注错点:         {len(self.high_efficiency_targets)}")
        print(f"总注错次数:         {total_injections}")
        print(f"总崩溃次数:         {total_crashes}")
        print(f"整体崩溃率:         {result['summary']['overall_crash_rate']:.1%}")
        print(f"日志范围:           log_{result['summary']['log_start']} - log_{result['summary']['log_end']}")
        print(f"\n结果已保存至: {afi_config.output_json_path}")
        print(f"{'='*60}")

        # 打印高效注错点摘要
        if self.high_efficiency_targets:
            print(f"\n高效注错点列表 (前 10 个):")
            for i, target in enumerate(self.high_efficiency_targets[:10]):
                print(f"  [{i+1}] 0x{target.offset:x} ({target.register}) depth={target.depth} "
                      f"crash_rate={target.crash_rate:.1%}")


def main():
    parser = argparse.ArgumentParser(
        description="自适应故障注入 - 基于易崩溃指令溯源",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 自动生成溯源并注错
  python adaptive_fi_wrapper.py --threshold 0.3 --injections 10

  # 使用已有 JSON
  python adaptive_fi_wrapper.py -i trace_result.json

  # 快速测试模式
  python adaptive_fi_wrapper.py --quick-test

  # 只生成溯源 JSON
  python adaptive_fi_wrapper.py --trace-only
        """
    )

    parser.add_argument('-i', '--input', help='输入溯源 JSON 文件（不存在则自动生成）')
    parser.add_argument('-o', '--output', help='输出结果 JSON 文件')
    parser.add_argument('--threshold', type=float, help='崩溃率阈值 (0-1)')
    parser.add_argument('--injections', type=int, help='每目标注错次数')
    parser.add_argument('--topp', type=int, help='初始 TopP')
    parser.add_argument('--topp-trace', type=int, help='溯源 TopP')
    parser.add_argument('--max-depth', type=int, help='最大溯源深度')
    parser.add_argument('--trace-only', action='store_true', help='仅生成溯源 JSON，不注错')
    parser.add_argument('--quick-test', action='store_true', help='快速测试模式')
    parser.add_argument('--full-exp', action='store_true', help='完整实验模式')
    parser.add_argument('--no-verbose', action='store_true', help='关闭详细输出')
    parser.add_argument('--use-pin', action='store_true', help='使用Pin工具注错（默认）')
    parser.add_argument('--use-gdb', action='store_true', help='使用GDB断点注错')

    args = parser.parse_args()

    # 应用命令行参数
    if args.quick_test:
        afi_config.set_quick_test_config()
    elif args.full_exp:
        afi_config.set_full_experiment_config()

    if args.input:
        afi_config.trace_json_path = args.input
    if args.output:
        afi_config.output_json_path = args.output
    if args.threshold is not None:
        afi_config.crash_threshold = args.threshold
    if args.injections:
        afi_config.injections_per_target = args.injections
    if args.topp:
        afi_config.topp_initial = args.topp
    if args.topp_trace:
        afi_config.topp_trace = args.topp_trace
    if args.max_depth is not None:
        afi_config.max_depth = args.max_depth
    if args.no_verbose:
        afi_config.verbose = False
    if args.use_gdb:
        afi_config.use_pin_injection = False
    if args.use_pin:
        afi_config.use_pin_injection = True

    # 验证配置
    if not afi_config.validate_config():
        print("配置验证失败，退出")
        sys.exit(1)

    # 仅生成溯源 JSON
    if args.trace_only:
        injector = AdaptiveFaultInjector()
        json_path = injector.run_tracer(afi_config.trace_json_path)
        print(f"\n溯源 JSON 已生成: {json_path}")
        sys.exit(0)

    # 运行自适应注错
    injector = AdaptiveFaultInjector()
    try:
        injector.run(afi_config.trace_json_path)
    except KeyboardInterrupt:
        print("\n\n用户中断，保存当前结果...")
        injector.save_results()
        sys.exit(0)
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
