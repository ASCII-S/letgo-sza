#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
单个CSV文件处理脚本
根据CSV文件中的Sig1pc列，在对应的汇编文件中查找指令，并将指令更新到Sig1Ins列
使用双指针优化算法提高处理效率
"""

import os
import argparse
import pandas as pd
import re
from tqdm import tqdm


def load_csv_file(file_path):
    """
    加载CSV文件到DataFrame
    
    Args:
        file_path (str): CSV文件路径
        
    Returns:
        pandas.DataFrame: 加载的CSV数据
    """
    try:
        return pd.read_csv(file_path)
    except Exception as e:
        raise Exception(f"加载CSV文件 {file_path} 失败: {str(e)}")


def load_asm_file(asm_file_path):
    """
    加载汇编文件，并按照PC值进行预处理
    
    Args:
        asm_file_path (str): 汇编文件路径
        
    Returns:
        list: 处理后的汇编指令列表，每个元素为(pc_value, instruction)
    """
    asm_instructions = []
    
    try:
        with open(asm_file_path, 'r') as f:
            for line in f:
                # 使用正则表达式匹配PC值和指令
                # 格式通常类似于: "4023c6:	f2 0f 10 04 c2    	movsd  (%rdx,%rax,8),%xmm0"
                pc_match = re.match(r'^\s*([a-f0-9]+):', line, re.IGNORECASE)
                if pc_match:
                    pc_value = pc_match.group(1).lower()
                    
                    # 尝试提取指令部分
                    instruction_match = re.search(r'[a-f0-9]+:\s+(?:[a-f0-9]{2}\s+)+\s*(.*)', line)
                    if instruction_match:
                        instruction = instruction_match.group(1).strip()
                    else:
                        # 如果上面的匹配失败，尝试更宽松的匹配
                        parts = line.strip().split('\t')
                        if len(parts) >= 3:
                            instruction = parts[-1].strip()
                        else:
                            continue
                            
                    asm_instructions.append((pc_value, instruction))
        
        return asm_instructions
    except Exception as e:
        raise Exception(f"加载汇编文件 {asm_file_path} 失败: {str(e)}")


def process_csv_file(csv_file_path, asm_dir, output_dir):
    """
    处理单个CSV文件，更新Sig1Ins列
    使用双指针算法优化处理效率
    
    Args:
        csv_file_path (str): 输入CSV文件路径
        asm_dir (str): 汇编文件目录
        output_dir (str): 输出目录
        
    Returns:
        str: 输出文件路径
    """
    # 加载CSV文件
    print(f"处理文件: {os.path.basename(csv_file_path)}")
    df = load_csv_file(csv_file_path)
    
    # 获取应用名
    app_name = os.path.splitext(os.path.basename(csv_file_path))[0]
    asm_file_path = os.path.join(asm_dir, f"{app_name}.asm")
    
    # 检查汇编文件是否存在
    if not os.path.exists(asm_file_path):
        raise FileNotFoundError(f"汇编文件不存在: {asm_file_path}")
    
    # 获取CSV中所有有效的Sig1pc值及其索引
    pc_values = []
    for idx, value in enumerate(df['Sig1pc']):
        if not pd.isna(value) and value != 'null':
            # 移除0x前缀
            clean_value = value.replace('0x', '').lower()
            pc_values.append((clean_value, idx))
    
    # 按PC值排序
    pc_values.sort(key=lambda x: x[0])
    
    print(f"Sig1pc有效值数量: {len(pc_values)}")
    print("加载汇编文件...")
    
    # 加载汇编文件
    asm_instructions = load_asm_file(asm_file_path)
    
    print(f"汇编指令数量: {len(asm_instructions)}")
    print("开始双指针匹配...")
    
    # 使用双指针算法匹配指令
    i, j = 0, 0  # i指向pc_values，j指向asm_instructions
    instruction_map = {}  # 用于存储匹配结果
    
    with tqdm(total=len(pc_values), desc=f"匹配处理 {app_name}") as pbar:
        while i < len(pc_values) and j < len(asm_instructions):
            csv_pc, idx = pc_values[i]
            asm_pc, instruction = asm_instructions[j]
            
            if csv_pc < asm_pc:
                # CSV中的PC值小于当前汇编行的PC值，继续检查下一个CSV的PC值
                i += 1
                pbar.update(1)
            elif csv_pc > asm_pc:
                # CSV中的PC值大于当前汇编行的PC值，继续检查下一个汇编行
                j += 1
            else:
                # 找到匹配，记录指令
                instruction_map[idx] = instruction
                i += 1
                pbar.update(1)
                # 不增加j，因为可能有多个相同PC值
    
    # 更新DataFrame中的Sig1Ins列
    different_count = 0
    for idx, instruction in instruction_map.items():
        # 检查原来的指令与新找到的指令是否不同
        old_instruction = df.at[idx, 'Sig1Ins']
        if pd.notna(old_instruction) and old_instruction != 'null' and old_instruction != instruction:
            different_count += 1
            print(f"指令不一致 [行 {idx}]:")
            print(f"  原指令: {old_instruction}")
            print(f"  新指令: {instruction}")
            print(f"  PC值: {df.at[idx, 'Sig1pc']}")
            print("---")
        
        # 更新指令
        df.at[idx, 'Sig1Ins'] = instruction
    
    if different_count > 0:
        print(f"共发现 {different_count} 个指令不一致")
    
    # 检查未匹配的PC值
    unmatched_count = len(pc_values) - len(instruction_map)
    if unmatched_count > 0:
        print(f"警告: 有 {unmatched_count} 个PC值未找到匹配指令")
        
        # 打印前10个未匹配的PC值作为示例
        unmatched_pcs = [pc for pc, idx in pc_values if idx not in instruction_map.keys()]
        print(f"未匹配的PC值示例(前10个): {unmatched_pcs[:10]}")
    
    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)
    
    # 保存处理后的CSV文件
    output_file_path = os.path.join(output_dir, f"{app_name}.csv")
    df.to_csv(output_file_path, index=False)
    
    print(f"处理完成，文件已保存到: {output_file_path}")
    return output_file_path


def main():
    # 参数解析
    parser = argparse.ArgumentParser(description="根据Sig1pc在汇编文件中查找指令并更新CSV")
    parser.add_argument("--input", type=str, help="输入CSV文件路径")
    parser.add_argument("--asm-dir", type=str, default="../asm", help="汇编文件目录路径")
    parser.add_argument("--output-dir", type=str, default="../CSV", help="输出目录路径")
    
    args = parser.parse_args()
    
    try:
        process_csv_file(args.input, args.asm_dir, args.output_dir)
    except Exception as e:
        print(f"Error: {str(e)}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main()) 