# Application Profiling - 程序维度剖析

使用 **app_profiler** 工具进行批量程序剖析的脚本集合。

> **重要更新**: 本项目已更新为使用新版 `app_profiler` 工具（位于 `/home/tongshiyu/pin/source/tools/pinfi/app_profiler/`），提供更全面的应用级特征剖析。
>
> **快速开始**: 参见 `QUICK_START.md`

## 应用配置

**配置文件位置**: `../applications.json` (共享配置，41个应用)

**查看可用应用**：
```bash
# 按套件统计
python3 list_applications.py --by-suite

# 查看所有应用
python3 list_applications.py

# 查看单个应用详情
python3 list_applications.py --app backprop
```

**应用统计**：
- **Rodinia**: 19个应用（OpenMP）
- **Mantevo**: 4个应用（MPI）
- **NPB**: 9个应用（Serial）
- **PolyBench**: 9个应用（Optimization）
- **总计**: 41个应用

---

## 核心脚本

### 1. profile_single.py - 单应用剖析

剖析单个应用程序。

**使用方法**：
```bash
python3 profile_single.py <app_name> [options]
```

**参数**：
- `app_name` - 应用名称（来自configure.py）
- `--output, -o` - 输出JSON路径（可选）
- `--timeout, -t` - 超时时间（秒，默认3600）

**示例**：
```bash
# 剖析backprop
python3 profile_single.py backprop

# 自定义输出路径和超时
python3 profile_single.py bfs --output ./my_bfs.json --timeout 7200
```

**输出**：
- JSON文件：`results/raw_json/<suite>/<app>_profile.json`
- 日志文件：`results/logs/<app>_profile_<timestamp>.log`

---

### 2. profile_batch.py - 批量剖析

批量剖析多个应用，支持并行处理。

**使用方法**：
```bash
python profile_batch.py [--all|--suite <name>|--apps <list>] [options]
```

**应用选择参数（互斥）**：
- `--all` - 剖析所有应用
- `--suite <name>` - 剖析指定套件（rodinia, mantevo, npb, polybench）
- `--apps <list>` - 指定应用列表

**其他参数**：
- `--exclude <list>` - 排除指定应用
- `--parallel, -p` - 并行任务数（1-4，默认1）
- `--timeout, -t` - 每个应用超时时间（秒，默认3600）
- `--retries, -r` - 失败重试次数（默认2）
- `--dry-run` - 只显示将要剖析的应用列表

**示例**：
```bash
# 剖析所有应用（串行）
python profile_batch.py --all

# 剖析Rodinia套件（4并行）
python profile_batch.py --suite rodinia --parallel 4

# 剖析指定应用
python profile_batch.py --apps backprop bfs hotspot

# 剖析所有但排除超时应用
python profile_batch.py --all --exclude hpl miniAMR

# Dry-run查看应用列表
python profile_batch.py --suite mantevo --dry-run

# 增加超时和重试
python profile_batch.py --all --timeout 7200 --retries 3
```

**输出**：
- 每个应用的JSON文件
- 批量日志：`results/logs/batch_profile_<timestamp>.log`
- 批量汇总：`results/summary/batch_summary_<timestamp>.json`

---

### 4. list_applications.py - 应用配置查看

查看和浏览应用配置信息。

**使用方法**：
```bash
python3 list_applications.py [options]
```

**参数**：
- `--by-suite` - 按套件统计应用
- `--suite <name>` - 只显示指定套件
- `--detailed, -d` - 显示详细信息
- `--app <name>` - 显示单个应用的详细配置

**示例**：
```bash
# 按套件统计
python3 list_applications.py --by-suite

# 表格形式列出所有应用
python3 list_applications.py

# 详细信息
python3 list_applications.py --detailed

# 查看Rodinia套件
python3 list_applications.py --suite rodinia

# 查看单个应用
python3 list_applications.py --app backprop
```

**输出**：
- 应用列表（表格或详细格式）
- 二进制路径、参数、PC范围
- MPI标记、套件归属

---

### 5. analyze_results.py - 结果分析

从JSON文件提取指标，生成汇总报告。

**使用方法**：
```bash
python analyze_results.py [options]
```

**参数**：
- `--json-dir, -j` - JSON文件目录（默认results/raw_json）
- `--output, -o` - 输出目录（默认results/summary）

