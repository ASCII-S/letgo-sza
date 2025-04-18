import os
import csv
import argparse
from collections import Counter

def count_instruction_types(folder_path):
    """
    统计指定文件夹下所有 CSV 文件中第一列指令类型的次数，并去重。
    """
    instruction_counter = Counter()

    # 遍历文件夹中的所有文件
    for file_name in os.listdir(folder_path):
        file_path = os.path.join(folder_path, file_name)

        # 仅处理 CSV 文件
        if os.path.isfile(file_path) and file_name.endswith('.csv'):
            with open(file_path, 'r', encoding='utf-8') as file:
                csv_reader = csv.reader(file)
                for row in csv_reader:
                    if row:  # 确保行不为空
                        instruction = row[0].strip()  # 获取第一列的指令类型
                        instruction_counter[instruction] += 1

    return instruction_counter

def save_results_to_txt(results, output_path):
    """
    将统计结果保存到 TXT 文件，去重指令名称并按字典序排序。
    """
    sorted_instructions = sorted(results.keys())  # 按字典序排序

    with open(output_path, 'w', encoding='utf-8') as file:
        for instruction in sorted_instructions:
            file.write(f"{instruction}\n")

def main():
    # 设置参数解析
    parser = argparse.ArgumentParser(description="统计文件夹下所有 CSV 文件的指令类型")
    parser.add_argument(
        "-w", "--folder", 
        type=str, 
        default="./TargetedAnalysis/mnemonic_count", 
        help="要统计的文件夹路径，默认为 ./csv_files"
    )
    args = parser.parse_args()

    # 获取输入文件夹路径
    folder_path = args.folder

    if not os.path.exists(folder_path):
        print(f"指定的文件夹路径不存在: {folder_path}")
        return

    # 统计指令类型
    results = count_instruction_types(folder_path)

    # 保存结果到 TXT 文件
    output_path = os.path.join(folder_path, "instType.txt")
    save_results_to_txt(results, output_path)

    print(f"统计结果已保存到 {output_path}")

if __name__ == "__main__":
    main()
