@echo off
cd /d E:\0WorkFolder\RainbowV1
call venv\Scripts\activate
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
pause
