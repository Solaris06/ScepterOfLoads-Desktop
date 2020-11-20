**Build Instructions:**

`git clone https://github.com/Solaris06/ScepterOfLoads-Desktop.git`

`cd ScepterOfLoads-Desktop`

`python3 -m venv scepter-venv`

`.\scepter-venv\Scripts\activate`

`pip install -r requirements.txt`

**Run instructions:**

``python3 main.py [link/path to footage] [start time, in s, of run], [resolution, ex: 1920x1080], [game footage portion of screen, w:h:x:y]``

After that you have 2 choices for duration:

`--splitsio abcd`

or

`--manual hh:mm:ss.xxx (ex: 00:54:03.950)`

Sit back, relax.  Debug info is printed to standard error, results are saved to res_(run date/time).csv
