# App Profiler 快速开始指南

本指南使用 **app_profiler** 工具对应用程序进行批量剖析分析。

## 工具说明

`app_profiler` 是基于 Intel Pin 的应用级特征剖析工具，用于分析程序的：

- **D类指标**：指令类型分布（整数、浮点、内存、控制流、逻辑、SIMD等）
- **A类指标**：数值敏感性（浮点运算、敏感运算、精度分布）
- **B类指标**：误差吸收能力（比较、饱和、MIN/MAX、舍入等）
- **C类指标**：库调用统计（math、BLAS、LAPACK、MPI、OpenMP等）

工具位置：`/home/tongshiyu/pin/source/tools/pinfi/app_profiler/`

## 前置检查

```bash
# 1. 验证配置
python3 test_profiler.py

# 2. 查看可用应用
python3 list_applications.py --by-suite
```

## 单个应用剖析

### 基础用法

```bash
# 剖析单个应用
python3 profile_single.py backprop

# 指定输出路径
python3 profile_single.py bfs --output /path/to/output.json

# 详细输出模式
python3 profile_single.py backprop --verbose
```

### 常用应用示例

```bash
# Rodinia 套件
python3 profile_single.py backprop
python3 profile_single.py bfs
python3 profile_single.py hotspot

# Mantevo 套件（MPI应用）
python3 profile_single.py HPCCG
python3 profile_single.py miniFE

# NPB 套件
python3 profile_single.py bt
python3 profile_single.py cg

# PolyBench 套件
python3 profile_single.py 2mm
python3 profile_single.py correlation
```

## 批量剖析

### 按套件剖析

```bash
# 剖析整个 Rodinia 套件（串行）
python3 profile_batch.py --suite rodinia

# 使用 4 个并行任务
python3 profile_batch.py --suite rodinia --parallel 4

# 剖析 Mantevo 套件（增加超时时间）
python3 profile_batch.py --suite mantevo --timeout 7200

# 剖析 PolyBench 套件
python3 profile_batch.py --suite polybench --parallel 4
```

### 剖析所有应用

```bash
# 剖析所有 41 个应用（串行）
python3 profile_batch.py --all

# 使用 4 个并行任务
python3 profile_batch.py --all --parallel 4

# 排除某些应用
python3 profile_batch.py --all --exclude hpl miniAMR
```

### 指定应用列表

```bash
# 剖析指定的几个应用
python3 profile_batch.py --apps backprop bfs hotspot kmeans

# 并行剖析
python3 profile_batch.py --apps backprop bfs hotspot --parallel 3
```

### Dry-run 模式

```bash
# 查看将要剖析的应用列表（不实际执行）
python3 profile_batch.py --suite rodinia --dry-run
python3 profile_batch.py --all --dry-run
```

## 输出文件

### 目录结构

```
results/
├── raw_json/          # 原始 JSON 数据
│   ├── rodinia/       # 按套件分类
│   │   ├── backprop_profile.json
│   │   ├── bfs_profile.json
│   │   └── ...
│   ├── mantevo/
│   ├── npb/
│   └── polybench/
├── summary/           # 分析汇总
├── visualization/     # 可视化图表
└── logs/              # 执行日志
    ├── backprop_profile_20260209_133045.log
    ├── batch_profile_20260209_133100.log
    └── ...
```

### JSON 输出格式

每个应用的 JSON 文件包含以下主要部分：

```json
{
  "tool_info": {
    "name": "Application Profiler",
    "version": "2.0",
    "main_image": "backprop"
  },
  "instruction_distribution": {
    "total": {"static_count": 1234, "exec_count": 567890},
    "by_category": {
      "int_arithmetic": {...},
      "float": {...},
      "memory": {...},
      "control_flow": {...},
      "logic": {...},
      "simd": {...}
    }
  },
  "numeric_sensitivity": {
    "float_inst_static": 100,
    "float_inst_exec": 30000,
    "operation_distribution": {...},
    "precision_distribution": {...}
  },
  "error_absorption": {
    "cmp_inst_exec": 5000,
    "test_inst_exec": 2000,
    ...
  },
  "library_calls": {
    "total_lib_calls": 500,
    "by_category": {...}
  }
}
```

