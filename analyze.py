import sys
import os
import re
import configure
import shutil
import pandas as pd
import csv
import findins
import argparse
import matplotlib.pyplot as plt
from pandas.plotting import table
import numpy as np
import sighandler
import seaborn as sns
from sdcjudger import Add_SDC_result_to_alllog_common
from gen_asm import disassemble_binary
#######---------------FOLLOWED ARE SWITCH---------------#########
## clsfy == 1 to move unfinished record to folder "unfinish"
clsfy = 1
## delbug = 1 to delete file that encounters Traceback
delbug = 0
## to_csv =1 will collect all information to csv under log_path,but cost much more time
to_csv = 1
## findins = 1 will auto find Sig1ins and Sig2ins according to Sig*pc and asm  
findmorebypc = 1
## the more debug_mode increase ,the more info been printed
debug_mode = 5
## show file example find by string like "No reg, Exit"
show_ss_example = 0



##定义parser
parser = argparse.ArgumentParser(description="Analyze log files.")
parser.add_argument('-file', type=str, help='Log file to process,benchmark according to configure.py')
parser.add_argument('-flag', type=str, help='flag means the number of Sig received')
parser.add_argument('-sdc_flag', type=str, help='sdc_flag means the number of SDC')

parser.add_argument('-bname', type=str, help='bname means benchmark name')
parser.add_argument('-i', type=str, help='specify param: inject_random_or_targeted(random,targeted)')
parser.add_argument('-s', type=str, help='specify param: select_type(call_retq,stack,mov,integer,float,cmp)')
parser.add_argument('-analyze_all', type=str, help='analyze all application one time')
parser.add_argument('-p', type=str, help="picture type")
parser.add_argument('-t', type=str, help="Table type")
args = parser.parse_args()
argslen =  sum(1 for arg in vars(args).values() if arg is not None)

progname = configure.progname if not args.bname else args.bname
inject_random_or_targeted = configure.inject_random_or_targeted if not args.i else args.i
select_type = configure.select_type if not args.s else args.s
analysis_folder = configure.analysis_folder 

file_count = 0

#不指定参数,默认从configure中获得参数
one_batch_folder = configure.one_batch_folder 
analysis_folder_name = configure.analysis_folder_name
result_analyze_csv_name = configure.result_analyze_csv_name

#手动输入参数,根据输入参数以configure的规则构建需要的参数
if argslen:    
    if inject_random_or_targeted == "random":
        Result_folder_name = "BenchmarkResult"
        analysis_folder_name = "analysis"
        result_analyze_csv_name = progname +'.csv'
        one_batch_folder = os.path.join(configure.letgo_base_home,Result_folder_name,progname)
    if inject_random_or_targeted == "targeted":
        Result_folder_name = "TargetedBenchmarkResult"
        analysis_folder_name = "TargetedAnalysis"
        result_analyze_csv_name = progname + '_' + select_type +'.csv'
        one_batch_folder = os.path.join(configure.letgo_base_home,Result_folder_name,progname,select_type)

analysis_folder = os.path.join(configure.letgo_base_home,analysis_folder_name)
analysis_csv_folder = os.path.join(analysis_folder,'CSV',progname) if inject_random_or_targeted=="targeted" else  os.path.join(analysis_folder,'CSV')
analysis_csv_file = os.path.join(analysis_csv_folder,result_analyze_csv_name)
asm_folder  = os.path.join(analysis_folder,'asm')
pic_folder  = os.path.join(analysis_folder,'PIC',progname) if inject_random_or_targeted=="targeted" else  os.path.join(analysis_folder,'PIC')

log_folder = os.path.join(one_batch_folder,"log")  ##数据源目录

print("log_folder in:\t",log_folder)
if not (os.path.exists(log_folder) and os.path.isdir(log_folder)):
    print("{} does not exist or is not a directory".format(log_folder))
    exit(0)


finish = []
crash_1 = []
crash_2 = []
crash_2p = []
unfinishedlist = []
#ignore masked and sdc
#ignore_no_crash = 1 if inject_random_or_targeted == "random" else 1
ignore_no_crash = 0

# 直接从 configure 中导入所需的变量
SdcAppList = configure.SdcAppList
MASKED = configure.MASKED
SDC = configure.SDC
SDC_UNACCEPTED = configure.SDC_UNACCEPTED
SDC_ACCEPTED = configure.SDC_ACCEPTED
C_MASKED = configure.C_MASKED
C_SDC = configure.C_SDC
C_SDC_UNACCEPTED = configure.C_SDC_UNACCEPTED
C_SDC_ACCEPTED = configure.C_SDC_ACCEPTED
DOUBLE_CRASH = configure.DOUBLE_CRASH
CRASH_NOPC = configure.CRASH_NOPC
# CAM = 'CntAccMem'
# ANIA = 'AdrsNotInAsm'
CAM = CRASH_NOPC
ANIA = CRASH_NOPC

max_error_spread = sighandler.MAX_ERROR_SPREAD

def find_and_print_sig_time(file_path):
    # 打开文件，逐行读取内容
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
        for line in file:
            # 检查是否有 "sig time:"
            if "sig time:" in line:
                # 输出包含 "sig time:" 的行
                print(line.strip())  

def is_valid_hex_address(s):
    return bool(re.fullmatch(r'^[0-9a-fA-F]{6}$', s))

def next_i_line_content(file, i, target):
    lines = []  # 存储读取的行
    for _ in range(i):
        try:
            next_line = next(file).strip()  # 获取下一行
            lines.append(next_line)  # 将行添加到列表
            if target in next_line:
                return next_line  # 如果找到目标，立即返回该行
        except StopIteration:
            # 如果到达文件末尾，退出循环
            break

    # 如果没有找到目标，返回所有行的连接
    return '\n'.join(lines) if lines else 'null'  # 如果没有读取到任何行，返回'null'

def move_file_to_dir(f, log_folder, folder_name):
    # 创建目标文件夹路径
    target_dir = os.path.join(log_folder, folder_name)

    # 检查目标文件夹是否存在，如果不存在则创建
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)

    # 构造目标路径
    destination = os.path.join(target_dir, os.path.basename(f))

    # 移动文件到目标文件夹
    try: 
        shutil.move(f, destination)
    except:
        print("File {} cannot been moved to {}".format(f, target_dir))

    

def search_string_in_log():
    ##下面统计文本

    # 定义要查找的字符串
    search_strings = [
        "set reg with address calculation",
        "set reg with fake",
        "set rbp and rsp to reasonable values",
        "Cannot insert breakpoint",
        "No reg, Exit",
        "Error",
        "received signal SIGSEGV, Segmentation fault.",
        "received signal SIGBUS, Bus error.",
        "received signal SIGABRT, Aborted.",
        "Program received signal SIGILL",
        "Valid FaultInject2Sig:",
        "Valid Fix2Sig:",
        "After Inject:",
        "After Fixed"
    ]

    # 定义文件夹路径
    folder_path = log_folder # 修改为你实际的文件夹路径

    # 用于存储结果的字典
    results = {key: [] for key in search_strings}

    # 遍历文件夹中的所有文件
    for filename in os.listdir(folder_path):
        # 构建完整文件路径
        file_path = os.path.join(folder_path, filename)

        # 只处理文本文件
        if os.path.isfile(file_path):
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
                content = file.read()
                for search_string in search_strings:
                    if search_string in content:
                        results[search_string].append(filename)

     # 统计每个字符串匹配的文件数
    counted_results = {key: len(set(val)) for key, val in results.items()}

    # 按照字典序排序 counted_results
    sorted_counted_results = sorted(counted_results.items())

    # 输出前几项结果（已按字典序排序）
    top_n = len(search_strings) + 1  # 设置你想要输出的前几项
    for i, (string, count) in enumerate(sorted_counted_results, 1):
        if i > top_n:
            break
        print("{}. '{}' found in {} files".format(i, string, count))


    # 如果你还需要显示具体的文件名，可以按以下方式输出
    if show_ss_example == 1:
        for string, filenames in results.items():
            print("\nFiles containing '{}':".format(string))
            top_n = 1
            for filename in set(filenames):
                if top_n <=0 :
                    break
                print("- {}".format(filename))
                file_path = os.path.join(folder_path, filename)
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
                    for line in file:
                        # 检查是否有 "sig time:"
                        if "sig time:" in line:
                            # 输出包含 "sig time:" 的行
                            print(line.strip())
                top_n -=1


