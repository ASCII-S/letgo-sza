#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量应用程序函数剖析脚本

功能：
1. 批量剖析多个应用程序的函数级特征
2. 支持按套件、按列表筛选
3. 并行处理（可选）
4. 失败重试机制
5. 进度跟踪和报告
"""

import os
import sys
import argparse
import json
import time
from datetime import datetime
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed

# 添加配置路径
profile_home = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, profile_home)
from config import (
    APP_SUITES, ALL_APPS,
    PROFILE_TIMEOUT, MAX_PARALLEL_JOBS, MAX_RETRIES,
    FUNCTION_SUMMARY_DIR, FUNCTION_LOGS_DIR, get_app_suite,
    FUNCTION_MIN_CALLS
)

# 尝试导入进度条（可选依赖）
try:
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False
    print("提示: 安装 tqdm 可以显示进度条 (pip install tqdm)")


def profile_single_app_with_retry(app_name, timeout, min_calls, max_retries,
                                   enable_dep=False, enable_lifetime=False):
    """
    剖析单个应用（带重试，用于并行处理）

    Args:
        app_name: 应用名称
        timeout: 超时时间
        min_calls: 最小调用次数过滤
        max_retries: 最大重试次数
        enable_dep: 启用F类数据依赖分析
        enable_lifetime: 启用G类生命周期分析

    Returns:
        dict: 剖析结果
    """
    from profile_single import FunctionProfiler

    for attempt in range(max_retries + 1):
        try:
            profiler = FunctionProfiler(app_name, min_calls=min_calls,
                                        enable_dep=enable_dep,
                                        enable_lifetime=enable_lifetime)
            result = profiler.run(timeout=timeout)
            result['app_name'] = app_name
            result['attempts'] = attempt + 1

            if result['success']:
                return result

            # 失败了，如果还有重试次数则继续
            if attempt < max_retries:
                print(f"  [{app_name}] 重试 {attempt + 1}/{max_retries}...")
                time.sleep(2)  # 等待2秒再重试

        except Exception as e:
            result = {
                'success': False,
                'app_name': app_name,
                'error': str(e),
                'attempts': attempt + 1,
                'elapsed_time': 0
            }

            if attempt < max_retries:
                print(f"  [{app_name}] 异常，重试 {attempt + 1}/{max_retries}...")
                time.sleep(2)

    return result


class BatchFunctionProfiler:
    """批量函数剖析器类"""

    def __init__(self, apps, parallel=1, timeout=PROFILE_TIMEOUT,
                 max_retries=MAX_RETRIES, min_calls=None,
                 enable_dep=False, enable_lifetime=False):
        """
        初始化批量剖析器

        Args:
            apps: 要剖析的应用列表
            parallel: 并行任务数
            timeout: 每个任务的超时时间
            max_retries: 最大重试次数
            min_calls: 最小调用次数过滤
            enable_dep: 启用F类数据依赖分析
            enable_lifetime: 启用G类生命周期分析
        """
        self.apps = apps
        self.parallel = min(parallel, MAX_PARALLEL_JOBS)
        self.timeout = timeout
        self.max_retries = max_retries
        self.min_calls = min_calls if min_calls is not None else FUNCTION_MIN_CALLS
        self.enable_dep = enable_dep
        self.enable_lifetime = enable_lifetime

        # 结果统计
        self.results = {
            'success': [],
            'failed': [],
            'timeout': [],
            'total_time': 0
        }

        # 日志文件
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.batch_log = os.path.join(FUNCTION_LOGS_DIR, f"batch_function_profile_{timestamp}.log")
        self.summary_json = os.path.join(FUNCTION_SUMMARY_DIR, f"batch_summary_{timestamp}.json")

    def _run_sequential(self):
        """串行执行（用于调试或并行度=1）"""
        print("使用串行模式...")

        iterator = tqdm(self.apps, desc="剖析进度") if HAS_TQDM else self.apps

        for app_name in iterator:
            result = profile_single_app_with_retry(
                app_name, self.timeout, self.min_calls, self.max_retries,
                self.enable_dep, self.enable_lifetime
            )
            self._record_result(result)

    def _run_parallel(self):
        """并行执行"""
        print(f"使用并行模式（{self.parallel}个任务）...")

        with ProcessPoolExecutor(max_workers=self.parallel) as executor:
            # 提交所有任务
            future_to_app = {
                executor.submit(
                    profile_single_app_with_retry,
                    app_name,
                    self.timeout,
                    self.min_calls,
                    self.max_retries,
                    self.enable_dep,
                    self.enable_lifetime
                ): app_name
                for app_name in self.apps
            }

            # 处理完成的任务
            if HAS_TQDM:
                for future in tqdm(as_completed(future_to_app), total=len(self.apps), desc="剖析进度"):
                    result = future.result()
                    self._record_result(result)
            else:
                completed = 0
                for future in as_completed(future_to_app):
                    result = future.result()
                    self._record_result(result)
                    completed += 1
                    print(f"进度: {completed}/{len(self.apps)}")

    def _record_result(self, result):
        """记录单个结果"""
        if result['success']:
            self.results['success'].append(result)
        elif 'timeout' in result.get('error', ''):
            self.results['timeout'].append(result)
        else:
            self.results['failed'].append(result)

    def run(self):
        """执行批量剖析"""
        print(f"\n{'='*70}")
        print(f"批量应用程序函数剖析")
        print(f"{'='*70}")
        print(f"应用数量: {len(self.apps)}")
        print(f"并行任务数: {self.parallel}")
        print(f"超时时间: {self.timeout}秒")
        print(f"最大重试: {self.max_retries}次")
        print(f"最小调用次数: {self.min_calls}")
        print(f"数据依赖分析(F类): {'是' if self.enable_dep else '否'}")
        print(f"生命周期分析(G类): {'是' if self.enable_lifetime else '否'}")
        print(f"批量日志: {self.batch_log}")
        print(f"{'='*70}\n")

        start_time = time.time()

        # 选择执行模式
        if self.parallel == 1:
            self._run_sequential()
        else:
            self._run_parallel()

        total_time = time.time() - start_time
        self.results['total_time'] = total_time

        # 生成汇总报告
        self._generate_summary()

        # 打印统计信息
        self._print_statistics()

        return self.results

    def _generate_summary(self):
        """生成汇总报告"""
        summary = {
            'timestamp': datetime.now().isoformat(),
            'configuration': {
                'apps_count': len(self.apps),
                'parallel_jobs': self.parallel,
                'timeout': self.timeout,
                'max_retries': self.max_retries,
                'min_calls': self.min_calls
            },
            'results': {
                'total': len(self.apps),
                'success': len(self.results['success']),
                'failed': len(self.results['failed']),
                'timeout': len(self.results['timeout'])
            },
            'total_time': self.results['total_time'],
            'details': {
                'success': self.results['success'],
                'failed': self.results['failed'],
                'timeout': self.results['timeout']
            }
        }

        # 保存JSON
        with open(self.summary_json, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)

        print(f"\n汇总报告已保存: {self.summary_json}")

    def _print_statistics(self):
        """打印统计信息"""
        print(f"\n{'='*70}")
        print("批量剖析统计")
        print(f"{'='*70}")
        print(f"总计: {len(self.apps)} 个应用")
        print(f"  成功: {len(self.results['success'])} 个")
        print(f"  失败: {len(self.results['failed'])} 个")
        print(f"  超时: {len(self.results['timeout'])} 个")
        print(f"总耗时: {self.results['total_time']:.1f} 秒")
        print(f"{'='*70}\n")

        # 打印失败列表
        if self.results['failed']:
            print("失败应用:")
            for r in self.results['failed']:
                print(f"  - {r['app_name']}: {r.get('error', '未知错误')}")
            print()

        # 打印超时列表
        if self.results['timeout']:
            print("超时应用:")
            for r in self.results['timeout']:
                print(f"  - {r['app_name']}")
            print()


def main():
    parser = argparse.ArgumentParser(
        description='批量剖析应用程序的函数级特征',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 剖析所有应用
  python profile_batch.py --all

  # 剖析rodinia套件
  python profile_batch.py --suite rodinia

  # 剖析指定应用
  python profile_batch.py --apps backprop,bfs,hotspot

  # 排除某些应用
  python profile_batch.py --all --exclude amg,hpl

  # 并行剖析（2个任务）
  python profile_batch.py --all --parallel 2

  # 只剖析调用次数>=5的函数
  python profile_batch.py --suite rodinia --min-calls 5

  # 启用可选分析（数据依赖+生命周期）
  python profile_batch.py --suite rodinia --enable-dep --enable-lifetime
        """
    )

    # 应用选择参数
    app_group = parser.add_mutually_exclusive_group(required=True)
    app_group.add_argument('--all', action='store_true',
                          help='剖析所有应用')
    app_group.add_argument('--suite', type=str, choices=list(APP_SUITES.keys()),
                          help='剖析指定套件的应用')
    app_group.add_argument('--apps', type=str,
                          help='逗号分隔的应用列表')

    # 其他参数
    parser.add_argument('--exclude', type=str, default='',
                       help='逗号分隔的要排除的应用列表')
    parser.add_argument('--parallel', '-p', type=int, default=1,
                       help=f'并行任务数（1-{MAX_PARALLEL_JOBS}），默认：1')
    parser.add_argument('--timeout', '-t', type=int, default=PROFILE_TIMEOUT,
                       help=f'每个应用的超时时间（秒），默认：{PROFILE_TIMEOUT}')
    parser.add_argument('--max-retries', '-r', type=int, default=MAX_RETRIES,
                       help=f'最大重试次数，默认：{MAX_RETRIES}')
    parser.add_argument('--min-calls', '-m', type=int, default=None,
                       help=f'最小调用次数过滤，默认：{FUNCTION_MIN_CALLS}')
    parser.add_argument('--enable-dep', action='store_true',
                       help='启用F类数据依赖分析（有性能开销）')
    parser.add_argument('--enable-lifetime', action='store_true',
                       help='启用G类生命周期分析（有性能开销）')

    args = parser.parse_args()

    # 确定要剖析的应用列表
    apps = []
    if args.all:
        apps = ALL_APPS.copy()
    elif args.suite:
        apps = APP_SUITES[args.suite].copy()
    elif args.apps:
        apps = [a.strip() for a in args.apps.split(',')]

    # 排除指定应用
    if args.exclude:
        exclude_list = [a.strip() for a in args.exclude.split(',')]
        apps = [a for a in apps if a not in exclude_list]

    if not apps:
        print("错误: 没有要剖析的应用")
        sys.exit(1)

    # 创建批量剖析器并运行
    profiler = BatchFunctionProfiler(
        apps=apps,
        parallel=args.parallel,
        timeout=args.timeout,
        max_retries=args.max_retries,
        min_calls=args.min_calls,
        enable_dep=args.enable_dep,
        enable_lifetime=args.enable_lifetime
    )

    results = profiler.run()

    # 返回退出码
    success_count = len(results['success'])
    total_count = len(apps)
    sys.exit(0 if success_count == total_count else 1)


if __name__ == '__main__':
    main()
