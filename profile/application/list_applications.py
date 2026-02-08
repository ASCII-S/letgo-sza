#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
应用配置查看工具

功能：
1. 列出所有应用及其配置
2. 按套件筛选
3. 显示详细信息（二进制路径、参数、PC范围等）
4. 支持多种输出格式（表格、详细、JSON）
"""

import os
import sys
import json
import argparse
from pathlib import Path

# 添加配置路径
profile_home = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, profile_home)
from config import APP_SUITES, get_app_config, MPI_APP


def load_json_config():
    """从 JSON 文件加载配置（从 profile 目录）"""
    json_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        'applications.json'
    )
    if os.path.exists(json_path):
        with open(json_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None


def list_apps_table(suite=None):
    """以表格形式列出应用"""
    print(f"\n{'='*100}")
    print(f"{'应用名称':<20} {'套件':<15} {'二进制路径':<50} {'MPI':<5}")
    print(f"{'='*100}")

    total = 0
    suites_to_list = {suite: APP_SUITES[suite]} if suite else APP_SUITES

    for suite_name, app_list in suites_to_list.items():
        for app_name in app_list:
            try:
                config = get_app_config(app_name)
                binpath = config['binpath']
                is_mpi = "是" if app_name in MPI_APP else "否"

                # 缩短路径显示
                if len(binpath) > 48:
                    binpath = "..." + binpath[-45:]

                print(f"{app_name:<20} {suite_name:<15} {binpath:<50} {is_mpi:<5}")
                total += 1
            except Exception as e:
                print(f"{app_name:<20} {suite_name:<15} [配置错误: {e}]")

    print(f"{'='*100}")
    print(f"总计: {total} 个应用\n")


def list_apps_detailed(suite=None, show_args=True):
    """详细列出应用配置"""
    suites_to_list = {suite: APP_SUITES[suite]} if suite else APP_SUITES

    total = 0
    for suite_name, app_list in suites_to_list.items():
        print(f"\n{'='*70}")
        print(f"套件: {suite_name.upper()}")
        print(f"{'='*70}\n")

        for app_name in app_list:
            try:
                config = get_app_config(app_name)
                total += 1

                print(f"  [{total}] {app_name}")
                print(f"      二进制: {config['binpath']}")

                if show_args and config.get('args'):
                    args_str = ' '.join(str(arg) for arg in config['args'])
                    if len(args_str) > 80:
                        args_str = args_str[:77] + "..."
                    print(f"      参数:   {args_str}")

                if 'pc_start' in config and 'pc_end' in config:
                    print(f"      PC范围: {config['pc_start']} - {config['pc_end']}")

                if app_name in MPI_APP:
                    print(f"      MPI:    是")

                print()

            except Exception as e:
                print(f"  [{total}] {app_name} - [错误: {e}]\n")

    print(f"{'='*70}")
    print(f"总计: {total} 个应用\n")


def list_by_suite():
    """按套件统计"""
    print(f"\n{'='*70}")
    print(f"应用统计（按套件）")
    print(f"{'='*70}")

    for suite_name, app_list in APP_SUITES.items():
        print(f"\n{suite_name.upper()} ({len(app_list)} 个应用):")
        for i, app_name in enumerate(app_list, 1):
            mpi_tag = " [MPI]" if app_name in MPI_APP else ""
            print(f"  {i:2d}. {app_name}{mpi_tag}")

    total = sum(len(apps) for apps in APP_SUITES.values())
    print(f"\n{'='*70}")
    print(f"总计: {total} 个应用")
    print(f"{'='*70}\n")


def export_to_json(output_file):
    """导出配置到 JSON"""
    config_data = {
        'suites': {}
    }

    for suite_name, app_list in APP_SUITES.items():
        config_data['suites'][suite_name] = {}

        for app_name in app_list:
            try:
                config = get_app_config(app_name)
                app_entry = {
                    'binpath': config['binpath'],
                    'args': config.get('args', [])
                }

                if 'pc_start' in config:
                    app_entry['pc_start'] = config['pc_start']
                if 'pc_end' in config:
                    app_entry['pc_end'] = config['pc_end']

                if app_name in MPI_APP:
                    app_entry['is_mpi'] = True

                config_data['suites'][suite_name][app_name] = app_entry
            except Exception as e:
                print(f"警告: 无法导出 {app_name}: {e}")

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(config_data, f, indent=2, ensure_ascii=False)

    print(f"✓ 配置已导出到: {output_file}")


def show_single_app(app_name):
    """显示单个应用的详细配置"""
    try:
        config = get_app_config(app_name)

        print(f"\n{'='*70}")
        print(f"应用: {app_name}")
        print(f"{'='*70}")
        print(f"二进制文件: {config['binpath']}")
        print(f"参数: {' '.join(str(arg) for arg in config.get('args', []))}")

        if 'pc_start' in config and 'pc_end' in config:
            print(f"PC范围: {config['pc_start']} - {config['pc_end']}")

        print(f"MPI应用: {'是' if app_name in MPI_APP else '否'}")

        # 检查二进制文件是否存在
        binpath = config['binpath']
        if os.path.exists(binpath):
            size = os.path.getsize(binpath) / (1024 * 1024)  # MB
            print(f"文件大小: {size:.2f} MB")
            print(f"文件状态: ✓ 存在")
        else:
            print(f"文件状态: ✗ 不存在")

        # 所属套件
        for suite_name, app_list in APP_SUITES.items():
            if app_name in app_list:
                print(f"所属套件: {suite_name}")
                break

        print(f"{'='*70}\n")

        # 显示完整命令示例
        print("剖析命令示例:")
        print(f"  python profile_single.py {app_name}")
        print()

    except Exception as e:
        print(f"错误: 无法获取应用 {app_name} 的配置: {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description='应用配置查看工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 列出所有应用（表格形式）
  python list_applications.py

  # 列出所有应用（详细信息）
  python list_applications.py --detailed

  # 列出指定套件的应用
  python list_applications.py --suite rodinia

  # 按套件统计
  python list_applications.py --by-suite

  # 查看单个应用详情
  python list_applications.py --app backprop

  # 导出到 JSON
  python list_applications.py --export apps.json
        """
    )

    parser.add_argument('--suite', type=str, choices=list(APP_SUITES.keys()),
                       help='只显示指定套件的应用')
    parser.add_argument('--detailed', '-d', action='store_true',
                       help='显示详细信息')
    parser.add_argument('--by-suite', action='store_true',
                       help='按套件统计')
    parser.add_argument('--app', type=str,
                       help='显示单个应用的详细配置')
    parser.add_argument('--export', type=str, metavar='FILE',
                       help='导出配置到 JSON 文件')
    parser.add_argument('--no-args', action='store_true',
                       help='不显示命令行参数（仅在详细模式下有效）')

    args = parser.parse_args()

    # 单个应用详情
    if args.app:
        show_single_app(args.app)

    # 导出到 JSON
    elif args.export:
        export_to_json(args.export)

    # 按套件统计
    elif args.by_suite:
        list_by_suite()

    # 详细列表
    elif args.detailed:
        list_apps_detailed(args.suite, show_args=not args.no_args)

    # 默认表格列表
    else:
        list_apps_table(args.suite)


if __name__ == '__main__':
    main()
