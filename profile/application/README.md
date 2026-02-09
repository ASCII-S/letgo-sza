# Application Profiler - 应用维度剖析

使用 `app_profiler` 工具批量剖析应用程序的 Python 脚本集合。

## 工具说明

**app_profiler** 是基于 Intel Pin 的应用级特征剖析工具，提供四类剖析指标：

- **D类 - 指令分布**: 整数/浮点/内存/控制流/逻辑/MOV/SIMD/其他（含细分）
- **A类 - 数值敏感性**: 浮点运算详细分类、精度分布、敏感运算（div/sqrt）
- **B类 - 误差吸收**: 比较/测试/饱和/MIN·MAX/绝对值/舍入指令
- **C类 - 库调用**: math/BLAS/LAPACK/memory/IO/string/MPI/OpenMP/pthread

工具位置: `/home/tongshiyu/pin/source/tools/pinfi/app_profiler/`
配置文件: `../applications.json` (41个应用)

---

## 快速开始

### 1. 验证配置

```bash
python3 test_profiler.py
```

### 2. 单应用剖析

```bash
# 基础用法
python3 profile_single.py backprop

# 详细模式
python3 profile_single.py backprop --verbose

# 指定输出和超时
python3 profile_single.py hpl --output /path/to/output.json --timeout 7200
```

### 3. 批量剖析

```bash
# 按套件剖析（串行）
python3 profile_batch.py --suite rodinia

# 并行剖析（4任务）
python3 profile_batch.py --suite rodinia --parallel 4

# 剖析所有应用
python3 profile_batch.py --all --parallel 4

# 指定应用列表（空格分隔）
python3 profile_batch.py --apps backprop bfs hotspot --parallel 3

# 指定应用列表（逗号分隔）
python3 profile_batch.py --apps backprop,bfs,hotspot --parallel 3

# 排除部分应用（空格分隔）
python3 profile_batch.py --all --exclude hpl miniAMR

# 排除部分应用（逗号分隔）
python3 profile_batch.py --all --exclude hpl,miniAMR,miniMD

# Dry-run预览
python3 profile_batch.py --suite mantevo --dry-run
```

### 4. 查看应用配置

```bash
# 按套件统计
python3 list_applications.py --by-suite

# 查看单个应用
python3 list_applications.py --app backprop

# 列出所有应用
python3 list_applications.py
```

---

## 命令行参数

### profile_single.py

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `app_name` | 应用名称（必需） | - |
| `--output, -o` | 输出JSON路径 | `results/raw_json/<suite>/<app>_profile.json` |
| `--timeout, -t` | 超时时间（秒） | 3600 |
| `--verbose, -v` | 详细输出模式 | False |

### profile_batch.py

**应用选择（互斥）:**
- `--all` - 剖析所有应用
- `--suite <name>` - 剖析指定套件（rodinia/mantevo/npb/polybench）
- `--apps <list>` - 指定应用列表（支持空格或逗号分隔）

**执行参数:**
- `--exclude <list>` - 排除指定应用（支持空格或逗号分隔）
- `--parallel, -p` - 并行任务数（1-4，默认1）
- `--timeout, -t` - 每应用超时（秒，默认3600）
- `--retries, -r` - 失败重试次数（默认2）
- `--dry-run` - 仅预览不执行

---

## 输出文件

### 目录结构

```
results/
├── raw_json/              # 剖析结果JSON
│   ├── rodinia/          # 按套件分类
│   │   ├── backprop_profile.json
│   │   └── ...
│   ├── mantevo/
│   ├── npb/
│   └── polybench/
├── summary/               # 批量汇总
│   └── batch_summary_<timestamp>.json
├── visualization/         # 可视化图表
└── logs/                  # 执行日志
    ├── <app>_profile_<timestamp>.log
    └── batch_profile_<timestamp>.log
```

