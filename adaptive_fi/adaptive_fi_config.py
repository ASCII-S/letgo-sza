#!/usr/bin/env python3
"""
adaptive_fi_config.py - 自适应故障注错配置模块

定义自适应注错的所有配置参数。
"""

import os
import sys

# 添加父目录到 Python 路径，以便导入 configure 模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import configure


# ============== 自适应注错核心参数 ==============

# 崩溃率阈值：超过此值的目标被认为是"高效注错点"
crash_threshold = 0.1

# 每个注错目标的测试次数
injections_per_target = 10

# 初始 depth=0 的 TopP 筛选数量
topp_initial = 100

# 每层溯源的 TopP 筛选数量
topp_trace = 100

# 最大溯源深度
max_depth = 10


# ============== 文件路径配置 ==============

# 溯源 JSON 文件路径（unified_tracer.so 输出）
trace_json_path = os.path.join(configure.one_batch_folder, "trace_result.json")

# 自适应注错结果 JSON 文件路径
output_json_path = os.path.join(configure.one_batch_folder, "adaptive_fi_result.json")

# unified_tracer.so 工具路径
tracer_lib_path = os.path.join(configure.toolbase, "obj-intel64/crashprone_tracer/unified_tracer.so")

# 临时 pool 文件路径（用于传递注错参数给 sighandler）
temp_pool_path = configure.pool_csv_file

# Pin 工具路径（targeted_faultinjection.so）
targeted_fi_lib_path = os.path.join(configure.toolbase, "obj-intel64/targeted_fi/targeted_faultinjection.so")


# ============== Pin+GDB 注错模式配置 ==============

# 注错模式开关：True=使用 Pin 注错，False=使用 GDB 注错（原方式）
use_pin_injection = True

# GDB 调试端口基址（避免多次实验端口冲突）
gdb_port_base = 12345


# ============== 日志相关配置 ==============

# 是否保留所有实验日志（兼容 analyze.py）
keep_all_logs = True

# 日志文件夹路径（继承自 configure.py）
log_folder = configure.log_folder

# SDC 输出文件夹路径
sdcout_folder = os.path.join(configure.one_batch_folder, "sdcout")


# ============== 实验控制参数 ==============

# 是否在 JSON 不存在时自动运行 unified_tracer.so
auto_run_tracer = True

# unified_tracer.so 超时时间（秒）
tracer_timeout = 1200

# 是否在发现高效注错点后立即溯源（True=DFS深度优先，False=BFS广度优先）
# 注意：我们使用的是混合策略，此参数保留用于调试
immediate_trace_on_high_crash = True


# ============== 过滤和筛选参数 ==============

# 只测试特定类型的易崩溃指令（空列表表示全部类型）
# 可选类型: "mem_write", "mem_read", "index_access", "indirect_cf", "div"
filter_cp_types = []

# 最小执行次数：执行次数低于此值的指令将被忽略
min_exec_count = 2

# 最大执行次数：用于限制 iteration 的上界
max_exec_count_for_iteration = 1000

# 程序基址：用于将 JSON 中的相对偏移转换为绝对地址
# 对于非 PIE 程序，通常是 0x400000
# 对于 PIE 程序，需要在运行时获取实际基址
program_base_address = 0x400000


# ============== 输出控制参数 ==============

# 是否在控制台打印详细进度
verbose = True

# 是否在每次注错后打印结果
print_each_injection = False

# 是否生成中间统计报告（每完成一个深度）
generate_intermediate_reports = True


# ============== 辅助函数 ==============

def validate_config():
    """验证配置参数的合法性"""
    errors = []

    if crash_threshold < 0 or crash_threshold > 1:
        errors.append("crash_threshold 必须在 [0, 1] 范围内")

    if injections_per_target < 1:
        errors.append("injections_per_target 必须 >= 1")

    if topp_initial < 1:
        errors.append("topp_initial 必须 >= 1")

    if topp_trace < 1:
        errors.append("topp_trace 必须 >= 1")

    if max_depth < 0:
        errors.append("max_depth 必须 >= 0")

    if not os.path.exists(configure.toolbase):
        errors.append(f"Pin 工具路径不存在: {configure.toolbase}")

    if errors:
        print("配置验证失败:")
        for err in errors:
            print(f"  - {err}")
        return False

    return True


def print_config():
    """打印当前配置"""
    print("=" * 60)
    print("自适应故障注错配置")
    print("=" * 60)
    print(f"崩溃率阈值:         {crash_threshold}")
    print(f"每目标注错次数:     {injections_per_target}")
    print(f"初始 TopP:          {topp_initial}")
    print(f"溯源 TopP:          {topp_trace}")
    print(f"最大深度:           {max_depth}")
    print(f"溯源 JSON 路径:     {trace_json_path}")
    print(f"输出 JSON 路径:     {output_json_path}")
    print(f"日志文件夹:         {log_folder}")
    print(f"程序名称:           {configure.progname}")
    print(f"程序路径:           {configure.benchmark}")
    print("=" * 60)


# ============== 配置预设 ==============

def set_quick_test_config():
    """快速测试配置（少量注错，快速验证）"""
    global crash_threshold, injections_per_target, topp_initial, topp_trace, max_depth
    crash_threshold = 0.3
    injections_per_target = 3
    topp_initial = 10
    topp_trace = 5
    max_depth = 2
    print("[Config] 已切换到快速测试模式")


def set_full_experiment_config():
    """完整实验配置（大规模注错）"""
    global crash_threshold, injections_per_target, topp_initial, topp_trace, max_depth
    crash_threshold = 0.3
    injections_per_target = 20
    topp_initial = 200
    topp_trace = 30
    max_depth = 5
    print("[Config] 已切换到完整实验模式")


def set_high_coverage_config():
    """高覆盖率配置（更多目标，更少重复）"""
    global crash_threshold, injections_per_target, topp_initial, topp_trace, max_depth
    crash_threshold = 0.2  # 降低阈值，增加溯源机会
    injections_per_target = 5
    topp_initial = 300
    topp_trace = 50
    max_depth = 3
    print("[Config] 已切换到高覆盖率模式")


# ============== 初始化 ==============

if __name__ == "__main__":
    print_config()
    if validate_config():
        print("\n✓ 配置验证通过")
    else:
        print("\n✗ 配置验证失败")
        sys.exit(1)
