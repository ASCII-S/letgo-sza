"""
配置管理器模块

负责读取applications.json，管理应用配置。
"""

import json
import os
import re
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field


# 应用比较方法映射
COMPARE_METHOD_MAP = {
    # 完全匹配
    'strong': ['bfs', 'backprop', 'nn', 'kmeans', 'particlefilter'],
    # 特定格式
    'hotspot': ['hotspot', 'hotspot3D'],
    'miniMD': ['miniMD'],
    'miniFE': ['miniFE'],
    'HPCCG': ['HPCCG'],
    'lu': ['lu'],
    'hpl': ['hpl'],
    'amg': ['amg'],
    # PolyBench
    'polybench': ['2mm', 'fdtd-2d', 'bicg', 'correlation', 'gesummv', 'syr2k', 'gaussian', 'convolution', 'mvt'],
    # NPB (NAS Parallel Benchmarks)
    'npb': ['bt', 'cg', 'ep', 'ft', 'is', 'mg', 'sp', 'ua'],
}

# 应用容差配置
TOLERANCE_MAP = {
    'hotspot': 1e-6,
    'hotspot3D': 1e-2,
    'lu': 1e-4,
    'miniMD': 1e-6,
    'miniFE': 1e-6,
    'HPCCG': 1e-6,
    'hpl': 16.0,  # HPL 使用阈值判定
    'amg': 1e-6,
    # PolyBench应用使用相对误差
    '2mm': 0.1,
    'fdtd-2d': 0.1,
    'bicg': 0.1,
    'correlation': 0.1,
    'gesummv': 0.1,
    'syr2k': 0.1,
    'gaussian': 0.1,
    'convolution': 0.1,
    'mvt': 0.1,
    # NPB应用使用内置验证，epsilon为精度阈值
    'bt': 1e-7,
    'cg': 1e-7,
    'ep': 1e-7,
    'ft': 1e-7,
    'is': 1e-7,
    'mg': 1e-7,
    'sp': 1e-7,
    'ua': 1e-7,
}

# 容差类型配置: 'absolute' (绝对误差) 或 'relative' (相对误差) 或 'threshold' (阈值判定)
TOLERANCE_TYPE_MAP = {
    # 绝对误差
    'hotspot': 'absolute',
    'hotspot3D': 'absolute',
    'lu': 'absolute',
    'miniMD': 'absolute',
    'miniFE': 'absolute',
    'HPCCG': 'absolute',
    # 阈值判定
    'hpl': 'threshold',
    # 相对误差
    '2mm': 'relative',
    'fdtd-2d': 'relative',
    'bicg': 'relative',
    'correlation': 'relative',
    'gesummv': 'relative',
    'syr2k': 'relative',
    'gaussian': 'relative',
    'convolution': 'relative',
    'mvt': 'relative',
    'amg': 'relative',
    # NPB应用使用内置验证（threshold类型，但验证逻辑在比较器内部）
    'bt': 'threshold',
    'cg': 'threshold',
    'ep': 'threshold',
    'ft': 'threshold',
    'is': 'threshold',
    'mg': 'threshold',
    'sp': 'threshold',
    'ua': 'threshold',
}

# 应用输出文件名配置（仅用于 output_type='file' 的应用）
OUTPUT_NAME_MAP = {
    # Rodinia file 类型应用
    'backprop': 'output.dat',
    'hotspot': 'output.txt',
    'hotspot3D': 'output.txt',
    'lu': 'lu_matrix_512.txt',
    'b+tree': 'output.txt',
    'bfs': 'output.txt',
    'heartwall': 'output.txt',
    'kmeans': 'output.txt',
    'leukocyte': 'result.txt',
    'nn': 'output.txt',
    'particlefilter': 'output.txt',
    'streamcluster': 'output.txt',
    # PolyBench应用 (stderr 类型，但有对应的输出文件名用于 golden 比较)
    '2mm': 'output_2mm.txt',
    'fdtd-2d': 'output_fdtd-2d.txt',
    'bicg': 'output_bicg.txt',
    'correlation': 'output_correlation.txt',
    'gesummv': 'output_gesummv.txt',
    'syr2k': 'output_syr2k.txt',
    'gaussian': 'output_gaussian.txt',
    'convolution': 'output_convolution.txt',
    'mvt': 'output_mvt.txt',
}

