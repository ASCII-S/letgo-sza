#!/bin/bash

# 批量实验脚本
# 功能：支持并行执行，目录复用（实验完成后目录可被下一个应用使用）
# 通过环境变量 PROGNAME_OVERRIDE 传递应用名，避免并行时 configure.py 冲突

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 默认并行数
PARALLEL_NUM=5

# 要批量测试的应用列表（可根据需要修改）
APP_LIST=(
    "HPCCG"
    "miniFE"
    "miniMD"
    "backprop"
    "bfs"
    "hotspot"
    "kmeans"
    "nn"
    "particlefilter"
    "hpl"
)

# 所有可用应用的完整列表
ALL_APPS=(
    # Rodinia
    "amg" "backprop" "bfs" "hotspot"
    "hpl" "kmeans"  "needle"
    "srad" "nn" "particlefilter" "lu"
    # Mantevo
    "HPCCG" "miniFE" 
    # NPB-SER
    "bt" "cg" "ep" "ft" "is" "lu" "mg" "sp" "ua"
    # PolyBench
    "2mm" "bicg" "correlation" "fdtd-2d" "gesummv" "syr2k"
)

# 日志目录
LOG_DIR="${SCRIPT_DIR}/logs"
# 用于并行任务状态跟踪的目录
STATUS_DIR="${SCRIPT_DIR}/.batch_status"
# 目录锁文件目录
LOCK_DIR="${SCRIPT_DIR}/.locks"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

log() {
    local msg="[$(date '+%Y-%m-%d %H:%M:%S')] $1"
    echo -e "$msg"
    # 使用文件锁避免并发写入冲突
    (
        flock -x 200
        echo -e "$msg" >> "${LOG_DIR}/batch_experiment.log"
    ) 200>"${LOG_DIR}/.log.lock"
}

# 获取可用的 letgo_Target 目录列表（按数字排序）
get_available_targets() {
    local targets=()
    for dir in "${SCRIPT_DIR}"/letgo_Target*/; do
        if [ -d "$dir" ] && [ -f "${dir}adaptive_inj.sh" ]; then
            targets+=("$(basename "$dir")")
        fi
    done
    # 按数字排序
    printf '%s\n' "${targets[@]}" | sort -V
}

# 获取一个空闲目录（带锁机制）
acquire_target_dir() {
    local targets=($(get_available_targets))

    for target in "${targets[@]}"; do
        local lock_file="${LOCK_DIR}/${target}.lock"

        # 尝试获取锁（非阻塞）
        if ( set -o noclobber; echo $$ > "$lock_file" ) 2>/dev/null; then
            echo "$target"
            return 0
        fi
    done

    # 没有空闲目录
    return 1
}

# 释放目录锁
release_target_dir() {
    local target="$1"
    local lock_file="${LOCK_DIR}/${target}.lock"
    rm -f "$lock_file"
}

# 单个应用的实验任务
run_single_experiment() {
    local app="$1"
    local target_dir="$2"
    local app_log="${LOG_DIR}/${app}.log"

    {
        echo "========== 开始实验: ${app} =========="
        echo "开始时间: $(date '+%Y-%m-%d %H:%M:%S')"
        echo "工作目录: ${SCRIPT_DIR}/${target_dir}"

        cd "${SCRIPT_DIR}/${target_dir}"

        # 通过环境变量传递 progname
        export PROGNAME_OVERRIDE="$app"

        echo "环境变量: PROGNAME_OVERRIDE=${PROGNAME_OVERRIDE}"
        echo ""

        # 运行实验
        bash adaptive_inj.sh
        local exit_code=$?

        echo ""
        echo "结束时间: $(date '+%Y-%m-%d %H:%M:%S')"

        if [ $exit_code -eq 0 ]; then
            echo "状态: 成功"
            echo "success" > "${STATUS_DIR}/${app}.status"
        else
            echo "状态: 失败 (exit code: ${exit_code})"
            echo "failed:${exit_code}" > "${STATUS_DIR}/${app}.status"
        fi
        echo "========== 实验结束: ${app} =========="
    } > "$app_log" 2>&1

    return $exit_code
}

