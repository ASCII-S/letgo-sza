# 用户指南目录

本目录包含 LetGo 故障注入工具的用户指南文档。

## 文档列表

### 手动指令注错

- **[手动指令注错使用指南.md](./手动指令注错使用指南.md)** - 完整的中文使用指南
  - 功能概述
  - 快速开始
  - 配置详解
  - 参数说明
  - 使用示例
  - 常见问题
  - 高级用法

- **[Manual_Injection_Quick_Guide.md](./Manual_Injection_Quick_Guide.md)** - 英文快速指南
  - Quick start
  - Parameter format
  - Examples
  - Common issues

## 快速链接

### 手动指令注错功能

手动指令注错允许你在 `configure.py` 中直接指定要注错的指令位置和次数。

**配置示例**：

```python
# configure.py

# 启用手动模式
use_manual_instructions = True

# 配置注错指令
manual_instructions = [
    ["rdx", "", "0x467c2b", 1023, 100],  # 注错 100 次
]
```

**参数格式**：

```
[regmem, reg, pc_hex, max_iteration, repeat_count]
 ^^^^^^  ^^^  ^^^^^^  ^^^^^^^^^^^^^  ^^^^^^^^^^^^
 寄存器  寄存器 地址    最大迭代次数    注错次数
```

**详细文档**：[手动指令注错使用指南.md](./手动指令注错使用指南.md)

---

## 其他资源

- [项目整体描述](../项目整体描述.md) - 项目架构和模块说明
- [MANUAL_INJECTION_GUIDE.md](../../MANUAL_INJECTION_GUIDE.md) - 根目录下的英文指南
- [test_manual_injection.py](../../test_manual_injection.py) - 功能测试脚本
- [manual_injection_examples_v2.py](../../manual_injection_examples_v2.py) - 配置示例

---

**最后更新**：2026-04-21
