@echo off
REM ============================================================
REM run_Claude_Experiment.bat
REM Chay thuc nghiem LLM-R2 voi Claude Opus 4.6 (Windows)
REM
REM Huong dan su dung:
REM   1. Mo file .env va nhap API key (bat dau = "sk-ant-api03-...")
REM   2. Chay: run_Claude_Experiment.bat
REM
REM Cau hinh (thay doi trong LLM_R2_Claude.py - cuoi file):
REM   - DATASET: dsb | tpch | job_syn
REM   - METHOD: queryCL | sentbert | plan | random
REM   - NUM_PROMPTS: so luong demonstration
REM ============================================================

REM ==== KIEN NGHI ====
REM Model tot nhat cho rewrite rules: claude-opus-4-6
REM Model nhanh hon: claude-sonnet-4-6
REM Model nhanh nhat: claude-haiku-4-5-20251001

echo ==============================================
echo   LLM-R2 + Claude Opus 4.6 Experiment
echo ==============================================
echo   Model:       claude-opus-4-6 (mac dinh)
echo   Dataset:     dsb (mac dinh, doi trong LLM_R2_Claude.py)
echo   Method:      queryCL (mac dinh)
echo ==============================================
echo.

cd /d "%~dp0"

echo [INFO] Chay voi Python tu .venv (da cai tat ca thu vien)...
REM Dat UTF-8 encoding de hien thi tieng Viet
chcp 65001 >nul 2>&1
set PYTHONIOENCODING=utf-8

echo.
echo Bat dau chay thuc nghiem voi Claude Opus 4.6...
echo.
..\.venv\Scripts\python.exe -X utf8 LLM_R2_Claude.py

echo.
echo === Thuc nghiem hoan tat ===
echo Ket qua luu tai: ..\results\
pause
