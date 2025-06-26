import os
pin_home = "/home/tongshiyu/pin/pin"
letgo_base_home = "/home/tongshiyu/pin/source/tools/letgo"
toolbase = "/home/tongshiyu/pin/source/tools/pinfi"
filib = toolbase + "/obj-intel64/faultinjection.so"
pin_tool_config = "/home/tongshiyu/pin/source/tools/pinfi/config_pintool.h"
Rodinia_base = "/home/tongshiyu/programs/rodinia-master"
PolyBench_base = "/home/tongshiyu/programs/PolyBenchC-4.2.1"
#toolbase = "/home/tongshiyu/pin/source/tools/pb_interceptor-master"
pin_base = "/home/tongshiyu/pin"
instcount = "pin.instcount.txt"

rodinia_app_list = ["amg", "b+tree", "backprop", "bfs", "heartwall", "hotspot", "hotspot3D", 
                    "hpl", "kmeans", "knn", "lu", "lavaMD", "leukocyte", "myocyte", "needle", 
                    "srad", "nn", "particlefilter", "streamcluster"]
mantevo_app_list = ["HPCCG", "miniFE", "miniMD", "miniAMR"]
NPB_SER_app_list = ["bt","cg","ep","ft","is","lu","mg","sp","ua"]
PolyBenchtList = ['2mm','bicg','correlation','fdtd-2d','gesummv','syr2k','gaussian','convolution','mvt']

prognames_supply = [
    # rodinia
    "amg", "b+tree", "backprop", "bfs", "heartwall", "hotspot", "hotspot3D", 
    "hpl", "kmeans", "knn", "lu", "lavaMD", "leukocyte", "myocyte", "needle", 
    "srad", "nn", "particlefilter", "streamcluster", 
    # mantevo
    "HPCCG", "miniFE", "miniMD", "miniAMR",
    # NPB-SER
    "bt","cg","ep","ft","is","lu","mg","sp","ua",
    # PolyBench
    "2mm", "bicg", "correlation", "fdtd-2d", "gesummv", "syr2k",
    # use
    "backprop","hpl", "hotspot","kmeans","particlefilter","nn""bfs","HPCCG", "miniFE"
]
#特殊名字后缀，默认为空
#special =""
special = "TargetedpopCheckParser"

#应用名取自prognames_supply
waittochangebyscrips = "gesummv"
progname = waittochangebyscrips

#随机注错还是对目标类型注错
inject_random_or_targeted = "random"
inject_random_or_targeted = "targeted"

# 对目标类型注错,详细参数。请保持select_type不变，对不同progname批量进行实验!!!
# all
# | stack   |   mov |   integer |   float   |   call_ret    |   cmp
# data_transfer,logical,control_flow, other
select_type = "stack"     
only_memory = 1
dynamic_analyze =  1 #置1则生成包含指令占比的信息,而非单纯catalog,谨慎!!!
high_bit_fault = 0 #在寄存器高位进行注错
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
debugfile = 0

#gdb_verbose,控制是否显示GDB交互信息，默认不显示
gdb_verbose = False
#废案
inject_op = 'all' ##用all表示不进行启发式注错,已废弃
#inject_op = '' 

