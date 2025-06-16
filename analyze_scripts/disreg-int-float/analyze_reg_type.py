#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分析CSV文件中Sig1Ins列的汇编指令，统计目标寄存器是整数寄存器和浮点寄存器的数量和占比
"""

import os
import re
import pandas as pd
import argparse
from collections import Counter

# 定义整数寄存器和浮点寄存器的正则表达式模式
INT_REG_PATTERN = r'%(r[a-z0-9]+|e[a-z][a-z]|[a-z][a-z]|[a-z]h|[a-z]l)'
FLOAT_REG_PATTERN = r'%(xmm[0-9]+|ymm[0-9]+|zmm[0-9]+|st[0-9]?)'

# 定义需要筛选的结果类型
RESULT_TYPES = ['C-Masked', 'C-SDCs-Acceptable', 'C-SDCs-Unacceptable', 'C-SDC', 'Recrash']

# 全局变量定义，用于标记寄存器类型
REG_TYPE_INTEGER = "Integer"
REG_TYPE_FLOAT = "Float"
REG_TYPE_UNKNOWN = "Unknown"

def extract_destination_register(instruction):
    """
    从汇编指令中提取目标寄存器
    
    Args:
        instruction (str): 汇编指令，如 "movss (%rax),%xmm0" 或 "movsd %xmm0,(%rdx,%rax,8)"
        
    Returns:
        str: 目标寄存器名称，如 "xmm0"，如果没有找到则返回None
    """
    if pd.isna(instruction) or not instruction.strip():
        return None
    
    # 规范化指令，移除多余空格
    instruction = re.sub(r'\s+', ' ', instruction.strip())
    
    # 处理指令前缀(lock, rep等)
    prefixes = ['lock', 'rep', 'repne', 'repnz', 'repe', 'repz']
    for prefix in prefixes:
        if instruction.lower().startswith(prefix + ' '):
            # 去除前缀，分析剩余部分
            instruction = instruction[len(prefix):].strip()
            break
    
    # 提取操作码
    parts = instruction.split(None, 1)
    if len(parts) < 2:
        return None
    
    opcode = parts[0].lower()
    operands_str = parts[1].strip()
    
    # 过滤特定指令类型
    # 1. 比较和测试指令不改变操作数
    if opcode in ['cmp', 'test']:
        return None
        
    # 2. 控制流指令通常不改变寄存器值
    if opcode.startswith(('j', 'call', 'ret')):
        return None
    
    # 处理 AVX/AVX2 三操作数指令 (如 vaddpd %ymm0,%ymm1,%ymm2)
    if opcode.startswith('v'):
        # 匹配三个寄存器操作数的模式
        tri_op_match = re.match(r'%\w+\s*,\s*%\w+\s*,\s*%(\w+)', operands_str)
        if tri_op_match:
            return tri_op_match.group(1)
    
    # 处理单操作数指令
    if ',' not in operands_str:
        # 单操作数指令列表
        single_op_instructions = ['push', 'pop', 'inc', 'dec', 'not', 'neg', 'bswap', 'idiv', 'div', 'imul', 'mul']
        
        # 如果是已知的单操作数指令，且操作数是寄存器
        if any(opcode.startswith(op) for op in single_op_instructions):
            reg_match = re.match(r'%(\w+)', operands_str)
            if reg_match:
                return reg_match.group(1)
        return None
    
    # 处理 LEA 和类似具有复杂内存寻址的指令
    if opcode == 'lea':
        # 针对形如 lea (%rsi,%rdi,4),%r8 的指令
        # 匹配第二个操作数（目标寄存器）
        lea_match = re.search(r',\s*%(\w+)$', operands_str)
        if lea_match:
            return lea_match.group(1)
        return None
    
    # 处理内存操作指令
    # 对于目标是内存的指令，我们不关心
    if re.search(r',\s*\([^)]*\)\s*$', operands_str):
        return None  # 目标是内存，如 add %eax,(%rbx)
    
    # 处理标准的两操作数指令
    # 对于大多数两操作数指令，目标寄存器是第二个操作数
    # 例如: mov %eax,%ebx - 目标是ebx
    last_op_match = re.search(r',\s*%(\w+)\s*$', operands_str)
    if last_op_match:
        return last_op_match.group(1)
    
    # 处理特殊格式：源是内存，目标是寄存器
    # 例如: mov (%rax),%ebx - 目标是ebx
    mem_to_reg_match = re.search(r'\([^)]*\)\s*,\s*%(\w+)', operands_str)
    if mem_to_reg_match:
        return mem_to_reg_match.group(1)
    
    # 如果没有找到清晰的目标寄存器模式，返回None
    return None

def classify_register(reg):
    """
    将寄存器分类为整数寄存器或浮点寄存器
    
    Args:
        reg (str): 寄存器名称，如 "xmm0" 或 "rax"
        
    Returns:
        str: 寄存器类型 ("Integer" 或 "Float")，如果无法分类则返回 "Unknown"
    """
    if reg is None:
        return "Unknown"
    
    # 浮点寄存器
    if reg.startswith(('xmm', 'ymm', 'zmm', 'st')):
        return "Float"
    
    # 整数寄存器
    # 64位寄存器: rax, rbx, rcx, rdx, rsi, rdi, rbp, rsp, r8-r15
    # 32位寄存器: eax, ebx, ecx, edx, esi, edi, ebp, esp
    # 16位寄存器: ax, bx, cx, dx, si, di, bp, sp
    # 8位高位寄存器: ah, bh, ch, dh
    # 8位低位寄存器: al, bl, cl, dl, sil, dil, bpl, spl
    if (reg.startswith(('r', 'e')) or 
        reg in ['ax', 'bx', 'cx', 'dx', 'si', 'di', 'sp', 'bp'] or
        reg.endswith(('h', 'l')) or
        any(reg == f'r{i}' for i in range(8, 16))):
        return "Integer"
    
    return "Unknown"

def extract_benchmark_name(file_path):
    """
    从文件路径中提取基准测试名称
    
    Args:
        file_path (str): 文件路径，如 "../CSV/2mm.csv"
        
    Returns:
        str: 基准测试名称，如 "2mm"
    """
    # 获取文件名（不含路径和扩展名）
    file_name = os.path.basename(file_path).split('.')[0]
    
    # 提取基准测试名称（去除前缀log_等）
    benchmark = re.sub(r'^log_', '', file_name)
    
    return benchmark

def analyze_file(input_file, output_dir, target_column='Sig1Ins', result_types=RESULT_TYPES):
    """
    分析CSV文件中的目标列，统计目标寄存器类型
    
    Args:
        input_file (str): 输入CSV文件路径
        output_dir (str): 输出目录路径
        target_column (str): 要分析的列名，默认为'Sig1Ins'
        result_types (list): 需要筛选的结果类型列表，默认为RESULT_TYPES
        
    Returns:
        tuple: (分析结果的DataFrame, 文件信息字典)
    """
    # 检查文件是否存在
    if not os.path.exists(input_file):
        print(f"错误：文件 {input_file} 不存在")
        return None, None
    
    # 读取CSV文件
    try:
        df = pd.read_csv(input_file)
    except Exception as e:
        print(f"读取文件 {input_file} 时出错: {e}")
        return None, None
    
    # 检查目标列是否存在
    if target_column not in df.columns:
        print(f"错误：列 '{target_column}' 在文件 {input_file} 中不存在")
        return None, None
    
    # 检查result列是否存在
    if 'result' not in df.columns:
        print(f"警告：列 'result' 在文件 {input_file} 中不存在，将不进行结果类型筛选")
    else:
        # 筛选指定的结果类型
        original_count = len(df)
        df = df[df['result'].isin(result_types)]
        filtered_count = len(df)
        print(f"筛选结果类型 {result_types}，从 {original_count} 行数据中保留 {filtered_count} 行 ({filtered_count/original_count*100:.2f}%)")
        
        if filtered_count == 0:
            print(f"警告：筛选后没有剩余数据，请检查结果类型是否正确")
            return None, None
    
    # 提取目标寄存器并分类
    df['目标寄存器'] = df[target_column].apply(extract_destination_register)
    df['寄存器类型'] = df['目标寄存器'].apply(classify_register)
    
    # 创建检测CSV数据
    # 先复制必要的列
    necessary_columns = ['input_file', target_column, 'result'] if 'input_file' in df.columns and 'result' in df.columns else \
                        ['input_file', target_column] if 'input_file' in df.columns else \
                        [target_column]
    
    inspect_df = df[necessary_columns].copy()
    # 添加寄存器判断结果
    inspect_df['提取的目标寄存器'] = df['目标寄存器']
    inspect_df['寄存器类型判断'] = df['寄存器类型']
    
    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)
    
    # 创建检测目录
    inspect_dir = os.path.join(output_dir, "inspect")
    os.makedirs(inspect_dir, exist_ok=True)
    
    # 保存检测结果
    file_name = os.path.basename(input_file).split('.')[0]
    inspect_file = os.path.join(inspect_dir, f"{file_name}_inspect.csv")
    inspect_df.to_csv(inspect_file, index=False, encoding='utf-8')
    
    print(f"检测文件已保存到 {inspect_file}，用于验证寄存器判断的正确性")
    
    # 统计各类型寄存器的数量
    reg_type_counts = df['寄存器类型'].value_counts()
    total_count = len(df)
    
    # 计算百分比
    reg_type_percentages = (reg_type_counts / total_count * 100).round(2)
    
    # 合并结果
    result_df = pd.DataFrame({
        '寄存器类型': reg_type_counts.index,
        '数量': reg_type_counts.values,
        '百分比': reg_type_percentages.values
    })
    
    # 获取基准测试名称
    benchmark = extract_benchmark_name(input_file)
    
    # 保存结果
    output_file = os.path.join(output_dir, f"{file_name}_reg_analysis.csv")
    result_df.to_csv(output_file, index=False, encoding='utf-8')
    
    print(f"分析完成，结果已保存到 {output_file}")
    
    # 返回更详细的分析结果，包括每个寄存器的具体统计
    detailed_counts = df['目标寄存器'].value_counts()
    detailed_df = pd.DataFrame({
        '目标寄存器': detailed_counts.index,
        '数量': detailed_counts.values,
        '百分比': (detailed_counts / total_count * 100).round(2),
        '类型': [classify_register(reg) for reg in detailed_counts.index]
    })
    
    detailed_output_file = os.path.join(output_dir, f"{file_name}_detailed_reg_analysis.csv")
    detailed_df.to_csv(detailed_output_file, index=False, encoding='utf-8')
    
    print(f"详细分析结果已保存到 {detailed_output_file}")
    
    # 返回文件信息字典，用于批处理脚本汇总
    file_info = {
        'benchmark': benchmark,
        'file_name': file_name,
        'output_file': output_file,
        'detailed_output_file': detailed_output_file,
        'inspect_file': inspect_file
    }
    
    return result_df, file_info

def main():
    """主函数：解析命令行参数并执行分析"""
    parser = argparse.ArgumentParser(description='分析CSV文件中的汇编指令，统计目标寄存器类型')
    parser.add_argument('-i', '--input', default='../CSV/sample.csv',
                        help='输入CSV文件路径，默认为../CSV/sample.csv')
    parser.add_argument('-o', '--output', default='./results',
                        help='输出目录路径，默认为./results')
    parser.add_argument('-c', '--column', default='Sig1Ins',
                        help='要分析的列名，默认为Sig1Ins')
    parser.add_argument('-r', '--result-types', nargs='+', default=RESULT_TYPES,
                        help=f'需要筛选的结果类型，默认为{RESULT_TYPES}')
    parser.add_argument('-t', '--test', action='store_true',
                        help='运行测试函数而不是主分析功能')
    
    args = parser.parse_args()
    
    if args.test:
        test_extract_and_classify()
    else:
        analyze_file(args.input, args.output, args.column, args.result_types)

def test_extract_and_classify():
    """测试函数：验证提取目标寄存器和分类功能"""
    test_instructions = [
        # 基本的数据移动指令
        "movss (%rax),%xmm0",         # 浮点寄存器目标
        "movsd %xmm0,(%rdx,%rax,8)",  # 目标是内存，应返回None
        "movq %rax,%rbx",             # 整数寄存器目标
        "movapd %xmm3,%xmm4",         # 浮点寄存器目标
        
        # 算术指令
        "add $1,%eax",                # 整数寄存器目标
        "sub %ebx,%ecx",              # 整数寄存器目标
        "addss %xmm1,%xmm2",          # 浮点寄存器目标
        "imul %r10,%r11",             # 整数寄存器目标
        
        # 特殊指令
        "lea (%rsi,%rdi,4),%r8",      # 整数寄存器目标
        "lea 8(%rsp),%rbp",           # 整数寄存器目标
        "push %rax",                  # 单操作数指令，目标是rax
        "pop %rbx",                   # 单操作数指令，目标是rbx
        "inc %edx",                   # 单操作数指令，目标是edx
        
        # 比较和控制指令
        "cmp %eax,%ebx",              # 比较指令，无目标寄存器
        "test %al,%bl",               # 比较指令，无目标寄存器
        "je label",                   # 跳转指令，无目标寄存器
        "jmp label",                  # 跳转指令，无目标寄存器
        
        # AVX/SIMD指令
        "vaddpd %ymm0,%ymm1,%ymm2",   # AVX指令，目标是ymm2
        "vpaddq %xmm1,%xmm2,%xmm0",   # AVX指令，目标是xmm0
        "vfmadd231pd %ymm3,%ymm4,%ymm5", # FMA指令，目标是ymm5
        
        # 带多个空格或特殊格式的指令
        "mov    %eax, %ebx",          # 多空格，目标是ebx
        "addl   $0x1,  %ecx",         # 多空格，目标是ecx
        
        # 复杂内存寻址
        "movq (%rbx,%rcx,8),%rdx",    # 复杂内存寻址读取，目标是rdx
        "movl %eax,(%ebx,%ecx,4)",    # 复杂内存寻址写入，无寄存器目标
        "lea 4(%rax,%rbx,8),%rcx",    # 复杂内存寻址+偏移，目标是rcx
        
        # 带前缀的内存操作
        "lock addl $0x1,(%rsp)",      # 带前缀，目标是内存，应返回None
        "lock xadd %eax,(%rbx)",      # 带前缀，目标是内存，应返回None
        "rep movsq",                  # 带前缀，无确定目标寄存器，应返回None
        
        # 其他特殊情况
        "xchg %eax,%ebx",             # 交换指令，有两个目标，但我们只返回ebx
        "bswap %edx",                 # 单操作数指令，目标是edx
        "cmovne %eax,%ebx",           # 条件移动，目标是ebx
        
        # 边界情况
        "mov  ",                      # 不完整指令
        ""                            # 空指令
    ]
    
    expected_results = [
        ("xmm0", "Float"),
        (None, "Unknown"),
        ("rbx", "Integer"),
        ("xmm4", "Float"),
        
        ("eax", "Integer"),
        ("ecx", "Integer"),
        ("xmm2", "Float"),
        ("r11", "Integer"),
        
        ("r8", "Integer"),
        ("rbp", "Integer"),
        ("rax", "Integer"),
        ("rbx", "Integer"),
        ("edx", "Integer"),
        
        (None, "Unknown"),
        (None, "Unknown"),
        (None, "Unknown"),
        (None, "Unknown"),
        
        ("ymm2", "Float"),
        ("xmm0", "Float"),
        ("ymm5", "Float"),
        
        ("ebx", "Integer"),
        ("ecx", "Integer"),
        
        ("rdx", "Integer"),
        (None, "Unknown"),
        ("rcx", "Integer"),
        
        (None, "Unknown"),
        (None, "Unknown"),
        (None, "Unknown"),
        
        ("ebx", "Integer"),
        ("edx", "Integer"),
        ("ebx", "Integer"),
        
        (None, "Unknown"),
        (None, "Unknown")
    ]
    
    print("\n测试目标寄存器提取和分类功能:")
    print("-" * 80)
    print(f"{'汇编指令':<40} {'提取的目标寄存器':<15} {'类型':<10} {'结果':<10}")
    print("-" * 80)
    
    total_tests = len(test_instructions)
    passed_tests = 0
    failed_tests = []
    
    for i, instruction in enumerate(test_instructions):
        reg = extract_destination_register(instruction)
        reg_type = classify_register(reg)
        
        expected_reg, expected_type = expected_results[i]
        result = "✓" if reg == expected_reg and reg_type == expected_type else "✗"
        
        if result == "✓":
            passed_tests += 1
        else:
            failed_tests.append((instruction, reg, expected_reg))
        
        print(f"{instruction:<40} {reg if reg else 'None':<15} {reg_type:<10} {result}")
    
    print("-" * 80)
    print(f"测试结果: {passed_tests}/{total_tests} 通过 ({passed_tests/total_tests*100:.1f}%)")
    
    if failed_tests:
        print("\n失败的测试用例:")
        for instr, actual, expected in failed_tests:
            print(f"指令: {instr}")
            print(f"  实际提取: {actual}")
            print(f"  预期结果: {expected}")
            print()
    
    return passed_tests == total_tests

if __name__ == '__main__':
    main() 