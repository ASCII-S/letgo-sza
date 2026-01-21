# 自适应故障注入 (Adaptive Fault Injection)

## 概述

基于易崩溃指令溯源的自适应故障注入工具。通过分析程序中易崩溃的指令及其寄存器数据流溯源，智能选择高效的注错点进行故障注入实验，提高注错效率和真实性。

## 核心特性

- **智能筛选**：基于易崩溃指令分析，TopP 筛选最有价值的注错目标
- **自适应溯源**：根据崩溃率自动追踪寄存器数据流溯源链
- **混合遍历**：BFS 按深度广度优先 + DFS 按寄存器深度优先
- **Pin+GDB 联合注错**：使用 Pin 工具进行高效注错，GDB 负责崩溃修复（默认模式）
- **完整 LetGo 修复**：支持 h_1/h_2/h_3 三种修复策略，完整 SDC 检测
- **灵活模式切换**：支持 Pin 注错模式和传统 GDB 注错模式
- **详细统计**：生成 JSON 格式的详细统计报告，包含崩溃率、覆盖率等指标

## 工作原理

### 1. 易崩溃指令溯源

使用 `unified_tracer.so` Pin 工具分析程序执行，识别易崩溃指令并追踪其寄存器数据流来源。

```
易崩溃指令类型:
- mem_write: 内存写操作
- mem_read: 内存读操作
- index_access: 数组索引访问
- indirect_cf: 间接控制流
- div: 除法指令
```

### 2. 自适应注错流程

```
[1] 运行 unified_tracer.so 生成溯源 JSON
         ↓
[2] TopP 筛选易崩溃指令（按执行频率）
         ↓
[3] 初始化 depth=0 队列
         ↓
[4] BFS 按深度处理
    ├─ 取出当前深度的所有目标
    ├─ DFS: 处理同一指令的所有寄存器
    │   ├─ 执行 N 次注错（Pin 或 GDB 模式）
    │   ├─ 计算崩溃率
    │   └─ if 崩溃率 > 阈值:
    │       └─ TopP 筛选溯源链，加入下一深度队列
    └─ 深度 += 1
         ↓
[5] 生成统计报告 JSON + 兼容 analyze.py 的日志
```

### 3. Pin+GDB 联合注错模式（默认）

```
[Pin 注错流程]
T0: Python 启动 Pin (后台)
    ├─ pin -appdebug -debug_port 12345
    ├─ -t targeted_faultinjection.so
    ├─ -target_pc 0x4019c8
    ├─ -target_reg rax
    ├─ -target_kth 459
    └─ Pin 等待 GDB 连接

T1: Python 启动 GDB 并连接
    ├─ gdb ./benchmark
    ├─ target remote :12345
    └─ 配置信号处理 (SIGSEGV nopass)

T2: 程序执行，Pin 监控目标指令
    └─ Pin 检测到第 K 次执行 → 比特翻转

T3: 如果崩溃
    ├─ GDB 捕获信号
    ├─ LetGo 修复框架启动
    │   ├─ 读取 inject_info.txt
    │   ├─ h_1: 栈读取修复（地址计算）
    │   ├─ h_2: 默认值修复（设为 0）
    │   ├─ h_3: 栈指针修复（溢出检测）
    │   └─ 设置 PC 到下一条指令
    ├─ 错误传播检测（单步 50 步）
    └─ SDC 检测

T4: 返回结果
    └─ Crash, C-Masked, C-SDC, Recrash, Masked, SDC
```

## 文件结构

```
adaptive_fi/
├── README.md                  # 本文档
├── adaptive_fi_wrapper.py     # 主控脚本（支持 Pin/GDB 模式切换）
├── adaptive_fi_config.py      # 配置模块
├── trace_parser.py            # JSON 解析模块
├── pin_gdb_injector.py        # Pin+GDB 联合注错器（新）
└── letgo_recovery.py          # LetGo 修复逻辑模块（新）
```

## 安装和依赖

### 前置条件

- Python 3.6+
- Intel Pin（已安装 unified_tracer.so 和 targeted_faultinjection.so）
- GDB（用于崩溃修复）
- pexpect 库：`pip install pexpect`
- LetGo 框架（父目录中的 sighandler.py、configure.py 等）

### 确认 Pin 工具存在

