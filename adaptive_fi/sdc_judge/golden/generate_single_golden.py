#!/usr/bin/env python3
"""
单应用Golden输出生成脚本

用法:
    python -m sdc_judge.golden.generate_single_golden <app_name> [选项]

示例:
    python -m sdc_judge.golden.generate_single_golden backprop
    python -m sdc_judge.golden.generate_single_golden hotspot --force
    python -m sdc_judge.golden.generate_single_golden bfs --list-apps
"""

import argparse
import sys
import os

from .golden_generator import GoldenGenerator

# 获取 adaptive_fi 目录路径
parent_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    parser = argparse.ArgumentParser(
        description='生成单个应用的Golden输出',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
  %(prog)s backprop                    # 生成backprop的Golden
  %(prog)s hotspot --force             # 强制重新生成hotspot
  %(prog)s --list-apps                 # 列出所有可用应用
  %(prog)s bfs --info                  # 查看应用信息
'''
    )

    parser.add_argument(
        'app_name',
        nargs='?',
        help='应用名称'
    )

    parser.add_argument(
        '--force', '-f',
        action='store_true',
        help='强制重新生成（即使已存在）'
    )

    parser.add_argument(
        '--config', '-c',
        default=os.path.join(parent_dir, 'applications.json'),
        help='配置文件路径（默认: applications.json）'
    )

    parser.add_argument(
        '--timeout', '-t',
        type=int,
        default=300,
        help='执行超时时间（秒，默认: 300）'
    )

    parser.add_argument(
        '--list-apps', '-l',
        action='store_true',
        help='列出所有可用应用'
    )

    parser.add_argument(
        '--list-suites', '-s',
        action='store_true',
        help='列出所有可用套件'
    )

    parser.add_argument(
        '--info', '-i',
        action='store_true',
        help='显示应用详细信息'
    )

    args = parser.parse_args()

    # 初始化Golden生成器
    try:
        generator = GoldenGenerator(
            config_path=args.config,
            timeout=args.timeout
        )
    except FileNotFoundError as e:
        print(f"错误: {e}")
        sys.exit(1)

    # 列出可用应用
    if args.list_apps:
        apps = generator.list_available_apps()
        print(f"可用应用 ({len(apps)} 个):")
        for app in sorted(apps):
            print(f"  {app}")
        sys.exit(0)

    # 列出可用套件
    if args.list_suites:
        suites = generator.list_available_suites()
        print(f"可用套件 ({len(suites)} 个):")
        for suite in suites:
            print(f"  {suite}")
        sys.exit(0)

    # 检查是否提供了应用名称
    if not args.app_name:
        print("错误: 请提供应用名称或使用 --list-apps 查看可用应用")
        parser.print_help()
        sys.exit(1)

    # 显示应用信息
    if args.info:
        info = generator.get_app_info(args.app_name)
        if info is None:
            print(f"错误: 应用不存在: {args.app_name}")
            sys.exit(1)
        print(f"应用信息: {args.app_name}")
        print("-" * 40)
        for key, value in info.items():
            print(f"  {key}: {value}")
        sys.exit(0)

    # 生成Golden输出
    try:
        golden = generator.generate_single(args.app_name, args.force)
        print(f"\n成功! Golden输出保存在: {golden.golden_dir}")
        print(f"输出文件: {list(golden.outputs.keys())}")
        sys.exit(0)
    except ValueError as e:
        print(f"错误: {e}")
        print("\n使用 --list-apps 查看可用应用")
        sys.exit(1)
    except Exception as e:
        print(f"错误: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
