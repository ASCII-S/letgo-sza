import os
pin_home = "/home/tongshiyu/pin/pin"
letgo_base_home = "./"
toolbase = "/home/tongshiyu/pin/source/tools/pinfi"
filib = toolbase + "/obj-intel64/faultinjection.so"
pin_tool_config = "/home/tongshiyu/pin/source/tools/pinfi/config_pintool.h"
Rodinia_base = "/home/tongshiyu/programs/rodinia-master"
#toolbase = "/home/tongshiyu/pin/source/tools/pb_interceptor-master"
pin_base = "/home/tongshiyu/pin"
instcount = "pin.instcount.txt"

prognames_supply = [
    # rodinia
    "amg", "b+tree", "backprop", "bfs", "heartwall", "hotspot", "hotspot3D", 
    "hpl", "kmeans", "knn", "lu", "lavaMD", "leukocyte", "myocyte", "needle", 
    "srad", "nn", "particlefilter", "streamcluster", 
    # mantevo
    "HPCCG", "miniFE", "miniMD", "miniAMR"
    # rodinia
    "backprop","hpl", "hotspot","kmeans","particlefilter","nn""bfs",
]
#特殊名字后缀，默认为空
#special =""
special = ""
#special = "OnlyH_3"

#应用名取自prognames_supply
waittochangebyscrips = "particlefilter"
progname = waittochangebyscrips

#随机注错还是对目标类型注错
inject_random_or_targeted = "random"
inject_random_or_targeted = "targeted"

#对目标类型注错,详细参数
select_type = "call_ret"     #stack,mov,integer,float,call_ret,cmp,---|---,data_transfer,logical,control_flow, other
only_memory = 1
dynamic_analyze =  1 #置1则生成包含指令占比的信息,而非单纯catalog,谨慎!!!
high_bit_fault = 1 #在寄存器高位进行注错
minCountInstInj = 20 #类型注错中，对pc重复注错的最小次数

#实验次数
numFI = 5000

#log起始index
num_start_from = 0
#log终止index
num_end_at = 5000

#注错工具
if inject_random_or_targeted == "targeted":
    inject_tool = 'breakpoint'
if inject_random_or_targeted == "random":
    inject_tool = 'pinfi'

#debugfile,用来生成sighandle中调试步骤,process.txt
debugfile = 1
#废案
inject_op = 'all' ##用all表示不进行启发式注错,已废弃
#inject_op = '' 

if progname == "amg":                                   ## amg    ----------有效实验太少
    progbin = "/home/tongshiyu/programs/LLNL/AMG-master/test/amg"
    optionlist = ['-n','5','5','5']
    pcstart = "401cb8"
    pcend = "49877c"
elif progname == "b+tree":                            ## backprop
    progbin = "/home/tongshiyu/programs/rodinia-master/openmp/b+tree/b+tree"
    optionlist = ['file' ,'/home/tongshiyu/programs/rodinia-master/data/b+tree/mil.txt' ,'command' ,'/home/tongshiyu/programs/rodinia-master/data/b+tree/command.txt']
    pcstart = "400f90"
    pcend = "405510"
elif progname == "backprop":                            ## backprop
    progbin = "/home/tongshiyu/programs/rodinia-master/openmp/backprop/backprop"
    optionlist = ['65536']
    pcstart = "400ad0"
    pcend = "4024d0"
elif progname == "bfs": 
    progbin = "/home/tongshiyu/programs/rodinia-master/openmp/bfs/bfs"
    datafile = "/home/tongshiyu/programs/rodinia-master/data/bfs/inputGen/graph64k.txt"
    optionlist = [datafile]
    pcstart = "400720"
    pcend = "400e80"
elif progname == "heartwall": 
    progbin = "/home/tongshiyu/programs/rodinia-master/openmp/heartwall/heartwall"
    datafile = "/home/tongshiyu/programs/rodinia-master/data/heartwall/test.avi"
    optionlist = [datafile,'20']
    pcstart = "400f00"
    pcend = "407440"
elif progname == "hotspot":
    progbin = "/home/tongshiyu/programs/rodinia-master/openmp/hotspot/hotspot"
    optionlist = ['64','64','2','1',"/home/tongshiyu/programs/rodinia-master/data/hotspot/temp_64",'/home/tongshiyu/programs/rodinia-master/data/hotspot/power_64', 'output.txt']
    pcstart = "400920"
    pcend = "401fd0"