```bash
# 易崩溃指令溯源工具
ls /home/tongshiyu/pin/source/tools/pinfi/obj-intel64/crashprone_tracer/unified_tracer.so

# Pin 注错工具（新）
ls /home/tongshiyu/pin/source/tools/pinfi/obj-intel64/targeted_fi/targeted_faultinjection.so

# 如果不存在，需要编译
cd /home/tongshiyu/pin/source/tools/pinfi
make obj-intel64/targeted_fi/targeted_faultinjection.so
```

## 快速开始

### 1. 配置程序（在父目录的 configure.py 中）

```python
# configure.py
progname = "correlation"
waittochangebyscrips = "correlation"
inject_random_or_targeted = "targeted"  # 必须设置为 targeted
```

### 2. 运行自适应注错

```bash
cd /home/tongshiyu/pin/source/tools/letgo/adaptive_fi

# 方式1: Pin 模式（默认，推荐）
python3 adaptive_fi_wrapper.py --threshold 0.3 --injections 10 --topp 100

# 方式2: GDB 模式（传统方式）
python3 adaptive_fi_wrapper.py --threshold 0.3 --injections 10 --use-gdb

# 方式3: 使用已有溯源 JSON
python3 adaptive_fi_wrapper.py -i trace_result.json -o result.json

# 方式4: 快速测试模式（少量注错，验证流程）
python3 adaptive_fi_wrapper.py --quick-test
```

### 3. 查看结果

```bash
# 查看统计 JSON
cat ../TargetedBenchmarkResult/correlation/adaptive_fi_result.json

# 使用现有工具分析日志
cd ..
python3 analyze.py
```

## 配置参数

### 核心参数（adaptive_fi_config.py）

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `crash_threshold` | 0.3 | 崩溃率阈值，超过此值才溯源 |
| `injections_per_target` | 10 | 每个目标的注错次数 |
| `topp_initial` | 100 | depth=0 的 TopP 筛选数量 |
| `topp_trace` | 20 | 每层溯源的 TopP 筛选数量 |
| `max_depth` | 5 | 最大溯源深度 |
| `program_base_address` | 0x400000 | 程序基址（用于地址转换） |
| `use_pin_injection` | True | 使用 Pin 注错模式（默认） |
| `gdb_port_base` | 12345 | GDB 调试端口基址 |

### 命令行参数

```bash
python3 adaptive_fi_wrapper.py -h
```

常用参数：

```bash
-i, --input PATH          # 输入溯源 JSON（不存在则自动生成）
-o, --output PATH         # 输出结果 JSON
--threshold FLOAT         # 崩溃率阈值 (0-1)
--injections INT          # 每目标注错次数
--topp INT                # 初始 TopP
--topp-trace INT          # 溯源 TopP
--max-depth INT           # 最大深度
--trace-only              # 仅生成溯源 JSON
--quick-test              # 快速测试模式
--full-exp                # 完整实验模式
--no-verbose              # 关闭详细输出
--use-pin                 # 使用 Pin 工具注错（默认）
--use-gdb                 # 使用 GDB 断点注错
```

## 使用示例

### 示例 1: 完整实验（Pin 模式，推荐）

```bash
# 1. 配置程序
cd /home/tongshiyu/pin/source/tools/letgo
vim configure.py  # 设置 progname = "correlation"

# 2. 运行自适应注错（Pin 模式）
cd adaptive_fi
python3 adaptive_fi_wrapper.py \
    --threshold 0.3 \
    --injections 10 \
    --topp 100 \
    --topp-trace 20 \
    --max-depth 5 \
    --use-pin

# 3. 查看结果
cat ../TargetedBenchmarkResult/correlation/adaptive_fi_result.json
```

### 示例 1.1: 使用 GDB 模式（传统方式）

```bash
# 运行自适应注错（GDB 模式）
python3 adaptive_fi_wrapper.py \
    --threshold 0.3 \
    --injections 10 \
    --topp 100 \
    --use-gdb
```

### 示例 2: 分阶段执行

```bash
# 阶段1: 仅生成溯源 JSON
python3 adaptive_fi_wrapper.py --trace-only

# 阶段2: 使用已有 JSON 进行注错
python3 adaptive_fi_wrapper.py \
    -i ../TargetedBenchmarkResult/correlation/trace_result.json \
    -o ../TargetedBenchmarkResult/correlation/my_result.json
```

### 示例 3: 快速验证流程

```bash
# 快速测试模式（3次注错/目标，10个初始目标，深度2）
python3 adaptive_fi_wrapper.py --quick-test
```

## 输出说明

