# PROJECT_KNOWLEDGE.md — Apostado-Play Discord Bot

> **هذا الملف هو "ذاكرة المشروع".** اقرأه قبل أي تعديل.
> **الكود الفعلي هو المصدر الأساسي للحقيقة.** إذا لم يطابق هذا الملف الكود، صحّح هذا الملف.

Last updated: 2026-10-05 (Full Codebase Audit)

---

## 1. Project Overview

**What it is:** A Discord bot that manages competitive **Free Fire** matchmaking for Arabic-speaking gaming servers: players join private voice "waiting rooms", a host creates a lobby with a Free Fire room ID/password, other players join via buttons, a match starts, and after the match the group collectively votes on **MVP WINNER** and **MVP LOSER**. Points, rank, dynamic title roles, leaderboard, reports/bans, jail and blacklist systems follow from that.

**Language:** Python. **Style:** Arabic-first UI text (embedded Discord Embeds), English code comments.

**Stack:**
| Concern | Technology |
|---|---|
| Discord | `discord.py >= 2.0.0` (classic `commands.Bot`, **prefix commands only**) |
| Database | `sqlite3` (stdlib) — local file `freefire_bot.db`, WAL mode |
| Optional cloud backup | `pymongo >= 4.0.0` (MongoDB Atlas) via `cloud_backup.py` |
| DNS | `dnspython >= 2.0.0` (transitive/for Atlas SRV) |
| Deploy | Railway — NIXPACKS builder, `python main.py` |

**External APIs:** Discord Gateway/REST only. **No HTTP APIs, no webhooks, no aiohttp.**
**Slash commands / application commands:** NONE.
**Cogs:** NONE — single-module architecture.

---

## 2. Architecture

The project is deliberately small but one file is very large:

```
Apostado-Play/
├── main.py                  (27 lines)   ← ENTRY POINT (execs the big file)
├── freefire-bot-main.py     (8,507)     ← 100% of the application
├── cloud_backup.py          (~501)       ← optional MongoDB Atlas sync layer
├── requirements.txt         (3 lines)
├── railway.json             (NIXPACKS build/start config)
├── Procfile                 (empty)
└── freefire_bot.db          (runtime, never commit)
```

**Why `main.py` execs the other file:** the bot file is named `freefire-bot-main.py`, which is **not** a valid Python module name (hyphens). `main.py` reads it, `compile()`s it, and `exec()`s it so the whole thing runs as one namespace. Consequences to remember:
- `__file__` inside the exec'd code points at `freefire-bot-main.py` — used for the DB path.
- Line numbers in logs/tracebacks refer to `freefire-bot-main.py`.
- There is **no import boundary** between "bot file" and "entry point" — you cannot `import` the bot to unit-test it.

### Internal structure of `freefire-bot-main.py` (top → bottom)

| Region | Approx. lines | Contents |
|---|---|---|
| Module docstring + imports | 1–54 | incl. optional `cloud_backup` import guarded by `try/except` |
| Logging | 56–64 | `logging.basicConfig(level=INFO)`, logger name `freefire` |
| **CONFIG block** | 66–210 | all tunables: `PREFIX`, `BOT_OWNER_ID`, `GAME_MODES`, timeouts, `RANK_TITLES`, `COLORS`, `BUILD_ID` |
| Rank/role helpers | 212–430 | colors, titles, progress bars, `get_role_tier_for_rank` |
| **Role system (fixed)** | 410–660 | `create_role_if_not_exists`, `role_change_with_retry`, `sync_player_role`, `sync_all_players_roles`, `setup_rank_roles_permissions` |
| `notify_admins` + `sanitize_user_text` | 658–750 | admin alerting |
| **`class Database`** | ~800–1990 | every SQL statement lives here |
| Nickname / embed builders | 2002–2300 | `extract_original_nickname`, `build_nickname_with_level`, `create_lobby_embed`, `create_profile_embed`, `update_member_nickname`, `update_leaderboard_channel` |
| **Create-prompt lifecycle** | 2344–2441 | `delete_message_safely`, `auto_hide_create_prompt`, `_delete_create_prompt_for_lobby`, `cleanup_lobby_memory` |
| Channel lifecycle | 2448–2621 | `create_match_channels`, `delete_match_channels`, `move_to_banned_channels`, `check_and_apply_auto_ban` |
| **Vote trigger** | 2696–2791 | `auto_trigger_vote` |
| Lobby timeout | 2799–2831 | `auto_lobby_timeout` |
| Match results | 2838–3008 | `process_match_result` (auto-MVP path) |
| Modals | 3008–3204 | `RoomInfoModal`, `JoinKeyModal`, `ReportReasonModal`, `ReportPlayerSelectView` |
| Report button | 3207–3231 | `ReportButtonView` |
| **Lobby view** | 3234–3626 | `LobbyButtonsView` (join/leave/cancel/start) |
| **Start-vote view** | 3626–3818 | `StartVoteView` |
| `MvpSelectionView` (**DEAD**) | 3822–3983 | old host-only MVP picker |
| **Collective MVP voting** | 3989–4557 | `build_mvp_voters`, `_collect_admin_members`, `escalate_mvp_dispute`, `MvpVoteView` |
| **Points application** | 4563–4782 | `process_match_result_with_mvps` |
| `VoteView` (**DEAD**) | 4768–5065 | old team1/team2 vote |
| Lobby creation UI | 5068–5182 | `CreateLobbyView`, `LobbyCreateModal`, `RematchView` |
| **Bot object + events** | 5202–5820 | `bot = commands.Bot(...)`, checks, `on_command_error`, `on_ready`, `auto_setup_guild`, `on_member_join`, `on_voice_state_update` |
| `on_message` gate | 5791–5858 | channel allow-list + jail message deletion |
| **Commands** | 5925–8480 | 55 prefix commands (full list in §4) |
| Boot | 8500–8507 | `bot.run(os.getenv("DISCORD_TOKEN"))` |

