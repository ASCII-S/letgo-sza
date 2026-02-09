# SDC 判定模块 (judge)

SDC 判定模块用于判断注错实验的输出是否为 SDC（静默数据损坏）。

## 目录结构

```
judge/
├── __init__.py                 # 模块导出
├── sdc_judge.py                # SDC 判定器核心
├── sdc_comparator.py           # SDC 比较器（协调器）
├── output_extractor.py         # 输出提取器
├── batch_judge_sdc.py          # 批量判定脚本
└── comparators/                # 比较方法模块
    ├── __init__.py             # 导出所有比较器
    ├── base.py                 # 基类和通用比较器
    ├── numeric.py              # 数值比较器（hotspot, lu）
    ├── mantevo.py              # Mantevo 套件比较器
    └── polybench.py            # PolyBench 套件比较器
```

## 核心组件

### 1. OutputExtractor (output_extractor.py)

**功能**：根据应用的 `output_type` 从正确位置提取程序输出。

| output_type | 数据来源 | 说明 |
|-------------|----------|------|
| `stdout` | `log/log_N` | 从日志文件中提取 "程序输出 (stdout):" 部分 |
| `stderr` | `log/log_N` | 从日志文件中提取 "程序错误输出 (stderr):" 部分 |
| `file` | `sdcout/log_N_output.*` | 直接使用 sdcout 目录中的输出文件 |

**使用示例**：

```python
from sdc_judge.judge.output_extractor import OutputExtractor

extractor = OutputExtractor()

# 提取 2mm 应用 log_0 的输出（stderr 类型）
result = extractor.extract(
    app_name='2mm',
    log_index=0,
    experiment_dir='/path/to/2mm/adaptive'
)

print(result.content)      # 输出内容或临时文件路径
print(result.output_type)  # 'stderr'
print(result.source)       # 'log'
print(result.error)        # None 或错误信息
```

### 2. SDCComparator (sdc_comparator.py)

**功能**：协调器模式，整合所有比较器，提供统一的比较接口。

**支持的比较方法**：

| 方法 | 适用应用 | 说明 |
|------|----------|------|
| `strong` | bfs, backprop, nn, kmeans, particlefilter | 二进制完全比较 |
| `common` | 大多数应用（默认） | numpy 数值容差比较 |
| `hotspot` | hotspot, hotspot3D | CSV 格式温度数据比较 |
| `lu` | lu | LU 矩阵分解验证 |
| `miniMD` | miniMD | 提取 Timestep 数据比较 |
| `miniFE` | miniFE | 提取 Final Resid Norm 比较 |
| `HPCCG` | HPCCG | 提取 Final residual 比较 |
| `polybench` | 2mm, bicg, correlation 等 | PolyBench 相对误差比较 |

**使用示例**：

```python
from sdc_judge.judge.sdc_comparator import SDCComparator

comparator = SDCComparator()

# 比较输出
result = comparator.compare(
    test_output='/path/to/test_output.txt',
    golden_output='/path/to/golden_output.txt',
    method='polybench',
    tolerance=0.1
)

print(result.is_match)   # True=匹配（Masked），False=不匹配（SDC）
print(result.message)    # 详细消息
print(result.max_error)  # 最大误差
```

### 3. SDCJudge (sdc_judge.py)

**功能**：SDC 判定器，整合配置管理、比较器，提供完整的判定流程。

**使用示例**：

```python
from sdc_judge.judge.sdc_judge import SDCJudge

judge = SDCJudge()

# 判定单个输出
result = judge.judge(
    test_output='/path/to/test_output.txt',
    golden_output='/path/to/golden_output.txt',
    app_name='hotspot',
    log_index=5
)

print(result.is_sdc)      # True=SDC，False=Masked
print(result.tolerance)   # 使用的容差
print(result.method)      # 比较方法
print(result.max_error)   # 最大误差

# 保存结果
judge.save_result(result, '/path/to/sdcresult/')
# 生成文件：/path/to/sdcresult/sdc_5.json
```

### 4. comparators/ 模块

比较器采用策略模式，每个比较器继承 `BaseComparator` 基类：

```python
from sdc_judge.judge.comparators import (
    CompareResult,      # 比较结果数据类
    BaseComparator,     # 基类
    StrongComparator,   # 精确比较
    CommonComparator,   # 通用数值比较
    HotspotComparator,  # Hotspot 比较
    LUComparator,       # LU 分解比较
    MiniMDComparator,   # miniMD 比较
    MiniFEComparator,   # miniFE 比较
    HPCCGComparator,    # HPCCG 比较
    PolybenchComparator # PolyBench 比较
)

# 直接使用比较器
comparator = PolybenchComparator()
result = comparator.compare(test_output, golden_output, tolerance=0.1)
```

