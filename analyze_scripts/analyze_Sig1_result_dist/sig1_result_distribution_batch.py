#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
@file sig1_result_distribution_batch.py
@brief 批量处理CSV文件并合并结果
@author AI助手
@date 创建于2023年
"""

import pandas as pd
import os
import glob
import argparse
from tqdm import tqdm

# 导入单文件处理模块
from sig1_result_distribution import get_distribution_from_csv

def batch_process_csv_files(input_dir, output_file):
    """
    批量处理目录中的所有CSV文件并合并结果
    
    @param input_dir 输入目录路径，包含要处理的CSV文件
    @param output_file 输出文件路径，用于保存合并后的结果
    @return None
    """
    # 获取输入目录中的所有CSV文件
    csv_files = glob.glob(os.path.join(input_dir, "*.csv"))
    
    if not csv_files:
        print(f"错误：在目录 {input_dir} 中未找到CSV文件")
        return
    
    print(f"找到 {len(csv_files)} 个CSV文件待处理")
    
    # 存储所有处理结果的列表
    all_results = []
    
    # 处理每个CSV文件
    for csv_file in tqdm(csv_files, desc="处理CSV文件"):
        # 使用单文件处理模块的函数获取分布结果
        result = get_distribution_from_csv(csv_file)
        if result is not None:
            all_results.append(result)
    
    if not all_results:
        print("错误：所有文件处理失败，无法合并结果")
        return
    
    # 合并所有结果
    print("合并所有结果...")
    
    # 初始化合并后的DataFrame
    merged_df = all_results[0]
    
    # 逐个合并其他结果
    for df in all_results[1:]:
        # 获取两个DataFrame的所有列（excluding program and result columns）
        cols1 = set(merged_df.columns) - {'program', 'result'}
        cols2 = set(df.columns) - {'program', 'result'}
        
        # 找出合并后需要的所有列
        all_cols = cols1.union(cols2)
        
        # 为缺失的列添加空值
        for col in all_cols:
            if col not in merged_df.columns:
                merged_df[col] = 0
            if col not in df.columns:
                df[col] = 0
        
        # 合并两个DataFrame
        merged_df = pd.concat([merged_df, df], ignore_index=True)
    
    # 创建输出目录（如果不存在）
    output_dir = os.path.dirname(output_file)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"创建输出目录：{output_dir}")
    
    # 保存合并后的结果
    merged_df.to_csv(output_file, index=False)
    print(f"合并结果已保存到：{output_file}")
    
    # 打印结果统计信息
    print(f"\n共处理了 {len(all_results)} 个CSV文件")
    print(f"合并后的结果包含 {len(merged_df)} 行数据")

if __name__ == "__main__":
    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(description='批量处理CSV文件并合并结果')
    parser.add_argument('--input_dir', '-i', default="../CSV", 
                        help='输入目录路径，包含要处理的CSV文件（默认：../CSV）')
    parser.add_argument('--output_file', '-o', default="./analysis_results/merged_result_sig1_distribution.csv",
                        help='输出文件路径，用于保存合并后的结果（默认：./analysis_results/merged_result_sig1_distribution.csv）')
    
    # 解析命令行参数
    args = parser.parse_args()
    
    # 批量处理CSV文件
    batch_process_csv_files(args.input_dir, args.output_file)
