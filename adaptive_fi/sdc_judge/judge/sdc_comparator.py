"""
SDC比较器模块

从sdcjudger.py重构的SDC判定逻辑，去除configure依赖，统一接口。
"""

import os
import sys
import filecmp
import numpy as np
import pandas as pd
import re
from typing import Tuple
from dataclasses import dataclass


# 默认比较结果字符串
CMP_STR = "Compare within tolerance: "


@dataclass
class CompareResult:
    """比较结果"""

    is_match: bool  # 是否匹配（在容差内）
    message: str  # 结果消息
    tolerance: float  # 使用的容差
    method: str  # 比较方法


def strong_compare(test_output: str, golden_output: str) -> Tuple[bool, str]:
    """
    二进制完全比较

    Args:
        test_output: 测试输出文件路径
        golden_output: Golden输出文件路径

    Returns:
        (is_match, message) 元组
    """
    is_match = filecmp.cmp(test_output, golden_output, shallow=False)
    message = f"{CMP_STR}{'True' if is_match else 'False'}"
    return is_match, message


def hotspot_compare(test_output: str, golden_output: str, tolerance: float = 1e-6) -> Tuple[bool, str]:
    """
    Hotspot CSV格式比较

    比较两个文件的数据，检查是否在容差范围内

    Args:
        test_output: 测试输出文件路径
        golden_output: Golden输出文件路径
        tolerance: 允许的误差范围

    Returns:
        (is_match, message) 元组
    """
    try:
        # 读取数据
        try:
            test_data = pd.read_csv(test_output, sep="\t", header=None, names=["Index", "Value"])
            golden_data = pd.read_csv(golden_output, sep="\t", header=None, names=["Index", "Value"])
        except Exception:
            return False, f"{CMP_STR}False (application generate no output)"

        # 检查结构是否匹配
        if test_data.shape != golden_data.shape:
            return False, f"{CMP_STR}False (Shape mismatch)"

        # 逐行比较
        for index, (test_val, golden_val) in enumerate(zip(test_data["Value"], golden_data["Value"])):
            if abs(test_val - golden_val) > tolerance:
                return False, f"{CMP_STR}False"

        return True, f"{CMP_STR}True"

    except Exception as e:
        return False, f"{CMP_STR}False (Error occurred: {e})"


def miniMD_compare(test_output: str, golden_output: str, tolerance: float = 1e-6) -> Tuple[bool, str]:
    """
    miniMD输出比较

    比较 "# Timestep T U P Time" 后两行的数据（排除Time列）

    Args:
        test_output: 测试输出文件路径
        golden_output: Golden输出文件路径
        tolerance: 允许的误差范围

    Returns:
        (is_match, message) 元组
    """
    try:
        # 读取两个文件
        with open(test_output, 'r') as f1, open(golden_output, 'r') as f2:
            test_lines = f1.readlines()
            golden_lines = f2.readlines()

        # 检查是否包含头部
        if not any("# Timestep T U P Time" in line for line in test_lines):
            return False, "application generate no output"

        # 定位header
        try:
            test_header_idx = test_lines.index("# Timestep T U P Time\n")
        except ValueError:
            return False, "application generate error output"

        try:
            golden_header_idx = golden_lines.index("# Timestep T U P Time\n")
        except ValueError:
            return False, f"{CMP_STR}False (# Timestep header not found in golden_output)"

        # 提取两行数据
        test_data = test_lines[test_header_idx + 1:test_header_idx + 3]
        golden_data = golden_lines[golden_header_idx + 1:golden_header_idx + 3]

        # 比较数据
        for test_line, golden_line in zip(test_data, golden_data):
            test_tokens = test_line.split()
            golden_tokens = golden_line.split()

            # 比较每个token（排除最后一个Time列）
            for test_token, golden_token in zip(test_tokens[:-1], golden_tokens[:-1]):
                try:
                    test_value = float(test_token)
                    golden_value = float(golden_token)
                    if abs(test_value - golden_value) > tolerance:
                        return False, f"{CMP_STR}False"
                except ValueError:
                    # 跳过非数字token
                    continue

        return True, f"{CMP_STR}True"

    except Exception as e:
        return False, f"{CMP_STR}Unexpected error: {e}"


