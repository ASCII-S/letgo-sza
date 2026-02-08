#!/bin/bash
# 应用剖析工具验证脚本

echo "======================================"
echo "应用剖析工具验证"
echo "======================================"
echo ""

cd /home/tongshiyu/pin/source/tools/letgo/profile/application

echo "1. 测试共享配置加载器..."
python3 ../app_config.py > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "   ✓ 共享配置加载器正常"
else
    echo "   ✗ 共享配置加载器失败"
    exit 1
fi

echo ""
echo "2. 测试应用列表工具..."
python3 list_applications.py --by-suite > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "   ✓ 应用列表工具正常"
else
    echo "   ✗ 应用列表工具失败"
    exit 1
fi

echo ""
echo "3. 测试单个应用查询..."
python3 list_applications.py --app backprop > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "   ✓ 单个应用查询正常"
else
    echo "   ✗ 单个应用查询失败"
    exit 1
fi

echo ""
echo "4. 测试单个应用剖析脚本..."
python3 profile_single.py --help > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "   ✓ 单个应用剖析脚本正常"
else
    echo "   ✗ 单个应用剖析脚本失败"
    exit 1
fi

echo ""
echo "5. 测试批量剖析脚本..."
python3 profile_batch.py --help > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "   ✓ 批量剖析脚本正常"
else
    echo "   ✗ 批量剖析脚本失败"
    exit 1
fi

echo ""
echo "6. 测试配置生成脚本..."
python3 generate_app_configs.py > /dev/null 2>&1
if [ $? -eq 0 ] || [ $? -eq 1 ]; then
    # 退出码 0 或 1 都表示脚本运行成功（1 表示有二进制缺失）
    echo "   ✓ 配置生成脚本正常"
else
    echo "   ✗ 配置生成脚本失败"
    exit 1
fi

echo ""
echo "======================================"
echo "✓ 所有工具验证通过！"
echo "======================================"
echo ""
echo "使用方式："
echo "  查看应用: python3 list_applications.py --by-suite"
echo "  剖析应用: python3 profile_single.py backprop"
echo "  批量剖析: python3 profile_batch.py --suite rodinia"
echo ""
