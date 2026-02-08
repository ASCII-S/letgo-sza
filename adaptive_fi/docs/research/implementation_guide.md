# 轻量级值域修复 - 实现指南

## 1. 实现路线图

### 阶段1: 基础检测功能（1周）

#### 1.1 添加检测方法到 `pin_gdb_injector.py`

```python
# 在 PinGdbInjector 类中添加以下方法

def _is_value_domain_anomaly(self, original: int, injected: int) -> bool:
    """
    检测寄存器值是否出现明显的值域异常

    策略：
    1. 小值突变：原值<4096，注错值>16倍原值
    2. 高位异常：高位比特突然出现（相差8位以上）
    """
    SMALL_VALUE_THRESHOLD = 4096
    AMPLIFICATION_FACTOR = 16
    HIGH_BIT_THRESHOLD = 8

    # 策略1：小值突变检测
    if original < SMALL_VALUE_THRESHOLD:
        if injected > original * AMPLIFICATION_FACTOR:
            return True

    # 策略2：高位异常比特检测
    diff = original ^ injected
    if diff > 0:
        msb_position = diff.bit_length() - 1
        original_msb = original.bit_length() - 1 if original > 0 else 0

        if msb_position - original_msb >= HIGH_BIT_THRESHOLD:
            return True

    return False

def _is_single_bit_flip(self, original: int, injected: int) -> tuple[bool, int]:
    """
    检测是否为单比特翻转

    原理：如果 diff = original XOR injected 是2的幂次，
          则说明只有一个比特位不同

    Returns:
        (是否单比特翻转, 翻转的比特位置)
    """
    diff = original ^ injected

    # 检查 diff 是否为 2 的幂次
    # 技巧：2^n & (2^n - 1) = 0
    if diff > 0 and (diff & (diff - 1)) == 0:
        bit_position = diff.bit_length() - 1
        return True, bit_position

    return False, -1

def _analyze_fault_pattern(self):
    """
    分析注错模式（用于调试和统计）

    输出到日志：
    - 值域异常类型
    - 比特翻转位置
    - 值变化幅度
    """
    original = int(self.inject_info.original_value, 16)
    injected = int(self.inject_info.injected_value, 16)

    print("\n" + "="*60)
    print("故障模式分析")
    print("="*60)
    print(f"原值:     0x{original:016x}  ({original})")
    print(f"注错值:   0x{injected:016x}  ({injected})")
    print(f"XOR差异:  0x{(original ^ injected):016x}")

    # 值域分析
    if original > 0:
        ratio = injected / original
        print(f"变化倍数: {ratio:.2f}x")

    # 比特分析
    is_single, bit_pos = self._is_single_bit_flip(original, injected)
    if is_single:
        print(f"故障类型: 单比特翻转（位 {bit_pos}）")
    else:
        diff = original ^ injected
        bit_count = bin(diff).count('1')
        print(f"故障类型: 多比特翻转（{bit_count} 个比特）")

    # 值域异常分析
    is_anomaly = self._is_value_domain_anomaly(original, injected)
    print(f"值域异常: {'是' if is_anomaly else '否'}")
    print("="*60)
```

### 阶段2: 轻量级修复逻辑（2周）

#### 2.1 实现修复尝试方法

