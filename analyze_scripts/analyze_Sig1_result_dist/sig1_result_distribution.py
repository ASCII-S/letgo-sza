#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
@file sig1_result_distribution.py
@brief 统计CSV文件中result列和Sig1列的分布关系
@author AI助手
@date 创建于2023年
"""

import pandas as pd
import os
import matplotlib.pyplot as plt
import seaborn as sns
import argparse

def get_distribution_from_csv(csv_file):
    """
    从CSV文件中提取result列和Sig1列的分布关系
    
    @param csv_file CSV文件路径
    @return 包含分析结果的DataFrame或None（如果处理失败）
    """
    # 检查文件是否存在
    if not os.path.exists(csv_file):
        print(f"错误：文件 {csv_file} 不存在")
        return None
    
    # 读取CSV文件
    try:
        df = pd.read_csv(csv_file)
    except Exception as e:
        print(f"读取CSV文件时出错：{e}")
        return None
    
    # 检查必要的列是否存在
    if 'result' not in df.columns or 'Sig1' not in df.columns:
        print("错误：CSV文件缺少必要的列 'result' 或 'Sig1'")
        return None
    
    # 获取CSV文件名（不含路径和扩展名）作为程序名
    program_name = os.path.splitext(os.path.basename(csv_file))[0]
    
    # 创建交叉表以显示分布
    distribution = pd.crosstab(df['result'], df['Sig1'])
    
    # 重置索引，将result变为普通列
    distribution = distribution.reset_index()
    
    # 添加程序名列，并确保它在result列的左侧
    distribution.insert(0, 'program', program_name)
    
    return distribution

def save_distribution(distribution, output_file, csv_filename):
    """
    保存分布结果到CSV文件
    
    @param distribution 分布结果DataFrame
    @param output_file 输出文件路径
    @param csv_filename 源CSV文件名（不含扩展名）
    @return None
    """
    if distribution is None:
        return
        
    distribution.to_csv(output_file, index=False)
    print(f"\n分布结果已保存到：{output_file}")

def generate_distribution_plot(distribution, plot_file, program_name):
    """
    生成分布热图
    
    @param distribution 分布结果DataFrame
    @param plot_file 输出图表文件路径
    @param program_name 程序名
    @return None
    """
    if distribution is None:
        return
        
    # 为了绘图，需要将数据重新设置为透视表格式
    plot_distribution = distribution.set_index(['program', 'result'])
    
    plt.figure(figsize=(12, 8))
    sns.heatmap(plot_distribution, annot=True, cmap="YlGnBu", fmt="d")
    plt.title(f'程序 {program_name} 的Result和Sig1分布热图')
    plt.tight_layout()
    
    # 保存图表
    plt.savefig(plot_file)
    print(f"分布热图已保存到：{plot_file}")

def analyze_distribution(csv_file, generate_plot=False):
    """
    分析CSV文件中result列和Sig1列的分布关系并保存结果
    
    @param csv_file CSV文件路径
    @param generate_plot 是否生成热图
    @return 分布结果DataFrame
    """
    # 获取分布数据
    distribution = get_distribution_from_csv(csv_file)
    
    if distribution is None:
        return None
    
    # 打印分布结果
    print("\n=== Result和Sig1的分布统计 ===")
    print(distribution)
    
    # 创建输出目录（脚本目录下的results文件夹）
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(script_dir, "analysis_results")
    
    # 如果输出目录不存在，创建它
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"创建输出目录：{output_dir}")
    
    # 获取CSV文件名（不含路径和扩展名）作为结果文件前缀
    csv_filename = os.path.splitext(os.path.basename(csv_file))[0]
    
    # 保存分布结果到CSV文件
    output_file = os.path.join(output_dir, f'{csv_filename}_result_sig1_distribution.csv')
    save_distribution(distribution, output_file, csv_filename)
    
    # 如果需要生成热图
    if generate_plot:
        plot_file = os.path.join(output_dir, f'{csv_filename}_result_sig1_distribution.png')
        generate_distribution_plot(distribution, plot_file, csv_filename)
    
    return distribution

if __name__ == "__main__":
    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(description='统计CSV文件中result列和Sig1列的分布关系')
    parser.add_argument('csv_file', help='输入的CSV文件路径')
    parser.add_argument('--plot', '-p', action='store_true', help='是否生成热图')
    
    # 解析命令行参数
    args = parser.parse_args()
    
    # 分析分布
    analyze_distribution(args.csv_file, args.plot)