## 高级选项

### 设置超时时间

```bash
# 默认超时 3600 秒（1小时）
python3 profile_single.py hpl --timeout 7200

# 批量剖析设置超时
python3 profile_batch.py --suite mantevo --timeout 7200
```

### 失败重试

```bash
# 设置最大重试次数（默认 2 次）
python3 profile_batch.py --all --retries 3
```

### 并行任务数

```bash
# 并行任务数范围：1-4
python3 profile_batch.py --all --parallel 4

# 根据 CPU 核心数调整
python3 profile_batch.py --suite rodinia --parallel 2
```

## 完整工作流示例

### 快速开始

```bash
# 1. 验证配置
python3 test_profiler.py

# 2. 查看应用列表
python3 list_applications.py --by-suite

# 3. 测试单个应用
python3 profile_single.py backprop

# 4. 批量剖析
python3 profile_batch.py --suite rodinia --parallel 4

# 5. 查看结果
ls -lh results/raw_json/rodinia/
cat results/logs/batch_profile_*.log
```

### 分阶段执行

```bash
# 阶段 1：快速套件（Rodinia + PolyBench）
python3 profile_batch.py --suite rodinia --parallel 4
python3 profile_batch.py --suite polybench --parallel 4

# 阶段 2：慢速套件（Mantevo + NPB）
python3 profile_batch.py --suite mantevo --timeout 7200 --parallel 2
python3 profile_batch.py --suite npb --parallel 3

# 阶段 3：查看批量汇总
ls -lh results/summary/batch_summary_*.json
```

### 增量执行（重试失败的应用）

```bash
# 查看批量日志，找出失败的应用
cat results/logs/batch_profile_*.log | grep "失败"

# 重新剖析失败的应用
python3 profile_batch.py --apps app1 app2 app3 --retries 3
```

## 故障排除

### 1. 工具未编译

**错误**: `app_profiler.so 不存在`

**解决方案**:
```bash
cd /home/tongshiyu/pin/source/tools/pinfi
make obj-intel64/app_profiler/app_profiler.so
```

### 2. 应用超时

**错误**: `剖析超时`

**解决方案**:
```bash
# 增加超时时间
python3 profile_single.py hpl --timeout 10800  # 3小时
```

### 3. MPI 应用失败

**错误**: `mpirun 命令未找到`

**解决方案**:
```bash
# 检查 MPI 环境
which mpirun
module load openmpi  # 或根据系统环境加载 MPI
```

### 4. 内存不足

**解决方案**:
```bash
# 减少并行任务数
python3 profile_batch.py --all --parallel 1

# 或分批处理
python3 profile_batch.py --suite rodinia
python3 profile_batch.py --suite polybench
```

### 5. 查看详细日志

```bash
# 查看单个应用的日志
cat results/logs/<app>_profile_*.log

# 查看批量剖析日志
cat results/logs/batch_profile_*.log

# 实时监控批量剖析
tail -f results/logs/batch_profile_*.log
```

## 性能优化建议

1. **并行任务数**: 根据 CPU 核心数选择，推荐 2-4 个并行任务
2. **超时设置**: 小程序使用默认值，大程序（hpl, miniAMR）建议 7200秒+
3. **分批处理**: 先处理快速套件（rodinia, polybench），再处理慢速套件（mantevo）
4. **Dry-run**: 使用 `--dry-run` 预览任务，避免误操作

## 依赖说明

### Python 依赖

```bash
# 可选依赖（用于进度条）
pip install tqdm
```

### 系统依赖

- Python 3.6+
- Intel Pin
- MPI 环境（用于 Mantevo 套件）
- 编译好的 app_profiler.so

## 参考文档

- 完整文档：`README.md`
- 工具文档：`/home/tongshiyu/pin/source/tools/pinfi/app_profiler/README.md`
- 应用配置：`applications.json`
- 配置文件：`../config.py`

## 支持

如有问题，请查看：
1. 工具日志：`results/logs/`
2. 应用配置：`list_applications.py --app <app_name>`
3. 配置验证：`python3 test_profiler.py`