```python
def _try_lightweight_repair(self) -> bool:
    """
    尝试轻量级值域修复

    流程：
    1. 解析注错信息
    2. 值域异常检测
    3. 单比特翻转检测
    4. 执行修复（修改寄存器值）
    5. 验证修复

    Returns:
        True: 轻量级修复成功
        False: 需要回退到LetGo
    """
    print("\n" + "="*60)
    print("轻量级值域修复尝试")
    print("="*60)

    # 解析注错信息
    original_value = int(self.inject_info.original_value, 16)
    injected_value = int(self.inject_info.injected_value, 16)
    register = self.inject_info.inject_reg

    print(f"寄存器:   {register}")
    print(f"原值:     0x{original_value:x}")
    print(f"注错值:   0x{injected_value:x}")

    # 1. 值域异常检测
    is_anomaly = self._is_value_domain_anomaly(original_value, injected_value)
    if not is_anomaly:
        print("结论:     非值域异常 → 回退到LetGo")
        return False

    print("检测:     ✓ 值域异常")

    # 2. 单比特翻转检测
    is_single_flip, bit_pos = self._is_single_bit_flip(original_value, injected_value)
    if not is_single_flip:
        print(f"检测:     ✗ 多比特翻转 → 回退到LetGo")
        return False

    print(f"检测:     ✓ 单比特翻转（位 {bit_pos}）")

    # 3. 执行修复
    print(f"\n修复动作: 恢复 {register} = 0x{original_value:x}")

    try:
        # 修改寄存器值
        self.gdb_process.sendline(f"set ${register} = 0x{original_value:x}")
        self.gdb_process.expect("\(gdb\)")

        # 验证修改
        self.gdb_process.sendline(f"print/x ${register}")
        idx = self.gdb_process.expect([
            f"\\$\\d+ = 0x{original_value:x}",
            "\(gdb\)"
        ])

        if idx == 0:
            self.gdb_process.expect("\(gdb\)")
            print(f"验证:     ✓ 寄存器已恢复")
        else:
            print(f"验证:     ✗ 寄存器修改失败")
            return False

        print("="*60)
        return True

    except Exception as e:
        print(f"错误:     修复失败 - {e}")
        print("="*60)
        return False
```

#### 2.2 实现后续行为检测

```python
def _check_post_lightweight_repair(self) -> str:
    """
    检测轻量级修复后的程序行为

    流程：
    1. 重新执行崩溃指令（continue）
    2. 监测是否再次崩溃
    3. 如果正常退出，进行SDC检测

    Returns:
        "LW-Masked": 轻量级修复成功，无SDC
        "LW-SDC": 轻量级修复成功，有SDC
        "LW-Recrash": 修复后再次崩溃
    """
    print("\n[后续检测] 重新执行程序...")
    print("[后续检测] （PC保持不变，从崩溃指令重新执行）")

    self.gdb_process.sendline("continue")

    patterns = [
        "Program received signal",  # 0: 再次崩溃
        "exited normally",          # 1: 正常退出
        "exited with code",         # 2: 非零退出
        "\(gdb\)",                  # 3: GDB提示符
        pexpect.TIMEOUT             # 4: 超时
    ]

    timeout = 180  # 3分钟超时
    i = self.gdb_process.expect(patterns, timeout=timeout)

    if i == 0:
        # 再次崩溃
        print("[后续检测] ✗ 再次崩溃")
        self.gdb_process.expect("\(gdb\)")
        return "LW-Recrash"

    # 等待GDB提示符
    if i != 3:
        try:
            self.gdb_process.expect("\(gdb\)", timeout=5)
        except:
            pass

    # 正常退出，进行SDC检测
    print("[后续检测] ✓ 程序正常退出")

    has_sdc = self._check_sdc()

    if has_sdc:
        print("[后续检测] 结果: 轻量级修复成功，但存在SDC")
        return "LW-SDC"
    else:
        print("[后续检测] 结果: 轻量级修复成功，无SDC")
        return "LW-Masked"
```

#### 2.3 修改崩溃恢复主流程

