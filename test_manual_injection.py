#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
手动指令注错功能测试脚本

用于验证 generate_manual_pool() 函数的正确性
"""

import sys
import os

# 添加项目路径
sys.path.insert(0, '/home/tongshiyu/pin/source/tools/letgo')

import configure
import InstPoolMaker

def test_manual_pool_generation():
    """测试手动 pool 生成功能"""

    print("=" * 60)
    print("测试手动指令注错 Pool 生成功能")
    print("=" * 60)

    # 临时修改配置
    original_manual_instructions = configure.manual_instructions
    original_one_batch_folder = configure.one_batch_folder

    # 设置测试配置
    configure.manual_instructions = [
        ["rbp", "", "0x4026b1", 12474, 3],    # 注错 3 次，max_iteration=12474
        ["rax", "", "402605", 12096, 2],      # 注错 2 次（不带 0x 前缀）
        ["rdx", "", "0x402678"],              # 注错 1 次（使用默认值）
    ]

    # 使用临时目录
    test_output_dir = "/tmp/letgo_test"
    os.makedirs(test_output_dir, exist_ok=True)
    configure.one_batch_folder = test_output_dir
    configure.manual_pool_name = "test_manual_pool.csv"

    # 生成 pool
    print("\n生成测试 pool...")
    pool_path = InstPoolMaker.generate_manual_pool()

    if pool_path and os.path.exists(pool_path):
        print(f"\n✓ Pool 文件生成成功: {pool_path}")

        # 读取并显示内容
        print("\n生成的 Pool 内容:")
        print("-" * 60)
        with open(pool_path, 'r') as f:
            content = f.read()
            print(content)
        print("-" * 60)

        # 验证行数
        with open(pool_path, 'r') as f:
            lines = f.readlines()
            expected_lines = 3 + 2 + 1  # 总共 6 行
            actual_lines = len(lines)

            if actual_lines == expected_lines:
                print(f"\n✓ 行数验证通过: {actual_lines} 行（预期 {expected_lines} 行）")
            else:
                print(f"\n✗ 行数验证失败: {actual_lines} 行（预期 {expected_lines} 行）")

        # 验证格式
        print("\n验证每行格式:")
        for i, line in enumerate(lines, 1):
            parts = line.strip().split(',')
            if len(parts) == 4:
                print(f"  行 {i}: ✓ {parts}")
            else:
                print(f"  行 {i}: ✗ 格式错误 {parts}")

        print("\n" + "=" * 60)
        print("测试完成！")
        print("=" * 60)

    else:
        print("\n✗ Pool 文件生成失败！")

    # 恢复原始配置
    configure.manual_instructions = original_manual_instructions
    configure.one_batch_folder = original_one_batch_folder

if __name__ == "__main__":
    test_manual_pool_generation()
