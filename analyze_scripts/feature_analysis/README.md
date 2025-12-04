# Feature Analysis Toolkit

增强型特征分析工具包，用于分析LetGo故障注入实验中收集的多维度特征及其对程序可修复性的影响。

## 📋 目录结构

```
feature_analysis/
├── feature_analyzer.py         # 核心分析器类（面向对象设计）
├── analyze_features.py         # 单程序分析脚本
├── analyze_features_batch.py   # 批处理分析脚本
├── config.py                   # 配置文件
├── README.md                   # 本文档
└── results/                    # 默认输出目录
    ├── individual/             # 各程序独立分析结果
    │   ├── backprop/
    │   ├── bfs/
    │   └── ...
    └── comparison/             # 跨程序对比分析
        ├── callDepth_comparison.png
        ├── feature_importance_heatmap.png
        └── ...
```

---

## 🎯 功能特性

### 1. 面向对象设计

- **`FeatureAnalyzer` 类**：封装所有分析逻辑
- 支持继承和扩展
- 清晰的API接口

### 2. 多数据源支持

- 默认读取 `../CSV/` 目录
- 支持自定义CSV路径
- 兼容 `analysis/CSV/` 和 `TargetedAnalysis/` 结构

### 3. 五大分析维度

| 分析类型 | 方法名 | 输出 |
|---------|--------|------|
| 调用深度分析 | `analyze_call_depth_recoverability()` | PNG图表 + CSV统计 |
| 指令类型分析 | `analyze_instr_type_heuristic()` | PNG图表 + CSV统计 |
| 执行进度分析 | `analyze_exec_progress()` | PNG图表 + CSV统计 |
| 栈指针偏移分析 | `analyze_rbp_rsp_delta()` | PNG图表 + CSV统计 |
| 特征重要性表 | `generate_feature_importance_table()` | CSV表格 |

### 4. 批处理能力

- 一次分析多个程序
- 自动生成跨程序对比报告
- 热力图、误差棒图等高级可视化

---

## 🚀 使用方法

### 方式1：单程序分析

```bash
cd analyze_scripts/feature_analysis

# 分析默认位置的CSV文件 (../CSV/backprop.csv)
python analyze_features.py backprop.csv

# 分析自定义路径的CSV文件
python analyze_features.py /path/to/experiment/backprop.csv

# 指定输出目录
python analyze_features.py backprop.csv --output ./my_results

# 指定程序名称（用于输出文件命名）
python analyze_features.py data.csv --name my_program

# 分析top 20操作码（默认15）
python analyze_features.py backprop.csv --top-opcodes 20
```

**输出文件示例**：
```
results/
├── backprop_callDepth_recoverability.png
├── backprop_callDepth_stats.csv
├── backprop_opcode_heuristic_dist.png
├── backprop_opcode_heuristic_stats.csv
├── backprop_execPhase_crash.png
├── backprop_execPhase_stats.csv
├── backprop_rbp_rsp_delta.png
├── backprop_rbpRspDelta_stats.csv
└── backprop_feature_importance.csv
```

---

### 方式2：批处理分析

```bash
cd analyze_scripts/feature_analysis

# 分析 ../CSV/ 目录下的所有程序
python analyze_features_batch.py

# 分析特定程序
python analyze_features_batch.py --programs backprop bfs nn

# 使用自定义CSV目录
python analyze_features_batch.py --csv-dir /path/to/csv

# 指定输出目录
python analyze_features_batch.py --output ./batch_results
```

**输出结构**：
```
results/
├── individual/                          # 各程序独立结果
│   ├── backprop/
│   │   ├── backprop_callDepth_recoverability.png
│   │   ├── backprop_callDepth_stats.csv
│   │   └── ...
│   ├── bfs/
│   └── nn/
└── comparison/                          # 跨程序对比
    ├── callDepth_comparison.png         # 调用深度对比图
    ├── callDepth_comparison.csv
    ├── feature_importance_heatmap.png   # 特征重要性热力图
    └── feature_importance_comparison.csv
```

---

### 方式3：Python API调用

