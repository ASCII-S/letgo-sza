"""
基础比较器模块

定义比较器基类和通用比较方法（strong, common）。
"""

import os
import filecmp
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Dict, Any

import numpy as np


@dataclass
class CompareResult:
    """比较结果"""
    is_match: bool  # 是否匹配
    message: str  # 结果消息
    method: str  # 使用的比较方法
    max_error: float = 0.0  # 最大误差
    details: Optional[Dict[str, Any]] = field(default_factory=dict)  # 详细信息


class BaseComparator(ABC):
    """比较器基类"""

    @property
    @abstractmethod
    def name(self) -> str:
        """比较器名称"""
        pass

    @abstractmethod
    def compare(
        self,
        test_output: str,
        golden_output: str,
        tolerance: float = 0.1
    ) -> CompareResult:
        """
        比较测试输出和黄金输出

        Args:
            test_output: 测试输出文件路径或内容
            golden_output: 黄金输出文件路径或内容
            tolerance: 容差值

        Returns:
            CompareResult: 比较结果
        """
        pass

    def _is_file_path(self, s: str) -> bool:
        """判断字符串是否为文件路径"""
        return os.path.exists(s) if s and len(s) < 1000 else False

    def _read_content(self, path_or_content: str) -> str:
        """读取文件内容或直接返回内容"""
        if self._is_file_path(path_or_content):
            with open(path_or_content, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        return path_or_content


class StrongComparator(BaseComparator):
    """
    精确比较器

    使用二进制比较，要求输出完全相同。
    适用于: bfs, backprop, nn, kmeans, particlefilter
    """

    @property
    def name(self) -> str:
        return "strong"

    def compare(
        self,
        test_output: str,
        golden_output: str,
        tolerance: float = 0.1
    ) -> CompareResult:
        """精确比较两个文件"""
        # 检查文件是否存在
        if not self._is_file_path(test_output):
            return CompareResult(
                is_match=False,
                message=f"测试输出文件不存在: {test_output}",
                method=self.name
            )

        if not self._is_file_path(golden_output):
            return CompareResult(
                is_match=False,
                message=f"黄金输出文件不存在: {golden_output}",
                method=self.name
            )

        # 使用 filecmp 进行二进制比较
        try:
            is_match = filecmp.cmp(test_output, golden_output, shallow=False)
            if is_match:
                return CompareResult(
                    is_match=True,
                    message="文件完全匹配",
                    method=self.name
                )
            else:
                return CompareResult(
                    is_match=False,
                    message="文件内容不匹配",
                    method=self.name
                )
        except Exception as e:
            return CompareResult(
                is_match=False,
                message=f"比较失败: {e}",
                method=self.name
            )


class CommonComparator(BaseComparator):
    """
    通用数值比较器

    使用 numpy 加载数据并进行容差比较。
    适用于: 大多数应用的默认比较方法
    """

    @property
    def name(self) -> str:
        return "common"

    def compare(
        self,
        test_output: str,
        golden_output: str,
        tolerance: float = 0.1
    ) -> CompareResult:
        """通用数值比较"""
        try:
            # 读取内容
            test_content = self._read_content(test_output)
            golden_content = self._read_content(golden_output)

            # 提取数值
            test_values = self._extract_numbers(test_content)
            golden_values = self._extract_numbers(golden_content)

            # 检查数量是否一致
            if len(test_values) != len(golden_values):
                return CompareResult(
                    is_match=False,
                    message=f"数值数量不匹配: 测试={len(test_values)}, 黄金={len(golden_values)}",
                    method=self.name,
                    details={
                        'test_count': len(test_values),
                        'golden_count': len(golden_values)
                    }
                )

            if len(test_values) == 0:
                return CompareResult(
                    is_match=False,
                    message="未找到可比较的数值",
                    method=self.name
                )

            # 计算误差
            test_arr = np.array(test_values)
            golden_arr = np.array(golden_values)
            diff = np.abs(test_arr - golden_arr)
            max_error = float(np.max(diff))

            is_match = np.allclose(test_arr, golden_arr, atol=tolerance, rtol=0)

            return CompareResult(
                is_match=is_match,
                message=f"容差比较: {'通过' if is_match else '失败'}, 最大误差={max_error:.6e}",
                method=self.name,
                max_error=max_error,
                details={
                    'tolerance': tolerance,
                    'value_count': len(test_values)
                }
            )

        except Exception as e:
            return CompareResult(
                is_match=False,
                message=f"比较失败: {e}",
                method=self.name
            )

    def _extract_numbers(self, content: str) -> list:
        """从内容中提取所有数值"""
        import re
        # 匹配整数和浮点数（包括科学计数法）
        pattern = r'[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?'
        matches = re.findall(pattern, content)
        numbers = []
        for m in matches:
            try:
                numbers.append(float(m))
            except ValueError:
                continue
        return numbers