def read_logs(progname, log_folder, output_dir, outputname):
    global file_count, crash_1, crash_2, crash_2p, finish, flag, detected, correct, sdc, unfinishedlist, output
    
        
    print("read log in folder:\t",log_folder)
    if to_csv == 1:
        csv_file_path = analysis_csv_file
        # 检查文件是否存在，如果存在则删除
        if os.path.exists(csv_file_path):
            os.remove(csv_file_path)
            print("Deleted old csv:\t", csv_file_path)
        else:
            print("Csv not exist:\t",csv_file_path)

    # 只选择以 "log_" 开头的文件并按名称排序
    log_files = sorted(
        [f for f in os.listdir(log_folder) if f.startswith("log_") and int(re.search(r'(\d+)', f).group()) < 99999],
        key=lambda x: int(re.search(r'(\d+)', x).group())
    )

    
    for f in log_files:
        # file_name = os.path.basename(f)
        # if file_name != "log_995":
        #     continue

        # print(file_name)

        file_count += 1
        f = os.path.join(log_folder, f)
        flag = 0
        sdc_flag = -1
        after_letgoin = 0
        with open(f, "r", encoding='utf-8', errors='ignore') as log:
            unfinished = 0
            lines = log.readlines()
            # 判断 lines 是否为空
            if not lines:
                print(f"文件 '{f}' 是空的，跳过此文件。")
                continue  # 跳过此文件
                
            bugin = 0
            for line in lines:
                if "Traceback" in line or "no such Breakpoint" in line or "SystemExit" in line or "exit_flag: True" in line:
                    print("Bug in:\t", f)
                    bugin = 1
                    if delbug == 1:
                        os.remove(f)  # 删除文件
                        print("delete:\t", f)
                        break
                    break
                if "Program received signal" in line and not after_letgoin and flag == 0:
                    flag = 1
                if "Letgo in!" in line :
                    after_letgoin = 1
                if "Program received signal" in line and after_letgoin and flag == 1:
                    flag = 2
                if "application generate no output" in line or "Timeout occurred" in line:
                    flag = 2
                if "No nextpc file is generated!" in line or "Crash place getting no PC" in line:
                    sdc_flag = 0
                    flag = 2

                ##Sdc Test
                if "1 tests completed and " in line:  # hpl
                    sdc_flag = 0
                    if "failed residual checks" in line:
                        sdc_flag = 1
                if "L*U equals M within tolerance( " + str(configure.lu_tolerance) + ' )' in line:
                    sdc_flag = 0
                    if 'False' in line:
                        sdc_flag = 1
                if configure.cmp_str in line:
                    sdc_flag = 0
                    if 'False' in line:
                        sdc_flag = 1
                if "Verification " in line and progname in ["bt", "cg", "ep", "ft", "is"]:
                    if "Successful" in line:
                        sdc_flag = 0
                    if "failed" in line:
                        sdc_flag = 1



                if "Exit" in line:
                    unfinished = 1
                if "Error" in line or "ERROR" in line: 
                    unfinished = 1
                if "Cannot insert breakpoint" in line:
                    unfinished = 1

            if unfinished == 1:
                unfinishedlist.append(f)
                if clsfy == 1:
                    move_file_to_dir(f, log_folder, "unfinish")
                #continue
            if bugin == 1:
                continue

            if flag == 1:
                crash_1.append(f)
            if flag == 2:
                crash_2.append(f)
            if flag > 2:
                crash_2p.append(f)
            if flag == 0:
                finish.append(f)
        if ignore_no_crash == 1 and flag == 0:
            continue
        if unfinished == 1:
            continue
        if to_csv == 1:
            # 创建 CSV 文件保存的目录
            extract_values_and_append_to_csv(log_folder, f,  output_dir, outputname, flag, sdc_flag)

def get_ins_info(Sig='Sig1', Sigpc='Sig1pc', SigIns='Sig1Ins', SigOpe='Sig1Ope', SigFunc='Sig1Func', address=None, asm_file=None, df=None, file=None, insline_context = None):
    """
    从 GDB 输出中提取指令信息并更新 DataFrame。
    """
    if df is None or file is None:
        print("Error: DataFrame or line is missing.")
        return
    
    try:
        # 提取指令行
        line = insline_context
        insline = "=> "+line.split("=>")[-1].strip("(gdb)").strip()
        # 更新 Sigpc
        df.loc[0, Sigpc] = insline.split('=>')[-1].split(':')[0].split('<')[0].strip()
        if address == 'null' or len(address) != 6 :
            address = df.loc[0, Sigpc]
        # 处理 'Cannot' 错误情况
        if Sig=='Sig1':
            if 'Cannot' in insline :
                df.loc[0, SigIns] = 'null'
                df.loc[0,'result'] = CAM
                return
            if asm_file is not None and (not findins.judge_address_in_asm(address.replace('0x', ''), asm_file)) :
                # 如果地址不在汇编文件中
                #print("crash:",df.loc[0,'input_file'],'\t',address)
                df.loc[0, SigIns] = 'null'
                df.loc[0,'result'] = ANIA
                return
            
        # 提取函数名
        if len(insline.split('<')) > 1:
            df.loc[0, SigFunc] = insline.split('<')[1].split('>')[0].split('+')[0]
        else:
            df.loc[0, SigFunc] = 'null'

        # 提取指令
        if len(insline.split(':')) > 1:
            df.loc[0, SigIns] = insline.split(':')[1].strip()
            if insline.split(':')[1].strip()=='':
                nextline = next(file,None).strip()
                df.loc[0, SigIns] = nextline
        else:
            df.loc[0, SigIns] = insline.split(':')[-1].replace('"', '').strip()
        # 提取操作
        if 'rex' in df.loc[0, SigIns]:
            if len(df.loc[0, SigIns].split(' ')) > 1:
                df.loc[0, SigOpe] = df.loc[0, SigIns].split(' ')[1]
            else:
                df.loc[0, SigOpe] = df.loc[0, SigIns]
        else:
            df.loc[0, SigOpe] = df.loc[0, SigIns].split(' ')[0]
        
        # if df.loc[0,'result'] == 'crash':
        #     print(df.loc[0,'input_file'])
        #     print("Line:", line)
        #     print("insLine:", insline)
    except Exception as e:
        print(f"Error processing signal information for {Sig}: {e}")
        print(df.loc[0, 'input_file'],"\tLine:", line)


