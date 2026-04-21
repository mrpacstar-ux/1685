const { chromium } = require('playwright');
const { createClient } = require('@supabase/supabase-js');

const SUPABASE_URL = process.env.SUPABASE_URL || 'https://fqnlvclorxwovabydhjg.supabase.co';
const SUPABASE_KEY = process.env.SUPABASE_KEY || 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImZxbmx2Y2xvcnh3b3ZhYnlkaGpnIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3NjU4NDMyNywiZXhwIjoyMDkyMTYwMzI3fQ.e7MZI90VtYVfiL5C1hwItctT1S0RGQvqOg-s7W8TWmY';

const FORT_LINK = "https://www.statsmasterdatahub.com/1685/rallydata/c5eaf4fxkl3vykx";
const KVK_LINK = "https://www.statsmasterdatahub.com/c13048/dashboard/ymheormqhugrg1a";

const supabase = createClient(SUPABASE_URL, SUPABASE_KEY);

async function runSync() {
    console.log("🚀 Launching browser...");
    const browser = await chromium.launch({ headless: true });
    const context = await browser.newContext({ viewport: { width: 1920, height: 1080 } });
    const page = await context.newPage();

    try {
        // --- 1. SCRAPE BARBARIAN FORTS ---
        console.log(`📡 Navigating to Fort Data...`);
        await page.goto(FORT_LINK, { waitUntil: 'networkidle' });
        await page.waitForTimeout(5000); 

        // Statmaster fix: Some tables only load after a scroll
        await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
        await page.waitForTimeout(2000);

        console.log("⏳ Scanning for all text containing coordinates...");
        const fortData = await page.evaluate(() => {
            // Find every single DIV on the page and check if it has X: and Y:
            const allElements = Array.from(document.querySelectorAll('div, tr, li'));
            const results = [];

            allElements.forEach(el => {
                const text = el.innerText;
                const coordsMatch = text.match(/X:\s*(\d+)\s*Y:\s*(\d+)/i);
                // Look for Level nearby
                const levelMatch = text.match(/Lvl\s*(\d+)|Level\s*(\d+)/i);

                if (coordsMatch) {
                    results.push({
                        level: levelMatch ? (levelMatch[1] || levelMatch[2]) : '5', 
                        coords: `X:${coordsMatch[1]} Y:${coordsMatch[2]}`,
                        player: text.split('\n')[0].substring(0, 20).trim(), // Grab first line
                        updated_at: new Date().toISOString()
                    });
                }
            });
            return results;
        });

        const uniqueForts = Array.from(new Map(fortData.map(f => [f.coords, f])).values());
        console.log(`✅ Found ${uniqueForts.length} unique rallies.`);

        if (uniqueForts.length > 0) {
            await supabase.from('fort_tracking').delete().neq('level', '-1'); 
            await supabase.from('fort_tracking').insert(uniqueForts);
        } else {
            // DEBUG: Save a screenshot if nothing found so you can see what went wrong
            await page.screenshot({ path: 'fort_debug.png' });
            console.log("📸 Screenshot saved as fort_debug.png (Check your GitHub Action artifacts)");
        }

        // --- 2. SCRAPE KVK DASHBOARD ---
        console.log(`📡 Navigating to KvK Dashboard...`);
        await page.goto(KVK_LINK, { waitUntil: 'networkidle' });
        await page.waitForTimeout(7000); // Dashboards are slow

        const kvkStats = await page.evaluate(() => {
            const body = document.body.innerText;
            // More aggressive Regex for Kill Points
            const pMatch = body.match(/Power\s*[:\n\s]*([\d.]+[BMK])/i) || body.match(/([\d.]+[BMK])\s*Power/i);
            const kMatch = body.match(/Kill\s*Points\s*[:\n\s]*([\d.]+[BMK])/i) || body.match(/([\d.]+[BMK])\s*Kill/i);

            return {
                power: pMatch ? pMatch[1] : 'N/A',
                kills: kMatch ? kMatch[1] : 'N/A'
            };
        });

        console.log(`✅ KvK Stats: Power: ${kvkStats.power}, Kills: ${kvkStats.kills}`);

        await supabase.from('kingdom_stats').update({
            power: kvkStats.power,
            kills: kvkStats.kills,
            last_sync: new Date().toISOString()
        }).eq('id', 1);

    } catch (error) {
        console.error("❌ Scraper Error:", error.message);
    } finally {
        await browser.close();
        console.log("🏁 Sync process finished.");
    }
}

runSync();
