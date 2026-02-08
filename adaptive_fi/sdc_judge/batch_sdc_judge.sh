#!/bin/bash
#
# 批量 SDC 判断脚本
#
# 用法:
#   ./batch_sdc_judge.sh                    # 对所有应用进行判断
#   ./batch_sdc_judge.sh backprop hotspot   # 仅对指定应用判断
#   ./batch_sdc_judge.sh --force            # 强制重新判断所有
#   ./batch_sdc_judge.sh --help             # 显示帮助
#

set -e  # 遇到错误立即退出

# 默认配置
RESULT_DIR="/home/tongshiyu/pin/source/tools/letgo/TargetedBenchmarkResult"
LOG_FILE="/tmp/sdc_judge_$(date +%Y%m%d_%H%M%S).log"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ADAPTIVE_FI_DIR="$(dirname "$SCRIPT_DIR")"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 帮助信息
show_help() {
    cat << EOF
批量 SDC 判断脚本

用法:
    $0 [选项] [应用名称...]

选项:
    --help, -h              显示此帮助信息
    --force, -f             强制重新判断已有结果
    --range START-END       指定日志范围，如 --range 0-99
    --verbose, -v           详细输出模式
    --dir PATH              指定实验结果目录（默认: $RESULT_DIR）
    --background, -b        在后台运行
    --log PATH              指定日志文件路径（默认: $LOG_FILE）

示例:
    $0                                  # 对所有应用进行判断
    $0 backprop hotspot                 # 仅对 backprop 和 hotspot 判断
    $0 --force                          # 强制重新判断所有应用
    $0 --range 0-99                     # 仅判断 log_0 到 log_99
    $0 --background backprop            # 后台判断 backprop
    $0 --verbose --force                # 详细输出 + 强制重判

EOF
}

# 解析参数
APPS=()
FORCE_FLAG=""
RANGE_FLAG=""
VERBOSE_FLAG=""
BACKGROUND=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --help|-h)
            show_help
            exit 0
            ;;
        --force|-f)
            FORCE_FLAG="--force"
            shift
            ;;
        --range)
            RANGE_FLAG="--range $2"
            shift 2
            ;;
        --verbose|-v)
            VERBOSE_FLAG="--verbose"
            shift
            ;;
        --dir)
            RESULT_DIR="$2"
            shift 2
            ;;
        --background|-b)
            BACKGROUND=true
            shift
            ;;
        --log)
            LOG_FILE="$2"
            shift 2
            ;;
        -*)
            echo -e "${RED}错误: 未知选项 $1${NC}"
            echo "使用 --help 查看帮助"
            exit 1
            ;;
        *)
            APPS+=("$1")
            shift
            ;;
    esac
done

# 检查实验结果目录
if [ ! -d "$RESULT_DIR" ]; then
    echo -e "${RED}错误: 实验结果目录不存在: $RESULT_DIR${NC}"
    exit 1
fi

# 构建命令
CMD="python3 -u -m sdc_judge.batch_judge_all_apps \"$RESULT_DIR\""

if [ ${#APPS[@]} -gt 0 ]; then
    CMD="$CMD --apps ${APPS[*]}"
fi

if [ -n "$FORCE_FLAG" ]; then
    CMD="$CMD $FORCE_FLAG"
fi

if [ -n "$RANGE_FLAG" ]; then
    CMD="$CMD $RANGE_FLAG"
fi

if [ -n "$VERBOSE_FLAG" ]; then
    CMD="$CMD $VERBOSE_FLAG"
fi

# 切换到 adaptive_fi 目录
cd "$ADAPTIVE_FI_DIR"

# 显示执行信息
echo -e "${GREEN}=====================================================${NC}"
echo -e "${GREEN}批量 SDC 判断${NC}"
echo -e "${GREEN}=====================================================${NC}"
echo "实验目录: $RESULT_DIR"
if [ ${#APPS[@]} -gt 0 ]; then
    echo "指定应用: ${APPS[*]}"
else
    echo "处理范围: 所有应用"
fi
[ -n "$FORCE_FLAG" ] && echo "模式: 强制重新判断"
[ -n "$RANGE_FLAG" ] && echo "日志范围: $RANGE_FLAG"
[ -n "$VERBOSE_FLAG" ] && echo "详细输出: 启用"
echo "日志文件: $LOG_FILE"
echo -e "${GREEN}=====================================================${NC}"
echo ""

# 执行命令
if [ "$BACKGROUND" = true ]; then
    # 后台执行
    echo -e "${YELLOW}在后台运行...${NC}"
    nohup bash -c "$CMD" > "$LOG_FILE" 2>&1 &
    PID=$!
    echo -e "${GREEN}后台任务已启动 (PID: $PID)${NC}"
    echo ""
    echo "查看进度:"
    echo "  tail -f $LOG_FILE"
    echo ""
    echo "查看最后 50 行:"
    echo "  tail -50 $LOG_FILE"
    echo ""
    echo "停止任务:"
    echo "  kill $PID"
    echo ""

    # 等待一下并显示初始输出
    sleep 3
    echo -e "${YELLOW}初始输出:${NC}"
    tail -20 "$LOG_FILE"
else
    # 前台执行（带日志记录）
    eval "$CMD" 2>&1 | tee "$LOG_FILE"
    EXIT_CODE=${PIPESTATUS[0]}

    echo ""
    if [ $EXIT_CODE -eq 0 ]; then
        echo -e "${GREEN}✓ 批量判断完成！${NC}"
    else
        echo -e "${RED}✗ 批量判断失败（退出码: $EXIT_CODE）${NC}"
    fi
    echo "完整日志: $LOG_FILE"

    exit $EXIT_CODE
fi
