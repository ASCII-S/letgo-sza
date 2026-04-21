#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
手动指令注错配置示例（更新版）

支持 5 参数格式：[regmem, reg, pc_hex, max_iteration, repeat_count]
"""

# ============================================================
# 示例 1: 从 catalog 获取完整信息
# ============================================================
# 假设 mov_catalog.csv 内容：
# rbp,,4026b1,MOV,mov eax, dword ptr [rbp-0x1c],12474
# rbp,,402605,MOV,mov eax, dword ptr [rbp-0x24],12096
# rdx,,402678,MOVSD_XMM,movsd xmm0, qword ptr [rdx+rax*8],12096

example_1_with_max_iteration = [
    ["rbp", "", "0x4026b1", 12474, 100],  # 使用 catalog 中的 max_iteration=12474
    ["rbp", "", "0x402605", 12096, 100],  # 使用 catalog 中的 max_iteration=12096
    ["rdx", "", "0x402678", 12096, 100],  # 使用 catalog 中的 max_iteration=12096
]

# ============================================================
# 示例 2: 简化配置（使用默认值）
# ============================================================
example_2_simple = [
    ["rbp", "", "0x4026b1", 100],  # 省略 max_iteration，使用默认 1023
    ["rbp", "", "0x402605", 100],  # repeat_count=100
    ["rdx", "", "0x402678", 100],
]

# ============================================================
# 示例 3: 混合配置
# ============================================================
example_3_mixed = [
    ["rbp", "", "0x4026b1", 12474, 200],  # 完整配置：注错 200 次
    ["rax", "", "0x402605", 50],          # 只指定 max_iteration，注错 1 次
    ["rdx", "", "0x402678"],              # 全部使用默认值
]

# ============================================================
# 示例 4: 测试 max_iteration 限制
# ============================================================
# 当 repeat_count > max_iteration 时，iteration 会被限制
example_4_limit = [
    ["rbp", "", "0x4026b1", 10, 100],  # max_iteration=10, repeat_count=100
    # 生成 100 条记录，但 iteration 只到 10，后续都是 10
]

# ============================================================
# 示例 5: 针对 fdtd-2d 的实际配置
# ============================================================
example_fdtd_2d = [
    ["rbp", "", "0x1180", 5000, 100],
    ["rbp", "", "0x11a0", 8000, 100],
    ["rax", "", "0x1200", 3000, 100],
]

# ============================================================
# 如何从 catalog 获取 max_iteration
# ============================================================
print("=" * 60)
print("如何从 catalog 获取 max_iteration")
print("=" * 60)
print("\n1. 查看 catalog 文件：")
print("   $ head -5 TargetedBenchmarkResult/fdtd-2d/mov/mov_catalog.csv")
print("\n2. Catalog 格式：")
print("   regmem, reg, pc_hex, mnemonic, asm, max_iteration")
print("   ^^^^^^  ^^^  ^^^^^^                  ^^^^^^^^^^^^^")
print("   第1列  第2列 第3列                   第6列（最后一列）")
print("\n3. 示例行：")
print("   rbp,,4026b1,MOV,mov eax, dword ptr [rbp-0x1c],12474")
print("                                                   ^^^^^")
print("                                                   这就是 max_iteration")
print("\n4. 配置到 manual_instructions：")
print("   ['rbp', '', '0x4026b1', 12474, 100]")
print("    ^^^^   ^^   ^^^^^^^^^  ^^^^^  ^^^")
print("    第1列  第2列 第3列      第6列  注错次数")

print("\n" + "=" * 60)
print("配置示例对比")
print("=" * 60)

examples = [
    ("完整配置", example_1_with_max_iteration),
    ("简化配置", example_2_simple),
    ("混合配置", example_3_mixed),
    ("限制测试", example_4_limit),
    ("fdtd-2d", example_fdtd_2d),
]

for name, config in examples:
    total = sum(x[4] if len(x) > 4 else (x[3] if len(x) > 3 and isinstance(x[3], int) and x[3] > 1023 else 1) for x in config)
    print(f"\n{name}:")
    print(f"  配置数: {len(config)} 条")
    print(f"  总注错次数: {total}")
    print(f"  示例: {config[0]}")
