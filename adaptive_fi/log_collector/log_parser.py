"""
日志解析器模块

从单个日志文件中提取所有关键信息。
"""

import re
import os
from typing import Dict, Optional, Tuple, List
from dataclasses import dataclass


class LogPatterns:
    """日志解析正则表达式模式库"""

    # ==== 旧版格式（GDB注错） ====
    # 基本注错信息
    PARAM_LIST = r"\['([^']*)', '([^']*)', '(\d+)', '(\d+)'\]"
    HEXPC = r"hexpc\s+([0-9a-fA-Fx]+)"
    BIT_LOCATION = r"bit location:\s*(\d+)"
    ITERATION = r"rechoose iteration.*?:\s*(\d+)"

    # ==== 新版格式（Pin+GDB联合注错） ====
    # Pin+GDB联合注错实验头部
    NEW_TARGET_PC = r"目标指令:\s*(0x[0-9a-fA-F]+)"
    NEW_TARGET_REG = r"目标寄存器:\s*(\w+)"
    NEW_INJECT_KTH = r"注错次数:\s*(\d+)"
    NEW_INJECT_BIT = r"注错位:\s*(-?\d+)"

    # ==== 通用模式 ====
    # 崩溃检测
    CRASH_SIGNAL = r"Program received signal (\w+)"

    # LetGo标记
    LETGO_MARKER = r"Letgo in!|LetGo修复框架"

    # SDC检测
    SDC_RESULT = r"Compare within tolerance\([^)]+\):\s*(True|False)"

    # 反汇编指令 - 只匹配到行尾
    DISASM = r"=> 0x[0-9a-fA-F]+\s*<[^>]+>:\s*([^\n]+)"

    # 时间戳
    TIMESTAMP = r"now time:\s*([0-9\-\s:\.]+)"


