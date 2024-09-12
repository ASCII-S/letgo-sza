import sys
import os
import re
import configure as cf
crash_1 = []
crash_2 = []
finish = []
flag = 0
detected = []
correct = []
sdc = []
unfinishedlist = []
output = []
checkingstring = 'Problem size        =  5'
#checkingstring1 = 'Iteration count     =  306'
checkingstring1 = 'Iteration count     =  306'
#checkingstring2 = 'Final Origin Energy = 1.670602e+05'
checkingstring2 = 'Final Origin Energy = 1.670602e+05'
#checkingstring3 = 'MaxAbsDiff   = 2.546585e-11'
checkingstring3 = 'MaxAbsDiff   = 2.546585e-11'
#checkingstring4 = 'TotalAbsDiff = 6.230039e-11'
checkingstring4 = 'TotalAbsDiff = 6.230039e-11'
#checkingstring5 = 'MaxRelDiff   = 2.178209e-15'
checkingstring5 = 'MaxRelDiff   = 2.178209e-15'
#basedir = "/data/pwu/LULESH3"

#log_dir = "./lu"
log_dir = os.path.join(cf.progname)
print(log_dir)
if not (os.path.exists(log_dir) and os.path.isdir(log_dir)):
    print("{} does not exist or is not a directory".format(log_dir))
    exit(0)

for f in os.listdir(log_dir):
    #print f
    if ".py" in f:
        continue
    if "log_" not in f:
        continue
    f = os.path.join(log_dir,f)
    with open(f,"r",encoding='utf-8', errors='ignore') as log:
       flag_sdc = -1000
       flag_output = -1000  ##默认程序没有结果输出
       unfinished = 0
       lines = log.readlines()
       flag = 0
       for line in lines:
          if "Traceback" in line:
            print("Bug in:\t",f)
          if "received" in line and "Segmentation fault" in line:
              flag += 1
          if "Application output" in line:
              flag_sdc = 0
              flag_output = 0
          if flag_output != -1000 and flag_sdc != -1000 :
              if checkingstring in line:
                  flag_output += 1
                  flag_sdc+= 1
              if checkingstring1 in line:
                  flag_output += 1
                  flag_sdc += 1
                #print line
              if checkingstring2 in line:
                  flag_output += 1
                  flag_sdc += 1
              if checkingstring3 in line:
                  flag_output += 1
              if checkingstring4 in line:
                  flag_output += 1
              if checkingstring5 in line:
                  flag_output += 1
              #print line
              #print flag_sdc
              if 'Diff' in line:
                  if 'e-' not in line:
                      flag_sdc -= 1
                      continue
                  parser = line.split('e-')[1]
                  res = re.findall('\d+', parser)
                  if len(res) > 0:
                    #pre = parser.split('-')[1]
                      if int(res[0]) >= 8:
                        #print line
                          flag_sdc += 1
                          #print line
                          #print flag_sdc
       #print flag_sdc
          if "Exit" in line:
              unfinished = 1
          if "Error" in line:
              unfinished = 1
          if "Cannot insert breakpoint" in line:
              unfinished = 1
       if unfinished == 1:
           unfinishedlist.append(f)
           continue
       if flag_output < 6 and flag_output != -1000: ##程序有输出
           sdc.append(f)
       if flag_sdc < 5 and flag_sdc != -1000:
              detected.append(f)
       if flag_output == 6:
           correct.append(f)     
           
       if flag == 1:
           crash_1.append(f)
       if flag == 2:
           crash_2.append(f)
       if flag == 0:
           finish.append(f)
       #break


print("crash1:\t",len(crash_1)) ##只收到一次越界错误segmentfault
print("crash2:\t",len(crash_2)) ##收到两次越界错误
print("finish:\t",len(finish))  ##一次错误都没有,直接结束
############
print("sdc:\t",len(sdc))
print("detected:\t",len(detected))
print("unfinishedlist:",len(unfinishedlist))
print(len(list(set(crash_1).difference((set(crash_1) & set(correct))))))
#print list(set(set(crash_1).difference((set(crash_1) & set(correct)))).difference(set(sdc)))
print("### sdc -> detected")
print(len(list(set(sdc).difference(set(detected)))))
print(len(list(set(detected).difference(set(sdc)))))
print("#### crash and detected")
print(len(list(set(crash_1) & set(detected))))
print("#### crash and sdc")
print(len(list(set(crash_1) & set(sdc))))
#print((list(set(crash_1) & set(sdc))))
#print list(set(crash_2) & set(correct))
n = 5
print("crash1:\t",crash_1[:n])
print("crash2:\t",crash_2[:n])
print("sdc:\t",sdc[:n])
#print(detected[:n])
print("finish:\t",finish[:n]) 
print("unfinishedlist:",unfinishedlist[:n])
#print(list(set(crash_1).difference((set(crash_1) & set(correct))))[:n])

def ss():
    ##下面统计文本

    # 定义要查找的字符串
    search_strings = [
        "set reg with address calculation",
        "set reg with fake",
        "Cannot get the size of the current stack frame",
        "set rbp and rsp to reasonable values",
        "received signal SIGSEGV, Segmentation fault.",
        "received signal SIGBUS",
        "received signal SIGABRT",
        "Error",
        "Cannot insert breakpoint",
        "No reg"
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

    # 将结果按计数排序
    sorted_results = sorted(counted_results.items(), key=lambda item: item[1], reverse=True)

    # 输出前几项结果
    top_n = len(search_strings)  # 设置你想要输出的前几项
    for i, (string, count) in enumerate(sorted_results[:top_n], 1):
        print("{}. '{}' found in {} files".format(i, string, count))


    # 如果你还需要显示具体的文件名，可以按以下方式输出
    for string, filenames in results.items():
        print("\nFiles containing '{}':".format(string))
        top_n = 3
        for filename in set(filenames):
            if top_n <=0 :
                break
            print("- {}".format(filename))
            top_n -=1

ss()