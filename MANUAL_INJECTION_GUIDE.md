# 手动指令注错功能使用指南

## 功能概述

手动指令注错功能允许你在 `configure.py` 中直接指定要注错的指令位置和次数，无需修改自动生成的 pool 文件。

## 配置方法

### 1. 启用手动注错模式

在 `configure.py` 中设置：

```python
# 确保是 targeted 模式
inject_random_or_targeted = "targeted"

# 启用手动指令注错
use_manual_instructions = True
```

### 2. 配置手动注错指令

在 `configure.py` 中的 `manual_instructions` 列表中添加配置：

```python
manual_instructions = [
    ["rbp", "", "0x4026b1", 12474, 100],  # 注错 100 次，max_iteration=12474
    ["rbp", "", "0x402605", 12096, 50],   # 注错 50 次，max_iteration=12096
    ["rdx", "", "0x402678"],              # 注错 1 次（使用默认值）
]
```

### 3. 参数说明

每条配置格式：`[regmem, reg, pc_hex, max_iteration(可选), repeat_count(可选)]`

- **regmem**: 内存操作数寄存器（如 `"rbp"`），如果没有则填 `""`
- **reg**: 目标寄存器（如 `"rax"`），如果没有则填 `""`
- **pc_hex**: 指令地址，支持以下格式：
  - 带 `0x` 前缀：`"0x4026b1"`
  - 不带前缀：`"4026b1"`
- **max_iteration**: 该指令在程序中的最大执行次数，默认为 1023
  - 可以从 catalog 文件的最后一列获取准确值
  - iteration 不会超过这个值
- **repeat_count**: 对该位置重复注错的次数，默认为 1
  - `iteration` 会自动按顺序分配：0, 1, 2, ..., min(max_iteration, repeat_count-1)
  - 例如 `repeat_count=100`，会生成 iteration 0~99 的 100 条注错配置

## 工作原理

### iteration 的含义

`iteration` 表示：**在程序执行过程中，该 PC 地址第几次被执行时触发注错**

例如，某条指令在程序中被执行 1000 次：
- `iteration=0` → 在第 1 次执行时注错
- `iteration=5` → 在第 6 次执行时注错
- `iteration=999` → 在第 1000 次执行时注错

### 自动分配 iteration

当你指定 `repeat_count=100` 时，系统会自动生成：
```
rbp,,4203185,0
rbp,,4203185,1
rbp,,4203185,2
...
rbp,,4203185,99
```

这样每次注错都在**不同的执行时刻**，避免重复。

## 使用示例

### 示例 1：对单个指令注错多次

```python
manual_instructions = [
    ["rbp", "", "0x4026b1", 12474, 100],  # 对该指令注错 100 次，max_iteration=12474
]
```

生成的 pool 包含 100 条配置，iteration 从 0 到 99。

### 示例 2：对多个指令分别注错

```python
manual_instructions = [
    ["rbp", "", "0x4026b1", 12474, 50],   # 指令 1：注错 50 次
    ["rax", "", "0x402605", 12096, 30],   # 指令 2：注错 30 次
    ["rdx", "", "0x402678", 12096, 20],   # 指令 3：注错 20 次
]
```

总共生成 100 条注错配置。

### 示例 3：只注错一次

```python
manual_instructions = [
    ["rbp", "", "0x4026b1"],  # 省略 max_iteration 和 repeat_count，使用默认值
]
```

生成 1 条配置，iteration=0，max_iteration=1023。

### 示例 4：指定 max_iteration 但只注错一次

```python
manual_instructions = [
    ["rbp", "", "0x4026b1", 12474],  # 只指定 max_iteration，repeat_count 默认为 1
]
```

生成 1 条配置，iteration=0，max_iteration=12474。

## 如何获取指令地址

### 方法 1：从 catalog 文件获取

运行一次自动目标注错，查看生成的 `mov_catalog.csv`：

```bash
head -10 TargetedBenchmarkResult/fdtd-2d/mov/mov_catalog.csv
```

输出示例：
```
rbp,,4026b1,MOV,mov eax, dword ptr [rbp-0x1c],12474
rbp,,402605,MOV,mov eax, dword ptr [rbp-0x24],12096
rdx,,402678,MOVSD_XMM,movsd xmm0, qword ptr [rdx+rax*8],12096
```

从中选择你想注错的指令地址（第 3 列）。

### 方法 2：使用 objdump 反汇编

```bash
objdump -d /path/to/binary | grep "mov"
```

## 运行流程

1. 在 `configure.py` 中配置 `manual_instructions`
2. 设置 `use_manual_instructions = True`
3. 运行 `python letgo_wrapper.py`
4. 系统会自动生成 `manual_pool.csv` 并使用它进行注错

## 注意事项

1. **手动模式优先级高于自动模式**：启用手动模式后，不会生成 catalog 和自动 pool
2. **iteration 范围**：确保 iteration 不超过该指令的实际执行次数（catalog 最后一列）
3. **实验次数**：`configure.numFI` 应该 ≥ 手动配置的总注错次数
4. **文件覆盖**：每次运行都会重新生成 `manual_pool.csv`

## 切换回自动模式

只需在 `configure.py` 中设置：

```python
use_manual_instructions = False
```

系统会自动回退到原有的自动生成 pool 流程。
