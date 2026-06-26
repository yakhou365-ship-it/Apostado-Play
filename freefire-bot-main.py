"""
===========================================================
  🔥 Free Fire Matchmaking Bot — v6.0 ULTIMATE
===========================================================
  🤖 تصميم Embeds مخفي بالكامل (Invisible #2B2D31)
  🔘 أزرار احترافية مع الإيموجيات وتنسيق الألوان
  📜 جميع الأوامر (إدارة + لاعبين) بتصميم موحد ونظيف
===========================================================
"""

import discord
from discord.ext import commands
import sqlite3
import json
import os
import asyncio
import logging
import re
from datetime import datetime

# ============================================================
# LOGGING & CONFIG
# ============================================================
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
logger = logging.getLogger("freefire")

PREFIX = "!!"
BOT_OWNER_ID = 1077949215772250143
STARTING_LEVEL = 1000
NICKNAME_MAX_LENGTH = 32

GAME_MODES = {
    "1v1": {"team_size": 1, "lobby_size": 2},
    "2v2": {"team_size": 2, "lobby_size": 4},
    "3v3": {"team_size": 3, "lobby_size": 6},
    "4v4": {"team_size": 4, "lobby_size": 8},
}
DEFAULT_MODE = "4v4"

MATCH_POINTS_BY_MODE = {
    "1v1": {"win": 20, "lose": 5},
    "2v2": {"win": 30, "lose": 10},
    "3v3": {"win": 40, "lose": 12},
    "4v4": {"win": 50, "lose": 15},
}
STREAK_BONUS = {3: 10, 5: 25, 10: 50}
VOTE_TIMEOUT_SECONDS = 120
LOBBY_TIMEOUT_SECONDS = 1800

COLORS = {
    "invisible": 0x2B2D31, # لون الـ Dark Mode الفاخر
    "success":   0x57F287, 
    "error":     0xED4245, 
    "warning":   0xFEE75C, 
}

def get_rank_title(level):
    if level >= 5000: return "أسطورة"
    if level >= 3000: return "نخبة"
    if level >= 2000: return "خبير"
    if level >= 1500: return "محترف"
    return "مبتدئ"

def get_rank_emoji(level):
    if level >= 5000: return "👑"
    if level >= 3000: return "💎"
    if level >= 2000: return "🔥"
    if level >= 1500: return "⭐"
    return "🎯"