## 命令行使用

### 批量 SDC 判定

```bash
cd /home/tongshiyu/pin/source/tools/letgo/adaptive_fi

# 对 stderr 类型应用（如 2mm）进行判定
python -m sdc_judge.judge.batch_judge_sdc \
    /path/to/TargetedBenchmarkResult/2mm/adaptive \
    2mm

# 对 file 类型应用（如 backprop）进行判定
python -m sdc_judge.judge.batch_judge_sdc \
    /path/to/TargetedBenchmarkResult/backprop/adaptive \
    backprop

# 指定日志范围
python -m sdc_judge.judge.batch_judge_sdc \
    /path/to/result/hotspot/adaptive \
    hotspot \
    --range 0-99

# 强制重新判定并显示详细输出
python -m sdc_judge.judge.batch_judge_sdc \
    /path/to/result/lu/adaptive \
    lu \
    --force --verbose
```

### 命令行参数

| 参数 | 说明 |
|------|------|
| `one_batch_folder` | 实验数据文件夹路径 |
| `app_name` | 应用名称 |
| `--range`, `-r` | 日志范围，如 `0-99` |
| `--force`, `-f` | 强制重新判定已有结果 |
| `--verbose`, `-v` | 详细输出 |

## 实验目录结构

```
TargetedBenchmarkResult/{app}/adaptive/
├── log/
│   ├── log_0                      # 实验日志（包含 stdout/stderr）
│   ├── log_1
│   ├── inject_info_0.txt          # 注错信息
│   └── inject_info_1.txt
├── sdcout/                        # file 类型应用的输出
│   ├── log_0_output.dat
│   └── log_1_output.dat
└── sdcresult/                     # SDC 判定结果
    ├── sdc_0.json
    └── sdc_1.json
```

## SDC 结果 JSON 格式

`sdcresult/sdc_N.json` 文件格式：

```json
{
  "log_index": 5,
  "is_sdc": true,
  "message": "PolyBench 比较: 失败, 最大相对误差=3.74e-01, 不匹配元素=1/384",
  "tolerance": 0.1,
  "method": "polybench",
  "max_error": 0.374,
  "test_output_path": "/tmp/sdc_judge_xxx/log_5_stderr.txt",
  "golden_output_path": "/path/to/golden_outputs/polybench/2mm/stdout.txt",
  "timestamp": "2026-02-08T21:19:54.293856",
  "app_name": "2mm"
}
```

## 日志解析规则

对于 `stdout`/`stderr` 类型的应用，OutputExtractor 从日志文件中解析输出：

**日志格式**：
```
程序输出 (stdout):
============================================================
[stdout 内容]
程序错误输出 (stderr):
============================================================
[stderr 内容]
```

- `stdout` 内容在 "程序输出 (stdout):" 和 "程序错误输出 (stderr):" 之间
- `stderr` 内容在 "程序错误输出 (stderr):" 之后

## 扩展比较器

添加新的比较方法：

1. 在 `comparators/` 目录创建新文件或在现有文件中添加类
2. 继承 `BaseComparator` 基类
3. 实现 `name` 属性和 `compare()` 方法
4. 在 `comparators/__init__.py` 中导出
5. 在 `sdc_comparator.py` 的 `SDCComparator.__init__()` 中注册

```python
# comparators/custom.py
from .base import BaseComparator, CompareResult

class CustomComparator(BaseComparator):
    @property
    def name(self) -> str:
        return "custom"

    def compare(self, test_output, golden_output, tolerance=0.1) -> CompareResult:
        # 实现比较逻辑
        ...
        return CompareResult(
            is_match=True,
            message="比较通过",
            method=self.name,
            max_error=0.0
        )
```

## 容差配置

不同应用的默认容差（在 `config_manager.py` 中配置）：

| 应用 | 容差 | 说明 |
|------|------|------|
| hotspot | 1e-6 | 绝对误差 |
| hotspot3D | 1e-2 | 绝对误差 |
| lu | 1e-4 | 绝对误差 |
| miniMD, miniFE, HPCCG | 1e-6 | 绝对误差 |
| PolyBench 应用 | 0.1 | 相对误差 |
| 其他应用 | 0.1 | 绝对误差 |

## 错误处理

- **日志文件不存在**：返回错误，跳过该实验
- **无法提取输出**：返回错误（可能是崩溃实验）
- **Golden 不存在**：抛出异常，需先生成 Golden
- **比较失败**：返回错误信息，记录详细原因