# MPI应用列表
MPI_APPS = ['HPCCG', 'miniFE', 'miniMD', 'miniAMR']

# 默认容差
DEFAULT_TOLERANCE = 0.1


@dataclass
class ApplicationConfig:
    """单应用配置"""

    name: str
    suite: str
    binpath: str
    args: List[str]
    pc_start: Optional[str] = None
    pc_end: Optional[str] = None
    is_mpi: bool = False

    # 自动推断的属性
    output_files: List[str] = field(default_factory=list)
    output_name: Optional[str] = None  # 应用输出文件名（如output.dat）
    needs_stdout: bool = True
    needs_stderr: bool = False  # 是否需要捕获stderr作为输出
    output_type: str = 'stdout'  # 输出类型: 'stdout', 'stderr', 'file'
    tolerance: float = DEFAULT_TOLERANCE
    tolerance_type: str = 'absolute'  # 容差类型: 'absolute' (绝对误差) 或 'relative' (相对误差)
    compare_method: str = 'common'
    working_dir: Optional[str] = None  # 工作目录（默认为应用所在目录）

    def __post_init__(self):
        """初始化后自动推断属性"""
        # 首先推断输出文件名（因为output_files依赖于output_name）
        self.output_name = self._get_output_name()
        self.output_files = self._extract_output_files()
        self.needs_stdout = self._needs_stdout_capture()
        self.tolerance = self._get_tolerance()
        self.tolerance_type = self._get_tolerance_type()
        self.compare_method = self._determine_compare_method()
        self.working_dir = self._determine_working_dir()

    def _get_output_name(self) -> Optional[str]:
        """
        获取应用输出文件名

        优先级：
        1. 从OUTPUT_NAME_MAP中查找应用名称
        2. 从args中提取（如果args中指定了输出文件）
        3. 返回None表示无文件输出或使用stdout

        Returns:
            输出文件名（如'output.dat'）或'none'（无输出文件）
        """
        # 优先使用映射表
        if self.name in OUTPUT_NAME_MAP:
            return OUTPUT_NAME_MAP[self.name]

        # 从args中查找
        for arg in self.args:
            # 跳过路径参数
            if arg.startswith('/') or arg.startswith('~'):
                continue
            # 检查是否是文件名
            if '.' in arg and not arg.startswith('-'):
                # 可能是输出文件名
                if arg.endswith(('.txt', '.dat', '.out')):
                    return arg

        return None

    def _extract_output_files(self) -> List[str]:
        """
        从args和output_name中提取完整的输出文件路径

        规则：
        1. 如果有output_name，在工作目录中查找
        2. 从args中提取重定向符号指定的文件
        3. 从args中提取最后的参数（如hotspot）
        """
        output_files = []

        # 规则1: 使用output_name和working_dir查找文件
        if self.output_name and self.output_name != 'none':
            # 如果是绝对路径
            if os.path.isabs(self.output_name):
                output_files.append(self.output_name)
            else:
                # 相对路径，会在执行时的工作目录中找到
                # 这里只保存文件名，后续会在app_executor中收集
                output_files.append(self.output_name)

        # 规则2: 重定向符号（优先处理）
        for arg in self.args:
            # 匹配 "2>/tmp/output.txt" 或 ">/path/file" 模式
            redirect_match = re.search(r'[12]?>(.+)', arg)
            if redirect_match:
                file_path = redirect_match.group(1).strip()
                if file_path not in output_files:  # 避免重复
                    output_files.append(file_path)

        # 规则3: hotspot系列的特殊处理（从args最后一个参数获取）
        if self.name in ['hotspot', 'hotspot3D']:
            if self.args and not self.args[-1].startswith('/'):
                # 最后一个参数通常是输出文件
                last_arg = self.args[-1]
                if last_arg.endswith(('.txt', '.dat', '.out')):
                    if last_arg not in output_files:
                        output_files.append(last_arg)

        # 规则4: streamcluster的特殊处理（倒数第二个参数）
        elif self.name == 'streamcluster':
            if len(self.args) >= 2:
                second_last = self.args[-2]
                if second_last.endswith(('.txt', '.dat', '.out')):
                    if second_last not in output_files:
                        output_files.append(second_last)

        return output_files

    def _needs_stdout_capture(self) -> bool:
        """
        判断是否需要捕获stdout

        MPI应用（HPCCG, miniFE, miniMD等）主要输出到stdout
        """
        # MPI应用需要捕获stdout
        if self.is_mpi or self.name in MPI_APPS:
            return True
        # 大多数应用都需要stdout
        return True

    def _get_tolerance(self) -> float:
        """获取容差配置"""
        return TOLERANCE_MAP.get(self.name, DEFAULT_TOLERANCE)

    def _get_tolerance_type(self) -> str:
        """
        获取容差类型

        Returns:
            'absolute' (绝对误差) 或 'relative' (相对误差)
        """
        return TOLERANCE_TYPE_MAP.get(self.name, 'absolute')

    def _determine_compare_method(self) -> str:
        """确定SDC比较方法"""
        for method, apps in COMPARE_METHOD_MAP.items():
            if self.name in apps:
                return method
        return 'common'

    def _determine_working_dir(self) -> Optional[str]:
        """
        确定工作目录

        策略：
        1. 使用应用二进制所在的目录（大多数应用）
        2. 对于某些特殊应用，可以指定特定的工作目录

        Returns:
            工作目录路径或None（表示使用临时目录）
        """
        # 获取应用所在目录
        binpath = self.binpath
        if binpath and os.path.exists(binpath):
            app_dir = os.path.dirname(os.path.abspath(binpath))
            # 对于某些需要配置文件的应用（如HPL），使用应用所在目录
            # 这样可以找到HPL.dat等配置文件
            return app_dir
        return None

    def get_command(self) -> List[str]:
        """获取执行命令（不包含重定向）"""
        # 过滤掉重定向参数（这些需要通过shell处理）
        clean_args = [arg for arg in self.args if '>' not in arg]
        return [self.binpath] + clean_args

    def has_stderr_redirect(self) -> bool:
        """检查是否有stderr重定向"""
        return any('2>' in arg for arg in self.args)

    def get_stderr_redirect_file(self) -> Optional[str]:
        """获取stderr重定向的文件路径"""
        for arg in self.args:
            if '2>' in arg:
                return arg.split('2>')[-1].strip()
        return None


