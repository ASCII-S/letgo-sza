#!/usr/bin/env python3
"""
测试所有应用的 SDC 判定功能

用法:
    python test_all_apps_sdc.py              # 测试所有应用
    python test_all_apps_sdc.py 2mm bicg     # 仅测试指定应用
"""

import os
import sys
import argparse

# 添加路径
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ADAPTIVE_FI_DIR = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, ADAPTIVE_FI_DIR)

from sdc_judge.config_manager import ConfigManager
from sdc_judge.judge.output_extractor import OutputExtractor
from sdc_judge.judge.sdc_comparator import SDCComparator
from sdc_judge.judge.sdc_judge import SDCJudge

# 路径配置
EXAMPLE_DATA_DIR = "/home/tongshiyu/pin/source/tools/letgo/TargetedBenchmarkResult_example"
GOLDEN_DIR = os.path.join(SCRIPT_DIR, "golden_outputs")


class Colors:
    """终端颜色"""
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    CYAN = '\033[0;36m'
    NC = '\033[0m'  # No Color


def print_separator():
    print(f"{Colors.BLUE}{'=' * 70}{Colors.NC}")


def get_golden_path(app_name: str, suite: str, output_type: str, output_name: str) -> str:
    """获取 Golden 输出路径"""
    golden_dir = os.path.join(GOLDEN_DIR, suite, app_name)

    if not os.path.exists(golden_dir):
        return None

    # stdout/stderr 类型使用 stdout.txt
    if output_type in ('stdout', 'stderr'):
        stdout_path = os.path.join(golden_dir, 'stdout.txt')
        if os.path.exists(stdout_path):
            return stdout_path

    # file 类型查找输出文件
    if output_name and output_name != 'none':
        output_path = os.path.join(golden_dir, output_name)
        if os.path.exists(output_path):
            return output_path

    # 查找第一个非 metadata 文件
    for f in os.listdir(golden_dir):
        if f != 'metadata.json' and os.path.isfile(os.path.join(golden_dir, f)):
            return os.path.join(golden_dir, f)

    return None


def count_logs(exp_dir: str) -> int:
    """统计日志数量"""
    log_dir = os.path.join(exp_dir, 'log')
    if not os.path.exists(log_dir):
        return 0

    count = 0
    for f in os.listdir(log_dir):
        if f.startswith('log_') and not f.endswith('.txt'):
            count += 1
    return count


def test_single_app(app_name: str, config_mgr: ConfigManager, extractor: OutputExtractor,
                    judge: SDCJudge, max_tests: int = 5) -> dict:
    """
    测试单个应用的 SDC 判定

    Returns:
        dict: 测试结果
    """
    result = {
        'app_name': app_name,
        'status': 'unknown',
        'output_type': None,
        'compare_method': None,
        'suite': None,
        'golden_path': None,
        'exp_dir': None,
        'log_count': 0,
        'tested': 0,
        'sdc': 0,
        'masked': 0,
        'error': 0,
        'message': ''
    }

    # 获取应用配置
    app_config = config_mgr.get_app(app_name)
    if app_config is None:
        result['status'] = 'skipped'
        result['message'] = '应用配置不存在'
        return result

    result['output_type'] = app_config.output_type
    result['compare_method'] = app_config.compare_method
    result['suite'] = app_config.suite

    # 检查实验数据
    exp_dir = os.path.join(EXAMPLE_DATA_DIR, app_name, 'adaptive')
    result['exp_dir'] = exp_dir

    if not os.path.exists(exp_dir):
        result['status'] = 'skipped'
        result['message'] = '实验数据不存在'
        return result

    # 统计日志数量
    log_count = count_logs(exp_dir)
    result['log_count'] = log_count

    if log_count == 0:
        result['status'] = 'skipped'
        result['message'] = '无日志文件'
        return result

    # 获取 Golden 路径
    golden_path = get_golden_path(
        app_name,
        app_config.suite,
        app_config.output_type,
        getattr(app_config, 'output_name', None)
    )
    result['golden_path'] = golden_path

    if golden_path is None:
        result['status'] = 'skipped'
        result['message'] = 'Golden 输出不存在'
        return result

    # 执行测试
    tested = 0
    sdc = 0
    masked = 0
    error = 0

    for log_index in range(min(max_tests, log_count)):
        try:
            # 提取测试输出
            extracted = extractor.extract(app_name, log_index, exp_dir)

            if extracted.error:
                error += 1
                continue

            test_output = extracted.content

            # 执行判定
            judge_result = judge.judge(
                test_output=test_output,
                golden_output=golden_path,
                app_name=app_name,
                log_index=log_index
            )

            tested += 1
            if judge_result.is_sdc:
                sdc += 1
            else:
                masked += 1

        except Exception as e:
            error += 1

    result['tested'] = tested
    result['sdc'] = sdc
    result['masked'] = masked
    result['error'] = error

    if tested > 0 or error > 0:
        result['status'] = 'success'
        result['message'] = f'SDC={sdc}, Masked={masked}, Error={error}'
    else:
        result['status'] = 'failed'
        result['message'] = '无法完成任何判定'

    return result


