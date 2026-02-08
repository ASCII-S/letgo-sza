# 日志收集模块 - 使用指南

## 概述

该模块为 `adaptive_fi_wrapper.py` 生成的实验日志提供收集和分析工具，将散落的日志文件整理成结构化的CSV格式，便于后续数据分析。

## 功能特性

- ✅ **自动日志扫描**：扫描指定文件夹下的所有 `log_N` 文件
- ✅ **信息提取**：提取13个关键字段（PC地址、寄存器、崩溃信息等）
- ✅ **结果分类**：自动分类为 Crash、C-Masked、C-SDC、Masked、SDC、Recrash 等
- ✅ **CSV生成**：生成标准CSV格式，易于Excel和Python分析
- ✅ **统计摘要**：显示结果分布、LetGo使用率、SDC检出率等
- ✅ **容错处理**：支持损坏日志、编码问题等异常情况
- ✅ **灵活参数**：支持日志范围过滤、自定义输出路径等

## 安装和使用

### 基本使用

```bash
# 进入脚本目录
cd /home/tongshiyu/pin/source/tools/letgo/adaptive_fi

# 收集日志（输出路径自动生成）
python collect_logs.py /path/to/exp_folder/bicg/div

# 查看帮助信息
python collect_logs.py --help
```

### 常见用例

#### 1. 基本收集并显示统计信息
```bash
python collect_logs.py /path/to/exp_folder/bicg/div --statistics
```

#### 2. 指定输出路径和应用名称
```bash
python collect_logs.py /path/to/exp_folder/bicg/div \
  --output ./results/bicg_div.csv \
  --app-name bicg
```

#### 3. 仅处理指定范围的日志（前500个）
```bash
python collect_logs.py /path/to/exp_folder \
  --log-range 0-500 \
  --verbose
```

#### 4. 详细输出和错误检查
```bash
python collect_logs.py /path/to/exp_folder \
  --verbose \
  --statistics \
  --save-warnings
```

#### 5. 生成JSON格式（可选）
```bash
python collect_logs.py /path/to/exp_folder \
  --format json \
  --output results.json
```

## CSV 字段说明

| 字段名 | 说明 | 示例 |
|--------|------|------|
| log_index | 日志编号 | 0, 1, 2, ... |
| target_pc_hex | 目标PC（十六进制） | 0x401f88 |
| target_pc_dec | 目标PC（十进制） | 4202376 |
| target_register | 目标寄存器 | rbp, rax, ... |
| inject_iteration | 注错迭代次数 | 19, 512, ... |
| inject_bit | 注错位位置 | 0-63 |
| crash_count | 崩溃次数 | 0, 1, 2, ... |
| crash_signals | 崩溃信号类型 | SIGSEGV, SIGFPE, ... |
| used_letgo | 是否使用LetGo修复 | True, False |
| has_sdc | 是否有SDC | True, False, None |
| result | 实验结果分类 | Crash, C-Masked, C-SDC, Masked, SDC, Recrash |
| disasm | 反汇编指令 | idivl -0x14(%rbp) |
| timestamp | 实验时间戳 | 2025-09-02 17:10:07.482315 |

## 结果分类说明

| 结果类型 | 说明 | 条件 |
|---------|------|------|
| Crash | 直接崩溃（无修复） | crash_count==1 且 !used_letgo |
| C-Masked | 修复后无错误 | crash_count==1 且 used_letgo 且 !has_sdc |
| C-SDC | 修复后有静默错误 | crash_count==1 且 used_letgo 且 has_sdc |
| Masked | 无崩溃无错误 | crash_count==0 且 !has_sdc |
| SDC | 无崩溃但有静默错误 | crash_count==0 且 has_sdc |
| Recrash | 多次崩溃 | crash_count>=2 |

## 命令行参数

```
位置参数:
  one_batch_folder          实验数据文件夹路径（包含log子文件夹）

可选参数:
  --help, -h                显示帮助信息
  --log-folder PATH         日志文件夹路径（默认：{one_batch_folder}/log）
  --output, -o PATH         输出CSV路径（默认：自动生成）
  --app-name, -n NAME       应用程序名称（用于输出文件名）
  --log-range START-END     日志范围，格式: 0-100 或 0:100
  --verbose, -v             详细输出
  --statistics, -s          显示统计摘要
  --format csv|json         输出格式（默认：csv）
  --no-validate             跳过日志验证（加快速度）
  --save-warnings           保存警告日志到 warnings.log
```

