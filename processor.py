import asyncio
import json,  sys, time, argparse, re
from tqdm import tqdm
from ctypes import windll
from itertools import zip_longest
import datetime as datetime
import ffmpeg
import ffmpeg as ffmpeg
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


BOX = [100,20,40,80]
MEDAL = [600,400,100,100]


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

    return medals,
TQDM_RBAR = "| Time Elapsed: {elapsed}}"
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
        j = open('infojson.json','w+')
        dims = (fmt[-1]['width'], fmt[-1]['height'])
        json.dump(idict, j, indent=2)
        return "yt stream retrieved"
    return "Nah"

def max_below(t,lst,idx=0):
    return max(filter(lambda intv: intv[idx] < t, lst), key=lambda l: l[0])

def min_above(t,lst,idx=0):
    return min(filter(lambda intv: intv[idx] > t, lst), key=lambda l: l[0])
yt_opts = {"skip_download": True, "match_filter": matchfilter}



def argless_test():
    global httplink, duration
    start = 2.667
    sio_id = "6jnu"
    runresp = requests.get("https://splits.io/api/v4/runs/{}".format(sio_id))
    if runresp.status_code == 200:
        print("splits.io request success")
    else:
        print("splits.io request failure: code " + str(runresp.status_code))
    runjson = runresp.json()
    splits = [s['realtime_end_ms']/1000 for s in runjson['run']['segments']]
    duration = splits[-1]
    runvid_link = "https://youtu.be/7cTZ1xp40ys"
    starttime = time.time()
    with YoutubeDL(yt_opts) as yt:
        yt.download([runvid_link])
    runvid_link = httplink
    rs = ffmpeg.input(runvid_link,ss=start,t=duration+5)
    RES = [1280,720]
    w,h,x,y = [900,506,380,0]
    boxdict = {"width": 100, "height": 20, "x": 40, "y": 80}
    medaldict = {"width": 100, "height": 100, "x": 600, "y":400}
    if w != 1280 or h != 720:
        scalefactor = w/1280
        for k,v in boxdict.items():
            boxdict[k] = int(boxdict[k]*scalefactor)
        for k,v in medaldict.items():
            medaldict[k] = int(medaldict[k]*scalefactor)
    boxdict['x'] += x
    boxdict['y'] += y
    medaldict['x'] += x
    medaldict['y'] += y
    loadints = darkness_pass(rs,boxdict)
    medalints = medal_pass(rs,medaldict)
    g_freezeints = freeze_pass(rs,duration+5, w,h,x,y)
    endtime = time.time()
    tdur = datetime.timedelta(seconds=(endtime-starttime))
    print("Total video processing time: {}".format(str(tdur)))

    cstart = 0
    cdur = 0
    splitidx = 0
    tolerance = .1
    minute = 1
    lstart = -1
    lend = -1



    freezeints = []
    gstart, gend = g_freezeints[0]
    for gapl in g_freezeints[1:]:
        ngstart, ngend = gapl
        if abs(gend - ngstart) <= tolerance:
            gend = ngend
        else:
            freezeints.append([gstart, gend])
            gstart = ngstart
            gend = ngend

    print("{} Screen freezes".format(len(freezeints)))

    #medal screen cleanup

    final_loads = loadints.copy()
    loadints_out = list(map(lambda t: [ str(datetime.timedelta(seconds=s+start)) for s in t], final_loads))
    with open("res_{}.csv".format(datetime.datetime.now().strftime("%b_%d_%Y_%H_%M_%S")), "w+") as f:
        f.write("Run Begin Timestamp: {}".format(str(datetime.timedelta(seconds=start))))
        f.write("\nLoad intervals:\n")
        f.write("\n".join(list(map(lambda i:  ",".join(i), loadints_out))))
        tdstr = datetime.timedelta(seconds=duration)
        rta_seconds = tdstr.total_seconds()
        loadless_seconds = rta_seconds
        print("RTA Total: {}\n".format(str(datetime.timedelta(seconds=rta_seconds))))
        f.write("\nRTA Total: {}\n".format(str(datetime.timedelta(seconds=rta_seconds))))

        for l in final_loads:
            if l[1] <= duration:
                loadless_seconds -= abs(l[1]-l[0])
            else:
                loadless_seconds -= (duration - l[0])
        print("Loadless Time: {}\n".format(datetime.timedelta(seconds=loadless_seconds)))
        f.write("Loadless Time: {}\n".format(datetime.timedelta(seconds=loadless_seconds)))
    with open("res_montage.txt", "w") as mf:
        mf.write(""";FFMETADATA
    title=None
    major_brand=isom
    minor_version=512
    compatible_brands=isomiso2avc1mp41
    encoder=Lavf58.23.102\n""")
        montage_fmt = "[CHAPTER]\nTIMEBASE=1/1000\nSTART={}\nEND={}\nTITLE=Load {} {}\n"
        mf.write(montage_fmt.format(0, (start * 1000), 0, "-1: (Run Start)", "\n"))

        for flidx in range(len(final_loads)-1):
            fls = final_loads[flidx][0] + start
            fle = final_loads[flidx][1] + start
            mf.write(montage_fmt.format(int(fls*1000), int(fls*1000)+1, flidx, "Start") + "\n")
            mf.write(montage_fmt.format(int(fle*1000), int(fle*1000)+1, flidx, "End") + "\n")

    total_t = time.time() - starttime
    MSGBOX("Results computed in {}".format(str(datetime.timedelta(seconds=total_t))))

