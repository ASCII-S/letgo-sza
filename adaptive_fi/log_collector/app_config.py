#!/usr/bin/env python3
"""
应用配置管理模块

加载和管理应用程序配置，支持 golden output 和 SDC 判定。
"""

import json
import os
from typing import Dict, Optional, Any, List


class AppConfig:
    """应用配置管理器"""

    _instance = None
    _config: Dict[str, Any] = {}

    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_config()
        return cls._instance

    def _load_config(self) -> None:
        """加载配置文件"""
        # 配置文件放在 adaptive_fi 根目录，便于复用
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'app_config.json'
        )

        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                self._config = json.load(f)
        else:
            self._config = {'applications': {}}

    def reload(self) -> None:
        """重新加载配置"""
        self._load_config()

    def get_app(self, app_name: str) -> Optional[Dict[str, Any]]:
        """
        获取应用配置

        Args:
            app_name: 应用名称

        Returns:
            应用配置字典，不存在则返回 None
        """
        return self._config.get('applications', {}).get(app_name)

    def get_all_apps(self) -> List[str]:
        """获取所有已配置的应用名称"""
        return list(self._config.get('applications', {}).keys())

    def get_output_type(self, app_name: str) -> str:
        """
        获取应用的输出类型

        Args:
            app_name: 应用名称

        Returns:
            输出类型: 'stdout', 'file', 或 'both'
        """
        app = self.get_app(app_name)
        if app:
            return app.get('output_type', 'stdout')
        return 'stdout'

    def get_golden_output(self, app_name: str) -> Optional[Dict[str, Any]]:
        """
        获取 golden output 配置

        Args:
            app_name: 应用名称

        Returns:
            golden output 配置字典
        """
        app = self.get_app(app_name)
        if app:
            return app.get('golden_output')
        return None

    def get_golden_output_path(self, app_name: str) -> Optional[str]:
        """
        获取 golden output 文件路径

        Args:
            app_name: 应用名称

        Returns:
            golden output 文件路径，不存在则返回 None
        """
        golden = self.get_golden_output(app_name)
        if golden:
            return golden.get('file')
        return None

    def get_output_pattern(self, app_name: str) -> Optional[str]:
        """
        获取输出文件匹配模式

        Args:
            app_name: 应用名称

        Returns:
            输出文件 glob 模式
        """
        golden = self.get_golden_output(app_name)
        if golden:
            return golden.get('pattern')
        return None

    def get_sdc_config(self, app_name: str) -> Optional[Dict[str, Any]]:
        """
        获取 SDC 检测配置

        Args:
            app_name: 应用名称

        Returns:
            SDC 检测配置字典
        """
        app = self.get_app(app_name)
        if app:
            return app.get('sdc_detection')
        return None

    def get_sdc_tolerance(self, app_name: str) -> float:
        """
        获取 SDC 检测容差

        Args:
            app_name: 应用名称

        Returns:
            数值比较容差
        """
        sdc = self.get_sdc_config(app_name)
        if sdc:
            return sdc.get('tolerance', 0)
        return 0

    def set_golden_output(self, app_name: str, file_path: str) -> bool:
        """
        设置 golden output 文件路径

        Args:
            app_name: 应用名称
            file_path: golden output 文件路径

        Returns:
            是否设置成功
        """
        if app_name not in self._config.get('applications', {}):
            return False

        if 'golden_output' not in self._config['applications'][app_name]:
            self._config['applications'][app_name]['golden_output'] = {}

        self._config['applications'][app_name]['golden_output']['file'] = file_path
        return True

    def save(self) -> None:
        """保存配置到文件"""
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'app_config.json'
        )

        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(self._config, f, indent=2, ensure_ascii=False)

    def is_configured(self, app_name: str) -> bool:
        """检查应用是否已配置"""
        return app_name in self._config.get('applications', {})

    def add_app(self, app_name: str, config: Dict[str, Any]) -> None:
        """
        添加新应用配置

        Args:
            app_name: 应用名称
            config: 应用配置字典
        """
        if 'applications' not in self._config:
            self._config['applications'] = {}
        self._config['applications'][app_name] = config

    def get_apps_by_suite(self, suite: str) -> List[str]:
        """
        获取指定套件的所有应用

        Args:
            suite: 套件名称 (rodinia, mantevo, etc.)

        Returns:
            应用名称列表
        """
        apps = []
        for name, config in self._config.get('applications', {}).items():
            if config.get('suite') == suite:
                apps.append(name)
        return apps

    def get_apps_by_output_type(self, output_type: str) -> List[str]:
        """
        获取指定输出类型的所有应用

        Args:
            output_type: 输出类型 ('stdout', 'file', 'both')

        Returns:
            应用名称列表
        """
        apps = []
        for name, config in self._config.get('applications', {}).items():
            if config.get('output_type') == output_type:
                apps.append(name)
        return apps


# 便捷函数
def get_config() -> AppConfig:
    """获取配置管理器实例"""
    return AppConfig()


def get_app_config(app_name: str) -> Optional[Dict[str, Any]]:
    """获取应用配置"""
    return get_config().get_app(app_name)


def get_golden_path(app_name: str) -> Optional[str]:
    """获取 golden output 路径"""
    return get_config().get_golden_output_path(app_name)


def is_file_output(app_name: str) -> bool:
    """检查应用是否输出到文件"""
    output_type = get_config().get_output_type(app_name)
    return output_type in ('file', 'both')


def is_stdout_output(app_name: str) -> bool:
    """检查应用是否输出到终端"""
    output_type = get_config().get_output_type(app_name)
    return output_type in ('stdout', 'both')
