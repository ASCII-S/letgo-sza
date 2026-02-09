"""
Golden生成器模块

协调器，整合ConfigManager、ApplicationExecutor、OutputCapturer。
"""

import os
from typing import Optional, List, Dict

from ..config_manager import ConfigManager, ApplicationConfig
from .app_executor import ApplicationExecutor, ExecutionResult
from .output_capturer import OutputCapturer, GoldenOutput


class GoldenGenerator:
    """Golden输出生成器（协调器）"""

    def __init__(
        self,
        config_path: Optional[str] = None,
        golden_base: Optional[str] = None,
        timeout: int = 300
    ):
        """
        初始化Golden生成器

        Args:
            config_path: applications.json路径（默认自动查找）
            golden_base: Golden输出基础目录（默认为sdc_judge/golden_outputs）
            timeout: 应用执行超时时间（秒）
        """
        # 初始化配置管理器
        self.config_mgr = ConfigManager(config_path)

        # 设置golden_base默认路径
        if golden_base is None:
            # 获取 sdc_judge/ 目录（golden/ 的父目录）
            sdc_judge_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            golden_base = os.path.join(sdc_judge_dir, 'golden_outputs')

        self.golden_base = golden_base

        # 初始化执行器和捕获器
        self.executor = ApplicationExecutor(timeout=timeout)
        self.capturer = OutputCapturer(golden_base=golden_base)

    def generate_single(
        self,
        app_name: str,
        force_regenerate: bool = False
    ) -> GoldenOutput:
        """
        生成单个应用的Golden输出

        Args:
            app_name: 应用名称
            force_regenerate: 强制重新生成（即使已存在）

        Returns:
            GoldenOutput对象

        Raises:
            ValueError: 如果应用不存在
            Exception: 如果执行失败
        """
        # 1. 获取应用配置
        app_config = self.config_mgr.get_app(app_name)
        if app_config is None:
            raise ValueError(f"应用不存在: {app_name}")

        # 2. 检查是否已存在
        if self.capturer.golden_exists(app_config) and not force_regenerate:
            golden_dir = self.capturer.get_golden_path(app_config)
            print(f"Golden已存在: {golden_dir}")
            print("使用 --force 强制重新生成")
            return GoldenOutput.from_dir(golden_dir)

        # 3. 执行应用（使用应用所在目录作为工作目录）
        print(f"执行应用: {app_name}")
        print(f"命令: {app_config.binpath} {' '.join(app_config.args)}")
        if app_config.working_dir:
            print(f"工作目录: {app_config.working_dir}")

        # 4. 执行应用
        try:
            exec_result = self.executor.execute(app_config)
        except Exception as e:
            raise Exception(f"应用执行失败: {e}")

        # 5. 检查执行结果
        if exec_result.returncode != 0:
            print(f"警告: 应用返回非零值: {exec_result.returncode}")
            # 不抛出异常，继续保存输出

        # 6. 捕获并保存输出
        print(f"保存Golden输出...")
        golden_output = self.capturer.capture_and_save(app_config, exec_result)

        print(f"✓ Golden生成成功: {golden_output.golden_dir}")
        return golden_output

    def generate_all(
        self,
        suites: Optional[List[str]] = None,
        force_regenerate: bool = False
    ) -> Dict[str, Optional[GoldenOutput]]:
        """
        批量生成Golden输出

        Args:
            suites: 指定套件列表（默认所有）
            force_regenerate: 强制重新生成

        Returns:
            字典：{app_name: GoldenOutput或None}
        """
        # 获取应用列表
        if suites:
            apps = []
            for suite in suites:
                apps.extend(self.config_mgr.get_suite_apps(suite))
        else:
            apps = self.config_mgr.get_all_apps()

        if not apps:
            print("没有找到应用")
            return {}

        print(f"准备生成 {len(apps)} 个应用的Golden输出")
        print("="*60)

        results = {}
        success_count = 0
        fail_count = 0

        for i, app_config in enumerate(apps):
            print(f"\n[{i+1}/{len(apps)}] 处理: {app_config.name} ({app_config.suite})")
            print("-"*60)

            try:
                golden = self.generate_single(app_config.name, force_regenerate)
                results[app_config.name] = golden
                success_count += 1
            except Exception as e:
                print(f"✗ 失败: {e}")
                results[app_config.name] = None
                fail_count += 1

        # 打印汇总
        print("\n" + "="*60)
        print(f"批量生成完成: {success_count}/{len(apps)} 成功")
        if fail_count > 0:
            print(f"失败: {fail_count} 个应用")
            print("\n失败的应用:")
            for name, result in results.items():
                if result is None:
                    print(f"  - {name}")
        print("="*60)

        return results

    def list_available_apps(self) -> List[str]:
        """列出所有可用的应用名称"""
        return self.config_mgr.get_all_app_names()

    def list_available_suites(self) -> List[str]:
        """列出所有可用的套件名称"""
        return self.config_mgr.get_suite_names()

    def get_app_info(self, app_name: str) -> Optional[Dict]:
        """
        获取应用信息

        Args:
            app_name: 应用名称

        Returns:
            应用信息字典或None
        """
        app_config = self.config_mgr.get_app(app_name)
        if app_config is None:
            return None

        return {
            'name': app_config.name,
            'suite': app_config.suite,
            'binpath': app_config.binpath,
            'args': app_config.args,
            'is_mpi': app_config.is_mpi,
            'output_type': app_config.output_type,
            'output_files': app_config.output_files,
            'needs_stdout': app_config.needs_stdout,
            'needs_stderr': app_config.needs_stderr,
            'tolerance': app_config.tolerance,
            'compare_method': app_config.compare_method,
            'golden_path': self.capturer.get_golden_path(app_config),
            'golden_exists': self.capturer.golden_exists(app_config),
        }

    def validate_golden(self, app_name: str) -> bool:
        """
        验证Golden输出是否存在且完整

        Args:
            app_name: 应用名称

        Returns:
            True如果有效，False否则
        """
        app_config = self.config_mgr.get_app(app_name)
        if app_config is None:
            return False

        if not self.capturer.golden_exists(app_config):
            return False

        # 检查是否有输出文件
        golden_dir = self.capturer.get_golden_path(app_config)
        files = os.listdir(golden_dir)

        # 至少应该有metadata.json
        if 'metadata.json' not in files:
            return False

        # 如果需要stdout，检查stdout.txt
        if app_config.needs_stdout and 'stdout.txt' not in files:
            return False

        return True
