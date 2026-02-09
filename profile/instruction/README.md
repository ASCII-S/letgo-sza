# 指令维度剖析脚本

基于Pin的instruction_profiler工具，实现指令级别的语义特征剖析和分析。

## 功能概述

- **profile_single.py** - 单应用指令剖析
- **profile_batch.py** - 批量并行剖析

## Pin工具说明

本脚本使用的Pin工具位于：`/home/tongshiyu/pin/source/tools/pinfi/instruction_profiler/`

工具详细说明请参考：`/home/tongshiyu/pin/source/tools/pinfi/instruction_profiler/README.md`

## 快速开始

### 1. 单应用剖析

```bash
# 剖析 backprop 的所有指令
python profile_single.py backprop

# 指定输出文件
python profile_single.py bfs --output ./my_bfs_instruction_profile.json

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

# 排除某些应用
python profile_batch.py --all --exclude amg,hpl

# 并行剖析(2个任务)
python profile_batch.py --suite rodinia --parallel 2
```

## 输出目录结构

```
results/
├── raw_json/               # 原始剖析结果
│   ├── rodinia/
│   │   ├── backprop_instruction_profile.json
│   │   ├── bfs_instruction_profile.json
│   │   └── ...
│   ├── mantevo/
│   ├── npb/
│   └── polybench/
├── summary/                # 汇总报告
│   └── batch_summary_*.json              # 批量剖析汇总
├── visualization/          # 可视化图表(预留)
└── logs/                   # 运行日志
```

## JSON输出格式

instruction_profiler输出的JSON结构：

```json
{
  "tool_info": {
    "name": "Instruction Profiler",
    "version": "1.0",
    "main_image": "/path/to/app",
    "base_address": "0x400000"
  },
  "instructions": [
    {
      "offset": "0x1234",
      "mnemonic": "MOV",
      "disasm": "mov rax, [rbp-0x8]",
      "size": 4,
      "category": "DATAXFER",
      "is_arith": false,
      "is_logic": false,
      "is_float": false,
      "is_simd": false,
      "is_data_move": true,
      "explicit_reg_read": ["RBP"],
      "explicit_reg_write": ["RAX"],
      "implicit_reg_read": [],
      "implicit_reg_write": [],
      "uses_flags": false,
      "is_mem_read": true,
      "is_mem_write": false,
      "mem_operand_count": 1,
      "mem_access_mode": "stack",
      "is_branch": false,
      "is_cond_branch": false,
      "is_call": false,
      "is_ret": false,
      "is_indirect": false,
      "is_crash_prone": true,
      "crash_prone_type": "mem_read"
    }
  ],
  "statistics": {
    "total_instructions": 1000
  }
}
```

## 指标分类说明

### A类：指令标识

| 指标 | 类型 | 说明 |
|------|------|------|
| `offset` | string | 相对于镜像基址的偏移(用于地址匹配) |
| `mnemonic` | string | 指令助记符(如 MOV, ADD) |
| `disasm` | string | 完整反汇编文本 |
| `size` | int | 指令字节长度 |

### B类：指令分类

| 指标 | 类型 | 说明 |
|------|------|------|
| `category` | string | XED 指令类别 |
| `is_arith` | bool | 是否为算术指令 |
| `is_logic` | bool | 是否为逻辑指令 |
| `is_float` | bool | 是否为浮点指令 |
| `is_simd` | bool | 是否为 SIMD 指令 |
| `is_data_move` | bool | 是否为数据移动指令 |

### C类：寄存器特征

| 指标 | 类型 | 说明 |
|------|------|------|
| `explicit_reg_read` | array | 显式读寄存器列表 |
| `explicit_reg_write` | array | 显式写寄存器列表 |
| `implicit_reg_read` | array | 隐式读寄存器列表(如 DIV 隐式使用 RAX) |
| `implicit_reg_write` | array | 隐式写寄存器列表 |
| `uses_flags` | bool | 是否读/写标志寄存器 |

### D类：访存特征

| 指标 | 类型 | 说明 |
|------|------|------|
| `is_mem_read` | bool | 是否读内存 |
| `is_mem_write` | bool | 是否写内存 |
| `mem_operand_count` | int | 内存操作数数量 |
| `mem_access_mode` | string | 寻址模式 |

**mem_access_mode 取值**：

| 值 | 说明 |
|----|------|
| `none` | 无内存访问 |
| `stack` | 栈访问(RSP/RBP 基址) |
| `array` | 数组式访问(base + index * scale) |
| `pointer` | 指针解引用(base + disp) |
| `rip_relative` | RIP 相对寻址(全局变量) |
| `absolute` | 绝对地址 |

