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
    const context = await browser.newContext({ viewport: { width: 1280, height: 800 } });
    const page = await context.newPage();

    try {
        // --- 1. SCRAPE BARBARIAN FORTS ---
        console.log(`📡 Navigating to Fort Data...`);
        await page.goto(FORT_LINK, { waitUntil: 'networkidle' });

        // Statmaster often requires clicking the 'This Week' tab to show data
        console.log("🖱️ Attempting to select 'This Week' filter...");
        const filterBtn = page.locator('button:has-text("This Week"), div:has-text("This Week")').first();
        if (await filterBtn.isVisible()) {
            await filterBtn.click();
            await page.waitForTimeout(2000); // Wait for filter animation
        }

        console.log("⏳ Scanning for rally entries...");
        const fortData = await page.evaluate(() => {
            // Target the specific data rows in the Statmaster hub
            const rows = Array.from(document.querySelectorAll('div')).filter(el => 
                el.innerText.includes('X:') && el.innerText.includes('Y:')
            );
            
            return rows.map(el => {
                const text = el.innerText;
                const lvl = text.match(/Level\s*(\d+)/i);
                const coords = text.match(/X:\s*\d+\s*Y:\s*\d+/i);
                if (lvl && coords) {
                    return {
                        level: lvl[1],
                        coords: coords[0].replace(/\s+/g, ' '),
                        player: text.split('\n')[0].trim(),
                        updated_at: new Date().toISOString()
                    };
                }
                return null;
            }).filter(Boolean);
        });

        const uniqueForts = Array.from(new Map(fortData.map(f => [f.coords, f])).values());
        console.log(`✅ Found ${uniqueForts.length} unique rallies.`);

        if (uniqueForts.length > 0) {
            await supabase.from('fort_tracking').delete().neq('level', '-1'); 
            await supabase.from('fort_tracking').insert(uniqueForts);
        }

        // --- 2. SCRAPE KVK DASHBOARD ---
        console.log(`📡 Navigating to KvK Dashboard...`);
        await page.goto(KVK_LINK, { waitUntil: 'networkidle' });
        await page.waitForTimeout(5000); // Give the dashboard charts time to load

        const kvkStats = await page.evaluate(() => {
            const findStat = (label) => {
                const elements = Array.from(document.querySelectorAll('div, span, p'));
                const target = elements.find(el => el.innerText.trim() === label);
                if (target && target.parentElement) {
                    // Look for a number (like 8.27B) in the same container
                    const val = target.parentElement.innerText.match(/[\d.]+([BMK])/);
                    return val ? val[0] : 'N/A';
                }
                return 'N/A';
            };

            return {
                power: findStat('Power'),
                kills: findStat('Kill Points') || findStat('Kills')
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