# ============================================================
# DATABASE
# ============================================================
class Database:
    def __init__(self, db_path="freefire_bot.db"):
        self.db_path = db_path
        self._create_tables()
        self._migrate()

    def conn(self):
        c = sqlite3.connect(self.db_path, timeout=30.0)
        c.row_factory = sqlite3.Row
        c.execute("PRAGMA foreign_keys = ON")
        c.execute("PRAGMA journal_mode=WAL")
        return c

    def _create_tables(self):
        c = self.conn()
        try:
            c.executescript("""
                CREATE TABLE IF NOT EXISTS guild_settings (guild_id INTEGER PRIMARY KEY, form_channel_id INTEGER DEFAULT NULL, announcement_role_id INTEGER DEFAULT NULL, leaderboard_channel_id INTEGER DEFAULT NULL, leaderboard_message_id INTEGER DEFAULT NULL, auto_channel_category_id INTEGER DEFAULT NULL);
                CREATE TABLE IF NOT EXISTS play_channels (id INTEGER PRIMARY KEY AUTOINCREMENT, guild_id INTEGER NOT NULL, channel_id INTEGER NOT NULL, UNIQUE(guild_id, channel_id));
                CREATE TABLE IF NOT EXISTS bot_commands_channels (id INTEGER PRIMARY KEY AUTOINCREMENT, guild_id INTEGER NOT NULL, channel_id INTEGER NOT NULL, UNIQUE(guild_id, channel_id));
                CREATE TABLE IF NOT EXISTS waiting_rooms (id INTEGER PRIMARY KEY AUTOINCREMENT, guild_id INTEGER NOT NULL, channel_id INTEGER NOT NULL, UNIQUE(guild_id, channel_id));
                CREATE TABLE IF NOT EXISTS players (user_id INTEGER, guild_id INTEGER NOT NULL, username TEXT NOT NULL, points INTEGER DEFAULT 0, rank_pos INTEGER DEFAULT 1, wins INTEGER DEFAULT 0, losses INTEGER DEFAULT 0, kills INTEGER DEFAULT 0, mvps INTEGER DEFAULT 0, matches_played INTEGER DEFAULT 0, level INTEGER DEFAULT 100, win_streak INTEGER DEFAULT 0, lose_streak INTEGER DEFAULT 0, max_win_streak INTEGER DEFAULT 0, original_nickname TEXT DEFAULT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY (user_id, guild_id));
                CREATE TABLE IF NOT EXISTS lobbies (id INTEGER PRIMARY KEY AUTOINCREMENT, guild_id INTEGER NOT NULL, creator_id INTEGER NOT NULL, game_mode TEXT DEFAULT '4v4', status TEXT DEFAULT 'waiting' CHECK(status IN ('waiting','started','voting','completed','cancelled')), team1_players TEXT DEFAULT '[]', team2_players TEXT DEFAULT '[]', first_joiner_id INTEGER DEFAULT NULL, room_id TEXT DEFAULT NULL, room_code TEXT DEFAULT NULL, private_key TEXT DEFAULT NULL, vote_message_id INTEGER DEFAULT NULL, message_id INTEGER DEFAULT NULL, channel_id INTEGER DEFAULT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, started_at TIMESTAMP DEFAULT NULL, completed_at TIMESTAMP DEFAULT NULL);
                CREATE TABLE IF NOT EXISTS match_channels (id INTEGER PRIMARY KEY AUTOINCREMENT, lobby_id INTEGER NOT NULL, guild_id INTEGER NOT NULL, category_id INTEGER DEFAULT NULL, team1_voice_id INTEGER DEFAULT NULL, team1_text_id INTEGER DEFAULT NULL, team2_voice_id INTEGER DEFAULT NULL, team2_text_id INTEGER DEFAULT NULL);
                CREATE TABLE IF NOT EXISTS lobby_votes (lobby_id INTEGER NOT NULL, user_id INTEGER NOT NULL, vote TEXT NOT NULL CHECK(vote IN ('team1','team2')), voted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY (lobby_id, user_id));
                CREATE TABLE IF NOT EXISTS vote_metadata (lobby_id INTEGER PRIMARY KEY, creator_id INTEGER NOT NULL, first_joiner_id INTEGER, message_id INTEGER);
                CREATE TABLE IF NOT EXISTS match_results (id INTEGER PRIMARY KEY AUTOINCREMENT, lobby_id INTEGER NOT NULL, winner_team TEXT NOT NULL CHECK(winner_team IN ('team1','team2')), team1_score INTEGER DEFAULT 0, team2_score INTEGER DEFAULT 0, mvp_id INTEGER DEFAULT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
            """)
            c.commit()
        finally: c.close()

    def _migrate(self):
        c = self.conn()
        try:
            for table, col, col_type in [("players", "win_streak", "INTEGER DEFAULT 0"), ("players", "lose_streak", "INTEGER DEFAULT 0"), ("players", "max_win_streak", "INTEGER DEFAULT 0"), ("players", "original_nickname", "TEXT DEFAULT NULL"), ("lobbies", "private_key", "TEXT DEFAULT NULL"), ("lobbies", "first_joiner_id", "INTEGER DEFAULT NULL")]:
                try: c.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_type}")
                except: pass
            c.commit()
        finally: c.close()

    # (Basic Getters/Setters...)
    def get_guild_settings(self, gid):
        c = self.conn(); r = c.execute("SELECT * FROM guild_settings WHERE guild_id=?", (gid,)).fetchone(); c.close(); return dict(r) if r else None
    def set_guild_setting(self, gid, key, val):
        c = self.conn(); c.execute("INSERT OR IGNORE INTO guild_settings(guild_id) VALUES(?)", (gid,)); c.execute(f"UPDATE guild_settings SET {key}=? WHERE guild_id=?", (val, gid)); c.commit(); c.close()
    def add_play_channel(self, gid, cid):
        c = self.conn()
        try: c.execute("INSERT INTO play_channels(guild_id,channel_id) VALUES(?,?)", (gid, cid)); c.commit(); return True
        except: return False
        finally: c.close()
    def get_play_channels(self, gid):
        c = self.conn(); res = [x["channel_id"] for x in c.execute("SELECT channel_id FROM play_channels WHERE guild_id=?", (gid,)).fetchall()]; c.close(); return res
    def add_commands_channel(self, gid, cid):
        c = self.conn()
        try: c.execute("INSERT INTO bot_commands_channels(guild_id,channel_id) VALUES(?,?)", (gid, cid)); c.commit(); return True
        except: return False
        finally: c.close()
    def remove_commands_channel(self, gid, cid):
        c = self.conn(); cur = c.execute("DELETE FROM bot_commands_channels WHERE guild_id=? AND channel_id=?", (gid, cid)); c.commit(); c.close(); return cur.rowcount > 0
    def get_commands_channels(self, gid):
        c = self.conn(); res = [x["channel_id"] for x in c.execute("SELECT channel_id FROM bot_commands_channels WHERE guild_id=?", (gid,)).fetchall()]; c.close(); return res
    def is_bot_allowed_channel(self, gid, cid):
        if cid in self.get_commands_channels(gid): return True
        c = self.conn(); res = c.execute("SELECT 1 FROM match_channels WHERE guild_id=? AND (team1_text_id=? OR team2_text_id=?) LIMIT 1", (gid, cid, cid)).fetchone() is not None; c.close(); return res
    def add_waiting_room(self, gid, cid):
        c = self.conn()
        try: c.execute("INSERT INTO waiting_rooms(guild_id,channel_id) VALUES(?,?)", (gid, cid)); c.commit(); return True
        except: return False
        finally: c.close()
    def get_waiting_rooms(self, gid):
        c = self.conn(); res = [x["channel_id"] for x in c.execute("SELECT channel_id FROM waiting_rooms WHERE guild_id=?", (gid,)).fetchall()]; c.close(); return res
    def get_available_waiting_room(self, gid, guild=None):
        rooms = self.get_waiting_rooms(gid)
        if not rooms: return None
        if guild:
            for cid in rooms:
                if guild.get_channel(cid): return cid
        return rooms[0]
    
    # (Players Logic...)
    def get_or_create_player(self, uid, gid, name):
        c = self.conn(); r = c.execute("SELECT * FROM players WHERE user_id=? AND guild_id=?", (uid, gid)).fetchone()
        if r: c.execute("UPDATE players SET last_active=?, username=? WHERE user_id=? AND guild_id=?", (datetime.now().isoformat(), name, uid, gid))
        else: c.execute("INSERT INTO players(user_id,guild_id,username,level) VALUES(?,?,?,?)", (uid, gid, name, STARTING_LEVEL))
        c.commit(); res = dict(c.execute("SELECT * FROM players WHERE user_id=? AND guild_id=?", (uid, gid)).fetchone()); c.close(); return res
    def get_player(self, uid, gid):
        c = self.conn(); r = c.execute("SELECT * FROM players WHERE user_id=? AND guild_id=?", (uid, gid)).fetchone(); c.close(); return dict(r) if r else None
    def update_player_stats(self, uid, gid, **kw):
        safe = {k: v for k, v in kw.items() if k in {"points","rank_pos","wins","losses","kills","mvps","matches_played","level","username","original_nickname","win_streak","lose_streak","max_win_streak"}}
        if not safe: return
        sets = ", ".join([f"{k}=?" for k in safe]); vals = list(safe.values()) + [datetime.now().isoformat(), uid, gid]
        c = self.conn(); c.execute(f"UPDATE players SET {sets}, last_active=? WHERE user_id=? AND guild_id=?", vals); c.commit(); c.close()
    def update_player_level(self, uid, gid, delta):
        c = self.conn(); c.execute("UPDATE players SET level=MAX(1,MIN(9999,level+?)), last_active=? WHERE user_id=? AND guild_id=?", (delta, datetime.now().isoformat(), uid, gid)); c.commit()
        r = c.execute("SELECT level FROM players WHERE user_id=? AND guild_id=?", (uid, gid)).fetchone(); c.close(); return dict(r)["level"] if r else STARTING_LEVEL
    def reset_stats(self, uid, gid):
        c = self.conn(); c.execute("UPDATE players SET points=0,wins=0,losses=0,kills=0,mvps=0,matches_played=0,rank_pos=1,level=?,win_streak=0,lose_streak=0,max_win_streak=0,last_active=? WHERE user_id=? AND guild_id=?", (STARTING_LEVEL, datetime.now().isoformat(), uid, gid)); c.commit(); c.close()
    def get_leaderboard(self, gid, limit=10):
        c = self.conn(); res = [dict(x) for x in c.execute("SELECT * FROM players WHERE guild_id=? ORDER BY points DESC LIMIT ?", (gid, limit)).fetchall()]; c.close(); return res

    # (Lobbies Logic...)
    def create_lobby(self, gid, creator, chan, mode="4v4"):
        c = self.conn(); cur = c.execute("INSERT INTO lobbies(guild_id,creator_id,channel_id,game_mode,team1_players) VALUES(?,?,?,?,?)", (gid, creator, chan, mode, json.dumps([creator]))); c.commit(); lid = cur.lastrowid; c.close(); return lid
    def get_lobby(self, lid):
        c = self.conn(); r = c.execute("SELECT * FROM lobbies WHERE id=?", (lid,)).fetchone(); c.close()
        if r:
            l = dict(r); l["team1_players"] = json.loads(l["team1_players"]); l["team2_players"] = json.loads(l["team2_players"]); return l
        return None
    def get_active_lobbies(self, gid):
        c = self.conn(); res = []
        for r in c.execute("SELECT * FROM lobbies WHERE guild_id=? AND status IN ('waiting','started','voting') ORDER BY created_at DESC", (gid,)).fetchall():
            l = dict(r); l["team1_players"] = json.loads(l["team1_players"]); l["team2_players"] = json.loads(l["team2_players"]); res.append(l)
        c.close(); return res
    def get_player_active_lobby(self, uid, gid):
        c = self.conn()
        for r in c.execute("SELECT * FROM lobbies WHERE guild_id=? AND status IN ('waiting','started','voting')", (gid,)).fetchall():
            l = dict(r); t1, t2 = json.loads(l["team1_players"]), json.loads(l["team2_players"])
            if uid in t1 or uid in t2:
                l["team1_players"], l["team2_players"] = t1, t2; c.close(); return l
        c.close(); return None
    def add_player_to_lobby(self, lid, uid, team):
        c = self.conn(); r = c.execute("SELECT * FROM lobbies WHERE id=?", (lid,)).fetchone()
        if not r: c.close(); return False
        l = dict(r); t1, t2 = json.loads(l["team1_players"]), json.loads(l["team2_players"])
        mode = l.get("game_mode", DEFAULT_MODE); ts = GAME_MODES.get(mode, GAME_MODES[DEFAULT_MODE])["team_size"]
        if team == "team1" and len(t1) < ts and uid not in t1: t1.append(uid)
        elif team == "team2" and len(t2) < ts and uid not in t2: t2.append(uid)
        else: c.close(); return False
        c.execute("UPDATE lobbies SET team1_players=?, team2_players=? WHERE id=?", (json.dumps(t1), json.dumps(t2), lid)); c.commit(); c.close(); return True
    def remove_player_from_lobby(self, lid, uid):
        c = self.conn(); r = c.execute("SELECT * FROM lobbies WHERE id=?", (lid,)).fetchone()
        if not r: c.close(); return False
        l = dict(r); t1, t2 = json.loads(l["team1_players"]), json.loads(l["team2_players"]); removed = False
        if uid in t1: t1.remove(uid); removed = True
        if uid in t2: t2.remove(uid); removed = True
        if removed: c.execute("UPDATE lobbies SET team1_players=?, team2_players=? WHERE id=?", (json.dumps(t1), json.dumps(t2), lid)); c.commit()
        c.close(); return removed
    def update_lobby_status(self, lid, status):
        c = self.conn()
        if status in ("started", "completed", "cancelled"):
            col = "started_at" if status == "started" else "completed_at"
            c.execute(f"UPDATE lobbies SET status=?, {col}=? WHERE id=?", (status, datetime.now().isoformat(), lid))
        else: c.execute("UPDATE lobbies SET status=? WHERE id=?", (status, lid))
        c.commit(); c.close()
    def update_lobby_message(self, lid, mid): c = self.conn(); c.execute("UPDATE lobbies SET message_id=? WHERE id=?", (mid, lid)); c.commit(); c.close()
    def set_first_joiner(self, lid, uid): c = self.conn(); c.execute("UPDATE lobbies SET first_joiner_id=? WHERE id=? AND first_joiner_id IS NULL", (uid, lid)); c.commit(); c.close()
    def set_room_info(self, lid, room_id, room_code, private_key=None): c = self.conn(); c.execute("UPDATE lobbies SET room_id=?, room_code=?, private_key=? WHERE id=?", (room_id, room_code, private_key, lid)); c.commit(); c.close()
    def get_lobby_private_key(self, lid): c = self.conn(); r = c.execute("SELECT private_key FROM lobbies WHERE id=?", (lid,)).fetchone(); c.close(); return r["private_key"] if r else None
    def reassign_creator(self, lid, new_creator_id): c = self.conn(); c.execute("UPDATE lobbies SET creator_id=? WHERE id=?", (new_creator_id, lid)); c.commit(); c.close()

    # (Match Channels & Votes...)
    def save_match_channels(self, lid, gid, cat_id, t1v, t1t, t2v, t2t): c = self.conn(); c.execute("INSERT INTO match_channels(lobby_id,guild_id,category_id,team1_voice_id,team1_text_id,team2_voice_id,team2_text_id) VALUES(?,?,?,?,?,?,?)", (lid, gid, cat_id, t1v, t1t, t2v, t2t)); c.commit(); c.close()
    def get_match_channels(self, lid): c = self.conn(); r = c.execute("SELECT * FROM match_channels WHERE lobby_id=?", (lid,)).fetchone(); c.close(); return dict(r) if r else None
    def delete_match_channels_record(self, lid): c = self.conn(); c.execute("DELETE FROM match_channels WHERE lobby_id=?", (lid,)); c.commit(); c.close()
    def cast_vote(self, lid, uid, vote):
        c = self.conn()
        try: c.execute("INSERT INTO lobby_votes(lobby_id,user_id,vote) VALUES(?,?,?)", (lid, uid, vote)); c.commit(); return True
        except: return False
        finally: c.close()
    def get_votes(self, lid): c = self.conn(); res = [dict(x) for x in c.execute("SELECT * FROM lobby_votes WHERE lobby_id=?", (lid,)).fetchall()]; c.close(); return res
    def has_voted(self, lid, uid): c = self.conn(); res = c.execute("SELECT 1 FROM lobby_votes WHERE lobby_id=? AND user_id=?", (lid, uid)).fetchone() is not None; c.close(); return res
    def clear_votes(self, lid): c = self.conn(); c.execute("DELETE FROM lobby_votes WHERE lobby_id=?", (lid,)); c.commit(); c.close()
    def set_vote_message(self, lid, mid): c = self.conn(); c.execute("UPDATE lobbies SET vote_message_id=? WHERE id=?", (mid, lid)); c.commit(); c.close()
    def save_vote_metadata(self, lid, creator_id, first_joiner_id, message_id=None): c = self.conn(); c.execute("INSERT OR REPLACE INTO vote_metadata(lobby_id,creator_id,first_joiner_id,message_id) VALUES(?,?,?,?)", (lid, creator_id, first_joiner_id, message_id)); c.commit(); c.close()
    def get_lobby_id_by_message(self, message_id): c = self.conn(); r = c.execute("SELECT lobby_id FROM vote_metadata WHERE message_id=?", (message_id,)).fetchone(); c.close(); return r["lobby_id"] if r else None
    def delete_vote_metadata(self, lid): c = self.conn(); c.execute("DELETE FROM vote_metadata WHERE lobby_id=?", (lid,)); c.commit(); c.close()
    def create_match_result(self, lid, winner, s1, s2, mvp=None): c = self.conn(); c.execute("INSERT INTO match_results(lobby_id,winner_team,team1_score,team2_score,mvp_id) VALUES(?,?,?,?,?)", (lid, winner, s1, s2, mvp)); c.commit(); c.close()

