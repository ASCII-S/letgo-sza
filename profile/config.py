#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
剖析配置文件
集中管理所有剖析相关的配置参数
"""

import os
import sys

# 添加 letgo 根目录到路径
LETGO_HOME = "/home/tongshiyu/pin/source/tools/letgo"
sys.path.insert(0, LETGO_HOME)

# 导入 configure.py 中的配置
from configure import (
    pin_home, toolbase,
    rodinia_app_list, mantevo_app_list, NPB_SER_app_list, PolyBenchtList,
    Rodinia_base, PolyBench_base
)

# ============================================================
# Pin 和工具路径配置
# ============================================================
PIN_BINARY = os.path.join(pin_home, "pin")
# 应用级剖析工具（新版本）
APP_PROFILER_TOOL = os.path.join(toolbase, "obj-intel64/app_profiler/app_profiler.so")
# 旧版本工具（如果存在）
PROFILER_TOOL = os.path.join(toolbase, "obj-intel64/application_profiler/application_profiler.so")
FUNCTION_PROFILER_TOOL = os.path.join(toolbase, "obj-intel64/function_profiler/function_profiler.so")
BBL_PROFILER_TOOL = os.path.join(toolbase, "obj-intel64/bbl_profiler/bbl_profiler.so")

# ============================================================
# 应用程序列表配置
# ============================================================
APP_SUITES = {
    'rodinia': rodinia_app_list,
    'mantevo': mantevo_app_list,
    'npb': NPB_SER_app_list,
    'polybench': PolyBenchtList
}

# 所有应用列表（用于批量处理）
ALL_APPS = []
for suite_apps in APP_SUITES.values():
    ALL_APPS.extend(suite_apps)

# 默认要剖析的应用（可通过命令行覆盖）
DEFAULT_PROFILE_APPS = ALL_APPS  # 默认剖析所有应用

# MPI 应用列表
MPI_APP = ["HPCCG", "miniAMR", "miniFE", "miniMD"]

# ============================================================
# 输出路径配置
# ============================================================
PROFILE_HOME = os.path.join(LETGO_HOME, "profile")
APPLICATION_PROFILE_DIR = os.path.join(PROFILE_HOME, "application")
RESULTS_DIR = os.path.join(APPLICATION_PROFILE_DIR, "results")

# 子目录
RAW_JSON_DIR = os.path.join(RESULTS_DIR, "raw_json")
SUMMARY_DIR = os.path.join(RESULTS_DIR, "summary")
VISUALIZATION_DIR = os.path.join(RESULTS_DIR, "visualization")
LOGS_DIR = os.path.join(RESULTS_DIR, "logs")

# 确保目录存在
for directory in [RAW_JSON_DIR, SUMMARY_DIR, VISUALIZATION_DIR, LOGS_DIR]:
    os.makedirs(directory, exist_ok=True)

# 按套件创建子目录
for suite in APP_SUITES.keys():
    suite_dir = os.path.join(RAW_JSON_DIR, suite)
    os.makedirs(suite_dir, exist_ok=True)

# Function维度输出目录配置
FUNCTION_PROFILE_DIR = os.path.join(PROFILE_HOME, "function")
FUNCTION_RESULTS_DIR = os.path.join(FUNCTION_PROFILE_DIR, "results")

# Function子目录
FUNCTION_RAW_JSON_DIR = os.path.join(FUNCTION_RESULTS_DIR, "raw_json")
FUNCTION_SUMMARY_DIR = os.path.join(FUNCTION_RESULTS_DIR, "summary")
FUNCTION_VISUALIZATION_DIR = os.path.join(FUNCTION_RESULTS_DIR, "visualization")
FUNCTION_LOGS_DIR = os.path.join(FUNCTION_RESULTS_DIR, "logs")

# 确保函数剖析相关目录存在
for directory in [FUNCTION_RAW_JSON_DIR, FUNCTION_SUMMARY_DIR,
                   FUNCTION_VISUALIZATION_DIR, FUNCTION_LOGS_DIR]:
    os.makedirs(directory, exist_ok=True)

# 按套件创建函数剖析子目录
for suite in APP_SUITES.keys():
    suite_dir = os.path.join(FUNCTION_RAW_JSON_DIR, suite)
    os.makedirs(suite_dir, exist_ok=True)

# ============================================================
# 剖析参数配置
# ============================================================

# 超时设置（秒）
PROFILE_TIMEOUT = 3600  # 1小时超时

# 并行处理配置
MAX_PARALLEL_JOBS = 4  # 最多同时运行4个剖析任务

# 重试配置
MAX_RETRIES = 2  # 失败后最多重试2次

# 函数级剖析参数
FUNCTION_MIN_CALLS = 1  # function_profiler的最小调用次数过滤（默认不过滤）

# BBL维度输出目录配置
BBL_PROFILE_DIR = os.path.join(PROFILE_HOME, "bbl")
BBL_RESULTS_DIR = os.path.join(BBL_PROFILE_DIR, "results")

# BBL子目录
BBL_RAW_JSON_DIR = os.path.join(BBL_RESULTS_DIR, "raw_json")
BBL_SUMMARY_DIR = os.path.join(BBL_RESULTS_DIR, "summary")
BBL_VISUALIZATION_DIR = os.path.join(BBL_RESULTS_DIR, "visualization")
BBL_LOGS_DIR = os.path.join(BBL_RESULTS_DIR, "logs")

# 确保BBL剖析相关目录存在
for directory in [BBL_RAW_JSON_DIR, BBL_SUMMARY_DIR,
                   BBL_VISUALIZATION_DIR, BBL_LOGS_DIR]:
    os.makedirs(directory, exist_ok=True)

# 按套件创建BBL剖析子目录
for suite in APP_SUITES.keys():
    suite_dir = os.path.join(BBL_RAW_JSON_DIR, suite)
    os.makedirs(suite_dir, exist_ok=True)

# ============================================================
# 分析和可视化配置
# ============================================================

# 关键指标列表（用于汇总报告）
KEY_METRICS = [
    'compute_memory_ratio',
    'bytes_per_instruction',
    'simd_ratio',
    'value_lifetime_avg',
    'value_fanout_avg',
    'register_rewrite_rate',
    'compare_instruction_density',
    'branch_bias',
    'loop_avg_iterations',
    'memory_read_write_ratio'
]

# 弹性评分权重
RESILIENCE_WEIGHTS = {
    'value_lifetime': 0.20,
    'value_fanout': 0.20,
    'register_rewrite_rate': 0.15,
    'compare_density': 0.15,
    'branch_bias': 0.10,
    'mask_operations': 0.10,
    'function_call_frequency': 0.10
}

# 可视化配置
FIGURE_DPI = 300
FIGURE_SIZE = (12, 8)
COLOR_SCHEMES = {
    'suite': ['#3498db', '#e74c3c', '#2ecc71', '#f39c12'],
    'workload': ['#9b59b6', '#1abc9c', '#e67e22', '#34495e', '#95a5a6']
}

# ============================================================
# 辅助函数：获取应用所属套件
# ============================================================
def get_app_suite(app_name):
    """获取应用所属的套件"""
    for suite, apps in APP_SUITES.items():
        if app_name in apps:
            return suite
    return 'unknown'

def get_output_json_path(app_name):
    """获取应用的JSON输出路径"""
    suite = get_app_suite(app_name)
    suite_dir = os.path.join(RAW_JSON_DIR, suite)
    return os.path.join(suite_dir, f"{app_name}_profile.json")

def get_app_config(app_name):
    """从 configure.py 获取应用配置"""
    from configure import use
    return use(app_name)

def get_function_output_json_path(app_name):
    """获取应用的函数剖析JSON输出路径"""
    suite = get_app_suite(app_name)
    suite_dir = os.path.join(FUNCTION_RAW_JSON_DIR, suite)
    return os.path.join(suite_dir, f"{app_name}_function_profile.json")

def get_bbl_output_json_path(app_name):
    """获取应用的BBL剖析JSON输出路径"""
    suite = get_app_suite(app_name)
    suite_dir = os.path.join(BBL_RAW_JSON_DIR, suite)
    return os.path.join(suite_dir, f"{app_name}_bbl_profile.json")
