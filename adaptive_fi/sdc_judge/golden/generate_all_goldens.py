#!/usr/bin/env python3
"""
批量生成所有应用的Golden输出

用法:
    python -m sdc_judge.golden.generate_all_goldens [选项]

示例:
    python -m sdc_judge.golden.generate_all_goldens                       # 生成所有应用
    python -m sdc_judge.golden.generate_all_goldens --suites rodinia      # 仅生成rodinia套件
    python -m sdc_judge.golden.generate_all_goldens --force               # 强制重新生成所有
    python -m sdc_judge.golden.generate_all_goldens --suites rodinia mantevo  # 多个套件
"""

import argparse
import sys
import os

from .golden_generator import GoldenGenerator

# 获取 adaptive_fi 目录路径
parent_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    parser = argparse.ArgumentParser(
        description='批量生成Golden输出',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
  %(prog)s                             # 生成所有应用
  %(prog)s --suites rodinia            # 仅rodinia套件
  %(prog)s --suites rodinia mantevo    # 多个套件
  %(prog)s --force                     # 强制重新生成
  %(prog)s --list-suites               # 列出所有套件
'''
    )

    parser.add_argument(
        '--suites',
        nargs='+',
        choices=['rodinia', 'mantevo', 'npb', 'polybench'],
        help='指定测试套件（默认：所有）'
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
        help='每个应用的执行超时时间（秒，默认: 300）'
    )

    parser.add_argument(
        '--list-suites', '-l',
        action='store_true',
        help='列出所有可用套件'
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

    # 列出可用套件
    if args.list_suites:
        suites = generator.list_available_suites()
        print(f"可用套件 ({len(suites)} 个):")
        for suite in suites:
            apps = generator.config_mgr.get_suite_apps(suite)
            print(f"  {suite}: {len(apps)} 个应用")
        sys.exit(0)

    # 批量生成Golden输出
    print("批量生成Golden输出")
    print("="*60)

    if args.suites:
        print(f"套件: {', '.join(args.suites)}")
    else:
        print("套件: 所有")

    print(f"强制重新生成: {'是' if args.force else '否'}")
    print(f"超时时间: {args.timeout}秒")
    print("="*60)

    try:
        results = generator.generate_all(args.suites, args.force)

        # 统计
        success = sum(1 for v in results.values() if v is not None)
        total = len(results)

        print(f"\n{'='*60}")
        print(f"批量生成完成: {success}/{total} 成功")

        if success < total:
            print(f"\n失败的应用:")
            for name, result in results.items():
                if result is None:
                    print(f"  - {name}")
            sys.exit(1)
        else:
            print(f"\n✓ 所有应用Golden输出生成成功!")
            sys.exit(0)

    except Exception as e:
        print(f"\n错误: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
