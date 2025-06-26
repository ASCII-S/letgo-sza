import os
import sys
import re
import pexpect

import objdump
import faultinject
import configure
import random
import shutil
import datetime
import InstPoolMaker
import sdcjudger
import time

GDB_PROMOPT = "\(gdb\)"
GDB_RUN = "run"
GDB_LAUNCH = "gdb " + configure.benchmark
GDB_HANDLE_BUS = "handle SIGBUS nopass"
GDB_HANDLE_SEGV = "handle SIGSEGV nopass"
GDB_HANDLE_ABT = "handle SIGABRT nopass"
GDB_HANDLE_FPE = "handle SIGFPE nopass"
GDB_HANDLE_ALL = "handle all stop print"

GDB_PRINT_PC = "print $pc"
GDB_CONTINUE = "continue"
GDB_NEXT = "stepi"
GDB_PRINT_REG = "print"
GDB_SET_REG = "set"
GDB_FAKE = "0"
GDB_DELETE_BP = "delete breakpoints"
GDB_DISPLAY = "x/i $pc"
GDB_BEFOREPC = "disassemble $pc-120, $pc"
GDB_SETPAGEOFF = "set pagination off"
GDB_RECORD = "record"

GDB_ERROR_SEGV = "Program received signal SIGSEGV"
GDB_ERROR_BUS = "Program received signal SIGBUS"
GDB_ERROR_ABT = "Program received signal SIGABRT"

MAX_ERROR_SPREAD = 50
PRT_ERR_LEN_INJ_SIG = "Valid Inj2Sig:"
PRT_ERR_LEN_FIX_SIG = "Valid Fix2Sig:"
PRT_ERR_LEN_MAX = "Safe " + str(MAX_ERROR_SPREAD)
PTR_ERR_INJ_MAX = "After Inject:" + PRT_ERR_LEN_MAX
PTR_ERR_FIX_MAX = "After Fixed:" + PRT_ERR_LEN_MAX

#debug file
debugfile = configure.debugfile

set_reg_fake = 1 ##h_1,h_2
is_rewind = 1   ##h_3
force_fix_rbp = 0

##log_path = "./self.log"
log_path = configure.log_folder
if not os.path.exists(log_path):
    os.makedirs(log_path)
    
def is_hexnumber(s):
    try:
        int(s,16)
        return True
    except ValueError:
        return False

def is_number(value):
    return value.isdigit()  # 如果是整数返回 True

