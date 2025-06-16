#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量分析注错后原位崩溃和非原位崩溃的分布占比

此脚本用于批量处理CSV目录下的所有CSV文件，分析原位崩溃和非原位崩溃的分布占比，
并将所有结果汇总到一个CSV文件中。
"""

import os
import glob
import pandas as pd
import argparse
from tqdm import tqdm

# 导入单文件分析函数
from analyze_crash_location import analyze_crash_location


def batch_analyze_crash_location(input_dir, output_file, file_pattern="*.csv"):
    """
    批量分析CSV目录下的所有CSV文件中的原位崩溃和非原位崩溃的分布占比
    
    参数:
        input_dir (str): 输入CSV文件目录
        output_file (str): 输出CSV文件路径
        file_pattern (str, optional): 文件匹配模式，默认为"*.csv"
        
    返回:
        bool: 是否成功完成分析
    """
    try:
        # 获取所有匹配的CSV文件
        file_pattern = os.path.join(input_dir, file_pattern)
        csv_files = glob.glob(file_pattern)
        
        if not csv_files:
            print(f"错误: 在'{input_dir}'中没有找到匹配的CSV文件")
            return False
        
        print(f"找到{len(csv_files)}个CSV文件，开始分析...")
        
        # 存储所有结果
        results = []
        
        # 使用tqdm显示进度
        for csv_file in tqdm(csv_files, desc="正在分析文件"):
            result = analyze_crash_location(csv_file)
            if result:
                results.append(result)
        
        # 创建汇总DataFrame
        if results:
            results_df = pd.DataFrame(results)
            
            # 确保输出目录存在
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            
            # 保存汇总结果
            results_df.to_csv(output_file, index=False)
            print(f"\n分析完成，结果已保存到 {output_file}")
            print(f"共分析了{len(results)}个文件")
            
            # 打印汇总信息
            total_errors = results_df['total_errors'].sum()
            total_same_location = results_df['same_location_crashes'].sum()
            total_different_location = results_df['different_location_crashes'].sum()
            
            avg_same_percentage = (total_same_location / total_errors * 100) if total_errors > 0 else 0
            avg_diff_percentage = (total_different_location / total_errors * 100) if total_errors > 0 else 0
            
            print(f"\n汇总统计:")
            print(f"总错误数: {total_errors}")
            print(f"原位崩溃数: {total_same_location} ({avg_same_percentage:.2f}%)")
            print(f"非原位崩溃数: {total_different_location} ({avg_diff_percentage:.2f}%)")
            
            return True
        else:
            print("警告: 没有成功分析任何文件")
            return False
            
    except Exception as e:
        print(f"批量处理过程中出错: {e}")
        return False


def main():
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='批量分析注错后原位崩溃和非原位崩溃的分布占比')
    parser.add_argument('--input-dir', '-i', type=str, required=False, default='../CSV',
                        help='输入CSV文件目录，默认为../CSV')
    parser.add_argument('--output', '-o', type=str, required=False, default='results/crash_location_summary.csv',
                        help='输出汇总CSV文件路径，默认为results/crash_location_summary.csv')
    parser.add_argument('--pattern', '-p', type=str, required=False, default='*.csv',
                        help='文件匹配模式，默认为*.csv')
    args = parser.parse_args()
    
    # 检查输入目录是否存在
    if not os.path.isdir(args.input_dir):
        print(f"错误: 输入目录'{args.input_dir}'不存在")
        return False
    
    # 运行批量分析
    batch_analyze_crash_location(args.input_dir, args.output, args.pattern)


if __name__ == "__main__":
    main() 