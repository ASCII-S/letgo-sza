import pandas as pd
import os
import re
import configure as cf 
##debug_mode = 1 will print debug info
debug_mode = 5

def extract_instruction_from_asm(benchmark_csv, asm_file,PC,df_Ins,df_Ope):
    # 读取 benchmark CSV 文件为 DataFrame
    df = pd.read_csv(benchmark_csv)

    # 按 Sig1pc 列排序
    df = df.sort_values(by=PC).reset_index(drop=True)

    # 读取 asm 文件
    with open(asm_file, 'r') as asm:
        asm_lines = asm.readlines()

    # 初始化双指针
    asm_idx = 0
    asm_len = len(asm_lines)

    # 查找对应 Sig1pc 的行，并提取指令
    for idx, row in df.iterrows():
        sig1pc = row[PC]
        if sig1pc == 'null':
            continue
        hex_sig1pc = sig1pc[2:]  # 提取十六进制形式的地址部分，不含 "0x"
        # 判断 hex_sig1pc 是否是六位的十六进制地址
        if len(hex_sig1pc) != 6 or not re.match(r'^[0-9a-fA-F]{6}$', hex_sig1pc):
            continue  # 如果不符合六位十六进制地址的格式，跳过当前循环

        if debug_mode >= 6:
            print("\nhex_sig1pc:\t",hex_sig1pc)
        # 双指针遍历 asm 文件
        while asm_idx < asm_len:
            asm_line = asm_lines[asm_idx].strip()

            # 获取 asm 行的地址部分 (":") 之前的内容
            asm_address = asm_line.split(':')[0]
            if len(asm_address) > 6:
                asm_idx += 1
                continue
            if not bool(re.fullmatch(r'[0-9A-Fa-f]{6}', asm_address)):
                asm_idx += 1
                continue
            

            # 比较 sig1pc 与当前 asm 行的地址
            if asm_address == hex_sig1pc:
                # 提取并保存指令部分（: 后面的内容）
                instruction = asm_line[30:]
                df.at[idx, df_Ins] = instruction  # 存储到 DataFrame 中
                df.at[idx, df_Ope] = instruction.split(' ')[0]  # 存储到 DataFrame 中
                if debug_mode >= 6:
                    print("ins:\t",instruction)
                    print("df ins:\t",df.at[idx, df_Ins])
                    print("df ope:\t",df.at[idx, df_Ope])
                    print("asm:\t",asm_address)
                break
            elif asm_address > hex_sig1pc:
                # 如果 asm 地址已经超过 sig1pc，退出内层循环
                idx += 1
                break

            asm_idx += 1  # 移动 asm 指针到下一行
    #print(df)
    return df


def findinsbyasm(program):
    # 使用示例：
    benchmark = program
    csv_folder = './CSV'
    asm_folder  = './asm'
    csv_output = benchmark +'.csv'

    benchmark_csv = os.path.join(csv_folder,benchmark+'.csv')  # CSV 文件路径
    benchmark_fix_csv = os.path.join(csv_folder,csv_output)
    asm_file = os.path.join(asm_folder,benchmark+'.asm')  # asm 文件路径

    df_updated = extract_instruction_from_asm(benchmark_csv, asm_file,"Sig1pc","Sig1Ins","Sig1Ope")
    df_updated.to_csv(benchmark_fix_csv, index=False)
    # 将更新后的 DataFrame 保存回 CSV 文件（可选）
    
    df_updated = extract_instruction_from_asm(benchmark_csv, asm_file,"Sig2pc","Sig2Ins","Sig2Ope")
    df_updated.to_csv(benchmark_fix_csv, index=False)

if __name__ == "__main__":
    findinsbyasm(cf.progname)