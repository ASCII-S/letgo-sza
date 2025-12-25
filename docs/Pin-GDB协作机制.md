# LetGo 框架中 Pin 与 GDB 的协作机制

本文档详细介绍 LetGo 故障注入与恢复框架中 Intel Pin 动态二进制插桩工具与 GDB 调试器的协作机制。

---

## 1. 系统架构概览

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           letgo_wrapper.py                               │
│                           (主控程序)                                     │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │
          ┌─────────────────────┼─────────────────────┐
          │                     │                     │
          ▼                     ▼                     ▼
┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐
│   Pin 工具链     │   │  sighandler.py  │   │  faultinject.py │
│  (动态分析)      │   │  (GDB 控制器)    │   │   (注入逻辑)     │
└────────┬────────┘   └────────┬────────┘   └────────┬────────┘
         │                     │                     │
         │    ┌────────────────┴────────────────┐    │
         │    │                                 │    │
         ▼    ▼                                 ▼    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         目标 HPC 应用程序                                │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 2. 核心组件职责

### 2.1 Pin 工具链 (`toolbase/obj-intel64/`)

| 工具模块 | 文件名 | 功能 |
|---------|--------|------|
| **instcount.so** | `instcount.so` | 统计程序动态指令总数 |
| **randomInst.so** | `randomInst.so` | 在指定动态指令位置提取指令信息 |
| **determineInst.so** | `determineInst.so` | 计算特定 PC 值的迭代次数 |
| **findnextinst.so** | `findnextinst.so` | 获取崩溃点下一条指令及寄存器信息 |
| **faultinjection.so** | `faultinjection.so` | Pin 方式故障注入（带调试端口） |

### 2.2 GDB 控制器 (`sighandler.py`)

```python
class SigHandler:
    """
    核心功能:
    1. 通过 pexpect 控制 GDB 进程
    2. 设置信号处理 (SIGSEGV, SIGBUS, SIGABRT, SIGFPE)
    3. 故障注入 (断点方式 / Pin 远程调试方式)
    4. 崩溃检测与 LetGo 恢复策略执行
    """
```

### 2.3 故障注入器 (`faultinject.py`)

```python
class FaultInjector:
    """
    核心功能:
    1. 调用 Pin 工具获取注入位置信息
    2. 生成单比特翻转故障值 (generateFaults)
    3. 获取崩溃点后续指令信息 (getNextPC)
    4. 获取栈帧大小信息 (get_stack_size)
    """
```

---

## 3. 两种故障注入模式

### 3.1 Breakpoint 模式（断点注入）

**适用场景**: `inject_random_or_targeted = "targeted"`

```
┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│  Pin 分析    │ ──► │  GDB 控制    │ ──► │  程序执行    │
│  获取位置    │      │  设置断点    │      │  到达断点    │
└─────────────┘      └─────────────┘      └──────┬──────┘
                                                  │
┌─────────────┐      ┌─────────────┐      ┌──────▼──────┐
│  继续执行    │ ◄── │  GDB 修改    │ ◄── │  读取寄存器  │
│  监控信号    │      │  寄存器值    │      │  注入故障    │
└─────────────┘      └─────────────┘      └─────────────┘
```

**详细流程 (`sighandler.py:214-541`)**:

1. **获取注入位置** (`inject_inst_by_breakpoint`)
   ```python
   fi = faultinject.FaultInjector(self.insts)
   args = fi.getBreakpoint  # 返回 [regmm, reg, pc, iteration]
   ```
   - `regmm`: 内存操作相关寄存器
   - `reg`: 普通寄存器
   - `pc`: 目标指令地址
   - `iteration`: PC 值在动态指令流中的迭代次数

2. **设置 GDB 断点**
   ```python
   GDB_BREAKPOINT = "break *" + str(hexpc)
   self.gdb_send(process, GDB_BREAKPOINT)
   ```

3. **运行到断点并迭代**
   ```python
   while iteration > 0:
       self.gdb_send(process, GDB_CONTINUE)
       iteration -= 1
   ```

