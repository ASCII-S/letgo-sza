import pexpect
import configure

def count_instructions_with_gdb(progbin, optionlist):
    """
    使用 gdb 和 pexpect 对指定的程序进行逐步指令计数。
    
    参数:
        progbin (str): 可执行文件的路径
        optionlist (list): 传递给程序的参数列表
    """
    # 构建 GDB 命令
    gdb_command = f"gdb --quiet --args {progbin} " + " ".join(optionlist)
    print(f"Running: {gdb_command}")

    # 启动 GDB 并加载目标程序
    process = pexpect.spawn(gdb_command, encoding='utf-8', timeout=10)
    
    # 期待 GDB 提示符
    process.expect_exact("(gdb)")
    
    # 运行程序直到遇到第一个断点或停止位置
    process.sendline("start")
    process.expect_exact("(gdb)")
    
    instruction_count = 0  # 指令计数器
    
    try:
        while True:
            # 执行单步指令 (stepi)
            process.sendline("stepi")
            index = process.expect(["(gdb)", pexpect.TIMEOUT, pexpect.EOF])
            
            if index == 0:
                # 成功执行 stepi，增加计数
                instruction_count += 1
                #print(f"Instruction count: {instruction_count}")
            else:
                # 出现超时或结束
                break

    except KeyboardInterrupt:
        print("Process interrupted by user.")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        # 结束 GDB
        process.sendline("quit")
        process.close()

    print(f"Total instructions executed: {instruction_count}")

# 使用方法
if __name__ == "__main__":
    # 替换为你的可执行文件路径
    count_instructions_with_gdb(configure.progbin, configure.optionlist)

