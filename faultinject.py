import sys
import os
import subprocess
import time
import random
import pexpect
import configure
import re
from concurrent.futures import ProcessPoolExecutor, as_completed
import findins

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

    def searchInInstfile(self, seq):
        regmem = ""
        reg = ""
        pc = "0"
        tarop_flag = 0
        ##pc不合法就一直随机找断点
        randomnum = random.randint(0,self.totalInst)
        execlist = [configure.pin_home,"-t",os.path.join(configure.toolbase,randinst_lib),randinst_config,str(randomnum)]
        execlist.append("-FileNameSeq")
        execlist.append(str(seq))
        execlist.append("--")
        execlist.append(configure.benchmark)

        for item in configure.args:
            execlist.append(item)
        ##test
        #time.sleep(random.uniform(0.5, 2))
        #print(execlist)
        ##test

        self.execute(execlist)
        # check if the file is generated
        
        if not os.path.isfile(instructionfile+str(seq)):
            print("No File generated!")
            sys.exit()
        with open(instructionfile+str(seq),"r") as f:##文件中包含的是在动态指令randomnum处的指令和寄存器信息.ip是该动态指令的ins值,mem或reg是ins中随机挑选的寄存器
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
        return regmem,reg,pc,tarop_flag,randomnum

    @property
    def getBreakpoint(self):
        ## get
        """

        :rtype: strings
        """
        
        regmem = ""
        reg = ""
        pc = "0"
        tarop_flag = 0
        randomnum = 0

        para = 1## 用多个进程随机找注错位置
        while(pc == ""or pc == "0" or ( reg == "" and regmem == "") or tarop_flag == 0):
            if para == 0:
                ##pc不合法就一直随机找断点
                randomnum = random.randint(0,self.totalInst)
                execlist = [configure.pin_home,"-t",os.path.join(configure.toolbase,randinst_lib),randinst_config,str(randomnum),"--",configure.benchmark]
                for item in configure.args:
                    execlist.append(item)
                self.execute(execlist)
                # check if the file is generated
                if not os.path.isfile(instructionfile):
                    print("No File generated!")
                    sys.exit(1)
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
            if para ==1:
                #regmem,reg,pc,tarop_flag,randomnum = self.searchInInstfile(1)

                with ProcessPoolExecutor() as executor:
                    future_to_seq = {executor.submit(self.searchInInstfile, seq): seq for seq in range(1,5)}
                    
                    for future in as_completed(future_to_seq):
                        seq = future_to_seq[future]
                        try:
                            # 获取任务的返回值
                            result = future.result()
                            if result is None:
                                continue  # 如果返回值为 None，跳过
                            
                            regmem, reg, pc, tarop_flag, randomnum = result
                            if   (int(configure.pcstart,16) <= int(pc,10) <= int(configure.pcend,16)):
                                print(int(pc))
                                break
                            print([regmem, reg, pc, tarop_flag, randomnum])
                            op = findins.decpc_to_op(int(pc,10))
                            print([op,configure.inject_op])
                            if  op == configure.inject_op:
                                break
                            
                        except Exception as e:
                            print(f"Error executing searchInInstfile({seq}): {e}")

            if reg == "" and regmem == "":
                #print("No reg, Try again")
                continue
            if pc == "0":
                continue
            if  not (int(configure.pcstart,16) <= int(pc,10) <= int(configure.pcend,16)):
                print(int(pc))
                continue

            wish_op = configure.inject_op
            opcode = self.decpc_to_op(pc)
            if  opcode != wish_op:
                print("\nWish opcode:\t",wish_op,"\nReceive opcode:\t",opcode)
                tarop_flag = 0
            else :
                print("\nBingo!\nWish opcode:\t",wish_op,"\nReceive opcode:\t",opcode)
                tarop_flag = 1
            if wish_op == 'all':
                tarop_flag = 1
            
            if reg.startswith("r") or regmem.startswith("r"):
                self.flag = 64
        
        execlist = [configure.pin_home,"-t",os.path.join(configure.toolbase,iterationinst),iterationinst_config1,str(pc),iterationinst_config2,str(randomnum),"--",configure.benchmark]
        for item in configure.args:
            execlist.append(item)
        #self.execute(execlist)

        if not os.path.isfile(iterationfile):
            print("No iteration file generated! Exit")
            return []

        with open(iterationfile,"r") as f:
            lines = f.readlines()
            for line in lines:
                line = line.rstrip("\n")
                iteration = line    ##iteration表示的是在randomnum范围内,ins值和pc值相同的次数;也就是pc值在randomnum范围内的迭代次数
        print([regmem,reg,pc, iteration])
        return [regmem,reg,pc, iteration]

    

    def decpc_to_op(self, decpc):
        """在 ASM 文件中查找包含指定 PC 值的行"""
        asm_file = os.path.join(configure.letgo_base_home,"./asm",configure.benchmark+'.asm')
        hexpc = hex(int(decpc))[2:]
        try:
            with open(asm_file, 'r') as file:
                for line in file:
                    if hexpc in line:  # 查找十六进制 PC 值
                        return line[30:].strip(' ').strip('\t').split(' ')[0]
        except FileNotFoundError:
            print(asm_file,"未找到。")
        except Exception as e:
            print("发生错误: ",e)

        return None  # 如果没有找到，返回 None



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