def darkness_pass(stream,box,pct="0.98",thr=".09"):
    global duration
    procs = stream.crop(**box).filter("hqdn3d").filter("colorchannelmixer",.95,0,0,0,.95,0,0,0,1.2,0,0).filter("blackdetect", d=1, pic_th=pct, pix_th=thr).output("-",format="null")
    proc = procs.run_async(pipe_stderr=True)
    loadints = []
    last_lint = 0
    with tqdm(total=duration,desc="Pass 1 of 3",bar_format="{l_bar}{bar}" + TQDM_RBAR, file=sys.stdout) as t:
        for b in proc.stderr:
            b = b.decode("utf-8")
            if "black_" in b:
                matches = re.findall(r'black_start:(\d+\.\d+) black_end:(\d+\.\d+)', b)
                if len(matches) > 0:
                    loadinterval = list(map(float, matches[0]))
                    #print("Pass 1 Progress: {}/{}".format(str(datetime.timedelta(seconds=loadinterval[0])), str(datetime.timedelta(seconds=duration))))
                    t.update(loadinterval[0]-last_lint)
                    last_lint = loadinterval[0]
                    loadints.append(loadinterval)
    if len(loadints) <= 1:
        print("No intervals detected")

        if len(loadints) == 1:
            print("Pure false positive: {},{}".format(*loadints[0]))
        else:
            print("Pure false negative")
        return []
    else:
        print("Load count (HUD Only): {}".format(len(loadints)))
    return loadints

def medal_pass(stream,medal):
    global duration
    medalints = []
    mstream = stream.crop(**medal).filter('chromahold',color="#D39D00",similarity="0.12",yuv=False) \
        .filter("chromakey", color="#808080", similarity="0.1", blend="0.005"). \
        filter("negate"). \
        filter("blackdetect",d=1,pix_th="0.3",pic_th="0.45") \
        .output("-",format="null")
    lastint = 0
    with tqdm(total=duration,desc="Pass 2 of 3",bar_format="{l_bar}{bar}" + TQDM_RBAR, file=sys.stdout) as t:
        for b in mstream.run_async(pipe_stderr=True).stderr:
            b = b.decode("utf-8")
            if "black_" in b:
                nums = b.split(":")[-3:]
                loadinterval = list(map(lambda n: float(n.split(" ")[0]), nums[:2]))
                t.update(lastint-loadinterval[0])
                lastint=loadinterval[0]
                medalints.append(loadinterval)
    return medalints
