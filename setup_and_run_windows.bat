@echo off
REM D13 one-click setup and run (Windows, Anaconda installed).
REM Double-click this file, or run it from "Anaconda Prompt" inside this folder.
cd /d %~dp0
call conda create -y -n d13 python=3.11
call conda activate d13
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python check_access.py
python run_all.py
echo.
echo Done. Outputs are in the "outputs" folder. To open the dashboard run:
echo     conda activate d13 ^&^& streamlit run app\streamlit_app.py
pause
