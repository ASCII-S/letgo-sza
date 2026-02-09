# 更新日志 (Changelog)

## 2026-02-09 - 重大更新：迁移至 app_profiler 工具

### 概述

本次更新将应用剖析工具从旧版 `application_profiler` 迁移到新版 `app_profiler`，提供更全面的应用级特征剖析能力。

### 主要变更

#### 1. 工具更新

- **新工具**: `/home/tongshiyu/pin/source/tools/pinfi/obj-intel64/app_profiler/app_profiler.so`
- **工具版本**: Application Profiler v2.0
- **文档位置**: `/home/tongshiyu/pin/source/tools/pinfi/app_profiler/README.md`

#### 2. 剖析能力提升

新增四大类剖析指标：

**D类 - 指令类型分布**
- 整数算术运算（add, sub, mul, div）
- 浮点运算（详见A类）
- 内存访问（load, store, stack）
- 控制流（jmp, jcc, call, ret）
- 逻辑运算（bitwise, shift）
- 数据移动（mov）
- SIMD向量指令（SSE, AVX, AVX512）
- 其他指令

**A类 - 数值敏感性**
- 浮点指令静态/动态数量
- 各类浮点运算（add/sub, mul, div, sqrt, fma, cmp, cvt）
- 单/双精度执行次数
- x87扩展精度
- SIMD浮点执行次数
- **敏感运算**: div 和 sqrt 对输入误差敏感

**B类 - 误差吸收能力**
- 比较指令（cmp - 提供错误检测机会）
- TEST指令（位测试）
- 饱和运算（吸收溢出）
- MIN/MAX指令（限制范围）
- 绝对值指令（消除符号错误）
- 舍入指令

**C类 - 库调用统计**
- math 库（数学函数）
- BLAS 库（基础线性代数）
- LAPACK 库（线性代数包）
- memory 库（内存管理）
- I/O 库（输入输出）
- string 库（字符串操作）
- MPI 库（消息传递）
- OpenMP 库（并行编程）
- pthread 库（POSIX线程）

#### 3. 配置文件更新

**config.py**
```python
# 新增 APP_PROFILER_TOOL 配置
APP_PROFILER_TOOL = os.path.join(toolbase, "obj-intel64/app_profiler/app_profiler.so")
```

#### 4. 脚本更新

**profile_single.py**
- 移除 PC 范围参数（pc_start, pc_end）
- 新增 `--verbose` 参数支持详细输出模式
- 更新命令构建逻辑
- 简化初始化接口

**profile_batch.py**
- 更新文档说明
- 保持原有批量处理逻辑

#### 5. 新增文件

1. **test_profiler.py** - 配置验证脚本
   - 验证工具路径
   - 测试应用配置
   - 统计套件信息

2. **QUICK_START.md** - 快速开始指南
   - 工具说明
   - 使用示例
   - 故障排除
   - 性能优化建议

3. **example_batch_profile.py** - Python API 示例
   - 单个应用剖析
   - 批量剖析
   - 套件剖析
   - 自定义输出
   - 错误处理

4. **CHANGELOG.md** - 本更新日志

### 使用变更

#### 旧版用法（不再支持）

```bash
# 旧版指定 PC 范围
python profile_single.py backprop --pc-start 400ad0 --pc-end 4024d0
```

#### 新版用法

```bash
# 自动剖析整个应用（无需指定 PC 范围）
python3 profile_single.py backprop

# 详细输出模式
python3 profile_single.py backprop --verbose
```

### 输出格式变更

#### 新增 JSON 字段

```json
{
  "tool_info": {
    "name": "Application Profiler",
    "version": "2.0"
  },
  "instruction_distribution": {
    "total": {...},
    "by_category": {...},
    "int_arithmetic_details": {...},
    "memory_details": {...},
    "control_flow_details": {...},
    "logic_details": {...},
    "simd_details": {...}
  },
  "numeric_sensitivity": {
    "float_inst_static": 100,
    "float_inst_exec": 30000,
    "operation_distribution": {...},
    "precision_distribution": {...}
  },
  "error_absorption": {
    "cmp_inst_exec": 5000,
    "test_inst_exec": 2000,
    "saturate_inst_exec": 100,
    "minmax_inst_exec": 50,
    "abs_inst_exec": 30,
    "round_inst_exec": 20
  },
  "library_calls": {
    "total_lib_calls": 500,
    "user_func_calls": 100,
    "by_category": {
      "math_lib": {...},
      "blas_lib": {...},
      "lapack_lib": {...},
      ...
    }
  },
  "global_stats": {...}
}
```

### 迁移指南

#### 对于现有用户

1. **验证配置**
   ```bash
   python3 test_profiler.py
   ```

2. **更新脚本调用**
   - 移除所有 `--pc-start` 和 `--pc-end` 参数
   - （可选）添加 `--verbose` 启用详细模式

3. **重新剖析应用**
   ```bash
   # 单个应用
   python3 profile_single.py <app_name>

   # 批量剖析
   python3 profile_batch.py --suite <suite_name>
   ```

4. **更新分析脚本**
   - 如果有自定义分析脚本，需要适配新的 JSON 字段

#### 对于新用户

参见 `QUICK_START.md` 快速上手。

### 向后兼容性

- ❌ **不兼容**: 旧版 JSON 输出格式
- ❌ **不兼容**: PC 范围参数
- ✅ **兼容**: 批量处理接口
- ✅ **兼容**: 应用配置格式（applications.json）
- ✅ **兼容**: Python API 基本用法

### 性能对比

| 特性 | 旧版 | 新版 |
|------|------|------|
| 指令分类 | 基础分类 | 8大类 + 细分 |
| 浮点分析 | 基础统计 | 详细分类 + 敏感运算 |
| 错误吸收 | 不支持 | 6类指标 |
| 库调用 | 基础统计 | 9类库详细分类 |
| 剖析范围 | 需指定PC | 自动全应用 |
| 输出大小 | ~5KB | ~5-10KB |

### 已知问题

1. **静态链接库函数**: 可能被识别为用户函数
2. **内联函数**: 无法被识别
3. **符号信息**: 需要符号信息以获得准确的函数名

### 后续计划

- [ ] 添加结果分析脚本（analyze_results.py）适配新格式
- [ ] 添加可视化工具（visualize.py）支持新指标
- [ ] 性能优化：减少工具开销
- [ ] 支持更多库函数分类

### 感谢

感谢使用本工具！如有问题，请查看：
- `README.md` - 完整文档
- `QUICK_START.md` - 快速开始
- `/home/tongshiyu/pin/source/tools/pinfi/app_profiler/README.md` - 工具文档

---

**版本**: v2.0
**日期**: 2026-02-09
**作者**: 项目维护团队