4. **执行故障注入**
   ```python
   # 普通寄存器注入
   content = fi.generateFaults(content)  # 单比特翻转
   self.gdb_send(process, GDB_SET_REG + " $" + reg + "=" + content)

   # 内存寄存器注入
   self.gdb_send(process, GDB_SET_REG + " $" + regmm + "=" + content)
   ```

### 3.2 PinFI 模式（Pin 远程调试注入）

**适用场景**: `inject_random_or_targeted = "random"`

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              启动流程                                    │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   GDB 进程                          Pin + faultinjection.so             │
│   ┌────────┐                        ┌────────────────────────┐          │
│   │ spawn  │                        │ pin -appdebug          │          │
│   │  gdb   │                        │  -t faultinjection.so  │          │
│   │  app   │                        │  -- benchmark          │          │
│   └────┬───┘                        └───────────┬────────────┘          │
│        │                                        │                       │
│        │         target remote :端口            │                       │
│        │◄───────────────────────────────────────│                       │
│        │                                        │                       │
│   ┌────▼───────────────────────────────────────▼────┐                   │
│   │              GDB 远程调试 Pin 进程               │                   │
│   │          (Pin 已完成故障注入，等待继续)           │                   │
│   └─────────────────────────────────────────────────┘                   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

**详细流程 (`sighandler.py:544-590`)**:

1. **启动 Pin 进程（带调试端口）**
   ```python
   execlist = [
       'pin', '-appdebug',           # 启用调试模式
       '-t', configure.filib,         # faultinjection.so
       '-o', configure.pin_instcount,
       '-fi_activation', configure.activate,
       '-fioption', 'AllInst',
       '--', benchmark
   ]
   self.process_remote_target = pexpect.spawn(' '.join(execlist))
   ```

2. **提取调试端口**
   ```python
   self.process_remote_target.expect('target remote :')
   self.process_remote_target.expect('\r\n')
   port = self.process_remote_target.before.decode('utf-8').strip()
   ```

3. **GDB 连接远程目标**
   ```python
   gdb_command = f"target remote :{port}"
   self.gdb_send(process, gdb_command)
   ```

4. **Pin 工具完成注入后，GDB 接管调试**
   - Pin 在 `activate` 文件中记录注入信息
   - GDB 继续执行并监控信号

---

## 4. LetGo 恢复框架

### 4.1 恢复触发条件

当程序收到崩溃信号时触发恢复 (`sighandler.py:1271-1355`):

```python
if "received signal" in after_continue:
    self.info_at_signal(process)    # 收集崩溃信息
    self.letgo_frame(process)       # 执行恢复策略
    self.error_spread(process, 1)   # 检测错误传播
```

### 4.2 恢复策略 (h_1, h_2, h_3)

**LetGo 恢复流程 (`sighandler.py:821-1268`)**:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         LetGo 恢复框架                                   │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Step 1: 获取崩溃点 PC 值                                               │
│          print $pc → 解析 0x... 地址                                    │
│                                                                         │
│  Step 2: 调用 Pin 获取指令信息                                          │
│          fi.getNextPC(decpc) → [nextpc, regw, stack, flag, ...]        │
│                                                                         │
│  Step 3: 根据指令类型选择恢复策略                                        │
│          ┌─────────────────────────────────────────────────────────┐    │
│          │  flag == 2 (栈读取指令)                                  │    │
│          │  └─► h_1: 基于地址计算恢复                                │    │
│          │      address = base + displacement + index * scale       │    │
│          │      set $regw = *address                                │    │
│          ├─────────────────────────────────────────────────────────┤    │
│          │  flag == 3 (非栈操作指令)                                 │    │
│          │  └─► h_2: 默认值恢复                                      │    │
│          │      set $regw = 0                                       │    │
│          ├─────────────────────────────────────────────────────────┤    │
│          │  flag == 1 (栈写入指令)                                   │    │
│          │  └─► h_3: 栈指针恢复                                      │    │
│          │      检测栈溢出: abs(rsp - rbp) > stack_size             │    │
│          │      set $rbp = rsp + size 或 set $rsp = rbp - size     │    │
│          └─────────────────────────────────────────────────────────┘    │
│                                                                         │
│  Step 4: 设置 PC 到下一条指令                                           │
│          set $pc = nextpc                                               │
│                                                                         │
│  Step 5: 继续执行程序                                                   │
│          continue                                                       │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 4.3 恢复策略详解

