# 自适应故障注入日志收集工具

## 📁 目录结构

```
adaptive_fi/
├── log_collector/          # 核心日志收集模块
│   ├── __init__.py
│   ├── log_parser.py       # 日志解析器
│   ├── csv_generator.py    # CSV生成器
│   ├── collector.py        # 收集协调器
│   └── README.md
│
├── scripts/                # 可执行脚本
│   ├── collect_logs.py     # 单应用处理脚本
│   └── batch_collect_logs.py  # 批量处理脚本
│
├── results/                # 实验结果（不纳入版本控制）
│   ├── all_apps/          # 批量处理结果
│   ├── single_apps/       # 单应用处理结果
│   └── collected/         # 其他收集结果
│
├── docs/                   # 文档
│   ├── USAGE_GUIDE_CN.md  # 使用指南
│   └── *.log              # 日志文件
│
└── README.md              # 本文件

```

## 🚀 快速开始

### 批量处理所有应用

```bash
cd /home/tongshiyu/pin/source/tools/letgo/adaptive_fi

python scripts/batch_collect_logs.py \
  --output-dir results/all_apps \
  --statistics
```

### 处理单个应用

```bash
python scripts/collect_logs.py \
  /home/tongshiyu/pin/source/tools/letgo/TargetedBenchmarkResult/backprop/adaptive \
  --output results/single_apps/backprop.csv \
  --statistics
```

## 📖 文档

- [详细使用指南](docs/USAGE_GUIDE_CN.md)
- [模块文档](log_collector/README.md)

## 📊 已处理结果

查看 `results/all_apps/` 目录下的统计报告：
- SUMMARY.md - 总体统计
- *_adaptive_logs.csv - 各应用CSV文件

## 🔧 维护

### 清理结果文件

```bash
# 清理所有结果（保留目录结构）
find results/ -name "*.csv" -delete
find results/ -name "*.md" ! -name "README.md" -delete
```

### 重新组织文件结构

```bash
python organize_structure.py
```

---

**版本**: 1.0  
**更新**: 2026-02-01