```python
def _handle_crash_recovery(self, inject_info_path: str) -> str:
    """
    处理崩溃恢复（整合轻量级修复）

    修改要点：
    1. 先尝试轻量级修复
    2. 如果失败，回退到LetGo
    """
    print("\n" + "="*60)
    print("崩溃恢复框架")
    print("="*60)

    # Step 1: 读取inject_info.txt
    if not os.path.exists(inject_info_path):
        print(f"[错误] inject_info.txt不存在: {inject_info_path}")
        return "Crash"

    self.inject_info = self._parse_inject_info(inject_info_path)

    # 输出注错信息
    print(f"[注错信息] PC: {self.inject_info.inject_pc}")
    print(f"[注错信息] 寄存器: {self.inject_info.inject_reg}")
    print(f"[注错信息] 原值: {self.inject_info.original_value}")
    print(f"[注错信息] 注错值: {self.inject_info.injected_value}")
    print(f"[注错信息] 下一条指令: {self.inject_info.next_pc}")

    # Step 2: 【新增】尝试轻量级修复
    lightweight_success = self._try_lightweight_repair()

    if lightweight_success:
        # 轻量级修复成功，检测后续行为
        result = self._check_post_lightweight_repair()

        if result in ["LW-Masked", "LW-SDC"]:
            # 轻量级修复确实成功
            return result
        else:
            # 修复后再次崩溃，回退到LetGo
            print("\n[回退] 轻量级修复无效，启动LetGo完整修复")

    # Step 3: LetGo完整修复（原有代码）
    print("\n" + "="*60)
    print("LetGo完整修复框架")
    print("="*60)

    # 创建LetGo恢复框架实例
    self.recovery = LetGoRecovery(
        gdb_process=self.gdb_process,
        inject_info=self.inject_info,
        verbose=self.verbose
    )

    # ... 后续LetGo修复代码保持不变 ...
```

### 阶段3: 统计与分析（1周）

#### 3.1 添加统计记录

```python
class LightweightRepairStats:
    """轻量级修复统计"""

    def __init__(self):
        self.total_crashes = 0
        self.value_anomaly_count = 0
        self.single_bit_flip_count = 0
        self.lw_repair_attempts = 0
        self.lw_repair_success = 0
        self.lw_masked = 0
        self.lw_sdc = 0
        self.lw_recrash = 0

        # 详细记录
        self.anomaly_cases = []  # 值域异常案例
        self.repair_cases = []   # 修复案例

    def record_crash(self, inject_info):
        """记录崩溃信息"""
        self.total_crashes += 1

        original = int(inject_info.original_value, 16)
        injected = int(inject_info.injected_value, 16)

        # ... 记录详细信息 ...

    def record_repair_attempt(self, success: bool, result: str):
        """记录修复尝试"""
        self.lw_repair_attempts += 1

        if success:
            self.lw_repair_success += 1

            if result == "LW-Masked":
                self.lw_masked += 1
            elif result == "LW-SDC":
                self.lw_sdc += 1
            elif result == "LW-Recrash":
                self.lw_recrash += 1

    def generate_report(self) -> dict:
        """生成统计报告"""
        return {
            "total_crashes": self.total_crashes,
            "value_anomaly": {
                "count": self.value_anomaly_count,
                "percentage": self.value_anomaly_count / max(1, self.total_crashes)
            },
            "single_bit_flip": {
                "count": self.single_bit_flip_count,
                "percentage": self.single_bit_flip_count / max(1, self.value_anomaly_count)
            },
            "lightweight_repair": {
                "attempts": self.lw_repair_attempts,
                "success_count": self.lw_repair_success,
                "success_rate": self.lw_repair_success / max(1, self.lw_repair_attempts),
                "masked": self.lw_masked,
                "sdc": self.lw_sdc,
                "recrash": self.lw_recrash
            }
        }
```

#### 3.2 集成到 `adaptive_fi_wrapper.py`

```python
class AdaptiveFaultInjector:
    def __init__(self):
        # ... 原有初始化 ...

        # 【新增】轻量级修复统计
        self.lw_stats = LightweightRepairStats()

    def save_results(self):
        """保存统计结果（扩展）"""
        # ... 原有结果 ...

        # 【新增】轻量级修复统计
        result["lightweight_repair_stats"] = self.lw_stats.generate_report()

        # ... 保存到JSON ...
```

---

## 2. 测试计划

### 2.1 单元测试

创建 `test_lightweight_repair.py`：