def print_result(result: dict):
    """打印单个应用的测试结果"""
    print()
    print_separator()
    print(f"{Colors.CYAN}应用: {Colors.YELLOW}{result['app_name']}{Colors.NC}")
    print_separator()

    if result['status'] == 'skipped':
        print(f"  状态:     {Colors.YELLOW}跳过{Colors.NC} - {result['message']}")
        return

    print(f"  套件:     {Colors.BLUE}{result['suite']}{Colors.NC}")
    print(f"  输出类型: {Colors.BLUE}{result['output_type']}{Colors.NC}")
    print(f"  比较方法: {Colors.BLUE}{result['compare_method']}{Colors.NC}")
    print(f"  实验数据: {result['exp_dir']}")
    print(f"  Golden:   {result['golden_path']}")
    print(f"  日志数量: {result['log_count']}")
    print()
    print(f"  {Colors.CYAN}判定结果:{Colors.NC}")
    print(f"    测试数: {result['tested']}")
    print(f"    SDC:    {Colors.RED}{result['sdc']}{Colors.NC}")
    print(f"    Masked: {Colors.GREEN}{result['masked']}{Colors.NC}")
    print(f"    错误:   {Colors.YELLOW}{result['error']}{Colors.NC}")

    if result['status'] == 'success':
        print(f"  {Colors.GREEN}✓ 测试通过{Colors.NC}")
    else:
        print(f"  {Colors.RED}✗ 测试失败{Colors.NC} - {result['message']}")


def main():
    parser = argparse.ArgumentParser(description='测试所有应用的 SDC 判定功能')
    parser.add_argument('apps', nargs='*', help='要测试的应用名称（默认测试所有）')
    parser.add_argument('--max-tests', '-n', type=int, default=5, help='每个应用最多测试的日志数量')
    args = parser.parse_args()

    # 打印标题
    print()
    print_separator()
    print(f"{Colors.CYAN}SDC 判定功能测试{Colors.NC}")
    print_separator()
    print(f"测试数据目录: {EXAMPLE_DATA_DIR}")
    print(f"Golden 目录:  {GOLDEN_DIR}")
    print(f"每应用测试数: {args.max_tests}")

    # 初始化
    config_mgr = ConfigManager()
    extractor = OutputExtractor()
    judge = SDCJudge()

    # 获取要测试的应用列表
    if args.apps:
        apps = args.apps
    else:
        # 获取所有有实验数据的应用
        apps = []
        if os.path.exists(EXAMPLE_DATA_DIR):
            for name in sorted(os.listdir(EXAMPLE_DATA_DIR)):
                if os.path.isdir(os.path.join(EXAMPLE_DATA_DIR, name)):
                    apps.append(name)

    print(f"待测试应用: {len(apps)} 个")

    # 测试每个应用
    results = []
    for app_name in apps:
        result = test_single_app(app_name, config_mgr, extractor, judge, args.max_tests)
        results.append(result)
        print_result(result)

    # 清理
    extractor.cleanup()

    # 打印汇总
    success = sum(1 for r in results if r['status'] == 'success')
    failed = sum(1 for r in results if r['status'] == 'failed')
    skipped = sum(1 for r in results if r['status'] == 'skipped')

    print()
    print_separator()
    print(f"{Colors.CYAN}测试汇总{Colors.NC}")
    print_separator()
    print(f"  总计:   {len(results)}")
    print(f"  成功:   {Colors.GREEN}{success}{Colors.NC}")
    print(f"  失败:   {Colors.RED}{failed}{Colors.NC}")
    print(f"  跳过:   {Colors.YELLOW}{skipped}{Colors.NC}")
    print_separator()

    # 列出各状态的应用
    if success > 0:
        print(f"\n{Colors.GREEN}成功的应用:{Colors.NC}")
        for r in results:
            if r['status'] == 'success':
                print(f"  - {r['app_name']}: {r['message']}")

    if failed > 0:
        print(f"\n{Colors.RED}失败的应用:{Colors.NC}")
        for r in results:
            if r['status'] == 'failed':
                print(f"  - {r['app_name']}: {r['message']}")

    if skipped > 0:
        print(f"\n{Colors.YELLOW}跳过的应用:{Colors.NC}")
        for r in results:
            if r['status'] == 'skipped':
                print(f"  - {r['app_name']}: {r['message']}")

    print()

    return 0 if failed == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
