import asyncio
import csv
from playwright.async_api import async_playwright
import json

async def scrape_exhibitors():
    """
    爬取展商目錄頁面並輸出為 CSV
    """
    url = "https://katalog.grupamtp.pl/en/?ec=TC22601&_ga=2.202882514.2110875607.1780539796-782084389.1780539687"
    
    exhibitors = []
    
    async with async_playwright() as p:
        # 啟動 Chromium browser
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        print(f"開啟 URL: {url}")
        await page.goto(url, wait_until="networkidle")
        
        # 等待展商卡片元素出現
        print("等待展商列表載入...")
        try:
            await page.wait_for_selector("[class*='exhibitor'], [class*='company'], tr", timeout=15000)
        except:
            print("警告: 未能等待到預期的選擇器")
        
        # 處理分頁或無限滾動
        previous_count = 0
        max_iterations = 50  # 防止無限循環
        iteration = 0
        
        while iteration < max_iterations:
            iteration += 1
            print(f"\n[迭代 {iteration}] 滾動並提取資料...")
            
            # 滾動到底部
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(1500)
            
            # 提取展商資料
            current_exhibitors = await page.evaluate("""
                () => {
                    const items = [];
                    
                    // 嘗試檢測頁面結構 - 尋找表格行或卡片
                    const rows = document.querySelectorAll('tr[role="row"], tr, [class*="item"], [class*="card"]');
                    
                    rows.forEach(el => {
                        // 從表格或卡片中提取欄位
                        const cells = el.querySelectorAll('td, [class*="cell"], [class*="field"]');
                        
                        if (cells.length > 0) {
                            let company = cells[0]?.textContent?.trim() || '';
                            let booth = cells[1]?.textContent?.trim() || '';
                            let country = cells[2]?.textContent?.trim() || '';
                            
                            // 尋找連結作為網站
                            let website = el.querySelector('a[href*="http"]')?.href || 
                                         el.querySelector('a')?.href || '';
                            
                            if (company && company.length > 0) {
                                items.push({
                                    company: company,
                                    booth: booth,
                                    country: country,
                                    website: website
                                });
                            }
                        }
                    });
                    
                    return items;
                }
            """)
            
            # 過濾掉空白項目
            current_exhibitors = [e for e in current_exhibitors if e['company'] and len(e['company']) > 2]
            
            print(f"本次找到: {len(current_exhibitors)} 個展商，累計: {len(exhibitors) + len(current_exhibitors)} 個")
            exhibitors.extend(current_exhibitors)
            
            # 嘗試點擊「下一頁」按鈕
            try:
                next_button = await page.query_selector(
                    "a.next, button[aria-label*='Next'], a[rel='next'], .pagination .next, [class*='next']"
                )
                
                if next_button:
                    is_visible = await next_button.evaluate("el => el.offsetParent !== null")
                    is_disabled = await next_button.evaluate(
                        "el => el.classList.contains('disabled') || el.hasAttribute('disabled') || el.getAttribute('aria-disabled') === 'true'"
                    )
                    
                    if is_visible and not is_disabled:
                        print("→ 點擊下一頁...")
                        await next_button.click()
                        await page.wait_for_timeout(2000)
                    else:
                        print("✓ 已到最後一頁")
                        break
                else:
                    # 沒有下一頁按鈕，檢查是否已加載所有內容
                    if len(exhibitors) > 0 and len(exhibitors) == previous_count:
                        print("✓ 無新資料，停止爬取")
                        break
            except Exception as e:
                print(f"下一頁檢查出錯: {e}")
            
            # 檢查是否有新資料
            if len(exhibitors) == previous_count and iteration > 2:
                print("✓ 沒有新資料，停止爬取")
                break
            
            previous_count = len(exhibitors)
        
        await browser.close()
    
    # 去重
    seen = set()
    unique_exhibitors = []
    for e in exhibitors:
        key = (e['company'].strip(), e['booth'].strip())
        if key not in seen:
            seen.add(key)
            unique_exhibitors.append(e)
    
    print(f"\n{'='*60}")
    print(f"總共爬取 {len(unique_exhibitors)} 個展商（去重後）")
    print(f"{'='*60}\n")
    
    # 輸出為 CSV
    output_file = "exhibitors.csv"
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['Company Name', 'Booth No', 'Country', 'Website'])
        writer.writeheader()
        
        for exhibitor in unique_exhibitors:
            writer.writerow({
                'Company Name': exhibitor['company'].strip(),
                'Booth No': exhibitor['booth'].strip(),
                'Country': exhibitor['country'].strip(),
                'Website': exhibitor['website'].strip()
            })
    
    print(f"✓ 資料已輸出到 {output_file}")
    
    # 顯示前幾筆
    print(f"\n前 5 筆展商資料：")
    for i, e in enumerate(unique_exhibitors[:5], 1):
        print(f"{i}. {e['company']} | Booth: {e['booth']} | Country: {e['country']}")

if __name__ == "__main__":
    asyncio.run(scrape_exhibitors())