db = Database()
active_lobby_messages = {}
lobby_timeout_timers = {}
vote_timeout_timers = {}

# ============================================================
# ULTIMATE PREMIUM EMBEDS & HELPERS
# ============================================================
def extract_original_nickname(nickname):
    if not nickname: return "Player"
    cleaned = re.sub(r"\[Lv\.\d+\]\s*", "", nickname)
    cleaned = re.sub(r"RANK\s+\d+\s*\|\s*", "", cleaned, flags=re.IGNORECASE).strip()
    return cleaned if cleaned else "Player"

def build_nickname_with_level(original_name, level):
    clean = extract_original_nickname(original_name)
    prefix = f"RANK {level} | "
    return f"{prefix}{clean[:NICKNAME_MAX_LENGTH - len(prefix)]}"

def create_lobby_embed(lobby, guild):
    mode = lobby.get("game_mode", DEFAULT_MODE)
    team_size = GAME_MODES.get(mode, GAME_MODES[DEFAULT_MODE])["team_size"]
    t1c, t2c = len(lobby["team1_players"]), len(lobby["team2_players"])
    total = t1c + t2c

    def make_team_list(players, limit):
        lines = []
        for i in range(limit):
            p = f"<@{players[i]}>" if i < len(players) else "Waiting..."
            lines.append(f"`{i+1}` {p}")
        return "\n".join(lines)

    t1_text = make_team_list(lobby["team1_players"], team_size)
    t2_text = make_team_list(lobby["team2_players"], team_size)

    status_text = "🟢 Ready to start!" if total == team_size * 2 else f"⏳ Needs {team_size * 2 - total} more player(s)."
    pk_text = "\n**Security:** 🔒 Private Match" if db.get_lobby_private_key(lobby['id']) else ""

    embed = discord.Embed(color=COLORS["invisible"])
    embed.description = (
        f"### ℹ️ {mode.upper()} Lobby #{lobby['id']}\n\n"
        f"**Host:** <@{lobby['creator_id']}>{pk_text}\n\n"
        f"**🔴 Team 1 [ {t1c}/{team_size} ]**\n{t1_text}\n\n"
        f"**🟢 Team 2 [ {t2c}/{team_size} ]**\n{t2_text}\n\n"
        f"**Status:** {status_text}"
    )
    return embed

def create_profile_embed(player, member=None):
    level = player.get("level", STARTING_LEVEL)
    rank_title = get_rank_title(level)
    wr = round((player["wins"] / max(player["matches_played"], 1)) * 100, 1)

    embed = discord.Embed(color=COLORS["invisible"])
    embed.description = (
        f"### 👤 Player Profile\n\n"
        f"**User:** <@{player['user_id']}>\n"
        f"**Rank:** {get_rank_emoji(level)} {rank_title} `#{level}`\n\n"
        f"**🏆 Performance:**\n"
        f"› **Points:** `{player['points']:,}`\n"
        f"› **Win Rate:** `{wr}%`\n"
        f"› **W/L:** `{player['wins']}W` / `{player['losses']}L`\n"
        f"› **Matches:** `{player['matches_played']}`\n"
        f"› **Kills / MVPs:** `{player['kills']}` / `{player['mvps']}`\n"
    )
    if member and member.display_avatar: embed.set_thumbnail(url=member.display_avatar.url)
    return embed

async def update_member_nickname(member, level):
    try:
        if not member.guild.me.guild_permissions.manage_nicknames or member.id == member.guild.owner_id: return
        original = extract_original_nickname(member.display_name)
        new_nick = build_nickname_with_level(original, level)
        if member.display_name != new_nick: await member.edit(nick=new_nick)
    except: pass

async def update_leaderboard_channel(guild):
    try:
        settings = db.get_guild_settings(guild.id)
        if not settings or not settings.get("leaderboard_channel_id"): return
        channel = guild.get_channel(settings["leaderboard_channel_id"])
        if not channel: return

        lb = db.get_leaderboard(guild.id, 10)
        embed = discord.Embed(color=COLORS["invisible"])
        desc = "### 🏆 Server Leaderboard\n\n"
        if not lb: desc += "No players ranked yet."
        else:
            for i, p in enumerate(lb):
                wr = round((p["wins"] / max(p["matches_played"], 1)) * 100, 1)
                desc += f"**{i+1}.** <@{p['user_id']}>\n"
                desc += f"› `{p['points']:,}` pts | Rank `#{p.get('level', STARTING_LEVEL)}` | WR `{wr}%`\n\n"
        embed.description = desc

        if settings.get("leaderboard_message_id"):
            try:
                msg = await channel.fetch_message(settings["leaderboard_message_id"])
                await msg.edit(embed=embed)
                return
            except: pass
        msg = await channel.send(embed=embed)
        db.set_guild_setting(guild.id, "leaderboard_message_id", msg.id)
    except: pass

