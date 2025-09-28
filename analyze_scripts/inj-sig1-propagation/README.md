# 注错原位崩溃分析工具

这个工具用于分析实验数据中的注错后原位崩溃和非原位崩溃的分布占比。通过比较第一次崩溃位置(Sig1pc)和第二次崩溃位置(Sig2pc)是否相同，来判断实验是否是原位崩溃。

## 功能特点

- 筛选特定result类型的数据（C-Masked，C-SDCs-Acceptable，C-SDCs-Unacceptable，C-SDC，Recrash,代码中可以设置）
- 判断实验是否为原位崩溃（第一次崩溃位置与第二次崩溃位置相同，代码中可以设置）
- 计算原位崩溃和非原位崩溃的占比
- 支持单文件分析和批量分析
- 生成汇总报告
- **新增功能**：支持导出原位crash和非原位crash的具体条目到单独的CSV文件

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

**导出具体条目**:
```bash
python analyze_crash_location.py --input /path/to/input.csv --export-details --details-dir results/details
```

参数说明:
- `--input`, `-i`: 输入CSV文件路径，默认为`../CSV`
- `--output`, `-o`: 输出CSV文件路径，默认为`results/<输入文件名>_crash_location_analysis.csv`
- `--export-details`, `-e`: 是否导出原位crash和非原位crash的具体条目到单独文件
- `--details-dir`, `-d`: 详细条目输出目录，默认为`results/details`

### 批量分析

```bash
python analyze_crash_location_batch.py --input-dir /path/to/csv/dir --output /path/to/summary.csv
```

**批量导出具体条目**:
```bash
python analyze_crash_location_batch.py --input-dir /path/to/csv/dir --export-details --details-dir results/details
```

参数说明:
- `--input-dir`, `-i`: 输入CSV文件目录，默认为`../CSV`
- `--output`, `-o`: 输出汇总CSV文件路径，默认为`results/crash_location_summary.csv`
- `--pattern`, `-p`: 文件匹配模式，默认为`*.csv`
- `--export-details`, `-e`: 是否导出每个文件中原位crash和非原位crash的具体条目到单独文件
- `--details-dir`, `-d`: 详细条目输出目录，默认为`results/details`

## 输出结果说明

### 统计汇总文件

分析结果将包含以下字段:

- `file_name`: 文件名（不含路径和扩展名）
- `total_errors`: 符合条件的错误总数
- `same_location_crashes`: 原位崩溃的数量
- `different_location_crashes`: 非原位崩溃的数量
- `same_location_percentage`: 原位崩溃的百分比
- `different_location_percentage`: 非原位崩溃的百分比

### 详细条目文件（启用--export-details时）

当启用导出详细条目功能时，会为每个输入文件生成两个详细文件：

- `{原文件名}_samelocation.csv`: 包含所有原位crash的具体条目数据
- `{原文件名}_differentlocation.csv`: 包含所有非原位crash的具体条目数据

这些详细文件包含原始CSV中所有的列信息，方便进一步分析特定条目的详细信息。

## 依赖

- Python 3.6+
- pandas (数据处理)
- argparse (命令行参数解析)
- tqdm (进度显示，批处理脚本需要)

## 示例

### 单文件分析示例

**基础分析**:
```bash
python analyze_crash_location.py -i ../CSV/backprop.csv -o results/backprop_crash_analysis.csv
```

**分析并导出详细条目**:
```bash
python analyze_crash_location.py -i ../CSV/backprop.csv -e -d results/details
# 将生成：
# - results/backprop_crash_location_analysis.csv (统计结果)
# - results/details/backprop_samelocation.csv (原位crash详细条目)
# - results/details/backprop_differentlocation.csv (非原位crash详细条目)
```

### 批量分析示例

**基础批量分析**:
```bash
python analyze_crash_location_batch.py -i ../CSV -o results/all_crash_summary.csv
```

**批量分析并导出所有详细条目**:
```bash
python analyze_crash_location_batch.py -i ../CSV -e -d results/details
# 将为../CSV目录下的每个CSV文件生成对应的详细条目文件
```

## 注意事项

- 确保CSV文件中包含`Sig1pc`、`Sig2pc`和`result`列
- 原位崩溃的判断基于`Sig1pc == Sig2pc`，两者完全相等才视为原位崩溃
- 结果文件将自动创建，但需要确保有写入权限
- 使用`--export-details`功能时，详细条目文件会包含原始CSV的所有列数据
- 详细条目文件只有在存在对应类型的crash时才会生成（如果没有原位crash，则不会生成_samelocation.csv文件） 