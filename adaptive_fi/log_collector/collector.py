"""
日志收集器模块

协调日志扫描、解析和CSV生成。
"""

import os
import re
import json
from typing import List, Optional, Tuple, Dict
import pandas as pd
from datetime import datetime

from .log_parser import LogParser, validate_log
from .csv_generator import CSVGenerator


class LogCollector:
    """日志收集协调器"""

    def __init__(self, log_folder: str, app_name: Optional[str] = None):
        """
        初始化收集器

        Args:
            log_folder: 日志文件夹路径
            app_name: 应用程序名称（用于输出文件名）
        """
        self.log_folder = log_folder
        self.app_name = app_name or "unknown"
        self.csv_gen = CSVGenerator()
        self.warnings = []
        self.parsed_count = 0
        self.failed_count = 0

    def scan_logs(self, log_range: Optional[Tuple[int, int]] = None) -> List[str]:
        """
        扫描log文件夹中的日志文件

        Args:
            log_range: 可选的日志范围 (start, end)，例如 (0, 100)

        Returns:
            排序后的日志文件路径列表
        """
        if not os.path.exists(self.log_folder):
            raise FileNotFoundError(f"日志文件夹不存在: {self.log_folder}")

        # 扫描所有 log_N 文件
        log_files = []
        pattern = re.compile(r'log_(\d+)$')

        for filename in os.listdir(self.log_folder):
            match = pattern.match(filename)
            if match:
                log_index = int(match.group(1))

                # 检查是否在范围内
                if log_range:
                    start, end = log_range
                    if log_index < start or log_index > end:
                        continue

                log_path = os.path.join(self.log_folder, filename)
                log_files.append((log_index, log_path))

        # 按日志编号排序
        log_files.sort(key=lambda x: x[0])

        return [path for _, path in log_files]

    def collect_all(self,
                    log_range: Optional[Tuple[int, int]] = None,
                    verbose: bool = False,
                    validate: bool = True,
                    collect_sdc_results: bool = True) -> pd.DataFrame:
        """
        收集所有日志

        Args:
            log_range: 可选的日志范围
            verbose: 是否输出详细信息
            validate: 是否在解析前验证日志
            collect_sdc_results: 是否同时收集SDC判断结果

        Returns:
            包含所有数据的DataFrame
        """
        log_files = self.scan_logs(log_range)

        # 加载SDC结果（如果存在）
        sdc_results = {}
        if collect_sdc_results:
            sdc_results = self._load_sdc_results(log_range)
            if verbose and sdc_results:
                print(f"找到 {len(sdc_results)} 个SDC判断结果")

        if verbose:
            print(f"\n找到 {len(log_files)} 个日志文件")
            print(f"开始解析...\n")

        for i, log_path in enumerate(log_files):
            if verbose and (i + 1) % 10 == 0:
                print(f"进度: {i + 1}/{len(log_files)}")

            try:
                # 可选：验证日志完整性
                if validate:
                    is_valid, warnings = validate_log(log_path)
                    if not is_valid:
                        self._handle_error(log_path, f"验证失败: {'; '.join(warnings)}")
                        continue

                # 解析日志
                parser = LogParser(log_path)
                data = parser.parse()

                # 关联SDC结果
                log_index = parser.log_index
                if log_index in sdc_results:
                    sdc_data = sdc_results[log_index]
                    data['is_sdc'] = sdc_data.get('is_sdc', None)
                    data['sdc_method'] = sdc_data.get('method', None)
                    data['sdc_tolerance'] = sdc_data.get('tolerance', None)
                    data['sdc_message'] = sdc_data.get('message', None)
                else:
                    # 如果没有SDC结果，设置为None
                    data['is_sdc'] = None
                    data['sdc_method'] = None
                    data['sdc_tolerance'] = None
                    data['sdc_message'] = None

                # 添加到CSV
                self.csv_gen.append_row(data)
                self.parsed_count += 1

            except Exception as e:
                self._handle_error(log_path, str(e))

        if verbose:
            print(f"\n解析完成!")
            print(f"成功: {self.parsed_count}, 失败: {self.failed_count}")

        return self.csv_gen.get_dataframe()

    def generate_csv(self,
                     output_path: Optional[str] = None,
                     show_statistics: bool = False) -> str:
        """
        生成CSV文件

        Args:
            output_path: 输出CSV路径（如不指定，自动生成）
            show_statistics: 是否显示统计摘要

        Returns:
            生成的CSV文件路径
        """
        # 如果未指定输出路径，自动生成
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = f"{self.app_name}_logs_{timestamp}.csv"

        # 保存CSV
        self.csv_gen.to_csv(output_path)

        # 显示统计信息
        if show_statistics:
            self.csv_gen.print_statistics()

        return output_path

    def _handle_error(self, log_file: str, error: str):
        """
        处理解析错误

        Args:
            log_file: 日志文件路径
            error: 错误信息
        """
        self.failed_count += 1
        warning = {
            'file': os.path.basename(log_file),
            'path': log_file,
            'error': error,
            'timestamp': datetime.now().isoformat(),
        }
        self.warnings.append(warning)

    def _load_sdc_results(self, log_range: Optional[Tuple[int, int]] = None) -> Dict[int, Dict]:
        """
        从sdcresult/目录加载SDC判断结果

        Args:
            log_range: 日志范围 (start, end)

        Returns:
            {log_index: sdc_result_dict} 映射
        """
        sdc_results = {}

        # 构建sdcresult目录路径
        # log_folder通常是 one_batch_folder/log，所以父目录是one_batch_folder
        base_folder = os.path.dirname(self.log_folder)
        sdc_result_folder = os.path.join(base_folder, "sdcresult")

        if not os.path.exists(sdc_result_folder):
            return sdc_results

        # 扫描sdc_N.json文件
        pattern = re.compile(r'^sdc_(\d+)\.json$')

        for filename in os.listdir(sdc_result_folder):
            match = pattern.match(filename)
            if match:
                log_index = int(match.group(1))

                # 检查范围
                if log_range:
                    start, end = log_range
                    if log_index < start or log_index > end:
                        continue

                # 加载JSON
                try:
                    filepath = os.path.join(sdc_result_folder, filename)
                    with open(filepath, 'r', encoding='utf-8') as f:
                        sdc_data = json.load(f)
                        sdc_results[log_index] = sdc_data
                except Exception as e:
                    # 静默处理加载失败（不影响日志收集）
                    pass

        return sdc_results

    def save_warning_log(self, warning_path: str = "warnings.log"):
        """
        保存警告日志

        Args:
            warning_path: 警告日志文件路径
        """
        if not self.warnings:
            return

        with open(warning_path, 'w', encoding='utf-8') as f:
            f.write("日志解析警告和错误报告\n")
            f.write("=" * 60 + "\n")
            f.write(f"总计: {len(self.warnings)} 个问题\n")
            f.write("=" * 60 + "\n\n")

            for i, warning in enumerate(self.warnings, 1):
                f.write(f"{i}. {warning['file']}\n")
                f.write(f"   路径: {warning['path']}\n")
                f.write(f"   错误: {warning['error']}\n")
                f.write(f"   时间: {warning['timestamp']}\n")
                f.write("\n")

    def get_summary(self) -> dict:
        """
        获取收集摘要

        Returns:
            包含摘要信息的字典
        """
        stats = self.csv_gen.get_statistics()

        return {
            'log_folder': self.log_folder,
            'app_name': self.app_name,
            'total_scanned': self.parsed_count + self.failed_count,
            'parsed_success': self.parsed_count,
            'parsed_failed': self.failed_count,
            'success_rate': (self.parsed_count / (self.parsed_count + self.failed_count) * 100)
                            if (self.parsed_count + self.failed_count) > 0 else 0.0,
            'statistics': stats,
            'warnings_count': len(self.warnings),
        }

    def print_summary(self):
        """打印收集摘要到控制台"""
        summary = self.get_summary()

        print("\n" + "=" * 60)
        print("日志收集摘要")
        print("=" * 60)
        print(f"应用程序: {summary['app_name']}")
        print(f"日志文件夹: {summary['log_folder']}")
        print(f"\n总扫描文件: {summary['total_scanned']}")
        print(f"成功解析: {summary['parsed_success']}")
        print(f"解析失败: {summary['parsed_failed']}")
        print(f"成功率: {summary['success_rate']:.1f}%")

        if summary['warnings_count'] > 0:
            print(f"\n⚠️  警告: {summary['warnings_count']} 个文件解析异常")
            print("   使用 save_warning_log() 保存详细信息")

        print("=" * 60)


def parse_log_range(range_str: str) -> Tuple[int, int]:
    """
    解析日志范围字符串

    Args:
        range_str: 范围字符串，如 "0-100" 或 "0:100"

    Returns:
        (start, end) 元组

    Raises:
        ValueError: 如果格式无效
    """
    if '-' in range_str:
        parts = range_str.split('-')
    elif ':' in range_str:
        parts = range_str.split(':')
    else:
        raise ValueError(f"无效的范围格式: {range_str}。应为 'start-end' 或 'start:end'")

    if len(parts) != 2:
        raise ValueError(f"无效的范围格式: {range_str}")

    try:
        start = int(parts[0].strip())
        end = int(parts[1].strip())
    except ValueError:
        raise ValueError(f"无效的数字: {range_str}")

    if start > end:
        raise ValueError(f"起始值不能大于结束值: {start} > {end}")

    return start, end
