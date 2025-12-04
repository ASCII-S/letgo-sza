#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Batch Feature Analysis Script

Analyzes multiple CSV files and generates comprehensive comparison reports.

Usage:
    python analyze_features_batch.py [options]
    python analyze_features_batch.py --csv-dir ../CSV
    python analyze_features_batch.py --programs backprop bfs nn

Author: Enhanced LetGo Framework
Date: 2025
"""

import argparse
import sys
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from analyze_scripts.feature_analysis.feature_analyzer import FeatureAnalyzer


def analyze_batch(csv_dir: Path, output_dir: Path, programs: list = None):
    """
    Analyze multiple programs and generate comparison reports.

    Args:
        csv_dir: Directory containing CSV files
        output_dir: Output directory for results
        programs: List of program names to analyze (None = all)
    """
    # Get CSV files
    if programs:
        csv_files = [csv_dir / f"{prog}.csv" for prog in programs]
        csv_files = [f for f in csv_files if f.exists()]
    else:
        csv_files = list(csv_dir.glob("*.csv"))

    if not csv_files:
        print("No CSV files found")
        return

    print(f"\n{'='*60}")
    print(f"Batch Feature Analysis")
    print(f"CSV Directory: {csv_dir}")
    print(f"Output Directory: {output_dir}")
    print(f"Programs to analyze: {len(csv_files)}")
    print(f"{'='*60}\n")

    # Create individual results directory
    individual_dir = output_dir / "individual"
    individual_dir.mkdir(parents=True, exist_ok=True)

    # Analyze each program
    all_stats = {
        'callDepth': [],
        'opcode': [],
        'execPhase': [],
        'rbpRspDelta': [],
        'featureImportance': []
    }

    for i, csv_file in enumerate(csv_files, 1):
        progname = csv_file.stem
        print(f"\n[{i}/{len(csv_files)}] Analyzing {progname}...")
        print("-" * 60)

        try:
            # Create analyzer for this program
            prog_output = individual_dir / progname
            analyzer = FeatureAnalyzer(
                csv_path=str(csv_file),
                output_dir=str(prog_output),
                progname=progname
            )

            # Run analyses and collect results
            stats = analyzer.run_all_analyses()

            # Collect statistics for comparison
            for stat_type in all_stats.keys():
                stat_file = prog_output / f"{progname}_{stat_type}_stats.csv"
                if stat_file.exists():
                    df = pd.read_csv(stat_file)
                    df['Program'] = progname
                    all_stats[stat_type].append(df)

        except Exception as e:
            print(f"  Error analyzing {progname}: {e}")
            continue

    # Generate comparison reports
    print(f"\n{'='*60}")
    print("Generating Comparison Reports...")
    print(f"{'='*60}\n")

    comparison_dir = output_dir / "comparison"
    comparison_dir.mkdir(parents=True, exist_ok=True)

    _generate_comparison_reports(all_stats, comparison_dir)

    print(f"\n{'='*60}")
    print("Batch Analysis Complete!")
    print(f"Individual results: {individual_dir}")
    print(f"Comparison reports: {comparison_dir}")
    print(f"{'='*60}")


def _generate_comparison_reports(all_stats: dict, output_dir: Path):
    """Generate cross-program comparison reports."""

    # 1. Call Depth Comparison
    if all_stats['callDepth']:
        print("  Generating call depth comparison...")
        df_combined = pd.concat(all_stats['callDepth'], ignore_index=True)

        # Average recovery rate by call depth across all programs
        avg_by_depth = df_combined.groupby('CallDepth')['Recovery_Rate'].agg(['mean', 'std', 'count'])
        avg_by_depth.to_csv(output_dir / 'callDepth_comparison.csv')

        # Plot
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.errorbar(avg_by_depth.index, avg_by_depth['mean'],
                    yerr=avg_by_depth['std'], marker='o', capsize=5,
                    linewidth=2, markersize=8)
        ax.set_title('调用深度对恢复成功率的影响（跨程序平均）')
        ax.set_xlabel('调用深度')
        ax.set_ylabel('平均恢复成功率 (%)')
        ax.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(output_dir / 'callDepth_comparison.png', dpi=300, bbox_inches='tight')
        plt.close()

    # 2. Program-wise Recovery Rate Summary
    if all_stats['featureImportance']:
        print("  Generating feature importance comparison...")
        df_combined = pd.concat(all_stats['featureImportance'], ignore_index=True)

        # Pivot table: Program x Feature
        summary = df_combined.groupby(['Program', 'Feature']).apply(
            lambda x: (x['Recoverable'].sum() / x['Total'].sum() * 100) if x['Total'].sum() > 0 else 0
        ).unstack(fill_value=0)

        summary.to_csv(output_dir / 'feature_importance_comparison.csv')

        # Heatmap
        fig, ax = plt.subplots(figsize=(12, 8))
        import seaborn as sns
        sns.heatmap(summary, annot=True, fmt='.1f', cmap='RdYlGn',
                   cbar_kws={'label': '恢复成功率 (%)'}, ax=ax)
        ax.set_title('各程序特征恢复成功率对比')
        ax.set_xlabel('特征')
        ax.set_ylabel('程序')
        plt.tight_layout()
        plt.savefig(output_dir / 'feature_importance_heatmap.png', dpi=300, bbox_inches='tight')
        plt.close()

    print("  Comparison reports generated!")


def main():
    parser = argparse.ArgumentParser(
        description="Batch analyze multiple programs' feature data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze all CSV files in ../CSV/
  python analyze_features_batch.py

  # Analyze specific programs
  python analyze_features_batch.py --programs backprop bfs nn

  # Use custom CSV directory
  python analyze_features_batch.py --csv-dir /path/to/csv

  # Specify custom output directory
  python analyze_features_batch.py --output ./batch_results
        """
    )

    parser.add_argument('--csv-dir', '-c', type=str, default='../CSV',
                       help='Directory containing CSV files (default: ../CSV)')
    parser.add_argument('--output', '-o', type=str, default='./results',
                       help='Output directory for results (default: ./results)')
    parser.add_argument('--programs', '-p', nargs='+', default=None,
                       help='Specific programs to analyze (default: all)')

    args = parser.parse_args()

    # Resolve paths
    csv_dir = Path(args.csv_dir)
    if not csv_dir.is_absolute():
        csv_dir = Path(__file__).parent / csv_dir

    if not csv_dir.exists():
        print(f"Error: CSV directory not found: {csv_dir}")
        sys.exit(1)

    output_dir = Path(args.output)

    # Run batch analysis
    analyze_batch(csv_dir, output_dir, args.programs)

    return 0


if __name__ == "__main__":
    sys.exit(main())
