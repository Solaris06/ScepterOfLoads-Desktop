@echo off
set exepath="%~dp0dist\ScepterOfLoads-0.0.1\ScepterOfLoads-0.0.1.exe"
IF "%%1"=="" (
    set /p FOOTAGE="No local file was opened. Enter a youtube link that contains the run to be retimed."
) ELSE (
    set FOOTAGE="%~dpnx1"
)
set /p START="Enter the timestamp, in seconds, of when the run starts. Last frame before fadeout, no episode select arrows:"
set /p RES="Enter the resolution of your OBS output as 1280x720, for example (or video, OBS is easier):"
set /p DIMS="Enter the dimensions of your game footage within the video, as width:height:x:y, where x and y are where the top-left corner of the footage is:"
set /p MANUALCHOICE="D you have a splits.io ID of the run? [Y/N]:"
if "%MANUALCHOICE%" == "Y" (
    set /p SIOID="Enter the 4-character splits.io id of the run."
    %exepath% %START% %RES% %DIMS% --splitsio "%SIOID%"
) else (
    set /p SPLITPATH="Enter the duration of the run in hh:mm:ss.mmm form (blank zeroes required for hour/minute/second)"
    %exepath% %START% %RES% %DIMS% --manual "%SPLITPATH%"
)
echo "Check the above for errors, otherwise you're done!"
pause