def miniFE_compare(test_output: str, golden_output: str, tolerance: float = 1e-6) -> Tuple[bool, str]:
    """
    miniFE输出比较

    比较 'Final Resid Norm' 值

    Args:
        test_output: 测试输出文件路径
        golden_output: Golden输出文件路径
        tolerance: 允许的误差范围

    Returns:
        (is_match, message) 元组
    """
    try:
        # 读取两个文件
        with open(test_output, 'r') as f1, open(golden_output, 'r') as f2:
            test_lines = f1.readlines()
            golden_lines = f2.readlines()

        # 定位 'Final Resid Norm' in test_output
        test_resid_norm = None
        for line in test_lines:
            if line.startswith("Final Resid Norm:"):
                try:
                    test_resid_norm = float(line.split(":")[1].strip())
                except ValueError:
                    return False, f"{CMP_STR}False (Invalid numeric format in test_output)"
                break

        if test_resid_norm is None:
            return False, "application generate no output"

        # 定位 'Final Resid Norm' in golden_output
        golden_resid_norm = None
        for line in golden_lines:
            if line.startswith("Final Resid Norm:"):
                try:
                    golden_resid_norm = float(line.split(":")[1].strip())
                except ValueError:
                    return False, f"{CMP_STR}False (Invalid numeric format in golden_output)"
                break

        if golden_resid_norm is None:
            return False, "bias not found in golden_output"

        # 比较residual norms
        if abs(test_resid_norm - golden_resid_norm) > tolerance:
            return False, f"{CMP_STR}False"

        return True, f"{CMP_STR}True"

    except Exception as e:
        return False, f"{CMP_STR}Unexpected error: {e}"


def HPCCG_compare(test_output: str, golden_output: str, tolerance: float = 1e-6) -> Tuple[bool, str]:
    """
    HPCCG输出比较

    比较 'Final residual:' 值

    Args:
        test_output: 测试输出文件路径
        golden_output: Golden输出文件路径
        tolerance: 允许的误差范围

    Returns:
        (is_match, message) 元组
    """
    try:
        # 读取两个文件
        with open(test_output, 'r') as f1, open(golden_output, 'r') as f2:
            test_lines = f1.readlines()
            golden_lines = f2.readlines()

        # 定位 'Final residual:' in test_output
        test_residual = None
        for line in test_lines:
            if line.startswith("Final residual:"):
                try:
                    test_residual = float(line.split(":")[1].strip())
                except ValueError:
                    return False, f"{CMP_STR}False (Invalid numeric format in test_output)"
                break

        if test_residual is None:
            return False, "application generate no output"

        # 定位 'Final residual:' in golden_output
        golden_residual = None
        for line in golden_lines:
            if line.startswith("Final residual:"):
                try:
                    golden_residual = float(line.split(":")[1].strip())
                except ValueError:
                    return False, f"{CMP_STR}False (Invalid numeric format in golden_output)"
                break

        if golden_residual is None:
            return False, f"{CMP_STR}False ('Final residual' not found in golden_output)"

        # 比较residuals
        if abs(test_residual - golden_residual) >= tolerance:
            return False, f"{CMP_STR}False"

        return True, f"{CMP_STR}True"

    except Exception as e:
        return False, f"{CMP_STR}Unexpected error: {e}"


def polybench_compare(test_output: str, golden_output: str, tolerance: float = 0.1) -> Tuple[bool, str]:
    """
    PolyBench输出比较

    使用外部polybench_output_validator库进行相对误差比较

    Args:
        test_output: 测试输出文件路径
        golden_output: Golden输出文件路径
        tolerance: 允许的相对误差

    Returns:
        (is_match, message) 元组
    """
    try:
        # 添加sdcjudger-lib目录到系统路径
        parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        lib_path = os.path.join(parent_dir, "sdcjudger-lib")
        if lib_path not in sys.path:
            sys.path.append(lib_path)

        from polybench_output_validator import compare_outputs

        # 使用compare_outputs函数
        is_relative_error = True
        result, max_rel_error, max_abs_error, ref_value, out_value, debug_msg = compare_outputs(
            golden_output,
            test_output,
            tolerance=tolerance,
            relative_error=is_relative_error
        )

        # 构建详细消息
        msg_parts = [
            "--------------------------------",
            f"tolerance: {tolerance}",
            f"max relative error: {max_rel_error:.6f}",
            f"max absolute error: {max_abs_error:.6f}",
        ]

        if ref_value is not None and out_value is not None:
            msg_parts.append(f"golden output value: {ref_value}")
            msg_parts.append(f"experiment output value: {out_value}")

        msg_parts.append(f"{CMP_STR}{'True' if result == 0 else 'False'}")

        message = "\n".join(msg_parts)
        is_match = (result == 0)

        return is_match, message

    except Exception as e:
        return False, f"{CMP_STR}False (Error: {str(e)})"


