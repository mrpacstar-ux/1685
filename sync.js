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
        await page.waitForTimeout(5000); // Wait for dynamic content

        const players = await page.evaluate(() => {
            const results = [];
            // Target all table rows (excluding the header)
            const rows = document.querySelectorAll('tbody tr');

            rows.forEach(row => {
                const cells = row.querySelectorAll('td');
                if (cells.length >= 4) {
                    // Column 1 usually contains Player Name + ID
                    const playerText = cells[1].innerText;
                    const idMatch = playerText.match(/(\d{8,10})/); // Looks for 8-10 digit IDs

                    if (idMatch) {
                        const playerId = idMatch[1];
                        // Name is usually the line NOT containing the ID
                        const name = playerText.split('\n').find(l => !l.includes(playerId) && l.trim().length > 1) || "Unknown";
                        
                        results.push({
                            player_id: playerId,
                            name: name.trim(),
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

        console.log(`Found ${players.length} players. Cleaning...`);

        // Deduplicate
        const uniquePlayers = Array.from(new Map(players.map(p => [p.player_id, p])).values());

        if (uniquePlayers.length > 0) {
            const { error } = await supabase
                .from('player_rankings')
                .upsert(uniquePlayers, { onConflict: 'player_id' });

            if (error) console.error("Supabase Error:", error.message);
            else console.log("Success! Data synced.");
        }
    } catch (err) {
        console.error("Scraper Error:", err.message);
    } finally {
        await browser.close();
    }
}
syncRallyRankings();
