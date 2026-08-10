const puppeteer = require('puppeteer-extra');
const StealthPlugin = require('puppeteer-extra-plugin-stealth');
const crypto = require('crypto');
require('dotenv').config({ path: '.env.local' });

// Aktifkan Stealth Plugin untuk menyorokkan identiti automasi
puppeteer.use(StealthPlugin());

function signLazada(apiPath, params, appSecret) {
    const sortedKeys = Object.keys(params).sort();
    let signStr = apiPath;
    for (const key of sortedKeys) {
        signStr += `${key}${params[key]}`;
    }
    return crypto.createHmac('sha256', appSecret).update(signStr, 'utf8').digest('hex').toUpperCase();
}

async function runPuppeteerStealthTest() {
    console.log("==================================================");
    console.log("🚀 [TEST 2B: PUPPETEER STEALTH] Mobile Web & Anti-Bot Bypass");
    console.log("==================================================");

    const appKey = process.env.LAZADA_LiteApp_Key || process.env.LAZADA_APP_KEY;
    const appSecret = process.env.LAZADA_LiteApp_Secret || process.env.LAZADA_APP_SECRET;
    const userToken = process.env.LAZADA_USER_TOKEN;

    if (!appKey || !appSecret || !userToken) {
        throw new Error("❌ [RALAT KUNCI API]: Kunci LAZADA_APP_KEY/SECRET/USER_TOKEN tidak ditemui!");
    }

    const browser = await puppeteer.launch({
        headless: true,
        args: [
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--disable-blink-features=AutomationControlled'
        ]
    });

    try {
        const page = await browser.newPage();

        // 1. Set Viewport & User-Agent emulasi peranti mobil (iPhone 13)
        await page.setViewport({ width: 390, height: 844, isMobile: true, hasTouch: true });
        await page.setUserAgent('Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1');

        let foundProductId = null;

        // 2. Pintasan Rangkaian (Network Intercept) untuk tangkap JSON response
        page.on('response', async (response) => {
            const url = response.url();
            if (url.includes('search') || url.includes('catalog') || url.includes('api')) {
                try {
                    const contentType = response.headers()['content-type'] || '';
                    if (contentType.includes('application/json')) {
                        const text = await response.text();
                        const matches = text.match(/"itemId":\s*"(\d+)"/) || text.match(/"productId":\s*"(\d+)"/);
                        if (matches && !foundProductId) {
                            foundProductId = matches[1];
                        }
                    }
                } catch (e) {
                    // Abaikan ralat pembacaan response
                }
            }
        });

        console.log("🌐 [Puppeteer Stealth] Membuka Lazada Mobile Search...");
        await page.goto('https://m.lazada.com.my/h5/search/index?q=kucing', {
            waitUntil: 'networkidle2',
            timeout: 35000
        });

        // 3. Fallback: Cari pautan terus di HTML Mobile jika network intercept gagal
        if (!foundProductId) {
            console.log("🔍 Mencari pautan produk dari DOM Mobile...");
            foundProductId = await page.evaluate(() => {
                const anchors = Array.from(document.querySelectorAll('a[href*="i"]'));
                for (const a of anchors) {
                    const href = a.href || '';
                    const match = href.match(/i(\d+)\.html/) || href.match(/-i(\d+)/);
                    if (match) return match[1];
                }
                return null;
            });
        }

        if (!foundProductId) {
            throw new Error("❌ [PUPPETEER STEALTH FAILED]: Pelayan Lazada masih mengesan IP Cloud GitHub Actions & menyekat halaman.");
        }

        console.log(`✅ Product ID Berjaya Ditemui: ${foundProductId}`);

        // 4. Penjanaan Link Affiliate Rasmi
        const timestamp = Date.now().toString();
        const apiPath = "/marketing/product/link";
        const params = {
            app_key: appKey.trim(),
            timestamp: timestamp,
            sign_method: "sha256",
            userToken: userToken.trim(),
            productId: foundProductId
        };
        params.sign = signLazada(apiPath, params, appSecret.trim());

        const queryString = new URLSearchParams(params).toString();
        const apiResponse = await fetch(`https://api.lazada.com.my/rest${apiPath}?${queryString}`);
        const resJson = await apiResponse.json();

        if (resJson.code !== "0" && resJson.code !== 0) {
            throw new Error(`Lazada API Failure: ${JSON.stringify(resJson, null, 2)}`);
        }

        const trackingLink = resJson.result?.data?.trackingLink || resJson.trackingLink;
        console.log(`🔗 Link Affiliate Rasmi: ${trackingLink}`);
        console.log("🟢 [SUCCESS: PUPPETEER STEALTH TEST PASSED]");

    } catch (err) {
        console.error("\n💥 [TEST PUPPETEER STEALTH GAGAL] Stack Trace Ralat Terperinci:");
        console.error(err.stack || err);
        process.exit(1);
    } finally {
        await browser.close();
    }
}

runPuppeteerStealthTest();