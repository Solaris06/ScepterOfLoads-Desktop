import subprocess, json, datetime, sys, csv, time, argparse
import srcomapi.datatypes as dtypes
import srcomapi
import ffmpeg
import requests, tqdm
import os.path as osp
sys.path.append(osp.join(osp.dirname(__file__), "lib"))

DEBUG = False
VIDEO = True
def clean_freezeline(line):
    line = line.strip().split(" ")[-1]
    if "x" in line:
        line = line.replace("x", 0)
    try:
        fline = float(line)
        return fline
    except ValueError:
        return -1
def minsec_td(string):
    minutes, seconds = string.split(":")
    return datetime.timedelta(minutes=int(minutes),seconds=int(seconds))

parser = argparse.ArgumentParser(description="Removes loads from a sonic '06 speedrun video. Currently only supports Sonic no MSG, but will take others in the future.")
parser.add_argument("link", type=str, help="the link to the run video (both twitch and youtube are supported)")
parser.add_argument("start", type=float, help="the time (in seconds) the run starts.  Go by footage (last frame before fadeout from menu), not by splitter.")
parser.add_argument("resolution", type=str,  help="The output resolution of your entire footage, in wxh form.  (1280x720, for example)")
parser.add_argument("gamelocation", type=str, help="The position of your game footage within your output. Format as w:h:x:y, where x and y are the coordinates of your capture's top left corner.")
parser.add_argument("--splitsio", type=str, nargs='?', help="The 4-character id of the splits.io associated with this run.  Optional, but recommended.")
parser.add_argument("--splitstext", type=str, nargs='?', help="The path to a text file with each split on a new line, formatted as hh:mm:ss.xxx.\nAll values must have trailing zeroes (05.089).")
parser.add_argument("--output", type=str, nargs="?", default="output.csv", help="The results filename. Will be output in .csv form.")
parser.add_argument("--sonly", type=bool, default="false")
args = parser.parse_args(sys.argv[1:])
runresp = None
if args.splitsio:
    sio_id = args.splitsio
    runresp = requests.get("https://splits.io/api/v4/runs/{}".format(sio_id))
    print("splits.io status code: {}".format(runresp.status_code))
    runjson = runresp.json()
if not DEBUG:
    if args.splitsio:
        sio_id = args.splitsio
        runresp = requests.get("https://splits.io/api/v4/runs/{}".format(sio_id))
        print("splits.io status code: {}".format(runresp.status_code))
        runjson = runresp.json()
        duration_ms = runjson['run']['segments'][-1]['realtime_end_ms']
        duration_s = str(duration_ms/1000)
    else:
        duration_s = str(60*60)
    load_intervals = []
    splits = []
    MANUAL = False
    if VIDEO:
        runvid_link = args.link

        vidw, vidh = map(int, args.resolution.split("x"))
        w,h,x,y = map(int, args.gamelocation.split(":"))
        #ytdl_path = osp.join(osp.dirname(__file__), "youtube-dl")
        #ytdl_path = "youtube-dl"
        starttime = time.time()

        if "http" in runvid_link:
            ytdl_res = subprocess.run(["youtube-dl","-g",runvid_link],stdout=subprocess.PIPE,encoding="utf-8")
            runvid_link = ytdl_res.stdout.split("\n")[0]
        runstream = ffmpeg.input(runvid_link)
        if w != vidw or h != vidh:
            #filterfmt = "[v]crop={}*iw:{}*ih:{}*iw:ih*{}[c],[c]freezedetect=n=-53dB:d=0.2[out],[out]nullsink"
            floatfmt = "{:04.2f}"
            widthratio = str(w/vidw).format(floatfmt) + "*iw"
            heightratio = str(h/vidh * .7).format(floatfmt) + "*ih"
            xratio = str(x/vidw).format(floatfmt) + "*iw"
            yratio = str(y/vidh).format(floatfmt) + "*ih"
            runstream = ffmpeg.filter(runstream, "crop", **{"w": widthratio, "h": heightratio, "x": xratio, "y": yratio})

        runstream = ffmpeg.filter(runstream, "freezedetect", **{"d": .2, "n": "-53dB"})
        cstart = 0
        cdur = 0
        loads = 0
        splitidx = 0
        tolerance = 1.05
        last_end = -1
        minute = 1
        loadinterval = []


        for l in ffresult.stderr:

            if l.startswith("[freezedetect"):
                if "start" in l and clean_freezeline(l) > (datetime.timedelta(minutes=49)).total_seconds():
                    break
                elif "start" in l and len(loadinterval) == 0:
                    cline = clean_freezeline(l)
                    if cline > 0 and cline not in [i[0] for i in load_intervals]:
                        loadinterval.append(clean_freezeline(l))
                elif "duration" in l and len(loadinterval) == 1:
                    cline = clean_freezeline(l)
                    if cline > 0:
                        loadinterval.append(cline)
                    else:
                        loadinterval = []
                        continue
                elif "end" in l and len(loadinterval) == 2:
                    if clean_freezeline(l) > 0:
                        loadinterval.append(loadinterval[0] + loadinterval[1])
                        load_intervals.append(loadinterval)
                        if loadinterval[0]/60 >= minute:
                            print("Progress: {} minutes in".format(minute))
                            minute+= 1
                    loadinterval = []
            else:
                print(l)
        endtime = time.time()
        tdur = datetime.timedelta(seconds=(endtime-starttime))
        print("Total processing time: {}".format(str(tdur)))


        #gap cleanup
        nogaps = []
        nogaps_nums = []
        gstart, gdur, gend = load_intervals[0]
        for gapl in load_intervals[1:]:
            ngstart, ngdur, ngend = gapl
            if abs(gend - ngstart) <= tolerance:
                gdur += ngdur
                gend = ngend
            else:
                nogaps.append("{},{},{}\n".format(gstart, gdur, gend))
                nogaps_nums.append([gstart,gdur,gend])
                gstart = ngstart
                gend = ngend
                gdur = ngdur


                #print("Total: {}".format(dur))
    with open('nick_5458_debug2.csv', "w")  as dbgf:
        dbgf.write("start,duration,end\n")
        dbgf.write("".join(nogaps))

