import os
import pandas as pd
import configure

def delete_files_based_on_csv(csv_file_path, log_path):
    # 读取 CSV 文件
    df = pd.read_csv(csv_file_path)

    # 提取 input_file 列，前提是 regmm 列为 'rip'
    files_to_delete = df[df['regmm'] == 'rip']['input_file'].tolist()

    # 遍历要删除的文件，检查并删除
    for file_name in files_to_delete:
        file_path = os.path.join(log_path, file_name)
        if os.path.exists(file_path):
            #os.remove(file_path)
            print(f"Deleted file: {file_path}")
        else:
            print(f"File not found: {file_path}")


def delete_log_based_on_index(log_directory=configure.log_path):
    # 列出所有文件
    files = os.listdir(log_directory)
    
    for file in files:
        # 检查文件名是否以"log_"开头
        if file.startswith("log_"):
            # 提取序号
            try:
                index = int(file.split('_')[1])
                # 删除序号大于或等于748的文件
                if index >= 1026:
                    file_path = os.path.join(log_directory, file)
                    os.remove(file_path)
                    print(f"Deleted: {file_path}")
            except (IndexError, ValueError):
                # 如果文件名格式不正确，则跳过
                continue

if __name__ == "__main__":
    # 使用示例
    #delete_files_based_on_csv(os.path.join(configure.csv_folder, configure.progname + '.csv'), configure.log_path)
    delete_log_based_on_index()
