const { chromium } = require('playwright');
const { createClient } = require('@supabase/supabase-js');

// --- CONFIGURATION ---
const SUPABASE_URL = 'YOUR_SUPABASE_URL';
const SUPABASE_KEY = 'YOUR_SUPABASE_SERVICE_ROLE_KEY'; // Use Service Role for backend scripts

const FORT_LINK = "https://www.statsmasterdatahub.com/1685/rallydata/c5eaf4fxkl3vykx";
const KVK_LINK = "https://www.statsmasterdatahub.com/c13048/dashboard/ymheormqhugrg1a";

const supabase = createClient(SUPABASE_URL, SUPABASE_KEY);

async function runSync() {
    console.log("🚀 Launching browser...");
    const browser = await chromium.launch({ headless: true });
    const context = await browser.newContext({
        userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'
    });
    const page = await context.newPage();

    try {
        // --- 1. SCRAPE BARBARIAN FORTS ---
        console.log(`📡 Navigating to Fort Data...`);
        await page.goto(FORT_LINK, { waitUntil: 'networkidle' });
        
        // Wait for the specific data ID span to ensure the list is rendered
        await page.waitForSelector('span:has-text("ID:")', { timeout: 20000 });

        const fortData = await page.evaluate(() => {
            // Find all containers that look like rally entries
            // Statmaster typically uses a flex or grid structure for these lists
            const entries = Array.from(document.querySelectorAll('div.flex.justify-between, .grid-cols-1'));
            
            return entries.map(el => {
                const text = el.innerText;
                const levelMatch = text.match(/Level\s*(\d+)/i);
                const coordsMatch = text.match(/X:\s*(\d+)\s*Y:\s*(\d+)/i);
                const playerMatch = text.match(/ID:\s*(\d+)/i); // Fallback to ID if name is hard to parse

                if (levelMatch && coordsMatch) {
                    return {
                        level: levelMatch[1],
                        coords: coordsMatch[0],
                        player: playerMatch ? playerMatch[1] : 'Unknown',
                        updated_at: new Date().toISOString()
                    };
                }
                return null;
            }).filter(item => item !== null);
        });

        console.log(`✅ Found ${fortData.length} forts. Updating Supabase...`);
        if (fortData.length > 0) {
            // Clear old forts and insert new ones
            await supabase.from('fort_tracking').delete().neq('level', '0'); 
            await supabase.from('fort_tracking').insert(fortData);
        }

        // --- 2. SCRAPE KVK DASHBOARD ---
        console.log(`📡 Navigating to KvK Dashboard...`);
        await page.goto(KVK_LINK, { waitUntil: 'networkidle' });

        const kvkStats = await page.evaluate(() => {
            // Look for Power and Kill numbers. 
            // We use a broad search for strings ending in 'B' or 'M' near labels.
            const bodyText = document.body.innerText;
            const powerMatch = bodyText.match(/([\d.]+B)\s*Power/i) || bodyText.match(/Power\s*([\d.]+B)/i);
            const killsMatch = bodyText.match(/([\d.]+B)\s*Kills/i) || bodyText.match(/Kills\s*([\d.]+B)/i);

            return {
                power: powerMatch ? powerMatch[1] : 'N/A',
                kills: killsMatch ? killsMatch[1] : 'N/A'
            };
        });

        console.log(`✅ Stats Found: Power: ${kvkStats.power}, Kills: ${kvkStats.kills}`);
        
        await supabase.from('kingdom_stats').update({
            power: kvkStats.power,
            kills: kvkStats.kills,
            last_sync: new Date().toISOString()
        }).eq('id', 1); // Assuming your kingdom row is ID 1

    } catch (error) {
        console.error("❌ Scraper Error:", error.message);
    } finally {
        await browser.close();
        console.log("🏁 Sync process finished.");
    }
}

runSync();
