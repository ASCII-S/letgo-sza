#!/usr/bin/env python3
"""
trace_parser.py - unified_tracer.so JSON 输出解析模块

解析易崩溃指令及其寄存器溯源链，提供数据结构供自适应注错使用。
"""

import json
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple


@dataclass
class SourceInst:
    """溯源指令 - 表示数据流中的一个源头指令"""
    offset: int              # 指令偏移（十进制）
    disasm: str              # 反汇编字符串
    depth: int               # 溯源深度（1=直接来源，2=二级来源...）
    hit_count: int           # 命中次数

    @classmethod
    def from_dict(cls, data: dict) -> 'SourceInst':
        """从 JSON 字典创建实例"""
        return cls(
            offset=int(data['offset'], 16),  # 十六进制转十进制
            disasm=data['disasm'],
            depth=data['depth'],
            hit_count=data['hit_count']
        )


@dataclass
class InjectionTarget:
    """注错目标 - 表示一个待测试的 (指令, 寄存器) 对"""
    offset: int              # 指令偏移（十进制）
    register: str            # 目标寄存器
    disasm: str              # 反汇编字符串
    depth: int               # 当前深度（0=易崩溃点本身）
    exec_count: int          # 执行次数
    cp_type: str = ""        # 易崩溃类型（仅 depth=0 时有意义）
    parent_offset: Optional[int] = None  # 父指令偏移

    # 运行时统计
    injection_count: int = 0
    crash_count: int = 0
    masked_count: int = 0
    sdc_count: int = 0
    results: List[str] = field(default_factory=list)

    @property
    def crash_rate(self) -> float:
        """计算崩溃率"""
        if self.injection_count == 0:
            return 0.0
        return self.crash_count / self.injection_count

    @property
    def key(self) -> Tuple[int, str]:
        """唯一标识键"""
        return (self.offset, self.register)

    def to_dict(self) -> dict:
        """转换为字典，用于 JSON 输出"""
        return {
            "offset": hex(self.offset),
            "register": self.register,
            "disasm": self.disasm,
            "depth": self.depth,
            "exec_count": self.exec_count,
            "cp_type": self.cp_type,
            "parent_offset": hex(self.parent_offset) if self.parent_offset else None,
            "injection_count": self.injection_count,
            "crash_count": self.crash_count,
            "masked_count": self.masked_count,
            "sdc_count": self.sdc_count,
            "crash_rate": round(self.crash_rate, 4),
            "results": self.results
        }


@dataclass
class CrashScenario:
    """崩溃场景 - 一个易崩溃指令及其所有寄存器的溯源"""
    offset: int              # 易崩溃指令偏移（十进制）
    disasm: str              # 反汇编字符串
    cp_type: str             # 易崩溃类型: mem_write, mem_read, index_access, indirect_cf, div
    exec_count: int          # 执行次数
    crash_regs: List[str]    # 崩溃寄存器列表
    register_traces: Dict[str, List[SourceInst]]  # 每个寄存器的溯源链

    @classmethod
    def from_dict(cls, data: dict) -> 'CrashScenario':
        """从 JSON 字典创建实例"""
        offset = int(data['offset'], 16)

        # 解析每个寄存器的溯源链
        register_traces = {}
        for reg_name, sources in data.get('register_traces', {}).items():
            trace_list = [SourceInst.from_dict(src) for src in sources]
            # 按深度排序
            trace_list.sort(key=lambda x: x.depth)
            register_traces[reg_name] = trace_list

        return cls(
            offset=offset,
            disasm=data['disasm'],
            cp_type=data['type'],
            exec_count=data['exec_count'],
            crash_regs=data['crash_regs'],
            register_traces=register_traces
        )

    def get_sources_at_depth(self, register: str, depth: int) -> List[SourceInst]:
        """获取指定寄存器在指定深度的溯源指令"""
        if register not in self.register_traces:
            return []
        return [src for src in self.register_traces[register] if src.depth == depth]

    def create_target(self, register: str, depth: int = 0,
                      parent_offset: Optional[int] = None) -> InjectionTarget:
        """为指定寄存器创建注错目标"""
        return InjectionTarget(
            offset=self.offset,
            register=register,
            disasm=self.disasm,
            depth=depth,
            exec_count=self.exec_count,
            cp_type=self.cp_type,
            parent_offset=parent_offset
        )


class TraceParser:
    """溯源 JSON 解析器"""

    def __init__(self, json_path: str):
        self.json_path = json_path
        self.config: dict = {}
        self.scenarios: List[CrashScenario] = []
        self.statistics: dict = {}

    def parse(self) -> List[CrashScenario]:
        """解析 JSON 文件，返回崩溃场景列表"""
        with open(self.json_path, 'r') as f:
            data = json.load(f)

        # 解析配置
        self.config = data.get('config', {})

        # 解析统计信息
        self.statistics = data.get('statistics', {})

        # 解析所有崩溃场景
        self.scenarios = [
            CrashScenario.from_dict(inst)
            for inst in data.get('crashprone_insts', [])
        ]

        return self.scenarios

    def get_top_scenarios(self, top_k: int) -> List[CrashScenario]:
        """按执行次数排序，返回 Top-K 场景"""
        sorted_scenarios = sorted(self.scenarios, key=lambda s: s.exec_count, reverse=True)
        return sorted_scenarios[:top_k]

    def filter_by_type(self, cp_types: List[str]) -> List[CrashScenario]:
        """按易崩溃类型过滤"""
        return [s for s in self.scenarios if s.cp_type in cp_types]

    def get_all_targets_at_depth0(self) -> List[InjectionTarget]:
        """获取所有 depth=0 的注错目标"""
        targets = []
        for scenario in self.scenarios:
            for reg in scenario.crash_regs:
                target = scenario.create_target(reg, depth=0)
                targets.append(target)
        return targets

    def summary(self) -> str:
        """返回解析结果摘要"""
        total_regs = sum(len(s.crash_regs) for s in self.scenarios)
        total_traces = sum(
            len(traces)
            for s in self.scenarios
            for traces in s.register_traces.values()
        )

        return (
            f"Trace Summary:\n"
            f"  Total crash-prone instructions: {len(self.scenarios)}\n"
            f"  Total crash registers: {total_regs}\n"
            f"  Total trace entries: {total_traces}\n"
            f"  Statistics: {self.statistics}"
        )


def parse_trace_json(json_path: str) -> List[CrashScenario]:
    """便捷函数：解析 JSON 并返回场景列表"""
    parser = TraceParser(json_path)
    return parser.parse()


# ============== 测试代码 ==============
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python trace_parser.py <trace_result.json>")
        sys.exit(1)

    json_path = sys.argv[1]
    parser = TraceParser(json_path)
    scenarios = parser.parse()

    print(parser.summary())
    print("\n" + "=" * 60)

    # 打印前 5 个场景
    for i, scenario in enumerate(scenarios[:5]):
        print(f"\n[{i+1}] 0x{scenario.offset:x}: {scenario.disasm}")
        print(f"    Type: {scenario.cp_type}, Exec: {scenario.exec_count}")
        print(f"    Crash regs: {scenario.crash_regs}")

        for reg, traces in scenario.register_traces.items():
            print(f"    {reg} traces ({len(traces)} entries):")
            for src in traces[:3]:
                print(f"      depth={src.depth}: 0x{src.offset:x} {src.disasm} (hit={src.hit_count})")
