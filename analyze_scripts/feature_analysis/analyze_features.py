#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Single Program Feature Analysis Script

Usage:
    python analyze_features.py <csv_file> [options]
    python analyze_features.py backprop.csv
    python analyze_features.py /path/to/custom.csv --output ./results

Author: Enhanced LetGo Framework
Date: 2025
"""

import argparse
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from analyze_scripts.feature_analysis.feature_analyzer import FeatureAnalyzer


def main():
    parser = argparse.ArgumentParser(
        description="Analyze program features and their impact on recoverability",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze CSV from default location (../CSV/)
  python analyze_features.py backprop.csv

  # Analyze custom CSV file
  python analyze_features.py /path/to/experiment/backprop.csv

  # Specify custom output directory
  python analyze_features.py backprop.csv --output ./my_results

  # Specify program name manually
  python analyze_features.py data.csv --name my_program
        """
    )

    parser.add_argument('csv_file', type=str,
                       help='CSV file name or path (if just filename, looks in ../CSV/)')
    parser.add_argument('--output', '-o', type=str, default='./results',
                       help='Output directory for results (default: ./results)')
    parser.add_argument('--name', '-n', type=str, default=None,
                       help='Program name (default: extracted from CSV filename)')
    parser.add_argument('--top-opcodes', '-t', type=int, default=15,
                       help='Number of top opcodes to analyze (default: 15)')

    args = parser.parse_args()

    # Resolve CSV path
    csv_path = Path(args.csv_file)
    if not csv_path.is_absolute() and not csv_path.exists():
        # Try ../CSV/ directory
        csv_path = Path(__file__).parent.parent / 'CSV' / args.csv_file

    if not csv_path.exists():
        print(f"Error: CSV file not found: {csv_path}")
        sys.exit(1)

    # Create analyzer
    print(f"Initializing Feature Analyzer...")
    analyzer = FeatureAnalyzer(
        csv_path=str(csv_path),
        output_dir=args.output,
        progname=args.name
    )

    # Run analyses
    analyzer.run_all_analyses()

    print(f"\nAll analysis results saved to: {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
