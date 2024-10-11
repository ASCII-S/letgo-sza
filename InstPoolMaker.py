
import faultinject
import configure
from faultinject import FaultInjector
from concurrent.futures import ProcessPoolExecutor, as_completed
import random
import subprocess
import time
import datetime
import os
import findins
import csv
## 随机查找注错位置,将有效的位置保存在benchmark的指令池中,供sighandler注错时使用

NEED = 10000

totalcount = 0
timeout = 500

randinst_lib = "obj-intel64/randomInst.so"
randinst_config = "-randinst"

iterationinst = "obj-intel64/determineInst.so"
iterationinst_config1 = "-pc"
iterationinst_config2 = "-randinst"

nextinst = "obj-intel64/findnextinst.so"
nextinst_config1 = "-pc"
instructionfile = "instruction"
iterationfile = "iteration"
nextpcfile = "nextpc"   ##由pb_interceptor中的findnextpc生成
stacksize = "spsize"    ##由pb_interceptor中的findnextpc生成

def execute(execlist):

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

def fetchTotalCount():
    instcount = configure.toolbase + "/obj-intel64/instcount_official.so"
    execlist = [configure.pin_home,"-t",instcount,"--",configure.benchmark]
    for item in configure.args:
        execlist.append(item)

    execute(execlist)
    with open(configure.instcount,"r") as f:
        lines = f.readlines()
        if len(lines) > 1:
            print("Error while loading inst count.")
            sys.exit(1)
        count = lines[0]
        count = count.rstrip("\n")
        totalcount = count.split(" ")[1]
        print("Instcount_official:\t",totalcount)
    return totalcount

def getBreakpoint(totalcount):
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
            randomnum = random.randint(0,totalcount)
            execlist = [configure.pin_home,"-t",os.path.join(configure.toolbase,randinst_lib),randinst_config,str(randomnum),"--",configure.benchmark]
            for item in configure.args:
                execlist.append(item)
            execute(execlist)
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
                fi = faultinject.FaultInjector(totalcount)
                future_to_seq = {executor.submit(fi.searchInInstfile, str(seq)): seq for seq in range(1,3)}
                
                for future in as_completed(future_to_seq):
                    seq = future_to_seq[future]
                    try:
                        
                        regmem, reg, pc, tarop_flag, randomnum = future.result()
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
                        break

        if reg == "" and regmem == "":
            #print("No reg, Try again")
            continue
        if pc == "0":
            continue
        if  not (int(configure.pcstart,16) <= int(pc,10) <= int(configure.pcend,16)):
            pc = int(pc)
            print(pc)
            continue

        wish_op = configure.inject_op
        opcode = findins.decpc_to_op(int(pc))
        if  opcode != wish_op:
            print("\nWish opcode:\t",wish_op,"\nReceive opcode:\t",opcode)
            tarop_flag = 0
        else :
            print("\nBingo!\nWish opcode:\t",wish_op,"\nReceive opcode:\t",opcode)
            tarop_flag = 1
        if wish_op == 'all':
            tarop_flag = 1
        
        if reg.startswith("r") or regmem.startswith("r"):
            flag = 64
    
    execlist = [configure.pin_home,"-t",os.path.join(configure.toolbase,iterationinst),iterationinst_config1,str(pc),iterationinst_config2,str(randomnum),"--",configure.benchmark]
    for item in configure.args:
        execlist.append(item)
    execute(execlist)

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


#fi = faultinject.FaultInjector(int(totalcount))
#args = fi.getBreakpoint  # [regmm, reg, pc, iteration]
##参数中包含的是在动态指令randomnum处的指令和寄存器信息.pc是该动态指令的ins值,regmm或reg是ins中随机挑选的寄存器
##iteration表示的是在randomnum范围内,ins值和pc值相同的次数;也就是pc值在randomnum范围内的迭代次数
def saveargs(args):
    # 确保目标文件夹存在
    os.makedirs('./instructionPool', exist_ok=True)
    
    # 指定文件名
    filename = os.path.join(configure.letgo_base_home,"instructionPool",configure.progname+'.csv')
    print(filename)
    # 以追加模式打开文件
    with open(filename, mode='a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(args)


def selectOneIns():
    totalcount = int(fetchTotalCount())
    args = getBreakpoint(totalcount)
    if len(args) != 4:
        print("Wrong return values! Exit!")
        self.log.close()
        process.close() 
        sys.stdout = sys.__stdout__
    saveargs(args)


def readArgsFromPool():
    # 构建文件路径
    filepath = os.path.join(configure.letgo_base_home, "instructionPool", configure.progname+".csv")
    
    # 用于存储最后一行数据
    args = []

    # 检查文件是否存在
    if not os.path.exists(filepath):
        print(f"Pool not found: {filepath}")
        return args

    # 读取所有行
    with open(filepath, mode='r') as file:
        lines = list(csv.reader(file))
        
        # 如果文件非空，保存最后一行并删除
        if lines:
            args = lines.pop()  # 删除并保存最后一行

    # 将修改后的内容重新写回到文件
    with open(filepath, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerows(lines)
    if len(args) == 4:
        print("args from Pool valid!")
    return args


def instPoolMaker():
    need = NEED
    while need>0:
        need -=1
        selectOneIns()

if __name__ == "__main__":
    print("This is a test!")
    instPoolMaker()
    #readArgsFromPool()