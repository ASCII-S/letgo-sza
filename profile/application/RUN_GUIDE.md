# run.sh 使用说明

## 脚本概述

`run.sh` 是应用程序剖析的批量执行脚本，用于一次性剖析多个应用程序。

## 快速开始

```bash
# 直接执行（使用默认配置）
./run.sh

# 或者使用 bash 执行
bash run.sh
```

## 应用列表

脚本默认剖析以下 29 个应用：

### Rodinia 套件 (11个)
- amg, backprop, bfs, hotspot
- hpl, kmeans, needle
- srad, nn, particlefilter, lu

### Mantevo 套件 (2个)
- HPCCG, miniFE

### NPB-SER 套件 (9个)
- bt, cg, ep, ft, is, mg, sp, ua

### PolyBench 套件 (7个)
- 2mm, bicg, correlation, fdtd-2d, gesummv, syr2k

## 配置参数

在脚本开头可以修改以下参数：

```bash
PARALLEL_JOBS=2          # 并行任务数 (1-4)
TIMEOUT=3600            # 超时时间(秒) - 默认1小时
MAX_RETRIES=2           # 最大重试次数
```

### 调整并行度

```bash
# 编辑 run.sh，修改第 24 行
PARALLEL_JOBS=1          # 串行执行（最安全）
PARALLEL_JOBS=2          # 2个任务并行（推荐）
PARALLEL_JOBS=4          # 4个任务并行（最大）
```

### 调整超时时间

```bash
# 编辑 run.sh，修改第 25 行
TIMEOUT=1800            # 30分钟
TIMEOUT=3600            # 1小时（默认）
TIMEOUT=7200            # 2小时（适用于大型应用）
```

## 修改应用列表

### 方法1: 编辑脚本中的 APPS 数组

编辑 `run.sh` 第 10-21 行：

```bash
APPS=(
    # 只剖析你需要的应用
    "backprop" "bfs" "hotspot"
    "kmeans" "nn"
)
```

### 方法2: 直接使用 Python 脚本

如果需要更灵活的控制，直接使用 Python 脚本：

```bash
# 剖析所有应用
python3 profile_batch.py --all

# 剖析指定套件
python3 profile_batch.py --suite rodinia

# 剖析指定应用（逗号分隔）
python3 profile_batch.py --apps backprop,bfs,hotspot

# 排除某些应用
python3 profile_batch.py --all --exclude amg,hpl

# 使用正则表达式筛选
python3 profile_batch.py --regex ".*mm$"  # 所有以mm结尾的应用

# 自定义参数
python3 profile_batch.py \
    --apps backprop,bfs,hotspot \
    --parallel 2 \
    --timeout 3600 \
    --max-retries 2
```

## 输出结果

脚本执行完成后，结果保存在以下目录：

```
results/
├── raw_json/              # 原始JSON剖析结果
│   ├── rodinia/
│   │   ├── backprop_profile.json
│   │   ├── bfs_profile.json
│   │   └── ...
│   ├── mantevo/
│   ├── npb/
│   └── polybench/
├── summary/               # 汇总报告
│   └── batch_summary_*.json
└── logs/                  # 运行日志
    ├── backprop_profile_*.log
    └── ...
```

## 执行示例

### 示例输出

```bash
$ ./run.sh
========================================
应用程序剖析批量执行
========================================
配置信息:
  应用数量: 29
  并行任务数: 2
  超时时间: 3600秒
  最大重试: 2 次

ℹ 开始批量剖析...

使用并行模式(2个任务)...
剖析进度: 100%|████████████████| 29/29 [15:30<00:00, 32.1s/it]

汇总报告已保存: results/summary/batch_summary_20260209_160530.json

======================================================================
批量剖析统计
======================================================================
总计: 29 个应用
  成功: 27 个
  失败: 2 个
  超时: 0 个
总耗时: 930.5 秒
======================================================================

失败应用:
  - knn: 剖析失败，退出码: 1
  - gaussian: 剖析失败，退出码: 2

⚠ 部分应用剖析失败 (退出码: 1)
ℹ 请查看日志文件了解详情: results/logs/

ℹ 结果文件位置:
  原始JSON: results/raw_json/
  汇总报告: results/summary/
  日志文件: results/logs/
```

## 故障排查

### 问题1: 权限错误

```bash
$ ./run.sh
bash: ./run.sh: Permission denied

# 解决方案：添加可执行权限
chmod +x run.sh
```

### 问题2: Python 脚本未找到

```bash
# 确保在正确的目录下执行
cd /home/tongshiyu/pin/source/tools/letgo/profile/application
./run.sh
```

### 问题3: 部分应用失败

查看详细日志：

```bash
# 查看最新的批量日志
ls -lt results/logs/batch_* | head -1

# 查看特定应用的日志
cat results/logs/backprop_profile_*.log
```

### 问题4: 超时

对于大型应用，可能需要增加超时时间：

```bash
# 编辑 run.sh
TIMEOUT=7200  # 增加到2小时
```

## 高级用法

### 分批执行

如果应用太多，可以分批执行：

```bash
# 第一批：Rodinia
python3 profile_batch.py --suite rodinia

# 第二批：Mantevo
python3 profile_batch.py --suite mantevo

# 第三批：NPB
python3 profile_batch.py --suite npb

# 第四批：PolyBench
python3 profile_batch.py --suite polybench
```

### 测试单个应用

在批量执行前，可以先测试单个应用：

```bash
# 测试单个应用
python3 profile_single.py backprop

# 查看结果
cat results/raw_json/rodinia/backprop_profile.json
```

### 后台执行

对于长时间运行的批量任务：

```bash
# 后台运行，并保存输出
nohup ./run.sh > run_output.log 2>&1 &

# 查看进度
tail -f run_output.log

# 查看进程
ps aux | grep profile_batch
```

## 性能建议

### 并行度选择

- **PARALLEL_JOBS=1**: 最安全，适合调试
- **PARALLEL_JOBS=2**: 推荐，平衡性能和稳定性
- **PARALLEL_JOBS=4**: 最快，但可能影响系统稳定性

### 资源消耗

每个剖析任务大约消耗：
- **CPU**: 1-2核心
- **内存**: 2-4GB
- **磁盘**: 每个结果文件约1-10MB

建议配置：
- **串行 (PARALLEL_JOBS=1)**: 2核CPU, 4GB内存
- **并行2 (PARALLEL_JOBS=2)**: 4核CPU, 8GB内存
- **并行4 (PARALLEL_JOBS=4)**: 8核CPU, 16GB内存

## 相关文件

- `profile_batch.py` - Python批量剖析脚本
- `profile_single.py` - Python单应用剖析脚本
- `config.py` - 配置文件
- `README.md` - 详细文档

## 注意事项

1. **NPB lu 冲突**: NPB套件的 `lu` 与 Rodinia 的 `lu` 同名，当前列表中只包含 Rodinia 版本
2. **MPI 应用**: HPCCG, miniFE 等需要 MPI 环境，脚本会自动使用 mpirun
3. **磁盘空间**: 确保有足够的磁盘空间存储结果（约300MB-1GB）
4. **执行时间**: 29个应用串行执行约需30-60分钟，并行2可缩短到15-30分钟
