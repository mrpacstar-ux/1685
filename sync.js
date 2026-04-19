// Fix for ReferenceError: File is not defined in older Node environments
if (typeof File === 'undefined') {
    global.File = class extends Blob {
        constructor(parts, filename, options = {}) {
            super(parts, options);
            this.name = filename;
            this.lastModified = options.lastModified || Date.now();
        }
    };
}

const axios = require('axios');
// ... rest of your code ...
const axios = require('axios');
const cheerio = require('cheerio');
const { createClient } = require('@supabase/supabase-js');

// Access Environment Variables
const supabase = createClient(process.env.SUPABASE_URL, process.env.SUPABASE_SERVICE_KEY);

const RALLY_URL = "https://www.statsmasterdatahub.com/1685/rallydata/c5eaf4fxkl3vykx";

async function syncRallyRankings() {
    try {
        console.log("Starting scrape of:", RALLY_URL);
        const { data } = await axios.get(RALLY_URL, {
            headers: { 'User-Agent': 'Mozilla/5.0' } // Helps bypass simple blocks
        });
        
        const $ = cheerio.load(data);
        const players = [];

        // Find the player cards - looking for the specific class from your snippet
        const cards = $('.bg-gray-800\\/50');
        console.log(`Found ${cards.length} player cards on page.`);

        if (cards.length === 0) {
            throw new Error("Could not find any player cards. The website layout might have changed.");
        }

        cards.each((i, el) => {
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

        console.log(`Parsed ${players.length} players successfully.`);

        if (players.length > 0) {
            const { error } = await supabase
                .from('player_rankings')
                .upsert(players, { onConflict: 'player_id' });

            if (error) throw error;
            console.log("Database upload successful!");
        }

    } catch (err) {
        console.error("CRASH ERROR:");
        console.error(err.message);
        process.exit(1); // Tells GitHub that the job failed
    }
}

syncRallyRankings();