#progname对应的程序路径和参数
if 1:
    if progname == "amg":                                   ## amg    ----------有效实验太少
        progbin = "/home/tongshiyu/programs/LLNL/AMG-master/test/amg"
        optionlist = ['-n','5','5','5']
        pcstart = "401cb8"  # 在注错方式是targeted时使用
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
    elif progname == "bt":                               
        progbin = "/home/tongshiyu/programs/NPB3.3.1/NPB3.3-SER/bin/bt.S.x"
        optionlist = []
        pcstart = "400af0"
        pcend = "40e870"
    elif progname == "cg":
        progbin = "/home/tongshiyu/programs/NPB3.3.1/NPB3.3-SER/bin/cg.S.x"
        optionlist = []

    elif progname == "dc":
        progbin = "/home/tongshiyu/programs/NPB3.3.1/NPB3.3-SER/bin/dc.S.x"
        optionlist = []

    elif progname == "ep":
        progbin = "/home/tongshiyu/programs/NPB3.3.1/NPB3.3-SER/bin/ep.S.x"
        optionlist = []

    elif progname == "ft":
        progbin = "/home/tongshiyu/programs/NPB3.3.1/NPB3.3-SER/bin/ft.S.x"
        optionlist = []

    elif progname == "is":
        progbin = "/home/tongshiyu/programs/NPB3.3.1/NPB3.3-SER/bin/is.S.x"
        optionlist = []

    elif progname == "lu":
        progbin = "/home/tongshiyu/programs/NPB3.3.1/NPB3.3-SER/bin/lu.S.x"
        optionlist = []

    elif progname == "mg":
        progbin = "/home/tongshiyu/programs/NPB3.3.1/NPB3.3-SER/bin/mg.S.x"
        optionlist = []

    elif progname == "sp":
        progbin = "/home/tongshiyu/programs/NPB3.3.1/NPB3.3-SER/bin/sp.S.x"
        optionlist = []

    elif progname == "ua":
        progbin = "/home/tongshiyu/programs/NPB3.3.1/NPB3.3-SER/bin/ua.S.x"
        optionlist = []

    ########################################polybench
    elif progname == "2mm":
        progbin = "/home/tongshiyu/programs/PolyBenchC-4.2.1/bin/2mm_ref"
        optionlist = ["2>/tmp/output_2mm.txt"]
        pcstart = "4011a0"
        pcend = "49359b"
    elif progname == "bicg":
        progbin = "/home/tongshiyu/programs/PolyBenchC-4.2.1/bin/bicg_ref"
        optionlist = ["2>/tmp/output_bicg.txt"]
        pcstart = "4011a0"
        pcend = "49346b"
    elif progname == "convolution":
        progbin = "/home/tongshiyu/programs/PolyBenchC-4.2.1/bin/convolution_ref"
        optionlist = ["2>/tmp/output_convolution.txt"]
        pcstart = "400af0"
        pcend = "40e870"
    elif progname == "correlation":
        progbin = "/home/tongshiyu/programs/PolyBenchC-4.2.1/bin/correlation_ref"
        optionlist = ["2>/tmp/output_correlation.txt"]
        pcstart = "11a0"
        pcend = "1dc4"
    elif progname == "fdtd-2d":
        progbin = "/home/tongshiyu/programs/PolyBenchC-4.2.1/bin/fdtd-2d_ref"
        optionlist = ["2>/tmp/output_fdtd-2d.txt"]
        pcstart = "1180"
        pcend = "1e34"
    elif progname == "gesummv":
        progbin = "/home/tongshiyu/programs/PolyBenchC-4.2.1/bin/gesummv_ref"
        optionlist = ["2>/tmp/output_gesummv.txt"]
        pcstart = "1180"
        pcend = "1a94"
    elif progname == "syr2k":
        progbin = "/home/tongshiyu/programs/PolyBenchC-4.2.1/bin/syr2k_ref"
        optionlist = ["2>/tmp/output_syr2k.txt"]
        pcstart = "1180"
        pcend = "1a94"
    elif progname == "gaussian":
        progbin = "/home/tongshiyu/programs/PolyBenchC-4.2.1/bin/gaussian_ref"
        optionlist = ["2>/tmp/output_gaussian.txt"]
        pcstart = "1180"
        pcend = "1a94"
    elif progname == "mvt":
        progbin = "/home/tongshiyu/programs/PolyBenchC-4.2.1/bin/mvt_ref"
        optionlist = ["2>/tmp/output_mvt.txt"]
        pcstart = "1180"
        pcend = "1a94"

benchmark = progbin
args = optionlist

# mpirun
MPI_SET = 0
mpi_cmd = ["mpirun","-np","1"]
MPI_APP = ["HPCCG","miniAMR","miniFE","miniMD"]
if progname in MPI_APP:
    MPI_SET = 1



# configuration of experiment outputs
OpenMpOutPutList = ['b+tree','backprop', 'bfs', 'heartwall', 'hotspot', 'hotspot3D','kmeans', 'lavaMD', 'leukocyte', 'lu', 'nn', 'particlefilter', 'streamcluster']
PolyBenchOutPutList = PolyBenchtList
SdcAppList = ['lu','hpl'].append(OpenMpOutPutList)
output_list = []
output_list.extend(['b+tree','bfs','heartwall','hotspot','kmeans','lavaMD','leukocyte','nn','particlefilter','streamcluster'])

