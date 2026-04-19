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

        // 1. Click "This Week"
        const weekButton = page.getByText(/This Week/i).last();
        await weekButton.click();
        await page.waitForTimeout(5000); // Wait for the table to populate

        // 2. Extract directly from the table elements in the browser
        const players = await page.evaluate(() => {
            const data = [];
            // Target every row in the table body
            const rows = document.querySelectorAll('table tbody tr');
            
            rows.forEach(row => {
                const cells = row.querySelectorAll('td');
                if (cells.length >= 5) {
                    // Extract text content from cells
                    // Column 0: Rank, 1: Player+ID, 2: Launched, 3: Joined, 4: Total, 5: Rally Score
                    const playerCell = cells[1].innerText;
                    const idMatch = playerCell.match(/\d{7,10}/); // Find the 7-10 digit ID

                    if (idMatch) {
                        data.push({
                            player_id: idMatch[0],
                            name: playerCell.replace(idMatch[0], '').replace('ID:', '').trim(),
                            launched: parseInt(cells[2].innerText.replace(/[^0-9]/g, '')) || 0,
                            joined: parseInt(cells[3].innerText.replace(/[^0-9]/g, '')) || 0,
                            total: parseInt(cells[4].innerText.replace(/[^0-9]/g, '')) || 0,
                            score: parseInt(cells[5].innerText.replace(/[^0-9]/g, '')) || 0,
                            updated_at: new Date().toISOString()
                        });
                    }
                }
            });
            return data;
        });

        console.log(`Found ${players.length} players via DOM extraction.`);

        if (players.length > 0) {
            const { error } = await supabase
                .from('player_rankings')
                .upsert(players, { onConflict: 'player_id' });

            if (error) throw error;
            console.log("Data synced successfully!");
        }
    } catch (err) {
        console.error("Scraper Error:", err.message);
    } finally {
        await browser.close();
    }
}

syncRallyRankings();
