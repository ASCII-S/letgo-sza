#!/usr/bin/env python3
"""
简化版批量日志收集脚本

只收集以下字段：
- app_name: 应用名
- input_file: 日志序号 (log_N)
- inj_pc: 注错地址
- Sig1: 崩溃时信号
- Sig1pc: 崩溃时指令地址
- Sig1ins: Sig1pc对应的指令
- result: 实验结果
"""

import os
import re
import sys
import json
import argparse
import subprocess
from typing import Dict, Optional, List, Tuple
from pathlib import Path

# 尝试导入pandas，如果失败则使用csv模块
try:
    import pandas as pd
    USE_PANDAS = True
except ImportError:
    import csv
    USE_PANDAS = False


class SimpleLogParser:
    """简化版日志解析器"""

    # 正则模式
    PATTERNS = {
        'target_pc': re.compile(r'目标指令:\s*(0x[0-9a-fA-F]+)'),
        'crash_signal': re.compile(r'Program received signal (\w+)'),
        'crash_pc': re.compile(r'崩溃点PC\s*=\s*(0x[0-9a-fA-F]+)'),  # Step 1: 崩溃点PC = 0x...
        'letgo_marker': re.compile(r'LetGo崩溃恢复框架启动|Letgo in!'),
        'binary_path': re.compile(r'Reading symbols from ([^\s]+?)\.\.\.'),  # 从GDB输出提取二进制路径
    }

    def __init__(self, log_path: str, binary_path: str = None):
        self.log_path = log_path
        self.log_index = self._extract_log_index()
        self.binary_path = binary_path
        self._objdump_cache = {}  # 缓存objdump结果

    def _extract_log_index(self) -> str:
        """提取日志编号，返回 log_N 格式"""
        basename = os.path.basename(self.log_path)
        match = re.match(r'(log_\d+)', basename)
        return match.group(1) if match else basename

    def _read_file(self) -> str:
        """读取日志文件"""
        encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'gbk']
        for encoding in encodings:
            try:
                with open(self.log_path, 'r', encoding=encoding) as f:
                    return f.read()
            except UnicodeDecodeError:
                continue
        with open(self.log_path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()

    def parse(self) -> Dict:
        """解析日志，返回需要的字段"""
        content = self._read_file()

        # 如果没有提供binary_path，尝试从日志中提取
        if not self.binary_path:
            binary_match = self.PATTERNS['binary_path'].search(content)
            if binary_match:
                self.binary_path = binary_match.group(1)

        # 提取注错PC
        inj_pc = None
        match = self.PATTERNS['target_pc'].search(content)
        if match:
            inj_pc = match.group(1)

        # 提取崩溃信号
        crash_signals = self.PATTERNS['crash_signal'].findall(content)
        sig1 = crash_signals[0] if crash_signals else None

        # 提取崩溃PC：从 "崩溃点PC = 0x..." 提取
        sig1pc = None
        pc_match = self.PATTERNS['crash_pc'].search(content)
        if pc_match:
            sig1pc = self._simplify_hex(pc_match.group(1))

        # 获取Sig1pc对应的指令
        sig1ins = None
        if sig1pc:
            sig1ins = self._get_instruction_at_pc(sig1pc)

        # 检测LetGo
        letgo_used = bool(self.PATTERNS['letgo_marker'].search(content))

        # 分类结果（不做SDC判断，由外部SDC判断结果决定）
        crash_count = len(crash_signals)
        result = self._classify_result(crash_count, letgo_used)

        return {
            'input_file': self.log_index,
            'inj_pc': inj_pc,
            'Sig1': sig1,
            'Sig1pc': sig1pc,
            'Sig1ins': sig1ins,
            'result': result,
        }

    def _simplify_hex(self, hex_str: str) -> str:
        """简化十六进制地址，去掉前导零: 0x0000000000401be0 -> 0x401be0"""
        if not hex_str or not hex_str.startswith('0x'):
            return hex_str
        # 去掉0x前缀，去掉前导零，再加回0x
        hex_part = hex_str[2:].lstrip('0') or '0'
        return '0x' + hex_part

    def _classify_result(self, crash_count: int, letgo_used: bool) -> str:
        """分类实验结果（基础分类，SDC由外部判断结果决定）"""
        if crash_count == 0:
            return "Masked"  # 无崩溃，待SDC判断确定是Masked还是SDC
        elif crash_count == 1:
            if letgo_used:
                return "C-Masked"  # 崩溃后修复，待SDC判断
            else:
                return "Crash"
        else:
            return "Recrash"

    def _get_instruction_at_pc(self, pc: str) -> Optional[str]:
        """通过objdump获取指定PC地址的指令"""
        if not self.binary_path or not os.path.exists(self.binary_path):
            return None

        if not pc or not pc.startswith('0x'):
            return None

        # 检查缓存
        if pc in self._objdump_cache:
            return self._objdump_cache[pc]

        try:
            # 将十六进制地址转换为整数
            addr = int(pc, 16)

            # 使用objdump只反汇编目标地址附近的代码（前后各16字节）
            start_addr = max(0, addr - 16)
            stop_addr = addr + 16

            cmd = [
                'objdump', '-d',
                f'--start-address=0x{start_addr:x}',
                f'--stop-address=0x{stop_addr:x}',
                self.binary_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)

            if result.returncode != 0:
                return None

            # 解析objdump输出，查找对应地址的指令
            # 格式: "  401be0:	48 89 e5             	mov    %rsp,%rbp"
            pc_normalized = pc.lower().lstrip('0x').lstrip('0') or '0'
            pattern = re.compile(rf'^\s*{pc_normalized}:\s+([0-9a-f\s]+)\s+(.+)$', re.IGNORECASE)

            for line in result.stdout.split('\n'):
                match = pattern.match(line)
                if match:
                    instruction = match.group(2).strip()
                    self._objdump_cache[pc] = instruction
                    return instruction

            return None
        except Exception as e:
            return None


def load_sdc_results(sdc_folder: str) -> Dict[str, Dict]:
    """加载SDC判断结果"""
    sdc_results = {}
    if not os.path.exists(sdc_folder):
        return sdc_results

    pattern = re.compile(r'^sdc_(\d+)\.json$')
    for filename in os.listdir(sdc_folder):
        match = pattern.match(filename)
        if match:
            log_index = f"log_{match.group(1)}"
            try:
                with open(os.path.join(sdc_folder, filename), 'r') as f:
                    sdc_results[log_index] = json.load(f)
            except:
                pass
    return sdc_results


def collect_app_logs(app_folder: str, app_name: str, verbose: bool = False) -> List[Dict]:
    """收集单个应用的日志"""
    log_folder = os.path.join(app_folder, 'adaptive', 'log')
    sdc_folder = os.path.join(app_folder, 'adaptive', 'sdcresult')

    if not os.path.exists(log_folder):
        if verbose:
            print(f"  跳过 {app_name}: 日志文件夹不存在")
        return []

    # 查找二进制文件路径
    binary_path = None
    possible_paths = [
        os.path.join(app_folder, app_name),
        os.path.join(app_folder, 'bin', app_name),
        os.path.join(app_folder, app_name + '.out'),
    ]
    for path in possible_paths:
        if os.path.exists(path) and os.path.isfile(path):
            binary_path = path
            break

    if verbose and binary_path:
        print(f"  {app_name}: 找到二进制文件 {binary_path}")

    # 加载SDC判断结果
    sdc_results = {}  # {log_index: is_sdc}
    if os.path.exists(sdc_folder):
        pattern = re.compile(r'^sdc_(\d+)\.json$')
        for filename in os.listdir(sdc_folder):
            match = pattern.match(filename)
            if match:
                log_index = f"log_{match.group(1)}"
                try:
                    with open(os.path.join(sdc_folder, filename), 'r') as f:
                        data = json.load(f)
                        sdc_results[log_index] = data.get('is_sdc')
                except:
                    pass

    # 扫描日志文件
    log_pattern = re.compile(r'^log_(\d+)$')
    log_files = []
    for filename in os.listdir(log_folder):
        if log_pattern.match(filename):
            log_files.append(os.path.join(log_folder, filename))

    if verbose:
        print(f"  {app_name}: 找到 {len(log_files)} 个日志文件, SDC已判断 {len(sdc_results)} 个")

    results = []
    for log_path in log_files:
        try:
            parser = SimpleLogParser(log_path, binary_path)
            data = parser.parse()
            data['app_name'] = app_name

            # 根据SDC判断结果更新result
            log_index = data['input_file']
            if log_index in sdc_results:
                is_sdc = sdc_results[log_index]
                if is_sdc is not None:
                    if data['result'] == 'Masked':
                        data['result'] = 'SDC' if is_sdc else 'Masked'
                    elif data['result'] == 'C-Masked':
                        data['result'] = 'C-SDC' if is_sdc else 'C-Masked'

            results.append(data)
        except Exception as e:
            if verbose:
                print(f"    解析失败 {os.path.basename(log_path)}: {e}")

    return results


def batch_collect(result_dir: str, output_csv: str, apps: List[str] = None, verbose: bool = False):
    """批量收集所有应用的日志"""
    if not os.path.exists(result_dir):
        print(f"错误: 结果目录不存在: {result_dir}")
        return

    # 获取应用列表
    if apps:
        app_list = apps
    else:
        app_list = [d for d in os.listdir(result_dir)
                    if os.path.isdir(os.path.join(result_dir, d))]

    app_list.sort()
    print(f"准备收集 {len(app_list)} 个应用的日志...")

    all_results = []
    for app_name in app_list:
        app_folder = os.path.join(result_dir, app_name)
        results = collect_app_logs(app_folder, app_name, verbose)
        all_results.extend(results)

    if not all_results:
        print("没有收集到任何数据")
        return

    # 输出CSV
    columns = ['app_name', 'input_file', 'inj_pc', 'Sig1', 'Sig1pc', 'Sig1ins', 'result']

    if USE_PANDAS:
        df = pd.DataFrame(all_results, columns=columns)
        df.to_csv(output_csv, index=False, encoding='utf-8-sig')
    else:
        with open(output_csv, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=columns)
            writer.writeheader()
            for row in all_results:
                writer.writerow({k: row.get(k) for k in columns})

    print(f"\n收集完成!")
    print(f"总计: {len(all_results)} 条记录")
    print(f"输出文件: {output_csv}")

    # 统计结果分布
    result_counts = {}
    for r in all_results:
        result = r['result']
        result_counts[result] = result_counts.get(result, 0) + 1

    print("\n结果分布:")
    for result, count in sorted(result_counts.items()):
        pct = count / len(all_results) * 100
        print(f"  {result:10s}: {count:6d} ({pct:5.1f}%)")


def main():
    parser = argparse.ArgumentParser(description='简化版批量日志收集')
    parser.add_argument('--dir', '-d',
                        default='/home/tongshiyu/pin/source/tools/letgo/TargetedBenchmarkResult',
                        help='实验结果目录')
    parser.add_argument('--output', '-o',
                        default='collected_results.csv',
                        help='输出CSV文件路径')
    parser.add_argument('--apps', '-a', nargs='+',
                        help='指定要收集的应用（默认全部）')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='详细输出')

    args = parser.parse_args()
    batch_collect(args.dir, args.output, args.apps, args.verbose)


if __name__ == '__main__':
    main()
