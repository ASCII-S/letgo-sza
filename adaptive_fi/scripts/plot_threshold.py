#!/usr/bin/env python3
"""
自适应注错阈值模拟 - 绘图脚本

基于 threshold_simulation.py 生成的CSV数据绘制图表。

支持：
- 单应用双Y轴折线图（崩溃率 + 指令丰富度）
- 所有应用汇总对比图

用法:
    # 绘制所有图表（单应用 + 汇总）
    python plot_threshold.py

    # 仅绘制指定应用
    python plot_threshold.py --apps 2mm bicg bt

    # 仅绘制汇总图
    python plot_threshold.py --summary-only

    # 指定数据目录
    python plot_threshold.py --data-dir ./my_data
"""

import csv
import argparse
from pathlib import Path
from collections import defaultdict

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# 默认路径
DEFAULT_DATA_DIR = Path(__file__).resolve().parent.parent / 'threshold_analysis'

# 绘图风格
plt.rcParams['font.sans-serif'] = ['DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

COLOR_CRASH = '#1f77b4'
COLOR_RICHNESS = '#d62728'


def load_per_app_csv(csv_path: Path) -> list:
    """加载单应用CSV数据。"""
    rows = []
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append({
                'threshold_pct': int(row['threshold_pct']),
                'selected_count': int(row['selected_count']),
                'total_injections': int(row['total_injections']),
                'total_crashes': int(row['total_crashes']),
                'overall_crash_rate': float(row['overall_crash_rate']),
                'unique_disasm_count': int(row['unique_disasm_count']),
            })
    return rows


def load_summary_csv(csv_path: Path) -> dict:
    """加载汇总CSV，返回 {benchmark: [rows]} 字典。"""
    data = defaultdict(list)
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row['benchmark']
            data[name].append({
                'threshold_pct': int(row['threshold_pct']),
                'selected_count': int(row['selected_count']),
                'total_injections': int(row['total_injections']),
                'total_crashes': int(row['total_crashes']),
                'overall_crash_rate': float(row['overall_crash_rate']),
                'unique_disasm_count': int(row['unique_disasm_count']),
            })
    return dict(data)


def plot_single_app(rows: list, benchmark_name: str, output_path: Path):
    """绘制单应用双Y轴折线图。"""
    thresholds = [r['threshold_pct'] for r in rows]
    crash_rates = [r['overall_crash_rate'] * 100 for r in rows]
    disasm_counts = [r['unique_disasm_count'] for r in rows]

    fig, ax1 = plt.subplots(figsize=(10, 6))

    # 左Y轴：崩溃率
    ax1.set_xlabel('Threshold (%)', fontsize=13)
    ax1.set_ylabel('Overall Crash Rate (%)', fontsize=13, color=COLOR_CRASH)
    line1, = ax1.plot(thresholds, crash_rates, color=COLOR_CRASH, marker='o',
                      linewidth=2, markersize=7, label='Crash Rate')
    ax1.tick_params(axis='y', labelcolor=COLOR_CRASH)
    ax1.set_xticks(thresholds)

    for x, y in zip(thresholds, crash_rates):
        ax1.annotate(f'{y:.1f}%', (x, y), textcoords='offset points',
                     xytext=(0, 10), ha='center', fontsize=8, color=COLOR_CRASH)

    # 右Y轴：指令丰富度
    ax2 = ax1.twinx()
    ax2.set_ylabel('Instruction Richness (Unique Disasm Count)',
                   fontsize=13, color=COLOR_RICHNESS)
    line2, = ax2.plot(thresholds, disasm_counts, color=COLOR_RICHNESS, marker='s',
                      linewidth=2, markersize=7, label='Instruction Richness')
    ax2.tick_params(axis='y', labelcolor=COLOR_RICHNESS)

    for x, y in zip(thresholds, disasm_counts):
        ax2.annotate(str(y), (x, y), textcoords='offset points',
                     xytext=(0, -14), ha='center', fontsize=8, color=COLOR_RICHNESS)

    lines = [line1, line2]
    labels = [l.get_label() for l in lines]
    ax1.legend(lines, labels, loc='upper left', fontsize=10)
    ax1.set_title(f'{benchmark_name} - Adaptive FI Threshold Analysis',
                  fontsize=15, pad=12)
    ax1.grid(True, alpha=0.3)

    plt.tight_layout()
    fig.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close(fig)


def plot_summary_crash_rate(all_data: dict, output_path: Path):
    """绘制所有应用的崩溃率随阈值变化的汇总折线图。"""
    fig, ax = plt.subplots(figsize=(14, 8))

    names = sorted(all_data.keys())
    cmap = plt.cm.get_cmap('tab20', len(names))

    for i, name in enumerate(names):
        rows = all_data[name]
        thresholds = [r['threshold_pct'] for r in rows]
        crash_rates = [r['overall_crash_rate'] * 100 for r in rows]
        ax.plot(thresholds, crash_rates, marker='o', markersize=4,
                linewidth=1.5, color=cmap(i), label=name)

    ax.set_xlabel('Threshold (%)', fontsize=13)
    ax.set_ylabel('Overall Crash Rate (%)', fontsize=13)
    ax.set_title('All Benchmarks - Crash Rate vs Threshold', fontsize=15, pad=12)
    ax.set_xticks(list(range(0, 100, 10)))
    ax.grid(True, alpha=0.3)
    ax.legend(bbox_to_anchor=(1.02, 1), loc='upper left', fontsize=8,
              ncol=1, borderaxespad=0)

    plt.tight_layout()
    fig.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close(fig)


def plot_summary_richness(all_data: dict, output_path: Path):
    """绘制所有应用的指令丰富度随阈值变化的汇总折线图。"""
    fig, ax = plt.subplots(figsize=(14, 8))

    names = sorted(all_data.keys())
    cmap = plt.cm.get_cmap('tab20', len(names))

    for i, name in enumerate(names):
        rows = all_data[name]
        thresholds = [r['threshold_pct'] for r in rows]
        disasm_counts = [r['unique_disasm_count'] for r in rows]
        ax.plot(thresholds, disasm_counts, marker='s', markersize=4,
                linewidth=1.5, color=cmap(i), label=name)

    ax.set_xlabel('Threshold (%)', fontsize=13)
    ax.set_ylabel('Instruction Richness (Unique Disasm Count)', fontsize=13)
    ax.set_title('All Benchmarks - Instruction Richness vs Threshold',
                 fontsize=15, pad=12)
    ax.set_xticks(list(range(0, 100, 10)))
    ax.grid(True, alpha=0.3)
    ax.legend(bbox_to_anchor=(1.02, 1), loc='upper left', fontsize=8,
              ncol=1, borderaxespad=0)

    plt.tight_layout()
    fig.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close(fig)


def plot_summary_normalized(all_data: dict, output_path: Path):
    """
    绘制归一化汇总图：以阈值=0%为基准，展示各应用的
    崩溃率变化倍数和指令丰富度保留比例。
    """
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 7))

    names = sorted(all_data.keys())
    cmap = plt.cm.get_cmap('tab20', len(names))

    for i, name in enumerate(names):
        rows = all_data[name]
        base_cr = rows[0]['overall_crash_rate']
        base_disasm = rows[0]['unique_disasm_count']
        if base_cr == 0 or base_disasm == 0:
            continue

        thresholds = [r['threshold_pct'] for r in rows]
        # 崩溃率相对变化
        cr_ratio = [r['overall_crash_rate'] / base_cr for r in rows]
        # 指令丰富度保留比例
        disasm_ratio = [r['unique_disasm_count'] / base_disasm for r in rows]

        ax1.plot(thresholds, cr_ratio, marker='o', markersize=3,
                 linewidth=1.2, color=cmap(i), label=name)
        ax2.plot(thresholds, disasm_ratio, marker='s', markersize=3,
                 linewidth=1.2, color=cmap(i), label=name)

    ax1.set_xlabel('Threshold (%)', fontsize=12)
    ax1.set_ylabel('Crash Rate Ratio (vs 0%)', fontsize=12)
    ax1.set_title('Crash Rate Change Ratio', fontsize=14)
    ax1.set_xticks(list(range(0, 100, 10)))
    ax1.axhline(y=1.0, color='gray', linestyle='--', alpha=0.5)
    ax1.grid(True, alpha=0.3)

    ax2.set_xlabel('Threshold (%)', fontsize=12)
    ax2.set_ylabel('Richness Retention Ratio (vs 0%)', fontsize=12)
    ax2.set_title('Instruction Richness Retention', fontsize=14)
    ax2.set_xticks(list(range(0, 100, 10)))
    ax2.axhline(y=1.0, color='gray', linestyle='--', alpha=0.5)
    ax2.grid(True, alpha=0.3)

    # 共享图例
    handles, labels = ax1.get_legend_handles_labels()
    fig.legend(handles, labels, bbox_to_anchor=(0.5, -0.02), loc='upper center',
               fontsize=7, ncol=7, borderaxespad=0)

    fig.suptitle('All Benchmarks - Normalized Threshold Analysis',
                 fontsize=16, y=1.02)
    plt.tight_layout()
    fig.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(
        description='自适应注错阈值模拟 - 绘图')
    parser.add_argument(
        '--data-dir',
        default=str(DEFAULT_DATA_DIR),
        help=f'CSV数据目录（默认: {DEFAULT_DATA_DIR}）')
    parser.add_argument(
        '--apps', nargs='+', default=None,
        help='仅绘制指定的benchmark（如: --apps 2mm bicg bt）')
    parser.add_argument(
        '--summary-only', action='store_true',
        help='仅绘制汇总图，跳过单应用图')
    args = parser.parse_args()

    data_dir = Path(args.data_dir).resolve()
    if not data_dir.exists():
        print(f"错误: 数据目录不存在: {data_dir}")
        print("请先运行 threshold_simulation.py 收集数据")
        return

    # 绘制单应用图
    if not args.summary_only:
        csv_files = sorted(data_dir.glob('*_threshold_simulation.csv'))
        csv_files = [f for f in csv_files
                     if f.name != 'all_benchmarks_threshold_simulation.csv']

        if args.apps:
            csv_files = [f for f in csv_files
                         if f.stem.replace('_threshold_simulation', '') in args.apps]

        for csv_path in csv_files:
            name = csv_path.stem.replace('_threshold_simulation', '')
            rows = load_per_app_csv(csv_path)
            if not rows:
                continue
            png_path = data_dir / f"{name}_threshold_analysis.png"
            plot_single_app(rows, name, png_path)
            print(f"[{name}] 图表已保存: {png_path}")

    # 绘制汇总图
    summary_csv = data_dir / 'all_benchmarks_threshold_simulation.csv'
    if summary_csv.exists():
        all_data = load_summary_csv(summary_csv)

        if args.apps:
            all_data = {k: v for k, v in all_data.items() if k in args.apps}

        if all_data:
            p1 = data_dir / 'summary_crash_rate.png'
            plot_summary_crash_rate(all_data, p1)
            print(f"汇总图(崩溃率)已保存: {p1}")

            p2 = data_dir / 'summary_instruction_richness.png'
            plot_summary_richness(all_data, p2)
            print(f"汇总图(指令丰富度)已保存: {p2}")

            p3 = data_dir / 'summary_normalized.png'
            plot_summary_normalized(all_data, p3)
            print(f"汇总图(归一化)已保存: {p3}")
        else:
            print("无汇总数据可绘制")
    else:
        print(f"未找到汇总CSV: {summary_csv}")
        print("请先运行 threshold_simulation.py 收集数据")

    print("\n绘图完成")


if __name__ == '__main__':
    main()