---

## 3. Entry Points

**Local:** `python main.py`
**Railway:** `railway.json` → NIXPACKS, `buildCommand: pip install -r requirements.txt`, `startCommand: python main.py`.

`main.py` first calls `ensure_dependencies()` which imports `discord` and, only if that raises `ImportError`, runs `pip install -r requirements.txt`. On Railway `pip install` has already run, so this is a no-op safety net.

**Boot sequence inside the bot file:**
1. Config constants evaluated (incl. `BUILD_ID` from `RAILWAY_GIT_COMMIT_SHA`).
2. `db = Database()` at module level → opens/creates SQLite, WAL, `CREATE TABLE IF NOT EXISTS`, `_migrate()`.
3. Optional cloud restore (`auto_restore_database`) if `MONGODB_URI` is set.
4. All `@bot.command` decorators register commands; all `@discord.ui.button` classes are collected.
5. `bot.run(TOKEN)` at the bottom, guarded by `if __name__ == "__main__"`.
6. `on_ready` fires: registers 4 persistent views → `change_presence` → auto-detects channels in every guild → starts the 60 s periodic rank sync.

**`DISCORD_TOKEN` is mandatory.** There is no fallback literal; the bot raises `RuntimeError` at boot if it is absent.

---

## 4. Commands

55 command functions, prefix `!!`. **No name or alias collisions** (verified programmatically).

### Player commands
| Command | Aliases | Purpose |
|---|---|---|
| `!!play <mode>` | — | mode-aware entry; errors if no mode given |
| `!!play1v1` `!!play2v2` `!!play3v3` `!!play4v4` | — | thin wrappers → `create_mode_lobby` |
| `!!p` | — | alias command |
| `!!points` | `mypoints`, `pts` | player's own points card |
| `!!card [user]` | — | profile embed |
| `!!top` | — | leaderboard embed |
| `!!leave` | — | leave current lobby |
| `!!matches` | — | list active lobbies in guild |
| `!!mylevel` `!!myrank` | — | own rank |
| `!!fixrank` | — | recompute own rank |
| `!!matchinfo <id>` | — | lobby detail |
| `!!report [@user] [reason]` | — | file a report |
| `!!reports [user]` | — | list reports |
| `!!rules` | — | print the rules embed |
| `!!general` | — | general info |
| `!!help` | — | 2-page command list |
| `!!botinfo` | — | version, **build SHA**, live config |
| `!!cloudstatus` | — | MongoDB connection status |

### Moderation (admin)
`!!banplayer`/`ban`, `!!unbanplayer`/`unban`, `!!banned`, `!!report @user`,
`!!setreportchannel`/`setreportch`/`addreportch`, `!!removereportchannel`/`delreportch`/`rmreportch`,
`!!reportchannels`/`reportch`/`listreportch`,
`!!jail`/`sendtojail`/`cheater`, `!!unjail`/`release`/`free`,
`!!blacklist`/`bl`, `!!unblacklist`/`ubl`/`removebl`, `!!blacklisted`/`bllist`/`blacklistlist`.

### Match resolution (admin)
`!!startvote`/`forcevote`/`sv` (bypass 10-min cooldown) · `!!resolve <id> <team1|team2>` ·
`!!w <id> <@user>` (force MVP WINNER) · `!!l <id> <@user>` (force MVP LOSER).