def extract_values_and_append_to_csv(log_folder, input_file, output_dir, outputname, flag, sdc_flag):

    # 创建一个空的 DataFrame
    df = pd.DataFrame(columns=['input_file','dynamicInstNum' ,'regmm','reg', 'injreg', 'inj_location', 'pc', 'iteration1','hexpc', 'ins', 'opcode', 'Func','result', 'Heuristic' ,'tolerance' ,'bias', 'Sig1','Sig1pc','Sig1Ins','Sig1Ope','Sig1Func','ErrSpd_Inj', 'Sig2','Sig2pc','Sig2Ins','Sig2Ope','Sig2Func','ErrSpd_Fix' ])
    

    if flag == 0:
        df.loc[0,'result'] = MASKED
        if sdc_flag == 1:
            df.loc[0,'result'] = SDC
    elif flag == 1:
        if sdc_flag == 0:
            df.loc[0,'result'] = C_MASKED
        if sdc_flag == 1:
            df.loc[0,'result'] = C_SDC
        if sdc_flag == -1:
            df.loc[0,'result'] = 'C-unknown'
    elif flag == 2:
        df.loc[0,'result'] = DOUBLE_CRASH
    else:
        df.loc[0,'result'] = 'crash2+'
        
    # 获取文件名
    file_name = os.path.basename(input_file)
    asm_file = os.path.join(asm_folder,progname+'.asm')
    df.loc[0,'input_file'] = file_name

    debug = 0
    if debug == 1:
        if df.loc[0,"input_file"] != "log_610":
            return
        print(df.loc[0,'result'])
    
    # 读取文件并提取所需内容
    with open(input_file, 'r') as file:
        values = ['null'] * 4
        SIGcount = 0
        Sig1byletgo_Flag = 0
        after_letgoin = 0

        for line in file:
            if "-randinst" in line:##最后一个随机数才是真实使用的随机数
                # 使用正则表达式查找 '-randinst ' 后面的数字
                match = re.search(r'-randinst (\d+)', line)
                # 检查是否找到匹配的结果
                if match:
                    df.loc[0,'dynamicInstNum']  = match.group(1)
                else:
                    print("Number not found")
                continue
            if "args ready" in line:
                args = line
                if debug_mode >= 9:
                    print("args:\t",args)
                # 提取单引号中的内容
                # 先去掉多余的部分，例如 "args:    "
                cleaned_args = args.split("[")[1].split("]")[0]  # 得到 "'rsi', '', '4202512', '641371'"
                values = cleaned_args.split("', '")              # 以 ', ' 作为分隔符

                # 去掉首尾的单引号
                values[0] = values[0].replace("'", "")           # 'rsi' -> rsi
                values[-1] = values[-1].replace("'", "")         # '641371' -> 641371
                values = [v if v else 'null' for v in values]
                if debug_mode >= 6 :
                    print("values:\t",values)
                try:
                    df.loc[0,'regmm'] = values[0]
                    df.loc[0,'reg'] = values[1]
                    df.loc[0,'pc'] = str(values[2])
                    df.loc[0,'hexpc'] = hex(int(df.loc[0,'pc']))
                    df.loc[0,'iteration1'] = values[3]
                except:
                    if debug_mode > 4 :
                        print(file_name,"\twith not complete args:\t",values)
                    break
                if values[0] != 'null' :
                    df.loc[0,'injreg'] = values[0]
                elif values[1] != 'null' :
                    df.loc[0,'injreg'] = values[1]
                else:
                    df.loc[0,'injreg'] = 'null'
                if df.loc[0,'pc'] == 'null':
                    #os.remove(input_file)
                    print(f"文件 '{input_file}' 需要删除。")
                continue
            if "fi inject instance:" in line:
                df.loc[0,'dynamicInstNum'] = line.split(':')[-1].strip()
            if "Activated:" in line:
                df.loc[0,'hexpc'] = line.split(' ')[-1].strip()
                df.loc[0,'injreg'] = line.split('in')[0].strip().split(' ')[-1].strip()
            if "display the inject inst start" in line:
                next_3_line = next_i_line_content(file,3,"=>")
                try:
                    df.loc[0,'Func'] = next_3_line.split(':')[0].split('<')[1].split('>')[0].split('+')[0]
                    df.loc[0,'ins'] = next_3_line.split(':')[1].strip()
                    df.loc[0,'opcode'] = df.loc[0,'ins'].split(' ')[0]
                except:
                    print(input_file,"extract ins failed")
                continue

            if "bit location:" in line:
                try:
                    df.loc[0,'inj_location'] = line.split(":")[1]
                except:
                    df.loc[0,'inj_location'] = "null"

            #首次遇到SIG
            if "Program received signal" in line and SIGcount == 0 and after_letgoin==0:
                Sig = 'Sig1'
                Sigpc = 'Sig1pc'
                SigIns = 'Sig1Ins'
                SigOpe = 'Sig1Ope'
                SigFunc = 'Sig1Func'

                try:
                    tmp = line.split(',')[0]
                    tmp = tmp.split('signal')[1]
                    df.loc[0,Sig] = tmp.strip()
                    insline = next_i_line_content(file,1,'0x')
                    address = 'null'
                    if '0x' in insline and 'in' in insline:
                        df.loc[0,Sigpc] = '0x' + insline.split(' ')[0].lstrip('0x').lstrip('0')
                        address = df.loc[0,Sigpc].lstrip("0x")
                        df.loc[0,SigFunc] = insline.strip().split(' ')[2].strip().split(' ')[0].strip()
                    insline = next_i_line_content(file,4,'=>')
                    if "=>" in insline:
                        #print(df.loc[0,"result"])
                        get_ins_info(Sig, Sigpc, SigIns, SigOpe, SigFunc, address, asm_file, df, file, insline)
                        #print(df.loc[0,"result"])
                        #sys.exit(1)
                except Exception as e:
                    print("get info at signal1 fail",input_file)
                    print(e)
                SIGcount = 1
                continue
                
            if "=>" in line and SIGcount == 1 and after_letgoin==0 and not df.loc[0,'Sig1pc']:
                Sig = 'Sig1'
                Sigpc = 'Sig1pc'
                SigIns = 'Sig1Ins'
                SigOpe = 'Sig1Ope'
                SigFunc = 'Sig1Func'
                address = 'null'
                insline = line
                
                get_ins_info(Sig, Sigpc, SigIns, SigOpe, SigFunc, address, asm_file, df, file)

                continue

            
            if 'Letgo in!' in line:
                after_letgoin = 1
                continue
            if Sig1byletgo_Flag == 1 and 'Letgo in!' in line:
                tmp = next_i_line_content(file,3,"=")
                tmp = tmp.split('0x')[-1][:6]
                try:
                    if is_valid_hex_address(tmp):
                        df.loc[0,'Sig1pc'] = '0x' + tmp.strip()
                        SIGcount = 1
                        if debug_mode > 5:
                            print("Find Sig1pc by Letgo in!\t",input_file)
                except:
                    if debug_mode > 4:
                        print("Sig1pc fetched by letgoin:\t",tmp)
                        print("Letgo in! next3line with no valid Sig1pc \t",input_file)
                    continue

            if "parse the pc value" in line and pd.isna(df.loc[0,'Sig1pc']) :
                try:
                    print_pc = next_i_line_content(file,2,"=")
                    df.loc[0,'Sig1pc'] = '0x' + print_pc.split('0x')[1].split(' ')[0]
                except:
                    print("no sig1pc in:\t",df.loc[0,'input_file'])

            if "multiple options" in line:
                df.loc[0,'Heuristic'] = "h_0"
                continue
            if "is stackr: have set reg with address calculation" in line or "h_1" in line:
                df.loc[0,'Heuristic'] = "h_1"
                continue
            if "not stackr,so set fake:" in line or "h_2" in line:
                df.loc[0,'Heuristic'] = "h_2"
                continue
            if "Set the" in line or "h_3" in line:
                df.loc[0,'Heuristic'] = "h_3"
                continue

            if "Inj2Sig" in line.strip():
                #print(line)
                df.loc[0,'ErrSpd_Inj'] = int(line.split(':')[-1])
                continue
            if ("After Inject:" in line):
                df.loc[0,'ErrSpd_Inj'] = str(max_error_spread)+'+'
                continue

            #再次遇到SIG
            if "Program received signal" in line and SIGcount == 1 and after_letgoin==1:#and df.loc[0,'result'] == DOUBLE_CRASH:  
                Sig = 'Sig2'
                Sigpc = 'Sig2pc'
                SigIns = 'Sig2Ins'
                SigOpe = 'Sig2Ope'
                SigFunc = 'Sig2Func'
                try:
                    tmp = line.split(',')[0]
                    tmp = tmp.split('signal')[1]
                    df.loc[0,Sig] = tmp.strip()
                    insline = next_i_line_content(file,1,'0x')
                    address = 'null'
                    asm_file = os.path.join(asm_folder,progname+'.asm')
                    if '0x' in insline and 'in' in insline:
                        df.loc[0,Sigpc] = '0x' + insline.split(' ')[0].lstrip('0x').lstrip('0')
                        address = df.loc[0,Sigpc].lstrip("0x")
                        df.loc[0,SigFunc] = insline.strip().split(' ')[2].strip().split(' ')[0].strip()
                        
                except Exception as e:
                    print("get info at signal2 fail",input_file)
                    print(e)
                SIGcount = 2
                continue

            if "=>" in line and SIGcount == 2 and after_letgoin==1 and not df.loc[0,'Sig2pc']:
                insline = line.split("=>")[-1].strip("(gdb)").strip()
                Sig = 'Sig2'
                Sigpc = 'Sig2pc'
                SigIns = 'Sig2Ins'
                SigOpe = 'Sig2Ope'
                SigFunc = 'Sig2Func'

                get_ins_info(Sig, Sigpc, SigIns, SigOpe, SigFunc, address, asm_file, df, file)

                continue


            if ("Valid Fix2Sig" in line ):
                df.loc[0,'ErrSpd_Fix'] = int(line.split(':')[-1])
            if ("After Fixed" in line) :
                df.loc[0,'ErrSpd_Fix'] = str(max_error_spread)+'+'

            ###保存tolerance,需要保留四位小数
            df.loc[0,'tolerance'] = '{:.4f}'.format(configure.tolerance)
            ###保存bias,需要保留四位小数
            special_bias_app_list = ["HPCCG","hpl","miniFE","miniMD"]
            #hpl
            if "||Ax-b||_oo/(eps*(||A||_oo*||x||_oo+||b||_oo)*N)=" in line:
                bias_value = float(line.split('=')[1].split("......")[0].strip())
                df.loc[0,'bias'] = '{:.4e}'.format(bias_value)
            #HPCCG
            if "Final residual:" in line:
                bias_value = float(line.split(':')[1].strip())
                df.loc[0,'bias'] = '{:.4e}'.format(bias_value)
            #miniFE
            if "Final Resid Norm" in line:
                bias_value = float(line.split(':')[1].strip())
                df.loc[0,'bias'] = '{:.4e}'.format(bias_value)
            #polybench
            if "max relative error" in line:
                bias_value = float(line.split(':')[1].strip())
                df.loc[0,'bias'] = '{:.4e}'.format(bias_value)
            
    

    #判断完一条log后的总结
    if not pd.isna(df.loc[0,'Sig1pc']) and asm_file is not None and not findins.judge_address_in_asm(str(df.loc[0,'Sig1pc']).replace('0x', ''), asm_file) :
        # 如果地址不在汇编文件中
        #print("crash:",df.loc[0,'input_file'],'\t',df.loc[0,'Sig1pc'])
        df.loc[0, 'Sig1Ins'] = 'null'
        df.loc[0,'result'] = ANIA
    #没有崩溃的情况，将bias设置为无穷大
    if df.loc[0,'result'] == DOUBLE_CRASH or df.loc[0,'result'] == CRASH_NOPC:
        df.loc[0,'bias'] = 'inf'
    if progname in configure.sdcprogram:
        #默认最严格的sdc判定，如果误差小，就将sdc进化成masked
        def update_sdc_result(bias, sdc_tolerance, masked_tolerance, df):
            """
            根据bias和容差更新SDC结果分类
            
            Args:
                bias: 偏差值
                sdc_tolerance: SDC容差阈值
                masked_tolerance: masked容差阈值
                df: 待更新的DataFrame
            """
            if abs(bias) > sdc_tolerance:
                # 超出sdc容差，直接判定为SDC_UNACCEPTED
                # 无需修复的样例
                if df.loc[0,'result'] == SDC or df.loc[0,'result'] == MASKED:
                    df.loc[0,'result'] = SDC_UNACCEPTED
                # 进行崩溃后修复的案例  
                if df.loc[0,'result'] == C_SDC or df.loc[0,'result'] == C_MASKED:
                    df.loc[0,'result'] = C_SDC_UNACCEPTED
            else:
                # 在sdc容差内，需要进一步判断是否在masked容差内
                if df.loc[0,'result'] == SDC or df.loc[0,'result'] == MASKED:
                    if abs(bias) > masked_tolerance:
                        # 超出masked容差，直接判定为SDC_UNACCEPTED
                        df.loc[0,'result'] = SDC_ACCEPTED
                    else:
                        df.loc[0,'result'] = MASKED
                if df.loc[0,'result'] == C_SDC or df.loc[0,'result'] == C_MASKED:
                    if abs(bias) > masked_tolerance:
                        df.loc[0,'result'] = C_SDC_ACCEPTED
                    else:
                        df.loc[0,'result'] = C_MASKED
        
        if progname == "miniFE":
            # 这里暂时用bias指代程序输出值
            golden_bias = 4.15995e-11
            # bias 需要精确保存,使用科学计数法
            bias = np.double(df.loc[0,'bias'])
            bias = bias - golden_bias
            sdc_tolerance = abs(golden_bias - 1.0e-06)
            masked_tolerance = 1.0e-11

            update_sdc_result(bias, sdc_tolerance, masked_tolerance, df)
        elif progname == "hpl":
            golden_bias = 0.00808361278
            bias = np.double(df.loc[0,'bias'])
            bias = bias - golden_bias
            sdc_tolerance = abs(golden_bias - 16.0)
            masked_tolerance = 1.0e-03
            update_sdc_result(bias, sdc_tolerance, masked_tolerance, df)
        elif progname == "HPCCG":
            golden_bias = 5.35506e-38
            bias = np.double(df.loc[0,'bias'])
            bias = bias - golden_bias
            sdc_tolerance = abs(golden_bias - 1.0e-28)
            masked_tolerance = 1.0e-38
            update_sdc_result(bias, sdc_tolerance, masked_tolerance, df)
        elif progname in configure.PolyBenchtList:
            bias = float(df.loc[0,'bias'])
            if abs(bias) > 1e-10:
                # 无需修复的样例
                if df.loc[0,'result'] == SDC or df.loc[0,'result'] == MASKED:
                     df.loc[0,'result'] = SDC_UNACCEPTED
                # 进行崩溃后修复的案例
                if df.loc[0,'result'] == C_SDC or df.loc[0,'result'] == C_MASKED:
                     df.loc[0,'result'] = C_SDC_UNACCEPTED
            else:
                if df.loc[0,'result'] == SDC or df.loc[0,'result'] == MASKED:
                     df.loc[0,'result'] = SDC_ACCEPTED
                if df.loc[0,'result'] == C_SDC or df.loc[0,'result'] == C_MASKED:
                     df.loc[0,'result'] = C_SDC_ACCEPTED
            # else:
            #     print(bias,df.loc[0,'input_file'])
    if debug == 1:
        print(df.loc[0,'result'])
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)  # 如果目录不存在则创建
    # 构造输出文件路径
    output_file = os.path.join(output_dir, outputname)
    # 以追加的形式写入到CSV文件
    df.to_csv(output_file, mode='a+', header=not os.path.exists(output_file), index=False, na_rep='null')

    #print("Data has been extracted and appended to {}.".format(output_file))

