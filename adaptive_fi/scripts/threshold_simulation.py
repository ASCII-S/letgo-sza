#!/usr/bin/env python3
"""
自适应注错阈值模拟 - 数据收集脚本

基于阈值=0（全遍历）的实验数据，模拟不同阈值（0%~90%）下的注错结果，
将模拟数据保存为CSV文件。

支持：
- 单个benchmark模拟
- 批量处理所有benchmark并生成汇总CSV

用法:
    # 批量处理所有benchmark（默认）
    python threshold_simulation.py

    # 处理指定的benchmark
    python threshold_simulation.py --apps 2mm bicg bt

    # 指定输出目录
    python threshold_simulation.py --output-dir ./my_output
"""

import json
import csv
import argparse
from pathlib import Path
from collections import defaultdict


# 项目根目录
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
RESULT_DIR = PROJECT_ROOT / 'TargetedBenchmarkResult'
DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent.parent / 'threshold_analysis'
COLLECTED_CSV = Path(__file__).resolve().parent.parent / 'collected_results.csv'

THRESHOLDS = [i / 100.0 for i in range(0, 100, 10)]

CSV_FIELDS_PER_APP = [
    'threshold_pct', 'selected_count', 'total_injections',
    'total_crashes', 'overall_crash_rate', 'unique_disasm_count', 'unique_crash_pc_count',
]

CSV_FIELDS_SUMMARY = [
    'benchmark', 'threshold_pct', 'selected_count', 'total_injections',
    'total_crashes', 'overall_crash_rate', 'unique_disasm_count', 'unique_crash_pc_count',
]


def load_crash_data(csv_path: Path) -> dict:
    """
    加载 collected_results.csv，构建 {app_name: {offset_suffix: [(crash_pc, crash_inst)]}} 索引。
    只保留有崩溃信号的记录的崩溃点地址和指令。

    注意：offset使用地址后缀匹配（去掉0x前缀后的部分），因为depth report中的offset
    是短地址（如0x24c4），而CSV中的inj_pc是完整地址（如0x4024c4）。
    """
    crash_index = defaultdict(lambda: defaultdict(list))

    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            app = row['app_name']
            inj_pc = row['inj_pc']
            sig1pc = row.get('Sig1pc', '').strip()
            sig1ins = row.get('Sig1ins', '').strip()

            # 只统计有崩溃信号的记录
            if row.get('Sig1') and sig1pc:
                # 提取地址后缀（去掉0x）用于匹配
                if inj_pc.startswith('0x'):
                    addr_suffix = inj_pc[2:].lower()
                    crash_index[app][addr_suffix].append((sig1pc, sig1ins))

    return dict(crash_index)


def load_depth_reports(benchmark_dir: Path) -> dict:
    """加载所有 adaptive_fi_depth{d}_report.json 文件。"""
    reports = {}
    d = 0
    while True:
        path = benchmark_dir / f"adaptive_fi_depth{d}_report.json"
        if not path.exists():
            break
        with open(path, 'r') as f:
            data = json.load(f)
        reports[d] = data['targets']
        d += 1
    return reports


def build_offset_max_crash_rate(targets: list) -> dict:
    """为某一层的 targets 构建 offset -> max_crash_rate 索引。"""
    index = {}
    for t in targets:
        offset = t['offset']
        cr = t.get('crash_rate', 0.0)
        if offset not in index or cr > index[offset]:
            index[offset] = cr
    return index


def simulate_threshold(reports: dict, threshold: float, crash_data: dict, app_name: str) -> dict:
    """
    模拟给定阈值下的注错结果。

    - depth0 全选
    - depth>=1：parent_offset 在上一层的 max crash_rate >= 阈值才选中
    - 递归：parent 被过滤则子树也不再探索
    - 统计崩溃点指令丰富度（从 crash_data 中提取）
    """
    max_depth = max(reports.keys())
    selected_targets = []

    # depth0 全选
    depth0_targets = reports.get(0, [])
    selected_targets.extend(depth0_targets)
    prev_offset_index = build_offset_max_crash_rate(depth0_targets)

    for d in range(1, max_depth + 1):
        current_targets = reports.get(d, [])
        current_selected = []

        for t in current_targets:
            parent_offset = t.get('parent_offset')
            if parent_offset is None:
                continue

            parent_max_cr = prev_offset_index.get(parent_offset, None)
            if parent_max_cr is None:
                continue

            if parent_max_cr >= threshold:
                current_selected.append(t)

        selected_targets.extend(current_selected)
        prev_offset_index = build_offset_max_crash_rate(current_selected)

    # 计算指标
    total_injection = sum(t.get('injection_count', 0) for t in selected_targets)
    total_crash = sum(t.get('crash_count', 0) for t in selected_targets)

    # 统计崩溃点指令丰富度和地址多样性
    unique_crash_instructions = set()
    unique_crash_pcs = set()
    app_crash_data = crash_data.get(app_name, {})

    for t in selected_targets:
        offset = t['offset']
        # 提取offset后缀用于匹配（去掉0x）
        if offset.startswith('0x'):
            offset_suffix = offset[2:].lower()
            # 尝试后缀匹配：CSV中的地址可能包含基地址
            for addr_suffix, crash_records in app_crash_data.items():
                if addr_suffix.endswith(offset_suffix):
                    for crash_pc, crash_inst in crash_records:
                        unique_crash_pcs.add(crash_pc)
                        if crash_inst:
                            unique_crash_instructions.add(crash_inst)

    overall_crash_rate = total_crash / total_injection if total_injection > 0 else 0.0

    return {
        'selected_count': len(selected_targets),
        'total_injections': total_injection,
        'total_crashes': total_crash,
        'overall_crash_rate': overall_crash_rate,
        'unique_disasm_count': len(unique_crash_instructions),
        'unique_crash_pc_count': len(unique_crash_pcs),
    }