## Python API 使用

### 基本示例

```python
from log_collector import LogCollector

# 创建收集器
collector = LogCollector(
    log_folder='/path/to/log/folder',
    app_name='bicg'
)

# 收集所有日志
df = collector.collect_all(verbose=True)

# 生成CSV
csv_path = collector.generate_csv(
    output_path='./results/bicg.csv',
    show_statistics=True
)

# 保存警告日志
if collector.warnings:
    collector.save_warning_log('warnings.log')
```

### 高级用法

```python
from log_collector import LogCollector, LogParser

# 解析单个日志
parser = LogParser('/path/to/log_0')
data = parser.parse()

print(f"PC: {data['target_pc_hex']}")
print(f"Crash Count: {data['crash_count']}")
print(f"Result: {data['result']}")

# 获取统计信息
collector = LogCollector('/path/to/logs')
df = collector.collect_all()
stats = collector.csv_gen.get_statistics()

print(f"总日志数: {stats['total']}")
print(f"结果分布: {stats['result_distribution']}")
```

## 性能指标

- **处理速度**：约 10-50 个日志/秒（取决于日志文件大小）
- **内存占用**：< 100MB（对于1000个日志）
- **支持规模**：可处理 10,000+ 个日志文件

## 输出示例

### 统计摘要
```
============================================================
日志收集统计摘要
============================================================
总日志数: 1560

结果分布:
  Crash:     412 (26.4%)
  C-Masked:  623 (40.0%)
  C-SDC:      89 (5.7%)
  Masked:    401 (25.7%)
  SDC:        28 (1.8%)
  Recrash:     5 (0.3%)

LetGo使用率: 46.4%
SDC检出率: 7.5%
============================================================
```

### CSV 文件示例
```csv
log_index,target_pc_hex,target_pc_dec,target_register,inject_iteration,inject_bit,crash_count,crash_signals,used_letgo,has_sdc,result,disasm,timestamp
0,0x401f88,4202376,rbp,19,31,1,SIGSEGV,True,False,C-Masked,idivl -0x14(%rbp),2025-09-02 17:10:07.482315
1,0x401f88,4202376,rbp,512,25,1,SIGFPE,True,False,C-Masked,idivl -0x14(%rbp),2025-09-02 17:11:00
2,0x401f88,4202376,rbp,88,15,0,,False,False,Masked,idivl -0x14(%rbp),2025-09-02 17:12:30
```

## 数据质量保证

脚本包含以下验证机制：

1. **编码检测**：自动尝试多种编码（utf-8, utf-8-sig, latin-1, gbk）
2. **完整性检查**：验证日志文件大小和关键字段
3. **格式验证**：检查PC地址、寄存器名称等字段的合理性
4. **一致性检查**：验证十六进制和十进制PC地址是否对应
5. **错误处理**：记录所有解析失败的日志，生成警告报告

## 故障排除

### 问题：部分字段为空或NULL
**原因**：日志文件不完整或格式变化
**解决**：使用 `--verbose` 查看详细信息，使用 `--save-warnings` 保存警告

### 问题：处理速度慢
**原因**：日志验证或文件读取编码尝试过多
**解决**：使用 `--no-validate` 跳过验证，加快处理

### 问题：结果分类不准确
**原因**：日志格式变化，正则表达式不匹配
**解决**：检查日志格式，可能需要更新正则表达式

## 扩展功能

模块设计支持以下扩展：

1. **多格式输出**：支持 JSON、Excel、SQLite 等
2. **可视化**：生成结果分布图表
3. **过滤功能**：按结果类型、崩溃率等过滤
4. **批处理**：一次处理多个应用程序
5. **Web界面**：提供在线查询和分析

## 许可证和联系方式

该模块由自适应故障注入项目提供。

---

**最后更新**：2026-02-01
**版本**：1.0.0
