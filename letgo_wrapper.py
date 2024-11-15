import sys
import os, errno
import sighandler
import faultinject
import configure
import subprocess
import time
import datetime
import traceback
import re
import argparse

timeout = 500


#obtain the total number of dynamic instructions

def execute(execlist,out,err):

        outFile = open(out,"w")
        errFile = open(err,"w")
        print(' '.join(execlist))
        p = subprocess.Popen(execlist, stdout=outFile,stderr=errFile)
        elapsetime = 0
        while (elapsetime < timeout):
            elapsetime += 1
            time.sleep(1)
            #print p.poll()
            if p.poll() is not None:
                print("\t program finish", p.returncode)
                print("\t time taken", elapsetime)
                return str(p.returncode)
        outFile.close()
        errFile.close()
        print("\tParent : Child timed out. Cleaning up ... ")
        p.kill()
        return "timed-out"


def silentremove(filename):
    try:
        os.remove(filename)
        print("remove:\t", filename)
    except FileNotFoundError:
        # 文件不存在时，忽略
        pass
    except OSError as e:
        # 处理其他类型的 OSError 错误，重新抛出异常
        if e.errno != errno.ENOENT:  # 如果是其他的错误，则重新抛出
            raise


def find_max_log_suffix(directory):
    # 初始化最大值
    max_number = -1
    max_file = None
    
    # 定义匹配以 "log_" 开头，后面跟数字的正则表达式
    pattern = re.compile(r"log_(\d+)")
    
    # 遍历指定文件夹中的所有文件
    for filename in os.listdir(directory):
        # 使用正则表达式匹配文件名
        match = pattern.match(filename)
        if match:
            # 提取匹配的数字部分
            number = int(match.group(1))
            # 如果找到更大的数字，更新最大值和对应的文件名
            if number > max_number:
                max_number = number
                max_file = filename
    
    if max_file:
        print("最大的 log 文件是: ",max_file, "后缀数字是: ","max_number")
        return max_number
    else:
        print("没有找到符合条件的文件。")
        return None


def find_max_log_suffix(directory):
    # 初始化最大值
    max_number = -1
    max_file = None
    
    # 定义匹配以 "log_" 开头，后面跟数字的正则表达式
    pattern = re.compile(r"log_(\d+)")
    
    # 遍历指定文件夹中的所有文件
    for filename in os.listdir(directory):
        # 使用正则表达式匹配文件名
        match = pattern.match(filename)
        if match:
            # 提取匹配的数字部分
            number = int(match.group(1))
            # 如果找到更大的数字，更新最大值和对应的文件名
            if number > max_number:
                max_number = number
                max_file = filename
    
    if max_file:
        print(f"最大的 log 文件是: {max_file}, 后缀数字是: {max_number},所在地址是: {directory}")
        return max_number
    else:
        print("没有找到符合条件的文件。")
        return None


if __name__ == "__main__":
    # 传入参数
    parser = argparse.ArgumentParser(description="Set log_count.")
    parser.add_argument('-si', type=int, help='Set start log_count', default=0)
    args = parser.parse_args()

    instcount = configure.toolbase + "/obj-intel64/instcount.so"
    print (instcount)
    execlist = [configure.pin_home,"-t",instcount,'-o',configure.pin_instcount,"--",configure.benchmark]

    for item in configure.args:
        execlist.append(item)


    out = "sampleout"
    err = "sampleerr"

    execute(execlist,out,err)

    if not os.path.isfile(instcount):
        print("No instcount.so file! Exit")
        sys.exit(1)

    totalcount = ""
    # with open(configure.instcount,"r") as f:
    #     lines = f.readlines()
    #     if len(lines) > 1:
    #         print("Error while loading inst count.")
    #         sys.exit(1)
    #     count = lines[0]
    #     count = count.rstrip("\n")
    #     totalcount = count.split(" ")[1]
    #     print("Instcount:\t",totalcount)
    file_path = configure.instcount
    try:
        with open(file_path, 'r') as f:
            first_line = f.readline()  # 读取第一行
            if ':' in first_line:
                totalcount = first_line.split(':')[1].strip()  # 提取冒号后的数字并去除空白字符
                print(f"Instcount:\t{totalcount}")
            else:
                print("No colon found in the first line.")
    except FileNotFoundError:
        print(f"File {file_path} not found.")
    except Exception as e:
        print(f"An error occurred: {e}")

    log_count = 0

    # 检查 log_path 是否存在，不存在则创建并初始化 log_count 为 0
    if not os.path.exists(configure.log_path):
        os.makedirs(configure.log_path)
        print(f"Created directory: {configure.log_path}")
    else:
        # 遍历 log_path 中的文件，统计文件数
        for root, dirs, files in os.walk(configure.log_path):
            log_count += len(files)

    # 如果 log_count 不为 0，则计算最大日志后缀
    if log_count != 0:
        log_count = find_max_log_suffix(configure.log_path) + 1
    
    if configure.num_start_from >  log_count:
        log_count = configure.num_start_from
        print("due to configure.num_start_from")
        print("log start from:\t",'log_'+str(log_count))

    if args.si and args.si > log_count:
        log_count = args.si
        print("log start from:\t",'log_'+str(args.si))

    print(f"log_count: {log_count}, numFI: {configure.numFI}")
    for i in range(log_count,log_count+configure.numFI):    ##从序号log_count开始写记录
        sys.stdout = sys.__stdout__
        print("\n----------------------------Test "+str(i)+"----------------------------")
        #clean up for this round
        silentremove(faultinject.instructionfile)
        silentremove(faultinject.nextpcfile)
        silentremove(configure.activate)
        try:
            print("sig.executeProgram start......")
            print("log:\t",os.path.join(configure.log_path,'log_'+str(i)))
            sig_time1 = datetime.datetime.now()
            print(sig_time1)

            sig = sighandler.SigHandler(totalcount,i)	
            sig.executeProgram(sig.process)
            
            sig_time2 = datetime.datetime.now()
            print("sig.executeProgram end.")
            print(sig_time2)
        except KeyboardInterrupt:
            print("Program interrupted by user. Exiting...")
            exit_flag = True  # 设置退出标志

        except SystemExit as e:
            print(f"SystemExit encountered during sig.executeProgram: (exit due to sighandle: timeout) {e}")

        except Exception as e:
            print(f"Error during sig.executeProgram: {e}")
            traceback.print_exc()

        finally:
            if 'exit_flag' in locals() and exit_flag:
                print(f"exit_flag: {exit_flag}")
                sys.exit(0)  # 退出程序
            print(f"Finished processing test {i}, moving to the next test.")
            continue
        print("sig time: ",sig_time2 - sig_time1)