def run_simulation(benchmark_dir: Path, app_name: str, crash_data: dict) -> list:
    """对所有阈值运行模拟，返回结果列表。"""
    reports = load_depth_reports(benchmark_dir)
    if not reports:
        return []

    results = []
    for th in THRESHOLDS:
        result = simulate_threshold(reports, th, crash_data, app_name)
        result['threshold'] = th
        result['threshold_pct'] = int(th * 100)
        results.append(result)

    return results


def save_per_app_csv(results: list, output_path: Path):
    """保存单个benchmark的模拟结果到CSV。"""
    with open(output_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS_PER_APP)
        writer.writeheader()
        for r in results:
            writer.writerow({k: r[k] for k in CSV_FIELDS_PER_APP})


def find_benchmarks(result_dir: Path, app_filter: list = None) -> list:
    """扫描 TargetedBenchmarkResult 目录，找到所有含 adaptive 数据的 benchmark。"""
    benchmarks = []
    for d in sorted(result_dir.iterdir()):
        if not d.is_dir():
            continue
        adaptive_dir = d / 'adaptive'
        if not adaptive_dir.exists():
            continue
        # 至少有 depth0 report
        if not (adaptive_dir / 'adaptive_fi_depth0_report.json').exists():
            continue
        name = d.name
        if app_filter and name not in app_filter:
            continue
        benchmarks.append((name, adaptive_dir))
    return benchmarks


def main():
    parser = argparse.ArgumentParser(
        description='自适应注错阈值模拟 - 数据收集')
    parser.add_argument(
        '--result-dir',
        default=str(RESULT_DIR),
        help=f'TargetedBenchmarkResult 根目录（默认: {RESULT_DIR}）')
    parser.add_argument(
        '--output-dir',
        default=str(DEFAULT_OUTPUT_DIR),
        help=f'输出目录（默认: {DEFAULT_OUTPUT_DIR}）')
    parser.add_argument(
        '--apps', nargs='+', default=None,
        help='仅处理指定的benchmark（如: --apps 2mm bicg bt）')
    parser.add_argument(
        '--crash-csv',
        default=str(COLLECTED_CSV),
        help=f'崩溃数据CSV路径（默认: {COLLECTED_CSV}）')
    args = parser.parse_args()

    result_dir = Path(args.result_dir).resolve()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    crash_csv_path = Path(args.crash_csv).resolve()
    if not crash_csv_path.exists():
        print(f"错误: 崩溃数据CSV不存在: {crash_csv_path}")
        return

    benchmarks = find_benchmarks(result_dir, args.apps)
    if not benchmarks:
        print("未找到任何有效的benchmark数据")
        return

    print(f"找到 {len(benchmarks)} 个benchmark")
    print(f"输出目录: {output_dir}")
    print(f"加载崩溃数据: {crash_csv_path}")

    # 加载崩溃数据
    crash_data = load_crash_data(crash_csv_path)
    print(f"已加载 {len(crash_data)} 个应用的崩溃数据")
    print()

    # 汇总数据
    all_rows = []
    success_count = 0

    for name, adaptive_dir in benchmarks:
        print(f"[{name}] 处理中...")
        results = run_simulation(adaptive_dir, name, crash_data)
        if not results:
            print(f"  跳过: 无有效数据")
            continue

        # 保存单应用CSV
        csv_path = output_dir / f"{name}_threshold_simulation.csv"
        save_per_app_csv(results, csv_path)

        # 打印摘要
        r0 = results[0]  # 阈值=0%
        r9 = results[-1]  # 阈值=90%
        print(f"  depths: {len(load_depth_reports(adaptive_dir))}, "
              f"targets(0%): {r0['selected_count']}, "
              f"targets(90%): {r9['selected_count']}, "
              f"crash_rate: {r0['overall_crash_rate']:.2%} -> {r9['overall_crash_rate']:.2%}")

        # 汇入汇总
        for r in results:
            row = {'benchmark': name}
            row.update({k: r[k] for k in CSV_FIELDS_PER_APP})
            all_rows.append(row)

        success_count += 1

    # 保存汇总CSV
    if all_rows:
        summary_path = output_dir / "all_benchmarks_threshold_simulation.csv"
        with open(summary_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=CSV_FIELDS_SUMMARY)
            writer.writeheader()
            writer.writerows(all_rows)
        print(f"\n汇总CSV已保存: {summary_path}")

    print(f"\n完成: {success_count}/{len(benchmarks)} 个benchmark处理成功")


if __name__ == '__main__':
    main()
