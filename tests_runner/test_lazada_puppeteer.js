const puppeteer = require('puppeteer');
const crypto = require('crypto');
require('dotenv').config({ path: '.env.local' });

function signLazada(apiPath, params, appSecret) {
    const sortedKeys = Object.keys(params).sort();
    let signStr = apiPath;
    for (const key of sortedKeys) {
        signStr += `${key}${params[key]}`;
    }
    return crypto.createHmac('sha256', appSecret).update(signStr, 'utf8').digest('hex').toUpperCase();
}

async function runPuppeteerTest() {
    console.log("==================================================");
    console.log("🚀 [TEST 2: PUPPETEER] Scraping Search & Official API Affiliate Link");
    console.log("==================================================");

    const appKey = process.env.LAZADA_LiteApp_Key || process.env.LAZADA_APP_KEY;
    const appSecret = process.env.LAZADA_LiteApp_Secret || process.env.LAZADA_APP_SECRET;
    const userToken = process.env.LAZADA_USER_TOKEN;

    if (!appKey || !appSecret || !userToken) {
        throw new Error("❌ [RALAT KUNCI API]: Kunci LAZADA_APP_KEY/SECRET/USER_TOKEN tidak ditemui!");
    }

    const browser = await puppeteer.launch({
        headless: true,
        args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
    });

    try {
        const page = await browser.newPage();
        await page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, Gecko) Chrome/120.0.0.0 Safari/537.36');
        
        console.log("🌐 Membuka halaman carian Lazada...");
        await page.goto('https://www.lazada.com.my/catalog/?q=kucing', { waitUntil: 'domcontentloaded', timeout: 30000 });

        console.log("🔍 Ekstrak pautan produk dari paparan...");
        const productLinks = await page.evaluate(() => {
            const anchors = Array.from(document.querySelectorAll('a[href*="-i"]'));
            return anchors.map(a => a.href).filter(href => href.includes('lazada.com.my/products/'));
        });

        console.log(`📦 Ditemui ${productLinks.length} pautan produk di halaman web.`);

        if (productLinks.length === 0) {
            throw new Error("❌ Puppeteer gagal mencari pautan produk di Lazada web.");
        }

        // Ekstrak Product ID dari URL
        const firstUrl = productLinks[0];
        const match = firstUrl.match(/-i(\d+)/);
        const productId = match ? match[1] : null;

        if (!productId) {
            throw new Error(`❌ Gagal mengekstrak Product ID dari URL: ${firstUrl}`);
        }

        console.log(`✅ Product ID Ditemui: ${productId}`);

        // Panggil API Rasmi untuk mendapatkan Link Affiliate
        const timestamp = Date.now().toString();
        const apiPath = "/marketing/product/link";
        const params = {
            app_key: appKey.trim(),
            timestamp: timestamp,
            sign_method: "sha256",
            userToken: userToken.trim(),
            productId: productId
        };
        params.sign = signLazada(apiPath, params, appSecret.trim());

        const queryString = new URLSearchParams(params).toString();
        const apiResponse = await fetch(`https://api.lazada.com.my/rest${apiPath}?${queryString}`);
        const resJson = await apiResponse.json();

        console.log("📊 API Response Code:", resJson.code);
        if (resJson.code !== "0" && resJson.code !== 0) {
            throw new Error(`Lazada API Failure: ${JSON.stringify(resJson, null, 2)}`);
        }

        const trackingLink = resJson.result?.data?.trackingLink || resJson.trackingLink;
        console.log(`🔗 Link Affiliate Rasmi: ${trackingLink}`);
        console.log("🟢 [SUCCESS: PUPPETEER TEST PASSED]");

    } catch (err) {
        console.error("\n💥 [TEST 2 GAGAL] Stack Trace Ralat Terperinci:");
        console.error(err.stack || err);
        process.exit(1);
    } finally {
        await browser.close();
    }
}

runPuppeteerTest();