def cleanup_lobby_memory(lobby_id):
    to_remove = [k for k, v in active_lobby_messages.items() if v == lobby_id]
    for k in to_remove: del active_lobby_messages[k]
    for d in (lobby_timeout_timers, vote_timeout_timers):
        if lobby_id in d:
            try: d[lobby_id].cancel()
            except: pass
            del d[lobby_id]
    try: db.delete_vote_metadata(lobby_id)
    except: pass

# ============================================================
# CHANNELS & VOTES LOGIC
# ============================================================
async def create_match_channels(guild, lobby, lobby_id):
    cat = await guild.create_category(f"🎮 Match #{lobby_id}", overwrites={
        guild.default_role: discord.PermissionOverwrite(read_messages=False, connect=False),
        guild.me: discord.PermissionOverwrite(read_messages=True, connect=True, manage_channels=True)
    })
    
    gen_ow = { guild.default_role: discord.PermissionOverwrite(read_messages=False, connect=False), guild.me: discord.PermissionOverwrite(read_messages=True, connect=True) }
    for pid in lobby["team1_players"] + lobby["team2_players"]:
        if (m := guild.get_member(pid)): gen_ow[m] = discord.PermissionOverwrite(read_messages=True, connect=True, speak=True, send_messages=True)
        
    t1_ow, t2_ow = { guild.default_role: discord.PermissionOverwrite(connect=False), guild.me: discord.PermissionOverwrite(connect=True) }, { guild.default_role: discord.PermissionOverwrite(connect=False), guild.me: discord.PermissionOverwrite(connect=True) }
    for pid in lobby["team1_players"]:
        if (m := guild.get_member(pid)): t1_ow[m] = discord.PermissionOverwrite(connect=True, speak=True)
    for pid in lobby["team2_players"]:
        if (m := guild.get_member(pid)): t2_ow[m] = discord.PermissionOverwrite(connect=True, speak=True)

    t1_v = await guild.create_voice_channel("『🎮』︱ᴛᴇᴀᴍ ɪ", category=cat, overwrites=t1_ow)
    t2_v = await guild.create_voice_channel("『🎮』︱ᴛᴇᴀᴍ ɪɪ", category=cat, overwrites=t2_ow)
    gen_t = await guild.create_text_channel("💬・general-chat", category=cat, overwrites=gen_ow)
    
    db.save_match_channels(lobby_id, guild.id, cat.id, t1_v.id, gen_t.id, t2_v.id, gen_t.id)
    return {"category": cat, "team1_voice": t1_v, "team1_text": gen_t, "team2_voice": t2_v, "team2_text": gen_t}

async def delete_match_channels(guild, lobby_id):
    if not (mc := db.get_match_channels(lobby_id)): return
    for k in ["team1_voice_id", "team2_voice_id", "team1_text_id", "team2_text_id", "category_id"]:
        if mc.get(k) and (ch := guild.get_channel(mc[k])):
            try: await ch.delete()
            except: pass
    db.delete_match_channels_record(lobby_id)

async def auto_trigger_vote(lobby_id, guild):
    lobby = db.get_lobby(lobby_id)
    if not lobby or lobby["status"] != "started": return
    db.update_lobby_status(lobby_id, "voting")
    mc = db.get_match_channels(lobby_id)
    if not mc: return

    embed = discord.Embed(color=COLORS["invisible"])
    embed.description = (
        f"### 🗳️ Vote — Match #{lobby_id}\n\n"
        f"**Host:** <@{lobby['creator_id']}>\n\n"
        f"The match has ended. You have **2 minutes** to vote for the winner.\n\n"
        f"**🔴 Team 1:** " + " ".join([f"<@{p}>" for p in lobby["team1_players"]]) + "\n"
        f"**🟢 Team 2:** " + " ".join([f"<@{p}>" for p in lobby["team2_players"]])
    )
    if (ch := guild.get_channel(mc["team1_text_id"])):
        msg = await ch.send(embed=embed, view=VoteView(lobby_id, lobby['creator_id'], lobby.get('first_joiner_id')))
        db.set_vote_message(lobby_id, msg.id)
        db.save_vote_metadata(lobby_id, lobby['creator_id'], lobby.get('first_joiner_id'), msg.id)

async def auto_lobby_timeout(lobby_id, guild):
    try:
        await asyncio.sleep(LOBBY_TIMEOUT_SECONDS)
        lobby = db.get_lobby(lobby_id)
        if not lobby or lobby["status"] != "waiting": return
        db.update_lobby_status(lobby_id, "cancelled")
        cleanup_lobby_memory(lobby_id)
        if (ch := guild.get_channel(lobby["channel_id"])):
            embed = discord.Embed(color=COLORS["invisible"])
            embed.description = f"### ℹ️ Time is Out!\n\n**Host:** <@{lobby['creator_id']}>\n\nLobby was cancelled due to inactivity.\n\n**Mode:** {lobby.get('game_mode').upper()}\nUse `{PREFIX}play` to try again."
            await ch.send(embed=embed)
    except asyncio.CancelledError: pass

async def process_match_result(guild, lobby_id, winner_team, channel=None):
    lobby = db.get_lobby(lobby_id)
    if not lobby or lobby["status"] == "completed": return
    db.update_lobby_status(lobby_id, "completed")

    wt = lobby["team1_players"] if winner_team == "team1" else lobby["team2_players"]
    lt = lobby["team2_players"] if winner_team == "team1" else lobby["team1_players"]
    db.create_match_result(lobby_id, winner_team, len(wt), len(lt))

    mode_points = MATCH_POINTS_BY_MODE.get(lobby.get("game_mode", DEFAULT_MODE), MATCH_POINTS_BY_MODE["4v4"])
    wp, lp = mode_points["win"], mode_points["lose"]

    for pid in wt:
        if (p := db.get_player(pid, guild.id)):
            ns = p.get("win_streak", 0) + 1
            pts = wp + STREAK_BONUS.get(ns, 50 if ns >= 10 else 0)
            db.update_player_stats(pid, guild.id, points=p["points"]+pts, wins=p["wins"]+1, matches_played=p["matches_played"]+1, win_streak=ns, lose_streak=0, max_win_streak=max(p.get("max_win_streak",0), ns))
            nl = db.update_player_level(pid, guild.id, +(3 if ns >= 5 else (2 if ns >= 3 else 1)))
            if (m := guild.get_member(pid)): await update_member_nickname(m, nl)

    for pid in lt:
        if (p := db.get_player(pid, guild.id)):
            ns = p.get("lose_streak", 0) + 1
            db.update_player_stats(pid, guild.id, points=p["points"]+lp, losses=p["losses"]+1, matches_played=p["matches_played"]+1, win_streak=0, lose_streak=ns)
            nl = db.update_player_level(pid, guild.id, -(2 if ns >= 3 else 1))
            if (m := guild.get_member(pid)): await update_member_nickname(m, nl)

    embed = discord.Embed(color=COLORS["invisible"])
    embed.description = (
        f"### ✅ Match Result — #{lobby_id}\n\n"
        f"**Winner:** {'Team 1' if winner_team == 'team1' else 'Team 2'}\n\n"
        f"**Winners (+{wp} pts):**\n" + "\n".join([f"› <@{x}>" for x in wt]) + "\n\n"
        f"**Losers (+{lp} pts):**\n" + "\n".join([f"› <@{x}>" for x in lt])
    )
    if channel: await channel.send(embed=embed)
    await update_leaderboard_channel(guild)

    for pid in wt + lt:
        if (m := guild.get_member(pid)) and m.voice and (vc := guild.get_channel(db.get_available_waiting_room(guild.id, guild))):
            try: await m.move_to(vc)
            except: pass

    await asyncio.sleep(5)
    await delete_match_channels(guild, lobby_id)
    cleanup_lobby_memory(lobby_id)

# ============================================================
# VIEWS & MODALS
# ============================================================
class RoomInfoModal(discord.ui.Modal, title="📋 Room Information"):
    room_id_input = discord.ui.TextInput(label="Room ID", required=True)
    password_input = discord.ui.TextInput(label="Password", required=False)
    private_key_input = discord.ui.TextInput(label="Private Key (Optional)", required=False)
    def __init__(self, lobby_id): super().__init__(timeout=300); self.lobby_id = lobby_id
    async def on_submit(self, i):
        db.set_room_info(self.lobby_id, self.room_id_input.value, self.password_input.value, self.private_key_input.value or None)
        await i.response.send_message(embed=discord.Embed(color=COLORS["invisible"], description=f"### ✅ Room Info Saved\n\n**Room ID:** `{self.room_id_input.value}`\n**Pass:** `{self.password_input.value or 'None'}`"), ephemeral=True)

