## 准备csv数据
- 随机注错的结果csv文件夹默认位置:
    - ./analysis/CSV
- 指令注错的结果csv文件夹默认位置:
    - ./TargetedAnalysis/CSV

## 使用./analyze.py分析脚本

该分析功能只能对单个程序进行分析,如果需要不同程序,需要手动修改指定程序名再进行分析.

- 确保condigure下的配置(程序名,指令类型)
    - waittochangebyscrips = "指定程序名"
    - inject_random_or_targeted = "targeted"
    - select_type = "指定指令类型"  

- 运行分析脚本:
    - 警告:
        - 直接使用 `python analyze.py` 会删除并重新生成该程序的csv文件,请谨慎使用
    - 功能1:
        - `python analyze.py -p all`
    - 功能2:
        - `python analyze.py -p all`

- 结果存放在`./TargetedAnalysis/PIC/程序名/`

## 使用其他分析脚本./analyze_scripts

- 将csv文件放在文件夹 `./analyze_scripts/CSV/` 下
    - 如果需要替换原来的csv文件夹,请以日期更名备份原来的CSV文件夹
- 到需要的分析脚本下运行batch脚本
- 结果放在该batch脚本下的result文件夹中

## 在./analyze_scripts下自定义分析脚本