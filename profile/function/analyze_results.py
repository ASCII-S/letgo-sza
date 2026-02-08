#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
函数剖析结果分析脚本 (v3.0)

适配function_profiler 3.0版本的JSON结构
功能：
1. 收集所有JSON结果
2. 提取关键指标（A-E类，可选F/G类）
3. 识别热点函数（高调用次数）
4. 识别访存密集函数（高内存访问）
5. 识别计算密集函数（高算术/浮点指令）
6. 分析函数复杂度
7. 生成汇总报告
"""

import os
import sys
import json
import argparse
from datetime import datetime
from pathlib import Path
from collections import defaultdict

# 添加配置路径
profile_home = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, profile_home)
from config import (
    FUNCTION_RAW_JSON_DIR, FUNCTION_SUMMARY_DIR,
    get_app_suite, APP_SUITES
)


class FunctionResultAnalyzer:
    """函数剖析结果分析器 (v3.0)"""

    def __init__(self):
        """初始化分析器"""
        self.raw_json_dir = FUNCTION_RAW_JSON_DIR
        self.summary_dir = FUNCTION_SUMMARY_DIR

        # 数据存储
        self.all_functions = []  # 所有函数的列表
        self.app_metrics = {}  # 应用级汇总指标
        self.suite_metrics = defaultdict(lambda: {
            'app_count': 0,
            'total_functions': 0,
            'avg_call_exec': 0,
            'avg_mem_access_ratio': 0,
            'avg_branch_density': 0,
            'avg_arith_density': 0
        })

    def collect_json_files(self):
        """收集所有JSON结果文件"""
        print("\n收集JSON文件中...")

        json_files = []
        for root, dirs, files in os.walk(self.raw_json_dir):
            for file in files:
                if file.endswith('_function_profile.json'):
                    json_files.append(os.path.join(root, file))

        print(f"找到 {len(json_files)} 个JSON文件")
        return json_files

    def extract_metrics_from_json(self, json_files):
        """从JSON文件提取指标（v3.0格式）"""
        print("\n提取指标中...")

        for json_file in json_files:
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # 获取应用名称和套件
                filename = os.path.basename(json_file)
                app_name = filename.replace('_function_profile.json', '')
                suite = get_app_suite(app_name)

                # 提取函数列表
                functions = data.get('functions', [])

                # 处理应用级指标
                app_metrics = {
                    'app_name': app_name,
                    'suite': suite,
                    'total_functions': len(functions),
                    'functions': []
                }

                # 处理每个函数
                for func in functions:
                    # 执行统计 (A类)
                    exec_stats = func.get('execution_stats', {})
                    # 数据流 (B1类)
                    data_flow = func.get('data_flow', {})
                    # 内存访问模式 (B1.5类)
                    mem_pattern = func.get('memory_access_pattern', {})
                    # 计算特性 (B2类)
                    compute = func.get('compute_characteristics', {})
                    # 控制流 (C类)
                    control_flow = func.get('control_flow', {})
                    # 寄存器使用 (D类)
                    reg_usage = func.get('register_usage', {})
                    # 控制流细化 (E类)
                    control_detail = func.get('control_flow_detail', {})
                    # 可选：数据依赖 (F类)
                    data_dep = func.get('data_dependency', {})
                    # 可选：生命周期 (G类)
                    lifetime = func.get('lifetime', {})

                    # 计算派生指标
                    inst_exec = exec_stats.get('inst_exec', 0)
                    inst_static = exec_stats.get('inst_static', 1)  # 避免除零
                    mem_read_exec = data_flow.get('mem_read_exec', 0)
                    mem_write_exec = data_flow.get('mem_write_exec', 0)
                    mem_access_ratio = (mem_read_exec + mem_write_exec) / inst_exec if inst_exec > 0 else 0
                    branch_density = control_flow.get('branch_static', 0) / inst_static if inst_static > 0 else 0
                    arith_density = compute.get('arith_static', 0) / inst_static if inst_static > 0 else 0

                    func_record = {
                        'app_name': app_name,
                        'suite': suite,
                        'function_name': func.get('function_name', 'unknown'),

                        # A类：执行统计
                        'call_exec': exec_stats.get('call_exec', 0),
                        'inst_exec': inst_exec,
                        'inst_static': inst_static,

                        # B1类：数据流
                        'mem_read_exec': mem_read_exec,
                        'mem_write_exec': mem_write_exec,
                        'mem_inst_exec': data_flow.get('mem_inst_exec', 0),
                        'mem_access_ratio': mem_access_ratio,

                        # B1.5类：内存访问模式
                        'seq_read_exec': mem_pattern.get('seq_read_exec', 0),
                        'stride_read_exec': mem_pattern.get('stride_read_exec', 0),
                        'random_read_exec': mem_pattern.get('random_read_exec', 0),
                        'seq_write_exec': mem_pattern.get('seq_write_exec', 0),
                        'stride_write_exec': mem_pattern.get('stride_write_exec', 0),
                        'random_write_exec': mem_pattern.get('random_write_exec', 0),

                        # B2类：计算特性
                        'arith_static': compute.get('arith_static', 0),
                        'logic_static': compute.get('logic_static', 0),
                        'float_static': compute.get('float_static', 0),
                        'simd_static': compute.get('simd_static', 0),
                        'arith_exec': compute.get('arith_exec', 0),
                        'float_exec': compute.get('float_exec', 0),
                        'arith_density': arith_density,

                        # C类：控制流
                        'branch_static': control_flow.get('branch_static', 0),
                        'branch_exec': control_flow.get('branch_exec', 0),
                        'branch_density': branch_density,
                        'loop_static': control_flow.get('loop_static', 0),
                        'return_static': control_flow.get('return_static', 0),
                        'call_static': control_flow.get('call_static', 0),
                        'indirect_exec': control_flow.get('indirect_exec', 0),

                        # D类：寄存器使用
                        'reg_read_exec': reg_usage.get('reg_read_exec', 0),
                        'reg_write_exec': reg_usage.get('reg_write_exec', 0),
                        'unique_reg_read': reg_usage.get('unique_reg_read', 0),
                        'unique_reg_write': reg_usage.get('unique_reg_write', 0),

                        # E类：控制流细化
                        'branch_taken_exec': control_detail.get('branch_taken_exec', 0),
                        'branch_not_taken_exec': control_detail.get('branch_not_taken_exec', 0),
                        'loop_iter_total': control_detail.get('loop_iter_total', 0),
                        'call_depth_max': control_detail.get('call_depth_max', 0),

                        # F类（可选）：数据依赖
                        'def_use_pairs': data_dep.get('def_use_pairs', 0),
                        'reg_dep_chain_max': data_dep.get('reg_dep_chain_max', 0),

                        # G类（可选）：生命周期
                        'reg_lifetime_total': lifetime.get('reg_lifetime_total', 0),
                        'dead_write_exec': lifetime.get('dead_write_exec', 0)
                    }

                    self.all_functions.append(func_record)
                    app_metrics['functions'].append(func_record)

                # 计算应用级统计
                if functions:
                    call_execs = [f['call_exec'] for f in app_metrics['functions']]
                    mem_ratios = [f['mem_access_ratio'] for f in app_metrics['functions']]
                    branch_densities = [f['branch_density'] for f in app_metrics['functions']]
                    arith_densities = [f['arith_density'] for f in app_metrics['functions']]

                    app_metrics['avg_call_exec'] = sum(call_execs) / len(call_execs)
                    app_metrics['max_call_exec'] = max(call_execs)
                    app_metrics['avg_mem_access_ratio'] = sum(mem_ratios) / len(mem_ratios)
                    app_metrics['max_mem_access_ratio'] = max(mem_ratios)
                    app_metrics['avg_branch_density'] = sum(branch_densities) / len(branch_densities)
                    app_metrics['avg_arith_density'] = sum(arith_densities) / len(arith_densities)

                self.app_metrics[app_name] = app_metrics

                # 更新套件级统计
                self.suite_metrics[suite]['app_count'] += 1
                self.suite_metrics[suite]['total_functions'] += len(functions)

            except Exception as e:
                print(f"  警告: 无法处理 {json_file}: {e}")

        print(f"成功处理 {len(self.app_metrics)} 个应用，{len(self.all_functions)} 个函数")

    def identify_hotspot_functions(self, top_n=20):
        """识别热点函数（高调用次数）"""
        print(f"\n识别热点函数（Top {top_n})...")

        sorted_funcs = sorted(
            self.all_functions,
            key=lambda x: x['call_exec'],
            reverse=True
        )

        return sorted_funcs[:top_n]

    def identify_memory_intensive_functions(self, top_n=20):
        """识别访存密集函数（高内存访问比）"""
        print(f"\n识别访存密集函数（Top {top_n})...")

        sorted_funcs = sorted(
            [f for f in self.all_functions if f['mem_access_ratio'] > 0],
            key=lambda x: x['mem_access_ratio'],
            reverse=True
        )

        return sorted_funcs[:top_n]

    def identify_compute_intensive_functions(self, top_n=20):
        """识别计算密集函数（高算术/浮点指令密度）"""
        print(f"\n识别计算密集函数（Top {top_n})...")

        # 综合评分：算术密度 + 浮点密度
        for func in self.all_functions:
            inst_static = func['inst_static'] or 1
            arith_score = func['arith_static'] / inst_static
            float_score = func['float_static'] / inst_static
            func['compute_score'] = arith_score + float_score * 2  # 浮点指令权重更高

        sorted_funcs = sorted(
            [f for f in self.all_functions if f.get('compute_score', 0) > 0],
            key=lambda x: x.get('compute_score', 0),
            reverse=True
        )

        return sorted_funcs[:top_n]

    def analyze_function_complexity(self, top_n=20):
        """分析函数复杂度（基于控制流）"""
        print(f"\n分析函数复杂度（Top {top_n})...")

        # 复杂度 = 分支密度 + 循环数（归一化） + 调用深度（归一化）
        max_loop = max([f['loop_static'] for f in self.all_functions]) or 1
        max_depth = max([f['call_depth_max'] for f in self.all_functions]) or 1

        for func in self.all_functions:
            func['complexity_score'] = (
                func['branch_density'] +
                (func['loop_static'] / max_loop) +
                (func['call_depth_max'] / max_depth)
            )

        sorted_funcs = sorted(
            self.all_functions,
            key=lambda x: x['complexity_score'],
            reverse=True
        )

        return sorted_funcs[:top_n]

    def generate_reports(self):
        """生成汇总报告"""
        print("\n生成汇总报告中...")

        # 1. 函数级详细指标CSV
        self._generate_metrics_csv()

        # 2. 热点函数报告
        hotspot_funcs = self.identify_hotspot_functions(top_n=20)
        self._generate_hotspot_report(hotspot_funcs)

        # 3. 访存密集函数报告
        memory_funcs = self.identify_memory_intensive_functions(top_n=20)
        self._generate_memory_intensive_report(memory_funcs)

        # 4. 计算密集函数报告
        compute_funcs = self.identify_compute_intensive_functions(top_n=20)
        self._generate_compute_intensive_report(compute_funcs)

        # 5. 函数复杂度报告
        complexity_funcs = self.analyze_function_complexity(top_n=20)
        self._generate_complexity_report(complexity_funcs)

        # 6. 套件对比报告
        self._generate_suite_comparison_report()

    def _generate_metrics_csv(self):
        """生成函数级详细指标CSV"""
        csv_file = os.path.join(self.summary_dir, 'function_metrics_summary.csv')

        try:
            import csv
            with open(csv_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=[
                    'app_name', 'suite', 'function_name', 'call_exec',
                    'inst_exec', 'inst_static', 'mem_access_ratio',
                    'branch_density', 'loop_static', 'arith_density',
                    'unique_reg_read', 'unique_reg_write', 'call_depth_max'
                ])
                writer.writeheader()

                for func in self.all_functions:
                    writer.writerow({
                        'app_name': func['app_name'],
                        'suite': func['suite'],
                        'function_name': func['function_name'],
                        'call_exec': func['call_exec'],
                        'inst_exec': func['inst_exec'],
                        'inst_static': func['inst_static'],
                        'mem_access_ratio': f"{func['mem_access_ratio']:.4f}",
                        'branch_density': f"{func['branch_density']:.4f}",
                        'loop_static': func['loop_static'],
                        'arith_density': f"{func['arith_density']:.4f}",
                        'unique_reg_read': func['unique_reg_read'],
                        'unique_reg_write': func['unique_reg_write'],
                        'call_depth_max': func['call_depth_max']
                    })

            print(f"  函数指标CSV: {csv_file}")

        except Exception as e:
            print(f"  警告: 无法生成CSV: {e}")

    def _generate_hotspot_report(self, hotspot_funcs):
        """生成热点函数报告"""
        report_file = os.path.join(self.summary_dir, 'hotspot_functions.txt')

        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("="*80 + "\n")
            f.write("热点函数分析 (按调用次数排序 - call_exec)\n")
            f.write("="*80 + "\n\n")
            f.write(f"生成时间: {datetime.now().isoformat()}\n")
            f.write(f"总计: {len(self.all_functions)} 个函数，显示Top {len(hotspot_funcs)}\n\n")

            f.write(f"{'排名':<5} {'应用':<15} {'函数名':<30} {'调用次数':<10} {'执行指令数':<12}\n")
            f.write("-"*80 + "\n")

            for i, func in enumerate(hotspot_funcs, 1):
                f.write(f"{i:<5} {func['app_name'][:14]:<15} {func['function_name'][:29]:<30} "
                       f"{func['call_exec']:<10} {func['inst_exec']:<12}\n")

            f.write("\n" + "="*80 + "\n")
            f.write("详细信息\n")
            f.write("="*80 + "\n\n")

            for i, func in enumerate(hotspot_funcs, 1):
                f.write(f"{i}. {func['function_name']} ({func['app_name']})\n")
                f.write(f"   调用次数: {func['call_exec']}\n")
                f.write(f"   执行指令数: {func['inst_exec']}\n")
                f.write(f"   静态指令数: {func['inst_static']}\n")
                f.write(f"   内存访问比: {func['mem_access_ratio']:.4f}\n")
                f.write(f"   分支密度: {func['branch_density']:.4f}\n")
                f.write("\n")

        print(f"  热点函数报告: {report_file}")

    def _generate_memory_intensive_report(self, memory_funcs):
        """生成访存密集函数报告"""
        report_file = os.path.join(self.summary_dir, 'memory_intensive_functions.txt')

        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("="*80 + "\n")
            f.write("访存密集函数分析 (按内存访问比排序)\n")
            f.write("="*80 + "\n\n")
            f.write(f"生成时间: {datetime.now().isoformat()}\n\n")

            f.write(f"{'排名':<5} {'应用':<15} {'函数名':<30} {'访存比':<10} {'读次数':<10} {'写次数':<10}\n")
            f.write("-"*80 + "\n")

            for i, func in enumerate(memory_funcs, 1):
                f.write(f"{i:<5} {func['app_name'][:14]:<15} {func['function_name'][:29]:<30} "
                       f"{func['mem_access_ratio']:<10.4f} {func['mem_read_exec']:<10} {func['mem_write_exec']:<10}\n")

            f.write("\n" + "="*80 + "\n")
            f.write("访问模式分析\n")
            f.write("="*80 + "\n\n")

            for i, func in enumerate(memory_funcs, 1):
                total_reads = func['seq_read_exec'] + func['stride_read_exec'] + func['random_read_exec']
                total_writes = func['seq_write_exec'] + func['stride_write_exec'] + func['random_write_exec']

                f.write(f"{i}. {func['function_name']} ({func['app_name']})\n")
                f.write(f"   内存访问比: {func['mem_access_ratio']:.4f}\n")
                f.write(f"   读访问: 连续={func['seq_read_exec']}, 步长={func['stride_read_exec']}, 随机={func['random_read_exec']}\n")
                f.write(f"   写访问: 连续={func['seq_write_exec']}, 步长={func['stride_write_exec']}, 随机={func['random_write_exec']}\n")
                if total_reads > 0:
                    f.write(f"   随机读比例: {func['random_read_exec']/total_reads:.2%}\n")
                f.write("\n")

        print(f"  访存密集函数报告: {report_file}")

    def _generate_compute_intensive_report(self, compute_funcs):
        """生成计算密集函数报告"""
        report_file = os.path.join(self.summary_dir, 'compute_intensive_functions.txt')

        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("="*80 + "\n")
            f.write("计算密集函数分析 (按计算评分排序)\n")
            f.write("="*80 + "\n\n")
            f.write(f"生成时间: {datetime.now().isoformat()}\n")
            f.write(f"评分 = 算术密度 + 浮点密度×2\n\n")

            f.write(f"{'排名':<5} {'应用':<15} {'函数名':<30} {'评分':<10}\n")
            f.write("-"*80 + "\n")

            for i, func in enumerate(compute_funcs, 1):
                f.write(f"{i:<5} {func['app_name'][:14]:<15} {func['function_name'][:29]:<30} "
                       f"{func.get('compute_score', 0):<10.4f}\n")

            f.write("\n" + "="*80 + "\n")
            f.write("详细信息\n")
            f.write("="*80 + "\n\n")

            for i, func in enumerate(compute_funcs, 1):
                f.write(f"{i}. {func['function_name']} ({func['app_name']})\n")
                f.write(f"   计算评分: {func.get('compute_score', 0):.4f}\n")
                f.write(f"   算术指令: {func['arith_static']} (密度: {func['arith_density']:.4f})\n")
                f.write(f"   浮点指令: {func['float_static']}\n")
                f.write(f"   SIMD指令: {func['simd_static']}\n")
                f.write("\n")

        print(f"  计算密集函数报告: {report_file}")

    def _generate_complexity_report(self, complexity_funcs):
        """生成函数复杂度报告"""
        report_file = os.path.join(self.summary_dir, 'function_complexity.txt')

        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("="*80 + "\n")
            f.write("函数复杂度分析 (综合控制流复杂度排序)\n")
            f.write("="*80 + "\n\n")
            f.write(f"生成时间: {datetime.now().isoformat()}\n")
            f.write(f"复杂度 = 分支密度 + 循环数(归一化) + 调用深度(归一化)\n\n")

            f.write(f"{'排名':<5} {'应用':<15} {'函数名':<30} {'复杂度':<10}\n")
            f.write("-"*80 + "\n")

            for i, func in enumerate(complexity_funcs, 1):
                f.write(f"{i:<5} {func['app_name'][:14]:<15} {func['function_name'][:29]:<30} "
                       f"{func['complexity_score']:<10.4f}\n")

            f.write("\n" + "="*80 + "\n")
            f.write("详细信息\n")
            f.write("="*80 + "\n\n")

            for i, func in enumerate(complexity_funcs, 1):
                f.write(f"{i}. {func['function_name']} ({func['app_name']})\n")
                f.write(f"   复杂度评分: {func['complexity_score']:.4f}\n")
                f.write(f"   分支密度: {func['branch_density']:.4f}\n")
                f.write(f"   循环数: {func['loop_static']}\n")
                f.write(f"   最大调用深度: {func['call_depth_max']}\n")
                f.write(f"   静态指令数: {func['inst_static']}\n")
                f.write("\n")

        print(f"  函数复杂度报告: {report_file}")

    def _generate_suite_comparison_report(self):
        """生成套件对比报告"""
        report_file = os.path.join(self.summary_dir, 'suite_comparison.txt')

        # 计算套件级统计
        for suite in self.suite_metrics:
            apps_count = self.suite_metrics[suite]['app_count']
            if apps_count > 0:
                call_execs = []
                mem_ratios = []
                branch_densities = []
                arith_densities = []

                for func in self.all_functions:
                    if func['suite'] == suite:
                        call_execs.append(func['call_exec'])
                        mem_ratios.append(func['mem_access_ratio'])
                        branch_densities.append(func['branch_density'])
                        arith_densities.append(func['arith_density'])

                if call_execs:
                    self.suite_metrics[suite]['avg_call_exec'] = sum(call_execs) / len(call_execs)
                    self.suite_metrics[suite]['avg_mem_access_ratio'] = sum(mem_ratios) / len(mem_ratios)
                    self.suite_metrics[suite]['avg_branch_density'] = sum(branch_densities) / len(branch_densities)
                    self.suite_metrics[suite]['avg_arith_density'] = sum(arith_densities) / len(arith_densities)

        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("="*80 + "\n")
            f.write("套件对比汇总 (基于v3.0指标)\n")
            f.write("="*80 + "\n\n")
            f.write(f"生成时间: {datetime.now().isoformat()}\n\n")

            f.write(f"{'套件':<15} {'应用数':<8} {'函数数':<10} {'平均调用':<12} "
                   f"{'平均访存比':<12} {'平均分支密度':<15} {'平均算术密度':<15}\n")
            f.write("-"*80 + "\n")

            for suite in sorted(self.suite_metrics.keys()):
                metrics = self.suite_metrics[suite]
                f.write(f"{suite:<15} {metrics['app_count']:<8} {metrics['total_functions']:<10} "
                       f"{metrics['avg_call_exec']:<12.2f} {metrics['avg_mem_access_ratio']:<12.4f} "
                       f"{metrics['avg_branch_density']:<15.4f} {metrics['avg_arith_density']:<15.4f}\n")

        print(f"  套件对比报告: {report_file}")


def main():
    parser = argparse.ArgumentParser(
        description='分析函数剖析结果 (v3.0)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 分析所有结果
  python analyze_results.py

适配function_profiler v3.0版本指标体系
        """
    )

    parser.add_argument('--output', '-o', type=str, default=None,
                       help='输出报告目录（默认：results/summary）')

    args = parser.parse_args()

    # 创建分析器
    analyzer = FunctionResultAnalyzer()

    # 收集JSON文件
    json_files = analyzer.collect_json_files()
    if not json_files:
        print("错误: 没有找到JSON剖析结果文件")
        sys.exit(1)

    # 提取指标
    analyzer.extract_metrics_from_json(json_files)

    # 生成报告
    analyzer.generate_reports()

    print(f"\n报告已生成在: {analyzer.summary_dir}")
    sys.exit(0)


if __name__ == '__main__':
    main()
