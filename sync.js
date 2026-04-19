const { chromium } = require('playwright');
const { createClient } = require('@supabase/supabase-js');

const supabase = createClient(process.env.SUPABASE_URL, process.env.SUPABASE_SERVICE_KEY);
const RALLY_URL = "https://www.statsmasterdatahub.com/1685/rallydata/c5eaf4fxkl3vykx";

async function syncRallyRankings() {
    console.log("Launching browser...");
    const browser = await chromium.launch({ headless: true });
    const page = await browser.newPage();

    try {
        await page.goto(RALLY_URL, { waitUntil: 'networkidle', timeout: 60000 });
        console.log("Page loaded. Waiting for table content...");
        
        // Wait for the table rows to appear
        await page.waitForSelector('tr', { timeout: 15000 });

        const players = await page.evaluate(() => {
            const results = [];
            // Target table rows
            const rows = Array.from(document.querySelectorAll('tr'));

            rows.forEach(row => {
                const cells = Array.from(row.querySelectorAll('td'));
                
                // We need rows that have at least 5 columns (Rank, Player, Launched, Joined, Total, Score)
                if (cells.length >= 5) {
                    const playerCell = cells[1].innerText; // Second column has Name and ID
                    const idMatch = playerCell.match(/ID:\s*(\d+)/);
                    
                    // Clean the name: remove the ID and the rank number
                    let name = playerCell.split('\n').find(line => !line.includes('ID:') && isNaN(line.trim())) || "Unknown";
                    
                    if (idMatch) {
                        results.push({
                            player_id: idMatch[1],
                            name: name.trim(),
                            // Target specific columns based on the Statmaster layout
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

        console.log(`Scraper found ${players.length} players with stats.`);

        if (players.length > 0) {
            // Deduplicate by ID
            const uniquePlayers = Array.from(
                new Map(players.map(p => [p.player_id, p])).values()
            );
            
            const { error } = await supabase
                .from('player_rankings')
                .upsert(uniquePlayers, { onConflict: 'player_id' });

            if (error) {
                console.error("Supabase Error:", error.message);
            } else {
                console.log(`Success! Synced ${uniquePlayers.length} unique players to Supabase.`);
            }
        }

    } catch (err) {
        console.error("Scraper Error:", err.message);
    } finally {
        await browser.close();
    }
}

syncRallyRankings();