def common_compare(test_output: str, golden_output: str, tolerance: float = 0.1) -> Tuple[bool, str]:
    """
    通用数值比较

    使用numpy加载并比较数值数据

    Args:
        test_output: 测试输出文件路径
        golden_output: Golden输出文件路径
        tolerance: 允许的误差范围

    Returns:
        (is_match, message) 元组
    """
    try:
        # 读取文件
        test_data = np.loadtxt(test_output)
        golden_data = np.loadtxt(golden_output)

        # 检查形状
        if test_data.shape != golden_data.shape:
            return False, f"{CMP_STR}False"

        # 计算差异
        difference = np.abs(test_data - golden_data)

        # 检查是否在容差范围内
        if np.all(difference <= tolerance):
            return True, f"{CMP_STR}True"
        else:
            return False, f"{CMP_STR}False"

    except Exception as e:
        return False, f"{CMP_STR}False (Error: {str(e)})"


class SDCComparator:
    """SDC比较器"""

    def __init__(self):
        """初始化比较器"""
        # 比较方法映射
        self.compare_methods = {
            'strong': strong_compare,
            'hotspot': hotspot_compare,
            'miniMD': miniMD_compare,
            'miniFE': miniFE_compare,
            'HPCCG': HPCCG_compare,
            'lu': self._lu_compare,  # 特殊处理
            'polybench': polybench_compare,
            'common': common_compare,
        }

    def compare(
        self,
        test_output: str,
        golden_output: str,
        method: str = 'common',
        tolerance: float = 0.1
    ) -> CompareResult:
        """
        比较测试输出和Golden输出

        Args:
            test_output: 测试输出文件路径
            golden_output: Golden输出文件路径
            method: 比较方法
            tolerance: 容差

        Returns:
            CompareResult对象
        """
        # 获取比较函数
        compare_func = self.compare_methods.get(method, common_compare)

        # 调用比较函数
        if method == 'strong':
            # strong_compare不需要tolerance
            is_match, message = compare_func(test_output, golden_output)
        else:
            is_match, message = compare_func(test_output, golden_output, tolerance)

        return CompareResult(is_match, message, tolerance, method)

    def _lu_compare(self, test_output: str, golden_output: str, tolerance: float = 1e-4) -> Tuple[bool, str]:
        """
        LU分解比较（特殊处理）

        计算L*U并与原始矩阵比较

        Args:
            test_output: 测试LU矩阵文件路径
            golden_output: Golden M矩阵文件路径
            tolerance: 容差

        Returns:
            (is_match, message) 元组
        """
        try:
            # 加载矩阵
            lu_matrix = np.loadtxt(test_output)
            m_matrix = np.loadtxt(golden_output)

            # 从文件名提取矩阵维度
            match = re.search(r'_(\d+)\.txt$', golden_output)
            if match:
                dim = int(match.group(1))
            else:
                dim = lu_matrix.shape[0]

            # 计算L*U
            tmp = np.zeros((dim, dim))
            for i in range(dim):
                for j in range(dim):
                    sum_val = 0.0
                    for k in range(min(i, j) + 1):
                        l = 1.0 if i == k else lu_matrix[i, k]
                        u = lu_matrix[k, j]
                        sum_val += l * u
                    tmp[i, j] = sum_val

            # 比较L*U和M
            is_match = np.allclose(tmp, m_matrix, atol=tolerance)
            message = f"L*U equals M within tolerance({tolerance}): {'True' if is_match else 'False'}"

            return is_match, message

        except Exception as e:
            return False, f"LU compare error: {str(e)}"
