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

#######---------------FOLLOWED ARE SWITCH---------------#########
## clsfy == 1 to move unfinished record to folder "unfinish"
clsfy = 0
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
parser.add_argument('-p', type=str, help="picture type")
parser.add_argument('-t', type=str, help="Table type")
args = parser.parse_args()

progname = configure.progname
if args.bname:
    progname = args.bname


file_count = 0
crash_1 = []
crash_2 = []
crash_2p = []
finish = []
flag = 0
unfinishedlist = []
output = []

log_dir = configure.log_path   ##数据源目录
print("log_dir in:\t",log_dir)
if not (os.path.exists(log_dir) and os.path.isdir(log_dir)):
    print("{} does not exist or is not a directory".format(log_dir))
    exit(0)

csv_dir = configure.csv_folder                  ##将log_dir的海量数据收集整理到csv_dir中
pic_dir = configure.pic_folder

"""#选定csv文件分析
csv_dir = os.path.join(configure.letgo_base_home,"nosdcarchive/CSV")
pic_dir = os.path.join(configure.letgo_base_home,"nosdcarchive/PIC")"""


# 直接从 configure 中导入所需的变量
SdcAppList = configure.SdcAppList
MASKED = configure.MASKED
SDC = configure.SDC
C_MASKED = configure.C_MASKED
C_SDC = configure.C_SDC
DOUBLE_CRASH = configure.DOUBLE_CRASH
CRASH2_PLUS = configure.CRASH2_PLUS



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

def move_file_to_dir(f, log_dir, folder_name):
    # 创建目标文件夹路径
    target_dir = os.path.join(log_dir, folder_name)

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
    folder_path = log_dir # 修改为你实际的文件夹路径

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


def read_logs(progname):
    global file_count, crash_1, crash_2, crash_2p, finish, flag, detected, correct, sdc, unfinishedlist, output
    
    if to_csv == 1:
        csv_file_path = os.path.join(log_dir,csv_dir, progname+'.csv')
        # 检查文件是否存在，如果存在则删除
        if os.path.exists(csv_file_path):
            os.remove(csv_file_path)
            print("Deleted old ",csv_file_path)
        else:
            print(progname+'.csv'," does not exist.")

    for f in os.listdir(log_dir):
        file_count +=1
        #print f
        if "log_" not in f:
            print("prefix should be 'log_'")
            continue
        f = os.path.join(log_dir,f)
        flag = 0
        sdc_flag = 0
        with open(f,"r",encoding='utf-8', errors='ignore') as log:
            unfinished = 0
            lines = log.readlines()
            # 判断 lines 是否为空
            if not lines:
                print(f"文件 '{f}' 是空的，跳过此文件。")
                continue  # 跳过此文件
            bugin = 0
            for line in lines:
                if "Traceback" in line:
                    print("Bug in:\t",f)
                    if delbug == 1:
                        os.remove(f)  # 删除文件
                        print("delete:\t",f)
                        bugin = 1
                        break
                if "Program received signal" in line:
                    flag += 1
                if "1 tests completed and failed residual checks" in line:##hpl
                    sdc_flag = 1
                if "sdcjuge: The outputs are different." in line:
                    sdc_flag = 1
                if "dismatch at" in line:##lu
                    sdc_flag = 1
                    
            #print flag_sdc
                if "Exit" in line:
                    unfinished = 1
                if "Error" in line:
                    unfinished = 1
                if "Cannot insert breakpoint" in line:
                    unfinished = 1

            if unfinished == 1:
                unfinishedlist.append(f)
                if clsfy == 1:
                    move_file_to_dir(f,log_dir,"unfinish")
                continue
            if bugin == 1:
                continue
                
            if flag == 1:
                crash_1.append(f)
            if flag == 2:
                crash_2.append(f)
            if flag >2:
                crash_2p.append(f)
            if flag == 0:
                finish.append(f)
            #break
        if to_csv == 1:
            extract_values_and_append_to_csv(f, log_dir, progname+'.csv', flag,sdc_flag)
