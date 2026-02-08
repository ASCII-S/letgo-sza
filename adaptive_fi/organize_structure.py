#!/usr/bin/env python3
"""
重组文件结构脚本
将散落的文件整理到合理的目录层次中
"""

import os
import shutil
from pathlib import Path

# 定义目录结构
STRUCTURE = {
    'scripts': 'Python脚本',
    'results': '实验结果CSV文件',
    'docs': '文档',
    'tests': '测试文件',
}

def create_structure():
    """创建目录结构"""
    base = Path('.')
    
    for dir_name in STRUCTURE.keys():
        dir_path = base / dir_name
        dir_path.mkdir(exist_ok=True)
        print(f"✓ 创建目录: {dir_name}/")
    
    # 在results下创建子目录
    (base / 'results' / 'all_apps').mkdir(exist_ok=True)
    (base / 'results' / 'single_apps').mkdir(exist_ok=True)
    print(f"✓ 创建子目录: results/all_apps/ 和 results/single_apps/")

def move_files():
    """移动文件到对应目录"""
    base = Path('.')
    moves = []
    
    # 移动脚本文件
    scripts = ['collect_logs.py', 'batch_collect_logs.py']
    for script in scripts:
        if (base / script).exists():
            moves.append((script, f'scripts/{script}'))
    
    # 移动CSV结果文件（平铺在根目录的）
    for csv in base.glob('*.csv'):
        if 'logs' in csv.name:
            moves.append((csv.name, f'results/single_apps/{csv.name}'))
    
    # 移动all_apps_logs目录
    if (base / 'all_apps_logs').exists():
        moves.append(('all_apps_logs', 'results/all_apps'))
    
    # 移动collected_logs目录
    if (base / 'collected_logs').exists():
        moves.append(('collected_logs', 'results/collected'))
    
    # 移动文档文件
    docs = ['USAGE_GUIDE_CN.md', 'batch_process.log']
    for doc in docs:
        if (base / doc).exists():
            moves.append((doc, f'docs/{doc}'))
    
    # 执行移动
    for src, dst in moves:
        src_path = base / src
        dst_path = base / dst
        
        # 如果目标已存在，先删除
        if dst_path.exists():
            if dst_path.is_dir():
                shutil.rmtree(dst_path)
            else:
                dst_path.unlink()
        
        # 移动文件/目录
        shutil.move(str(src_path), str(dst_path))
        print(f"✓ 移动: {src} -> {dst}")

def create_readme():
    """创建主README"""
    readme_content = """# 自适应故障注入日志收集工具

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

python scripts/batch_collect_logs.py \\
  --output-dir results/all_apps \\
  --statistics
```

### 处理单个应用

```bash
python scripts/collect_logs.py \\
  /home/tongshiyu/pin/source/tools/letgo/TargetedBenchmarkResult/backprop/adaptive \\
  --output results/single_apps/backprop.csv \\
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
"""
    
    with open('README.md', 'w', encoding='utf-8') as f:
        f.write(readme_content)
    print("✓ 创建: README.md")

def create_gitignore():
    """创建.gitignore"""
    gitignore_content = """# 结果文件
results/**/*.csv
results/**/*.log
results/**/SUMMARY.md

# Python缓存
__pycache__/
*.py[cod]
*$py.class
*.so

# 测试
.pytest_cache/
*.cover
.coverage

# 编辑器
.vscode/
.idea/
*.swp
*.swo
*~

# 临时文件
*.tmp
*.bak
warnings.log
"""
    
    with open('.gitignore', 'w', encoding='utf-8') as f:
        f.write(gitignore_content)
    print("✓ 创建: .gitignore")

def create_results_readme():
    """在results目录创建README"""
    readme = """# 实验结果

此目录存放日志收集生成的CSV文件。

## 子目录

- `all_apps/` - 批量处理所有应用的结果
- `single_apps/` - 单个应用处理的结果  
- `collected/` - 其他收集结果

## 说明

所有CSV文件均不纳入版本控制。
"""
    
    with open('results/README.md', 'w', encoding='utf-8') as f:
        f.write(readme)
    print("✓ 创建: results/README.md")

def main():
    print("\n" + "="*60)
    print("重组文件结构")
    print("="*60 + "\n")
    
    # 1. 创建目录结构
    print("[1/5] 创建目录结构...")
    create_structure()
    
    # 2. 移动文件
    print("\n[2/5] 移动文件...")
    move_files()
    
    # 3. 创建README
    print("\n[3/5] 创建文档...")
    create_readme()
    
    # 4. 创建.gitignore
    print("\n[4/5] 创建.gitignore...")
    create_gitignore()
    
    # 5. 创建results README
    print("\n[5/5] 创建results/README.md...")
    create_results_readme()
    
    print("\n" + "="*60)
    print("✓ 文件结构重组完成！")
    print("="*60)
    print("\n新的目录结构：")
    print("""
adaptive_fi/
├── log_collector/       # 核心模块
├── scripts/            # 可执行脚本
├── results/            # 实验结果
│   ├── all_apps/
│   ├── single_apps/
│   └── collected/
├── docs/               # 文档
└── README.md
    """)

if __name__ == '__main__':
    main()
