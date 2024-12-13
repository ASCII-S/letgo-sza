
import faultinject
import configure
from faultinject import FaultInjector
from concurrent.futures import ProcessPoolExecutor, as_completed
import multiprocessing

import sys
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
saveInsTypelib  = configure.toolbase + "/obj-intel64/saveInstcategory.so"
saveInsTypelib_config1 = "-ins_type"
saveInsTypelib_config2 = "-address_count_file"
saveInsTypelib_config3 = "-dynamic_analyze"
saveInsTypelib_config4 = "-inst_type_table_file"
saveInsTypelib_config5 = "-only_memory"

distributionInstCatalib  = configure.toolbase + "/obj-intel64/distributionInstCata.so"
distributionInstCatalib_config1 = "-inst_type_table_file"
distributionInstCatalib_mnemonic_count_file = "-mnemonic_count_file"
distributionInstCatalib_dynamic_analyze = "-dynamic_analyze"
distributionInstCatalib_config4 = "-des_register_count_file"
distributionInstCatalib_config5 = "-src_register_count_file"

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
    #用库函数并行的随机找要注错的断点
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


def delete_files_based_on_csv(csv_file_path, log_path=configure.log_folder):
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

def Random_instPoolMaker():
    totalcount = int(fetchTotalCount())
    need = NEED
    while need>0:
        need -=1
        selectOneIns(totalcount)


def generate_mnemonic_count_file(mnemonic_count_file = configure.mnemonic_count_file):
    execlist = [configure.pin_home,"-t",distributionInstCatalib,\
                distributionInstCatalib_mnemonic_count_file,os.path.join(configure.letgo_base_home,configure.progname,mnemonic_count_file),\
                distributionInstCatalib_dynamic_analyze,"0",\
                "--",configure.benchmark]
    for item in configure.args:
        execlist.append(item)
    #print(''.join(execlist))
    execute(execlist)
    return mnemonic_count_file


def generate_catalog(catalog_csv_file = configure.catalog_csv_file):
    execlist = [configure.pin_home,"-t",saveInsTypelib,saveInsTypelib_config1,configure.select_type,saveInsTypelib_config2,catalog_csv_file,saveInsTypelib_config3,str(configure.dynamic_analyze),saveInsTypelib_config5 ,str(configure.only_memory), "--",configure.benchmark]
    for item in configure.args:
        execlist.append(item)
    print(''.join(execlist))
    execute(execlist)
    return catalog_csv_file

def generate_Pool_from_catalog1(catalog_csv_file=configure.catalog_csv_file, pool_csv_file = configure.pool_csv_file, num_samples=1000):
    # 该算法考虑了catalog中一行的占比进行随机
    """
    从catalog_csv_file中随机选择num_samples行数据，并将每行的前三个参数保存到pool_csv_file。
    选择行的概率基于每行的出现次数。

    :param catalog_csv_file: 输入的csv文件路径
    :param pool_csv_file: 输出的csv文件路径
    :param num_samples: 随机选择的样本数量，默认为1000
    """
    # 读取 catalog_csv_file 的内容并解析为行和出现次数
    lines = []
    weights = []
    
    with open(catalog_csv_file, 'r') as infile:
        reader = csv.reader(infile)
        for row in reader:
            if row:  # 忽略空行
                count = int(row[4])  # 取出出现次数
                lines.append(row[:3])  # 取前三个参数
                weights.append(count)  # 使用次数作为权重
    
    # 计算加权随机选择
    total_count = sum(weights)


    # 打开 pool_csv_file 进行写入
    with open(pool_csv_file, 'w', newline='') as outfile:
        writer = csv.writer(outfile)
        
        for _ in range(num_samples):
            selected_line = random.choices(lines, weights, k=1)[0]  # 根据权重随机选择一行
            args = selected_line[:2]
            # 将第三列的十六进制数转为十进制
            hex_value = selected_line[2]  # 获取第三列（十六进制数字）
            decimal_value = str(int(hex_value, 16))  # 转换为十进制字符串
            args.append(decimal_value)
            # 为选中的行生成随机数字
            args.append(str(random.randint(0, 1024)))
            #args.append(hex_value)
            outfile.write(','.join(args) + '\n')

    print(f"已通过catalog创建{num_samples}条注错位置，保存到 {pool_csv_file}")
    return pool_csv_file


