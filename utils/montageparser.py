import re,csv
from datetime import datetime, timedelta
from itertools import zip_longest

start_re = r'START=([\d\.]+)'
end_re = r'Ending at ([\d\.:]+)'
BASE = datetime(1900,1,1,0,0,0,0)
def parsets(dat):
    if "." in dat:
        return (datetime.strptime(dat, "%H:%M:%S.%f") - BASE).total_seconds()
    else:
        return (datetime.strptime(dat, "%H:%M:%S") - BASE).total_seconds()

if __name__ == "__main__":
    montage = open('../res_montage.txt').read()
    alls_matches = re.findall(start_re, montage)
    alle_matches = re.findall(end_re, montage)
    starts = [float(s)/1000 for s in alls_matches]
    ends = [parsets(e) for e in alle_matches]
    with open('montage_out.csv', 'w') as csvf:
        csvf.write("start,end\n")
        for s,e in zip_longest(starts,ends,fillvalue='-'):
            if s == "-" or e == "-":
                break
            csvf.write("{},{}\n".format(s,e))

    print("Done")
