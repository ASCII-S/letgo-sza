#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批处理脚本
批量处理CSVraw文件夹中的所有CSV文件，根据Sig1pc列在对应汇编文件中查找指令，更新Sig1Ins列
"""

import os
import argparse
import glob
from tqdm import tqdm
from fix_ins_by_asm import process_csv_file


def process_all_csv_files(input_dir, asm_dir, output_dir):
    """
    处理指定目录下的所有CSV文件
    
    Args:
        input_dir (str): 输入CSV文件目录
        asm_dir (str): 汇编文件目录
        output_dir (str): 输出目录
        
    Returns:
        int: 成功处理的文件数量
    """
    # 获取所有CSV文件
    csv_files = glob.glob(os.path.join(input_dir, "*.csv"))
    
    if not csv_files:
        print(f"警告: 在 {input_dir} 中未找到CSV文件")
        return 0
    
    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)
    
    success_count = 0
    failed_files = []
    
    # 显示处理进度
    print(f"找到 {len(csv_files)} 个CSV文件")
    
    # 处理每个CSV文件
    for csv_file in tqdm(csv_files, desc="处理CSV文件"):
        try:
            process_csv_file(csv_file, asm_dir, output_dir)
            success_count += 1
        except Exception as e:
            failed_files.append((os.path.basename(csv_file), str(e)))
            print(f"处理文件 {os.path.basename(csv_file)} 失败: {str(e)}")
    
    # 汇总报告
    print("\n处理完成!")
    print(f"成功处理: {success_count}/{len(csv_files)} 文件")
    
    if failed_files:
        print("\n失败文件:")
        for file_name, error in failed_files:
            print(f"- {file_name}: {error}")
    
    return success_count


def main():
    # 参数解析
    parser = argparse.ArgumentParser(description="批量处理CSV文件，根据Sig1pc填充Sig1Ins列")
    parser.add_argument("--input-dir", type=str, default="../CSVraw", help="输入CSV文件目录")
    parser.add_argument("--asm-dir", type=str, default="../asm", help="汇编文件目录")
    parser.add_argument("--output-dir", type=str, default="../CSV", help="输出目录")
    
    args = parser.parse_args()
    
    # 处理所有CSV文件
    success_count = process_all_csv_files(args.input_dir, args.asm_dir, args.output_dir)
    
    return 0 if success_count > 0 else 1


if __name__ == "__main__":
    exit(main()) 