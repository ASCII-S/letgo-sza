import os
pin_home = "/home/tongshiyu/pin/pin"
letgo_base_home = "/home/tongshiyu/pin/source/tools/letgo"

progname = 'hpl'
numFI = 1000



if progname == 'hpl':
    progbin = "/home/tongshiyu/programs/hpl-2.3/testing/xhpl"
    optionlist = ['']
elif progname == 'lu':
    progbin = "/home/tongshiyu/programs/rodinia-master/openmp/lud/lud"
    optionlist = ['-s512']
elif progname == "amg":                                   ## amg    ----------有效实验太少
    progbin = "/home/tongshiyu/programs/LLNL/AMG-master/test/amg"
    optionlist = ['-n','5','5','5']
elif progname == "bfs": 
    progbin = "/home/tongshiyu/programs/rodinia-master/openmp/bfs/bfs"
    datafile = "/home/tongshiyu/programs/rodinia-master/data/bfs/inputGen/graph64k.txt"
    optionlist = [datafile]
elif progname == "myocyte":
    progbin = "/home/tongshiyu/programs/rodinia-master/openmp/myocyte/myocyte"
    optionlist = ['1000', '1', '0', '4']
elif progname == "hotspot":
    progbin = "/home/tongshiyu/programs/rodinia-master/openmp/hotspot/hotspot"
    optionlist = ['64','64','2','1',"/home/tongshiyu/programs/rodinia-master/data/hotspot/temp_64",'/home/tongshiyu/programs/rodinia-master/data/hotspot/power_64', './hotspot/outfile']
elif progname == "knn":                                 ## KNN
    progbin = "/home/tongshiyu/programs/rodinia-master/openmp/nn/nn"
    datafile = ("/home/tongshiyu/programs/rodinia-master/openmp/nn/cane10k.db")
    optionlist = [datafile, '5', '30', '90']
elif progname == "backprop":                            ## backprop
    progbin = "/home/tongshiyu/programs/rodinia-master/openmp/backprop/backprop"
    optionlist = ['65536']
benchmark = progbin
args = optionlist

toolbase = "/home/tongshiyu/pin/source/tools/pinfi"
pin_tool_config = "/home/tongshiyu/pin/source/tools/pinfi/config_pintool.h"



#toolbase = "/home/tongshiyu/pin/source/tools/pb_interceptor-master"
pin_base = "/home/tongshiyu/pin"
instcount = "inscount.out"
#log_path = progname
log_path = os.path.join(letgo_base_home,progname)
