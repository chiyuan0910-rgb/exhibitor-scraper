# Exhibitor Scraper

爬取 GrupaMTP 展商目錄的 Python 爬蟲，使用 Playwright 提取展商信息並輸出為 CSV。

## 功能特性

- ✅ 使用 Playwright + Chromium 自動化瀏覽
- ✅ Headless 模式運行（無需顯示瀏覽器）
- ✅ 智能等待頁面加載
- ✅ 自動處理分頁
- ✅ 支持無限滾動加載
- ✅ 自動去重
- ✅ 輸出 UTF-8 編碼 CSV 文件

## 提取信息

每條展商記錄包含：
- **Company Name** - 公司名稱
- **Booth No** - 展位號
- **Country** - 國家
- **Website** - 網站

## 快速開始

### 1. 安裝依賴

```bash
pip install -r requirements.txt
playwright install chromium
```

### 2. 運行爬蟲

```bash
python scraper.py
```

### 3. 查看結果

爬蟲完成後會生成 `exhibitors.csv` 文件。

## 輸出示例

```csv
Company Name,Booth No,Country,Website
Example Company Ltd.,A-101,Poland,https://example.com
Another Corp,B-205,Germany,https://another.de
```

## 目標 URL

```
https://katalog.grupamtp.pl/en/?ec=TC22601&_ga=2.202882514.2110875607.1780539796-782084389.1780539687
```

## 技術棧

- **Python 3.7+**
- **Playwright** - 瀏覽器自動化
- **Chromium** - 無頭瀏覽器
- **csv** - CSV 格式輸出

## 故障排除

### 問題：Chromium 未安裝
```bash
playwright install chromium
```

### 問題：超時錯誤
增加 `wait_for_timeout` 的值或檢查網絡連接。

### 問題：找不到元素
檢查目標網站是否更新了 HTML 結構，可能需要調整選擇器。

## 開發者

Chiyuan RGB

## 許可證

MIT