class SigHandler:
    def __init__(self, insts, trial):
        self.insts = int(insts)
        self.trial = trial
        self.verbose_gdb = configure.gdb_verbose  # 控制是否显示GDB交互信息，默认不显示
        
        logname = os.path.join(log_path,('log_'+str(self.trial) ))
        self.log = open(str(logname), "w", buffering=1)
        sys.stdout = self.log
        sys.stderr = self.log

        

        self.sig_start_time = datetime.datetime.now()
        self.sig_end_time = datetime.datetime.now()
        self.letgo_start_time = datetime.datetime.now()
        
        self.process_remote_target = None
        if debugfile == 1:
            remote_target_logname = 'remote_target.txt'
            self.logfile2 = open(remote_target_logname, 'wb')

        launch = GDB_LAUNCH
        if configure.MPI_SET == 1:
            launch = " ".join(configure.mpi_cmd) + " " + launch
        self.process = pexpect.spawn(launch)
        if debugfile == 1:
            #self.process.logfile = sys.stdout.buffer
            process_logname = 'process.txt'
            self.logfile = open(process_logname, 'wb')
            self.process.logfile = self.logfile

        print("do pexpect.spawn: gdb  has launched!")
        print(GDB_LAUNCH)

    def gdb_sendline_and_expect(self, process, command, description="", timeout=None, verbose=False):
        """
        统一的GDB交互方法，发送命令并等待响应，使用统一的打印格式
        
        Args:
            process: pexpect进程对象
            command: 要发送给GDB的命令
            description: 命令描述，用于日志
            timeout: 超时时间，None表示使用默认值
            verbose: 是否打印交互信息，默认False不打印
            
        Returns:
            tuple: (返回码, 响应内容)
            返回码: 0=超时, 1=成功, 2=EOF
        """
        if verbose:
            print(f"[send gdb] {command}" + (f" #{description}" if description else ""))
        
        process.sendline(command)
        
        expect_list = [pexpect.TIMEOUT, GDB_PROMOPT]
        if timeout is not None:
            i = process.expect(expect_list, timeout=timeout)
        else:
            i = process.expect(expect_list)
            
        response = process.before.decode('utf-8').strip()
        
        if i == 0:
            if verbose:
                print(f"[gdb timeout] {response}")
            return 0, response
        elif i == 1:
            # 只有当响应不为空且不等于命令本身时才打印响应
            if verbose and response.strip() and response.strip() != command.strip():
                print(f"[gdb response] {response}")
            return 1, response
        else:
            if verbose:
                print(f"[gdb eof] {response}")
            return 2, response

    def gdb_sendline_and_expect_extended(self, process, command, description="", timeout=None, 
                                       expect_patterns=None, pattern_names=None, verbose=False):
        """
        扩展的GDB交互方法，支持自定义expect模式
        
        Args:
            process: pexpect进程对象
            command: 要发送给GDB的命令
            description: 命令描述
            timeout: 超时时间
            expect_patterns: 自定义的expect模式列表
            pattern_names: 对应的模式名称列表
            verbose: 是否打印交互信息，默认False不打印
            
        Returns:
            tuple: (匹配的模式索引, 响应内容)
        """
        if verbose:
            print(f"[send gdb] {command}" + (f" #{description}" if description else ""))
        
        process.sendline(command)
        
        if expect_patterns is None:
            expect_patterns = [pexpect.TIMEOUT, GDB_PROMOPT, pexpect.EOF]
            pattern_names = ["TIMEOUT", "PROMPT", "EOF"]
        
        if timeout is not None:
            i = process.expect(expect_patterns, timeout=timeout)
        else:
            i = process.expect(expect_patterns)
            
        response = process.before.decode('utf-8').strip()
        
        if pattern_names and i < len(pattern_names):
            # 只有当响应不为空且不等于命令本身时才打印响应
            if verbose and response.strip() and response.strip() != command.strip():
                print(f"[gdb {pattern_names[i].lower()}] {response}")
        else:
            if verbose and response.strip() and response.strip() != command.strip():
                print(f"[gdb pattern_{i}] {response}")
            
        return i, response

    def gdb_send(self, process, command, description="", timeout=None):
        """简化的GDB交互方法，使用类的verbose设置"""
        return self.gdb_sendline_and_expect(process, command, description, timeout, verbose=self.verbose_gdb)
    
    def gdb_send_extended(self, process, command, description="", timeout=None, expect_patterns=None, pattern_names=None):
        """简化的扩展GDB交互方法，使用类的verbose设置"""
        return self.gdb_sendline_and_expect_extended(process, command, description, timeout, expect_patterns, pattern_names, verbose=self.verbose_gdb)
    
    def enable_gdb_verbose(self):
        """启用GDB交互信息显示"""
        self.verbose_gdb = True
    
    def disable_gdb_verbose(self):
        """禁用GDB交互信息显示"""
        self.verbose_gdb = False
    
    def gdb_send_verbose(self, process, command, description="", timeout=None,verbose=True):
        """强制GDB交互信息的方法"""
        return self.gdb_sendline_and_expect(process, command, description, timeout, verbose=verbose)
    
    def gdb_send_extended_force(self, process, command, description="", timeout=None, expect_patterns=None, pattern_names=None,verbose=True):
        """强制GDB交互信息的扩展方法"""
        return self.gdb_sendline_and_expect_extended(process, command, description, timeout, expect_patterns, pattern_names, verbose=verbose)

    def inject_inst_by_breakpoint(self,process):
    # Prepare gdb run
        ###  IMPORTANT: 以下输出格式由analyze.py解析，请勿随意修改关键字符串
        ###  关键解析标记: "args ready for set breakpoint:", "display the inject inst start", "Fault injection is done"
        ori_reg = ""

        GDB_RUN = "run"
        for item in configure.args:
            GDB_RUN += " " + item

    # Set a breakpoint: need pc and iteration number
        ##
        print('Start set a breakpoint...')
        fi = faultinject.FaultInjector(self.insts)
        if configure.inject_random_or_targeted == "random":
            try:
                ##首先尝试从随机指令池中提取指令
                result = InstPoolMaker.readArgsFromPool()
                # 检查 result 的长度是否为 5
                if len(result) != 5:
                    raise ValueError("Wrong return values! Exit!")  # 抛出异常跳转到 except 块
                args = result[0:4]
                randomnum = result[-1]
                print("-randinst", randomnum)  ###  IMPORTANT: analyze.py解析此格式提取随机指令序号
            except:
                ##指令池空，则直接随机找指令
                args = fi.getBreakpoint  # [regmm, reg, pc, iteration]

        if configure.inject_random_or_targeted == "targeted":
            pool_file = configure.pool_csv_file
            if not os.path.exists(pool_file):
                print(f"Error: File '{pool_file}' does not exist.")
                sys.exit(1)
            if os.path.getsize(pool_file)==0:
                print(f"Error: File '{pool_file}' is empty.")
                sys.stdout = sys.__stdout__
                print("Finish all!!!\tindex start: {start}, index end: {end}")
                sys.exit(1)
            result = InstPoolMaker.readArgsFromPool(pool_file)
            #兼容原来的输出
            args = result[0:4]
            randomnum = result[-1]
            # random_number = random.randint(0, 128)
            # args.append(str(random_number))
            print(args)


        ##参数中包含的是在动态指令randomnum处的指令和寄存器信息.pc是该动态指令的ins值,regmm或reg是ins中随机挑选的寄存器
        ##iteration表示的是在randomnum范围内,ins值和pc值相同的次数;也就是pc值在randomnum范围内的迭代次数
        if len(args) != 4:
            print("Wrong return values! Exit!")
            self.log.close()
            process.close()
            sys.stdout = sys.__stdout__
            sys.exit(1)
            return

        regmm = args[0].rstrip("\n")    ##
        reg = args[1].rstrip("\n")
        pc = args[2].rstrip("\n")
        iteration = int(args[3].rstrip("\n"))
        # next = hex(int(args[4]))
        print('args ready for set breakpoint:\t',args)  ###  IMPORTANT: analyze.py解析此行提取注入参数
        hexpc = hex(int(pc))
        print('hexpc\t',hexpc)
        GDB_BREAKPOINT = "break *" + str(hexpc)
        i, bp_response = self.gdb_send(process, GDB_BREAKPOINT, f"设置断点在地址{hexpc}")
        if i == 0:
            print('ERROR! Could not set the breakpoint')
            print((str(process)))
            self.log.close()
            process.close()
            sys.stdout = sys.__stdout__
            return
        if i == 1:
            print(bp_response)
            print('Successfully set the breakpoint')

    # run application to target breakpoint
        ##


        i, output = self.gdb_send(process, GDB_RUN, "运行程序到断点")
        if i == 0:
            print('ERROR! Could not run the program')
            self.log.close()
            process.terminate()
            process.close()
            sys.stdout = sys.__stdout__
            return
        if i == 1:
            print('----------------------Start output----------------------\n',output,'\n----------------------End output----------------------')
            if "Breakpoint" not in output:
                print("no such Breakpoint:\t",hexpc)
                self.log.close()
                process.terminate()
                process.close()
                sys.stdout = sys.__stdout__
                return
            if "Breakpoint" in output:
                print("Pause at the breakpoint for the first time!")
                # inject a fault
                print('start inject a fault')
                if iteration > 1024:
                    iteration = iteration%1024 #random.randint(0, 1024)
                print('rechoose iteration in range (0,1024):\t',iteration)
                # while iteration > 0:
                #     process.sendline(GDB_CONTINUE)
                #     i = process.expect([pexpect.TIMEOUT, GDB_PROMOPT])
                #     if i == 0:
                #         print('ERROR while continuing the program')
                #         print((process.before.decode('utf-8'), process.after))
                #         print((str(process)))
                #         self.log.close()
                #         process.close()
                #         sys.stdout = sys.__stdout__
                #         return
                #     if i == 1:
                #         iteration -= 1
                while iteration > 0:
                    try:
                        i, continue_output = self.gdb_send_extended(
                            process, GDB_CONTINUE, f"继续执行到断点(剩余{iteration}次)",
                            timeout=2, expect_patterns=[pexpect.TIMEOUT, GDB_PROMOPT, pexpect.EOF],
                            pattern_names=["TIMEOUT", "PROMPT", "EOF"])
                        
                        if i == 0:
                            print('ERROR while continuing the program')
                            print((str(process)))
                            self.log.close()
                            process.close()
                            sys.stdout = sys.__stdout__
                            return
                        
                        if i == 1:
                            iteration -= 1

                        if i == 2:  # 如果是 pexpect.EOF，说明进程已退出
                            print("Process has exited (iteration over runtime).")
                            return
                    except pexpect.ExceptionPexpect as e:
                        print(f"pexpect error: {e}")
                        process.close()
                        sys.stdout = sys.__stdout__
                        return

    # print out the current instruction for more info
                ###
                
                #process.interact()
                
                i, response = self.gdb_send_verbose(process, GDB_SETPAGEOFF, "关闭分页")

                i, output = self.gdb_send_verbose(process, GDB_BEFOREPC, "显示注入点前的指令")
                if i == 0:
                    print("ERROR when displaying the insts before inject place")
                    print((str(process)))
                    self.log.close()
                    process.close()
                    sys.stdout = sys.__stdout__
                    return
                if i == 1:
                    #print("\nbefore inject inst:--------------------------------------\t\n:",output,"before inject inst end:--------------------------------------\n")
                    pass

    # No.iteration breakpoint
                i, save_response = self.gdb_send_verbose(process, "set $saved_pc = $pc", "保存当前PC值")
                i, inject_inst = self.gdb_send_extended(
                    process, "x/i $saved_pc", "显示要注入的指令",
                    expect_patterns=[pexpect.TIMEOUT, GDB_PROMOPT, pexpect.EOF],
                    pattern_names=["TIMEOUT", "PROMPT", "EOF"])
                if i == 0:
                    print("ERROR when displaying the inst")
                    print((str(process)))
                    self.log.close()
                    process.close()
                    sys.stdout = sys.__stdout__
                    return
                if i == 1:
                    print("display the inject inst start:\n",inject_inst.strip(),"\ndisplay the inject inst end.")  ###  IMPORTANT: analyze.py解析此行提取注入指令
                if i == 2:
                    print("process end")
                    return

    # inject reg
                if regmm == "":  # it means that it is a normal instruction and we need to inject the fault to the dest reg
                    print('Meet a normal instruction:')
                    i, output = self.gdb_send(process, GDB_NEXT, "单步执行指令")
                    print(output)
                    if i == 0:
                        print('ERROR! Can not step in')
                        print((str(process)))
                        self.log.close()
                        process.close()
                        sys.stdout = sys.__stdout__
                        return
                    if i == 1:
                        i, reg_output = self.gdb_send_verbose(process, GDB_PRINT_REG + " $" + reg, f"获取寄存器{reg}的值")
                        if i == 0:
                            print('ERROR while analyzing the content of the register')
                            print((str(process)))
                            self.log.close()
                            sys.stdout = sys.__stdout__
                            print("exit due to sighandle: timeout")
                            sys.exit(1)
                        if i == 1:
                            output = reg_output
                            print("print reg:\t",output)
                            content = ""
                            if "0x" in output:
                                items = output.split(" ")
                                for item in items:
                                    if "0x" in item:
                                        content = item
                            else:
                                items = output.split(" ")
                                content = items[len(items) - 1]
                            content = content.lstrip("nan")
                            content = content.lstrip("-nan")
                            content = fi.generateFaults(content)
                            i, set_output = self.gdb_send_verbose(process, GDB_SET_REG + " $" + reg + "=" + content, f"向寄存器{reg}注入故障值{content}")
                            if i == 0:
                                print('ERROR while waiting for changing the value')
                                print((str(process)))
                                self.log.close()
                                process.close()
                                sys.stdout = sys.__stdout__
                                return
                            if i == 1:
                                output = set_output
                                if "=" in output:
                                    print(output)
                                    print("Fault injection is done")

    # inject regmm                                    
                if reg == "":  # it means that it is a memory instruction. Need to inject before it is executed.
                    print('Meet a memory instruction:')
                    i, output = self.gdb_send_verbose(process, GDB_PRINT_REG + " $" + regmm, f"获取内存寄存器{regmm}的值")
                    if i == 0:
                        print('ERROR while analyzing the content of the register mem')
                        print((str(process)))
                        self.log.close()
                        process.close()
                        sys.stdout = sys.__stdout__
                        return
                    if i == 1:
                        content = ""
                        if "0x" in output:
                            items = output.split(" ")
                            for item in items:
                                if "0x" in item:
                                    content = item
                        else:
                            items = output.split(" ")
                            content = items[len(items) - 1]
                        content = content.lstrip("nan")
                        content = content.lstrip("-nan")
                        print("content:\t",content)
                        ori_reg = content.rstrip("\r\n")
                        if content!="":
                            content = fi.generateFaults(content)
                        else:
                            print('error! content is null!')
                        i, mem_output = self.gdb_send_verbose(process, GDB_SET_REG + " $" + regmm + "=" + content, f"向内存寄存器{regmm}注入故障值{content}")
                        if i == 0:
                            print('ERROR while waiting for changing the value mem')
                            print((str(process)))
                            self.log.close()
                            process.close()
                            sys.stdout = sys.__stdout__
                            return
                        if i == 1:
                            output = mem_output
                            if "=" in output:
                                print(output)
                                print("Fault injection is done mem")
                        ## change the regmm back to its original data after execution
                        ## need to single step one inst
                        try:
                            inject_op = inject_inst.split("=>")[1].split(":")[1].strip().split(" ")[0]
                            print("op:\t",inject_op)
                        except:
                            print("inject_inst:\t",inject_inst)
                            sys.exit()

                        ##对内存相关额寄存器注错后还原寄存器的值
                        # if 'j' not in inject_op:
                        #     process.sendline(GDB_NEXT)
                        #     i = process.expect([pexpect.TIMEOUT, GDB_PROMOPT])
                        #     if i == 0:
                        #         print("ERROR when single step")
                        #         print(process.before.decode('utf-8'), process.after)
                        #         print(str(process))
                        #         self.log.close()
                        #         process.close()
                        #         sys.stdout = sys.__stdout__
                        #         return
                        #     if i == 1:
                        #         print("Single step")
                        #         output = process.before.decode('utf-8')
                        #         if 'received signal' in output:
                        #             print("Crash after single step, considered working!")


                        #     process.sendline(GDB_SET_REG + " $" + regmm + "=" + ori_reg)
                        #     i = process.expect([pexpect.TIMEOUT, GDB_PROMOPT])
                        #     if i == 0:
                        #         print("ERROR when setting the regmm back after single step")
                        #         print(process.before.decode('utf-8'), process.after)
                        #         print(str(process))
                        #         self.log.close()
                        #         process.close()
                        #         sys.stdout = sys.__stdout__
                        #         return
                        #     if i == 1:
                        #         print("Change the value back")
                        
    # del breakpoints
                """print("GDB is now interactive. You can type GDB commands.")
                process.interact()  # 交互模式，允许用户直接控制 GDB"""

                i, delete_response = self.gdb_send(process, GDB_DELETE_BP, "删除所有断点")
                if i == 0:
                    print("ERROR when deleting breakpoints")
                    print((str(process)))
                    self.log.close()
                    process.close()
                    sys.stdout = sys.__stdout__
                    return
                if i == 1:
                    print(delete_response)
                    print("Delete all breakpoints")


    def inject_inst_by_faultinjection(self,process):
        # process 进入状态：gdb只指定了可执行文件
        # process 离开状态：pin对程序注错后保留调试端口，process通过远程端口调试用pin注错后的程序
        ###  IMPORTANT: 以下输出格式由analyze.py解析，请勿随意修改关键字符串
        ###  关键解析标记: "fi inject instance:", "Activated:", "bit location:"
        benchmark = configure.benchmark
        execlist = []
        if configure.MPI_SET == 1:
            execlist.extend(configure.mpi_cmd)
        if configure.progname in configure.OpenMpOutPutList:
            execlist = ["env","OUTPUT=1"]  # 设置环境变量 OUTPUT=1
        execlist.extend([
            'pin',
            '-appdebug',
            '-t', configure.filib,
            '-o', configure.pin_instcount,
            '-fi_activation', configure.activate,
            '-fioption', 'AllInst',
            "-index", str(self.trial),
            '--', benchmark
        ])
        execlist.extend(configure.args)

        print("launch process_remote_target:\t",' '.join(execlist))
        self.process_remote_target = pexpect.spawn(' '.join(execlist))
        if debugfile == 1:
            #self.process_remote_target.logfile =  sys.stdout.buffer
            self.process_remote_target.logfile = self.logfile2

        try:
            self.process_remote_target.expect('target remote :')
            self.process_remote_target.expect('\r\n')
            port = self.process_remote_target.before.decode('utf-8').strip()
            print("Extracted port:", port)

            gdb_command = f"target remote :{port}"
            print("process cmd:",gdb_command)

            i, response = self.gdb_send(process, gdb_command, f"连接到远程调试端口{port}")
            print("respone to 'target remote :' :\n",response)

            #print((process.before.decode('utf-8')))
        except:
            print("Port not found")
        
        print("inject inst by faultinjection has done")
        return self.process_remote_target

    def print_file_to_log(self,file_path):
        sys.stdout = self.log
        # 使用 with 打开文件，这样文件在读取后会自动关闭
        with open(file_path, 'r') as file:
            # 读取文件的所有内容
            file_content = file.read()
            
            # 打印文件内容
            print(file_content)

    def capture_process_output(process, output_file_path):
        """
        捕获pexpect进程的输出，并实时写入文件和控制台
        """
        try:
            # 打开文件用于写入
            with open(output_file_path, 'a') as output_file:

                while True:
                    try:
                        # 等待输出或结束符
                        i = process.expect([pexpect.EOF, pexpect.TIMEOUT], timeout=1)
                        output = process.before.decode('utf-8').strip()

                        if output:
                            # 实时写入文件和打印到控制台
                            output_file.write(output + '\n')
                            output_file.flush()  # 确保内容立即写入文件
                            print(output)

                        if i == 0:  # EOF: 进程结束
                            break

                    except pexpect.TIMEOUT:
                        # 捕获超时（非致命错误）
                        continue
                    except pexpect.exceptions.ExceptionPexpect as e:
                        # 捕获其他pexpect异常
                        print("Error while capturing output:", e)
                        break
        except Exception as e:
            print("Unexpected error:", e)

    def print_process(self, process, max_timeout_retries=10):
        """
        持续读取并打印进程输出，直到进程结束或达到最大超时次数。

        :param process: pexpect 进程对象
        :param max_timeout_retries: 最大超时重试次数
        :return: 进程的全部输出
        """
        alloutput = ''
        timeout_retries = 0  # 超时重试计数

        while True:
            try:
                output = process.read_nonblocking(size=1024, timeout=1)  # 每次读取 1024 字节
                if isinstance(output, bytes):
                    output = output.decode('utf-8')  # 如果是bytes，进行解码
                if output:
                    alloutput = alloutput + ' ' + output.strip()
                    timeout_retries = 0  # 重置超时计数器
            except pexpect.TIMEOUT:
                timeout_retries += 1  # 超时重试次数加1
                if timeout_retries >= max_timeout_retries:
                    #print("进程无输出，超时次数达到上限。")
                    break  # 达到最大重试次数时退出
            except pexpect.EOF:
                break  # 进程结束时退出

        return alloutput.strip()



    def error_spread(self,process,seq_casuse_signal):#此处的seq_casuse_signal是指错误引发点的序号,例如注错点是序号1,第一次修复则是2
        ##出发点是错误引发点,即注错点或第一次修复点,逐步执行,终点是收到signal或程序结束;返回值rcv_sig表示是否出错,output
        ##检查从注错/修复到出错的错误传播,只打印前MAX_ERROR_SPREAD长度的指令;当出现错误时,需要把signal打印,并且打印x/i $pc;当没有任何错误时;
        ###  IMPORTANT: 以下输出格式由analyze.py解析，请勿随意修改关键字符串
        ###  关键解析标记: "Valid Inj2Sig:", "Valid Fix2Sig:", "After Inject:", "After Fixed:"
        ##i = process.expect([pexpect.TIMEOUT, GDB_PROMOPT])
        #print((process.before.decode('utf-8'), process.after))
        stepi_num = 0
        output = 'NO OUTPUT'##用来保存出错类型,供接下来介入letgo_frame使用
        rcv_sig = 0

        buffer_clear = self.print_process(process).strip()
        if buffer_clear:
            print("before spread clear buffer:")
            print(buffer_clear)
            print("end clear")

        print("\nSite",seq_casuse_signal,"Ready to record error spread.\n")
        
        while stepi_num <= MAX_ERROR_SPREAD:
            #打印前MAX_ERROR_SPREAD条指令
            try:
                stepioutput = ""
                i, stepioutput = self.gdb_send_extended(
                    process, "stepi", f"单步执行第{stepi_num}条指令",
                    expect_patterns=[pexpect.TIMEOUT, "(gdb)"],
                    pattern_names=["TIMEOUT", "PROMPT"])

                if i == 0 :
                    print("error in stepi_in",seq_casuse_signal)
                    print("error stepioutput\t",stepioutput,"end error stepioutput")
                    break
                # 打印当前指令
                if "received signal" in stepioutput:
                    rcv_sig = 1 #当前出错,不着急打印,等待判断附近之外出现signal后再一起打印
                    print("received signal during error spread:")
                    stepioutput = "stepioutput:\t" + stepioutput
                    print(stepioutput.strip())
                    break
                print(stepi_num)
                stepi_num += 1
                if stepi_num >= MAX_ERROR_SPREAD:
                    break
                
                i, pc_output = self.gdb_send_extended(
                    process, GDB_DISPLAY, "显示当前PC指令",
                    timeout=5, expect_patterns=[pexpect.TIMEOUT, "(gdb)"],
                    pattern_names=["TIMEOUT", "PROMPT"])
                if i == 0:
                    print("Error: Timeout after x/i $pc.",seq_casuse_signal)
                    break
                pc_output = pc_output.replace('\r','').replace('\n','').strip()
                if "The program is not being run." in pc_output:
                    print("program stop!")
                    self.print_process(process)
                    return 0,'no crash'
                print(re.sub(r'[\n()]', '', pc_output))  # 打印当前的 PC 状态

            except pexpect.EOF:
                print("GDB process ended.")
                break
            except pexpect.TIMEOUT:
                print("Timeout waiting for GDB response.")
                break
        #print(i)
        #print("OUTPUT\n",output)
        ##结束打印MAX_ERROR_SPREAD指令
        
        if rcv_sig == 0:##附近没有出错,就继续运行直到出错或者结束
            i, coutput = self.gdb_send_extended(
                process, GDB_CONTINUE, "继续执行直到出错或结束",
                timeout=180, expect_patterns=[GDB_PROMOPT, pexpect.TIMEOUT],
                pattern_names=["PROMPT", "TIMEOUT"])
            if "received signal" in coutput:
                rcv_sig = 1
                print(re.sub(r'[\n()]', '', coutput))
            else:       #完美masked
                print(coutput)
        if rcv_sig == 1:##此处gdb已经由于signal的存在而暂停,无论远近,采取同一个方法打印
            i, output = self.gdb_send(process, GDB_DISPLAY, "显示崩溃点指令")
            print("print $pc:\t",output)
        buffer = self.print_process(process)
        if not buffer.strip() == '':
            print("clear buffer:",self.print_process(process),"end clear.")


        if stepi_num < MAX_ERROR_SPREAD :#满足这个条件,必定在附近出现了signal，用于总结错误传播长度
            if seq_casuse_signal == 0:
                print(PRT_ERR_LEN_INJ_SIG,stepi_num)
            if seq_casuse_signal == 1:
                print(PRT_ERR_LEN_FIX_SIG,stepi_num)
        else:  #附近没有出错
            if seq_casuse_signal == 0:
                print(PTR_ERR_INJ_MAX)
            if seq_casuse_signal == 1:
                print(PTR_ERR_FIX_MAX)
        return rcv_sig,output

    def info_at_signal(self,process):
        """#出错前手动调试
        sys.__stdout__.write("interact")
        process.interact()"""

        i, sigout = self.gdb_send(process, "stepi", "单步执行以获取信号信息")
        if "received signal" in sigout:
            print(sigout)
            i, pc_info = self.gdb_send(process, "x/i $pc", "显示当前指令")
            print(pc_info.replace("\n", "").replace("\r", ""))

            i, gdbout = self.gdb_send(process, "backtrace", "显示调用栈")
            if i == 0:
                print("ERROR when watching backtrace")
                self.log.close()
                process.close()
                sys.stdout = sys.__stdout__
                return
            print("\nat sig backtrace:\t",(gdbout))
            # if "return" in gdbout:
            #     process.sendline("return")
            #     print(process.expect([pexpect.TIMEOUT, "(gdb)"]))
            # print("backrace end")

    def letgo_frame(self,process):
        ######  call this when encoutering SIG and gdb pause
        ###  LetGo framework steps in
        #####
        ###  IMPORTANT: 以下输出格式由analyze.py解析，请勿随意修改关键字符串
        ###  关键解析标记: "Letgo in!", "parse the pc value", "h_1", "h_2", "h_3"
        print("="*60)
        print("  子步骤 1/6: LetGo框架启动，开始故障修复")
        print("="*60)
        
        output = self.print_process(process)
        if output.strip():
            print("clear before:",output)
        print('\nLetgo in!')  ###  IMPORTANT: analyze.py解析此标记识别LetGo框架启动
        self.letgo_start_time = datetime.datetime.now()
        
        print("\n  子步骤 1.1: 获取当前崩溃点的PC值")
        i, pc_response = self.gdb_send(process, GDB_PRINT_PC, "获取当前崩溃点的PC值")
        if i != 1:
            print("ERROR: 无法获取PC值，修复失败")
            print("error entering letgo: cannot print pc")
            return 1
    
        # parse the pc value by regex 0x
        # send the pc to pin, and get all info we need
        print('  子步骤 1.2: 解析PC值并获取指令信息')
        output = pc_response
        if "receiced signal" in output:
            try:
                print("no => but find:\t",'0x'+output.split('0x')[1].split(' ')[0])
            except:
                print(output)
        else:
            print("parse the pc value by regex 0x")  ###  IMPORTANT: analyze.py解析此标记获取PC值
            print(output)
        match = re.findall('0[xX]?[A-Fa-f0-9]+', pc_response)
        if len(match) == 0:
            print("ERROR: 无法从输出中提取PC地址")
            print("Crash place getting no PC!")
            return 1
        
        decpc = int(match[0], 0)    ##此处的match[0]是一个包含0x的十六进制地址,使用int将其转化为十进制
        print(f"[信息] 解析得到崩溃点PC地址: {hex(decpc)}")
        
        print("\n  子步骤 1.3: 通过Pin工具获取指令详细信息")
        try:
            fi = faultinject.FaultInjector(self.insts)
            args = fi.getNextPC(decpc)  ## 此处要关注faultinjecion.cpp中的getNextPC函数
            
            if len(args) != 8:
                print("ERROR: Pin工具返回的指令信息不完整")
                print("No nextpc!")
                return 1
        except Exception as process_error:
            print("ERROR: 无法从Pin工具获取指令信息")
            print("No nextpc!\nOpen file failed...")
            return 1
        
        print("[信息] Pin工具返回的指令信息:")
        print(args)
        
        print("\n  子步骤 1.4: 解析指令信息参数")
        thispc = decpc
        nextpc = args[0]    ##ins的下一条指令的pc值
        regwlist = args[1]  ##ins的所有写寄存器的列表
        stack = args[2]     ##ins是栈操作则和base相同,否则为nostack
        flag = args[3]      ## stackw: 1, stackr: 2 , nostack: 3
        base = args[4]      ##ins在内存中的基地址
        index = args[5]     ##ins在内存中的索引寄存器值,基地址偏移
        displacement = args[6]  ##指令中内存操作的位移量
        scale = args[7]     ##内存因子,用来和index配合使用,实现复杂内存寻址
        
        print(f"  - 当前PC: {hex(thispc)}")
        print(f"  - 下一条指令PC: {hex(nextpc) if isinstance(nextpc, int) else nextpc}")
        print(f"  - 写寄存器列表: {regwlist}")
        print(f"  - 栈操作标识: {stack}")
        print(f"  - 指令类型标志: {flag} (1=栈写入, 2=栈读取, 3=非栈操作)")
        print(f"  - 内存基地址寄存器: {base}")
        print(f"  - 内存索引寄存器: {index}")
        print(f"  - 内存偏移量: {displacement}")
        print(f"  - 内存缩放因子: {scale}")
                    
        print("\n" + "="*60)
        print("  子步骤 2/6: 开始寄存器修复操作")
        print("="*60)
        
        do_recovery = 1
        self.enable_gdb_verbose()
        if do_recovery == 1:
            #####
            # We can have multiple options here. For now, we feed the value (0) to the supposed-to-write register
            #####
            print('  子步骤 2.1: 准备修复选项')
            if set_reg_fake == 1:    ##处理写寄存器regw,set_reg_fake是手动开关
                print(f"[信息] 需要修复的写寄存器列表: {regwlist}")
                for regw_idx, regw in enumerate(regwlist):
                    print(f"\n--- 修复寄存器 {regw_idx+1}/{len(regwlist)}: {regw} ---")
                    if flag == 2:   ##处理栈读相关的而寄存器, 重计算内存写的位置
                        print("    子步骤 2.2: 栈读取指令修复 - 重新计算内存地址")
                        print("h_1 start")
                        final_b = 0 ##base 
                        final_i = 0 ##index
                        final_d = 0 ##displacement
                        final_s = 0 ##scale
                        ## we can try to calculate a valid number for regw
                        if base == "":                          ##开始解析base
                            print("[警告] 没有基地址寄存器，跳过此寄存器修复")
                            print("no base")
                            continue
                        print(f"    子步骤 2.2.1: 获取基地址寄存器 {base} 的值")
                        print("base:\t",base)
                        i, basestr = self.gdb_send(process, GDB_PRINT_REG + " $" + base, f"获取基地址寄存器{base}的值")
                        if i == 0:
                            print("ERROR: 无法获取基地址寄存器值")
                            print("ERROR when getting the base")
                            print((str(process)))
                            self.log.close()
                            process.close()
                            sys.stdout = sys.__stdout__
                            return
                        print("basestr:\t",basestr)
                        content = ""
                        if "0x" in basestr:
                            items = basestr.split(" ")
                            for item in items:
                                if "0x" in item:
                                    content = item
                        else:
                            items = basestr.split(" ")
                            content = items[len(items) - 1]
                        content = content.lstrip("nan")
                        content = content.lstrip("-nan")
                        if "0x" in content:
                            final_b = int(content, 16)   ## 修复之前的base和现在的这个Base一样吗
                        else:
                            final_b = int(content)  ##base解析完毕,content保存了将basestr从16进制转化到10进制的结果
                        print(f"    子步骤 2.2.2: 获取索引寄存器 {index} 的值")
                        if index == "null":         ##开始解析index
                            print("[信息] 没有索引寄存器")
                            print("no index")
                        else:
                            i, indexstr = self.gdb_send(process, GDB_PRINT_REG + " $" + index, f"获取索引寄存器{index}的值")
                            if i == 0:
                                print("ERROR: 无法获取索引寄存器值")
                                print("ERROR when getting the index")
                                print((str(process)))
                                self.log.close()
                                process.close()
                                sys.stdout = sys.__stdout__
                                return
                            print("indexstr:\t",indexstr)
                            content = ""
                            if "0x" in indexstr:
                                items = indexstr.split(" ")
                                for item in items:
                                    if "0x" in item:
                                        content = item
                            else:
                                items = indexstr.split(" ")
                                content = items[len(items) - 1]
                            content = content.lstrip("nan")
                            content = content.lstrip("-nan")
                            if "0x" in content:
                                final_i = int(content, 16)
                            else:
                                final_i = int(content)  ##index解析完毕

                            final_d = int(displacement)
                            final_s = int(scale)
                            
                            print("    子步骤 2.2.3: 计算有效内存地址")
                            ##用base,displacement,index,scale综合确定修改后的地址值
                            address = final_b + final_d + final_i * final_s   # 基地址、内存偏移量、基地址偏移、内存因子
                            print(f"[计算] 有效地址 = base + displacement + index * scale")
                            print("address: {0}, final_b: {1}, final_d: {2}, final_i: {3}, final_s: {4}".format(
                                hex(address),  # 将address转换为十六进制
                                hex(final_b),  # 将final_b转换为十六进制
                                hex(final_d),           # 将final_d转换为十六进制
                                hex(final_i),           # 将final_i转换为十六进制
                                hex(final_s)            # 将final_s转换为十六进制
                            ))
                            print(f"[结果] 计算得到的有效地址: {hex(address)}")

                            print("    子步骤 2.2.4: 读取该地址处的数值")
                            i, finalres = self.gdb_send(process, GDB_PRINT_REG + " *" + str(address), f"读取内存地址{hex(address)}处的值")
                            if i == 0:
                                print("ERROR: 无法读取内存地址处的值")
                                print("ERROR when getting the final value")
                                print((str(process)))
                                self.log.close()
                                process.close()
                                sys.stdout = sys.__stdout__
                                return
                            # finalres是什么？
                            content = ""
                            if "0x" in finalres:
                                items = finalres.split(" ")
                                for item in items:
                                    if "0x" in item:
                                        content = item
                            else:
                                items = finalres.split(" ")
                                content = items[len(items) - 1]
                            content = content.lstrip("nan")
                            content = content.lstrip("-nan")

                            i, print_regw = self.gdb_send(process, GDB_PRINT_REG + " $" + regw, f"获取目标寄存器{regw}的当前值")
                            if i == 0:
                                print("ERROR when getting the base")
                                print((str(process)))
                                self.log.close()
                                process.close()
                                sys.stdout = sys.__stdout__
                                return

                            print("    子步骤 2.2.5: 将读取的值设置到目标寄存器")
                            print("change regw key:\t",regw.strip())   
                            print("unchanged regw value:\t",print_regw.strip())
                            print("change regw value to:\t",content.strip())
                            i, set_response = self.gdb_send(process, GDB_SET_REG + " $" + regw + "=" + content, f"设置寄存器{regw}为{content}")
                            if i == 0:
                                print("ERROR: 无法设置寄存器值")
                                print("ERROR when setting the final value")
                                print((str(process)))
                                self.log.close()
                                process.close()
                                sys.stdout = sys.__stdout__
                                return
                            if i == 1:
                                print("[成功] 栈读取修复完成 - 已通过地址计算设置寄存器值")
                                print("is stackr: have set reg with address calculation ")  ###  IMPORTANT: analyze.py解析此标记识别h_1修复策略
                            print("h_1 end")

                    else:   ##处理其他memory-load，用0代替读到的数据，原因是内存中有很多零
                        print("    子步骤 2.3: 非栈读取指令修复 - 设置默认值0")
                        if "xmm" in regw:
                            regw = regw+".uint128"
                            print(f"[信息] 检测到XMM寄存器，修改为 {regw}")
                        print("h_2 start")
                        i, fake_response = self.gdb_send(process, GDB_SET_REG + " $" + regw + "=" + GDB_FAKE, f"设置寄存器{regw}为默认值{GDB_FAKE}")
                        if i == 0:
                            print("ERROR: 无法设置寄存器默认值")
                            print("ERROR when setting the reg value")
                            print((str(process)))
                            self.log.close()
                            process.close()
                            sys.stdout = sys.__stdout__
                            return
                        if i == 1:
                            print(f"[成功] 非栈读取修复完成 - 已设置寄存器 {regw} = {GDB_FAKE}")
                            print("not stackr,so set fake:\t",regw)  ###  IMPORTANT: analyze.py解析此标记识别h_2修复策略
                        print("h_2 end")

            print("\n" + "="*60)
            print("  子步骤 3/6: 栈指针修复操作")
            print("="*60)
            
            # try to set the rbp and rsp to reasonable values
            ##print('set rbp and rsp to reasonable values')  怎么判断
            if is_rewind == 1 and (flag == 1 or flag == 2):    ##flag1表示栈的写入,这里flag和上面multiple options中的if冲突,也就是只有else执行时才执行此处;is_rewind是手动开关
                print("  子步骤 3.1: 检测到栈操作指令，开始栈指针修复")
                print("h_3 start")
                print('stackw, set rbp and rsp to reasonable values')
                stackinfo = ["rbp", "rsp"]
                print("stack:\t",stack)
                if stack != "" or force_fix_rbp:
                    print("  子步骤 3.2: 获取栈帧大小信息")
                    size = fi.get_stack_size()  ##size保存的是ins所在函数初始为局部变量分配的空间大小,典型的函数栈帧设置的一部分
                    if size == "":
                        size = "0"
                    if size != "":
                        print(f"[信息] 获取到栈帧大小: {size}")
                        print("size:\t",size)
                        print("  子步骤 3.3: 确定需要修复的栈指针")
                        try:
                            stackinfo.remove(stack)
                        except:
                            stack = "rbp"
                            stackinfo.remove("rbp")
                        rxp = stackinfo[0]#rxp=rsp
                        print(f"[信息] 栈操作寄存器: {stack}, 另一个栈指针: {rxp}")
                        print("stack size != null, rxp=", rxp)
                        print(f"  子步骤 3.4: 获取 {rxp} 寄存器的当前值")
                        ##解析$rxp内容
                        i, output = self.gdb_send(process, GDB_PRINT_REG + " $" + rxp, f"获取栈指针寄存器{rxp}的值")
                        if i == 0:
                            print(f"ERROR: 无法获取 {rxp} 寄存器值")
                            print("ERROR when getting the value of the rbp or rsp")
                            print((str(process)))
                            self.log.close()
                            process.close()
                            sys.stdout = sys.__stdout__
                            return
                        if i == 1:
                            content_rxp = ""
                            if "0x" in output:
                                items = output.split(" ")
                                for item in items:
                                    if "0x" in item:
                                        content_rxp = item
                            else:
                                items = output.split(" ")
                                content_rxp = items[len(items) - 1]
                            content_rxp = content_rxp.lstrip("nan")
                            content_rxp = content_rxp.lstrip("-nan")
                            print("content_rxp:",rxp,content_rxp)
                            size_rxp = 0
                            if "0x" in content_rxp:
                                if is_hexnumber(content_rxp):
                                    size_rxp = int(content_rxp, 16)
                            else:
                                if is_number(content_rxp):
                                    size_rxp = int(content_rxp)
                            print("size_rxp:",rxp,size_rxp)
                            print(f"  子步骤 3.5: 获取 {stack} 寄存器的当前值")
                            ##解析$stack
                            i, output = self.gdb_send(process, GDB_PRINT_REG + " $" + stack, f"获取栈指针寄存器{stack}的值")
                            if i == 0:
                                print(f"ERROR: 无法获取 {stack} 寄存器值")
                                print("ERROR when getting the value of the rbp or rsp")
                                print((str(process)))
                                self.log.close()
                                process.close()
                                sys.stdout = sys.__stdout__
                                return
                            if i == 1:
                                content_stack = ""
                                if "0x" in output:
                                    items = output.split(" ")
                                    for item in items:
                                        if "0x" in item:
                                            content_stack = item
                                else:
                                    items = output.split(" ")
                                    content_stack = items[len(items) - 1]
                                content_stack = content_stack.lstrip("nan")
                                content_stack = content_stack.lstrip("-nan")
                                print("content_stack:",stack,content_stack)
                                size_stack = 0
                                if "0x" in content_stack:
                                    if is_hexnumber(content_stack):
                                        size_stack = int(content_stack, 16)
                                else:
                                    if is_number(content_stack):
                                        size_stack = int(content_stack)
                                print("size_stack:",stack,size_stack)

                            size = int(size,16)
                            print("size:\t",size)
                            
                            print("  子步骤 3.6: 检测栈溢出并修复栈指针")
                            print(f"[检查] {rxp}值: {size_rxp}, {stack}值: {size_stack}, 栈帧大小: {size}")
                            # if abs(size_rxp - size_stack) > size and size_stack > size and size_rxp > size:##检测是否栈溢出
                            #     process.sendline(GDB_SET_REG + " $" + stack + "=" + content_rxp)
                            if (abs(size_rxp - size_stack) > size and size_stack > size and size_rxp > size) or (size_rxp-size_stack>0):##检测是否栈溢出
                                print("[检测] 发现栈溢出，开始修复")
                                if stack == "rbp":
                                    setback = str(size_rxp+size)
                                    print(f"[计算] rbp修复值 = {rxp}值 + 栈帧大小 = {size_rxp} + {size} = {setback}")
                                if stack == "rsp":
                                    setback = str(size_rxp-size)
                                    print(f"[计算] rsp修复值 = {rxp}值 - 栈帧大小 = {size_rxp} - {size} = {setback}")
                                i, stack_response = self.gdb_send(process, GDB_SET_REG + " $" + stack + "=" + setback, f"设置栈指针{stack}为修复值{setback}")
                                if i == 0:
                                    print(f"ERROR: 无法重置 {stack} 寄存器")
                                    print(("ERROR when resetting the " + stack))
                                    print((str(process)))
                                    self.log.close()
                                    process.close()
                                    sys.stdout = sys.__stdout__
                                    return

                                if i == 1:
                                    print(f"[成功] 栈指针 {stack} 修复完成")
                                    print(("Set the " + stack + " back! "))  ###  IMPORTANT: analyze.py解析此标记识别h_3修复策略
                                    print("h_3 end")
                                    nextpc = thispc
                                    print("[信息] 设置重做当前指令")
                                    print("redo:\t",nextpc)
                            else:
                                print("[信息] 未检测到栈溢出，无需修复栈指针")
                    
                else:
                    print("[警告] 无法获取当前栈帧大小，跳过栈指针修复")
                    print("Cannot get the size of the current stack frame")
            else:
                print("[信息] 非栈操作指令或栈修复功能已禁用，跳过栈指针修复")
        
        print("\n" + "="*60)
        print("  子步骤 4/6: 设置程序计数器到下一条指令")
        print("="*60)
        
        #process.interact()
        print(f"  子步骤 4.1: 设置PC寄存器到下一条指令地址")
        next_pc_hex = str(hex(int(nextpc)))
        i, gdb_response = self.gdb_send(process, GDB_SET_REG + " $pc=" + next_pc_hex, f"设置PC寄存器为{next_pc_hex}")
        print("nextpc:\t",gdb_response)
        if i == 0:
            print("ERROR: 无法设置PC值")
            print("ERROR when setting the pc value")
            print((str(process)))
            self.log.close()
            process.close()
            sys.stdout = sys.__stdout__
            return
        else:
            print(f"[成功] PC寄存器已设置为: {next_pc_hex}")
        self.disable_gdb_verbose()
        
        print("\n" + "="*60)
        print("  子步骤 5/6: LetGo框架修复完成")
        print("="*60)
        print("[信息] 所有修复操作已完成，程序准备继续执行")
        print(f"[总结] 修复的寄存器数量: {len(regwlist) if regwlist else 0}")
        print(f"[总结] 修复的指令类型: {'栈读取' if flag == 2 else '栈写入' if flag == 1 else '非栈操作'}")
        print(f"[总结] 程序将从地址 {next_pc_hex} 继续执行")


    def handle_after_injection(self,process):
        print("process continue...")
        
        index, after_continue = self.gdb_send_extended(
            process, GDB_CONTINUE, "注入后继续执行程序",
            timeout=600, expect_patterns=[GDB_PROMOPT, pexpect.EOF, pexpect.TIMEOUT],
            pattern_names=["PROMPT", "EOF", "TIMEOUT"])
            
        if index == 0:
            print("Received GDB prompt,process pause or stop.")
        elif index == 1:
            print("Received EOF")
        elif index == 2:
            print("Timeout occurred")
            self.log.close()
            process.terminate()
            process.close()
            sys.stdout = sys.__stdout__
            raise Exception("Process timed out")  # 或者使用自定义异常
            return
        #print(after_continue)
        
        if "received signal" in after_continue:
            print("\n" + "="*60)
            print("修改状态后验证和错误传播检测")
            print("="*60)
            
            #print("after_continue:\t",after_continue)
            rcv_sig = 0 #假设通过修复不会再收到信号
            print("第1步: 获取信号详细信息")
            self.info_at_signal(process)
            self.letgo_start_time = datetime.datetime.now()
            print("第2步: 启动LetGo框架修复 (包含6个子步骤)")
            exit_code = self.letgo_frame(process)
            rcv_sig = 0
            if exit_code == 1:#letgo执行失败了
                print("[错误] LetGo框架修复失败")
                rcv_sig =1
            else:
                print("[成功] LetGo框架修复完成")

            ##letgo_frame执行完毕,开始计算介入letgo_frame后的错误传播
            print("第3步: 检测修复后的错误传播")
            if rcv_sig==0:
                rcv_sig,output= self.error_spread(process,1)

            if rcv_sig == 0:
                print("[成功] 修复后无错误传播，程序可以继续执行")
                print("Process Continue!\n")
                print("第4步: 继续执行程序")
                i, continue_response = self.gdb_send(process, GDB_CONTINUE, "继续执行修复后的程序")
                print("Application output:\n")
                #print(output)
            if rcv_sig == 1:
                print("[失败] 修复后仍有错误传播，终止程序")
                print("第4步: 终止程序执行")
                self.info_at_signal(process)
                i, kill_response = self.gdb_send(process, "kill", "终止程序执行")
        else:   # 注错后没有收到信号
            print("\n" + "="*60)
            print("情况: 注错后无信号触发 - 可能是SDC（Silent Data Corruption）")
            print("="*60)
            
            if after_continue.strip():
                print("after_continue:\t",after_continue)
            print("\n[信息] 没有触发崩溃信号")
            print("No triggering crashes")

            output = self.print_process(process)
            if output.strip():
                print("clear buffer before sdc:")
                print(output)
                print("end buffer clear")
            
            print("[信息] 程序可能发生了静默数据损坏（SDC），需要进一步检查输出结果")

        
        try:
            # sdcjudger.SDC_saver(index = str(self.trial))
            self.sig_end_time = datetime.datetime.now()
            print("Letgo time: ",self.sig_end_time - self.letgo_start_time)
        except:
            pass
        print("sig time: ",self.sig_end_time - self.sig_start_time)
        print("Now Time:\t" , (datetime.datetime.now()))


    def inject_by_breakpoint_and_recover(self,process):
        self.inject_inst_by_breakpoint(process)

        #rcv_sig,output= self.error_spread(process,0)

        self.handle_after_injection(process)
        
        sdcjudger.SDC_saver(index = str(self.trial))

    def inject_by_pinfi_and_recover(self,process):
        self.process_remote_target = self.inject_inst_by_faultinjection(process)
        self.handle_after_injection(process)

        print("app output:")
        # 等待进程输出，直到超时或进程结束
        result = self.process_remote_target.expect([pexpect.EOF, pexpect.TIMEOUT], timeout=300)  # 捕获EOF或超时
        # 获取并打印进程输出
        output = self.process_remote_target.before.decode('utf-8').strip()
        if output:
            if configure.progname in configure.PolyBenchOutPutList:
                output_path = os.path.join('/tmp/',configure.output_name)
                with open(output_path, 'w') as f:
                    f.write(output)
            else:
                print(output)
        print("end output.")
        
        sdcjudger.SDC_saver(index = str(self.trial))
        
        print("injection info:")
        self.print_file_to_log(configure.activate)
        print("end injection info.")

    def executeProgram(self,process):
        global GDB_LAUNCH, GDB_ARG, GDB_PROMOPT, GDB_RUN, GDB_HANDLE, GDB_ERROR, GDB_NEXT, GDB_CONTINUE, GDB_FAKE
        self.sig_start_time = datetime.datetime.now()
        print("now time:\t",self.sig_start_time)

        i = process.expect([pexpect.TIMEOUT, GDB_PROMOPT])
        if i == 0:
            print('ERROR! Could not run GDB')
            print((process.before.decode('utf-8'), process.after))
            print((str(process)))
            self.log.close()
            process.close()
            sys.stdout = sys.__stdout__
            return
        if i == 1:
            temp = process.before.decode('utf-8')  ## just to flush the before buffer

            self.gdb_send(process, GDB_HANDLE_BUS, "设置SIGBUS信号处理")
            self.gdb_send(process, GDB_HANDLE_SEGV, "设置SIGSEGV信号处理") 
            self.gdb_send(process, GDB_HANDLE_ABT, "设置SIGABRT信号处理")
            self.gdb_send(process, GDB_HANDLE_FPE, "设置SIGFPE信号处理")
            self.gdb_send(process, "set print demangle on", "开启符号名称显示")
            self.gdb_send(process, "set confirm off", "关闭确认提示")

            if configure.progname in configure.OpenMpOutPutList:
                GDB_ENV = "set env OUTPUT 1"
                self.gdb_send(process, GDB_ENV, "设置环境变量OUTPUT=1")  

        if configure.inject_tool == 'pinfi':
            self.inject_by_pinfi_and_recover(process)
        elif configure.inject_tool == 'breakpoint':
            self.inject_by_breakpoint_and_recover(process)
