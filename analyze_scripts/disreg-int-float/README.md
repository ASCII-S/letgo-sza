# 整数寄存器与浮点寄存器分析工具

这个工具集用于分析CSV文件中汇编指令的目标寄存器类型，区分整数寄存器和浮点寄存器，并计算它们的数量和占比。在分析前，会先根据指定的result列值进行筛选。

## 功能特点

- 从汇编指令中提取目标寄存器（如 `%xmm0`, `%rax` 等）
- 将寄存器分类为整数寄存器、浮点寄存器或未知类型
- 筛选指定的结果类型，默认包括 `C-Masked`, `C-SDCs-Acceptable`, `C-SDCs-Unacceptable`, `C-SDC`, `Recrash`
- 统计不同类型寄存器的数量和占比
- 生成详细的每个寄存器统计和总体分类统计
- 生成用于检验寄存器判断正确性的CSV文件
- 支持单个文件分析和批量文件处理
- 自动提取基准测试名称（benchmark）
- 汇总所有分析结果，并包含benchmark信息
- 将汇总结果存放在独立的summary文件夹中

## 文件结构

```
disreg-int-float/
├── analyze_reg_type.py         # 单文件分析工具
├── analyze_reg_type_batch.py   # 批量处理CSV文件的脚本
├── results/                    # 分析结果输出目录
│   ├── summary/                # 汇总结果存放目录
│   │   ├── all_benchmarks_reg_analysis_*.csv      # 所有基准测试的汇总分析结果
│   │   ├── all_inspect_results_*.csv              # 所有检测结果的汇总
│   │   ├── summary_reg_analysis_*.csv             # 所有文件的寄存器类型统计汇总
│   │   └── detailed_summary_reg_analysis_*.csv    # 所有文件的每个寄存器详细统计汇总
│   ├── inspect/                # 检测文件存放目录
│   │   └── <文件名>_inspect.csv                   # 各文件的检测结果
│   ├── <文件名>_reg_analysis.csv                  # 各文件的分析结果
│   └── <文件名>_detailed_reg_analysis.csv         # 各文件的详细分析结果
└── README.md                   # 本文档
```

## 使用方法

### 分析单个文件

```bash
python3 analyze_reg_type.py -i <输入CSV文件路径> -o <输出目录> -c <目标列名> -r <结果类型1> <结果类型2> ...
```

参数说明：
- `-i, --input`: 输入CSV文件路径，默认为'../CSV/sample.csv'
- `-o, --output`: 输出目录路径，默认为'./results'
- `-c, --column`: 要分析的列名，默认为'Sig1Ins'
- `-r, --result-types`: 需要筛选的结果类型，默认为['C-Masked', 'C-SDCs-Acceptable', 'C-SDCs-Unacceptable', 'C-SDC', 'Recrash']

示例：
```bash
# 使用默认结果类型
python3 analyze_reg_type.py -i ../CSV/data.csv -o ./results -c Sig1Ins

# 只分析特定结果类型
python3 analyze_reg_type.py -i ../CSV/data.csv -o ./results -c Sig1Ins -r "C-Masked" "C-SDC"
```

### 批量处理多个文件

```bash
python3 analyze_reg_type_batch.py -i <输入目录> -o <输出目录> -c <目标列名> -p <文件匹配模式> -r <结果类型1> <结果类型2> ...
```

参数说明：
- `-i, --input`: 输入目录路径，默认为'../CSV'
- `-o, --output`: 输出目录路径，默认为'./results'
- `-c, --column`: 要分析的列名，默认为'Sig1Ins'
- `-p, --pattern`: 文件匹配模式，默认为'*.csv'
- `-r, --result-types`: 需要筛选的结果类型，默认为['C-Masked', 'C-SDCs-Acceptable', 'C-SDCs-Unacceptable', 'C-SDC', 'Recrash']

示例：
```bash
# 使用默认结果类型
python3 analyze_reg_type_batch.py -i ../CSV -o ./results

# 只分析特定结果类型
python3 analyze_reg_type_batch.py -i ../CSV -o ./results -r "C-Masked" "Recrash"
```

## 输出文件

每个分析的CSV文件会生成三个结果文件：

1. `<文件名>_reg_analysis.csv`: 包含整数寄存器、浮点寄存器和未知类型的数量和占比统计
2. `<文件名>_detailed_reg_analysis.csv`: 包含每个目标寄存器的详细统计
3. `inspect/<文件名>_inspect.csv`: 包含原始数据、汇编指令以及寄存器判断结果，用于检验正确性

批量处理会额外在`summary`子目录中生成以下汇总文件：

1. `all_benchmarks_reg_analysis_<结果类型>.csv`: 所有基准测试的汇总分析结果，包含benchmark列
2. `all_inspect_results_<结果类型>.csv`: 所有检测结果的汇总，用于批量验证寄存器判断正确性
3. `summary_reg_analysis_<结果类型>.csv`: 所有文件的寄存器类型统计汇总
4. `detailed_summary_reg_analysis_<结果类型>.csv`: 所有文件的每个寄存器详细统计汇总

## 依赖

- Python 3.6+
- pandas
- tqdm (用于显示进度条) 