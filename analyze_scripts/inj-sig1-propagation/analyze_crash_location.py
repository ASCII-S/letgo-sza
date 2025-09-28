#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分析注错后原位崩溃和非原位崩溃的分布占比

此脚本用于分析单个CSV文件，通过比较pc和Sig1pc是否相等，
判断实验是否是注错后原位崩溃。

新增功能：
- 支持导出原位crash和非原位crash的具体条目到单独的CSV文件
- 文件名格式：{原文件名}_samelocation.csv 和 {原文件名}_differentlocation.csv
"""

import os
import sys
import pandas as pd
import argparse


def analyze_crash_location(input_file, output_file=None, export_details=False, details_output_dir=None):
    """
    分析CSV文件中的原位崩溃和非原位崩溃的分布占比
    
    参数:
        input_file (str): 输入CSV文件路径
        output_file (str, optional): 输出CSV文件路径，默认为None
        export_details (bool, optional): 是否导出具体条目，默认为False
        details_output_dir (str, optional): 详细条目输出目录，默认为None
        
    返回:
        dict: 包含分析结果的字典
    """
    try:
        # 读取CSV文件
        df = pd.read_csv(input_file)
        
        # 提取文件名（不含路径和扩展名）
        file_name = os.path.splitext(os.path.basename(input_file))[0]
        
        # 筛选指定result类型的数据
        # target_results = ['C-Masked', 'C-SDCs-Acceptable', 'C-SDCs-Unacceptable', 'C-SDC', 'Recrash']
        target_results = ['Recrash']
        filtered_df = df[df['result'].isin(target_results)]
        
        # 如果筛选后数据为空，返回空结果
        if filtered_df.empty:
            print(f"警告: {input_file} 没有符合条件的数据")
            return {
                'file_name': file_name,
                'total_errors': 0,
                'same_location_crashes': 0,
                'different_location_crashes': 0,
                'same_location_percentage': 0,
                'different_location_percentage': 0
            }
        
        # 计算原位崩溃和非原位崩溃的数量
        # 原位崩溃: pc == Sig1pc
        same_location = filtered_df[filtered_df['Sig1pc'] == filtered_df['Sig2pc']]
        different_location = filtered_df[filtered_df['Sig1pc'] != filtered_df['Sig2pc']]
        
        # 填充NaN值以确保数据完整性
        same_location_count = len(same_location)
        different_location_count = len(different_location)
        total_count = same_location_count + different_location_count
        
        # 计算百分比
        same_location_percentage = (same_location_count / total_count * 100) if total_count > 0 else 0
        different_location_percentage = (different_location_count / total_count * 100) if total_count > 0 else 0
        
        # 导出具体条目到单独文件
        if export_details and same_location_count > 0:
            # 设置详细输出目录
            if details_output_dir is None:
                details_output_dir = "results/details"
            
            # 确保输出目录存在
            os.makedirs(details_output_dir, exist_ok=True)
            
            # 导出原位crash条目
            same_location_file = os.path.join(details_output_dir, f"{file_name}_samelocation.csv")
            same_location.to_csv(same_location_file, index=False)
            print(f"原位crash条目已保存到 {same_location_file}")
            
            # 可选：也导出非原位crash条目
            if different_location_count > 0:
                different_location_file = os.path.join(details_output_dir, f"{file_name}_differentlocation.csv")
                different_location.to_csv(different_location_file, index=False)
                print(f"非原位crash条目已保存到 {different_location_file}")
        
        # 准备结果
        result = {
            'file_name': file_name,
            'total_errors': total_count,
            'same_location_crashes': same_location_count,
            'different_location_crashes': different_location_count,
            'same_location_percentage': same_location_percentage,
            'different_location_percentage': different_location_percentage
        }
        
        # 如果指定了输出文件，保存结果
        if output_file:
            result_df = pd.DataFrame([result])
            result_df.to_csv(output_file, index=False)
            print(f"结果已保存到 {output_file}")
        
        return result
        
    except Exception as e:
        print(f"处理文件 {input_file} 时出错: {e}")
        return None


def main():
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='分析注错后原位崩溃和非原位崩溃的分布占比')
    parser.add_argument('--input', '-i', type=str, required=False, default='../CSV',
                        help='输入CSV文件路径')
    parser.add_argument('--output', '-o', type=str, required=False,
                        help='输出CSV文件路径')
    parser.add_argument('--export-details', '-e', action='store_true',
                        help='是否导出原位crash和非原位crash的具体条目到单独文件')
    parser.add_argument('--details-dir', '-d', type=str, required=False, default='results/details',
                        help='详细条目输出目录，默认为results/details')
    args = parser.parse_args()
    
    # 如果输入是目录，提示用户使用批处理脚本
    if os.path.isdir(args.input):
        print(f"错误: 输入'{args.input}'是一个目录。请指定单个CSV文件，或使用批处理脚本。")
        print("提示: 使用 analyze_crash_location_batch.py 进行批量处理")
        sys.exit(1)
    
    # 如果输入文件不存在，退出
    if not os.path.isfile(args.input):
        print(f"错误: 输入文件'{args.input}'不存在")
        sys.exit(1)
    
    # 如果未指定输出文件，使用默认命名
    if not args.output:
        file_name = os.path.splitext(os.path.basename(args.input))[0]
        args.output = f"results/{file_name}_crash_location_analysis.csv"
    
    # 确保输出目录存在
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    
    # 运行分析
    analyze_crash_location(args.input, args.output, args.export_details, args.details_dir)


if __name__ == "__main__":
    main() 