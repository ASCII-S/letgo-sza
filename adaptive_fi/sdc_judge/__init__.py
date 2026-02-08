"""
SDC判定模块

提供以下功能：
1. 读取应用配置(applications.json)
2. 执行应用程序并捕获输出
3. 生成Golden输出
4. SDC判定（比较输出与Golden）

模块结构：
- config_manager: 配置管理器
- golden: Golden生成相关
  - app_executor: 应用执行器
  - output_capturer: 输出捕获器
  - golden_generator: Golden生成器
- judge: SDC判断相关
  - sdc_comparator: SDC比较器
  - sdc_judge: SDC判断器

主要组件：
- ConfigManager: 配置管理器
- ApplicationExecutor: 应用执行器
- OutputCapturer: 输出捕获器
- GoldenGenerator: Golden生成器
- SDCComparator: SDC比较器
- SDCJudge: SDC判断器
"""

from .config_manager import ConfigManager, ApplicationConfig
from .golden import (
    ApplicationExecutor,
    ExecutionResult,
    OutputCapturer,
    GoldenOutput,
    GoldenGenerator,
)
from .judge import (
    SDCComparator,
    CompareResult,
    SDCJudge,
    SDCJudgeResult,
)

__all__ = [
    # 配置管理
    'ConfigManager',
    'ApplicationConfig',
    # Golden生成
    'ApplicationExecutor',
    'ExecutionResult',
    'OutputCapturer',
    'GoldenOutput',
    'GoldenGenerator',
    # SDC判断
    'SDCComparator',
    'CompareResult',
    'SDCJudge',
    'SDCJudgeResult',
]

__version__ = '1.1.0'