**示例**：
```bash
# 分析默认目录
python analyze_results.py

# 指定自定义目录
python analyze_results.py --json-dir ./custom_json --output ./custom_summary
```

**输出文件**：
1. `metrics_summary.csv` - 指标汇总CSV
   - app_name, suite, workload_type
   - 所有关键指标
   - resilience_score

2. `suite_comparison.csv` - 套件对比
   - 每个套件的mean, std, min, max

3. `resilience_scores.csv` - 弹性评分排行
   - app_name, suite, resilience_score, grade

4. `summary_report.txt` - 文本报告
   - 按套件统计
   - 工作负载类型分布
   - Top 10 高/低弹性程序

---

### 6. visualize.py - 可视化

生成可视化图表。

**使用方法**：
```bash
python visualize.py [options]
```

**参数**：
- `--summary-dir, -s` - 汇总数据目录（默认results/summary）
- `--output, -o` - 输出目录（默认results/visualization）

**示例**：
```bash
# 生成所有图表
python visualize.py

# 自定义目录
python visualize.py --summary-dir ./custom_summary --output ./custom_plots
```

**输出图表**：
1. `workload_classification.png` - 工作负载分类饼图
2. `compute_memory_ratio.png` - 计算/访存比柱状图（按套件着色）
3. `suite_heatmap.png` - 套件特征对比热图（归一化）
4. `resilience_ranking.png` - 弹性评分排行（横向柱状图）
5. `dataflow_features.png` - 数据流特征散点图

---

## 完整工作流

### 基础流程

```bash
# 1. 查看要剖析的应用
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

### 分阶段执行

```bash
# 阶段1：先剖析Rodinia和PolyBench
python profile_batch.py --suite rodinia --parallel 4
python profile_batch.py --suite polybench --parallel 4

# 阶段2：再剖析Mantevo和NPB（可能需要更长时间）
python profile_batch.py --suite mantevo --timeout 7200
python profile_batch.py --suite npb

# 阶段3：汇总分析
python analyze_results.py
python visualize.py
```

### 增量执行

```bash
# 只剖析失败的应用
python profile_batch.py --apps app1 app2 app3

# 重新分析（会处理所有已有的JSON）
python analyze_results.py
python visualize.py
```

---

## 关键指标说明

### 程序工作负载类型
- **compute_memory_ratio** - 计算/访存比
  - `>10`: 计算密集型
  - `2-10`: 计算偏向型
  - `0.5-2`: 混合型
  - `0.1-0.5`: 访存偏向型
  - `<0.1`: 访存密集型

- **bytes_per_instruction** - 每指令访存字节数
- **simd_ratio** - SIMD/向量化比例
- **workload_type** - 工作负载分类

### 数据流特征
- **value_lifetime_avg** - 值生命周期（平均）
  - 从定义到首次使用的指令跨度
  - 越短→错误传播能力有限→高弹性

- **value_fanout_avg** - 值扇出度（平均）
  - 一个值被后续指令使用的次数
  - 越低→错误影响范围小→高弹性

- **register_rewrite_rate** - 寄存器重写率
  - 寄存器被覆写的频率
  - 越高→错误被快速覆盖→高弹性

### 冗余和校验
- **compare_instruction_density** - 比较指令密度
  - CMP/CMOV指令占比
  - 越高→隐式错误检查多→高弹性

### 控制流特征
- **branch_bias** - 分支偏向性
  - 分支方向倾向程度（0-1）
  - 越高→错误难以改变控制流→高弹性

- **loop_avg_iterations** - 循环平均迭代次数

### 内存访问
- **memory_read_write_ratio** - 内存读写比
  - 读/写次数比
  - 写多→错误被覆盖→高弹性

### 弹性评分
- **resilience_score** - 综合弹性评分（0-100）
  - 基于上述指标加权计算
  - A级（≥70）：高弹性
  - B级（50-70）：中等弹性
  - C级（<50）：低弹性

---

## 输出JSON格式

application_profiler 输出的JSON包含以下主要部分：

```json
{
  "tool_info": {...},
  "execution_summary": {
    "total_instructions": 12345678,
    "total_basic_blocks": 5000
  },
  "program_workload_type": {
    "classification": {"type": "访存偏向型"},
    "metrics": {
      "compute_memory_ratio": {"value": 0.45},
      "bytes_per_instruction": 2.3
    }
  },
  "data_flow_characteristics": {
    "metrics": {
      "value_lifetime": {"average": 15.5, "median": 10},
      "value_fanout": {"average": 3.2}
    }
  },
  "control_flow_characteristics": {...},
  "memory_access_patterns": {...},
  "instruction_characteristics": {...}
}
```

---

## 故障排除

### 1. 剖析失败
**症状**：某个应用剖析失败

**解决方案**：
```bash
# 查看日志
cat results/logs/<app>_profile_*.log

