#!/bin/bash
#
# 测试所有应用的 SDC 判定功能
#
# 用法: ./test_all_apps_sdc.sh [应用名...]
#
# 示例:
#   ./test_all_apps_sdc.sh           # 测试所有应用
#   ./test_all_apps_sdc.sh 2mm bicg  # 仅测试指定应用
#

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 路径配置
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ADAPTIVE_FI_DIR="$(dirname "$SCRIPT_DIR")"
EXAMPLE_DATA_DIR="/home/tongshiyu/pin/source/tools/letgo/TargetedBenchmarkResult_example"
GOLDEN_DIR="$SCRIPT_DIR/golden_outputs"

# 切换到 adaptive_fi 目录
cd "$ADAPTIVE_FI_DIR"

# 统计变量
TOTAL=0
SUCCESS=0
FAILED=0
SKIPPED=0

# 打印分隔线
print_separator() {
    echo -e "${BLUE}============================================================${NC}"
}

# 打印标题
print_header() {
    echo ""
    print_separator
    echo -e "${CYAN}SDC 判定功能测试${NC}"
    print_separator
    echo -e "测试数据目录: ${EXAMPLE_DATA_DIR}"
    echo -e "Golden 目录:  ${GOLDEN_DIR}"
    echo ""
}

# 获取应用的输出类型和比较方法
get_app_info() {
    local app_name=$1
    python3 -c "
import sys
sys.path.insert(0, '$ADAPTIVE_FI_DIR')
from sdc_judge.config_manager import ConfigManager
config = ConfigManager()
app = config.get_app('$app_name')
if app:
    output_name = getattr(app, 'output_name', '') or ''
    print(f'{app.output_type}|{app.compare_method}|{app.suite}|{output_name}')
else:
    print('unknown|unknown|unknown|')
" 2>/dev/null
}

# 获取 Golden 路径
get_golden_path() {
    local app_name=$1
    local suite=$2
    local output_type=$3
    local output_name=$4
    local golden_dir="$GOLDEN_DIR/$suite/$app_name"

    if [ -d "$golden_dir" ]; then
        # stdout/stderr 类型使用 stdout.txt
        if [ "$output_type" = "stdout" ] || [ "$output_type" = "stderr" ]; then
            if [ -f "$golden_dir/stdout.txt" ]; then
                echo "$golden_dir/stdout.txt"
                return
            fi
        fi

        # file 类型使用 output_name
        if [ "$output_type" = "file" ] && [ -n "$output_name" ]; then
            if [ -f "$golden_dir/$output_name" ]; then
                echo "$golden_dir/$output_name"
                return
            fi
        fi

        # 查找第一个非 metadata/README 文件
        local first_file=$(ls "$golden_dir" 2>/dev/null | grep -v -E '(metadata.json|README.md|stdout.txt)' | head -1)
        if [ -n "$first_file" ]; then
            echo "$golden_dir/$first_file"
            return
        fi

        # 最后尝试 stdout.txt
        if [ -f "$golden_dir/stdout.txt" ]; then
            echo "$golden_dir/stdout.txt"
            return
        fi

        echo "NOT_FOUND"
    else
        echo "NOT_FOUND"
    fi
}

