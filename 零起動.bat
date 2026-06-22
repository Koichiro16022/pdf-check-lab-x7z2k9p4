@echo off
chcp 65001 > nul
echo ================================================
echo    零(ZERO) スタンダード版 v1.0 Phase 1
echo    起動中...
echo ================================================
echo.

cd /d "%~dp0"

REM Pythonの実行ファイルを直接指定
set PYTHON_EXE=python\python.exe
set SCRIPTS_PATH=python\Scripts

echo Pythonバージョン確認:
%PYTHON_EXE% --version
echo.

echo 必要なライブラリをインストール中...
echo （少々お待ちください）
%PYTHON_EXE% -m pip install --upgrade pip
%PYTHON_EXE% -m pip install streamlit openpyxl pandas numpy Pillow python-dateutil
echo.
echo インストール完了
echo.

echo 最新バージョンを確認中...
%PYTHON_EXE% updater.py

echo Streamlitを起動します...
echo ブラウザが自動的に開きます...
echo.
%PYTHON_EXE% -m streamlit run streamlit_app.py

echo.
echo ================================================
echo 終了しました
echo ウィンドウを閉じてもかまいません
echo ================================================
pause
