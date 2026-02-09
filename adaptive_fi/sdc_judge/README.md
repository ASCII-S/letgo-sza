# SDC判定模块

SDC判定模块用于生成应用Golden输出，并进行SDC（静默数据损坏）判定。

## 模块结构

```
sdc_judge/
├── __init__.py              # 模块导出
├── config_manager.py        # 配置管理器 - 读取applications.json
├── golden/                  # Golden生成相关
│   ├── __init__.py
│   ├── app_executor.py      # 应用执行器 - 执行应用程序
│   ├── output_capturer.py   # 输出捕获器 - 捕获并保存输出
│   ├── golden_generator.py  # Golden生成器 - 协调器
│   ├── generate_single_golden.py # 单应用Golden生成脚本
│   └── generate_all_goldens.py   # 批量Golden生成脚本
├── judge/                   # SDC判断相关
│   ├── __init__.py
│   ├── sdc_comparator.py    # SDC比较器 - SDC判定逻辑
│   ├── sdc_judge.py         # SDC判定器 - 批量SDC判定核心
│   └── batch_judge_sdc.py   # 单应用批量SDC判定脚本
├── batch_judge_all_apps.py  # 所有应用批量SDC判定脚本（Python）
├── batch_sdc_judge.sh       # 批量SDC判定脚本（Bash，功能完整）
├── quick_sdc_judge.sh       # 快速SDC判定脚本（Bash，一键运行）
├── golden_outputs/          # Golden输出存储目录
└── README.md                # 本文件
```

## 快速开始

### 生成单个应用的Golden输出

```bash
cd /home/tongshiyu/pin/source/tools/letgo/adaptive_fi

# 生成backprop的Golden
python -m sdc_judge.golden.generate_single_golden backprop

# 强制重新生成hotspot
python -m sdc_judge.golden.generate_single_golden hotspot --force

# 查看应用信息
python -m sdc_judge.golden.generate_single_golden bfs --info

# 列出所有可用应用
python -m sdc_judge.golden.generate_single_golden --list-apps
```

### 批量生成所有应用的Golden输出

```bash
# 生成所有应用
python -m sdc_judge.golden.generate_all_goldens

# 仅生成rodinia套件
python -m sdc_judge.golden.generate_all_goldens --suites rodinia

# 生成多个套件
python -m sdc_judge.golden.generate_all_goldens --suites rodinia mantevo

# 强制重新生成
python -m sdc_judge.golden.generate_all_goldens --force

# 列出所有套件
python -m sdc_judge.golden.generate_all_goldens --list-suites
```

### 批量SDC判定

#### 对单个应用进行SDC判定

```bash
# 对bicg/adaptive所有实验进行SDC判定
python -m sdc_judge.judge.batch_judge_sdc /path/to/TargetedBenchmarkResult/bicg/adaptive bicg

# 仅对log_0到log_99进行判定
python -m sdc_judge.judge.batch_judge_sdc /path/to/result/hotspot/adaptive hotspot --range 0-99

# 强制重新判定已有结果，并显示详细输出
python -m sdc_judge.judge.batch_judge_sdc /path/to/result/lu/adaptive lu --force --verbose
```

#### 对所有应用批量进行SDC判定

**方式1：使用 Bash 脚本（推荐）**

```bash
cd /home/tongshiyu/pin/source/tools/letgo/adaptive_fi/sdc_judge

# 快速一键运行（后台模式）
./quick_sdc_judge.sh

# 完整功能脚本
./batch_sdc_judge.sh                        # 对所有应用判定
./batch_sdc_judge.sh backprop hotspot       # 仅判定指定应用
./batch_sdc_judge.sh --force                # 强制重新判定
./batch_sdc_judge.sh --range 0-99           # 指定日志范围
./batch_sdc_judge.sh --background           # 后台运行
./batch_sdc_judge.sh --verbose              # 详细输出
./batch_sdc_judge.sh --help                 # 查看完整帮助
```

**方式2：使用 Python 命令**