# 测试单个应用
test_app() {
    local app_name=$1
    local exp_dir="$EXAMPLE_DATA_DIR/$app_name/adaptive"

    ((TOTAL++))

    echo ""
    print_separator
    echo -e "${CYAN}测试应用: ${YELLOW}$app_name${NC}"
    print_separator

    # 检查实验数据是否存在
    if [ ! -d "$exp_dir" ]; then
        echo -e "  实验数据: ${RED}不存在${NC} ($exp_dir)"
        echo -e "  ${YELLOW}跳过${NC}"
        ((SKIPPED++))
        return
    fi

    # 获取应用信息
    local app_info=$(get_app_info "$app_name")
    local output_type=$(echo "$app_info" | cut -d'|' -f1)
    local compare_method=$(echo "$app_info" | cut -d'|' -f2)
    local suite=$(echo "$app_info" | cut -d'|' -f3)
    local output_name=$(echo "$app_info" | cut -d'|' -f4)

    if [ "$output_type" == "unknown" ]; then
        echo -e "  应用配置: ${RED}未找到${NC}"
        echo -e "  ${YELLOW}跳过${NC}"
        ((SKIPPED++))
        return
    fi

    # 获取 Golden 路径
    local golden_path=$(get_golden_path "$app_name" "$suite" "$output_type" "$output_name")

    # 打印应用信息
    echo -e "  套件:     ${BLUE}$suite${NC}"
    echo -e "  输出类型: ${BLUE}$output_type${NC}"
    echo -e "  比较方法: ${BLUE}$compare_method${NC}"
    echo -e "  实验数据: $exp_dir"

    if [ "$golden_path" == "NOT_FOUND" ]; then
        echo -e "  Golden:   ${RED}不存在${NC}"
        echo -e "  ${YELLOW}跳过${NC}"
        ((SKIPPED++))
        return
    fi
    echo -e "  Golden:   $golden_path"

    # 统计日志数量
    local log_count
    log_count=$(ls "$exp_dir/log/" 2>/dev/null | grep -c "^log_")
    log_count=${log_count:-0}
    log_count=$(echo "$log_count" | tr -d '[:space:]')
    echo -e "  日志数量: $log_count"

    if [ "$log_count" -eq 0 ] 2>/dev/null || [ -z "$log_count" ]; then
        echo -e "  ${YELLOW}无日志文件，跳过${NC}"
        ((SKIPPED++))
        return
    fi

    echo ""
    echo -e "  ${CYAN}执行 SDC 判定...${NC}"

    # 执行判定（只测试前 5 个日志）
    local max_range=$((log_count > 5 ? 4 : log_count - 1))
    local output
    output=$(python3 -m sdc_judge.judge.batch_judge_sdc "$exp_dir" "$app_name" --range "0-$max_range" --force 2>&1)
    local exit_code=$?

    # 解析结果
    local sdc_count=$(echo "$output" | grep "^SDC:" | awk '{print $2}')
    local masked_count=$(echo "$output" | grep "^Masked:" | awk '{print $2}')
    local error_count=$(echo "$output" | grep "^错误:" | awk '{print $2}')
    local total_count=$(echo "$output" | grep "^总计:" | awk '{print $2}')

    echo ""
    echo -e "  ${CYAN}判定结果:${NC}"

    if [ $exit_code -eq 0 ] && [ -n "$total_count" ]; then
        echo -e "    总计:   $total_count"
        echo -e "    SDC:    ${RED}$sdc_count${NC}"
        echo -e "    Masked: ${GREEN}$masked_count${NC}"
        echo -e "    错误:   ${YELLOW}$error_count${NC}"

        # 检查是否有成功判定的结果
        if [ "$sdc_count" -gt 0 ] || [ "$masked_count" -gt 0 ]; then
            echo -e "  ${GREEN}✓ 测试通过${NC}"
            ((SUCCESS++))
        else
            echo -e "  ${YELLOW}⚠ 全部为错误（可能是崩溃实验）${NC}"
            ((SUCCESS++))  # 仍然算成功，因为判定逻辑正常
        fi
    else
        echo -e "  ${RED}✗ 测试失败${NC}"
        echo -e "  错误信息:"
        echo "$output" | tail -10 | sed 's/^/    /'
        ((FAILED++))
    fi
}

# 主函数
main() {
    print_header

    # 获取要测试的应用列表
    local apps=()
    if [ $# -gt 0 ]; then
        # 使用命令行参数指定的应用
        apps=("$@")
    else
        # 测试所有可用的应用
        for dir in "$EXAMPLE_DATA_DIR"/*/; do
            local app_name=$(basename "$dir")
            apps+=("$app_name")
        done
    fi

    echo -e "待测试应用: ${#apps[@]} 个"
    echo -e "应用列表: ${apps[*]}"

    # 测试每个应用
    for app in "${apps[@]}"; do
        test_app "$app"
    done

    # 打印汇总
    echo ""
    print_separator
    echo -e "${CYAN}测试汇总${NC}"
    print_separator
    echo -e "  总计:   $TOTAL"
    echo -e "  成功:   ${GREEN}$SUCCESS${NC}"
    echo -e "  失败:   ${RED}$FAILED${NC}"
    echo -e "  跳过:   ${YELLOW}$SKIPPED${NC}"
    print_separator

    # 返回状态码
    if [ $FAILED -gt 0 ]; then
        exit 1
    else
        exit 0
    fi
}

# 运行主函数
main "$@"
