import json,  sys, time, argparse, os
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
def legacy_detect(load, freeze):
    medals = []

    for l in range(len(load) - 2):
        start, end = load[l]
        if len(medals) > 0 and abs(medals[-1][-1] - start) < 45:
            continue
        subintervals = list(filter(lambda f: f[0] >= start and f[1] <= end, freeze))
        if len(subintervals) > 0:
            mdict = {}
            f_extra = freeze.index(subintervals[-1])
            if f_extra + 1 < len(freeze) and freeze[f_extra + 1][0] < end:
                subintervals.append(freeze[f_extra + 1])
            if abs(subintervals[0][1] - subintervals[0][0]) < 4 and abs(load[l + 1][0] - start) < 30:
                mdict = {}
                if len(subintervals) > 1 and abs(subintervals[1][1] - subintervals[1][0]) <= 2.2 and abs(
                        load[l + 2][0] - load[l + 1][-1]) < 5:

                    if abs(start - load[l + 2][0]) > 22.5:
                        print("Skipping Medal: {} -> {}".format(start, load[l + 2][0]))
                    elif abs(load[l + 2][0] - load[l + 1][-1]) < 1.5:
                        print("Deffering Medal: {} -> {}".format(start, load[l + 2][0]))
                        mdict['medals'] = medals[l:l+2]
                        postloads = [m for m in freeze if m[0] > load[l + 1][1]]
                        if len(postloads) > 0:
                            print("New interval end {}".format(postloads[0][0]))
                            mdict['shift'] = postloads[0][0]
                        else:
                            mdict['shift'] = -1
                    else:
                        medals.append(load[l])
                        medals.append(load[l + 1])
                        postloads = [m for m in freeze if m[0] > load[l + 1][1]]
                        if len(postloads) > 0:
                            print("New interval end {}".format(postloads[0][0]))
                            mdict['shift'] = postloads[0][0]
                        else:
                            mdict['shift'] = -1

                else:
                    if abs(start - load[l + 1][0]) > 22.5:
                        print("Skipping Medal: {} -> {}".format(start, load[l + 1][0]))
                    else:
                        mdict['medals'] =[load[l]]
                        postloads = [m for m in freeze if m[0] > load[l][1]]
                        if len(postloads) > 0:
                            print("New interval end {}".format(postloads[0][0]))
                            mdict['shift'] = postloads[0][0]
                        else:
                            mdict['shift'] = -1
                if mdict != {}:
                    medals.append(mdict)
    return medals

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
parser.add_argument("--L", action="store_true", help="Use if the run in consideration is neither AGM nor all stories.")
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
runstream = ffmpeg.input(runvid_link).trim(start=args.start,end=args.start+runduration+6).setpts('PTS-STARTPTS')
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
                              **{"w": dims[0], "h": dims[1] * .75, "x":0,
                                 "y":0})
#first pass
if dims[0] != 1280 or dims[1] != 720:
    w *= dims[0]/1280
    h *= dims[1]/720

proc = runstream.setpts('PTS-STARTPTS').filter("scale", width=1280, height=720*.75).crop(width=100,height=30,x=40,y=80).filter("blackdetect", d=1, pic_th="0.995", pix_th="0.1").output("-",format="null").run_async(pipe_stderr=True)
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
runstream = runstream.filter("freezedetect", d=0.2, n="-53 dB").output("-", format="null")

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



freezeints = []
gstart, _, gend = g_freezeints[0]
for gapl in g_freezeints[1:]:
    ngstart, _, ngend = gapl
    if abs(gend - ngstart) <= .22:
        gend = ngend
    else:
        freezeints.append([gstart, gend])
        gstart = ngstart
        gend = ngend





#medal screen cleanup
medalscreens = []