# 工作进程：获取目录 -> 运行实验 -> 释放目录
worker_process() {
    local app="$1"

    # 等待获取空闲目录
    local target_dir=""
    local wait_count=0
    while true; do
        target_dir=$(acquire_target_dir)
        if [ -n "$target_dir" ]; then
            break
        fi
        sleep 1
        ((wait_count++))
        if [ $((wait_count % 30)) -eq 0 ]; then
            log "${YELLOW}[${app}] 等待空闲目录... (${wait_count}s)${NC}"
        fi
    done

    log "${BLUE}[启动] ${app} -> ${target_dir}${NC}"

    # 运行实验
    run_single_experiment "$app" "$target_dir"
    local exit_code=$?

    # 释放目录
    release_target_dir "$target_dir"

    if [ $exit_code -eq 0 ]; then
        log "${GREEN}[完成] ${app} (${target_dir}) ✓${NC}"
    else
        log "${RED}[失败] ${app} (${target_dir}) ✗${NC}"
    fi

    return $exit_code
}

# 显示使用帮助
show_help() {
    echo "用法: $0 [选项] [应用列表...]"
    echo ""
    echo "选项:"
    echo "  -h, --help          显示帮助信息"
    echo "  -l, --list          列出所有可用的应用名称"
    echo "  -a, --all           对所有默认应用运行实验 (APP_LIST, 10个)"
    echo "  -A, --ALL           对所有可用应用运行实验 (ALL_APPS, 37个)"
    echo "  -p, --parallel N    设置并行数 (默认: ${PARALLEL_NUM})"
    echo "  -s, --sequential    顺序执行（不并行）"
    echo "  -t, --targets       列出可用的 letgo_Target 目录"
    echo "  -c, --clean         清理日志和状态文件"
    echo "  -k, --kill          停止所有正在运行的实验任务"
    echo ""
    echo "示例:"
    echo "  $0 HPCCG miniFE           对 HPCCG 和 miniFE 运行实验"
    echo "  $0 -p 3 -a                使用 3 个并行任务运行默认应用"
    echo "  $0 -p 5 -A                使用 5 个并行任务运行所有应用"
    echo "  $0 -s HPCCG miniFE        顺序运行 HPCCG 和 miniFE"
    echo "  $0 -k                     停止所有正在运行的实验"
    echo ""
    echo "特性:"
    echo "  - 目录复用：实验完成后目录立即可被下一个应用使用"
    echo "  - 只需要 N 个目录即可并行运行 N 个任务（不需要每个应用一个目录）"
    echo "  - 通过环境变量 PROGNAME_OVERRIDE 传递应用名"
    echo "  - 日志保存在 ${LOG_DIR}/ 目录下"
}

# 列出所有可用应用
list_apps() {
    echo "可用的应用列表:"
    echo ""
    echo "  Rodinia (18个):"
    echo "    amg, b+tree, backprop, bfs, heartwall, hotspot, hotspot3D,"
    echo "    hpl, kmeans, knn, lavaMD, leukocyte, myocyte, needle,"
    echo "    srad, nn, particlefilter, streamcluster"
    echo ""
    echo "  Mantevo (4个):"
    echo "    HPCCG, miniFE, miniMD, miniAMR"
    echo ""
    echo "  NPB-SER (9个):"
    echo "    bt, cg, ep, ft, is, lu, mg, sp, ua"
    echo ""
    echo "  PolyBench (6个):"
    echo "    2mm, bicg, correlation, fdtd-2d, gesummv, syr2k"
    echo ""
    echo "  共计: 37 个应用"
}

# 列出可用目录
list_targets() {
    echo "可用的 letgo_Target 目录:"
    local targets=($(get_available_targets))
    local count=0
    for t in "${targets[@]}"; do
        echo "  [$((++count))] $t"
    done
    echo ""
    echo "共 ${#targets[@]} 个可用目录"
}

# 清理日志和状态
clean_logs() {
    echo "清理日志和状态文件..."
    rm -rf "$STATUS_DIR"
    rm -rf "$LOG_DIR"
    rm -rf "$LOCK_DIR"
    echo "清理完成"
}

