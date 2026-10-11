
#!/bin/bash

echo "========================================"
echo "  智聘未来 · AI 全流程智能招聘系统"
echo "  Mac/Linux一键启动脚本"
echo "========================================"
echo ""

echo "[1/4] 检查Python环境..."
if command -v python3 >/dev/null 2>&1; then
    PYTHON_CMD=python3
    PIP_CMD=pip3
elif command -v python >/dev/null 2>&1; then
    PYTHON_CMD=python
    PIP_CMD=pip
else
    echo "ERROR: 未找到Python，请先安装Python 3.8+"
    echo "   下载地址: https://www.python.org/downloads/"
    exit 1
fi

$PYTHON_CMD --version
echo "OK: Python检查通过"
echo ""

echo "[2/4] 安装依赖..."
$PIP_CMD install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "WARN: 依赖安装可能有问题，但继续尝试启动..."
fi
echo "OK: 依赖处理完成"
echo ""

echo "[3/4] 检查配置文件..."
if [ ! -f "04_data/.env" ]; then
    echo "WARN: 未找到.env文件，从.env.example复制..."
    cp "04_data/.env.example" "04_data/.env"
    echo "OK: 配置文件已创建，请编辑 04_data/.env 填入您的配置"
fi
echo "OK: 配置检查完成"
echo ""

echo "[4/4] 准备启动应用..."
echo ""

echo "========================================"
echo "  准备完成！正在启动应用..."
echo "========================================"
echo ""
echo "应用将在浏览器中打开"
echo "访问地址: http://localhost:8501"
echo ""
echo "按 Ctrl+C 可停止应用"
echo ""

$PYTHON_CMD "01_project_code/run_flask.py"
