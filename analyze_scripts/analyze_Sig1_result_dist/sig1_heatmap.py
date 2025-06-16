#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
@file sig1_heatmap.py
@brief 为每个程序生成结果分布热力图
@author AI助手
@date 创建于2023年
"""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os
import numpy as np
from matplotlib.colors import LogNorm, Normalize

# 导入配置
from sig1_heatmap_config import *

# 自定义颜色规范化处理，确保0值也有颜色
class CustomNorm(Normalize):
    def __init__(self, vmin=None, vmax=None, clip=False):
        super().__init__(vmin, vmax, clip)
        
    def __call__(self, value, clip=None):
        # 将0值映射到略高于vmin的值，而不是vmin
        # 这样0值会有一个非常浅的颜色而不是空白
        if hasattr(value, "__iter__"):
            mask = np.isclose(value, 0)
            result = np.ma.masked_array(value, mask=mask)
            result = super().__call__(result, clip)
            # 为0值分配一个非常小的颜色值（略高于vmin）
            result.data[mask] = 0.05  # 0.05是一个非常浅的颜色值
            return result
        else:
            if value == 0:
                return 5
            else:
                return super().__call__(value, clip)

# 自定义对数规范化处理，确保0值也有颜色
class CustomLogNorm(LogNorm):
    def __init__(self, vmin=None, vmax=None, clip=False):
        super().__init__(vmin, vmax, clip)
        
    def __call__(self, value, clip=None):
        # 先用一个非常小的正数替换0值
        if hasattr(value, "__iter__"):
            mask = np.isclose(value, 0)
            temp_value = value.copy()
            temp_value[mask] = 1e-10  # 替换0值为一个非常小的正数
            result = super().__call__(temp_value, clip)
            # 为0值分配一个特殊的颜色值（通常是最浅的颜色）
            result.data[mask] = 0.05  # 0.05是一个非常浅的颜色值
            return result
        else:
            if value == 0:
                return 5
            else:
                return super().__call__(value, clip)

def setup_figure_style():
    """
    设置全局图表样式
    """
    # 设置字体样式
    plt.rcParams.update({
        'font.family': FONT_FAMILY,
        'font.weight': FONT_WEIGHT,
        'font.style': FONT_STYLE,
        'font.size': TICK_FONTSIZE,
        'figure.facecolor': FIGURE_FACECOLOR,
        'axes.facecolor': AXES_FACECOLOR
    })

def create_heatmaps(csv_file=CSV_FILE, output_dir=OUTPUT_DIR, signal_columns=SIGNAL_COLUMNS):
    """
    为CSV文件中每个程序创建热力图
    
    @param csv_file CSV文件路径
    @param output_dir 输出目录
    @param signal_columns 要显示的信号列，如果为None则显示所有信号列
    """
    # 设置全局图表样式
    setup_figure_style()
    
    # 检查文件是否存在
    if not os.path.exists(csv_file):
        print(f"错误：文件 {csv_file} 不存在")
        return
    
    # 读取CSV文件
    try:
        df = pd.read_csv(csv_file)
    except Exception as e:
        print(f"读取CSV文件时出错：{e}")
        return
    
    # 检查必要的列是否存在
    if 'program' not in df.columns or 'result' not in df.columns:
        print("错误：CSV文件缺少必要的列 'program' 或 'result'")
        return
    
    # 如果没有指定信号列，则使用除program和result外的所有列
    if signal_columns is None:
        signal_columns = [col for col in df.columns if col not in ['program', 'result']]
    
    # 如果指定的信号列不存在，则报错
    for col in signal_columns:
        if col not in df.columns:
            print(f"错误：CSV文件中不存在列 '{col}'")
            return
    
    # 创建输出目录
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"创建输出目录：{output_dir}")
    
    # 根据配置选择热力图布局类型
    if HEATMAP_LAYOUT == 1:
        # 程序为单独的热力图，行=结果类型，列=信号类型
        create_program_based_heatmaps(df, output_dir, signal_columns)
    elif HEATMAP_LAYOUT == 2:
        # 信号类型为单独的热力图，行=程序，列=结果类型
        create_signal_based_heatmaps(df, output_dir)
    elif HEATMAP_LAYOUT == 3:
        # 结果类型为单独的热力图，行=信号类型，列=程序
        create_result_based_heatmaps(df, output_dir)
    else:
        print(f"错误：未知的热力图布局类型 {HEATMAP_LAYOUT}")
        return

def apply_heatmap_style(ax):
    """
    应用热力图样式设置
    
    @param ax matplotlib轴对象
    """
    # 设置坐标轴标签颜色
    ax.xaxis.label.set_color(XLABEL_COLOR)
    ax.yaxis.label.set_color(YLABEL_COLOR)
    
    # 设置刻度标签颜色
    ax.tick_params(axis='x', colors=TICK_COLOR)
    ax.tick_params(axis='y', colors=TICK_COLOR)
    
    # 设置网格线
    if SHOW_GRID:
        ax.grid(True, color=GRID_COLOR, linestyle=GRID_LINESTYLE, linewidth=GRID_LINEWIDTH)
    else:
        ax.grid(False)

def create_program_based_heatmaps(df, output_dir, signal_columns):
    """
    为每个程序创建热力图，行=结果类型，列=信号类型
    
    @param df 数据DataFrame
    @param output_dir 输出目录
    @param signal_columns 要显示的信号列
    """
    # 过滤程序列表
    if PROGRAM_LIST is not None:
        programs = [p for p in PROGRAM_LIST if p in df['program'].unique()]
        if not programs:
            print("错误：配置的程序列表中没有与数据匹配的程序")
            return
    else:
        programs = df['program'].unique()
    
    # 如果配置为按程序名称排序，则排序
    if SORT_BY_PROGRAM:
        programs = sorted(programs)
    
    print(f"找到 {len(programs)} 个程序，准备生成热力图")
    
    # 过滤结果类型
    if RESULT_TYPES is not None:
        result_types = [r for r in RESULT_TYPES if r in df['result'].unique()]
    else:
        result_types = df['result'].unique()
    
    # 如果配置为按结果类型排序，则排序
    if SORT_BY_RESULT and RESULT_ORDER is not None:
        # 按照RESULT_ORDER中指定的顺序排序，不在列表中的放在最后
        def result_sort_key(x):
            try:
                return RESULT_ORDER.index(x)
            except ValueError:
                return len(RESULT_ORDER) + 1
        result_types = sorted(result_types, key=result_sort_key)
    elif SORT_BY_RESULT:
        result_types = sorted(result_types)
    
    # 如果配置为按信号类型排序，则排序信号列
    if SORT_BY_SIGNAL and SIGNAL_ORDER is not None:
        # 按照SIGNAL_ORDER中指定的顺序排序，不在列表中的放在最后
        def signal_sort_key(x):
            try:
                return SIGNAL_ORDER.index(x)
            except ValueError:
                return len(SIGNAL_ORDER) + 1
        signal_columns = sorted(signal_columns, key=signal_sort_key)
    elif SORT_BY_SIGNAL:
        signal_columns = sorted(signal_columns)
    
    # 为每个程序生成热力图
    for program in programs:
        # 筛选当前程序的数据
        program_df = df[df['program'] == program]
        
        # 筛选结果类型
        program_df = program_df[program_df['result'].isin(result_types)]
        
        # 如果无数据，则跳过
        if len(program_df) == 0:
            print(f"警告：程序 {program} 没有符合条件的数据，跳过")
            continue
        
        # 提取需要的列：result和signal_columns
        heatmap_df = program_df[['result'] + signal_columns]
        
        # 将result设置为索引
        heatmap_df = heatmap_df.set_index('result')
        
        # 确保行顺序与result_types一致
        heatmap_df = heatmap_df.reindex(result_types)
        
        # 确保列顺序与signal_columns一致
        heatmap_df = heatmap_df[signal_columns]
        
        # 将NaN替换为0
        heatmap_df = heatmap_df.fillna(0)
        
        # 确定图表尺寸
        figsize = FIGURE_SIZE
        if AUTO_ADJUST_FIGSIZE:
            # 根据行数和列数动态调整图形大小
            n_rows = len(heatmap_df)
            n_cols = len(signal_columns)
            # 确保每行至少有MIN_ROW_HEIGHT英寸高
            row_height = max(MIN_ROW_HEIGHT, FIGURE_SIZE[1] * MAX_ROW_HEIGHT_RATIO)
            figure_height = max(FIGURE_SIZE[1], n_rows * row_height)
            figure_width = FIGURE_SIZE[0]
            figsize = (figure_width, figure_height)
        
        # 创建热力图
        plt.figure(figsize=figsize, facecolor=FIGURE_FACECOLOR)
        
        # 判断是否使用对数刻度
        if USE_LOG_SCALE and heatmap_df.max().max() > 0:
            # 检查数据是否适合对数刻度
            data_range = heatmap_df.values
            data_range = data_range[data_range > 0]  # 只考虑正值
            if len(data_range) > 0:
                # 使用对数刻度，并使用自定义的LogNorm确保0值也有颜色
                norm = CustomLogNorm(vmin=data_range.min(), vmax=data_range.max())
                ax = sns.heatmap(
                    heatmap_df, 
                    annot=SHOW_ANNOTATIONS, 
                    cmap=CMAP, 
                    fmt=ANNOTATION_FORMAT, 
                    linewidths=LINEWIDTHS,
                    norm=norm,
                    annot_kws={"size": ANNOT_FONTSIZE, "color": ANNOT_COLOR}
                )
            else:
                # 数据不适合对数刻度，使用常规热力图
                norm = CustomNorm(vmin=0, vmax=1)
                ax = sns.heatmap(
                    heatmap_df, 
                    annot=SHOW_ANNOTATIONS, 
                    cmap=CMAP, 
                    fmt=ANNOTATION_FORMAT, 
                    linewidths=LINEWIDTHS,
                    norm=norm,
                    annot_kws={"size": ANNOT_FONTSIZE, "color": ANNOT_COLOR}
                )
        else:
            # 使用常规热力图，确保0值也有颜色
            vmax = heatmap_df.max().max()
            norm = CustomNorm(vmin=0, vmax=vmax if vmax > 0 else 1)
            ax = sns.heatmap(
                heatmap_df, 
                annot=SHOW_ANNOTATIONS, 
                cmap=CMAP, 
                fmt=ANNOTATION_FORMAT, 
                linewidths=LINEWIDTHS,
                norm=norm,
                annot_kws={"size": ANNOT_FONTSIZE, "color": ANNOT_COLOR}
            )
        
        # 设置标题和标签
        plt.title(
            PROGRAM_CHART_TITLE_TEMPLATE.format(program=program), 
            fontsize=TITLE_FONTSIZE, 
            color=TITLE_COLOR, 
            weight=FONT_WEIGHT, 
            style=FONT_STYLE
        )
        plt.xlabel(
            PROGRAM_CHART_XLABEL, 
            fontsize=XLABEL_FONTSIZE, 
            color=XLABEL_COLOR, 
            weight=FONT_WEIGHT, 
            style=FONT_STYLE
        )
        plt.ylabel(
            PROGRAM_CHART_YLABEL, 
            fontsize=YLABEL_FONTSIZE, 
            color=YLABEL_COLOR, 
            weight=FONT_WEIGHT, 
            style=FONT_STYLE
        )
        
        # 应用热力图样式
        apply_heatmap_style(ax)
        
        # 调整布局
        plt.tight_layout()
        
        # 保存图表
        output_file = os.path.join(output_dir, f'{program}_heatmap.{IMAGE_FORMAT}')
        plt.savefig(output_file, dpi=DPI)
        plt.close()
        
        print(f"已生成程序 {program} 的热力图：{output_file}")

def create_signal_based_heatmaps(df, output_dir):
    """
    为每个信号类型创建热力图，行=程序，列=结果类型
    
    @param df 数据DataFrame
    @param output_dir 输出目录
    """
    # 获取所有信号列
    if SIGNAL_COLUMNS is None:
        signal_columns = [col for col in df.columns if col not in ['program', 'result']]
    else:
        signal_columns = SIGNAL_COLUMNS
    
    # 如果配置为按信号类型排序，则排序
    if SORT_BY_SIGNAL and SIGNAL_ORDER is not None:
        def signal_sort_key(x):
            try:
                return SIGNAL_ORDER.index(x)
            except ValueError:
                return len(SIGNAL_ORDER) + 1
        signal_columns = sorted(signal_columns, key=signal_sort_key)
    elif SORT_BY_SIGNAL:
        signal_columns = sorted(signal_columns)
    
    # 过滤程序列表
    if PROGRAM_LIST is not None:
        programs = [p for p in PROGRAM_LIST if p in df['program'].unique()]
    else:
        programs = df['program'].unique()
    
    # 如果配置为按程序名称排序，则排序
    if SORT_BY_PROGRAM:
        programs = sorted(programs)
    
    # 过滤结果类型
    if RESULT_TYPES is not None:
        result_types = [r for r in RESULT_TYPES if r in df['result'].unique()]
    else:
        result_types = df['result'].unique()
    
    # 如果配置为按结果类型排序，则排序
    if SORT_BY_RESULT and RESULT_ORDER is not None:
        def result_sort_key(x):
            try:
                return RESULT_ORDER.index(x)
            except ValueError:
                return len(RESULT_ORDER) + 1
        result_types = sorted(result_types, key=result_sort_key)
    elif SORT_BY_RESULT:
        result_types = sorted(result_types)
    
    print(f"找到 {len(signal_columns)} 个信号类型，准备生成热力图")
    
    # 为每个信号类型生成热力图
    for signal in signal_columns:
        # 创建数据透视表：程序为行，结果类型为列，单元格值为信号列的值
        pivot_df = df.pivot_table(
            index='program', 
            columns='result', 
            values=signal,
            fill_value=0
        )
        
        # 筛选程序和结果类型
        pivot_df = pivot_df.loc[pivot_df.index.isin(programs), :]
        pivot_df = pivot_df.loc[:, pivot_df.columns.isin(result_types)]
        
        # 确保列顺序与result_types一致
        pivot_df = pivot_df.reindex(columns=result_types)
        
        # 确保行顺序与programs一致
        pivot_df = pivot_df.reindex(index=programs)
        
        # 将NaN替换为0
        pivot_df = pivot_df.fillna(0)
        
        # 确定图表尺寸
        figsize = FIGURE_SIZE
        if AUTO_ADJUST_FIGSIZE:
            # 根据行数和列数动态调整图形大小
            n_rows = len(pivot_df)
            n_cols = len(pivot_df.columns)
            # 确保每行至少有MIN_ROW_HEIGHT英寸高
            row_height = max(MIN_ROW_HEIGHT, FIGURE_SIZE[1] * MAX_ROW_HEIGHT_RATIO)
            figure_height = max(FIGURE_SIZE[1], n_rows * row_height)
            figure_width = FIGURE_SIZE[0]
            figsize = (figure_width, figure_height)
        
        # 创建热力图
        plt.figure(figsize=figsize, facecolor=FIGURE_FACECOLOR)
        
        # 判断是否使用对数刻度
        if USE_LOG_SCALE and pivot_df.max().max() > 0:
            # 检查数据是否适合对数刻度
            data_range = pivot_df.values
            data_range = data_range[data_range > 0]  # 只考虑正值
            if len(data_range) > 0:
                # 使用对数刻度，并使用自定义的LogNorm确保0值也有颜色
                norm = CustomLogNorm(vmin=data_range.min(), vmax=data_range.max())
                ax = sns.heatmap(
                    pivot_df, 
                    annot=SHOW_ANNOTATIONS, 
                    cmap=CMAP, 
                    fmt=ANNOTATION_FORMAT, 
                    linewidths=LINEWIDTHS,
                    norm=norm,
                    annot_kws={"size": ANNOT_FONTSIZE, "color": ANNOT_COLOR}
                )
            else:
                # 数据不适合对数刻度，使用常规热力图
                norm = CustomNorm(vmin=0, vmax=1)
                ax = sns.heatmap(
                    pivot_df, 
                    annot=SHOW_ANNOTATIONS, 
                    cmap=CMAP, 
                    fmt=ANNOTATION_FORMAT, 
                    linewidths=LINEWIDTHS,
                    norm=norm,
                    annot_kws={"size": ANNOT_FONTSIZE, "color": ANNOT_COLOR}
                )
        else:
            # 使用常规热力图，确保0值也有颜色
            vmax = pivot_df.max().max()
            norm = CustomNorm(vmin=0, vmax=vmax if vmax > 0 else 1)
            ax = sns.heatmap(
                pivot_df, 
                annot=SHOW_ANNOTATIONS, 
                cmap=CMAP, 
                fmt=ANNOTATION_FORMAT, 
                linewidths=LINEWIDTHS,
                norm=norm,
                annot_kws={"size": ANNOT_FONTSIZE, "color": ANNOT_COLOR}
            )
        
        # 设置标题和标签
        plt.title(
            SIGNAL_CHART_TITLE_TEMPLATE.format(signal=signal), 
            fontsize=TITLE_FONTSIZE, 
            color=TITLE_COLOR, 
            weight=FONT_WEIGHT, 
            style=FONT_STYLE
        )
        plt.xlabel(
            SIGNAL_CHART_XLABEL, 
            fontsize=XLABEL_FONTSIZE, 
            color=XLABEL_COLOR, 
            weight=FONT_WEIGHT, 
            style=FONT_STYLE
        )
        plt.ylabel(
            SIGNAL_CHART_YLABEL, 
            fontsize=YLABEL_FONTSIZE, 
            color=YLABEL_COLOR, 
            weight=FONT_WEIGHT, 
            style=FONT_STYLE
        )
        
        # 应用热力图样式
        apply_heatmap_style(ax)
        
        # 调整布局
        plt.tight_layout()
        
        # 保存图表
        output_file = os.path.join(output_dir, f'signal_{signal}_heatmap.{IMAGE_FORMAT}')
        plt.savefig(output_file, dpi=DPI)
        plt.close()
        
        print(f"已生成信号 {signal} 的热力图：{output_file}")

def create_result_based_heatmaps(df, output_dir):
    """
    为每个结果类型创建热力图，行=信号类型，列=程序
    
    @param df 数据DataFrame
    @param output_dir 输出目录
    """
    # 获取所有信号列
    if SIGNAL_COLUMNS is None:
        signal_columns = [col for col in df.columns if col not in ['program', 'result']]
    else:
        signal_columns = SIGNAL_COLUMNS
    
    # 如果配置为按信号类型排序，则排序
    if SORT_BY_SIGNAL and SIGNAL_ORDER is not None:
        def signal_sort_key(x):
            try:
                return SIGNAL_ORDER.index(x)
            except ValueError:
                return len(SIGNAL_ORDER) + 1
        signal_columns = sorted(signal_columns, key=signal_sort_key)
    elif SORT_BY_SIGNAL:
        signal_columns = sorted(signal_columns)
    
    # 过滤程序列表
    if PROGRAM_LIST is not None:
        programs = [p for p in PROGRAM_LIST if p in df['program'].unique()]
    else:
        programs = df['program'].unique()
    
    # 如果配置为按程序名称排序，则排序
    if SORT_BY_PROGRAM:
        programs = sorted(programs)
    
    # 过滤结果类型
    if RESULT_TYPES is not None:
        result_types = [r for r in RESULT_TYPES if r in df['result'].unique()]
    else:
        result_types = df['result'].unique()
    
    # 如果配置为按结果类型排序，则排序
    if SORT_BY_RESULT and RESULT_ORDER is not None:
        def result_sort_key(x):
            try:
                return RESULT_ORDER.index(x)
            except ValueError:
                return len(RESULT_ORDER) + 1
        result_types = sorted(result_types, key=result_sort_key)
    elif SORT_BY_RESULT:
        result_types = sorted(result_types)
    
    print(f"找到 {len(result_types)} 个结果类型，准备生成热力图")
    
    # 为每个结果类型生成热力图
    for result_type in result_types:
        # 筛选当前结果类型的数据
        result_df = df[df['result'] == result_type]
        
        # 如果无数据，则跳过
        if len(result_df) == 0:
            print(f"警告：结果类型 {result_type} 没有数据，跳过")
            continue
        
        # 创建透视表
        # 行是信号类型，列是程序
        pivot_data = {}
        
        # 筛选程序
        result_df = result_df[result_df['program'].isin(programs)]
        
        # 对于每个信号类型
        for signal in signal_columns:
            # 创建一行数据
            row_data = {}
            
            # 对于每个程序
            for program in programs:
                # 获取当前程序、当前结果类型、当前信号的值
                value = result_df[result_df['program'] == program][signal].sum()
                row_data[program] = value
            
            # 将行数据添加到透视表
            pivot_data[signal] = row_data
        
        # 创建DataFrame
        pivot_df = pd.DataFrame(pivot_data).T
        
        # 将NaN替换为0
        pivot_df = pivot_df.fillna(0)
        
        # 确定图表尺寸
        figsize = FIGURE_SIZE
        if AUTO_ADJUST_FIGSIZE:
            # 根据行数和列数动态调整图形大小
            n_rows = len(pivot_df)
            n_cols = len(pivot_df.columns)
            # 确保每行至少有MIN_ROW_HEIGHT英寸高
            row_height = max(MIN_ROW_HEIGHT, FIGURE_SIZE[1] * MAX_ROW_HEIGHT_RATIO)
            figure_height = max(FIGURE_SIZE[1], n_rows * row_height)
            figure_width = FIGURE_SIZE[0] * (n_cols / 10)  # 根据列数调整宽度
            figure_width = max(FIGURE_SIZE[0], figure_width)
            figsize = (figure_width, figure_height)
        
        # 创建热力图
        plt.figure(figsize=figsize, facecolor=FIGURE_FACECOLOR)
        
        # 判断是否使用对数刻度
        if USE_LOG_SCALE and pivot_df.max().max() > 0:
            # 检查数据是否适合对数刻度
            data_range = pivot_df.values
            data_range = data_range[data_range > 0]  # 只考虑正值
            if len(data_range) > 0:
                # 使用对数刻度，并使用自定义的LogNorm确保0值也有颜色
                norm = CustomLogNorm(vmin=data_range.min(), vmax=data_range.max())
                ax = sns.heatmap(
                    pivot_df, 
                    annot=SHOW_ANNOTATIONS, 
                    cmap=CMAP, 
                    fmt=ANNOTATION_FORMAT, 
                    linewidths=LINEWIDTHS,
                    norm=norm,
                    annot_kws={"size": ANNOT_FONTSIZE, "color": ANNOT_COLOR}
                )
            else:
                # 数据不适合对数刻度，使用常规热力图
                norm = CustomNorm(vmin=0, vmax=1)
                ax = sns.heatmap(
                    pivot_df, 
                    annot=SHOW_ANNOTATIONS, 
                    cmap=CMAP, 
                    fmt=ANNOTATION_FORMAT, 
                    linewidths=LINEWIDTHS,
                    norm=norm,
                    annot_kws={"size": ANNOT_FONTSIZE, "color": ANNOT_COLOR}
                )
        else:
            # 使用常规热力图，确保0值也有颜色
            vmax = pivot_df.max().max()
            norm = CustomNorm(vmin=0, vmax=vmax if vmax > 0 else 1)
            ax = sns.heatmap(
                pivot_df, 
                annot=SHOW_ANNOTATIONS, 
                cmap=CMAP, 
                fmt=ANNOTATION_FORMAT, 
                linewidths=LINEWIDTHS,
                norm=norm,
                annot_kws={"size": ANNOT_FONTSIZE, "color": ANNOT_COLOR}
            )
        
        # 设置标题和标签
        plt.title(
            RESULT_CHART_TITLE_TEMPLATE.format(result=result_type), 
            fontsize=TITLE_FONTSIZE, 
            color=TITLE_COLOR, 
            weight=FONT_WEIGHT, 
            style=FONT_STYLE
        )
        plt.xlabel(
            RESULT_CHART_XLABEL, 
            fontsize=XLABEL_FONTSIZE, 
            color=XLABEL_COLOR, 
            weight=FONT_WEIGHT, 
            style=FONT_STYLE
        )
        plt.ylabel(
            RESULT_CHART_YLABEL, 
            fontsize=YLABEL_FONTSIZE, 
            color=YLABEL_COLOR, 
            weight=FONT_WEIGHT, 
            style=FONT_STYLE
        )
        
        # 应用热力图样式
        apply_heatmap_style(ax)
        
        # 如果程序数量较多，调整x轴标签的角度
        if len(programs) > 5:
            plt.xticks(rotation=ROTATE_XTICKS, ha=XTICKS_HA)
        
        # 调整布局
        plt.tight_layout()
        
        # 保存图表
        result_name = result_type.replace(' ', '_').replace('-', '_')
        output_file = os.path.join(output_dir, f'result_{result_name}_heatmap.{IMAGE_FORMAT}')
        plt.savefig(output_file, dpi=DPI)
        plt.close()
        
        print(f"已生成结果类型 {result_type} 的热力图：{output_file}")

if __name__ == "__main__":
    # 创建热力图
    create_heatmaps()
    print("所有热力图生成完成！") 