class ConfigManager:
    """配置管理器"""

    def __init__(self, config_path: Optional[str] = None):
        """
        初始化配置管理器

        Args:
            config_path: applications.json的路径，默认为模块同级目录
        """
        if config_path is None:
            # 默认路径：adaptive_fi/applications.json
            module_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            config_path = os.path.join(module_dir, 'applications.json')

        self.config_path = config_path
        self._config: Dict[str, Any] = {}
        self._apps: Dict[str, ApplicationConfig] = {}
        self._load_config()

    def _load_config(self) -> None:
        """加载配置文件"""
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"配置文件不存在: {self.config_path}")

        with open(self.config_path, 'r', encoding='utf-8') as f:
            self._config = json.load(f)

        # 解析所有应用配置
        self._parse_apps()

    def _parse_apps(self) -> None:
        """解析所有应用配置"""
        suites = self._config.get('suites', {})

        for suite_name, suite_data in suites.items():
            apps = suite_data.get('applications', {})
            for app_name, app_data in apps.items():
                # 创建ApplicationConfig对象
                app_config = ApplicationConfig(
                    name=app_name,
                    suite=suite_name,
                    binpath=app_data.get('binpath', ''),
                    args=app_data.get('args', []),
                    pc_start=app_data.get('pc_start'),
                    pc_end=app_data.get('pc_end'),
                    is_mpi=app_data.get('is_mpi', False),
                )

                # 如果applications.json中指定了working_dir，覆盖自动推断的
                if 'working_dir' in app_data and app_data['working_dir']:
                    app_config.working_dir = app_data['working_dir']

                # 如果applications.json中指定了output_name，覆盖自动推断的
                if 'output_name' in app_data and app_data['output_name']:
                    app_config.output_name = app_data['output_name']
                    # 重新计算output_files
                    app_config.output_files = app_config._extract_output_files()

                # 如果applications.json中指定了output_type，覆盖默认值
                # output_type: 'stdout' | 'stderr' | 'file'
                if 'output_type' in app_data:
                    app_config.output_type = app_data['output_type']
                    # 根据output_type设置needs_stdout和needs_stderr
                    if app_config.output_type == 'stderr':
                        app_config.needs_stdout = False
                        app_config.needs_stderr = True
                    elif app_config.output_type == 'file':
                        app_config.needs_stdout = False
                        app_config.needs_stderr = False
                    else:  # stdout
                        app_config.needs_stdout = True
                        app_config.needs_stderr = False

                # 如果applications.json中指定了compare_method，覆盖自动推断的
                if 'compare_method' in app_data and app_data['compare_method']:
                    app_config.compare_method = app_data['compare_method']

                # 如果applications.json中指定了tolerance，覆盖自动推断的
                if 'tolerance' in app_data and app_data['tolerance'] is not None:
                    app_config.tolerance = app_data['tolerance']

                # 如果applications.json中指定了tolerance_type，覆盖自动推断的
                if 'tolerance_type' in app_data and app_data['tolerance_type']:
                    app_config.tolerance_type = app_data['tolerance_type']

                self._apps[app_name] = app_config

    def reload(self) -> None:
        """重新加载配置"""
        self._apps.clear()
        self._load_config()

    def get_app(self, name: str) -> Optional[ApplicationConfig]:
        """
        获取应用配置

        Args:
            name: 应用名称

        Returns:
            ApplicationConfig对象，不存在则返回None
        """
        return self._apps.get(name)

    def get_all_apps(self) -> List[ApplicationConfig]:
        """获取所有应用配置"""
        return list(self._apps.values())

    def get_all_app_names(self) -> List[str]:
        """获取所有应用名称"""
        return list(self._apps.keys())

    def get_suite_apps(self, suite: str) -> List[ApplicationConfig]:
        """
        获取特定套件的应用

        Args:
            suite: 套件名称（rodinia, mantevo, npb, polybench）

        Returns:
            该套件下的应用配置列表
        """
        return [app for app in self._apps.values() if app.suite == suite]

    def get_suite_names(self) -> List[str]:
        """获取所有套件名称"""
        return list(self._config.get('suites', {}).keys())

    def app_exists(self, name: str) -> bool:
        """检查应用是否存在"""
        return name in self._apps

    def get_metadata(self) -> Dict[str, Any]:
        """获取配置元数据"""
        return self._config.get('metadata', {})

    def __len__(self) -> int:
        """返回应用总数"""
        return len(self._apps)

    def __contains__(self, name: str) -> bool:
        """支持 'app_name' in config_manager 语法"""
        return name in self._apps

    def __iter__(self):
        """支持迭代"""
        return iter(self._apps.values())


def get_default_config_path() -> str:
    """获取默认配置文件路径"""
    module_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(module_dir, 'applications.json')


# 便捷函数
def load_config(config_path: Optional[str] = None) -> ConfigManager:
    """加载配置的便捷函数"""
    return ConfigManager(config_path)
