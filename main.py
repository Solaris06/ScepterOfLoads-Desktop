import asyncio
import json,  sys, time, argparse, os
from ctypes import windll
from itertools import zip_longest
import datetime as datetime
import ffmpeg
import requests
import os.path as osp
from youtube_dl import YoutubeDL
import shlex
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


def legacy_detect(load, freeze):

    medals = load.copy()
    edits = []
    for l in range(len(load) - 2):
        start, end = load[l]
        if len(medals) > 0 and abs(medals[-1][-1] - start) < 45:
             continue
        subintervals = list(filter(lambda f: f[0] >= start and f[1] <= end, freeze))
        if len(subintervals) > 0:
            f_extra = freeze.index(subintervals[-1])

            if f_extra + 1 < len(freeze) and freeze[f_extra + 1][0] < end:
                subintervals.append(freeze[f_extra + 1])
            if abs(subintervals[0][1] - subintervals[0][0]) < 4 and abs(load[l + 1][0] - start) < 30:

                if len(subintervals) > 1 and abs(subintervals[1][1] - subintervals[1][0]) <= 2.2 and abs(
                        load[l + 2][0] - load[l + 1][-1]) < 5:
                    if abs(start - load[l + 2][0]) > 22.5:
                        print("Skipping Medal: {} -> {}".format(start, load[l + 2][0]))
                        continue
                    else:
                        if abs(load[l + 2][0] - load[l + 1][-1]) < 1.5:
                            print("Deffering Medal: {} -> {}".format(start, load[l + 2][0]))
                        else:
                            print("Medals: {} -> {}".format(start, load[l + 2][0]))

                        if l + 2 < len(load):
                            adj_idx = medals.index(load[l + 2])
                            edits.append(load[l+2])
                            fbefore = list(filter(lambda f: f[0] > load[l + 2][0], g_freezeints))[0]
                            medals[adj_idx][0] = fbefore[0]
                        medals.remove(load[l])
                        medals.remove(load[l + 1])
                        medals.remove(load[l + 2])
                else:
                    if l + 1 < len(load):
                        if load[l + 1] or load[l] not in medals:

                            continue
                        adj_idx = medals.index(load[l + 1])
                        edits.append(load[l + 1])
                        fbefore = list(filter(lambda f: f[0] > load[l+1][0], g_freezeints))[0]
                        medals[adj_idx][0] = fbefore[0]
                    medals.remove(load[l])
                    medals.remove(load[l + 1])
                    
    return medals, edits
def minsec_td(string):
    minutes, seconds = string.split(":")
    return datetime.timedelta(minutes=int(minutes),seconds=int(seconds))
httplink = ""
dims = None
async def hud_pass(prog):
    proc = await asyncio.create_subprocess_exec(prog, stderr=asyncio.subprocess.PIPE)

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

def max_below(t,lst,idx=0):
    return max(filter(lambda intv: intv[idx] < t, lst), key=lambda l: l[0])

def min_above(t,lst,idx=0):
    return min(filter(lambda intv: intv[idx] > t, lst), key=lambda l: l[0])
yt_opts = {"skip_download": True, "match_filter": matchfilter}

parser = argparse.ArgumentParser(description="Removes loads from a sonic '06 speedrun video. Currently only supports Sonic no MSG, but will take others in the future.")
parser.add_argument("link", type=str, help="the link to the run video (both twitch and youtube are supported)")
parser.add_argument("start", type=float, help="the time (in seconds) the run starts.  Go by footage (last frame before fadeout from menu), not by splitter.")
parser.add_argument("resolution", type=str,  help="The output resolution of your entire footage, in wxh form.  (1280x720, for example)")
parser.add_argument("gamelocation", type=str, help="The position of your game footage within your output. Format as w:h:x:y, where x and y are the coordinates of your capture's top left corner.")
parser.add_argument("--L", action="store_true", help="Use if the run in consideration is neither AGM nor all stories.")
parser.add_argument("--splitsio", type=str, nargs='?', help="The 4-character id of the splits.io associated with this run.  Optional, but recommended.")
parser.add_argument("--splitstext", type=str, nargs='?', help="The path to a text file with each split on a new line, formatted as hh:mm:ss.xxx.\nAll values must have trailing zeroes (05.089).")
parser.add_argument("--output", type=str, nargs="?", default="output.csv", help="The results filename. Will be output in .csv form.")
parser.add_argument("--manual", type=str, nargs="?", help="""The duration of the run, as determined by livesplit and/or the verifier. in HH:MM:SS.mmm format.  00:56:02.300 is valid.""")
parser.add_argument("--sonly", type=bool, default="false")
parser.add_argument("--denoise", action="store_true",  help="""Runs a denoise filter (hqdn3d) on the footage before processing.  Use if ends are good but starts are not.""")
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
    splits = [s['realtime_end_ms']/1000 for s in runjson['run']['segments']]
    runduration = splits[-1]
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
    rs = ffmpeg.filter(runstream, "crop", **{"w": w/vidw*dims[0], "h": h/vidh*dims[1], "x": x/vidw*dims[0], "y": y/vidh*dims[1]}).filter("scale", 1280,720)
    w = w/vidw*dims[0]
    h = h/vidh*dims[1]
