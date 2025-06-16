#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量分析多个CSV文件中的汇编指令，统计目标寄存器是整数寄存器和浮点寄存器的数量和占比
"""

import os
import glob
import pandas as pd
import argparse
from tqdm import tqdm
from analyze_reg_type import analyze_file, RESULT_TYPES, extract_benchmark_name

def batch_analyze(input_dir, output_dir, target_column='Sig1Ins', file_pattern='*.csv', result_types=RESULT_TYPES):
    """
    批量分析目录中的所有CSV文件
    
    Args:
        input_dir (str): 输入目录路径
        output_dir (str): 输出目录路径
        target_column (str): 要分析的列名，默认为'Sig1Ins'
        file_pattern (str): 文件匹配模式，默认为'*.csv'
        result_types (list): 需要筛选的结果类型列表，默认为RESULT_TYPES
        
    Returns:
        pd.DataFrame: 合并后的分析结果
    """
    # 获取所有匹配的CSV文件
    csv_files = glob.glob(os.path.join(input_dir, file_pattern))
    
    if not csv_files:
        print(f"警告：在 {input_dir} 中没有找到匹配 {file_pattern} 的文件")
        return None
    
    print(f"找到 {len(csv_files)} 个CSV文件待分析")
    print(f"将筛选结果类型: {result_types}")
    
    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)
    
    # 创建summary子目录
    summary_dir = os.path.join(output_dir, "summary")
    os.makedirs(summary_dir, exist_ok=True)
    
    # 创建inspect子目录
    inspect_dir = os.path.join(output_dir, "inspect")
    os.makedirs(inspect_dir, exist_ok=True)
    
    # 存储所有文件的分析结果
    all_results = []
    all_detailed_results = []
    all_reg_analysis_files = []  # 存储所有reg_analysis结果文件的信息
    all_inspect_files = []       # 存储所有检测文件的信息
    all_raw_results = []         # 存储带result列的原始分析结果
    
    # 分析每个文件
    for csv_file in tqdm(csv_files, desc="分析进度"):
        file_name = os.path.basename(csv_file).split('.')[0]
        
        try:
            # 读取原始CSV文件以获取result列
            try:
                original_df = pd.read_csv(csv_file)
                has_result_column = 'result' in original_df.columns
            except:
                has_result_column = False
            
            # 分析单个文件
            result_df, file_info = analyze_file(csv_file, output_dir, target_column, result_types)
            
            if result_df is not None and file_info is not None:
                # 添加文件名和benchmark列
                result_df['文件名'] = file_name
                result_df['benchmark'] = file_info['benchmark']
                all_results.append(result_df)
                all_reg_analysis_files.append(file_info)
                
                # 收集检测文件信息
                if 'inspect_file' in file_info and os.path.exists(file_info['inspect_file']):
                    all_inspect_files.append(file_info['inspect_file'])
                
                # 读取详细结果文件
                detailed_file = os.path.join(output_dir, f"{file_name}_detailed_reg_analysis.csv")
                if os.path.exists(detailed_file):
                    detailed_df = pd.read_csv(detailed_file)
                    detailed_df['文件名'] = file_name
                    detailed_df['benchmark'] = file_info['benchmark']
                    all_detailed_results.append(detailed_df)
                
                # 读取检测文件以获取原始数据（包含result列）
                if has_result_column:
                    inspect_file = os.path.join(inspect_dir, f"{file_name}_inspect.csv")
                    if os.path.exists(inspect_file):
                        raw_df = pd.read_csv(inspect_file)
                        raw_df['文件名'] = file_name
                        raw_df['benchmark'] = file_info['benchmark']
                        all_raw_results.append(raw_df)
        except Exception as e:
            print(f"处理文件 {csv_file} 时出错: {e}")
            continue
    
    if not all_results:
        print("没有成功分析任何文件")
        return None
    
    # 合并所有结果
    combined_results = pd.concat(all_results, ignore_index=True)
    
    # 按寄存器类型汇总统计
    summary = combined_results.groupby('寄存器类型').agg({
        '数量': 'sum'
    }).reset_index()
    
    # 计算总数和百分比
    total = summary['数量'].sum()
    summary['百分比'] = (summary['数量'] / total * 100).round(2)
    
    # 生成结果类型字符串用于文件名
    result_types_str = '_'.join(result_types) if len(result_types) <= 3 else f"{len(result_types)}种结果类型"
    
    # 保存汇总结果到summary子目录
    summary_file = os.path.join(summary_dir, f"summary_reg_analysis_{result_types_str}.csv")
    summary.to_csv(summary_file, index=False, encoding='utf-8')
    
    print(f"汇总分析完成，结果已保存到 {summary_file}")
    
    # 保存详细汇总结果到summary子目录
    if all_detailed_results:
        combined_detailed = pd.concat(all_detailed_results, ignore_index=True)
        
        # 按寄存器汇总统计
        detailed_summary = combined_detailed.groupby(['目标寄存器', '类型']).agg({
            '数量': 'sum'
        }).reset_index()
        
        # 计算总数和百分比
        detailed_summary['百分比'] = (detailed_summary['数量'] / detailed_summary['数量'].sum() * 100).round(2)
        
        # 按数量降序排序
        detailed_summary = detailed_summary.sort_values('数量', ascending=False)
        
        # 保存详细汇总结果到summary子目录
        detailed_summary_file = os.path.join(summary_dir, f"detailed_summary_reg_analysis_{result_types_str}.csv")
        detailed_summary.to_csv(detailed_summary_file, index=False, encoding='utf-8')
        
        print(f"详细汇总分析完成，结果已保存到 {detailed_summary_file}")
    
    # 汇总所有单文件reg_analysis结果，创建包含benchmark列的总表
    all_benchmark_results = []
    
    # 读取每个reg_analysis文件并添加benchmark信息
    for file_info in all_reg_analysis_files:
        try:
            # 读取reg_analysis文件
            reg_analysis_file = file_info['output_file']
            if os.path.exists(reg_analysis_file):
                df = pd.read_csv(reg_analysis_file)
                
                # 添加benchmark列
                df['benchmark'] = file_info['benchmark']
                
                all_benchmark_results.append(df)
        except Exception as e:
            print(f"汇总文件 {reg_analysis_file} 时出错: {e}")
            continue
    
    if all_benchmark_results:
        # 合并所有reg_analysis结果
        combined_benchmark_results = pd.concat(all_benchmark_results, ignore_index=True)
        
        # 保存包含benchmark列的汇总结果到summary子目录
        benchmark_summary_file = os.path.join(summary_dir, f"all_benchmarks_reg_analysis_{result_types_str}.csv")
        combined_benchmark_results.to_csv(benchmark_summary_file, index=False, encoding='utf-8')
        
        print(f"所有基准测试汇总分析完成，结果已保存到 {benchmark_summary_file}")
    
    # 按寄存器类型和结果类型生成分类统计
    if all_raw_results:
        combined_raw = pd.concat(all_raw_results, ignore_index=True)
        
        # 确保有寄存器类型和result列
        if '寄存器类型判断' in combined_raw.columns and 'result' in combined_raw.columns:
            # 按照寄存器类型和result进行分组统计
            reg_result_stats = combined_raw.groupby(['benchmark', '寄存器类型判断', 'result']).size().reset_index(name='数量')
            
            # 计算每个基准测试+寄存器类型内不同result的比例
            reg_result_stats['benchmark_reg'] = reg_result_stats['benchmark'] + '_' + reg_result_stats['寄存器类型判断']
            reg_result_pivot = reg_result_stats.pivot_table(
                index=['benchmark', '寄存器类型判断'], 
                columns='result', 
                values='数量',
                aggfunc='sum',
                fill_value=0
            ).reset_index()
            
            # 计算总数
            reg_result_pivot['总数'] = reg_result_pivot.iloc[:, 2:].sum(axis=1)
            
            # 计算每种结果类型的百分比
            for result_type in reg_result_pivot.columns[2:-1]:  # 跳过benchmark、寄存器类型和总数列
                reg_result_pivot[f'{result_type}_百分比'] = (reg_result_pivot[result_type] / reg_result_pivot['总数'] * 100).round(2)
            
            # 保存按寄存器类型和结果类型分组的统计结果
            reg_result_file = os.path.join(summary_dir, f"reg_type_result_analysis_{result_types_str}.csv")
            reg_result_pivot.to_csv(reg_result_file, index=False, encoding='utf-8')
            
            print(f"按寄存器类型和结果类型的分析完成，结果已保存到 {reg_result_file}")
            
            # 生成全局汇总（不区分benchmark）
            global_reg_result = combined_raw.groupby(['寄存器类型判断', 'result']).size().reset_index(name='数量')
            global_pivot = global_reg_result.pivot_table(
                index='寄存器类型判断',
                columns='result',
                values='数量',
                aggfunc='sum',
                fill_value=0
            ).reset_index()
            
            # 计算总数和百分比
            global_pivot['总数'] = global_pivot.iloc[:, 1:].sum(axis=1)
            for result_type in global_pivot.columns[1:-1]:
                global_pivot[f'{result_type}_百分比'] = (global_pivot[result_type] / global_pivot['总数'] * 100).round(2)
            
            # 保存全局汇总结果
            global_file = os.path.join(summary_dir, f"global_reg_type_result_analysis_{result_types_str}.csv")
            global_pivot.to_csv(global_file, index=False, encoding='utf-8')
            
            print(f"全局寄存器类型和结果类型分析完成，结果已保存到 {global_file}")
    
    # 汇总所有检测文件
    if all_inspect_files:
        all_inspect_results = []
        
        # 读取每个inspect文件
        for inspect_file in all_inspect_files:
            try:
                df = pd.read_csv(inspect_file)
                # 添加文件名信息
                file_name = os.path.basename(inspect_file).split('_inspect.csv')[0]
                df['检测文件'] = file_name
                all_inspect_results.append(df)
            except Exception as e:
                print(f"读取检测文件 {inspect_file} 时出错: {e}")
                continue
        
        if all_inspect_results:
            # 合并所有检测结果
            combined_inspect_results = pd.concat(all_inspect_results, ignore_index=True)
            
            # 保存汇总检测结果到summary子目录
            inspect_summary_file = os.path.join(summary_dir, f"all_inspect_results_{result_types_str}.csv")
            combined_inspect_results.to_csv(inspect_summary_file, index=False, encoding='utf-8')
            
            print(f"所有检测结果汇总完成，结果已保存到 {inspect_summary_file}")
    
    return summary

def main():
    """主函数：解析命令行参数并执行批量分析"""
    parser = argparse.ArgumentParser(description='批量分析CSV文件中的汇编指令，统计目标寄存器类型')
    parser.add_argument('-i', '--input', default='../CSV',
                        help='输入目录路径，默认为../CSV')
    parser.add_argument('-o', '--output', default='./results',
                        help='输出目录路径，默认为./results')
    parser.add_argument('-c', '--column', default='Sig1Ins',
                        help='要分析的列名，默认为Sig1Ins')
    parser.add_argument('-p', '--pattern', default='*.csv',
                        help='文件匹配模式，默认为*.csv')
    parser.add_argument('-r', '--result-types', nargs='+', default=RESULT_TYPES,
                        help=f'需要筛选的结果类型，默认为{RESULT_TYPES}')
    
    args = parser.parse_args()
    
    batch_analyze(args.input, args.output, args.column, args.pattern, args.result_types)

if __name__ == '__main__':
    main() 