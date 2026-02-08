#!/usr/bin/env python3
"""
批量收集日志脚本

批量处理 TargetedBenchmarkResult 目录下所有应用程序的日志，
为每个应用生成独立的CSV文件。

用法:
    python batch_collect_logs.py [选项]

示例:
    # 处理所有应用程序
    python batch_collect_logs.py

    # 指定输出目录
    python batch_collect_logs.py --output-dir ./results

    # 处理指定的应用程序
    python batch_collect_logs.py --apps backprop hpl kmeans

    # 详细输出
    python batch_collect_logs.py --verbose
"""

import argparse
import os
import sys
from typing import List, Dict
from datetime import datetime

# 添加父目录到路径以便导入模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from log_collector import LogCollector


def find_log_folders(base_dir: str) -> List[Dict[str, str]]:
    """
    扫描基准测试结果目录，找到所有log文件夹

    Args:
        base_dir: TargetedBenchmarkResult 基准目录

    Returns:
        包含应用程序信息的字典列表
    """
    log_folders = []

    if not os.path.exists(base_dir):
        print(f"⚠️  目录不存在: {base_dir}")
        return log_folders

    # 遍历应用程序目录
    for app_name in os.listdir(base_dir):
        app_path = os.path.join(base_dir, app_name)

        # 跳过文件
        if not os.path.isdir(app_path):
            continue

        # 遍历 select_type 目录（如 adaptive）
        for select_type in os.listdir(app_path):
            select_type_path = os.path.join(app_path, select_type)

            # 跳过文件
            if not os.path.isdir(select_type_path):
                continue

            # 检查是否有 log 文件夹
            log_folder = os.path.join(select_type_path, 'log')
            if os.path.exists(log_folder) and os.path.isdir(log_folder):
                # 统计日志数量
                log_files = [f for f in os.listdir(log_folder) if f.startswith('log_')]

                log_folders.append({
                    'app_name': app_name,
                    'select_type': select_type,
                    'log_folder': log_folder,
                    'batch_folder': select_type_path,
                    'log_count': len(log_files)
                })

    # 按应用名称排序
    log_folders.sort(key=lambda x: x['app_name'])

    return log_folders


