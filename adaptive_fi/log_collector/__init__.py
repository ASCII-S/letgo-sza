"""
日志收集模块

该模块提供了从adaptive_fi实验日志中提取信息并生成CSV的功能。

主要组件：
- LogParser: 日志文件解析器
- CSVGenerator: CSV文件生成器
- LogCollector: 日志收集协调器
- AppConfig: 应用配置管理器
"""

from .log_parser import LogParser
from .csv_generator import CSVGenerator
from .collector import LogCollector
from .app_config import AppConfig, get_config, get_app_config, get_golden_path

__all__ = [
    'LogParser',
    'CSVGenerator',
    'LogCollector',
    'AppConfig',
    'get_config',
    'get_app_config',
    'get_golden_path'
]
__version__ = '1.0.0'
