#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import numpy as np
import os
import argparse

def parse_polybench_output(file_path, array_name=None):
    """
    解析PolyBench输出文件，提取数值数组
    
    参数:
        file_path (str): 输出文件的路径
        array_name (str, optional): 要提取的数组名称，如果为None则提取第一个数组
        
    返回:
        numpy.ndarray: 提取的数值数组
    """
    with open(file_path, 'r') as f:
        content = f.read()
    
    # 匹配所有数组
    pattern = r"begin dump: (\w+)([\s\S]*?)end\s+dump: \1"
    matches = re.findall(pattern, content)
    
    if not matches:
        raise ValueError(f"在文件 {file_path} 中没有找到数组数据")
    
    # 如果指定了数组名称，则提取该数组
    if array_name:
        for name, data in matches:
            if name == array_name:
                break
        else:
            raise ValueError(f"在文件 {file_path} 中没有找到名为 {array_name} 的数组")
    else:
        # 默认提取第一个数组
        name, data = matches[0]
    
    # 处理数据
    data = data.strip()
    # 将所有空白字符替换为单个空格
    data = re.sub(r'\s+', ' ', data)
    # 分割成浮点数列表
    values = [float(x) for x in data.split()]
    
    return np.array(values)

def validate_output(golden_file, output_file, tolerance=0.05, relative_error=True, array_name=None):
    """
    验证输出结果是否在可接受范围内
    
    参数:
        golden_file (str): 参考输出文件路径
        output_file (str): 实验输出文件路径
        tolerance (float): 可接受的误差范围，默认为5%
        relative_error (bool): 是否使用相对误差，False则使用绝对误差
        array_name (str, optional): 要验证的数组名称，默认为None(提取第一个数组)
        
    返回:
        tuple: (是否通过验证(bool), 最大绝对误差(float), 最大相对误差(float), 参考值(float), 实验值(float), 调试消息(str))
    """
    # 解析文件
    try:
        ref_data = parse_polybench_output(golden_file, array_name)
        out_data = parse_polybench_output(output_file, array_name)
    except Exception as e:
        debug_msg = f"解析错误: {str(e)}"
        return False, float('inf'), float('inf'), None, None, debug_msg
    
    # 检查数组大小是否一致
    if ref_data.size != out_data.size:
        debug_msg = f"数组大小不一致: 参考数组大小={ref_data.size}, 输出数组大小={out_data.size}"
        return False, float('inf'), float('inf'), None, None, debug_msg
    
    # 计算绝对误差
    abs_errors = np.abs(ref_data - out_data)
    max_abs_error = np.max(abs_errors)
    abs_error_idx = np.argmax(abs_errors)
    
    # 计算相对误差
    mask = ref_data != 0
    rel_errors = np.zeros_like(ref_data)
    rel_errors[mask] = np.abs((ref_data[mask] - out_data[mask]) / ref_data[mask])
    max_rel_error = np.max(rel_errors)
    rel_error_idx = np.argmax(rel_errors)
    
    # 获取误差对应的原始值和实验值
    # 使用用于判断是否通过的误差类型来选择索引
    error_idx = rel_error_idx if relative_error else abs_error_idx
    ref_value = ref_data[error_idx]
    out_value = out_data[error_idx]
    
    # 计算超出容差的错误数量
    if relative_error:
        error_count = np.sum(rel_errors > tolerance)
        errors_used = rel_errors
    else:
        error_count = np.sum(abs_errors > tolerance)
        errors_used = abs_errors
    
    # 判断是否通过验证
    passed = error_count == 0
    
    # 创建调试消息
    if passed:
        debug_msg = f"验证通过: 使用{'相对' if relative_error else '绝对'}误差，最大绝对误差={max_abs_error:.6f}，最大相对误差={max_rel_error:.6f}"
    else:
        debug_msg = f"验证失败: {error_count}个值超出{'相对' if relative_error else '绝对'}误差容差({tolerance:.6f})，最大绝对误差={max_abs_error:.6f}，最大相对误差={max_rel_error:.6f}，位置={error_idx}"
    
    return passed, max_abs_error, max_rel_error, ref_value, out_value, debug_msg

