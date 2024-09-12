import os
pin_home = "/home/tongshiyu/pin/pin"

progname = 'hotspot'

if progname == 'hpl':
    progbin = "/home/tongshiyu/programs/hpl-2.3/testing/xhpl"
    optionlist = ['']
elif progname == 'lu':
    progbin = "/home/tongshiyu/programs/rodinia-master/openmp/lud/lud"
    optionlist = ['-s512']
elif progname == 'fft':
    progbin = "/root/localTool/HPL/splash2/codes/kernels/fft/FFT"
    optionlist = ['']
elif progname == "amg":                                   ## amg
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
    datafile = "./filelist.txt"
    optionlist = [datafile, '5', '30', '90']


benchmark = progbin
args = optionlist
#toolbase = "/home/tongshiyu/pin/source/tools/pinfi"
toolbase = "/home/tongshiyu/pin/source/tools/pb_interceptor-master"
pin_base = "/home/tongshiyu/pin"
instcount = "inscount.out"
numFI = 200
log_path = progname