class JoinKeyModal(discord.ui.Modal, title="🔑 Enter Private Key"):
    key_input = discord.ui.TextInput(label="Private Key", required=True)
    def __init__(self, lobby_id, team, pk, view_ref): super().__init__(timeout=120); self.lobby_id, self.team, self.pk, self.view_ref = lobby_id, team, pk, view_ref
    async def on_submit(self, i):
        if self.key_input.value == self.pk: await self.view_ref._complete_join(i, self.team)
        else: await i.response.send_message(embed=discord.Embed(color=COLORS["invisible"], description="### ❌ Wrong Key\n\nThe private key is incorrect."), ephemeral=True)

class LobbyButtonsView(discord.ui.View):
    def __init__(self, lobby_id, creator_id, guild_id):
        super().__init__(timeout=None)
        self.lobby_id, self.creator_id, self.guild_id = lobby_id, creator_id, guild_id

    @discord.ui.button(label="Join Team 1", style=discord.ButtonStyle.danger, emoji="🔴")
    async def btn_t1(self, i, b): await self._handle_join(i, "team1")
    @discord.ui.button(label="Join Team 2", style=discord.ButtonStyle.success, emoji="🟢")
    async def btn_t2(self, i, b): await self._handle_join(i, "team2")
    @discord.ui.button(label="Leave", style=discord.ButtonStyle.secondary, emoji="🚪")
    async def btn_leave(self, i, b):
        if db.remove_player_from_lobby(self.lobby_id, i.user.id):
            try: await i.message.edit(embed=create_lobby_embed(db.get_lobby(self.lobby_id), i.guild), view=self)
            except: pass
            await i.response.send_message("✅ Left lobby.", ephemeral=True)
        else: await i.response.send_message("❌ Not in this lobby.", ephemeral=True)

    @discord.ui.button(label="Cancel Match", style=discord.ButtonStyle.danger, emoji="✖️")
    async def btn_cancel(self, i, b):
        if i.user.id != self.creator_id and not i.user.guild_permissions.administrator: return await i.response.send_message("❌ Only host can cancel.", ephemeral=True)
        db.update_lobby_status(self.lobby_id, "cancelled")
        cleanup_lobby_memory(self.lobby_id)
        await delete_match_channels(i.guild, self.lobby_id)
        try: await i.message.edit(embed=discord.Embed(color=COLORS["invisible"], description=f"### ❌ Match Cancelled\n\nCancelled by <@{i.user.id}>."), view=None)
        except: pass
        await i.response.send_message("✅ Cancelled.", ephemeral=True)

    async def _handle_join(self, i, team):
        lobby = db.get_lobby(self.lobby_id)
        if not lobby or lobby["status"] != "waiting": return await i.response.send_message("❌ Lobby not active.", ephemeral=True)
        mem = i.guild.get_member(i.user.id)
        if not mem or not mem.voice or mem.voice.channel.id not in db.get_waiting_rooms(i.guild.id):
            return await i.response.send_message(embed=discord.Embed(color=COLORS["invisible"], description="### ℹ️ Voice Error\n\nYou must be in a Waiting Room voice channel."), ephemeral=True)
        existing = db.get_player_active_lobby(i.user.id, i.guild.id)
        if existing and existing["id"] != self.lobby_id: return await i.response.send_message("❌ Leave your current lobby first.", ephemeral=True)
        if (pk := db.get_lobby_private_key(self.lobby_id)): return await i.response.send_modal(JoinKeyModal(self.lobby_id, team, pk, self))
        await self._complete_join(i, team)

    async def _complete_join(self, i, team):
        lobby = db.get_lobby(self.lobby_id)
        ts = GAME_MODES.get(lobby["game_mode"], GAME_MODES[DEFAULT_MODE])["team_size"]
        if len(lobby["team1_players" if team == "team1" else "team2_players"]) >= ts: return await i.response.send_message("❌ Team full.", ephemeral=True)
        
        if i.user.id in lobby["team2_players" if team == "team1" else "team1_players"]: db.remove_player_from_lobby(self.lobby_id, i.user.id)
        db.add_player_to_lobby(self.lobby_id, i.user.id, team)
        if i.user.id != lobby["creator_id"]: db.set_first_joiner(self.lobby_id, i.user.id)
        
        lobby = db.get_lobby(self.lobby_id)
        try: await i.message.edit(embed=create_lobby_embed(lobby, i.guild), view=self)
        except: pass
        await i.response.send_message(f"✅ Joined {'Team 1' if team=='team1' else 'Team 2'}!", ephemeral=True)
        
        if lobby.get("room_id"):
            await i.followup.send(embed=discord.Embed(color=COLORS["invisible"], description=f"### 📡 Room Info\n\n**ID:** `{lobby['room_id']}`\n**Pass:** `{lobby.get('room_code') or 'None'}`"), ephemeral=True)

        if len(lobby["team1_players"]) >= ts and len(lobby["team2_players"]) >= ts:
            db.update_lobby_status(self.lobby_id, "started")
            for item in self.children: item.disabled = True
            try: await i.message.edit(view=self)
            except: pass
            channels = await create_match_channels(i.guild, lobby, self.lobby_id)
            if not channels: return
            await i.channel.send(embed=discord.Embed(color=COLORS["invisible"], description="### ✅ Match Ready!\n\nMatch started. Moving players..."))
            for p in lobby["team1_players"] + lobby["team2_players"]:
                if (m := i.guild.get_member(p)) and m.voice:
                    try: await m.move_to(channels["team1_voice"] if p in lobby["team1_players"] else channels["team2_voice"])
                    except: pass
            
            start_embed = discord.Embed(color=COLORS["invisible"], description=f"### 🎮 Match Started!\n\n**Host:** <@{lobby['creator_id']}>\n\nMatch is live! Click **Start Vote** when finished.")
            if lobby.get('room_id'): start_embed.description += f"\n\n**Room Info:**\nID: `{lobby['room_id']}`\nPass: `{lobby.get('room_code') or 'None'}`"
            try: await channels["team1_text"].send(embed=start_embed, view=StartVoteView(self.lobby_id, i.guild.id, lobby["creator_id"]))
            except: pass

class StartVoteView(discord.ui.View):
    def __init__(self, lobby_id, guild_id, creator_id):
        super().__init__(timeout=None)
        self.lobby_id, self.guild_id, self.creator_id = lobby_id, guild_id, creator_id
    @discord.ui.button(label="Start Vote", style=discord.ButtonStyle.success, emoji="🗳️")
    async def btn_start(self, i, b):
        if i.user.id != self.creator_id: return await i.response.send_message("❌ Only host can start vote.", ephemeral=True)
        await i.response.send_message("✅ Vote started!", ephemeral=True)
        for item in self.children: item.disabled = True
        try: await i.message.edit(view=self)
        except: pass
        asyncio.create_task(auto_trigger_vote(self.lobby_id, i.guild))
    @discord.ui.button(label="Cancel Match", style=discord.ButtonStyle.danger, emoji="✖️")
    async def btn_cancel(self, i, b):
        if i.user.id != self.creator_id and not i.user.guild_permissions.administrator: return await i.response.send_message("❌ Only host can cancel.", ephemeral=True)
        db.update_lobby_status(self.lobby_id, "cancelled")
        cleanup_lobby_memory(self.lobby_id)
        if (lobby := db.get_lobby(self.lobby_id)):
            for p in lobby["team1_players"] + lobby["team2_players"]:
                if (m := i.guild.get_member(p)) and m.voice and (vc := i.guild.get_channel(db.get_available_waiting_room(i.guild.id, i.guild))):
                    try: await m.move_to(vc)
                    except: pass
        await delete_match_channels(i.guild, self.lobby_id)
        await i.response.send_message(embed=discord.Embed(color=COLORS["invisible"], description="### ❌ Match Cancelled\n\nChannels deleted."))