def normalize_dynamic_inst_num(df,out_col):
    # 计算 dynamicInstNum 列的最小值和最大值
    min_value = df['dynamicInstNum'].min()
    max_value = df['dynamicInstNum'].max()
    
    # 进行 Min-Max 归一化，映射到 0 到 100
    df[out_col] = ((df['dynamicInstNum'] - min_value) / (max_value - min_value)) * 100
    
    return df


def quantify_smooth_col(df,col,key,col_out):
    # 对 df 按照 'dynamicInstNum' 列升序排序
    df = df.sort_values(by='dynamicInstNum').reset_index(drop=True)
    # 根据 'result' 列的值创建新的列 'Ybool'
    df['Ybool'] = df[col].apply(lambda x: 100 if x in key else 0)
    # 创建新的列 'Y'，用于存储平滑后的值
    Y_values = []

    # 遍历每一行，计算前后 100 项的 Ybool 加和再取平均
    for i in range(len(df)):
        # 计算当前点前后 100 项的索引范围
        start_index = max(0, i - 100)
        end_index = min(len(df), i + 101)  # 包含当前行和后 100 行

        # 计算前后 100 项的 Ybool 加和并取平均值
        smoothed_value = df['Ybool'][start_index:end_index].mean()

        # 保留小数点后四位
        Y_values.append(round(smoothed_value, 4))

    # 将平滑后的值添加到 DataFrame 中作为新的列 'Y'
    #return Y_values
    df[col_out] = Y_values
    #print(Y_values)

    return df


def pic1XappYaveragecrash(csv_dir, output_dir):
    # 列出文件夹中所有以 .csv 结尾的文件
    print("-----------------p1-----------------")
    csv_files = [file for file in os.listdir(csv_dir) if file.endswith('.csv')]

    file_names = []
    before_averages = []
    after_averages = []

    for file_name in csv_files:
        file_path = os.path.join(csv_dir, file_name)
        
        
        try:
            # 读取 CSV 文件
            df = pd.read_csv(file_path)
            # 检查是否包含 'result' 列
            if 'result' not in df.columns:
                print(f"File {file_name} does not contain 'result' column. Skipping...")
                continue
            #Y
            df1 = quantify_smooth_col(df,'result',[DOUBLE_CRASH,CRASH_NOPC,C_MASKED,C_SDC],'Before Recovery')
            df2 = quantify_smooth_col(df,'result',[DOUBLE_CRASH,CRASH_NOPC],'After Recovery')


            # 计算平均值
            before_avg = df1['Ybool'].mean()
            after_avg = df2['Ybool'].mean()
            before_avg = round(before_avg,2)
            after_avg = round(after_avg,2)
            # 存储结果
            file_names.append(file_name.replace('.csv',''))
            before_averages.append(before_avg)
            after_averages.append(after_avg)

            # 将修改后的数据保存回 CSV 文件
            #df.to_csv(file_path, index=False)
            print(f"Processed file: {file_name}")
        except:
            print("error in file:\t",file_name)

    # 绘制柱状图
    x = range(len(file_names))  # 横坐标位置

    plt.figure(figsize=(10, 5))
    bar_width = 0.35  # 柱宽度

    # 绘制每个文件的 Before 和 After 柱
    before_bars = plt.bar(x, before_averages, width=bar_width, label='Before Recovery', color='blue', align='center')
    after_bars = plt.bar([i + bar_width for i in x], after_averages, width=bar_width, label='After Recovery', color='orange', align='center')

    # 添加具体的 y 值标签到柱子上
    for bar in before_bars:
        yval = bar.get_height()
        plt.text(bar.get_x() + bar.get_width() / 2, yval, round(yval, 4), ha='center', va='bottom')

    for bar in after_bars:
        yval = bar.get_height()
        plt.text(bar.get_x() + bar.get_width() / 2, yval, round(yval, 4), ha='center', va='bottom')

    # 设置纵轴和横轴范围
    plt.ylim(0, 100)  # 纵轴范围
    # 设置刻度
    plt.yticks(range(20, 101, 20), [f'{i}%' for i in range(20, 101, 20)])  # 纵坐标从20到100，每隔20

    # 设置横坐标标签
    plt.xticks([i + bar_width / 2 for i in x], file_names, rotation=45, ha='right')

    #plt.xlabel('File Name')
    plt.ylabel('Crash%')
    plt.title('Crash% Averages: Before and After Recovery ')
    plt.legend()
    
    # 保存图形到指定路径
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"Created directory: {output_dir}")
    output_path = os.path.join(output_dir,'XappYaveragecrash')
    plt.tight_layout()
    plt.savefig(output_path, dpi=600)
    print("pic save in:\t", output_path+'.png')
    plt.close()  # 关闭图形以释放内存


