
import faultinject
import configure
from faultinject import FaultInjector
from concurrent.futures import ProcessPoolExecutor, as_completed
import multiprocessing

import random
import subprocess
import time
import datetime
import os
import findins
import csv
import pandas as pd


## NEVER RUN THIS　FILE UNDER LETGO_BASE_HOME !!! THIS WILL CAUSE INVALID SDC DATA!
## CD IN INSTPOOL THEN RUN INSTPOOLMAKER.PY
## 随机查找注错位置,将有效的位置保存在benchmark的指令池中,供sighandler注错时使用
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

NEED = 100 + configure.numFI * 2
instpool_folder = configure.instpool_folder
poolname = configure.progname+'_inspool.csv'

instructionstart = 1
instructionend = 4

totalcount = 0
timeout = 500
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
    findpc = 0
    para = 1## 用多个进程随机找注错位置
    while(pc == ""or pc == "0" or ( reg == "" and regmem == "") or (reg == '*invalid*' or regmem == '*invalid*') or tarop_flag == 0 ):
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
            stop_event = multiprocessing.Event()
            fi = faultinject.FaultInjector(totalcount)
            with ProcessPoolExecutor() as executor:
                future_to_seq = {executor.submit(fi.searchInInstfile, str(seq)): seq for seq in range(instructionstart,instructionend+1)}
                
                for future in as_completed(future_to_seq):
                    seq = future_to_seq[future]
                    if stop_event.is_set():
                        break
                    try:
                        regmem, reg, pc, tarop_flag, randomnum = future.result()
                        if reg == '*invalid*' or regmem == '*invalid*':
                            continue
                        if ((int(configure.pcstart,16) <= int(pc,10)) and (int(pc,10) <= int(configure.pcend,16))):
                            print(f"Found valid PC: {int(pc)}")
                            stop_event.set()  # 通知其他线程停止
                            findpc = 1
                            break
                        """op = findins.decpc_to_op(int(pc,10))
                        print([op,configure.inject_op])
                        if  op == configure.inject_op:
                            break"""
                        
                    except Exception as e:
                        print(f"Error executing searchInInstfile({seq}): {e}")
                        stop_event.set()  # 如果发生错误，停止所有线程
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

        if reg.startswith("r") or regmem.startswith("r"):
            flag = 64
        if findpc == 1:
            break
        """wish_op = configure.inject_op
        if wish_op == 'all':
            tarop_flag = 1
            continue
        opcode = findins.decpc_to_op(int(pc))
        if  opcode != wish_op:
            print("\nWish opcode:\t",wish_op,"\nReceive opcode:\t",opcode)
            tarop_flag = 0
        else :
            print("\nBingo!\nWish opcode:\t",wish_op,"\nReceive opcode:\t",opcode)
            tarop_flag = 1"""
        
    
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
    print("find valid args:\t",[regmem,reg,pc, iteration,randomnum])
    return [regmem,reg,pc, iteration,randomnum]

def extract_args_based_on_csv(csv_file):
    # 读取 CSV 文件
    df = pd.read_csv(csv_file)

    # 用于存储独特的结果
    unique_results = set()

    # 遍历 DataFrame，判断条件并保存
    for _, row in df.iterrows():
        #if row['result'] in [configure.C_MASKED, configure.C_SDC, configure.DOUBLE_CRASH]:
        if row['regmm'] == 'rip':
            # 判断 dynamicInstNum 是否为 null
            if pd.notnull(row['dynamicInstNum']):
                # 提取所需的列
                args = (
                    row['regmm'] if pd.notnull(row['regmm']) else '',  # 使用空值代替 nan
                    row['reg'] if pd.notnull(row['reg']) else '',      # 使用空值代替 nan
                    row['pc'],
                    row['iteration1'],
                    int(row['dynamicInstNum'])  # 保存为整数
                )
                
                # 使用元组确保结果唯一
                unique_results.add(args)

    # 保存独特的结果
    for result in unique_results:
        saveargs(result)


def delete_files_based_on_csv(csv_file_path, log_path=configure.log_path):
    # 读取 CSV 文件
    df = pd.read_csv(csv_file_path)

    # 提取 input_file 列，前提是 regmm 列为 'rip'
    files_to_delete = df[df['regmm'] == 'rip']['input_file'].tolist()

    # 遍历要删除的文件，检查并删除
    for file_name in files_to_delete:
        file_path = os.path.join(log_path, file_name)
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"Deleted file: {file_path}")
        else:
            print(f"File not found: {file_path}")


#fi = faultinject.FaultInjector(int(totalcount))
#args = fi.getBreakpoint  # [regmm, reg, pc, iteration]
##参数中包含的是在动态指令randomnum处的指令和寄存器信息.pc是该动态指令的ins值,regmm或reg是ins中随机挑选的寄存器
##iteration表示的是在randomnum范围内,ins值和pc值相同的次数;也就是pc值在randomnum范围内的迭代次数
def saveargs(args):
    # 确保目标文件夹存在
    os.makedirs(instpool_folder, exist_ok=True)
    
    # 指定文件名
    filename = os.path.join(instpool_folder,poolname)
    # 以追加模式打开文件
    with open(filename, mode='a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(args)
    print("args add to:\t",filename)


def selectOneIns(totalcount):
    result = getBreakpoint(totalcount)
    if len(result) < 5:
        return
    args = result[:-1]
    randomnum = result[-1]
    print("sleectOneIns:\t",args,randomnum)

    saveargs(result)


def readArgsFromPool():
    # 构建文件路径
    filepath = os.path.join(configure.instpool_folder, poolname)
    
    # 用于存储最后一行数据
    args = []

    # 检查文件是否存在
    if not os.path.exists(filepath):
        print(f"Pool not found: {filepath}")
        print("do it by self")
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
    if len(args) == 5:
        print("args from Pool valid!")
    return args


def Random_instPoolMaker():
    totalcount = int(fetchTotalCount())
    need = NEED
    while need>0:
        need -=1
        selectOneIns(totalcount)

if __name__ == "__main__":
    print("PoolMaker!")
    Random_instPoolMaker()

    #csv_file = os.path.join(configure.csv_folder,configure.progname+'.csv')
    #extract_args_based_on_csv(csv_file)
    #delete_files_based_on_csv(csv_file)