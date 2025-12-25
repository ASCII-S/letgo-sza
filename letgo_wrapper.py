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
import InstPoolMaker
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
        print("最大的 log 文件是: ",max_file, "后缀数字是: ",max_number)
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


  
    if configure.inject_random_or_targeted == "targeted":
        if not os.path.exists(configure.mnemonic_count_file):
            print("Generating mnemonic_count...")
            mnemonic_count_file = InstPoolMaker.generate_mnemonic_count_file(mnemonic_count_file = configure.mnemonic_count_file)
        if not os.path.exists(configure.catalog_csv_file):
            print("Generating catalog...")
            catalog_path = InstPoolMaker.generate_catalog(catalog_csv_file = configure.catalog_csv_file)
        if not os.path.exists(configure.pool_csv_file) or os.path.getsize(configure.pool_csv_file)==0:
            print("Generating pool...")
            pool_path = InstPoolMaker.generate_Pool_from_catalog(catalog_csv_file=configure.catalog_csv_file, pool_csv_file = configure.pool_csv_file, num_samples=configure.numFI)
            print(f"Pool generated at: {pool_path}")
        else:
            print("Pool already exists, skip generating pool from catalog...")

    # ====== 影响力分析集成 ======
    if hasattr(configure, 'use_influence_analysis') and configure.use_influence_analysis:
        print("\n=== Influence Analysis Mode Enabled ===")

        # 影响力 catalog 和 pool 文件路径
        influence_catalog = os.path.join(configure.one_batch_folder, configure.influence_catalog_name)
        influence_pool = os.path.join(configure.one_batch_folder, configure.influence_pool_name)

        # 检查影响力 catalog 是否存在
        if not os.path.exists(influence_catalog):
            print("Generating influence catalog (data flow + control flow analysis)...")
            InstPoolMaker.generate_influence_catalog(influence_catalog)

        # 检查影响力 pool 是否存在
        if not os.path.exists(influence_pool) or os.path.getsize(influence_pool) == 0:
            print("Generating influence-weighted pool...")
            InstPoolMaker.generate_influence_weighted_pool(
                influence_catalog=influence_catalog,
                pool_file=influence_pool,
                num_samples=configure.numFI,
                weight_mode=configure.influence_weight_mode,
                min_score=configure.min_influence_score,
                exclude_dead=configure.exclude_dead_defs
            )
        else:
            print(f"Influence pool already exists: {influence_pool}")

        # 将影响力 pool 设置为当前使用的 pool
        configure.pool_csv_file = influence_pool
        print(f"Using influence-weighted pool: {configure.pool_csv_file}")
        print("=== Influence Analysis Setup Complete ===\n")

    log_count = 0

    # 检查 log_path 是否存在，不存在则创建并初始化 log_count 为 0
    if not os.path.exists(configure.log_folder):
        os.makedirs(configure.log_folder)
        print(f"Created directory: {configure.log_folder}")
    else:
        # 遍历 log_path 中的文件，统计文件数
        for root, dirs, files in os.walk(configure.log_folder):
            log_count += len(files)

    # 如果 log_count 不为 0，则计算最大日志后缀
    if log_count != 0:
        log_count = find_max_log_suffix(configure.log_folder) + 1
    
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
    for i in range(start,end):    ##从序号log_count开始写记录
        sys.stdout = sys.__stdout__
        print("\n----------------------------Test "+str(i)+"----------------------------")
        #clean up for this round
        silentremove(faultinject.instructionfile)
        silentremove(faultinject.nextpcfile)
        silentremove(configure.activate)
        try:
            print("sig.executeProgram start......")
            print("log:\t",os.path.join(configure.log_folder,'log_'+str(i)))
            sig_time1 = datetime.datetime.now()
            print(sig_time1,flush=True)
            sig = sighandler.SigHandler(totalcount,i)	
            sig.executeProgram(sig.process)
            
            sig_time2 = datetime.datetime.now()
            print("sig.executeProgram end.")
            print(sig_time2,flush = True)
        except KeyboardInterrupt:
            print("Program interrupted by user. Exiting...")
            exit_flag = True  # 设置退出标志

        except SystemExit as e:
            print(f"SystemExit encountered during sig.executeProgram: (exit due to sighandle: timeout) {e}")
            exit_flag = True  # 设置退出标志

        except Exception as e:
            print(f"Error during sig.executeProgram: {e}")
            traceback.print_exc()

        finally:
            if 'exit_flag' in locals() and exit_flag:
                print(f"exit_flag: {exit_flag}")
                sys.exit(0)  # 退出程序
            print(f"Finished processing test {i}, moving to the next test.",flush=True)
            continue
        print("sig time: ",sig_time2 - sig_time1)

    sys.stdout = sys.__stdout__
    print(f"Finish all!!!\tindex start: {start}, index end: {end}")








