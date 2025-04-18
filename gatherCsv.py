import os
import pandas as pd

def csv_to_excel(folder_path, output_file):
    """
    将文件夹内的所有 CSV 文件整合到一个 Excel 文件中，每个 CSV 文件对应一个 Sheet。

    Args:
        folder_path (str): CSV 文件所在文件夹路径。
        output_file (str): 输出的 Excel 文件路径。
    """
    # 创建一个 ExcelWriter 对象
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        # 遍历文件夹中的所有文件
        for file_name in os.listdir(folder_path):
            # 检查文件是否是 CSV 文件
            if file_name.endswith('.csv'):
                file_path = os.path.join(folder_path, file_name)
                # 读取 CSV 文件
                try:
                    df = pd.read_csv(file_path)
                except Exception as e:
                    print(f"无法读取文件 {file_name}: {e}")
                    continue
                # 获取 Sheet 名称（去掉扩展名）
                sheet_name = os.path.splitext(file_name)[0][:31]  # Excel 的 Sheet 名最长为 31 字符
                # 写入到 Excel 的 Sheet 中
                df.to_excel(writer, sheet_name=sheet_name, index=False)
                print(f"已添加文件 {file_name} 到 Sheet {sheet_name}")
    
    print(f"所有 CSV 文件已整合到 {output_file}")

# 使用示例
if __name__ == "__main__":
    folder_path = input("请输入 CSV 文件夹路径: ").strip()
    output_file = input("请输入输出的 Excel 文件名（包括路径）: ").strip()
    csv_to_excel(folder_path, output_file)