```python
from feature_analyzer import FeatureAnalyzer

# 创建分析器实例
analyzer = FeatureAnalyzer(
    csv_path='../CSV/backprop.csv',
    output_dir='./results',
    progname='backprop'
)

# 运行所有分析
analyzer.run_all_analyses()

# 或单独运行特定分析
df_call_depth = analyzer.analyze_call_depth_recoverability()
df_opcode = analyzer.analyze_instr_type_heuristic(top_n=20)
df_phase = analyzer.analyze_exec_progress()
df_delta = analyzer.analyze_rbp_rsp_delta()
df_importance = analyzer.generate_feature_importance_table()
```

---

## 📊 分析报告详解

### 1. 调用深度分析

**文件名**: `<progname>_callDepth_recoverability.png`

**图表内容**:
- 左图：堆积柱状图，展示各调用深度的结果分布（C-Masked, C-SDC, Recrash）
- 右图：折线图，展示恢复成功率随调用深度的变化趋势

**统计文件**: `<progname>_callDepth_stats.csv`

**应用场景**:
- 评估函数调用深度对容错能力的影响
- 识别易修复的调用深度范围
- 论文图表：证明浅层调用更易修复

---

### 2. 指令类型与修复策略分析

**文件名**: `<progname>_opcode_heuristic_dist.png`

**图表内容**:
- 堆积柱状图，展示top N操作码使用的修复策略分布（h_1, h_2, h_3）

**统计文件**: `<progname>_opcode_heuristic_stats.csv`

**应用场景**:
- 分析不同指令类型的修复特点
- 优化修复策略的针对性
- 论文表格：各指令类型的修复策略偏好

---

### 3. 执行进度分析

**文件名**: `<progname>_execPhase_crash.png`

**图表内容**:
- 柱状图，展示程序不同执行阶段的崩溃率

**统计文件**: `<progname>_execPhase_stats.csv`

**应用场景**:
- 识别程序脆弱阶段
- 指导关键代码段的加固
- 论文图表：执行阶段对崩溃的影响

---

### 4. 栈指针偏移分析

**文件名**: `<progname>_rbp_rsp_delta.png`

**图表内容**:
- 柱状图，展示不同RBP-RSP偏移范围的恢复成功率

**统计文件**: `<progname>_rbpRspDelta_stats.csv`

**应用场景**:
- 评估栈状态对h_1策略的影响
- 优化栈修复算法
- 论文数据：栈完整性与可修复性关系

---

### 5. 特征重要性表

**文件名**: `<progname>_feature_importance.csv`

**内容**:
```
Feature       | Value      | Total | Recoverable | Recoverability
--------------|------------|-------|-------------|---------------
CallDepth     | 1          | 150   | 128         | 85.3%
CallDepth     | 2          | 280   | 231         | 82.5%
InstrFlag     | StackRead  | 420   | 336         | 80.0%
IsRecursive   | No         | 780   | 624         | 80.0%
```

**应用场景**:
- 快速识别关键特征
- 特征选择（用于机器学习）
- 论文表格：特征对可修复性的定量评估

---

## ⚙️ 配置说明

编辑 `config.py` 自定义分析参数：

```python
# 分析参数
TOP_OPCODES = 15                    # 分析的top操作码数量
EXEC_PROGRESS_PHASES = [...]        # 执行进度阶段划分
RBP_RSP_DELTA_BINS = [...]          # 栈偏移分箱

# 可视化配置
FIGURE_DPI = 300                    # 图像分辨率
COLOR_SCHEMES = {...}               # 配色方案

# 批处理配置
BATCH_PROGRAMS = None               # 指定批处理程序列表
GENERATE_COMPARISON = True          # 是否生成对比报告
```

---

## 🔧 依赖要求

```bash
# Python >= 3.6
pip install pandas matplotlib seaborn numpy
```

---

## 📈 批处理对比报告

### 1. 调用深度对比 (`callDepth_comparison.png`)

- **误差棒图**：展示所有程序的平均恢复率 ± 标准差
- **应用**：跨程序趋势分析

### 2. 特征重要性热力图 (`feature_importance_heatmap.png`)

