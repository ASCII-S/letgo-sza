# Manual Instruction Injection User Guide

## Quick Start

### 1. Enable Manual Mode

In `configure.py`:

```python
# Enable targeted mode
inject_random_or_targeted = "targeted"

# Enable manual instruction injection
use_manual_instructions = True
```

### 2. Configure Instructions

```python
manual_instructions = [
    # [regmem, reg, pc_hex, max_iteration, repeat_count]
    ["rdx", "", "0x467c2b", 1023, 100],  # Inject 100 times
]
```

### 3. Run Experiment

```bash
python letgo_wrapper.py
```

---

## Parameter Format

```python
[regmem, reg, pc_hex, max_iteration, repeat_count]
```

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `regmem` | ✅ | - | Memory operand register (e.g., `"rbp"`) |
| `reg` | ✅ | - | Target register (e.g., `"rax"`) |
| `pc_hex` | ✅ | - | Instruction address (hex format) |
| `max_iteration` | ❌ | 1023 | Maximum execution count of this instruction |
| `repeat_count` | ❌ | 1 | Number of times to inject at this location |

---

## How to Get max_iteration

From catalog file (last column):

```bash
head -5 TargetedBenchmarkResult/fdtd-2d/mov/mov_catalog.csv
```

Output:
```
rbp,,4026b1,MOV,mov eax, dword ptr [rbp-0x1c],12474
                                               ^^^^^
                                               max_iteration
```

---

## Examples

### Example 1: Basic Configuration

```python
manual_instructions = [
    ["rbp", "", "0x4026b1", 12474, 100],  # From catalog
    ["rbp", "", "0x402605", 12096, 100],
    ["rdx", "", "0x402678", 12096, 100],
]
```

### Example 2: Single Injection

```python
manual_instructions = [
    ["rbp", "", "0x4026b1", 12474, 1],  # Inject once
]
```

### Example 3: Mixed Configuration

```python
manual_instructions = [
    ["rbp", "", "0x4026b1", 12474, 200],  # High priority
    ["rax", "", "0x402605", 12096, 50],   # Medium priority
    ["rdx", "", "0x402678", 12096, 10],   # Low priority
]
```

---

## Common Issues

### Q: Why is the pool file empty?

**Cause**: Wrong parameter format (4 parameters instead of 5).

**Wrong**:
```python
["rdx", "", "0x467c2b", 100]  # ❌ Only generates 1 record!
```

**Correct**:
```python
["rdx", "", "0x467c2b", 1023, 100]  # ✅ Generates 100 records
```

### Q: How to verify the configuration?

```bash
python -c "
import configure
import InstPoolMaker
pool_path = InstPoolMaker.generate_manual_pool(pool_csv_file='/tmp/test.csv')
import subprocess
subprocess.run(['wc', '-l', '/tmp/test.csv'])
"
```

---

## Parameter Cheat Sheet

```
[regmem, reg, pc_hex, max_iteration, repeat_count]
 ^^^^^^  ^^^  ^^^^^^  ^^^^^^^^^^^^^  ^^^^^^^^^^^^
 Register Reg Address Max Iterations Inject Count
 (Required)           (Optional)     (Optional)
```

---

For detailed documentation in Chinese, see: `手动指令注错使用指南.md`
