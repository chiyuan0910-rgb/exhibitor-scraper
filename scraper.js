const { chromium } = require('playwright');
const fs = require('fs');
const csv = require('csv-writer');

async function scrapeExhibitors() {
  const browser = await chromium.launch({
    headless: true,
  });

  const page = await browser.newPage();
  const exhibitors = [];
  const visitedUrls = new Set();

  try {
    console.log('Opening URL...');
    await page.goto('https://directory.imts.com/8_0/explore/exhibitor-gallery.cfm?featured=false&pavilion=TOOL', {
      waitUntil: 'networkidle',
    });

    // Wait for exhibitor cards to load
    console.log('Waiting for exhibitor cards to load...');
    await page.waitForSelector('[class*="exhibitor"], [class*="card"], [class*="gallery"]', {
      timeout: 10000,
    }).catch(() => console.log('Card selector timeout, proceeding anyway...'));

    let previousHeight = 0;
    let currentPage = 1;

    while (true) {
      console.log(`\nProcessing page ${currentPage}...`);

      // Wait a bit for content to stabilize
      await page.waitForTimeout(2000);

      // Extract exhibitor data from current page
      const pageExhibitors = await page.evaluate(() => {
        const exhibitors = [];
        
        // Try multiple selectors for exhibitor containers
        const containers = document.querySelectorAll(
          '[class*="exhibitor"], [class*="company"], [class*="vendor"], .gallery-item, .card'
        );

        containers.forEach((container) => {
          try {
            const nameEl = container.querySelector('[class*="name"], h2, h3, .company-name');
            const productEl = container.querySelector('[class*="product"], [class*="category"], .product-info');
            const countryEl = container.querySelector('[class*="country"], [class*="location"], .country');
            const websiteEl = container.querySelector('a[href*="http"]');
            const emailEl = container.querySelector('[href*="mailto"]');

            if (nameEl) {
              exhibitors.push({
                name: nameEl.textContent?.trim() || '',
                product: productEl?.textContent?.trim() || '',
                country: countryEl?.textContent?.trim() || '',
                website: websiteEl?.href || websiteEl?.textContent?.trim() || '',
                email: emailEl?.href?.replace('mailto:', '') || emailEl?.textContent?.trim() || '',
              });
            }
          } catch (e) {
            console.error('Error parsing container:', e);
          }
        });

        return exhibitors;
      });

      // Add unique exhibitors
      pageExhibitors.forEach((exhibitor) => {
        const key = `${exhibitor.name}|${exhibitor.website}`;
        if (!visitedUrls.has(key) && exhibitor.name) {
          visitedUrls.add(key);
          exhibitors.push(exhibitor);
        }
      });

      console.log(`Found ${pageExhibitors.length} exhibitors on page ${currentPage}`);
      console.log(`Total unique exhibitors: ${exhibitors.length}`);

      // Try to scroll to bottom
      const newHeight = await page.evaluate(() => document.body.scrollHeight);
      
      if (newHeight === previousHeight) {
        console.log('Reached bottom or no more content');
        break;
      }

      // Scroll to bottom
      await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
      previousHeight = newHeight;

      // Check for next button and click it
      const nextButton = await page.$(
        'a:has-text("Next"), button:has-text("Next"), [class*="next"], .pagination a'
      ).catch(() => null);

      if (nextButton) {
        console.log('Found next button, clicking...');
        await nextButton.click();
        currentPage++;
        await page.waitForTimeout(2000);
      } else {
        console.log('No next button found, ending scrape');
        break;
      }
    }

    // Write to CSV
    console.log(`\nWriting ${exhibitors.length} exhibitors to CSV...`);
    const writer = csv.createObjectCsvWriter({
      path: 'exhibitors.csv',
      header: [
        { id: 'name', title: 'Company Name' },
        { id: 'product', title: 'Main Product' },
        { id: 'country', title: 'Country' },
        { id: 'website', title: 'Website' },
        { id: 'email', title: 'Email' },
      ],
    });

    await writer.writeRecords(exhibitors);
    console.log('CSV file created successfully: exhibitors.csv');

  } catch (error) {
    console.error('Error during scraping:', error);
  } finally {
    await browser.close();
  }
}

scrapeExhibitors();
