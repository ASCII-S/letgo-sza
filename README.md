# PolyBench输出验证工具

这个工具用于验证PolyBench应用的实验输出是否在可接受的误差范围内。它可以解析PolyBench标准输出格式，提取数值数组，并将实验输出与黄金参考输出进行比较。

## 功能特点

- 解析PolyBench标准输出格式
- 支持相对误差和绝对误差比较
- 可配置的容差阈值
- 支持批量验证多个应用输出
- 详细的验证结果报告

## 安装依赖

```bash
pip install numpy
```

## 使用方法

### 单个文件验证

```python
from polybench_output_validator import validate_output

# 使用默认参数验证（5%相对误差）
passed, error_percentage, max_error, max_error_idx, message = validate_output(
    "参考输出文件.out", 
    "实验输出文件.txt"
)

print(f"验证结果: {'通过' if passed else '失败'}")
print(f"错误百分比: {error_percentage:.2f}%")
print(f"最大误差: {max_error:.6f}")
print(f"最大误差索引: {max_error_idx}")
print(f"信息: {message}")
```

### 批量验证

```python
from polybench_output_validator import batch_validate
import json

# 批量验证所有应用
results = batch_validate(
    "参考输出目录",  # 包含*_ref.out文件的目录
    "实验输出目录"   # 包含*_{应用名}.txt文件的目录
)

# 将结果保存为JSON
with open("validation_results.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
```

### 自定义验证参数

```python
# 使用自定义容差（1%相对误差）
validate_output(
    "参考输出文件.out", 
    "实验输出文件.txt",
    tolerance=0.01  # 1%容差
)

# 使用绝对误差
validate_output(
    "参考输出文件.out", 
    "实验输出文件.txt",
    tolerance=1.0,  # 绝对误差值1.0
    relative_error=False
)

# 指定数组名称
validate_output(
    "参考输出文件.out", 
    "实验输出文件.txt",
    array_name="D"  # 只验证名为D的数组
)
```

## 文件说明

- `polybench_output_validator.py`: 主要功能实现
- `test_output_validator.py`: 单元测试
- `example_usage.py`: 使用示例

## 运行测试

```bash
python test_output_validator.py
```

## 运行示例

```bash
python example_usage.py
```

## 输出格式

`validate_output`函数返回一个5元组，包含：

1. `passed`: 布尔值，表示验证是否通过
2. `error_percentage`: 超出容差的错误百分比
3. `max_error`: 最大误差值
4. `max_error_idx`: 最大误差的索引位置
5. `message`: 验证结果消息

`batch_validate`函数返回一个字典，其中键是应用名称，值是包含验证结果的列表。
