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

        console.log("Selecting 'This Week'...");
        const weekButton = page.getByText(/This Week/i).last();
        await weekButton.click();
        
        // Wait for the data to actually appear in the UI
        console.log("Waiting for data load...");
        await page.waitForSelector('text=ID:', { timeout: 20000 });
        
        // Scroll slowly to trigger lazy loading
        await page.evaluate(async () => {
            for (let i = 0; i < 5; i++) {
                window.scrollBy(0, 1000);
                await new Promise(r => setTimeout(r, 500));
            }
        });

        const players = await page.evaluate(() => {
            const results = [];
            // Find every element that contains "ID:"
            const idElements = Array.from(document.querySelectorAll('*')).filter(el => 
                el.children.length === 0 && el.innerText.includes('ID:')
            );

            idElements.forEach(idEl => {
                // Find the container that holds this player's data (the row/card)
                const container = idEl.closest('div[class*="row"], div[class*="item"], tr') || idEl.parentElement.parentElement;
                
                if (container) {
                    const text = container.innerText;
                    const lines = text.split('\n').map(s => s.trim()).filter(s => s.length > 0);
                    
                    // Statmaster structure usually: [Rank], [Name], [ID: 123], [Stat1], [Stat2]...
                    const idMatch = text.match(/ID:\s*(\d+)/);
                    
                    if (idMatch) {
                        // Find all standalone numbers in the container
                        const numbers = text.match(/\b\d+[\d,]*\b/g) || [];
                        // Filter out the ID from our numbers list
                        const stats = numbers.filter(n => n !== idMatch[1] && n.length < 8);

                        results.push({
                            player_id: idMatch[1],
                            // Name is usually the line before the ID or the first non-numeric line
                            name: lines.find(l => !l.includes('ID:') && isNaN(l.replace(/,/g,''))) || "Unknown",
                            launched: parseInt(stats[0]?.replace(/,/g,'')) || 0,
                            joined: parseInt(stats[1]?.replace(/,/g,'')) || 0,
                            total: parseInt(stats[2]?.replace(/,/g,'')) || 0,
                            score: parseInt(stats[3]?.replace(/,/g,'')) || 0,
                            updated_at: new Date().toISOString()
                        });
                    }
                }
            });
            return results;
        });

        console.log(`Scraper identified ${players.length} player entries.`);

        if (players.length > 0) {
            // Deduplicate
            const uniquePlayers = Array.from(new Map(players.map(p => [p.player_id, p])).values());
            console.log(`Syncing ${uniquePlayers.length} unique players...`);

            const { error } = await supabase
                .from('player_rankings')
                .upsert(uniquePlayers, { onConflict: 'player_id' });

            if (error) throw error;
            console.log("Success! Database updated.");
        } else {
            console.log("Failed to extract data. The page structure is likely protected or non-standard.");
        }

    } catch (err) {
        console.error("Scraper Error:", err.message);
    } finally {
        await browser.close();
    }
}

syncRallyRankings();
