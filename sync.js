const { chromium } = require('playwright');
const { createClient } = require('@supabase/supabase-js');

const supabase = createClient(process.env.SUPABASE_URL, process.env.SUPABASE_SERVICE_KEY);
const RALLY_URL = "https://www.statsmasterdatahub.com/1685/rallydata/c5eaf4fxkl3vykx";

async function syncRallyRankings() {
    console.log("Launching browser to bypass protection...");
    const browser = await chromium.launch({ headless: true });
    const page = await browser.newPage();

    try {
        // Navigate and wait for the content
        await page.goto(RALLY_URL, { waitUntil: 'networkidle', timeout: 60000 });
        
        // Give it a few seconds to ensure the table fully renders
        await page.waitForTimeout(5000);

        const players = await page.evaluate(() => {
            const results = [];
            // Target elements containing "ID:"
            const cards = Array.from(document.querySelectorAll('div')).filter(el => el.innerText.includes('ID:'));

            cards.forEach(card => {
                const text = card.innerText;
                const nameEl = card.querySelector('.truncate, .font-bold');
                const idMatch = text.match(/ID:\s*(\d+)/);
                
                // Regex to find all numbers in the text
                const numbers = text.match(/\b\d+\b/g) || [];

                if (idMatch) {
                    results.push({
                        player_id: idMatch[1],
                        name: nameEl ? nameEl.innerText.trim() : "Unknown",
                        launched: parseInt(numbers[1]) || 0,
                        joined: parseInt(numbers[2]) || 0,
                        total: parseInt(numbers[3]) || 0,
                        score: parseInt(numbers[4]) || 0,
                        updated_at: new Date().toISOString()
                    });
                }
            });
            return results;
        });

        console.log(`Browser found ${players.length} players total.`);

        if (players.length > 0) {
            // --- DEDUPLICATION LOGIC ---
            // This creates a Map using player_id as the key. 
            // If the same ID appears twice, the newer one overwrites the old one.
            const uniquePlayers = Array.from(
                new Map(players.map(p => [p.player_id, p])).values()
            );
            
            console.log(`Filtered down to ${uniquePlayers.length} unique players.`);

            const { error } = await supabase
                .from('player_rankings')
                .upsert(uniquePlayers, { onConflict: 'player_id' });

            if (error) {
                console.error("Supabase Error:", error.message);
            } else {
                console.log("Success! Data pushed to Supabase.");
            }
        } else {
            console.log("No players found in the browser session.");
        }

    } catch (err) {
        console.error("Browser Error:", err.message);
    } finally {
        await browser.close();
    }
}

syncRallyRankings();