if progname in output_list:
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
elif progname in PolyBenchOutPutList:
    output_name = "output_"+progname+".txt"
else:
    output_name = ''


# golden output of program
if 1:
    in_path = progname + '/' + output_name
    golden_output = os.path.join(Rodinia_base, "results", in_path)
    if progname == 'hotspot':
        golden_output = "/home/tongshiyu/programs/rodinia-master/openmp/hotspot/output.txt"
    if progname == 'miniMD':
        golden_output = "/home/tongshiyu/programs/mantevo/miniMD/ref/output.txt"
    if progname == 'miniFE':
        golden_output = "/home/tongshiyu/programs/mantevo/miniFE/openmp/basic/output.txt"
    if progname == 'HPCCG':
        golden_output = "/home/tongshiyu/programs/mantevo/HPCCG/output.txt"
    elif progname == 'hpl':
        golden_output = "/home/tongshiyu/programs/hpl-2.3/testing/output.txt"
    if progname == 'nn':
        golden_output = "/home/tongshiyu/programs/rodinia-master/openmp/nn/output.txt"
    if progname == 'kmeans':
        golden_output = "/home/tongshiyu/programs/rodinia-master/openmp/kmeans/output.txt"
    if progname == 'particlefilter':
        golden_output = "/home/tongshiyu/programs/rodinia-master/openmp/particlefilter/output.txt"
    if progname in ['2mm', 'fdtd-2d', 'bicg', 'correlation', 'gesummv', 'syr2k']:
        golden_output_folder = "/home/tongshiyu/programs/PolyBenchC-4.2.1/golden_output"
        golden_output_name = progname+"_ref.out"
        golden_output = os.path.join(golden_output_folder, golden_output_name)

# configuration of sdc tolerance
sdcprogram = []
sdcprogram.extend(["HPCCG", "hpl", "miniFE", "miniMD"])
sdcprogram.extend(PolyBenchtList)
tolerance = 0.1
lu_tolerance = 1e-4
if progname == 'hotspot3D':
    tolerance = 1e-2
elif progname == 'lu':
    lu_tolerance = 1e-4
elif progname in ['2mm', 'fdtd-2d', 'bicg', 'correlation', 'gesummv', 'syr2k']:
    # polybench采用相对误差
    tolerance = 0.1
# elif progname in ["HPCCG", "hpl", "miniFE", "miniMD"]:
#     tolerance = 0.1
cmp_str = "Compare within tolerance("+str(tolerance)+"):"


# configuration of folder
if 1:
    if inject_random_or_targeted == "random":
        Result_folder_name = "BenchmarkResult"
        # Result_folder_name = "mnt/BenchmarkResult-202501"
        analysis_folder_name = "analysis"+special
        insInjection_pool_csv_name = progname + ".csv"
        result_analyze_csv_name = progname +'.csv'
        one_batch_folder = os.path.join(letgo_base_home,Result_folder_name,progname)
        catalog_csv_file = ''
    if not inject_random_or_targeted == "random":
        Result_folder_name = "TargetedBenchmarkResult"+special
        # Result_folder_name = "/home/tongshiyu/pin/source/tools/letgo/mnt/TargetedBenchmarkResult-202501"
        analysis_folder_name = "TargetedAnalysis"+special
        # analysis_folder_name = "/home/tongshiyu/pin/source/tools/letgo/TargetedAnalysis-202501"
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
SDC_UNACCEPTED = 'SDCs-Unacceptable'
SDC_ACCEPTED = 'SDCs-Acceptable'
C_MASKED = 'C-Masked'
C_SDC = 'C-SDC'
C_SDC_UNACCEPTED = 'C-SDCs-Unacceptable'
C_SDC_ACCEPTED = 'C-SDCs-Acceptable'
DOUBLE_CRASH = 'Recrash'
CRASH_NOPC = 'Recrash'

# tmp file about faultinjection.cpp
pin_instcount = "./pin.instcount.txt"
activate = "./activate"