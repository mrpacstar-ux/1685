const axios = require('axios');
const cheerio = require('cheerio');
const { createClient } = require('@supabase/supabase-js');

const supabase = createClient(process.env.SUPABASE_URL, process.env.SUPABASE_SERVICE_KEY);
const RALLY_URL = "https://www.statsmasterdatahub.com/1685/rallydata/c5eaf4fxkl3vykx";

async function syncRallyRankings() {
    try {
        console.log("Starting Deep Scan...");
        const { data } = await axios.get(RALLY_URL, {
            headers: { 
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept-Language': 'en-US,en;q=0.9'
            }
        });
        
        const $ = cheerio.load(data);
        const players = [];

        // STRATEGY: Instead of one class, we look for any element containing "ID:"
        // and then navigate to its parent container.
        $(":contains('ID:')").each((i, el) => {
            const container = $(el).closest('div.bg-gray-800\\/50, div.rounded-lg, tr');
            
            if (container.length) {
                const name = container.find('.truncate, .font-bold').first().text().trim();
                const idMatch = container.text().match(/ID:\s*(\d+)/);
                const id = idMatch ? idMatch[1] : null;
                
                // Collect all numbers found in the container
                const numbers = [];
                container.find('.text-base, td').each((j, numEl) => {
                    const val = $(numEl).text().trim();
                    if (/^\d+$/.test(val)) numbers.push(parseInt(val));
                });

                if (name && id && numbers.length >= 3) {
                    players.push({
                        player_id: id,
                        name: name,
                        launched: numbers[0] || 0,
                        joined: numbers[1] || 0,
                        total: numbers[2] || 0,
                        score: numbers[3] || (numbers[0] * 3 + numbers[1]) || 0,
                        updated_at: new Date()
                    });
                }
            }
        });

        console.log(`Deep Scan Results: Found ${players.length} players.`);

        if (players.length > 0) {
            // Remove duplicates from the array based on ID
            const uniquePlayers = Array.from(new Map(players.map(p => [p.player_id, p])).values());
            
            const { error } = await supabase
                .from('player_rankings')
                .upsert(uniquePlayers, { onConflict: 'player_id' });

            if (error) throw error;
            console.log(`Successfully synced ${uniquePlayers.length} unique players to Supabase.`);
        } else {
            // DEBUG: If still 0, print a snippet of the HTML to the log so we can see what's wrong
            console.log("HTML Preview:", data.substring(0, 500));
        }

    } catch (err) {
        console.error("Scraper Error:", err.message);
        process.exit(1);
    }
}

syncRallyRankings();
