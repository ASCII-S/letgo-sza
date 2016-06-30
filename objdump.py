import os
import sys
import subprocess
import re


class ObjHandler:
    def __init__(self, executable):
        self.executable = executable

    def runObjdump(self):
        p = subprocess.Popen(['objdump', '-D', self.exectuable], stdout=subprocess.PIPE)
        stdout = p.communicate()
        inst = {}
        for line in stdout:
            ## a line should look like this: 0101f:	00 66 04             	add    %ah,0x4(%rsi)
            if ">:" in line:
                continue
            sublines = line.split(":")
            if len(sublines) == 0:
                print "This line does not contain useful info"
            else:
                pc = sublines[0]
                byte = ""
                res = re.finditer('([0-9A-Fa-f][0-9A-Fa-f] ){1,5}',sublines[1])
                for match in res:
                    byte = match.group(0)
                inst[pc] = byte
        return inst


