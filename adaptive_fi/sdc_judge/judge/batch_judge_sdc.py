#!/usr/bin/env python3
"""
批量SDC判断脚本

对已有的实验结果进行批量SDC判断，将结果保存为JSON。

用法:
    python -m sdc_judge.judge.batch_judge_sdc <one_batch_folder> <app_name> [选项]

示例:
    # 对bicg/adaptive所有实验进行SDC判断
    python -m sdc_judge.judge.batch_judge_sdc /path/to/TargetedBenchmarkResult/bicg/adaptive bicg

    # 仅对log_0到log_99进行判断
    python -m sdc_judge.judge.batch_judge_sdc /path/to/result/bicg/adaptive bicg --range 0-99

    # 强制重新判断已有结果
    python -m sdc_judge.judge.batch_judge_sdc /path/to/result/bicg/adaptive bicg --force
"""

import argparse
import os
import sys
import re
from typing import Tuple, Optional

from .sdc_judge import SDCJudge, SDCJudgeResult


class BatchSDCJudge:
    """批量SDC判断器"""

    def __init__(self, one_batch_folder: str, app_name: str):
        """
        初始化批量判断器

        Args:
            one_batch_folder: 实验文件夹路径
            app_name: 应用名称
        """
        self.one_batch_folder = one_batch_folder
        self.app_name = app_name

        # 路径配置
        self.log_folder = os.path.join(one_batch_folder, "log")
        self.sdcout_folder = os.path.join(one_batch_folder, "sdcout")
        self.sdcresult_folder = os.path.join(one_batch_folder, "sdcresult")

        # 初始化SDC判断器
        self.judge = SDCJudge()

        # 统计信息
        self.total = 0
        self.sdc_count = 0
        self.masked_count = 0
        self.error_count = 0
        self.skipped_count = 0

    def find_output_file(self, log_index: int) -> Optional[str]:
        """
        查找log_N对应的输出文件

        规则：在sdcout/目录中查找log_N_output.*或log_N.*

        Args:
            log_index: 日志序号

        Returns:
            输出文件路径，不存在返回None
        """
        if not os.path.exists(self.sdcout_folder):
            return None

        # 尝试多种输出文件命名规则
        # 优先匹配 log_N_output.扩展名，然后匹配 log_N.扩展名
        # 使用精确的正则表达式，避免log_2匹配到log_210
        patterns = [
            rf"^log_{log_index}_output\..*$",      # log_2_output.dat
            rf"^log_{log_index}_.*$",              # log_2_anything.dat (下划线分隔)
            rf"^log_{log_index}\..*$",             # log_2.dat (直接扩展名)
        ]

        for pattern in patterns:
            regex = re.compile(pattern)
            for filename in os.listdir(self.sdcout_folder):
                if regex.match(filename):
                    return os.path.join(self.sdcout_folder, filename)

        return None

    def get_golden_output(self) -> str:
        """
        获取应用的Golden输出文件路径

        从sdc_judge/golden_outputs/{suite}/{app_name}中查找

        Returns:
            Golden输出文件路径

        Raises:
            FileNotFoundError: 如果Golden输出不存在
        """
        # 导入golden_generator查找golden路径
        from ..golden.golden_generator import GoldenGenerator

        generator = GoldenGenerator()
        app_config = generator.config_mgr.get_app(self.app_name)

        if app_config is None:
            raise ValueError(f"应用不存在: {self.app_name}")

        # 获取golden路径
        golden_dir = generator.capturer.get_golden_path(app_config)

        # 在golden_dir中查找输出文件
        if app_config.output_name and app_config.output_name != 'none':
            golden_output = os.path.join(golden_dir, app_config.output_name)
            if os.path.exists(golden_output):
                return golden_output

        # 尝试在golden_dir中查找第一个文件
        if os.path.exists(golden_dir):
            files = [f for f in os.listdir(golden_dir)
                    if os.path.isfile(os.path.join(golden_dir, f))]
            if files:
                return os.path.join(golden_dir, files[0])

        raise FileNotFoundError(f"Golden输出不存在: {self.app_name}")

    def judge_single(self, log_index: int, force: bool = False, verbose: bool = False) -> bool:
        """
        对单个实验进行SDC判断

        Args:
            log_index: 日志序号
            force: 强制重新判断已有结果
            verbose: 详细输出

        Returns:
            True=判断成功，False=判断失败
        """
        # 检查结果文件是否已存在
        result_file = os.path.join(self.sdcresult_folder, f"sdc_{log_index}.json")
        if os.path.exists(result_file) and not force:
            if verbose:
                print(f"  log_{log_index}: 结果已存在，跳过")
            self.skipped_count += 1
            return True  # 已有结果，跳过

        # 查找输出文件
        test_output = self.find_output_file(log_index)
        if test_output is None:
            if verbose:
                print(f"  log_{log_index}: 找不到输出文件，跳过")
            self.error_count += 1
            return False

        # 获取Golden输出（只需获取一次，后续缓存）
        if not hasattr(self, '_cached_golden_output'):
            try:
                self._cached_golden_output = self.get_golden_output()
            except (FileNotFoundError, ValueError) as e:
                print(f"\n错误: Golden输出获取失败: {e}")
                print("请先运行 generate_single_golden.py 或 generate_all_goldens.py 生成Golden输出")
                return False

        golden_output = self._cached_golden_output

        # 执行SDC判断
        try:
            result = self.judge.judge(
                test_output=test_output,
                golden_output=golden_output,
                app_name=self.app_name,
                log_index=log_index
            )

            # 保存结果
            self.judge.save_result(result, self.sdcresult_folder)

            # 更新统计
            if result.is_sdc:
                self.sdc_count += 1
                if verbose:
                    print(f"  log_{log_index}: SDC")
            else:
                self.masked_count += 1
                if verbose:
                    print(f"  log_{log_index}: Masked")

            return True

        except Exception as e:
            if verbose:
                print(f"  log_{log_index}: 判断失败: {e}")
            self.error_count += 1
            return False

    def scan_log_range(self, log_range: Optional[Tuple[int, int]] = None) -> list:
        """
        扫描日志序号范围

        Args:
            log_range: (start, end)范围，None表示扫描所有

        Returns:
            排序后的日志序号列表
        """
        if not os.path.exists(self.log_folder):
            return []

        log_indices = []
        pattern = re.compile(r'^log_(\d+)$')

        for filename in os.listdir(self.log_folder):
            match = pattern.match(filename)
            if match:
                log_index = int(match.group(1))

                # 检查范围
                if log_range:
                    start, end = log_range
                    if log_index < start or log_index > end:
                        continue

                log_indices.append(log_index)

        return sorted(log_indices)

    def run(self, log_range: Optional[Tuple[int, int]] = None, force: bool = False, verbose: bool = False):
        """
        执行批量SDC判断

        Args:
            log_range: 日志范围 (start, end)
            force: 强制重新判断
            verbose: 详细输出
        """
        # 扫描日志
        log_indices = self.scan_log_range(log_range)

        if not log_indices:
            print("未找到日志文件")
            return

        print(f"\n{'='*60}")
        print(f"批量SDC判断")
        print(f"{'='*60}")
        print(f"实验目录: {self.one_batch_folder}")
        print(f"应用名称: {self.app_name}")
        print(f"扫描范围: log_{log_indices[0]} 到 log_{log_indices[-1]}")
        print(f"总计: {len(log_indices)} 个实验")
        print()

        # 执行判断
        for i, log_index in enumerate(log_indices):
            if (i + 1) % 100 == 0 or i == 0:
                print(f"进度: {i + 1}/{len(log_indices)}", end='\r')

            self.total += 1
            self.judge_single(log_index, force, verbose)

        # 清除进度显示
        print()

        # 输出统计
        print(f"\n{'='*60}")
        print(f"判断完成")
        print(f"{'='*60}")
        print(f"总计: {self.total}")
        print(f"SDC: {self.sdc_count}")
        print(f"Masked: {self.masked_count}")
        print(f"跳过: {self.skipped_count}")
        print(f"错误: {self.error_count}")
        print(f"\n结果保存在: {self.sdcresult_folder}")
        print()


