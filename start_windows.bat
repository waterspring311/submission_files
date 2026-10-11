
@echo off
setlocal
echo ========================================
echo   智聘未来 · AI 全流程智能招聘系统
echo   Windows一键启动脚本
echo ========================================
echo.

echo [1/4] 检查Python环境...
set "PYTHON_CMD=python"
if exist "E:\cwj\Python\Python311\python.exe" set "PYTHON_CMD=E:\cwj\Python\Python311\python.exe"

%PYTHON_CMD% --version >nul 2>nul
if errorlevel 1 (
    set "PYTHON_CMD=py -3"
    %PYTHON_CMD% --version >nul 2>nul
    if errorlevel 1 (
        echo ERROR: 未找到Python，请先安装Python 3.8+
        echo    下载地址: https://www.python.org/downloads/
        pause
        exit /b 1
    )
)
%PYTHON_CMD% --version
echo OK: Python检查通过
echo.

echo [2/4] 安装依赖...
%PYTHON_CMD% -m pip install -r requirements.txt
if errorlevel 1 (
    echo WARN: 依赖安装可能有问题，但继续尝试启动...
)
echo OK: 依赖处理完成
echo.

echo [3/4] 检查配置文件...
if not exist "04_data\.env" (
    echo WARN: 未找到.env文件，从.env.example复制...
    copy "04_data\.env.example" "04_data\.env"
    echo OK: 配置文件已创建，请编辑 04_data\.env 填入您的配置
)
echo OK: 配置检查完成
echo.

echo [4/4] 准备启动应用...
echo.

echo ========================================
echo   准备完成！正在启动应用...
echo ========================================
echo.
echo 应用将在浏览器中打开
echo 访问地址: http://localhost:8501
echo.
echo 按 Ctrl+C 可停止应用
echo.

%PYTHON_CMD% 01_project_code/run_flask.py

pause
