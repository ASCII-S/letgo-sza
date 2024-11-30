import os
import numpy as np
import shutil
import filecmp
import contextlib
import configure
import re
import sys
import pandas as pd

class LU_SDC_Judger:
    def __init__(self, lu_file, m_file, tolerance=configure.lu_tolerance):
        # 加载矩阵文件并获取矩阵维度
        self.lu_matrix = self.load_matrix(lu_file)
        self.m_matrix = self.load_matrix(m_file)
        self.matrix_dim = self.extract_matrix_dim(m_file)
        self.tolerance = tolerance  # 误差容忍度

    def extract_matrix_dim(self, file_name):
        # 从文件名中提取矩阵维度
        match = re.search(r'_(\d+)\.txt$', file_name)
        return int(match.group(1)) if match else None

    def load_matrix(self, file_path):
        # 读取矩阵文件
        return np.loadtxt(file_path)

    def calculate_lu_product(self):
        dim = self.matrix_dim
        if dim is None:
            raise ValueError("Matrix dimension could not be determined.")
        
        tmp = np.zeros((dim, dim))
        for i in range(dim):
            for j in range(dim):
                sum_val = 0.0
                for k in range(min(i, j) + 1):
                    l = 1.0 if i == k else self.lu_matrix[i, k]
                    u = self.lu_matrix[k, j]
                    sum_val += l * u
                tmp[i, j] = sum_val
        return tmp

    def compare_with_original(self):
        # 计算L*U并与原始矩阵比较
        lu_product = self.calculate_lu_product()
        comparison = np.allclose(lu_product, self.m_matrix, atol=self.tolerance)
        print("L*U equals M within tolerance(",self.tolerance,'):\t' , comparison)

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


def Add_SDC_result_to_alllog_LU(log_path=configure.log_folder, sdcout_folder=configure.sdcout_folder, tolerance=configure.lu_tolerance):
    len = find_max_log_suffix(log_path)
    for index in range(len):
        log_index_file = os.path.join(log_path, f'log_{index}')
        this_output = os.path.join(sdcout_folder, f'log_{index}_lu_matrix_512.txt')
        golden_output = os.path.join(configure.Rodinia_base,"/openmp/lud", 'm_matrix_512.txt')
        
        # 检查文件是否存在
        if not os.path.exists(this_output) or not os.path.exists(golden_output):
            continue
        
        # 判断是否已经对该log_index进行了判断
        with open(log_index_file, 'r') as f:
            content = f.read()
            if "L*U equals M within tolerance( "+str(configure.lu_tolerance)+' )' in content or "No nextpc" in content:
                print("skip:\t",index)
                continue
        
        # 重定向输出到 log_index_file
        with open(log_index_file, 'a') as log_file:
            with contextlib.redirect_stdout(log_file):
                # 创建判断对象并进行比较
                judger = LU_SDC_Judger(this_output, golden_output, tolerance)
                judger.compare_with_original()
        print('log_'+str(index)+'\n')


def Add_SDC_result_to_alllog_common(log_path=configure.log_folder, sdcout_folder=configure.sdcout_folder, tolerance=configure.tolerance):
    len = find_max_log_suffix(log_path)

    in_path = configure.progname + '/' + configure.output_name

    golden_output = os.path.join(configure.Rodinia_base, "results", in_path)
    if configure.progname == 'hotspot':
        golden_output = "/home/tongshiyu/programs/rodinia-master/openmp/hotspot/output.txt"
    if configure.progname == 'miniMD':
        golden_output = "/home/tongshiyu/programs/mantevo/miniMD/ref/output.txt"
    if configure.progname == 'miniFE':
        golden_output = "/home/tongshiyu/programs/mantevo/miniFE/openmp/basic/output.txt"
    if configure.progname == 'HPCCG':
        golden_output = "/home/tongshiyu/programs/mantevo/HPCCG/output.txt"
    if configure.progname == 'nn':
        golden_output = "/home/tongshiyu/programs/rodinia-master/openmp/nn/output.txt"
    if configure.progname == 'kmeans':
        golden_output = "/home/tongshiyu/programs/rodinia-master/openmp/kmeans/output.txt"
    if configure.progname == 'particlefilter':
        golden_output = "/home/tongshiyu/programs/rodinia-master/openmp/particlefilter/output.txt"

    
    for index in range(len+1):
        
        log_index_file = os.path.join(log_path, f'log_{index}')
        this_output = os.path.join(sdcout_folder, f'log_{index}_{configure.output_name}')
        if configure.output_name == 'none':
            this_output = log_index_file
        # 检查文件是否存在
        if not os.path.exists(this_output) or not os.path.exists(golden_output) or not os.path.exists(log_index_file):
            if not configure.output_name == 'none':
                continue
        
        # 判断是否已经对该log_index进行了判断
        with open(log_index_file, 'r') as f:
            content = f.read()
            if configure.cmp_str in content or "No nextpc" in content or "application generate no output" in content:
                #print("skip:\t",index)
                continue
        fail = 0
        # 重定向输出到 log_index_file
        with open(log_index_file, 'a') as log_file:
            with contextlib.redirect_stdout(log_file):
            #with contextlib.redirect_stdout(sys.__stdout__):
                # 创建判断对象并进行比较
                try:
                    if configure.progname in ['bfs','backprop','nn',"kmeans","particlefilter"]:
                        strong_compare_outputs(this_output,golden_output)
                    elif configure.progname == 'hotspot':
                        hotspot_compare_outputs(this_output, golden_output, tolerance)
                    elif configure.progname == 'miniMD':
                        miniMD_compare_outputs(this_output, golden_output, tolerance)
                    elif configure.progname == 'miniFE':
                        miniFE_compare_outputs(this_output, golden_output, tolerance)
                    elif configure.progname == 'HPCCG':
                        HPCCG_compare_outputs(this_output, golden_output, tolerance)
                    else:
                        common_compare_outputs(this_output, golden_output, tolerance)
                except Exception as e:
                    fail = 1
                    print("fail:\t",e)
                # print(log_index_file)
                # print(this_output)
                # print(golden_output)
                # sys.exit(1) 
        if fail == 1:
            print("fail in:\t"+'log_'+str(index)+'\n')
    print(configure.progname,":\tadd sdc result from log_0 to ",'log_'+str(index)+'\n')

