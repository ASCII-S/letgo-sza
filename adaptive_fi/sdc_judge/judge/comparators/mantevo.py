"""
Mantevo 套件比较器模块

提供 miniMD, miniFE, HPCCG 的比较方法。
"""

import re
from typing import Optional, List

import numpy as np

from .base import BaseComparator, CompareResult


class MiniMDComparator(BaseComparator):
    """
    miniMD 比较器

    比较 "# Timestep T U P Time" 后两行的数据（排除 Time 列）。
    适用于: miniMD
    """

    @property
    def name(self) -> str:
        return "miniMD"

    def compare(
        self,
        test_output: str,
        golden_output: str,
        tolerance: float = 1e-6
    ) -> CompareResult:
        """比较 miniMD 输出"""
        try:
            # 读取内容
            test_content = self._read_content(test_output)
            golden_content = self._read_content(golden_output)

            # 提取数据
            test_data = self._extract_timestep_data(test_content)
            golden_data = self._extract_timestep_data(golden_content)

            if test_data is None:
                return CompareResult(
                    is_match=False,
                    message="无法从测试输出中提取 Timestep 数据",
                    method=self.name
                )

            if golden_data is None:
                return CompareResult(
                    is_match=False,
                    message="无法从黄金输出中提取 Timestep 数据",
                    method=self.name
                )

            # 比较数据（排除 Time 列，即最后一列）
            test_arr = np.array(test_data)[:, :-1]  # 排除最后一列
            golden_arr = np.array(golden_data)[:, :-1]

            if test_arr.shape != golden_arr.shape:
                return CompareResult(
                    is_match=False,
                    message=f"数据维度不匹配: 测试={test_arr.shape}, 黄金={golden_arr.shape}",
                    method=self.name
                )

            diff = np.abs(test_arr - golden_arr)
            max_error = float(np.max(diff))
            is_match = np.allclose(test_arr, golden_arr, atol=tolerance, rtol=0)

            return CompareResult(
                is_match=is_match,
                message=f"miniMD 比较: {'通过' if is_match else '失败'}, 最大误差={max_error:.6e}",
                method=self.name,
                max_error=max_error,
                details={
                    'tolerance': tolerance,
                    'rows_compared': test_arr.shape[0]
                }
            )

        except Exception as e:
            return CompareResult(
                is_match=False,
                message=f"miniMD 比较失败: {e}",
                method=self.name
            )

    def _extract_timestep_data(self, content: str) -> Optional[List[List[float]]]:
        """
        提取 Timestep 数据

        查找 "# Timestep T U P Time" 标记，然后提取后面两行数据
        """
        lines = content.strip().split('\n')
        data = []
        found_header = False

        for i, line in enumerate(lines):
            if '# Timestep' in line and 'T' in line and 'U' in line and 'P' in line:
                found_header = True
                continue

            if found_header:
                line = line.strip()
                if not line:
                    continue
                # 解析数值行
                values = re.split(r'\s+', line)
                row = []
                for v in values:
                    try:
                        row.append(float(v))
                    except ValueError:
                        continue
                if row:
                    data.append(row)
                    if len(data) >= 2:  # 只取两行
                        break

        return data if data else None


class MiniFEComparator(BaseComparator):
    """
    miniFE 比较器

    比较 "Final Resid Norm" 值。
    适用于: miniFE
    """

    @property
    def name(self) -> str:
        return "miniFE"

    def compare(
        self,
        test_output: str,
        golden_output: str,
        tolerance: float = 1e-6
    ) -> CompareResult:
        """比较 miniFE 输出"""
        try:
            # 读取内容
            test_content = self._read_content(test_output)
            golden_content = self._read_content(golden_output)

            # 提取 Final Resid Norm
            test_value = self._extract_final_resid_norm(test_content)
            golden_value = self._extract_final_resid_norm(golden_content)

            if test_value is None:
                return CompareResult(
                    is_match=False,
                    message="无法从测试输出中提取 Final Resid Norm",
                    method=self.name
                )

            if golden_value is None:
                return CompareResult(
                    is_match=False,
                    message="无法从黄金输出中提取 Final Resid Norm",
                    method=self.name
                )

            # 比较
            diff = abs(test_value - golden_value)
            is_match = diff <= tolerance

            return CompareResult(
                is_match=is_match,
                message=f"miniFE 比较: {'通过' if is_match else '失败'}, "
                        f"测试={test_value:.6e}, 黄金={golden_value:.6e}, 误差={diff:.6e}",
                method=self.name,
                max_error=diff,
                details={
                    'tolerance': tolerance,
                    'test_value': test_value,
                    'golden_value': golden_value
                }
            )

        except Exception as e:
            return CompareResult(
                is_match=False,
                message=f"miniFE 比较失败: {e}",
                method=self.name
            )

    def _extract_final_resid_norm(self, content: str) -> Optional[float]:
        """提取 Final Resid Norm 值"""
        # 匹配 "Final Resid Norm: 1.234e-05" 格式
        pattern = r'Final\s+Resid\s+Norm[:\s]+([+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)'
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                pass
        return None


class HPCCGComparator(BaseComparator):
    """
    HPCCG 比较器

    比较 "Final residual" 值。
    适用于: HPCCG
    """

    @property
    def name(self) -> str:
        return "HPCCG"

    def compare(
        self,
        test_output: str,
        golden_output: str,
        tolerance: float = 1e-6
    ) -> CompareResult:
        """比较 HPCCG 输出"""
        try:
            # 读取内容
            test_content = self._read_content(test_output)
            golden_content = self._read_content(golden_output)

            # 提取 Final residual
            test_value = self._extract_final_residual(test_content)
            golden_value = self._extract_final_residual(golden_content)

            if test_value is None:
                return CompareResult(
                    is_match=False,
                    message="无法从测试输出中提取 Final residual",
                    method=self.name
                )

            if golden_value is None:
                return CompareResult(
                    is_match=False,
                    message="无法从黄金输出中提取 Final residual",
                    method=self.name
                )

            # 比较
            diff = abs(test_value - golden_value)
            is_match = diff <= tolerance

            return CompareResult(
                is_match=is_match,
                message=f"HPCCG 比较: {'通过' if is_match else '失败'}, "
                        f"测试={test_value:.6e}, 黄金={golden_value:.6e}, 误差={diff:.6e}",
                method=self.name,
                max_error=diff,
                details={
                    'tolerance': tolerance,
                    'test_value': test_value,
                    'golden_value': golden_value
                }
            )

        except Exception as e:
            return CompareResult(
                is_match=False,
                message=f"HPCCG 比较失败: {e}",
                method=self.name
            )

    def _extract_final_residual(self, content: str) -> Optional[float]:
        """提取 Final residual 值"""
        # 匹配 "Final residual: 1.234e-05" 或 "Final residual = 1.234e-05" 格式
        pattern = r'Final\s+residual[:\s=]+([+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)'
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                pass
        return None
