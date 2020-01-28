import sys
import os
import re
crash_1 = []
crash_2 = []
finish = []
flag = 0
detected = []
correct = []
sdc = []
unfinishedlist = []
output = []
checkingstring = 'Problem size        =  5'
#checkingstring1 = 'Iteration count     =  306'
checkingstring1 = 'Iteration count     =  306'
#checkingstring2 = 'Final Origin Energy = 1.670602e+05'
checkingstring2 = 'Final Origin Energy = 1.670602e+05'
#checkingstring3 = 'MaxAbsDiff   = 2.546585e-11'
checkingstring3 = 'MaxAbsDiff   = 2.546585e-11'
#checkingstring4 = 'TotalAbsDiff = 6.230039e-11'
checkingstring4 = 'TotalAbsDiff = 6.230039e-11'
#checkingstring5 = 'MaxRelDiff   = 2.178209e-15'
checkingstring5 = 'MaxRelDiff   = 2.178209e-15'
#basedir = "/data/pwu/LULESH3"

for f in os.listdir("."):
    #print f
    if ".py" in f:
        continue
    with open(f,"r") as log:
       flag_sdc = -1000
       flag_output = -1000
       unfinished = 0
       lines = log.readlines()
       flag = 0
       for line in lines:
          if "received" in line and "Segmentation fault" in line:
              flag += 1
          if "Application output" in line:
              flag_sdc = 0
              flag_output = 0
          if flag_output != -1000 and flag_sdc != -1000 :
              if checkingstring in line:
                  flag_output += 1
                  flag_sdc+= 1
              if checkingstring1 in line:
                  flag_output += 1
                  flag_sdc += 1
                #print line
              if checkingstring2 in line:
                  flag_output += 1
                  flag_sdc += 1
              if checkingstring3 in line:
                  flag_output += 1
              if checkingstring4 in line:
                  flag_output += 1
              if checkingstring5 in line:
                  flag_output += 1
              #print line
              #print flag_sdc
              if 'Diff' in line:
                  if 'e-' not in line:
                      flag_sdc -= 1
                      continue
                  parser = line.split('e-')[1]
                  res = re.findall('\d+', parser)
                  if len(res) > 0:
                    #pre = parser.split('-')[1]
                      if int(res[0]) >= 8:
                        #print line
                          flag_sdc += 1
                          #print line
                          #print flag_sdc
       #print flag_sdc
          if "Exit" in line:
              unfinished = 1
          if "Error" in line:
              unfinished = 1
       if unfinished == 1:
           unfinishedlist.append(f)
           continue
       if flag_output < 6 and flag_output != -1000:
           sdc.append(f)
       if flag_sdc < 5 and flag_sdc != -1000:
              detected.append(f)
       if flag_output == 6:
           correct.append(f)     
           
       if flag == 1:
           crash_1.append(f)
       if flag == 2:
           crash_2.append(f)
       if flag == 0:
           finish.append(f)
       #break
print len(crash_1)
print len(crash_2)
print len(finish)
############
print len(sdc)
print len(detected)
print len(unfinishedlist)
print len(list(set(crash_1).difference((set(crash_1) & set(correct)))))
#print list(set(set(crash_1).difference((set(crash_1) & set(correct)))).difference(set(sdc)))
print "### sdc -> detected"
print len(list(set(sdc).difference(set(detected))))
print len(list(set(detected).difference(set(sdc))))
print "#### crash and detected"
print len(list(set(crash_1) & set(detected)))
print "#### crash and sdc"
print len(list(set(crash_1) & set(sdc)))
#print list(set(crash_2) & set(correct))

        
