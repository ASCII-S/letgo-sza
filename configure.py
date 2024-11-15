import os
pin_home = "/home/tongshiyu/pin/pin"
letgo_base_home = "/home/tongshiyu/pin/source/tools/letgo"
toolbase = "/home/tongshiyu/pin/source/tools/pinfi"
filib = toolbase + "/obj-intel64/faultinjection.so"
pin_tool_config = "/home/tongshiyu/pin/source/tools/pinfi/config_pintool.h"
Rodinia_base = "/home/tongshiyu/programs/rodinia-master"
#toolbase = "/home/tongshiyu/pin/source/tools/pb_interceptor-master"
pin_base = "/home/tongshiyu/pin"
instcount = "pin.instcount.txt"


progname = "bfs"
numFI = 1000
num_start_from = 0
inject_op = 'all' ##用all表示不进行启发式注错
#inject_op = '' 


if progname == "amg":                                   ## amg    ----------有效实验太少
    progbin = "/home/tongshiyu/programs/LLNL/AMG-master/test/amg"
    optionlist = ['-n','5','5','5']
    pcstart = "401cb8"
    pcend = "49877c"
elif progname == "b+tree":                            ## backprop
    progbin = "/home/tongshiyu/programs/rodinia-master/openmp/b+tree/b+tree"
    optionlist = ['file' ,'/home/tongshiyu/programs/rodinia-master/data/b+tree/mil.txt' ,'command' ,'/home/tongshiyu/programs/rodinia-master/data/b+tree/command.txt']
    pcstart = "400d28"
    pcend = "40551c"
elif progname == "backprop":                            ## backprop
    progbin = "/home/tongshiyu/programs/rodinia-master/openmp/backprop/backprop"
    optionlist = ['65536']
    pcstart = "400968"
    pcend = "401f1c"
elif progname == "bfs": 
    progbin = "/home/tongshiyu/programs/rodinia-master/openmp/bfs/bfs"
    datafile = "/home/tongshiyu/programs/rodinia-master/data/bfs/inputGen/graph64k.txt"
    optionlist = [datafile]
    pcstart = "400740"
    pcend = "400cd0"
elif progname == "heartwall": 
    progbin = "/home/tongshiyu/programs/rodinia-master/openmp/heartwall/heartwall"
    datafile = "/home/tongshiyu/programs/rodinia-master/data/heartwall/test.avi"
    optionlist = [datafile,'20']
    pcstart = "400740"
    pcend = "400cd0"
elif progname == "hotspot":
    progbin = "/home/tongshiyu/programs/rodinia-master/openmp/hotspot/hotspot"
    optionlist = ['64','64','2','1',"/home/tongshiyu/programs/rodinia-master/data/hotspot/temp_64",'/home/tongshiyu/programs/rodinia-master/data/hotspot/power_64', 'output.txt']
    pcstart = "4007e0"
    pcend = "4018fc"
elif progname == "hotspot3D":
    progbin = "/home/tongshiyu/programs/rodinia-master/openmp/hotspot3D/3D"
    optionlist = ['512','8','100',"/home/tongshiyu/programs/rodinia-master/data/hotspot3D/power_512x8",'/home/tongshiyu/programs/rodinia-master/data/hotspot3D/temp_512x8', 'output.txt']
    pcstart = "400b08"
    pcend = "401d8c"
elif progname == 'hpl':
    progbin = "/home/tongshiyu/programs/hpl-2.3/testing/xhpl"
    optionlist = ['']
    pcstart = "401060"
    pcend = "41d6ec"
elif progname == "kmeans":                              ## Kmeans
    progbin = "/home/tongshiyu/programs/rodinia-master/openmp/kmeans/kmeans"
    datafile = "/home/tongshiyu/programs/rodinia-master/data/kmeans/inputGen/1000_34.txt"
    optionlist = ['-i', datafile]
    pcstart = "400b58"
    pcend = "401b7c"
elif progname == "knn":                                 ## KNN
    progbin = "/home/tongshiyu/programs/rodinia-master/openmp/nn/nn"
    datafile = ("/home/tongshiyu/programs/rodinia-master/openmp/nn/cane10k.db")
    optionlist = [datafile, '5', '30', '90']
elif progname == 'lu':
    progbin = "/home/tongshiyu/programs/rodinia-master/openmp/lud/lud"
    optionlist = ['-s512 -v']
    pcstart = "400b40"
    pcend = "401bac"
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

benchmark = progbin
args = optionlist

# configuration of save outputs
OpenMpOutPutList = ['b+tree','backprop', 'bfs', 'heartwall', 'hotspot', 'hotspot3D','kmeans', 'lavaMD', 'leukocyte', 'nn', 'particlefilter', 'streamcluster']
SdcAppList = ['lu','hpl'].append(OpenMpOutPutList)
if progname in ['b+tree','bfs','heartwall','hotspot','kmeans','lavaMD','leukocyte','nn','particlefilter','streamcluster']:
    output_name = 'output.txt'
elif progname in ['leukocyte']:
    output_name = 'result.txt'
elif progname == 'backprop':
    output_name = 'output.dat'
elif progname == 'lu':
    lu_output_name = 'lu_matrix_512.txt'
    m_output_path = 'm_matrix_512.txt'

# configuration of sdc tolerance
tolerance = 1e-2
lu_tolerance = 1e-4
if progname == 'hotspot3D':
    tolerance = 1e-2
if progname == 'lu':
    lu_tolerance = 1e-4
cmp_str = "Compare within tolerance("+str(tolerance)+"):\t"


# configuration of folder
result_path = os.path.join(letgo_base_home,"BenchmarkResult")
#result_path = os.path.join(letgo_base_home,"nosdcarchive","BenchmarkResult")

prog_folder = os.path.join(result_path,progname)
log_path = os.path.join(result_path,progname,"log")
sdcout_folder = os.path.join(result_path,progname,"sdcout")
instpool_folder = os.path.join(result_path,progname)

analysis_folder = os.path.join(letgo_base_home,'analysis')
csv_folder = os.path.join(analysis_folder,'CSV')
asm_folder  = os.path.join(analysis_folder,'asm')
pic_folder  = os.path.join(analysis_folder,'PIC')

# define results
MASKED = 'Masked'
SDC = 'SDC'
C_MASKED = 'C-Masked'
C_SDC = 'C-SDC'
DOUBLE_CRASH = 'Double crash'
CRASH_NOPC = 'crash'

# about faultinjection.cpp
pin_instcount = "./pin.instcount.txt"
activate = "./activate"