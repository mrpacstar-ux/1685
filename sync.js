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

        // 1. Force a click on "This Week"
        console.log("Selecting 'This Week' filter...");
        // Using a regex for 'This Week' to handle potential capitalization/spacing differences
        const weekButton = await page.getByText(/This Week/i);
        
        if (await weekButton.isVisible()) {
            await weekButton.click();
            console.log("Clicked 'This Week'. Waiting for data to refresh...");
            // Give the site 3 seconds to process the filter change
            await page.waitForTimeout(3000); 
        } else {
            console.log("Could not find 'This Week' button. Proceeding with default view...");
        }

        // 2. Wait for the player rows to appear
        await page.waitForSelector('text=ID:', { timeout: 20000 });
        
        // Scroll to the bottom to ensure "Lazy Loading" captures all 260+ players
        await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
        await page.waitForTimeout(2000);

        // 3. Extract the text content
        const content = await page.innerText('body');

        // 4. Regex Pattern to capture Name, ID, and the 4 stat numbers
        const playerPattern = /([^\n]+)\s+ID:\s*(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)/g;
        let match;
        const players = [];

        while ((match = playerPattern.exec(content)) !== null) {
            const nameRaw = match[1].trim();
            // Clean up rank numbers (e.g., "1Siłvєr" -> "Siłvєr")
            const cleanName = nameRaw.replace(/^\d+/, '').trim();

            players.push({
                player_id: match[2],
                name: cleanName || "Unknown",
                launched: parseInt(match[3]) || 0,
                joined: parseInt(match[4]) || 0,
                total: parseInt(match[5]) || 0,
                score: parseInt(match[6]) || 0,
                updated_at: new Date().toISOString()
            });
        }

        console.log(`Found ${players.length} players for the week.`);

        if (players.length > 0) {
            // Deduplicate
            const uniquePlayers = Array.from(new Map(players.map(p => [p.player_id, p])).values());
            
            const { error } = await supabase
                .from('player_rankings')
                .upsert(uniquePlayers, { onConflict: 'player_id' });

            if (error) throw error;
            console.log(`Success! ${uniquePlayers.length} records updated in Supabase.`);
        } else {
            console.log("Pattern match failed. Check if 'This Week' view layout is different.");
        }

    } catch (err) {
        console.error("Scraper Error:", err.message);
    } finally {
        await browser.close();
    }
}

syncRallyRankings();