else:
    if args.denoise:
        rs = ffmpeg.filter(runstream, "crop",
                              **{"w": dims[0], "h": dims[1], "x":0,
                                 "y":0}).filter("scale", 1280,720).filter("hqdn3d")
    else:
        rs = ffmpeg.filter(runstream, "crop",
                              **{"w": dims[0], "h": dims[1], "x":0,
                                 "y":0}).filter("scale", 1280,720)

#first pass
if dims[0] != 1280 or dims[1] != 720:
    w *= dims[0]/1280
    h *= dims[1]/720
rsargs =  rs.crop(width=100,height=30,x=40,y=80).filter("blackdetect", d=.75, pic_th="0.995", pix_th="0.07").output("dbg.mkv").compile()
print(shlex.join(rsargs).replace("'",'"' ))
rsargs = rs.crop(width=100,height=100,x=600,y=400).filter('chromahold',color="#D39D00",similarity="0.075",yuv=False)\
    .filter("chromakey", color="#808080", similarity="0.1", blend="0.005").\
        filter("negate").\
filter("blackdetect",d=1,pix_th="0.25",pic_th="0.45")\
    .output("-",format="null").compile()
print(shlex.join(rsargs).replace("'",'"' ))
rsargs = rs.filter('crop',1280,540).filter("freezedetect", d=0.1, n="-48dB").output("-", format="null").compile()
print(shlex.join(rsargs).replace("'",'"' ))

proc = rs.crop(width=100,height=30,x=40,y=80).filter("blackdetect", d=1, pic_th="0.995", pix_th="0.015").output("-",format="null").run_async(pipe_stderr=True)
loadints = []
for b in proc.stderr:
    b = b.decode("utf-8")
    if "black_" in b:
        nums = b.split(":")[-3:]
        loadinterval = list(map(lambda  n: float(n.split(" ")[0]) + args.start, nums[:2]))
        if len(loadints) % 5 == 0:
            print(("Pass 1: {:02f}% done".format((loadinterval[0]-args.start)/(runduration)*100)))

        loadints.append(loadinterval)
#second pass

medalints = []
mstream = rs.crop(width=100,height=100,x=600,y=400).filter('chromahold',color="#D39D00",similarity="0.075",yuv=False)\
    .filter("chromakey", color="#808080", similarity="0.1", blend="0.005").\
        filter("negate").\
filter("blackdetect",d=1,pix_th="0.25",pic_th="0.45")\
    .output("-",format="null").run_async(pipe_stderr=True)

for b in mstream.stderr:
    b = b.decode("utf-8")
    if "black_" in b:
        nums = b.split(":")[-3:]
        loadinterval = list(map(lambda n: float(n.split(" ")[0]) + args.start, nums[:2]))
        if len(medalints) % 5 == 0:
            print(("Pass 2: {:02f}% done".format((loadinterval[0]-args.start)/(runduration*100))))
        medalints.append(loadinterval)
#third pass
runstream = runstream

cstart = 0
cdur = 0
g_freezeints = []
splitidx = 0
tolerance = .15
minute = 1
loadinterval = []
ffresult = rs.filter('crop',1280,540).filter("freezedetect", d=0.1, n="-48dB").output("-", format="null").run_async(pipe_stderr=True)
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
            g_freezeints.append(list(map(lambda l: l+args.start,loadinterval)))
            if len(g_freezeints) % 15 == 0:
                print("Pass 3: {:02f}% done".format(loadinterval[0]/runduration*100))
        loadinterval = []

endtime = time.time()
tdur = datetime.timedelta(seconds=(endtime-starttime))
print("Total video processing time: {}".format(str(tdur)))

#MSGBOX("Third Pass done, cleaning up + outputting results")



