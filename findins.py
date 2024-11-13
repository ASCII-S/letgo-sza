import pandas as pd
import os
import re
import configure
##debug_mode = 1 will print debug info
debug_mode = 5

def dec_to_hex(decimal):
    """将十进制整数转换为十六进制字符串"""
    if not isinstance(decimal, int):
        raise ValueError("输入必须是一个整数")
    # 使用 hex() 函数转换，并去掉前缀 '0x'
    return hex(decimal)[2:]

def decpc_to_op(decpc):
    """在 ASM 文件中查找包含指定 PC 值的行"""
    asm_file = os.path.join(configure.asm_folder,configure.benchmark+'.asm')
    #print(asm_file)
    hexpc = dec_to_hex(decpc)
    try:
        with open(asm_file, 'r') as file:
            for line in file:
                if hexpc in line:  # 查找十六进制 PC 值
                    return line[30:].strip(' ').strip('\t').split(' ')[0]
    except FileNotFoundError:
        print(asm_file,"未找到。")
    except Exception as e:
        print("发生错误: ",e)

    return None  # 如果没有找到，返回 None
      

def extract_instruction_from_asm(benchmark_csv, asm_file,PC,df_Ins,df_Ope,df_Func):
    ##PC是已知的汇编地址,通过asm_file,将所有缺失df_Ins,df_Ope,df_Func信息的的行补充完成
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
    
    func = 'error'
    # 查找对应 Sig1pc 的行，并提取指令
    for idx, row in df.iterrows():
        #sig1pc = row[PC]
        sig1pc = df.at[idx, PC]
        if sig1pc == 'null':
            continue
        if pd.isna(df.at[idx, PC]):
            continue

        try:
            hex_sig1pc = sig1pc.replace('0x','')  # 提取十六进制形式的地址部分，不含 "0x"
        except:
            print(df.at[idx, 'input_file'],str(df.at[idx, PC]),sig1pc)
            continue
            #exit(0)
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

            if '0000000000' in asm_line[0:10]:
                func = asm_line[17:-2]
            if len(asm_address) > 6:##跳过函数名称部分
                asm_idx += 1
                continue
            if not bool(re.fullmatch(r'[0-9A-Fa-f]{6}', asm_address)):
                asm_idx += 1
                continue
            

            # 比较 sig1pc 与当前 asm 行的地址
            if asm_address == hex_sig1pc:
                # 提取并保存指令部分（: 后面的内容）
                instruction = asm_line[30:]
                if df.at[idx, df_Ins] == 'null':
                    df.at[idx, df_Ins] = instruction.strip('"')  # 存储到 DataFrame 中
                if df.at[idx, df_Ope] == 'null':
                    df.at[idx, df_Ope] = instruction.split(' ')[0]  # 存储到 DataFrame 中
                if df.at[idx, df_Func] == 'null':
                    df.at[idx, df_Func] = func
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
    csv_folder = configure.csv_folder
    asm_folder  = configure.asm_folder
    csv_output = benchmark +'.csv'

    benchmark_csv = os.path.join(csv_folder,benchmark+'.csv')  # CSV 文件路径
    benchmark_fix_csv = os.path.join(csv_folder,csv_output)
    asm_file = os.path.join(asm_folder,benchmark+'.asm')  # asm 文件路径

    if(1):
        df_updated = extract_instruction_from_asm(benchmark_csv, asm_file,"hexpc","ins","opcode","Func")
        df_updated.to_csv(benchmark_fix_csv, index=False,na_rep='null')

        df_updated = extract_instruction_from_asm(benchmark_csv, asm_file,"Sig1pc","Sig1Ins","Sig1Ope","Sig1Func")
        df_updated.to_csv(benchmark_fix_csv, index=False,na_rep='null')
        # 将更新后的 DataFrame 保存回 CSV 文件（可选）
        
        df_updated = extract_instruction_from_asm(benchmark_csv, asm_file,"Sig2pc","Sig2Ins","Sig2Ope","Sig2Func")

        df_updated = df_updated.sort_values(by='result')

        df_updated.to_csv(benchmark_fix_csv, index=False,na_rep='null')


def judge_address_in_asm(address,asm_file):
    """
    判断六位地址是否出现在 asm 文件中

    Parameters:
    address (str): 六位地址，通常是 16 进制格式，如 '123456'
    asm_file (str): 汇编文件的路径

    Returns:
    bool: 如果地址出现在文件中，返回 True，否则返回 False
    """
    # 确保地址是六位的16进制格式，例如 '123456'
    if len(address) != 6 :
        #print(f"Invalid address format: {address}. It should be in the format '123456'.")
        return False
    
    # 读取文件内容并检查地址是否出现
    try:
        with open(asm_file, 'r') as file:
            file_content = file.read()
            if address.lower() in file_content.lower():
                #print(f"Address {address} found in {asm_file}.")
                return True
            else:
                #print(f"Address {address} not found in {asm_file}.")
                return False
    except FileNotFoundError:
        print(f"Error: The file {asm_file} was not found.")
        return False
    except Exception as e:
        print(f"An error occurred: {e}")
        return False



if __name__ == "__main__":
    findinsbyasm(configure.progname)