def pic1XappYaveragecrash1(csv_dir, output_dir):
    # 列出文件夹中所有以.csv结尾的文件
    print("-----------------new_function-----------------")
    csv_files = [file for file in os.listdir(csv_dir) if file.endswith('.csv')]

    file_names = []
    double_crash_crash_nopc_c_masked_c_sdc_ratios = []
    double_crash_crash_nopc_ratios = []

    for file_name in csv_files:
        file_path = os.path.join(csv_dir, file_name)
        try:
            # 读取CSV文件
            df = pd.read_csv(file_path)
            if 'result' not in df.columns:
                print(f"File {file_name} does not contain 'result' column. Skipping...")
                continue

            total_count = len(df)
            double_crash_crash_nopc_c_masked_c_sdc_count = len(df[(df['result'] == DOUBLE_CRASH) |
                                                                 (df['result'] == CRASH_NOPC) |
                                                                 (df['result'] == C_MASKED) |
                                                                 (df['result'] == C_SDC)])
            double_crash_crash_nopc_count = len(df[(df['result'] == DOUBLE_CRASH) |
                                                   (df['result'] == 'crash')])

            ratio1 = double_crash_crash_nopc_c_masked_c_sdc_count / total_count if total_count > 0 else 0
            ratio2 = double_crash_crash_nopc_count / total_count if total_count > 0 else 0

            ratio1 = round(ratio1, 2)
            ratio2 = round(ratio2, 2)

            file_names.append(file_name.replace('.csv', ''))
            double_crash_crash_nopc_c_masked_c_sdc_ratios.append(ratio1)
            double_crash_crash_nopc_ratios.append(ratio2)

            print(f"Processed file: {file_name}")
        except:
            print("error in file:\t", file_name)

    # 绘制柱状图
    x = range(len(file_names))

    plt.figure(figsize=(10, 5))
    bar_width = 0.35

    bar1 = plt.bar(x, double_crash_crash_nopc_c_masked_c_sdc_ratios, width=bar_width, label='[DOUBLE_CRASH,CRASH_NOPC,C_MASKED,C_SDC] Ratio', color='green', align='center')
    bar2 = plt.bar([i + bar_width for i in x], double_crash_crash_nopc_ratios, width=bar_width, label='[DOUBLE_CRASH,CRASH_NOPC] Ratio', color='red', align='center')

    for b in bar1:
        yval = b.get_height()
        plt.text(b.get_x() + b.get_width() / 2, yval, round(yval, 4), ha='center', va='bottom')

    for b in bar2:
        yval = b.get_height()
        plt.text(b.get_x() + b.get_width() / 2, yval, round(yval, 4), ha='center', va='bottom')

    plt.ylim(0, 1)
    plt.yticks([0.1 * i for i in range(0, 11)], [f'{10 * i}%' for i in range(0, 11)])

    plt.xticks([i + bar_width / 2 for i in x], file_names, rotation=45, ha='right')

    plt.ylabel('Ratio')
    plt.title('Ratios of Different Categories in CSV Files')
    plt.legend()

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"Created directory: {output_dir}")
    output_path = os.path.join(output_dir, 'new_function_result')
    plt.tight_layout()
    plt.savefig(output_path, dpi=600)
    print("pic save in:\t", output_path+".png")

def pic4XappYresultundercrash(csv_dir, output_dir):
    # 列出文件夹中所有以 .csv 结尾的文件
    print("-----------------p4-----------------")
    csv_files = [file for file in os.listdir(csv_dir) if file.endswith('.csv')]
    target_elements = [C_MASKED,C_SDC,DOUBLE_CRASH,'crash']
    target_colors = ['green', 'Gold',  'OrangeRed', 'purple']
    """
    计算指定文件中 'result' 列中目标元素的个数及其占比，并保存结果到 DataFrame。
    
    :param csv_dir: 包含CSV文件的目录路径
    :param csv_files: 需要处理的CSV文件列表
    :param target_elements: 需要统计的目标元素列表
    :return: 结果的 DataFrame
    """
    # 存储结果
    file_names = []
    element_ratios = {element: [] for element in target_elements}

    for file_name in csv_files:
        file_path = os.path.join(csv_dir, file_name)

        try:
            # 读取 CSV 文件
            df = pd.read_csv(file_path)
            # 检查是否包含 'result' 列
            if 'result' not in df.columns:
                print(f"File {file_name} does not contain 'result' column. Skipping...")
                continue

            # 统计每种类型的个数
            crash_count = df['result'].value_counts()
            total_crashes = sum(crash_count[element] for element in target_elements if element in crash_count)

            # 计算百分比
            for element in target_elements:
                element_count = crash_count.get(element, 0)
                ratio = (element_count / total_crashes) * 100 if total_crashes > 0 else 0
                element_ratios[element].append(ratio)

            # 存储文件名
            file_names.append(file_name.replace(".csv",""))

            print(f"Processed file: {file_name}")
        except Exception as e:
            print(f"Error in file: {file_name}. Exception: {e}")

    # 组织结果到 DataFrame
    result_data = {'File Name': file_names}
    for element, ratios in element_ratios.items():
        result_data[f'{element}%'] = ratios

    result_df = pd.DataFrame(result_data)
    result_df.to_csv(os.path.join(output_dir,"pic4XappYresultundercrash.csv"), index=False)
    """
    根据 DataFrame 中的元素比例绘制堆积柱状图，并保存图表。
    
    :param result_df: 包含比例数据的 DataFrame
    :param target_elements: 需要绘制的目标元素列表
    :param output_dir: 保存输出图片的目录路径
    """
    # 提取数据
    file_names = result_df['File Name']
    x = range(len(file_names))  # 横坐标位置

    # 准备堆积数据
    bottoms = [0] * len(file_names)  # 初始化堆积基线
    plt.figure(figsize=(12, 6))

    target_elements = [C_MASKED,C_SDC,DOUBLE_CRASH,'crash']
    # 绘制堆积柱状图
    for element, color in zip(target_elements, target_colors):
        element_ratios = result_df[f'{element}%']
        plt.bar(x, element_ratios, bottom=bottoms, label=f'{element}', color=color)
        # 更新堆积基线
        bottoms = [b + e for b, e in zip(bottoms, element_ratios)]

    # 设置纵轴和横轴范围
    plt.ylim(0, 100)  # 纵轴范围固定在0到100
    plt.yticks(range(0, 101, 20), [f'{i}%' for i in range(0, 101, 20)])  # 纵坐标每隔20打一个标注，带百分号
    plt.xticks(x, file_names, rotation=45, ha='right')  # 横坐标为文件名
    plt.ylabel('%')
    plt.title('Result Ratios')
    plt.legend()

    # 保存图形到指定路径
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"Created directory: {output_dir}")
    output_path = os.path.join(output_dir, 'pic4XappYresultundercrash.png')
    plt.tight_layout()
    plt.savefig(output_path, dpi=600)
    print(f"Picture saved to: {output_path}")
    plt.close()  # 关闭图形以释放内存