### Setup / data (admin or owner)
`!!setup`, `!!autosetup`/`autoset`/`checksetup`, `!!cleanup`, `!!scan`, `!!deletecat`/`delcat`,
`!!confirmcat`, `!!fixrankall`/`forcerankall`, `!!setcommandschannel`, `!!setleaderboard`,
`!!resetstats`, `!!resetrankall`/`forceresetrankall`/`resetallranks`, `!!setlevel`, `!!setpoints`,
`!!syncnicknames`, `!!syncroles`/`syncranks`/`updateroles`.

### Owner-only
`!!cloudbackup` (`@commands.is_owner()`), `!!cloudrestore` (`@commands.is_owner()`).

### DM-only
`!!serverleave` — refuses to run in a guild, requires `BOT_OWNER_ID`.

### Guards
```python
is_admin_check              -> ctx.author.guild_permissions.administrator
is_bot_owner_check          -> id == BOT_OWNER_ID
is_bot_owner_or_admin_check -> either
is_high_role_member         -> BOT_OWNER_ID / Administrator / Manage Guild (used by !!play 1v1)
```
Additionally a **global** `blacklist_global_check` is wired as a bot-wide check for command access, plus `on_voice_state_update` enforcement for banned/jailed members.

---

## 5. Events

| Event | Line | Job |
|---|---|---|
| `on_ready` | 5309 | register 4 persistent views, presence, per-guild auto-detect, success messages, start periodic rank sync |
| `on_command_error` | 5274 | friendly cooldown / permission / blacklist replies; `CommandNotFound` is silently ignored; everything else is logged with traceback |
| `on_guild_join` | 5636 | logs membership |
| `on_member_join` | 5641 | creates the player row, sets `RANK n \| name` nickname |
| `on_voice_state_update` | 5663 | **3 enforcement blocks**: banned-player voice lock, jailed-player voice lock, blacklist leave/rejoin tracking |
| `on_message` | 5791 | jail chat restriction (deletes messages outside jail channels), command-channel allow-list, DM handling |

**No** `on_command`, `on_message_delete`, `on_raw_reaction_add`, `on_disconnect`, or `on_resumed`.
`tasks.loop` is **not** used — the only background loop is a hand-rolled `while True` inside `on_ready`.

---

## 6. Features

### 6.1 Lobby lifecycle
1. `!!play <mode>` → `create_mode_lobby()` validates: not banned → channel allowed → inside a waiting voice room → no other active lobby.
2. Posts a **"Create Lobby"** prompt with one button and starts a 60 s auto-delete timer (`CREATE_PROMPT_DELETE_AFTER`). Any older prompt from the same user is deleted first, so prompts never stack.
3. `LobbyCreateModal` collects Room ID / Password / Private Key, creates the lobby, **links the prompt to the lobby** (so it survives to match end instead of being deleted), and schedules `auto_lobby_timeout` (30 min).
4. `LobbyButtonsView` handles Join Team 1 / Join Team 2 / Leave / Cancel Game. Joining requires being in a waiting room and entering the private key when one exists.
5. On a full lobby → `StartVoteView` offers **🗳️ Start Vote** and **❌ Cancel Match**.
6. `StartVoteView` enforces a **10-minute cooldown** from match start (bypassable with `!!startvote`).
7. `auto_lobby_timeout` cancels a stale `waiting` lobby after 30 minutes.

### 6.2 Match channels
`create_match_channels()` creates a category `🎮 Match #id`, two team voice channels, and **one shared text channel** stored as *both* `team1_text_id` and `team2_text_id`. `_active_match_voice_channels` tracks the voice channels so `on_voice_state_update` can attribute leave/rejoin events to the blacklist system. `_original_voice_channels` remembers where each player came from, and `delete_match_channels()` moves everyone back before deleting.

### 6.3 Collective MVP voting (current system)
- **Voters:** `build_mvp_voters()` takes the **first 2 players of each team** = 4 voters. The lobby creator is always ordered first within team 1. For tiny modes it back-fills so the count never drops below 2.
- **Two selects + two buttons:** `🏆 MVP WINNER` select, `✦ MVP LOSER` select, `⚠️ تاغ الأدمن` button (`tag_admin_btn_{lobby_id}`), `📊 حالة التصويت` button (`mvp_status_btn_{lobby_id}`, ephemeral tally).
- **Consensus:** `MVP_CONSENSUS_NEEDED = 3` of 4 identical choices → applied automatically.
- **Escalation to an admin** (`escalate_mvp_dispute`) happens when: all voters have voted but no 3-way consensus (includes 2×2 deadlock), the consensus MVP WINNER and LOSER end up on the *same team*, or the 60 s view timeout expires. If an admin is present in a waiting room the bot moves them; otherwise it tags admins and hands over the exact `!!w` / `!!l` commands.
- Votes live in the in-memory dict `self.votes` and are **lost on restart** (see Known Limitations).

### 6.4 Points and rank
| Outcome | Points |
|---|---|
| Winner-team MVP | `+80` |
| Other winners | `+30` |
| Loser-team MVP | `+30` |
| Other losers | `-30` |

