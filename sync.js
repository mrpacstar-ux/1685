const { chromium } = require('playwright');
const { createClient } = require('@supabase/supabase-js');

const supabase = createClient(process.env.SUPABASE_URL, process.env.SUPABASE_SERVICE_KEY);
const RALLY_URL = "https://www.statsmasterdatahub.com/1685/rallydata/c5eaf4fxkl3vykx";

async function syncRallyRankings() {
    console.log("Launching browser...");
    const browser = await chromium.launch({ 
        headless: true,
        args: ['--disable-blink-features=AutomationControlled'] // Helps bypass bot detection
    });
    
    // Set a realistic User-Agent so it doesn't look like a bot
    const context = await browser.newContext({
        userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    });
    const page = await context.newPage();

    try {
        console.log(`Navigating to ${RALLY_URL}...`);
        // Wait for the network to be quiet
        await page.goto(RALLY_URL, { waitUntil: 'networkidle', timeout: 60000 });
        
        // CRITICAL: Wait for the specific data table to appear
        console.log("Waiting for table data to load...");
        await page.waitForSelector('table tbody tr', { timeout: 20000 });
        
        // Extra 2-second sleep just to be safe for slow animations
        await page.waitForTimeout(2000);

        const players = await page.evaluate(() => {
            const results = [];
            // Target the table body specifically
            const rows = document.querySelectorAll('table tbody tr');

            rows.forEach(row => {
                const cells = row.querySelectorAll('td');
                // Ensure we have the right number of columns (Rank, Player, Launched, Joined, Total, Score)
                if (cells.length >= 5) {
                    const playerText = cells[1].innerText;
                    const idMatch = playerText.match(/ID:\s*(\d+)/);
                    
                    if (idMatch) {
                        const playerId = idMatch[1];
                        // Extract name: get lines, find the one that isn't the ID and isn't just a number
                        const nameLines = playerText.split('\n').map(l => l.trim());
                        const name = nameLines.find(l => !l.includes('ID:') && isNaN(l) && l.length > 0) || "Unknown";
                        
                        results.push({
                            player_id: playerId,
                            name: name,
                            launched: parseInt(cells[2].innerText.replace(/,/g, '')) || 0,
                            joined: parseInt(cells[3].innerText.replace(/,/g, '')) || 0,
                            total: parseInt(cells[4].innerText.replace(/,/g, '')) || 0,
                            score: parseInt(cells[5]?.innerText.replace(/,/g, '')) || 0,
                            updated_at: new Date().toISOString()
                        });
                    }
                }
            });
            return results;
        });

        console.log(`Successfully found ${players.length} players.`);

        if (players.length > 0) {
            // Deduplicate to prevent Supabase errors
            const uniquePlayers = Array.from(new Map(players.map(p => [p.player_id, p])).values());
            
            const { error } = await supabase
                .from('player_rankings')
                .upsert(uniquePlayers, { onConflict: 'player_id' });

            if (error) throw error;
            console.log(`Synced ${uniquePlayers.length} players to database.`);
        } else {
            console.log("Warning: Table was found but it was empty. The site might be blocking the scraper script.");
        }

    } catch (err) {
        console.error("Scraper Error:", err.message);
        // Take a screenshot if it fails so we can see what the bot sees
        if (page) await page.screenshot({ path: 'error_screenshot.png' });
    } finally {
        await browser.close();
    }
}

syncRallyRankings();
