import sys
import os
import subprocess
import time
import random
import pexpect

toolbase = "/home/bo/pb_interceptor"
pinbase = "/home/bo/pin-2.11-49306-gcc.3.4.6-ia32_intel64-linux/pin"
randinst_lib = "obj-intel64/randomInst.so"
randinst_config = "-randinst"

iterationinst = "obj-intel64/determineInst.so"
iterationinst_config1 = "-pc"
iterationinst_config2 = "-randomInt"

binary = ""
timeout = 500

instructionfile = "instruction"
iterationfile = "iteration"


class FaultInjector:

    def __init__(self, binary, totalInst):
        self.totalInst = totalInst
        self.binary = binary

    def getBreakpoint(self,total):
        ## get
        """

        :rtype: strings
        """
        randomnum = random.randint(0,total)
        execlist = [pinbase,"-t",os.path.join(toolbase,randinst_lib),randinst_config,str(randomnum),"--",self.binary]
        self.execute(execlist)
        # check if the file is generated
        if os.path.isfile(instructionfile) != True:
            print "No File generated!"
            exit()
        regmem = ""
        reg = ""
        pc = ""
        iteration = ""
        next = ""
        with open(instructionfile,"r") as f:
            lines = f.readlines()
            for line in lines:
                line = line.rstrip("")
                if "REGNOTVALID" in line:
                    print "REG not valid! Exit"
                    exit()
                if "mem:" in line:
                    regmem = line.split(":")[1]
                if "reg:" in line:
                    reg = line.split(":")[1]
                if "pc:" in line:
                    pc = line.split(":")[1]
                if "next:" in line:
                    next = line.split(":")[1]
        if reg == "" and regmem == "":
            print "No reg, Exit"
            exit()
        execlist = [pinbase,"-t",os.path.join(toolbase,iterationinst),iterationinst_config1,str(pc),iterationinst_config2,randomnum,"--",self.binary]
        self.execute(execlist)

        if os.path.isfile(iterationfile):
            print "No iteration file generated! Exit"
            exit()

        with open(iterationfile,"r") as f:
            lines = f.readlines()
            for line in lines:
                line = line.rstrip("\n")
                iteration = line

        return [regmem,reg,pc, iteration,next]


    def execute(self,execlist):

        print ' '.join(execlist)
        p = subprocess.Popen(execlist)
        elapsetime = 0
        while (elapsetime < timeout):
            elapsetime += 1
            time.sleep(1)
            #print p.poll()
            if p.poll() is not None:
                print "\t program finish", p.returncode
                print "\t time taken", elapsetime
                return str(p.returncode)
        print "\tParent : Child timed out. Cleaning up ... "
        p.kill()
        return "timed-out"
	    #should never go here


    def generateFaults(self,ori_value):

        pos = random.randint(0,31)
        mask = (1 << pos)
        print "New value is "+str(int(ori_value,16)^mask)+" Old value is "+ori_value
        return str(int(ori_value)^mask)