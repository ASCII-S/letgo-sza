import sys
import os
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

instcount = configure.pin_base+"/source/tools/ManualExamples/obj-intel64/inscount0.so"

execlist = [configure.pin_home,"-t",instcount,"--",configure.benchmark,configure.args]

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
    print "Test"
    print totalcount
    sig = sighandler.SigHandler(totalcount,i)
    sig.executeProgram()







