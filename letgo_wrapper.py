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
    except OSError as e: # this would be "except OSError, e:" before Python 2.6
        if e.errno != errno.ENOENT: # errno.ENOENT = no such file or directory
            raise # re-raise exception if a different error occured


instcount = configure.pin_base+"/source/tools/ManualExamples/obj-intel64/inscount0.so"

execlist = [configure.pin_home,"-t",instcount,"--",configure.benchmark]

for item in configure.args:
    execlist.append(item)


out = "sampleout"
err = "sampleerr"

execute(execlist,out,err)

if not os.path.isfile(instcount):
    print("No instcount file! Exit")
    sys.exit(1)

totalcount = ""
with open(configure.instcount,"r") as f:
    lines = f.readlines()
    if len(lines) > 1:
        print("Error while loading inst count.")
        sys.exit(1)
    count = lines[0]
    count = count.rstrip("\n")
    print(count)
    totalcount = count.split(" ")[1]

log_count = 0
"""for root, dirs, files in os.walk(sighandler.log_path):
    log_count += len(files)
    #print(log_count,"\tlogs in ./log")
    #exit(0)"""
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

log_count = 0
for root, dirs, files in os.walk(sighandler.log_path):
    # 统计文件数
    log_count += len(files)
if log_count != 0:
    log_count = find_max_log_suffix(sighandler.log_path) + 1

for i in range(log_count,log_count+configure.numFI):    ##从序号log_count开始写记录
    sys.stdout = sys.__stdout__
    print("\n----------------------------Test "+str(i)+"----------------------------")
    try:
        os.remove("x.asc")
        print("remove output file 3")
    except:
        print("Oops, no x.asc file found. Ignoring. 3")
    try:
        print("sig.executeProgram start......")
        sig_time1 = datetime.datetime.now()
        print(sig_time1)
        sig = sighandler.SigHandler(totalcount,i)	
        sig.executeProgram()
        sig_time2 = datetime.datetime.now()
        print(sig_time2)
    except SystemExit as e:
        print(f"SystemExit encountered during sig.executeProgram: (exit due to sighandle: timeout){e}")
        continue  # continue to the next iteration
    except Exception as e:
        print(f"Error during sig.executeProgram: {e}")
        traceback.print_exc()
        continue
    print("sig time: ",sig_time2 - sig_time1)
    #clean up for next round
    #silentremove(faultinject.instructionfile)
    #silentremove(faultinject.iterationfile)
    #silentremove(faultinject.nextpcfile)
    ## add trial number to the output file 
    try:
        os.rename("x.asc", "x.asc-" + str(i))
    except:
        print("Oops, no x.vec file found. Ignoring.")