# 停止所有子任务
stop_all() {
    echo -e "${YELLOW}正在停止所有批量实验任务...${NC}"

    local killed=0

    # 停止 batch_experiment.sh 的其他实例（排除当前进程）
    local batch_pids=$(pgrep -f "batch_experiment.sh" | grep -v "$$")
    if [ -n "$batch_pids" ]; then
        echo "停止 batch_experiment.sh 进程..."
        for pid in $batch_pids; do
            kill -TERM "$pid" 2>/dev/null && ((killed++))
        done
    fi

    # 停止所有 adaptive_inj.sh 子进程
    local inj_pids=$(pgrep -f "adaptive_inj.sh")
    if [ -n "$inj_pids" ]; then
        echo "停止 adaptive_inj.sh 进程..."
        for pid in $inj_pids; do
            kill -TERM "$pid" 2>/dev/null && ((killed++))
        done
    fi

    # 停止所有 pin 相关进程
    local pin_pids=$(pgrep -f "pin.*-t.*letgo")
    if [ -n "$pin_pids" ]; then
        echo "停止 pin 进程..."
        for pid in $pin_pids; do
            kill -TERM "$pid" 2>/dev/null && ((killed++))
        done
    fi

    # 等待一秒后强制终止残留进程
    sleep 1

    # 强制终止仍在运行的进程
    local remaining_pids=$(pgrep -f "(batch_experiment|adaptive_inj|pin.*letgo)" | grep -v "$$")
    if [ -n "$remaining_pids" ]; then
        echo -e "${RED}强制终止残留进程...${NC}"
        for pid in $remaining_pids; do
            kill -9 "$pid" 2>/dev/null && ((killed++))
        done
    fi

    # 清理锁文件
    if [ -d "$LOCK_DIR" ]; then
        rm -rf "$LOCK_DIR"
        echo "已清理锁文件"
    fi

    if [ $killed -gt 0 ]; then
        echo -e "${GREEN}已停止 ${killed} 个进程${NC}"
    else
        echo "没有发现正在运行的实验任务"
    fi
}