"""
    print("crash1:\t",len(crash_1)) ##只收到一次越界错误segmentfault
    print("crash2:\t",len(crash_2)) ##收到两次越界错误
    print("no crash finish:\t",len(finish))  ##一次错误都没有,直接结束
    ############
    #print("sdc:\t",len(sdc))
    #print("detected:\t",len(detected))
    print("file count:",file_count)
    print("unfinishedlist:",len(unfinishedlist))
    print("valid countL",file_count-len(unfinishedlist))

    n = 5
    print("\ncrash1:\t",crash_1[:n])
    find_and_print_sig_time(os.path.join(crash_1[0]))
    print("crash2:\t",crash_2[:n])
    try:
        print("crash2+:\t",crash_2p[:n])
        print("crash2+len:\t",len(crash_2p))
    except:
        print("no crash2+")
    if len(crash_2)>1:
        find_and_print_sig_time(os.path.join(crash_2[0]))
    #print("sdc:\t",sdc[:n])
    #print(detected[:n])
    print("no crash finish:\t",finish[:n]) 
    find_and_print_sig_time(os.path.join(finish[0]))
    #print("unfinishedlist:",unfinishedlist[:n])
    #find_and_print_sig_time(os.path.join(unfinishedlist[0]))
    #print(list(set(crash_1).difference((set(crash_1) & set(correct))))[:n])
"""

def extract_values_and_append_to_csv(input_file, log_dir, outputname, flag, sdc_flag):
    if debug_mode >=6:
        print("\nnow do extract_values_and_append_to_csv")
    # 创建 CSV 文件保存的目录
    output_dir = os.path.join(log_dir,csv_dir)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)  # 如果目录不存在则创建

    # 创建一个空的 DataFrame
    df = pd.DataFrame(columns=['input_file','dynamicInstNum' ,'regmm','reg', 'injreg', 'pc', 'iteration1','hexpc', 'ins', 'opcode', 'Func','result', 'Sig1','Sig1pc','Sig1Ins','Sig1Ope','Sig1Func','ErrSpd_Inj', 'Sig2','Sig2pc','Sig2Ins','Sig2Ope','Sig2Func','ErrSpd_Fix' ])


    if flag == 0:
        df.loc[0, 'result'] = MASKED
        if sdc_flag == 1:
            df.loc[0, 'result'] = SDC
    elif flag == 1:
        df.loc[0, 'result'] = C_MASKED
        if sdc_flag == 1:
            df.loc[0, 'result'] = C_SDC
    elif flag == 2:
        df.loc[0, 'result'] = DOUBLE_CRASH
    else:
        df.loc[0, 'result'] = CRASH2_PLUS
        
    # 获取文件名
    file_name = os.path.basename(input_file)
    df.loc[0,'input_file'] = file_name

    # 读取文件并提取所需内容
    with open(input_file, 'r') as file:
        values = ['null'] * 4
        SIGcount = 0
        Sig1byletgo_Flag = 0

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

            if "display the inst:" in line:
                next_3_line = next_i_line_content(file,3,"=>")
                #print(next_3_line)
                # 提取指令和函数名
                ins = ""
                # 查找指令和函数名
                parts = next_3_line.split(':')
                #print (parts)
                if len(parts) > 1:
                    # 提取指令
                    ins = parts[-1].strip(' ')  # 冒号后面的内容，去除多余空格
                    if ins == '':
                        ins = next_i_line_content(file,1,"0x").split('#')[0].rstrip()
                        print("ins not in => line")
                        print(ins)
                    opcode = ins.split(' ')[0]
                
                # 将提取到的值添加到 DataFrame 中
                df.loc[0,'ins'] = ins 
                df.loc[0,'opcode'] = opcode
                
                continue
            
            #首次遇到SIG
            if "received signal" in line and SIGcount == 0 :#and df.loc[0,'result'] != MASKED:  
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
                    if '0x' in insline:
                        df.loc[0,Sigpc] = '0x' + insline.split(' ')[0].lstrip('0')
                        df.loc[0,SigFunc] = insline.split('in')[-1].split(' ')[0].strip()
                    
                    insline = next_i_line_content(file,2,'=>')
                    if '=>' in insline:
                        df.loc[0,Sigpc] = insline.split('=>')[-1].split(':')[0].split('<')[0].strip()
                        if len(insline.split(':')) > 1:
                            df.loc[0,SigIns] = insline.split(':')[1].strip('"')
                        else:
                            df.loc[0,SigIns] = insline.split(':')[-1].replace('"','').strip('"')

                        """if 'rex' in df.loc[0,SigIns]:
                            df.loc[0,SigOpe] = df.loc[0,SigIns].split(' ')[1]
                        else:
                            df.loc[0,SigOpe] = df.loc[0,SigIns].split(' ')[0]"""

                        if len(insline.split('<')) > 1:
                            df.loc[0,SigFunc] = insline.split('<')[1].split('>')[0].split('+')[0].strip('<')
                        else:
                            df.loc[0,SigFunc] = 'null'
                except:
                    print("get info at signal1 fail",input_file)
                SIGcount = 1
                continue

            if Sig1byletgo_Flag == 1 and 'Letgo in!' in line:
                tmp = next_i_line_content(file,3,"=")
                tmp = tmp.split('0x')[-1][:6]
                try:
                    if is_valid_hex_address(tmp):
                        df.loc[0,'Sig1pc'] = '0x' + tmp.strip(' ')
                        SIGcount = 1
                        if debug_mode > 5:
                            print("Find Sig1pc by Letgo in!\t",input_file)
                except:
                    if debug_mode > 4:
                        print("Sig1pc fetched by letgoin:\t",tmp)
                        print("Letgo in! next3line with no valid Sig1pc \t",input_file)
                    continue
                


            if "Inj2Sig" in line.strip():
                #print(line)
                df.loc[0,'ErrSpd_Inj'] = int(line.split(':')[-1])
                continue
            if ("After Inject:" in line):
                df.loc[0,'ErrSpd_Inj'] = 999
                continue

            #再次遇到SIG
            if "received signal" in line and SIGcount == 1 :#and df.loc[0,'result'] == DOUBLE_CRASH:  
                Sig = 'Sig2'
                Sigpc = 'Sig2pc'
                SigIns = 'Sig2Ins'
                SigOpe = 'Sig2Ope'
                SigFunc = 'Sig2Func'

                try:
                    tmp = line.split(',')[0]
                    tmp = tmp.split('signal')[1]
                    df.loc[0,Sig] = tmp.strip()
                    """insline = next_i_line_content(file,1,'0x')
                    if '0x' in insline:
                        df.loc[0,Sigpc] = '0x' + insline.split(' ')[0].lstrip('0')
                        df.loc[0,SigFunc] = insline.split('in')[-1].split(' ')[0].strip()"""
                    
                    insline = next_i_line_content(file,2,'=>')
                    if '=>' in insline:
                        df.loc[0,Sigpc] = insline.split('=>')[-1].split(':')[0].split('<')[0].strip()
                        if len(insline.split(':')) > 1:
                            df.loc[0,SigIns] = insline.split(':')[1].strip('"')
                        else:
                            df.loc[0,SigIns] = insline.split(':')[-1].replace('"','').strip('"')

                        """if 'rex' in df.loc[0,SigIns]:
                            df.loc[0,SigOpe] = df.loc[0,SigIns].split(' ')[1]
                        else:
                            df.loc[0,SigOpe] = df.loc[0,SigIns].split(' ')[0]"""

                        if len(insline.split('<')) > 1:
                            df.loc[0,SigFunc] = insline.split('<')[1].split('>')[0].split('+')[0].strip('<')
                        else:
                            df.loc[0,SigFunc] = 'null'
                except:
                    print("get info at signal2 fail",input_file)
                
                continue

            if ("Valid Fix2Sig" in line ):
                df.loc[0,'ErrSpd_Fix'] = int(line.split(':')[-1])
            if ("After Fixed" in line) :
                df.loc[0,'ErrSpd_Fix'] = 999

        if debug_mode > 7:
            print("after extract_values_and_append_to_csv df Followed:\n",df.to_string(header=False, index=False))

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
            df1 = quantify_smooth_col(df,'result',[DOUBLE_CRASH,C_MASKED],'Before Recovery')
            df2 = quantify_smooth_col(df,'result',[DOUBLE_CRASH],'After Recovery')


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
    print("pic save in:\t", output_path)
    plt.close()  # 关闭图形以释放内存