- **热力图**：行=程序，列=特征，值=恢复成功率
- **应用**：识别通用vs程序特定的重要特征

---

## 📝 数据格式要求

### 输入CSV必须包含的列：

| 列名 | 类型 | 说明 |
|------|------|------|
| `result` | string | 结果分类（C-Masked, C-SDC, Recrash等） |
| `CallDepth` | int | 调用深度 |
| `CallChain` | string | 调用链 |
| `InstrFlag` | int | 指令类型（1/2/3） |
| `opcode` | string | 操作码 |
| `Heuristic` | string | 修复策略（h_1/h_2/h_3） |
| `RBP_RSP_Delta` | int | 栈指针偏移 |
| `ExecProgress` | float | 执行进度（0-1） |
| `IsRecursive` | bool | 是否递归 |

**注意**：如果某列不存在或全为null，相关分析会自动跳过。

---

## 🛠️ 故障排查

### 问题1：找不到CSV文件

```bash
# 错误信息
Error: CSV file not found: ../CSV/backprop.csv

# 解决方案
# 1. 检查CSV文件是否存在
ls ../CSV/backprop.csv

# 2. 使用绝对路径
python analyze_features.py /full/path/to/backprop.csv

# 3. 或指定CSV目录
python analyze_features_batch.py --csv-dir /path/to/csv
```

---

### 问题2：缺少特征列

```bash
# 输出
No valid CallDepth data found

# 原因
CSV文件中没有 CallDepth 列，或全为 null

# 解决方案
# 1. 确认使用了增强版sighandler.py和analyze.py
# 2. 重新运行实验以收集新特征
# 3. 检查日志文件是否包含 "=== Call Stack Features ==="
grep "Call Stack Features" BenchmarkResult/backprop/log/log_0
```

---

### 问题3：中文乱码

```bash
# 解决方案1：安装中文字体
# Ubuntu/Debian
sudo apt-get install fonts-wqy-zenhei

# CentOS/RHEL
sudo yum install wqy-zenhei-fonts

# 解决方案2：修改config.py使用英文标签
# 或在代码中设置
import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
```

---

## 📚 扩展开发

### 添加新的分析功能

```python
# 在 FeatureAnalyzer 类中添加新方法
class FeatureAnalyzer:
    def analyze_custom_feature(self) -> Optional[pd.DataFrame]:
        """自定义特征分析"""
        print("\n=== Custom Feature Analysis ===")

        # 1. 数据验证
        df_valid = self.df_crash[self.df_crash['CustomFeature'].notna()].copy()
        if len(df_valid) == 0:
            print("  No valid data")
            return None

        # 2. 统计计算
        stats = ...

        # 3. 可视化
        fig, ax = plt.subplots(figsize=(10, 6))
        # ... 绘图代码 ...
        self._save_figure(fig, f'{self.progname}_custom_feature.png')

        # 4. 保存统计
        stats_path = self.output_dir / f"{self.progname}_custom_stats.csv"
        stats.to_csv(stats_path, index=False)

        return stats
```

然后在 `run_all_analyses()` 中调用：

```python
def run_all_analyses(self):
    analyses = [
        # ... 现有分析 ...
        ('Custom Feature', self.analyze_custom_feature),
    ]
    # ...
```

---

## 🔗 相关文档

- [项目整体描述](../../docs/项目整体描述.md)
- [特征增强说明](../../docs/FEATURE_ENHANCEMENT.md)
- [原始analyze.py文档](../../README.md)

---

## 🤝 贡献指南

欢迎贡献新的分析功能！请遵循以下规范：

1. 新分析方法放在 `FeatureAnalyzer` 类中
2. 方法命名：`analyze_<feature_name>()`
3. 返回 `Optional[pd.DataFrame]` 类型
4. 输出文件命名：`<progname>_<feature>_<type>.<ext>`
5. 添加单元测试和文档

---

## 📄 许可证

遵循原LetGo框架许可证

---

## 👤 作者

增强功能开发者: Enhanced LetGo Framework Team
原始LetGo框架: [原作者]

---

## 📮 反馈

如有问题或建议，请提交Issue或Pull Request。
