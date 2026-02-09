# 指令剖析故障排查

## 失败应用分析

### 1. knn (退出码 1)

**问题**: 应用程序运行时失败，输出 "error opening flist"

**原因**: knn程序需要读取 `filelist.txt` 文件，该文件在应用的工作目录中，但剖析时可能从错误的目录执行。

**日志输出**:
```
[Instruction Profiler] Total instructions analyzed: 559
error opening flist
```

**解决方案**:
1. 检查 `filelist.txt` 是否存在于正确位置
2. 确保程序从正确的工作目录运行

**验证**:
```bash
cd /home/tongshiyu/programs/rodinia-master/openmp/nn
./nn cane10k.db 5 30 90
```

**状态**: ⚠️ 应用程序问题（已生成JSON文件，但应用执行失败）

---

### 2. miniAMR (退出码 255)

**问题**: MPI应用参数解析失败

**原因**: configure.py 中的参数格式不正确
```python
optionlist = ["--npx 1 --npy 1 --npz 1", "--report_diffusion","--checksum_freq", "10"]
```
第一个参数 `"--npx 1 --npy 1 --npz 1"` 是单个字符串，应该拆分为独立的参数。

**错误信息**:
```
** Error ** Unknown input parameter --npx 1 --npy 1 --npz 1
```

**解决方案**: 修改 `/home/tongshiyu/pin/source/tools/letgo/configure.py`

**修改前**:
```python
elif progname == "miniAMR":
    progbin = "/home/tongshiyu/programs/mantevo/miniAMR/ref/miniAMR.x"
    optionlist = ["--npx 1 --npy 1 --npz 1", "--report_diffusion","--checksum_freq", "10"]
```

**修改后**:
```python
elif progname == "miniAMR":
    progbin = "/home/tongshiyu/programs/mantevo/miniAMR/ref/miniAMR.x"
    optionlist = ["--npx", "1", "--npy", "1", "--npz", "1", "--report_diffusion", "--checksum_freq", "10"]
```

**验证**:
```bash
mpirun -np 1 /home/tongshiyu/programs/mantevo/miniAMR/ref/miniAMR.x --npx 1 --npy 1 --npz 1 --report_diffusion --checksum_freq 10
```

**状态**: ❌ 需要修复 configure.py

---

### 3. gaussian (退出码 2)

**问题**: 二进制文件不存在

**原因**: configure.py 中指定的文件路径不存在
```python
progbin = "/home/tongshiyu/programs/PolyBenchC-4.2.1/bin/gaussian_ref"
```

**错误信息**:
```
/home/tongshiyu/programs/PolyBenchC-4.2.1/bin/gaussian_ref : No such file or directory
```

**验证**:
```bash
ls /home/tongshiyu/programs/PolyBenchC-4.2.1/bin/ | grep gaussian
# 无输出，文件不存在
```

**解决方案**:
1. **选项A**: 编译 gaussian 程序
   ```bash
   cd /home/tongshiyu/programs/PolyBenchC-4.2.1
   # 查找 gaussian 源代码并编译
   ```

2. **选项B**: 从应用列表中移除
   修改 configure.py，从 PolyBenchtList 中移除 'gaussian'

**状态**: ❌ 文件缺失，需要编译或从列表移除

---

### 4. convolution (退出码 2)

**问题**: 二进制文件不存在

**原因**: configure.py 中指定的文件路径不存在
```python
progbin = "/home/tongshiyu/programs/PolyBenchC-4.2.1/bin/convolution_ref"
```

**错误信息**:
```
/home/tongshiyu/programs/PolyBenchC-4.2.1/bin/convolution_ref : No such file or directory
```

**验证**:
```bash
ls /home/tongshiyu/programs/PolyBenchC-4.2.1/bin/ | grep convolution
# 无输出，文件不存在
```

**解决方案**:
1. **选项A**: 编译 convolution 程序
   ```bash
   cd /home/tongshiyu/programs/PolyBenchC-4.2.1
   # 查找 convolution 源代码并编译
   ```

2. **选项B**: 从应用列表中移除
   修改 configure.py，从 PolyBenchtList 中移除 'convolution'

**状态**: ❌ 文件缺失，需要编译或从列表移除

---

## 快速修复脚本

### 修复 miniAMR 参数问题

```bash
cd /home/tongshiyu/pin/source/tools/letgo
cp configure.py configure.py.backup

# 手动编辑 configure.py，找到 miniAMR 配置并修改参数列表
```

### 从列表移除缺失的应用

如果不需要编译 gaussian 和 convolution，可以临时从批量剖析中排除它们：

```bash
# 使用 --exclude 参数
python profile_batch.py --suite polybench --exclude gaussian,convolution
```

或者永久修改 configure.py：

```python
# 修改前
PolyBenchtList = ['2mm','bicg','correlation','fdtd-2d','gesummv','syr2k','gaussian','convolution','mvt']

# 修改后
PolyBenchtList = ['2mm','bicg','correlation','fdtd-2d','gesummv','syr2k','mvt']
```

---

## 总结

| 应用 | 退出码 | 问题类型 | 优先级 | 修复难度 |
|------|--------|----------|--------|----------|
| knn | 1 | 应用运行时错误 | 低 | 中 |
| miniAMR | 255 | 配置文件参数格式错误 | **高** | 简单 |
| gaussian | 2 | 二进制文件缺失 | 中 | 中 |
| convolution | 2 | 二进制文件缺失 | 中 | 中 |

**建议优先修复**: miniAMR（只需修改一行配置）

---

## 验证修复

修复后重新运行：

```bash
# 单个应用测试
python profile_single.py miniAMR

# 批量测试（排除问题应用）
python profile_batch.py --suite mantevo
python profile_batch.py --suite polybench --exclude gaussian,convolution

# 测试 knn
python profile_single.py knn
```
