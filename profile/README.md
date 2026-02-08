# Profile - 应用程序剖析系统

批量应用程序剖析工具，用于分析程序的弹性特征。

## 目录结构

```
profile/
├── README.md                    # 本文件
├── config.py                    # 剖析参数配置
├── applications.json            # 应用配置（41个应用）✨
├── app_config.py               # 应用配置加载器（Python API）✨
│
├── application/                 # 程序维度剖析
│   ├── README.md               # 详细使用说明
│   ├── list_applications.py    # 应用配置查看工具 ✨
│   ├── profile_single.py       # 单应用剖析脚本
│   ├── profile_batch.py        # 批量剖析脚本
│   ├── analyze_results.py      # 结果汇总分析
│   ├── visualize.py            # 可视化图表生成
│   ├── verify_tools.sh         # 工具验证脚本 ✨
│   └── results/                # 剖析结果
│       ├── raw_json/           # 原始JSON（按套件分类）
│       ├── summary/            # 汇总报告（CSV+TXT）
│       ├── visualization/      # 可视化图表（PNG）
│       └── logs/               # 运行日志
│
├── instruction/                 # 指令维度剖析（预留，可使用 applications.json）
├── function/                    # 函数维度剖析（预留，可使用 applications.json）
└── scripts/                     # 辅助脚本
```

## 应用配置

**配置文件**: `applications.json` - 包含 41 个应用的完整配置

**应用统计**:
- **Rodinia**: 19个应用（OpenMP并行计算）
- **Mantevo**: 4个应用（MPI应用）
- **NPB**: 9个应用（NAS基准测试）
- **PolyBench**: 9个应用（多面体优化）
- **总计**: 41个应用

**配置内容**:
- 二进制文件路径
- 命令行参数
- MPI标记
- 按套件分类

**查看应用配置**:
```bash
cd application

# 查看所有应用统计
python3 list_applications.py --by-suite

# 查看所有应用列表
python3 list_applications.py

# 查看单个应用详情
python3 list_applications.py --app backprop

# 查看特定套件
python3 list_applications.py --suite rodinia
```

**在其他维度使用配置** (function/instruction):
```python
import sys
sys.path.insert(0, '/home/tongshiyu/pin/source/tools/letgo/profile')
from app_config import ApplicationConfig

config = ApplicationConfig()
all_apps = config.get_all_apps()           # 所有应用
app_cfg = config.get_app_config('backprop')  # 获取配置
binpath = config.get_app_binpath('backprop')
```

---

## 快速开始

### 1. 依赖安装

```bash
pip install pandas numpy matplotlib seaborn tqdm
```

### 2. 查看应用

```bash
cd /home/tongshiyu/pin/source/tools/letgo/profile/application

# 查看所有可用应用
python3 list_applications.py --by-suite

# 查看详细信息
python3 list_applications.py --detailed
```

### 3. 批量剖析

```bash
# 剖析所有应用（4并行）
python3 profile_batch.py --all --parallel 4

# 剖析特定套件
python3 profile_batch.py --suite rodinia --parallel 4

# 剖析指定应用
python3 profile_batch.py --apps backprop bfs hotspot
```

### 4. 分析结果

```bash
# 生成汇总报告
python3 analyze_results.py

# 生成可视化图表
python3 visualize.py

# 查看文本报告
cat results/summary/summary_report.txt
```

### 5. 验证工具

```bash
# 运行验证脚本
./verify_tools.sh
```

---

## 主要功能

### 程序维度剖析
- **应用配置管理**: 41个应用的统一配置
- **批量剖析**: 支持按套件、按列表批量处理
- **并行处理**: 1-4个并行任务
- **容错机制**: 超时控制、失败重试
- **弹性评分**: 基于7个关键指标（0-100分）
- **可视化**: 5种图表类型

### 配置管理工具
- **list_applications.py**: 查看和浏览应用配置
  - 表格视图、详细视图
  - 按套件筛选
  - 单个应用详情

- **app_config.py**: Python配置加载器
  - 供各维度剖析共享使用
  - 统一的API接口
  - 自动路径管理

### 关键指标
- `compute_memory_ratio` - 计算/访存比
- `value_lifetime_avg` - 值生命周期
- `value_fanout_avg` - 值扇出度
- `register_rewrite_rate` - 寄存器重写率
- `compare_instruction_density` - 比较指令密度
- `branch_bias` - 分支偏向性
- `resilience_score` - 综合弹性评分

---

## 使用示例

### 按套件剖析

```bash
cd application

# Rodinia套件（19个应用）
python3 profile_batch.py --suite rodinia --parallel 4

# Mantevo套件（4个MPI应用）
python3 profile_batch.py --suite mantevo

# NPB套件（9个应用）
python3 profile_batch.py --suite npb

# PolyBench套件（9个应用）
python3 profile_batch.py --suite polybench
```

### 剖析指定应用

```bash
# 单个应用
python3 profile_single.py backprop

# 多个应用
python3 profile_batch.py --apps backprop bfs hotspot

# 自定义输出和超时
python3 profile_single.py hpl --output ./hpl.json --timeout 7200
```