def pic2XdynamicexcYcrash(csv_dir, output_dir):
    # 列出文件夹中所有以 .csv 结尾的文件
    print("-----------------p2-----------------")
    csv_files = [file for file in os.listdir(csv_dir) if file.endswith('.csv')]
    output_dir = os.path.join(output_dir,'dynamic_crash')
    for file_name in csv_files:
        file_path = os.path.join(csv_dir, file_name)
        
        
        try:
            # 读取 CSV 文件
            df = pd.read_csv(file_path)
            # 检查是否包含 'result' 列
            if 'result' not in df.columns:
                print(f"File {file_name} does not contain 'result' column. Skipping...")
                continue
            # Y
            df = quantify_smooth_col(df, 'result', [DOUBLE_CRASH, C_MASKED], 'Before Recovery')
            df = quantify_smooth_col(df, 'result', [DOUBLE_CRASH], 'After Recovery')
            #X
            df = normalize_dynamic_inst_num(df,'dynamicExc')
            
            # 绘制折线图
            plt.figure(figsize=(10, 6))
            plt.plot(df['dynamicExc'], df['Before Recovery'], label='Before Recovery', color='blue', linewidth=1)
            plt.plot(df['dynamicExc'], df['After Recovery'], label='After Recovery', color='orange', linewidth=1)

            # 设置纵轴和横轴范围
            plt.ylim(0, 100)  # 纵轴范围
            plt.xlim(0, 100)  # 横轴范围
            # 设置刻度
            plt.xticks(range(0, 101, 20), [f'{i}%' for i in range(0, 101, 20)])  # 横坐标从0到100，每隔20
            plt.yticks(range(20, 101, 20), [f'{i}%' for i in range(20, 101, 20)])  # 纵坐标从20到100，每隔20

            # 添加图表标题和标签
            plt.title(f'Crash% for {file_name}')
            plt.xlabel('Dynamic Execution (dynamicExc)')
            plt.ylabel('Crash%')
            plt.legend()

            # 保存图形到指定路径
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
                print(f"Created directory: {output_dir}")

            output_path = os.path.join(output_dir, f'XdynamicYcrash_{file_name.replace(".csv","")}.png')
            plt.tight_layout()
            plt.savefig(output_path, dpi=600)
            print(f"Saved plot for {file_name} in {output_path}")

            plt.close()  # 关闭图形以释放内存

        except Exception as e:
            print("error in file:\t",file_name)
            # 打印错误信息
            print(f"An error occurred: {e}")



def pic3_XdynamicExc_YcontinueIncrash(csv_dir, output_dir):
    # 列出文件夹中所有以 .csv 结尾的文件
    print("-----------------p3-----------------")
    csv_files = [file for file in os.listdir(csv_dir) if file.endswith('.csv')]
    output_dir = os.path.join(output_dir,'dynamic_continueIncrash')

    for file_name in csv_files:
        file_path = os.path.join(csv_dir, file_name)
        
        
        try:
            # 读取 CSV 文件
            df = pd.read_csv(file_path)
            # 检查是否包含 'result' 列
            if 'result' not in df.columns:
                print(f"File {file_name} does not contain 'result' column. Skipping...")
                continue
            # Y
            df = quantify_smooth_col(df, 'result', [DOUBLE_CRASH,C_MASKED,C_SDC], 'CRASH')
            df = quantify_smooth_col(df, 'result', [DOUBLE_CRASH], 'DOUBLE_CRASH')
            if file_name.replace('.csv','') in SdcAppList:
                df = quantify_smooth_col(df, 'result', [C_SDC], 'C_SDC')
            df = quantify_smooth_col(df, 'result', [C_MASKED], 'C_MASKED')
            df = quantify_smooth_col(df, 'result', [MASKED], 'MASKED')
            #X
            df = normalize_dynamic_inst_num(df,'dynamicExc')
            
            # 绘制折线图
            plt.figure(figsize=(10, 5))
            #plt.plot(df['dynamicExc'], df['DOUBLE_CRASH']/df['CRASH']*100, label='Continued_crash', color='blue', linewidth=1)
            plt.plot(df['dynamicExc'], df['C_MASKED']/df['CRASH']*100, label='Continued_correct', color='red', linewidth=1)
            if file_name.replace('.csv','') in SdcAppList:
                plt.plot(df['dynamicExc'], df['C_SDC']/df['CRASH']*100, label='Continued_SDC', color='green', linewidth=1)

            # 设置纵轴和横轴范围
            plt.ylim(0, 100)  # 纵轴范围
            plt.xlim(0, 100)  # 横轴范围
            # 设置刻度
            plt.xticks(range(0, 101, 20), [f'{i}%' for i in range(0, 101, 20)])  # 横坐标从0到100，每隔20
            plt.yticks(range(20, 101, 20), [f'{i}%' for i in range(20, 101, 20)])  # 纵坐标从20到100，每隔20

            # 添加图表标题和标签
            plt.title(f'Continued_correct% for {file_name}')
            plt.xlabel('Dynamic Execution (dynamicExc)')
            plt.ylabel(' ')
            plt.legend()

            # 保存图形到指定路径
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
                print(f"Created directory: {output_dir}")

            output_path = os.path.join(output_dir, f"XdynamicYcontinueIncrash_{file_name.replace('.csv','')}.png")
            plt.tight_layout()
            plt.savefig(output_path, dpi=600)
            print(f"Saved plot for {file_name} in {output_path}")

            plt.close()  # 关闭图形以释放内存

        except Exception as e:
            print("error in file:\t",file_name)
            # 打印错误信息
            print(f"An error occurred: {e}")


def save_three_line_table(result_table, file_name, output_dir, prefix):
    # 创建一个新的图形
    fig, ax = plt.subplots()  # 可以根据需要调整大小

    # 关闭坐标轴
    ax.axis('tight')
    ax.axis('off')

    # 设置标题
    title = f'Recoverability in {file_name}'
    plt.title(title, fontsize=14, weight='bold')

    # 创建表格
    table_data = result_table.values
    columns = result_table.columns.tolist()
    
    # 创建表格
    table = ax.table(cellText=table_data, colLabels=columns, cellLoc='center', loc='center')

    # 设置表格样式
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1.2, 1.2)  # 调整表格大小

    

    # 保存为图片
    output_path = f"{output_dir}/{prefix}{file_name.strip('.csv')}.png"
    plt.savefig(output_path, bbox_inches='tight', dpi=300)
    plt.close()  # 关闭图形以释放内存


def plot_grouped_bar_chart(result_table, file_name, output_dir, prefix):
    # 过滤掉 col1 值小于 1 的行
    filtered_result_table = result_table[result_table[result_table.columns[1]] >= 1]  # 根据 col1 进行过滤

    # 创建一个新的图形
    fig, ax = plt.subplots(figsize=(10, 6))  # 根据需要调整大小

    # 设置标题
    title = f'Recoverability in {file_name}'
    plt.title(title, fontsize=14, weight='bold')

    # 获取数据
    categories = filtered_result_table[filtered_result_table.columns[0]]  # 第一列作为横坐标
    num_columns = len(filtered_result_table.columns) - 1  # 除去第一列的列数
    values = filtered_result_table.iloc[:, 1:num_columns + 1]  # 获取后面的所有列

    # 设置柱宽和位置
    bar_width = 0.2
    x = np.arange(len(categories))  # 横坐标位置

    # 绘制柱状图
    for i in range(num_columns):
        bars = ax.bar(x + i * bar_width, values.iloc[:, i], width=bar_width, label=filtered_result_table.columns[i + 1])
        
        # 添加标签
        for bar in bars:
            yval = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2, yval, f'{yval:.1f}', ha='center', va='bottom', fontsize=10)

    # 设置坐标轴标签
    ax.set_xlabel('Categories', fontsize=12)
    ax.set_ylabel('Values', fontsize=12)
    ax.set_xticks(x + bar_width * (num_columns - 1) / 2)  # 设置 x 轴的刻度位置
    ax.set_xticklabels(categories, rotation=45, ha='right')  # 设置 x 轴标签并旋转

    # 添加图例
    ax.legend()

    # 保存为图片
    output_path = f"{output_dir}/{prefix}{file_name.strip('.csv')}_grouped_bar_chart.png"
    plt.tight_layout()  # 自动调整布局
    plt.savefig(output_path, bbox_inches='tight', dpi=300)
    plt.close()  # 关闭图形以释放内存

    print(f"Grouped bar chart saved at: {output_path}")



