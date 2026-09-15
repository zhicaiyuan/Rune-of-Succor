@echo off
set PROJ=E:\游戏\符济\Rune-of-Succor\符济\符济.uproject
set EXE=C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe
set SCRIPT=E:\游戏\符济\Rune-of-Succor\符济\Content\Python\fix_tps_camera.py
"%EXE%" "%PROJ%" -unattended -nop4 -nosplash -NullRHI -stdout -FullStdOutLogOutput -ExecutePythonScript="%SCRIPT%"
echo EXITCODE=%ERRORLEVEL%