def pic4XappYresultundercrash(csv_dir, output_dir):
    # 列出文件夹中所有以 .csv 结尾的文件

    csv_files = [file for file in os.listdir(csv_dir) if file.endswith('.csv')]

    file_names = []
    DOUBLE_CRASH_ratios = []
    C_MASKED_ratios = []
    C_SDC_ratios = []

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
            df = quantify_smooth_col(df,'result',[DOUBLE_CRASH,C_MASKED,C_SDC],'Crash')
            df = quantify_smooth_col(df,'result',[DOUBLE_CRASH],'DOUBLE_CRASH')
            df = quantify_smooth_col(df,'result',[C_MASKED],'C_MASKED')
            df = quantify_smooth_col(df,'result',[C_SDC],'C_SDC')

            # 计算每列的比例
            DOUBLE_CRASH_ratio = df['DOUBLE_CRASH'].sum() / df['Crash'].sum() * 100
            C_MASKED_ratio = df['C_MASKED'].sum() / df['Crash'].sum() * 100
            C_SDC_ratio = df['C_SDC'].sum() / df['Crash'].sum() * 100

            # 存储结果
            file_names.append(file_name.strip('.csv'))
            DOUBLE_CRASH_ratios.append(DOUBLE_CRASH_ratio)
            C_MASKED_ratios.append(C_MASKED_ratio)
            C_SDC_ratios.append(C_SDC_ratio)

            print(f"Processed file: {file_name}")
        except:
            print("error in file:\t",file_name)
        # 保存结果到 CSV 文件

    result_df = pd.DataFrame({
        'File Name': file_names,
        'C_MASKED/Crash (%)': C_MASKED_ratios,
        'C_SDC/Crash (%)': C_SDC_ratios,
        'DOUBLE_CRASH/Crash (%)': DOUBLE_CRASH_ratios
    })

    # 输出结果 CSV 文件路径
    csv_output_path = os.path.join(output_dir, 'pic4XappYresultundercrash.csv')
    result_df.to_csv(csv_output_path, index=False)
    print(f"Summary saved to: {csv_output_path}")

    # 绘制柱状图
    x = range(len(file_names))  # 横坐标位置

    plt.figure(figsize=(10, 5))
    bar_width = 0.35  # 柱宽度

    # 绘制堆积柱状图，顺序为：C_MASKED_ratios, C_SDC_ratios, DOUBLE_CRASH_ratios
    plt.bar(x, C_MASKED_ratios, label='C_MASKED/Crash', color='green')
    plt.bar(x, C_SDC_ratios, bottom=C_MASKED_ratios, label='C_SDC/Crash', color='orange')
    plt.bar(x, DOUBLE_CRASH_ratios, bottom=[i + j for i, j in zip(C_MASKED_ratios, C_SDC_ratios)], label='DOUBLE_CRASH/Crash', color='red')

    # 设置纵轴和横轴范围
    plt.ylim(0, 100)  # 纵轴范围固定在0到100
    plt.yticks(range(0, 101, 20), [f'{i}%' for i in range(0, 101, 20)])  # 纵坐标每隔20打一个标注，带百分号

    plt.xticks(x, file_names, rotation=45, ha='right')  # 横坐标为文件名
    #plt.xlabel('File Name')
    plt.ylabel('%')
    plt.title('Crash Ratios: DOUBLE_CRASH, C_MASKED, C_SDC')
    plt.legend()

    
    # 保存图形到指定路径
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"Created directory: {output_dir}")
    output_path = os.path.join(output_dir,'pic4XappYresultundercrash')
    plt.tight_layout()
    plt.savefig(output_path, dpi=600)
    print("pic save in:\t", output_path)
    plt.close()  # 关闭图形以释放内存