### 排除特定应用

```bash
# 剖析所有应用但排除超时的应用
python3 profile_batch.py --all --exclude hpl miniAMR --timeout 7200
```

### 查看应用信息

```bash
# 按套件统计
python3 list_applications.py --by-suite

# 查看Rodinia套件的所有应用
python3 list_applications.py --suite rodinia

# 查看backprop的详细配置
python3 list_applications.py --app backprop
```

---

## 输出文件

### 原始结果
- `results/raw_json/<suite>/<app>_profile.json` - 每个应用的剖析结果

### 汇总报告
- `results/summary/metrics_summary.csv` - 指标汇总CSV
- `results/summary/suite_comparison.csv` - 套件对比
- `results/summary/resilience_scores.csv` - 弹性评分
- `results/summary/summary_report.txt` - 文本报告

### 可视化图表
- `results/visualization/workload_classification.png` - 工作负载分类饼图
- `results/visualization/compute_memory_ratio.png` - 计算/访存比柱状图
- `results/visualization/suite_heatmap.png` - 套件特征热图
- `results/visualization/resilience_ranking.png` - 弹性评分排行
- `results/visualization/dataflow_features.png` - 数据流特征散点图

---

## 常见问题

### Q: application_profiler 工具未编译？
```bash
cd /home/tongshiyu/pin/source/tools/pinfi
make obj-intel64/application_profiler/application_profiler.so
```

### Q: 如何查看有哪些应用可以剖析？
```bash
cd application
python3 list_applications.py --by-suite
```

### Q: 某些应用超时？
增加超时时间：
```bash
python3 profile_batch.py --all --timeout 7200  # 2小时
```

### Q: 内存不足？
减少并行任务数：
```bash
python3 profile_batch.py --all --parallel 2
```

### Q: 如何更新应用配置？
如果修改了 `../configure.py` 中的应用配置：
```bash
cd application
python3 generate_app_configs.py
```

### Q: 模块导入错误？
运行验证脚本检查：
```bash
cd application
./verify_tools.sh
```

---

## 配置说明

### 剖析参数配置

配置文件：`config.py`

主要配置项：
- `PROFILE_TIMEOUT` - 单个应用超时时间（默认3600秒）
- `MAX_PARALLEL_JOBS` - 最大并行任务数（默认4）
- `MAX_RETRIES` - 失败重试次数（默认2）
- `RESILIENCE_WEIGHTS` - 弹性评分权重

### 应用配置

配置文件：`applications.json`

从 `../configure.py` 自动生成，包含：
- 二进制文件路径（`binpath`）
- 命令行参数（`args`）
- MPI标记（`is_mpi`）
- 按套件分类

配置示例：
```json
{
  "suites": {
    "rodinia": {
      "applications": {
        "backprop": {
          "binpath": "/path/to/backprop",
          "args": ["65536"]
        }
      }
    }
  }
}
```

---

## 弹性评分说明

弹性评分（0-100分）基于以下指标加权计算：

| 指标 | 权重 | 高弹性阈值 | 低弹性阈值 |
|------|------|-----------|-----------|
| 值生命周期 | 20% | < 10 指令 | > 50 指令 |
| 值扇出度 | 20% | < 3 | > 8 |
| 寄存器重写率 | 15% | > 30% | < 10% |
| 比较指令密度 | 15% | > 5% | < 2% |
| 分支偏向性 | 10% | > 0.8 | < 0.6 |

**评分等级**：
- A级（≥70）：高弹性
- B级（50-70）：中等弹性
- C级（<50）：低弹性

---

## 工作流程示例

### 完整工作流

```bash
cd application

# 1. 查看可用应用
python3 list_applications.py --by-suite

# 2. 批量剖析
python3 profile_batch.py --all --parallel 4

# 3. 分析结果
python3 analyze_results.py

# 4. 生成图表
python3 visualize.py

# 5. 查看报告
cat results/summary/summary_report.txt
ls results/visualization/
```

### 分套件处理

```bash
# 按套件分别处理
python3 profile_batch.py --suite rodinia --parallel 4
python3 profile_batch.py --suite mantevo
python3 profile_batch.py --suite npb
python3 profile_batch.py --suite polybench

# 汇总分析
python3 analyze_results.py
python3 visualize.py
```

---

## 详细文档

- **应用维度剖析**: `application/README.md` - 详细的脚本使用说明
- **Pin工具文档**: `/home/tongshiyu/pin/source/tools/pinfi/application_profiler/README.md`

---

## 扩展

预留了以下维度的扩展接口：

### instruction/ - 指令维度剖析
可使用 `applications.json` 和 `app_config.py` 获取应用配置

### function/ - 函数维度剖析
可使用 `applications.json` 和 `app_config.py` 获取应用配置

**使用示例**：
```python
import sys
sys.path.insert(0, '/path/to/profile')
from app_config import ApplicationConfig

config = ApplicationConfig()
for app_name in config.get_all_apps():
    binpath = config.get_app_binpath(app_name)
    args = config.get_app_args(app_name)
    # 进行指令/函数维度剖析...
```

---

## 许可

与 LetGo 项目保持一致
