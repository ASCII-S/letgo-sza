"""
SDC判断模块

提供以下功能：
1. SDC判定（比较输出与Golden）
2. 批量SDC判断
3. SDC结果管理

主要组件：
- SDCComparator: SDC比较器
- SDCJudge: SDC判断器
- SDCJudgeResult: SDC判断结果
"""

from .sdc_comparator import SDCComparator, CompareResult
from .sdc_judge import SDCJudge, SDCJudgeResult

__all__ = [
    'SDCComparator',
    'CompareResult',
    'SDCJudge',
    'SDCJudgeResult',
]
