"""
influence_reader.py - 影响力指标读取模块

功能：读取 influence_catalog.csv，根据 PC 地址查询指令的影响力指标
用于在故障注入实验时输出到日志，供 analyze.py 收集

影响力指标包括：
    数据流指标:
        - def_use_dist: 定义到首次使用的距离（指令数）
        - use_count: 被使用次数
        - is_dead: 是否为死定义
        - live_range: 活跃范围

    控制流指标:
        - is_in_loop: 是否在循环内
        - is_control_flow: 是否控制流指令
        - is_mem_write: 是否内存写操作

    综合指标:
        - influence_score: 综合影响力分数 (0-30)
"""

import os
import pandas as pd
import configure


class InfluenceCatalogReader:
    """影响力 catalog 读取器"""

    # 日志输出标记（analyze.py 将解析这些标记）
    LOG_MARKER_START = "=== Influence Metrics ==="
    LOG_MARKER_END = "=== End Influence Metrics ==="

    def __init__(self, catalog_path=None):
        """
        初始化读取器

        Args:
            catalog_path: influence_catalog.csv 的路径，默认从 configure 获取
        """
        if catalog_path is None:
            catalog_path = os.path.join(
                configure.one_batch_folder,
                getattr(configure, 'influence_catalog_name', 'influence_catalog.csv')
            )

        self.catalog_path = catalog_path
        self.catalog_df = None
        self.pc_index = {}  # PC -> DataFrame index 的映射
        self._loaded = False

    def load(self):
        """加载 influence catalog"""
        if not os.path.exists(self.catalog_path):
            print(f"[InfluenceReader] Catalog not found: {self.catalog_path}")
            return False

        try:
            self.catalog_df = pd.read_csv(self.catalog_path)
            # 构建 PC 索引
            for idx, row in self.catalog_df.iterrows():
                pc = int(row['pc'])
                self.pc_index[pc] = idx

            self._loaded = True
            print(f"[InfluenceReader] Loaded {len(self.catalog_df)} instructions from catalog")
            return True
        except Exception as e:
            print(f"[InfluenceReader] Error loading catalog: {e}")
            return False

    def get_metrics(self, pc):
        """
        获取指定 PC 的影响力指标

        Args:
            pc: 指令地址（可以是 int 或 hex 字符串）

        Returns:
            dict: 影响力指标字典，如果未找到返回 None
        """
        if not self._loaded:
            if not self.load():
                return None

        # 转换 PC 为整数
        if isinstance(pc, str):
            if pc.startswith('0x') or pc.startswith('0X'):
                pc = int(pc, 16)
            else:
                pc = int(pc)

        # 查找 PC
        if pc not in self.pc_index:
            return None

        idx = self.pc_index[pc]
        row = self.catalog_df.iloc[idx]

        metrics = {
            'pc': int(row['pc']),
            'mnemonic': row['mnemonic'],
            # 数据流指标
            'def_use_dist': int(row['def_use_dist']),
            'use_count': int(row['use_count']),
            'is_dead': int(row['is_dead']),
            'live_range': int(row['live_range']),
            # 控制流指标
            'is_in_loop': int(row['is_in_loop']),
            'is_control_flow': int(row.get('is_control_flow', 0)),
            'is_mem_write': int(row.get('is_mem_write', 0)),
            # 综合分数
            'influence_score': float(row['influence_score'])
        }

        return metrics

    def print_metrics(self, pc):
        """
        打印指定 PC 的影响力指标（输出到日志）

        格式设计为便于 analyze.py 解析：
        === Influence Metrics ===
        InfPC: 4202512
        InfMnemonic: mov
        DefUseDist: 3
        UseCount: 5
        IsDead: 0
        LiveRange: 47
        IsInLoop: 1
        IsControlFlow: 0
        IsMemWrite: 0
        InfluenceScore: 18.5
        === End Influence Metrics ===

        Args:
            pc: 指令地址
        """
        metrics = self.get_metrics(pc)

        print(self.LOG_MARKER_START)

        if metrics is None:
            print(f"InfPC: {pc}")
            print("InfStatus: NOT_FOUND")
        else:
            print(f"InfPC: {metrics['pc']}")
            print(f"InfMnemonic: {metrics['mnemonic']}")
            print(f"DefUseDist: {metrics['def_use_dist']}")
            print(f"UseCount: {metrics['use_count']}")
            print(f"IsDead: {metrics['is_dead']}")
            print(f"LiveRange: {metrics['live_range']}")
            print(f"IsInLoop: {metrics['is_in_loop']}")
            print(f"IsControlFlow: {metrics['is_control_flow']}")
            print(f"IsMemWrite: {metrics['is_mem_write']}")
            print(f"InfluenceScore: {metrics['influence_score']:.2f}")

        print(self.LOG_MARKER_END)

    def get_statistics(self):
        """获取 catalog 的统计信息"""
        if not self._loaded:
            if not self.load():
                return None

        df = self.catalog_df
        stats = {
            'total': len(df),
            'dead_count': len(df[df['is_dead'] == 1]),
            'loop_count': len(df[df['is_in_loop'] == 1]),
            'avg_score': df['influence_score'].mean(),
            'max_score': df['influence_score'].max(),
            'min_score': df['influence_score'].min(),
        }
        return stats


# 全局单例
_global_reader = None

def get_influence_reader():
    """获取全局影响力读取器实例"""
    global _global_reader
    if _global_reader is None:
        _global_reader = InfluenceCatalogReader()
    return _global_reader


def print_influence_metrics(pc):
    """便捷函数：打印指定 PC 的影响力指标"""
    reader = get_influence_reader()
    reader.print_metrics(pc)


def get_influence_metrics(pc):
    """便捷函数：获取指定 PC 的影响力指标"""
    reader = get_influence_reader()
    return reader.get_metrics(pc)


if __name__ == "__main__":
    # 测试代码
    reader = InfluenceCatalogReader()
    if reader.load():
        stats = reader.get_statistics()
        print(f"Catalog Statistics:")
        print(f"  Total instructions: {stats['total']}")
        print(f"  Dead definitions: {stats['dead_count']}")
        print(f"  In loops: {stats['loop_count']}")
        print(f"  Avg score: {stats['avg_score']:.2f}")
        print(f"  Score range: {stats['min_score']:.2f} ~ {stats['max_score']:.2f}")