class VoteView(discord.ui.View):
    def __init__(self, lobby_id, creator_id, first_joiner_id):
        super().__init__(timeout=VOTE_TIMEOUT_SECONDS)
        self.lobby_id, self.creator_id, self.first_joiner_id = lobby_id, creator_id, first_joiner_id
    async def on_timeout(self):
        lobby = db.get_lobby(self.lobby_id)
        if not lobby or lobby["status"] != "voting": return
        votes = db.get_votes(self.lobby_id)
        g = bot.get_guild(lobby["guild_id"])
        mc = db.get_match_channels(self.lobby_id)
        ch = g.get_channel(mc["team1_text_id"]) if mc else g.get_channel(lobby["channel_id"])
        if not votes: return await ch.send(embed=discord.Embed(color=COLORS["invisible"], description="### ℹ️ Vote Timeout\n\nNo votes cast. Admin resolve needed."))
        t1v, t2v = sum(1 for v in votes if v["vote"]=="team1"), sum(1 for v in votes if v["vote"]=="team2")
        if t1v == t2v: return await ch.send(embed=discord.Embed(color=COLORS["invisible"], description="### ℹ️ Tie\n\nVote tied. Admin resolve needed."))
        await process_match_result(g, self.lobby_id, "team1" if t1v > t2v else "team2", ch)
    @discord.ui.button(label="Team 1", style=discord.ButtonStyle.danger, emoji="🔴")
    async def btn_t1(self, i, b): await self._vote(i, "team1")
    @discord.ui.button(label="Team 2", style=discord.ButtonStyle.success, emoji="🟢")
    async def btn_t2(self, i, b): await self._vote(i, "team2")
    async def _vote(self, i, choice):
        lobby = db.get_lobby(self.lobby_id)
        if not lobby or lobby["status"] != "voting": return await i.response.send_message("❌ Vote inactive.", ephemeral=True)
        all_p = lobby["team1_players"] + lobby["team2_players"]
        if i.user.id not in all_p: return await i.response.send_message("❌ Not in match.", ephemeral=True)
        if db.has_voted(self.lobby_id, i.user.id): return await i.response.send_message("❌ Already voted.", ephemeral=True)
        db.cast_vote(self.lobby_id, i.user.id, choice)
        await i.response.send_message("✅ Voted!", ephemeral=True)
        if len(db.get_votes(self.lobby_id)) >= len(all_p):
            for item in self.children: item.disabled = True
            try: await i.message.edit(view=self)
            except: pass
            t1v, t2v = sum(1 for v in db.get_votes(self.lobby_id) if v["vote"]=="team1"), sum(1 for v in db.get_votes(self.lobby_id) if v["vote"]=="team2")
            if t1v == t2v: await i.channel.send(embed=discord.Embed(color=COLORS["invisible"], description="### ℹ️ Tie\n\nAdmin resolve needed."))
            else: await process_match_result(i.guild, self.lobby_id, "team1" if t1v > t2v else "team2", i.channel)

class CreateLobbyView(discord.ui.View):
    def __init__(self, ctx, mode):
        super().__init__(timeout=300)
        self.ctx, self.mode = ctx, mode
    @discord.ui.button(label="Create Lobby", style=discord.ButtonStyle.success, emoji="🎮")
    async def btn_create(self, i, b):
        if i.user.id != self.ctx.author.id: return await i.response.send_message("❌ Not your command.", ephemeral=True)
        await i.response.send_modal(LobbyCreateModal(self.ctx, self.mode))
        for item in self.children: item.disabled = True
        try: await i.message.edit(view=self)
        except: pass

class LobbyCreateModal(discord.ui.Modal, title="🎮 Enter Room Info"):
    room_id = discord.ui.TextInput(label="Room ID", required=True)
    password = discord.ui.TextInput(label="Password", required=False)
    priv_key = discord.ui.TextInput(label="Private Key (Optional)", required=False)
    def __init__(self, ctx, mode): super().__init__(timeout=300); self.ctx, self.mode = ctx, mode
    async def on_submit(self, i):
        lid = db.create_lobby(self.ctx.guild.id, self.ctx.author.id, self.ctx.channel.id, mode=self.mode)
        db.set_room_info(lid, self.room_id.value, self.password.value, self.priv_key.value or None)
        db.add_player_to_lobby(lid, self.ctx.author.id, "team1")
        msg = await self.ctx.send(embed=create_lobby_embed(db.get_lobby(lid), self.ctx.guild), view=LobbyButtonsView(lid, self.ctx.author.id, self.ctx.guild.id))
        db.update_lobby_message(lid, msg.id)
        lobby_timeout_timers[lid] = asyncio.create_task(auto_lobby_timeout(lid, self.ctx.guild))
        await i.response.send_message(embed=discord.Embed(color=COLORS["invisible"], description="### ✅ Lobby Created\n\nLobby is now live!"), ephemeral=True)

# ============================================================
# BOT COMMANDS & EVENTS
# ============================================================
intents = discord.Intents.default()
intents.members = True; intents.message_content = True; intents.voice_states = True
bot = commands.Bot(command_prefix=PREFIX, intents=intents, help_command=None)

def is_admin_check(ctx): return ctx.author.guild_permissions.administrator
def is_bot_owner_or_admin_check(ctx): return ctx.author.id == BOT_OWNER_ID or ctx.author.guild_permissions.administrator
def is_high_role_member(member):
    if member.guild_permissions.administrator or member.guild_permissions.manage_guild: return True
    guild_roles = [r for r in member.guild.roles if r.hoist and r != member.guild.default_role]
    return (member.top_role.position if member.top_role else 0) >= max(1, max(r.position for r in guild_roles) // 2) if guild_roles else False

@bot.event
async def on_ready():
    logger.info(f"✅ {bot.user} online!")
    bot.add_view(VoteView(0,0,0)); bot.add_view(LobbyButtonsView(0,0,0)); bot.add_view(StartVoteView(0,0,0))
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=f"Free Fire | {PREFIX}play"))

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        msg = ctx.message.content.lower()
        if msg.startswith(f"{PREFIX}play"):
            embed = discord.Embed(color=COLORS["invisible"])
            embed.description = (f"### ℹ️ Invalid Command!\n\n**Host:** {ctx.author.mention}\n\nYou didn't enter the command correctly.\n\n**Mode:** 4V4 (Default)\nUse `{PREFIX}play` or `{PREFIX}play1v1` without spaces to try again.")
            await ctx.send(embed=embed)
    elif isinstance(error, commands.CommandOnCooldown):
        await ctx.send(embed=discord.Embed(color=COLORS["invisible"], description=f"### ⏳ Cooldown\n\nPlease wait `{error.retry_after:.1f}s`."))
    elif isinstance(error, commands.CheckFailure):
        await ctx.send(embed=discord.Embed(color=COLORS["invisible"], description="### ❌ Access Denied\n\nYou don't have permission."))

@bot.event
async def on_message(message):
    if message.author.bot or not message.guild: return
    allowed = [f"{PREFIX}p", f"{PREFIX}setup", f"{PREFIX}top", f"{PREFIX}matches", f"{PREFIX}card", f"{PREFIX}matchinfo", f"{PREFIX}mylevel", f"{PREFIX}myrank", f"{PREFIX}fixrank", f"{PREFIX}leave"]
    cmd = message.content.strip().split()[0] if message.content.strip().split() else ""
    if not db.is_bot_allowed_channel(message.guild.id, message.channel.id) and not message.author.guild_permissions.administrator and cmd not in allowed:
        if message.content.startswith(PREFIX):
            try: await message.reply(embed=discord.Embed(color=COLORS["invisible"], description="### ❌ Not Allowed\n\nUse this in Play channels."), delete_after=10)
            except: pass
        return
    await bot.process_commands(message)

async def create_mode_lobby(ctx, mode, args):
    if args:
        return await ctx.send(embed=discord.Embed(color=COLORS["invisible"], description=f"### ℹ️ Invalid Command!\n\n**Host:** {ctx.author.mention}\n\nYou didn't enter the command correctly (removed spaces).\n\n**Mode:** {mode.upper()}\nUse `{PREFIX}play{'' if mode=='4v4' else mode}` to try again."))
    mem = ctx.guild.get_member(ctx.author.id)
    if not mem or not mem.voice or mem.voice.channel.id not in db.get_waiting_rooms(ctx.guild.id):
        return await ctx.send(embed=discord.Embed(color=COLORS["invisible"], description="### ℹ️ Voice Required\n\nYou must be in a Waiting Room voice channel."))
    if db.get_player_active_lobby(ctx.author.id, ctx.guild.id):
        return await ctx.send(embed=discord.Embed(color=COLORS["invisible"], description="### ❌ Error\n\nLeave your current lobby first."))
    await ctx.send(embed=discord.Embed(color=COLORS["invisible"], description=f"### 🎮 Create {mode.upper()} Lobby\n\nClick below to enter room info."), view=CreateLobbyView(ctx, mode))

