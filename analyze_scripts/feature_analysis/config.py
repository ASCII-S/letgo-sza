#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Configuration file for Feature Analysis

This file contains configurable parameters for feature analysis.
Modify these values to customize the analysis behavior.

Author: Enhanced LetGo Framework
Date: 2025
"""

# ============================================================
# Data Source Configuration
# ============================================================

# Default CSV directory (relative to this script)
DEFAULT_CSV_DIR = "../CSV"

# Default output directory
DEFAULT_OUTPUT_DIR = "./results"

# ============================================================
# Analysis Parameters
# ============================================================

# Number of top opcodes to analyze in instruction type analysis
TOP_OPCODES = 15

# Execution progress phase bins
# Format: [lower_bound, upper_bound, label]
EXEC_PROGRESS_PHASES = [
    (0.0, 0.1, '初始化'),
    (0.1, 0.5, '计算前期'),
    (0.5, 0.9, '计算后期'),
    (0.9, 1.0, '收尾')
]

# RBP-RSP Delta bins (in bytes)
RBP_RSP_DELTA_BINS = [0, 64, 128, 256, 512, 1024, float('inf')]
RBP_RSP_DELTA_LABELS = ['0-64', '64-128', '128-256', '256-512', '512-1024', '>1024']

# ============================================================
# Visualization Configuration
# ============================================================

# Figure DPI for saved images
FIGURE_DPI = 300

# Default figure size
FIGURE_SIZE = (10, 6)

# Color schemes
COLOR_SCHEMES = {
    'recoverability': ['#2ecc71', '#e74c3c', '#95a5a6'],  # Green, Red, Gray
    'heuristic': ['#3498db', '#e67e22', '#9b59b6'],       # Blue, Orange, Purple
    'phase': '#e67e22',  # Orange
    'default': 'steelblue'
}

# Font configuration
FONT_CONFIG = {
    'family': 'sans-serif',
    'sans-serif': ['SimHei', 'DejaVu Sans'],
    'size': 10
}

# ============================================================
# Feature Definitions
# ============================================================

# Feature categories and their display names
FEATURE_CATEGORIES = {
    'CallDepth': '调用深度',
    'CallChain': '调用链',
    'DistFromMain': '距离Main',
    'IsRecursive': '递归调用',
    'CallerFunc': '调用者函数',
    'RBP_RSP_Delta': '栈指针偏移',
    'InstrFlag': '指令类型',
    'HasBase': '基址寄存器',
    'HasIndex': '索引寄存器',
    'HasDisplacement': '位移量',
    'ExecProgress': '执行进度'
}

# InstrFlag value mappings
INSTR_FLAG_MAPPING = {
    1: 'StackWrite',
    2: 'StackRead',
    3: 'NonStack'
}

# Result categories
RESULT_CATEGORIES = {
    'Masked': '完全屏蔽',
    'SDC': '静默数据损坏',
    'C-Masked': '崩溃后恢复成功',
    'C-SDC': '崩溃后恢复但SDC',
    'Recrash': '再次崩溃',
    'crash': '崩溃'
}

# ============================================================
# Export Configuration
# ============================================================

# CSV export settings
CSV_EXPORT_SETTINGS = {
    'index': False,
    'encoding': 'utf-8',
    'float_format': '%.2f'
}

# Image export settings
IMAGE_EXPORT_SETTINGS = {
    'dpi': FIGURE_DPI,
    'bbox_inches': 'tight',
    'format': 'png'
}

# ============================================================
# Batch Analysis Configuration
# ============================================================

# Programs to analyze in batch mode (None = all)
BATCH_PROGRAMS = None  # Set to ['backprop', 'bfs', 'nn'] to analyze specific programs

# Generate comparison reports
GENERATE_COMPARISON = True

# Comparison report types
COMPARISON_REPORTS = [
    'callDepth',
    'featureImportance',
    'execPhase'
]