def pic2XdynamicexcYcrash(csv_dir, output_dir):
    # 列出文件夹中所有以 .csv 结尾的文件

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
                print(f"File {file_name} does not contain necessary columns. Skipping...")
                continue

            col1 = 'Percentage of Each Category in Total'
            col2 = 'Crash to Masked%'
            col3 = 'Crash to SDC%'
            # 创建一个空的结果表格
            result_table = pd.DataFrame(columns=[func, col1, col2, col3])  # 添加 col3

            # 根据列 'Func' 中的唯一值进行分组计算
            for func_value in df[func].unique():
                if isinstance(func_value, float):
                    continue

                func_group = df[df[func] == func_value]
                total_count = func_group.shape[0]  # 该组的总项数

                # 计算 C_MASKED 的百分比
                c_masked_count = func_group[func_group['result'] == C_MASKED].shape[0]
                c_masked_percentage = (c_masked_count / total_count * 100) if total_count > 0 else 0

                # 计算 C_SDC 的百分比
                c_sdc_count = func_group[func_group['result'] == C_SDC].shape[0]
                c_sdc_percentage = (c_sdc_count / total_count * 100) if total_count > 0 else 0

                # 计算 func 在整个 DataFrame 中的百分比
                total_func_count = df[func].notna().sum()  # 计算列名为 func 的非空行数
                func_percentage = (total_count / total_func_count * 100) if total_func_count > 0 else 0

                # 将计算结果添加到结果表格中，交换列的顺序
                new_row = pd.DataFrame({
                    func: [func_value],
                    col1: [round(func_percentage, 2)],  # 先放 func 的百分比
                    col2: [round(c_masked_percentage, 2)],  # 再放 C_MASKED 的百分比
                    col3: [round(c_sdc_percentage, 2)]  # 最后放 C_SDC 的百分比
                })
                result_table = pd.concat([result_table, new_row], ignore_index=True)

            # 保存结果表格到输出目录
            output_file_path = os.path.join(output_dir, f"FuncCrash_{file_name.replace('.csv', '')}.csv")
            result_table = result_table.sort_values(by=col1, ascending=False)  # 根据新第一列排序
            result_table.to_csv(output_file_path, index=False)
            print(f"Processed and saved summary for file: {file_name}")

        except Exception as e:
            print(f"Error processing file {file_name}: {e}")

        save_three_line_table(result_table, file_name, output_dir, "FuncCrash_")
        plot_grouped_bar_chart(result_table, file_name, output_dir, "FuncCrash_")
        print("\n")



