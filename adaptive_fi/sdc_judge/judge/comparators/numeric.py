"""
数值比较器模块

提供 Hotspot 和 LU 矩阵分解的比较方法。
"""

import os
import re
from typing import List, Tuple, Optional

import numpy as np

from .base import BaseComparator, CompareResult


class HotspotComparator(BaseComparator):
    """
    Hotspot 比较器

    比较 CSV 格式的温度数据，支持容差比较。
    适用于: hotspot, hotspot3D
    """

    @property
    def name(self) -> str:
        return "hotspot"

    def compare(
        self,
        test_output: str,
        golden_output: str,
        tolerance: float = 1e-6
    ) -> CompareResult:
        """比较 Hotspot 输出"""
        try:
            # 读取内容
            test_content = self._read_content(test_output)
            golden_content = self._read_content(golden_output)

            # 解析数据
            test_data = self._parse_csv_data(test_content)
            golden_data = self._parse_csv_data(golden_content)

            # 检查维度
            if test_data.shape != golden_data.shape:
                return CompareResult(
                    is_match=False,
                    message=f"数据维度不匹配: 测试={test_data.shape}, 黄金={golden_data.shape}",
                    method=self.name,
                    details={
                        'test_shape': test_data.shape,
                        'golden_shape': golden_data.shape
                    }
                )

            # 计算误差
            diff = np.abs(test_data - golden_data)
            max_error = float(np.max(diff))
            is_match = np.allclose(test_data, golden_data, atol=tolerance, rtol=0)

            return CompareResult(
                is_match=is_match,
                message=f"Hotspot 比较: {'通过' if is_match else '失败'}, 最大误差={max_error:.6e}",
                method=self.name,
                max_error=max_error,
                details={
                    'tolerance': tolerance,
                    'shape': test_data.shape,
                    'total_elements': test_data.size
                }
            )

        except Exception as e:
            return CompareResult(
                is_match=False,
                message=f"Hotspot 比较失败: {e}",
                method=self.name
            )

    def _parse_csv_data(self, content: str) -> np.ndarray:
        """解析 CSV 格式的数据"""
        lines = content.strip().split('\n')
        data = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            # 支持逗号、空格、制表符分隔
            values = re.split(r'[,\s\t]+', line)
            row = []
            for v in values:
                v = v.strip()
                if v:
                    try:
                        row.append(float(v))
                    except ValueError:
                        continue
            if row:
                data.append(row)
        return np.array(data)


class LUComparator(BaseComparator):
    """
    LU 矩阵分解比较器

    验证 L*U 是否等于原始矩阵。
    适用于: lu (LUD)
    """

    @property
    def name(self) -> str:
        return "lu"

    def compare(
        self,
        test_output: str,
        golden_output: str,
        tolerance: float = 1e-4
    ) -> CompareResult:
        """比较 LU 分解结果"""
        try:
            # 读取内容
            test_content = self._read_content(test_output)
            golden_content = self._read_content(golden_output)

            # 解析矩阵
            test_matrix = self._parse_matrix(test_content)
            golden_matrix = self._parse_matrix(golden_content)

            if test_matrix is None or golden_matrix is None:
                return CompareResult(
                    is_match=False,
                    message="无法解析矩阵数据",
                    method=self.name
                )

            # 检查维度
            if test_matrix.shape != golden_matrix.shape:
                return CompareResult(
                    is_match=False,
                    message=f"矩阵维度不匹配: 测试={test_matrix.shape}, 黄金={golden_matrix.shape}",
                    method=self.name
                )

            # 从 LU 分解结果中提取 L 和 U
            test_L, test_U = self._extract_LU(test_matrix)
            golden_L, golden_U = self._extract_LU(golden_matrix)

            # 计算 L*U
            test_product = np.dot(test_L, test_U)
            golden_product = np.dot(golden_L, golden_U)

            # 比较结果
            diff = np.abs(test_product - golden_product)
            max_error = float(np.max(diff))
            is_match = np.allclose(test_product, golden_product, atol=tolerance, rtol=0)

            return CompareResult(
                is_match=is_match,
                message=f"LU 比较: {'通过' if is_match else '失败'}, 最大误差={max_error:.6e}",
                method=self.name,
                max_error=max_error,
                details={
                    'tolerance': tolerance,
                    'matrix_shape': test_matrix.shape
                }
            )

        except Exception as e:
            return CompareResult(
                is_match=False,
                message=f"LU 比较失败: {e}",
                method=self.name
            )

    def _parse_matrix(self, content: str) -> Optional[np.ndarray]:
        """解析矩阵数据"""
        lines = content.strip().split('\n')
        data = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            values = re.split(r'[,\s\t]+', line)
            row = []
            for v in values:
                v = v.strip()
                if v:
                    try:
                        row.append(float(v))
                    except ValueError:
                        continue
            if row:
                data.append(row)

        if not data:
            return None

        # 确保所有行长度一致
        max_len = max(len(row) for row in data)
        for row in data:
            while len(row) < max_len:
                row.append(0.0)

        return np.array(data)

    def _extract_LU(self, matrix: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        从合并的 LU 矩阵中提取 L 和 U

        LU 分解结果通常存储在一个矩阵中：
        - U 是上三角部分（包括对角线）
        - L 是下三角部分（对角线为 1）
        """
        n = matrix.shape[0]

        # 提取 U（上三角，包括对角线）
        U = np.triu(matrix)

        # 提取 L（下三角，对角线为 1）
        L = np.tril(matrix, k=-1)
        np.fill_diagonal(L, 1.0)

        return L, U