def Init():
    progname = configure.progname
    if progname in configure.OpenMpOutPutList:
        in_path = progname + '/' + configure.output_name
        golden_output_path = os.path.join(configure.Rodinia_base, "results", in_path)
    if progname == 'lu':
        m_output_name = 'm_matrix_512.txt'
        golden_output_path = os.path.join('./' 'm_matrix_512.txt')

    this_output_path = os.path.join('./',configure.output_name)

    return this_output_path,golden_output_path

def move_this_output(output_path,save_dir,index):
    # 构造新的文件名
    log_name = f"log_{index}"
    output_filename = os.path.basename(output_path)
    new_file_name = log_name + '_' + output_filename
    # 确保目标目录存在
    os.makedirs(save_dir, exist_ok=True)
    
    # 构造源文件路径和目标文件路径
    src_file_path = output_path
    dest_file_path = os.path.join(save_dir, new_file_name)
    
    # 移动并重命名文件
    try:
        shutil.move(src_file_path, dest_file_path)
        print(f"File renamed to {new_file_name} and moved to {save_dir}")
    except FileNotFoundError:
        print(f"File {output_path} not found.")
    except Exception as e:
        print(f"An error occurred: {e}")
    return dest_file_path


def read_binary_file(filename, dtype=np.float32):
    """读取二进制文件并返回 NumPy 数组"""
    with open(filename, 'rb') as f:
        return np.fromfile(f, dtype=dtype)

def strong_compare_outputs(this_output, golden_output):
    # 使用 filecmp.cmp() 比较两个文件
    if filecmp.cmp(this_output, golden_output, shallow=False):
        print("Compare within tolerance(0.0): True")
        return 0
    else:
        print("Compare within tolerance(0.0): False")
        return 1

def clean_non_numeric(data):
    """ 提取数据中的数字部分并返回。删除非数字字符。"""
    cleaned_data = []
    for item in data:
        # 使用正则表达式去掉非数字字符，只保留有效的数字部分
        cleaned_item = re.sub(r'[^0-9\.]', '', item)  # 保留数字和小数点
        if cleaned_item:
            try:
                cleaned_data.append(float(cleaned_item))
            except ValueError:
                pass  # 如果无法转换为浮动类型，忽略该项
    return cleaned_data

def hotspot_compare_outputs(this_output_path, golden_output_path, tolerance):
    """
    Compare two files' data to check if they are within a specified tolerance, and print results in a specific format.
    
    :param this_output_path: File path containing this_output data.
    :param golden_output_path: File path containing golden_output data.
    :param tolerance: Allowed tolerance range.
    :param cmp_str: Prefix string for output messages.
    :return: 0 if all data are within tolerance, 1 if any data exceed the tolerance.
    """
    try:
        cmp_str = configure.cmp_str
        # Read data
        try:
            this_output = pd.read_csv(this_output_path, sep="\t", header=None, names=["Index", "Value"])
            golden_output = pd.read_csv(golden_output_path, sep="\t", header=None, names=["Index", "Value"])
        except:
            print("application generate no output")
            return 1
        # Check if the structures of the two files match
        if this_output.shape != golden_output.shape:
            print(cmp_str + "False (Shape mismatch)")
            return 1

        # Iterate through each row and compare values
        for index, (this_num, golden_num) in enumerate(zip(this_output["Value"], golden_output["Value"])):
            if abs(this_num - golden_num) > tolerance:
                print(cmp_str + "False")
                return 1

        # If all rows are within tolerance
        print(cmp_str + "True")
        return 0

    except Exception as e:
        print(cmp_str + f"Error occurred: {e}")
        return 1