### JSON 格式

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
      "mov": {...},
      "simd": {...},
      "other": {...}
    },
    "int_arithmetic_details": {"add": {...}, "sub": {...}, ...},
    "memory_details": {"load": {...}, "store": {...}, "stack": {...}},
    "control_flow_details": {"jmp": {...}, "jcc": {...}, "call": {...}, "ret": {...}},
    "logic_details": {"bitwise": {...}, "shift": {...}},
    "simd_details": {"sse": {...}, "avx": {...}, "avx512": {...}}
  },
  "numeric_sensitivity": {
    "float_inst_static": 100,
    "float_inst_exec": 30000,
    "operation_distribution": {
      "add_sub": 10000,
      "mul": 8000,
      "div": 100,
      "sqrt": 50,
      "fma": 5000,
      "cmp": 1000,
      "cvt": 500
    },
    "precision_distribution": {
      "single": 5000,
      "double": 25000,
      "x87": 0
    },
    "simd_float_exec": 10000
  },
  "error_absorption": {
    "cmp_inst_exec": 5000,
    "test_inst_exec": 2000,
    "saturate_inst_exec": 100,
    "minmax_inst_exec": 50,
    "abs_inst_exec": 30,
    "round_inst_exec": 20
  },
  "library_calls": {
    "total_lib_calls": 500,
    "user_func_calls": 100,
    "by_category": {
      "math_lib": {"call_count": 50, "unique_funcs": 5, "functions": [...]},
      "blas_lib": {...},
      "lapack_lib": {...},
      "memory_lib": {...},
      "io_lib": {...},
      "string_lib": {...},
      "mpi_lib": {...},
      "omp_lib": {...},
      "pthread_lib": {...}
    }
  },
  "global_stats": {
    "total_inst_static": 1234,
    "total_inst_exec": 567890,
    "total_func_calls": 600
  }
}
```

---

## Python API

### 基础用法

```python
from profile_single import ApplicationProfiler

# 创建剖析器
profiler = ApplicationProfiler("backprop", verbose=False)

# 执行剖析
result = profiler.run(timeout=300)

# 检查结果
if result['success']:
    print(f"成功: {result['output_file']}")
    print(f"耗时: {result['elapsed_time']:.1f}秒")
else:
    print(f"失败: {result['error']}")
```

### 批量剖析

```python
from profile_single import ApplicationProfiler

apps = ["backprop", "bfs", "hotspot"]
results = []

for app_name in apps:
    profiler = ApplicationProfiler(app_name)
    result = profiler.run(timeout=300)
    results.append((app_name, result))

    status = "✓" if result['success'] else "✗"
    print(f"{status} {app_name}")
```

完整示例请参考 `example_batch_profile.py`。

---

## 应用套件

**配置来源**: `../applications.json`

| 套件 | 数量 | 说明 |
|------|------|------|
| **rodinia** | 19 | Rodinia Benchmark Suite (OpenMP) |
| **mantevo** | 4 | Mantevo Benchmark Suite (MPI) |
| **npb** | 9 | NAS Parallel Benchmarks Serial |
| **polybench** | 9 | PolyBench/C Benchmark Suite |
| **总计** | 41 | - |

**MPI应用**: HPCCG, miniAMR, miniFE, miniMD

---

## 常见问题

### 1. 工具未编译

```bash
# 编译 app_profiler
cd /home/tongshiyu/pin/source/tools/pinfi
make obj-intel64/app_profiler/app_profiler.so
```

### 2. 应用超时

```bash
# 增加超时时间
python3 profile_single.py hpl --timeout 10800
python3 profile_batch.py --suite mantevo --timeout 7200
```

### 3. MPI应用失败

```bash
# 检查MPI环境
which mpirun
module load openmpi
```

### 4. 内存不足

```bash
# 减少并行数或分批处理
python3 profile_batch.py --all --parallel 1
python3 profile_batch.py --suite rodinia
python3 profile_batch.py --suite polybench
```

### 5. 查看日志

```bash
# 单应用日志
cat results/logs/<app>_profile_*.log

# 批量日志
cat results/logs/batch_profile_*.log
tail -f results/logs/batch_profile_*.log  # 实时监控
```

---

## 性能建议

1. **并行任务**: 根据CPU核心数选择，推荐2-4个
2. **超时设置**: 小程序用默认值，大程序（hpl/miniAMR）建议7200秒+
3. **分批处理**: 先快速套件（rodinia/polybench），再慢速套件（mantevo）
4. **Dry-run**: 使用 `--dry-run` 预览任务

---

## 脚本说明

| 脚本 | 功能 |
|------|------|
| `profile_single.py` | 单应用剖析 |
| `profile_batch.py` | 批量剖析（支持并行） |
| `list_applications.py` | 查看应用配置 |
| `test_profiler.py` | 验证配置 |
| `example_batch_profile.py` | Python API示例 |
| `generate_app_configs.py` | 生成applications.json |

---

## 依赖

**Python依赖**:
```bash
pip install tqdm  # 可选，用于进度条
```

**系统依赖**:
- Python 3.6+
- Intel Pin
- MPI环境（用于Mantevo套件）
- 编译好的 `app_profiler.so`

---

## 参考

- **工具文档**: `/home/tongshiyu/pin/source/tools/pinfi/app_profiler/README.md`
- **配置文件**: `../applications.json` 和 `../config.py`
- **完整配置**: `/home/tongshiyu/pin/source/tools/letgo/configure.py`

---

**版本**: v2.0
**最后更新**: 2026-02-09
