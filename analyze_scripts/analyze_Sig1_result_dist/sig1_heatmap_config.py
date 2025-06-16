#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
@file sig1_heatmap_config.py
@brief 热力图的配置选项
@author AI助手
@date 创建于2023年
"""

# 配置文件路径
CSV_FILE = "./analysis_results/merged_result_sig1_distribution.csv"

# 输出目录
OUTPUT_DIR = "./analysis_results/heatmaps"

# 信号列，如果为None则使用所有信号列
SIGNAL_COLUMNS = ["SIGBUS", "SIGSEGV", "SIGABRT"]

# 结果类型，如果为None则使用所有结果类型
RESULT_TYPES = ["C-Masked", "C-SDCs-Acceptable", "C-SDCs-Unacceptable", "Recrash"]  # 例如: ["C-Masked", "C-SDCs-Acceptable", "C-SDCs-Unacceptable", "Recrash"]

# 程序列表，如果为None则使用所有程序
PROGRAM_LIST = None  # 例如: ["fdtd-2d", "HPCCG", "miniFE"]

# 热力图布局类型
# 1: 程序为单独的热力图，行=结果类型，列=信号类型
# 2: 信号类型为单独的热力图，行=程序，列=结果类型
# 3: 结果类型为单独的热力图，行=信号类型，列=程序
HEATMAP_LAYOUT = 3

# 图表尺寸
FIGURE_SIZE = (10, 8)

# 热力图颜色方案
# 可选值: YlGnBu, viridis, plasma, inferno, magma, cividis, 
#        Blues, Greens, Reds, Purples, Oranges, Greys
CMAP = "YlGnBu"

# 是否使用对数刻度
USE_LOG_SCALE = True

# 是否在每个单元格中显示数值
SHOW_ANNOTATIONS = True

# 热力图单元格边框宽度
LINEWIDTHS = 0.5

# 图表标题和坐标轴标签
# 布局类型1：程序为中心的热力图
PROGRAM_CHART_TITLE_TEMPLATE = "program: {program}"  # {program}将被替换为具体程序名
PROGRAM_CHART_XLABEL = ""
PROGRAM_CHART_YLABEL = ""

# 布局类型2：信号为中心的热力图
SIGNAL_CHART_TITLE_TEMPLATE = "signal: {signal}"  # {signal}将被替换为具体信号名
SIGNAL_CHART_XLABEL = "result type"
SIGNAL_CHART_YLABEL = "program"

# 布局类型3：结果为中心的热力图
RESULT_CHART_TITLE_TEMPLATE = "result type: {result}"  # {result}将被替换为具体结果类型
RESULT_CHART_XLABEL = "program"
RESULT_CHART_YLABEL = "signal type"

# 字体设置
FONT_FAMILY = "monospace"  # 可选: serif, sans-serif, cursive, fantasy, monospace
FONT_WEIGHT = "normal"  # 可选: normal, bold, light, ultralight, heavy
FONT_STYLE = "normal"  # 可选: normal, italic, oblique

# 字体大小设置
TITLE_FONTSIZE = 18
XLABEL_FONTSIZE = 14
YLABEL_FONTSIZE = 14
TICK_FONTSIZE = 12
ANNOT_FONTSIZE = 10

# 字体颜色设置
TITLE_COLOR = "black"
XLABEL_COLOR = "black"
YLABEL_COLOR = "black"
TICK_COLOR = "black"
ANNOT_COLOR = "black"

# 图像输出DPI
DPI = 300

# 热力图单元格标注格式
# 'd'表示整数, '.1f'表示保留一位小数
ANNOTATION_FORMAT = "d"

# 输出图像格式
# 可选: 'png', 'jpg', 'svg', 'pdf'
IMAGE_FORMAT = "png"

# 是否按名称排序
SORT_BY_PROGRAM = True  # 程序排序
SORT_BY_RESULT = True   # 结果类型排序
SORT_BY_SIGNAL = True   # 信号类型排序

# 信号类型显示顺序（如果为None则按字母顺序排序）
SIGNAL_ORDER = ["SIGBUS", "SIGSEGV", "SIGFPE", "SIGABRT"]

# 结果类型显示顺序（如果为None则按字母顺序排序）
# RESULT_ORDER = ["C-Masked", "C-SDCs-Acceptable", "C-SDCs-Unacceptable", "Recrash", "C-unknown"]
RESULT_ORDER = ["Recrash", "C-SDCs-Unacceptable", "C-SDCs-Acceptable", "C-Masked"]

# 是否调整图形大小以适应数据大小
# 如果为True，则会根据行数和列数自动调整图形大小
AUTO_ADJUST_FIGSIZE = True

# 最大行高比例和最小行高
MAX_ROW_HEIGHT_RATIO = 0.2  # 相对于图形高度
MIN_ROW_HEIGHT = 0.5  # 英寸

# 坐标轴设置
ROTATE_XTICKS = 45  # X轴标签旋转角度（当程序数量多时）
XTICKS_HA = "right"  # X轴标签水平对齐方式, 可选: left, right, center

# 图表网格线设置
SHOW_GRID = False  # 是否显示网格线
GRID_COLOR = "#cccccc"  # 网格线颜色
GRID_LINESTYLE = "--"  # 网格线样式
GRID_LINEWIDTH = 0.5  # 网格线宽度

# 图表背景色
FIGURE_FACECOLOR = "white"
AXES_FACECOLOR = "#f8f8f8" 