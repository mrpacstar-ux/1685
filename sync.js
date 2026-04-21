const { chromium } = require('playwright');
const { createClient } = require('@supabase/supabase-js');

// --- CONFIGURATION ---
const SUPABASE_URL = process.env.SUPABASE_URL || 'https://fqnlvclorxwovabydhjg.supabase.co';
const SUPABASE_KEY = process.env.SUPABASE_KEY || 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImZxbmx2Y2xvcnh3b3ZhYnlkaGpnIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3NjU4NDMyNywiZXhwIjoyMDkyMTYwMzI3fQ.e7MZI90VtYVfiL5C1hwItctT1S0RGQvqOg-s7W8TWmY';

const FORT_LINK = "https://www.statsmasterdatahub.com/1685/rallydata/c5eaf4fxkl3vykx";
const KVK_LINK = "https://www.statsmasterdatahub.com/c13048/dashboard/ymheormqhugrg1a";

const supabase = createClient(SUPABASE_URL, SUPABASE_KEY);

async function runSync() {
    console.log("🚀 Launching browser...");
    const browser = await chromium.launch({ headless: true });
    const context = await browser.newContext({
        userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
    });
    const page = await context.newPage();

    try {
        // --- 1. SCRAPE BARBARIAN FORTS ---
        console.log(`📡 Navigating to Fort Data: ${FORT_LINK}`);
        await page.goto(FORT_LINK, { waitUntil: 'networkidle', timeout: 60000 });
        
        console.log("⏳ Waiting for data to render...");
        await page.waitForSelector('span:has-text("ID:")', { state: 'attached', timeout: 30000 });

        const fortData = await page.evaluate(() => {
            const entries = Array.from(document.querySelectorAll('div')).filter(el => 
                el.innerText.includes('ID:') && el.innerText.includes('Level')
            );
            
            return entries.map(el => {
                const text = el.innerText;
                const levelMatch = text.match(/Level\s*(\d+)/i);
                const coordsMatch = text.match(/X:\s*(\d+)\s*Y:\s*(\d+)/i);
                const idMatch = text.match(/ID:\s*(\d+)/i);
                
                const lines = text.split('\n');
                const name = lines[0].split('Level')[0].trim();

                if (levelMatch && coordsMatch) {
                    return {
                        level: levelMatch[1],
                        coords: coordsMatch[0],
                        player: name || (idMatch ? idMatch[1] : 'Unknown'),
                        updated_at: new Date().toISOString()
                    };
                }
                return null;
            }).filter(item => item !== null);
        });

        const uniqueForts = Array.from(new Map(fortData.map(item => [item.coords, item])).values());

        console.log(`✅ Found ${uniqueForts.length} unique rallies.`);
        
        if (uniqueForts.length > 0) {
            // Delete old data (Filter ensures we don't accidentally wipe unrelated rows)
            await supabase.from('fort_tracking').delete().neq('level', '-1'); 
            const { error: fortError } = await supabase.from('fort_tracking').insert(uniqueForts);
            if (fortError) console.error("❌ Supabase Fort Error:", fortError.message);
            else console.log("💾 Forts updated in Supabase.");
        }

        // --- 2. SCRAPE KVK DASHBOARD ---
        console.log(`📡 Navigating to KvK Dashboard: ${KVK_LINK}`);
        await page.goto(KVK_LINK, { waitUntil: 'networkidle', timeout: 60000 });

        const kvkStats = await page.evaluate(() => {
            const bodyText = document.body.innerText;
            const powerMatch = bodyText.match(/([\d.]+B|M)\s*Power/i) || bodyText.match(/Power\s*([\d.]+B|M)/i);
            const killsMatch = bodyText.match(/([\d.]+B|M)\s*Kill/i) || bodyText.match(/Kill\s*Points\s*([\d.]+B|M)/i);

            return {
                power: powerMatch ? powerMatch[1] : 'N/A',
                kills: killsMatch ? killsMatch[1] : 'N/A'
            };
        });

        console.log(`✅ KvK Stats: Power: ${kvkStats.power}, Kills: ${kvkStats.kills}`);
        
        const { error: statsError } = await supabase.from('kingdom_stats').update({
            power: kvkStats.power,
            kills: kvkStats.kills,
            last_sync: new Date().toISOString()
        }).eq('id', 1);

        if (statsError) console.error("❌ Supabase Stats Error:", statsError.message);
        else console.log("💾 Kingdom stats updated in Supabase.");

    } catch (error) {
        console.error("❌ Critical Scraper Error:", error.message);
    } finally {
        await browser.close();
        console.log("🏁 Sync process finished.");
    }
}

runSync();
