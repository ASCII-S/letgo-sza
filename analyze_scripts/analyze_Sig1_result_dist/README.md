# Sig1与Result分布关系分析工具

## 功能概述

本工具用于分析CSV文件中`result`列和`Sig1`列的分布关系，主要包含以下功能:

1. 统计每个`result`类型在不同`Sig1`信号上的分布数量
2. 支持单个CSV文件分析与批量处理
3. 生成可视化热图(可选)
4. 将多个CSV文件的结果合并成一个汇总表

## 文件结构

```
analyze_Sig1_result_dist/
├── README.md                         # 本说明文件
├── sig1_result_distribution.py       # 单文件处理脚本
├── sig1_result_distribution_batch.py # 批量处理脚本
└── results/                          # 输出结果目录
    ├── <program>_result_sig1_distribution.csv  # 单个文件分析结果
    ├── <program>_result_sig1_distribution.png  # 单个文件热图(可选)
    └── merged_result_sig1_distribution.csv     # 合并后的结果
```

## 依赖项

- Python 3.6+
- pandas
- matplotlib
- seaborn
- tqdm (用于显示进度条)

可以使用以下命令安装必要的依赖:

```bash
pip install pandas matplotlib seaborn tqdm
```

## 使用方法

### 单个文件分析

```bash
python sig1_result_distribution.py <csv文件路径> [--plot]
```

参数说明:
- `<csv文件路径>`: 要分析的CSV文件路径
- `--plot` 或 `-p`: 可选参数，是否生成热图

示例:
```bash
python sig1_result_distribution.py ../CSV/2mm.csv --plot
```

### 批量处理CSV文件

```bash
python sig1_result_distribution_batch.py [--input_dir <输入目录>] [--output_file <输出文件路径>]
```

参数说明:
- `--input_dir` 或 `-i`: 输入目录路径，默认为`../CSV`
- `--output_file` 或 `-o`: 输出文件路径，默认为`./results/merged_result_sig1_distribution.csv`

示例:
```bash
python sig1_result_distribution_batch.py --input_dir ../../CSV --output_file ./results/all_programs.csv
```

## 输出文件格式

### 单个文件分析结果

输出CSV文件格式如下:

```
program,result,SIGSEGV,SIGBUS,SIGFPE,...
2mm,C-Masked,888,777,0,...
```

其中:
- `program`: 程序名，从输入CSV文件名获取
- `result`: result列的枚举值
- `SIGSEGV`, `SIGBUS`等: Sig1列的枚举值，表示该result类型在对应Sig1上的数量

### 合并后的结果文件

合并多个CSV文件的分析结果，格式与单个文件分析结果相同，但包含多个程序的数据。

## 功能扩展

两个脚本已经实现了模块化设计:
- `sig1_result_distribution.py` 提供了可重用的基础函数
- `sig1_result_distribution_batch.py` 调用这些函数实现批量处理

如需扩展功能，可以直接导入和使用这些函数。 