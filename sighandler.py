import os
import sys
import re
import pexpect

import objdump
import faultinject
import configure

GDB_PROMOPT = "\(gdb\)"
GDB_RUN = "run "+configure.args
GDB_LAUNCH = "gdb "+configure.benchmark
GDB_HANDLE_BUS = "handle SIGBUS nopass"
GDB_HANDLE_SEGV = "handle SIGSEGV nopass"
GDB_PRINT_PC = "print $pc"
GDB_CONTINUE = "c"
GDB_NEXT = "stepi"
GDB_PRINT_REG = "print"
GDB_FAKE = "0"

GDB_ERROR_SEGV = "Program received signal SIGSEGV"
GDB_ERROR_BUS = "Program received signal SIGBUS"


class SigHandler:

    def __init__(self, insts,trial):
        self.insts = int(insts)
        self.trial = trial

    def executeProgram(self):
        global GDB_LAUNCH, GDB_ARG, GDB_PROMOPT, GDB_RUN, GDB_HANDLE, GDB_ERROR, GDB_NEXT,GDB_CONTINUE,GDB_FAKE
        log = open(str(self.trial),"w")
        sys.stdout = log
        process = pexpect.spawn(GDB_LAUNCH)
        i = process.expect([pexpect.TIMEOUT,GDB_PROMOPT])
        if i == 0:
            print('ERROR! Could not run GDB')
            print(process.before, process.after)
            print(str(process))
            log.close()
            sys.exit(1)
        if i == 1:
            temp = process.before ## just to flush the before buffer
            print('Program starts!')
            process.sendline(GDB_HANDLE_BUS)
            process.expect([pexpect.TIMEOUT, GDB_PROMOPT])
            print(process.before)
            process.sendline(GDB_HANDLE_SEGV)
            process.expect([pexpect.TIMEOUT, GDB_PROMOPT])
            print(process.before)

        ##
        # Set a breakpoint: need pc and iteration number
        ##
        fi = faultinject.FaultInjector(self.insts)
        args = fi.getBreakpoint() # [regmm, reg, pc, iteration]

        if len(args) != 4:
            print "Wrong return values! Exit!"
            log.close()
            sys.exit(1)

        regmm = args[0].rstrip("\n")
        reg = args[1].rstrip("\n")
        pc = args[2].rstrip("\n")
        iteration = int(args[3].rstrip("\n"))
        #next = hex(int(args[4]))
        print args
        hexpc = hex(int(pc))
        print hexpc
        GDB_BREAKPOINT = "break *"+str(hexpc)
        process.sendline(GDB_BREAKPOINT)
        i = process.expect([pexpect.TIMEOUT, GDB_PROMOPT])
        if i == 0:
            print'ERROR! Could not set the breakpoint'
            print process.before, process.after
            print str(process)
            log.close()
            sys.exit (1)
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
                        print 'ERROR while continuing the program'
                        print process.before, process.after
                        print str(process)
                        log.close()
                        sys.exit(1)
                    if i == 1:
                        iteration -= 1
                        print process.before
                        print "Jumping to the next iteration"

                if regmm == "": # it means that it is a normal instruction and we need to inject the fault to the dest reg
                    process.sendline(GDB_NEXT)
                    i = process.expect([pexpect.TIMEOUT, GDB_PROMOPT])
                    if i == 0:
                        print 'ERROR! Can not step in'
                        print process.before, process.after
                        print str(process)
                        log.close()
                        sys.exit(1)
                    if i == 1:
                        process.sendline(GDB_PRINT_REG+" $"+reg)
                        i = process.expect([pexpect.TIMEOUT, GDB_PROMOPT])
                        if i == 0:
                            print 'ERROR while analyzing the content of the register'
                            print process.before, process.after
                            print str(process)
                            log.close()
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
                            process.sendline(GDB_PRINT_REG+" "+reg+"="+content)
                            i = process.expect([pexpect.TIMEOUT, GDB_PROMOPT])
                            if i == 0:
                                print 'ERROR while waiting for changing the value'
                                print process.before, process.after
                                print str(process)
                                log.close()
                                sys.exit(1)
                            if i == 1:
                                output = process.before
                                if "=" in output:
                                    print "Fault injection is done"
                if reg == "": # it means that it is a memory instruction. Need to inject before it is executed.
                    process.sendline(GDB_PRINT_REG+" $"+regmm)
                    i = process.expect([pexpect.TIMEOUT, GDB_PROMOPT])
                    if i == 0:
                        print 'ERROR while analyzing the content of the register mem'
                        print process.before, process.after
                        print str(process)
                        log.close()
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
                        process.sendline(GDB_PRINT_REG+" "+regmm+"="+content)
                        i = process.expect([pexpect.TIMEOUT, GDB_PROMOPT])
                        if i == 0:
                            print 'ERROR while waiting for changing the value mem'
                            print process.before, process.after
                            print str(process)
                            log.close()
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
                    log.close()
                    sys.exit(1)

                if i == 1:

                    output = process.before
                    if GDB_ERROR_SEGV in output or GDB_ERROR_BUS in output:
                        ##
                        # Need to pass the current pc to pin, and get all the info
                        ##
                        process.sendline(GDB_PRINT_PC)
                        i = process.expect([pexpect.TIMEOUT,GDB_PROMOPT])
                        if i == 1:
                            # parse the pc value by regex 0x
                            # send the pc to pin, and get all info we need
                            match = re.findall('^(0[xX])?[A-Fa-f0-9]+$',process.before)
                            if len(match) == 0:
                                print "Error while getting no PC!"
                                log.close()
                                sys.exit(1)
                            decpc = int(match[0],0)
                            args = fi.getNextPC(decpc)
                            if len(args) != 2:
                                print "Error while returning incorrect length"
                                log.close()
                                sys.exit(1)

                            nextpc = args[0]
                            regwlist = args[1]
                            process.sendline(GDB_PRINT_REG+" $pc="+str(nextpc))
                            i = process.expect([pexpect.TIMEOUT, GDB_PROMOPT])
                            if i == 0:
                                print "ERROR when setting the pc value"
                                print process.before, process.after
                                print str(process)
                                log.close()
                                sys.exit(1)

                            if i == 1:
                            #####
                            # We can have multiple options here. For now, we feed the value (0) to the supposed-to-write register
                            #####
                                for reg in regwlist:
                                    process.sendline(GDB_PRINT_REG+" "+reg+"="+GDB_FAKE)
                                    i = process.expect([pexpect.TIMEOUT,GDB_PROMOPT])
                                    if i == 0:
                                         print "ERROR when setting the reg value"
                                         print process.before, process.after
                                         print str(process)
                                         log.close()
                                         sys.exit(1)



                                process.snedline(GDB_CONTINUE)
                                i = process.expect([pexpect.TIMEOUT,GDB_PROMOPT])
                                if i == 0:
                                    print "ERROR when continue after feeding the regsters"
                                    print process.before, process.after
                                    print str(process)
                                    log.close()
                                    sys.exit(1)

                                if i == 1:
                                    print "Program finishes!"
                                    print process.before, process.after
                                    log.close()
                                    sys.stdout = sys.__stdout__
                    else:
                        print process.before










