@echo off
rem Same as fetch_outputs.py, for a Windows PC without Python: fetch_outputs.cmd user@gpu-server [repository path on the server, default GASP]
rem Packs the results on the server, copies the pack, unpacks it into this repository's outputs folder (needs ssh, scp, tar: built into Windows 10 and later).
if "%~1"=="" echo usage: fetch_outputs.cmd user@gpu-server [path on the server] && exit /b 1
set R=%~2
if "%R%"=="" set R=GASP
ssh %1 "cd %R% && ls -d outputs/llm outputs/llm_sens outputs/llm_*_stats outputs/llm_local_pilot* outputs/*.log 2>/dev/null | tee /dev/stderr | tar czf outputs/gasp_outputs.tgz -T - && du -h outputs/gasp_outputs.tgz" || exit /b 1
if not exist "%~dp0..\outputs" mkdir "%~dp0..\outputs"
scp -q %1:%R%/outputs/gasp_outputs.tgz "%~dp0..\outputs\gasp_outputs.tgz" || exit /b 1
tar xzf "%~dp0..\outputs\gasp_outputs.tgz" -C "%~dp0.." && del "%~dp0..\outputs\gasp_outputs.tgz"
echo done: see %~dp0..\outputs\llm
