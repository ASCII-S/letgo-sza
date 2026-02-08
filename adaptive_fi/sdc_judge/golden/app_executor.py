"""
应用执行器模块

负责执行应用程序，处理普通应用和MPI应用。
"""

import os
import subprocess
import shlex
from typing import Optional, List
from dataclasses import dataclass

from ..config_manager import ApplicationConfig


@dataclass
class ExecutionResult:
    """执行结果"""

    stdout: str
    stderr: str
    returncode: int
    output_files: List[str]
    command: str


class ApplicationExecutor:
    """应用程序执行器"""

    def __init__(self, timeout: int = 300):
        """
        初始化执行器

        Args:
            timeout: 超时时间（秒），默认300秒
        """
        self.timeout = timeout

    def execute(
        self,
        app_config: ApplicationConfig,
        work_dir: Optional[str] = None
    ) -> ExecutionResult:
        """
        执行应用程序

        Args:
            app_config: 应用配置
            work_dir: 工作目录（用于输出文件）
                     如果为None，优先使用app_config.working_dir
                     如果还是None，则使用应用所在目录

        Returns:
            ExecutionResult对象
        """
        # 确定工作目录
        if work_dir is None:
            work_dir = app_config.working_dir

        if app_config.is_mpi:
            return self._execute_mpi(app_config, work_dir)
        else:
            return self._execute_normal(app_config, work_dir)

    def _execute_normal(
        self,
        app_config: ApplicationConfig,
        work_dir: Optional[str]
    ) -> ExecutionResult:
        """
        执行普通应用

        Args:
            app_config: 应用配置
            work_dir: 工作目录

        Returns:
            ExecutionResult对象
        """
        # 设置环境变量（nn等程序需要OUTPUT=1才会输出文件）
        env = os.environ.copy()
        env['OUTPUT'] = '1'

        # 检查是否需要shell执行（处理重定向）
        has_redirect = app_config.has_stderr_redirect()

        if has_redirect:
            # 需要使用shell处理重定向
            cmd_str = f"{app_config.binpath} {' '.join(app_config.args)}"
            result = subprocess.run(
                cmd_str,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=self.timeout,
                cwd=work_dir or os.getcwd(),
                env=env
            )
            command = cmd_str
        else:
            # 正常执行
            cmd = app_config.get_command()
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=self.timeout,
                cwd=work_dir or os.getcwd(),
                env=env
            )
            command = ' '.join(cmd)

        # 收集输出文件
        output_files = self._collect_output_files(app_config, work_dir)

        return ExecutionResult(
            stdout=result.stdout,
            stderr=result.stderr,
            returncode=result.returncode,
            output_files=output_files,
            command=command
        )

    def _execute_mpi(
        self,
        app_config: ApplicationConfig,
        work_dir: Optional[str]
    ) -> ExecutionResult:
        """
        执行MPI应用

        Args:
            app_config: 应用配置
            work_dir: 工作目录

        Returns:
            ExecutionResult对象
        """
        # 设置环境变量（确保一致性）
        env = os.environ.copy()
        env['OUTPUT'] = '1'

        # 构建mpirun命令
        cmd = ['mpirun', '-np', '1', app_config.binpath] + app_config.args

        # 移除重定向（MPI应用一般不用）
        cmd = [arg for arg in cmd if '>' not in arg]

        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=self.timeout,
            cwd=work_dir or os.getcwd(),
            env=env
        )

        # MPI应用通常无文件输出
        output_files = self._collect_output_files(app_config, work_dir)

        return ExecutionResult(
            stdout=result.stdout,
            stderr=result.stderr,
            returncode=result.returncode,
            output_files=output_files,
            command=' '.join(cmd)
        )

    def _collect_output_files(
        self,
        app_config: ApplicationConfig,
        work_dir: Optional[str]
    ) -> List[str]:
        """
        收集应用生成的输出文件

        Args:
            app_config: 应用配置
            work_dir: 工作目录

        Returns:
            找到的输出文件绝对路径列表
        """
        output_files = []
        search_dir = work_dir or os.getcwd()

        for output_file in app_config.output_files:
            # 如果是绝对路径
            if os.path.isabs(output_file):
                if os.path.exists(output_file):
                    output_files.append(output_file)
            else:
                # 相对路径，在工作目录中查找
                full_path = os.path.join(search_dir, output_file)
                if os.path.exists(full_path):
                    output_files.append(full_path)

        return output_files

    def execute_with_retry(
        self,
        app_config: ApplicationConfig,
        work_dir: Optional[str] = None,
        max_retries: int = 3
    ) -> ExecutionResult:
        """
        执行应用（带重试）

        Args:
            app_config: 应用配置
            work_dir: 工作目录
            max_retries: 最大重试次数

        Returns:
            ExecutionResult对象

        Raises:
            Exception: 如果所有重试都失败
        """
        last_exception = None

        for attempt in range(max_retries):
            try:
                return self.execute(app_config, work_dir)
            except subprocess.TimeoutExpired as e:
                last_exception = e
                print(f"执行超时，重试 {attempt + 1}/{max_retries}...")
            except Exception as e:
                last_exception = e
                print(f"执行失败: {e}，重试 {attempt + 1}/{max_retries}...")

        raise Exception(f"执行失败，已重试{max_retries}次: {last_exception}")
