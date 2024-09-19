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
GDB_PROMOPT = "\(gdb\)"
GDB_RUN = "run"
GDB_LAUNCH = "gdb " + configure.benchmark
GDB_HANDLE_BUS = "handle SIGBUS nopass"
GDB_HANDLE_SEGV = "handle SIGSEGV nopass"
GDB_HANDLE_ABT = "handle SIGABRT nopass"
GDB_PRINT_PC = "print $pc"
GDB_CONTINUE = "c"
GDB_NEXT = "stepi"
GDB_PRINT_REG = "print"
GDB_SET_REG = "set"
GDB_FAKE = "0"
GDB_DELETE_BP = "delete breakpoints 1"
GDB_DISPLAY = "x/i $pc"

GDB_ERROR_SEGV = "Program received signal SIGSEGV"
GDB_ERROR_BUS = "Program received signal SIGBUS"
GDB_ERROR_ABT = "Program received signal SIGABT"

ERR_LEN_INJ_SIG = "Valid FaultInject2Sig:\t"
ERR_LEN_FIX_SIG = "Valid Fix2Sig:\t"
ERR_LEN_OVR_50 = "More than 50 instruction..."

is_fake = 1
is_rewind = 1

##log_path = "./log"
log_path = os.path.join(configure.letgo_base_home,configure.progname)
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

    def executeProgram(self):
        global GDB_LAUNCH, GDB_ARG, GDB_PROMOPT, GDB_RUN, GDB_HANDLE, GDB_ERROR, GDB_NEXT, GDB_CONTINUE, GDB_FAKE
        sig_time1 = datetime.datetime.now()
        GDB_RUN = "run"
        for item in configure.args:
            GDB_RUN += " " + item
        logname = os.path.join(log_path,('log_'+str(self.trial) ))
        #logname_err = os.path.join(log_path,('err_'+str(self.trial) ))
        log = open(str(logname), "w")
        #log_err = open(str(logname_err), "w")
        sys.stdout = log
        sys.stderr = log
        #sys.stdout = sys.__stdout__
        #print(log)
        ori_reg = ""
        process = pexpect.spawn(GDB_LAUNCH)
        print("do pexpect.spawn: gdb  has launched!")
        i = process.expect([pexpect.TIMEOUT, GDB_PROMOPT])
        if i == 0:
            print('ERROR! Could not run GDB')
            print((process.before.decode('utf-8'), process.after))
            print((str(process)))
            log.close()
            process.close()
            sys.stdout = sys.__stdout__
            return
        if i == 1:
            temp = process.before.decode('utf-8')  ## just to flush the before buffer
            print('Program starts!')
            process.sendline(GDB_HANDLE_BUS)
            process.expect([pexpect.TIMEOUT, GDB_PROMOPT])
            print((process.before.decode('utf-8')))
            process.sendline(GDB_HANDLE_SEGV)
            process.expect([pexpect.TIMEOUT, GDB_PROMOPT])
            print((process.before.decode('utf-8')))
            process.sendline(GDB_HANDLE_ABT)
            process.expect([pexpect.TIMEOUT, GDB_PROMOPT])
            print((process.before.decode('utf-8')))

        ##
        # Set a breakpoint: need pc and iteration number
        ##
        print('Start set a breakpoint...')
        fi = faultinject.FaultInjector(self.insts)
        args = fi.getBreakpoint  # [regmm, reg, pc, iteration]
        ##参数中包含的是在动态指令randomnum处的指令和寄存器信息.pc是该动态指令的ins值,regmm或reg是ins中随机挑选的寄存器
        ##iteration表示的是在randomnum范围内,ins值和pc值相同的次数;也就是pc值在randomnum范围内的迭代次数
        if len(args) != 4:
            print("Wrong return values! Exit!")
            log.close()
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
            log.close()
            process.close()
            sys.stdout = sys.__stdout__
            return
        if i == 1:
            print((process.before.decode('utf-8')))
            print('Successfully set the breakpoint')

        """print("GDB is now interactive. You can type GDB commands.")
        process.interact()  # 交互模式，允许用户直接控制 GDB"""

        process.sendline(GDB_RUN)
        i = process.expect([pexpect.TIMEOUT, GDB_PROMOPT])
        if i == 0:
            print('ERROR! Could not run the program')
            print((process.before.decode('utf-8'), process.after))
            print((str(process)))
            log.close()
            process.terminate()
            process.close()
            sys.stdout = sys.__stdout__
            return
        if i == 1:
            output = process.before.decode('utf-8')
            print('----------------------Start output----------------------\n',output,'\n----------------------End output----------------------')
            if "Breakpoint" in output:
                print("Pause at the breakpoint for the first time!")
                # inject a fault
                print('start inject a fault')
                if iteration > 1024:
                    iteration = random.randint(0, 1024)
                print('iteration:\t',iteration)
                while iteration > 0:
                    process.sendline(GDB_CONTINUE)
                    i = process.expect([pexpect.TIMEOUT, GDB_PROMOPT])
                    if i == 0:
                        print('ERROR while continuing the program')
                        print((process.before.decode('utf-8'), process.after))
                        print((str(process)))
                        log.close()
                        process.close()
                        sys.stdout = sys.__stdout__
                        return
                    if i == 1:
                        iteration -= 1

                ###
                # print out the current instruction for more info
                ###
                process.sendline(GDB_DISPLAY)
                i = process.expect([pexpect.TIMEOUT, GDB_PROMOPT])
                if i == 0:
                    print("ERROR when displaying the inst")
                    print((process.before.decode('utf-8'), process.after))
                    print((str(process)))
                    log.close()
                    process.close()
                    sys.stdout = sys.__stdout__
                    return

                if i == 1:
                    output = process.before.decode('utf-8')
                    print(output)

                if regmm == "":  # it means that it is a normal instruction and we need to inject the fault to the dest reg
                    print('Meet a normal instruction:')
                    process.sendline(GDB_NEXT)
                    i = process.expect([pexpect.TIMEOUT, GDB_PROMOPT])
                    if i == 0:
                        print('ERROR! Can not step in')
                        print((process.before.decode('utf-8'), process.after))
                        print((str(process)))
                        log.close()
                        process.close()
                        sys.stdout = sys.__stdout__
                        return
                    if i == 1:
                        process.sendline(GDB_PRINT_REG + " $" + reg)
                        i = process.expect([pexpect.TIMEOUT, GDB_PROMOPT])
                        if i == 0:
                            print('ERROR while analyzing the content of the register')
                            print((process.before.decode('utf-8'), process.after))
                            print((str(process)))
                            log.close()
                            sys.stdout = sys.__stdout__
                            print("exit due to sighandle: timeout")
                            sys.exit(1)
                        if i == 1:
                            output = process.before.decode('utf-8')
                            print(output)
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
                            print("content:\n",content)
                            content = fi.generateFaults(content)
                            process.sendline(GDB_SET_REG + " $" + reg + "=" + content)
                            i = process.expect([pexpect.TIMEOUT, GDB_PROMOPT])
                            if i == 0:
                                print('ERROR while waiting for changing the value')
                                print((process.before.decode('utf-8'), process.after))
                                print((str(process)))
                                log.close()
                                process.close()
                                sys.stdout = sys.__stdout__
                                return
                            if i == 1:
                                output = process.before.decode('utf-8')
                                if "=" in output:
                                    print("Fault injection is done")
                if reg == "":  # it means that it is a memory instruction. Need to inject before it is executed.
                    print('Meet a memory instruction:')
                    process.sendline(GDB_PRINT_REG + " $" + regmm)
                    i = process.expect([pexpect.TIMEOUT, GDB_PROMOPT])
                    if i == 0:
                        print('ERROR while analyzing the content of the register mem')
                        print((process.before.decode('utf-8'), process.after))
                        print((str(process)))
                        log.close()
                        process.close()
                        sys.stdout = sys.__stdout__
                        return
                    if i == 1:
                        output = process.before.decode('utf-8')
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
                        print("content:\n",content)
                        ori_reg = content.rstrip("\r\n")
                        if content!="":
                            print(content)
                            content = fi.generateFaults(content)
                        else:
                            print('error! content is null!')
                        process.sendline(GDB_SET_REG + " $" + regmm + "=" + content)
                        i = process.expect([pexpect.TIMEOUT, GDB_PROMOPT])
                        if i == 0:
                            print('ERROR while waiting for changing the value mem')
                            print((process.before.decode('utf-8'), process.after))
                            print((str(process)))
                            log.close()
                            process.close()
                            sys.stdout = sys.__stdout__
                            return
                        if i == 1:
                            output = process.before.decode('utf-8')
                            if "=" in output:
                                print("Fault injection is done mem")
                        ## change the regmm back to its original data after execution
                        ## need to single step one inst
                        '''
                        process.sendline(GDB_NEXT)
                        i = process.expect([pexpect.TIMEOUT, GDB_PROMOPT])
                        if i == 0:
                            print "ERROR when single step"
                            print process.before.decode('utf-8'), process.after
                            print str(process)
                            log.close()
                            process.close()
                            sys.stdout = sys.__stdout__
                            return
                        if i == 1:
                            print "Single step"
                            output = process.before.decode('utf-8')
                            if GDB_ERROR_BUS in output or GDB_ERROR_SEGV in output:
                                print "Crash after single step, considered working!"
                        process.sendline(GDB_SET_REG+" $"+regmm+"="+ori_reg)
                        i = process.expect([pexpect.TIMEOUT, GDB_PROMOPT])
                        if i == 0:
                            print "ERROR when setting the regmm back after single step"
                            print process.before.decode('utf-8'), process.after
                            print str(process)
                            log.close()
                            process.close()
                            sys.stdout = sys.__stdout__
                            return
                        if i == 1:
                            print "Change the value back"
                        '''
                process.sendline(GDB_DELETE_BP)
                i = process.expect([pexpect.TIMEOUT, GDB_PROMOPT])
                if i == 0:
                    print("ERROR when deleting breakpoints")
                    print((process.before.decode('utf-8'), process.after))
                    print((str(process)))
                    log.close()
                    process.close()
                    sys.stdout = sys.__stdout__
                    return
                if i == 1:
                    print("Delete all breakpoints")

                ##逐步执行,检查从注错到出错的错误传播;
                stepi_num = 0
                output = ''
                i = 1
                while True:
                    try:
                        process.sendline("stepi")
                        i = process.expect([pexpect.TIMEOUT, "(gdb)"])
                        if i == 0 :
                            break
                        # 打印当前指令
                        if "received signal" in process.before.decode('utf-8'):
                            output = process.before.decode('utf-8')
                            break
                        else:
                            process.sendline("x/i $pc")
                            i = process.expect([pexpect.TIMEOUT, "(gdb)"])
                            print(process.before.decode('utf-8'))
                            stepi_num += 1
                            if stepi_num >= 50:
                                break

                    except pexpect.EOF:
                        print("GDB process ended.")
                        break
                    except pexpect.TIMEOUT:
                        print("Timeout waiting for GDB response.")
                        break
                if stepi_num < 50 :
                    print(ERR_LEN_INJ_SIG,stepi_num)
                else:
                    print("After inject:" + ERR_LEN_OVR_50)
                
                process.sendline(GDB_CONTINUE)
                i = process.expect([pexpect.TIMEOUT, GDB_PROMOPT])

                if i == 0:
                    print("ERROR when passing to signal handler")
                    print((process.before.decode('utf-8'), process.after))
                    print((str(process)))
                    log.close()
                    process.close()
                    sys.stdout = sys.__stdout__
                    return

                if i == 1:
                    
                    output = process.before.decode('utf-8')
                    #print('judge letgo framwork2:\n',output)
                    if GDB_ERROR_SEGV in output or GDB_ERROR_BUS in output or GDB_ERROR_ABT in output:
                        ##
                        # Need to pass the current pc to pin, and get all the info
                        ##
                        if reg == "" and ori_reg != "":
                            process.sendline(GDB_SET_REG + " $" + regmm + "=" + ori_reg)
                            i = process.expect([pexpect.TIMEOUT, GDB_PROMOPT])
                            if i == 0:
                                print("ERROR when setting the regmm back after single step")
                                print((process.before.decode('utf-8'), process.after))
                                print((str(process)))
                                log.close()
                                process.close()
                                sys.stdout = sys.__stdout__
                                return
                            if i == 1:
                                print("Change the value back")
                        ######
                        ###  LetGo framework steps in
                        #####
                        print('Letgo in!')
                        process.sendline(GDB_PRINT_PC)
                        i = process.expect([pexpect.TIMEOUT, GDB_PROMOPT])
                        if i == 1:
                            # parse the pc value by regex 0x
                            # send the pc to pin, and get all info we need
                            print('parse the pc value by regex 0x')
                            print((process.before.decode('utf-8')))
                            match = re.findall('0[xX]?[A-Fa-f0-9]+', process.before.decode('utf-8'))
                            if len(match) == 0:
                                print("Error while getting no PC!")
                                log.close()
                                process.close()
                                sys.stdout = sys.__stdout__
                                return
                            print(match[0])
                            decpc = int(match[0], 0)    ##此处的match[0]是一个包含0x的十六进制地址,使用int将其转化为十进制
                            args = fi.getNextPC(decpc)  ## 此处要关注faultinjecion.cpp中的getNextPC函数
                            if len(args) != 8:
                                print("Error while returning incorrect length")
                                log.close()
                                process.close()
                                sys.stdout = sys.__stdout__
                                return
                            print(args)
                            try:
                                shutil.rmtree("graphics_output")
                                print("remove output file 1")
                            except:
                                print("Oops, no x.vec file found. Ignoring. 1")
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
                            if i == 0:
                                print("ERROR when setting the pc value")
                                print((process.before.decode('utf-8'), process.after))
                                print((str(process)))
                                log.close()
                                process.close()
                                sys.stdout = sys.__stdout__
                                return

                            if i == 1:
                                #####
                                # We can have multiple options here. For now, we feed the value (0) to the supposed-to-write register
                                #####
                                print('multiple options')
                                if is_fake == 1:    ##处理写寄存器regw
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
                                            print("base:/t",base)
                                            process.sendline(GDB_PRINT_REG + " $" + base)
                                            i = process.expect([pexpect.TIMEOUT, GDB_PROMOPT])
                                            if i == 0:
                                                print("ERROR when getting the base")
                                                print((process.before.decode('utf-8'), process.after))
                                                print((str(process)))
                                                log.close()
                                                process.close()
                                                sys.stdout = sys.__stdout__
                                                return
                                            basestr = process.before.decode('utf-8')##开始解析basestr
                                            print("basestr:/t",basestr)
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
                                                final_b = int(content, 16)
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
                                                    log.close()
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
                                                address = final_b + final_d + final_i * final_s

                                                process.sendline(GDB_PRINT_REG + " *" + str(address))
                                                i = process.expect([pexpect.TIMEOUT, GDB_PROMOPT])
                                                if i == 0:
                                                    print("ERROR when getting the final value")
                                                    print((process.before.decode('utf-8'), process.after))
                                                    print((str(process)))
                                                    log.close()
                                                    process.close()
                                                    sys.stdout = sys.__stdout__
                                                    return
                                                finalres = process.before.decode('utf-8')
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
                                                process.sendline(GDB_SET_REG + " $" + regw + "=" + content) 
                                                i = process.expect([pexpect.TIMEOUT, GDB_PROMOPT])
                                                if i == 0:
                                                    print("ERROR when setting the final value")
                                                    print((process.before.decode('utf-8'), process.after))
                                                    print((str(process)))
                                                    log.close()
                                                    process.close()
                                                    sys.stdout = sys.__stdout__
                                                    return
                                                if i == 1:
                                                    print("set reg with address calculation ")
                                                    print(content)

                                        else:   ##flag=!2用来控制这个分支条件
                                            if "xmm" in regw:
                                                regw = regw+".uint128"
                                            print("set fake:\t",regw)
                                            process.sendline(GDB_SET_REG + " $" + regw + "=" + GDB_FAKE)
                                            i = process.expect([pexpect.TIMEOUT, GDB_PROMOPT])
                                            if i == 0:
                                                print("ERROR when setting the reg value")
                                                print((process.before.decode('utf-8'), process.after))
                                                print((str(process)))
                                                log.close()
                                                process.close()
                                                sys.stdout = sys.__stdout__
                                                return
                                            if i == 1:
                                               print("set reg with fake")

                                # try to set the rbp and rsp to reasonable values
                                ##print('set rbp and rsp to reasonable values')
                                if is_rewind == 1 and flag == 1:    ##这里flag和上面multiple options中的if冲突,也就是只有else执行时才执行此处
                                    print('set rbp and rsp to reasonable values')
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
                                                log.close()
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
                                                size_rxp = 0
                                                if "0x" in content_rxp:
                                                    if is_hexnumber(content_rxp):
                                                        size_rxp = int(content_rxp, 16)
                                                else:
                                                    if is_number(content_rxp):
                                                        size_rxp = int(content_rxp)
                                                ##解析$stack
                                                process.sendline(GDB_PRINT_REG + " $" + stack)
                                                i = process.expect([pexpect.TIMEOUT, GDB_PROMOPT])
                                                if i == 0:
                                                    print("ERROR when getting the value of the rbp or rsp")
                                                    print((process.before.decode('utf-8'), process.after))
                                                    print((str(process)))
                                                    log.close()
                                                    process.close()
                                                    sys.stdout = sys.__stdout__
                                                    return
                                                if i == 1:
                                                    output = process.before.decode('utf-8')
                                                    print(output)
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
                                                    size_stack = 0
                                                    if "0x" in content_stack:
                                                        if is_hexnumber(content_stack):
                                                            size_stack = int(content_stack, 16)
                                                    else:
                                                        if is_number(content_stack):
                                                            size_stack = int(content_stack)

                                                size = int(size,16)
                                                if abs(size_rxp - size_stack) > size and size_stack > size and size_rxp > size:##检测是否栈溢出
                                                    process.sendline(GDB_SET_REG + " $" + stack + "=" + content_rxp)
                                                    i = process.expect([pexpect.TIMEOUT, GDB_PROMOPT])
                                                    if i == 0:
                                                        print(("ERROR when resetting the " + stack))
                                                        print((process.before.decode('utf-8'), process.after))
                                                        print((str(process)))
                                                        log.close()
                                                        process.close()
                                                        sys.stdout = sys.__stdout__
                                                        return

                                                    if i == 1:
                                                        print(("Set the " + stack + " back! "))
                                                        print((process.before.decode('utf-8'), process.after))
                                    else:
                                        print("Cannot get the size of the current stack frame")
                                '''
                                if reg == "":
                                    if "rbp" in regmm or "rsp" in regmm:
                                        process.sendline(GDB_SET_REG+" $"+regmm+"="+str(ori_reg))
                                        i = process.expect([pexpect.TIMEOUT,GDB_PROMOPT])
                                        if i == 0:
                                            print "ERROR when resetting the rbp and rsp"
                                            print process.before.decode('utf-8'), process.after
                                            print str(process)
                                            log.close()
                                            process.close()
                                            sys.stdout = sys.__stdout__
                                            return

                                        if i == 1:
                                            print "Set memory base back!"
                                            print process.before.decode('utf-8'), process.after

                                if regmm == "":
                                    if "rsi" in reg or "rdi" in reg:
                                        process.sendline(GDB_SET_REG+" $"+reg+"="+str(ori_reg))
                                        process.expect([pexpect.TIMEOUT,GDB_PROMOPT])
                                        if i == 0:
                                            print "ERROR when resetting the rsi and rdi"
                                            print process.before.decode('utf-8'), process.after
                                            print str(process)
                                            log.close()
                                            process.close()
                                            sys.stdout = sys.__stdout__
                                            return

                                        if i == 1:
                                            print "Set index base back!"
                                            print process.before.decode('utf-8'), process.after
                                '''
                                print((datetime.datetime.now()))


                                ##逐步执行,检查从注错到出错的错误传播;
                                stepi_num = 0
                                output = ''
                                i = 1
                                while True:
                                    try:
                                        process.sendline("stepi")
                                        i = process.expect([pexpect.TIMEOUT, "(gdb)"])
                                        if i == 0 :
                                            break
                                        # 打印当前指令
                                        if "received signal" in process.before.decode('utf-8'):
                                            output = process.before.decode('utf-8')
                                            break
                                        else:
                                            process.sendline("x/i $pc")
                                            i = process.expect([pexpect.TIMEOUT, "(gdb)"])
                                            print(process.before.decode('utf-8'))
                                            stepi_num += 1
                                            if stepi_num >= 50:
                                                break

                                    except pexpect.EOF:
                                        print("GDB process ended.")
                                        break
                                    except pexpect.TIMEOUT:
                                        print("Timeout waiting for GDB response.")
                                        break
                                if stepi_num < 50 :
                                    print(ERR_LEN_FIX_SIG,stepi_num)
                                else:
                                    print("After Fixed:" + ERR_LEN_OVR_50)


                                process.sendline(GDB_CONTINUE)
                                i = process.expect([pexpect.TIMEOUT, GDB_PROMOPT])
                                if i == 0:
                                    print("ERROR when continue after feeding the regsters")
                                    print((process.before.decode('utf-8'), process.after))
                                    print((str(process)))
                                    log.close()
                                    process.close()
                                    sys.stdout = sys.__stdout__
                                    return

                                if i == 1:
                                    print("Process Continue!\nApplication output")
                                    print((process.before.decode('utf-8'), process.after))
                                    sig_time2 = datetime.datetime.now()
                                    print("sig time: ",sig_time2 - sig_time1)
                                    log.close()
                                    process.close()
                                    sys.stdout = sys.__stdout__
                                print((datetime.datetime.now()))
                                
                    else:
                        print("No triggering crashes")
                        print("Application output")
                        print((process.before.decode('utf-8')))
                        sig_time2 = datetime.datetime.now()
                        print("sig time: ",sig_time2 - sig_time1)
                        sys.stdout = sys.__stdout__
        
            