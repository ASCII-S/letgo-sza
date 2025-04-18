#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import pandas as pd
import argparse
from datetime import datetime

def analyze_csv(input_file, columns_to_group, output_dir=None, output_filename=None):
    """
    分析CSV文件，根据指定列分组，计算计数和占比
    
    参数:
        input_file (str): 输入CSV文件路径
        columns_to_group (list): 用于分组的列名列表
        output_dir (str): 输出目录，默认为input_file所在目录下的analysis_results
        output_filename (str): 输出文件名，默认为原文件名_analysis.csv
    
    返回:
        str: 输出文件的路径
    """
    print(f"开始分析CSV文件: {input_file}")
    
    # 读取CSV文件
    df = pd.read_csv(input_file)
    total_records = len(df)
    
    print(f"总记录数: {total_records}")
    
    # 检查指定的列是否都存在
    missing_columns = [col for col in columns_to_group if col not in df.columns]
    if missing_columns:
        raise ValueError(f"CSV文件中缺少以下列: {missing_columns}")
    
    # 清理数据：将null值替换为字符串'null'
    for col in columns_to_group:
        df[col] = df[col].fillna('null')
    
    # 根据指定列分组并计数
    grouped = df.groupby(columns_to_group).size().reset_index(name='count')
    
    # 计算占比
    grouped['percentage'] = grouped['count'] / total_records * 100
    
    # 按计数降序排序
    grouped = grouped.sort_values('count', ascending=False)
    
    # 设置输出目录和文件名
    if output_dir is None:
        input_dir = os.path.dirname(input_file)
        output_dir = os.path.join(input_dir, 'analysis_results')
    
    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)
    
    # 设置输出文件名
    if output_filename is None:
        base_name = os.path.basename(input_file)
        name_without_ext = os.path.splitext(base_name)[0]
        output_filename = f"{name_without_ext}_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    output_path = os.path.join(output_dir, output_filename)
    
    # 保存结果
    grouped.to_csv(output_path, index=False)
    
    print(f"分析完成，结果保存至: {output_path}")
    print(f"发现 {len(grouped)} 个不同的组合")
    
    if len(grouped) > 0:
        print(f"占比最高的是: {grouped.iloc[0][columns_to_group].tolist()} (占比 {grouped.iloc[0]['percentage']:.2f}%)")
    else:
        print("警告: 没有找到任何匹配的记录")
    
    return output_path

def main():
    parser = argparse.ArgumentParser(description='分析CSV文件，按指定列分组并计算占比')
    parser.add_argument('input_file', help='输入CSV文件路径')
    parser.add_argument('--columns', '-c', nargs='+', required=True, help='用于分组的列名列表')
    parser.add_argument('--output-dir', '-o', help='输出目录路径')
    parser.add_argument('--output-filename', '-f', help='输出文件名')
    
    args = parser.parse_args()
    
    analyze_csv(args.input_file, args.columns, args.output_dir, args.output_filename)

if __name__ == "__main__":
    main() 