# 并行执行实验（目录复用模式）
run_parallel() {
    local apps=("$@")
    local targets=($(get_available_targets))
    local num_targets=${#targets[@]}
    local num_apps=${#apps[@]}

    # 检查并行数
    local actual_parallel=$PARALLEL_NUM
    if [ $num_targets -lt $PARALLEL_NUM ]; then
        log "${YELLOW}警告: 可用目录数 ($num_targets) 少于并行数 ($PARALLEL_NUM)，将使用 $num_targets 个并行任务${NC}"
        actual_parallel=$num_targets
    fi

    if [ $num_targets -eq 0 ]; then
        log "${RED}错误: 没有可用的 letgo_Target 目录${NC}"
        exit 1
    fi

    # 准备目录
    rm -rf "$STATUS_DIR" "$LOCK_DIR"
    mkdir -p "$STATUS_DIR" "$LOCK_DIR" "$LOG_DIR"

    log "========== 并行批量实验开始 =========="
    log "应用数量: ${num_apps}, 并行数: ${actual_parallel}, 可用目录: ${num_targets}"
    log "应用列表: ${apps[*]}"
    log ""

    # 启动所有任务（由 worker 自己获取目录）
    local pids=()
    local running=0
    local app_index=0

    while [ $app_index -lt $num_apps ] || [ $running -gt 0 ]; do
        # 清理已完成的进程
        for i in "${!pids[@]}"; do
            if [ -n "${pids[$i]}" ] && ! kill -0 "${pids[$i]}" 2>/dev/null; then
                wait "${pids[$i]}" 2>/dev/null
                unset 'pids[i]'
                ((running--))
            fi
        done

        # 启动新任务（如果有空闲槽位且还有待处理的应用）
        while [ $running -lt $actual_parallel ] && [ $app_index -lt $num_apps ]; do
            local app="${apps[$app_index]}"
            worker_process "$app" &
            pids+=($!)
            ((running++))
            ((app_index++))
        done

        # 短暂等待
        if [ $running -gt 0 ]; then
            sleep 0.5
        fi
    done

    # 等待所有任务完成
    for pid in "${pids[@]}"; do
        if [ -n "$pid" ]; then
            wait "$pid" 2>/dev/null
        fi
    done

    # 统计结果
    log ""
    log "========== 实验结果 =========="
    local success_count=0
    local fail_count=0

    for app in "${apps[@]}"; do
        if [ -f "${STATUS_DIR}/${app}.status" ]; then
            local status=$(cat "${STATUS_DIR}/${app}.status")
            if [ "$status" = "success" ]; then
                log "${GREEN}✓ ${app}${NC}"
                ((success_count++))
            else
                log "${RED}✗ ${app} (${status})${NC}"
                ((fail_count++))
            fi
        else
            log "${RED}✗ ${app} (状态未知)${NC}"
            ((fail_count++))
        fi
    done

    log ""
    log "========== 并行批量实验结束 =========="
    log "总计: ${num_apps}, 成功: ${success_count}, 失败: ${fail_count}"
    log "详细日志: ${LOG_DIR}/"

    # 清理锁文件
    rm -rf "$LOCK_DIR"
}

# 顺序执行实验
run_sequential() {
    local apps=("$@")
    local targets=($(get_available_targets))
    local num_apps=${#apps[@]}

    if [ ${#targets[@]} -eq 0 ]; then
        log "${RED}错误: 没有可用的 letgo_Target 目录${NC}"
        exit 1
    fi

    mkdir -p "$LOG_DIR"

    # 使用第一个目录
    local target_dir="${targets[0]}"

    log "========== 顺序批量实验开始 =========="
    log "应用列表: ${apps[*]}"
    log "使用目录: ${target_dir}"

    local success_count=0
    local fail_count=0

    for i in "${!apps[@]}"; do
        local app="${apps[$i]}"

        log ""
        log "---------- [$((i+1))/${num_apps}] ${app} ----------"

        run_single_experiment "$app" "$target_dir"
        local exit_code=$?

        if [ $exit_code -eq 0 ]; then
            log "${GREEN}✓ ${app}: 成功${NC}"
            ((success_count++))
        else
            log "${RED}✗ ${app}: 失败${NC}"
            ((fail_count++))
        fi
    done

    log ""
    log "========== 顺序批量实验结束 =========="
    log "成功: ${success_count}, 失败: ${fail_count}"
}

# 主函数
main() {
    local apps=()
    local sequential=false

    # 解析参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                exit 0
                ;;
            -l|--list)
                list_apps
                exit 0
                ;;
            -t|--targets)
                list_targets
                exit 0
                ;;
            -c|--clean)
                clean_logs
                exit 0
                ;;
            -k|--kill)
                stop_all
                exit 0
                ;;
            -p|--parallel)
                PARALLEL_NUM="$2"
                shift 2
                ;;
            -s|--sequential)
                sequential=true
                shift
                ;;
            -a|--all)
                apps=("${APP_LIST[@]}")
                shift
                ;;
            -A|--ALL)
                apps=("${ALL_APPS[@]}")
                shift
                ;;
            -*)
                echo "未知选项: $1"
                show_help
                exit 1
                ;;
            *)
                apps+=("$1")
                shift
                ;;
        esac
    done

    # 如果没有指定应用，显示帮助
    if [ ${#apps[@]} -eq 0 ]; then
        show_help
        exit 1
    fi

    # 启动时清理旧的锁文件（防止上次异常退出后锁未释放）
    if [ -d "$LOCK_DIR" ]; then
        echo -e "${YELLOW}清理旧的锁文件...${NC}"
        rm -rf "$LOCK_DIR"
    fi

    # 创建日志目录
    mkdir -p "$LOG_DIR"

    # 检查可用目录数量
    local targets=($(get_available_targets))
    if [ ${#targets[@]} -eq 0 ]; then
        log "${RED}错误: 没有找到可用的 letgo_Target 目录${NC}"
        exit 1
    fi

    log "可用目录: ${#targets[@]} 个"

    if [ "$sequential" = true ]; then
        run_sequential "${apps[@]}"
    else
        run_parallel "${apps[@]}"
    fi
}

main "$@"
