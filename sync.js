const { chromium } = require('playwright');
const { createClient } = require('@supabase/supabase-js');

const supabase = createClient(process.env.SUPABASE_URL, process.env.SUPABASE_SERVICE_KEY);
const RALLY_URL = "https://www.statsmasterdatahub.com/1685/rallydata/c5eaf4fxkl3vykx";

async function syncRallyRankings() {
    console.log("Launching browser in Sniffer Mode...");
    const browser = await chromium.launch({ headless: true });
    const context = await browser.newContext();
    const page = await context.newPage();

    let jsonData = null;

    // Eavesdrop on all network requests the page makes
    page.on('response', async (response) => {
        const url = response.url();
        // Look for the specific data endpoint (usually contains 'rallydata' or 'json')
        if (url.includes('rallydata') && response.status() === 200) {
            try {
                const text = await response.text();
                // Check if this response looks like the player data we need
                if (text.includes('ID:')) {
                    jsonData = text;
                    console.log("Found the data source!");
                }
            } catch (e) { /* Not the response we wanted */ }
        }
    });

    try {
        await page.goto(RALLY_URL, { waitUntil: 'networkidle', timeout: 60000 });
        
        // Wait a few seconds for the background data fetch to finish
        await page.waitForTimeout(5000);

        // If sniffing failed, fall back to a "force-read" of the entire page body
        const content = jsonData || await page.innerText('body');
        
        // This regex looks for patterns like: Name, ID: 12345, 10, 20, 30...
        const playerPattern = /([^\n]+)\s+ID:\s*(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)/g;
        let match;
        const players = [];

        while ((match = playerPattern.exec(content)) !== null) {
            players.push({
                player_id: match[2],
                name: match[1].trim().replace(/^\d+\s+/, ''), // Clean leading rank numbers
                launched: parseInt(match[3]) || 0,
                joined: parseInt(match[4]) || 0,
                total: parseInt(match[5]) || 0,
                score: parseInt(match[6]) || 0,
                updated_at: new Date().toISOString()
            });
        }

        console.log(`Found ${players.length} players via network/regex scan.`);

        if (players.length > 0) {
            const uniquePlayers = Array.from(new Map(players.map(p => [p.player_id, p])).values());
            
            const { error } = await supabase
                .from('player_rankings')
                .upsert(uniquePlayers, { onConflict: 'player_id' });

            if (error) throw error;
            console.log("Success! Data synced to Supabase.");
        } else {
            console.log("No data matches found. Printing first 100 chars for debug:");
            console.log(content.substring(0, 100));
        }

    } catch (err) {
        console.error("Critical Error:", err.message);
    } finally {
        await browser.close();
    }
}

syncRallyRankings();