| 策略 | 名称 | 触发条件 | 恢复方法 | 代码位置 |
|------|------|----------|----------|----------|
| **h_1** | 栈读取修复 | `flag == 2` | 重新计算内存地址，读取正确值 | `sighandler.py:952-1084` |
| **h_2** | 默认值修复 | `flag == 3` | 将目标寄存器设为 0 | `sighandler.py:1086-1104` |
| **h_3** | 栈指针修复 | `flag == 1/2` | 根据栈帧大小修复 rbp/rsp | `sighandler.py:1112-1238` |

---

## 5. 数据流与文件交互

### 5.1 Pin 生成的临时文件

| 文件名 | 生成工具 | 内容 | 用途 |
|--------|----------|------|------|
| `instruction` | randomInst.so | `mem:`, `reg:`, `pc:` | 注入位置信息 |
| `iteration` | determineInst.so | 迭代次数 | 断点次数计算 |
| `nextpc` | findnextinst.so | `nextpc:`, `regw:`, `stack:`, ... | 恢复信息 |
| `spsize` | findnextinst.so | 栈帧大小 | h_3 策略使用 |
| `activate` | faultinjection.so | 注入激活信息 | PinFI 模式 |
| `pin.instcount.txt` | instcount.so | 动态指令总数 | 随机注入范围 |

### 5.2 日志文件结构

```
log_folder/
├── log_0          # 第 0 次实验日志
├── log_1          # 第 1 次实验日志
├── ...
└── log_N          # 第 N 次实验日志

每个日志包含:
- 注入参数 (args ready for set breakpoint)
- 注入指令 (display the inject inst)
- 恢复过程 (Letgo in!, h_1/h_2/h_3)
- 错误传播距离 (Valid Inj2Sig, Valid Fix2Sig)
- 最终结果 (Masked/SDC/C-Masked/C-SDC/Recrash)
```

---

## 6. GDB 命令交互封装

### 6.1 核心 GDB 命令

```python
# sighandler.py 中定义的 GDB 命令常量
GDB_LAUNCH = "gdb " + configure.benchmark
GDB_RUN = "run"
GDB_CONTINUE = "continue"
GDB_NEXT = "stepi"
GDB_PRINT_PC = "print $pc"
GDB_PRINT_REG = "print"
GDB_SET_REG = "set"
GDB_DISPLAY = "x/i $pc"
GDB_BEFOREPC = "disassemble $pc-120, $pc"
GDB_DELETE_BP = "delete breakpoints"

# 信号处理设置
GDB_HANDLE_SEGV = "handle SIGSEGV nopass"
GDB_HANDLE_BUS = "handle SIGBUS nopass"
GDB_HANDLE_ABT = "handle SIGABRT nopass"
GDB_HANDLE_FPE = "handle SIGFPE nopass"
```

### 6.2 GDB 交互封装方法

```python
def gdb_send(self, process, command, description="", timeout=None):
    """
    统一的 GDB 交互方法

    返回值:
        (0, response) - 超时
        (1, response) - 成功
        (2, response) - EOF
    """
    process.sendline(command)
    i = process.expect([pexpect.TIMEOUT, GDB_PROMOPT])
    return i, process.before.decode('utf-8').strip()
```

---

## 7. 典型执行流程

### 7.1 Breakpoint 模式完整流程

```
1. letgo_wrapper.py 启动
   │
   ├─► Pin instcount.so 统计动态指令数
   │
   ├─► (如果 targeted) 生成指令池
   │
   └─► 循环执行实验 (i = 0 to numFI)
       │
       ├─► 创建 SigHandler 实例
       │   └─► pexpect.spawn("gdb benchmark")
       │
       ├─► executeProgram()
       │   ├─► 配置信号处理
       │   └─► inject_by_breakpoint_and_recover()
       │
       ├─► inject_inst_by_breakpoint()
       │   ├─► Pin randomInst.so 获取注入位置
       │   ├─► Pin determineInst.so 获取迭代次数
       │   ├─► GDB: break *pc
       │   ├─► GDB: run args
       │   ├─► GDB: continue × iteration
       │   ├─► GDB: print $reg
       │   ├─► 生成故障值 (单比特翻转)
       │   └─► GDB: set $reg = fault_value
       │
       ├─► handle_after_injection()
       │   ├─► GDB: continue
       │   │
       │   ├─► [如果收到信号]
       │   │   ├─► info_at_signal() 收集信息
       │   │   ├─► letgo_frame() 执行恢复
       │   │   │   ├─► Pin findnextinst.so 获取恢复信息
       │   │   │   ├─► 执行 h_1/h_2/h_3 策略
       │   │   │   └─► GDB: set $pc = nextpc
       │   │   └─► error_spread() 检测错误传播
       │   │
       │   └─► [如果无信号]
       │       └─► 可能是 Masked 或 SDC
       │
       └─► SDC_saver() 保存结果
```