def process_application(app_info: Dict,
                       output_dir: str,
                       verbose: bool = False,
                       show_statistics: bool = False) -> bool:
    """
    处理单个应用程序的日志

    Args:
        app_info: 应用程序信息字典
        output_dir: 输出目录
        verbose: 是否详细输出
        show_statistics: 是否显示统计信息

    Returns:
        是否成功
    """
    app_name = app_info['app_name']
    select_type = app_info['select_type']
    log_folder = app_info['log_folder']
    log_count = app_info['log_count']

    print(f"\n{'='*60}")
    print(f"处理应用程序: {app_name} ({select_type})")
    print(f"日志文件数: {log_count}")
    print(f"{'='*60}")

    if log_count == 0:
        print("⚠️  没有日志文件，跳过")
        return False

    try:
        # 创建收集器
        collector = LogCollector(log_folder, app_name)

        # 收集日志（跳过验证以提高速度）
        df = collector.collect_all(verbose=verbose, validate=False)

        if df.empty:
            print("⚠️  未找到有效数据")
            return False

        # 生成输出文件名
        output_filename = f"{app_name}_{select_type}_logs.csv"
        output_path = os.path.join(output_dir, output_filename)

        # 生成CSV
        collector.generate_csv(output_path, show_statistics=False)

        print(f"✓ CSV文件已生成: {output_path}")

        # 显示统计信息
        if show_statistics or verbose:
            collector.csv_gen.print_statistics()

        # 显示摘要
        if verbose:
            collector.print_summary()

        return True

    except Exception as e:
        print(f"❌ 错误: {e}")
        if verbose:
            import traceback
            traceback.print_exc()
        return False


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='批量收集 TargetedBenchmarkResult 目录下所有应用程序的日志',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 处理所有应用程序
  %(prog)s

  # 指定输出目录
  %(prog)s --output-dir ./results

  # 处理指定的应用程序
  %(prog)s --apps backprop hpl kmeans

  # 详细输出并显示统计信息
  %(prog)s --verbose --statistics
        """
    )

    parser.add_argument(
        '--base-dir',
        default='/home/tongshiyu/pin/source/tools/letgo/TargetedBenchmarkResult',
        help='TargetedBenchmarkResult 基准目录路径'
    )

    parser.add_argument(
        '--output-dir', '-o',
        default=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'results', 'all_apps'),
        help='输出目录路径（默认：../results/all_apps）'
    )

    parser.add_argument(
        '--apps',
        nargs='+',
        help='指定要处理的应用程序列表（默认：处理所有）'
    )

    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='详细输出'
    )

    parser.add_argument(
        '--statistics', '-s',
        action='store_true',
        help='显示每个应用的统计摘要'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='仅列出将要处理的应用程序，不实际执行'
    )

    args = parser.parse_args()

    # 查找所有log文件夹
    print("正在扫描应用程序...")
    log_folders = find_log_folders(args.base_dir)

    if not log_folders:
        print("❌ 未找到任何包含日志的应用程序")
        sys.exit(1)

    # 过滤指定的应用程序
    if args.apps:
        log_folders = [
            info for info in log_folders
            if info['app_name'] in args.apps
        ]

        if not log_folders:
            print(f"❌ 未找到指定的应用程序: {', '.join(args.apps)}")
            sys.exit(1)

    # 显示找到的应用程序
    print(f"\n找到 {len(log_folders)} 个应用程序:")
    print(f"{'序号':<6}{'应用名称':<20}{'类型':<12}{'日志数':<10}{'路径'}")
    print("-" * 100)
    for i, info in enumerate(log_folders, 1):
        print(f"{i:<6}{info['app_name']:<20}{info['select_type']:<12}"
              f"{info['log_count']:<10}{info['log_folder']}")

    total_logs = sum(info['log_count'] for info in log_folders)
    print(f"\n总计: {len(log_folders)} 个应用程序，{total_logs} 个日志文件")

    # Dry run模式
    if args.dry_run:
        print("\n[Dry Run 模式] 仅列出，不实际执行")
        return

    # 创建输出目录
    os.makedirs(args.output_dir, exist_ok=True)
    print(f"\n输出目录: {args.output_dir}")

    # 处理每个应用程序
    print("\n" + "=" * 60)
    print("开始批量处理...")
    print("=" * 60)

    success_count = 0
    failed_apps = []

    start_time = datetime.now()

    for i, app_info in enumerate(log_folders, 1):
        print(f"\n[{i}/{len(log_folders)}]", end=' ')

        success = process_application(
            app_info,
            args.output_dir,
            verbose=args.verbose,
            show_statistics=args.statistics
        )

        if success:
            success_count += 1
        else:
            failed_apps.append(app_info['app_name'])

    # 最终摘要
    end_time = datetime.now()
    elapsed = end_time - start_time

    print("\n" + "=" * 60)
    print("批量处理完成")
    print("=" * 60)
    print(f"总应用数: {len(log_folders)}")
    print(f"成功: {success_count}")
    print(f"失败: {len(failed_apps)}")

    if failed_apps:
        print(f"\n失败的应用程序: {', '.join(failed_apps)}")

    print(f"\n总耗时: {elapsed}")
    print(f"输出目录: {os.path.abspath(args.output_dir)}")

    # 列出生成的文件
    csv_files = [f for f in os.listdir(args.output_dir) if f.endswith('.csv')]
    if csv_files:
        print(f"\n生成的CSV文件 ({len(csv_files)}个):")
        for csv_file in sorted(csv_files):
            file_path = os.path.join(args.output_dir, csv_file)
            file_size = os.path.getsize(file_path)
            print(f"  - {csv_file} ({file_size:,} bytes)")


if __name__ == '__main__':
    main()
