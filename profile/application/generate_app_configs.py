#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
应用配置生成脚本

功能：
1. 从 configure.py 提取应用配置
2. 生成 applications.json 配置文件
3. 验证配置完整性
"""

import os
import sys
import json
from pathlib import Path

# 添加配置路径
profile_home = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, profile_home)
from config import (
    APP_SUITES, ALL_APPS, MPI_APP,
    get_app_config
)


def generate_app_configs():
    """从 configure.py 生成应用配置 JSON"""

    config_data = {
        "metadata": {
            "description": "应用程序剖析配置文件",
            "generated": "auto-generated",
            "total_applications": len(ALL_APPS)
        },
        "suites": {}
    }

    suite_descriptions = {
        'rodinia': 'Rodinia Benchmark Suite',
        'mantevo': 'Mantevo Benchmark Suite',
        'npb': 'NAS Parallel Benchmarks Serial',
        'polybench': 'PolyBench/C Benchmark Suite'
    }

    # 遍历每个套件
    for suite_name, app_list in APP_SUITES.items():
        config_data['suites'][suite_name] = {
            'description': suite_descriptions.get(suite_name, suite_name),
            'applications': {}
        }

        # 遍历每个应用
        for app_name in app_list:
            try:
                app_config = get_app_config(app_name)

                # 基本配置
                app_entry = {
                    'binpath': app_config['binpath'],
                    'args': app_config.get('args', [])
                }

                # PC 范围（可选）
                if 'pc_start' in app_config:
                    app_entry['pc_start'] = app_config['pc_start']
                if 'pc_end' in app_config:
                    app_entry['pc_end'] = app_config['pc_end']

                # MPI 标记
                if app_name in MPI_APP:
                    app_entry['is_mpi'] = True

                config_data['suites'][suite_name]['applications'][app_name] = app_entry

            except Exception as e:
                print(f"警告: 无法获取应用 {app_name} 的配置: {e}")
                continue

    return config_data


def save_config_to_json(config_data, output_file):
    """保存配置到 JSON 文件"""
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(config_data, f, indent=2, ensure_ascii=False)
    print(f"✓ 配置已保存到: {output_file}")


def verify_binaries(config_data):
    """验证二进制文件是否存在"""
    print("\n验证二进制文件...")
    missing = []

    for suite_name, suite_data in config_data['suites'].items():
        for app_name, app_config in suite_data['applications'].items():
            binpath = app_config['binpath']
            if not os.path.exists(binpath):
                missing.append((suite_name, app_name, binpath))

    if missing:
        print(f"\n⚠ 发现 {len(missing)} 个缺失的二进制文件:")
        for suite, app, path in missing:
            print(f"  [{suite}] {app}: {path}")
    else:
        print("✓ 所有二进制文件都存在")

    return len(missing) == 0


def print_summary(config_data):
    """打印配置摘要"""
    print(f"\n{'='*70}")
    print(f"应用配置生成摘要")
    print(f"{'='*70}")

    total = 0
    for suite_name, suite_data in config_data['suites'].items():
        count = len(suite_data['applications'])
        total += count
        print(f"  {suite_name:15s}: {count:2d} 个应用")

    print(f"  {'总计':15s}: {total:2d} 个应用")
    print(f"{'='*70}\n")


def main():
    """主函数"""
    print("正在生成应用配置...")

    # 生成配置
    config_data = generate_app_configs()

    # 输出文件路径（放在 profile 目录下，供各维度剖析共享）
    output_file = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        'applications.json'
    )

    # 保存配置
    save_config_to_json(config_data, output_file)

    # 打印摘要
    print_summary(config_data)

    # 验证二进制文件
    all_exist = verify_binaries(config_data)

    if all_exist:
        print("✓ 配置生成完成，所有二进制文件都存在")
        return 0
    else:
        print("⚠ 配置生成完成，但部分二进制文件缺失")
        return 1


if __name__ == '__main__':
    sys.exit(main())