freezeints = []
gstart, _, gend = g_freezeints[0]
for gapl in g_freezeints[1:]:
    ngstart, _, ngend = gapl
    if abs(gend - ngstart) <= tolerance:
        gend = ngend
    else:
        freezeints.append([gstart, gend])
        gstart = ngstart
        gend = ngend






#medal screen cleanup

final_loads = loadints.copy()
shorten_target = []
midx = 0
while midx < len(medalints):
    mstart,mend = medalints[midx]
    if mend-mstart >= 2:

        oldinterval_l = list(filter(lambda i: i[0] < mstart and i[1] > mstart, final_loads))
        if len(oldinterval_l) < 1:
            midx += 1
            continue
        final_loads.remove(oldinterval_l[0])
    midx += 1
extensions = []
#freeze removal, get medal screens out of the data structure too
for m in range(len(final_loads)):
    lstart = final_loads[m][0]
    lend = final_loads[m][1]
    internal_intvs = list(filter(lambda f: (lstart > f[0] and abs(lstart - f[0]) <= 4.2), freezeints))
    if len(internal_intvs) > 0:
        intern = max(internal_intvs, key=lambda i: i[0])
        if intern[0] < lstart:
            if any([i[0] <= (intern[0]) and i[-1] >= (intern[0]) and i[0] != lstart for i in final_loads]):
                print("Skipping interval {}->{}, overlap".format(lstart,lend))
            elif lstart - intern[0] < 2.0:
                print("Adjusting interval by {} s:".format(lstart - intern[0]))

                extensions.append(lstart-intern[0])
                print("Before: {} -> {}".format(lstart, lend))
                final_loads[m][0] = intern[0]
                print("After: {} -> {}".format(intern[0], lend))

final_loads.sort(key=lambda l: l[0])


jsonf = open('dbg.json', 'w+')
json.dump({"loadints": loadints, "medalints": medalints, "freezeints": freezeints, "finalloads": final_loads}, jsonf, indent=2)
jsonf.close()
print("Done with footage, applying to splits...")

#windll.user32.MessageBoxW(0, "Outputting", "Scepter", 0x1000)
loadints_out = list(map(lambda t: [ str(datetime.timedelta(seconds=s)) for s in t], final_loads))
medals_out = list(map(lambda t: [ str(datetime.timedelta(seconds=s)) for s in t], medalints))

with open("res_{}.csv".format(datetime.datetime.now().strftime("%b_%d_%Y_%H_%M_%S")), "w+") as f:
    f.write("Run Begin Timestamp: {}".format(str(datetime.timedelta(seconds=args.start))))
    f.write("\nLoad intervals:\n")
    f.write("\n".join(list(map(lambda i:  ",".join(i), loadints_out))))
    tdstr = datetime.timedelta(seconds=runduration)
    rta_seconds = tdstr.total_seconds()
    loadless_seconds = rta_seconds
    print("RTA Total: {}\n".format(str(datetime.timedelta(seconds=rta_seconds))))
    f.write("\nRTA Total: {}\n".format(str(datetime.timedelta(seconds=rta_seconds))))

    for l in final_loads:
        if l[1] < runduration + args.start:
            loadless_seconds -= abs(l[1]-l[0])
        else:
            loadless_seconds -= (runduration + args.start - l[0])
    print("Loadless Time: {}\n".format(datetime.timedelta(seconds=loadless_seconds)))
    f.write("Loadless Time: {}\n".format(datetime.timedelta(seconds=loadless_seconds)))
final_loads = [list(map(lambda t: t + args.start, fl)) for fl in final_loads]
with open("res_montage.txt", "w") as mf:
    mf.write(""";FFMETADATA1
title=None
major_brand=isom
minor_version=512
compatible_brands=isomiso2avc1mp41
encoder=Lavf58.23.102\n""")
    montage_fmt = "[CHAPTER]\nTIMEBASE=1/1000\nSTART={}\nEND={}\nTITLE=Load {} {}\n"
    loadidx = 1
    mf.write(montage_fmt.format(0, (args.start * 1000), 0, "-1: (Run Start)", "\n"))

    for flidx in range(len(final_loads)-1):
        fls = final_loads[flidx][0] - args.start
        fle = final_loads[flidx][1] - args.start
        mf.write(montage_fmt.format(int(fls*1000), int(fls*1000)+1, flidx*2, "Start") + "\n")
        mf.write(montage_fmt.format(int(fle*1000), int(fle*1000)+1, flidx*2+1, "End") + "\n")