```python
import pytest
from pin_gdb_injector import PinGdbInjector

class TestValueDomainAnomaly:
    """测试值域异常检测"""

    def test_small_value_amplification(self):
        """测试小值放大检测"""
        injector = PinGdbInjector(log_index=0)

        # 正常情况：1 -> 2 (2倍)
        assert not injector._is_value_domain_anomaly(1, 2)

        # 异常情况：1 -> 0x400001 (4M倍)
        assert injector._is_value_domain_anomaly(1, 0x400001)

        # 边界情况：100 -> 1600 (16倍)
        assert not injector._is_value_domain_anomaly(100, 1600)

        # 边界情况：100 -> 1601 (>16倍)
        assert injector._is_value_domain_anomaly(100, 1601)

    def test_high_bit_anomaly(self):
        """测试高位异常检测"""
        injector = PinGdbInjector(log_index=0)

        # 高8位翻转：0x1 -> 0x10001
        assert injector._is_value_domain_anomaly(0x1, 0x10001)

        # 低位翻转：0x100 -> 0x101
        assert not injector._is_value_domain_anomaly(0x100, 0x101)

class TestSingleBitFlip:
    """测试单比特翻转检测"""

    def test_single_bit_cases(self):
        """测试单比特翻转"""
        injector = PinGdbInjector(log_index=0)

        # 单比特翻转：0x1 -> 0x400001 (位22)
        is_single, bit_pos = injector._is_single_bit_flip(0x1, 0x400001)
        assert is_single
        assert bit_pos == 22

        # 单比特翻转：0x0 -> 0x80 (位7)
        is_single, bit_pos = injector._is_single_bit_flip(0x0, 0x80)
        assert is_single
        assert bit_pos == 7

    def test_multi_bit_cases(self):
        """测试多比特翻转"""
        injector = PinGdbInjector(log_index=0)

        # 多比特翻转：0x1 -> 0x3 (位0和位1)
        is_single, bit_pos = injector._is_single_bit_flip(0x1, 0x3)
        assert not is_single

        # 多比特翻转：0x0 -> 0x5 (位0和位2)
        is_single, bit_pos = injector._is_single_bit_flip(0x0, 0x5)
        assert not is_single
```

### 2.2 集成测试

创建测试脚本 `scripts/test_lw_repair.sh`：

```bash
#!/bin/bash

# 测试轻量级修复功能

echo "======================================"
echo "轻量级修复功能测试"
echo "======================================"

# 测试1：单个程序
echo ""
echo "测试1: backprop 程序"
python3 adaptive_fi_wrapper.py \
    --quick-test \
    --injections 5 \
    --verbose

# 检查结果
if [ -f "TargetedBenchmarkResult/backprop/adaptive/adaptive_fi_result.json" ]; then
    echo "✓ 结果文件生成成功"

    # 提取轻量级修复统计
    python3 -c "
import json
with open('TargetedBenchmarkResult/backprop/adaptive/adaptive_fi_result.json') as f:
    data = json.load(f)
    lw_stats = data.get('lightweight_repair_stats', {})
    print('\n轻量级修复统计:')
    print(json.dumps(lw_stats, indent=2))
    "
else
    echo "✗ 结果文件未生成"
    exit 1
fi
```

---

## 3. 调试指南

### 3.1 调试值域检测

```python
# 在 _try_lightweight_repair() 中添加调试输出

def _try_lightweight_repair(self) -> bool:
    # ... 前面代码 ...

    # 【调试】输出详细的比特信息
    if self.verbose:
        original_bin = bin(original_value)
        injected_bin = bin(injected_value)
        diff_bin = bin(original_value ^ injected_value)

        print(f"\n[调试] 二进制分析:")
        print(f"  原值:   {original_bin}")
        print(f"  注错值: {injected_bin}")
        print(f"  XOR:    {diff_bin}")

        # 输出每个比特位
        for i in range(64):
            orig_bit = (original_value >> i) & 1
            inj_bit = (injected_value >> i) & 1
            if orig_bit != inj_bit:
                print(f"  位 {i}: {orig_bit} -> {inj_bit}")
```

### 3.2 日志分析

查看实验日志中的轻量级修复信息：