# PLAYER COMMANDS
@bot.command(name="play")
@commands.cooldown(1, 10, commands.BucketType.user)
async def play_cmd(ctx, *args): await create_mode_lobby(ctx, "4v4", args)
@bot.command(name="play1v1")
@commands.cooldown(1, 10, commands.BucketType.user)
async def play1v1_cmd(ctx, *args):
    if not is_high_role_member(ctx.author): return await ctx.send(embed=discord.Embed(color=COLORS["invisible"], description="### 🔒 Access Denied\n\nOnly high roles can host 1v1."))
    await create_mode_lobby(ctx, "1v1", args)
@bot.command(name="play2v2")
@commands.cooldown(1, 10, commands.BucketType.user)
async def play2v2_cmd(ctx, *args): await create_mode_lobby(ctx, "2v2", args)
@bot.command(name="play3v3")
@commands.cooldown(1, 10, commands.BucketType.user)
async def play3v3_cmd(ctx, *args): await create_mode_lobby(ctx, "3v3", args)
@bot.command(name="play4v4")
@commands.cooldown(1, 10, commands.BucketType.user)
async def play4v4_cmd(ctx, *args): await create_mode_lobby(ctx, "4v4", args)

@bot.command(name="leave")
async def leave_cmd(ctx):
    lobby = db.get_player_active_lobby(ctx.author.id, ctx.guild.id)
    if not lobby: return await ctx.send(embed=discord.Embed(color=COLORS["invisible"], description="### ❌ Not in Lobby\n\nYou are not in any active lobby."))
    db.remove_player_from_lobby(lobby["id"], ctx.author.id)
    await ctx.send(embed=discord.Embed(color=COLORS["invisible"], description=f"### ✅ Left Lobby\n\nYou left lobby `#{lobby['id']}`."))

@bot.command(name="matches")
async def matches_cmd(ctx):
    lobbies = db.get_active_lobbies(ctx.guild.id)
    if not lobbies: return await ctx.send(embed=discord.Embed(color=COLORS["invisible"], description="### 🎮 Active Lobbies\n\nNo active lobbies right now."))
    desc = "### 🎮 Active Lobbies\n\n"
    for l in lobbies[:5]:
        m = l.get("game_mode", DEFAULT_MODE)
        ts = GAME_MODES.get(m, GAME_MODES[DEFAULT_MODE])["team_size"]
        desc += f"**#{l['id']}** {m.upper()} — Status: `{l['status']}`\n› 🔴 `{len(l['team1_players'])}/{ts}` | 🟢 `{len(l['team2_players'])}/{ts}`\n\n"
    await ctx.send(embed=discord.Embed(color=COLORS["invisible"], description=desc))

@bot.command(name="p")
async def p_cmd(ctx, member: discord.Member = None):
    t = member or ctx.author; p = db.get_or_create_player(t.id, ctx.guild.id, t.display_name)
    await ctx.send(embed=create_profile_embed(p, t))

@bot.command(name="card")
async def card_cmd(ctx, member: discord.Member = None):
    if "zelika" not in (ctx.channel.name.lower() if ctx.channel.name else ""):
        return await ctx.send(embed=discord.Embed(color=COLORS["invisible"], description="### ❌ Not Allowed\n\nThis command works only in `zelika-play`."))
    t = member or ctx.author; p = db.get_or_create_player(t.id, ctx.guild.id, t.display_name)
    await ctx.send(embed=create_profile_embed(p, t))

@bot.command(name="top")
async def top_cmd(ctx):
    lb = db.get_leaderboard(ctx.guild.id, 10)
    desc = "### 🏆 Top 10 Leaderboard\n\n"
    if not lb: desc += "No players ranked yet."
    else:
        for i, p in enumerate(lb):
            wr = round((p["wins"] / max(p["matches_played"], 1)) * 100, 1)
            desc += f"**{i+1}.** <@{p['user_id']}>\n› `{p['points']:,}` pts | Rank `#{p.get('level', STARTING_LEVEL)}` | WR `{wr}%`\n\n"
    await ctx.send(embed=discord.Embed(color=COLORS["invisible"], description=desc))

@bot.command(name="mylevel")
async def mylevel_cmd(ctx, member: discord.Member = None):
    t = member or ctx.author; p = db.get_or_create_player(t.id, ctx.guild.id, t.display_name)
    await ctx.send(embed=discord.Embed(color=COLORS["invisible"], description=f"### 🏅 Your Rank\n\n<@{t.id}> — Rank `#{p.get('level', STARTING_LEVEL)}`"))

@bot.command(name="myrank")
async def myrank_cmd(ctx):
    p = db.get_or_create_player(ctx.author.id, ctx.guild.id, ctx.author.display_name)
    original = p.get("original_nickname") or extract_original_nickname(ctx.author.display_name)
    target = build_nickname_with_level(original, p.get("level", STARTING_LEVEL))
    await ctx.send(embed=discord.Embed(color=COLORS["invisible"], description=f"### 📝 Nickname Status\n\n**Current:** `{ctx.author.display_name}`\n**Target:** `{target}`"))

@bot.command(name="fixrank")
async def fixrank_cmd(ctx, member: discord.Member = None):
    t = member or ctx.author; p = db.get_or_create_player(t.id, ctx.guild.id, t.display_name)
    lvl = p.get("level", STARTING_LEVEL)
    if t.id == ctx.guild.owner_id: return await ctx.send(embed=discord.Embed(color=COLORS["invisible"], description=f"### ⚠️ Server Owner\n\nCannot change owner nickname. Your level is `#{lvl}`."))
    await update_member_nickname(t, lvl)
    await ctx.send(embed=discord.Embed(color=COLORS["invisible"], description=f"### ✅ Rank Applied\n\nUpdated <@{t.id}> to `#{lvl}`."))

@bot.command(name="matchinfo")
async def matchinfo_cmd(ctx, lobby_id: int = None):
    if lobby_id is None: return await ctx.send(embed=discord.Embed(color=COLORS["invisible"], description=f"### ❌ Missing ID\n\nUsage: `{PREFIX}matchinfo <id>`"))
    l = db.get_lobby(lobby_id)
    if not l: return await ctx.send(embed=discord.Embed(color=COLORS["invisible"], description=f"### ❌ Not Found\n\nLobby `#{lobby_id}` doesn't exist."))
    desc = f"### 📋 Match #{lobby_id}\n\n**Status:** `{l['status']}`\n**Mode:** `{l.get('game_mode', DEFAULT_MODE).upper()}`\n\n**🔴 Team 1:**\n"
    desc += "\n".join([f"› <@{p}>" for p in l["team1_players"]]) or "› *Empty*"
    desc += "\n\n**🟢 Team 2:**\n"
    desc += "\n".join([f"› <@{p}>" for p in l["team2_players"]]) or "› *Empty*"
    await ctx.send(embed=discord.Embed(color=COLORS["invisible"], description=desc))

# ADMIN COMMANDS
@bot.command(name="setup")
@commands.check(is_bot_owner_or_admin_check)
async def setup_cmd(ctx):
    guild = ctx.guild
    cat = discord.utils.get(guild.categories, name="🎮 FREE FIRE")
    if not cat: cat = await guild.create_category("🎮 FREE FIRE")

    cmd_ch_name = "📜・اوامر-اللاعبين"
    if not discord.utils.get(guild.text_channels, name=cmd_ch_name):
        cmd_ch = await guild.create_text_channel(cmd_ch_name, category=cat, position=0, overwrites={guild.default_role: discord.PermissionOverwrite(read_messages=True, send_messages=False), guild.me: discord.PermissionOverwrite(send_messages=True)})
        help_embed = discord.Embed(color=COLORS["invisible"], description=f"### ℹ️ الأوامر المتاحة للاعبين\n\n**🎮 تحديات (Play):**\n`{PREFIX}play` — لإنشاء روم 4v4\n`{PREFIX}play2v2` — لإنشاء روم 2v2\n`{PREFIX}play3v3` — لإنشاء روم 3v3\n`{PREFIX}play1v1` — لإنشاء روم 1v1 (رتب عليا فقط)\n\n**📊 إحصائيات (Stats):**\n`{PREFIX}p` — بروفايلك\n`{PREFIX}top` — قائمة المتصدرين\n`{PREFIX}matches` — الرومات النشطة\n`{PREFIX}leave` — للخروج من الروم\n")
        msg = await cmd_ch.send(embed=help_embed); await msg.pin(); db.add_commands_channel(guild.id, cmd_ch.id)

    for ch_name in ["🎮・apostada-play", "🏆・leaderboard"]:
        if not discord.utils.get(guild.text_channels, name=ch_name):
            ch = await guild.create_text_channel(ch_name, category=cat)
            db.add_commands_channel(guild.id, ch.id); db.add_play_channel(guild.id, ch.id)
            if "leaderboard" in ch_name: db.set_guild_setting(guild.id, "leaderboard_channel_id", ch.id)

    for ch_name in ["⏳・Waiting 1", "⏳・Waiting 2"]:
        if not discord.utils.get(guild.voice_channels, name=ch_name):
            ch = await guild.create_voice_channel(ch_name, category=cat); db.add_waiting_room(guild.id, ch.id)

    await ctx.send(embed=discord.Embed(color=COLORS["invisible"], description="### ✅ Setup Complete!\n\nChannels and pinned commands created."))