`WINNER_MVP_POINTS`, `LOSER_MVP_POINTS` and the team constants live in the config block. The **winning team is derived from the MVP WINNER's team**. `db.recalculate_ranks(gid)` recomputes every player's `level` by counting players above them (negative points get pushed past 1000 so they sort below everybody). Nicknames and title roles are re-synced afterwards.

### 6.5 Dynamic title roles
`RANK_TITLES` tiers: `#1 🏆 Best Player` · `#2–10 💎 Goated` · `#11–50 ⭐ Skilled` · `#51–100 🎯 Efficient`; above 100 no role.

The audit fixed the previously silent error handling here. `sync_player_role()` now:
- removes the old tier with `role_change_with_retry()` (3 attempts, exponential backoff `1.5s × 2ⁿ`) for rate limits / transient HTTP errors;
- treats `discord.Forbidden` and role-hierarchy errors as **permanent**, breaks out immediately and notifies admins;
- **anti-accumulation guard:** if the old role cannot be removed, the new one is **not** added, so a player can never accumulate several title roles;
- `setup_rank_roles_permissions()` grants soundboard / waiting-room permissions with `logger.warning()` on failure instead of `pass`.

### 6.6 Reports, bans, jail, blacklist
- `REPORT_THRESHOLD = 6` reports ⇒ auto-ban + move to an investigation voice + voice lock.
- Report reasons are sanitized by `sanitize_user_text()` (see Security).
- Jail: role `JAIL`, category `🔒 JAIL`, chats `・💬jail-chat` / `・💬jail-prouves`. `on_message` deletes jailed members' messages outside those chats; `on_voice_state_update` confines them to `🔒 Jail-<user_id>`.
- Blacklist: 180 s cumulative absence **or** 5 leave/rejoin cycles inside a match voice ⇒ 10-minute ban.

### 6.7 Rules channel
`ensure_rules_channel()` is idempotent: it looks for a channel named `RULES_CHANNEL_NAME = "🛡️・rules"`, creates it only if absent, and **never deletes a pre-existing one**. It is read-only with respect to `guild.default_role`. The rules body has a single source of truth, `build_rules_embed(guild_name)`, used by `!!setup`, `!!autosetup` and `!!rules`. All failures are logged with context; none are swallowed.

---

## 7. Database

SQLite file `freefire_bot.db` (override with `DB_PATH`). WAL, `synchronous=NORMAL`, `cache_size=10000`, `mmap_size=256MB`, `foreign_keys=ON`.

**Connection model:** one `sqlite3.connect(..., isolation_level=None)` per thread via `threading.local()`. `conn()` validates with `SELECT 1` and transparently reopens if the handle was closed — verified working (this is what makes the stray `c.close()` in `_migrate()` harmless).

**14 tables:**

| Table | Purpose | Key constraint |
|---|---|---|
| `players` | per-guild stats, points, level, streaks, original nickname | **none** (see Known Issues) |
| `lobbies` | room, status, both team rosters (JSON strings), private key, vote/startvote message ids | `id` PK |
| `match_channels` | category + 2 voice + 2 text ids per lobby | `id` PK |
| `player_reports` | reports | `UNIQUE(guild_id, reporter_id, reported_id)` |
| `banned_players` | bans + assigned investigation voice | `PRIMARY KEY (guild_id, user_id)` |
| `blacklist_log` | active blacklists | `UNIQUE(guild_id, user_id)` |
| `lobby_votes` | legacy team votes | `PRIMARY KEY (lobby_id, user_id)` |
| `vote_metadata` | creator / first joiner / vote message id | `lobby_id` PK |
| `match_results` | match history | `id` PK, `CHECK(winner_team IN ('team1','team2'))` |
| `guild_settings` | leaderboard channel + message id, report channel ids | `guild_id` PK |
| `play_channels` / `bot_commands_channels` / `waiting_rooms` | channel allow-lists | `UNIQUE(guild_id, channel_id)` |
| `allowed_guilds` | owner whitelist | `guild_id` PK |

**Lobby `status` lifecycle:** `waiting` → `started` → `voting` → `completed`; also `cancelled`.
`get_player_active_lobby()` treats `waiting`, `started` **and `voting`** as active — this is why a lobby stuck in `voting` locks its players out of new lobbies (fixed, see §14).

**Key queries:** `recalculate_ranks()` (rank by points with a tiebreak column, negative points pushed below `STARTING_LEVEL`), `get_top_points()`, `get_leaderboard()`, `update_match_player()`, `get_lobby_id_by_lobby_message()` / `_by_start_vote_message()` / `_by_message()` (recover a lobby id from a message id after a restart).

