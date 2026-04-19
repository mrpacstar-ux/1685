const axios = require('axios');
const cheerio = require('cheerio');
const { createClient } = require('@supabase/supabase-js');

const supabase = createClient('YOUR_SUPABASE_URL', 'YOUR_SUPABASE_SERVICE_KEY');
const RALLY_URL = "https://www.statsmasterdatahub.com/1685/rallydata/c5eaf4fxkl3vykx";

async function syncRallyRankings() {
    try {
        const { data } = await axios.get(RALLY_URL);
        const $ = cheerio.load(data);
        const players = [];

        // We target the mobile-view cards or the desktop rows. 
        // Based on your snippet, we'll grab the player cards:
        $('.bg-gray-800\\/50').each((i, el) => {
            const name = $(el).find('.truncate').text().trim();
            const id = $(el).find('.text-\\[10px\\]').text().replace('ID: ', '').trim();
            
            // Stats are in a grid of 4. We grab them by index.
            const stats = $(el).find('.text-base.font-bold');
            const launched = $(stats[0]).text().trim();
            const joined = $(stats[1]).text().trim();
            const total = $(stats[2]).text().trim();
            const score = $(stats[3]).text().trim();

            if (name) {
                players.push({
                    player_id: id,
                    name: name,
                    launched: parseInt(launched),
                    joined: parseInt(joined),
                    total: parseInt(total),
                    score: parseInt(score),
                    updated_at: new Date()
                });
            }
        });

        // Upsert into Supabase (updates existing IDs, inserts new ones)
        const { error } = await supabase
            .from('player_rankings')
            .upsert(players, { onConflict: 'player_id' });

        if (error) throw error;
        console.log(`Successfully synced ${players.length} players.`);

    } catch (err) {
        console.error("Scrape Error:", err.message);
    }
}

syncRallyRankings();