```bash
# 对所有应用进行SDC判定
python -m sdc_judge.batch_judge_all_apps /path/to/TargetedBenchmarkResult

# 只处理特定应用
python -m sdc_judge.batch_judge_all_apps /path/to/TargetedBenchmarkResult --apps backprop hotspot bfs

# 指定日志范围并强制重新判定
python -m sdc_judge.batch_judge_all_apps /path/to/TargetedBenchmarkResult --range 0-99 --force

# 详细输出模式
python -m sdc_judge.batch_judge_all_apps /path/to/TargetedBenchmarkResult --verbose
```

## 工作流程

### 完整实验流程

#### 方案1：单个应用流程

```bash
# 步骤1：运行自适应注错实验（只记录崩溃）
python adaptive_fi_wrapper.py

# 步骤2：实验结束后，运行批量SDC判定
python -m sdc_judge.judge.batch_judge_sdc \
    /path/to/TargetedBenchmarkResult/bicg/adaptive \
    bicg

# 步骤3：收集日志（自动关联SDC结果）
python scripts/collect_logs.py \
    /path/to/TargetedBenchmarkResult/bicg/adaptive
```

#### 方案2：批量处理所有应用

```bash
# 步骤1：运行多个应用的自适应注错实验
# （对每个应用分别运行 adaptive_fi_wrapper.py）

# 步骤2：对所有应用批量进行SDC判定
python -m sdc_judge.batch_judge_all_apps \
    /path/to/TargetedBenchmarkResult

# 步骤3：批量收集所有应用的日志
python scripts/batch_collect_logs.py \
    /path/to/TargetedBenchmarkResult
```

### 实验目录结构

```
TargetedBenchmarkResult/{app}/adaptive/
├── log/
│   ├── log_0                      # 实验日志
│   ├── log_1
│   ├── inject_info_0.txt          # 注错信息
│   └── inject_info_1.txt
├── sdcout/
│   ├── log_0_output.dat           # 程序输出
│   └── log_1_output.dat
├── sdcresult/                     # SDC判定结果
│   ├── sdc_0.json
│   └── sdc_1.json
└── adaptive_fi_result.json
```

### SDC结果JSON格式

`sdcresult/sdc_N.json` 文件格式：

```json
{
  "log_index": 5,
  "is_sdc": true,
  "message": "Compare within tolerance: False",
  "tolerance": 0.1,
  "method": "common",
  "max_error": 0.15,
  "test_output_path": "/path/to/sdcout/log_5_output.dat",
  "golden_output_path": "/path/to/golden_outputs/rodinia/hotspot/output.txt",
  "timestamp": "2026-02-07T10:30:45.123456",
  "app_name": "hotspot"
}
```

## 工作目录说明

**重要**：应用执行时的工作目录设置

- **默认行为**：在应用二进制文件所在目录执行
- **原因**：某些应用（如HPL）需要在其安装目录下找到配置文件（如`HPL.dat`）
- **输出文件**：应用生成的输出文件（指定为相对路径的）会保存在应用目录中，然后被复制到Golden目录

**示例**：
- HPL应用：`/home/tongshiyu/programs/hpl-2.3/testing/xhpl` → 工作目录为 `/home/tongshiyu/programs/hpl-2.3/testing/`
- hotspot应用：`/home/tongshiyu/programs/rodinia-master/openmp/hotspot/hotspot` → 工作目录为 `/home/tongshiyu/programs/rodinia-master/openmp/hotspot/`

### 自定义工作目录

如果应用需要特定的工作目录（非二进制所在目录），可以在 `applications.json` 中为应用添加 `"working_dir"` 字段：

```json
"hpl": {
  "binpath": "/home/tongshiyu/programs/hpl-2.3/testing/xhpl",
  "args": [""],
  "working_dir": "/home/tongshiyu/pin/source/tools/letgo/letgo_Target/letgo_Target1/"
}
```

这样HPL应用会在指定的工作目录中执行，能够找到该目录中的`HPL.dat`等配置文件。

## Golden输出目录结构

生成完成后的目录结构：