**Caching:** `Database._channels_cache` memoizes `get_commands_channels()` (`cmd_ch_<gid>`) and `get_play_channels()` (`play_ch_<gid>`). Both add/remove paths now invalidate their own key, and `auto_setup_guild()` flushes every key for the guild when it finishes.

**No explicit transactions** (`BEGIN` is never issued). Multi-row updates (a whole match's worth of points) are therefore not atomic — see Known Issues.

---

## 8. External Services

| Service | Used for | State |
|---|---|---|
| Discord Gateway + REST | everything | required |
| MongoDB Atlas | optional cloud backup/restore via `cloud_backup.py`, needs `MONGODB_URI` | optional; degrades gracefully |

`cloud_backup.py` exposes `_get_client`, `is_cloud_enabled`, `auto_restore_database`, `sync_guild_players_to_cloud`, `sync_player_to_cloud`, `sync_bans_to_cloud`, `sync_guild_settings_to_cloud`, `full_backup_to_cloud`, `full_restore_from_cloud`, `get_all_cloud_guilds`.

**Important:** `sync_player_to_cloud`, `sync_bans_to_cloud` and `sync_guild_settings_to_cloud` are imported but **never called**. Only the bulk `sync_guild_players_to_cloud` (from `recalculate_ranks`), `auto_restore_database`, and the owner-only backup/restore commands are wired. **Bans and guild settings are not backed up.**

---

## 9. Permissions

- Bot needs: `Manage Roles`, `Manage Nicknames`, `Move Members`, `Manage Channels`, `Manage Messages`, `Connect`/`Speak`, `Embed Links`, and `Administrator` is recommended for the auto-detect flow.
- `guild.default_role` is granted **no** access to match categories or the rules channel. The bot never mutates `default_role`'s permissions — it only reads it.
- Rank title roles are created with the bot's own colour and no special permissions beyond what `setup_rank_roles_permissions()` grants (soundboard, waiting-room access).
- Only the lobby **creator** can cancel a match (`LobbyButtonsView.cancel_game_btn`), unless the clicker has `administrator`.
- Only **admins** can vote-related arbitration (`!!resolve`, `!!w`, `!!l`, `!!startvote`).
- `notify_admins()` targets: the role literally named `ADMIN_ROLE_NAME = "Admin"`, every non-managed role with `administrator`/`manage_guild`, the top 3 positioned roles, and the guild owner — de-duplicated. It falls back to a `match-results` channel, then a play channel, then the first writable text channel.

---

## 10. Configuration

**Required environment variable:**

| Variable | Purpose |
|---|---|
| `DISCORD_TOKEN` | bot token. **No fallback literal** — the bot refuses to boot without it. |

**Optional:**

| Variable | Purpose |
|---|---|
| `MONGODB_URI` | enables the cloud backup layer |
| `DB_PATH` | overrides the SQLite file location |
| `RAILWAY_GIT_COMMIT_SHA` | set automatically by Railway; displayed as `🔨 Build` in `!!botinfo` |
| `BOT_BUILD_ID` | manual override for the build fingerprint |

**Hard-coded identifiers that must be edited per deployment:** `BOT_OWNER_ID = 1077949215772250143`, `ADMIN_ROLE_NAME = "Admin"`, `BLACKLIST_ROLE_NAME`, `JAIL_ROLE_NAME`, `JAIL_CATEGORY_NAME`, `RANK_TITLES[*].name`, `RULES_CHANNEL_NAME`, `WAITING_PRV_CATEGORY_HINT`, `BOT_LOGO_URL`, `SERVER_GIFS_BY_NAME`.

**No `.env` support:** `python-dotenv` is *not* in `requirements.txt`. Secrets must be real environment variables.

---

## 11. Important Dependencies

| Package | Role |
|---|---|
| `discord.py` | Gateway client, commands framework, UI (View/Button/Select/Modal) |
| `pymongo` | MongoDB Atlas driver for `cloud_backup.py` |
| `dnspython` | DNS SRV resolution needed by Atlas connection strings |

All three are declared with `>=` floors and no upper bounds, so a Railway rebuild can pick up a **breaking** new major version. This is a real deployment risk (see Known Issues).

---

## 12. Data Flow

**Match flow (happy path):**
```
!!play 4v4  ──► create_mode_lobby ──► "Create Lobby" prompt (+60s auto-delete timer)
      │ click 📋 ──► LobbyCreateModal ──► db.create_lobby / add_player_to_lobby
      │                                      └─► links prompt → lobby (survives to match end)
      ▼
others press "Join Team 1/2" ──► LobbyButtonsView._handle_join
      │  ├─ banned?          → ephemeral ban notice + move to investigation voice
      │  ├─ not in waiting?  → list available waiting rooms
      │  ├─ already in lobby?→ block (unless a started match lacks room info)
      │  └─ private key set? → JoinKeyModal ─► _complete_join
      ▼
lobby full ──► StartVoteView (🗳️ Start Vote) ──► 10-min cooldown check
      ▼
auto_trigger_vote ──► status='voting'
      ├─► build_mvp_voters ─► MvpVoteView (2 selects + 2 buttons) posted in the match text channel
      │        ├─ 3/4 consensus          ─► _apply ─► process_match_result_with_mvps
      │        ├─ 2×2 / same-team / all-voted-no-consensus ─► escalate_mvp_dispute
      │        └─ on_timeout (60 s)       ─► escalate_mvp_dispute
      └─► failure at any step ─► status reverted to 'started' + notify_admins   (audit fix)
      ▼
process_match_result_with_mvps
      ├─ db.update_lobby_status('completed')  ← done FIRST so the match always closes
      ├─ update_match_player per player (+80/+30/+30/-30)
      ├─ db.recalculate_ranks(guild_id)
      ├─ update_member_nickname + sync_player_role per player
      ├─ db.create_match_result
      ├─ post result embed → match text channel + match-results
      ├─ update_leaderboard_channel
      ├─ delete_match_channels (move everyone home, then delete)
      └─ cleanup_lobby_memory  →  also deletes the linked "Create Lobby" prompt
```

**Points → rank → roles:** `update_match_player` writes points/stats → `recalculate_ranks` rewrites every `level` in the guild → `update_member_nickname` sets `RANK n | name` → `sync_player_role` grants/removes the tier role.

**Admin alerting:** any unrecoverable failure calls `notify_admins()`, which pings the admin roles and drops a message in the match-results channel. It has **no** rate limiting and is called from many failure paths.

---

## 13. Known Limitations

1. **Votes do not survive a restart.** `MvpVoteView.votes` is in memory and the view is not persistent, so a redeploy during the 60 s window loses the vote and the lobby stays `voting` until an admin uses `!!w`/`!!l`/`!!resolve`.
2. **Timers do not survive a restart.** `lobby_timeout_timers`, `vote_timeout_timers`, `_create_prompt_timers` are all in-memory `asyncio` tasks. `LobbyButtonsView`/`StartVoteView` re-resolve their lobby id from the message id, which is why those still work.
3. **No cooldowns anywhere** — `@commands.cooldown` is used **zero** times. Any command (including `!!play`) can be spammed; only Discord's global rate limiter protects the bot.
4. **No host transfer.** If the lobby creator leaves, `lobbies.creator_id` still points at them; only they or an admin can cancel, and the lobby waits out its 30-minute timeout.
5. **`players` has no UNIQUE `(user_id, guild_id)` constraint.** Correctness relies entirely on `get_or_create_player()` checking first. Any concurrent/duplicate insert path would silently create duplicate rows and corrupt ranking.
6. **No transactions.** A crash midway through `process_match_result_with_mvps` leaves some players updated and others not (the `!!setpoints` hint in the admin alert is the manual remedy).
7. **SQLite on Railway is ephemeral.** The volume must be mounted or data is lost on redeploy. `MONGODB_URI` is the intended durable path.
8. **MATCH channel limit.** Each match creates a category + 3 channels; Discord's 500-channel guild cap is the real ceiling.
9. **Unbounded dependency versions** (`>=` with no ceiling) can break a build at any time.
10. **`VOTE_TIMEOUT_SECONDS = 60`** is very tight for a 4-player consensus that requires **two** dropdown selections each.

---

## 14. Known Issues

Status legend: **FIXED** in this audit · **OPEN** (needs a product decision) · **BY-DESIGN**.

### FIXED in the 2026-10-05 audit
| Sev | Issue | Fix |
|---|---|---|
| CRITICAL | `auto_trigger_vote` set status `voting` **before** verifying it could show the vote UI. Missing `match_channels` row or a deleted match text channel ⇒ early `return` with the lobby stuck in `voting` forever. Since `get_player_active_lobby()` counts `voting` as active, **every player in that lobby could never create a new lobby again.** | Revert to `started` + `notify_admins` on all three failure paths (no channels / missing text channel / send failure). The send is now wrapped in `try/except discord.HTTPException`. |
| HIGH | `on_ready` ran `asyncio.create_task(periodic_rank_sync())` unconditionally, and `on_ready` fires again on **every reconnect**. Each reconnect added another 60-second loop doing `recalculate_ranks` + `sync_all_players_roles` for every guild ⇒ N loops, N× the Discord API calls, rate-limit pressure. | Module-level `_periodic_rank_task`; the previous task is cancelled and awaited before a new one starts. Regression-tested (see §16). |
| HIGH | Role-hierarchy / Forbidden errors when granting or removing rank title roles were silently swallowed by bare `pass`. | `role_change_with_retry()` (3 attempts, exponential backoff), `discord.Forbidden` treated as permanent, surfaced via `notify_admins()`, plus the anti-accumulation guard (never add the new tier if the old one could not be removed). |
| MEDIUM | **Mention injection:** `!!report <user> <reason>` and `ReportReasonModal` stored raw user text, which was then interpolated into `notify_admins()` output **sent non-ephemerally**. A player could mass-ping (`<@&id>`, `@everyone`) and could also exceed the 1024-char Discord field limit and trigger `HTTPException 400`. | New `sanitize_user_text()` inserts a zero-width space after `@` in `<@id>` / `<@!id>` / `<@&id>` / `@everyone` / `@here`, collapses newlines and caps at 200 chars. Applied at both input sites, so `!!reports` is protected too (sanitised at rest). |
| MEDIUM | `CreateLobbyView` is registered as a persistent view with `ctx=None`. Pressing a leftover "Create Lobby" button after a restart hit `self.ctx.author.id` on `None` ⇒ unhandled `AttributeError`. | Explicit `if self.ctx is None` guard returning "run the command again". |
| MEDIUM | `Database.get_play_channels()` caches under `play_ch_<gid>`, but `add_play_channel()` / `remove_play_channel()` never invalidated it — stale channel lists until restart (affects `RematchView` target channel and `notify_admins` fallback). | Both methods now pop `play_ch_<gid>`. |
| MEDIUM | Every command touches `ctx.guild`, and **no** command guards `ctx.guild is None`, while `on_message` processed commands in DMs ⇒ `AttributeError` logged with no reply to the user. | DM branch now only forwards `!!serverleave` and otherwise explains that commands are guild-only. |

### OPEN — deliberately not changed (needs your decision)
| Sev | Issue | Why it was not changed |
|---|---|---|
| MEDIUM | **Host leaves the lobby ⇒ lobby unmanageable** (creator id is never reassigned; only an admin can cancel). | Auto-transferring the host changes game rules. Needs your call. |
| MEDIUM | **No cooldowns on any command.** `!!play`/`!!report` spam can hit rate limits. | Adding `@commands.cooldown` changes UX; pick the limits you want. |
| MEDIUM | **`players` has no UNIQUE `(user_id, guild_id)`** — duplicates would corrupt the leaderboard. | Needs a data migration; risky to do unattended. |
| MEDIUM | **No transactions** in `process_match_result_with_mvps`. | Wrapping in BEGIN/COMMIT changes failure semantics. |
| MEDIUM | **MongoDB backup is incomplete** — `sync_bans_to_cloud` and `sync_guild_settings_to_cloud` are imported but never called. | Wiring bans/settings to Atlas changes what is persisted. |
| LOW | `on_ready` re-runs the full auto-detect **and re-posts the "AUTO-DETECT Complete" message to every guild on every reconnect** (message spam). | Cosmetic, but changing it hides useful startup info. |
| LOW | **Dead code:** `VoteView` (old team vote) and `MvpSelectionView` (old host-only MVP picker). Both are unreachable — zero instantiations on any live path, and neither is registered as persistent — but `VoteView.on_timeout` instantiates `MvpSelectionView`. | Deleting ~350 lines is a clean-up with a small regression risk; not done unilaterally. |
| LOW | ~26 unused locals (`t1m`, `t2m`, `mode_info`, `banned`, `avatar_url`, `rank_title`) and ~44 f-strings with no placeholders. | Cosmetic. |
| LOW | `on_command_error` uses a bare `logger.exception` for unknown errors — users get no feedback. | Needs a decision on what to expose. |
| LOW | Result embeds label levels as `RANK #{old}→#{new}` although `old`/`new` are **levels**, not ranks. | Cosmetic wording. |
| LOW | Remaining bare `except: pass` sites: `update_leaderboard_channel`, `create_banned_voice_channels` / `move_to_banned_channels`, `_execute_cancel`, blacklist role removal, `MvpSelectionView`. | Same class of bug as the role fix, but each needs per-site review. |
| LOW | Unbounded dependency versions in `requirements.txt`. | Pinning may break the current deploy. |

### BY-DESIGN
- Rules channel is read-only for `@everyone` and is never deleted by the bot.
- The bot re-adds itself to the channel allow-lists on every start (auto-detect), so DB drift self-heals.
- `!!play` deliberately **errors** when no mode is given, to steer users to `!!play4v4`.

---

## 15. Important Design Decisions

1. **Single-file application with an `exec()` entry point.** The bot file has hyphens in its name, so it cannot be imported. `main.py` compiles and execs it. Preserved deliberately — splitting the file is the only real refactor that would pay off, and it is a large change.
2. **`db = Database()` at module level**, before `bot.run()`. The whole design assumes the DB is always available and synchronous.
3. **`get_player_active_lobby()` counts `voting` as active.** This is what makes "stuck in voting" a lockout rather than a cosmetic issue — the reason the CRITICAL fix above reverts state instead of just logging.
4. **The winner team is derived from MVP WINNER's team**, not voted separately. With 4 voters picking two MVPs, this is the simplest consistent rule.
5. **Consensus is 3 of 4, not unanimity.** Chosen so a single silent player cannot block a match, while still requiring genuine agreement.
6. **A same-team MVP WINNER + MVP LOSER pair is treated as impossible** and escalates instead of applying obviously-wrong points.
7. **Anti-accumulation guard on roles.** Refusing to add a new title role when the old one cannot be removed trades a missed cosmetic update for never showing a player several ranks at once.
8. **`build_rules_embed()` is the single source of truth** for rules text (previously duplicated in three places).
9. **`ensure_rules_channel()` never deletes.** It only ever creates when absent.
10. **`BUILD_ID` reads `RAILWAY_GIT_COMMIT_SHA`** so `!!botinfo` reveals which build is actually running — added because we could not tell whether a redeploy had picked up new commits.
11. **Legacy `lobby_votes` + `vote_metadata` tables are retained** even though the current system keeps votes in memory, so old rows are not lost and `!!resolve` still works.

---

## 16. Testing

**No test suite exists in the repo.** There is no CI, no linter config, and no test runner configured.

**Verification performed during the 2026-10-05 audit:**

| Check | Result |
|---|---|
| `ast.parse` on `freefire-bot-main.py` | OK |
| `pyflakes` — undefined names | **none** |
| `pyflakes` — unused imports / locals / placeholder-less f-strings | informational only |
| Schema build: extracted every `CREATE TABLE` into a temp SQLite DB | 14 tables created, columns confirmed |
| Command inventory + name/alias collision scan (AST) | 55 commands, **0 collisions** |
| Event / View / Button / Select / Modal inventory (AST) | 6 events, 9 views, 13 buttons, 5 selects, 4 modals |
| `eval` / `exec` / `pickle` / `os.system` / `subprocess` scan | none in the bot file |
| Hard-coded-secret scan (token/Mongo URI/API-key regexes) | none found |
| `conn()` self-heal after a stray `close()` | reproduced and verified working |
| `play_channels` cache consistency after add/remove | verified with a live SQLite harness |
| `periodic_rank_sync` duplicate-task regression test | old code leaked 3/3 loops; fixed code keeps exactly 1 |
| `sanitize_user_text` unit tests (6 injection vectors, length cap, whitespace, Arabic, email) | all pass |
| `auto_trigger_vote` structural test (1 transition in, ≥3 recoveries out, send wrapped in try) | all pass |
| `CreateLobbyView` null-ctx guard ordering | passes |

**NOT TESTED — Reason:** everything requiring a live Discord connection.

Specifically **NOT TESTED**: gateway login; any prefix command; any button/select/modal interaction; interaction lifecycle (defer/edit/ephemeral, expired tokens); voice state transitions and member moves; channel/role/category creation and deletion; rate-limit behaviour under load; nickname and role assignment against a real hierarchy; `notify_admins` delivery; SQLite behaviour on Railway's actual filesystem; MongoDB cloud sync; `!!botinfo` build fingerprint in production.

**Suggested first steps when you get a test token:** a `pytest` suite that imports `freefire-bot-main.py` via `importlib` (needed because of the hyphen) with `discord` mocked, plus one throwaway guild for manual interaction testing.

---

## 17. Change History

| Commit / Date | Change |
|---|---|
| `35472be` | Rank-role error handling (no more silent `pass`), retry with backoff, admin notification, anti-accumulation guard; **collective 4-voter MVP voting** replaced the old team vote; `!!help` updated |
| `a555d3b` | "Create Lobby" prompt auto-deletes after 60 s if no room was created, and is deleted when the match ends; rules channel restored and improved |
| `c585615` | Build fingerprint (`BUILD_ID` from `RAILWAY_GIT_COMMIT_SHA`) surfaced in `!!botinfo`; Arabic text fix |
| *audit, uncommitted at time of writing* | Fixed the CRITICAL `voting`-lockout in `auto_trigger_vote`; fixed the duplicate periodic-task leak on reconnect; added `sanitize_user_text()` to close the mention-injection hole; guarded `CreateLobbyView` against `ctx=None` after restart; fixed the `play_channels` cache invalidation; made DM command handling explicit. Created this document. |

### Deployment reminder
The bot on Railway only runs what was last deployed. After pushing, redeploy, then run `!!botinfo` and confirm **`🔨 Build`** shows the expected commit SHA — not `local-dev`. If it shows `local-dev`, the new code is not live.