def parse_log_range(range_str: str) -> Tuple[int, int]:
    """
    解析日志范围字符串

    Args:
        range_str: 范围字符串，如 "0-99" 或 "0:99"

    Returns:
        (start, end) 元组

    Raises:
        ValueError: 如果格式错误
    """
    # 支持 - 和 : 两种分隔符
    if '-' in range_str:
        parts = range_str.split('-')
    elif ':' in range_str:
        parts = range_str.split(':')
    else:
        raise ValueError(f"日志范围格式错误: {range_str}，应为 'start-end' 或 'start:end'")

    if len(parts) != 2:
        raise ValueError(f"日志范围格式错误: {range_str}")

    try:
        start = int(parts[0])
        end = int(parts[1])
    except ValueError:
        raise ValueError(f"日志范围格式错误: {range_str}，start和end必须是整数")

    if start > end:
        raise ValueError(f"日志范围错误: start({start}) > end({end})")

    return (start, end)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='批量对实验结果进行SDC判断',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 对bicg/adaptive所有实验进行SDC判断
  %(prog)s /path/to/TargetedBenchmarkResult/bicg/adaptive bicg

  # 仅对log_0到log_99进行判断
  %(prog)s /path/to/result/hotspot/adaptive hotspot --range 0-99

  # 强制重新判断已有结果，并显示详细输出
  %(prog)s /path/to/result/lu/adaptive lu --force --verbose
        """
    )

    parser.add_argument('one_batch_folder', help='实验数据文件夹路径')
    parser.add_argument('app_name', help='应用名称')
    parser.add_argument('--range', '-r', help='日志范围 (start-end)，如 0-99')
    parser.add_argument('--force', '-f', action='store_true', help='强制重新判断已有结果')
    parser.add_argument('--verbose', '-v', action='store_true', help='详细输出')

    args = parser.parse_args()

    # 检查实验文件夹是否存在
    if not os.path.exists(args.one_batch_folder):
        print(f"错误: 实验文件夹不存在: {args.one_batch_folder}")
        sys.exit(1)

    # 解析日志范围
    log_range = None
    if args.range:
        try:
            log_range = parse_log_range(args.range)
        except ValueError as e:
            print(f"错误: {e}")
            sys.exit(1)

    # 执行批量判断
    try:
        batch_judge = BatchSDCJudge(args.one_batch_folder, args.app_name)
        batch_judge.run(log_range, args.force, args.verbose)
    except KeyboardInterrupt:
        print("\n\n用户中断")
        sys.exit(130)
    except Exception as e:
        print(f"\n错误: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
