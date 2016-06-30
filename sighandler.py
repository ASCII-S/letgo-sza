import os
import sys
import re
import pexpect

import objdump
import faultinject

benchmark = ""
GDB_PROMOPT = "(gdb)"
GDB_ARG = "" # need a space in the beginning
GDB_RUN = "run"+GDB_ARG
GDB_LAUNCH = "gdb "+benchmark
GDB_HANDLE_BUS = "handle SIGBUS nopass"
GDB_HANDLE_SEGV = "handle SIGSEGV nopass"
GDB_PRINT_PC = "x/i $pc"
GDB_CONTINUE = "c"
GDB_NEXT = "stepi"
GDB_PRINT_REG = "print"

GDB_ERROR_SEGV = "Program received signal SIGSEGV"
GDB_ERROR_BUS = "Program received signal SIGBUS"

totalinst = ''

class SigHandler:

    def __init__(self, executable, insts):
        self.executable = executable
        self.insts = insts

    def executeProgram(self):
        global GDB_LAUNCH, GDB_ARG, GDB_PROMOPT, GDB_RUN, GDB_HANDLE, GDB_ERROR, GDB_NEXT,GDB_CONTINUE
        process = pexpect.spawn(GDB_LAUNCH)
        i = process.expect([pexpect.TIMEOUT,GDB_PROMOPT])
        if i == 0:
            print('ERROR! Could not run GDB')
            print(process.before, process.after)
            print(str(process))
            sys.exit (1)
        if i == 1:
            print('Program starts!')
            process.sendline(GDB_HANDLE_BUS)
            process.expect([pexpect.TIMEOUT, GDB_PROMOPT])
            print('Signal handler SIGBUS changed!')
            process.sendline(GDB_HANDLE_SEGV)
            process.expect([pexpect.TIMEOUT, GDB_PROMOPT])
            print('Signal handler SIGSEGV changed!')

        ##
        # Set a breakpoint: need pc and iteration number
        ##
        fi = faultinject(totalinst,benchmark)
        args = fi.getBreakpoint(totalinst) # [regmm, reg, pc, iteration]

        if len(args) != 5:
            print "Wrong return values! Exit!"
            exit()

        regmm = args[0]
        reg = args[1]
        pc = args[2]
        iteration = int(args[3])
        next = hex(int(args[4]))

        hexpc = hex(int(pc))
        print hexpc
        GDB_BREAKPOINT = "break *"+str(hexpc)
        process.sendline(GDB_BREAKPOINT)
        i = process.expect([pexpect.TIMEOUT, GDB_PROMOPT])
        if i == 0:
            print'ERROR! Could not set the breakpoint'
            print process.before, process.after
            print str(process)
            sys.exit (1)
        if i == 1:
            print 'Successfully set the breakpoint'


        process.sendline(GDB_RUN)
        i = process.expect([pexpect.TIMEOUT, GDB_PROMOPT])
        if i == 0:
            print 'ERROR! Could not run the program'
            print process.before, process.after
            print str(process)
            sys.exit(1)
        if i == 1:
            output = process.before
            if "Breakpoint" in output:
                print "Pause at the breakpoint for the first time!"
                # inject a fault
                while iteration > 0:
                    process.sendline(GDB_CONTINUE)
                    i = process.expect([pexpect.TIMEOUT, GDB_PROMOPT])
                    if i == 0:
                        print 'ERROR while conitinuing the program'
                        print process.before, process.after
                        print str(process)
                        sys.exit(1)
                    if i == 1:
                        iteration = iteration -1
                        print "Jumping to the next iteration"

                if regmm == "": # it means that it is a normal instruction and we need to inject the fault to the dest reg
                    process.sendline(GDB_NEXT)
                    i = process.expect([pexpect.TIMEOUT, GDB_PROMOPT])
                    if i == 0:
                        print 'ERROR! Can not step in'
                        print process.before, process.after
                        print str(process)
                        sys.exit(1)
                    if i == 1:
                        process.sendline(GDB_PRINT_REG+"$"+reg)
                        i = process.expect([pexpect.TIMEOUT, GDB_PROMOPT])
                        if i == 0:
                            print 'ERROR while analyzing the content of the register'
                            print process.before, process.after
                            print str(process)
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
                                content = items[len(items)-1]
                                content = fi.generateFaults(content)
                                process.sendline(GDB_PRINT_PC+" "+reg+"="+content)
                                i = process.expect([pexpect.TIMEOUT, GDB_PROMOPT])
                                if i == 0:
                                    print 'ERROR while waiting for changing the value'
                                    print process.before, process.after
                                    print str(process)
                                    sys.exit(1)
                                if i == 1:
                                    output = process.before
                                    if "=" in output:
                                        print "Fault injection is done"
                if reg == "": # it means that it is a memory instruction. Need to inject before it is executed.
                    process.sendline(GDB_PRINT_REG+"$"+regmm)
                    i = process.expect([pexpect.TIMEOUT, GDB_PROMOPT])
                    if i == 0:
                        print 'ERROR while analyzing the content of the register mem'
                        print process.before, process.after
                        print str(process)
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
                            content = items[len(items)-1]
                            content = fi.generateFaults(content)
                            process.sendline(GDB_PRINT_PC+" "+regmm+"="+content)
                            i = process.expect([pexpect.TIMEOUT, GDB_PROMOPT])
                            if i == 0:
                                print 'ERROR while waiting for changing the value mem'
                                print process.before, process.after
                                print str(process)
                                sys.exit(1)
                            if i == 1:
                                output = process.before
                                if "=" in output:
                                    print "Fault injection is done mem"
                process.sendline(GDB_CONTINUE)
                i = process.expect([pexpect.TIMEOUT, GDB_PROMOPT])
                if i == 0:
                    print "ERROR when passing to signal handler"
                    print process.before, process.after
                    print str(process)
                    sys.exit(1)

                if i == 1:

                    output = process.before
                    if GDB_ERROR_SEGV in output or GDB_ERROR_BUS in output:
                        process.sendline(GDB_PRINT_REG+" $pc="+str(next))











