# 注错原位崩溃分析工具

这个工具用于分析实验数据中的注错后原位崩溃和非原位崩溃的分布占比。通过比较注错位置(pc)和崩溃位置(Sig1pc)是否相同，来判断实验是否是原位崩溃。

## 功能特点

- 筛选特定result类型的数据（C-Masked，C-SDCs-Acceptable，C-SDCs-Unacceptable，C-SDC，Recrash,代码中可以设置）
- 判断实验是否为原位崩溃（注错位置与崩溃位置相同，代码中可以设置）
- 计算原位崩溃和非原位崩溃的占比
- 支持单文件分析和批量分析
- 生成汇总报告

## 目录结构

```
inj-sig1-propagation/
├── analyze_crash_location.py         # 单文件分析工具
├── analyze_crash_location_batch.py   # 批量处理CSV文件的脚本
└── README.md                         # 本文档
```

## 使用方法

### 单文件分析

```bash
python analyze_crash_location.py --input /path/to/input.csv --output /path/to/output.csv
```

参数说明:
- `--input`, `-i`: 输入CSV文件路径，默认为`../CSV`
- `--output`, `-o`: 输出CSV文件路径，默认为`results/<输入文件名>_crash_location_analysis.csv`

### 批量分析

```bash
python analyze_crash_location_batch.py --input-dir /path/to/csv/dir --output /path/to/summary.csv
```

参数说明:
- `--input-dir`, `-i`: 输入CSV文件目录，默认为`../CSV`
- `--output`, `-o`: 输出汇总CSV文件路径，默认为`results/crash_location_summary.csv`
- `--pattern`, `-p`: 文件匹配模式，默认为`*.csv`

## 输出结果说明

分析结果将包含以下字段:

- `file_name`: 文件名（不含路径和扩展名）
- `total_errors`: 符合条件的错误总数
- `same_location_crashes`: 原位崩溃的数量
- `different_location_crashes`: 非原位崩溃的数量
- `same_location_percentage`: 原位崩溃的百分比
- `different_location_percentage`: 非原位崩溃的百分比

## 依赖

- Python 3.6+
- pandas (数据处理)
- argparse (命令行参数解析)
- tqdm (进度显示，批处理脚本需要)

## 示例

### 单文件分析示例

```bash
python analyze_crash_location.py -i ../CSV/backprop.csv -o results/backprop_crash_analysis.csv
```

### 批量分析示例

```bash
python analyze_crash_location_batch.py -i ../CSV -o results/all_crash_summary.csv
```

## 注意事项

- 确保CSV文件中包含`pc`、`Sig1pc`和`result`列
- 原位崩溃的判断基于`pc == Sig1pc`，两者完全相等才视为原位崩溃
- 结果文件将自动创建，但需要确保有写入权限 