### 7.2 PinFI 模式完整流程

```
1. letgo_wrapper.py 启动
   │
   └─► 循环执行实验
       │
       ├─► 创建 SigHandler 实例
       │   └─► pexpect.spawn("gdb benchmark")
       │
       ├─► executeProgram()
       │   └─► inject_by_pinfi_and_recover()
       │
       ├─► inject_inst_by_faultinjection()
       │   ├─► pexpect.spawn("pin -appdebug -t faultinjection.so ...")
       │   ├─► 等待 "target remote :" 输出
       │   ├─► 提取端口号
       │   └─► GDB: target remote :端口
       │
       ├─► handle_after_injection()
       │   └─► (同 Breakpoint 模式的恢复流程)
       │
       └─► 读取 Pin 进程输出
           └─► 保存 SDC 结果
```

---

## 8. 关键代码位置索引

| 功能 | 文件 | 行号 | 方法/函数 |
|------|------|------|-----------|
| 主循环入口 | `letgo_wrapper.py` | 216-251 | `main` |
| GDB 进程创建 | `sighandler.py` | 92-100 | `__init__` |
| 断点注入 | `sighandler.py` | 214-541 | `inject_inst_by_breakpoint` |
| PinFI 注入 | `sighandler.py` | 544-590 | `inject_inst_by_faultinjection` |
| 信号后处理 | `sighandler.py` | 1271-1355 | `handle_after_injection` |
| LetGo 恢复框架 | `sighandler.py` | 821-1268 | `letgo_frame` |
| 错误传播检测 | `sighandler.py` | 666-762 | `error_spread` |
| 获取断点位置 | `faultinject.py` | 81-190 | `getBreakpoint` |
| 获取恢复信息 | `faultinject.py` | 278-318 | `getNextPC` |
| 故障值生成 | `faultinject.py` | 235-260 | `generateFaults` |

---

## 9. 配置参数说明

```python
# configure.py 关键配置

# 注入模式选择
inject_random_or_targeted = "targeted"  # 或 "random"

# 注入工具自动选择
if inject_random_or_targeted == "targeted":
    inject_tool = 'breakpoint'  # 使用 GDB 断点注入
if inject_random_or_targeted == "random":
    inject_tool = 'pinfi'       # 使用 Pin 远程调试注入

# 实验次数
numFI = 5000

# PC 地址范围 (targeted 模式)
pcstart = "401cb8"
pcend = "49877c"

# 调试开关
debugfile = 0        # 是否生成调试日志
gdb_verbose = False  # 是否显示 GDB 交互
```

---

## 10. 总结

LetGo 框架通过 Pin 和 GDB 的紧密协作实现了完整的故障注入与恢复实验：

1. **Pin** 负责:
   - 动态指令分析和位置定位
   - 提供指令元信息（寄存器、内存操作、栈信息）
   - PinFI 模式下的故障注入

2. **GDB** 负责:
   - 程序执行控制（断点、单步、继续）
   - 寄存器读取和修改
   - 信号捕获和处理
   - 恢复策略的执行

3. **协作关键点**:
   - Breakpoint 模式：Pin 分析 → GDB 注入 → GDB 恢复
   - PinFI 模式：Pin 注入 + 调试端口 → GDB 远程连接 → GDB 恢复

这种设计使得框架既能进行精确的目标类型注入（Breakpoint），又能进行高效的随机注入（PinFI），同时保持了统一的恢复策略执行流程。
