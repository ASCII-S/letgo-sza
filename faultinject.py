import sys
import os
import subprocess
import time
import random
import pexpect
import configure
import re


randinst_lib = "obj-intel64/randomInst.so"
randinst_config = "-randinst"

iterationinst = "obj-intel64/determineInst.so"
iterationinst_config1 = "-pc"
iterationinst_config2 = "-randinst"

nextinst = "obj-intel64/findnextinst.so"
nextinst_config1 = "-pc"

binary = ""
timeout = 500

instructionfile = "instruction"
iterationfile = "iteration"
nextpcfile = "nextpc"   ##由pb_interceptor中的findnextpc生成
stacksize = "spsize"    ##由pb_interceptor中的findnextpc生成

class FaultInjector:

    def __init__(self,totalInst):
        self.totalInst = totalInst
        self.flag = 32

    @property
    def getBreakpoint(self):
        ## get
        """

        :rtype: strings
        """
        randomnum = random.randint(0,self.totalInst)
        execlist = [configure.pin_home,"-t",os.path.join(configure.toolbase,randinst_lib),randinst_config,str(randomnum),"--",configure.benchmark]
        for item in configure.args:
            execlist.append(item)
        self.execute(execlist)
        # check if the file is generated
        if not os.path.isfile(instructionfile):
            print("No File generated!")
            sys.exit(1)
        regmem = ""
        reg = ""
        pc = ""
        iteration = ""
        with open(instructionfile,"r") as f:##文件中包含的是在动态指令randomnum处的指令和寄存器信息.ip是该动态指令的ins值,mem或reg是ins中随机挑选的寄存器
            lines = f.readlines()
            for line in lines:
                line = line.rstrip("")
                if "REGNOTVALID" in line:
                    print("REG not valid! Exit")
                    sys.exit(1)
                if "mem:" in line:  
                    regmem = line.split(":")[1].rstrip("\n")
                if "reg:" in line:
                    reg = line.split(":")[1].rstrip("\n")
                if "pc:" in line:
                    pc = line.split(":")[1].rstrip("\n")
                #if "next:" in line:
                #    next = line.split(":")[1]
        if reg == "" and regmem == "":
            print("No reg, Exit")
            return []
        if reg.startswith("r") or regmem.startswith("r"):
            self.flag = 64
        execlist = [configure.pin_home,"-t",os.path.join(configure.toolbase,iterationinst),iterationinst_config1,str(pc),iterationinst_config2,str(randomnum),"--",configure.benchmark]
        for item in configure.args:
            execlist.append(item)
        self.execute(execlist)

        if not os.path.isfile(iterationfile):
            print("No iteration file generated! Exit")
            return []

        with open(iterationfile,"r") as f:
            lines = f.readlines()
            for line in lines:
                line = line.rstrip("\n")
                iteration = line    ##iteration表示的是在randomnum范围内,ins值和pc值相同的次数;也就是pc值在randomnum范围内的迭代次数

        return [regmem,reg,pc, iteration]


    def execute(self,execlist):

        """

        :rtype: object
        """
        print(' '.join(execlist))
        p = subprocess.Popen(execlist)
        elapsetime = 0
        while (elapsetime < timeout):
            elapsetime += 1
            time.sleep(1)
            #print p.poll()
            if p.poll() is not None:
                print("\t program finish", p.returncode)
                print("\t time taken", elapsetime)
                return str(p.returncode)
        print("\tParent : Child timed out. Cleaning up ... ")
        p.kill()
        return "timed-out"
	    #should never go here


    def generateFaults(self,ori_value):
        #print("ori_value:\n",ori_value)
        ## it is complicated because if it is a 0x then non-digital chars are allowed, need a complicated regex.
        if "0x" in ori_value:
            res = re.findall('0[xX]?[A-Fa-f0-9]+',ori_value)
            ori_value = res[0]
        else:
            ori_value = re.sub("\D","",ori_value)
        bitsize = 31
        if self.flag == 64:
            bitsize = 63
        pos = random.randint(0,bitsize)
        mask = (1 << pos)
        decvalue = 0
        if "0x" in ori_value:
            decvalue = int(ori_value,16)
        else:
            decvalue = int(ori_value)
        print("New value is "+str(decvalue^mask)+" Old value is "+str(decvalue))##将原始值以随机长度,按位异或得到新值
        return str(decvalue^mask)
    
    def get_stack_size(self):
        size = ""
        with open(stacksize,"r") as f:  ##stacksize中保存的是ins所在函数的第一个包含sub和rsp的汇编指令,即为局部变量分配空间的指令,由于汇编代码中会集中把局部变量放在开头分配,因此size为该函数为局部变量预留的空间
            lines = f.readlines()
            for line in lines:
                line = line.rstrip("\n")
                if "," in line:
                    items = line.split(",")
                    size = items[len(items)-1]

        return size

    def getNextPC(self,pc):
        execlist = [configure.pin_home,"-t",os.path.join(configure.toolbase,nextinst),nextinst_config1,str(pc),"--",configure.benchmark]
        for item in configure.args:
            execlist.append(item)
        self.execute(execlist)
        if not os.path.isfile(nextpcfile):
            print("No nextpc file is generated! Exit")
            return []
        nextpc = ""
        regw = []
        stack = ""
        flag = 0 # stackw: 1, stackr: 2 , nostack: 3
        displacement = 0
        scale = 0
        index = ""
        base = ""
        with open(nextpcfile,"r") as f:
            lines = f.readlines()
            for line in lines:
                line = line.rstrip("\n")
                if "nextpc:" in line:
                    nextpc = line.split(":")[1]
                if "regw" in line:
                    regw.append(line.split(":")[1])
                if "stackr:" in line:
                    stack = line.split(":")[1]
                    flag = 2
                if "stackw:" in line:
                    stack = line.split(":")[1]
                    flag = 1
                if "nostack" in line:
                    flag = 3
                if "base:" in line:
                    base = line.split(":")[1]
                if "index:" in line:
                    index = line.split(":")[1]
                if "displacement:" in line:
                    displacement = line.split(":")[1]
                if "scale:" in line:
                    scale = line.split(":")[1]
        return [nextpc,regw,stack,flag,base,index,displacement,scale]