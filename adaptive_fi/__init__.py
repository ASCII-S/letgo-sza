"""
adaptive_fi - 自适应故障注入模块

基于易崩溃指令溯源的自适应故障注入工具。
"""

from .trace_parser import (
    TraceParser,
    CrashScenario,
    InjectionTarget,
    SourceInst,
    parse_trace_json
)

__all__ = [
    'TraceParser',
    'CrashScenario',
    'InjectionTarget',
    'SourceInst',
    'parse_trace_json'
]

__version__ = '1.0.0'
