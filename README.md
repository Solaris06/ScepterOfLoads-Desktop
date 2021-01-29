**Build Instructions:**

###Prerequisites:
* Python 3.7 or above with pip
* ffmpeg release full (*not* essentials) either added to your PATH environment variable or locally available.
*  Windows builds available here: https://www.gyan.dev/ffmpeg/builds/ 

`git clone https://github.com/Solaris06/ScepterOfLoads-Desktop.git`

`cd ScepterOfLoads-Desktop`

`python3 -m venv scepter-venv`

`.\scepter-venv\Scripts\activate`

`pip install -r requirements.txt`

To build an executable:

`.\scepter-venv\Scripts\activate`

`pyinstaller -D -n ScepterBuild processor.py`

This will, by default, create an executable folder/package in the `dist` folder.  

**Run instructions:**

``python3 main.py [link/path to footage] [start time, in s, of run], [resolution, ex: 1920x1080], [game footage portion of screen, w:h:x:y]``

After that you have 2 choices for duration:

`--splitsio abcd`

or

`--manual hh:mm:ss.xxx (ex: 00:54:03.950)`

Sit back, relax.  Debug numbers are stored in `dbg.json`, final results are saved to `res_(run date/time).csv`.

This will notify you with a forced-to-top popup dialog when finished.  If not desired, contact me.

For now, this outputs res_montage.txt that can be applied to add load location metadata to an existing video.
Details to come.