elif progname == "hotspot3D":
    progbin = "/home/tongshiyu/programs/rodinia-master/openmp/hotspot3D/3D"
    optionlist = ['512','8','100',"/home/tongshiyu/programs/rodinia-master/data/hotspot3D/power_512x8",'/home/tongshiyu/programs/rodinia-master/data/hotspot3D/temp_512x8', 'output.txt']
    pcstart = "400ce0"
    pcend = "401d80"
elif progname == 'hpl':
    progbin = "/home/tongshiyu/programs/hpl-2.3/testing/xhpl"
    optionlist = ['']
    pcstart = "4013d0"
    pcend = "41fbd0"
elif progname == "kmeans":                              ## Kmeans
    progbin = "/home/tongshiyu/programs/rodinia-master/openmp/kmeans/kmeans"
    datafile = "/home/tongshiyu/programs/rodinia-master/data/kmeans/inputGen/1000_34.txt"
    optionlist = ['-i', datafile]
    pcstart = "400d20"
    pcend = "402110"
elif progname == "knn":                                 ## KNN
    progbin = "/home/tongshiyu/programs/rodinia-master/openmp/nn/nn"
    datafile = ("/home/tongshiyu/programs/rodinia-master/openmp/nn/cane10k.db")
    optionlist = [datafile, '5', '30', '90']
elif progname == 'lu':
    progbin = "/home/tongshiyu/programs/rodinia-master/openmp/lud/lud"
    optionlist = ['-s512']
    pcstart = "400df0"
    pcend = "401d30"
elif progname == 'lavaMD':
    progbin = "/home/tongshiyu/programs/rodinia-master/openmp/lavaMD/lavaMD"
    optionlist = ['-boxes1d', '10']
    pcstart = "400a40"
    pcend = "401890"
elif progname == 'leukocyte':
    progbin = "/home/tongshiyu/programs/rodinia-master/openmp/leukocyte/leukocyte"
    datafile = "/home/tongshiyu/programs/rodinia-master/data/leukocyte/testfile.avi"
    optionlist = ['5', '4', datafile]
    pcstart = "401540"
    pcend = "41fc90"
elif progname == "myocyte":
    progbin = "/home/tongshiyu/programs/rodinia-master/openmp/myocyte/myocyte"
    optionlist = ['1000', '1', '0', '4']
elif progname == "needle":                              ## Needle
    progbin = "/home/tongshiyu/programs/rodinia-master/openmp/nw/needle"
    optionlist = ['2048', '10', '2']
    pcstart = "400c30"
    pcend = "401980"
elif progname == "srad":
    progbin = "/home/tongshiyu/programs/rodinia-master/openmp/srad_v1/srad"
    optionlist = ['15', '0.5', '285', '250', '1']
    pcstart = "400910"
    pcend = "401ddc"
elif progname == "nn":
    progbin = "/home/tongshiyu/programs/rodinia-master/openmp/nn/nn"
    datafile = "/home/tongshiyu/programs/rodinia-master/openmp/nn/filelist.txt"
    optionlist = [datafile,'5', '30', '90']
    pcstart = "400aa0"
    pcend = "401390"
elif progname == "particlefilter":
    progbin = "/home/tongshiyu/programs/rodinia-master/openmp/particlefilter/particle_filter"
    optionlist = ['-x', '64', '-y', '64', '-z', '5', '-np', '1000']
    pcstart = "4009c0"
    pcend = "4030a0"
elif progname == "streamcluster":
    progbin = "/home/tongshiyu/programs/rodinia-master/openmp/streamcluster/streamcluster"
    optionlist = ["10", "20", "256", "4096", "4096", "100", "none", "output.txt", "1"]
    pcstart = "4011e0"
    pcend = "403e30"
elif progname == "HPCCG":                               ## HPCCG
    progbin = "/home/tongshiyu/programs/mantevo/HPCCG/test_HPCCG"
    optionlist = ['30', '30', '30']
    pcstart = "4021a0"
    pcend = "40b550"
elif progname == "miniAMR":                              
    progbin = "/home/tongshiyu/programs/mantevo/miniAMR/ref/miniAMR.x"
    optionlist = ["--npx 1 --npy 1 --npz 1", "--report_diffusion","--checksum_freq", "10"]
    pcstart = "401110"
    pcend = "43a2c0"
elif progname == "miniFE":                               ## minife
    progbin = "/home/tongshiyu/programs/mantevo/miniFE/openmp/basic/miniFE.x"
    optionlist = ['nx=20']#,'verify_solution=1']
    pcstart = "402ba0"
    pcend = "41de90"
