#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
应用配置加载工具（共享）

供 profile 文件夹下各维度的剖析脚本使用
- application: 应用程序维度
- function: 函数维度
- instruction: 指令维度
"""

import os
import json
from pathlib import Path


class ApplicationConfig:
    """应用配置管理器"""

    def __init__(self, profile_home=None):
        """
        初始化配置管理器

        Args:
            profile_home: profile 目录路径（可选，自动检测）
        """
        if profile_home is None:
            # 自动检测 profile 目录
            current_file = os.path.abspath(__file__)
            if 'profile' in current_file:
                # 如果在 profile 下的子目录，向上查找
                parts = Path(current_file).parts
                try:
                    profile_idx = parts.index('profile')
                    profile_home = os.path.join(*parts[:profile_idx + 1])
                except ValueError:
                    # 找不到 profile 目录，使用默认路径
                    profile_home = os.path.dirname(os.path.dirname(__file__))
            else:
                profile_home = os.path.dirname(os.path.dirname(__file__))

        self.profile_home = profile_home
        self.config_file = os.path.join(profile_home, 'applications.json')
        self.config_data = None
        self._load_config()

    def _load_config(self):
        """加载配置文件"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self.config_data = json.load(f)
            except Exception as e:
                raise RuntimeError(f"无法加载配置文件 {self.config_file}: {e}")
        else:
            raise FileNotFoundError(f"配置文件不存在: {self.config_file}")

    def get_app_config(self, app_name):
        """
        获取指定应用的配置

        Args:
            app_name: 应用名称

        Returns:
            dict: 应用配置信息
        """
        if not self.config_data:
            raise RuntimeError("配置未加载")

        for suite_name, suite_data in self.config_data.get('suites', {}).items():
            for app, config in suite_data.get('applications', {}).items():
                if app == app_name:
                    return {
                        'app_name': app_name,
                        'suite': suite_name,
                        **config
                    }

        raise ValueError(f"未找到应用配置: {app_name}")

    def get_all_apps(self):
        """获取所有应用名称"""
        apps = []
        for suite_data in self.config_data.get('suites', {}).values():
            apps.extend(suite_data.get('applications', {}).keys())
        return apps

    def get_suite_apps(self, suite_name):
        """获取指定套件的所有应用"""
        suite_data = self.config_data.get('suites', {}).get(suite_name, {})
        return list(suite_data.get('applications', {}).keys())

    def get_all_suites(self):
        """获取所有套件名称"""
        return list(self.config_data.get('suites', {}).keys())

    def get_app_binpath(self, app_name):
        """获取应用的二进制文件路径"""
        config = self.get_app_config(app_name)
        return config['binpath']

    def get_app_args(self, app_name):
        """获取应用的命令行参数"""
        config = self.get_app_config(app_name)
        return config.get('args', [])

    def get_app_pc_range(self, app_name):
        """获取应用的 PC 范围"""
        config = self.get_app_config(app_name)
        return (config.get('pc_start'), config.get('pc_end'))

    def is_mpi_app(self, app_name):
        """检查应用是否为 MPI 应用"""
        config = self.get_app_config(app_name)
        return config.get('is_mpi', False)

    def print_summary(self):
        """打印配置摘要"""
        print(f"\n{'='*70}")
        print("应用配置加载器")
        print(f"{'='*70}")
        print(f"配置文件: {self.config_file}")
        print(f"文件存在: {'✓' if os.path.exists(self.config_file) else '✗'}")

        if self.config_data:
            total = 0
            for suite_name, suite_data in self.config_data.get('suites', {}).items():
                count = len(suite_data.get('applications', {}))
                total += count
                print(f"  {suite_name}: {count} 个应用")
            print(f"  总计: {total} 个应用")

        print(f"{'='*70}\n")


def get_app_config_loader(profile_home=None):
    """获取应用配置加载器实例"""
    return ApplicationConfig(profile_home)


if __name__ == '__main__':
    # 测试脚本
    try:
        loader = ApplicationConfig()
        loader.print_summary()

        # 测试获取应用配置
        print("\n测试应用配置查询:")
        test_apps = ['backprop', 'HPCCG', 'bt']
        for app in test_apps:
            try:
                config = loader.get_app_config(app)
                print(f"\n  {app}:")
                print(f"    Suite: {config['suite']}")
                print(f"    Binary: {config['binpath']}")
                print(f"    MPI: {loader.is_mpi_app(app)}")
            except Exception as e:
                print(f"  {app}: 错误 - {e}")

    except Exception as e:
        print(f"✗ 错误: {e}")
        import sys
        sys.exit(1)
