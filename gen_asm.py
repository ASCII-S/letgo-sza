import os
import subprocess
import re
import configure

def disassemble_binary():
    # 确保 asm_folder 存在
    if not os.path.exists(configure.asm_folder):
        os.makedirs(configure.asm_folder)

    # 反汇编二进制文件
    input_file = configure.progbin
    output_file = os.path.join(configure.asm_folder, configure.progname+'.asm')

    try:
        # 使用 objdump 仅对 .text 段进行反汇编
        subprocess.run(['objdump', '-d', '--section=.text', input_file], stdout=open(output_file, 'w'), check=True)
        print(f"Disassembly of .text section complete. Output saved to {output_file}")

        # 读取汇编文件并提取 .text 段的起止地址
        pcstart, pcend = extract_text_section_address_range(output_file)
        print(f'pcstart = "{pcstart}"')
        print(f'pcend = "{pcend}"')

    except subprocess.CalledProcessError as e:
        print(f"Error during disassembly: {e}")

def extract_text_section_address_range(asm_file):
    min_address = float('inf')
    max_address = float('-inf')
    in_text_section = False  # 标志是否在 .text 段内

    with open(asm_file, 'r') as f:
        for line in f:
            # 检查是否进入 .text 段
            if re.match(r'\s*Disassembly of section \.text:', line):
                in_text_section = True
                continue
            # 如果到达其他段的汇编代码，退出 .text 段
            elif re.match(r'\s*Disassembly of section ', line):
                in_text_section = False

            # 只处理 .text 段的指令行
            if in_text_section:
                match = re.match(r'^\s*([0-9a-fA-F]+):', line)
                if match:
                    address = int(match.group(1), 16)
                    if address < min_address:
                        min_address = address
                    if address > max_address:
                        max_address = address

    # 返回十六进制地址范围
    pcstart = f"{min_address:08x}" if min_address != float('inf') else None
    pcend = f"{max_address:08x}" if max_address != float('-inf') else None
    return pcstart.lstrip('0'), pcend.lstrip('0')

# 运行反汇编函数
if __name__ == "__main__":
    disassemble_binary()
