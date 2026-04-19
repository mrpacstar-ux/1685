const { chromium } = require('playwright');
const { createClient } = require('@supabase/supabase-js');

const supabase = createClient(process.env.SUPABASE_URL, process.env.SUPABASE_SERVICE_KEY);
const RALLY_URL = "https://www.statsmasterdatahub.com/1685/rallydata/c5eaf4fxkl3vykx";

async function syncRallyRankings() {
    console.log("Launching browser...");
    const browser = await chromium.launch({ headless: true });
    const context = await browser.newContext();
    const page = await context.newPage();

    try {
        console.log(`Navigating to ${RALLY_URL}...`);
        await page.goto(RALLY_URL, { waitUntil: 'networkidle', timeout: 60000 });

        console.log("Selecting 'This Week' filter...");
        const weekButton = page.getByText(/This Week/i).last();
        
        try {
            await weekButton.click();
            console.log("Clicked 'This Week'. Waiting 8 seconds for the full list...");
            // Weekly lists are huge, give it plenty of time to finish the spinny loader
            await page.waitForTimeout(8000); 
        } catch (e) {
            console.log("Filter click skipped (might be default).");
        }

        // Instead of waiting for a specific selector, we just wait for the page to have "ID:" anywhere
        await page.waitForFunction(() => document.body.innerText.includes('ID:'), { timeout: 30000 });
        
        console.log("Scrolling to capture all players...");
        await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
        await page.waitForTimeout(2000);

        const content = await page.innerText('body');

        // This Regex is tuned to match exactly what you see in the logs
        const playerPattern = /([^\n]+)\s+ID:\s*(\d+)\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)/g;
        let match;
        const players = [];

        while ((match = playerPattern.exec(content)) !== null) {
            const nameRaw = match[1].trim();
            // Clean up: removes rank numbers from start and "ID:" from end
            const cleanName = nameRaw.replace(/^\d+/, '').replace(/ID:.*$/, '').trim();

            players.push({
                player_id: match[2],
                name: cleanName || "Unknown",
                launched: parseInt(match[3].replace(/,/g, '')) || 0,
                joined: parseInt(match[4].replace(/,/g, '')) || 0,
                total: parseInt(match[5].replace(/,/g, '')) || 0,
                score: parseInt(match[6].replace(/,/g, '')) || 0,
                updated_at: new Date().toISOString()
            });
        }

        console.log(`Found ${players.length} players total.`);

        if (players.length > 0) {
            const uniquePlayers = Array.from(new Map(players.map(p => [p.player_id, p])).values());
            console.log(`Syncing ${uniquePlayers.length} unique players...`);

            const { error } = await supabase
                .from('player_rankings')
                .upsert(uniquePlayers, { onConflict: 'player_id' });

            if (error) throw error;
            console.log("Success! Check your website now.");
        } else {
            console.log("Regex failed to grab players. Page snapshot (first 200 chars):");
            console.log(content.substring(0, 200));
        }

    } catch (err) {
        console.error("Scraper Error:", err.message);
    } finally {
        await browser.close();
    }
}

syncRallyRankings();
