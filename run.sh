#!/bin/bash

# Exhibitor Scraper - 一鍵運行腳本

echo "================================"
echo "展商爬蟲 - 自動安裝與運行"
echo "================================"
echo ""

# 檢查 Python
echo "✓ 檢查 Python..."
if ! command -v python3 &> /dev/null; then
    echo "✗ 未找到 Python 3，請先安裝 Python 3.7+"
    exit 1
fi

python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "  → Python $python_version"

# 創建虛擬環境（可選但推薦）
echo ""
echo "✓ 設置虛擬環境..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "  → 虛擬環境已創建"
fi

# 激活虛擬環境
source venv/bin/activate 2>/dev/null || . venv/Scripts/activate 2>/dev/null

# 升級 pip
echo ""
echo "✓ 升級 pip..."
pip install --upgrade pip -q

# 安裝依賴
echo ""
echo "✓ 安裝依賴..."
pip install -r requirements.txt -q

# 安裝 Playwright 瀏覽器
echo ""
echo "✓ 安裝 Playwright Chromium..."
playwright install chromium -q

# 運行爬蟲
echo ""
echo "✓ 啟動爬蟲..."
echo "================================"
echo ""

python3 scraper.py

echo ""
echo "================================"
echo "✓ 完成！"
echo "✓ 結果已保存到 exhibitors.csv"
echo "================================"
