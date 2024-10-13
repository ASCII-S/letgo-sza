import os
pin_home = "/home/tongshiyu/pin/pin"
letgo_base_home = "/home/tongshiyu/pin/source/tools/letgo"

progname = 'hotspot'
numFI = 5000
inject_op = 'all' ##用all表示不进行启发式注错
#inject_op = '' 



if progname == 'hpl':
    progbin = "/home/tongshiyu/programs/hpl-2.3/testing/xhpl"
    optionlist = ['']
    pcstart = "401060"
    pcend = "41d6ec"
elif progname == 'lu':
    progbin = "/home/tongshiyu/programs/rodinia-master/openmp/lud/lud"
    optionlist = ['-s512']
    pcstart = "400c30"
    pcend = "401980"
elif progname == "amg":                                   ## amg    ----------有效实验太少
    progbin = "/home/tongshiyu/programs/LLNL/AMG-master/test/amg"
    optionlist = ['-n','5','5','5']
    pcstart = "401cb8"
    pcend = "49877c"
elif progname == "bfs": 
    progbin = "/home/tongshiyu/programs/rodinia-master/openmp/bfs/bfs"
    datafile = "/home/tongshiyu/programs/rodinia-master/data/bfs/inputGen/graph64k.txt"
    optionlist = [datafile]
    pcstart = "400650"
    pcend = "400cdc"
elif progname == "myocyte":
    progbin = "/home/tongshiyu/programs/rodinia-master/openmp/myocyte/myocyte"
    optionlist = ['1000', '1', '0', '4']
elif progname == "hotspot":
    progbin = "/home/tongshiyu/programs/rodinia-master/openmp/hotspot/hotspot"
    optionlist = ['64','64','2','1',"/home/tongshiyu/programs/rodinia-master/data/hotspot/temp_64",'/home/tongshiyu/programs/rodinia-master/data/hotspot/power_64', './hotspot/outfile']
    pcstart = "4007e0"
    pcend = "4018fc"
elif progname == "knn":                                 ## KNN
    progbin = "/home/tongshiyu/programs/rodinia-master/openmp/nn/nn"
    datafile = ("/home/tongshiyu/programs/rodinia-master/openmp/nn/cane10k.db")
    optionlist = [datafile, '5', '30', '90']
elif progname == "backprop":                            ## backprop
    progbin = "/home/tongshiyu/programs/rodinia-master/openmp/backprop/backprop"
    optionlist = ['65536']
    pcstart = "400968"
    pcend = "401f1c"
benchmark = progbin
args = optionlist

toolbase = "/home/tongshiyu/pin/source/tools/pinfi"
pin_tool_config = "/home/tongshiyu/pin/source/tools/pinfi/config_pintool.h"

#toolbase = "/home/tongshiyu/pin/source/tools/pb_interceptor-master"
pin_base = "/home/tongshiyu/pin"
instcount = "inscount.out"
#log_path = progname
log_path = os.path.join(letgo_base_home,progname)

csv_folder = os.path.join(letgo_base_home,'CSV')
asm_folder  = os.path.join(letgo_base_home,'asm')
pic_folder  = os.path.join(letgo_base_home,'PIC')