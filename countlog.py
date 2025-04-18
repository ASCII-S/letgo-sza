import os
from collections import Counter
import configure

# 递归遍历文件夹，统计文件和文件夹数量
def count_files_and_folders(directory):
    file_count = 0
    folder_count = 0
    tree_structure = {}

    # 遍历目录中的所有项目
    for root, dirs, files in os.walk(directory):
        # 计算当前目录中的文件和文件夹数量
        file_count += len(files)
        folder_count += len(dirs)
        
        # 存储当前目录的树形结构信息
        tree_structure[root] = {
            "files": len(files),
            "dirs": len(dirs),
            "total": len(files) + len(dirs)
        }

    return tree_structure

# 递归打印文件夹树
def print_tree(directory, tree_structure, indent=""):
    # 打印当前目录的树形结构
    if directory in tree_structure:
        files = tree_structure[directory]["files"]
        dirs = tree_structure[directory]["dirs"]
        total = tree_structure[directory]["total"]
        
        # 打印目录信息
        #print(f"{indent}{os.path.basename(directory)} (Files: {files}, Folders: {dirs}, Total: {total})")
        print(f"{indent}{os.path.basename(directory)} :{files}")
        # 递归打印子文件夹的信息
        for sub_dir in os.listdir(directory):
            sub_path = os.path.join(directory, sub_dir)
            if os.path.isdir(sub_path):
                print_tree(sub_path, tree_structure, indent + "    ")

# 主函数
def main(directory):
    tree_structure = count_files_and_folders(directory)
    print_tree(directory, tree_structure)
# 使用示例
directory_path = os.path.join(configure.letgo_base_home,configure.Result_folder_name)  # 例如 '/path/to/your/folder'
main(directory_path)
