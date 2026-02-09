#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试脚本：验证 app_profiler 工具是否正确配置
"""

import os
import sys

# 添加配置路径
profile_home = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, profile_home)

from config import (
    PIN_BINARY, APP_PROFILER_TOOL,
    get_app_config, get_output_json_path,
    APP_SUITES, ALL_APPS, MPI_APP
)

def test_paths():
    """测试路径配置"""
    print("="*70)
    print("路径配置测试")
    print("="*70)

    print(f"\nPin 二进制文件: {PIN_BINARY}")
    print(f"存在: {os.path.exists(PIN_BINARY)}")

    print(f"\napp_profiler 工具: {APP_PROFILER_TOOL}")
    print(f"存在: {os.path.exists(APP_PROFILER_TOOL)}")

    if not os.path.exists(APP_PROFILER_TOOL):
        print("\n错误: app_profiler.so 不存在，请先编译工具！")
        print("编译命令: cd /home/tongshiyu/pin/source/tools/pinfi && make obj-intel64/app_profiler.so")
        return False

    return True

def test_app_config():
    """测试应用配置"""
    print("\n" + "="*70)
    print("应用配置测试")
    print("="*70)

    print(f"\n可用套件: {list(APP_SUITES.keys())}")
    print(f"总应用数: {len(ALL_APPS)}")
    print(f"MPI 应用: {MPI_APP}")

    # 测试一个应用的配置
    test_app = "backprop"
    print(f"\n测试应用: {test_app}")
    try:
        config = get_app_config(test_app)
        print(f"  二进制路径: {config['binpath']}")
        print(f"  参数: {config.get('args', [])}")
        print(f"  存在: {os.path.exists(config['binpath'])}")

        output_json = get_output_json_path(test_app)
        print(f"  输出路径: {output_json}")
        print(f"  输出目录存在: {os.path.exists(os.path.dirname(output_json))}")
    except Exception as e:
        print(f"  错误: {e}")
        return False

    return True

def test_suite_apps():
    """测试每个套件的应用数量"""
    print("\n" + "="*70)
    print("套件统计")
    print("="*70)

    for suite, apps in APP_SUITES.items():
        print(f"\n{suite.upper()}: {len(apps)} 个应用")

        # 检查前3个应用的二进制文件
        for app in apps[:3]:
            try:
                config = get_app_config(app)
                exists = os.path.exists(config['binpath'])
                status = "✓" if exists else "✗"
                print(f"  {status} {app}")
            except Exception as e:
                print(f"  ✗ {app}: {e}")

def main():
    print("\napp_profiler 工具配置验证\n")

    # 测试路径
    if not test_paths():
        sys.exit(1)

    # 测试应用配置
    if not test_app_config():
        sys.exit(1)

    # 测试套件
    test_suite_apps()

    print("\n" + "="*70)
    print("配置验证完成！")
    print("="*70)
    print("\n可以开始使用以下命令进行剖析：")
    print("  python profile_single.py backprop")
    print("  python profile_batch.py --suite rodinia --parallel 4")
    print()

if __name__ == '__main__':
    main()
