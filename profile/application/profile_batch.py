#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量应用程序剖析脚本（使用 app_profiler 工具）

功能：
1. 批量剖析多个应用程序
2. 支持按套件、按列表、按正则表达式筛选
3. 并行处理（可选）
4. 失败重试机制
5. 进度跟踪和报告

剖析指标：
- D类：指令类型分布（整数、浮点、内存、控制流、逻辑、SIMD等）
- A类：数值敏感性（浮点指令、敏感运算、精度分布）
- B类：误差吸收能力（比较、饱和、MIN/MAX、舍入等）
- C类：库调用统计（math、BLAS、LAPACK、MPI、OpenMP等）
"""

import os
import sys
import argparse
import json
import time
from datetime import datetime
from pathlib import Path

# 添加配置路径
profile_home = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, profile_home)
from config import (
    APP_SUITES, ALL_APPS, DEFAULT_PROFILE_APPS,
    PROFILE_TIMEOUT, MAX_PARALLEL_JOBS, MAX_RETRIES,
    SUMMARY_DIR, LOGS_DIR, get_app_suite
)

# 尝试导入进度条（可选依赖）
try:
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False
    print("提示: 安装 tqdm 可以显示进度条 (pip install tqdm)")


def profile_single_app(app_name, timeout=PROFILE_TIMEOUT):
    """
    剖析单个应用（独立函数，用于并行处理）

    Args:
        app_name: 应用名称
        timeout: 超时时间

    Returns:
        dict: 剖析结果
    """
    from profile_single import ApplicationProfiler

    try:
        profiler = ApplicationProfiler(app_name)
        result = profiler.run(timeout=timeout)
        result['app_name'] = app_name
        return result
    except Exception as e:
        return {
            'success': False,
            'app_name': app_name,
            'error': str(e),
            'elapsed_time': 0
        }


class BatchProfiler:
    """批量剖析器类"""

    def __init__(self, apps, parallel=1, timeout=PROFILE_TIMEOUT, max_retries=MAX_RETRIES):
        """
        初始化批量剖析器

        Args:
            apps: 要剖析的应用列表
            parallel: 并行任务数
            timeout: 每个任务的超时时间
            max_retries: 最大重试次数
        """
        self.apps = apps
        self.parallel = min(parallel, MAX_PARALLEL_JOBS)
        self.timeout = timeout
        self.max_retries = max_retries

        # 结果统计
        self.results = {
            'success': [],
            'failed': [],
            'timeout': [],
            'total_time': 0
        }

        # 日志文件
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.batch_log = os.path.join(LOGS_DIR, f"batch_profile_{timestamp}.log")
        self.summary_json = os.path.join(SUMMARY_DIR, f"batch_summary_{timestamp}.json")

    def _profile_single_with_retry(self, app_name):
        """
        剖析单个应用（带重试）

        Args:
            app_name: 应用名称

        Returns:
            dict: 剖析结果
        """
        from profile_single import ApplicationProfiler

        for attempt in range(self.max_retries + 1):
            try:
                profiler = ApplicationProfiler(app_name)
                result = profiler.run(timeout=self.timeout)
                result['app_name'] = app_name
                result['attempts'] = attempt + 1

                if result['success']:
                    return result

                # 失败了，如果还有重试次数则继续
                if attempt < self.max_retries:
                    print(f"  重试 {attempt + 1}/{self.max_retries}...")
                    time.sleep(2)  # 等待2秒再重试

            except Exception as e:
                result = {
                    'success': False,
                    'app_name': app_name,
                    'error': str(e),
                    'attempts': attempt + 1
                }

                if attempt < self.max_retries:
                    print(f"  异常，重试 {attempt + 1}/{self.max_retries}...")
                    time.sleep(2)

        return result

    def run(self):
        """执行批量剖析"""
        print(f"\n{'='*70}")
        print(f"批量应用程序剖析")
        print(f"{'='*70}")
        print(f"应用数量: {len(self.apps)}")
        print(f"并行任务数: {self.parallel}")
        print(f"超时时间: {self.timeout}秒")
        print(f"最大重试: {self.max_retries}次")
        print(f"批量日志: {self.batch_log}")
        print(f"{'='*70}\n")

        start_time = time.time()

        with open(self.batch_log, 'w') as log_f:
            log_f.write(f"批量剖析开始: {datetime.now()}\n")
            log_f.write(f"应用列表: {', '.join(self.apps)}\n\n")

        if self.parallel > 1:
            # 并行处理
            print(f"使用 {self.parallel} 个并行任务\n")
            self._run_parallel()
        else:
            # 串行处理
            print("串行处理\n")
            self._run_sequential()

        total_time = time.time() - start_time
        self.results['total_time'] = total_time

        # 打印汇总
        self._print_summary()

        # 保存汇总JSON
        self._save_summary()

        return self.results

    def _run_sequential(self):
        """串行执行"""
        if HAS_TQDM:
            app_iter = tqdm(self.apps, desc="剖析进度")
        else:
            app_iter = self.apps

        for i, app_name in enumerate(app_iter):
            if not HAS_TQDM:
                print(f"[{i+1}/{len(self.apps)}] 剖析 {app_name}...")
            result = self._profile_single_with_retry(app_name)
            self._record_result(result)

    def _run_parallel(self):
        """并行执行"""
        from concurrent.futures import ProcessPoolExecutor, as_completed

        with ProcessPoolExecutor(max_workers=self.parallel) as executor:
            # 提交所有任务
            future_to_app = {
                executor.submit(profile_single_app, app, self.timeout): app
                for app in self.apps
            }

            # 收集结果
            if HAS_TQDM:
                futures_iter = tqdm(as_completed(future_to_app),
                                   total=len(self.apps),
                                   desc="剖析进度")
            else:
                futures_iter = as_completed(future_to_app)

            completed = 0
            for future in futures_iter:
                completed += 1
                if not HAS_TQDM:
                    app = future_to_app[future]
                    print(f"[{completed}/{len(self.apps)}] 完成 {app}")
                result = future.result()
                self._record_result(result)

    def _record_result(self, result):
        """记录单个结果"""
        app_name = result['app_name']

        if result['success']:
            self.results['success'].append(result)
        elif 'timeout' in result.get('error', '').lower() or '超时' in result.get('error', ''):
            self.results['timeout'].append(result)
        else:
            self.results['failed'].append(result)

        # 写入批量日志
        with open(self.batch_log, 'a') as log_f:
            status = "成功" if result['success'] else "失败"
            log_f.write(f"[{datetime.now()}] {app_name}: {status}\n")
            if not result['success']:
                log_f.write(f"  错误: {result.get('error', 'Unknown')}\n")

    def _print_summary(self):
        """打印汇总信息"""
        print(f"\n{'='*70}")
        print(f"批量剖析完成")
        print(f"{'='*70}")
        print(f"总耗时: {self.results['total_time']:.1f}秒")
        print(f"成功: {len(self.results['success'])}/{len(self.apps)}")
        print(f"失败: {len(self.results['failed'])}/{len(self.apps)}")
        print(f"超时: {len(self.results['timeout'])}/{len(self.apps)}")

        if self.results['failed']:
            print(f"\n失败的应用:")
            for r in self.results['failed']:
                print(f"  - {r['app_name']}: {r.get('error', 'Unknown')}")

        if self.results['timeout']:
            print(f"\n超时的应用:")
            for r in self.results['timeout']:
                print(f"  - {r['app_name']}")

        print(f"\n详细日志: {self.batch_log}")
        print(f"汇总JSON: {self.summary_json}")
        print(f"{'='*70}\n")

    def _save_summary(self):
        """保存汇总JSON"""
        summary = {
            'timestamp': datetime.now().isoformat(),
            'total_apps': len(self.apps),
            'success_count': len(self.results['success']),
            'failed_count': len(self.results['failed']),
            'timeout_count': len(self.results['timeout']),
            'total_time_seconds': self.results['total_time'],
            'parallel_jobs': self.parallel,
            'timeout_per_app': self.timeout,
            'results': {
                'success': [
                    {
                        'app': r['app_name'],
                        'output': r.get('output_file'),
                        'elapsed': r.get('elapsed_time'),
                        'size_mb': r.get('file_size_mb')
                    } for r in self.results['success']
                ],
                'failed': [
                    {
                        'app': r['app_name'],
                        'error': r.get('error'),
                        'attempts': r.get('attempts')
                    } for r in self.results['failed']
                ],
                'timeout': [
                    {
                        'app': r['app_name'],
                        'elapsed': r.get('elapsed_time')
                    } for r in self.results['timeout']
                ]
            }
        }

        with open(self.summary_json, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)


def parse_app_list(args):
    """解析应用列表"""
    apps = []

    # 如果指定了具体的应用名
    if args.apps:
        # 支持逗号分隔的应用名
        apps = []
        for app in args.apps:
            if ',' in app:
                apps.extend([a.strip() for a in app.split(',')])
            else:
                apps.append(app)

    # 如果指定了套件
    elif args.suite:
        if args.suite not in APP_SUITES:
            print(f"错误: 未知套件 '{args.suite}'")
            print(f"可用套件: {', '.join(APP_SUITES.keys())}")
            sys.exit(1)
        apps = APP_SUITES[args.suite]

    # 如果指定了all
    elif args.all:
        apps = ALL_APPS

    # 默认使用配置中的列表
    else:
        apps = DEFAULT_PROFILE_APPS

    # 排除指定的应用（支持逗号分隔）
    if args.exclude:
        exclude_list = []
        for item in args.exclude:
            if ',' in item:
                exclude_list.extend([a.strip() for a in item.split(',')])
            else:
                exclude_list.append(item)
        apps = [app for app in apps if app not in exclude_list]

    return apps


def main():
    parser = argparse.ArgumentParser(
        description='批量剖析多个应用程序',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 剖析所有应用
  python profile_batch.py --all

  # 剖析Rodinia套件
  python profile_batch.py --suite rodinia

  # 剖析指定应用（空格分隔）
  python profile_batch.py --apps backprop bfs hotspot

  # 剖析指定应用（逗号分隔）
  python profile_batch.py --apps backprop,bfs,hotspot

  # 剖析所有但排除某些应用（空格分隔）
  python profile_batch.py --all --exclude hpl miniAMR

  # 剖析所有但排除某些应用（逗号分隔）
  python profile_batch.py --all --exclude hpl,miniAMR

  # 使用4个并行任务
  python profile_batch.py --suite mantevo --parallel 4

  # 设置超时和重试
  python profile_batch.py --all --timeout 7200 --retries 3
        """
    )

    # 应用选择参数
    app_group = parser.add_mutually_exclusive_group()
    app_group.add_argument('--all', action='store_true',
                          help='剖析所有应用')
    app_group.add_argument('--suite', type=str, choices=list(APP_SUITES.keys()),
                          help='剖析指定套件的所有应用')
    app_group.add_argument('--apps', nargs='+', type=str,
                          help='指定要剖析的应用列表（空格或逗号分隔）')

    parser.add_argument('--exclude', nargs='+', type=str, default=[],
                       help='排除指定的应用（空格或逗号分隔）')

    # 执行参数
    parser.add_argument('--parallel', '-p', type=int, default=1,
                       help=f'并行任务数（1-{MAX_PARALLEL_JOBS}），默认：1（串行）')
    parser.add_argument('--timeout', '-t', type=int, default=PROFILE_TIMEOUT,
                       help=f'每个应用的超时时间（秒），默认：{PROFILE_TIMEOUT}')
    parser.add_argument('--retries', '-r', type=int, default=MAX_RETRIES,
                       help=f'失败后的最大重试次数，默认：{MAX_RETRIES}')

    # 其他参数
    parser.add_argument('--dry-run', action='store_true',
                       help='只显示将要剖析的应用列表，不实际执行')

    args = parser.parse_args()

    # 解析应用列表
    apps = parse_app_list(args)

    if not apps:
        print("错误: 没有指定要剖析的应用")
        print("使用 --help 查看帮助")
        sys.exit(1)

    # Dry run模式
    if args.dry_run:
        print(f"将要剖析的应用 ({len(apps)}):")
        for i, app in enumerate(apps, 1):
            suite = get_app_suite(app)
            print(f"  {i:2d}. {app:20s} [{suite}]")
        print(f"\n总计: {len(apps)} 个应用")
        sys.exit(0)

    # 创建批量剖析器并运行
    batch_profiler = BatchProfiler(
        apps=apps,
        parallel=args.parallel,
        timeout=args.timeout,
        max_retries=args.retries
    )

    results = batch_profiler.run()

    # 返回退出码
    success_count = len(results['success'])
    total_count = len(apps)
    sys.exit(0 if success_count == total_count else 1)


if __name__ == '__main__':
    main()