elif progname == "miniMD":                               
    progbin = "/home/tongshiyu/programs/mantevo/miniMD/ref/miniMD"
    optionlist = []
    pcstart = "401930"
    pcend = "416650"

benchmark = progbin
args = optionlist

# mpirun
MPI_SET = 0
mpi_cmd = ["mpirun","-np","1"]
MPI_APP = ["HPCCG","miniAMR","miniFE","miniMD"]
if progname in MPI_APP:
    MPI_SET = 1


# configuration of save outputs
OpenMpOutPutList = ['b+tree','backprop', 'bfs', 'heartwall', 'hotspot', 'hotspot3D','kmeans', 'lavaMD', 'leukocyte', 'lu', 'nn', 'particlefilter', 'streamcluster']
SdcAppList = ['lu','hpl'].append(OpenMpOutPutList)
if progname in ['b+tree','bfs','heartwall','hotspot','kmeans','lavaMD','leukocyte','nn','particlefilter','streamcluster']:
    output_name = 'output.txt'
elif progname in ['leukocyte']:
    output_name = 'result.txt'
elif progname == 'backprop':
    output_name = 'output.dat'
elif progname == 'lu':
    output_name = 'lu_matrix_512.txt'
    lu_output_name = 'lu_matrix_512.txt'
    m_output_path = 'm_matrix_512.txt'
elif progname in ['miniMD','miniFE','HPCCG','hpl']:
    output_name = 'none'
else:
    output_name = ''

# configuration of sdc tolerance
tolerance = 0.0
lu_tolerance = 1e-4
if progname == 'hotspot3D':
    tolerance = 1e-2
if progname == 'lu':
    lu_tolerance = 1e-4
cmp_str = "Compare within tolerance("+str(tolerance)+"):"


# configuration of folder
if inject_random_or_targeted == "random":
    Result_folder_name = "BenchmarkResult"
    analysis_folder_name = "analysis"+special
    insInjection_pool_csv_name = progname + ".csv"
    result_analyze_csv_name = progname +'.csv'
    one_batch_folder = os.path.join(letgo_base_home,Result_folder_name,progname)
    catalog_csv_file = ''
if not inject_random_or_targeted == "random":
    Result_folder_name = "TargetedBenchmarkResult"+special
    analysis_folder_name = "TargetedAnalysis"+special
    catalog_csv_name = select_type+"_catalog"+".csv"
    insInjection_pool_csv_name = select_type + "_pool" + ".csv"
    result_analyze_csv_name = progname + '_' + select_type +'.csv'
    one_batch_folder = os.path.join(letgo_base_home,Result_folder_name,progname,select_type)
    catalog_csv_file = os.path.join(one_batch_folder,catalog_csv_name)
#程序运行数据文件夹
log_folder = os.path.join(one_batch_folder,"log")
sdcout_folder = os.path.join(one_batch_folder,"sdcout")
instpool_folder = os.path.join(one_batch_folder)
#程序运行结果分析文件夹
analysis_folder = os.path.join(letgo_base_home,analysis_folder_name)
csv_folder = os.path.join(analysis_folder,'CSV',progname) if inject_random_or_targeted=="targeted" else  os.path.join(analysis_folder,'CSV')
asm_folder  = os.path.join(analysis_folder,'asm')
pic_folder  = os.path.join(analysis_folder,'PIC',progname) if inject_random_or_targeted=="targeted" else  os.path.join(analysis_folder,'PIC')
mnemonic_count_folder = os.path.join(analysis_folder,'mnemonic_count')
#文件占位符
mnemonic_count_name = progname + "_" + "mnemonic_count.csv"
mnemonic_count_file = os.path.join(mnemonic_count_folder,mnemonic_count_name)
pool_csv_file = os.path.join(one_batch_folder, insInjection_pool_csv_name)
csv_file = os.path.join(csv_folder,result_analyze_csv_name)

folders_to_create = []
folders_to_create.extend([one_batch_folder,log_folder,sdcout_folder,instpool_folder,one_batch_folder,analysis_folder,csv_folder,asm_folder,pic_folder,mnemonic_count_folder])
for folder in folders_to_create:
    os.makedirs(folder, exist_ok=True)



# define results
MASKED = 'Masked'
SDC = 'SDC'
C_MASKED = 'C-Masked'
C_SDC = 'C-SDC'
DOUBLE_CRASH = 'Recrash'
CRASH_NOPC = 'Recrash'

# tmp file about faultinjection.cpp
pin_instcount = "./pin.instcount.txt"
activate = "./activate"