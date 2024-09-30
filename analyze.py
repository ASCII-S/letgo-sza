import sys
import os
import re
import configure as cf
import shutil
import pandas as pd
import csv
import findins as fdi
import argparse

#######---------------FOLLOWED ARE SWITCH---------------#########
## clsfy == 1 to move unfinished record to folder "unfinish"
clsfy = 1
## delbug = 1 to delete file that encounters Traceback
delbug = 0
## to_csv =1 will collect all information to csv under log_path,but cost much more time
to_csv = 1
## findins = 1 will auto fix Sig1ins and Sig2ins according to Sig*pc and asm  
findins = 1
## the more debug_mode increase ,the more info been printed
debug_mode = 5
## show file example find by string like "No reg, Exit"
show_ss_example = 0



file_count = 0
crash_1 = []
crash_2 = []
crash_2p = []
finish = []
flag = 0
unfinishedlist = []
output = []

log_dir = os.path.join(cf.progname)
print(log_dir)
if not (os.path.exists(log_dir) and os.path.isdir(log_dir)):
    print("{} does not exist or is not a directory".format(log_dir))
    exit(0)


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

def next_i_line_content(file,i):
    while i>0:
        try:
            next_line = next(file).strip()  # 获取下一行
            #print("Next line:", next_line)
            i -= 1
        except StopIteration:
            # 如果到达文件末尾，则停止获取下一行
            #print("Reached end of file.")
            #print(next(file).strip())
            return 'null'
    return next_line

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

    

def ss():
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


def ana1(progname):
    global file_count, crash_1, crash_2, crash_2p, finish, flag, detected, correct, sdc, unfinishedlist, output
    
    if to_csv == 1:
        csv_file_path = os.path.join(log_dir,"../CSV", progname+'.csv')
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
            continue
        f = os.path.join(log_dir,f)
        flag = 0
        with open(f,"r",encoding='utf-8', errors='ignore') as log:
            unfinished = 0
            lines = log.readlines()
            
            for line in lines:
                if "Traceback" in line:
                    print("Bug in:\t",f)
                    if delbug == 1:
                        os.remove(f)  # 删除文件
                        print("delete:\t",f)
                if "Program received signal" in line:
                    flag += 1
                if "1 tests completed and failed residual checks" in line:
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
            extract_values_and_append_to_csv(f, log_dir, progname+'.csv', flag)

    print("crash1:\t",len(crash_1)) ##只收到一次越界错误segmentfault
    print("crash2:\t",len(crash_2)) ##收到两次越界错误
    print("no crash finish:\t",len(finish))  ##一次错误都没有,直接结束
    ############
    #print("sdc:\t",len(sdc))
    #print("detected:\t",len(detected))
    print("file count:",file_count)
    print("unfinishedlist:",len(unfinishedlist))
    print("valid countL",file_count-len(unfinishedlist))
    """print(len(list(set(crash_1).difference((set(crash_1) & set(correct))))))
    #print list(set(set(crash_1).difference((set(crash_1) & set(correct)))).difference(set(sdc)))
    print("### sdc -> detected")
    print(len(list(set(sdc).difference(set(detected)))))
    print(len(list(set(detected).difference(set(sdc)))))
    print("#### crash and detected")
    print(len(list(set(crash_1) & set(detected))))
    print("#### crash and sdc")
    print(len(list(set(crash_1) & set(sdc))))
    #print((list(set(crash_1) & set(sdc))))
    #print list(set(crash_2) & set(correct))"""
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


