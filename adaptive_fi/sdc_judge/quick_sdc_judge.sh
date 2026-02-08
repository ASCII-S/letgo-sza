#!/bin/bash
#
# 快速 SDC 判断脚本 - 一键运行，对所有应用进行判断
#
# 使用方法：直接运行此脚本
#   ./quick_sdc_judge.sh
#

# 进入脚本所在目录的父目录（adaptive_fi）
cd "$(dirname "$0")/.."

# 实验结果目录
RESULT_DIR="/home/tongshiyu/pin/source/tools/letgo/TargetedBenchmarkResult"

# 日志文件
LOG_FILE="/tmp/sdc_batch_$(date +%Y%m%d_%H%M%S).log"

echo "========================================================"
echo "批量 SDC 判断 - 快速模式"
echo "========================================================"
echo "实验目录: $RESULT_DIR"
echo "日志文件: $LOG_FILE"
echo "========================================================"
echo ""

# 后台运行批量判断
nohup python3 -u -m sdc_judge.batch_judge_all_apps "$RESULT_DIR" > "$LOG_FILE" 2>&1 &
PID=$!

echo "✓ 批量判断已在后台启动 (PID: $PID)"
echo ""
echo "查看实时进度:"
echo "  tail -f $LOG_FILE"
echo ""
echo "查看最近输出:"
echo "  tail -50 $LOG_FILE"
echo ""
echo "停止任务:"
echo "  kill $PID"
echo ""

# 等待一下并显示初始输出
sleep 3
echo "初始输出:"
echo "----------------------------------------"
tail -20 "$LOG_FILE"
echo "----------------------------------------"
echo ""
echo "✓ 任务正在后台运行，查看完整日志: $LOG_FILE"