if DEBUG:
    tolerance = 1
    allintervals = open("nick_5458_debug2.csv", 'r').readlines()
    load_intervals = [list(map(float, s[:-1].split(","))) for s in allintervals[1:]]
    nogaps = []
    nogaps_nums = []
    gstart, gdur, gend = load_intervals[0]
    for gapl in load_intervals[1:]:
        ngstart, ngdur, ngend = gapl
        if abs(gend - ngstart) <= tolerance:
            gdur += ngdur
            gend = ngend
        else:
            nogaps.append("{},{},{}\n".format(gstart, gdur, gend))
            nogaps_nums.append([gstart, gdur, gend])
            gstart = ngstart
            gend = ngend
            gdur = ngdur

print("Done with footage, applying to splits...")
if runresp is not None:
    splitnames = [runjson['run']['segments'][i]['display_name'] for i in range(len(runjson['run']['segments']))]

    rankadjust = [2, 2, 1, 2, 2, 1, 1, 2, 0, 1, 2, 2, 0, 0, 1, 2, 2, 0] #trials skip
    flamecoreidx = 10
    splits = [s['realtime_end_ms'] for s in runjson['run']['segments']]
    splits = list(map(lambda s: datetime.timedelta(milliseconds=s), splits))
    formatted_splits = list(map(str, splits))
    seconds_splits = list(map(lambda s: s.total_seconds(), splits))
    for i in range(len(splits)):
        if rankadjust[i] == 0:
            continue
        print("Split name: {}".format(splitnames[i]))
        ctime = seconds_splits[i]

        preresults = ctime - 6 * rankadjust[i]
        potentialsplits = sorted(load_intervals, key=lambda li: abs(li[0] - preresults))

        residx = load_intervals.index(potentialsplits[0])
        if i == flamecoreidx and not args.sonly:
            climbs = 0
            while load_intervals[residx-climbs][1] < 10:
                climbs += 1
            climbidx = residx - climbs + 1
            restart = load_intervals[residx][0]
            while load_intervals[climbidx][0] < restart and load_intervals[climbidx][1] < 5:
                print("FC : {}".format(load_intervals[climbidx]))
                del load_intervals[climbidx]
                residx -= 1
        if load_intervals[residx][0] < preresults:
            residx += 1
        while rankadjust[i] > 0  and residx < len(load_intervals) and load_intervals[residx][0] < ctime:
            cduration = load_intervals[residx][1]
            if cduration >= 3:
                break
            else:
                print(load_intervals[residx])
                del load_intervals[residx]
                rankadjust[i] -= 1
loadless_splits = []
loads = 0
k = 0
for i in range(len(seconds_splits)):
    if k >= len(load_intervals):
        break
    while k < len(load_intervals) and load_intervals[k][0] < seconds_splits[i]:
        loads += load_intervals[k][1]
        k += 1
        if k >= len(load_intervals):
            break
    loadless_splits.append(seconds_splits[i] - loads)
output_text = []
outf = open('focus_4725.csv', 'w')
outf.write("Split,RTA,Loadless,Loads\n")
datlist = []
for n in range(len(loadless_splits)):
    if seconds_splits[n] == 0:
        continue

    print("{}: {} / {}".format(splitnames[n], datetime.timedelta(seconds=seconds_splits[n]), datetime.timedelta(seconds=loadless_splits[n])))
    datlist = [splitnames[n], datetime.timedelta(seconds=seconds_splits[n]), datetime.timedelta(seconds=loadless_splits[n])]
    outf.write("{},{},{}\n".format(*datlist))
outf.close()