```bash
# 查找所有尝试轻量级修复的日志
grep -r "轻量级值域修复" TargetedBenchmarkResult/*/adaptive/log/

# 统计成功率
grep -r "✓ 寄存器已恢复" TargetedBenchmarkResult/*/adaptive/log/ | wc -l
grep -r "✗ 寄存器修改失败" TargetedBenchmarkResult/*/adaptive/log/ | wc -l
```

---

## 4. 性能优化

### 4.1 减少不必要的检测

```python
# 在注错之前预判是否可能是值域异常
def should_try_lightweight_repair(self) -> bool:
    """
    预判是否值得尝试轻量级修复

    避免对以下情况进行检测：
    1. 原值和注错值相同（注错未生效）
    2. 原值已经很大（不太可能是值域异常）
    3. 寄存器是栈指针等特殊寄存器
    """
    original = int(self.inject_info.original_value, 16)
    injected = int(self.inject_info.injected_value, 16)
    register = self.inject_info.inject_reg

    # 值相同，跳过
    if original == injected:
        return False

    # 原值太大，不太可能是值域异常
    if original > 0x100000:  # 1MB
        return False

    # 栈指针等特殊寄存器，跳过
    if register.lower() in ['rsp', 'esp', 'rbp', 'ebp']:
        return False

    return True
```

### 4.2 批量处理

```python
# 对多个崩溃进行批量分析
def batch_analyze_crashes(log_folder: str):
    """批量分析崩溃日志，识别值域异常模式"""

    anomaly_patterns = defaultdict(int)

    for log_file in os.listdir(log_folder):
        if not log_file.startswith("log_"):
            continue

        # 解析日志，提取注错信息
        # ...

        # 统计模式
        if is_value_domain_anomaly(original, injected):
            pattern = f"{register}_{bit_pos}"
            anomaly_patterns[pattern] += 1

    # 输出最常见的异常模式
    print("最常见的值域异常模式:")
    for pattern, count in sorted(anomaly_patterns.items(),
                                 key=lambda x: x[1], reverse=True)[:10]:
        print(f"  {pattern}: {count} 次")
```

---

## 5. 常见问题

### Q1: 轻量级修复后仍然崩溃？

**可能原因**：
1. 故障已经传播到其他寄存器或内存
2. 程序状态已经被破坏（如栈帧损坏）
3. 多比特翻转导致的复杂错误

**解决方案**：
- 记录这些情况，回退到LetGo修复
- 分析日志，查看是否有其他异常

### Q2: 如何判断阈值是否合理？

**方法**：
1. 收集大量实验数据
2. 绘制原值-注错值分布图
3. 调整阈值，观察覆盖率和误报率
4. 使用ROC曲线找到最优阈值

### Q3: 指针类型如何处理？

**特殊处理**：
```python
def is_pointer_value_anomaly(original: int, injected: int) -> bool:
    """指针类型的值域异常检测"""

    # 指针通常在某个地址范围内
    # 例如：栈地址通常在 0x7fxxxxxx
    #      堆地址通常在 0x55xxxxxx

    # 检测地址高位是否改变
    original_high = original >> 32
    injected_high = injected >> 32

    if original_high != injected_high:
        # 高32位改变，很可能是异常
        return True

    # 检测地址是否对齐
    if original % 8 == 0 and injected % 8 != 0:
        # 对齐被破坏
        return True

    return False
```

---

## 6. 下一步工作

### 6.1 短期目标（本周）
- [ ] 实现基础检测功能
- [ ] 集成到现有框架
- [ ] 在1-2个程序上测试

### 6.2 中期目标（本月）
- [ ] 完整实现轻量级修复
- [ ] 在所有Benchmark上评估
- [ ] 收集统计数据

### 6.3 长期目标（3个月）
- [ ] 优化算法和阈值
- [ ] 撰写论文草稿
- [ ] 准备投稿

---

## 附录：完整代码示例

见 `/home/tongshiyu/pin/source/tools/letgo/adaptive_fi/docs/research/code_examples/`

- `lightweight_repair_full.py` - 完整实现
- `test_cases.py` - 测试用例
- `analysis_tools.py` - 分析工具