def generate_Pool_from_catalog2(catalog_csv_file=configure.catalog_csv_file, pool_csv_file = configure.pool_csv_file, num_samples=1000):
    # 该算法忽略了catalog中一行的占比,强制进行随机
    """
    从catalog_csv_file中随机选择num_samples行数据，并将每行的前三个参数保存到pool_csv_file。

    :param catalog_csv_file: 输入的csv文件路径
    :param num_samples: 随机选择的样本数量，默认为1000
    """
    # 读取 catalog_csv_file 的内容
    with open(catalog_csv_file, 'r') as infile:
        lines = infile.readlines()


    # 打开 pool_csv_file 进行写入
    with open(pool_csv_file, 'w') as outfile:
        # 随机选择 num_samples 行并处理
        for _ in range(num_samples):
            random_line = random.choice(lines)  # 随机选择一行

            # 提取前三个参数
            columns = random_line.strip().split(',')  # 假设每行的数据由逗号分隔
            selected_params = columns[:2]  # 获取前三个参数
            selected_params.append(str(int(columns[2],16)))

            random_number = str(random.randint(0, 64))
            selected_params.append(random_number)
            # 将结果写入文件
            outfile.write(','.join(selected_params) + '\n')

    print(f"已通过catalog创建{num_samples} 条注错位置，保存到 {pool_csv_file}")
    return pool_csv_file

def generate_Pool_from_catalog(catalog_csv_file=configure.catalog_csv_file, pool_csv_file = configure.pool_csv_file, num_samples=2000):
    ##该方法为每行创建20个注错机会,行的选择方式是选择前50条
    """
    从catalog_csv_file中随机选择50行（如果行数大于50），并将每行的前三个参数和一个附加的参数（1到20）写入到pool_csv_file中。
    如果catalog_csv_file的行数小于50，则处理所有行。

    :param catalog_csv_file: 输入的csv文件路径
    :param num_samples: 随机选择的样本数量，默认为1000
    """
    # 读取 catalog_csv_file 的所有行
    with open(catalog_csv_file, 'r') as infile:
        lines = infile.readlines()

    # # 如果行数大于50，随机选择50行；如果小于50，则使用所有行
    # if len(lines) > 50:
    #     lines = random.sample(lines, 50)

    # 如果行数大于 100，使用前 100 行；否则使用所有行
    if len(lines) > 80:
        lines = lines[:80]

    nums_one_inst = min(int(num_samples/len(lines)),50)
    # 打开 pool_csv_file 进行写入
    with open(pool_csv_file, 'w') as outfile:
        # 遍历每一行
        for line in lines:
            # 提取前三个参数
            columns = line.strip().split(',')  # 假设每行的数据由逗号分隔
            selected_params = columns[:2]  # 获取前两个参数
            selected_params.append(str(int(columns[2], 16)))  # 将第三个参数转换为十进制
            max_iteration = int(columns[-1])-1
            # 为每一行创建20个副本，每个副本附加一个新的参数（从1到20）
            for i in range(0, nums_one_inst):
                iteration = str(min(max_iteration,i))
                new_line = selected_params + [iteration]  # 添加从1到20的数值
                outfile.write(','.join(new_line) + '\n')

    print(f"已通过catalog创建{len(lines) * 20} 条注错位置，保存到 {pool_csv_file}")
    return pool_csv_file

def readArgsFromPool(filepath = os.path.join(configure.instpool_folder, poolname)):
    
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



if __name__ == "__main__":
    print("PoolMaker!")
    #Random_instPoolMaker()
    path = generate_catalog()
    path = generate_Pool_from_catalog(path)
    print(readArgsFromPool(path))
    #csv_file = os.path.join(configure.csv_folder,configure.progname+'.csv')
    #extract_args_based_on_csv(csv_file)
    #delete_files_based_on_csv(csv_file)