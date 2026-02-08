"""
CSV生成器模块

管理CSV数据的收集和输出。
"""

import pandas as pd
from typing import List, Dict, Optional
from collections import defaultdict


# CSV列名定义
CSV_COLUMNS = [
    'log_index',         # 日志编号
    'target_pc_hex',     # 十六进制PC
    'target_pc_dec',     # 十进制PC
    'target_register',   # 注错寄存器
    'inject_iteration',  # 注错迭代次数
    'inject_bit',        # 注错位位置
    'crash_count',       # 崩溃次数
    'crash_signals',     # 崩溃信号类型
    'used_letgo',        # 是否使用LetGo
    'has_sdc',           # 是否有SDC
    'result',            # 结果分类
    'disasm',            # 反汇编指令
    'timestamp',         # 时间戳
]


class CSVGenerator:
    """CSV文件生成器"""

    def __init__(self, columns: Optional[List[str]] = None):
        """
        初始化CSV生成器

        Args:
            columns: CSV列名列表，默认使用CSV_COLUMNS
        """
        self.columns = columns or CSV_COLUMNS
        self.data = []
        self.error_count = 0

    def append_row(self, data: Dict):
        """
        添加一行数据

        Args:
            data: 包含字段的字典
        """
        # 创建一行数据，确保所有列都存在
        row = {}
        for col in self.columns:
            row[col] = data.get(col, None)

        self.data.append(row)

    def to_csv(self, path: str, encoding: str = 'utf-8-sig'):
        """
        保存为CSV文件

        Args:
            path: 输出CSV文件路径
            encoding: 文件编码，默认 utf-8-sig（支持Excel）
        """
        df = self.get_dataframe()
        df.to_csv(path, index=False, encoding=encoding)

    def get_dataframe(self) -> pd.DataFrame:
        """
        获取pandas DataFrame

        Returns:
            包含所有数据的DataFrame
        """
        if not self.data:
            # 返回空DataFrame但包含列名
            return pd.DataFrame(columns=self.columns)

        return pd.DataFrame(self.data, columns=self.columns)

    def get_statistics(self) -> Dict:
        """
        获取统计摘要

        Returns:
            包含统计信息的字典
        """
        df = self.get_dataframe()

        if df.empty:
            return {
                'total': 0,
                'result_distribution': {},
                'letgo_usage_rate': 0.0,
                'sdc_detection_rate': 0.0,
                'completeness': {},
            }

        total = len(df)

        # 结果分布
        result_dist = df['result'].value_counts().to_dict()

        # LetGo使用率
        letgo_count = df['used_letgo'].sum() if 'used_letgo' in df.columns else 0
        letgo_usage_rate = (letgo_count / total * 100) if total > 0 else 0.0

        # SDC检出率（has_sdc为True的数量）
        sdc_count = (df['has_sdc'] == True).sum() if 'has_sdc' in df.columns else 0
        sdc_detection_rate = (sdc_count / total * 100) if total > 0 else 0.0

        # 数据完整性（各字段非空率）
        completeness = {}
        for col in self.columns:
            non_null_count = df[col].notna().sum()
            completeness[col] = (non_null_count / total * 100) if total > 0 else 0.0

        return {
            'total': total,
            'result_distribution': result_dist,
            'letgo_usage_rate': letgo_usage_rate,
            'sdc_detection_rate': sdc_detection_rate,
            'completeness': completeness,
        }

    def print_statistics(self):
        """打印统计摘要到控制台"""
        stats = self.get_statistics()

        print("\n" + "=" * 60)
        print("日志收集统计摘要")
        print("=" * 60)
        print(f"总日志数: {stats['total']}")

        print("\n结果分布:")
        for result_type, count in sorted(stats['result_distribution'].items()):
            percentage = (count / stats['total'] * 100) if stats['total'] > 0 else 0
            print(f"  {result_type:10s} {count:5d} ({percentage:5.1f}%)")

        print(f"\nLetGo使用率: {stats['letgo_usage_rate']:.1f}%")
        print(f"SDC检出率: {stats['sdc_detection_rate']:.1f}%")

        # 检查数据完整性问题
        print("\n数据完整性:")
        incomplete_fields = [
            (field, rate) for field, rate in stats['completeness'].items()
            if rate < 100.0
        ]

        if incomplete_fields:
            print("  以下字段存在缺失：")
            for field, rate in incomplete_fields:
                print(f"    {field:20s} {rate:5.1f}%")
        else:
            print("  ✓ 所有字段完整")

        print("=" * 60 + "\n")

    def validate_data(self) -> List[str]:
        """
        验证数据合理性

        Returns:
            问题列表（如果为空表示无问题）
        """
        issues = []
        df = self.get_dataframe()

        if df.empty:
            issues.append("无数据")
            return issues

        # 检查1: 结果分布合理性
        if 'result' in df.columns:
            masked_count = (df['result'] == 'Masked').sum()
            total = len(df)
            masked_ratio = masked_count / total if total > 0 else 0

            if masked_ratio > 0.95:
                issues.append(f"Masked比例过高 ({masked_ratio*100:.1f}%)，可能存在问题")

        # 检查2: 崩溃数据一致性
        if all(col in df.columns for col in ['crash_count', 'used_letgo', 'result']):
            # 检查：crash_count==1 且 used_letgo==False 时，result应为Crash
            inconsistent = df[
                (df['crash_count'] == 1) &
                (df['used_letgo'] == False) &
                (df['result'] != 'Crash')
            ]

            if len(inconsistent) > 0:
                issues.append(
                    f"发现{len(inconsistent)}条数据分类不一致：崩溃1次且未使用LetGo，结果应为Crash"
                )

        # 检查3: PC地址一致性
        if all(col in df.columns for col in ['target_pc_hex', 'target_pc_dec']):
            # 检查十六进制和十进制PC是否对应
            for idx, row in df.iterrows():
                if pd.notna(row['target_pc_hex']) and pd.notna(row['target_pc_dec']):
                    try:
                        hex_pc = row['target_pc_hex']
                        if isinstance(hex_pc, str):
                            hex_value = int(hex_pc, 16)
                            if hex_value != row['target_pc_dec']:
                                issues.append(
                                    f"行{idx}: PC地址不一致 ({hex_pc} != {row['target_pc_dec']})"
                                )
                    except (ValueError, TypeError):
                        pass

        return issues