### E类：控制流特征

| 指标 | 类型 | 说明 |
|------|------|------|
| `is_branch` | bool | 是否为分支指令 |
| `is_cond_branch` | bool | 是否为条件分支 |
| `is_call` | bool | 是否为调用指令 |
| `is_ret` | bool | 是否为返回指令 |
| `is_indirect` | bool | 是否为间接跳转/调用 |

### F类：故障敏感性

| 指标 | 类型 | 说明 |
|------|------|------|
| `is_crash_prone` | bool | 是否为易崩溃指令 |
| `crash_prone_type` | string | 易崩溃类型 |

**crash_prone_type 取值**：

| 值 | 说明 |
|----|------|
| `none` | 非易崩溃指令 |
| `mem_read` | 内存读操作 |
| `mem_write` | 内存写操作 |
| `indirect_cf` | 间接控制流 |
| `div` | 除法指令 |

## 使用场景

1. **崩溃分析**：通过崩溃时的指令地址(offset)匹配到该指令的静态特征
2. **故障注入研究**：识别易崩溃指令，分析故障敏感性
3. **程序特征分析**：统计指令类型分布、访存模式等

## 命令行参数

### profile_single.py

| 参数 | 简写 | 默认值 | 说明 |
|------|------|--------|------|
| app_name | - | 必需 | 应用程序名称 |
| --output | -o | 自动生成 | 输出JSON文件路径 |
| --timeout | -t | 3600 | 超时时间(秒) |

### profile_batch.py

| 参数 | 简写 | 默认值 | 说明 |
|------|------|--------|------|
| --all | - | - | 剖析所有应用 |
| --suite | - | - | 剖析指定套件 |
| --apps | - | - | 逗号分隔的应用列表 |
| --exclude | - | - | 要排除的应用列表 |
| --parallel | -p | 1 | 并行任务数(1-4) |
| --timeout | -t | 3600 | 超时时间(秒) |
| --max-retries | -r | 2 | 最大重试次数 |

## 依赖

### 必需
- Python 3.6+
- 已编译的 instruction_profiler Pin工具

### 可选
- tqdm - 进度条显示

```bash
# 安装可选依赖
pip install tqdm
```

## 与现有架构的关系

本脚本复用以下共享组件：
- `config.py` - 配置管理
- `app_config.py` - 应用配置加载器
- `applications.json` - 应用配置文件

目录结构与 `application/`、`function/` 维度保持一致。

## 注意事项

- 仅分析主程序的可执行段，不分析动态链接库
- 需要程序包含符号信息以获得完整的指令覆盖
- 输出的 offset 是相对于镜像基址的偏移，使用时需要加上运行时基址
- 指令剖析输出文件可能较大，请预留足够的磁盘空间

## 指标汇总表

| 类别 | 指标名 | 类型 | 说明 |
|------|--------|------|------|
| A | offset | string | 相对镜像基址的偏移 |
| A | mnemonic | string | 指令助记符 |
| A | disasm | string | 完整反汇编文本 |
| A | size | int | 指令字节长度 |
| B | category | string | XED指令类别 |
| B | is_arith | bool | 算术指令 |
| B | is_logic | bool | 逻辑指令 |
| B | is_float | bool | 浮点指令 |
| B | is_simd | bool | SIMD指令 |
| B | is_data_move | bool | 数据移动指令 |
| C | explicit_reg_read | array | 显式读寄存器 |
| C | explicit_reg_write | array | 显式写寄存器 |
| C | implicit_reg_read | array | 隐式读寄存器 |
| C | implicit_reg_write | array | 隐式写寄存器 |
| C | uses_flags | bool | 是否使用标志寄存器 |
| D | is_mem_read | bool | 是否读内存 |
| D | is_mem_write | bool | 是否写内存 |
| D | mem_operand_count | int | 内存操作数数量 |
| D | mem_access_mode | string | 内存寻址模式 |
| E | is_branch | bool | 是否为分支 |
| E | is_cond_branch | bool | 是否为条件分支 |
| E | is_call | bool | 是否为函数调用 |
| E | is_ret | bool | 是否为返回 |
| E | is_indirect | bool | 是否为间接跳转 |
| F | is_crash_prone | bool | 是否易崩溃 |
| F | crash_prone_type | string | 崩溃类型 |

## 版本

- **脚本版本**: 1.0
- **instruction_profiler版本**: 1.0
- **依赖**: Intel Pin, instruction_profiler.so
