import os
import sys
import re
import pexpect

import objdump
import faultinject
import configure
import random
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

is_fake = 1
is_rewind = 1


class SigHandler:
    def __init__(self, insts, trial):
        self.insts = int(insts)
        self.trial = trial

    def executeProgram(self):
        global GDB_LAUNCH, GDB_ARG, GDB_PROMOPT, GDB_RUN, GDB_HANDLE, GDB_ERROR, GDB_NEXT, GDB_CONTINUE, GDB_FAKE
        GDB_RUN = "run"
        for item in configure.args:
            GDB_RUN += " " + item
        log = open(str(self.trial), "w")
        sys.stdout = log
        ori_reg = ""
        process = pexpect.spawn(GDB_LAUNCH)
        i = process.expect([pexpect.TIMEOUT, GDB_PROMOPT])
        if i == 0:
            print('ERROR! Could not run GDB')
            print(process.before, process.after)
            print(str(process))
            log.close()
            process.close()
            sys.stdout = sys.__stdout__
            return
        if i == 1:
            temp = process.before  ## just to flush the before buffer
            print('Program starts!')
            process.sendline(GDB_HANDLE_BUS)
            process.expect([pexpect.TIMEOUT, GDB_PROMOPT])
            print(process.before)
            process.sendline(GDB_HANDLE_SEGV)
            process.expect([pexpect.TIMEOUT, GDB_PROMOPT])
            print(process.before)
            process.sendline(GDB_HANDLE_ABT)
            process.expect([pexpect.TIMEOUT, GDB_PROMOPT])
            print(process.before)

        ##
        # Set a breakpoint: need pc and iteration number
        ##
        fi = faultinject.FaultInjector(self.insts)
        args = fi.getBreakpoint  # [regmm, reg, pc, iteration]

        if len(args) != 4:
            print "Wrong return values! Exit!"
            log.close()
            process.close()
            sys.stdout = sys.__stdout__
            return

        for item in configure.outputfile:
            try:
                os.remove(item)
                print "remove output file "+item
            except:
                print "Oops, no "+item+" file found. Ignore in 1"

        regmm = args[0].rstrip("\n")
        reg = args[1].rstrip("\n")
        pc = args[2].rstrip("\n")
        iteration = int(args[3].rstrip("\n"))
        # next = hex(int(args[4]))
        print args
        hexpc = hex(int(pc))
        print hexpc
        GDB_BREAKPOINT = "break *" + str(hexpc)
        process.sendline(GDB_BREAKPOINT)
        i = process.expect([pexpect.TIMEOUT, GDB_PROMOPT])
        if i == 0:
            print'ERROR! Could not set the breakpoint'
            print process.before, process.after
            print str(process)
            log.close()
            process.close()
            sys.stdout = sys.__stdout__
            return
        if i == 1:
            print process.before
            print 'Successfully set the breakpoint'

        process.sendline(GDB_RUN)
        i = process.expect([pexpect.TIMEOUT, GDB_PROMOPT])
        if i == 0:
            print 'ERROR! Could not run the program'
            print process.before, process.after
            print str(process)
            log.close()
            process.terminate()
            process.close()
            sys.stdout = sys.__stdout__
            return
        if i == 1:
            output = process.before
            if "Breakpoint" in output:
                print "Pause at the breakpoint for the first time!"
                # inject a fault
                if iteration > 1024:
                    iteration = random.randint(0, 1024)
                print iteration
                while iteration > 0:
                    process.sendline(GDB_CONTINUE)
                    i = process.expect([pexpect.TIMEOUT, GDB_PROMOPT])
                    if i == 0:
                        print 'ERROR while continuing the program'
                        print process.before, process.after
                        print str(process)
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
                    print "ERROR when displaying the inst"
                    print process.before, process.after
                    print str(process)
                    log.close()
                    process.close()
                    sys.stdout = sys.__stdout__
                    return

                if i == 1:
                    output = process.before
                    print output

                if regmm == "":  # it means that it is a normal instruction and we need to inject the fault to the dest reg
                    process.sendline(GDB_NEXT)
                    i = process.expect([pexpect.TIMEOUT, GDB_PROMOPT])
                    if i == 0:
                        print 'ERROR! Can not step in'
                        print process.before, process.after
                        print str(process)
                        log.close()
                        process.close()
                        sys.stdout = sys.__stdout__
                        return
                    if i == 1:
                        process.sendline(GDB_PRINT_REG + " $" + reg)
                        i = process.expect([pexpect.TIMEOUT, GDB_PROMOPT])
                        if i == 0:
                            print 'ERROR while analyzing the content of the register'
                            print process.before, process.after
                            print str(process)
                            log.close()
                            sys.stdout = sys.__stdout__
                            sys.exit(1)
                        if i == 1:
                            output = process.before
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
                            if content == "nodigit":
                                print "ERROR when generating faults"
                                print str(process)
                                log.close()
                                process.close()
                                sys.stdout = sys.__stdout__
                                return
                            process.sendline(GDB_SET_REG + " $" + reg + "=" + content)
                            i = process.expect([pexpect.TIMEOUT, GDB_PROMOPT])
                            if i == 0:
                                print 'ERROR while waiting for changing the value'
                                print process.before, process.after
                                print str(process)
                                log.close()
                                process.close()
                                sys.stdout = sys.__stdout__
                                return
                            if i == 1:
                                output = process.before
                                if "=" in output:
                                    print "Fault injection is done"
                if reg == "":  # it means that it is a memory instruction. Need to inject before it is executed.
                    process.sendline(GDB_PRINT_REG + " $" + regmm)
                    i = process.expect([pexpect.TIMEOUT, GDB_PROMOPT])
                    if i == 0:
                        print 'ERROR while analyzing the content of the register mem'
                        print process.before, process.after
                        print str(process)
                        log.close()
                        process.close()
                        sys.stdout = sys.__stdout__
                        return
                    if i == 1:
                        output = process.before
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
                        ori_reg = content.rstrip("\r\n")
                        content = fi.generateFaults(content)
                        if content == "nodigit":
                                print "ERROR when generating faults"
                                print str(process)
                                log.close()
                                process.close()
                                sys.stdout = sys.__stdout__
                                return
                        process.sendline(GDB_SET_REG + " $" + regmm + "=" + content)
                        i = process.expect([pexpect.TIMEOUT, GDB_PROMOPT])
                        if i == 0:
                            print 'ERROR while waiting for changing the value mem'
                            print process.before, process.after
                            print str(process)
                            log.close()
                            process.close()
                            sys.stdout = sys.__stdout__
                            return
                        if i == 1:
                            output = process.before
                            if "=" in output:
                                print "Fault injection is done mem"
                        ## change the regmm back to its original data after execution
                        ## need to single step one inst
                        '''
                        process.sendline(GDB_NEXT)
                        i = process.expect([pexpect.TIMEOUT, GDB_PROMOPT])
                        if i == 0:
                            print "ERROR when single step"
                            print process.before, process.after
                            print str(process)
                            log.close()
                            process.close()
                            sys.stdout = sys.__stdout__
                            return
                        if i == 1:
                            print "Single step"
                            output = process.before
                            if GDB_ERROR_BUS in output or GDB_ERROR_SEGV in output:
                                print "Crash after single step, considered working!"
                        process.sendline(GDB_SET_REG+" $"+regmm+"="+ori_reg)
                        i = process.expect([pexpect.TIMEOUT, GDB_PROMOPT])
                        if i == 0:
                            print "ERROR when setting the regmm back after single step"
                            print process.before, process.after
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
                    print "ERROR when deleting breakpoints"
                    print process.before, process.after
                    print str(process)
                    log.close()
                    process.close()
                    sys.stdout = sys.__stdout__
                    return
                if i == 1:
                    print "Delete all breakpoints"

                print datetime.datetime.now()
                process.sendline(GDB_CONTINUE)
                i = process.expect([pexpect.TIMEOUT, GDB_PROMOPT])
                if i == 0:
                    print "ERROR when passing to signal handler"
                    print process.before, process.after
                    print str(process)
                    log.close()
                    process.close()
                    sys.stdout = sys.__stdout__
                    return

                if i == 1:
                    print datetime.datetime.now()
                    output = process.before
                    print output
                    if GDB_ERROR_SEGV in output or GDB_ERROR_BUS in output or GDB_ERROR_ABT in output:
                        ##
                        # Need to pass the current pc to pin, and get all the info
                        ##
                        if reg == "" and ori_reg != "":
                            process.sendline(GDB_SET_REG + " $" + regmm + "=" + ori_reg)
                            i = process.expect([pexpect.TIMEOUT, GDB_PROMOPT])
                            if i == 0:
                                print "ERROR when setting the regmm back after single step"
                                print process.before, process.after
                                print str(process)
                                log.close()
                                process.close()
                                sys.stdout = sys.__stdout__
                                return
                            if i == 1:
                                print "Change the value back"
                        ######
                        ###  LetGo framework steps in
                        #####
                        process.sendline(GDB_PRINT_PC)
                        i = process.expect([pexpect.TIMEOUT, GDB_PROMOPT])
                        if i == 1:
                            # parse the pc value by regex 0x
                            # send the pc to pin, and get all info we need
                            print process.before
                            match = re.findall('0[xX]?[A-Fa-f0-9]+', process.before)
                            if len(match) == 0:
                                print "Error while getting no PC!"
                                log.close()
                                process.close()
                                sys.stdout = sys.__stdout__
                                return
                            decpc = int(match[0], 0)
                            args = fi.getNextPC(decpc)
                            if len(args) != 8:
                                print "Error while returning incorrect length"
                                log.close()
                                process.close()
                                sys.stdout = sys.__stdout__
                                return
                            print args
                            for item in configure.outputfile:
                                try:
                                    os.remove(item)
                                    print "remove output file "+item
                                except:
                                    print "Oops, no "+item+" file found. Ignore in 2"
                            nextpc = args[0]
                            regwlist = args[1]
                            stack = args[2]
                            flag = args[3]
                            base = args[4]
                            index = args[5]
                            displacement = args[6]
                            scale = args[7]
                            process.sendline(GDB_PRINT_REG + " $pc=" + str(nextpc))
                            i = process.expect([pexpect.TIMEOUT, GDB_PROMOPT])
                            if i == 0:
                                print "ERROR when setting the pc value"
                                print process.before, process.after
                                print str(process)
                                log.close()
                                process.close()
                                sys.stdout = sys.__stdout__
                                return

                            if i == 1:
                                #####
                                # We can have multiple options here. For now, we feed the value (0) to the supposed-to-write register
                                #####
                                if is_fake == 1:
                                    for regw in regwlist:
                                        if flag == 2:
                                            final_b = 0
                                            final_i = 0
                                            final_d = 0
                                            final_s = 0
                                            ## we can try to calculate a valid number for regw
                                            if base == "":
                                                print "no base"
                                                continue
                                            process.sendline(GDB_PRINT_REG + " $" + base)
                                            i = process.expect([pexpect.TIMEOUT, GDB_PROMOPT])
                                            if i == 0:
                                                print "ERROR when getting the base"
                                                print process.before, process.after
                                                print str(process)
                                                log.close()
                                                process.close()
                                                sys.stdout = sys.__stdout__
                                                return
                                            basestr = process.before
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
                                                final_b = int(content)
                                            if index == "null":
                                                print "no index"
                                            else:
                                                process.sendline(GDB_PRINT_REG + " $" + index)
                                                i = process.expect([pexpect.TIMEOUT, GDB_PROMOPT])
                                                if i == 0:
                                                    print "ERROR when getting the index"
                                                    print process.before, process.after
                                                    print str(process)
                                                    log.close()
                                                    process.close()
                                                    sys.stdout = sys.__stdout__
                                                    return
                                                indexstr = process.before
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
                                                    final_i = int(content)

                                                final_d = int(displacement)
                                                final_s = int(scale)
                                                address = final_b + final_d + final_i * final_s
                                                process.sendline(GDB_PRINT_REG + " *" + str(address))
                                                i = process.expect([pexpect.TIMEOUT, GDB_PROMOPT])
                                                if i == 0:
                                                    print "ERROR when getting the final value"
                                                    print process.before, process.after
                                                    print str(process)
                                                    log.close()
                                                    process.close()
                                                    sys.stdout = sys.__stdout__
                                                    return
                                                finalres = process.before
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
                                                    print "ERROR when setting the final value"
                                                    print process.before, process.after
                                                    print str(process)
                                                    log.close()
                                                    process.close()
                                                    sys.stdout = sys.__stdout__
                                                    return
                                                if i == 1:
                                                    print "set reg with address calculation "
                                                    print content

                                        else:
                                            process.sendline(GDB_SET_REG + " $" + regw + "=" + GDB_FAKE)
                                            i = process.expect([pexpect.TIMEOUT, GDB_PROMOPT])
                                            if i == 0:
                                                print "ERROR when setting the reg value"
                                                print process.before, process.after
                                                print str(process)
                                                log.close()
                                                process.close()
                                                sys.stdout = sys.__stdout__
                                                return
                                            if i == 1:
                                               print "set reg with fake"

                                # try to set the rbp and rsp to reasonable values
                                if is_rewind == 1 and flag == 1:
                                    stackinfo = ["rbp", "rsp"]
                                    if stack != "":
                                        size = fi.getStackSize()
                                        stackinfo.remove(stack)
                                        rxp = stackinfo[0]
                                        process.sendline(GDB_PRINT_REG + " $" + rxp)
                                        i = process.expect([pexpect.TIMEOUT, GDB_PROMOPT])
                                        if i == 0:
                                            print "ERROR when getting the value of the rbp or rsp"
                                            print process.before, process.after
                                            print str(process)
                                            log.close()
                                            process.close()
                                            sys.stdout = sys.__stdout__
                                            return

                                        if i == 1:
                                            output = process.before
                                            content_rxp = ""
                                            if "0x" in output:
                                                items = output.split(" ")
                                                for item in items:
                                                    if "0x" in item:
                                                        content_rxp = item
                                            else:
                                                items = output.split(" ")
                                                content_rxp = items[len(items) - 1]
                                            process.sendline(GDB_PRINT_REG+" $"+stack)
                                            if i == 0:
                                                print "ERROR when getting the value of the rbp or rsp"
                                                print process.before, process.after
                                                print str(process)
                                                log.close()
                                                process.close()
                                                sys.stdout = sys.__stdout__
                                                return

                                            if i == 1:
                                                output = process.before
                                                content_stack = ""
                                                if "0x" in output:
                                                    items = output.split(" ")
                                                    for item in items:
                                                        if "0x" in item:
                                                            content_stack = item
                                                else:
                                                    items = output.split(" ")
                                                    content_stack = items[len(items) - 1]
                                            if abs(int(content_stack,16) - int(content_rxp,16)) > int(size,16):
                                                i = process.sendline(GDB_SET_REG + " $" + stack + "=" + content_rxp)
                                                if i == 0:
                                                    print "ERROR when resetting the " + stack
                                                    print process.before, process.after
                                                    print str(process)
                                                    log.close()
                                                    process.close()
                                                    sys.stdout = sys.__stdout__
                                                    return

                                                if i == 1:
                                                    print "Set the " + stack + " back! "
                                                    print process.before, process.after
                                '''
                                if reg == "":
                                    if "rbp" in regmm or "rsp" in regmm:
                                        process.sendline(GDB_SET_REG+" $"+regmm+"="+str(ori_reg))
                                        i = process.expect([pexpect.TIMEOUT,GDB_PROMOPT])
                                        if i == 0:
                                            print "ERROR when resetting the rbp and rsp"
                                            print process.before, process.after
                                            print str(process)
                                            log.close()
                                            process.close()
                                            sys.stdout = sys.__stdout__
                                            return

                                        if i == 1:
                                            print "Set memory base back!"
                                            print process.before, process.after

                                if regmm == "":
                                    if "rsi" in reg or "rdi" in reg:
                                        process.sendline(GDB_SET_REG+" $"+reg+"="+str(ori_reg))
                                        process.expect([pexpect.TIMEOUT,GDB_PROMOPT])
                                        if i == 0:
                                            print "ERROR when resetting the rsi and rdi"
                                            print process.before, process.after
                                            print str(process)
                                            log.close()
                                            process.close()
                                            sys.stdout = sys.__stdout__
                                            return

                                        if i == 1:
                                            print "Set index base back!"
                                            print process.before, process.after
                                '''
                                print datetime.datetime.now()
                                process.sendline(GDB_CONTINUE)
                                i = process.expect([pexpect.TIMEOUT, GDB_PROMOPT])
                                if i == 0:
                                    print "ERROR when continue after feeding the regsters"
                                    print process.before, process.after
                                    print str(process)
                                    log.close()
                                    process.close()
                                    sys.stdout = sys.__stdout__
                                    return

                                if i == 1:
                                    print "Application output"
                                    print "After continue"
                                    print datetime.datetime.now()
                                    print process.before, process.after
                                    log.close()
                                    process.close()
                                    sys.stdout = sys.__stdout__
                    else:
                        print datetime.datetime.now()
                        print "No triggering crashes"
                        print "Application output"
                        print process.before
                        sys.stdout = sys.__stdout__
