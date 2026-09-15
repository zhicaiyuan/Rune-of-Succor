@echo off
"C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe" "E:\??\??\Rune-of-Succor\??\??.uproject" -unattended -nop4 -nosplash -NullRHI -stdout -FullStdOutLogOutput -ExecutePythonScript="E:\??\??\Rune-of-Succor\??\Content\Python\setup_strafe_locomotion.py"
echo EXITCODE=%ERRORLEVEL%
