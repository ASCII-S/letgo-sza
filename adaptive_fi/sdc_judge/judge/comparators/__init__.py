"""
比较器模块

提供各种 SDC 比较方法的实现。
"""

from .base import (
    CompareResult,
    BaseComparator,
    StrongComparator,
    CommonComparator,
)
from .numeric import (
    HotspotComparator,
    LUComparator,
)
from .mantevo import (
    MiniMDComparator,
    MiniFEComparator,
    HPCCGComparator,
)
from .polybench import (
    PolybenchComparator,
)
from .rodinia import (
    AMGComparator,
    HPLComparator,
)
from .npb import (
    NPBComparator,
)

__all__ = [
    # 基础类
    'CompareResult',
    'BaseComparator',
    # 通用比较器
    'StrongComparator',
    'CommonComparator',
    # 数值比较器
    'HotspotComparator',
    'LUComparator',
    # Mantevo 比较器
    'MiniMDComparator',
    'MiniFEComparator',
    'HPCCGComparator',
    # PolyBench 比较器
    'PolybenchComparator',
    # Rodinia 特殊比较器
    'AMGComparator',
    'HPLComparator',
    # NPB 比较器
    'NPBComparator',
]