def Tab2SigCrash(csv_dir, sig, output_dir):
    func = sig
    # 确保输出目录存在
    output_dir = os.path.join(output_dir, 'Tab2SigCrash')
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
                print(f"File {file_name} does not contain necessary columns. Skipping...")
                continue

            col1 = 'Percentage of Each Category in Total'  # 先放 func 的百分比
            col2 = 'Crash Recover%'  # 再放 C_MASKED 的百分比
            # 创建一个空的结果表格
            result_table = pd.DataFrame(columns=[func, col1, col2])

            # 根据列 'Func' 中的唯一值进行分组计算
            for func_value in df[func].unique():
                if isinstance(func_value, float):
                    continue

                func_group = df[df[func] == func_value]
                total_count = func_group.shape[0]  # 该组的总项数

                # 计算 Double_Crash 的百分比
                c_masked_count = func_group[func_group['result'] == C_MASKED].shape[0]
                c_masked_percentage = (c_masked_count / total_count * 100) if total_count > 0 else 0

                # 计算 func 在整个 DataFrame 中的百分比
                total_func_count = df[func].notna().sum()  # 计算列名为 func 的非空行数
                func_percentage = (total_count / total_func_count * 100) if total_func_count > 0 else 0

                # 将计算结果添加到结果表格中
                new_row = pd.DataFrame({
                    func: [func_value],
                    col1: [round(func_percentage, 2)],  # 交换列的顺序
                    col2: [round(c_masked_percentage, 2)]
                })
                result_table = pd.concat([result_table, new_row], ignore_index=True)

            # 保存结果表格到输出目录
            output_file_path = os.path.join(output_dir, f"SigCrash_{file_name.replace('.csv', '')}.csv")
            result_table = result_table.sort_values(by=col1, ascending=False)  # 根据新第一列排序
            result_table.to_csv(output_file_path, index=False)
            print(f"Processed and saved summary for file: {file_name}")

        except Exception as e:
            print(f"Error processing file {file_name}: {e}")

        save_three_line_table(result_table, file_name, output_dir, "SigCrash_")
        plot_grouped_bar_chart(result_table, file_name, output_dir, "SigCrash_")




def all(progname):
    print("Read logs and generate csv")
    read_logs(progname)
    search_string_in_log()
    if findmorebypc == 1:
        findins.findinsbyasm(progname)

def main():
    if args.p or args.t:
        if args.p == '1':
            pic1XappYaveragecrash(csv_dir,pic_dir)
        elif args.p == '2':
            pic2XdynamicexcYcrash(csv_dir,pic_dir)
        elif args.p == '3':
            pic3_XdynamicExc_YcontinueIncrash(csv_dir,pic_dir)
        elif args.p == '4':
            pic4XappYresultundercrash(csv_dir,pic_dir)
        if args.t == '1':
            Tab1FuncCrash(csv_dir,'Sig1Func',pic_dir)
        if args.t == '2':
            Tab2SigCrash(csv_dir,'Sig1',pic_dir)
        if args.p == 'all':
            pic1XappYaveragecrash(csv_dir,pic_dir)
            pic2XdynamicexcYcrash(csv_dir,pic_dir)
            pic3_XdynamicExc_YcontinueIncrash(csv_dir,pic_dir)
            pic4XappYresultundercrash(csv_dir,pic_dir)
        if args.t == 'all':
            Tab1FuncCrash(csv_dir,'Sig1Func',pic_dir)
            Tab2SigCrash(csv_dir,'Sig1',pic_dir)
        return

    if args.file and args.flag:##调试单个log
        extract_values_and_append_to_csv(os.path.join(log_dir,str(args.file)),log_dir,args.file+'.csv',args.flag, args.sdc_flag)
        if debug_mode >=6 :
            print("Finish Csv:\t",args.file)
    else:
        # 直接运行的情况
        all(progname)
        if debug_mode >=6 :
            print("Running without file argument.")



if __name__ == "__main__":
    main()
    

    