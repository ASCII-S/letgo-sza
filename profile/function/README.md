# 函数维度剖析脚本

基于Pin的function_profiler工具（v3.0），实现函数级别的特征剖析和分析。

## 功能概述

- **profile_single.py** - 单应用函数剖析
- **profile_batch.py** - 批量并行剖析
- **analyze_results.py** - 结果分析（热点函数、内存密集、计算密集、复杂度分析）
- **visualize.py** - 可视化（预留接口）

## 快速开始

### 1. 单应用剖析

```bash
# 剖析 backprop 的所有函数
python profile_single.py backprop

# 指定输出文件
python profile_single.py bfs --output ./my_bfs_function_profile.json

# 只剖析调用次数>=5的函数
python profile_single.py hotspot --min-calls 5

# 启用可选分析（F类数据依赖 + G类生命周期）
python profile_single.py backprop --enable-dep --enable-lifetime

# 设置超时时间
python profile_single.py hpl --timeout 7200
```

### 2. 批量剖析

```bash
# 剖析所有应用
python profile_batch.py --all

# 剖析rodinia套件
python profile_batch.py --suite rodinia

# 剖析指定应用
python profile_batch.py --apps backprop,bfs,hotspot
python profile_batch.py --enable-dep --enable-lifetime --apps 2mm,backprop,bfs,bicg,correlation,fdtd-2d,gesummv,hotspot,HPCCG,hpl,kmeans,miniFE,nn,particlefilter,syr2k
# 排除某些应用
python profile_batch.py --all --exclude amg,hpl

# 并行剖析（2个任务）
python profile_batch.py --suite rodinia --parallel 2

# 只剖析高频调用函数
python profile_batch.py --suite rodinia --min-calls 5
```

### 3. 分析结果

```bash
# 分析所有剖析结果
python analyze_results.py
```

### 4. 可视化（预留）

```bash
# 查看可用的可视化选项
python visualize.py
```

## 输出目录结构

```
results/
├── raw_json/               # 原始剖析结果
│   ├── rodinia/
│   │   ├── backprop_function_profile.json
│   │   ├── bfs_function_profile.json
│   │   └── ...
│   ├── mantevo/
│   ├── npb/
│   └── polybench/
├── summary/                # 汇总报告
│   ├── function_metrics_summary.csv      # 所有函数详细指标
│   ├── hotspot_functions.txt             # 热点函数分析（按调用次数）
│   ├── memory_intensive_functions.txt    # 内存密集函数分析
│   ├── compute_intensive_functions.txt   # 计算密集函数分析
│   ├── function_complexity.txt           # 函数复杂度分析
│   ├── suite_comparison.txt              # 套件对比
│   └── batch_summary_*.json              # 批量剖析汇总
├── visualization/          # 可视化图表（预留）
└── logs/                   # 运行日志
```

## JSON输出格式（v3.0）

function_profiler v3.0 输出的JSON结构（包含A-G类指标）：

```json
{
  "tool_info": {
    "name": "Function Profiler",
    "version": "3.0",
    "main_image": "/path/to/executable",
    "base_address": "0x400000"
  },
  "functions": [
    {
      "function_name": "main",
      "start_addr": "0x401234",
      "end_addr": "0x401567",
      "offset_start": "0x1234",
      "offset_end": "0x1567",
      "function_size_bytes": 819,

      "execution_stats": {              // A类：执行统计
        "call_exec": 100,
        "inst_exec": 23456,
        "inst_static": 234
      },

      "data_flow": {                    // B1类：数据流
        "mem_read_static": 50,
        "mem_write_static": 30,
        "mem_inst_static": 70,
        "mem_read_exec": 1200,
        "mem_write_exec": 800,
        "mem_inst_exec": 1800
      },

      "memory_access_pattern": {        // B1.5类：内存访问模式（按读写分离）
        "seq_read_exec": 1000,
        "stride_read_exec": 150,
        "random_read_exec": 50,
        "seq_write_exec": 600,
        "stride_write_exec": 100,
        "random_write_exec": 100
      },

      "compute_characteristics": {      // B2类：计算特性
        "arith_static": 40,
        "logic_static": 20,
        "float_static": 15,
        "simd_static": 5,
        "arith_exec": 5000,
        "logic_exec": 2000,
        "float_exec": 1000,
        "simd_exec": 500,
        "pure_compute_static": 60,
        "pure_compute_exec": 6000,
        "data_movement_static": 80,
        "data_movement_exec": 8000
      },

      "control_flow": {                 // C类：控制流
        "branch_static": 45,
        "branch_exec": 1000,
        "loop_static": 5,
        "return_static": 1,
        "call_static": 10,
        "indirect_exec": 50
      },

      "register_usage": {               // D类：寄存器使用
        "reg_read_exec": 10000,
        "reg_write_exec": 5000,
        "reg_read_static": 200,
        "reg_write_static": 100,
        "unique_reg_read": 12,
        "unique_reg_write": 8
      },

      "control_flow_detail": {          // E类：控制流细化
        "branch_taken_exec": 600,
        "branch_not_taken_exec": 400,
        "cond_branch_static": 40,
        "uncond_branch_static": 5,
        "loop_iter_total": 2500,
        "call_depth_max": 5
      },

      "data_dependency": {              // F类：数据依赖（可选）
        "def_use_pairs": 3500,
        "reg_dep_chain_max": 15,
        "mem_to_reg_exec": 1200,
        "reg_to_mem_exec": 800
      },

      "lifetime": {                     // G类：生命周期（可选）
        "reg_lifetime_total": 15000,
        "dead_write_exec": 250,
        "first_use_dist_total": 5000
      }
    }
  ],
  "statistics": {
    "total_functions_analyzed": 24,
    "total_inst_executed": 234567
  }
}
```

