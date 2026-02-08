"""
输出捕获器模块

负责捕获应用输出（stdout和输出文件）并保存到Golden目录。
"""

import os
import json
import shutil
from typing import Dict, Optional
from datetime import datetime
from dataclasses import dataclass

from ..config_manager import ApplicationConfig
from .app_executor import ExecutionResult


@dataclass
class GoldenOutput:
    """Golden输出信息"""

    golden_dir: str  # golden输出目录
    outputs: Dict[str, str]  # 输出文件映射 {文件名: 路径}
    metadata: Dict  # 元数据

    @classmethod
    def from_dir(cls, golden_dir: str) -> 'GoldenOutput':
        """从已存在的目录加载Golden输出"""
        metadata_path = os.path.join(golden_dir, 'metadata.json')

        # 加载元数据
        metadata = {}
        if os.path.exists(metadata_path):
            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)

        # 收集输出文件
        outputs = {}
        for filename in os.listdir(golden_dir):
            file_path = os.path.join(golden_dir, filename)
            if os.path.isfile(file_path) and filename != 'metadata.json':
                outputs[filename] = file_path

        return cls(golden_dir, outputs, metadata)


class OutputCapturer:
    """输出捕获器"""

    def __init__(self, golden_base: str = 'golden_outputs'):
        """
        初始化捕获器

        Args:
            golden_base: Golden输出的基础目录名（默认在sdc_judge目录内）
        """
        self.golden_base = golden_base

    def capture_and_save(
        self,
        app_config: ApplicationConfig,
        exec_result: ExecutionResult
    ) -> GoldenOutput:
        """
        捕获并保存Golden输出

        Args:
            app_config: 应用配置
            exec_result: 执行结果

        Returns:
            GoldenOutput对象
        """
        # 获取Golden目录
        golden_dir = self._get_golden_dir(app_config)
        os.makedirs(golden_dir, exist_ok=True)

        outputs = {}

        # 1. 保存stdout
        if app_config.needs_stdout:
            stdout_path = os.path.join(golden_dir, 'stdout.txt')
            self._save_stdout(exec_result.stdout, stdout_path)
            outputs['stdout.txt'] = stdout_path

        # 2. 保存输出文件
        for file_path in exec_result.output_files:
            if os.path.exists(file_path):
                dest_filename = os.path.basename(file_path)
                dest_path = os.path.join(golden_dir, dest_filename)
                try:
                    shutil.copy2(file_path, dest_path)
                    outputs[dest_filename] = dest_path
                except Exception as e:
                    print(f"警告: 复制输出文件失败 {file_path}: {e}")

        # 3. 保存元数据
        metadata = self._create_metadata(app_config, exec_result, outputs)
        metadata_path = os.path.join(golden_dir, 'metadata.json')
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

        return GoldenOutput(golden_dir, outputs, metadata)

    def _get_golden_dir(self, app_config: ApplicationConfig) -> str:
        """
        获取Golden输出目录

        目录结构：{golden_base}/{suite}/{app_name}/

        Args:
            app_config: 应用配置

        Returns:
            Golden目录路径
        """
        return os.path.join(self.golden_base, app_config.suite, app_config.name)

    def _save_stdout(self, stdout: str, stdout_path: str) -> None:
        """
        保存标准输出

        Args:
            stdout: 标准输出内容
            stdout_path: 保存路径
        """
        with open(stdout_path, 'w', encoding='utf-8', errors='ignore') as f:
            f.write(stdout)

    def _create_metadata(
        self,
        app_config: ApplicationConfig,
        exec_result: ExecutionResult,
        outputs: Dict[str, str]
    ) -> Dict:
        """
        创建元数据

        Args:
            app_config: 应用配置
            exec_result: 执行结果
            outputs: 输出文件映射

        Returns:
            元数据字典
        """
        return {
            'app_name': app_config.name,
            'suite': app_config.suite,
            'binpath': app_config.binpath,
            'args': app_config.args,
            'pc_start': app_config.pc_start,
            'pc_end': app_config.pc_end,
            'is_mpi': app_config.is_mpi,
            'tolerance': app_config.tolerance,
            'compare_method': app_config.compare_method,
            'returncode': exec_result.returncode,
            'command': exec_result.command,
            'generated_at': datetime.now().isoformat(),
            'outputs': list(outputs.keys()),
        }

    def golden_exists(self, app_config: ApplicationConfig) -> bool:
        """
        检查Golden输出是否已存在

        Args:
            app_config: 应用配置

        Returns:
            True如果已存在，False否则
        """
        golden_dir = self._get_golden_dir(app_config)
        return os.path.exists(golden_dir) and os.path.isdir(golden_dir)

    def get_golden_path(self, app_config: ApplicationConfig) -> str:
        """
        获取Golden目录路径

        Args:
            app_config: 应用配置

        Returns:
            Golden目录路径
        """
        return self._get_golden_dir(app_config)

    def get_stdout_path(self, app_config: ApplicationConfig) -> str:
        """
        获取stdout.txt的路径

        Args:
            app_config: 应用配置

        Returns:
            stdout.txt的路径
        """
        return os.path.join(self._get_golden_dir(app_config), 'stdout.txt')

    def get_output_file_path(self, app_config: ApplicationConfig, filename: str) -> str:
        """
        获取输出文件的路径

        Args:
            app_config: 应用配置
            filename: 文件名

        Returns:
            文件的路径
        """
        return os.path.join(self._get_golden_dir(app_config), filename)
