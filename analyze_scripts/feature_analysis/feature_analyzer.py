#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Feature Analyzer for LetGo Framework

This module provides a comprehensive feature analysis toolkit for analyzing
the relationship between program features and fault recoverability.

Author: Enhanced LetGo Framework
Date: 2025
"""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Set matplotlib parameters for better Chinese font support
plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False


class FeatureAnalyzer:
    """
    Feature Analyzer for LetGo fault injection experiments.

    This class provides methods to analyze various features collected during
    fault injection experiments and their impact on recoverability.
    """

    def __init__(self, csv_path: str, output_dir: str, progname: str = None):
        """
        Initialize the Feature Analyzer.

        Args:
            csv_path: Path to the CSV file containing experiment results
            output_dir: Directory to save analysis results
            progname: Program name (optional, extracted from csv_path if not provided)
        """
        self.csv_path = Path(csv_path)
        self.output_dir = Path(output_dir)
        self.progname = progname or self.csv_path.stem

        # Create output directory if it doesn't exist
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Load data
        self._load_data()

    def _load_data(self):
        """Load and validate CSV data."""
        if not self.csv_path.exists():
            raise FileNotFoundError(f"CSV file not found: {self.csv_path}")

        print(f"Loading data from: {self.csv_path}")
        self.df = pd.read_csv(self.csv_path)
        print(f"Total records: {len(self.df)}")

        # Filter crash records
        self.df_crash = self.df[
            self.df['result'].str.startswith('C-', na=False) |
            (self.df['result'] == 'Recrash')
        ].copy()
        print(f"Records with crashes: {len(self.df_crash)}")

    def _save_figure(self, fig: plt.Figure, filename: str):
        """Helper method to save figure."""
        output_path = self.output_dir / filename
        fig.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"  Saved: {output_path}")
        plt.close(fig)

    def analyze_call_depth_recoverability(self) -> Optional[pd.DataFrame]:
        """
        Analyze the impact of call depth on recoverability.

        Returns:
            DataFrame with recovery statistics by call depth
        """
        print("\n=== Analysis 1: Call Depth vs Recoverability ===")

        df_valid = self.df_crash[self.df_crash['CallDepth'].notna()].copy()
        if len(df_valid) == 0:
            print("  No valid CallDepth data found")
            return None

        print(f"  Valid records: {len(df_valid)}")

        # Calculate recovery statistics
        recovery_data = []
        for depth in sorted(df_valid['CallDepth'].unique()):
            subset = df_valid[df_valid['CallDepth'] == depth]
            total = len(subset)
            c_masked = len(subset[subset['result'] == 'C-Masked'])
            c_sdc = len(subset[subset['result'] == 'C-SDC'])
            recrash = len(subset[subset['result'] == 'Recrash'])

            recovery_data.append({
                'CallDepth': depth,
                'Total': total,
                'C-Masked': c_masked,
                'C-SDC': c_sdc,
                'Recrash': recrash,
                'Recovery_Rate': c_masked / total * 100 if total > 0 else 0
            })

        recovery_df = pd.DataFrame(recovery_data)
        print("\n  Recovery statistics by call depth:")
        print(recovery_df.to_string(index=False))

        # Save statistics
        stats_path = self.output_dir / f"{self.progname}_callDepth_stats.csv"
        recovery_df.to_csv(stats_path, index=False)
        print(f"  Saved statistics: {stats_path}")

        # Plot
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

        # Subplot 1: Stacked bar chart
        depth_stats = df_valid.groupby(['CallDepth', 'result']).size().unstack(fill_value=0)
        depth_stats_pct = depth_stats.div(depth_stats.sum(axis=1), axis=0) * 100

        if 'C-Masked' in depth_stats_pct.columns:
            depth_stats_pct[['C-Masked', 'C-SDC', 'Recrash']].plot(
                kind='bar', stacked=False, ax=ax1, colormap='Set2'
            )
            ax1.set_title(f'{self.progname} - 调用深度对可修复性的影响')
            ax1.set_xlabel('调用深度')
            ax1.set_ylabel('比例 (%)')
            ax1.legend(['C-Masked', 'C-SDC', 'Recrash'])
            ax1.grid(axis='y', alpha=0.3)

        # Subplot 2: Recovery rate line chart
        ax2.plot(recovery_df['CallDepth'], recovery_df['Recovery_Rate'],
                marker='o', linewidth=2, markersize=8, color='steelblue')
        ax2.set_title(f'{self.progname} - 调用深度与恢复成功率')
        ax2.set_xlabel('调用深度')
        ax2.set_ylabel('恢复成功率 (%)')
        ax2.grid(True, alpha=0.3)

        # Add value labels
        for x, y in zip(recovery_df['CallDepth'], recovery_df['Recovery_Rate']):
            ax2.text(x, y + 2, f'{y:.1f}%', ha='center', va='bottom', fontsize=9)

        plt.tight_layout()
        self._save_figure(fig, f'{self.progname}_callDepth_recoverability.png')

        return recovery_df

    def analyze_instr_type_heuristic(self, top_n: int = 15) -> Optional[pd.DataFrame]:
        """
        Analyze instruction type and heuristic strategy distribution.

        Args:
            top_n: Number of top opcodes to analyze

        Returns:
            DataFrame with heuristic distribution by instruction type
        """
        print("\n=== Analysis 2: Instruction Type vs Heuristic Strategy ===")

        df_valid = self.df_crash[
            (self.df_crash['opcode'].notna()) &
            (self.df_crash['Heuristic'].notna())
        ].copy()

        if len(df_valid) == 0:
            print("  No valid data found")
            return None

        print(f"  Valid records: {len(df_valid)}")

        # Get top N opcodes
        top_opcodes = df_valid['opcode'].value_counts().head(top_n).index
        df_top = df_valid[df_valid['opcode'].isin(top_opcodes)]

        # Create crosstab
        cross_tab = pd.crosstab(df_top['opcode'], df_top['Heuristic'], normalize='index') * 100

        print(f"\n  Heuristic distribution by instruction type (top {top_n}):")
        print(cross_tab.round(2).to_string())

        # Save statistics
        stats_path = self.output_dir / f"{self.progname}_opcode_heuristic_stats.csv"
        cross_tab.to_csv(stats_path)
        print(f"  Saved statistics: {stats_path}")

        # Plot
        fig, ax = plt.subplots(figsize=(12, 8))
        cross_tab.plot(kind='bar', stacked=True, ax=ax,
                      colormap='Set3', edgecolor='black', linewidth=0.5)
        ax.set_title(f'{self.progname} - 指令类型与修复策略分布')
        ax.set_xlabel('操作码')
        ax.set_ylabel('比例 (%)')
        ax.legend(title='修复策略', bbox_to_anchor=(1.05, 1), loc='upper left')
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()

        self._save_figure(fig, f'{self.progname}_opcode_heuristic_dist.png')

        return cross_tab

    def analyze_exec_progress(self) -> Optional[pd.DataFrame]:
        """
        Analyze program execution phase impact on crashes.

        Returns:
            DataFrame with crash statistics by execution phase
        """
        print("\n=== Analysis 3: Execution Progress vs Crash Rate ===")

        df_valid = self.df[self.df['ExecProgress'].notna()].copy()
        if len(df_valid) == 0:
            print("  No valid ExecProgress data found")
            return None

        print(f"  Valid records: {len(df_valid)}")

        # Divide into phases
        df_valid['ExecPhase'] = pd.cut(
            df_valid['ExecProgress'],
            bins=[0, 0.1, 0.5, 0.9, 1.0],
            labels=['初始化', '计算前期', '计算后期', '收尾']
        )

        # Calculate crash rate for each phase
        phase_stats = []
        for phase in ['初始化', '计算前期', '计算后期', '收尾']:
            subset = df_valid[df_valid['ExecPhase'] == phase]
            total = len(subset)
            if total == 0:
                continue
            crashed = len(subset[subset['result'].isin(['crash', 'Recrash', 'C-Masked', 'C-SDC'])])
            phase_stats.append({
                'Phase': phase,
                'Total': total,
                'Crashed': crashed,
                'Crash_Rate': crashed / total * 100
            })

        if len(phase_stats) == 0:
            print("  No valid phase statistics")
            return None

        phase_df = pd.DataFrame(phase_stats)
        print("\n  Crash statistics by execution phase:")
        print(phase_df.to_string(index=False))

        # Save statistics
        stats_path = self.output_dir / f"{self.progname}_execPhase_stats.csv"
        phase_df.to_csv(stats_path, index=False)
        print(f"  Saved statistics: {stats_path}")

        # Plot
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.bar(phase_df['Phase'], phase_df['Crash_Rate'],
               color='coral', edgecolor='black', width=0.6)
        ax.set_title(f'{self.progname} - 程序执行阶段与崩溃率')
        ax.set_xlabel('执行阶段')
        ax.set_ylabel('崩溃率 (%)')
        ax.grid(axis='y', alpha=0.3)

        # Add value labels
        for i, v in enumerate(phase_df['Crash_Rate']):
            ax.text(i, v + 1, f'{v:.1f}%', ha='center', va='bottom', fontsize=10)

        plt.tight_layout()
        self._save_figure(fig, f'{self.progname}_execPhase_crash.png')

        return phase_df

    def analyze_rbp_rsp_delta(self) -> Optional[pd.DataFrame]:
        """
        Analyze RBP-RSP delta distribution and its impact on recovery.

        Returns:
            DataFrame with recovery statistics by RBP-RSP delta range
        """
        print("\n=== Analysis 4: RBP-RSP Delta Distribution ===")

        df_valid = self.df_crash[self.df_crash['RBP_RSP_Delta'].notna()].copy()
        if len(df_valid) == 0:
            print("  No valid RBP_RSP_Delta data found")
            return None

        print(f"  Valid records: {len(df_valid)}")

        # Create bins for delta values
        bins = [0, 64, 128, 256, 512, 1024, float('inf')]
        labels = ['0-64', '64-128', '128-256', '256-512', '512-1024', '>1024']
        df_valid['Delta_Range'] = pd.cut(df_valid['RBP_RSP_Delta'], bins=bins, labels=labels)

        # Calculate recovery rate for each range
        range_stats = []
        for rng in labels:
            subset = df_valid[df_valid['Delta_Range'] == rng]
            total = len(subset)
            if total == 0:
                continue
            recoverable = len(subset[subset['result'] == 'C-Masked'])
            range_stats.append({
                'Range': rng,
                'Total': total,
                'Recoverable': recoverable,
                'Recovery_Rate': recoverable / total * 100 if total > 0 else 0
            })

        if len(range_stats) == 0:
            print("  No valid statistics")
            return None

        range_df = pd.DataFrame(range_stats)
        print("\n  Recovery statistics by RBP-RSP delta range:")
        print(range_df.to_string(index=False))

        # Save statistics
        stats_path = self.output_dir / f"{self.progname}_rbpRspDelta_stats.csv"
        range_df.to_csv(stats_path, index=False)
        print(f"  Saved statistics: {stats_path}")

        # Plot
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.bar(range_df['Range'], range_df['Recovery_Rate'],
               color='steelblue', edgecolor='black', width=0.6)
        ax.set_title(f'{self.progname} - 栈指针偏移量与恢复成功率')
        ax.set_xlabel('RBP-RSP Delta 范围 (字节)')
        ax.set_ylabel('恢复成功率 (%)')
        ax.grid(axis='y', alpha=0.3)

        # Add value labels
        for i, v in enumerate(range_df['Recovery_Rate']):
            ax.text(i, v + 1, f'{v:.1f}%', ha='center', va='bottom', fontsize=10)

        plt.tight_layout()
        self._save_figure(fig, f'{self.progname}_rbp_rsp_delta.png')

        return range_df

    def generate_feature_importance_table(self) -> Optional[pd.DataFrame]:
        """
        Generate a comprehensive feature importance table.

        Returns:
            DataFrame with feature importance statistics
        """
        print("\n=== Analysis 5: Feature Importance Table ===")

        results = []

        # Feature 1: CallDepth
        if 'CallDepth' in self.df_crash.columns and self.df_crash['CallDepth'].notna().any():
            for depth in sorted(self.df_crash['CallDepth'].dropna().unique()):
                subset = self.df_crash[self.df_crash['CallDepth'] == depth]
                recoverable = len(subset[subset['result'] == 'C-Masked'])
                total = len(subset[subset['result'].str.startswith('C-', na=False)])
                if total > 0:
                    results.append({
                        'Feature': 'CallDepth',
                        'Value': f'{int(depth)}',
                        'Total': total,
                        'Recoverable': recoverable,
                        'Recoverability': f"{recoverable/total*100:.1f}%"
                    })

        # Feature 2: InstrFlag
        if 'InstrFlag' in self.df_crash.columns and self.df_crash['InstrFlag'].notna().any():
            flag_names = {1: 'StackWrite', 2: 'StackRead', 3: 'NonStack'}
            for flag in sorted(self.df_crash['InstrFlag'].dropna().unique()):
                subset = self.df_crash[self.df_crash['InstrFlag'] == flag]
                recoverable = len(subset[subset['result'] == 'C-Masked'])
                total = len(subset[subset['result'].str.startswith('C-', na=False)])
                if total > 0:
                    flag_name = flag_names.get(int(flag), 'Unknown')
                    results.append({
                        'Feature': 'InstrFlag',
                        'Value': flag_name,
                        'Total': total,
                        'Recoverable': recoverable,
                        'Recoverability': f"{recoverable/total*100:.1f}%"
                    })

        # Feature 3: IsRecursive
        if 'IsRecursive' in self.df_crash.columns and self.df_crash['IsRecursive'].notna().any():
            for is_rec in [True, False]:
                subset = self.df_crash[self.df_crash['IsRecursive'] == is_rec]
                recoverable = len(subset[subset['result'] == 'C-Masked'])
                total = len(subset[subset['result'].str.startswith('C-', na=False)])
                if total > 0:
                    results.append({
                        'Feature': 'IsRecursive',
                        'Value': 'Yes' if is_rec else 'No',
                        'Total': total,
                        'Recoverable': recoverable,
                        'Recoverability': f"{recoverable/total*100:.1f}%"
                    })

        if len(results) == 0:
            print("  No valid feature data found")
            return None

        result_df = pd.DataFrame(results)

        # Save to CSV
        output_csv = self.output_dir / f'{self.progname}_feature_importance.csv'
        result_df.to_csv(output_csv, index=False)

        print("\n  Feature Importance Table:")
        print(result_df.to_string(index=False))
        print(f"  Saved to: {output_csv}")

        return result_df

    def run_all_analyses(self):
        """Run all available analyses."""
        print("\n" + "="*60)
        print(f"Starting Feature Analysis for {self.progname}")
        print("="*60)

        analyses = [
            ('Call Depth', self.analyze_call_depth_recoverability),
            ('Instruction Type', self.analyze_instr_type_heuristic),
            ('Execution Progress', self.analyze_exec_progress),
            ('RBP-RSP Delta', self.analyze_rbp_rsp_delta),
            ('Feature Importance', self.generate_feature_importance_table),
        ]

        for name, func in analyses:
            try:
                func()
            except Exception as e:
                print(f"  Error in {name} analysis: {e}")

        print("\n" + "="*60)
        print("Feature Analysis Complete!")
        print(f"All outputs saved to: {self.output_dir}")
        print("="*60)