**命名约定**：
- `_static`：静态数量（代码中的指令数）
- `_exec`：动态执行次数（运行时执行的次数）

## 指标分类说明（v3.0）

| 类别 | 名称 | 说明 | 是否可选 |
|------|------|------|----------|
| A | 执行统计 | 调用次数、指令执行次数 | 否 |
| B1 | 数据流 | 内存读写次数 | 否 |
| B1.5 | 内存访问模式 | 连续/步长/随机访问 | 否 |
| B2 | 计算特性 | 算术/逻辑/浮点/SIMD指令 | 否 |
| C | 控制流 | 分支/循环/调用 | 否 |
| D | 寄存器使用 | 寄存器读写统计 | 否 |
| E | 控制流细化 | 分支方向/循环迭代/调用深度 | 否 |
| F | 数据依赖 | 定义-使用对 | **是**（--enable-dep） |
| G | 生命周期 | 寄存器存活/死写 | **是**（--enable-lifetime） |

### A类：执行统计
| 指标 | 说明 |
|------|------|
| call_exec | 函数被调用次数（动态） |
| inst_exec | 执行的总指令数（动态） |
| inst_static | 静态指令数量（代码规模） |

### B1类：数据流
| 指标 | 类型 | 说明 |
|------|------|------|
| mem_read_static | 静态 | 内存读指令静态数量 |
| mem_write_static | 静态 | 内存写指令静态数量 |
| mem_inst_static | 静态 | 涉及内存访问的指令数（不重复计数）|
| mem_read_exec | 动态 | 内存读执行次数 |
| mem_write_exec | 动态 | 内存写执行次数 |
| mem_inst_exec | 动态 | 访存指令执行次数（不重复计数，一条RMW指令只计一次）|

**说明**：一条指令可能同时读写（如 `ADD [mem], reg`），此时 `mem_read_exec` 和 `mem_write_exec` 都会 +1，但 `mem_inst_exec` 只 +1。

### B1.5类：内存访问模式（按读写分离）
| 指标 | 说明 |
|------|------|
| seq_read_exec | 连续读执行次数（地址差≤64字节）|
| stride_read_exec | 步长读执行次数（固定步长模式）|
| random_read_exec | 随机读执行次数 |
| seq_write_exec | 连续写执行次数（地址差≤64字节）|
| stride_write_exec | 步长写执行次数（固定步长模式）|
| random_write_exec | 随机写执行次数 |

### B2类：计算特性
| 指标 | 类型 | 说明 |
|------|------|------|
| arith_static | 静态 | 算术指令静态数量（ADD/SUB/MUL/DIV等）|
| logic_static | 静态 | 逻辑指令静态数量（AND/OR/XOR等）|
| float_static | 静态 | 浮点指令静态数量 |
| simd_static | 静态 | SIMD/向量指令静态数量 |
| arith_exec | 动态 | 算术指令执行次数 |
| logic_exec | 动态 | 逻辑指令执行次数 |
| float_exec | 动态 | 浮点指令执行次数 |
| simd_exec | 动态 | SIMD/向量指令执行次数 |
| pure_compute_static | 静态 | 纯计算指令数量（不涉及内存访问的计算指令）|
| pure_compute_exec | 动态 | 纯计算指令执行次数 |
| data_movement_static | 静态 | 数据移动指令数量（MOV/LEA/XCHG/PUSH/POP）|
| data_movement_exec | 动态 | 数据移动指令执行次数 |

