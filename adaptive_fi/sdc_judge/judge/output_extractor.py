"""
输出提取器模块

根据应用的 output_type 从正确位置提取程序输出：
- stdout/stderr 应用：从 log/log_N 日志文件中提取
- file 应用：从 sdcout/log_N_output.xxx 文件中获取
"""

import os
import re
from dataclasses import dataclass
from typing import Optional, List
from pathlib import Path

# 导入配置管理器
import sys
sdc_judge_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if sdc_judge_dir not in sys.path:
    sys.path.insert(0, sdc_judge_dir)

from config_manager import ConfigManager


@dataclass
class ExtractedOutput:
    """提取的输出结果"""
    content: str  # 输出内容（文件路径或实际内容）
    source: str  # 来源：'log', 'sdcout', 'temp_file'
    source_path: str  # 源文件路径
    output_type: str  # 输出类型：'stdout', 'stderr', 'file'
    is_file: bool  # 是否为文件路径（True）或内容字符串（False）
    error: Optional[str] = None  # 错误信息


class OutputExtractor:
    """
    输出提取器

    统一处理不同输出类型的提取逻辑：
    - stdout/stderr: 从日志文件中解析提取
    - file: 从 sdcout 目录获取输出文件
    """

    # 日志中的分隔符
    SEPARATOR = "=" * 60

    # 日志中的标记
    STDOUT_MARKER = "程序输出 (stdout):"
    STDERR_MARKER = "程序错误输出 (stderr):"
    CLEANUP_MARKER = "[清理]"

    def __init__(self, config_path: Optional[str] = None):
        """
        初始化输出提取器

        Args:
            config_path: applications.json 路径（可选）
        """
        self.config_mgr = ConfigManager(config_path)
        # 临时文件目录
        self._temp_dir = None

    def _find_exact_separator(self, content: str, start_pos: int = 0) -> int:
        """
        查找精确的分隔符行（正好是 60 个等号的独立行）

        这个方法避免匹配到程序输出中包含更多等号的行（如 HPL 的 80 等号行）

        Args:
            content: 要搜索的内容
            start_pos: 开始搜索的位置

        Returns:
            分隔符的起始位置，如果未找到返回 -1
        """
        pos = start_pos
        while True:
            # 查找下一个分隔符
            pos = content.find(self.SEPARATOR, pos)
            if pos == -1:
                return -1

            # 检查这是否是独立的 60 等号行
            # 获取该行的起始和结束位置
            line_start = content.rfind('\n', 0, pos)
            line_start = line_start + 1 if line_start != -1 else 0

            line_end = content.find('\n', pos)
            line_end = line_end if line_end != -1 else len(content)

            # 提取整行内容
            line = content[line_start:line_end]

            # 检查是否正好是 60 个等号
            if line == self.SEPARATOR:
                return line_start  # 返回行的起始位置

            # 继续搜索
            pos += 1

    def extract(
        self,
        app_name: str,
        log_index: int,
        experiment_dir: str
    ) -> ExtractedOutput:
        """
        提取程序输出

        Args:
            app_name: 应用名称
            log_index: 日志索引
            experiment_dir: 实验目录 (如 .../2mm/adaptive/)

        Returns:
            ExtractedOutput: 包含输出内容和来源信息
        """
        # 获取应用配置
        app_config = self.config_mgr.get_app(app_name)
        if app_config is None:
            return ExtractedOutput(
                content="",
                source="error",
                source_path="",
                output_type="unknown",
                is_file=False,
                error=f"未找到应用配置: {app_name}"
            )

        output_type = app_config.output_type

        if output_type in ('stdout', 'stderr'):
            return self._extract_from_log(
                experiment_dir=experiment_dir,
                log_index=log_index,
                output_type=output_type
            )
        else:  # file
            return self._extract_from_sdcout(
                experiment_dir=experiment_dir,
                log_index=log_index,
                app_config=app_config
            )

    def _extract_from_log(
        self,
        experiment_dir: str,
        log_index: int,
        output_type: str
    ) -> ExtractedOutput:
        """
        从日志文件提取 stdout 或 stderr 内容

        Args:
            experiment_dir: 实验目录
            log_index: 日志索引
            output_type: 'stdout' 或 'stderr'

        Returns:
            ExtractedOutput
        """
        # 构建日志文件路径
        log_path = os.path.join(experiment_dir, 'log', f'log_{log_index}')

        if not os.path.exists(log_path):
            return ExtractedOutput(
                content="",
                source="log",
                source_path=log_path,
                output_type=output_type,
                is_file=False,
                error=f"日志文件不存在: {log_path}"
            )

        try:
            with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                log_content = f.read()

            # 解析日志，提取对应输出
            if output_type == 'stdout':
                extracted = self._parse_stdout_from_log(log_content)
            else:  # stderr
                extracted = self._parse_stderr_from_log(log_content)

            if extracted is None:
                return ExtractedOutput(
                    content="",
                    source="log",
                    source_path=log_path,
                    output_type=output_type,
                    is_file=False,
                    error=f"无法从日志中提取 {output_type} 内容"
                )

            # 将提取的内容保存到临时文件，以便比较器使用
            temp_file = self._save_to_temp_file(extracted, log_index, output_type)

            return ExtractedOutput(
                content=temp_file if temp_file else extracted,
                source="log",
                source_path=log_path,
                output_type=output_type,
                is_file=bool(temp_file)
            )

        except Exception as e:
            return ExtractedOutput(
                content="",
                source="log",
                source_path=log_path,
                output_type=output_type,
                is_file=False,
                error=f"读取日志失败: {e}"
            )

    def _parse_stdout_from_log(self, log_content: str) -> Optional[str]:
        """
        从日志内容中解析 stdout

        日志格式：
        程序输出 (stdout):
        ============================================================
        [stdout 内容]
        ============================================================
        程序错误输出 (stderr):
        ============================================================

        或者（无 stderr 时）：
        程序输出 (stdout):
        ============================================================
        [stdout 内容]
        ============================================================
        [清理] ...
        """
        # 查找 stdout 标记
        stdout_start = log_content.find(self.STDOUT_MARKER)
        if stdout_start == -1:
            return None

        # 跳过标记和分隔符
        content_start = stdout_start + len(self.STDOUT_MARKER)
        # 跳过分隔符行（使用精确匹配）
        sep_pos = self._find_exact_separator(log_content, content_start)
        if sep_pos != -1:
            # 跳过分隔符行和换行符
            content_start = sep_pos + len(self.SEPARATOR)
            # 跳过换行符
            if content_start < len(log_content) and log_content[content_start] == '\n':
                content_start += 1

        # 查找 stderr 标记作为结束位置
        stderr_start = log_content.find(self.STDERR_MARKER, content_start)
        if stderr_start != -1:
            # 找到 stderr 标记前的分隔符
            content_end = log_content.rfind(self.SEPARATOR, content_start, stderr_start)
            if content_end == -1:
                content_end = stderr_start
        else:
            # 如果没有 stderr 标记，查找 [清理] 标记
            cleanup_start = log_content.find(self.CLEANUP_MARKER, content_start)
            if cleanup_start != -1:
                # 找到 [清理] 标记前的精确分隔符
                # 从 content_start 开始向后查找最后一个精确分隔符
                content_end = cleanup_start
                # 向前查找最近的精确分隔符
                search_pos = content_start
                last_exact_sep = -1
                while True:
                    exact_sep = self._find_exact_separator(log_content, search_pos)
                    if exact_sep == -1 or exact_sep >= cleanup_start:
                        break
                    last_exact_sep = exact_sep
                    search_pos = exact_sep + len(self.SEPARATOR) + 1

                if last_exact_sep != -1:
                    content_end = last_exact_sep
            else:
                # 都没有，取到文件末尾
                content_end = len(log_content)

        # 提取内容
        stdout_content = log_content[content_start:content_end].strip()

        # 清理：移除开头的分隔符（如果有）
        if stdout_content.startswith(self.SEPARATOR):
            stdout_content = stdout_content[len(self.SEPARATOR):].strip()

        # 清理：移除 GDB 调试信息
        stdout_content = self._remove_gdb_debug_info(stdout_content)

        return stdout_content if stdout_content else None

    def _remove_gdb_debug_info(self, content: str) -> str:
        """
        移除 GDB 调试信息

        Pin+GDB 注错框架会在程序输出开头添加调试信息：
        - "Application stopped until continued from debugger."
        - "Start GDB, then issue this command at the (gdb) prompt:"
        - "  target remote :PORT"

        这些信息不是程序的实际输出，需要过滤掉。

        Args:
            content: 原始 stdout 内容

        Returns:
            过滤后的内容
        """
        if not content:
            return content

        lines = content.split('\n')
        filtered_lines = []
        skip_mode = False

        for line in lines:
            stripped = line.strip()

            # 检测 GDB 调试信息的开始
            if stripped == "Application stopped until continued from debugger.":
                skip_mode = True
                continue

            # 跳过 GDB 调试信息
            if skip_mode:
                if stripped.startswith("Start GDB, then issue this command"):
                    continue
                if stripped.startswith("target remote :"):
                    skip_mode = False  # 这是最后一行调试信息
                    continue

            # 跳过末尾的 "quit" 命令（GDB 退出命令）
            if stripped == "quit":
                continue

            filtered_lines.append(line)

        return '\n'.join(filtered_lines).strip()

    def _parse_stderr_from_log(self, log_content: str) -> Optional[str]:
        """
        从日志内容中解析 stderr

        日志格式：
        程序错误输出 (stderr):
        ============================================================
        [stderr 内容]
        """
        # 查找 stderr 标记
        stderr_start = log_content.find(self.STDERR_MARKER)
        if stderr_start == -1:
            return None

        # 跳过标记
        content_start = stderr_start + len(self.STDERR_MARKER)

        # 跳过分隔符行
        sep_pos = log_content.find(self.SEPARATOR, content_start)
        if sep_pos != -1 and sep_pos - content_start < 10:  # 分隔符应该紧跟标记
            content_start = sep_pos + len(self.SEPARATOR)

        # 查找结束位置（下一个主要分隔符或文件结束）
        # 通常 stderr 是日志的最后部分
        remaining = log_content[content_start:]

        # 查找可能的结束标记
        end_markers = [
            "\n" + self.SEPARATOR + "\n实验",  # 下一个实验开始
            "\n[时间戳]",  # 时间戳标记
        ]

        content_end = len(remaining)
        for marker in end_markers:
            pos = remaining.find(marker)
            if pos != -1 and pos < content_end:
                content_end = pos

        stderr_content = remaining[:content_end].strip()

        # 清理：移除开头的分隔符（如果有）
        if stderr_content.startswith(self.SEPARATOR):
            stderr_content = stderr_content[len(self.SEPARATOR):].strip()

        return stderr_content if stderr_content else None

    def _extract_from_sdcout(
        self,
        experiment_dir: str,
        log_index: int,
        app_config
    ) -> ExtractedOutput:
        """
        从 sdcout 目录获取输出文件

        Args:
            experiment_dir: 实验目录
            log_index: 日志索引
            app_config: 应用配置

        Returns:
            ExtractedOutput
        """
        sdcout_dir = os.path.join(experiment_dir, 'sdcout')

        if not os.path.exists(sdcout_dir):
            return ExtractedOutput(
                content="",
                source="sdcout",
                source_path=sdcout_dir,
                output_type="file",
                is_file=False,
                error=f"sdcout 目录不存在: {sdcout_dir}"
            )

        # 查找输出文件
        output_file = self._find_output_file(sdcout_dir, log_index, app_config)

        if output_file is None:
            return ExtractedOutput(
                content="",
                source="sdcout",
                source_path=sdcout_dir,
                output_type="file",
                is_file=False,
                error=f"未找到 log_{log_index} 的输出文件"
            )

        return ExtractedOutput(
            content=output_file,
            source="sdcout",
            source_path=output_file,
            output_type="file",
            is_file=True
        )

    def _find_output_file(
        self,
        sdcout_dir: str,
        log_index: int,
        app_config
    ) -> Optional[str]:
        """
        在 sdcout 目录中查找输出文件

        支持的命名模式：
        - log_{index}_output.{ext}
        - log_{index}.{ext}
        - log_{index}_{output_name}
        """
        # 获取预期的输出文件名
        output_name = getattr(app_config, 'output_name', None)

        # 尝试不同的命名模式
        patterns = [
            f"log_{log_index}_output.*",
            f"log_{log_index}.*",
        ]

        if output_name:
            # 获取扩展名
            _, ext = os.path.splitext(output_name)
            patterns.insert(0, f"log_{log_index}_output{ext}")
            patterns.insert(1, f"log_{log_index}{ext}")
            patterns.insert(2, f"log_{log_index}_{output_name}")

        # 列出目录中的文件
        try:
            files = os.listdir(sdcout_dir)
        except Exception:
            return None

        # 按模式匹配
        for pattern in patterns:
            regex = pattern.replace(".", r"\.").replace("*", ".*")
            for filename in files:
                if re.match(f"^{regex}$", filename):
                    return os.path.join(sdcout_dir, filename)

        return None

    def _save_to_temp_file(
        self,
        content: str,
        log_index: int,
        output_type: str
    ) -> Optional[str]:
        """
        将提取的内容保存到临时文件

        Args:
            content: 输出内容
            log_index: 日志索引
            output_type: 输出类型

        Returns:
            临时文件路径，失败返回 None
        """
        import tempfile

        if self._temp_dir is None:
            self._temp_dir = tempfile.mkdtemp(prefix="sdc_judge_")

        try:
            temp_file = os.path.join(
                self._temp_dir,
                f"log_{log_index}_{output_type}.txt"
            )
            with open(temp_file, 'w', encoding='utf-8') as f:
                f.write(content)
            return temp_file
        except Exception:
            return None

    def cleanup(self):
        """清理临时文件"""
        if self._temp_dir and os.path.exists(self._temp_dir):
            import shutil
            try:
                shutil.rmtree(self._temp_dir)
            except Exception:
                pass
            self._temp_dir = None

    def __del__(self):
        """析构时清理临时文件"""
        self.cleanup()


# 便捷函数
def extract_output(
    app_name: str,
    log_index: int,
    experiment_dir: str,
    config_path: Optional[str] = None
) -> ExtractedOutput:
    """
    提取程序输出的便捷函数

    Args:
        app_name: 应用名称
        log_index: 日志索引
        experiment_dir: 实验目录
        config_path: 配置文件路径（可选）

    Returns:
        ExtractedOutput
    """
    extractor = OutputExtractor(config_path)
    return extractor.extract(app_name, log_index, experiment_dir)