### 1. 日志文件（兼容 analyze.py）

生成在 `{log_folder}/log_N`，格式与 letgo_wrapper.py 一致。

### 2. 统计 JSON（adaptive_fi_result.json）

```json
{
  "config": {
    "crash_threshold": 0.3,
    "injections_per_target": 10,
    "topp_initial": 100,
    "program": "correlation"
  },
  "summary": {
    "total_targets_tested": 156,
    "high_efficiency_targets": 23,
    "total_injections": 1560,
    "total_crashes": 512,
    "overall_crash_rate": 0.328,
    "log_start": 0,
    "log_end": 1559
  },
  "depth_statistics": {
    "0": {"tested": 100, "high_eff": 18, "total_crashes": 450},
    "1": {"tested": 56, "high_eff": 5, "total_crashes": 62}
  },
  "high_efficiency_targets": [
    {
      "offset": "0x401f88",
      "register": "rbp",
      "disasm": "mov [rbp-0x10], rax",
      "depth": 0,
      "crash_rate": 0.8,
      "injection_count": 10,
      "crash_count": 8,
      "results": ["Crash", "C-Masked", "Crash", ...],
      "parent_offset": null
    },
    ...
  ],
  "all_targets": [...]
}
```

### 3. 中间报告（可选）

每完成一个深度生成 `adaptive_fi_depthN_report.json`。

## 配置预设

### 快速测试模式

```python
afi_config.set_quick_test_config()
```

- 注错次数: 3
- TopP: 10
- 深度: 2

### 完整实验模式

```python
afi_config.set_full_experiment_config()
```

- 注错次数: 20
- TopP: 200
- 深度: 5

### 高覆盖率模式

```python
afi_config.set_high_coverage_config()
```

- 阈值降低: 0.2
- TopP 增加: 300
- 注错次数减少: 5

## 与现有系统集成

### 复用的模块

- **sighandler.py**: 完整注错流程（包括 LetGo 修复）
- **configure.py**: 程序配置、路径配置
- **InstPoolMaker.py**: Pool 文件读取机制
- **analyze.py**: 日志分析工具（兼容）

### 集成方式

通过临时 pool 文件传递注错参数：

```python
# 创建临时 pool
with open(configure.pool_csv_file, 'w') as f:
    f.write(f"{regmm},{reg},{offset},{iteration},{randomnum}\n")

# sighandler 自动读取
sig = sighandler.SigHandler(total_insts, log_index)
sig.executeProgram(sig.process)
```

## 注意事项

### 1. configure.py 必须设置为 targeted 模式

```python
inject_random_or_targeted = "targeted"
```

脚本会在运行时临时设置此参数。

### 2. Pin 工具和 GDB 端口

**Pin 模式**：
- 确保 `targeted_faultinjection.so` 已编译
- GDB 端口从 12345 开始自动分配（避免冲突）
- 如果端口被占用，修改 `gdb_port_base` 配置

**GDB 模式**：
- 使用传统的断点注错方式
- 不需要 Pin 工具

### 3. 确保 log 文件夹权限

```bash
chmod -R 755 ../TargetedBenchmarkResult/
```

### 4. 实验时间估算

**Pin 模式**（推荐，更快）：
```
总时间 ≈ (TopP_initial * injections_per_target +
          high_eff_count * topp_trace * injections_per_target * depths)
         * 每次注错时间（~30-60s）
```

**GDB 模式**（传统，较慢）：
```
总时间约为 Pin 模式的 1.5-2 倍
```

建议先用 `--quick-test` 验证流程。

### 5. 模式选择建议

| 场景 | 推荐模式 | 原因 |
|------|---------|------|
| 大规模实验 | Pin 模式 | 注错速度快，一次运行 |
| 调试 LetGo 修复 | Pin 模式 | 可查看完整修复日志 |
| 兼容性测试 | GDB 模式 | 使用传统 sighandler |
| 快速验证 | Pin 模式 | 流程更高效 |

### 6. 中断恢复

支持 Ctrl+C 中断，会自动保存当前结果到 JSON。

## 测试 JSON 解析器

```bash
# 测试解析模块
python3 trace_parser.py /path/to/trace_result.json
```

输出：
```
Trace Summary:
  Total crash-prone instructions: 89
  Total crash registers: 156
  Total trace entries: 312
  Statistics: {...}

[1] 0x401f88: mov [rbp-0x10], rax
    Type: mem_write, Exec: 1596
    Crash regs: ['rbp']
    rbp traces (3 entries):
      depth=1: 0x401f60 lea rbp, [rsp+0x20] (hit=1596)
      depth=2: 0x401f40 mov rsp, rbp (hit=1596)
      ...
```