### C类：控制流
| 指标 | 类型 | 说明 |
|------|------|------|
| branch_static | 静态 | 分支指令数（静态）|
| branch_exec | 动态 | 分支执行次数（动态）|
| loop_static | 静态 | 循环数（通过回边检测）|
| return_static | 静态 | 返回点数（RET指令数）|
| call_static | 静态 | 调用指令数（CALL指令数）|
| indirect_exec | 动态 | 间接跳转执行次数 |

### D类：寄存器使用
| 指标 | 类型 | 说明 |
|------|------|------|
| reg_read_exec | 动态 | 寄存器读取执行次数 |
| reg_write_exec | 动态 | 寄存器写入执行次数 |
| reg_read_static | 静态 | 所有指令的寄存器读操作数总和 |
| reg_write_static | 静态 | 所有指令的寄存器写操作数总和 |
| unique_reg_read | 静态 | 使用的不同读寄存器数量 |
| unique_reg_write | 静态 | 使用的不同写寄存器数量 |

### E类：控制流细化
| 指标 | 类型 | 说明 |
|------|------|------|
| branch_taken_exec | 动态 | 分支跳转执行次数 |
| branch_not_taken_exec | 动态 | 分支不跳转执行次数 |
| cond_branch_static | 静态 | 条件分支静态数量 |
| uncond_branch_static | 静态 | 无条件跳转静态数量 |
| loop_iter_total | 动态 | 循环总迭代次数 |
| call_depth_max | 动态 | 最大调用深度 |

### F类：数据依赖（可选，需 --enable-dep）
| 指标 | 说明 |
|------|------|
| def_use_pairs | 定义-使用对总数 |
| reg_dep_chain_max | 最长寄存器依赖链（最大指令距离）|
| mem_to_reg_exec | 内存→寄存器传递次数 |
| reg_to_mem_exec | 寄存器→内存传递次数 |

### G类：生命周期（可选，需 --enable-lifetime）
| 指标 | 说明 |
|------|------|
| reg_lifetime_total | 寄存器值总存活指令数 |
| dead_write_exec | 死写次数（写后未读即被覆盖）|
| first_use_dist_total | 定义到首次使用的总指令距离 |

## 分析功能说明

### 1. 热点函数识别

基于 `call_exec` 识别高频调用函数：
- 排序方式：按调用次数降序
- 输出：Top 20 热点函数列表
- 包含：调用次数、执行指令数、内存访问比、分支密度

### 2. 内存密集函数分析

基于 `mem_access_ratio` 识别内存密集函数：
- 排序方式：按内存访问比降序
- 输出：Top 20 内存密集函数列表
- 内存访问比计算：`(mem_read_exec + mem_write_exec) / inst_exec`
- 包含访问模式分析（连续/步长/随机）

### 3. 计算密集函数分析

基于计算指令密度识别计算密集函数：
- 计算得分 = `(arith_exec + float_exec) / inst_exec`
- 排序方式：按计算密度降序
- 输出：Top 20 计算密集函数列表
- 包含：算术/浮点/SIMD指令分布

### 4. 函数复杂度分析

基于控制流特征计算综合复杂度：
```
复杂度评分 = branch_density + loop_ratio + indirect_branch_ratio
其中:
  branch_density = branch_exec / inst_exec
  loop_ratio = loop_static / inst_static (归一化)
  indirect_branch_ratio = indirect_branch_exec / branch_exec
```
- 排序方式：按复杂度评分降序
- 输出：Top 20 复杂函数列表

## 命令行参数

### profile_single.py

| 参数 | 简写 | 默认值 | 说明 |
|------|------|--------|------|
| app_name | - | 必需 | 应用程序名称 |
| --output | -o | 自动生成 | 输出JSON文件路径 |
| --min-calls | -m | 1 | 最小调用次数过滤 |
| --enable-dep | - | 否 | 启用F类数据依赖分析（有性能开销） |
| --enable-lifetime | - | 否 | 启用G类生命周期分析（有性能开销） |
| --timeout | -t | 3600 | 超时时间（秒） |

### profile_batch.py

| 参数 | 简写 | 默认值 | 说明 |
|------|------|--------|------|
| --all | - | - | 剖析所有应用 |
| --suite | - | - | 剖析指定套件 |
| --apps | - | - | 逗号分隔的应用列表 |
| --exclude | - | - | 要排除的应用列表 |
| --parallel | -p | 1 | 并行任务数（1-4） |
| --timeout | -t | 3600 | 超时时间（秒） |
| --max-retries | -r | 2 | 最大重试次数 |
| --min-calls | -m | 1 | 最小调用次数过滤 |
| --enable-dep | - | 否 | 启用F类数据依赖分析 |
| --enable-lifetime | - | 否 | 启用G类生命周期分析 |

**注意**：启用 `--enable-dep` 和 `--enable-lifetime` 会增加剖析开销，建议仅在需要时启用。