```
golden_outputs/
├── rodinia/
│   ├── backprop/
│   │   ├── metadata.json        # 元数据
│   │   ├── stdout.txt           # 标准输出
│   │   └── [output files]       # 应用生成的输出文件
│   ├── hotspot/
│   │   ├── metadata.json
│   │   ├── stdout.txt
│   │   └── output.txt           # 应用输出文件
│   └── ...
├── mantevo/
│   ├── HPCCG/
│   │   ├── metadata.json
│   │   └── stdout.txt           # MPI应用仅stdout
│   ├── miniMD/
│   │   ├── metadata.json
│   │   └── stdout.txt
│   └── ...
├── npb/
└── polybench/
```

## 模块使用（Python API）

### 基本用法

```python
from sdc_judge import GoldenGenerator

# 初始化
generator = GoldenGenerator()

# 生成单个应用
golden = generator.generate_single('backprop')
print(golden.golden_dir)  # Golden目录路径
print(golden.outputs)      # 输出文件映射

# 生成所有应用
results = generator.generate_all()

# 生成特定套件
results = generator.generate_all(suites=['rodinia', 'mantevo'])

# 强制重新生成
golden = generator.generate_single('backprop', force_regenerate=True)
```

### 使用配置管理器

```python
from sdc_judge import ConfigManager

# 初始化
config = ConfigManager()

# 获取应用配置
app_config = config.get_app('backprop')
print(app_config.binpath)
print(app_config.args)
print(app_config.compare_method)  # 比较方法
print(app_config.tolerance)       # 容差

# 获取套件的所有应用
rodinia_apps = config.get_suite_apps('rodinia')

# 列出所有应用
all_apps = config.get_all_apps()
```

### 执行应用程序

```python
from sdc_judge import ApplicationExecutor, ConfigManager
import tempfile

# 初始化
config = ConfigManager()
executor = ApplicationExecutor()

# 获取应用配置
app_config = config.get_app('backprop')

# 创建临时工作目录并执行
with tempfile.TemporaryDirectory() as work_dir:
    result = executor.execute(app_config, work_dir)
    print(result.stdout)
    print(result.returncode)
    print(result.output_files)
```

### SDC比较

```python
from sdc_judge import SDCComparator

# 初始化
comparator = SDCComparator()

# 比较输出
result = comparator.compare(
    test_output='/path/to/test.txt',
    golden_output='/path/to/golden.txt',
    method='hotspot',
    tolerance=1e-6
)

print(result.is_match)  # 是否匹配
print(result.message)   # 结果消息
print(result.method)    # 比较方法
```

### SDC判定（批量）

```python
from sdc_judge import SDCJudge, SDCJudgeResult

# 初始化
judge = SDCJudge()

# 判定单个输出
result = judge.judge(
    test_output='/path/to/sdcout/log_5_output.dat',
    golden_output='/path/to/golden_outputs/rodinia/hotspot/output.txt',
    app_name='hotspot',
    log_index=5
)

print(result.is_sdc)      # True=SDC, False=Masked
print(result.message)     # 详细比较信息
print(result.tolerance)   # 容差
print(result.method)      # 比较方法

# 保存结果为JSON
judge.save_result(result, '/path/to/sdcresult/')
# 生成文件：/path/to/sdcresult/sdc_5.json
```

### 批量SDC判定

```python
from sdc_judge.judge.batch_judge_sdc import BatchSDCJudge

# 初始化
batch_judge = BatchSDCJudge(
    one_batch_folder='/path/to/TargetedBenchmarkResult/bicg/adaptive',
    app_name='bicg'
)

# 运行批量判定
batch_judge.run(
    log_range=(0, 99),  # 可选：指定范围
    force=False,        # 是否强制重新判定
    verbose=True        # 详细输出
)

# 查看统计
print(f"SDC: {batch_judge.sdc_count}")
print(f"Masked: {batch_judge.masked_count}")
print(f"错误: {batch_judge.error_count}")
```

## 支持的应用类型

### 完全比较（strong）
- bfs, backprop, nn, kmeans, particlefilter
- 输出必须完全相同

### 特定格式比较
- **hotspot, hotspot3D**: CSV格式，支持容差比较
- **miniMD**: 提取特定行数据比较
- **miniFE**: 提取Final Resid Norm值比较
- **HPCCG**: 提取Final residual值比较
- **lu**: LU矩阵分解比较