def compare_outputs(golden_output_path, this_output_path, tolerance=0.05, relative_error=True, array_name=None):
    """
    比较PolyBench应用输出是否在容差范围内，用于集成到SDC判断框架
    
    参数:
        golden_output_path (str): 黄金参考输出文件路径
        this_output_path (str): 实验输出文件路径
        tolerance (float): 允许的误差范围，默认为5%
        relative_error (bool): 是否使用相对误差，默认为True
        array_name (str, optional): 要验证的数组名称，默认为None(验证所有数组)
        
    返回:
        tuple: (状态码(int), 最大相对误差(float), 最大绝对误差(float), 参考值(float), 实验值(float), 调试消息(str))
        状态码：0表示在容差范围内，1表示超出容差
    """
    try:
        # 如果指定了数组名称，则只验证该数组
        if array_name:
            passed, max_abs_error, max_rel_error, ref_value, out_value, debug_msg = validate_output(
                golden_output_path, this_output_path, tolerance, relative_error, array_name
            )
            
            if not passed:
                print(f"is relative error: {relative_error}")
                print(f"Compare within tolerance: False (Array: {array_name})")
                print(f"最大绝对误差: {max_abs_error:.6f}")
                print(f"最大相对误差: {max_rel_error:.6f}")
                print(f"参考值: {ref_value}, 实验值: {out_value}")
                print(f"调试信息: {debug_msg}")
                return 1, max_rel_error, max_abs_error, ref_value, out_value, debug_msg
            
            print(f"Compare within tolerance: True (Array: {array_name})")
            print(f"调试信息: {debug_msg}")
            return 0, max_rel_error, max_abs_error, ref_value, out_value, debug_msg
        else:
            # 如果没有指定数组名称，则验证所有数组
            # 提取所有数组名称
            with open(golden_output_path, 'r') as f:
                content = f.read()
            
            pattern = r"begin dump: (\w+)"
            array_names = re.findall(pattern, content)
            
            if not array_names:
                print(f"Compare within tolerance: False (No arrays found)")
                return 1, 0.0, 0.0, None, None, "No arrays found"
                
            # 验证每个数组
            max_abs_error = 0.0
            max_rel_error = 0.0
            all_debug_msgs = []
            max_error_ref_value = None
            max_error_out_value = None
            error_debug_msg = ""
            
            for arr_name in array_names:
                passed, arr_max_abs_error, arr_max_rel_error, ref_value, out_value, debug_msg = validate_output(
                    golden_output_path, this_output_path, tolerance, relative_error, arr_name
                )
                
                all_debug_msgs.append(f"数组 {arr_name}: {debug_msg}")
                
                # 记录最大误差和对应的参考值和实验值
                if arr_max_abs_error > max_abs_error:
                    max_abs_error = arr_max_abs_error
                    # 如果是绝对误差，更新对应的ref_value和out_value
                    if not relative_error:
                        max_error_ref_value = ref_value
                        max_error_out_value = out_value
                        error_debug_msg = debug_msg
                        
                if arr_max_rel_error > max_rel_error:
                    max_rel_error = arr_max_rel_error
                    # 如果是相对误差，更新对应的ref_value和out_value
                    if relative_error:
                        max_error_ref_value = ref_value
                        max_error_out_value = out_value
                        error_debug_msg = debug_msg
                
                if not passed:
                    print(f"相对误差: {relative_error}")
                    print(f"Compare within tolerance: False (Array: {arr_name})")
                    print(f"最大绝对误差: {arr_max_abs_error:.6f}")
                    print(f"最大相对误差: {arr_max_rel_error:.6f}")
                    print(f"参考值: {ref_value}, 实验值: {out_value}")
                    print(f"调试信息: {debug_msg}")
                    return 1, arr_max_rel_error, arr_max_abs_error, ref_value, out_value, debug_msg
            
            # 所有数组都通过验证
            print(f"Compare within tolerance: True (All arrays)")
            print(f"调试信息汇总:\n" + "\n".join(all_debug_msgs))
            summary_debug_msg = "\n".join(all_debug_msgs)
            return 0, max_rel_error, max_abs_error, max_error_ref_value, max_error_out_value, summary_debug_msg
            
    except Exception as e:
        error_msg = f"Error: {str(e)}"
        print(f"Compare within tolerance: False ({error_msg})")
        return 1, 100.0, 0.0, None, None, error_msg

if __name__ == "__main__":
    # 示例：测试单个文件
    import sys
    
    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(description='验证PolyBench输出是否在容差范围内')
    parser.add_argument('golden_file', help='参考输出文件路径')
    parser.add_argument('output_file', help='实验输出文件路径')
    parser.add_argument('-t', '--tolerance', type=float, default=0.05, help='容差值，默认为0.05 (5%%)')
    parser.add_argument('-a', '--array', help='指定要验证的数组名称，默认验证所有数组')
    parser.add_argument('-r', '--relative', action='store_true', help='使用相对误差（默认）')
    parser.add_argument('-b', '--absolute', action='store_true', help='使用绝对误差')
    parser.add_argument('-v', '--verbose', action='store_true', help='显示详细输出')
    
    # 解析命令行参数
    args = parser.parse_args()
    
    # 检查文件是否存在
    if not os.path.exists(args.golden_file) or not os.path.exists(args.output_file):
        print(f"错误: 文件不存在 - {args.golden_file} 或 {args.output_file}")
        sys.exit(1)
    
    # 确定是使用相对误差还是绝对误差
    relative_error = not args.absolute
    
    # 使用compare_outputs进行比较
    if args.verbose:
        print("--------------------------------")
        print(f"比较文件: {args.golden_file} 和 {args.output_file}")
        print(f"容差: {args.tolerance}")
        print(f"数组: {args.array if args.array else '所有数组'}")
        print(f"使用{'相对' if relative_error else '绝对'}误差")
        print("--------------------------------")
    result = compare_outputs(
        args.golden_file, 
        args.output_file, 
        tolerance=args.tolerance,
        array_name=args.array,
        relative_error=relative_error
    )
    
    if args.verbose:
        print(f"结果: {'通过' if result[0] == 0 else '失败'}")
    
    sys.exit(result[0]) 