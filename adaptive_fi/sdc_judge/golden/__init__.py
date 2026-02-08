"""
Golden输出生成模块

提供以下功能：
1. 执行应用程序并捕获输出
2. 生成Golden输出
3. 管理Golden输出目录

主要组件：
- ApplicationExecutor: 应用执行器
- OutputCapturer: 输出捕获器
- GoldenGenerator: Golden生成器（协调器）
"""

from .app_executor import ApplicationExecutor, ExecutionResult
from .output_capturer import OutputCapturer, GoldenOutput
from .golden_generator import GoldenGenerator

__all__ = [
    'ApplicationExecutor',
    'ExecutionResult',
    'OutputCapturer',
    'GoldenOutput',
    'GoldenGenerator',
]
