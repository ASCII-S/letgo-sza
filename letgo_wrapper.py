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


def run_command(command):
    """
    运行命令行并返回输出结果。

    参数:
        command (list): 要执行的命令行，以列表形式传入，例如 ["python3.8", "../analyze.py"]。

    返回:
        dict: 包含标准输出、标准错误和返回码的字典。
    """
    try:
        # 执行命令
        result = subprocess.run(
            command,                     # 命令及参数
            check=True,                  # 如果命令返回非零值，抛出 CalledProcessError
            text=True,                   # 输出解码为字符串
            capture_output=True          # 捕获标准输出和标准错误
        )
        
        # 返回成功结果
        return {
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
            "returncode": result.returncode,
        }

    except subprocess.CalledProcessError as e:
        # 捕获命令失败的异常
        return {
            "stdout": e.stdout.strip() if e.stdout else "",
            "stderr": e.stderr.strip() if e.stderr else "",
            "returncode": e.returncode,
            "error": f"Command failed with return code {e.returncode}",
        }

    except Exception as e:
        # 捕获其他异常
        return {
            "stdout": "",
            "stderr": "",
            "returncode": -1,
            "error": f"An unexpected error occurred: {e}",
        }


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
    execlist = []
    if configure.MPI_SET == 1:
        execlist.extend(configure.mpi_cmd)
    
    pin_benchmark = [configure.pin_home,"-t",instcount,'-o',configure.pin_instcount,"--",configure.benchmark]
    execlist.extend(pin_benchmark)

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
    
    start = log_count
    end = log_count + configure.numFI
    if configure.num_end_at < end :
        end = configure.num_end_at
    print(f"index start: {start}, index end: {end}")
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
    
    # 实验完成自动分析
    sys.stdout = sys.__stdout__
    command = ["python3.8",os.path.join(configure.letgo_base_home,"sdcjudger.py")]
    result = run_command(command)
    print(result.get("stdout","No sdcout"))

    command = ["python3.8",os.path.join(configure.letgo_base_home,"analyze.py"),"-bname",configure.progname]
    result = run_command(command)
    print(result.get("stdout","No analyze output"))








