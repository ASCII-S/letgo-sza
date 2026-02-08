#!/usr/bin/env python3
"""
自适应故障注入日志收集脚本

从 adaptive_fi 实验日志中提取信息并生成CSV文件。

用法:
    python collect_logs.py <one_batch_folder> [选项]

示例:
    # 基本使用
    python collect_logs.py /path/to/experiment/bicg/div

    # 指定输出和范围
    python collect_logs.py /path/to/experiment/bicg/div \\
        --output ./results/bicg_div.csv \\
        --app-name bicg \\
        --log-range 0-500 \\
        --verbose
"""

import argparse
import os
import sys
from typing import Optional

# 添加父目录到路径以便导入模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from log_collector import LogCollector
from log_collector.collector import parse_log_range


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='收集和分析自适应故障注入实验日志',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 基本使用
  %(prog)s /home/user/experiments/bicg/div

  # 指定输出路径和范围
  %(prog)s /path/to/exp_folder \\
    --output ./results/analysis.csv \\
    --app-name bicg \\
    --log-range 0-500 \\
    --verbose

  # 显示统计信息
  %(prog)s /path/to/exp_folder --statistics
        """
    )

    # 位置参数
    parser.add_argument(
        'one_batch_folder',
        help='实验数据文件夹路径（包含log子文件夹）'
    )

    # 可选参数
    parser.add_argument(
        '--log-folder',
        help='日志文件夹路径（默认：{one_batch_folder}/log）'
    )

    parser.add_argument(
        '--output', '-o',
        help='输出CSV路径（默认：自动生成）'
    )

    parser.add_argument(
        '--app-name', '-n',
        help='应用程序名称（用于输出文件名）'
    )

    parser.add_argument(
        '--log-range',
        help='日志范围，格式: start-end 或 start:end（如：0-100）'
    )

    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='详细输出'
    )

    parser.add_argument(
        '--statistics', '-s',
        action='store_true',
        help='显示统计摘要'
    )

    parser.add_argument(
        '--format', '-f',
        choices=['csv', 'json'],
        default='csv',
        help='输出格式（默认：csv）'
    )

    parser.add_argument(
        '--no-validate',
        action='store_true',
        help='跳过日志验证（加快速度）'
    )

    parser.add_argument(
        '--save-warnings',
        action='store_true',
        help='保存警告日志到 warnings.log'
    )

    args = parser.parse_args()

    # 确定日志文件夹
    if args.log_folder:
        log_folder = args.log_folder
    else:
        log_folder = os.path.join(args.one_batch_folder, 'log')

    # 检查日志文件夹是否存在
    if not os.path.exists(log_folder):
        print(f"❌ 错误: 日志文件夹不存在: {log_folder}")
        sys.exit(1)

    # 确定应用程序名称
    if args.app_name:
        app_name = args.app_name
    else:
        # 从路径中提取应用名称
        app_name = os.path.basename(os.path.normpath(args.one_batch_folder))

    # 解析日志范围
    log_range = None
    if args.log_range:
        try:
            log_range = parse_log_range(args.log_range)
            if args.verbose:
                print(f"日志范围: {log_range[0]} - {log_range[1]}")
        except ValueError as e:
            print(f"❌ 错误: {e}")
            sys.exit(1)

    # 创建收集器
    if args.verbose:
        print(f"\n应用程序: {app_name}")
        print(f"日志文件夹: {log_folder}")

    collector = LogCollector(log_folder, app_name)

    try:
        # 收集日志
        df = collector.collect_all(
            log_range=log_range,
            verbose=args.verbose,
            validate=not args.no_validate
        )

        if df.empty:
            print("\n⚠️  警告: 未找到有效的日志数据")
            sys.exit(1)

        # 生成输出
        if args.format == 'csv':
            output_path = collector.generate_csv(
                output_path=args.output,
                show_statistics=False  # 后面单独显示
            )
            print(f"\n✓ CSV文件已生成: {output_path}")

        elif args.format == 'json':
            output_path = args.output or f"{app_name}_logs.json"
            df.to_json(output_path, orient='records', indent=2, force_ascii=False)
            print(f"\n✓ JSON文件已生成: {output_path}")

        # 显示统计信息
        if args.statistics or args.verbose:
            collector.csv_gen.print_statistics()

        # 显示收集摘要
        if args.verbose:
            collector.print_summary()

        # 保存警告日志
        if args.save_warnings and collector.warnings:
            warning_path = "warnings.log"
            collector.save_warning_log(warning_path)
            print(f"\n⚠️  警告日志已保存: {warning_path}")

        # 数据验证
        if args.verbose:
            issues = collector.csv_gen.validate_data()
            if issues:
                print("\n⚠️  数据验证发现以下问题:")
                for issue in issues:
                    print(f"   - {issue}")
            else:
                print("\n✓ 数据验证通过")

    except KeyboardInterrupt:
        print("\n\n⚠️  操作已取消")
        sys.exit(130)

    except Exception as e:
        print(f"\n❌ 错误: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
