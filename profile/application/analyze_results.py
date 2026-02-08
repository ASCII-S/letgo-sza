#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
剖析结果汇总分析脚本

功能：
1. 从多个JSON文件提取关键指标
2. 生成汇总CSV报告
3. 按套件分组统计
4. 计算弹性评分
5. 生成文本报告
"""

import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime

# 尝试导入pandas（必需）
try:
    import pandas as pd
except ImportError:
    print("错误: 需要安装 pandas (pip install pandas)")
    sys.exit(1)

# 添加配置路径
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import (
    RAW_JSON_DIR, SUMMARY_DIR, APP_SUITES,
    KEY_METRICS, RESILIENCE_WEIGHTS, get_app_suite
)


class ResultAnalyzer:
    """结果分析器类"""

    def __init__(self, json_dir=RAW_JSON_DIR, output_dir=SUMMARY_DIR):
        """
        初始化分析器

        Args:
            json_dir: JSON文件目录
            output_dir: 输出目录
        """
        self.json_dir = Path(json_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 数据存储
        self.raw_data = []  # 原始数据列表
        self.metrics_df = None  # 指标DataFrame

    def collect_json_files(self):
        """收集所有JSON文件"""
        json_files = []

        # 遍历所有套件子目录
        for suite in APP_SUITES.keys():
            suite_dir = self.json_dir / suite
            if suite_dir.exists():
                json_files.extend(suite_dir.glob("*_profile.json"))

        print(f"找到 {len(json_files)} 个JSON文件")
        return json_files

    def extract_metrics_from_json(self, json_path):
        """
        从JSON文件提取关键指标

        Args:
            json_path: JSON文件路径

        Returns:
            dict: 提取的指标字典
        """
        try:
            with open(json_path, 'r') as f:
                data = json.load(f)

            app_name = json_path.stem.replace('_profile', '')
            suite = get_app_suite(app_name)

            metrics = {
                'app_name': app_name,
                'suite': suite,
                'json_file': str(json_path)
            }

            # 提取程序工作负载类型指标
            if 'program_workload_type' in data:
                workload = data['program_workload_type']

                # 计算/访存比
                if 'metrics' in workload:
                    workload_metrics = workload['metrics']

                    if 'compute_memory_ratio' in workload_metrics:
                        cmr = workload_metrics['compute_memory_ratio']
                        if isinstance(cmr, dict):
                            metrics['compute_memory_ratio'] = cmr.get('value')
                        else:
                            metrics['compute_memory_ratio'] = cmr

                    # 每指令访存字节数
                    if 'bytes_per_instruction' in workload_metrics:
                        bpi = workload_metrics['bytes_per_instruction']
                        if isinstance(bpi, dict):
                            metrics['bytes_per_instruction'] = bpi.get('value')
                        else:
                            metrics['bytes_per_instruction'] = bpi

                    # SIMD比例
                    if 'simd_ratio' in workload_metrics:
                        simd = workload_metrics['simd_ratio']
                        if isinstance(simd, dict):
                            metrics['simd_ratio'] = simd.get('value')
                        else:
                            metrics['simd_ratio'] = simd

                    # 数据移动指令比例
                    if 'data_movement_ratio' in workload_metrics:
                        dmr = workload_metrics['data_movement_ratio']
                        if isinstance(dmr, dict):
                            metrics['data_movement_ratio'] = dmr.get('value')
                        else:
                            metrics['data_movement_ratio'] = dmr

                # 工作负载分类
                if 'classification' in workload:
                    metrics['workload_type'] = workload['classification'].get('type')

            # 提取数据流特征
            if 'data_flow_characteristics' in data:
                dataflow = data['data_flow_characteristics']

                if 'metrics' in dataflow:
                    df_metrics = dataflow['metrics']

                    # 值生命周期
                    if 'value_lifetime' in df_metrics:
                        vl = df_metrics['value_lifetime']
                        if isinstance(vl, dict):
                            metrics['value_lifetime_avg'] = vl.get('average')
                            metrics['value_lifetime_median'] = vl.get('median')
                        else:
                            metrics['value_lifetime_avg'] = vl

                    # 值扇出度
                    if 'value_fanout' in df_metrics:
                        vf = df_metrics['value_fanout']
                        if isinstance(vf, dict):
                            metrics['value_fanout_avg'] = vf.get('average')
                        else:
                            metrics['value_fanout_avg'] = vf

                    # 寄存器重写率
                    if 'register_rewrite_frequency' in df_metrics:
                        rrf = df_metrics['register_rewrite_frequency']
                        if isinstance(rrf, dict):
                            metrics['register_rewrite_rate'] = rrf.get('rate')
                        else:
                            metrics['register_rewrite_rate'] = rrf

            # 提取冗余和校验特征
            if 'redundancy_check_characteristics' in data:
                redundancy = data['redundancy_check_characteristics']

                if 'metrics' in redundancy:
                    rc_metrics = redundancy['metrics']

                    # 比较指令密度
                    if 'compare_instruction_density' in rc_metrics:
                        cid = rc_metrics['compare_instruction_density']
                        if isinstance(cid, dict):
                            metrics['compare_instruction_density'] = cid.get('density')
                        else:
                            metrics['compare_instruction_density'] = cid

            # 提取控制流特征
            if 'control_flow_characteristics' in data:
                control = data['control_flow_characteristics']

                if 'metrics' in control:
                    cf_metrics = control['metrics']

                    # 分支统计
                    if 'branch_statistics' in cf_metrics:
                        bs = cf_metrics['branch_statistics']
                        if isinstance(bs, dict):
                            metrics['branch_bias'] = bs.get('branch_bias')
                            metrics['total_branches'] = bs.get('total_branches')

                    # 循环统计
                    if 'loop_characteristics' in cf_metrics:
                        lc = cf_metrics['loop_characteristics']
                        if isinstance(lc, dict):
                            metrics['loop_avg_iterations'] = lc.get('average_iterations')

                    # 函数调用深度
                    if 'function_call_depth' in cf_metrics:
                        fcd = cf_metrics['function_call_depth']
                        if isinstance(fcd, dict):
                            metrics['function_call_depth_max'] = fcd.get('max')
                            metrics['function_call_depth_avg'] = fcd.get('average')

            # 提取内存访问模式
            if 'memory_access_patterns' in data:
                memory = data['memory_access_patterns']

                if 'metrics' in memory:
                    ma_metrics = memory['metrics']

                    # 读写比例
                    if 'read_write_ratio' in ma_metrics:
                        rwr = ma_metrics['read_write_ratio']
                        if isinstance(rwr, dict):
                            metrics['memory_read_write_ratio'] = rwr.get('ratio')
                        else:
                            metrics['memory_read_write_ratio'] = rwr

                    # 栈访问比例
                    if 'stack_access_ratio' in ma_metrics:
                        sar = ma_metrics['stack_access_ratio']
                        if isinstance(sar, dict):
                            metrics['stack_access_ratio'] = sar.get('ratio')
                        else:
                            metrics['stack_access_ratio'] = sar

            # 提取总执行指令数
            if 'execution_summary' in data:
                metrics['total_instructions'] = data['execution_summary'].get('total_instructions')
                metrics['total_basic_blocks'] = data['execution_summary'].get('total_basic_blocks')

            # 提取指令分布
            if 'instruction_characteristics' in data:
                inst = data['instruction_characteristics']
                if 'distribution' in inst:
                    dist = inst['distribution']
                    for inst_type, count in dist.items():
                        metrics[f'inst_{inst_type}'] = count

            return metrics

        except Exception as e:
            print(f"  警告: 解析 {json_path.name} 失败: {e}")
            return None

    def calculate_resilience_score(self, row):
        """
        计算弹性评分（0-100分）

        基于多个指标的加权平均
        """
        score = 0
        total_weight = 0

        # 值生命周期（越短越好）
        if pd.notna(row.get('value_lifetime_avg')):
            lifetime = row['value_lifetime_avg']
            # 归一化：< 10 好，> 50 差
            lifetime_score = max(0, min(100, 100 - (lifetime - 10) * 2))
            score += lifetime_score * RESILIENCE_WEIGHTS['value_lifetime']
            total_weight += RESILIENCE_WEIGHTS['value_lifetime']

        # 值扇出度（越低越好）
        if pd.notna(row.get('value_fanout_avg')):
            fanout = row['value_fanout_avg']
            # 归一化：< 3 好，> 8 差
            fanout_score = max(0, min(100, 100 - (fanout - 3) * 15))
            score += fanout_score * RESILIENCE_WEIGHTS['value_fanout']
            total_weight += RESILIENCE_WEIGHTS['value_fanout']

        # 寄存器重写率（越高越好）
        if pd.notna(row.get('register_rewrite_rate')):
            rewrite = row['register_rewrite_rate']
            if rewrite < 1:  # 如果是小数形式
                rewrite = rewrite * 100  # 转为百分比
            # 归一化：> 30% 好，< 10% 差
            rewrite_score = max(0, min(100, (rewrite - 10) * 5))
            score += rewrite_score * RESILIENCE_WEIGHTS['register_rewrite_rate']
            total_weight += RESILIENCE_WEIGHTS['register_rewrite_rate']

        # 比较指令密度（越高越好）
        if pd.notna(row.get('compare_instruction_density')):
            compare = row['compare_instruction_density']
            if compare < 1:  # 如果是小数形式
                compare = compare * 100
            # 归一化：> 5% 好，< 2% 差
            compare_score = max(0, min(100, (compare - 2) * 25))
            score += compare_score * RESILIENCE_WEIGHTS['compare_density']
            total_weight += RESILIENCE_WEIGHTS['compare_density']

        # 分支偏向性（越高越好）
        if pd.notna(row.get('branch_bias')):
            bias = row['branch_bias']
            # 归一化：> 0.8 好，< 0.6 差
            bias_score = max(0, min(100, (bias - 0.6) * 250))
            score += bias_score * RESILIENCE_WEIGHTS['branch_bias']
            total_weight += RESILIENCE_WEIGHTS['branch_bias']

        if total_weight > 0:
            return score / total_weight
        return None

    def analyze(self):
        """执行分析"""
        print(f"\n{'='*70}")
        print(f"剖析结果汇总分析")
        print(f"{'='*70}")
        print(f"JSON目录: {self.json_dir}")
        print(f"输出目录: {self.output_dir}")
        print()

        # 收集JSON文件
        json_files = self.collect_json_files()

        if not json_files:
            print("错误: 未找到JSON文件")
            return False

        # 提取指标
        print("\n提取指标...")
        for json_path in json_files:
            print(f"  处理: {json_path.name}")
            metrics = self.extract_metrics_from_json(json_path)
            if metrics:
                self.raw_data.append(metrics)

        if not self.raw_data:
            print("错误: 未能提取任何指标")
            return False

        # 创建DataFrame
        self.metrics_df = pd.DataFrame(self.raw_data)

        # 计算弹性评分
        print("\n计算弹性评分...")
        self.metrics_df['resilience_score'] = self.metrics_df.apply(
            self.calculate_resilience_score, axis=1
        )

        # 生成报告
        self._generate_metrics_summary()
        self._generate_suite_comparison()
        self._generate_resilience_scores()
        self._generate_text_report()

        print(f"\n{'='*70}")
        print(f"分析完成！")
        print(f"结果已保存到: {self.output_dir}")
        print(f"{'='*70}\n")

        return True

    def _generate_metrics_summary(self):
        """生成指标汇总CSV"""
        output_file = self.output_dir / 'metrics_summary.csv'

        # 选择要输出的列
        base_columns = ['app_name', 'suite', 'workload_type']
        available_columns = [col for col in base_columns if col in self.metrics_df.columns]

        # 添加可用的指标列
        for metric in KEY_METRICS + ['resilience_score']:
            if metric in self.metrics_df.columns:
                available_columns.append(metric)

        summary_df = self.metrics_df[available_columns].copy()
        summary_df.to_csv(output_file, index=False, float_format='%.4f')

        print(f"✓ 指标汇总: {output_file}")

    def _generate_suite_comparison(self):
        """生成套件对比CSV"""
        output_file = self.output_dir / 'suite_comparison.csv'

        # 按套件分组统计
        numeric_cols = self.metrics_df.select_dtypes(include=['number']).columns
        suite_stats = self.metrics_df.groupby('suite')[numeric_cols].agg(['mean', 'std', 'min', 'max'])

        suite_stats.to_csv(output_file, float_format='%.4f')

        print(f"✓ 套件对比: {output_file}")

    def _generate_resilience_scores(self):
        """生成弹性评分CSV"""
        output_file = self.output_dir / 'resilience_scores.csv'

        # 按弹性评分排序
        score_df = self.metrics_df[['app_name', 'suite', 'resilience_score']].copy()
        score_df = score_df.sort_values('resilience_score', ascending=False)

        # 添加等级
        def get_grade(score):
            if pd.isna(score):
                return 'N/A'
            elif score >= 70:
                return 'A (高弹性)'
            elif score >= 50:
                return 'B (中等弹性)'
            else:
                return 'C (低弹性)'

        score_df['grade'] = score_df['resilience_score'].apply(get_grade)

        score_df.to_csv(output_file, index=False, float_format='%.2f')

        print(f"✓ 弹性评分: {output_file}")

    def _generate_text_report(self):
        """生成文本报告"""
        output_file = self.output_dir / 'summary_report.txt'

        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("="*70 + "\n")
            f.write(" " * 20 + "程序剖析汇总报告\n")
            f.write("="*70 + "\n\n")

            f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"分析程序数: {len(self.metrics_df)}\n\n")

            # 按套件统计
            f.write("-" * 70 + "\n")
            f.write("按套件统计\n")
            f.write("-" * 70 + "\n\n")

            for suite in APP_SUITES.keys():
                suite_df = self.metrics_df[self.metrics_df['suite'] == suite]
                if len(suite_df) > 0:
                    f.write(f"{suite.upper()}:\n")
                    f.write(f"  程序数: {len(suite_df)}\n")

                    # 工作负载类型分布
                    if 'workload_type' in suite_df.columns:
                        workload_dist = suite_df['workload_type'].value_counts()
                        f.write(f"  工作负载类型分布:\n")
                        for wtype, count in workload_dist.items():
                            if pd.notna(wtype):
                                f.write(f"    - {wtype}: {count}\n")

                    # 平均弹性评分
                    if 'resilience_score' in suite_df.columns:
                        avg_score = suite_df['resilience_score'].mean()
                        if pd.notna(avg_score):
                            f.write(f"  平均弹性评分: {avg_score:.2f}\n")

                    f.write("\n")

            # 工作负载类型分布
            f.write("-" * 70 + "\n")
            f.write("工作负载类型分布\n")
            f.write("-" * 70 + "\n\n")

            if 'workload_type' in self.metrics_df.columns:
                workload_counts = self.metrics_df['workload_type'].value_counts()
                for wtype, count in workload_counts.items():
                    if pd.notna(wtype):
                        percentage = count / len(self.metrics_df) * 100
                        f.write(f"{wtype}: {count} ({percentage:.1f}%)\n")

            f.write("\n")

            # Top弹性评分
            f.write("-" * 70 + "\n")
            f.write("Top 10 高弹性程序\n")
            f.write("-" * 70 + "\n\n")

            if 'resilience_score' in self.metrics_df.columns:
                top_resilient = self.metrics_df.nlargest(10, 'resilience_score')[
                    ['app_name', 'suite', 'resilience_score']
                ]

                for idx, row in top_resilient.iterrows():
                    score = row['resilience_score']
                    score_str = f"{score:.2f}" if pd.notna(score) else "N/A"
                    f.write(f"{row['app_name']:20s} [{row['suite']:10s}] "
                           f"评分: {score_str}\n")

            f.write("\n")

            # Bottom弹性评分
            f.write("-" * 70 + "\n")
            f.write("Top 10 低弹性程序\n")
            f.write("-" * 70 + "\n\n")

            if 'resilience_score' in self.metrics_df.columns:
                bottom_resilient = self.metrics_df.nsmallest(10, 'resilience_score')[
                    ['app_name', 'suite', 'resilience_score']
                ]

                for idx, row in bottom_resilient.iterrows():
                    score = row['resilience_score']
                    score_str = f"{score:.2f}" if pd.notna(score) else "N/A"
                    f.write(f"{row['app_name']:20s} [{row['suite']:10s}] "
                           f"评分: {score_str}\n")

            f.write("\n")
            f.write("="*70 + "\n")

        print(f"✓ 文本报告: {output_file}")


def main():
    parser = argparse.ArgumentParser(
        description='汇总分析剖析结果',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 分析默认目录的结果
  python analyze_results.py

  # 指定JSON目录
  python analyze_results.py --json-dir ./custom_results/raw_json

  # 指定输出目录
  python analyze_results.py --output ./custom_summary
        """
    )

    parser.add_argument('--json-dir', '-j', type=str, default=RAW_JSON_DIR,
                       help=f'JSON文件目录（默认：{RAW_JSON_DIR}）')
    parser.add_argument('--output', '-o', type=str, default=SUMMARY_DIR,
                       help=f'输出目录（默认：{SUMMARY_DIR}）')

    args = parser.parse_args()

    # 创建分析器并运行
    analyzer = ResultAnalyzer(
        json_dir=args.json_dir,
        output_dir=args.output
    )

    success = analyzer.analyze()

    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