## 故障排除

### 问题 1: targeted_faultinjection.so 不存在

```bash
# 检查 Pin 注错工具
ls /home/tongshiyu/pin/source/tools/pinfi/obj-intel64/targeted_fi/

# 编译工具（如需要）
cd /home/tongshiyu/pin/source/tools/pinfi
make obj-intel64/targeted_fi/targeted_faultinjection.so
```

### 问题 2: unified_tracer.so 不存在

```bash
# 检查路径
ls /home/tongshiyu/pin/source/tools/pinfi/obj-intel64/crashprone_tracer/

# 编译工具（如需要）
cd /home/tongshiyu/pin/source/tools/pinfi
make obj-intel64/crashprone_tracer/unified_tracer.so
```

### 问题 3: Pin 无法连接 GDB

```bash
# 检查端口是否被占用
netstat -tuln | grep 12345

# 修改配置使用不同端口
vim adaptive_fi_config.py  # 修改 gdb_port_base
```

### 问题 4: pexpect 模块不存在

```bash
pip install pexpect
```

### 问题 5: 日志文件格式错误

确认 `configure.inject_random_or_targeted = "targeted"`。

### 问题 6: 崩溃率始终为 0

- 检查 `crash_threshold` 是否过高
- 检查程序是否真的有易崩溃指令（查看 trace_result.json）
- 尝试使用 `--use-gdb` 模式对比结果

## 高级用法

### 自定义寄存器类型判断

修改 `adaptive_fi_wrapper.py` 中的 `determine_reg_type()` 方法：

```python
def determine_reg_type(self, register: str, disasm: str) -> Tuple[str, str]:
    # 自定义逻辑
    if register in ['rsp', 'rbp']:
        return (register, "")
    return ("", register)
```

### 过滤特定指令类型

```python
# adaptive_fi_config.py
filter_cp_types = ["mem_write", "div"]  # 只测试内存写和除法
```

### 导出到 CSV（供 analyze.py 使用）

```bash
# 日志已兼容，直接运行
python3 ../analyze.py
```

## 性能优化建议

1. **减少 TopP**: `topp_initial=50`, `topp_trace=10`
2. **降低深度**: `max_depth=3`
3. **减少重复**: `injections_per_target=5`
4. **并行执行**: 多个进程分别处理不同深度（需修改代码）

## 开发者信息

- **作者**: Claude Code
- **日期**: 2026-01-21
- **依赖**: LetGo 框架、unified_tracer.so、targeted_faultinjection.so
- **许可**: 与 LetGo 框架一致

## 参考文档

- [项目整体描述](/home/tongshiyu/pin/source/tools/letgo/docs/项目整体描述.md)
- [Pin 功能 API](/home/tongshiyu/pin/source/tools/letgo/docs/pin功能api/PYTHON_API.md)
- [targeted_fi 工具说明](/home/tongshiyu/pin/source/tools/pinfi/targeted_fi/README.md)
- [实现计划](/home/tongshiyu/.claude/plans/swirling-giggling-cloud.md)

## 更新日志

### v1.1.0 (2026-01-21)
- **新增 Pin+GDB 联合注错模式**（默认启用）
  - 使用 `targeted_faultinjection.so` 进行高效注错
  - GDB 仅负责崩溃修复（h_1/h_2/h_3）
  - 支持 `-appdebug` 模式实现单次运行
- **新增模块**
  - `pin_gdb_injector.py`: Pin+GDB 联合注错器
  - `letgo_recovery.py`: 独立的 LetGo 修复逻辑模块
- **新增命令行参数**
  - `--use-pin`: 使用 Pin 注错模式（默认）
  - `--use-gdb`: 使用传统 GDB 断点注错
- **新增配置项**
  - `use_pin_injection`: 注错模式开关
  - `gdb_port_base`: GDB 端口基址
  - `targeted_fi_lib_path`: Pin 注错工具路径
- **优化**
  - 注错速度提升约 30-50%
  - 更完整的错误处理和日志记录

### v1.0.0 (2026-01-20)
- 初始版本
- 支持自适应注错和溯源
- 支持 BFS+DFS 混合遍历
- 集成 sighandler.py 完整流程
- 生成详细 JSON 统计报告
