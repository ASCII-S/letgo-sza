#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
剖析结果可视化脚本

功能：
1. 工作负载分类饼图
2. 计算/访存比对比柱状图
3. 指令分布热图
4. 数据流特征雷达图
5. 套件对比热图
6. 弹性评分排行
"""

import os
import sys
import argparse
from pathlib import Path

# 尝试导入必需的库
try:
    import pandas as pd
    import matplotlib.pyplot as plt
    import seaborn as sns
    import numpy as np
except ImportError as e:
    print(f"错误: 缺少必需的库: {e}")
    print("请安装: pip install pandas matplotlib seaborn numpy")
    sys.exit(1)

# 添加配置路径
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import (
    SUMMARY_DIR, VISUALIZATION_DIR,
    FIGURE_DPI, FIGURE_SIZE, COLOR_SCHEMES, APP_SUITES
)

# 设置中文字体（尝试多种字体）
try:
    plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans', 'Arial Unicode MS']
    plt.rcParams['axes.unicode_minus'] = False
except:
    print("提示: 无法设置中文字体，图表标题可能显示为方块")


class ResultVisualizer:
    """结果可视化器类"""

    def __init__(self, summary_dir=SUMMARY_DIR, output_dir=VISUALIZATION_DIR):
        """
        初始化可视化器

        Args:
            summary_dir: 汇总数据目录
            output_dir: 输出目录
        """
        self.summary_dir = Path(summary_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 加载数据
        self._load_data()

    def _load_data(self):
        """加载汇总数据"""
        metrics_file = self.summary_dir / 'metrics_summary.csv'

        if not metrics_file.exists():
            raise FileNotFoundError(
                f"未找到汇总数据文件: {metrics_file}\n"
                f"请先运行 analyze_results.py 生成汇总数据"
            )

        self.metrics_df = pd.read_csv(metrics_file)
        print(f"加载数据: {len(self.metrics_df)} 个应用")

    def plot_workload_classification(self):
        """工作负载分类饼图"""
        if 'workload_type' not in self.metrics_df.columns:
            print("  跳过: 缺少 workload_type 列")
            return

        fig, ax = plt.subplots(figsize=(10, 8))

        workload_counts = self.metrics_df['workload_type'].value_counts()

        colors = COLOR_SCHEMES['workload'][:len(workload_counts)]
        ax.pie(workload_counts, labels=workload_counts.index, autopct='%1.1f%%',
               colors=colors, startangle=90)
        ax.set_title('Program Workload Type Distribution', fontsize=16, fontweight='bold')

        plt.tight_layout()
        output_file = self.output_dir / 'workload_classification.png'
        plt.savefig(output_file, dpi=FIGURE_DPI, bbox_inches='tight')
        plt.close()

        print(f"✓ {output_file.name}")

    def plot_compute_memory_ratio(self):
        """计算/访存比对比柱状图"""
        if 'compute_memory_ratio' not in self.metrics_df.columns:
            print("  跳过: 缺少 compute_memory_ratio 列")
            return

        df = self.metrics_df[self.metrics_df['compute_memory_ratio'].notna()].copy()
        if len(df) == 0:
            print("  跳过: 无有效数据")
            return

        df = df.sort_values('compute_memory_ratio', ascending=False)

        fig, ax = plt.subplots(figsize=(14, 8))

        # 按套件着色
        colors = []
        suite_color_map = {suite: COLOR_SCHEMES['suite'][i % len(COLOR_SCHEMES['suite'])]
                          for i, suite in enumerate(APP_SUITES.keys())}

        for suite in df['suite']:
            colors.append(suite_color_map.get(suite, 'gray'))

        bars = ax.bar(range(len(df)), df['compute_memory_ratio'], color=colors)

        ax.set_xticks(range(len(df)))
        ax.set_xticklabels(df['app_name'], rotation=45, ha='right')
        ax.set_ylabel('Compute/Memory Ratio', fontsize=12)
        ax.set_title('Application Compute/Memory Ratio Comparison', fontsize=16, fontweight='bold')
        ax.grid(axis='y', alpha=0.3)

        # 添加参考线
        ax.axhline(y=10, color='red', linestyle='--', alpha=0.7, label='Compute-intensive (>10)')
        ax.axhline(y=0.5, color='blue', linestyle='--', alpha=0.7, label='Memory-intensive (<0.5)')
        ax.legend()

        plt.tight_layout()
        output_file = self.output_dir / 'compute_memory_ratio.png'
        plt.savefig(output_file, dpi=FIGURE_DPI, bbox_inches='tight')
        plt.close()

        print(f"✓ {output_file.name}")

    def plot_suite_heatmap(self):
        """套件特征对比热图"""
        # 选择数值列
        numeric_cols = [
            'compute_memory_ratio', 'bytes_per_instruction',
            'value_lifetime_avg', 'value_fanout_avg',
            'register_rewrite_rate', 'branch_bias'
        ]

        available_cols = [col for col in numeric_cols if col in self.metrics_df.columns]

        if len(available_cols) < 2:
            print("  跳过: 数值列不足")
            return

        # 按套件分组计算均值
        suite_means = self.metrics_df.groupby('suite')[available_cols].mean()

        # 归一化（0-1）
        suite_means_norm = (suite_means - suite_means.min()) / (suite_means.max() - suite_means.min())

        fig, ax = plt.subplots(figsize=(12, 6))

        sns.heatmap(suite_means_norm.T, annot=True, fmt='.2f', cmap='RdYlGn',
                   cbar_kws={'label': 'Normalized Value'}, ax=ax)

        ax.set_title('Suite Feature Comparison (Normalized)', fontsize=16, fontweight='bold')
        ax.set_xlabel('Suite', fontsize=12)
        ax.set_ylabel('Feature', fontsize=12)

        plt.tight_layout()
        output_file = self.output_dir / 'suite_heatmap.png'
        plt.savefig(output_file, dpi=FIGURE_DPI, bbox_inches='tight')
        plt.close()

        print(f"✓ {output_file.name}")

    def plot_resilience_ranking(self):
        """弹性评分排行"""
        if 'resilience_score' not in self.metrics_df.columns:
            print("  跳过: 缺少 resilience_score 列")
            return

        df = self.metrics_df[self.metrics_df['resilience_score'].notna()].copy()
        if len(df) == 0:
            print("  跳过: 无有效弹性评分数据")
            return

        df = df.sort_values('resilience_score', ascending=True)  # 升序，底部最低

        fig, ax = plt.subplots(figsize=(10, max(8, len(df) * 0.3)))

        # 根据评分着色
        colors = []
        for score in df['resilience_score']:
            if score >= 70:
                colors.append('#2ecc71')  # 绿色
            elif score >= 50:
                colors.append('#f39c12')  # 橙色
            else:
                colors.append('#e74c3c')  # 红色

        bars = ax.barh(range(len(df)), df['resilience_score'], color=colors)

        ax.set_yticks(range(len(df)))
        ax.set_yticklabels(df['app_name'])
        ax.set_xlabel('Resilience Score', fontsize=12)
        ax.set_title('Application Resilience Score Ranking', fontsize=16, fontweight='bold')
        ax.grid(axis='x', alpha=0.3)

        # 添加评分值标签
        for i, score in enumerate(df['resilience_score']):
            ax.text(score + 1, i, f'{score:.1f}', va='center', fontsize=9)

        # 添加等级线
        ax.axvline(x=70, color='green', linestyle='--', alpha=0.5, label='A (High Resilience)')
        ax.axvline(x=50, color='orange', linestyle='--', alpha=0.5, label='B (Medium)')
        ax.legend(loc='lower right')

        plt.tight_layout()
        output_file = self.output_dir / 'resilience_ranking.png'
        plt.savefig(output_file, dpi=FIGURE_DPI, bbox_inches='tight')
        plt.close()

        print(f"✓ {output_file.name}")

    def plot_dataflow_features(self):
        """数据流特征散点图"""
        if 'value_lifetime_avg' not in self.metrics_df.columns or \
           'value_fanout_avg' not in self.metrics_df.columns:
            print("  跳过: 缺少数据流特征列")
            return

        df = self.metrics_df[['app_name', 'suite', 'value_lifetime_avg', 'value_fanout_avg']].dropna()
        if len(df) == 0:
            print("  跳过: 无有效数据流特征数据")
            return

        fig, ax = plt.subplots(figsize=(12, 8))

        # 按套件着色
        suite_color_map = {suite: COLOR_SCHEMES['suite'][i % len(COLOR_SCHEMES['suite'])]
                          for i, suite in enumerate(APP_SUITES.keys())}

        for suite in APP_SUITES.keys():
            suite_df = df[df['suite'] == suite]
            if len(suite_df) > 0:
                ax.scatter(suite_df['value_lifetime_avg'], suite_df['value_fanout_avg'],
                          label=suite, color=suite_color_map[suite], s=100, alpha=0.6)

        ax.set_xlabel('Value Lifetime (avg)', fontsize=12)
        ax.set_ylabel('Value Fanout (avg)', fontsize=12)
        ax.set_title('Data Flow Characteristics', fontsize=16, fontweight='bold')
        ax.legend()
        ax.grid(alpha=0.3)

        plt.tight_layout()
        output_file = self.output_dir / 'dataflow_features.png'
        plt.savefig(output_file, dpi=FIGURE_DPI, bbox_inches='tight')
        plt.close()

        print(f"✓ {output_file.name}")

    def generate_all_plots(self):
        """生成所有图表"""
        print(f"\n{'='*70}")
        print(f"生成可视化图表")
        print(f"{'='*70}\n")

        plots = [
            ('工作负载分类', self.plot_workload_classification),
            ('计算/访存比对比', self.plot_compute_memory_ratio),
            ('套件特征热图', self.plot_suite_heatmap),
            ('弹性评分排行', self.plot_resilience_ranking),
            ('数据流特征散点图', self.plot_dataflow_features),
        ]

        for name, plot_func in plots:
            try:
                print(f"{name}:")
                plot_func()
            except Exception as e:
                print(f"  错误: {e}")

        print(f"\n{'='*70}")
        print(f"可视化完成！")
        print(f"图表已保存到: {self.output_dir}")
        print(f"{'='*70}\n")


def main():
    parser = argparse.ArgumentParser(
        description='可视化剖析结果',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 生成所有图表
  python visualize.py

  # 指定汇总数据目录
  python visualize.py --summary-dir ./custom_summary

  # 指定输出目录
  python visualize.py --output ./custom_plots
        """
    )

    parser.add_argument('--summary-dir', '-s', type=str, default=SUMMARY_DIR,
                       help=f'汇总数据目录（默认：{SUMMARY_DIR}）')
    parser.add_argument('--output', '-o', type=str, default=VISUALIZATION_DIR,
                       help=f'输出目录（默认：{VISUALIZATION_DIR}）')

    args = parser.parse_args()

    # 创建可视化器并运行
    try:
        visualizer = ResultVisualizer(
            summary_dir=args.summary_dir,
            output_dir=args.output
        )

        visualizer.generate_all_plots()

    except Exception as e:
        print(f"错误: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