### PolyBench应用
- 2mm, fdtd-2d, bicg, correlation, gesummv, syr2k, gaussian, convolution, mvt
- 使用polybench_output_validator库进行相对误差比较

### 通用比较（common）
- 其他应用，使用numpy数组容差比较

## 配置文件

应用配置来自 `applications.json`，包含：
- **binpath**: 应用二进制文件路径
- **args**: 命令行参数列表
- **pc_start/pc_end**: 指令范围（可选）
- **is_mpi**: 是否MPI应用（可选）
- **output_type**: 输出类型（可选，见下文）
- **working_dir**: 工作目录（可选）

配置管理器自动推断：
- **output_files**: 输出文件列表（从args提取）
- **needs_stdout**: 是否捕获stdout
- **needs_stderr**: 是否捕获stderr
- **tolerance**: 容差值（根据应用类型）
- **compare_method**: 比较方法（根据应用类型）

### output_type 配置

用于指定应用的输出类型，决定 Golden 生成时捕获哪种输出：

| output_type | 说明 | 示例应用 |
|-------------|------|----------|
| `"stdout"` | 捕获标准输出（默认） | 大多数应用 |
| `"stderr"` | 捕获标准错误输出 | PolyBench 套件 |
| `"file"` | 仅捕获指定的输出文件 | hotspot 等 |

**配置示例**：

```json
"2mm": {
  "binpath": "/path/to/2mm_ref",
  "args": [],
  "output_type": "stderr"
}
```

**说明**：PolyBench 套件的应用通过 stderr 输出计算结果（`==BEGIN DUMP_ARRAYS==`），因此需要配置 `"output_type": "stderr"`。

## 容差配置

不同应用的默认容差：

| 应用 | 容差 |
|------|------|
| hotspot | 1e-6 |
| hotspot3D | 1e-2 |
| lu | 1e-4 |
| miniMD | 1e-6 |
| miniFE | 1e-6 |
| HPCCG | 1e-6 |
| PolyBench应用 | 0.1 (相对误差) |
| 其他应用 | 0.1 |

## MPI应用

MPI应用（HPCCG, miniFE, miniMD, miniAMR）通过以下方式处理：
- 使用 `mpirun -np 1` 启动
- 输出到stdout（不产生文件输出）
- 自动保存stdout.txt

## 错误处理

脚本会自动处理以下错误：
- 应用不存在
- 应用执行失败或超时
- 输出文件缺失
- 数据格式错误

使用 `--force` 标志可以强制重新生成已存在的Golden。

## 扩展

### 添加新应用

在 `applications.json` 中添加应用配置，模块会自动识别：

```json
"new_app": {
  "binpath": "/path/to/binary",
  "args": ["arg1", "arg2", "output.txt"],
  "pc_start": "400000",
  "pc_end": "500000",
  "is_mpi": false
}
```

### 添加新的比较方法

在 `sdc_comparator.py` 中添加新的比较函数，然后在 `COMPARE_METHOD_MAP` 中注册。

## 性能建议

- 在后台运行批量生成：`nohup python -m sdc_judge.golden.generate_all_goldens &`
- 对于大型应用，增加 `--timeout` 时间
- 第一次生成所有Golden可能需要较长时间（取决于应用数量和执行时间）

## 故障排除

### Golden生成失败

1. 检查应用二进制文件是否存在：`ls <binpath>`
2. 检查应用参数是否正确：`python -m sdc_judge.golden.generate_single_golden <app> --info`
3. 增加超时时间：`--timeout 600`
4. 检查stdout和stderr输出

### SDC判定失败

1. 确保Golden输出文件完整
2. 检查比较方法是否正确：`python -m sdc_judge.golden.generate_single_golden <app> --info`
3. 调整tolerance容差值
4. 对于崩溃实验（无sdcout输出），会被正确标记为错误而非Masked

### 批量判定问题

1. 确保实验目录结构正确（包含log/和sdcout/文件夹）
2. 使用 `--verbose` 查看详细输出
3. 使用 `--range` 限制判定范围进行调试

## 许可证

与adaptive_fi项目相同