# 增加超时重试
python profile_single.py <app> --timeout 7200
```

### 2. MPI应用失败
**症状**：Mantevo应用报错

**解决方案**：
检查MPI环境：
```bash
which mpirun
mpirun --version
```

### 3. JSON解析错误
**症状**：analyze_results.py报JSON格式错误

**解决方案**：
```bash
# 检查JSON文件
cat results/raw_json/<suite>/<app>_profile.json

# 删除损坏的JSON并重新剖析
rm results/raw_json/<suite>/<app>_profile.json
python profile_single.py <app>
```

### 4. 可视化失败
**症状**：visualize.py报缺少数据

**解决方案**：
```bash
# 先运行分析
python analyze_results.py

# 检查汇总文件
ls results/summary/
```

### 5. 内存不足
**症状**：系统卡住或OOM

**解决方案**：
```bash
# 减少并行数
python profile_batch.py --all --parallel 2

# 或分批处理
python profile_batch.py --suite rodinia
python profile_batch.py --suite mantevo
...
```

---

## 性能优化建议

### 1. 并行处理
- 推荐4个并行任务：`--parallel 4`
- CPU核心数少时降低并行数

### 2. 超时设置
- 小程序（如backprop）：默认3600秒足够
- 大程序（如hpl）：建议7200秒或更多

### 3. 分批处理
```bash
# 先处理快速的套件
python profile_batch.py --suite rodinia --parallel 4
python profile_batch.py --suite polybench --parallel 4

# 再处理慢速套件
python profile_batch.py --suite mantevo --timeout 7200
```

---

## 依赖说明

### 必需依赖
```bash
pip install pandas numpy
```

### 可视化依赖（可选）
```bash
pip install matplotlib seaborn
```

### 进度条（可选）
```bash
pip install tqdm
```

### 系统要求
- Python 3.6+
- application_profiler.so 已编译
- Pin 工具
- MPI环境（用于Mantevo套件）

---

## 配置文件

配置文件：`../config.py`

可修改的配置：
```python
# 超时时间
PROFILE_TIMEOUT = 3600  # 1小时

# 并行任务数
MAX_PARALLEL_JOBS = 4

# 重试次数
MAX_RETRIES = 2

# 弹性评分权重
RESILIENCE_WEIGHTS = {
    'value_lifetime': 0.20,
    'value_fanout': 0.20,
    'register_rewrite_rate': 0.15,
    'compare_density': 0.15,
    'branch_bias': 0.10,
    'mask_operations': 0.10,
    'function_call_frequency': 0.10
}
```

---

## 常见用例

### 用例1：全量剖析所有应用
```bash
python profile_batch.py --all --parallel 4
python analyze_results.py
python visualize.py
```

### 用例2：对比不同套件的弹性特征
```bash
python profile_batch.py --suite rodinia --parallel 4
python profile_batch.py --suite mantevo
python analyze_results.py
# 查看 suite_comparison.csv 和 suite_heatmap.png
```

### 用例3：识别高弹性/低弹性应用
```bash
python profile_batch.py --all --parallel 4
python analyze_results.py
# 查看 resilience_scores.csv 和 resilience_ranking.png
```

### 用例4：分析特定应用的弹性瓶颈
```bash
python profile_single.py <app>
# 查看 raw_json/<suite>/<app>_profile.json
# 分析哪些指标导致低弹性评分
```

---

## 扩展和定制

### 添加新指标
在 `analyze_results.py` 的 `extract_metrics_from_json()` 中添加：
```python
if 'new_feature' in data:
    metrics['new_metric'] = data['new_feature'].get('value')
```

### 修改弹性评分算法
在 `../config.py` 中修改 `RESILIENCE_WEIGHTS`

### 添加新图表
在 `visualize.py` 中添加新的绘图函数

---

## 许可

与 LetGo 项目保持一致
