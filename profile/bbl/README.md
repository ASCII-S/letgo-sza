# BBL维度批量剖析

## 概述

BBL（基本块）维度剖析工具，用于批量分析应用程序的BBL级别执行特征。BBL是比函数更细粒度的分析单位，每个BBL是单入口单出口的代码序列，无内部分支，便于精确定位故障影响范围。

## 目录结构

```
bbl/
├── profile_single.py       # 单个应用BBL剖析
├── profile_batch.py        # 批量应用BBL剖析
├── README.md               # 本文档
└── results/                # 输出结果目录
    ├── raw_json/           # 原始JSON输出（按套件分类）
    │   ├── rodinia/
    │   ├── mantevo/
    │   ├── npb/
    │   └── polybench/
    ├── summary/            # 批量剖析汇总报告
    ├── visualization/      # 可视化结果（未来实现）
    └── logs/               # 执行日志
```

## 工具依赖

本工具依赖于 [bbl_profiler](/home/tongshiyu/pin/source/tools/pinfi/bbl_profiler/README.md)，请确保已编译：

```bash
cd /home/tongshiyu/pin/source/tools/pinfi
make obj-intel64/bbl_profiler/bbl_profiler.so
```

## BBL剖析指标

BBL Profiler 收集的指标包括：

| 类别 | 名称 | 说明 |
|------|------|------|
| A | 基本属性 | BBL地址、所属函数、指令数量、字节大小 |
| B | 执行统计 | 执行次数、指令执行次数 |
| C | 控制流特征 | 后继数量、循环头、函数入口/出口、终结类型 |
| D | 计算特征 | 内存/算术/逻辑/浮点/SIMD指令统计 |
| E | 数据依赖 | live_in/out、寄存器def/use、内存↔寄存器传递 |
| F | 边统计 | BBL间转移关系和执行次数 |

## 快速开始

### 1. 单个应用剖析

```bash
# 基本使用
python profile_single.py backprop

# 指定输出文件
python profile_single.py bfs --output ./my_bfs_bbl.json

# 设置超时时间（秒）
python profile_single.py hpl --timeout 7200
```

### 2. 批量应用剖析

```bash
# 剖析所有应用
python profile_batch.py --all

# 剖析指定套件
python profile_batch.py --suite rodinia

# 剖析指定应用列表
python profile_batch.py --apps backprop,bfs,hotspot
python profile_batch.py --apps 2mm,backprop,bfs,bicg,correlation,fdtd-2d,gesummv,hotspot,HPCCG,hpl,kmeans,miniFE,nn,particlefilter,syr2k
# 排除某些应用
python profile_batch.py --all --exclude amg,hpl

# 并行剖析（2个任务同时运行）
python profile_batch.py --suite rodinia --parallel 2

# 自定义超时和重试
python profile_batch.py --suite mantevo --timeout 7200 --max-retries 3
```

## 命令行参数

### profile_single.py

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `app_name` | 应用程序名称（必需） | - |
| `--output, -o` | 输出JSON文件路径 | `results/raw_json/<suite>/<app>_bbl_profile.json` |
| `--timeout, -t` | 超时时间（秒） | 3600 |

