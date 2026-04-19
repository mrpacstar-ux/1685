const { chromium } = require('playwright');
const { createClient } = require('@supabase/supabase-js');

const supabase = createClient(process.env.SUPABASE_URL, process.env.SUPABASE_SERVICE_KEY);
const RALLY_URL = "https://www.statsmasterdatahub.com/1685/rallydata/c5eaf4fxkl3vykx";

async function syncRallyRankings() {
    console.log("Launching browser to bypass protection...");
    const browser = await chromium.launch({ headless: true });
    const page = await browser.newPage();

    try {
        // Navigate and wait for the content to actually load
        await page.goto(RALLY_URL, { waitUntil: 'networkidle' });
        
        // Give it an extra 5 seconds in case of a Cloudflare "Wait" screen
        await page.waitForTimeout(5000);

        // Extract data directly from the browser context
        const players = await page.evaluate(() => {
            const results = [];
            // We look for elements containing "ID:"
            const cards = Array.from(document.querySelectorAll('div')).filter(el => el.innerText.includes('ID:'));

            cards.forEach(card => {
                // Try to find the name (usually a bold or large text near the top of the card)
                const nameEl = card.querySelector('.truncate, .font-bold');
                const text = card.innerText;
                const idMatch = text.match(/ID:\s*(\d+)/);
                
                // Find all standalone numbers (Stats)
                const numbers = text.match(/\b\d+\b/g) || [];

                if (nameEl && idMatch) {
                    results.push({
                        player_id: idMatch[1],
                        name: nameEl.innerText.trim(),
                        launched: parseInt(numbers[1]) || 0,
                        joined: parseInt(numbers[2]) || 0,
                        total: parseInt(numbers[3]) || 0,
                        score: parseInt(numbers[4]) || 0,
                        updated_at: new Date()
                    });
                }
            });
            return results;
        });

        console.log(`Browser found ${players.length} players.`);

        if (players.length > 0) {
            const { error } = await supabase
                .from('player_rankings')
                .upsert(players, { onConflict: 'player_id' });

            if (error) throw error;
            console.log("Success! Data pushed to Supabase.");
        }

    } catch (err) {
        console.error("Browser Error:", err.message);
    } finally {
        await browser.close();
    }
}

syncRallyRankings();