def extract_values_and_append_to_csv(input_file, log_dir, outputname, flag):
    if debug_mode >=6:
        print("\nnow do extract_values_and_append_to_csv")
    # 创建 CSV 文件保存的目录
    output_dir = os.path.join(log_dir, '../CSV')
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)  # 如果目录不存在则创建

    # 创建一个空的 DataFrame
    df = pd.DataFrame(columns=['input_file', 'regmm','reg', 'injreg', 'pc', 'iteration1','hexpc', 'ins', 'opcode', 'func', 'result', 'Sig1','Sig1pc','Sig1Ins','Sig1Ope','ErrSpd_Inj', 'Sig2','Sig2pc','Sig2Ins','Sig2Ope','ErrSpd_Fix' ])
    
    if flag == 0:
        df.loc[0,'result'] = 'masked'
    elif flag == 1:
        df.loc[0,'result'] = 'crash1'
    elif flag == 2:
        df.loc[0,'result'] = 'crash2'
    else:
        df.loc[0,'result'] = 'crash2+'
    # 获取文件名
    file_name = os.path.basename(input_file)

    # 读取文件并提取所需内容
    with open(input_file, 'r') as file:
        values = ['null'] * 4
        SIGcount = 0
        Sig1byletgo_Flag = 0

        for line in file:
            if "args" in line:
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
                    df.loc[0,'pc'] = values[2]
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
                continue

            if "start inject a fault" in line:
                next_3_line = next_i_line_content(file,3)
                #print(next_3_line)
                # 提取指令和函数名
                ins = ""
                func = ""
                # 查找指令和函数名
                parts = next_3_line.split(':')
                #print (parts)
                if len(parts) > 1:
                    # 提取指令
                    ins = parts[-1].strip(' ')  # 冒号后面的内容，去除多余空格
                    if ins == '':
                        ins = next_i_line_content(file,1).split('#')[0].rstrip()
                        #print(ins)
                    opcode = ins.split(' ')[0]
                    # 提取函数名
                    func_part = parts[0].split('<')[1]  # 获取尖括号内容
                    func = func_part.split('+')[0]  # 提取函数名，不包括+部分
                
                #print (ins,func)
                # 将提取到的值添加到 DataFrame 中
                df.loc[0,'ins'] = ins 
                df.loc[0,'opcode'] = opcode
                df.loc[0,'func'] = func
                df.loc[0,'input_file'] = file_name
                
                #df.loc[len(df)] = values + [ins, func, file_name]  # 合并值和新提取的字段
                continue
            
            #首次遇到SIG
            if "received signal" in line and SIGcount == 0 and df.loc[0,'result'] != 'masked':  
                tmp = line.split(',')[0]
                tmp = tmp.split('signal')[1]
                df.loc[0,'Sig1'] = tmp
                df.loc[0,'Sig1pc'] = '0x'+next_i_line_content(file,1).split(' ')[0][-6:].strip('\n').strip(' ')
                try:
                    if not is_valid_hex_address(str(df.loc[0,'Sig1pc'])[2:]):
                        df.loc[0,'Sig1pc'] = 'null'
                        Sig1byletgo_Flag = 1
                        continue
                except:
                    print("error Sig1pc",df.loc[0,'Sig1pc'],input_file)
                    df.loc[0,'Sig1pc'] = 'null'
                    Sig1byletgo_Flag = 1
                
                """nexl = next_i_line_content(file,3)
                if "=>" in nexl:
                    nexl = nexl.split('#')[0].rstrip()
                    df.loc[0,'Sig1Ins'] = nexl.split(':')[-1]
                    df.loc[0,'Sig1Ope'] = str(df.loc[0,'Sig1Ins']).split(' ')[0]"""
                SIGcount += 1
                continue

            if Sig1byletgo_Flag == 1 and 'Letgo in!' in line:
                tmp = next_i_line_content(file,3)
                tmp = tmp.split('0x')[-1][:6]
                try:
                    if is_valid_hex_address(tmp):
                        df.loc[0,'Sig1pc'] = '0x' + tmp.strip(' ')
                        SIGcount += 1
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
            if "received signal" in line and SIGcount == 1 and (df.loc[0,'result'] == 'crash2' or df.loc[0,'result'] == 'crash2+'):  
                tmp = line.split(',')[0]
                tmp = tmp.split('signal')[1]
                df.loc[0,'Sig2'] = tmp
                #print(df.loc[0,'Sig2pc'])
                near_number = 7
                while near_number >0 :
                    nexl = ''
                    if "=>" in nexl:
                        df.loc[0,'Sig2pc'] = (nexl.split(':')[0]).split('=>')[1].strip(' ').strip('\n')[:8]
                        if debug_mode >= 6:
                            print ("Sig2pc by near:\t",df.loc[0,'Sig2pc'])
                        break

                    nexl = next_i_line_content(file,1)
                    near_number -= 1
                    if nexl == 'null' or "0x0000000000" in nexl:  ##表明最后一行是接收到信号的内容
                        try:
                            df.loc[0,'Sig2pc'] = '0x'+line.split('0x0000000000')[1][:6]
                        except:
                            if debug_mode >= 6:
                                print("Sig2 can not find pc! :",input_file)
                            break
                    
                

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


def all():
    ana1(cf.progname)
    ss()
    if findins == 1:
        fdi.findinsbyasm(cf.progname)

def main():
    parser = argparse.ArgumentParser(description="Analyze log files.")
    parser.add_argument('-file', type=str, help='Log file to process,benchmark according to configure.py')
    parser.add_argument('-flag', type=str, help='flag means the number of Sig received')

    args = parser.parse_args()

    if args.file and args.flag:
        extract_values_and_append_to_csv(os.path.join(log_dir,str(args.file)),log_dir,args.file+'.csv',args.flag)
        if debug_mode >=6 :
            print("Finish EV&ACsv:\t",args.file)
    else:
        # 直接运行的情况
        all()
        if debug_mode >=6 :
            print("Running without file argument.")


if __name__ == "__main__":
    main()
    

    