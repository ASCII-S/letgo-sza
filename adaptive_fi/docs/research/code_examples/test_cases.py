#!/usr/bin/env python3
"""
轻量级值域修复 - 测试用例示例

本文件展示了如何使用值域异常检测和单比特翻转检测函数。
可以直接运行以验证算法的正确性。
"""


def is_value_domain_anomaly(original: int, injected: int) -> bool:
    """
    检测寄存器值是否出现明显的值域异常

    Args:
        original: 原始值
        injected: 注错后的值

    Returns:
        True if 检测到值域异常, False otherwise
    """
    SMALL_VALUE_THRESHOLD = 4096
    AMPLIFICATION_FACTOR = 16
    HIGH_BIT_THRESHOLD = 8

    # 策略1：小值突变检测
    if original < SMALL_VALUE_THRESHOLD:
        if injected > original * AMPLIFICATION_FACTOR:
            return True

    # 策略2：高位异常比特检测
    diff = original ^ injected
    if diff > 0:
        msb_position = diff.bit_length() - 1
        original_msb = original.bit_length() - 1 if original > 0 else 0

        if msb_position - original_msb >= HIGH_BIT_THRESHOLD:
            return True

    return False


def is_single_bit_flip(original: int, injected: int) -> tuple:
    """
    检测是否为单比特翻转

    Args:
        original: 原始值
        injected: 注错后的值

    Returns:
        (是否单比特翻转, 翻转的比特位置)
    """
    diff = original ^ injected

    # 检查 diff 是否为 2 的幂次
    if diff > 0 and (diff & (diff - 1)) == 0:
        bit_position = diff.bit_length() - 1
        return True, bit_position

    return False, -1


def analyze_fault_case(original: int, injected: int, description: str = ""):
    """
    分析单个故障案例

    Args:
        original: 原始值
        injected: 注错后的值
        description: 案例描述
    """
    print("\n" + "="*70)
    if description:
        print(f"案例: {description}")
    print("="*70)

    print(f"原值:     0x{original:016x}  ({original})")
    print(f"注错值:   0x{injected:016x}  ({injected})")
    print(f"XOR差异:  0x{(original ^ injected):016x}")

    if original > 0:
        ratio = injected / original
        print(f"变化倍数: {ratio:.2f}x")

    # 单比特翻转检测
    is_single, bit_pos = is_single_bit_flip(original, injected)
    if is_single:
        print(f"故障类型: ✓ 单比特翻转（位 {bit_pos}）")
    else:
        diff = original ^ injected
        bit_count = bin(diff).count('1')
        print(f"故障类型: ✗ 多比特翻转（{bit_count} 个比特）")

    # 值域异常检测
    is_anomaly = is_value_domain_anomaly(original, injected)
    print(f"值域异常: {'✓ 是' if is_anomaly else '✗ 否'}")

    # 修复建议
    if is_single and is_anomaly:
        print(f"\n修复建议: ✓ 可使用轻量级修复")
        print(f"         直接恢复寄存器值: 0x{injected:x} → 0x{original:x}")
    else:
        print(f"\n修复建议: ✗ 使用LetGo完整修复")

    print("="*70)


def run_test_cases():
    """运行测试案例"""
    print("\n" + "#"*70)
    print("# 轻量级值域修复 - 测试案例")
    print("#"*70)

    # 测试案例1: 实际观察到的案例（hpl/log_1）
    analyze_fault_case(
        original=0x1,
        injected=0x400001,
        description="实际案例 - hpl程序日志"
    )

    # 测试案例2: 循环计数器翻转
    analyze_fault_case(
        original=100,
        injected=0x100064,
        description="循环计数器高位翻转"
    )

    # 测试案例3: 布尔值翻转
    analyze_fault_case(
        original=0,
        injected=0x80,
        description="布尔值单比特翻转（位7）"
    )

    # 测试案例4: 多比特翻转（不适用轻量级修复）
    analyze_fault_case(
        original=0x1,
        injected=0x3,
        description="多比特翻转（位0和位1）"
    )

    # 测试案例5: 正常值变化（不是异常）
    analyze_fault_case(
        original=100,
        injected=105,
        description="正常值变化（非异常）"
    )

    # 测试案例6: 大值翻转（不太可能是值域异常）
    analyze_fault_case(
        original=0x7fffffff,
        injected=0xffffffff,
        description="大值翻转（MSB位）"
    )

    # 测试案例7: 指针低位翻转
    analyze_fault_case(
        original=0x7fffffffe000,
        injected=0x7fffffffe080,
        description="指针低位翻转（位7）"
    )

    # 测试案例8: 数组索引翻转
    analyze_fault_case(
        original=64,
        injected=0x800040,
        description="数组索引高位翻转（位23）"
    )


def run_statistical_analysis():
    """统计分析"""
    print("\n\n" + "#"*70)
    print("# 统计分析")
    print("#"*70)

    test_cases = [
        (0x1, 0x400001),        # 单比特，值域异常
        (100, 0x100064),        # 单比特，值域异常
        (0, 0x80),              # 单比特，值域异常
        (0x1, 0x3),             # 多比特
        (100, 105),             # 正常变化
        (0x7fffffff, 0xffffffff),  # 大值翻转
        (64, 0x800040),         # 单比特，值域异常
        (1000, 1024),           # 正常变化
        (0, 0x1),               # 单比特，值域异常
        (255, 0x10000ff),       # 单比特，值域异常
    ]

    total = len(test_cases)
    value_anomaly_count = 0
    single_bit_count = 0
    lightweight_applicable = 0

    for original, injected in test_cases:
        is_anomaly = is_value_domain_anomaly(original, injected)
        is_single, _ = is_single_bit_flip(original, injected)

        if is_anomaly:
            value_anomaly_count += 1
        if is_single:
            single_bit_count += 1
        if is_anomaly and is_single:
            lightweight_applicable += 1

    print(f"\n测试案例总数:       {total}")
    print(f"值域异常数量:       {value_anomaly_count} ({value_anomaly_count/total*100:.1f}%)")
    print(f"单比特翻转数量:     {single_bit_count} ({single_bit_count/total*100:.1f}%)")
    print(f"轻量级修复适用:     {lightweight_applicable} ({lightweight_applicable/total*100:.1f}%)")

    print(f"\n在值域异常中，单比特翻转占比: {single_bit_count/max(1, value_anomaly_count)*100:.1f}%")


def main():
    """主函数"""
    # 运行测试案例
    run_test_cases()

    # 统计分析
    run_statistical_analysis()

    print("\n" + "#"*70)
    print("# 测试完成")
    print("#"*70)
    print("\n提示：")
    print("  - ✓ 表示检测通过或适用轻量级修复")
    print("  - ✗ 表示检测失败或需要LetGo修复")
    print()


if __name__ == "__main__":
    main()