def freeze_pass(stream, duration,w,h,x,y):
    proc = stream.crop(x,y,w,(h*3)//4).filter("hqdn3d").filter("freezedetect", d=0.1, n="-53dB").output("-", format="null").run_async(pipe_stderr=True)
    g_freezeints = []
    lstart = -1
    lend = -1
    lastint = 0
    with tqdm(total=duration,desc="Pass 3 of 3",bar_format="{l_bar}{bar}" + TQDM_RBAR, file=sys.stdout) as t:
        for l in proc.stderr:
            l = l.decode("utf-8")

            if "freezedetect.freeze" in l:
                if "start" in l and clean_freezeline(l) > duration+3.5:
                    break
                elif "start" in l:
                    lstart = float(l.split(":")[-1].strip())
                elif "end" in l and lstart != -1:
                    if clean_freezeline(l) > 0:
                        lend = float(l.split(":")[-1].strip())
                        g_freezeints.append([lstart,lend])
                        t.update(lstart-lastint)
                        lastint=lstart
                        lstart = -1
                        lend = -1
                    loadinterval = []
    return g_freezeints
DISABLE_PASS = [False, False, False]
parser = argparse.ArgumentParser(description="Removes loads from a sonic '06 speedrun video. Currently in the testing phase.")
parser.add_argument("link", type=str, help="the link to the run video (both twitch and youtube are supported)")
parser.add_argument("start", type=float, help="the time (in seconds) the run starts.  Go by footage (last frame before fadeout from menu), not by splitter.")
parser.add_argument("resolution", type=str,  help="The output resolution of your entire footage, in wxh form.  (1280x720, for example)")
parser.add_argument("gamelocation", type=str, help="The position of your game footage within your output. Format as w:h:x:y, where x and y are the coordinates of your capture's top left corner.")
parser.add_argument("--splitsio", type=str, nargs='?', help="The 4-character id of the splits.io associated with this run.  Optional, but recommended.")
parser.add_argument("--manual", type=str, nargs="?", help="""The duration of the run, as determined by livesplit and/or the verifier. in HH:MM:SS.mmm format.  00:56:02.300 is valid.""")
runresp = None
category = ""

splitnames = []
splits = []

duration = -1
if len(sys.argv) == 1:
    argless_test()
args = parser.parse_args(sys.argv[1:])

if args.splitsio:
    sio_id = args.splitsio
    runresp = requests.get("https://splits.io/api/v4/runs/{}".format(sio_id))
    print("splits.io status code: {}".format(runresp.status_code))
    runjson = runresp.json()
    splits = [s['realtime_end_ms']/1000 for s in runjson['run']['segments']]
    duration = splits[-1]
elif args.manual:
    split_t = args.manual.split(":")
    h = int(split_t[0])
    m = int(split_t[1])
    s = float(split_t[2])
    duration = 3600*h + 60*m + s
else:
    raise ValueError


load_intervals = []
runvid_link = args.link
RES = list(map(int, args.resolution.split("x")))
w,h,x,y = map(lambda n: int(n), args.gamelocation.split(":"))

starttime = time.time()

if "http" in runvid_link and "%3D" not in runvid_link:
    with YoutubeDL(yt_opts) as yt:
        yt.download([runvid_link])
    runvid_link = httplink
boxdict = {"width": 100, "height": 20, "x": 40, "y": 80}
medaldict = {"width": 100, "height": 100, "x": 600, "y":400}
rs = ffmpeg.input(runvid_link,ss=args.start,t=duration+args.start)
if w != 1280 or h != 720:
    scalefactor = w/1280
    for k,v in boxdict.items():
        boxdict[k] = int(boxdict[k]*scalefactor)
    for k,v in medaldict.items():
        medaldict[k] = int(medaldict[k]*scalefactor)
boxdict['x'] += x
boxdict['y'] += y
medaldict['x'] += x
medaldict['y'] += y
if DISABLE_PASS[0]:
    loadints = []
else:
    loadints = darkness_pass(rs, boxdict)

#second pass

medalints = []
if not DISABLE_PASS[1]:
    mstream = rs.crop(**medaldict).filter('chromahold',color="#D39D00",similarity="0.12",yuv=False)\
        .filter("chromakey", color="#808080", similarity="0.1", blend="0.005").\
            filter("negate").\
    filter("blackdetect",d=1,pix_th="0.3",pic_th="0.45")\
        .output("-",format="null")


    for b in mstream.run_async(pipe_stderr=True).stderr:
        b = b.decode("utf-8")
        if "black_" in b:
            nums = b.split(":")[-3:]
            loadinterval = list(map(lambda n: float(n.split(" ")[0]), nums[:2]))
            print("Pass 2 Progress: {}/{}".format(str(datetime.timedelta(seconds=loadinterval[0])), str(datetime.timedelta(seconds=duration))))
            medalints.append(loadinterval)
#third pass
if not DISABLE_PASS[2]:
    runstream = rs

    cstart = 0
    cdur = 0
    g_freezeints = []
    splitidx = 0
    tolerance = .1
    minute = 1
    lstart = -1
    lend = -1
    g_freezeints = freeze_pass(rs, duration, w, h, x, y)

    """
    for l in ffresult.stderr:
        l = l.decode("utf-8")
    
        if "freezedetect.freeze" in l:
            if "start" in l and clean_freezeline(l) > duration+3.5:
                break
            elif "start" in l:
                lstart = float(l.split(":")[-1].strip())
            elif "end" in l and lstart != -1:
                if clean_freezeline(l) > 0:
                    lend = float(l.split(":")[-1].strip())
                    g_freezeints.append([lstart,lend])
                    lstart = -1
                    lend = -1
                    if len(g_freezeints) % 15 == 0:
                        print("Progress: {}/{}".format(str(datetime.timedelta(seconds=loadinterval[0])), str(datetime.timedelta(seconds=duration))))
                loadinterval = []
                """
    endtime = time.time()
    tdur = datetime.timedelta(seconds=(endtime-starttime))
    print("Total video processing time: {}".format(str(tdur)))

    #MSGBOX("Third Pass done, cleaning up + outputting results")



    freezeints = []
    gstart, gend = g_freezeints[0]
    for gapl in g_freezeints[1:]:
        ngstart, ngend = gapl
        if abs(gend - ngstart) <= tolerance:
            gend = ngend
        else:
            freezeints.append([gstart, gend])
            gstart = ngstart
            gend = ngend

    print("{} Screen freezes".format(len(freezeints)))



if any(DISABLE_PASS):
    print("Passes done")
    sys.exit(5)
#medal screen cleanup

final_loads = loadints.copy()
shorten_target = []
midx = 0
medalints = [[l[0] + 2.667, l[1]+ 2.667] for l in medalints]
while midx < len(medalints):
    mstart,mend = medalints[midx]
    if mend-mstart >= 2.5 and mend-mstart <= 2.7:
        oldinterval_l = list(filter(lambda i: i[0] < mstart and i[1] > mstart, final_loads))
        if len(oldinterval_l) < 1:
            midx += 1
            continue
        allmedals = list(filter(lambda k: k[0]  > oldinterval_l[0][0] and k[1] < oldinterval_l[0][1], medalints))
        if len(allmedals) >= 1:
            lidx = final_loads.index(oldinterval_l[0])
            final_loads[lidx][0] = allmedals[-1][-1]
            midx += len(allmedals) - 1
    midx += 1
extensions = []
#freeze removal, get medal screens out of the data structure too
for m in range(len(final_loads)):
    lstart = final_loads[m][0]
    lend = final_loads[m][1]
    internal_intvs = list(filter(lambda f: (lstart > f[0] and abs(lstart - f[0]) <= 7), freezeints))
    if len(internal_intvs) > 0:
        intern = max(internal_intvs, key=lambda i: i[0])
        if intern[0] < lstart:
            if any([i[0] <= (intern[0]) and i[-1] >= (intern[0]) and i[0] != lstart for i in final_loads]):
                print("Skipping interval {}->{}, overlap".format(lstart,lend))
            elif lstart - intern[0] < 5:
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
    tdstr = datetime.timedelta(seconds=duration)
    rta_seconds = tdstr.total_seconds()
    loadless_seconds = rta_seconds
    print("RTA Total: {}\n".format(str(datetime.timedelta(seconds=rta_seconds))))
    f.write("\nRTA Total: {}\n".format(str(datetime.timedelta(seconds=rta_seconds))))

    final_loads = list(filter(lambda i: i[0] < duration, final_loads))
    if final_loads[-1][1] > duration:
        final_loads[-1][1] = duration
    all_loads = sum(map(lambda i: i[1]-i[0], final_loads))
    loadless_seconds = duration - all_loads
    print("Loadless Time: {}\n".format(datetime.timedelta(seconds=loadless_seconds)))
    f.write("Loadless Time: {}\n".format(datetime.timedelta(seconds=loadless_seconds)))
final_loads = [list(map(lambda t: t + args.start, fl)) for fl in final_loads]
with open("res_montage.txt", "w") as mf:
    mf.write(""";FFMETADATA
title=None
major_brand=isom
minor_version=512
compatible_brands=isomiso2avc1mp41
encoder=Lavf58.23.102\n""")
    montage_fmt = "[CHAPTER]\nTIMEBASE=1/1000\nSTART={}\nEND={}\nTITLE=Load {} {}\n"
    loadidx = 1
    mf.write(montage_fmt.format(0, (args.start * 1000), 0, "-1: (Run Start)", "\n"))

    for flidx in range(len(final_loads)-1):
        fls = final_loads[flidx][0] + args.start
        fle = final_loads[flidx][1] + args.start
        mf.write(montage_fmt.format(int(fls*1000), int(fls*1000)+1, flidx, "Start") + "\n")
        mf.write(montage_fmt.format(int(fle*1000), int(fle*1000)+1, flidx, "End") + "\n")

total_t = time.time() - starttime
MSGBOX("Results computed in {}".format(str(datetime.timedelta(seconds=total_t))))











