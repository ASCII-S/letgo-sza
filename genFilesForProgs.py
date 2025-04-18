import os
import sys
from InstPoolMaker import generate_mnemonic_count_file
from InstPoolMaker import radioofjmp
import configure

def change_progname_in_config(config_file, startstring, new_progname):
    """
    修改配置文件中的 progname 为新的值。

    :param config_file: 配置文件的路径。
    :param new_progname: 新的程序名称，将替换配置文件中的 progname。
    """
    # 检查文件是否存在
    if not os.path.exists(config_file):
        print(f"错误: 文件 {config_file} 不存在!")
        return

    # 读取配置文件内容
    with open(config_file, 'r') as file:
        config_lines = file.readlines()

    # 查找所有的 progname 配置项
    progname_indices = [i for i, line in enumerate(config_lines) if line.strip().startswith(startstring)]
    
    # 检查是否有唯一的 progname 配置项
    if len(progname_indices) == 0:
        print("错误: 配置文件中未找到 progname 配置项!")
        return
    elif len(progname_indices) > 1:
        print(f"错误: 配置文件中找到多个 progname 配置项, 请检查文件! 位置: {progname_indices}")
        return

    # 替换找到的唯一 progname 配置项
    progname_index = progname_indices[0]
    config_lines[progname_index] = f'{startstring}"{new_progname}"\n'
    print(f"已将 {startstring} 更改为: {new_progname}")

    # 将修改后的内容写回到文件
    with open(config_file, 'w') as file:
        file.writelines(config_lines)
    
    print(f"配置文件 {config_file} 更新成功!")

def run_multiple_tasks_in_parallel_with_results(func, task_names):
    with multiprocessing.Pool(processes=len(task_names)) as pool:
        results = pool.map(func, task_names)
    print("Results:", results)

def main():
    # 示例: 使用该函数修改配置文件中的 progname
    # 调用函数时，传入文件地址和新值
    config_file_path = "./configure.py"  # 这里替换为实际的配置文件路径
    file_path = configure.mnemonic_count_file
    startstring = "waittochangebyscrips = "
    # 获取当前的 progname
    current_progname = configure.progname
    print("Current progname:", current_progname)

    prognames_supply = [
    # rodinia
    "amg", "b+tree", "backprop", "bfs", "heartwall", "hotspot", "hotspot3D", 
    "hpl", "kmeans", "knn", "lu", "lavaMD", "leukocyte", "myocyte", "needle", 
    "srad", "nn", "particlefilter", "streamcluster", 
    # mantevo
    "HPCCG", "miniFE", "miniMD", "miniAMR"
    ]

    prognames_list = [
    "backprop", "bfs", "hotspot", 
    "hpl", "kmeans",
    "nn", "particlefilter", 
    # mantevo
    "HPCCG", "miniFE", "miniMD"
    ]

    # 检查文件是否存在
    if os.path.exists(file_path):
        print("Exist:\t", file_path)
        
        # 查找当前 progname 在 prognames_list 中的索引
        try:
            current_index = prognames_list.index(current_progname)
        except ValueError:
            print(f"Error: current progname '{current_progname}' not found in the list.")
            current_index = -1

        # 循环查找并更新 progname
        if current_index != -1:
            # 计算下一个 progname 索引，使用取余来实现循环
            next_index = (current_index + 1) % len(prognames_list)
            next_progname = prognames_list[next_index]
            
            print(f"Updating progname from {current_progname} to {next_progname}")
            
            # 更新 config 文件中的 progname
            change_progname_in_config(config_file_path, startstring, next_progname)
        else:
            print("Current progname not found in the list.")
        return
    else:
        print(f"File does not exist: {file_path}")
    ##针对特定progname需要创建的文件

    #generate_mnemonic_count_file()
    radioofjmp()



if __name__ == "__main__":
    main()