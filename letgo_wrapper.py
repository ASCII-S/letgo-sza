import sys
import os, errno
import sighandler
import faultinject
import configure
import subprocess
import time

timeout = 500


#obtain the total number of dynamic instructions

def execute(execlist,out,err):

        outFile = open(out,"w")
        errFile = open(err,"w")
        print ' '.join(execlist)
        p = subprocess.Popen(execlist, stdout=outFile,stderr=errFile)
        elapsetime = 0
        while (elapsetime < timeout):
            elapsetime += 1
            time.sleep(1)
            #print p.poll()
            if p.poll() is not None:
                print "\t program finish", p.returncode
                print "\t time taken", elapsetime
                return str(p.returncode)
        outFile.close()
        errFile.close()
        print "\tParent : Child timed out. Cleaning up ... "
        p.kill()
        return "timed-out"


def silentremove(filename):
    try:
        os.remove(filename)
    except OSError as e: # this would be "except OSError, e:" before Python 2.6
        if e.errno != errno.ENOENT: # errno.ENOENT = no such file or directory
            raise # re-raise exception if a different error occured


instcount = configure.pin_base+"/source/tools/ManualExamples/obj-intel64/inscount0.so"

execlist = [configure.pin_home,"-t",instcount,"--",configure.benchmark]

for item in configure.args:
    execlist.append(item)


out = "sampleout"
err = "sampleerr"

execute(execlist,out,err)

if not os.path.isfile(instcount):
    print "No instcount file! Exit"
    sys.exit(1)

totalcount = ""
with open(configure.instcount,"r") as f:
    lines = f.readlines()
    if len(lines) > 1:
        print "Error while loading inst count."
        sys.exit(1)
    count = lines[0]
    count = count.rstrip("\n")
    print count
    totalcount = count.split(" ")[1]


for i in range(0,configure.numFI):
    sys.stdout = sys.__stdout__
    print "Test "+str(i)
    sig = sighandler.SigHandler(totalcount,i)
    for item in configure.outputfile:
        try:
            os.remove(item)
            print "remove output file in the wrapper"
        except:
            print "Oops, no "+item+" file found. Ignore in wrapper"
    sig.executeProgram()
    #clean up for next round
    silentremove(faultinject.instructionfile)
    silentremove(faultinject.iterationfile)
    silentremove(faultinject.nextpcfile)
    for item in configure.outputfile:
        try:
            os.rename(item,item+"-"+str(i))
        except:
            print "Oops, no "+item+" file found. Ignoring"







