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
dims = None
def matchfilter(idict):
    global httplink, dims
    formats = idict['formats']
    fmt = list(filter(lambda f: f.get('width') is not None and f.get('width') <= 1280, formats))
    if httplink == "":
        httplink = fmt[-1]['url']
        j = open('infojson.json','w')
        dims = (fmt[-1]['width'], fmt[-1]['height'])
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
parser.add_argument("--manual", type=str, nargs="?", help="""The duration of the run, as determined by livesplit and/or the verifier. in HH:MM:SS.mmm format.  00:56:02.300 is valid.""")
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
    split_t = args.manual.split(":")
    h = int(split_t[0])
    m = int(split_t[1])
    s = float(split_t[2])
    runduration = 3600*h + 60*m + s

load_intervals = []
runvid_link = args.link
vidw, vidh = map(int, args.resolution.split("x"))
w,h,x,y = map(int, args.gamelocation.split(":"))
starttime = time.time()

if "http" in runvid_link:
    with YoutubeDL(yt_opts) as yt:
        yt.download([runvid_link])
        runvid_link = httplink
else:
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
    runstream = ffmpeg.filter(runstream, "crop", **{"w": w/vidw*dims[0], "h": h/vidh*dims[1]*.7, "x": x/vidw*dims[0], "y": y/vidh*dims[1]})
    w = w/vidw*dims[0]
    h = h/vidh*dims[1]
else:
    runstream = ffmpeg.filter(runstream, "crop",
                              **{"w": dims[0], "h": dims[1] * .7, "x":0,
                                 "y":0})
#first pass
if dims[0] != 1280 or dims[1] != 720:
    w *= dims[0]/1280
    h *= dims[1]/720
proc = runstream.setpts('PTS-STARTPTS').crop(width=w//16,height=h//18,x=w//64,y=h//9).filter("blackdetect", d=1, pic_th="0.995", pix_th="0.1").output("-", format="null").run_async(pipe_stderr=True)
loadints = []
for b in proc.stderr:
    b = b.decode("utf-8")
    if "black_" in b:
        nums = b.split(":")[-3:]
        loadinterval = [float(n.split(" ")[0]) for n in nums[:2]]
        if len(loadints) % 5 == 0:
            print(("Pass 1: {:02f}% done".format(loadinterval[0]/runduration*100)))

        loadints.append(loadinterval)


#second pass
runstream = runstream.filter("freezedetect", d=0.2, n="-53dB").output("-", format="null")

cstart = 0
cdur = 0
g_freezeints = []
splitidx = 0
tolerance = 1
minute = 1
loadinterval = []
ffresult = ffmpeg.run_async(runstream, pipe_stderr=True)
for l in ffresult.stderr:
    l = l.decode("utf-8")
    if "start" in l and clean_freezeline(l) > args.start+runduration+3.5:
        break
    elif "start" in l and len(loadinterval) == 0:
        cline = clean_freezeline(l)
        if cline > 0 and cline not in [i[0] for i in g_freezeints]:
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
            loadinterval.append(clean_freezeline(l))
            g_freezeints.append(loadinterval)
            if len(g_freezeints) % 15 == 0:
                print("Pass 2: {:02f}% done".format(loadinterval[0]/runduration*100))
        loadinterval = []

endtime = time.time()
tdur = datetime.timedelta(seconds=(endtime-starttime))
print("Total video processing time: {}".format(str(tdur)))

MSGBOX("Second Pass done, cleaning up + outputting results")
#gap cleanup
freezeints = []
gstart, _, gend = g_freezeints[0]
for gapl in g_freezeints[1:]:
    ngstart, _, ngend = gapl
    if abs(gend - ngstart) <= 1:
        gend = ngend
    else:
        freezeints.append([gstart, gend])
        gstart = ngstart
        gend = ngend
#medal screen cleanup
medalscreens = []
for l in range(len(loadints)-2):
    start, end = loadints[l]
    if len(medalscreens) > 0 and abs(medalscreens[-1][-1] - start) < 45:
        continue
    subintervals = list(filter(lambda f: f[0] >= start and f[1] <= end, freezeints))
    if len(subintervals) > 0:
        f_extra = freezeints.index(subintervals[-1])

        if f_extra + 1 < len(freezeints) and freezeints[f_extra+1][0] < end:
            subintervals.append(freezeints[f_extra+1])
        if abs(subintervals[0][1] - subintervals[0][0]) < 4 and abs(loadints[l+1][0] - start) < 30:

            if len(subintervals) > 1 and abs(subintervals[1][1] - subintervals[1][0]) <= 2.2 and abs(
                    loadints[l + 2][0] - loadints[l + 1][-1]) < 5:
                if abs(start - loadints[l+2][0]) > 22.5:
                    print("SKipping Medal: {} -> {}".format(start, loadints[l+2][0]))
                elif abs(loadints[l+2][0] - loadints[l+1][-1]) < 1.5:
                    print("Deffering Medal: {} -> {}".format(start, loadints[l + 2][0]))
                    medalscreens.append([start, loadints[l + 2][0]])
                else:
                    medalscreens.append([start, loadints[l+2][0]])
                    print("Medals: {} -> {}".format(start, loadints[l+2][0]))
            else:
                if abs(start - loadints[l + 1][0]) > 22.5:
                    print("Skipping Medal: {} -> {}".format(start, loadints[l + 1][0]))
                else:
                    medalscreens.append([start, loadints[l + 1][0]])
                    print("Medals: {} -> {}".format(start, loadints[l + 1][0]))
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



with open("res_{}.csv".format(datetime.datetime.now().strftime("%b_%d_%Y_%H_%M_%S")), "w") as f:
    f.write("Run Begin Timestamp: {}".format(str(datetime.timedelta(seconds=args.start))))
    f.write("\nMedal Screens (added back into RTA):\n")
    f.write("\n".join(list(map(lambda i:  ",".join(i), medalscreens_out))))
    tdstr = datetime.timedelta(seconds=runduration)
    rta_seconds = tdstr.total_seconds()
    loadless_seconds = rta_seconds
    print("RTA Total: {}".format(str(datetime.timedelta(seconds=rta_seconds))))
    f.write("RTA Total: {}\n".format(str(datetime.timedelta(seconds=rta_seconds))))

    for l in loadints:
        loadless_seconds -= abs(l[1]-l[0])
    print("Loadless+Medal-Less Time: {}\n".format(datetime.timedelta(seconds=loadless_seconds)))
    f.write("Loadless+Medal-Less Time: {}\n".format(datetime.timedelta(seconds=loadless_seconds)))
    for m in medalscreens:
        loadless_seconds += abs(m[1]-m[0])
    #add back the medal screens later
    print("Loadless Time: {}\n".format(datetime.timedelta(seconds=loadless_seconds)))
    f.write("Loadless Time: {}\n".format(datetime.timedelta(seconds=loadless_seconds)))








