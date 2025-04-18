# CSV文件分析工具

## 功能说明
此工具用于批量分析CSV文件，提供以下功能：
- 按指定列（Sig1Ins, Func, result, ErrSpd_Inj）进行分组分析
- 处理CSV文件格式，标准化输出
- 分析Func和Sig1Func的匹配分布
- 支持批量处理多个CSV文件
- 自动生成分析结果报告

## 使用方法

### 1. 基本转换功能
将CSV文件转换为标准格式（添加FuncMatch列）：
```bash
python desired_format.py -i input.csv
```

### 2. 匹配分布分析
分析不同Sig1Ins下Func与Sig1Func的匹配情况：
```bash
python desired_format.py -i input.csv --analyze-match
```

按result分组进行匹配分析：
```bash
python desired_format.py -i input.csv --analyze-match --group-by-result
```

### 参数说明
- `-i, --input`: 指定输入CSV文件或目录（默认为analysis_results目录）
- `-o, --output`: 指定输出CSV文件或目录
- `-p, --in-place`: 是否原位修改文件（直接覆盖输入文件）
- `-a, --analyze-match`: 是否分析FuncMatch分布
- `-g, --group-by-result`: 是否按result列分组（仅在分析FuncMatch分布时有效）

## 输出说明
- 基本转换结果：保存在`transformed_csv`目录中
- 匹配分布分析：保存在`match_dist_analysis`目录中
- 文件命名：根据操作类型添加相应前缀

## 文件格式
### 转换后的CSV文件
包含以下列：
- Sig1Ins: 汇编指令
- Sig1Func: 原函数名
- Func: 执行函数名
- result: 执行结果
- ErrSpd_Inj: 错误注入情况
- count: 统计数量
- FuncMatch: 函数名匹配情况（1表示匹配，0表示不匹配）

### 匹配分布分析结果
包含以下列：
- Sig1Ins: 汇编指令
- [result]: 执行结果（可选，使用--group-by-result时）
- FuncMatchCount: 函数名匹配的数量
- FuncNotMatchCount: 函数名不匹配的数量 