// Supabase Edge Function: sync a user's Discord SERVER roles -> users.role
//
// Deploy:  supabase functions deploy discord-role-sync
// Secrets: supabase secrets set DISCORD_BOT_TOKEN=... DISCORD_GUILD_ID=... \
//          DISCORD_R5_ROLE_ID=... DISCORD_R4_ROLE_ID=... \
//          SUPABASE_URL=... SUPABASE_SERVICE_KEY=...
//
// Call it from the front end right after a successful Discord login:
//   await fetch(`${FUNCTIONS_URL}/discord-role-sync`, {
//     method: 'POST',
//     headers: { Authorization: `Bearer ${session.access_token}` },
//   });
//
// It reads the caller's discord_id from their users row, asks Discord which
// server roles they have, maps R5/R4 role IDs -> 'r5'/'r4', and updates the row.
// Members with neither officer role are left as 'member' (never demotes an R5
// that was set manually unless DEMOTE=1).

import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const {
  DISCORD_BOT_TOKEN, DISCORD_GUILD_ID,
  DISCORD_R5_ROLE_ID, DISCORD_R4_ROLE_ID,
  SUPABASE_URL, SUPABASE_SERVICE_KEY,
  DEMOTE, // "1" to allow auto-demotion when officer role is removed in Discord
} = Deno.env.toObject();

const admin = createClient(SUPABASE_URL, SUPABASE_SERVICE_KEY, {
  auth: { persistSession: false },
});

Deno.serve(async (req) => {
  try {
    // 1. Identify the caller from their JWT.
    const jwt = (req.headers.get("Authorization") || "").replace("Bearer ", "");
    if (!jwt) return json({ error: "no auth" }, 401);
    const { data: who, error: whoErr } = await admin.auth.getUser(jwt);
    if (whoErr || !who?.user) return json({ error: "bad token" }, 401);
    const authUid = who.user.id;

    // 2. Find their app user row + discord_id.
    const { data: urow } = await admin
      .from("users").select("id, discord_id, role").eq("auth_uid", authUid).single();
    const discordId = urow?.discord_id || who.user.user_metadata?.provider_id;
    if (!discordId) return json({ error: "no discord_id linked" }, 400);

    // 3. Ask Discord for this member's roles in your guild.
    const res = await fetch(
      `https://discord.com/api/v10/guilds/${DISCORD_GUILD_ID}/members/${discordId}`,
      { headers: { Authorization: `Bot ${DISCORD_BOT_TOKEN}` } },
    );
    if (!res.ok) return json({ error: `discord ${res.status}` }, 502);
    const member = await res.json();
    const roleIds: string[] = member.roles || [];

    // 4. Map server roles -> app role.
    let appRole: string | null = null;
    if (DISCORD_R5_ROLE_ID && roleIds.includes(DISCORD_R5_ROLE_ID)) appRole = "r5";
    else if (DISCORD_R4_ROLE_ID && roleIds.includes(DISCORD_R4_ROLE_ID)) appRole = "r4";
    else if (DEMOTE === "1") appRole = "member";

    if (!appRole) return json({ ok: true, role: urow?.role || "member", changed: false });

    // 5. Persist + audit.
    await admin.from("users")
      .update({ role: appRole, discord_name: member.user?.username, last_login: new Date().toISOString() })
      .eq("auth_uid", authUid);
    await admin.from("user_audit").insert({
      actor_id: urow?.id, action: "role_set", target_id: urow?.id,
      detail: { source: "discord", role: appRole, roleIds },
    });

    return json({ ok: true, role: appRole, changed: true });
  } catch (e) {
    return json({ error: String(e) }, 500);
  }
});

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status, headers: { "content-type": "application/json" },
  });
}