def bfs_compare_outputs(this_output, golden_output, tolerance=configure.tolerance):
    try:
        # 使用 dtype=str 来读取所有内容为字符串
        this_data = np.genfromtxt(this_output, dtype=str, delimiter=None)
        golden_data = np.genfromtxt(golden_output, dtype=str, delimiter=None)
    except Exception as e:
        print("application generate no output")
        return 1

    # 比较行数
    if this_data.shape[0] != golden_data.shape[0]:
        print("application generate no output")
        return 1

    # 对每一行进行比较
    for i in range(this_data.shape[0]):
        try:
            # 提取每一行的数字部分
            this_row_data = clean_non_numeric(this_data[i])
            golden_row_data = clean_non_numeric(golden_data[i])
        except ValueError:
            print(f"Error processing row {i}: {this_data[i]} vs {golden_data[i]}")
            return 1

        # 如果数字元素数量不一致，打印警告并返回错误
        if len(this_row_data) != len(golden_row_data):
            print(f"Mismatch in number of elements in row {i}: {this_row_data} vs {golden_row_data}")
            return 1

        # 对每一对数字进行比较，检查差异是否在容忍度范围内
        for this_num, golden_num in zip(this_row_data, golden_row_data):
            if abs(this_num - golden_num) > tolerance:
                print(configure.cmp_str+"False")
                return 1

    # 如果所有行都匹配
    print(configure.cmp_str+"True")
    return 0

def miniMD_compare_outputs(this_output_path, golden_output_path, tolerance):
    """
    Compare two files' specific rows' values to check if they are within a specified tolerance, 
    focusing on the two rows of data after the '# Timestep T U P Time' header and excluding the 'Time' column.

    :param this_output_path: File path containing this_output data.
    :param golden_output_path: File path containing golden_output data.
    :param tolerance: Allowed tolerance range.
    :return: 0 if the data are within tolerance, 1 otherwise.
    """
    cmp_str = configure.cmp_str  # Custom comparison string
    try:
        # Read both files into lists of lines
        with open(this_output_path, 'r') as f1, open(golden_output_path, 'r') as f2:
            this_lines = f1.readlines()
            golden_lines = f2.readlines()
            
        # Check if this_output contains "# Timestep T U P"
        if not any("# Timestep T U P Time" in line for line in this_lines):
            print("application generate no output")
            return 1

        # Locate the header and extract the two rows following it
        try:
            header_index = this_lines.index("# Timestep T U P Time\n")
        except ValueError:
            print(this_output_path)
            print("application generate error output")
            return 1
        try:
            golden_header_index = golden_lines.index("# Timestep T U P Time\n")
        except ValueError:
            print(f"{cmp_str}False (# Timestep header not found in golden_output)")
            return 1
        # Extract two rows following the header
        this_data = this_lines[header_index + 1:header_index + 3]
        golden_data = golden_lines[golden_header_index + 1:golden_header_index + 3]

        # Compare the extracted rows
        for line_index, (this_line, golden_line) in enumerate(zip(this_data, golden_data)):
            this_tokens = this_line.split()
            golden_tokens = golden_line.split()
            #print(this_tokens)
            # Compare each numeric token except the last one (Time column)
            for i, (this_token, golden_token) in enumerate(zip(this_tokens[:-1], golden_tokens[:-1])):
                try:
                    this_value = float(this_token)
                    golden_value = float(golden_token)
                    #print(abs(this_value - golden_value))
                    if abs(this_value - golden_value) > tolerance:
                        print(f"{cmp_str}False")
                        return 1
                except ValueError:
                    # Skip non-numeric tokens
                    continue

        # If all tokens are within tolerance
        print(cmp_str + "True")
        return 0

    except Exception as e:
        print(f"{cmp_str}Unexpected error: {e}")
        return 1

