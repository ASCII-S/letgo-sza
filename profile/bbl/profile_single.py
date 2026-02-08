#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
单个应用程序BBL剖析脚本

功能：
1. 读取applications.json中的应用配置
2. 调用bbl_profiler进行BBL级剖析
3. 保存JSON结果
4. 处理MPI应用的特殊情况
5. 错误处理和日志记录
"""

import os
import sys
import subprocess
import argparse
import json
import time
from datetime import datetime
from pathlib import Path

# 添加配置路径
profile_home = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, profile_home)
from config import (
    PIN_BINARY, BBL_PROFILER_TOOL,
    get_app_config, get_bbl_output_json_path,
    PROFILE_TIMEOUT, MPI_APP, BBL_LOGS_DIR
)


class BBLProfiler:
    """BBL剖析器类"""

    def __init__(self, app_name, output_json=None):
        """
        初始化剖析器

        Args:
            app_name: 应用程序名称
            output_json: 输出JSON路径（可选）
        """
        self.app_name = app_name
        self.output_json = output_json or get_bbl_output_json_path(app_name)

        # 从 configure.py 获取应用配置
        try:
            self.config = get_app_config(app_name)
        except Exception as e:
            raise ValueError(f"无法获取应用 {app_name} 的配置: {e}")

        self.binpath = self.config['binpath']
        self.args = self.config.get('args', [])

        self.is_mpi = app_name in MPI_APP

        # 日志文件
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.log_file = os.path.join(BBL_LOGS_DIR, f"{app_name}_bbl_profile_{timestamp}.log")

    def _build_command(self):
        """构建剖析命令"""
        cmd = []

        # MPI应用需要使用mpirun
        if self.is_mpi:
            cmd.extend(['mpirun', '-np', '1'])

        # Pin 和工具
        cmd.extend([PIN_BINARY, '-t', BBL_PROFILER_TOOL])

        # 输出文件
        cmd.extend(['-o', self.output_json])

        # 程序和参数
        cmd.append('--')
        cmd.append(self.binpath)
        cmd.extend(self.args)

        return cmd

    def run(self, timeout=PROFILE_TIMEOUT):
        """
        执行剖析

        Args:
            timeout: 超时时间（秒）

        Returns:
            dict: 包含执行状态的字典
        """
        cmd = self._build_command()

        print(f"\n{'='*60}")
        print(f"BBL剖析应用: {self.app_name}")
        print(f"{'='*60}")
        print(f"二进制文件: {self.binpath}")
        print(f"参数: {' '.join(str(a) for a in self.args)}")
        print(f"输出JSON: {self.output_json}")
        print(f"MPI应用: {'是' if self.is_mpi else '否'}")
        print(f"命令: {' '.join(cmd)}")
        print(f"日志: {self.log_file}")
        print()

        start_time = time.time()

        try:
            # 执行命令
            with open(self.log_file, 'w') as log_f:
                log_f.write(f"BBL剖析命令: {' '.join(cmd)}\n")
                log_f.write(f"开始时间: {datetime.now()}\n\n")
                log_f.flush()

                # 工作目录：优先使用 workplace，否则使用二进制文件目录
                workplace_dir = os.path.join(
                    os.path.dirname(os.path.dirname(__file__)),
                    'workplace'
                )
                work_dir = workplace_dir if os.path.exists(workplace_dir) else os.path.dirname(self.binpath)

                process = subprocess.Popen(
                    cmd,
                    stdout=log_f,
                    stderr=subprocess.STDOUT,
                    cwd=work_dir
                )

                # 等待完成或超时
                try:
                    returncode = process.wait(timeout=timeout)
                except subprocess.TimeoutExpired:
                    process.kill()
                    elapsed = time.time() - start_time
                    error_msg = f"剖析超时（{elapsed:.1f}秒）"
                    print(f"✗ {error_msg}")
                    return {
                        'success': False,
                        'error': error_msg,
                        'elapsed_time': elapsed
                    }

            elapsed = time.time() - start_time

            # 检查返回码
            if returncode != 0:
                error_msg = f"剖析失败，退出码: {returncode}"
                print(f"✗ {error_msg}")
                return {
                    'success': False,
                    'error': error_msg,
                    'elapsed_time': elapsed
                }

            # 检查输出文件
            if not os.path.exists(self.output_json):
                error_msg = "输出JSON文件未生成"
                print(f"✗ {error_msg}")
                return {
                    'success': False,
                    'error': error_msg,
                    'elapsed_time': elapsed
                }

            # 验证JSON格式
            try:
                with open(self.output_json, 'r') as f:
                    json_data = json.load(f)

                # 检查必要字段
                assert 'tool_info' in json_data, "缺少tool_info"
                assert 'bbls' in json_data, "缺少bbls列表"
                assert isinstance(json_data['bbls'], list), "bbls必须是列表"

                file_size = os.path.getsize(self.output_json) / (1024 * 1024)  # MB
                num_bbls = len(json_data['bbls'])
                num_edges = len(json_data.get('edges', []))

            except json.JSONDecodeError as e:
                error_msg = f"JSON格式错误: {e}"
                print(f"✗ {error_msg}")
                return {
                    'success': False,
                    'error': error_msg,
                    'elapsed_time': elapsed
                }
            except AssertionError as e:
                error_msg = f"JSON结构错误: {e}"
                print(f"✗ {error_msg}")
                return {
                    'success': False,
                    'error': error_msg,
                    'elapsed_time': elapsed
                }

            print(f"✓ 剖析成功！")
            print(f"  耗时: {elapsed:.1f}秒")
            print(f"  输出大小: {file_size:.2f} MB")
            print(f"  BBL数量: {num_bbls}")
            print(f"  边数量: {num_edges}")
            print(f"  日志: {self.log_file}")

            return {
                'success': True,
                'output_file': self.output_json,
                'file_size_mb': file_size,
                'num_bbls': num_bbls,
                'num_edges': num_edges,
                'elapsed_time': elapsed,
                'log_file': self.log_file
            }

        except Exception as e:
            elapsed = time.time() - start_time
            error_msg = f"剖析异常: {str(e)}"
            print(f"✗ {error_msg}")
            return {
                'success': False,
                'error': error_msg,
                'elapsed_time': elapsed
            }


def main():
    parser = argparse.ArgumentParser(
        description='剖析单个应用程序的BBL级特征',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 剖析 backprop 的所有BBL
  python profile_single.py backprop

  # 剖析并指定输出文件
  python profile_single.py bfs --output ./my_bfs_bbl_profile.json

  # 设置超时时间
  python profile_single.py hpl --timeout 7200
        """
    )

    parser.add_argument('app_name', type=str,
                       help='应用程序名称（来自applications.json）')
    parser.add_argument('--output', '-o', type=str, default=None,
                       help='输出JSON文件路径（默认：results/raw_json/<suite>/<app>_bbl_profile.json）')
    parser.add_argument('--timeout', '-t', type=int, default=PROFILE_TIMEOUT,
                       help=f'超时时间（秒），默认：{PROFILE_TIMEOUT}')

    args = parser.parse_args()

    # 创建剖析器并运行
    profiler = BBLProfiler(
        args.app_name,
        output_json=args.output
    )

    result = profiler.run(timeout=args.timeout)

    # 返回退出码
    sys.exit(0 if result['success'] else 1)


if __name__ == '__main__':
    main()