def Tab1FuncCrash(csv_dir, func, output_dir):
    # 确保输出目录存在
    output_dir = os.path.join(output_dir, 'Tab1FuncCrash')
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"Created output directory: {output_dir}")

    # 列出所有CSV文件
    csv_files = [file for file in os.listdir(csv_dir) if file.endswith('.csv')]

    for file_name in csv_files:
        file_path = os.path.join(csv_dir, file_name)

        try:
            # 读取 CSV 文件为 DataFrame
            df = pd.read_csv(file_path)

            # 检查是否包含必要的列
            if func not in df.columns or 'result' not in df.columns:
                print(f"File {file_name} does not contain necessary columns:\t {str(func)}. Skipping...")
                continue

            col1 = 'Percentage of Each Category in Total'
            col2 = 'Crash to Masked%'
            col3 = 'Crash to SDC%'
            col4 = 'Crash to Double%'
            result_table = pd.DataFrame(columns=[func, col1, col2, col3, col4])

            # 根据列 'Func' 中的唯一值进行分组计算
            for func_value in df[func].unique():
                if isinstance(func_value, float):
                    continue

                func_group = df[df[func] == func_value]
                total_count = func_group.shape[0]

                # 计算 C_MASKED 和 C_SDC 的百分比
                c_masked_count = func_group[func_group['result'] == C_MASKED].shape[0]
                c_masked_percentage = (c_masked_count / total_count * 100) if total_count > 0 else 0

                c_sdc_count = func_group[func_group['result'] == C_SDC].shape[0]
                c_sdc_percentage = (c_sdc_count / total_count * 100) if total_count > 0 else 0

                # 计算 DOUBLE_CRASH 的百分比
                double_crash_count = func_group[func_group['result'] == DOUBLE_CRASH].shape[0]
                double_crash_percentage = (double_crash_count / total_count * 100) if total_count > 0 else 0

                # 计算 func 在整个 DataFrame 中的百分比
                total_func_count = df[func].notna().sum()
                func_percentage = (total_count / total_func_count * 100) if total_func_count > 0 else 0

                # 将计算结果添加到结果表格中
                new_row = pd.DataFrame({
                    func: [func_value],
                    col1: [round(func_percentage, 2)],
                    col2: [round(c_masked_percentage, 2)],
                    col3: [round(c_sdc_percentage, 2)],
                    col4: [round(double_crash_percentage, 2)]  # 添加 DOUBLE_CRASH 的百分比
                })
                result_table = pd.concat([result_table, new_row], ignore_index=True)

            # 过滤掉 Percentage of Each Category in Total 小于 1% 的数据
            #result_table = result_table[result_table[col1] >= 1]

            # 排序
            result_table = result_table.sort_values(by=col1, ascending=False)

            # 保存结果表格到输出目录
            output_file_path = os.path.join(output_dir, f"FuncCrash_{file_name.replace('.csv', '')}.csv")
            result_table.to_csv(output_file_path, index=False)
            print(f"Processed and saved summary for file: {file_name}")

            # 画堆积图
            plot_stacked_bar_chart(file_name.replace('.csv', ''), result_table, func, col2, col3, col4, output_file_path)

        except Exception as e:
            print(f"Error processing file {file_name}: {e}")

def plot_stacked_bar_chart1(filename, data, func, col2, col3, col4, col1, output_file_path):
    # 设置样式
    sns.set(style='white')
    plt.figure(figsize=(12, 6))

    # 堆积图
    bar_width = 0.4
    indices = np.arange(len(data))

    # 计算每一部分的高度
    heights_col2 = data[col2] #* data[col1] / 100
    heights_col3 = data[col3] #* data[col1] / 100
    heights_col4 = data[col4] #* data[col1] / 100

    # 创建堆积图
    plt.bar(indices, heights_col2, color='green', label=col2)
    plt.bar(indices, heights_col3, bottom=heights_col2, color='yellow', label=col3)
    plt.bar(indices, heights_col4, bottom=heights_col2 + heights_col3, color='red', label=col4)

    
    # 设置标题和标签
    plt.ylabel('Percentage (%)', fontsize=14, fontweight='bold')
    plt.title('Repairability of ' + filename, fontsize=16, fontweight='bold')
    plt.xticks(indices, data[func], rotation=45, ha='right', fontsize=12)
    
    # 设置图例
    plt.legend(fontsize=12, loc='upper left', bbox_to_anchor=(1, 1))

    # 美化图形
    plt.tight_layout()
    
    # 保存图形
    chart_file_path = output_file_path.replace('.csv', '.png')
    plt.savefig(chart_file_path, dpi=300, bbox_inches='tight')  # 高分辨率输出
    plt.close()
    print(f"Saved stacked bar chart for {output_file_path}")

def count_result_elements(csv_dir, output_dir, app='all'):
    """
    统计csv目录中result列的不同元素个数并保存到指定输出目录，输出格式包含app信息。
    
    :param csv_dir: 包含CSV文件的目录
    :param output_dir: 输出文件保存的目录
    :param app: 指定的CSV文件名（不带路径），如果为'all'则处理所有文件
    """
    try:
        # 创建输出目录（如果不存在）
        os.makedirs(output_dir, exist_ok=True)

        # 确定需要处理的文件列表
        if app == 'all':
            all_files = [os.path.join(csv_dir, f) for f in os.listdir(csv_dir) if f.endswith('.csv')]
        else:
            file_path = os.path.join(csv_dir, app+'.csv')
            if os.path.isfile(file_path):
                all_files = [file_path]
            else:
                raise FileNotFoundError(f"File {app} not found in {csv_dir}")

        # 初始化结果存储
        results = []

        for file in all_files:
            try:
                data = pd.read_csv(file)
                if 'result' in data.columns:
                    file_name = os.path.basename(file)
                    result_counts = data['result'].value_counts()
                    result_dict = {'app': file_name}
                    result_dict['total'] = int(result_counts.sum())
                    result_dict.update(result_counts.to_dict())
                    results.append(result_dict)
            except Exception as e:
                print(f"Error reading {file}: {e}")

        # 转换为DataFrame，填充缺失值为0
        result_df = pd.DataFrame(results).fillna(0)
        # 确保所有值为整数（除app列外）
        for col in result_df.columns:
            if col != 'app':
                result_df[col] = result_df[col].astype(int)


        # 保存到CSV文件
        output_file = os.path.join(output_dir, "result_counts.csv")
        result_df.to_csv(output_file, index=False)

        # 打印结果
        print(result_df)

        return result_df

    except Exception as e:
        print(f"An error occurred: {e}")
        return None

def plot_stacked_bar_chart(filename, data, func, target_elements, target_colors, output_file_path):
    """
    绘制堆积柱状图，显示每个目标元素的占比，并保存为图片。
    
    :param filename: 当前文件名，用于标题
    :param data: 包含目标列的 DataFrame
    :param func: 分组列名称
    :param target_elements: 目标元素列表
    :param target_colors: 每个目标元素的对应颜色列表
    :param output_file_path: 输出文件路径
    """
    import matplotlib.pyplot as plt
    import numpy as np

    # 设置样式
    plt.figure(figsize=(12, 6))

    # 堆积图参数
    bar_width = 0.4
    indices = np.arange(len(data))

    # 初始化堆积基线
    bottoms = np.zeros(len(data))

    # 绘制堆积图
    for element, color in zip(target_elements, target_colors):
        heights = data[f'{element}%']
        plt.bar(indices, heights, bottom=bottoms, color=color, label=element)
        bottoms += heights

    # 设置标题和标签
    plt.ylabel('Percentage (%)', fontsize=14, fontweight='bold')
    plt.title(f'Repairability of {filename}', fontsize=16, fontweight='bold')
    plt.xticks(indices, data[func], rotation=45, ha='right', fontsize=12)

    # 设置图例
    plt.legend(fontsize=12, loc='upper left', bbox_to_anchor=(1, 1))

    # 美化图形
    plt.tight_layout()

    # 保存图形
    chart_file_path = output_file_path.replace('.csv', '.png')
    plt.savefig(chart_file_path, dpi=300, bbox_inches='tight')  # 高分辨率输出
    plt.close()
    print(f"Saved stacked bar chart for {chart_file_path}")


def Tab_col_Recovery(csv_dir, grouping_column, output_dir):
    """
    计算每个 group 的 target_elements 在 result 列中的百分比，并绘制堆积图。
    
    :param csv_dir: 包含 CSV 文件的目录路径
    :param grouping_column: 分组的列
    :param target_elements: 要统计的目标元素列表
    :param output_dir: 输出目录
    """
    target_elements = [C_MASKED,C_SDC,DOUBLE_CRASH]
    target_colors = ['green', 'Gold',  'OrangeRed', 'purple']
    # 确保输出目录存在
    output_dir = os.path.join(output_dir, f'Tab_{grouping_column}_Recovery')
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"Created output directory: {output_dir}")

    # 列出所有 CSV 文件
    csv_files = [file for file in os.listdir(csv_dir) if file.endswith('.csv')]

    for file_name in csv_files:
        file_path = os.path.join(csv_dir, file_name)

        try:
            # 读取 CSV 文件为 DataFrame
            df = pd.read_csv(file_path)

            # 检查是否包含必要的列
            if grouping_column not in df.columns or 'result' not in df.columns:
                print(f"File {file_name} does not contain necessary columns. Skipping...")
                continue

            # 剔除 result 列中不在目标元素列表中的行
            df = df[df['result'].isin(target_elements)]

            # 初始化结果表格
            col_percentage = 'Percentage of Each Category in Total'
            result_table_columns = [grouping_column, col_percentage] + [f'{elem}%' for elem in target_elements]
            result_table = pd.DataFrame(columns=result_table_columns)

            # 根据分组进行统计
            for value in df[grouping_column].unique():
                if isinstance(value, float):
                    continue

                group = df[df[grouping_column] == value]
                total_count = group.shape[0]

                # 计算每个目标元素的百分比
                percentages = {}
                for element in target_elements:
                    element_count = group[group['result'] == element].shape[0]
                    percentages[f'{element}%'] = (element_count / total_count * 100) if total_count > 0 else 0

                # 计算分组在整个 DataFrame 中的百分比
                total_count_non_na = df[grouping_column].notna().sum()
                percentage = (total_count / total_count_non_na * 100) if total_count_non_na > 0 else 0

                # 添加结果到结果表
                new_row = {grouping_column: value, col_percentage: round(percentage, 2)}
                new_row.update({key: round(value, 2) for key, value in percentages.items()})
                result_table = pd.concat([result_table, pd.DataFrame([new_row])], ignore_index=True)

            # 排序
            result_table = result_table.sort_values(by=col_percentage, ascending=False)

            # 保存结果表格到输出目录
            output_file_path = os.path.join(output_dir, f"Recovery_{file_name.replace('.csv', '')}.csv")
            result_table.to_csv(output_file_path, index=False)
            print(f"Processed and saved summary for file: {file_name}")

            plot_stacked_bar_chart(file_name.replace('.csv', ''), result_table, grouping_column, target_elements, target_colors, output_file_path)
        except Exception as e:
            print(f"Error processing file {file_name}: {e}")

