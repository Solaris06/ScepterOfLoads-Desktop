
from tkinter import *
from tkinter import ttk
from PIL import Image, ImageTk
import ffmpeg
import numpy as np
from youtube_dl import YoutubeDL
httplink = ""
dims = (-1,-1)
def matchfilter(idict):
    global httplink, dims
    formats = idict['formats']
    fmt = list(filter(lambda f: f.get('width') is not None and f.get('width') <= 1280, formats))
    if httplink == "":
        httplink = fmt[-1]['url']
        dims = (fmt[-1]['width'], fmt[-1]['height'])
        return "yt stream retrieved"
    return "whoops"

def getframe(url, frame_num=600):
    yt_opts = {"skip_download": True, "match_filter": matchfilter}
    with YoutubeDL(yt_opts) as yt:
        yt.download([url])
    stream = ffmpeg.input(httplink)
    out, _ = (
        stream
            .filter_('select', 'gte(n,{})'.format(frame_num))
            .output('pipe:', format='rawvideo', pix_fmt='rgb24', vframes=1)
            .run(capture_stdout=True, capture_stderr=True)
    )
    return np.frombuffer(out,np.uint8).reshape([*dims[::-1],3])


root = Tk()
root.title("Scepter of Loadtimes")
content = ttk.Frame(root, padding="3 3 12 12")
content.grid(column=0, row=0, sticky=(N,W,E,S))
root.columnconfigure(0, weight=1)
root.rowconfigure(0, weight=1)

def showframe(*args):
    try:
        yturl = str(runurl.get())
        pilim = Image.fromarray(getframe(yturl))

        t = Toplevel()
        im = ImageTk.PhotoImage(image=pilim,master=t)
        t.title("Thumbnail")
        canvas = Canvas(t,width=dims[0]+100,height=dims[1]+100)
        canvas.pack()
        canvas.create_image(25,25,anchor="nw",image=im)
        t.mainloop()
    except ValueError:
        return


runurl = StringVar()

ulabel = ttk.Label(content, text="Run URL")
ulabel.grid(column=1, row=1)

url_entry = ttk.Entry(content, textvariable=runurl)
url_entry.grid(column=2,row=1)

btn = ttk.Button(content, text="Get Thumbnail",command=showframe).grid(column=2,row=2, sticky=E)

root.mainloop()


