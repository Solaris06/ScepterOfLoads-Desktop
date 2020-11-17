import json, datetime, sys, csv, time, argparse
from ctypes import windll

import datetime as datetime
import ffmpeg
import requests
import os.path as osp
from youtube_dl import YoutubeDL

DEBUG = False
VIDEO = True
def MSGBOX(msg):
    windll.user32.MessageBoxW(0,msg,"Scepter-Desktop",0x1000)

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
httplink = ""
def matchfilter(idict):
    global httplink
    formats = idict['formats']
    fmt = list(filter(lambda f: f.get('width') == 1280 and f.get('ext') == 'mp4', formats))
    if httplink == "":
        httplink = fmt[0]['url']
        j = open('infojson.json','w')
        json.dump(idict, j, indent=2)
        return "Ye"
    return "Nah"
yt_opts = {"skip_download": True, "match_filter": matchfilter}

parser = argparse.ArgumentParser(description="Removes loads from a sonic '06 speedrun video. Currently only supports Sonic no MSG, but will take others in the future.")
parser.add_argument("link", type=str, help="the link to the run video (both twitch and youtube are supported)")
parser.add_argument("start", type=float, help="the time (in seconds) the run starts.  Go by footage (last frame before fadeout from menu), not by splitter.")
parser.add_argument("resolution", type=str,  help="The output resolution of your entire footage, in wxh form.  (1280x720, for example)")
parser.add_argument("gamelocation", type=str, help="The position of your game footage within your output. Format as w:h:x:y, where x and y are the coordinates of your capture's top left corner.")
parser.add_argument("--splitsio", type=str, nargs='?', help="The 4-character id of the splits.io associated with this run.  Optional, but recommended.")
parser.add_argument("--splitstext", type=str, nargs='?', help="The path to a text file with each split on a new line, formatted as hh:mm:ss.xxx.\nAll values must have trailing zeroes (05.089).")
parser.add_argument("--output", type=str, nargs="?", default="output.csv", help="The results filename. Will be output in .csv form.")
parser.add_argument("--manual", type=str, nargs="?", help="""The path to the csv file containing results. provided no splits.io id is specified.  Format your .csv like this:
First line: name,time,medals
Other lines below:Mission 1,01:50.200,0
All missions have 0 medals.  2 if you S-rank, 1 if you A-D rank, 0 if you gold medal skip.""")
parser.add_argument("--sonly", type=bool, default="false")
args = parser.parse_args(sys.argv[1:])
runresp = None
category = ""
rankadjust = []
cat_ranks = {"Silver": [2, 2, 1, 2, 2, 1, 1, 2, 0, 1, 2, 2, 0, 0, 1, 2, 2, 0],
             "Sonic": [0, 1, 2, 1, 2, 0, 0, 0, 1, 1, 1, 2, 1, 2, 1, 1, 0, 0, 0, 1, 1, 0]}

splitnames = []
splits = []

runduration = -1
if args.splitsio:
    sio_id = args.splitsio
    runresp = requests.get("https://splits.io/api/v4/runs/{}".format(sio_id))
    print("splits.io status code: {}".format(runresp.status_code))
    runjson = runresp.json()
    category = runjson['run']['category']['name']
    splitnames = [runjson['run']['segments'][i]['display_name'] for i in range(len(runjson['run']['segments']))]
    splits = [s['realtime_end_ms'] for s in runjson['run']['segments']]
    runduration = splits[-1]/1000
    for n, radj in cat_ranks.items():
        if n in category:
            rankadjust = radj
            break
elif args.manual:
    if not osp.exists(args.manual):
        print("File {} not found, check pathname".format(args.manual))
        raise FileNotFoundError
    with open(args.manual) as csvf:
        splits = []
        cread = csv.DictReader(csvf)
        for row in cread:
            splitnames.append(row['name'])
            microsecond_row = row['time'] + "000"
            dtver = datetime.datetime.strptime(row['time'], "%M:%S.%f")
            rankadjust.append(int(row['medals']))
            splits.append(datetime.timedelta(minutes=dtver.minute, seconds=dtver.second, microseconds=dtver.microsecond))
        runduration = splits[-1].total_seconds()

load_intervals = []
runvid_link = args.link
vidw, vidh = map(int, args.resolution.split("x"))
w,h,x,y = map(int, args.gamelocation.split(":"))
starttime = time.time()

if "http" in runvid_link:
    with YoutubeDL(yt_opts) as yt:
        yt.download([runvid_link])
        runvid_link = httplink
probe = ffmpeg.probe(args.link)
video_stream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'video'), None)
dims = (int(video_stream['width']), int(video_stream['height']))
runstream = ffmpeg.input(runvid_link).trim(start=args.start,end=args.start+runduration+3.5).setpts('PTS-STARTPTS')
if w != vidw or h != vidh:
    #filterfmt = "[v]crop={}*iw:{}*ih:{}*iw:ih*{}[c],[c]freezedetect=n=-53dB:d=0.2[out],[out]nullsink"
    floatfmt = "{:04.2f}"
    widthratio = str(w/vidw).format(floatfmt) + "*iw"
    heightratio = str(h/vidh * .7).format(floatfmt) + "*ih"
    xratio = str(x/vidw).format(floatfmt) + "*iw"
    yratio = str(y/vidh).format(floatfmt) + "*ih"
    runstream = ffmpeg.filter(runstream, "crop", **{"w": w/vidw*dims[0], "h": h/vidh*dims[1], "x": x/vidw*dims[0], "y": y/vidh*dims[1]})
    w = w/vidw*dims[0]
    h = h/vidh*dims[1]
