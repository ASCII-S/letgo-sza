"""
NPB (NAS Parallel Benchmarks) 比较器模块

支持的应用：
- bt (Block Tri-diagonal)
- cg (Conjugate Gradient)
- ep (Embarrassingly Parallel)
- ft (Fourier Transform)
- is (Integer Sort)
- lu (Lower-Upper Gauss-Seidel)
- mg (Multi-Grid)
- sp (Scalar Penta-diagonal)
- ua (Unstructured Adaptive)
"""

import re
from typing import Optional, Tuple, List
from .base import BaseComparator, CompareResult


class NPBComparator(BaseComparator):
    """
    NPB (NAS Parallel Benchmarks) 比较器

    NPB 应用内置了验证机制，输出中包含：
    1. Verification 状态：SUCCESSFUL 或 UNSUCCESSFUL
    2. RMS-norms 比较：计算值、参考值、相对误差

    SDC 判定逻辑：
    1. 首先检查 Verification 状态
    2. 如果状态为 SUCCESSFUL，则判定为 Masked
    3. 如果状态为 UNSUCCESSFUL 或无法提取，则判定为 SDC
    4. 可选：检查 RMS-norms 的相对误差是否超过 epsilon
    """

    # 默认 epsilon（NPB 标准精度）
    DEFAULT_EPSILON = 1e-7

    @property
    def name(self) -> str:
        """比较器名称"""
        return "npb"

    def compare(
        self,
        test_output: str,
        golden_output: str,
        tolerance: float = DEFAULT_EPSILON
    ) -> CompareResult:
        """
        比较 NPB 应用输出

        Args:
            test_output: 测试输出内容
            golden_output: 黄金输出内容（用于参考，但主要依赖内置验证）
            tolerance: epsilon 精度阈值

        Returns:
            CompareResult
        """
        # 读取文件内容
        test_content = self._read_content(test_output)
        if test_content is None:
            return CompareResult(
                is_match=False,
                message=f"无法读取测试输出: {test_output}",
                method="npb",
                max_error=None
            )

        # 提取验证状态
        verification_status = self._extract_verification_status(test_content)

        # 提取 epsilon
        epsilon = self._extract_epsilon(test_content)
        if epsilon is None:
            epsilon = tolerance

        # 提取 RMS-norms 误差
        rms_errors = self._extract_rms_errors(test_content)
        max_error = max(rms_errors) if rms_errors else None

        # 判定逻辑
        if verification_status is None:
            # 无法提取验证状态，可能程序崩溃或输出不完整
            return CompareResult(
                is_match=False,
                message="无法从输出中提取 Verification 状态",
                method="npb",
                max_error=max_error,
                details={
                    "verification_status": None,
                    "epsilon": epsilon,
                    "rms_errors": rms_errors
                }
            )

        if verification_status.upper() == "SUCCESSFUL":
            # 验证成功
            # 额外检查：如果有 RMS 误差，确保都在 epsilon 范围内
            if rms_errors and max_error is not None:
                if max_error > epsilon:
                    return CompareResult(
                        is_match=False,
                        message=f"NPB 验证状态为 SUCCESSFUL，但 RMS 误差超过 epsilon: max_error={max_error:.6e}, epsilon={epsilon:.6e}",
                        method="npb",
                        max_error=max_error,
                        details={
                            "verification_status": verification_status,
                            "epsilon": epsilon,
                            "rms_errors": rms_errors
                        }
                    )

            return CompareResult(
                is_match=True,
                message=f"NPB 验证: 通过, 状态={verification_status}, epsilon={epsilon:.6e}" +
                        (f", max_rms_error={max_error:.6e}" if max_error else ""),
                method="npb",
                max_error=max_error,
                details={
                    "verification_status": verification_status,
                    "epsilon": epsilon,
                    "rms_errors": rms_errors
                }
            )
        else:
            # 验证失败
            return CompareResult(
                is_match=False,
                message=f"NPB 验证: 失败, 状态={verification_status}",
                method="npb",
                max_error=max_error,
                details={
                    "verification_status": verification_status,
                    "epsilon": epsilon,
                    "rms_errors": rms_errors
                }
            )

    def _extract_verification_status(self, content: str) -> Optional[str]:
        """
        提取 Verification 状态

        可能的格式：
        - "Verification Successful"
        - "Verification    =               SUCCESSFUL"
        - "Verification    =             UNSUCCESSFUL"

        Returns:
            "SUCCESSFUL", "UNSUCCESSFUL", 或 None
        """
        # 模式1: "Verification Successful" 或 "Verification Unsuccessful"
        pattern1 = r'Verification\s+(Successful|Unsuccessful)'
        match = re.search(pattern1, content, re.IGNORECASE)
        if match:
            return match.group(1).upper()

        # 模式2: "Verification    =               SUCCESSFUL"
        pattern2 = r'Verification\s*=\s*(SUCCESSFUL|UNSUCCESSFUL)'
        match = re.search(pattern2, content, re.IGNORECASE)
        if match:
            return match.group(1).upper()

        return None

    def _extract_epsilon(self, content: str) -> Optional[float]:
        """
        提取 epsilon 精度设置

        格式: "accuracy setting for epsilon =  0.1000000000000E-07"

        Returns:
            epsilon 值或 None
        """
        pattern = r'accuracy setting for epsilon\s*=\s*([+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)'
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                pass
        return None

    def _extract_rms_errors(self, content: str) -> List[float]:
        """
        提取 RMS-norms 的相对误差

        格式:
        Comparison of RMS-norms of residual
                  1 0.1703428370954E+00 0.1703428370954E+00 0.7201925617357E-13
                  2 0.1297525207003E-01 0.1297525207003E-01 0.3680617304070E-12

        第三列是相对误差

        Returns:
            相对误差列表
        """
        errors = []

        # 查找 RMS-norms 比较部分
        # 匹配格式: 索引 计算值 参考值 相对误差
        pattern = r'^\s*(\d+)\s+([+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)\s+([+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)\s+([+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)\s*$'

        for line in content.split('\n'):
            match = re.match(pattern, line)
            if match:
                try:
                    # 第四个值是相对误差
                    error = float(match.group(4))
                    errors.append(abs(error))
                except ValueError:
                    pass

        return errors
