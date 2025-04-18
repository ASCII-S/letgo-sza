#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
此脚本用于批量分析CSV文件夹下的所有CSV文件
通过对每个文件应用相同的分组逻辑，生成分析结果
支持通过命令行参数指定CSV文件夹路径
"""

import os
import sys
import glob
import argparse
from analyze_csv_Sig1Ins import analyze_csv


def main():
    """
    批量处理CSV文件夹下的所有CSV文件的主函数
    对每个文件指定要分组的列为 Sig1Ins, Func, result, ErrSpd_Inj
    支持通过命令行参数指定CSV文件夹路径
    """
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='批量分析CSV文件，按指定列分组并计算占比')
    parser.add_argument('--csv-folder', '-f', 
                        help='CSV文件夹路径，默认为脚本目录下的./CSV')
    args = parser.parse_args()
    
    # 获取当前脚本所在目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 设置CSV文件夹路径，优先使用命令行参数指定的路径
    if args.csv_folder:
        csv_folder = args.csv_folder
    else:
        csv_folder = os.path.join(current_dir, '../CSV')
    
    # 检查CSV文件夹是否存在
    if not os.path.exists(csv_folder):
        print(f"错误: CSV文件夹 {csv_folder} 不存在")
        sys.exit(1)
    
    print(f"使用CSV文件夹路径: {csv_folder}")
    
    # 设置输出目录
    output_dir = os.path.join(current_dir, 'analysis_results')
    
    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)
    
    # 指定需要分组的列
    columns_to_group = ['Sig1Ins','Sig1Func',  'Func', 'result', 'ErrSpd_Inj']
    
    # 获取CSV文件夹下所有的CSV文件
    csv_files = glob.glob(os.path.join(csv_folder, '*.csv'))
    
    if not csv_files:
        print(f"错误: 在 {csv_folder} 中没有找到CSV文件")
        # print_usage()
        sys.exit(1)
    
    print(f"发现 {len(csv_files)} 个CSV文件需要处理")
    
    # 依次处理每个CSV文件
    for csv_file in csv_files:
        # 获取文件名（不含扩展名）
        file_name = os.path.basename(csv_file)
        file_name_without_ext = os.path.splitext(file_name)[0]
        
        # 设置输出文件名
        output_filename = f"{file_name_without_ext}_Sig1Ins_Func_result_ErrSpd_Inj_patterns.csv"
        
        print(f"\n开始处理文件: {file_name}")
        
        # 调用分析函数
        try:
            output_path = analyze_csv(
                input_file=csv_file,
                columns_to_group=columns_to_group,
                output_dir=output_dir,
                output_filename=output_filename
            )
            print(f"文件 {file_name} 分析完成! 结果保存在: {output_path}")
        except Exception as e:
            print(f"处理文件 {file_name} 时出现错误: {str(e)}")
            # 继续处理下一个文件，而不是终止程序
            continue
    
    print("\n所有CSV文件处理完毕!")

if __name__ == "__main__":
    main() 