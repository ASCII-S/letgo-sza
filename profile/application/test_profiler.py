#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""验证 app_profiler 工具配置"""

import os
import sys

profile_home = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, profile_home)

from config import PIN_BINARY, APP_PROFILER_TOOL, APP_SUITES, MPI_APP, get_app_config

def main():
    print("app_profiler 配置验证\n" + "="*50)

    # 检查路径
    print(f"\nPin: {PIN_BINARY}")
    print(f"  存在: {os.path.exists(PIN_BINARY)}")

    print(f"\napp_profiler: {APP_PROFILER_TOOL}")
    print(f"  存在: {os.path.exists(APP_PROFILER_TOOL)}")

    if not os.path.exists(APP_PROFILER_TOOL):
        print("\n错误: app_profiler.so 不存在！")
        print("编译: cd /home/tongshiyu/pin/source/tools/pinfi && make obj-intel64/app_profiler/app_profiler.so")
        return 1

    # 检查应用配置
    print(f"\n应用套件:")
    for suite, apps in APP_SUITES.items():
        print(f"  {suite}: {len(apps)} 个应用")

    print(f"\nMPI应用: {MPI_APP}")

    # 测试一个应用
    test_app = "backprop"
    try:
        config = get_app_config(test_app)
        print(f"\n测试应用 '{test_app}':")
        print(f"  路径: {config['binpath']}")
        print(f"  存在: {os.path.exists(config['binpath'])}")
    except Exception as e:
        print(f"\n错误: {e}")
        return 1

    print("\n" + "="*50)
    print("验证通过！可以开始使用：")
    print("  python3 profile_single.py backprop")
    print("  python3 profile_batch.py --suite rodinia --parallel 4")
    return 0

if __name__ == '__main__':
    sys.exit(main())