else:
    w,h  = dims
#first pass
proc = runstream.crop(width=w//16,height=h//18,x=w//64,y=h//9).filter("blackdetect", d=1, pic_th="0.995", pix_th="0.12").output("-", format="null").run_async(pipe_stderr=True)
loadints = []
for b in proc.stderr:
    b = b.decode("utf-8")
    print(b)
    if "black_" in b:
        nums = b.split(":")[-3:]
        loadinterval = [float(n.split(" ")[0]) for n in nums[:2]]
        if int(loadinterval[0]) % 60 <= 2:
            print("Pass 1: {} minutes in".format(int(loadinterval[0]) // 60))

        loadints.append(loadinterval)
MSGBOX("darkness detection finished")
#second pass
runstream = runstream.trim(start=args.start,end=args.start+runduration+3.5).setpts('PTS-STARTPTS').filter("freezedetect", d=0.2, n="-53dB").output("-", format="null")

cstart = 0
cdur = 0
freezeints = []
splitidx = 0
tolerance = .6
minute = 1
loadinterval = []
ffresult = ffmpeg.run_async(runstream, pipe_stderr=True)
for l in ffresult.stderr:
    l = l.decode("utf-8")
    if "start" in l and clean_freezeline(l) > args.start+runduration+3.5:
        break
    elif "start" in l and len(loadinterval) == 0:
        cline = clean_freezeline(l)
        if cline > 0 and cline not in [i[0] for i in freezeints]:
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
            freezeints.append(loadinterval)
            if int(loadinterval[0] / 60) % 60 == 0:
                print("Pass 2: {} minutes in".format(int(loadinterval[0] / 60)))

        loadinterval = []

endtime = time.time()
tdur = datetime.timedelta(seconds=(endtime-starttime))
print("Total video processing time: {}".format(str(tdur)))

MSGBOX("Second Pass done, cleaning up + outputting results")
#gap cleanup

freezeints =list(map(lambda td:  [td[0], td[2]], freezeints))
#medal screen cleanup
medalscreens = []
for l in range(len(loadints)-1):
    start, end = loadints[l]
    if len(medalscreens) > 0 and abs(medalscreens[-1][-1] - start) < 45:
        continue
    subintervals = list(filter(lambda f: f[0] >= start and f[1] <= end, freezeints))
    if len(subintervals) > 0:
        f_extra = freezeints.index(subintervals[-1])

        if f_extra + 1 < len(freezeints) and freezeints[f_extra+1][0] < end:
            subintervals.append(freezeints[f_extra+1])
        if abs(subintervals[0][1] - subintervals[0][0]) < 2.5 and abs(loadints[l+1][0] - start) < 30:
            if len(subintervals) > 1 and abs(subintervals[1][1] - subintervals[1][0]) < 2.5 and abs(
                    loadints[l + 2][0] - loadints[l + 1][-1]) < 5:
                medalscreens.append([start, loadints[l+2][0]])
                print("Medals: {} -> {}".format(start, loadints[l+2][0]))
            else:
                medalscreens.append([start, loadints[l+1][0]])
                print("Medals: {} -> {}".format(start, loadints[l+1][0]))

print("Done with footage, applying to splits...")
for fg in freezeints:
    fstart, fend = fg
    for b in range(len(loadints)):
        if fstart < loadints[b][0] and fend >= loadints[b][0]:
            if abs(loadints[b][0] - fstart) <= 2:
                #print("[DEBUG] Adjusted interval: {} -> {}".format(loadints[b][0], fstart))  # log it
                loadints[b][0] = fstart #add the entire duration of the freeze + the gap between, only for small gaps
                break
windll.user32.MessageBoxW(0, "Outputting", "Scepter", 0x1000)
loadints_out = list(map(lambda t: [ str(datetime.timedelta(seconds=s+args.start)) for s in t], loadints))
freezeints_out = list(map(lambda t: [ str(datetime.timedelta(seconds=s+args.start)) for s in t], freezeints))
medalscreens_out = list(map(lambda t: [ str(datetime.timedelta(seconds=s+args.start)) for s in t], medalscreens))
with open("res_verbose.csv", "w") as dbgf:
    dbgf.write("Black Screen Detections:\n")
    dbgf.write("\n".join(list(map(lambda i: ",".join(i), loadints_out))))
    dbgf.write("\n---\nFreeze Detections:\n")
    dbgf.write("\n".join(list(map(lambda i:  ",".join(i), freezeints_out))))
    dbgf.write("\n---\nMedal Screens:\n")
    dbgf.write("\n".join(list(map(lambda i:  ",".join(i), medalscreens_out))))



with open("res.csv", "w") as f:
    f.write("Run Begin Timestamp: {}".format(str(datetime.timedelta(seconds=args.start))))
    f.write("\nMedal Screens (added back into RTA):\n")
    f.write("\n".join(list(map(lambda i:  ",".join(i), medalscreens_out))))
    tdstr = datetime.timedelta(seconds=runduration)
    rta_seconds = tdstr.total_seconds()
    loadless_seconds = rta_seconds
    print("RTA Total: {}".format(str(datetime.timedelta(seconds=rta_seconds))))
    for l in loadints:
        loadless_seconds -= l[1]-l[0]
    print("RTA No loads no medals: {}\n".format(str(datetime.timedelta(seconds=loadless_seconds))))
    for m in medalscreens:
        loadless_seconds += m[1]-m[0]
    #add back the medal screens later
    f.write("Run Loadless Time: {}\n".format(datetime.timedelta(seconds=loadless_seconds)))