@bot.command(name="cleanup")
@commands.check(is_bot_owner_or_admin_check)
async def cleanup_cmd(ctx):
    deleted = 0
    for cat in ctx.guild.categories:
        if cat.name.startswith("🎮 Match #"):
            for ch in cat.channels:
                try: await ch.delete()
                except: pass
            try: await cat.delete(); deleted += 1
            except: pass
    await ctx.send(embed=discord.Embed(color=COLORS["invisible"], description=f"### 🧹 Cleanup Complete\n\nDeleted `{deleted}` match categories."))

@bot.command(name="scan")
@commands.check(is_bot_owner_or_admin_check)
async def scan_cmd(ctx):
    desc = f"### 🔍 Server Scan\n\n**Categories:** `{len(ctx.guild.categories)}`\n**Text:** `{len(ctx.guild.text_channels)}`\n**Voice:** `{len(ctx.guild.voice_channels)}`"
    await ctx.send(embed=discord.Embed(color=COLORS["invisible"], description=desc))

@bot.command(name="deletecat")
@commands.check(is_bot_owner_or_admin_check)
async def deletecat_cmd(ctx, *, name: str = None):
    if not name: return await ctx.send(embed=discord.Embed(color=COLORS["invisible"], description=f"### ❌ Missing Name\n\nUsage: `{PREFIX}deletecat <name>`"))
    target = discord.utils.find(lambda c: name.lower() in c.name.lower(), ctx.guild.categories)
    if not target: return await ctx.send(embed=discord.Embed(color=COLORS["invisible"], description="### ❌ Not Found\n\nNo category matches."))
    await ctx.send(embed=discord.Embed(color=COLORS["invisible"], description=f"### ⚠️ Confirm Deletion\n\nTarget: `{target.name}`\nUse `{PREFIX}confirmcat {target.name}` to delete."))

@bot.command(name="confirmcat")
@commands.check(is_bot_owner_or_admin_check)
async def confirmcat_cmd(ctx, *, name: str = None):
    if not name: return
    target = discord.utils.find(lambda c: name.lower() in c.name.lower(), ctx.guild.categories)
    if not target: return
    for ch in target.channels:
        try: await ch.delete()
        except: pass
    try: await target.delete()
    except: pass
    await ctx.send(embed=discord.Embed(color=COLORS["invisible"], description=f"### 🗑️ Deleted\n\nCategory `{target.name}` deleted."))

@bot.command(name="botinfo")
async def botinfo_cmd(ctx):
    await ctx.send(embed=discord.Embed(color=COLORS["invisible"], description=f"### 🤖 Bot Info\n\n**Version:** v6.0 ULTIMATE\n**Style:** Invisible Embeds\n**Prefix:** `{PREFIX}`\n**Servers:** `{len(bot.guilds)}`"))

@bot.command(name="setcommandschannel")
@commands.check(is_admin_check)
async def setcommandschannel_cmd(ctx, channel: discord.TextChannel = None):
    ch = channel or ctx.channel
    if ch.id in db.get_commands_channels(ctx.guild.id):
        db.remove_commands_channel(ctx.guild.id, ch.id)
        await ctx.send(embed=discord.Embed(color=COLORS["invisible"], description=f"### ✅ Removed\n\n{ch.mention} removed from command channels."))
    else:
        db.add_commands_channel(ctx.guild.id, ch.id)
        await ctx.send(embed=discord.Embed(color=COLORS["invisible"], description=f"### ✅ Added\n\n{ch.mention} added to command channels."))

@bot.command(name="setleaderboard")
@commands.check(is_admin_check)
async def setleaderboard_cmd(ctx):
    db.set_guild_setting(ctx.guild.id, "leaderboard_channel_id", ctx.channel.id)
    await update_leaderboard_channel(ctx.guild)
    await ctx.send(embed=discord.Embed(color=COLORS["invisible"], description=f"### ✅ Leaderboard Set\n\n{ctx.channel.mention} is now the leaderboard."))

@bot.command(name="resolve")
@commands.check(is_admin_check)
async def resolve_cmd(ctx, lobby_id: int = None, winner: str = None):
    if not lobby_id or not winner or winner.lower() not in ["team1", "team2"]:
        return await ctx.send(embed=discord.Embed(color=COLORS["invisible"], description=f"### ❌ Error\n\nUsage: `{PREFIX}resolve <id> <team1|team2>`"))
    lobby = db.get_lobby(lobby_id)
    if not lobby or lobby["status"] != "voting": return await ctx.send(embed=discord.Embed(color=COLORS["invisible"], description="### ❌ Error\n\nLobby is not in voting status."))
    await ctx.send(embed=discord.Embed(color=COLORS["invisible"], description=f"### ⚖️ Resolved\n\nAdmin forced winner: **{'Team 1' if winner=='team1' else 'Team 2'}**"))
    await process_match_result(ctx.guild, lobby_id, winner.lower(), ctx.channel)

@bot.command(name="resetstats")
@commands.check(is_admin_check)
async def resetstats_cmd(ctx, member: discord.Member = None):
    if not member: return await ctx.send(embed=discord.Embed(color=COLORS["invisible"], description=f"### ❌ Missing User\n\nUsage: `{PREFIX}resetstats @user`"))
    db.reset_stats(member.id, ctx.guild.id)
    await update_member_nickname(member, STARTING_LEVEL)
    await ctx.send(embed=discord.Embed(color=COLORS["invisible"], description=f"### ✅ Stats Reset\n\n<@{member.id}> stats wiped."))

@bot.command(name="resetrankall")
@commands.check(is_admin_check)
async def resetrankall_cmd(ctx):
    msg = await ctx.send(embed=discord.Embed(color=COLORS["invisible"], description="### 🚀 Resetting All Ranks..."))
    for m in ctx.guild.members:
        if m.bot: continue
        db.get_or_create_player(m.id, ctx.guild.id, m.display_name)
        db.update_player_stats(m.id, ctx.guild.id, level=STARTING_LEVEL)
        await update_member_nickname(m, STARTING_LEVEL)
    await msg.edit(embed=discord.Embed(color=COLORS["invisible"], description="### ✅ All Ranks Reset\n\nEveryone is back to 1000."))

@bot.command(name="setlevel")
@commands.check(is_admin_check)
async def setlevel_cmd(ctx, member: discord.Member = None, level: int = None):
    if not member or not level: return await ctx.send(embed=discord.Embed(color=COLORS["invisible"], description=f"### ❌ Missing Args\n\nUsage: `{PREFIX}setlevel @user <lvl>`"))
    db.get_or_create_player(member.id, ctx.guild.id, member.display_name)
    db.update_player_stats(member.id, ctx.guild.id, level=level)
    await update_member_nickname(member, level)
    await ctx.send(embed=discord.Embed(color=COLORS["invisible"], description=f"### ✅ Level Updated\n\n<@{member.id}> is now `#{level}`."))

@bot.command(name="syncnicknames")
@commands.check(is_admin_check)
async def syncnicknames_cmd(ctx):
    msg = await ctx.send(embed=discord.Embed(color=COLORS["invisible"], description="### 🔄 Syncing..."))
    for m in ctx.guild.members:
        if m.bot: continue
        p = db.get_or_create_player(m.id, ctx.guild.id, m.display_name)
        await update_member_nickname(m, p.get("level", STARTING_LEVEL))
    await msg.edit(embed=discord.Embed(color=COLORS["invisible"], description="### ✅ Synced\n\nAll nicknames updated."))

@bot.command(name="fixrankall")
@commands.check(is_admin_check)
async def fixrankall_cmd(ctx):
    await syncnicknames_cmd(ctx)

if __name__ == "__main__":
    TOKEN = os.getenv("DISCORD_TOKEN") or "MTUxNzU4NjA4MTk3NTg5NDAxNw.GIdlur.eijw9tG-o5G6KE6JygXiNlFlkyZZVtRmgqJvAk"
    bot.run(TOKEN)