def Tab_col_Recovery2(csv_dir, grouping_column, output_dir):
    # 确保输出目录存在
    output_dir = os.path.join(output_dir, 'Tab_'+str(grouping_column)+'_Recovery')
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"Created output directory: {output_dir}")

    # 列出所有CSV文件
    csv_files = [file for file in os.listdir(csv_dir) if file.endswith('.csv')]

    for file_name in csv_files:
        file_path = os.path.join(csv_dir, file_name)

        try:
            # 读取 CSV 文件为 DataFrame
            df = pd.read_csv(file_path)

            # 检查是否包含必要的列
            if grouping_column not in df.columns or 'result' not in df.columns:
                print(f"File {file_name} does not contain necessary columns{str(grouping_column)}. Skipping...")
                continue

            # 剔除 result 列中为 C_MASKED 或 C_SDC 的行
            df = df[~df['result'].isin([MASKED, SDC])]

            col1 = 'Percentage of Each Category in Total'
            col2 = 'C_MASKED%'
            col3 = 'C_SDC%'
            col4 = 'DOUBLE_CRASH%'
            result_table = pd.DataFrame(columns=[grouping_column, col1, col2, col3, col4])

            # 根据选择的列进行分组计算
            for value in df[grouping_column].unique():
                if isinstance(value, float):
                    continue

                group = df[df[grouping_column] == value]
                total_count = group.shape[0]

                # 计算 C_MASKED 和 C_SDC 的百分比
                c_masked_count = group[group['result'] == C_MASKED].shape[0]
                c_masked_percentage = (c_masked_count / total_count * 100) if total_count > 0 else 0

                c_sdc_count = group[group['result'] == C_SDC].shape[0]
                c_sdc_percentage = (c_sdc_count / total_count * 100) if total_count > 0 else 0

                # 计算 DOUBLE_CRASH 的百分比
                double_crash_count = group[group['result'] == DOUBLE_CRASH].shape[0]
                double_crash_percentage = (double_crash_count / total_count * 100) if total_count > 0 else 0

                # 计算 func 在整个 DataFrame 中的百分比
                total_count_non_na = df[grouping_column].notna().sum()
                percentage = (total_count / total_count_non_na * 100) if total_count_non_na > 0 else 0

                # 将计算结果添加到结果表格中
                new_row = pd.DataFrame({
                    grouping_column: [value],
                    col1: [round(percentage, 2)],
                    col2: [round(c_masked_percentage, 2)],
                    col3: [round(c_sdc_percentage, 2)],
                    col4: [round(double_crash_percentage, 2)]
                })
                result_table = pd.concat([result_table, new_row], ignore_index=True)

            # 排序
            result_table = result_table.sort_values(by=col1, ascending=False)

            # 保存结果表格到输出目录
            output_file_path = os.path.join(output_dir, f"Recovery_{file_name.replace('.csv', '')}.csv")
            result_table.to_csv(output_file_path, index=False)
            print(f"Processed and saved summary for file: {file_name}")

            # 画堆积图
            plot_stacked_bar_chart(file_name.replace('.csv', ''), result_table, grouping_column, col2, col3, col4, col1,output_file_path)

        except Exception as e:
            print(f"Error processing file {file_name}: {e}")


def analyze_one_batch(progname, log_folder, analysis_csv_folder, result_analyze_csv_name, asm_folder):
    print("Read logs and generate csv")

    print(f"Processing program: {progname}")
    read_logs(progname, log_folder, analysis_csv_folder, result_analyze_csv_name)

    # 检查是否需要进行更多的查找
    if findmorebypc == 1:
        try:
            asm_file = os.path.join(asm_folder,progname+'.asm')
            findins.findinsbyasm(progname,asm_file,analysis_csv_file)
        except Exception as e:
            print("error findins.findinsbyasm(progname):\t",e)


def main():
    global progname,inject_random_or_targeted,select_type
    if args.p or args.t:
        csv_dir = analysis_csv_folder
        pic_dir = pic_folder
        if args.p == '1':
            pic1XappYaveragecrash(csv_dir,pic_dir)
        elif args.p == '2':
            pic2XdynamicexcYcrash(csv_dir,pic_dir)
        elif args.p == '3':
            pic3_XdynamicExc_YcontinueIncrash(csv_dir,pic_dir)
        elif args.p == '4':
            pic4XappYresultundercrash(csv_dir,pic_dir)
        if args.t == '1':
            Tab_col_Recovery(csv_dir,'Sig1Func',pic_dir)
        elif args.t == '2':
            Tab_col_Recovery(csv_dir,'Sig1',pic_dir)
        elif args.t == '3':
            Tab_col_Recovery(csv_dir, 'injreg', pic_dir)
        elif args.t == 'result':
            count_result_elements(csv_dir, pic_dir, all)
        elif args.t and not args.t == 'all':
            Tab_col_Recovery(csv_dir, args.t, pic_dir)
        if args.p == 'all':
            pic1XappYaveragecrash(csv_dir,pic_dir)
            pic2XdynamicexcYcrash(csv_dir,pic_dir)
            #pic3_XdynamicExc_YcontinueIncrash(csv_dir,pic_dir)
            pic4XappYresultundercrash(csv_dir,pic_dir)
        if args.t == 'all':
            count_result_elements(csv_dir, pic_dir, app='all')
            Tab_col_Recovery(csv_dir,'Heuristic',pic_dir)
            Tab_col_Recovery(csv_dir,'Sig1Func',pic_dir)
            Tab_col_Recovery(csv_dir,'Sig1',pic_dir)
            Tab_col_Recovery(csv_dir, 'injreg', pic_dir)
            Tab_col_Recovery(csv_dir, 'Sig1Ope', pic_dir)
            Tab_col_Recovery(csv_dir, 'ErrSpd_Fix', pic_dir)
            
        return

    if args.file and args.flag:##调试单个log
        extract_values_and_append_to_csv(os.path.join(log_folder,str(args.file)),log_folder,args.file+'.csv',args.flag, args.sdc_flag)
        return

    if args.analyze_all:
        directory = os.path.join(configure.letgo_base_home,Result_folder_name)
        try:
            # 获取目录中所有子文件夹名
            prognames = [name for name in os.listdir(directory) if os.path.isdir(os.path.join(directory, name))]
            
            # 批量调用 all 函数
            for progname in prognames:
                try:
                    print (progname)
                    continue
                    analyze_one_batch(progname, log_folder, analysis_csv_folder, result_analyze_csv_name, asm_folder)
                except:
                    print("--------------------------------fail--------------------------------")
                    continue
        except Exception as e:
            print(f"An error occurred during batch processing: {e}")
            sys.exit(1)
        return

    # 下面是针对单个程序的分析，会解析该程序的log文件夹，生成csv文件
    if 1:
        # 先反汇编得到静态信息
        disassemble_binary()
        # 通过golden_output比较,在log文件中添加sdc结果
        Add_SDC_result_to_alllog_common(progname = progname, \
                                        output_name = configure.output_name, \
                                        log_path= os.path.join(one_batch_folder,"log"), \
                                        sdcout_folder= os.path.join(one_batch_folder,"sdcout"), \
                                        cmp_str = configure.cmp_str,\
                                        tolerance=configure.tolerance)
        # 读取一个log文件,生成csv文件的一行结果
        analyze_one_batch(progname, log_folder, analysis_csv_folder, result_analyze_csv_name, asm_folder)



if __name__ == "__main__":
    main()
    

    