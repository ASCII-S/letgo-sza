# 🎯 自适应故障注入日志收集完整指南

## 目录
1. [快速开始](#快速开始)
2. [脚本说明](#脚本说明)
3. [详细使用](#详细使用)
4. [输出格式](#输出格式)
5. [常见问题](#常见问题)
6. [性能指标](#性能指标)

---

## 快速开始

### 方式1：批量处理所有应用程序（推荐）

```bash
cd /home/tongshiyu/pin/source/tools/letgo/adaptive_fi

# 一键处理所有应用
python batch_collect_logs.py --output-dir ./results --statistics
```

### 方式2：处理单个应用程序

```bash
# 处理backprop应用
python collect_logs.py \
  /home/tongshiyu/pin/source/tools/letgo/TargetedBenchmarkResult/backprop/adaptive \
  --output results/backprop.csv \
  --statistics
```

### 方式3：处理指定的应用程序集合

```bash
# 仅处理 backprop, hpl, kmeans 三个应用
python batch_collect_logs.py \
  --apps backprop hpl kmeans \
  --output-dir ./results
```

---

## 脚本说明

### 核心组件

#### 1. `log_collector/` 模块

**log_parser.py** - 日志解析器
- 支持两种日志格式（旧版GDB、新版Pin+GDB）
- 提取13个关键字段
- 自动格式检测和转换

**csv_generator.py** - CSV生成器  
- DataFrame管理和输出
- 统计摘要计算
- 数据验证

**collector.py** - 收集协调器
- 日志文件扫描
- 批量解析和聚合
- 错误处理和记录

#### 2. `collect_logs.py` - 单应用脚本

处理单个应用程序的日志

#### 3. `batch_collect_logs.py` - 批处理脚本

批量处理 TargetedBenchmarkResult 目录下的所有应用

---

## 详细使用

### 命令行参数详解

#### collect_logs.py

```bash
python collect_logs.py <one_batch_folder> [选项]

位置参数:
  one_batch_folder      实验数据文件夹路径（包含log子文件夹）

可选参数:
  --help, -h            显示帮助信息
  --log-folder PATH     日志文件夹路径（默认：{one_batch_folder}/log）
  --output, -o PATH     输出CSV路径（默认：自动生成）
  --app-name, -n NAME   应用程序名称（用于输出文件名）
  --log-range START-END 日志范围，格式: 0-100
  --verbose, -v         详细输出
  --statistics, -s      显示统计摘要
  --format csv|json     输出格式（默认：csv）
  --no-validate         跳过日志验证（加快速度）
  --save-warnings       保存警告日志到 warnings.log
```

#### batch_collect_logs.py

```bash
python batch_collect_logs.py [选项]

可选参数:
  --help, -h            显示帮助信息
  --base-dir PATH       TargetedBenchmarkResult 基准目录
  --output-dir, -o DIR  输出目录路径（默认：./collected_logs）
  --apps APP1 APP2 ...  指定要处理的应用程序（默认：处理所有）
  --verbose, -v         详细输出
  --statistics, -s      显示统计摘要
  --dry-run             仅列出，不实际执行
```

### 使用示例

#### 示例1：基本使用

```bash
# 处理backprop，显示进度和统计
python collect_logs.py \
  /home/tongshiyu/pin/source/tools/letgo/TargetedBenchmarkResult/backprop/adaptive \
  --verbose --statistics
```

输出：
```
找到 1901 个日志文件
开始解析...
进度: 10/1901
...

日志收集统计摘要
总日志数: 1901
结果分布:
  C-Masked     319 (16.8%)
  Masked      1032 (54.3%)
  Recrash      550 (28.9%)
```

#### 示例2：处理日志范围

```bash
# 只处理前100个日志（快速测试）
python collect_logs.py \
  /path/to/exp/hpl/adaptive \
  --log-range 0-100 \
  --output test_output.csv
```

#### 示例3：处理所有应用并生成报告

```bash
# 批量处理所有应用，显示统计
python batch_collect_logs.py \
  --output-dir ./all_results \
  --statistics \
  --verbose
```

#### 示例4：Dry-run测试

```bash
# 仅列出将要处理的应用，不实际执行
python batch_collect_logs.py --dry-run
```

输出会显示找到的应用程序列表和日志文件统计。

---

## 输出格式

### CSV 列说明

| 列名 | 类型 | 说明 | 示例 |
|------|------|------|------|
| log_index | int | 日志编号 | 0, 10, 100 |
| target_pc_hex | str | 目标PC地址（十六进制） | 0x400d59 |
| target_pc_dec | int | 目标PC地址（十进制） | 4197721 |
| target_register | str | 目标寄存器 | rax, rbp, rsi |
| inject_iteration | int | 注错迭代次数 | 359, 512 |
| inject_bit | int | 注错位位置 | 0-63, None |
| crash_count | int | 崩溃次数 | 0, 1, 2+ |
| crash_signals | str | 崩溃信号类型 | SIGSEGV, SIGFPE, SIGBUS |
| used_letgo | bool | 是否使用LetGo修复 | True, False |
| has_sdc | bool | 是否有SDC | True, False, None |
| result | str | 结果分类 | Crash, C-Masked, C-SDC, Masked, SDC, Recrash |
| disasm | str | 反汇编指令 | idivl -0x14(%rbp) |
| timestamp | str | 时间戳 | 2025-09-02 17:10:07 |

### CSV 示例

```csv
log_index,target_pc_hex,target_pc_dec,target_register,inject_iteration,inject_bit,crash_count,crash_signals,used_letgo,has_sdc,result,disasm,timestamp
0,0x400d59,4197721,rax,359,,,2,SIGSEGV,True,,Recrash,,
1,0x400d59,4197721,rax,189,,,1,SIGSEGV,True,,C-Masked,,
2,0x400d59,4197721,rax,99,,,0,,False,,Masked,,
```

### 统计摘要格式

```
============================================================
日志收集统计摘要
============================================================
总日志数: 1901

结果分布:
  C-Masked     319 (16.8%)
  Masked      1032 (54.3%)
  Recrash      550 (28.9%)

LetGo使用率: 45.7%
SDC检出率: 0.0%

数据完整性:
  以下字段存在缺失：
    inject_bit             0.0%
    has_sdc                0.0%
    disasm                 0.0%
    timestamp              0.0%
```

---

## Python API 使用

### 基本用法

```python
from log_collector import LogCollector, LogParser

# 方式1：使用收集器
collector = LogCollector(
    log_folder='/path/to/log',
    app_name='myapp'
)

# 收集所有日志
df = collector.collect_all(verbose=True)

# 生成CSV
csv_path = collector.generate_csv(
    output_path='output.csv',
    show_statistics=True
)

# 获取统计信息
stats = collector.csv_gen.get_statistics()
print(f"总日志数: {stats['total']}")
print(f"结果分布: {stats['result_distribution']}")
```

### 高级用法

```python
# 方式2：使用解析器处理单个日志
parser = LogParser('/path/to/log_0')
data = parser.parse()

print(f"PC: {data['target_pc_hex']}")
print(f"寄存器: {data['target_register']}")
print(f"结果: {data['result']}")

# 方式3：使用日志范围处理
collector = LogCollector('/path/to/logs', 'myapp')
df = collector.collect_all(log_range=(0, 100))  # 只处理前100个

# 方式4：数据分析
import pandas as pd

df = pd.read_csv('output.csv')

# 按结果分类统计
result_counts = df['result'].value_counts()

# 按应用分析
if 'app_name' in df.columns:
    app_analysis = df.groupby('app_name').agg({
        'result': 'value_counts',
        'used_letgo': 'mean'
    })

# 计算修复成功率
letgo_masked = df[(df['used_letgo'] == True) & (df['result'].isin(['C-Masked', 'C-SDC']))].shape[0]
letgo_total = df[df['used_letgo'] == True].shape[0]
recovery_rate = letgo_masked / letgo_total if letgo_total > 0 else 0
print(f"修复成功率: {recovery_rate * 100:.1f}%")
```

---

## 常见问题

### Q1：脚本找不到日志文件怎么办？

**A：** 检查以下几点：

1. 确认日志文件夹路径正确：
   ```bash
   ls /home/tongshiyu/pin/source/tools/letgo/TargetedBenchmarkResult/backprop/adaptive/log
   ```

2. 确认日志文件命名格式为 `log_N`（其中N是数字）

3. 使用 `--dry-run` 参数查看脚本是否能找到应用：
   ```bash
   python batch_collect_logs.py --dry-run
   ```

### Q2：某些字段为空是什么原因？

**A：** 新版Pin+GDB日志格式与旧版不同，某些字段（inject_bit、has_sdc等）在新版中未提供。

- 旧版格式：包含更多细节（disasm、timestamp等）
- 新版格式：结构更简化，但基础字段完整

### Q3：如何加速处理？

**A：** 使用以下优化方法：

```bash
# 跳过日志验证（最快）
python collect_logs.py /path/to/logs --no-validate

# 只处理日志范围（快速测试）
python collect_logs.py /path/to/logs --log-range 0-100

# 使用Dry-run检查（零处理时间）
python batch_collect_logs.py --dry-run
```

### Q4：如何处理特定的应用程序？

**A：** 使用 `--apps` 参数：

```bash
# 只处理backprop和hpl
python batch_collect_logs.py --apps backprop hpl

# 查看所有可用应用
python batch_collect_logs.py --dry-run
```

### Q5：生成的CSV太大了怎么办？

**A：** 分两步处理：

```bash
# 第1步：处理指定应用
python batch_collect_logs.py --apps backprop --output-dir ./results

# 第2步：合并CSV（如需要）
python << 'PYTHON'
import pandas as pd
import glob
dfs = [pd.read_csv(f) for f in glob.glob('results/*.csv')]
combined = pd.concat(dfs, ignore_index=True)
combined.to_csv('combined_results.csv', index=False)
PYTHON
```

---

## 性能指标

### 处理速度

| 类型 | 速度 | 说明 |
|------|------|------|
| 有验证 | 500-1000 日志/秒 | 检查日志完整性 |
| 无验证 | 3000+ 日志/秒 | 跳过验证步骤 |
| 范围处理 | 5000+ 日志/秒 | 处理指定范围 |

### 内存占用

| 日志数 | 内存占用 | 说明 |
|--------|---------|------|
| 1000 | < 50 MB | 单应用处理 |
| 10000 | < 100 MB | 多应用处理 |
| 20000 | < 200 MB | 全量处理 |

### 实际处理示例

```
处理 19,234 个日志文件
总耗时：5.9 秒
处理速度：3,262 日志/秒
输出大小：919.4 KB
```

---

## 故障排除

### 日志验证失败

```bash
# 使用 --no-validate 跳过验证
python collect_logs.py /path/to/logs --no-validate
```

### 编码错误

脚本会自动尝试多种编码（utf-8、latin-1、gbk等），如仍有问题：

```bash
# 使用 --save-warnings 保存错误信息
python collect_logs.py /path/to/logs --save-warnings
```

查看 `warnings.log` 文件了解具体错误。

### 输出路径问题

```bash
# 确保输出目录存在且可写
python collect_logs.py /path/to/logs \
  --output /absolute/path/to/output.csv
```

---

## 后续分析建议

### 1. 数据导入

```python
import pandas as pd

# 读取CSV
df = pd.read_csv('backprop_adaptive_logs.csv')

# 查看基本信息
print(df.info())
print(df.describe())
```

### 2. 结果分析

```python
# 计算各类型占比
result_counts = df['result'].value_counts()
result_pct = df['result'].value_counts(normalize=True) * 100

# 按寄存器分析
reg_analysis = df.groupby('target_register').agg({
    'result': lambda x: (x == 'Recrash').sum(),
    'used_letgo': 'mean'
})
```

### 3. 可视化

```python
import matplotlib.pyplot as plt

# 结果分布饼图
df['result'].value_counts().plot(kind='pie')

# LetGo使用率
df['used_letgo'].value_counts().plot(kind='bar')

# 按应用对比
import seaborn as sns
sns.countplot(data=df, x='result')
```

---

## 许可证与支持

该工具由自适应故障注入项目提供。

**文档版本**：1.0  
**更新时间**：2026-02-01  
**联系方式**：见项目 README.md

---

**快速链接**
- [模块文档](./log_collector/README.md)
- [统计报告](./all_apps_logs/SUMMARY.md)
- [脚本源码](./batch_collect_logs.py)
