#!/usr/bin/env python3
"""
批量对所有应用进行SDC判断

扫描实验结果目录，对所有已有实验记录的应用进行SDC判断。

用法:
    python -m sdc_judge.batch_judge_all_apps <result_base_dir> [选项]

示例:
    # 对所有应用进行SDC判断
    python -m sdc_judge.batch_judge_all_apps /path/to/TargetedBenchmarkResult

    # 指定范围并强制重新判断
    python -m sdc_judge.batch_judge_all_apps /path/to/TargetedBenchmarkResult --range 0-99 --force

    # 只处理特定应用
    python -m sdc_judge.batch_judge_all_apps /path/to/TargetedBenchmarkResult --apps backprop hotspot
"""

import argparse
import os
import sys
from typing import List, Optional, Tuple

from .judge.batch_judge_sdc import BatchSDCJudge, parse_log_range


class BatchJudgeAllApps:
    """批量对所有应用进行SDC判断"""

    def __init__(self, result_base_dir: str):
        """
        初始化

        Args:
            result_base_dir: 实验结果基础目录（如 TargetedBenchmarkResult/）
        """
        self.result_base_dir = result_base_dir
        self.total_apps = 0
        self.success_apps = 0
        self.failed_apps = []

    def scan_apps(self, app_filter: Optional[List[str]] = None) -> List[Tuple[str, str]]:
        """
        扫描所有可用的应用实验目录

        Args:
            app_filter: 应用名称过滤列表，None表示处理所有

        Returns:
            [(app_name, adaptive_path), ...] 列表
        """
        if not os.path.exists(self.result_base_dir):
            raise FileNotFoundError(f"实验结果目录不存在: {self.result_base_dir}")

        apps = []

        # 扫描所有子目录
        for item in os.listdir(self.result_base_dir):
            item_path = os.path.join(self.result_base_dir, item)

            # 跳过非目录项
            if not os.path.isdir(item_path):
                continue

            # 跳过特殊目录
            if item.startswith('.') or item in ['Readme.md']:
                continue

            # 检查是否在过滤列表中
            if app_filter and item not in app_filter:
                continue

            # 检查是否有 adaptive 子目录
            adaptive_path = os.path.join(item_path, 'adaptive')
            if os.path.exists(adaptive_path) and os.path.isdir(adaptive_path):
                # 检查是否有 log 和 sdcout 目录
                log_path = os.path.join(adaptive_path, 'log')
                sdcout_path = os.path.join(adaptive_path, 'sdcout')

                if os.path.exists(log_path) and os.path.exists(sdcout_path):
                    apps.append((item, adaptive_path))
                else:
                    print(f"⚠️  {item}: adaptive 目录缺少 log/ 或 sdcout/，跳过")

        return sorted(apps)

    def judge_single_app(
        self,
        app_name: str,
        adaptive_path: str,
        log_range: Optional[Tuple[int, int]] = None,
        force: bool = False,
        verbose: bool = False
    ) -> bool:
        """
        对单个应用进行SDC判断

        Args:
            app_name: 应用名称
            adaptive_path: adaptive 文件夹路径
            log_range: 日志范围
            force: 强制重新判断
            verbose: 详细输出

        Returns:
            True=成功，False=失败
        """
        print(f"\n{'='*60}")
        print(f"处理应用: {app_name}")
        print(f"{'='*60}")

        try:
            batch_judge = BatchSDCJudge(adaptive_path, app_name)
            batch_judge.run(log_range, force, verbose)

            # 检查是否有判断成功
            if batch_judge.total > 0:
                success_rate = (batch_judge.sdc_count + batch_judge.masked_count) / batch_judge.total * 100
                print(f"\n✓ {app_name}: 判断成功率 {success_rate:.1f}%")
                return True
            else:
                print(f"\n✗ {app_name}: 未找到可判断的日志")
                return False

        except Exception as e:
            print(f"\n✗ {app_name}: 判断失败: {e}")
            return False

    def run(
        self,
        app_filter: Optional[List[str]] = None,
        log_range: Optional[Tuple[int, int]] = None,
        force: bool = False,
        verbose: bool = False
    ):
        """
        执行批量SDC判断

        Args:
            app_filter: 应用名称过滤列表
            log_range: 日志范围
            force: 强制重新判断
            verbose: 详细输出
        """
        # 扫描应用
        apps = self.scan_apps(app_filter)

        if not apps:
            print("未找到可处理的应用")
            if app_filter:
                print(f"过滤条件: {', '.join(app_filter)}")
            return

        self.total_apps = len(apps)

        print(f"\n{'='*60}")
        print(f"批量SDC判断 - 所有应用")
        print(f"{'='*60}")
        print(f"实验目录: {self.result_base_dir}")
        print(f"找到应用: {self.total_apps} 个")
        if app_filter:
            print(f"过滤条件: {', '.join(app_filter)}")
        if log_range:
            print(f"日志范围: log_{log_range[0]} 到 log_{log_range[1]}")
        print(f"强制重判: {'是' if force else '否'}")
        print(f"{'='*60}")

        # 列出所有应用
        print(f"\n应用列表:")
        for i, (app_name, _) in enumerate(apps, 1):
            print(f"  {i}. {app_name}")

        # 逐个处理
        for i, (app_name, adaptive_path) in enumerate(apps, 1):
            print(f"\n[{i}/{self.total_apps}] 开始处理: {app_name}")

            success = self.judge_single_app(
                app_name, adaptive_path, log_range, force, verbose
            )

            if success:
                self.success_apps += 1
            else:
                self.failed_apps.append(app_name)

        # 输出汇总
        self._print_summary()

    def _print_summary(self):
        """输出汇总信息"""
        print(f"\n{'='*60}")
        print(f"批量SDC判断完成")
        print(f"{'='*60}")
        print(f"总计应用: {self.total_apps}")
        print(f"成功: {self.success_apps}")
        print(f"失败: {len(self.failed_apps)}")

        if self.failed_apps:
            print(f"\n失败的应用:")
            for app in self.failed_apps:
                print(f"  - {app}")
        else:
            print(f"\n✓ 所有应用SDC判断完成!")

        print(f"{'='*60}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='批量对所有应用进行SDC判断',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 对所有应用进行SDC判断
  %(prog)s /path/to/TargetedBenchmarkResult

  # 指定范围并强制重新判断
  %(prog)s /path/to/TargetedBenchmarkResult --range 0-99 --force

  # 只处理特定应用
  %(prog)s /path/to/TargetedBenchmarkResult --apps backprop hotspot bfs

  # 详细输出模式
  %(prog)s /path/to/TargetedBenchmarkResult --verbose
        """
    )

    parser.add_argument(
        'result_base_dir',
        help='实验结果基础目录（如 TargetedBenchmarkResult/）'
    )

    parser.add_argument(
        '--apps', '-a',
        nargs='+',
        help='指定要处理的应用名称（默认：所有）'
    )

    parser.add_argument(
        '--range', '-r',
        help='日志范围 (start-end)，如 0-99'
    )

    parser.add_argument(
        '--force', '-f',
        action='store_true',
        help='强制重新判断已有结果'
    )

    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='详细输出'
    )

    args = parser.parse_args()

    # 检查目录是否存在
    if not os.path.exists(args.result_base_dir):
        print(f"错误: 实验结果目录不存在: {args.result_base_dir}")
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
        batch_judge = BatchJudgeAllApps(args.result_base_dir)
        batch_judge.run(
            app_filter=args.apps,
            log_range=log_range,
            force=args.force,
            verbose=args.verbose
        )

        # 根据结果设置退出码
        if batch_judge.failed_apps:
            sys.exit(1)
        else:
            sys.exit(0)

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
