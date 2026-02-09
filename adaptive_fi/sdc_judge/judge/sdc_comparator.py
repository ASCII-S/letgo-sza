"""
SDC比较器模块

协调器模式，整合所有比较器。
保持向后兼容的接口。
"""

import os
import sys
from typing import Tuple, Optional, Dict, Any

# 导入新的比较器
from .comparators import (
    CompareResult,
    BaseComparator,
    StrongComparator,
    CommonComparator,
    HotspotComparator,
    LUComparator,
    MiniMDComparator,
    MiniFEComparator,
    HPCCGComparator,
    PolybenchComparator,
    AMGComparator,
    HPLComparator,
    NPBComparator,
)

# 默认比较结果字符串（保持向后兼容）
CMP_STR = "Compare within tolerance: "


class SDCComparator:
    """
    SDC比较器（协调器）

    整合所有比较器，提供统一的比较接口。
    """

    def __init__(self):
        """初始化比较器"""
        # 注册所有比较器实例
        self._comparators: Dict[str, BaseComparator] = {
            'strong': StrongComparator(),
            'common': CommonComparator(),
            'hotspot': HotspotComparator(),
            'lu': LUComparator(),
            'miniMD': MiniMDComparator(),
            'miniFE': MiniFEComparator(),
            'HPCCG': HPCCGComparator(),
            'polybench': PolybenchComparator(),
            'amg': AMGComparator(),
            'hpl': HPLComparator(),
            'npb': NPBComparator(),
        }

        # 向后兼容：保留旧的函数式接口映射
        self.compare_methods = {
            'strong': self._wrap_strong,
            'hotspot': self._wrap_hotspot,
            'miniMD': self._wrap_miniMD,
            'miniFE': self._wrap_miniFE,
            'HPCCG': self._wrap_HPCCG,
            'lu': self._wrap_lu,
            'polybench': self._wrap_polybench,
            'common': self._wrap_common,
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
            test_output: 测试输出文件路径或内容
            golden_output: Golden输出文件路径或内容
            method: 比较方法
            tolerance: 容差

        Returns:
            CompareResult对象
        """
        # 获取比较器
        comparator = self._comparators.get(method)

        if comparator is None:
            # 使用默认比较器
            comparator = self._comparators['common']

        # 执行比较
        result = comparator.compare(test_output, golden_output, tolerance)

        return result

    def get_comparator(self, method: str) -> Optional[BaseComparator]:
        """
        获取指定的比较器实例

        Args:
            method: 比较方法名称

        Returns:
            比较器实例或None
        """
        return self._comparators.get(method)

    def register_comparator(self, name: str, comparator: BaseComparator) -> None:
        """
        注册新的比较器

        Args:
            name: 比较器名称
            comparator: 比较器实例
        """
        self._comparators[name] = comparator

    def list_methods(self) -> list:
        """列出所有可用的比较方法"""
        return list(self._comparators.keys())

    # ========== 向后兼容的包装函数 ==========

    def _wrap_strong(self, test_output: str, golden_output: str) -> Tuple[bool, str]:
        """包装 StrongComparator"""
        result = self._comparators['strong'].compare(test_output, golden_output, 0)
        return result.is_match, f"{CMP_STR}{'True' if result.is_match else 'False'}"

    def _wrap_hotspot(self, test_output: str, golden_output: str, tolerance: float = 1e-6) -> Tuple[bool, str]:
        """包装 HotspotComparator"""
        result = self._comparators['hotspot'].compare(test_output, golden_output, tolerance)
        return result.is_match, f"{CMP_STR}{'True' if result.is_match else 'False'}"

    def _wrap_miniMD(self, test_output: str, golden_output: str, tolerance: float = 1e-6) -> Tuple[bool, str]:
        """包装 MiniMDComparator"""
        result = self._comparators['miniMD'].compare(test_output, golden_output, tolerance)
        return result.is_match, f"{CMP_STR}{'True' if result.is_match else 'False'}"

    def _wrap_miniFE(self, test_output: str, golden_output: str, tolerance: float = 1e-6) -> Tuple[bool, str]:
        """包装 MiniFEComparator"""
        result = self._comparators['miniFE'].compare(test_output, golden_output, tolerance)
        return result.is_match, f"{CMP_STR}{'True' if result.is_match else 'False'}"

    def _wrap_HPCCG(self, test_output: str, golden_output: str, tolerance: float = 1e-6) -> Tuple[bool, str]:
        """包装 HPCCGComparator"""
        result = self._comparators['HPCCG'].compare(test_output, golden_output, tolerance)
        return result.is_match, f"{CMP_STR}{'True' if result.is_match else 'False'}"

    def _wrap_lu(self, test_output: str, golden_output: str, tolerance: float = 1e-4) -> Tuple[bool, str]:
        """包装 LUComparator"""
        result = self._comparators['lu'].compare(test_output, golden_output, tolerance)
        return result.is_match, result.message

    def _wrap_polybench(self, test_output: str, golden_output: str, tolerance: float = 0.1) -> Tuple[bool, str]:
        """包装 PolybenchComparator"""
        result = self._comparators['polybench'].compare(test_output, golden_output, tolerance)
        return result.is_match, f"{CMP_STR}{'True' if result.is_match else 'False'}"

    def _wrap_common(self, test_output: str, golden_output: str, tolerance: float = 0.1) -> Tuple[bool, str]:
        """包装 CommonComparator"""
        result = self._comparators['common'].compare(test_output, golden_output, tolerance)
        return result.is_match, f"{CMP_STR}{'True' if result.is_match else 'False'}"


# ========== 向后兼容的模块级函数 ==========
# 这些函数保持与旧代码的兼容性

def strong_compare(test_output: str, golden_output: str) -> Tuple[bool, str]:
    """二进制完全比较（向后兼容）"""
    comparator = StrongComparator()
    result = comparator.compare(test_output, golden_output, 0)
    return result.is_match, f"{CMP_STR}{'True' if result.is_match else 'False'}"


def hotspot_compare(test_output: str, golden_output: str, tolerance: float = 1e-6) -> Tuple[bool, str]:
    """Hotspot CSV格式比较（向后兼容）"""
    comparator = HotspotComparator()
    result = comparator.compare(test_output, golden_output, tolerance)
    return result.is_match, f"{CMP_STR}{'True' if result.is_match else 'False'}"


def miniMD_compare(test_output: str, golden_output: str, tolerance: float = 1e-6) -> Tuple[bool, str]:
    """miniMD输出比较（向后兼容）"""
    comparator = MiniMDComparator()
    result = comparator.compare(test_output, golden_output, tolerance)
    return result.is_match, f"{CMP_STR}{'True' if result.is_match else 'False'}"


def miniFE_compare(test_output: str, golden_output: str, tolerance: float = 1e-6) -> Tuple[bool, str]:
    """miniFE输出比较（向后兼容）"""
    comparator = MiniFEComparator()
    result = comparator.compare(test_output, golden_output, tolerance)
    return result.is_match, f"{CMP_STR}{'True' if result.is_match else 'False'}"


def HPCCG_compare(test_output: str, golden_output: str, tolerance: float = 1e-6) -> Tuple[bool, str]:
    """HPCCG输出比较（向后兼容）"""
    comparator = HPCCGComparator()
    result = comparator.compare(test_output, golden_output, tolerance)
    return result.is_match, f"{CMP_STR}{'True' if result.is_match else 'False'}"


def polybench_compare(test_output: str, golden_output: str, tolerance: float = 0.1) -> Tuple[bool, str]:
    """PolyBench输出比较（向后兼容）"""
    comparator = PolybenchComparator()
    result = comparator.compare(test_output, golden_output, tolerance)
    return result.is_match, f"{CMP_STR}{'True' if result.is_match else 'False'}"


def common_compare(test_output: str, golden_output: str, tolerance: float = 0.1) -> Tuple[bool, str]:
    """通用数值比较（向后兼容）"""
    comparator = CommonComparator()
    result = comparator.compare(test_output, golden_output, tolerance)
    return result.is_match, f"{CMP_STR}{'True' if result.is_match else 'False'}"