## 依赖

### 必需
- Python 3.6+
- 已编译的 function_profiler Pin工具（v3.0）

### 可选
- tqdm - 进度条显示
- pandas - 数据分析
- matplotlib - 可视化

```bash
# 安装可选依赖
pip install tqdm pandas matplotlib
```

## 与现有架构的关系

本脚本复用以下共享组件：
- `config.py` - 配置管理
- `app_config.py` - 应用配置加载器
- `applications.json` - 应用配置文件

目录结构与 `application/` 维度保持一致。

## 指标汇总表

| 类别 | 指标名 | 类型 | 说明 |
|------|--------|------|------|
| A | call_exec | 动态 | 函数调用执行次数 |
| A | inst_exec | 动态 | 总指令执行次数 |
| A | inst_static | 静态 | 静态指令数量 |
| B1 | mem_read_static | 静态 | 内存读指令静态数量 |
| B1 | mem_write_static | 静态 | 内存写指令静态数量 |
| B1 | mem_inst_static | 静态 | 涉及内存访问的指令数 |
| B1 | mem_read_exec | 动态 | 内存读执行次数 |
| B1 | mem_write_exec | 动态 | 内存写执行次数 |
| B1 | mem_inst_exec | 动态 | 访存指令执行次数 |
| B1.5 | seq_read_exec | 动态 | 连续读执行次数 |
| B1.5 | stride_read_exec | 动态 | 步长读执行次数 |
| B1.5 | random_read_exec | 动态 | 随机读执行次数 |
| B1.5 | seq_write_exec | 动态 | 连续写执行次数 |
| B1.5 | stride_write_exec | 动态 | 步长写执行次数 |
| B1.5 | random_write_exec | 动态 | 随机写执行次数 |
| B2 | arith_static | 静态 | 算术指令静态数量 |
| B2 | logic_static | 静态 | 逻辑指令静态数量 |
| B2 | float_static | 静态 | 浮点指令静态数量 |
| B2 | simd_static | 静态 | SIMD指令静态数量 |
| B2 | arith_exec | 动态 | 算术指令执行次数 |
| B2 | logic_exec | 动态 | 逻辑指令执行次数 |
| B2 | float_exec | 动态 | 浮点指令执行次数 |
| B2 | simd_exec | 动态 | SIMD指令执行次数 |
| B2 | pure_compute_static | 静态 | 纯计算指令静态数量 |
| B2 | pure_compute_exec | 动态 | 纯计算指令执行次数 |
| B2 | data_movement_static | 静态 | 数据移动指令静态数量 |
| B2 | data_movement_exec | 动态 | 数据移动指令执行次数 |
| C | branch_static | 静态 | 分支指令静态数量 |
| C | branch_exec | 动态 | 分支指令执行次数 |
| C | loop_static | 静态 | 循环静态数量 |
| C | return_static | 静态 | 返回点静态数量 |
| C | call_static | 静态 | 函数调用静态数量 |
| C | indirect_exec | 动态 | 间接跳转执行次数 |
| D | reg_read_exec | 动态 | 寄存器读取执行次数 |
| D | reg_write_exec | 动态 | 寄存器写入执行次数 |
| D | reg_read_static | 静态 | 静态寄存器读操作数 |
| D | reg_write_static | 静态 | 静态寄存器写操作数 |
| D | unique_reg_read | 静态 | 使用的不同读寄存器数 |
| D | unique_reg_write | 静态 | 使用的不同写寄存器数 |
| E | branch_taken_exec | 动态 | 分支跳转执行次数 |
| E | branch_not_taken_exec | 动态 | 分支未跳转执行次数 |
| E | cond_branch_static | 静态 | 条件分支静态数量 |
| E | uncond_branch_static | 静态 | 无条件跳转静态数量 |
| E | loop_iter_total | 动态 | 循环总迭代次数 |
| E | call_depth_max | 动态 | 最大调用深度 |
| F | def_use_pairs | 动态 | 定义-使用对总数 [可选] |
| F | reg_dep_chain_max | 动态 | 最长寄存器依赖链 [可选] |
| F | mem_to_reg_exec | 动态 | 内存→寄存器传递次数 [可选] |
| F | reg_to_mem_exec | 动态 | 寄存器→内存传递次数 [可选] |
| G | reg_lifetime_total | 动态 | 寄存器值总存活指令数 [可选] |
| G | dead_write_exec | 动态 | 死写次数 [可选] |
| G | first_use_dist_total | 动态 | 定义到首次使用的总距离 [可选] |

## 版本

- **脚本版本**: 1.1（适配function_profiler v3.0）
- **function_profiler版本**: 3.0
- **依赖**: Intel Pin, function_profiler.so