if not args.L:
    for l in range(len(loadints)-1): #skip the first fadeout, thus not starting at 0
        start, end = loadints[l]
        if len(medalscreens) > 0 and (loadints[l] in medalscreens): #start must be 45s *ahead* of the last medal screen's ending, rta starts at a fadeout
            continue
        subintervals = list(filter(lambda f: f[0] >= start - .2, freezeints))
        if len(subintervals) > 0: #index protection + black screen freeze and fade to black end are MAX this far apart, no exceptions
            premedal_blackscreen_t = abs(subintervals[0][0] - start)
            if premedal_blackscreen_t < .5: #fadeout -> freeze
                n_medals = 0 #first medal candidate
                if len(subintervals) > 1:
                    c_duration = subintervals[n_medals+1][1] - subintervals[n_medals+1][0] #0 was the pre-medal screenfreeze, so 1 is the first medal

                    while l + n_medals < len(loadints) and n_medals < 4 and (n_medals + 1) < len(subintervals): # there isn't a way to manipulate how long the screen freezes before the text box appears, first to prevent index out of bounds stuff
                        medal_stopspin_pwing_t = abs(subintervals[n_medals+1][1] - subintervals[n_medals+1][0]) #medal spin halt to prompt
                        stopspin_prompt_t = abs(subintervals[n_medals+1][1] - loadints[l+n_medals][1]) # the screenfreeze is interrupted when the prompt appears, RTA is counted from here
                        if medal_stopspin_pwing_t <= 2.5 and stopspin_prompt_t < .5:
                            n_medals += 1
                        else:
                            break
                #note: staying at either the save prompt *or* any medal clear screen does not count as loading per the scepter :^)
                if n_medals >= 1: #if there are any medals at all
                    print("Number of medals: {}".format(n_medals+1))
                    # we want the medal screen to be bounded on both sides by the load interval due to the save prompt after, so get the load interval start *after* the last one we checked
                    if l + n_medals + 1 < len(loadints):
                        print("Medal screen: {} -> {}".format(start, loadints[l + n_medals + 1][0]))
                        #however, we need to remove only the load intervals that are *not* counted as RTA like the prompts are
                        for k in range(l, l+n_medals+1, 1):
                            medalscreens.append(loadints[k]) #so instead of the whole thing we append just the non-prompt bits
                elif (end-start) > 5 and (end-start) < 10: #fuckin mashers, it's a magic number and i hate it, but if you sit on a prompt you give the loop above a medal, but if you don't sit on either long enough this is about it
                    print("Non-S rank (?)")
                    print("Medal screen: {} -> {}".format(start,end))
                    medalscreens.append(loadints[l])
if len(medalscreens) <= 3:
    print("Falling back to legacy medal detection...")
    medal_dict = legacy_detect(loadints, freezeints)
    #get the shifts in there so the  end of the medal screens are RTA too

final_loads = []
extensions = []

#freeze removal, get medal screens out of the data structure too
for lstart, lend in filter(lambda l: l not in medalscreens, loadints):
    internal_intvs = list(filter(lambda f: (lstart > f[0] and abs(lstart - f[0]) <= 4.5) and (f[1] >= lend - 2.5), freezeints))
    if len(internal_intvs) > 0:
        intern = max(internal_intvs, key=lambda i: i[0])
        if intern[0] < lstart:
            if any([i[0] <= (intern[0]) and i[1] >= (intern[0]) and i[0] != lstart for i in loadints]):
                print("Skipping interval {}->{}, overlap".format(lstart,lend))
                if not (lstart in [l[0] for l in final_loads] or lend in [l[1] for l in final_loads]):
                    final_loads.append([lstart, lend])
            else:
                print("Adjusting interval by {} s:".format(lstart - intern[0]))

                extensions.append(lstart-intern[0])
                print("Before: {} -> {}".format(lstart, lend))
                lstart = intern[0]
                print("After: {} -> {}".format(lstart, lend))
    if not (lstart in [l[0] for l in final_loads] or lend in [l[1] for l in final_loads]):
        final_loads.append([lstart, lend])



print("Done with footage, applying to splits...")

windll.user32.MessageBoxW(0, "Outputting", "Scepter", 0x1000)
loadints_out = list(map(lambda t: [ str(datetime.timedelta(seconds=s+args.start)) for s in t], final_loads))
freezeints_out = list(map(lambda t: [ str(datetime.timedelta(seconds=s+args.start)) for s in t], freezeints))
medalscreens_out = list(map(lambda t: [ str(datetime.timedelta(seconds=s+args.start)) for s in t], medalscreens))
with open("res_{}.csv".format(datetime.datetime.now().strftime("%b_%d_%Y_%H_%M_%S")), "w+") as f:
    f.write("Run Begin Timestamp: {}".format(str(datetime.timedelta(seconds=args.start))))
    f.write("\nMedal Screens (added back into RTA):\n")
    f.write("\n".join(list(map(lambda i:  ",".join(i), medalscreens_out))))
    tdstr = datetime.timedelta(seconds=runduration)
    rta_seconds = tdstr.total_seconds()
    loadless_seconds = rta_seconds
    print("RTA Total: {}\n".format(str(datetime.timedelta(seconds=rta_seconds))))
    f.write("\nRTA Total: {}\n".format(str(datetime.timedelta(seconds=rta_seconds))))

    for l in final_loads:
        loadless_seconds -= abs(l[1]-l[0])
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
    montage_fmt = "[CHAPTER]\nTIMEBASE=1/1000\nSTART={}\nEND={}\nTITLE=Load {} Ending at {}\n"
    loadidx = 1
    print(montage_fmt.format(0, (args.start * 1000)-1, 0, str(datetime.timedelta(seconds=args.start))))

    mf.write(montage_fmt.format(0, (args.start * 1000)-1, 0, str(datetime.timedelta(seconds=args.start))) + "\n")
    for flidx in range(len(final_loads)-1):

        fls = final_loads[flidx][0]
        fle = final_loads[flidx][1]
        che = final_loads[flidx + 1][0] - .001
        print(montage_fmt.format(fls*1000, che*1000, flidx + 1, str(datetime.timedelta(seconds=fle))))
        mf.write(montage_fmt.format(fls*1000, che*1000, flidx + 1, str(datetime.timedelta(seconds=fle))) + "\n")
















