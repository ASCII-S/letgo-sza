#!/bin/bash

# 分发 adaptive_inj.sh 到各个 letgo_Target 子目录的脚本

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_FILE="${SCRIPT_DIR}/adaptive_inj.sh"

# 检查源文件是否存在
if [ ! -f "$SOURCE_FILE" ]; then
    echo "错误: 源文件 $SOURCE_FILE 不存在"
    exit 1
fi

# 计数器
copied=0
skipped=0

# 遍历所有 letgo_Target* 子目录
for dir in "${SCRIPT_DIR}"/letgo_Target*/; do
    if [ -d "$dir" ]; then
        target_file="${dir}adaptive_inj.sh"
        cp "$SOURCE_FILE" "$target_file"
        chmod +x "$target_file"
        echo "已复制到: $dir"
        ((copied++))
    fi
done

echo ""
echo "分发完成！共复制到 $copied 个目录"
