"""
Rodinia 套件特殊比较器模块

提供 Rodinia 套件中需要特殊处理的应用比较方法。
"""

import re
from typing import Optional, Tuple

from .base import BaseComparator, CompareResult


class AMGComparator(BaseComparator):
    """
    AMG (Algebraic Multigrid) 比较器

    比较 "Final Relative Residual Norm" 值。

    AMG 是一个代数多重网格求解器，用于求解大规模稀疏线性方程组。
    Final Relative Residual Norm 表示迭代求解的最终相对残差范数，
    是衡量求解精度的关键指标。

    适用于: amg
    """

    @property
    def name(self) -> str:
        return "amg"

    def compare(
        self,
        test_output: str,
        golden_output: str,
        tolerance: float = 1e-6
    ) -> CompareResult:
        """比较 AMG 输出"""
        try:
            # 读取内容
            test_content = self._read_content(test_output)
            golden_content = self._read_content(golden_output)

            # 提取 Final Relative Residual Norm
            test_value = self._extract_final_residual_norm(test_content)
            golden_value = self._extract_final_residual_norm(golden_content)

            if test_value is None:
                return CompareResult(
                    is_match=False,
                    message="无法从测试输出中提取 Final Relative Residual Norm",
                    method=self.name
                )

            if golden_value is None:
                return CompareResult(
                    is_match=False,
                    message="无法从黄金输出中提取 Final Relative Residual Norm",
                    method=self.name
                )

            # 计算相对误差（因为残差值可能非常小，使用相对误差更合理）
            if golden_value != 0:
                relative_error = abs(test_value - golden_value) / abs(golden_value)
            else:
                relative_error = abs(test_value - golden_value)

            abs_error = abs(test_value - golden_value)
            is_match = relative_error <= tolerance

            return CompareResult(
                is_match=is_match,
                message=f"AMG 比较: {'通过' if is_match else '失败'}, "
                        f"测试={test_value:.6e}, 黄金={golden_value:.6e}, "
                        f"相对误差={relative_error:.6e}",
                method=self.name,
                max_error=relative_error,
                details={
                    'tolerance': tolerance,
                    'test_value': test_value,
                    'golden_value': golden_value,
                    'absolute_error': abs_error,
                    'relative_error': relative_error
                }
            )

        except Exception as e:
            return CompareResult(
                is_match=False,
                message=f"AMG 比较失败: {e}",
                method=self.name
            )

    def _extract_final_residual_norm(self, content: str) -> Optional[float]:
        """
        提取 Final Relative Residual Norm 值

        匹配格式: "Final Relative Residual Norm = 7.803030e-09"
        """
        # 匹配 "Final Relative Residual Norm = 1.234e-05" 格式
        pattern = r'Final\s+Relative\s+Residual\s+Norm\s*=\s*([+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)'
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                pass
        return None


class HPLComparator(BaseComparator):
    """
    HPL (High-Performance Linpack) 比较器

    HPL 是高性能计算领域的标准基准测试，用于求解稠密线性方程组。

    判定标准：
    - 提取 scaled residual 值: ||Ax-b||_oo/(eps*(||A||_oo*||x||_oo+||b||_oo)*N)
    - 如果 scaled residual < 16.0，则判定为 PASSED (Masked)
    - 如果 scaled residual >= 16.0 或无法提取，则判定为 SDC

    注意：HPL 的判定不依赖于与黄金输出的比较，而是检查 scaled residual 是否在阈值内。
    tolerance 参数在此比较器中表示 scaled residual 的阈值（默认 16.0）。

    适用于: hpl
    """

    # HPL 默认阈值
    DEFAULT_THRESHOLD = 16.0

    @property
    def name(self) -> str:
        return "hpl"

    def compare(
        self,
        test_output: str,
        golden_output: str,
        tolerance: float = 16.0
    ) -> CompareResult:
        """
        比较 HPL 输出

        Args:
            test_output: 测试输出文件路径或内容
            golden_output: 黄金输出文件路径或内容（用于提取阈值，可选）
            tolerance: scaled residual 阈值（默认 16.0）
        """
        try:
            # 读取测试输出内容
            test_content = self._read_content(test_output)

            # 从黄金输出中提取阈值（如果有）
            threshold = tolerance
            if golden_output:
                golden_content = self._read_content(golden_output)
                extracted_threshold = self._extract_threshold(golden_content)
                if extracted_threshold is not None:
                    threshold = extracted_threshold

            # 提取 scaled residual 和 PASSED/FAILED 状态
            residual, passed = self._extract_residual_and_status(test_content)

            if residual is None:
                return CompareResult(
                    is_match=False,
                    message="无法从测试输出中提取 scaled residual",
                    method=self.name
                )

            # 判定逻辑：residual < threshold 且状态为 PASSED
            is_match = residual < threshold and passed

            status_str = "PASSED" if passed else "FAILED"
            return CompareResult(
                is_match=is_match,
                message=f"HPL 比较: {'通过' if is_match else '失败'}, "
                        f"scaled_residual={residual:.6e}, 阈值={threshold}, "
                        f"状态={status_str}",
                method=self.name,
                max_error=residual,
                details={
                    'threshold': threshold,
                    'scaled_residual': residual,
                    'passed': passed,
                    'within_threshold': residual < threshold
                }
            )

        except Exception as e:
            return CompareResult(
                is_match=False,
                message=f"HPL 比较失败: {e}",
                method=self.name
            )

    def _extract_residual_and_status(self, content: str) -> Tuple[Optional[float], bool]:
        """
        提取 scaled residual 值和 PASSED/FAILED 状态

        匹配格式:
        ||Ax-b||_oo/(eps*(||A||_oo*||x||_oo+||b||_oo)*N)=   8.08361278e-03 ...... PASSED
        """
        # 匹配 scaled residual 和状态
        pattern = r'\|\|Ax-b\|\|_oo/\(eps\*\(\|\|A\|\|_oo\*\|\|x\|\|_oo\+\|\|b\|\|_oo\)\*N\)\s*=\s*([+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)\s*\.+\s*(PASSED|FAILED)'
        match = re.search(pattern, content, re.IGNORECASE)

        if match:
            try:
                residual = float(match.group(1))
                passed = match.group(2).upper() == 'PASSED'
                return residual, passed
            except ValueError:
                pass

        # 备用模式：只匹配数值
        pattern_simple = r'\|\|Ax-b\|\|_oo/.*?=\s*([+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)'
        match = re.search(pattern_simple, content)
        if match:
            try:
                residual = float(match.group(1))
                # 检查是否有 PASSED 字样
                passed = 'PASSED' in content.upper()
                return residual, passed
            except ValueError:
                pass

        return None, False

    def _extract_threshold(self, content: str) -> Optional[float]:
        """
        从输出中提取阈值

        匹配格式:
        Computational tests pass if scaled residuals are less than                16.0
        """
        pattern = r'Computational tests pass if scaled residuals are less than\s+([+-]?(?:\d+\.?\d*|\.\d+))'
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                pass
        return None

