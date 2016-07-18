import sys
import os
import subprocess
import time
import random
import pexpect
import configure


randinst_lib = "obj-intel64/randomInst.so"
randinst_config = "-randinst"

iterationinst = "obj-intel64/determineInst.so"
iterationinst_config1 = "-pc"
iterationinst_config2 = "-randinst"

nextinst = "obj-intel64/findnextpc.so"
nextinst_config1 = "-pc"

binary = ""
timeout = 500

instructionfile = "instruction"
iterationfile = "iteration"
nextpcfile = "nextpc"


class FaultInjector:

    def __init__(self,totalInst):
        self.totalInst = totalInst

    def getBreakpoint(self):
        ## get
        """

        :rtype: strings
        """
        randomnum = random.randint(0,self.totalInst)
        execlist = [configure.pin_home,"-t",os.path.join(configure.toolbase,randinst_lib),randinst_config,str(randomnum),"--",configure.benchmark,configure.args]
        self.execute(execlist)
        # check if the file is generated
        if not os.path.isfile(instructionfile):
            print "No File generated!"
            exit()
        regmem = ""
        reg = ""
        pc = ""
        iteration = ""
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
                #if "next:" in line:
                #    next = line.split(":")[1]
        if reg == "" and regmem == "":
            print "No reg, Exit"
            exit()
        execlist = [configure.pin_home,"-t",os.path.join(configure.toolbase,iterationinst),iterationinst_config1,str(pc),iterationinst_config2,randomnum,"--",configure.benchmark,configure.args]
        self.execute(execlist)

        if not os.path.isfile(iterationfile):
            print "No iteration file generated! Exit"
            exit()

        with open(iterationfile,"r") as f:
            lines = f.readlines()
            for line in lines:
                line = line.rstrip("\n")
                iteration = line

        return [regmem,reg,pc, iteration]


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

    def getNextPC(self,pc):
        execlist = [configure.pin_home,"-t",os.path.join(configure.toolbase,instructionfile),nextinst_config1,str(pc),"--",configure.benchmark,configure.args]
        p = self.execute(execlist)
        if not os.path.isfile(nextpcfile):
            print "No nextpc file is generated! Exit"
            exit()
        nextpc = ""
        regw = []
        with open(nextpcfile,"r") as f:
            lines = f.readlines()
            for line in lines:
                line = line.rstrip("\n")
                if "nextpc:" in line:
                    nextpc = line.split(":")[1]
                if "regw" in line:
                    regw.append(line.split(":")[1])
        return [nextpc,regw]