# Apostado Play Bot — Documentation

Free Fire matchmaking Discord bot (discord.py 2.x, SQLite + optional MongoDB cloud backup). Prefix: `!!`.

## 1. Features
- Lobbies for 1v1 / 2v2 / 3v3 / 4v4 with team voice/text channels, host, join keys (Room ID / Password / Private Key).
- MVP voting (2v2-4v4) and winning-team voting (1v1); admin fallback (`!!w`, `!!l`, `!!resolve`, `!!startvote`).
- Points, rank positions, rank-title roles (Best Player / Goated / Skilled / Efficient), nicknames, Leaderboard channel.
- Reports with auto-ban (6 reports), investigation voices, JAIL system, Blacklist system.
- Auto-detection of channels (`!!autosetup`), rules channel, results channel.
- Cloud sync (MongoDB) for players, bans, blacklist, reports, settings.

## 2. Commands (55)
**Play (8):** `play [mode]`, `play1v1` (high roles only), `play2v2`, `play3v3`, `play4v4`, `p` (profile), `leave`, `matches`
**Stats (7):** `points` (`mypoints`, `pts`), `card`, `top`, `mylevel`, `myrank`, `fixrank`, `matchinfo <id>`
**Info (5):** `rules`, `general`, `help`, `botinfo`, `cloudstatus`
**Setup (admin, 8):** `setup`, `autosetup` (`autoset`, `checksetup`), `cleanup`, `scan [page]`, `deletecat <name>` (`delcat`), `confirmcat <name>`, `setcommandschannel [#ch]`, `setleaderboard`
**Ranks/Roles (admin, 8):** `fixrankall`, `syncnicknames`, `syncroles`, `setlevel`, `setpoints`, `resetstats`, `resetrankall`, `resolve <id> <team1|team2>`
**Match control (admin, 4):** `w <id> <@user>` (MVP winner), `l <id> <@user>` (MVP loser), `startvote [id]`, `resolve`
**Reports & bans (7):** `report`, `reports`, `banplayer` (`ban`), `unbanplayer` (`unban`), `banned`, `setreportchannel`, `removereportchannel`, `reportchannels`
**JAIL (2):** `jail @user|ID [reason]` (`sendtojail`, `cheater`), `unjail` (`release`, `free`)
**Blacklist (3):** `blacklist` (`bl`), `unblacklist` (`ubl`, `removebl`), `blacklisted` (`bllist`)
**Owner (3):** `cloudbackup`, `cloudrestore`, `serverleave` (DM only)

## 3. Database (SQLite, 14 tables)
`guild_settings`, `play_channels`, `bot_commands_channels`, `waiting_rooms`, `allowed_guilds`, `players` (points, wins, losses, mvps, matches_played, matches_hosted, level, streaks…), `lobbies`, `match_channels`, `lobby_votes`, `vote_metadata`, `match_results`, `player_reports`, `banned_players`, `blacklist_log`.
`matches_hosted` is incremented exactly once per `create_lobby`.

## 4. JAIL system
`setup_jail_system(guild)` creates the `JAIL` role, the `🔒 JAIL` category and the text channels `・💬jail-chat` and `・💬jail-prouves`; jailed players lose view access everywhere else. The in-memory cache is valid only if the role, category and both channels still exist. Failures are logged (no silent excepts) and channel creation is skipped if the category cannot be created.

## 5. Blacklist system
Players who leave match voices too often are blacklisted for 5 minutes (`BLACKLIST_DURATION`). Cumulative absence limit 300 s, max 8 leaves, warnings at 50 % and 80 %, leaves shorter than 10 s are ignored, tracking uses `time.time()`, and resets after 60 s of staying in the match. Blacklisted players get the `🔇 Blacklisted` role, cannot use bot commands, and are listed in the blacklist channel.

## 6. Cloud sync (`cloud_backup.py`)
Enabled only when `MONGODB_URI` is set. Functions: `sync_player_to_cloud`, `sync_guild_players_to_cloud`, `restore_players_from_cloud`, `sync_guild_settings_to_cloud`, `restore_guild_settings_from_cloud`, `sync_channels_to_cloud`, `restore_channels_from_cloud`, `sync_bans_to_cloud`, `restore_bans_from_cloud`, `sync_blacklist_to_cloud`, `restore_blacklist_from_cloud`, `sync_reports_to_cloud`, `restore_reports_from_cloud`, `auto_restore_database`, `full_backup_to_cloud`, `full_restore_from_cloud`.

## 7. Bot permissions and intents
Permissions: View Channels, Send Messages, Embed Links, Attach Files, Read Message History, Add Reactions, Manage Messages, **Manage Channels**, **Manage Roles**, Manage Nicknames, Move Members, Connect. The bot role must sit **above** the rank/JAIL/Blacklist roles.
Privileged intents (enable in the Developer Portal): Server Members, Message Content. Also uses Voice States, Reactions, DM messages.

## 8. Environment variables
| Variable | Required | Purpose |
|---|---|---|
| `DISCORD_TOKEN` | yes | Bot token (never hard-code it) |
| `MONGODB_URI` | no | Enables cloud backup/sync |
| `DB_PATH` | no | SQLite file location (use a persistent volume) |
| `PORT` | no | Health-check server port (Railway/Render) |
| `BOT_BUILD_ID` / `RAILWAY_GIT_COMMIT_SHA` | no | Build id shown in `!!botinfo` |

## 9. Deployment
`Procfile`: `web: python main.py`; `railway.json` uses NIXPACKS and `python main.py`. `main.py` installs requirements if needed and runs `freefire-bot-main.py`.
