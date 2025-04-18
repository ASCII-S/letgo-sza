#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
此脚本用于将analyze_csv_Sig1Ins_batch.py生成的CSV文件转换为指定格式：
1. 只保留Sig1Ins列非null的行
2. 不展示percentage列
3. 新增一列判断Func和Sig1Func是否指向相同函数名（忽略格式差异）
4. 默认原位修改CSV文件
5. 默认处理analysis_results文件夹中的所有CSV文件
6. 可以统计不同Sig1Ins下FuncMatch的分布情况
"""

import os
import sys
import pandas as pd
import argparse
import glob


def transform_csv(input_file, output_file=None, in_place=True):
    """
    转换CSV文件为指定格式
    
    参数:
        input_file (str): 输入CSV文件路径
        output_file (str, optional): 输出CSV文件路径，默认为在输入文件名前添加"transformed_"
        in_place (bool, optional): 是否原位修改文件，默认为True
    
    返回:
        str: 输出文件的路径
    """
    try:
        # 读取CSV文件
        df = pd.read_csv(input_file)
        
        # 1. 只保留Sig1Ins列非null的行
        df = df[df['Sig1Ins'].notna() & (df['Sig1Ins'] != 'null')]
        
        # 2. 删除percentage列(如果存在)
        if 'percentage' in df.columns:
            df = df.drop('percentage', axis=1)
        
        # 3. 新增一列判断Func和Sig1Func是否指向相同函数名
        def compare_func_names(row):
            # 如果任一值为null，返回0
            if pd.isna(row['Func']) or pd.isna(row['Sig1Func']) or row['Func'] == 'null' or row['Sig1Func'] == 'null':
                return 0
                
            # 确保值是字符串类型
            func_str = str(row['Func'])
            sig1func_str = str(row['Sig1Func'])
            
            # 从Func中去除前缀"<"，并提取函数名部分
            if func_str.startswith('<'):
                func_str = func_str[1:]
                
            # 比较处理后的函数名
            return 1 if func_str == sig1func_str else 0
        
        # 添加新列"FuncMatch"表示两个函数名是否匹配
        df['FuncMatch'] = df.apply(compare_func_names, axis=1)
        
        # 设置输出文件路径
        if in_place:
            output_file = input_file
        elif output_file is None:
            dir_name = os.path.dirname(input_file)
            dir_name = os.path.join(dir_name, "transformed_csv")
            if not os.path.exists(dir_name):
                os.makedirs(dir_name)
            base_name = os.path.basename(input_file)
            output_file = os.path.join(dir_name, "transformed_"+base_name)
        
        # 保存到CSV文件
        df.to_csv(output_file, index=False)
        
        print(f"转换完成! 结果保存在: {output_file}")
        return output_file
        
    except Exception as e:
        print(f"处理文件时出现错误: {str(e)}")
        return None


def analyze_func_match_distribution(input_file, output_file=None, group_by_result=False):
    """
    分析不同Sig1Ins和result下Sig1Func和Func的匹配分布
    
    参数:
        input_file (str): 输入CSV文件路径
        output_file (str, optional): 输出CSV文件路径，默认为在输入文件名前添加"match_dist_"
        group_by_result (bool, optional): 是否按result列分组，默认为False
    
    返回:
        pandas.DataFrame: 包含匹配分布的DataFrame
    """
    try:
        # 读取CSV文件
        df = pd.read_csv(input_file)
        
        # 只保留Sig1Ins列非null的行
        df = df[df['Sig1Ins'].notna() & (df['Sig1Ins'] != 'null')]
        
        # 确保count列存在并为数值类型
        if 'count' not in df.columns:
            print(f"警告: {input_file} 中没有'count'列，将默认每行count为1")
            df['count'] = 1
        else:
            df['count'] = pd.to_numeric(df['count'], errors='coerce').fillna(1)
        
        # 确保FuncMatch列存在
        if 'FuncMatch' not in df.columns:
            print(f"警告: {input_file} 中没有'FuncMatch'列，将先计算FuncMatch")
            
            def compare_func_names(row):
                # 如果任一值为null，返回0
                if pd.isna(row['Func']) or pd.isna(row['Sig1Func']) or row['Func'] == 'null' or row['Sig1Func'] == 'null':
                    return 0
                    
                # 确保值是字符串类型
                func_str = str(row['Func'])
                sig1func_str = str(row['Sig1Func'])
                
                # 从Func中去除前缀"<"，并提取函数名部分
                if func_str.startswith('<'):
                    func_str = func_str[1:]
                    
                # 比较处理后的函数名
                return 1 if func_str == sig1func_str else 0
            
            # 添加新列"FuncMatch"表示两个函数名是否匹配
            df['FuncMatch'] = df.apply(compare_func_names, axis=1)
        
        # 定义分组字段
        groupby_cols = ['Sig1Ins']
        if group_by_result and 'result' in df.columns:
            groupby_cols.append('result')
        
        # 创建匹配计数列
        df['match_count'] = df['count'] * df['FuncMatch']
        df['not_match_count'] = df['count'] * (1 - df['FuncMatch'])
        
        # 按Sig1Ins (和可能的result)分组，计算FuncMatch和非FuncMatch的次数
        result_df = df.groupby(groupby_cols).agg({
            'match_count': 'sum', 
            'not_match_count': 'sum'
        }).reset_index()
        
        # 重命名列名
        result_df.rename(columns={
            'match_count': 'FuncMatchCount',
            'not_match_count': 'FuncNotMatchCount'
        }, inplace=True)
        
        # 设置输出文件路径,新建文件夹保存        
        if output_file is None:
            dir_name = os.path.dirname(input_file)
            dir_name = os.path.join(dir_name, "match_dist_analysis")
            if not os.path.exists(dir_name):
                os.makedirs(dir_name)
            base_name = os.path.basename(input_file)
            output_file = os.path.join(dir_name, "match_dist_"+base_name)
        
        # 保存到CSV文件
        result_df.to_csv(output_file, index=False)
        
        print(f"匹配分布分析完成! 结果保存在: {output_file}")
        return result_df
        
    except Exception as e:
        print(f"分析匹配分布时出现错误: {str(e)}")
        return None


def process_directory(dir_path, output_dir=None, in_place=True):
    """
    处理指定目录下的所有CSV文件
    
    参数:
        dir_path (str): 目录路径
        output_dir (str, optional): 输出目录路径，默认与输入目录相同
        in_place (bool, optional): 是否原位修改文件，默认为True
    
    返回:
        int: 成功处理的文件数量
    """
    if not os.path.isdir(dir_path):
        print(f"错误: {dir_path} 不是有效目录")
        return 0
    
    # 获取目录中所有的CSV文件
    csv_files = glob.glob(os.path.join(dir_path, "*.csv"))
    
    if not csv_files:
        print(f"警告: 在 {dir_path} 中未找到CSV文件")
        return 0
    
    success_count = 0
    
    for csv_file in csv_files:
        output_file = None
        
        # 如果指定了输出目录且不是原位修改
        if output_dir and not in_place:
            base_name = os.path.basename(csv_file)
            output_file = os.path.join(output_dir, base_name)
        
        # 处理CSV文件
        result = transform_csv(csv_file, output_file, in_place)
        
        if result:
            success_count += 1
    
    print(f"成功处理 {success_count}/{len(csv_files)} 个CSV文件")
    return success_count


def main():
    """
    主函数，解析命令行参数并调用转换函数
    """
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='将CSV文件转换为指定格式')
    parser.add_argument('--input', '-i', default='analysis_results',
                        help='输入CSV文件路径或目录路径，默认为"analysis_results"目录')
    parser.add_argument('--output', '-o',
                        help='输出CSV文件路径或目录路径')
    parser.add_argument('--in-place', '-p', action='store_true',
                        help='是否原位修改文件，直接覆盖输入文件')
    parser.add_argument('--analyze-match', '-a', action='store_true',
                        help='是否分析FuncMatch分布')
    parser.add_argument('--group-by-result', '-g', action='store_true',
                        help='是否按result列分组（仅在分析FuncMatch分布时有效）')
    
    args = parser.parse_args()
    
    input_path = args.input
    
    # 如果需要分析FuncMatch分布
    if args.analyze_match:
        if os.path.isfile(input_path):
            analyze_func_match_distribution(input_path, args.output, args.group_by_result)
        elif os.path.isdir(input_path):
            csv_files = glob.glob(os.path.join(input_path, "*.csv"))
            for csv_file in csv_files:
                output_file = None
                if args.output:
                    base_name = os.path.basename(csv_file)
                    output_file = os.path.join(args.output, "match_dist_"+base_name)
                analyze_func_match_distribution(csv_file, output_file, args.group_by_result)
        else:
            print(f"错误: {input_path} 不是有效的文件或目录")
            sys.exit(1)
    else:
        # 如果输入路径是目录，处理目录中的所有CSV文件
        if os.path.isdir(input_path):
            process_directory(input_path, args.output, args.in_place)
        # 如果输入路径是文件，处理单个文件
        elif os.path.isfile(input_path):
            transform_csv(input_path, args.output, args.in_place)
        else:
            print(f"错误: {input_path} 不是有效的文件或目录")
            sys.exit(1)


if __name__ == "__main__":
    main()
