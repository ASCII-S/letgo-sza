# 运行letgo

## 配置实验参数`configure.py`

- 配置程序名
- 配置指令类型
- 配置注错类型
- 实验次数等

## 在独立文件夹中运行letgo

在对benchmark注错并修复时，会在当前文件夹下生成静态分析文件，因此保证各个benchmark不相互影响，所以需要在独立文件夹下运行不同参数的实验。任何参数的切换都需要一个独立的文件夹。建议先固定注错类型参数，然后切换程序名在各个文件夹下运行。

建议学习并使用`tmux`进行多任务管理。

### 随机注错

在`letgo_pinfi`文件夹中进入`letgo_pinfi1`文件夹,运行`bash runletgo.sh`

### 指令注错

在`letgo_targeted`文件夹中进入`letgo_targeted1`文件夹,运行`bash runletgo.sh`

## 检查结果

找到结果文件夹，并且将本次实验的配置参数，日期等信息写入readme中。

### 随机注错结果

在`BenchmarkResult`下，每个benchmark的注错结果都保存在`./BenchmarkResult/程序名/`下

### 指令类型注错结果

在`TargetedAnalysis`下，每个benchmark的注错结果都保存在`./TargetedAnalysis/程序名/`下

指令类型包含独立文件夹以及其注错位点。

# 分析结果

## 收集结果

将log形式的结果，转换为csv形式以便后续分析。

检查configure.py中参数不变，切换不同的程序名，执行`python analyze.py`
- 随机注错的结果csv文件夹默认位置:
    - `./analysis/CSV`
- 指令注错的结果csv文件夹默认位置:
    - `./TargetedAnalysis/CSV`

将本次实验的参数信息也以readme形式同步记录到`./analysis`和`./TargetedAnalysis`下。

## 使用`./analyze.py`分析脚本

该分析功能只能对单个程序进行分析,如果需要不同程序,需要手动修改指定程序名再进行分析.

- 确保condigure下的配置(程序名,指令类型)
    - waittochangebyscrips = "指定程序名"
    - inject_random_or_targeted = "targeted"
    - select_type = "指定指令类型"  

- 运行分析脚本:
    - 警告:
        - 直接使用 `python analyze.py` 会删除并基于结果文件夹(`BenchmarkResult`或`TargetedAnalysis`)重新生成该程序的csv文件,请谨慎使用
    - 功能1:
        - `python analyze.py -p all`
    - 功能2:
        - `python analyze.py -t all`

- 结果存放在`./TargetedAnalysis/PIC/`中

## 使用其他分析脚本`./analyze_scripts/`

- 将csv文件放在文件夹 `./analyze_scripts/CSV/` 下
    - 如果需要替换原来的csv文件夹,请以日期更名备份原来的CSV文件夹
- 到需要的分析脚本下运行batch脚本
- 结果放在该batch脚本下的result文件夹中

## 在./analyze_scripts下自定义分析脚本

可以依据readme运行一些分析脚本。

也可以自己编写分析脚本。

## 存档结果

等待一批实验完成并且完成分析结果后:
- 将结果文件夹(`BenchmarkResult`或`TargetedBenchmarkResult`)添加日期后缀以存档。
- 将分析结果文件夹(`Analysis`或`TargetedAnalysis`)添加日期后缀以存档

硬盘空间不足时，挂载硬盘到./mnt/下，将存档后的结果文件夹移动到该硬盘。