### profile_batch.py

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--all` | 剖析所有应用 | - |
| `--suite` | 剖析指定套件（rodinia/mantevo/npb/polybench） | - |
| `--apps` | 逗号分隔的应用列表 | - |
| `--exclude` | 逗号分隔的要排除的应用 | - |
| `--parallel, -p` | 并行任务数（1-4） | 1 |
| `--timeout, -t` | 每个应用的超时时间（秒） | 3600 |
| `--max-retries, -r` | 最大重试次数 | 2 |

## 输出格式

### JSON输出结构

```json
{
  "tool_info": {
    "tool_name": "bbl_profiler",
    "version": "1.0",
    "target_program": "backprop"
  },
  "bbls": [
    {
      "bbl_addr": "0x401000",
      "function_name": "main",
      "num_instructions": 15,
      "basic_stats": {
        "exec_count": 1000,
        "inst_exec_count": 15000
      },
      "control_flow": {
        "num_successors": 2,
        "is_loop_header": false,
        "terminator_type": "conditional_branch"
      },
      "compute": {
        "memory_ops_static": 5,
        "arithmetic_ops_static": 8,
        "memory_ops_exec": 5000,
        "arithmetic_ops_exec": 8000
      },
      "data_dependency": {
        "live_in_count": 3,
        "live_out_count": 2
      }
    }
  ],
  "edges": [
    {
      "from_bbl": "0x401000",
      "to_bbl": "0x401020",
      "exec_count": 800,
      "edge_type": "taken"
    }
  ],
  "statistics": {
    "total_bbls": 256,
    "total_edges": 412,
    "total_instructions_executed": 1500000
  }
}
```

### 批量剖析汇总报告

位于 `results/summary/batch_summary_<timestamp>.json`：

```json
{
  "timestamp": "2024-02-07T12:34:56",
  "configuration": {
    "apps_count": 10,
    "parallel_jobs": 2,
    "timeout": 3600,
    "max_retries": 2
  },
  "results": {
    "total": 10,
    "success": 8,
    "failed": 1,
    "timeout": 1
  },
  "total_time": 1234.5,
  "details": {
    "success": [...],
    "failed": [...],
    "timeout": [...]
  }
}
```

## 与函数维度剖析的对比

| 维度 | 函数维度 | BBL维度 |
|------|---------|---------|
| 粒度 | 粗（包含多个BBL） | 细（单个控制流单元） |
| 内部控制流 | 有分支/循环 | 无分支，顺序执行 |
| 故障定位精度 | 粗略定位到函数 | 精确定位到代码块 |
| CFG分析 | 调用图 | 控制流图边 |
| 热点识别 | 函数级热点 | BBL级热点（更精确） |
| 输出大小 | 较小 | 较大（BBL数量多） |
| 执行开销 | 较小 | 较大（更细粒度追踪） |

## 研究应用场景

基于BBL维度剖析可以研究：

1. **RQ1**: 循环头BBL的故障影响是否显著大于普通BBL？
2. **RQ2**: 高`live_out_count`的BBL是否SDC风险更高？
3. **RQ3**: BBL执行频率与故障屏蔽率的关系？
4. **RQ4**: 不同终结类型的BBL弹性特征差异？
5. **热路径分析**: 识别高频执行的BBL序列
6. **关键BBL识别**: 找出对程序输出影响最大的BBL

## 故障排查

### 常见问题

1. **工具未编译**
   ```bash
   错误: BBL_PROFILER_TOOL not found
   解决: cd /home/tongshiyu/pin/source/tools/pinfi && make obj-intel64/bbl_profiler/bbl_profiler.so
   ```

2. **应用配置缺失**
   ```bash
   错误: 无法获取应用 xxx 的配置
   解决: 检查 configure.py 中是否有该应用的配置
   ```

3. **剖析超时**
   - 增加超时时间：`--timeout 7200`
   - 对于长时间运行的应用，考虑减少输入规模

4. **JSON输出过大**
   - BBL数量多会导致JSON文件很大（可能上百MB）
   - 确保有足够的磁盘空间
   - 后续可考虑添加过滤选项（如只保存高频BBL）

### 查看日志

```bash
# 单个应用的日志
ls results/logs/<app>_bbl_profile_*.log

# 批量剖析日志
ls results/logs/batch_bbl_profile_*.log
```

## 性能考虑

- **执行开销**: BBL级追踪的开销比函数级大，预期慢5-10倍
- **输出大小**: JSON文件可能很大（10-500MB），需要足够磁盘空间
- **并行处理**: 建议使用 `--parallel 2` 或 `--parallel 4` 加速批量剖析
- **内存使用**: 每个剖析任务可能需要数GB内存

## 后续工作

- [ ] 添加 `analyze_results.py` 进行BBL特征统计分析
- [ ] 添加 `visualize.py` 生成控制流图可视化
- [ ] 支持过滤选项（如只保存执行次数 > N 的BBL）
- [ ] 与故障注入结果关联分析
- [ ] 计算BBL级弹性评分

## 参考文档

- [bbl_profiler工具文档](/home/tongshiyu/pin/source/tools/pinfi/bbl_profiler/README.md)
- [bbl_profiler指标详解](/home/tongshiyu/pin/source/tools/pinfi/bbl_profiler/docs/METRICS_GUIDE.md)
- [函数维度剖析文档](/home/tongshiyu/pin/source/tools/letgo/profile/function/README.md)

## 版本历史

- **v1.0** (2024-02-07): 初始版本，支持单个和批量BBL剖析