def miniFE_compare_outputs(this_output_path, golden_output_path, tolerance): 
    """
    Compare the 'Final Resid Norm' value in two files to check if they are within a specified tolerance.

    :param this_output_path: File path containing this_output data.
    :param golden_output_path: File path containing golden_output data.
    :param tolerance: Allowed tolerance range.
    :return: 0 if the data are within tolerance, 1 otherwise.
    """
    cmp_str = configure.cmp_str  # Custom comparison string
    try:
        # Read both files into lists of lines
        with open(this_output_path, 'r') as f1, open(golden_output_path, 'r') as f2:
            this_lines = f1.readlines()
            golden_lines = f2.readlines()

        # Locate the line containing 'Final Resid Norm' in this_output
        this_resid_norm = None
        for line in this_lines:
            if line.startswith("Final Resid Norm:"):
                try:
                    this_resid_norm = float(line.split(":")[1].strip())
                except ValueError:
                    print(f"{cmp_str}False (Invalid numeric format in this_output)")
                    return 1
                break

        if this_resid_norm is None:
            print(this_output_path)
            print("application generate no output")
            return 1

        # Locate the line containing 'Final Resid Norm' in golden_output
        golden_resid_norm = None
        for line in golden_lines:
            if line.startswith("Final Resid Norm:"):
                try:
                    golden_resid_norm = float(line.split(":")[1].strip())
                except ValueError:
                    print(f"{cmp_str}False (Invalid numeric format in golden_output)")
                    return 1
                break

        if golden_resid_norm is None:
            print("bias not found in golden_output")
            sys.exit(1)
            return 1

        # Compare the residual norms
        if abs(this_resid_norm - golden_resid_norm) > tolerance:
            print(f"{cmp_str}False")
            return 1

        # If the values are within tolerance
        print(cmp_str + "True")
        return 0

    except Exception as e:
        print(f"{cmp_str}Unexpected error: {e}")
        return 1

def HPCCG_compare_outputs(this_output_path, golden_output_path, tolerance):
    """
    Compare the 'Final residual' value in two files to check if they are within a specified tolerance.

    :param this_output_path: File path containing this_output data.
    :param golden_output_path: File path containing golden_output data.
    :param tolerance: Allowed tolerance range.
    :return: 0 if the data are within tolerance, 1 otherwise.
    """
    cmp_str = configure.cmp_str  # Custom comparison string
    try:
        # Read both files into lists of lines
        with open(this_output_path, 'r') as f1, open(golden_output_path, 'r') as f2:
            this_lines = f1.readlines()
            golden_lines = f2.readlines()

        # Locate the line containing 'Final residual:' in this_output
        this_residual = None
        for line in this_lines:
            if line.startswith("Final residual:"):
                try:
                    this_residual = float(line.split(":")[1].strip())
                except ValueError:
                    print(f"{cmp_str}False (Invalid numeric format in this_output)")
                    return 1
                break

        if this_residual is None:
            print(this_output_path)
            print("application generate no output")
            return 1

        # Locate the line containing 'Final residual:' in golden_output
        golden_residual = None
        for line in golden_lines:
            if line.startswith("Final residual:"):
                try:
                    golden_residual = float(line.split(":")[1].strip())
                except ValueError:
                    print(f"{cmp_str}False (Invalid numeric format in golden_output)")
                    return 1
                break

        if golden_residual is None:
            print(f"{cmp_str}False ('Final residual' not found in golden_output)")
            return 1

        # Compare the residuals
        if abs(this_residual - golden_residual) > tolerance:
            print(f"{cmp_str}False")
            return 1

        # If the values are within tolerance
        print(cmp_str + "True")
        return 0

    except Exception as e:
        print(f"{cmp_str}Unexpected error: {e}")
        return 1

def common_compare_outputs(this_output, golden_output, tolerance=configure.tolerance):
    # 读取文件内容
    this_data = np.loadtxt(this_output)
    golden_data = np.loadtxt(golden_output)

    # 检查数据的形状是否相同
    if this_data.shape != golden_data.shape:
        print("Files have different shapes, cannot compare.")
        return 1

    # 计算差异
    difference = np.abs(this_data - golden_data)

    # 检查是否所有差异都在容忍度范围内
    if np.all(difference <= tolerance):
        print(configure.cmp_str+"True")
        return 0
    else:
        print(configure.cmp_str+"False")
        return 1


def SDC_saver(index,progname=configure.progname,sdcout_dir=configure.sdcout_folder):
    print("SDC_saver...")
    if progname == 'lu': 
        this_output,golden_output = Init()
        this_output = move_this_output(this_output,sdcout_dir,index)
        #golden_output = move_this_output(golden_output,sdcout_dir,index)
    elif progname in ['b+tree','bfs','heartwall','hotspot','kmeans','lavaMD','leukocyte','nn','particlefilter','streamcluster'] or progname == 'backprop':
        this_output,golden_output = Init()
        this_output = move_this_output(this_output,sdcout_dir,index)
    





if __name__ == "__main__":

    #process_log_and_sdcout(configure.log_folder, configure.sdcout_folder)
    ##单独验证lu的某一条log
    if (configure.progname == 'lu'):
        Add_SDC_result_to_alllog_LU()
    else:
        Add_SDC_result_to_alllog_common()
