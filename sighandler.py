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

# 影响力指标读取器
try:
    from influence_reader import print_influence_metrics, get_influence_metrics
    INFLUENCE_READER_AVAILABLE = True
except ImportError:
    INFLUENCE_READER_AVAILABLE = False
    print("[Warning] influence_reader module not available")

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
    return value.isdigit()  # Returns True if the value is an integer

class SigHandler:
    def __init__(self, insts, trial):
        self.insts = int(insts)
        self.trial = trial
        self.verbose_gdb = configure.gdb_verbose  # Controls whether to display GDB interaction info, default is False
        
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
        Unified GDB interaction method, sends command and waits for response, using unified print format
        
        Args:
            process: pexpect process object
            command: Command to send to GDB
            description: Command description for logging
            timeout: Timeout duration, None means use default
            verbose: Whether to print interaction info, default False
            
        Returns:
            tuple: (return code, response content)
            return code: 0=timeout, 1=success, 2=EOF
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
            # Only print response when it's not empty and not equal to command itself
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
        Extended GDB interaction method, supports custom expect patterns
        
        Args:
            process: pexpect process object
            command: Command to send to GDB
            description: Command description
            timeout: Timeout duration
            expect_patterns: Custom expect pattern list
            pattern_names: Corresponding pattern name list
            verbose: Whether to print interaction info, default False
            
        Returns:
            tuple: (matched pattern index, response content)
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
            # Only print response when it's not empty and not equal to command itself
            if verbose and response.strip() and response.strip() != command.strip():
                print(f"[gdb {pattern_names[i].lower()}] {response}")
        else:
            if verbose and response.strip() and response.strip() != command.strip():
                print(f"[gdb pattern_{i}] {response}")
            
        return i, response

    def gdb_send(self, process, command, description="", timeout=None):
        """Simplified GDB interaction method using class's verbose setting"""
        return self.gdb_sendline_and_expect(process, command, description, timeout, verbose=self.verbose_gdb)
    
    def gdb_send_extended(self, process, command, description="", timeout=None, expect_patterns=None, pattern_names=None):
        """Simplified extended GDB interaction method using class's verbose setting"""
        return self.gdb_sendline_and_expect_extended(process, command, description, timeout, expect_patterns, pattern_names, verbose=self.verbose_gdb)
    
    def enable_gdb_verbose(self):
        """Enable GDB interaction info display"""
        self.verbose_gdb = True
    
    def disable_gdb_verbose(self):
        """Disable GDB interaction info display"""
        self.verbose_gdb = False
    
    def gdb_send_verbose(self, process, command, description="", timeout=None,verbose=True):
        """Force GDB interaction info method"""
        return self.gdb_sendline_and_expect(process, command, description, timeout, verbose=verbose)
    
    def gdb_send_extended_force(self, process, command, description="", timeout=None, expect_patterns=None, pattern_names=None,verbose=True):
        """Force GDB interaction info extended method"""
        return self.gdb_sendline_and_expect_extended(process, command, description, timeout, expect_patterns, pattern_names, verbose=verbose)

    def inject_inst_by_breakpoint(self,process):
    # Prepare gdb run
        ###  IMPORTANT: The following output format is parsed by analyze.py, please do not modify key strings arbitrarily
        ###  Key parsing markers: "args ready for set breakpoint:", "display the inject inst start", "Fault injection is done"
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
                ##First try to extract instructions from the random instruction pool
                result = InstPoolMaker.readArgsFromPool()
                # Check if result length is 5
                if len(result) != 5:
                    raise ValueError("Wrong return values! Exit!")  # Throw exception to jump to except block
                args = result[0:4]
                randomnum = result[-1]
                print("-randinst", randomnum)  ###  IMPORTANT: analyze.py parses this format to extract random instruction number
            except:
                ##If instruction pool is empty, then directly find random instructions
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
            #Compatible with original output
            args = result[0:4]
            randomnum = result[-1]
            print(args)

        ##Parameters contain instruction and register information at dynamic instruction randomnum. pc is the ins value of that dynamic instruction, regmm or reg is randomly selected register from ins
        ##iteration indicates the number of times ins value equals pc value within randomnum range; that is, the number of iterations of pc value within randomnum range
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
        print('args ready for set breakpoint:\t',args)  ###  IMPORTANT: analyze.py parses this line to extract injection parameters
        hexpc = hex(int(pc))
        print('hexpc\t',hexpc)

        # 输出影响力指标到日志（供 analyze.py 收集）
        if INFLUENCE_READER_AVAILABLE and hasattr(configure, 'use_influence_analysis') and configure.use_influence_analysis:
            print_influence_metrics(pc)
        GDB_BREAKPOINT = "break *" + str(hexpc)
        i, bp_response = self.gdb_send(process, GDB_BREAKPOINT, f"Set breakpoint at address {hexpc}")
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


        i, output = self.gdb_send(process, GDB_RUN, "Run program to breakpoint")
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
                            process, GDB_CONTINUE, f"Continue to breakpoint (remaining {iteration} times)",
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

                        if i == 2:  # If it's pexpect.EOF, it means the process has exited
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
                
                i, response = self.gdb_send_verbose(process, GDB_SETPAGEOFF, "Disable pagination")

                i, output = self.gdb_send_verbose(process, GDB_BEFOREPC, "Display instructions before injection point")
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
                i, save_response = self.gdb_send_verbose(process, "set $saved_pc = $pc", "Save current PC value")
                i, inject_inst = self.gdb_send_extended(
                    process, "x/i $saved_pc", "Display instruction to be injected",
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
                    print("display the inject inst start:\n",inject_inst.strip(),"\ndisplay the inject inst end.")  ###  IMPORTANT: analyze.py parses this line to extract injection instruction
                if i == 2:
                    print("process end")
                    return

    # inject reg
                if regmm == "":  # it means that it is a normal instruction and we need to inject the fault to the dest reg
                    print('Meet a normal instruction:')
                    i, output = self.gdb_send(process, GDB_NEXT, "Single step instruction")
                    print(output)
                    if i == 0:
                        print('ERROR! Can not step in')
                        print((str(process)))
                        self.log.close()
                        process.close()
                        sys.stdout = sys.__stdout__
                        return
                    if i == 1:
                        i, reg_output = self.gdb_send_verbose(process, GDB_PRINT_REG + " $" + reg, f"Get register {reg} value")
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
                            i, set_output = self.gdb_send_verbose(process, GDB_SET_REG + " $" + reg + "=" + content, f"Inject fault value {content} to register {reg}")
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
                    i, output = self.gdb_send_verbose(process, GDB_PRINT_REG + " $" + regmm, f"Get memory register {regmm} value")
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
                        i, mem_output = self.gdb_send_verbose(process, GDB_SET_REG + " $" + regmm + "=" + content, f"Inject fault value {content} to memory register {regmm}")
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

                        ##Restore register value after fault injection to memory-related register
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
                process.interact()  # Interactive mode, allows user to control GDB directly"""

                i, delete_response = self.gdb_send(process, GDB_DELETE_BP, "Delete all breakpoints")
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
        # process entry state: gdb only specifies executable file
        # process exit state: pin injects fault into program and keeps debug port, process debugs pin-injected program through remote port
        ###  IMPORTANT: The following output format is parsed by analyze.py, please do not modify key strings arbitrarily
        ###  Key parsing markers: "fi inject instance:", "Activated:", "bit location:"
        benchmark = configure.benchmark
        execlist = []
        if configure.MPI_SET == 1:
            execlist.extend(configure.mpi_cmd)
        if configure.progname in configure.OpenMpOutPutList:
            execlist = ["env","OUTPUT=1"]  # Set environment variable OUTPUT=1
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

            i, response = self.gdb_send(process, gdb_command, f"Connect to remote debug port {port}")
            print("respone to 'target remote :' :\n",response)

            #print((process.before.decode('utf-8')))
        except:
            print("Port not found")
        
        print("inject inst by faultinjection has done")
        return self.process_remote_target

    def print_file_to_log(self,file_path):
        sys.stdout = self.log
        # Use with to open file, so the file will be automatically closed after reading
        with open(file_path, 'r') as file:
            # Read all content of the file
            file_content = file.read()
            
            # Print file content
            print(file_content)

    def capture_process_output(process, output_file_path):
        """
        Capture pexpect process output and write to file and console in real time
        """
        try:
            # Open file for writing
            with open(output_file_path, 'a') as output_file:

                while True:
                    try:
                        # Wait for output or termination
                        i = process.expect([pexpect.EOF, pexpect.TIMEOUT], timeout=1)
                        output = process.before.decode('utf-8').strip()

                        if output:
                            # Write to file and print to console in real time
                            output_file.write(output + '\n')
                            output_file.flush()  # Ensure content is written to file immediately
                            print(output)

                        if i == 0:  # EOF: process terminated
                            break

                    except pexpect.TIMEOUT:
                        # Catch timeout (non-fatal error)
                        continue
                    except pexpect.exceptions.ExceptionPexpect as e:
                        # Catch other pexpect exceptions
                        print("Error while capturing output:", e)
                        break
        except Exception as e:
            print("Unexpected error:", e)

    def print_process(self, process, max_timeout_retries=10):
        """
        Continuously read and print process output until process ends or maximum timeout count is reached.

        :param process: pexpect process object
        :param max_timeout_retries: maximum timeout retry count
        :return: complete output of the process
        """
        alloutput = ''
        timeout_retries = 0  # timeout retry counter

        while True:
            try:
                output = process.read_nonblocking(size=1024, timeout=1)  # Read 1024 bytes each time
                if isinstance(output, bytes):
                    output = output.decode('utf-8')  # Decode if it's bytes
                if output:
                    alloutput = alloutput + ' ' + output.strip()
                    timeout_retries = 0  # Reset timeout counter
            except pexpect.TIMEOUT:
                timeout_retries += 1  # Increment timeout retry count
                if timeout_retries >= max_timeout_retries:
                    #print("Process has no output, timeout count reached limit.")
                    break  # Exit when maximum retry count is reached
            except pexpect.EOF:
                break  # Exit when process ends

        return alloutput.strip()



    def error_spread(self,process,seq_casuse_signal):#Here seq_casuse_signal refers to the sequence number of the error trigger point, e.g., injection point is sequence 1, first repair is sequence 2
        ##Starting point is error trigger point, i.e., injection point or first repair point, execute step by step, end point is receiving signal or program end; return value rcv_sig indicates whether error occurred, output
        ##Check error propagation from injection/repair to error, only print first MAX_ERROR_SPREAD length instructions; when error occurs, need to print signal and print x/i $pc; when no error occurs;
        ###  IMPORTANT: The following output format is parsed by analyze.py, please do not modify key strings arbitrarily
        ###  Key parsing markers: "Valid Inj2Sig:", "Valid Fix2Sig:", "After Inject:", "After Fixed:"
        ##i = process.expect([pexpect.TIMEOUT, GDB_PROMOPT])
        #print((process.before.decode('utf-8'), process.after))
        stepi_num = 0
        output = 'NO OUTPUT'##Used to save error type for subsequent letgo_frame use
        rcv_sig = 0

        buffer_clear = self.print_process(process).strip()
        if buffer_clear:
            print("before spread clear buffer:")
            print(buffer_clear)
            print("end clear")

        print("\nSite",seq_casuse_signal,"Ready to record error spread.\n")
        
        while stepi_num <= MAX_ERROR_SPREAD:
            #Print first MAX_ERROR_SPREAD instructions
            try:
                stepioutput = ""
                i, stepioutput = self.gdb_send_extended(
                    process, "stepi", f"Single step execute instruction {stepi_num}",
                    expect_patterns=[pexpect.TIMEOUT, "(gdb)"],
                    pattern_names=["TIMEOUT", "PROMPT"])

                if i == 0 :
                    print("error in stepi_in",seq_casuse_signal)
                    print("error stepioutput\t",stepioutput,"end error stepioutput")
                    break
                # Print current instruction
                if "received signal" in stepioutput:
                    rcv_sig = 1 #Current error occurred, don't rush to print, wait for judgment after signal appears nearby then print together
                    print("received signal during error spread:")
                    stepioutput = "stepioutput:\t" + stepioutput
                    print(stepioutput.strip())
                    break
                print(stepi_num)
                stepi_num += 1
                if stepi_num >= MAX_ERROR_SPREAD:
                    break
                
                i, pc_output = self.gdb_send_extended(
                    process, GDB_DISPLAY, "Display current PC instruction",
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
                print(re.sub(r'[\n()]', '', pc_output))  # Print current PC status

            except pexpect.EOF:
                print("GDB process ended.")
                break
            except pexpect.TIMEOUT:
                print("Timeout waiting for GDB response.")
                break
        #print(i)
        #print("OUTPUT\n",output)
        ##End printing MAX_ERROR_SPREAD instructions
        
        if rcv_sig == 0:##No error occurred nearby, continue running until error or end
            i, coutput = self.gdb_send_extended(
                process, GDB_CONTINUE, "Continue execution until error or end",
                timeout=180, expect_patterns=[GDB_PROMOPT, pexpect.TIMEOUT],
                pattern_names=["PROMPT", "TIMEOUT"])
            if "received signal" in coutput:
                rcv_sig = 1
                print(re.sub(r'[\n()]', '', coutput))
            else:       #Perfect masked
                print(coutput)
        if rcv_sig == 1:##Here gdb has paused due to signal presence, regardless of distance, use same method to print
            i, output = self.gdb_send(process, GDB_DISPLAY, "Display crash point instruction")
            print("print $pc:\t",output)
        buffer = self.print_process(process)
        if not buffer.strip() == '':
            print("clear buffer:",self.print_process(process),"end clear.")


        if stepi_num < MAX_ERROR_SPREAD :#Meeting this condition, signal must have appeared nearby, used to summarize error propagation length
            if seq_casuse_signal == 0:
                print(PRT_ERR_LEN_INJ_SIG,stepi_num)
            if seq_casuse_signal == 1:
                print(PRT_ERR_LEN_FIX_SIG,stepi_num)
        else:  #No error occurred nearby
            if seq_casuse_signal == 0:
                print(PTR_ERR_INJ_MAX)
            if seq_casuse_signal == 1:
                print(PTR_ERR_FIX_MAX)
        return rcv_sig,output

    def info_at_signal(self,process):
        """#Manual debugging before error
        sys.__stdout__.write("interact")
        process.interact()"""

        i, sigout = self.gdb_send(process, "stepi", "Single step to get signal info")
        if "received signal" in sigout:
            print(sigout)
            i, pc_info = self.gdb_send(process, "x/i $pc", "Display current instruction")
            print(pc_info.replace("\n", "").replace("\r", ""))

            i, gdbout = self.gdb_send(process, "backtrace", "Display call stack")
            if i == 0:
                print("ERROR when watching backtrace")
                self.log.close()
                process.close()
                sys.stdout = sys.__stdout__
                return
            print("\nat sig backtrace:\t",(gdbout))

            # ====== Feature Collection: Call Stack Analysis ======
            print("=== Call Stack Features ===")  # analyze.py parsing marker
            try:
                # Feature 1: Call depth
                call_depth = gdbout.count('#')
                print(f"CallDepth: {call_depth}")

                # Feature 2: Complete call chain (top 8 frames)
                frames = re.findall(r'#\d+\s+.*?in\s+(\w+)', gdbout)
                if frames:
                    call_chain = '->'.join(frames[:8])
                    print(f"CallChain: {call_chain}")

                    # Feature 3: Distance from main
                    if 'main' in frames:
                        dist_from_main = frames.index('main')
                        print(f"DistFromMain: {dist_from_main}")
                    else:
                        print(f"DistFromMain: -1")

                    # Feature 4: Is recursive
                    is_recursive = len(frames) != len(set(frames))
                    print(f"IsRecursive: {is_recursive}")

                    # Feature 5: Caller function
                    if len(frames) > 1:
                        print(f"CallerFunc: {frames[1]}")
            except Exception as e:
                print(f"Error parsing backtrace: {e}")
            print("=== End Call Stack Features ===")
            # ====== End Feature Collection ======

            # if "return" in gdbout:
            #     process.sendline("return")
            #     print(process.expect([pexpect.TIMEOUT, "(gdb)"]))
            # print("backrace end")

    def letgo_frame(self,process):
        ######  call this when encoutering SIG and gdb pause
        ###  LetGo framework steps in
        #####
        ###  IMPORTANT: The following output format is parsed by analyze.py, please do not modify key strings arbitrarily
        ###  Key parsing markers: "Letgo in!", "parse the pc value", "h_1", "h_2", "h_3"
        print("="*60)
        print("  Step 1/6: LetGo framework started, beginning fault recovery")
        print("="*60)
        
        output = self.print_process(process)
        if output.strip():
            print("clear before:",output)
        print('\nLetgo in!')  ###  IMPORTANT: analyze.py parses this marker to identify LetGo framework startup
        self.letgo_start_time = datetime.datetime.now()
        
        print("\n  Step 1.1: Getting current crash point PC value")
        i, pc_response = self.gdb_send(process, GDB_PRINT_PC, "Getting current crash point PC value")
        if i != 1:
            print("ERROR: Cannot get PC value, recovery failed")
            print("error entering letgo: cannot print pc")
            return 1
    
        # parse the pc value by regex 0x
        # send the pc to pin, and get all info we need
        print('  Step 1.2: Parsing PC value and getting instruction information')
        output = pc_response
        if "receiced signal" in output:
            try:
                print("no => but find:\t",'0x'+output.split('0x')[1].split(' ')[0])
            except:
                print(output)
        else:
            print("parse the pc value by regex 0x")  ###  IMPORTANT: analyze.py parses this marker to get PC value
            print(output)
        match = re.findall('0[xX]?[A-Fa-f0-9]+', pc_response)
        if len(match) == 0:
            print("ERROR: Cannot extract PC address from output")
            print("Crash place getting no PC!")
            return 1
        
        decpc = int(match[0], 0)    ##Here match[0] is a hexadecimal address containing 0x, using int to convert it to decimal
        print(f"[Info] Parsed crash point PC address: {hex(decpc)}")
        
        print("\n  Step 1.3: Getting detailed instruction information through Pin tool")
        try:
            fi = faultinject.FaultInjector(self.insts)
            args = fi.getNextPC(decpc)  ## Need to pay attention to getNextPC function in faultinjecion.cpp here
            
            if len(args) != 9:
                print("ERROR: Instruction information returned by Pin tool is incomplete")
                print("No nextpc!")
                return 1
        except Exception as process_error:
            print("ERROR: Cannot get instruction information from Pin tool")
            print("No nextpc!\nOpen file failed...")
            return 1
        
        print("[Info] Instruction information returned by Pin tool:")
        print(args)
        
        print("\n  Step 1.4: Parsing instruction information parameters")
        thispc = decpc
        nextpc = args[0]    ##pc value of next instruction after ins
        regwlist = args[1]  ##list of all write registers of ins
        stack = args[2]     ##same as base if ins is stack operation, otherwise nostack
        flag = args[3]      ## stackw: 1, stackr: 2 , nostack: 3
        base = args[4]      ##base address of ins in memory
        index = args[5]     ##index register value in memory of ins, base offset
        displacement = args[6]  ##displacement amount of memory operation in instruction
        scale = args[7]     ##memory factor, used with index to achieve complex memory addressing
        regrlist = args[8]  ##list of all read registers of ins
        ###
        print(f"  - Current PC: {hex(thispc)}")
        print(f"  - Next instruction PC: {hex(nextpc) if isinstance(nextpc, int) else nextpc}")
        print(f"  - Write register list: {regwlist}")
        print(f"  - Read register list: {regrlist}")
        print(f"  - Stack operation identifier: {stack}")
        print(f"  - Instruction type flag: {flag} (1=stack write, 2=stack read, 3=non-stack operation)")
        print(f"  - Memory base register: {base}")
        print(f"  - Memory index register: {index}")
        print(f"  - Memory displacement: {displacement}")
        print(f"  - Memory scale factor: {scale}")

        # 在gdb中打印regwlist，base，index这些寄存器
        print("\n=== Register Values at Crash Point ===")
        for regw in regwlist:
            i, regwlist_val = self.gdb_send(process, "p/x $" + regw, "Get value of write register " + regw)
            if i == 1:
                reg_match = re.search(r'0x[0-9a-fA-F]+', regwlist_val)
                if reg_match:
                    print(f"  {regw}: {reg_match.group()}")
                else:
                    print(f"  {regw}: {regwlist_val}")
            else:
                print(f"  {regw}: Failed to get value")

        # 打印base寄存器
        if base and base != '' and base != 'null':
            i, base_val = self.gdb_send(process, "p/x $" + base, "Get value of base register " + base)
            if i == 1:
                base_match = re.search(r'0x[0-9a-fA-F]+', base_val)
                if base_match:
                    print(f"  {base}: {base_match.group()}")
                else:
                    print(f"  {base}: {base_val}")
            else:
                print(f"  {base}: Failed to get value")

        # 打印index寄存器
        if index and index != '' and index != 'null':
            i, index_val = self.gdb_send(process, "p/x $" + index, "Get value of index register " + index)
            if i == 1:
                index_match = re.search(r'0x[0-9a-fA-F]+', index_val)
                if index_match:
                    print(f"  {index}: {index_match.group()}")
                else:
                    print(f"  {index}: {index_val}")
            else:
                print(f"  {index}: Failed to get value")

        # 打印regrlist寄存器
        for regr in regrlist:
            i, regr_val = self.gdb_send(process, "p/x $" + regr, "Get value of read register " + regr)
            if i == 1:
                reg_match = re.search(r'0x[0-9a-fA-F]+', regr_val)
                if reg_match:
                    print(f"  {regr}: {reg_match.group()}")
                else:
                    print(f"  {regr}: {regr_val}")
            else:
                print(f"  {regr}: Failed to get value")

        print("=== End Register Values ===\n")

        # ====== Feature Collection: Register and Memory Features ======
        print("\n=== Register and Memory Features ===")
        try:
            # Feature 6: Stack pointer state
            i, rsp_val = self.gdb_send(process, "p/x $rsp", "Get RSP")
            i, rbp_val = self.gdb_send(process, "p/x $rbp", "Get RBP")

            if i == 1:
                rsp_match = re.search(r'0x[0-9a-fA-F]+', rsp_val)
                rbp_match = re.search(r'0x[0-9a-fA-F]+', rbp_val)
                if rsp_match and rbp_match:
                    rsp = int(rsp_match.group(), 16)
                    rbp = int(rbp_match.group(), 16)
                    rbp_rsp_delta = abs(rbp - rsp)
                    print(f"RBP_RSP_Delta: {rbp_rsp_delta}")

            # Feature 7: Stack frame size
            i, frame_info = self.gdb_send(process, "info frame", "Get frame info")
            if 'Stack level' in frame_info:
                print("StackFrameInfo:", frame_info.split('\n')[0])  # First line contains key info

            # Feature 8: Instruction operand features (from existing args)
            print(f"InstrFlag: {flag}")  # 1=stackw, 2=stackr, 3=nostack
            print(f"HasBase: {base != ''}")
            print(f"HasIndex: {index != 'null'}")
            print(f"HasDisplacement: {displacement != 0}")

        except Exception as e:
            print(f"Error collecting register features: {e}")
        print("=== End Register and Memory Features ===")
        # ====== End Feature Collection ======

        print("\n" + "="*60)
        print("  Step 2/6: Starting register recovery operation")
        print("="*60)
        
        do_recovery = 1
        self.enable_gdb_verbose()
        if do_recovery == 1:
            #####
            # We can have multiple options here. For now, we feed the value (0) to the supposed-to-write register
            #####
            print('  Step 2.1: Preparing recovery options')
            if set_reg_fake == 1:    ##Process write register regw, set_reg_fake is manual switch
                print(f"[Info] Write register list to recover: {regwlist}")
                for regw_idx, regw in enumerate(regwlist):
                    print(f"\n--- Recovering register {regw_idx+1}/{len(regwlist)}: {regw} ---")
                    if flag == 2:   ##Process stack read related registers, recalculate memory write position
                        print("    Step 2.2: Stack read instruction recovery - Recalculating memory address")
                        print("h_1 start")
                        final_b = 0 ##base 
                        final_i = 0 ##index
                        final_d = 0 ##displacement
                        final_s = 0 ##scale
                        ## we can try to calculate a valid number for regw
                        if base == "":                          ##Start parsing base
                            print("[Warning] No base address register, skipping this register recovery")
                            print("no base")
                            continue
                        print(f"    Sub-step 2.2.1: Get base address register {base} value")
                        print("base:\t",base)
                        i, basestr = self.gdb_send(process, GDB_PRINT_REG + " $" + base, f"Get base address register {base} value")
                        if i == 0:
                            print("ERROR: Cannot get base address register value")
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
                            final_b = int(content, 16)   ## Is the base before repair the same as the current base?
                        else:
                            final_b = int(content)  ##Base parsing completed, content saved the result of converting basestr from hexadecimal to decimal
                        print(f"    Sub-step 2.2.2: Get index register {index} value")
                        if index == "null":         ##Start parsing index
                            print("[Info] No index register")
                            print("no index")
                        else:
                            i, indexstr = self.gdb_send(process, GDB_PRINT_REG + " $" + index, f"Get index register {index} value")
                            if i == 0:
                                print("ERROR: Cannot get index register value")
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
                                final_i = int(content)  ##Index parsing completed

                            final_d = int(displacement)
                            final_s = int(scale)
                            
                            print("    Sub-step 2.2.3: Calculate effective memory address")
                            ##Use base, displacement, index, scale to comprehensively determine modified address value
                            address = final_b + final_d + final_i * final_s   # Base address, memory offset, base offset, memory factor
                            print(f"[Calculation] Effective address = base + displacement + index * scale")
                            print("address: {0}, final_b: {1}, final_d: {2}, final_i: {3}, final_s: {4}".format(
                                hex(address),  # Convert address to hexadecimal
                                hex(final_b),  # Convert final_b to hexadecimal
                                hex(final_d),           # Convert final_d to hexadecimal
                                hex(final_i),           # Convert final_i to hexadecimal
                                hex(final_s)            # Convert final_s to hexadecimal
                            ))
                            print(f"[Result] Calculated effective address: {hex(address)}")

                            print("    Sub-step 2.2.4: Read value at this address")
                            i, finalres = self.gdb_send(process, GDB_PRINT_REG + " *" + str(address), f"Read value at memory address {hex(address)}")
                            if i == 0:
                                print("ERROR: Cannot read value at memory address")
                                print("ERROR when getting the final value")
                                print((str(process)))
                                self.log.close()
                                process.close()
                                sys.stdout = sys.__stdout__
                                return
                            # What is finalres?
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

                            i, print_regw = self.gdb_send(process, GDB_PRINT_REG + " $" + regw, f"Get current value of target register {regw}")
                            if i == 0:
                                print("ERROR when getting the base")
                                print((str(process)))
                                self.log.close()
                                process.close()
                                sys.stdout = sys.__stdout__
                                return

                            print("    Sub-step 2.2.5: Set read value to target register")
                            print("change regw key:\t",regw.strip())   
                            print("unchanged regw value:\t",print_regw.strip())
                            print("change regw value to:\t",content.strip())
                            i, set_response = self.gdb_send(process, GDB_SET_REG + " $" + regw + "=" + content, f"Set register {regw} to {content}")
                            if i == 0:
                                print("ERROR: Cannot set register value")
                                print("ERROR when setting the final value")
                                print((str(process)))
                                self.log.close()
                                process.close()
                                sys.stdout = sys.__stdout__
                                return
                            if i == 1:
                                print("[Success] Stack read repair completed - Register value set through address calculation")
                                print("is stackr: have set reg with address calculation ")  ###  IMPORTANT: analyze.py parses this marker to identify h_1 repair strategy
                            print("h_1 end")

                    else:   ##Handle other memory-load, replace read data with 0, because there are many zeros in memory
                        print("    Sub-step 2.3: Non-stack read instruction repair - Set default value 0")
                        if "xmm" in regw:
                            regw = regw+".uint128"
                            print(f"[Info] XMM register detected, modified to {regw}")
                        print("h_2 start")
                        i, fake_response = self.gdb_send(process, GDB_SET_REG + " $" + regw + "=" + GDB_FAKE, f"Set register {regw} to default value {GDB_FAKE}")
                        if i == 0:
                            print("ERROR: Cannot set register default value")
                            print("ERROR when setting the reg value")
                            print((str(process)))
                            self.log.close()
                            process.close()
                            sys.stdout = sys.__stdout__
                            return
                        if i == 1:
                            print(f"[Success] Non-stack read repair completed - Set register {regw} = {GDB_FAKE}")
                            print("not stackr,so set fake:\t",regw)  ###  IMPORTANT: analyze.py parses this marker to identify h_2 repair strategy
                        print("h_2 end")

            print("\n" + "="*60)
            print("  Step 3/6: Stack pointer recovery operation")
            print("="*60)
            
            # try to set the rbp and rsp to reasonable values
            ##print('set rbp and rsp to reasonable values')  How to judge
            if is_rewind == 1 and (flag == 1 or flag == 2):    ##flag1 indicates stack write, here flag conflicts with if in multiple options above, that is, only when else executes will this be executed; is_rewind is manual switch
                print("  Step 3.1: Detected stack operation instruction, beginning stack pointer recovery")
                print("h_3 start")
                print('stackw, set rbp and rsp to reasonable values')
                stackinfo = ["rbp", "rsp"]
                print("stack:\t",stack)
                if stack != "" or force_fix_rbp:
                    print("  Step 3.2: Getting stack frame size information")
                    size = fi.get_stack_size()  ##size saves the space size initially allocated for local variables in the function where ins is located, a typical part of function stack frame setup
                    if size == "":
                        size = "0"
                    if size != "":
                        print(f"[Info] Retrieved stack frame size: {size}")
                        print("size:\t",size)
                        print("  Step 3.3: Determining stack pointer to be fixed")
                        try:
                            stackinfo.remove(stack)
                        except:
                            stack = "rbp"
                            stackinfo.remove("rbp")
                        rxp = stackinfo[0]#rxp=rsp
                        print(f"[Info] Stack operation register: {stack}, another stack pointer: {rxp}")
                        print("stack size != null, rxp=", rxp)
                        print(f"  Step 3.4: Getting current value of {rxp} register")
                        ##Parse $rxp content
                        i, output = self.gdb_send(process, GDB_PRINT_REG + " $" + rxp, f"Getting value of stack pointer register {rxp}")
                        if i == 0:
                            print(f"ERROR: Cannot get value of {rxp} register")
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
                            print(f"  Step 3.5: Getting current value of {stack} register")
                            ##Parse $stack
                            i, output = self.gdb_send(process, GDB_PRINT_REG + " $" + stack, f"Getting value of stack pointer register {stack}")
                            if i == 0:
                                print(f"ERROR: Cannot get value of {stack} register")
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
                            
                            print("  Step 3.6: Detecting stack overflow and fixing stack pointer")
                            print(f"[Check] {rxp} value: {size_rxp}, {stack} value: {size_stack}, stack frame size: {size}")
                            # if abs(size_rxp - size_stack) > size and size_stack > size and size_rxp > size:##Check if stack overflow
                            #     process.sendline(GDB_SET_REG + " $" + stack + "=" + content_rxp)
                            if (abs(size_rxp - size_stack) > size and size_stack > size and size_rxp > size) or (size_rxp-size_stack>0):##Check if stack overflow
                                print("[Detected] Stack overflow detected, beginning repair")
                                if stack == "rbp":
                                    setback = str(size_rxp+size)
                                    print(f"[Calculation] rbp repair value = {rxp} value + stack frame size = {size_rxp} + {size} = {setback}")
                                if stack == "rsp":
                                    setback = str(size_rxp-size)
                                    print(f"[Calculation] rsp repair value = {rxp} value - stack frame size = {size_rxp} - {size} = {setback}")
                                i, stack_response = self.gdb_send(process, GDB_SET_REG + " $" + stack + "=" + setback, f"Setting stack pointer {stack} to repair value {setback}")
                                if i == 0:
                                    print(f"ERROR: Cannot reset {stack} register")
                                    print(("ERROR when resetting the " + stack))
                                    print((str(process)))
                                    self.log.close()
                                    process.close()
                                    sys.stdout = sys.__stdout__
                                    return

                                if i == 1:
                                    print(f"[Success] Stack pointer {stack} recovery complete")
                                    print(("Set the " + stack + " back! "))  ###  IMPORTANT: analyze.py parses this marker to identify h_3 repair strategy
                                    print("h_3 end")
                                    nextpc = thispc
                                    print("[Info] Setting redo current instruction")
                                    print("redo:\t",nextpc)
                            else:
                                print("[Info] Stack overflow not detected, no stack pointer repair needed")
                    
                else:
                    print("[Warning] Cannot get current stack frame size, skipping stack pointer recovery")
                    print("Cannot get the size of the current stack frame")
            else:
                print("[Info] Non-stack operation instruction or stack recovery disabled, skipping stack pointer recovery")
        
        print("\n" + "="*60)
        print("  Step 4/6: Setting program counter to next instruction")
        print("="*60)
        
        #process.interact()
        print(f"  Step 4.1: Setting PC register to next instruction address")
        next_pc_hex = str(hex(int(nextpc)))
        i, gdb_response = self.gdb_send(process, GDB_SET_REG + " $pc=" + next_pc_hex, f"Setting PC register to {next_pc_hex}")
        print("nextpc:\t",gdb_response)
        if i == 0:
            print("ERROR: Cannot set PC value")
            print("ERROR when setting the pc value")
            print((str(process)))
            self.log.close()
            process.close()
            sys.stdout = sys.__stdout__
            return
        else:
            print(f"[Success] PC register set to: {next_pc_hex}")
        self.disable_gdb_verbose()
        
        print("\n" + "="*60)
        print("  Step 5/6: LetGo framework recovery complete")
        print("="*60)
        print("[Info] All recovery operations completed, program ready to continue execution")
        # 在gdb中打印regwlist，base，index这些寄存器
        print("\n=== Register Values after recovery ===")
        for regw in regwlist:
            i, regwlist_val = self.gdb_send(process, "p/x $" + regw, "Get value of write register " + regw)
            if i == 1:
                reg_match = re.search(r'0x[0-9a-fA-F]+', regwlist_val)
                if reg_match:
                    print(f"  {regw}: {reg_match.group()}")
                else:
                    print(f"  {regw}: {regwlist_val}")
            else:
                print(f"  {regw}: Failed to get value")

        # 打印base寄存器
        if base and base != '' and base != 'null':
            i, base_val = self.gdb_send(process, "p/x $" + base, "Get value of base register " + base)
            if i == 1:
                base_match = re.search(r'0x[0-9a-fA-F]+', base_val)
                if base_match:
                    print(f"  {base}: {base_match.group()}")
                else:
                    print(f"  {base}: {base_val}")
            else:
                print(f"  {base}: Failed to get value")

        # 打印index寄存器
        if index and index != '' and index != 'null':
            i, index_val = self.gdb_send(process, "p/x $" + index, "Get value of index register " + index)
            if i == 1:
                index_match = re.search(r'0x[0-9a-fA-F]+', index_val)
                if index_match:
                    print(f"  {index}: {index_match.group()}")
                else:
                    print(f"  {index}: {index_val}")
            else:
                print(f"  {index}: Failed to get value")

        # 打印regrlist寄存器
        for regr in regrlist:
            i, regr_val = self.gdb_send(process, "p/x $" + regr, "Get value of read register " + regr)
            if i == 1:
                reg_match = re.search(r'0x[0-9a-fA-F]+', regr_val)
                if reg_match:
                    print(f"  {regr}: {reg_match.group()}")
                else:
                    print(f"  {regr}: {regr_val}")
            else:
                print(f"  {regr}: Failed to get value")

        print("=== End Register Values ===\n")
        print(f"[Summary] Number of registers fixed: {len(regwlist) if regwlist else 0}")
        print(f"[Summary] Instruction type fixed: {'Stack read' if flag == 2 else 'Stack write' if flag == 1 else 'Non-stack operation'}")
        print(f"[Summary] Program will continue execution from address {next_pc_hex}")


    def handle_after_injection(self,process):
        print("process continue...")
        
        index, after_continue = self.gdb_send_extended(
            process, GDB_CONTINUE, "Continue program execution",
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
            raise Exception("Process timed out")  # Or use custom exception
            return
        #print(after_continue)
        
        if "received signal" in after_continue:
            print("\n" + "="*60)
            print("Modify state and error propagation detection")
            print("="*60)
            
            #print("after_continue:\t",after_continue)
            rcv_sig = 0 #Assume no signal will be received after repair
            print("Step 1: Getting signal details")
            self.info_at_signal(process)
            self.letgo_start_time = datetime.datetime.now()
            print("Step 2: Starting LetGo framework recovery (including 6 sub-steps)")
            exit_code = self.letgo_frame(process)
            rcv_sig = 0
            if exit_code == 1:#letgo execution failed
                print("[Error] LetGo framework recovery failed")
                rcv_sig =1
            else:
                print("[Success] LetGo framework recovery complete")
                

            ##After letgo_frame execution, start error propagation detection
            print("Step 3: Detecting error propagation after recovery")
            if rcv_sig==0:
                rcv_sig,output= self.error_spread(process,1)

            if rcv_sig == 0:
                print("[Success] No error propagation after repair, program can continue execution")
                print("Process Continue!\n")
                print("Step 4: Continue program execution")
                i, continue_response = self.gdb_send(process, GDB_CONTINUE, "Continue program after repair")
                print("Application output:\n")
                #print(output)
            if rcv_sig == 1:
                print("[Failed] Error propagation still exists, terminating program")
                print("Step 4: Terminate program execution")
                self.info_at_signal(process)
                i, kill_response = self.gdb_send(process, "kill", "Terminate program execution")
        else:   # No signal triggered after injection
            print("\n" + "="*60)
            print("Case: No signal triggered after injection - possibly SDC (Silent Data Corruption)")
            print("="*60)
            
            if after_continue.strip():
                print("after_continue:\t",after_continue)
            print("\n[Info] No crash signal triggered")
            print("No triggering crashes")

            output = self.print_process(process)
            if output.strip():
                print("clear buffer before sdc:")
                print(output)
                print("end buffer clear")
            
            print("[Info] Program may have experienced silent data corruption (SDC), further check output results")

        
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
        # Wait for process output until timeout or process ends
        result = self.process_remote_target.expect([pexpect.EOF, pexpect.TIMEOUT], timeout=300)  # Catch EOF or timeout
        # Get and print process output
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

        # 输出影响力指标到日志（PinFI 模式）
        if INFLUENCE_READER_AVAILABLE and hasattr(configure, 'use_influence_analysis') and configure.use_influence_analysis:
            try:
                # 从 activate 文件读取 PC
                if os.path.exists(configure.activate):
                    with open(configure.activate, 'r') as f:
                        for line in f:
                            if 'Activated:' in line:
                                # 格式: "Activated: <reg> in <pc>"
                                pc_str = line.strip().split()[-1]
                                if pc_str.startswith('0x'):
                                    pc = int(pc_str, 16)
                                else:
                                    pc = int(pc_str)
                                print_influence_metrics(pc)
                                break
            except Exception as e:
                print(f"[InfluenceReader] Error reading activate file: {e}")

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

            self.gdb_send(process, GDB_HANDLE_BUS, "Setting SIGBUS signal handler")
            self.gdb_send(process, GDB_HANDLE_SEGV, "Setting SIGSEGV signal handler") 
            self.gdb_send(process, GDB_HANDLE_ABT, "Setting SIGABRT signal handler")
            self.gdb_send(process, GDB_HANDLE_FPE, "Setting SIGFPE signal handler")
            self.gdb_send(process, "set print demangle on", "Enabling symbol name display")
            self.gdb_send(process, "set confirm off", "Disabling confirmation prompt")

            if configure.progname in configure.OpenMpOutPutList:
                GDB_ENV = "set env OUTPUT 1"
                self.gdb_send(process, GDB_ENV, "Setting environment variable OUTPUT=1")  

        if configure.inject_tool == 'pinfi':
            self.inject_by_pinfi_and_recover(process)
        elif configure.inject_tool == 'breakpoint':
            self.inject_by_breakpoint_and_recover(process)
