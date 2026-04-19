const { chromium } = require('playwright');
const { createClient } = require('@supabase/supabase-js');

const supabase = createClient(process.env.SUPABASE_URL, process.env.SUPABASE_SERVICE_KEY);
const RALLY_URL = "https://www.statsmasterdatahub.com/1685/rallydata/c5eaf4fxkl3vykx";

async function syncRallyRankings() {
    console.log("Launching browser...");
    const browser = await chromium.launch({ headless: true });
    const context = await browser.newContext({
        userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    });
    const page = await context.newPage();

    try {
        console.log(`Navigating to ${RALLY_URL}...`);
        await page.goto(RALLY_URL, { waitUntil: 'networkidle', timeout: 60000 });

        // 1. Handle "This Week" Filter with Strict Mode Fix
        console.log("Selecting 'This Week' filter...");
        const weekButton = page.getByText(/This Week/i).last();
        
        try {
            await weekButton.waitFor({ state: 'visible', timeout: 10000 });
            await weekButton.click();
            console.log("Clicked 'This Week'. Waiting for data to refresh...");
            // Weekly data takes longer to load, so we wait 5 seconds
            await page.waitForTimeout(5000); 
        } catch (e) {
            console.log("Could not click 'This Week' button, it may already be selected.");
        }

        // 2. Ensure data is present before scraping
        console.log("Waiting for player rows...");
        await page.waitForSelector('text=ID:', { timeout: 20000 });
        
        // Scroll to trigger lazy loading for the full list of players
        await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
        await page.waitForTimeout(2000);

        // 3. Extract all page text
        const content = await page.innerText('body');

        // 4. Regex Pattern to capture: Name, ID: 123, Launched, Joined, Total, Score
        const playerPattern = /([^\n]+)\s+ID:\s*(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)/g;
        let match;
        const players = [];

        while ((match = playerPattern.exec(content)) !== null) {
            const nameRaw = match[1].trim();
            
            // CLEANING: Remove leading rank numbers (e.g., "1Siłvєr" -> "Siłvєr")
            // and remove any stray "ID:" text if the regex caught it
            const cleanName = nameRaw.replace(/^\d+/, '').replace(/ID:.*$/, '').trim();

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

        console.log(`Found ${players.length} players total.`);

        if (players.length > 0) {
            // Deduplicate by player_id
            const uniquePlayers = Array.from(new Map(players.map(p => [p.player_id, p])).values());
            console.log(`Syncing ${uniquePlayers.length} unique players to Supabase...`);

            const { error } = await supabase
                .from('player_rankings')
                .upsert(uniquePlayers, { onConflict: 'player_id' });

            if (error) throw error;
            console.log("Success! Data is now live in Supabase.");
        } else {
            console.log("Error: Scraper found 0 players. The page layout might have changed.");
        }

    } catch (err) {
        console.error("Critical Scraper Error:", err.message);
    } finally {
        await browser.close();
    }
}

syncRallyRankings();
