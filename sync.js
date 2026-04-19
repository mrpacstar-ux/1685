// 1. FIX FOR NODE ENVIRONMENTS
if (typeof File === 'undefined') {
    global.File = class extends Blob {
        constructor(parts, filename, options = {}) {
            super(parts, options);
            this.name = filename;
            this.lastModified = options.lastModified || Date.now();
        }
    };
}

// 2. DEPENDENCIES (Only declared ONCE)
const axios = require('axios');
const cheerio = require('cheerio');
const { createClient } = require('@supabase/supabase-js');

// 3. CONFIGURATION
const supabase = createClient(process.env.SUPABASE_URL, process.env.SUPABASE_SERVICE_KEY);
const RALLY_URL = "https://www.statsmasterdatahub.com/1685/rallydata/c5eaf4fxkl3vykx";

// 4. THE SCRAPER FUNCTION
async function syncRallyRankings() {
    try {
        console.log("Fetching data from Statmaster...");
        const { data } = await axios.get(RALLY_URL, {
            headers: { 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36' }
        });
        
        const $ = cheerio.load(data);
        const players = [];

        // Targeting the cards based on the HTML snippet you provided
        $('.bg-gray-800\\/50').each((i, el) => {
            const name = $(el).find('.truncate').first().text().trim();
            const idRaw = $(el).find('.text-\\[10px\\]').text();
            const idMatch = idRaw.match(/ID:\s*(\d+)/);
            const id = idMatch ? idMatch[1] : null;
            
            const stats = $(el).find('.text-base.font-bold');
            
            if (name && id) {
                players.push({
                    player_id: id,
                    name: name,
                    launched: parseInt($(stats[0]).text()) || 0,
                    joined: parseInt($(stats[1]).text()) || 0,
                    total: parseInt($(stats[2]).text()) || 0,
                    score: parseInt($(stats[3]).text()) || 0,
                    updated_at: new Date()
                });
            }
        });

        console.log(`Successfully parsed ${players.length} players.`);

        if (players.length > 0) {
            const { error } = await supabase
                .from('player_rankings')
                .upsert(players, { onConflict: 'player_id' });

            if (error) throw error;
            console.log("Data successfully synced to Supabase!");
        } else {
            console.log("No players found. Check if the website layout changed.");
        }

    } catch (err) {
        console.error("Scraper Error:", err.message);
        process.exit(1);
    }
}

// 5. RUN IT
syncRallyRankings();
