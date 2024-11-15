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

GDB_PROMOPT = "\(gdb\)"
GDB_RUN = "run"
GDB_LAUNCH = "gdb " + configure.benchmark
GDB_HANDLE_BUS = "handle SIGBUS nopass"
GDB_HANDLE_SEGV = "handle SIGSEGV nopass"
GDB_HANDLE_ABT = "handle SIGABRT nopass"
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

##debug_mode
debug_mode = 5

is_fake = 1
is_rewind = 1

##log_path = "./self.log"
log_path = configure.log_path
if not os.path.exists(log_path):
    os.makedirs(log_path)
    
def is_hexnumber(s):
    try:
        int(s,16)
        return True
    except ValueError:
        return False

class SigHandler:
    def __init__(self, insts, trial):
        self.insts = int(insts)
        self.trial = trial

        logname = os.path.join(log_path,('log_'+str(self.trial) ))
        self.log = open(str(logname), "w")
        sys.stdout = self.log
        sys.stderr = self.log

        self.lastinst = ''

        self.sig_start_time = datetime.datetime.now()
        self.sig_end_time = datetime.datetime.now()
        self.letgo_start_time = datetime.datetime.now()

        self.process_remote_target = None
        self.process = pexpect.spawn(GDB_LAUNCH)
        print("do pexpect.spawn: gdb  has launched!")


    def inject_inst_by_breakpoint(self,process):
    # Prepare gdb run
        ori_reg = ""

        GDB_RUN = "run"
        for item in configure.args:
            GDB_RUN += " " + item

    # Set a breakpoint: need pc and iteration number
        ##
        print('Start set a breakpoint...')
        fi = faultinject.FaultInjector(self.insts)
        try:
            result = InstPoolMaker.readArgsFromPool()
            # 检查 result 的长度是否为 5
            if len(result) != 5:
                raise ValueError("Wrong return values! Exit!")  # 抛出异常跳转到 except 块
            args = result[0:4]
            randomnum = result[-1]
            print("-randinst", randomnum)
        except:
            args = fi.getBreakpoint  # [regmm, reg, pc, iteration]

        ##参数中包含的是在动态指令randomnum处的指令和寄存器信息.pc是该动态指令的ins值,regmm或reg是ins中随机挑选的寄存器
        ##iteration表示的是在randomnum范围内,ins值和pc值相同的次数;也就是pc值在randomnum范围内的迭代次数
        if len(args) != 4:
            print("Wrong return values! Exit!")
            self.log.close()
            process.close()
            sys.stdout = sys.__stdout__
            return
        try:
            shutil.rmtree("graphics_output")
            print("remove output file 2")
        except:
            print("Oops, no x.vec file found. Ignoring. 2")

        regmm = args[0].rstrip("\n")    ##
        reg = args[1].rstrip("\n")
        pc = args[2].rstrip("\n")
        iteration = int(args[3].rstrip("\n"))
        # next = hex(int(args[4]))
        print('args ready for set breakpoint:\t',args)
        hexpc = hex(int(pc))
        print('hexpc\t',hexpc)
        GDB_BREAKPOINT = "break *" + str(hexpc)
        process.sendline(GDB_BREAKPOINT)
        i = process.expect([pexpect.TIMEOUT, GDB_PROMOPT])
        if i == 0:
            print('ERROR! Could not set the breakpoint')
            print((process.before.decode('utf-8'), process.after))
            print((str(process)))
            self.log.close()
            process.close()
            sys.stdout = sys.__stdout__
            return
        if i == 1:
            print((process.before.decode('utf-8')))
            print('Successfully set the breakpoint')

    # run application
        ##


        process.sendline(GDB_RUN)
        i = process.expect([pexpect.TIMEOUT, GDB_PROMOPT])
        if i == 0:
            print('ERROR! Could not run the program')
            print((process.before.decode('utf-8'), process.after))
            self.log.close()
            process.terminate()
            process.close()
            sys.stdout = sys.__stdout__
            return
        if i == 1:
            output = process.before.decode('utf-8')
            print('----------------------Start output----------------------\n',output,'\n----------------------End output----------------------')
            if "Breakpoint" not in output:
                print("no such Breakpoint!")
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
                while iteration > 0:
                    process.sendline(GDB_CONTINUE)
                    i = process.expect([pexpect.TIMEOUT, GDB_PROMOPT])
                    if i == 0:
                        print('ERROR while continuing the program')
                        print((process.before.decode('utf-8'), process.after))
                        print((str(process)))
                        self.log.close()
                        process.close()
                        sys.stdout = sys.__stdout__
                        return
                    if i == 1:
                        iteration -= 1

    # print out the current instruction for more info
                ###
                
                #process.interact()
                
                process.sendline(GDB_SETPAGEOFF)
                i = process.expect([pexpect.TIMEOUT, GDB_PROMOPT])

                process.sendline(GDB_BEFOREPC)
                i = process.expect([pexpect.TIMEOUT, GDB_PROMOPT])
                if i == 0:
                    print("ERROR when displaying the insts before inject place")
                    print((process.before.decode('utf-8'), process.after))
                    print((str(process)))
                    self.log.close()
                    process.close()
                    sys.stdout = sys.__stdout__
                    return
                if i == 1:
                    output = process.before.decode('utf-8')
                    print("\nbefore inject inst:--------------------------------------\t\n:",output,"before inject inst end:--------------------------------------\n")

    # No.iteration breakpoint
                process.sendline("set $saved_pc = $pc")
                i = process.expect([pexpect.TIMEOUT, GDB_PROMOPT])
                process.sendline("x/i $saved_pc")
                i = process.expect([pexpect.TIMEOUT, GDB_PROMOPT])
                if i == 0:
                    print("ERROR when displaying the inst")
                    print((process.before.decode('utf-8'), process.after))
                    print((str(process)))
                    self.log.close()
                    process.close()
                    sys.stdout = sys.__stdout__
                    return
                if i == 1:
                    inject_inst = process.before.decode('utf-8')
                    print("display the inject inst start:\n",inject_inst,"display the inject inst end.")

    # inject reg
                if regmm == "":  # it means that it is a normal instruction and we need to inject the fault to the dest reg
                    print('Meet a normal instruction:')
                    process.sendline(GDB_NEXT)
                    i = process.expect([pexpect.TIMEOUT, GDB_PROMOPT])
                    output = process.before.decode('utf-8')
                    print(output)
                    if i == 0:
                        print('ERROR! Can not step in')
                        print((process.before.decode('utf-8'), process.after))
                        print((str(process)))
                        self.log.close()
                        process.close()
                        sys.stdout = sys.__stdout__
                        return
                    if i == 1:
                        process.sendline(GDB_PRINT_REG + " $" + reg)
                        process.expect([pexpect.TIMEOUT, GDB_PROMOPT])
                        if i == 0:
                            print('ERROR while analyzing the content of the register')
                            print((process.before.decode('utf-8'), process.after))
                            print((str(process)))
                            self.log.close()
                            sys.stdout = sys.__stdout__
                            print("exit due to sighandle: timeout")
                            sys.exit(1)
                        if i == 1:
                            output = process.before.decode('utf-8')
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
                            process.sendline(GDB_SET_REG + " $" + reg + "=" + content)
                            i = process.expect([pexpect.TIMEOUT, GDB_PROMOPT])
                            if i == 0:
                                print('ERROR while waiting for changing the value')
                                print((process.before.decode('utf-8'), process.after))
                                print((str(process)))
                                self.log.close()
                                process.close()
                                sys.stdout = sys.__stdout__
                                return
                            if i == 1:
                                output = process.before.decode('utf-8')
                                if "=" in output:
                                    print(output)
                                    print("Fault injection is done")

    # inject regmm                                    
                if reg == "":  # it means that it is a memory instruction. Need to inject before it is executed.
                    print('Meet a memory instruction:')
                    process.sendline(GDB_PRINT_REG + " $" + regmm)
                    i = process.expect([pexpect.TIMEOUT, GDB_PROMOPT])
                    if i == 0:
                        print('ERROR while analyzing the content of the register mem')
                        print((process.before.decode('utf-8'), process.after))
                        print((str(process)))
                        self.log.close()
                        process.close()
                        sys.stdout = sys.__stdout__
                        return
                    if i == 1:
                        output = process.before.decode('utf-8')
                        print("print regmm:\t",output)
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
                        process.sendline(GDB_SET_REG + " $" + regmm + "=" + content)
                        i = process.expect([pexpect.TIMEOUT, GDB_PROMOPT])
                        if i == 0:
                            print('ERROR while waiting for changing the value mem')
                            print((process.before.decode('utf-8'), process.after))
                            print((str(process)))
                            self.log.close()
                            process.close()
                            sys.stdout = sys.__stdout__
                            return
                        if i == 1:
                            output = process.before.decode('utf-8')
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
                        if 'j' not in inject_op:
                            process.sendline(GDB_NEXT)
                            i = process.expect([pexpect.TIMEOUT, GDB_PROMOPT])
                            if i == 0:
                                print("ERROR when single step")
                                print(process.before.decode('utf-8'), process.after)
                                print(str(process))
                                self.log.close()
                                process.close()
                                sys.stdout = sys.__stdout__
                                return
                            if i == 1:
                                print("Single step")
                                output = process.before.decode('utf-8')
                                if 'received signal' in output:
                                    print("Crash after single step, considered working!")


                            process.sendline(GDB_SET_REG + " $" + regmm + "=" + ori_reg)
                            i = process.expect([pexpect.TIMEOUT, GDB_PROMOPT])
                            if i == 0:
                                print("ERROR when setting the regmm back after single step")
                                print(process.before.decode('utf-8'), process.after)
                                print(str(process))
                                self.log.close()
                                process.close()
                                sys.stdout = sys.__stdout__
                                return
                            if i == 1:
                                print("Change the value back")
                        
    # del breakpoints
                """print("GDB is now interactive. You can type GDB commands.")
                process.interact()  # 交互模式，允许用户直接控制 GDB"""

                process.sendline(GDB_DELETE_BP)
                process.sendline('y')
                i = process.expect([pexpect.TIMEOUT, GDB_PROMOPT])
                if i == 0:
                    print("ERROR when deleting breakpoints")
                    print((process.before.decode('utf-8'), process.after))
                    print((str(process)))
                    self.log.close()
                    process.close()
                    sys.stdout = sys.__stdout__
                    return
                if i == 1:
                    print(process.before.decode('utf-8'))
                    print("Delete all breakpoints")

    def inject_inst_by_faultinjection(self,process):
        # process 进入状态：gdb只指定了可执行文件
        # process 离开状态：pin对程序注错后保留调试端口，process通过远程端口调试用pin注错后的程序
        benchmark = configure.benchmark
        execlist = []
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
        output = self.print_process(self.process_remote_target)

        try:
            port = output.split(':')[-1].strip()
            print("Extracted port:", port)

            gdb_command = f"target remote :{port}"
            print("process cmd:",gdb_command)
            process.sendline(gdb_command)
            process.expect([pexpect.TIMEOUT, GDB_PROMOPT])
            process.sendline(GDB_CONTINUE)
            process.expect([pexpect.TIMEOUT, GDB_PROMOPT])
            #print((process.before.decode('utf-8')))
        except:
            print("Port not found")
            
        return self.process_remote_target

    def print_file_to_log(self,file_path):
        sys.stdout = self.log
        print("app result:",self.print_process(self.process_remote_target))
        # 使用 with 打开文件，这样文件在读取后会自动关闭
        with open(file_path, 'r') as file:
            # 读取文件的所有内容
            file_content = file.read()
            
            # 打印文件内容
            print(file_content)


    def print_process(self,process):
        alloutput = ''
        # 捕获并打印输出
        while True:
            try:
                # 捕获输出并打印到屏幕
                output = process.read_nonblocking(size=1024, timeout=1).decode('utf-8')  # 每次读取 1024 字节
                if output:
                    #print(output)
                    alloutput = alloutput + '\n' +output.rstrip()
            except pexpect.TIMEOUT:
                break  # 如果没有输出，则继续循环
            except pexpect.EOF:
                break  # 如果进程结束，则退出循环
        return alloutput

    def error_spread(self,process,seq_casuse_signal):#此处的seq_casuse_signal是指错误引发点的序号,例如注错点是序号1,第一次修复则是2
        ##出发点是错误引发点,即注错点或第一次修复点,逐步执行,终点是收到signal或程序结束;返回值rcv_sig表示是否出错,output
        ##检查从注错/修复到出错的错误传播,只打印前MAX_ERROR_SPREAD长度的指令;当出现错误时,需要把signal打印,并且打印x/i $pc;当没有任何错误时;
        ##i = process.expect([pexpect.TIMEOUT, GDB_PROMOPT])
        #print((process.before.decode('utf-8'), process.after))
        stepi_num = 0
        output = 'NO OUTPUT'##用来保存出错类型,供接下来介入letgo_frame使用
        rcv_sig = 0

        output = self.print_process(process)
        print(output)
        print("\nSite",seq_casuse_signal,"Ready to record error spread.\n")
        
        while stepi_num <= MAX_ERROR_SPREAD:
            #打印前MAX_ERROR_SPREAD条指令
            try:
                stepi_output = ""
                process.sendline("stepi")
                i = process.expect([pexpect.TIMEOUT, "(gdb)"])
                stepioutput = process.before.decode('utf-8')

                if i == 0 :
                    print("error in stepi_in",seq_casuse_signal)
                    break
                # 打印当前指令
                if "received signal" in stepioutput:
                    rcv_sig = 1 #当前出错,不着急打印,等待判断附近之外出现signal后再一起打印
                    print(stepioutput.strip())
                    break
                if "The program is not being run." in stepioutput:
                    print("program stop!")
                    return 0,'no crash'
                print(stepi_num)
                stepi_num += 1
                if stepi_num >= MAX_ERROR_SPREAD:
                    break
                
                process.sendline(GDB_DISPLAY)
                i = process.expect([pexpect.TIMEOUT, "(gdb)"], timeout=5)  # 设置超时等待
                if i == 0:
                    print("Error: Timeout after x/i $pc.",seq_casuse_signal)
                    break
                pc_output = process.before.decode('utf-8').strip()
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
        
        """ if stepi_num < MAX_ERROR_SPREAD :#满足这个条件,必定在附近出现了signal
            if seq_casuse_signal == 0:
                print(PRT_ERR_LEN_INJ_SIG,stepi_num)
            if seq_casuse_signal == 1:
                print(PRT_ERR_LEN_FIX_SIG,stepi_num)
        else:#附近没有出错
            if seq_casuse_signal == 0:
                print(PTR_ERR_INJ_MAX)
            if seq_casuse_signal == 1:
                print(PTR_ERR_FIX_MAX)"""
        
        if rcv_sig == 0:##附近没有出错,就继续运行直到出错或者结束
            process.sendline(GDB_CONTINUE)
            i = process.expect([pexpect.TIMEOUT, GDB_PROMOPT])
            coutput = process.before.decode('utf-8')
            if "received signal" in coutput  :
                rcv_sig = 1
                print(re.sub(r'[\n()]', '', coutput))
            else:       #完美masked
                print(output)
            output = coutput
        if rcv_sig == 1:##此处gdb已经由于signal的存在而暂停,无论远近,采取同一个方法打印
            process.sendline(GDB_DISPLAY)
            process.expect([pexpect.TIMEOUT, GDB_PROMOPT])
            output = process.before.decode('utf-8')

        if output == "NO OUTPUT":
            print("seq",seq_casuse_signal,"receive no signal")
        else:
            print(output)

        if stepi_num < MAX_ERROR_SPREAD :#满足这个条件,必定在附近出现了signal，用于总结错误传播长度
            if seq_casuse_signal == 0:
                print(PRT_ERR_LEN_INJ_SIG,stepi_num)
            if seq_casuse_signal == 1:
                print(PRT_ERR_LEN_FIX_SIG,stepi_num)
        else:#附近没有出错
            if seq_casuse_signal == 0:
                print(PTR_ERR_INJ_MAX)
            if seq_casuse_signal == 1:
                print(PTR_ERR_FIX_MAX)
        return rcv_sig,output

    def info_at_signal(self,process):
        """#出错前手动调试
        sys.__stdout__.write("interact")
        process.interact()"""

        process.sendline("stepi")
        process.expect([pexpect.TIMEOUT, "(gdb)"])
        sigout = process.before.decode('utf-8')
        if "received signal" in sigout:
            
            process.expect([pexpect.TIMEOUT, "(gdb)"])
            process.sendline("backtrace")
            process.expect([pexpect.TIMEOUT, "(gdb)"])
            gdbout = process.before.decode('utf-8')
            print("\nat sig backtrace:\t",(gdbout),"backrace end")
        #出错前手动调试
        #sys.__stdout__.write("interact")
        #process.interact()

    def letgo_frame(self,process):
        ######  call this when encoutering SIG and gdb pause
        ###  LetGo framework steps in
        #####
        print('\nLetgo in!')
        self.letgo_start_time = datetime.datetime.now()
        process.sendline(GDB_PRINT_PC)
        i = process.expect([pexpect.TIMEOUT, GDB_PROMOPT])
        if i == 1:
            # parse the pc value by regex 0x
            # send the pc to pin, and get all info we need
            print('parse the pc value by regex 0x')
            print((process.before.decode('utf-8')))
            match = re.findall('0[xX]?[A-Fa-f0-9]+', process.before.decode('utf-8'))
            if len(match) == 0:
                print("Crash place getting no PC!")                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        
                self.log.close()
                process.close()
                sys.stdout = sys.__stdout__
                return
            #print(match[0])
            decpc = int(match[0], 0)    ##此处的match[0]是一个包含0x的十六进制地址,使用int将其转化为十进制
            try:
                fi = faultinject.FaultInjector(self.insts)
                args = fi.getNextPC(decpc)  ## 此处要关注faultinjecion.cpp中的getNextPC函数
                if len(args) != 8:
                    print("No nextpc!")
                    self.log.close()
                    process.close()
                    sys.stdout = sys.__stdout__
                    return
            except Exception as process_error:
                print("No nextpc!\nOpen file failed...")
                return
            
            print(args)
            nextpc = args[0]    ##ins的下一条指令
            regwlist = args[1]  ##ins的所有写寄存器的列表
            stack = args[2]     ##ins是栈操作则和base相同,否则为nostack
            flag = args[3]      ## stackw: 1, stackr: 2 , nostack: 3
            base = args[4]      ##ins在内存中的基地址
            index = args[5]     ##ins在内存中的索引寄存器值,基地址偏移
            displacement = args[6]  ##指令中内存操作的位移量
            scale = args[7]     ##内存因子,用来和index配合使用,实现复杂内存寻址
            
            process.sendline(GDB_PRINT_REG + " $pc=" + str(nextpc))
            i = process.expect([pexpect.TIMEOUT, GDB_PROMOPT])
            print("nextpc:\t",process.before.decode('utf-8'))
            if i == 0:
                print("ERROR when setting the pc value")
                print((process.before.decode('utf-8'), process.after))
                print((str(process)))
                self.log.close()
                process.close()
                sys.stdout = sys.__stdout__
                return

            if i == 1:
                #####
                # We can have multiple options here. For now, we feed the value (0) to the supposed-to-write register
                #####
                print('multiple options')
                if is_fake == 1:    ##处理写寄存器regw,is_fake是手动开关
                    for regw in regwlist:
                        if flag == 2:   ##这里是把regw设置成合适的值,else中是用一个fake值来替代regw
                            final_b = 0 ##base 
                            final_i = 0 ##index
                            final_d = 0 ##displacement
                            final_s = 0 ##scale
                            ## we can try to calculate a valid number for regw
                            if base == "":                          ##开始解析base
                                print("no base")
                                continue
                            print("base:\t",base)
                            process.sendline(GDB_PRINT_REG + " $" + base)   ##？？？
                            i = process.expect([pexpect.TIMEOUT, GDB_PROMOPT])
                            if i == 0:
                                print("ERROR when getting the base")
                                print((process.before.decode('utf-8'), process.after))
                                print((str(process)))
                                self.log.close()
                                process.close()
                                sys.stdout = sys.__stdout__
                                return
                            basestr = process.before.decode('utf-8')##开始解析basestr
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
                            if index == "null":         ##开始解析index
                                print("no index")
                            else:
                                process.sendline(GDB_PRINT_REG + " $" + index)
                                i = process.expect([pexpect.TIMEOUT, GDB_PROMOPT])
                                if i == 0:
                                    print("ERROR when getting the index")
                                    print((process.before.decode('utf-8'), process.after))
                                    print((str(process)))
                                    self.log.close()
                                    process.close()
                                    sys.stdout = sys.__stdout__
                                    return
                                indexstr = process.before.decode('utf-8')
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
                                ##用base,displacement,index,scale综合确定修改后的地址值
                                address = final_b + final_d + final_i * final_s   # 基地址、内存偏移量、基地址偏移、内存因子
                                print("address:"+str(address),"final_b:"+str(final_b),"final_d:"+str(final_d),"final_i:"+str(final_i),"final_s:"+str(final_s),)

                                process.sendline(GDB_PRINT_REG + " *" + str(address))
                                i = process.expect([pexpect.TIMEOUT, GDB_PROMOPT])
                                if i == 0:
                                    print("ERROR when getting the final value")
                                    print((process.before.decode('utf-8'), process.after))
                                    print((str(process)))
                                    self.log.close()
                                    process.close()
                                    sys.stdout = sys.__stdout__
                                    return
                                finalres = process.before.decode('utf-8')   # 打印位于address中的内容
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
                                print("change regw key:\t",regw)   
                                print("change regw value:\t",content.strip())
                                process.sendline(GDB_SET_REG + " $" + regw + "=" + content)     # 这是什么 为什么要这样
                                i = process.expect([pexpect.TIMEOUT, GDB_PROMOPT])
                                if i == 0:
                                    print("ERROR when setting the final value")
                                    print((process.before.decode('utf-8'), process.after))
                                    print((str(process)))
                                    self.log.close()
                                    process.close()
                                    sys.stdout = sys.__stdout__
                                    return
                                if i == 1:
                                    print("is stackr: have set reg with address calculation ")

                        else:   ##flag=!2用来控制这个分支条件
                            if "xmm" in regw:
                                regw = regw+".uint128"
                            process.sendline(GDB_SET_REG + " $" + regw + "=" + GDB_FAKE)   #？？？
                            i = process.expect([pexpect.TIMEOUT, GDB_PROMOPT])
                            if i == 0:
                                print("ERROR when setting the reg value")
                                print((process.before.decode('utf-8'), process.after))
                                print((str(process)))
                                self.log.close()
                                process.close()
                                sys.stdout = sys.__stdout__
                                return
                            if i == 1:
                                print("not stackr,so set fake:\t",regw)

                # try to set the rbp and rsp to reasonable values
                ##print('set rbp and rsp to reasonable values')  怎么判断
                if is_rewind == 1 and flag == 1:    ##这里flag和上面multiple options中的if冲突,也就是只有else执行时才执行此处;is_rewind是手动开关
                    print('stackw, set rbp and rsp to reasonable values')
                    stackinfo = ["rbp", "rsp"]
                    if stack != "":
                        size = fi.get_stack_size()  ##size保存的是ins所在函数初始为局部变量分配的空间大小,典型的函数栈帧设置的一部分
                        if size != "":
                            stackinfo.remove(stack)
                            rxp = stackinfo[0]
                            ##解析$rxp内容
                            process.sendline(GDB_PRINT_REG + " $" + rxp)
                            i = process.expect([pexpect.TIMEOUT, GDB_PROMOPT])
                            if i == 0:
                                print("ERROR when getting the value of the rbp or rsp")
                                print((process.before.decode('utf-8'), process.after))
                                print((str(process)))
                                self.log.close()
                                process.close()
                                sys.stdout = sys.__stdout__
                                return
                            if i == 1:
                                output = process.before.decode('utf-8')
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
                                ##解析$stack
                                process.sendline(GDB_PRINT_REG + " $" + stack)
                                i = process.expect([pexpect.TIMEOUT, GDB_PROMOPT])
                                if i == 0:
                                    print("ERROR when getting the value of the rbp or rsp")
                                    print((process.before.decode('utf-8'), process.after))
                                    print((str(process)))
                                    self.log.close()
                                    process.close()
                                    sys.stdout = sys.__stdout__
                                    return
                                if i == 1:
                                    output = process.before.decode('utf-8')
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
                                if abs(size_rxp - size_stack) > size and size_stack > size and size_rxp > size:##检测是否栈溢出
                                    process.sendline(GDB_SET_REG + " $" + stack + "=" + content_rxp)
                                    i = process.expect([pexpect.TIMEOUT, GDB_PROMOPT])
                                    if i == 0:
                                        print(("ERROR when resetting the " + stack))
                                        print((process.before.decode('utf-8'), process.after))
                                        print((str(process)))
                                        self.log.close()
                                        process.close()
                                        sys.stdout = sys.__stdout__
                                        return

                                    if i == 1:
                                        print(("Set the " + stack + " back! "))
                                        print((process.before.decode('utf-8'), process.after))
                    else:
                        print("Cannot get the size of the current stack frame")
                
    def handle_after_injection(self,process):
        rcv_sig,output= self.error_spread(process,0)
        

        if  rcv_sig == 1:
            """if reg == "" and ori_reg != "":
                process.sendline(GDB_SET_REG + " $" + regmm + "=" + ori_reg)
                i = process.expect([pexpect.TIMEOUT, GDB_PROMOPT])
                if i == 0:
                    print("ERROR when setting the regmm back after single step")
                    print((process.before.decode('utf-8'), process.after))
                    print((str(process)))
                    self.log.close()
                    process.close()
                    sys.stdout = sys.__stdout__
                    return
                if i == 1:
                    print((process.before.decode('utf-8')))
                    print("Change the value back")"""


            self.info_at_signal(process)
            self.letgo_start_time = datetime.datetime.now()
            self.letgo_frame(process)

            ##此处开始计算介入letgo_frame后的错误传播
            rcv_sig,output= self.error_spread(process,1)
            if rcv_sig == 0:
                print("Process Continue!\n")
                process.sendline(GDB_CONTINUE)
                print("Application output:\n")
                #print(output)
            if rcv_sig == 1:
                self.info_at_signal(process)
                process.sendline("kill")
                process.expect([pexpect.TIMEOUT, "(gdb)"])
                process.sendline("y")
                process.expect([pexpect.TIMEOUT, "(gdb)"])
            
            output = self.print_process(process)
            print(output)

            sdcjudger.SDC_saver(index = str(self.trial))
            self.sig_end_time = datetime.datetime.now()
            print("Letgo time: ",self.sig_end_time - self.letgo_start_time)
            print("sig time: ",self.sig_end_time - self.sig_start_time)
            print("Now Time:\t" , (datetime.datetime.now()))
            

                        
        if  rcv_sig == 0:
            #print(output,"\n")
            print("\nNo triggering crashes")
            print("Application output\n")

            output = self.print_process(process)
            print(output)

            sdcjudger.SDC_saver(index = str(self.trial))
            self.sig_end_time = datetime.datetime.now()
            print("sig time: ",self.sig_end_time - self.sig_start_time)
            print("Now Time:\t" , (datetime.datetime.now()))




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
            process.sendline(GDB_HANDLE_BUS)
            process.expect([pexpect.TIMEOUT, GDB_PROMOPT])
            print((process.before.decode('utf-8')))
            process.sendline(GDB_HANDLE_SEGV)
            process.expect([pexpect.TIMEOUT, GDB_PROMOPT])
            print((process.before.decode('utf-8')))
            process.sendline(GDB_HANDLE_ABT)
            process.expect([pexpect.TIMEOUT, GDB_PROMOPT])
            print((process.before.decode('utf-8')))

            # process.sendline(GDB_HANDLE_ALL)
            # process.expect([pexpect.TIMEOUT, GDB_PROMOPT])
            # print((process.before.decode('utf-8')))

            if configure.progname in configure.OpenMpOutPutList:
                GDB_ENV = "set env OUTPUT 1"
                process.sendline(GDB_ENV)
                process.expect([pexpect.TIMEOUT, GDB_PROMOPT])
                print(process.before.decode('utf-8'))            

        #self.inject_inst_by_breakpoint(process)

        self.process_remote_target = self.inject_inst_by_faultinjection(process)
        self.handle_after_injection(process)

        self.print_file_to_log(configure.activate)