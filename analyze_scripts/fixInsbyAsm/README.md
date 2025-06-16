# fixInsbyAsm - CSV指令查找工具

该工具用于根据CSV文件中的`Sig1pc`列值，在对应的汇编文件中查找指令，并更新到CSV文件的`Sig1Ins`列。

## 功能

- 根据CSV文件中的`Sig1pc`列（程序计数器值）在汇编文件中查找对应的指令
- 将找到的指令更新到CSV文件的`Sig1Ins`列
- 支持单个CSV文件处理和批量处理

## 脚本说明

本工具包含两个主要脚本：

1. `fix_ins_by_asm.py` - 单个CSV文件处理脚本
2. `fix_ins_by_asm_batch.py` - 批量处理脚本

## 使用方法

### 处理单个文件

```bash
python fix_ins_by_asm.py --input ../CSVraw/2mm.csv --asm-dir ../asm --output-dir ../CSV
```

参数说明：
- `--input`: 输入CSV文件路径
- `--asm-dir`: 汇编文件目录路径（默认为"../asm"）
- `--output-dir`: 输出目录路径（默认为"../CSV"）

### 批量处理

```bash
python fix_ins_by_asm_batch.py --input-dir ../CSVraw --asm-dir ../asm --output-dir ../CSV
```

参数说明：
- `--input-dir`: 输入CSV文件目录（默认为"../CSVraw"）
- `--asm-dir`: 汇编文件目录（默认为"../asm"）
- `--output-dir`: 输出目录（默认为"../CSV"）

## 处理步骤

1. 读取CSV文件
2. 获取CSV文件名对应的应用程序名
3. 查找对应的汇编文件
4. 对于CSV文件中的每一行：
   - 获取`Sig1pc`列的值
   - 在汇编文件中查找对应的指令
   - 将找到的指令更新到`Sig1Ins`列
5. 将更新后的CSV文件保存到输出目录

## 例子

假设`CSVraw/2mm.csv`文件中有一行：
```
...,0x4023c6,...
```

脚本会在`asm/2mm.asm`文件中查找地址`4023c6`对应的指令，例如：
```
4023c6:	f2 0f 10 04 c2    	movsd  (%rdx,%rax,8),%xmm0
```

然后将指令`movsd  (%rdx,%rax,8),%xmm0`更新到CSV文件的`Sig1Ins`列，并保存到`CSV/2mm.csv`。

## 依赖

- Python 3.6+
- pandas（数据处理）
- tqdm（进度显示）
- re（正则表达式） 