class LogParser:
    """单个日志文件解析器"""

    def __init__(self, log_path: str):
        """
        初始化解析器

        Args:
            log_path: 日志文件路径
        """
        self.log_path = log_path
        self.log_index = self._extract_log_index()
        self.content = None
        self._compile_patterns()

    def _extract_log_index(self) -> int:
        """从文件名提取日志编号"""
        basename = os.path.basename(self.log_path)
        match = re.match(r'log_(\d+)', basename)
        if match:
            return int(match.group(1))
        return -1

    def _compile_patterns(self):
        """预编译正则表达式（性能优化）"""
        self.patterns = {
            # 旧版格式
            'param_list': re.compile(LogPatterns.PARAM_LIST),
            'hexpc': re.compile(LogPatterns.HEXPC),
            'bit_location': re.compile(LogPatterns.BIT_LOCATION),
            'iteration': re.compile(LogPatterns.ITERATION),
            # 新版格式
            'new_target_pc': re.compile(LogPatterns.NEW_TARGET_PC),
            'new_target_reg': re.compile(LogPatterns.NEW_TARGET_REG),
            'new_inject_kth': re.compile(LogPatterns.NEW_INJECT_KTH),
            'new_inject_bit': re.compile(LogPatterns.NEW_INJECT_BIT),
            # 通用
            'crash_signal': re.compile(LogPatterns.CRASH_SIGNAL),
            'letgo_marker': re.compile(LogPatterns.LETGO_MARKER),
            'sdc_result': re.compile(LogPatterns.SDC_RESULT),
            'disasm': re.compile(LogPatterns.DISASM),
            'timestamp': re.compile(LogPatterns.TIMESTAMP),
        }

    def _read_file(self) -> str:
        """读取日志文件，尝试多种编码"""
        encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'gbk']

        for encoding in encodings:
            try:
                with open(self.log_path, 'r', encoding=encoding) as f:
                    return f.read()
            except (UnicodeDecodeError, LookupError):
                continue

        # 如果所有编码都失败，使用errors='ignore'
        with open(self.log_path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()

    def parse(self) -> Dict:
        """
        主解析函数，返回所有提取的字段

        Returns:
            包含所有字段的字典
        """
        self.content = self._read_file()

        return {
            'log_index': self.log_index,
            'target_pc_hex': self._extract_pc_hex(),
            'target_pc_dec': self._extract_pc_dec(),
            'target_register': self._extract_register(),
            'inject_iteration': self._extract_iteration(),
            'inject_bit': self._extract_bit_location(),
            'crash_count': self._count_crashes()[0],
            'crash_signals': self._count_crashes()[1],
            'used_letgo': self._detect_letgo(),
            'has_sdc': self._detect_sdc(),
            'result': self._classify_result(),
            'disasm': self._extract_disasm(),
            'timestamp': self._extract_timestamp(),
        }

    def _extract_pc_hex(self) -> Optional[str]:
        """提取十六进制PC地址"""
        # 尝试新版格式
        match = self.patterns['new_target_pc'].search(self.content)
        if match:
            return match.group(1)

        # 尝试旧版格式
        match = self.patterns['hexpc'].search(self.content)
        if match:
            pc_hex = match.group(1)
            # 确保格式为 0xXXXXXX
            if not pc_hex.startswith('0x'):
                pc_hex = '0x' + pc_hex
            return pc_hex
        return None

    def _extract_pc_dec(self) -> Optional[int]:
        """提取十进制PC地址"""
        # 尝试从十六进制转换
        pc_hex = self._extract_pc_hex()
        if pc_hex:
            try:
                return int(pc_hex, 16)
            except ValueError:
                pass

        # 尝试旧版格式的参数列表
        match = self.patterns['param_list'].search(self.content)
        if match:
            try:
                return int(match.group(3))
            except (ValueError, IndexError):
                pass
        return None

    def _extract_register(self) -> Optional[str]:
        """提取目标寄存器"""
        # 尝试新版格式
        match = self.patterns['new_target_reg'].search(self.content)
        if match:
            return match.group(1).strip()

        # 尝试旧版格式
        match = self.patterns['param_list'].search(self.content)
        if match:
            reg = match.group(1).strip()
            if reg:
                return reg
        return None

    def _extract_iteration(self) -> Optional[int]:
        """提取注错迭代次数"""
        # 尝试新版格式
        match = self.patterns['new_inject_kth'].search(self.content)
        if match:
            try:
                return int(match.group(1))
            except (ValueError, IndexError):
                pass

        # 尝试旧版格式：从 "rechoose iteration" 行提取
        match = self.patterns['iteration'].search(self.content)
        if match:
            try:
                return int(match.group(1))
            except (ValueError, IndexError):
                pass

        # 尝试从参数列表第4项提取
        match = self.patterns['param_list'].search(self.content)
        if match:
            try:
                return int(match.group(4))
            except (ValueError, IndexError):
                pass

        return None

    def _extract_bit_location(self) -> Optional[int]:
        """提取注错位位置"""
        # 尝试新版格式
        match = self.patterns['new_inject_bit'].search(self.content)
        if match:
            try:
                val = int(match.group(1))
                # 新版格式中 -1 表示无位级错误（整体错误）
                if val == -1:
                    return None
                return val
            except (ValueError, IndexError):
                pass

        # 尝试旧版格式
        match = self.patterns['bit_location'].search(self.content)
        if match:
            try:
                return int(match.group(1))
            except (ValueError, IndexError):
                pass
        return None

    def _count_crashes(self) -> Tuple[int, str]:
        """
        统计程序崩溃次数和信号类型

        Returns:
            (崩溃次数, 信号类型字符串)
        """
        matches = self.patterns['crash_signal'].findall(self.content)
        crash_count = len(matches)

        # 提取唯一的信号类型
        unique_signals = list(set(matches)) if matches else []
        signals_str = ', '.join(unique_signals) if unique_signals else ''

        return crash_count, signals_str

    def _detect_letgo(self) -> bool:
        """检测是否使用LetGo修复框架"""
        return bool(self.patterns['letgo_marker'].search(self.content))

    def _detect_sdc(self) -> Optional[bool]:
        """
        检测SDC (Silent Data Corruption)

        Returns:
            True: 有SDC
            False: 无SDC (Masked)
            None: 无法判断
        """
        matches = self.patterns['sdc_result'].findall(self.content)
        if matches:
            # 使用最后一个匹配（通常是最终结果）
            last_match = matches[-1]
            if last_match == 'False':
                return True  # 有SDC
            elif last_match == 'True':
                return False  # 无SDC (Masked)

        return None  # 无法判断

    def _classify_result(self) -> str:
        """
        根据日志内容分类结果

        分类逻辑复用自 adaptive_fi_wrapper.py:286-323
        """
        crash_count = self._count_crashes()[0]
        letgo_used = self._detect_letgo()
        has_sdc = self._detect_sdc()

        if crash_count == 0:
            # 无崩溃
            if has_sdc == True:
                return "SDC"
            else:
                return "Masked"

        elif crash_count == 1:
            # 一次崩溃
            if letgo_used:
                # 进入修复
                if has_sdc == True:
                    return "C-SDC"
                else:
                    return "C-Masked"
            else:
                # 崩溃但未进入修复
                return "Crash"

        else:  # crash_count >= 2
            # 二次或多次崩溃
            return "Recrash"

    def _extract_disasm(self) -> Optional[str]:
        """提取反汇编指令"""
        match = self.patterns['disasm'].search(self.content)
        if match:
            instr = match.group(1).strip()
            # 移除多余的控制字符
            instr = re.sub(r'\s+', ' ', instr)
            return instr
        return None

    def _extract_timestamp(self) -> Optional[str]:
        """提取时间戳"""
        match = self.patterns['timestamp'].search(self.content)
        if match:
            # 清理时间戳格式
            timestamp = match.group(1).strip()
            return timestamp
        return None


def validate_log(log_path: str) -> Tuple[bool, List[str]]:
    """
    验证日志文件的基本完整性

    Args:
        log_path: 日志文件路径

    Returns:
        (是否有效, 警告列表)
    """
    warnings = []

    try:
        # 检查文件大小
        if not os.path.exists(log_path):
            warnings.append("文件不存在")
            return False, warnings

        file_size = os.path.getsize(log_path)
        if file_size < 100:
            warnings.append(f"文件过小 ({file_size} bytes)")

        # 尝试读取文件
        parser = LogParser(log_path)
        content = parser._read_file()

        # 检查关键信息是否存在
        if len(content) < 50:
            warnings.append("文件内容过少")

        if "args ready" not in content:
            warnings.append("缺少注错参数信息 (args ready)")

        if "hexpc" not in content:
            warnings.append("缺少PC地址信息 (hexpc)")

        # 检查异常标记
        if "Traceback" in content or "Exception" in content:
            warnings.append("文件包含异常堆栈")

        return len(warnings) == 0, warnings

    except Exception as e:
        warnings.append(f"读取异常: {str(e)}")
        return False, warnings
