"""
PolyBench 套件比较器模块

提供 PolyBench 应用的比较方法，使用 polybench_output_validator 库。
适用于: 2mm, fdtd-2d, bicg, correlation, gesummv, syr2k, gaussian, convolution, mvt
"""

import re
from typing import List, Optional, Tuple

import numpy as np

from .base import BaseComparator, CompareResult


class PolybenchComparator(BaseComparator):
    """
    PolyBench 比较器

    使用相对误差比较 PolyBench 应用的输出。
    PolyBench 输出格式为 ==BEGIN DUMP_ARRAYS== ... ==END DUMP_ARRAYS==
    """

    @property
    def name(self) -> str:
        return "polybench"

    def compare(
        self,
        test_output: str,
        golden_output: str,
        tolerance: float = 0.1
    ) -> CompareResult:
        """比较 PolyBench 输出"""
        try:
            # 读取内容
            test_content = self._read_content(test_output)
            golden_content = self._read_content(golden_output)

            # 尝试使用 polybench_output_validator 库
            try:
                from polybench_output_validator import validate_output
                is_valid = validate_output(test_content, golden_content, tolerance)
                if is_valid:
                    return CompareResult(
                        is_match=True,
                        message="PolyBench 验证通过（使用 polybench_output_validator）",
                        method=self.name,
                        details={'tolerance': tolerance, 'validator': 'polybench_output_validator'}
                    )
                else:
                    return CompareResult(
                        is_match=False,
                        message="PolyBench 验证失败（使用 polybench_output_validator）",
                        method=self.name,
                        details={'tolerance': tolerance, 'validator': 'polybench_output_validator'}
                    )
            except ImportError:
                # 如果库不可用，使用内置方法
                pass

            # 内置比较方法
            return self._builtin_compare(test_content, golden_content, tolerance)

        except Exception as e:
            return CompareResult(
                is_match=False,
                message=f"PolyBench 比较失败: {e}",
                method=self.name
            )

    def _builtin_compare(
        self,
        test_content: str,
        golden_content: str,
        tolerance: float
    ) -> CompareResult:
        """内置的 PolyBench 比较方法"""
        # 提取数组数据
        test_arrays = self._extract_arrays(test_content)
        golden_arrays = self._extract_arrays(golden_content)

        if not test_arrays:
            return CompareResult(
                is_match=False,
                message="无法从测试输出中提取数组数据",
                method=self.name
            )

        if not golden_arrays:
            return CompareResult(
                is_match=False,
                message="无法从黄金输出中提取数组数据",
                method=self.name
            )

        # 检查数组数量
        if len(test_arrays) != len(golden_arrays):
            return CompareResult(
                is_match=False,
                message=f"数组数量不匹配: 测试={len(test_arrays)}, 黄金={len(golden_arrays)}",
                method=self.name
            )

        # 比较每个数组
        max_rel_error = 0.0
        total_elements = 0
        mismatched_elements = 0

        for (test_name, test_data), (golden_name, golden_data) in zip(test_arrays, golden_arrays):
            if len(test_data) != len(golden_data):
                return CompareResult(
                    is_match=False,
                    message=f"数组 {test_name} 元素数量不匹配: 测试={len(test_data)}, 黄金={len(golden_data)}",
                    method=self.name
                )

            for t_val, g_val in zip(test_data, golden_data):
                total_elements += 1
                # 计算相对误差
                if abs(g_val) > 1e-10:
                    rel_error = abs(t_val - g_val) / abs(g_val)
                else:
                    rel_error = abs(t_val - g_val)

                max_rel_error = max(max_rel_error, rel_error)
                if rel_error > tolerance:
                    mismatched_elements += 1

        is_match = mismatched_elements == 0

        return CompareResult(
            is_match=is_match,
            message=f"PolyBench 比较: {'通过' if is_match else '失败'}, "
                    f"最大相对误差={max_rel_error:.6e}, "
                    f"不匹配元素={mismatched_elements}/{total_elements}",
            method=self.name,
            max_error=max_rel_error,
            details={
                'tolerance': tolerance,
                'total_elements': total_elements,
                'mismatched_elements': mismatched_elements,
                'array_count': len(test_arrays),
                'validator': 'builtin'
            }
        )

    def _extract_arrays(self, content: str) -> List[Tuple[str, List[float]]]:
        """
        从 PolyBench 输出中提取数组数据

        格式示例:
        ==BEGIN DUMP_ARRAYS==
        begin dump: D
        6.74 6.20 6.89 ...
        end   dump: D
        ==END   DUMP_ARRAYS==
        """
        arrays = []

        # 查找 DUMP_ARRAYS 块
        dump_pattern = r'==BEGIN DUMP_ARRAYS==(.*?)==END\s+DUMP_ARRAYS=='
        dump_match = re.search(dump_pattern, content, re.DOTALL)

        if not dump_match:
            # 尝试直接解析数值（可能没有标记）
            numbers = self._extract_all_numbers(content)
            if numbers:
                arrays.append(('data', numbers))
            return arrays

        dump_content = dump_match.group(1)

        # 查找每个数组
        array_pattern = r'begin dump:\s*(\w+)(.*?)end\s+dump:\s*\1'
        for match in re.finditer(array_pattern, dump_content, re.DOTALL | re.IGNORECASE):
            array_name = match.group(1)
            array_content = match.group(2)
            numbers = self._extract_all_numbers(array_content)
            if numbers:
                arrays.append((array_name, numbers))

        return arrays

    def _extract_all_numbers(self, content: str) -> List[float]:
        """从内容中提取所有数值"""
        pattern = r'[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?'
        matches = re.findall(pattern, content)
        numbers = []
        for m in matches:
            try:
                numbers.append(float(m))
            except ValueError:
                continue
        return numbers
