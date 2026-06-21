"""
===========================================================
  🔥 Free Fire Matchmaking Bot — v4.0 CLEAN
===========================================================
  🤖 كل شي تلقائي! الأزرار + Modal + Private Key
  🎨 شكل احترافي مطابق لـ Apostado Manager
  🧹 كود نظيف بدون كود ميت
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
from typing import Optional, List, Dict, Any

# ============================================================
# LOGGING
# ============================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("freefire")

# ============================================================
# CONFIG
# ============================================================
PREFIX = "!!"
BOT_OWNER_ID = 1077949215772250143
BOT_OWNER_NAME = "aizenx000"
GUILD_WHITELIST_ENABLED = True

STARTING_LEVEL = 100
MIN_RANK = 1
MAX_RANK = 9999
NICKNAME_MAX_LENGTH = 32

GAME_MODES = {
    "1v1": {"team_size": 1, "lobby_size": 2, "emoji": "⚔️", "color": 0xFF4444},
    "2v2": {"team_size": 2, "lobby_size": 4, "emoji": "🔥", "color": 0xFF8800},
    "3v3": {"team_size": 3, "lobby_size": 6, "emoji": "💎", "color": 0x00BFFF},
    "4v4": {"team_size": 4, "lobby_size": 8, "emoji": "👑", "color": 0xFFD700},
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
    "success": 0x00FF7F, "error": 0xFF0000, "warning": 0xFFD700,
    "info": 0x00BFFF, "play": 0xFF6B00, "profile": 0x2B2D31,
    "leaderboard": 0xFFD700, "match": 0x3498DB, "admin": 0xE74C3C,
    "vote": 0x9B59B6, "auto": 0x00FF7F,
}

GUILD_SETTINGS_COLUMNS = {
    "form_channel_id", "announcement_role_id", "leaderboard_channel_id",
    "leaderboard_message_id", "auto_channel_category_id"
}


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
                CREATE TABLE IF NOT EXISTS guild_settings (
                    guild_id INTEGER PRIMARY KEY,
                    form_channel_id INTEGER DEFAULT NULL,
                    announcement_role_id INTEGER DEFAULT NULL,
                    leaderboard_channel_id INTEGER DEFAULT NULL,
                    leaderboard_message_id INTEGER DEFAULT NULL,
                    auto_channel_category_id INTEGER DEFAULT NULL
                );
                CREATE TABLE IF NOT EXISTS play_channels (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER NOT NULL, channel_id INTEGER NOT NULL,
                    UNIQUE(guild_id, channel_id)
                );
                CREATE TABLE IF NOT EXISTS bot_commands_channels (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER NOT NULL, channel_id INTEGER NOT NULL,
                    UNIQUE(guild_id, channel_id)
                );
                CREATE TABLE IF NOT EXISTS waiting_rooms (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER NOT NULL, channel_id INTEGER NOT NULL,
                    UNIQUE(guild_id, channel_id)
                );
                CREATE TABLE IF NOT EXISTS allowed_guilds (
                    guild_id INTEGER PRIMARY KEY,
                    guild_name TEXT, added_by INTEGER,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS players (
                    user_id INTEGER, guild_id INTEGER NOT NULL,
                    username TEXT NOT NULL, points INTEGER DEFAULT 0,
                    rank_pos INTEGER DEFAULT 1, wins INTEGER DEFAULT 0,
                    losses INTEGER DEFAULT 0, kills INTEGER DEFAULT 0,
                    mvps INTEGER DEFAULT 0, matches_played INTEGER DEFAULT 0,
                    level INTEGER DEFAULT 100,
                    win_streak INTEGER DEFAULT 0, lose_streak INTEGER DEFAULT 0,
                    max_win_streak INTEGER DEFAULT 0,
                    original_nickname TEXT DEFAULT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_id, guild_id)
                );
                CREATE TABLE IF NOT EXISTS lobbies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER NOT NULL, creator_id INTEGER NOT NULL,
                    game_mode TEXT DEFAULT '4v4',
                    status TEXT DEFAULT 'waiting' CHECK(status IN ('waiting','started','voting','completed','cancelled')),
                    team1_players TEXT DEFAULT '[]', team2_players TEXT DEFAULT '[]',
                    first_joiner_id INTEGER DEFAULT NULL,
                    room_id TEXT DEFAULT NULL, room_code TEXT DEFAULT NULL,
                    private_key TEXT DEFAULT NULL,
                    vote_message_id INTEGER DEFAULT NULL,
                    message_id INTEGER DEFAULT NULL, channel_id INTEGER DEFAULT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    started_at TIMESTAMP DEFAULT NULL, completed_at TIMESTAMP DEFAULT NULL
                );
                CREATE TABLE IF NOT EXISTS match_channels (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    lobby_id INTEGER NOT NULL, guild_id INTEGER NOT NULL,
                    category_id INTEGER DEFAULT NULL,
                    team1_voice_id INTEGER DEFAULT NULL, team1_text_id INTEGER DEFAULT NULL,
                    team2_voice_id INTEGER DEFAULT NULL, team2_text_id INTEGER DEFAULT NULL
                );
                CREATE TABLE IF NOT EXISTS lobby_votes (
                    lobby_id INTEGER NOT NULL, user_id INTEGER NOT NULL,
                    vote TEXT NOT NULL CHECK(vote IN ('team1','team2')),
                    voted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (lobby_id, user_id)
                );
                CREATE TABLE IF NOT EXISTS vote_metadata (
                    lobby_id INTEGER PRIMARY KEY,
                    creator_id INTEGER NOT NULL, first_joiner_id INTEGER,
                    message_id INTEGER
                );
                CREATE TABLE IF NOT EXISTS match_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    lobby_id INTEGER NOT NULL,
                    winner_team TEXT NOT NULL CHECK(winner_team IN ('team1','team2')),
                    team1_score INTEGER DEFAULT 0, team2_score INTEGER DEFAULT 0,
                    mvp_id INTEGER DEFAULT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            c.commit()
        finally:
            c.close()

    def _migrate(self):
        c = self.conn()
        try:
            for table, col, col_type in [
                ("players", "win_streak", "INTEGER DEFAULT 0"),
                ("players", "lose_streak", "INTEGER DEFAULT 0"),
                ("players", "max_win_streak", "INTEGER DEFAULT 0"),
                ("players", "original_nickname", "TEXT DEFAULT NULL"),
                ("lobbies", "private_key", "TEXT DEFAULT NULL"),
                ("lobbies", "first_joiner_id", "INTEGER DEFAULT NULL"),
            ]:
                try:
                    c.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_type}")
                except sqlite3.OperationalError:
                    pass
            c.commit()
        finally:
            c.close()

    def get_guild_settings(self, gid):
        conn = self.conn()
        try:
            r = conn.execute("SELECT * FROM guild_settings WHERE guild_id=?", (gid,)).fetchone()
            return dict(r) if r else None
        finally:
            conn.close()

    def set_guild_setting(self, gid, key, val):
        if key not in GUILD_SETTINGS_COLUMNS:
            raise ValueError(f"Invalid key: {key}")
        conn = self.conn()
        try:
            conn.execute("INSERT OR IGNORE INTO guild_settings(guild_id) VALUES(?)", (gid,))
            conn.execute(f"UPDATE guild_settings SET {key}=? WHERE guild_id=?", (val, gid))
            conn.commit()
        finally:
            conn.close()

    def add_play_channel(self, gid, cid):
        conn = self.conn()
        try:
            conn.execute("INSERT INTO play_channels(guild_id,channel_id) VALUES(?,?)", (gid, cid))
            conn.commit(); return True
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()

    def remove_play_channel(self, gid, cid):
        conn = self.conn()
        try:
            cur = conn.execute("DELETE FROM play_channels WHERE guild_id=? AND channel_id=?", (gid, cid))
            conn.commit(); return cur.rowcount > 0
        finally:
            conn.close()

    def get_play_channels(self, gid):
        conn = self.conn()
        try:
            return [x["channel_id"] for x in conn.execute("SELECT channel_id FROM play_channels WHERE guild_id=?", (gid,)).fetchall()]
        finally:
            conn.close()

    def add_commands_channel(self, gid, cid):
        conn = self.conn()
        try:
            conn.execute("INSERT INTO bot_commands_channels(guild_id,channel_id) VALUES(?,?)", (gid, cid))
            conn.commit(); return True
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()

    def remove_commands_channel(self, gid, cid):
        conn = self.conn()
        try:
            cur = conn.execute("DELETE FROM bot_commands_channels WHERE guild_id=? AND channel_id=?", (gid, cid))
            conn.commit(); return cur.rowcount > 0
        finally:
            conn.close()

    def get_commands_channels(self, gid):
        conn = self.conn()
        try:
            return [x["channel_id"] for x in conn.execute("SELECT channel_id FROM bot_commands_channels WHERE guild_id=?", (gid,)).fetchall()]
        finally:
            conn.close()

    def is_bot_allowed_channel(self, gid, cid):
        if cid in self.get_commands_channels(gid):
            return True
        conn = self.conn()
        try:
            return conn.execute("SELECT 1 FROM match_channels WHERE guild_id=? AND (team1_text_id=? OR team2_text_id=?) LIMIT 1", (gid, cid, cid)).fetchone() is not None
        finally:
            conn.close()

    def add_waiting_room(self, gid, cid):
        conn = self.conn()
        try:
            conn.execute("INSERT INTO waiting_rooms(guild_id,channel_id) VALUES(?,?)", (gid, cid))
            conn.commit(); return True
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()

    def remove_waiting_room(self, gid, cid):
        conn = self.conn()
        try:
            cur = conn.execute("DELETE FROM waiting_rooms WHERE guild_id=? AND channel_id=?", (gid, cid))
            conn.commit(); return cur.rowcount > 0
        finally:
            conn.close()

    def get_waiting_rooms(self, gid):
        conn = self.conn()
        try:
            return [x["channel_id"] for x in conn.execute("SELECT channel_id FROM waiting_rooms WHERE guild_id=?", (gid,)).fetchall()]
        finally:
            conn.close()

    def get_available_waiting_room(self, gid, guild=None):
        rooms = self.get_waiting_rooms(gid)
        if not rooms:
            return None
        if guild:
            for cid in rooms:
                ch = guild.get_channel(cid)
                if ch:
                    return cid
        return rooms[0]

    def add_allowed_guild(self, gid, name, added_by):
        conn = self.conn()
        try:
            conn.execute("INSERT OR REPLACE INTO allowed_guilds(guild_id,guild_name,added_by) VALUES(?,?,?)", (gid, name, added_by))
            conn.commit()
        finally:
            conn.close()

    def remove_allowed_guild(self, gid):
        conn = self.conn()
        try:
            cur = conn.execute("DELETE FROM allowed_guilds WHERE guild_id=?", (gid,))
            conn.commit(); return cur.rowcount > 0
        finally:
            conn.close()

    def is_guild_allowed(self, gid):
        if not GUILD_WHITELIST_ENABLED:
            return True
        conn = self.conn()
        try:
            return conn.execute("SELECT 1 FROM allowed_guilds WHERE guild_id=?", (gid,)).fetchone() is not None
        finally:
            conn.close()

    def get_allowed_guilds(self):
        conn = self.conn()
        try:
            return [dict(x) for x in conn.execute("SELECT * FROM allowed_guilds ORDER BY added_at DESC").fetchall()]
        finally:
            conn.close()

    def get_or_create_player(self, uid, gid, name):
        conn = self.conn()
        try:
            r = conn.execute("SELECT * FROM players WHERE user_id=? AND guild_id=?", (uid, gid)).fetchone()
            if r:
                conn.execute("UPDATE players SET last_active=?, username=? WHERE user_id=? AND guild_id=?", (datetime.now().isoformat(), name, uid, gid))
                conn.commit()
                return dict(conn.execute("SELECT * FROM players WHERE user_id=? AND guild_id=?", (uid, gid)).fetchone())
            else:
                conn.execute("INSERT INTO players(user_id,guild_id,username,level) VALUES(?,?,?,?)", (uid, gid, name, STARTING_LEVEL))
                conn.commit()
                return dict(conn.execute("SELECT * FROM players WHERE user_id=? AND guild_id=?", (uid, gid)).fetchone())
        finally:
            conn.close()

    def get_player(self, uid, gid):
        conn = self.conn()
        try:
            r = conn.execute("SELECT * FROM players WHERE user_id=? AND guild_id=?", (uid, gid)).fetchone()
            return dict(r) if r else None
        finally:
            conn.close()

    def update_player_stats(self, uid, gid, **kw):
        ALLOWED = {"points","rank_pos","wins","losses","kills","mvps","matches_played","level","username","original_nickname","win_streak","lose_streak","max_win_streak"}
        safe = {k: v for k, v in kw.items() if k in ALLOWED}
        if not safe:
            return
        sets = ", ".join([f"{k}=?" for k in safe])
        vals = list(safe.values()) + [datetime.now().isoformat(), uid, gid]
        conn = self.conn()
        try:
            conn.execute(f"UPDATE players SET {sets}, last_active=? WHERE user_id=? AND guild_id=?", vals)
            conn.commit()
        finally:
            conn.close()

    def update_player_level(self, uid, gid, delta):
        actual_delta = -delta
        conn = self.conn()
        try:
            conn.execute("UPDATE players SET level=MAX(1,MIN(9999,level+?)), last_active=? WHERE user_id=? AND guild_id=?", (actual_delta, datetime.now().isoformat(), uid, gid))
            conn.commit()
            r = conn.execute("SELECT level FROM players WHERE user_id=? AND guild_id=?", (uid, gid)).fetchone()
            return dict(r)["level"] if r else STARTING_LEVEL
        finally:
            conn.close()

    def reset_stats(self, uid, gid):
        conn = self.conn()
        try:
            conn.execute("UPDATE players SET points=0,wins=0,losses=0,kills=0,mvps=0,matches_played=0,rank_pos=1,level=?,win_streak=0,lose_streak=0,max_win_streak=0,last_active=? WHERE user_id=? AND guild_id=?", (STARTING_LEVEL, datetime.now().isoformat(), uid, gid))
            conn.commit()
        finally:
            conn.close()

    def get_leaderboard(self, gid, limit=10):
        conn = self.conn()
        try:
            return [dict(x) for x in conn.execute("SELECT * FROM players WHERE guild_id=? ORDER BY points DESC LIMIT ?", (gid, limit)).fetchall()]
        finally:
            conn.close()

    def get_player_rank(self, points):
        return 1

    def create_lobby(self, gid, creator, chan, mode="4v4"):
        conn = self.conn()
        try:
            cur = conn.execute("INSERT INTO lobbies(guild_id,creator_id,channel_id,game_mode,team1_players) VALUES(?,?,?,?,?)", (gid, creator, chan, mode, json.dumps([creator])))
            conn.commit(); return cur.lastrowid
        finally:
            conn.close()

    def get_lobby(self, lid):
        conn = self.conn()
        try:
            r = conn.execute("SELECT * FROM lobbies WHERE id=?", (lid,)).fetchone()
            if r:
                l = dict(r)
                l["team1_players"] = json.loads(l["team1_players"])
                l["team2_players"] = json.loads(l["team2_players"])
                return l
            return None
        finally:
            conn.close()

    def get_active_lobbies(self, gid):
        conn = self.conn()
        try:
            res = []
            for r in conn.execute("SELECT * FROM lobbies WHERE guild_id=? AND status IN ('waiting','started','voting') ORDER BY created_at DESC", (gid,)).fetchall():
                l = dict(r)
                l["team1_players"] = json.loads(l["team1_players"])
                l["team2_players"] = json.loads(l["team2_players"])
                res.append(l)
            return res
        finally:
            conn.close()

    def get_player_active_lobby(self, uid, gid):
        conn = self.conn()
        try:
            for r in conn.execute("SELECT * FROM lobbies WHERE guild_id=? AND status IN ('waiting','started','voting')", (gid,)).fetchall():
                l = dict(r)
                t1 = json.loads(l["team1_players"]); t2 = json.loads(l["team2_players"])
                if uid in t1 or uid in t2:
                    l["team1_players"] = t1; l["team2_players"] = t2
                    return l
            return None
        finally:
            conn.close()

    def add_player_to_lobby(self, lid, uid, team):
        conn = self.conn()
        try:
            r = conn.execute("SELECT * FROM lobbies WHERE id=?", (lid,)).fetchone()
            if not r: return False
            l = dict(r)
            t1 = json.loads(l["team1_players"]); t2 = json.loads(l["team2_players"])
            mode = l.get("game_mode", DEFAULT_MODE)
            team_size = GAME_MODES.get(mode, GAME_MODES[DEFAULT_MODE])["team_size"]
            if team == "team1":
                if len(t1) >= team_size: return False
                if uid not in t1: t1.append(uid)
            elif team == "team2":
                if len(t2) >= team_size: return False
                if uid not in t2: t2.append(uid)
            else: return False
            conn.execute("UPDATE lobbies SET team1_players=?, team2_players=? WHERE id=?", (json.dumps(t1), json.dumps(t2), lid))
            conn.commit(); return True
        finally:
            conn.close()

    def remove_player_from_lobby(self, lid, uid):
        conn = self.conn()
        try:
            r = conn.execute("SELECT * FROM lobbies WHERE id=?", (lid,)).fetchone()
            if not r: return False
            l = dict(r)
            t1 = json.loads(l["team1_players"]); t2 = json.loads(l["team2_players"])
            removed = False
            if uid in t1: t1.remove(uid); removed = True
            if uid in t2: t2.remove(uid); removed = True
            if removed:
                conn.execute("UPDATE lobbies SET team1_players=?, team2_players=? WHERE id=?", (json.dumps(t1), json.dumps(t2), lid))
                conn.commit()
            return removed
        finally:
            conn.close()

    def update_lobby_status(self, lid, status):
        conn = self.conn()
        try:
            if status == "started":
                conn.execute("UPDATE lobbies SET status=?, started_at=? WHERE id=?", (status, datetime.now().isoformat(), lid))
            elif status in ("completed", "cancelled"):
                conn.execute("UPDATE lobbies SET status=?, completed_at=? WHERE id=?", (status, datetime.now().isoformat(), lid))
            else:
                conn.execute("UPDATE lobbies SET status=? WHERE id=?", (status, lid))
            conn.commit()
        finally:
            conn.close()

    def update_lobby_message(self, lid, mid):
        conn = self.conn()
        try:
            conn.execute("UPDATE lobbies SET message_id=? WHERE id=?", (mid, lid))
            conn.commit()
        finally:
            conn.close()

    def set_first_joiner(self, lid, uid):
        conn = self.conn()
        try:
            conn.execute("UPDATE lobbies SET first_joiner_id=? WHERE id=? AND first_joiner_id IS NULL", (uid, lid))
            conn.commit()
        finally:
            conn.close()

    def set_room_info(self, lid, room_id, room_code, private_key=None):
        conn = self.conn()
        try:
            if private_key is not None:
                conn.execute("UPDATE lobbies SET room_id=?, room_code=?, private_key=? WHERE id=?", (room_id, room_code, private_key, lid))
            else:
                conn.execute("UPDATE lobbies SET room_id=?, room_code=? WHERE id=?", (room_id, room_code, lid))
            conn.commit()
        finally:
            conn.close()

    def get_lobby_private_key(self, lid):
        conn = self.conn()
        try:
            r = conn.execute("SELECT private_key FROM lobbies WHERE id=?", (lid,)).fetchone()
            return r["private_key"] if r and r["private_key"] else None
        finally:
            conn.close()

    def reassign_creator(self, lid, new_creator_id):
        conn = self.conn()
        try:
            conn.execute("UPDATE lobbies SET creator_id=? WHERE id=?", (new_creator_id, lid))
            conn.commit()
        finally:
            conn.close()

    def save_match_channels(self, lid, gid, cat_id, t1v, t1t, t2v, t2t):
        conn = self.conn()
        try:
            conn.execute("INSERT INTO match_channels(lobby_id,guild_id,category_id,team1_voice_id,team1_text_id,team2_voice_id,team2_text_id) VALUES(?,?,?,?,?,?,?)", (lid, gid, cat_id, t1v, t1t, t2v, t2t))
            conn.commit()
        finally:
            conn.close()

    def get_match_channels(self, lid):
        conn = self.conn()
        try:
            r = conn.execute("SELECT * FROM match_channels WHERE lobby_id=?", (lid,)).fetchone()
            return dict(r) if r else None
        finally:
            conn.close()

    def delete_match_channels_record(self, lid):
        conn = self.conn()
        try:
            conn.execute("DELETE FROM match_channels WHERE lobby_id=?", (lid,))
            conn.commit()
        finally:
            conn.close()

    def get_all_active_match_channels(self, gid):
        conn = self.conn()
        try:
            return [dict(x) for x in conn.execute("SELECT mc.* FROM match_channels mc JOIN lobbies l ON mc.lobby_id=l.id WHERE mc.guild_id=? AND l.status IN ('started','voting')", (gid,)).fetchall()]
        finally:
            conn.close()

    def cast_vote(self, lid, uid, vote):
        conn = self.conn()
        try:
            conn.execute("INSERT INTO lobby_votes(lobby_id,user_id,vote) VALUES(?,?,?)", (lid, uid, vote))
            conn.commit(); return True
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()

    def get_votes(self, lid):
        conn = self.conn()
        try:
            return [dict(x) for x in conn.execute("SELECT * FROM lobby_votes WHERE lobby_id=?", (lid,)).fetchall()]
        finally:
            conn.close()

    def has_voted(self, lid, uid):
        conn = self.conn()
        try:
            return conn.execute("SELECT 1 FROM lobby_votes WHERE lobby_id=? AND user_id=?", (lid, uid)).fetchone() is not None
        finally:
            conn.close()

    def clear_votes(self, lid):
        conn = self.conn()
        try:
            conn.execute("DELETE FROM lobby_votes WHERE lobby_id=?", (lid,))
            conn.commit()
        finally:
            conn.close()

    def set_vote_message(self, lid, mid):
        conn = self.conn()
        try:
            conn.execute("UPDATE lobbies SET vote_message_id=? WHERE id=?", (mid, lid))
            conn.commit()
        finally:
            conn.close()

    def save_vote_metadata(self, lid, creator_id, first_joiner_id, message_id=None):
        conn = self.conn()
        try:
            conn.execute("INSERT OR REPLACE INTO vote_metadata(lobby_id,creator_id,first_joiner_id,message_id) VALUES(?,?,?,?)", (lid, creator_id, first_joiner_id, message_id))
            conn.commit()
        finally:
            conn.close()

    def get_vote_metadata(self, lid):
        conn = self.conn()
        try:
            r = conn.execute("SELECT * FROM vote_metadata WHERE lobby_id=?", (lid,)).fetchone()
            return dict(r) if r else None
        finally:
            conn.close()

    def get_lobby_id_by_message(self, message_id):
        conn = self.conn()
        try:
            r = conn.execute("SELECT lobby_id FROM vote_metadata WHERE message_id=?", (message_id,)).fetchone()
            return r["lobby_id"] if r else None
        finally:
            conn.close()

    def delete_vote_metadata(self, lid):
        conn = self.conn()
        try:
            conn.execute("DELETE FROM vote_metadata WHERE lobby_id=?", (lid,))
            conn.commit()
        finally:
            conn.close()

    def create_match_result(self, lid, winner, s1, s2, mvp=None):
        conn = self.conn()
        try:
            cur = conn.execute("INSERT INTO match_results(lobby_id,winner_team,team1_score,team2_score,mvp_id) VALUES(?,?,?,?,?)", (lid, winner, s1, s2, mvp))
            conn.commit(); return cur.lastrowid
        finally:
            conn.close()

    def add_points(self, uid, gid, amount):
        conn = self.conn()
        try:
            conn.execute("UPDATE players SET points=MAX(0,points+?), last_active=? WHERE user_id=? AND guild_id=?", (amount, datetime.now().isoformat(), uid, gid))
            conn.commit()
        finally:
            conn.close()


db = Database()
active_lobby_messages = {}
lobby_timeout_timers = {}
vote_timeout_timers = {}

# ============================================================
# HELPERS
# ============================================================

def extract_original_nickname(nickname):
    if not nickname:
        return "Player"
    cleaned = re.sub(r"\[Lv\.\d+\]\s*", "", nickname)
    cleaned = re.sub(r"RANK\s+\d+\s*\|\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"Rank\s+\d+\s*", "", cleaned)
    cleaned = cleaned.strip()
    return cleaned if cleaned else "Player"


def build_nickname_with_level(original_name, level):
    clean = extract_original_nickname(original_name)
    if not clean:
        clean = "Player"
    prefix = f"RANK {level} | "
    if len(prefix) >= NICKNAME_MAX_LENGTH:
        return prefix[:NICKNAME_MAX_LENGTH]
    return f"{prefix}{clean[:NICKNAME_MAX_LENGTH - len(prefix)]}"


def create_lobby_embed(lobby, guild):
    """🆕 شكل مطابق لـ Apostado — بسيط ونظيف."""
    mode = lobby.get("game_mode", DEFAULT_MODE)
    mode_info = GAME_MODES.get(mode, GAME_MODES[DEFAULT_MODE])
    team_size = mode_info["team_size"]
    lobby_size = mode_info["lobby_size"]
    mode_emoji = mode_info["emoji"]
    mode_color = mode_info["color"]

    t1c = len(lobby["team1_players"])
    t2c = len(lobby["team2_players"])

    embed = discord.Embed(
        title=f"{mode_emoji} Free Fire {mode.upper()} Match",
        description=f"Match started by <@{lobby['creator_id']}>",
        color=mode_color
    )

    t1_text = "\n".join([f"<@{pid}>" for pid in lobby["team1_players"][:team_size]]) or "Empty"
    t2_text = "\n".join([f"<@{pid}>" for pid in lobby["team2_players"][:team_size]]) or "Empty"

    embed.add_field(name=f"🔴 Team 1 ({t1c}/{team_size})", value=t1_text, inline=True)
    embed.add_field(name=f"🟢 Team 2 ({t2c}/{team_size})", value=t2_text, inline=True)

    pk = db.get_lobby_private_key(lobby['id'])
    if pk:
        embed.add_field(name="🔒 Private Match", value="Enter key to join & view info", inline=False)

    return embed


def create_profile_embed(player, member=None):
    """🆕 بطاقة لاعب — مطابقة لـ Apostado: بسيطة، سوداء، 8 حقول."""
    level = player.get("level", STARTING_LEVEL)
    wr = round((player["wins"] / max(player["matches_played"], 1)) * 100, 1)
    organize = player["wins"] - player["losses"]

    embed = discord.Embed(color=0x2B2D31)
    if member:
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.title = member.display_name
    else:
        embed.title = player["username"]
    embed.description = f"Rank #{level}"

    embed.add_field(name="POINTS", value=str(player["points"]), inline=True)
    embed.add_field(name="WINS", value=str(player["wins"]), inline=True)
    embed.add_field(name="LOSSES", value=str(player["losses"]), inline=True)
    embed.add_field(name="MVPS", value=str(player["mvps"]), inline=True)
    embed.add_field(name="MATCHES", value=str(player["matches_played"]), inline=True)
    embed.add_field(name="ORGANIZE", value=str(organize), inline=True)
    embed.add_field(name="WINRATE", value=f"{wr}%", inline=True)
    embed.add_field(name="RANK", value=f"#{level}", inline=True)

    return embed


async def update_member_nickname(member, level):
    try:
        if not member.guild.me.guild_permissions.manage_nicknames:
            return
        if member.id == member.guild.owner_id:
            return
        original_from_display = extract_original_nickname(member.display_name)
        player = db.get_or_create_player(member.id, member.guild.id, original_from_display)
        if player.get("original_nickname") and player["original_nickname"] != "Player":
            original = player["original_nickname"]
        else:
            original = original_from_display
            db.update_player_stats(member.id, member.guild.id, original_nickname=original)
        new_nick = build_nickname_with_level(original, level)
        if member.display_name != new_nick:
            old_nick = member.display_name
            try:
                await member.edit(nick=new_nick)
                logger.info(f"✅ Nickname: '{old_nick}' → '{new_nick}'")
            except discord.Forbidden:
                logger.warning(f"❌ Forbidden to change nickname for {member.id}")
            except discord.HTTPException as e:
                logger.warning(f"❌ HTTP error: {e}")
    except Exception as e:
        logger.exception(f"update_member_nickname failed: {e}")


async def update_leaderboard_channel(guild):
    try:
        settings = db.get_guild_settings(guild.id)
        if not settings or not settings.get("leaderboard_channel_id"):
            return
        channel = guild.get_channel(settings["leaderboard_channel_id"])
        if not channel:
            return
        lb = db.get_leaderboard(guild.id, 10)
        embed = discord.Embed(title="🏆 Free Fire Leaderboard — Top 10", color=0xFFD700)
        if not lb:
            embed.description = f"No players yet! Start playing with `{PREFIX}play`"
        else:
            medals = ["🥇", "🥈", "🥉"]
            desc = ""
            for i, p in enumerate(lb):
                m = medals[i] if i < 3 else f"`#{i+1}`"
                mem = guild.get_member(p["user_id"])
                name = mem.display_name if mem else p["username"]
                level = p.get("level", STARTING_LEVEL)
                wr = round((p["wins"] / max(p["matches_played"], 1)) * 100, 1)
                desc += f"{m} **{name}**\n   📊 {p['points']} pts | 🏅 RANK {level} | 🎮 {p['matches_played']}M | ✅ {p['wins']}W | ❌ {p['losses']}L | 📈 {wr}%\n\n"
            embed.description = desc
        embed.set_footer(text="Free Fire Bot v4.0 🤖")
        if settings.get("leaderboard_message_id"):
            try:
                msg = await channel.fetch_message(settings["leaderboard_message_id"])
                await msg.edit(embed=embed)
                return
            except (discord.NotFound, discord.Forbidden):
                pass
        msg = await channel.send(embed=embed)
        db.set_guild_setting(guild.id, "leaderboard_message_id", msg.id)
    except Exception as e:
        logger.exception(f"update_leaderboard_channel failed: {e}")


def cleanup_lobby_memory(lobby_id):
    to_remove = [k for k, v in active_lobby_messages.items() if v == lobby_id]
    for k in to_remove:
        del active_lobby_messages[k]
    for timer_dict in (lobby_timeout_timers, vote_timeout_timers):
        if lobby_id in timer_dict:
            try:
                timer_dict[lobby_id].cancel()
            except Exception:
                pass
            del timer_dict[lobby_id]
    try:
        db.delete_vote_metadata(lobby_id)
    except Exception:
        pass


# ============================================================
# CHANNEL CREATION
# ============================================================

async def create_match_channels(guild, lobby, lobby_id):
    """ينشئ Category جديدة + فويسات + شات عام لكل ماتش."""
    cat_name = f"🎮 Match #{lobby_id}"
    cat = await guild.create_category(cat_name, overwrites={
        guild.default_role: discord.PermissionOverwrite(read_messages=False, connect=False),
        guild.me: discord.PermissionOverwrite(read_messages=True, connect=True, manage_channels=True, manage_messages=True)
    })

    general_overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False, connect=False),
        guild.me: discord.PermissionOverwrite(read_messages=True, connect=True, manage_channels=True, manage_messages=True)
    }
    for pid in lobby["team1_players"] + lobby["team2_players"]:
        m = guild.get_member(pid)
        if m:
            general_overwrites[m] = discord.PermissionOverwrite(read_messages=True, connect=True, speak=True, stream=True, send_messages=True, view_channel=True)

    t1_overwrites = {
        guild.default_role: discord.PermissionOverwrite(connect=False),
        guild.me: discord.PermissionOverwrite(connect=True, manage_channels=True)
    }
    for pid in lobby["team1_players"]:
        m = guild.get_member(pid)
        if m:
            t1_overwrites[m] = discord.PermissionOverwrite(connect=True, speak=True, stream=True)

    t2_overwrites = {
        guild.default_role: discord.PermissionOverwrite(connect=False),
        guild.me: discord.PermissionOverwrite(connect=True, manage_channels=True)
    }
    for pid in lobby["team2_players"]:
        m = guild.get_member(pid)
        if m:
            t2_overwrites[m] = discord.PermissionOverwrite(connect=True, speak=True, stream=True)

    t1_voice = await guild.create_voice_channel("『🎮』︱ᴛᴇᴀᴍ ɪ", category=cat, overwrites=t1_overwrites)
    t2_voice = await guild.create_voice_channel("『🎮』︱ᴛᴇᴀᴍ ɪɪ", category=cat, overwrites=t2_overwrites)
    general_text = await guild.create_text_channel("💬・general-chat", category=cat, overwrites=general_overwrites)

    db.save_match_channels(lobby_id, guild.id, cat.id, t1_voice.id, general_text.id, t2_voice.id, general_text.id)
    return {"category": cat, "team1_voice": t1_voice, "team1_text": general_text, "team2_voice": t2_voice, "team2_text": general_text, "general_text": general_text}


async def delete_match_channels(guild, lobby_id):
    mc = db.get_match_channels(lobby_id)
    if not mc:
        return
    for voice_key in ["team1_voice_id", "team2_voice_id"]:
        voice_id = mc.get(voice_key)
        if voice_id:
            ch = guild.get_channel(voice_id)
            if ch:
                try: await ch.delete()
                except (discord.NotFound, discord.Forbidden): pass
    for text_key in ["team1_text_id", "team2_text_id"]:
        text_id = mc.get(text_key)
        if text_id:
            ch = guild.get_channel(text_id)
            if ch:
                try: await ch.delete()
                except (discord.NotFound, discord.Forbidden): pass
    cat_id = mc.get("category_id")
    if cat_id:
        cat = guild.get_channel(cat_id)
        if cat and isinstance(cat, discord.CategoryChannel):
            try: await cat.delete()
            except (discord.NotFound, discord.Forbidden): pass
    db.delete_match_channels_record(lobby_id)


# ============================================================
# VOTE TRIGGER
# ============================================================

async def auto_trigger_vote(lobby_id, guild):
    try:
        lobby = db.get_lobby(lobby_id)
        if not lobby or lobby["status"] != "started":
            return
        db.update_lobby_status(lobby_id, "voting")
        lobby = db.get_lobby(lobby_id)

        creator_id = lobby["creator_id"]
        first_joiner_id = lobby.get("first_joiner_id")
        mc = db.get_match_channels(lobby_id)
        if not mc:
            return

        vote_embed = discord.Embed(
            title=f"🗳️ Vote — Match #{lobby_id}",
            description=f"صوّتوا للفريق الرابح!\n\n⏱️ دقيقتين للتصويت.",
            color=COLORS["vote"]
        )
        t1m = " ".join([f"<@{p}>" for p in lobby["team1_players"]])
        t2m = " ".join([f"<@{p}>" for p in lobby["team2_players"]])
        vote_embed.add_field(name="🔴 Team 1", value=t1m, inline=True)
        vote_embed.add_field(name="🟢 Team 2", value=t2m, inline=True)

        general_text = guild.get_channel(mc["team1_text_id"])
        vote_msg_id = None
        if general_text:
            vote_msg = await general_text.send(f"🗳️ {t1m} {t2m}", embed=vote_embed, view=VoteView(lobby_id, creator_id, first_joiner_id))
            db.set_vote_message(lobby_id, vote_msg.id)
            vote_msg_id = vote_msg.id

        db.save_vote_metadata(lobby_id, creator_id, first_joiner_id, vote_msg_id)
    except Exception as e:
        logger.exception(f"auto_trigger_vote failed: {e}")


async def auto_lobby_timeout(lobby_id, guild):
    try:
        await asyncio.sleep(LOBBY_TIMEOUT_SECONDS)
        lobby = db.get_lobby(lobby_id)
        if not lobby or lobby["status"] != "waiting":
            return
        db.update_lobby_status(lobby_id, "cancelled")
        cleanup_lobby_memory(lobby_id)
        ch = guild.get_channel(lobby["channel_id"])
        if ch:
            await ch.send(embed=discord.Embed(title="⏰ Lobby Cancelled", description=f"Lobby #{lobby_id} cancelled (timeout).", color=COLORS["warning"]))
    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.exception(f"auto_lobby_timeout failed: {e}")


# ============================================================
# PROCESS MATCH RESULT
# ============================================================

async def process_match_result(guild, lobby_id, winner_team, channel=None):
    try:
        logger.info(f"🏆 process_match_result — lobby={lobby_id}, winner={winner_team}")
        lobby = db.get_lobby(lobby_id)
        if not lobby:
            return
        if lobby["status"] == "completed":
            logger.warning(f"Already completed: {lobby_id}")
            return

        db.update_lobby_status(lobby_id, "completed")
        db.create_match_result(lobby_id, winner_team,
            len(lobby["team1_players"]) if winner_team == "team1" else 0,
            len(lobby["team2_players"]) if winner_team == "team2" else 0)

        game_mode = lobby.get("game_mode", DEFAULT_MODE)
        mode_points = MATCH_POINTS_BY_MODE.get(game_mode, MATCH_POINTS_BY_MODE["4v4"])
        wp = mode_points["win"]
        lp = mode_points["lose"]
        wt = lobby["team1_players"] if winner_team == "team1" else lobby["team2_players"]
        lt = lobby["team2_players"] if winner_team == "team1" else lobby["team1_players"]

        for pid in wt:
            p = db.get_player(pid, guild.id)
            if p:
                new_win_streak = p.get("win_streak", 0) + 1
                streak_bonus = STREAK_BONUS.get(new_win_streak, 50 if new_win_streak >= 10 else 0)
                total_points = wp + streak_bonus
                new_points = p["points"] + total_points
                new_max = max(p.get("max_win_streak", 0), new_win_streak)
                db.update_player_stats(pid, guild.id, points=new_points, wins=p["wins"]+1, matches_played=p["matches_played"]+1, win_streak=new_win_streak, lose_streak=0, max_win_streak=new_max)
                rank_change = 3 if new_win_streak >= 5 else (2 if new_win_streak >= 3 else 1)
                new_level = p["level"]
                for _ in range(rank_change):
                    new_level = db.update_player_level(pid, guild.id, +1)
                m = guild.get_member(pid)
                if m:
                    await update_member_nickname(m, new_level)

        for pid in lt:
            p = db.get_player(pid, guild.id)
            if p:
                new_lose_streak = p.get("lose_streak", 0) + 1
                new_points = p["points"] + lp
                db.update_player_stats(pid, guild.id, points=new_points, losses=p["losses"]+1, matches_played=p["matches_played"]+1, win_streak=0, lose_streak=new_lose_streak)
                rank_change = 2 if new_lose_streak >= 3 else 1
                new_level = p["level"]
                for _ in range(rank_change):
                    new_level = db.update_player_level(pid, guild.id, -1)
                m = guild.get_member(pid)
                if m:
                    await update_member_nickname(m, new_level)

        wd = "🔴 Team 1" if winner_team == "team1" else "🟢 Team 2"
        embed = discord.Embed(title=f"🏆 Match Result — #{lobby_id}", description=f"**{wd} wins!** 🎉", color=COLORS["success"])
        if channel:
            await channel.send(embed=embed)

        await update_leaderboard_channel(guild)

        # 🆕 أعد اللاعبين لغرف الانتظار
        all_players = lobby["team1_players"] + lobby["team2_players"]
        for pid in all_players:
            m = guild.get_member(pid)
            if m and m.voice:
                waiting_cid = db.get_available_waiting_room(guild.id, guild)
                if waiting_cid:
                    vc = guild.get_channel(waiting_cid)
                    if vc:
                        try: await m.move_to(vc)
                        except (discord.HTTPException, discord.Forbidden): pass

        await asyncio.sleep(5)
        await delete_match_channels(guild, lobby_id)
        cleanup_lobby_memory(lobby_id)
    except Exception as e:
        logger.exception(f"process_match_result failed: {e}")

# ============================================================
# VIEWS
# ============================================================

class RoomInfoModal(discord.ui.Modal, title="📋 Enter Room Information"):
    room_id_input = discord.ui.TextInput(label="Room ID (Numbers Only)", placeholder="Enter room ID", required=True, min_length=3, max_length=20)
    password_input = discord.ui.TextInput(label="Password (Optional)", placeholder="Enter password if any", required=False, max_length=20)
    private_key_input = discord.ui.TextInput(label="Private Match Key (Optional)", placeholder="If set, players must enter it to join", required=False, max_length=20)

    def __init__(self, lobby_id, guild_id):
        super().__init__(timeout=300)
        self.lobby_id = lobby_id
        self.guild_id = guild_id

    async def on_submit(self, interaction):
        try:
            room_id = str(self.room_id_input.value).strip()
            password = str(self.password_input.value).strip() if self.password_input.value else ""
            private_key = str(self.private_key_input.value).strip() if self.private_key_input.value else ""
            lobby = db.get_lobby(self.lobby_id)
            if not lobby or lobby["status"] != "started":
                await interaction.response.send_message("❌ Match not active!", ephemeral=True)
                return
            if lobby["creator_id"] != interaction.user.id:
                await interaction.response.send_message("❌ Only the host!", ephemeral=True)
                return
            db.set_room_info(self.lobby_id, room_id, password, private_key if private_key else None)
            await interaction.response.send_message(
                embed=discord.Embed(title="✅ Room Info Saved!", description=f"ID: `{room_id}` | Code: `{password or 'N/A'}`" + (f"\n🔒 Key: `{private_key}`" if private_key else ""), color=COLORS["success"]),
                ephemeral=True
            )
        except Exception as e:
            logger.exception(f"RoomInfoModal failed: {e}")


class JoinKeyModal(discord.ui.Modal, title="🔑 Enter Private Match Key"):
    key_input = discord.ui.TextInput(label="Private Match Key", placeholder="Enter the key", required=True, min_length=1, max_length=20)

    def __init__(self, lobby_id, guild_id, creator_id, team, private_key, view):
        super().__init__(timeout=120)
        self.lobby_id = lobby_id
        self.guild_id = guild_id
        self.creator_id = creator_id
        self.team = team
        self.private_key = private_key
        self.view_ref = view

    async def on_submit(self, interaction):
        try:
            entered = str(self.key_input.value).strip()
            if entered == self.private_key:
                await self.view_ref._complete_join(interaction, self.team)
            else:
                await interaction.response.send_message(embed=discord.Embed(title="❌ Wrong Key", description="Incorrect key!", color=COLORS["error"]), ephemeral=True)
        except Exception as e:
            logger.exception(f"JoinKeyModal failed: {e}")


class LobbyButtonsView(discord.ui.View):
    def __init__(self, lobby_id, creator_id, guild_id):
        super().__init__(timeout=None)
        self.lobby_id = lobby_id
        self.creator_id = creator_id
        self.guild_id = guild_id

    @discord.ui.button(label="Join Team 1", style=discord.ButtonStyle.danger, custom_id="join_team1_btn")
    async def join_team1_btn(self, interaction, button):
        await self._handle_join(interaction, "team1")

    @discord.ui.button(label="Join Team 2", style=discord.ButtonStyle.success, custom_id="join_team2_btn")
    async def join_team2_btn(self, interaction, button):
        await self._handle_join(interaction, "team2")

    @discord.ui.button(label="Leave", style=discord.ButtonStyle.secondary, custom_id="leave_lobby_btn")
    async def leave_lobby_btn(self, interaction, button):
        uid = interaction.user.id
        if db.remove_player_from_lobby(self.lobby_id, uid):
            lobby = db.get_lobby(self.lobby_id)
            if lobby:
                try: await interaction.message.edit(embed=create_lobby_embed(lobby, interaction.guild), view=self)
                except discord.HTTPException: pass
            await interaction.response.send_message(f"✅ Left lobby #{self.lobby_id}", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Not in this lobby!", ephemeral=True)

    @discord.ui.button(label="Cancel Game", style=discord.ButtonStyle.danger, custom_id="cancel_game_btn")
    async def cancel_game_btn(self, interaction, button):
        uid = interaction.user.id
        lobby = db.get_lobby(self.lobby_id)
        if not lobby:
            await interaction.response.send_message("❌ Lobby not found!", ephemeral=True)
            return
        creator_id = self.creator_id or lobby["creator_id"]
        if uid != creator_id and not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(f"❌ Only the host! Host: <@{creator_id}>", ephemeral=True)
            return
        db.update_lobby_status(self.lobby_id, "cancelled")
        cleanup_lobby_memory(self.lobby_id)
        await delete_match_channels(interaction.guild, self.lobby_id)
        mode = lobby.get("game_mode", DEFAULT_MODE).upper()
        try: await interaction.message.edit(embed=discord.Embed(title="❌ Match Cancelled", description=f"{mode} match was cancelled by the host.\nUse `{PREFIX}play` to start a new match.", color=COLORS["error"]), view=None)
        except discord.HTTPException: pass
        await interaction.response.send_message("✅ Match cancelled.", ephemeral=True)

    async def _handle_join(self, interaction, team):
        uid = interaction.user.id
        lobby = db.get_lobby(self.lobby_id)
        if not lobby or lobby["status"] != "waiting":
            await interaction.response.send_message("❌ Lobby not active!", ephemeral=True)
            return

        member = interaction.guild.get_member(uid)
        if not member or not member.voice or not member.voice.channel:
            waiting_rooms = db.get_waiting_rooms(interaction.guild.id)
            available = []
            for wr_id in waiting_rooms:
                wr = interaction.guild.get_channel(wr_id)
                if wr and wr.permissions_for(member).connect:
                    available.append(wr.mention)
            rooms_text = "\n".join([f"• {r}" for r in available[:10]]) if available else "• None available"
            await interaction.response.send_message(embed=discord.Embed(title="⏳ Must be in a waiting room", description=f"🔊 Available:\n{rooms_text}", color=COLORS["warning"]), ephemeral=True)
            return
        else:
            waiting_rooms = db.get_waiting_rooms(interaction.guild.id)
            if member.voice.channel.id not in waiting_rooms:
                available = []
                for wr_id in waiting_rooms:
                    wr = interaction.guild.get_channel(wr_id)
                    if wr and wr.permissions_for(member).connect:
                        available.append(wr.mention)
                rooms_text = "\n".join([f"• {r}" for r in available[:10]]) if available else "• None"
                await interaction.response.send_message(embed=discord.Embed(title="⏳ Must be in a waiting room", description=f"You're in `{member.voice.channel.name}` — not a waiting room!\n🔊 Available:\n{rooms_text}", color=COLORS["warning"]), ephemeral=True)
                return

        existing = db.get_player_active_lobby(uid, interaction.guild.id)
        if existing and existing["id"] != self.lobby_id:
            if existing["status"] == "started" and not existing.get("room_id"):
                await interaction.response.send_message(embed=discord.Embed(title="⏳ Pending Match", description="You have a pending match. Finish it first.", color=COLORS["warning"]), ephemeral=True)
                return
            await interaction.response.send_message(f"❌ Already in lobby #{existing['id']}! Leave first.", ephemeral=True)
            return

        pk = db.get_lobby_private_key(self.lobby_id)
        if pk:
            await interaction.response.send_modal(JoinKeyModal(self.lobby_id, self.guild_id, self.creator_id, team, pk, self))
            return

        await self._complete_join(interaction, team)

    async def _complete_join(self, interaction, team):
        uid = interaction.user.id
        lobby = db.get_lobby(self.lobby_id)
        if not lobby:
            try: await interaction.response.send_message("❌ Lobby gone!", ephemeral=True)
            except: pass
            return

        mode = lobby.get("game_mode", DEFAULT_MODE)
        team_size = GAME_MODES.get(mode, GAME_MODES[DEFAULT_MODE])["team_size"]
        target = lobby["team1_players"] if team == "team1" else lobby["team2_players"]
        if len(target) >= team_size:
            await interaction.response.send_message(f"❌ Team full! ({len(target)}/{team_size})", ephemeral=True)
            return

        if uid in (lobby["team2_players"] if team == "team1" else lobby["team1_players"]):
            db.remove_player_from_lobby(self.lobby_id, uid)
        db.add_player_to_lobby(self.lobby_id, uid, team)
        if uid != lobby["creator_id"]:
            db.set_first_joiner(self.lobby_id, uid)

        lobby = db.get_lobby(self.lobby_id)
        try: await interaction.message.edit(embed=create_lobby_embed(lobby, interaction.guild), view=self)
        except discord.HTTPException: pass

        team_name = "Team 1" if team == "team1" else "Team 2"
        await interaction.response.send_message(f"✅ Joined **{team_name}**!", ephemeral=True)

        if lobby.get("room_id"):
            room_embed = discord.Embed(title="📡 Room Info", description=f"**Room ID:** `{lobby['room_id']}`\n**Password:** `{lobby.get('room_code') or 'N/A'}`\n\nJoin now! 🔥", color=COLORS["auto"])
            await interaction.followup.send(embed=room_embed, ephemeral=True)

        waiting_cid = db.get_available_waiting_room(interaction.guild.id, interaction.guild)
        if waiting_cid:
            vc = interaction.guild.get_channel(waiting_cid)
            member = interaction.guild.get_member(uid)
            if vc and member and member.voice:
                try: await member.move_to(vc)
                except: pass

        player = db.get_or_create_player(uid, interaction.guild.id, interaction.user.display_name)
        member = interaction.guild.get_member(uid)
        if member:
            await update_member_nickname(member, player.get("level", STARTING_LEVEL))

        # AUTO-START
        mode_info = GAME_MODES.get(mode, GAME_MODES[DEFAULT_MODE])
        t1c = len(lobby["team1_players"])
        t2c = len(lobby["team2_players"])
        total = t1c + t2c
        if total >= mode_info["lobby_size"] and t1c >= mode_info["team_size"] and t2c >= mode_info["team_size"] and lobby["status"] == "waiting":
            if self.lobby_id in lobby_timeout_timers:
                lobby_timeout_timers[self.lobby_id].cancel()
            db.update_lobby_status(self.lobby_id, "started")
            lobby = db.get_lobby(self.lobby_id)

            for item in self.children:
                item.disabled = True
            try: await interaction.message.edit(view=self)
            except: pass

            try:
                channels = await create_match_channels(interaction.guild, lobby, self.lobby_id)
            except Exception as e:
                logger.exception(f"create_match_channels failed: {e}")
                channels = None

            if not channels:
                db.update_lobby_status(self.lobby_id, "cancelled")
                cleanup_lobby_memory(self.lobby_id)
                await interaction.channel.send(embed=discord.Embed(title="❌ Failed to start", description=f"Could not create channels. Lobby #{self.lobby_id} cancelled.", color=COLORS["error"]))
                return

            t1m = " ".join([f"<@{p}>" for p in lobby["team1_players"]])
            t2m = " ".join([f"<@{p}>" for p in lobby["team2_players"]])

            await interaction.channel.send(embed=discord.Embed(title="✅ Match Ready!", description="Moving players to voice channels...", color=COLORS["success"], timestamp=discord.utils.utcnow()))

            if channels:
                for pid in lobby["team1_players"]:
                    m = interaction.guild.get_member(pid)
                    if m and m.voice:
                        try: await m.move_to(channels["team1_voice"])
                        except: pass
                for pid in lobby["team2_players"]:
                    m = interaction.guild.get_member(pid)
                    if m and m.voice:
                        try: await m.move_to(channels["team2_voice"])
                        except: pass

                if lobby.get("room_id"):
                    all_players = lobby["team1_players"] + lobby["team2_players"]
                    mentions = " ".join([f"<@{pid}>" for pid in all_players])
                    room_embed = discord.Embed(title="📡 Room Info", description=f"**Room ID:** `{lobby['room_id']}`\n**Password:** `{lobby.get('room_code') or 'N/A'}`\n\nJoin now! 🔥", color=COLORS["auto"])
                    try: await channels["team1_text"].send(mentions, embed=room_embed)
                    except: pass

                start_vote_view = StartVoteView(self.lobby_id, interaction.guild.id, lobby["creator_id"])
                start_embed = discord.Embed(title="🎮 Match Started!", description=f"Lobby #{self.lobby_id} — {mode.upper()}\n\n👑 Host: press **Start Vote** when done.", color=COLORS["auto"])
                try: await channels["team1_text"].send(embed=start_embed, view=start_vote_view)
                except: pass


class StartVoteView(discord.ui.View):
    def __init__(self, lobby_id, guild_id, creator_id):
        super().__init__(timeout=None)
        self.lobby_id = lobby_id
        self.guild_id = guild_id
        self.creator_id = creator_id

    @discord.ui.button(label="🗳️ Start Vote", style=discord.ButtonStyle.success, custom_id="start_vote_btn")
    async def start_vote_btn(self, interaction, button):
        if interaction.user.id != self.creator_id:
            await interaction.response.send_message(f"❌ Only host! Host: <@{self.creator_id}>", ephemeral=True)
            return
        guild = bot.get_guild(self.guild_id)
        if guild:
            await interaction.response.send_message("✅ Vote started!", ephemeral=True)
            for item in self.children:
                item.disabled = True
            try: await interaction.message.edit(view=self)
            except: pass
            logger.info(f"🗳️ Vote started by creator for lobby {self.lobby_id}")
            asyncio.create_task(auto_trigger_vote(self.lobby_id, guild))


class VoteView(discord.ui.View):
    def __init__(self, lobby_id=None, creator_id=None, first_joiner_id=None):
        super().__init__(timeout=VOTE_TIMEOUT_SECONDS)
        self.lobby_id = lobby_id
        self.creator_id = creator_id
        self.first_joiner_id = first_joiner_id

    async def on_timeout(self):
        if not self.lobby_id:
            return
        lobby = db.get_lobby(self.lobby_id)
        if not lobby or lobby["status"] != "voting":
            return
        votes = db.get_votes(self.lobby_id)
        guild = bot.get_guild(lobby["guild_id"])
        if not guild:
            return
        mc = db.get_match_channels(self.lobby_id)
        result_ch = guild.get_channel(mc["team1_text_id"]) if mc else guild.get_channel(lobby["channel_id"])

        if not votes:
            if result_ch:
                await result_ch.send(embed=discord.Embed(title="⏰ Vote Timeout", description=f"No votes! Admin: `{PREFIX}resolve {self.lobby_id} team1|team2`", color=COLORS["warning"]))
            return

        t1v = sum(1 for v in votes if v["vote"] == "team1")
        t2v = sum(1 for v in votes if v["vote"] == "team2")
        if t1v > t2v:
            winner = "team1"
        elif t2v > t1v:
            winner = "team2"
        else:
            if result_ch:
                await result_ch.send(embed=discord.Embed(title="⏰ Tie!", description=f"Tie ({t1v}-{t2v})! Admin: `{PREFIX}resolve {self.lobby_id} team1|team2`", color=COLORS["warning"]))
            return

        wd = "🔴 Team 1" if winner == "team1" else "🟢 Team 2"
        if result_ch:
            await result_ch.send(embed=discord.Embed(title="⏰ Vote Ended!", description=f"Result: **{wd}** ({t1v}-{t2v})\n🏆 Calculating...", color=COLORS["success"]))
        await process_match_result(guild, self.lobby_id, winner, result_ch)

    @discord.ui.button(label="🟠 Team 1", style=discord.ButtonStyle.danger, custom_id="vote_team1")
    async def vote_team1(self, interaction, button):
        await self._handle_vote(interaction, "team1")

    @discord.ui.button(label="🟢 Team 2", style=discord.ButtonStyle.success, custom_id="vote_team2")
    async def vote_team2(self, interaction, button):
        await self._handle_vote(interaction, "team2")

    async def _handle_vote(self, interaction, vote_choice):
        uid = interaction.user.id
        lobby_id = self.lobby_id
        if lobby_id is None and interaction.message:
            lobby_id = db.get_lobby_id_by_message(interaction.message.id)
        if lobby_id is None:
            await interaction.response.send_message("❌ Cannot determine lobby!", ephemeral=True)
            return

        lobby = db.get_lobby(lobby_id)
        if not lobby or lobby["status"] != "voting":
            await interaction.response.send_message("❌ Vote not active!", ephemeral=True)
            return

        all_players = lobby["team1_players"] + lobby["team2_players"]
        if uid not in all_players:
            await interaction.response.send_message("❌ Not in this match!", ephemeral=True)
            return

        if db.has_voted(lobby_id, uid):
            await interaction.response.send_message("❌ Already voted!", ephemeral=True)
            return

        db.cast_vote(lobby_id, uid, vote_choice)
        wd = "🟠 Team 1" if vote_choice == "team1" else "🟢 Team 2"
        await interaction.response.send_message(f"✅ Voted **{wd}**!", ephemeral=True)

        votes = db.get_votes(lobby_id)
        total_voters = len(all_players)
        votes_count = len(votes)
        t1v = sum(1 for v in votes if v["vote"] == "team1")
        t2v = sum(1 for v in votes if v["vote"] == "team2")
        await interaction.channel.send(embed=discord.Embed(description=f"🗳️ **Vote:** 🟠 {t1v} — 🟢 {t2v} | {votes_count}/{total_voters}", color=COLORS["vote"]))

        if votes_count >= total_voters:
            if lobby_id in vote_timeout_timers:
                vote_timeout_timers[lobby_id].cancel()
            if t1v > t2v:
                winner = "team1"
            elif t2v > t1v:
                winner = "team2"
            else:
                await interaction.channel.send(embed=discord.Embed(title="⏰ Tie!", description=f"Tie ({t1v}-{t2v})! Admin: `{PREFIX}resolve {lobby_id} team1|team2`", color=COLORS["warning"]))
                return

            wd = "🟠 Team 1" if winner == "team1" else "🟢 Team 2"
            await interaction.channel.send(embed=discord.Embed(title="✅ Vote Complete!", description=f"All voted! Winner: **{wd}** ({t1v}-{t2v}) 🎉", color=COLORS["success"]))
            mc = db.get_match_channels(lobby_id)
            result_ch = interaction.guild.get_channel(mc["team1_text_id"]) if mc else interaction.channel
            await process_match_result(interaction.guild, lobby_id, winner, result_ch)
            for item in self.children:
                item.disabled = True
            try: await interaction.message.edit(view=self)
            except: pass


class CreateLobbyView(discord.ui.View):
    def __init__(self, ctx, mode):
        super().__init__(timeout=300)
        self.ctx = ctx
        self.mode = mode

    @discord.ui.button(label="📋 Create Lobby", style=discord.ButtonStyle.success, custom_id="create_lobby_btn")
    async def create_lobby_btn(self, interaction, button):
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("❌ Not your command!", ephemeral=True)
            return
        await interaction.response.send_modal(LobbyCreateModal(self.ctx, self.mode))
        for item in self.children:
            item.disabled = True
        try: await interaction.message.edit(view=self)
        except: pass


class LobbyCreateModal(discord.ui.Modal, title="🎮 Create Lobby — Enter Room Info"):
    room_id_input = discord.ui.TextInput(label="Room ID (Numbers Only)", placeholder="Enter room ID", required=True, min_length=3, max_length=20)
    password_input = discord.ui.TextInput(label="Password (Optional)", placeholder="Enter password if any", required=False, max_length=20)
    private_key_input = discord.ui.TextInput(label="Private Match Key (Optional)", placeholder="If set, players must enter it to join", required=False, max_length=20)

    def __init__(self, ctx, mode):
        super().__init__(timeout=300)
        self.ctx = ctx
        self.mode = mode

    async def on_submit(self, interaction):
        try:
            room_id = str(self.room_id_input.value).strip()
            password = str(self.password_input.value).strip() if self.password_input.value else ""
            private_key = str(self.private_key_input.value).strip() if self.private_key_input.value else ""
            guild = self.ctx.guild
            user = self.ctx.author
            lid = db.create_lobby(guild.id, user.id, self.ctx.channel.id, mode=self.mode)
            db.set_room_info(lid, room_id, password, private_key if private_key else None)
            db.add_player_to_lobby(lid, user.id, "team1")
            lobby = db.get_lobby(lid)
            embed = create_lobby_embed(lobby, guild)
            view = LobbyButtonsView(lid, user.id, guild.id)
            msg = await self.ctx.send(embed=embed, view=view)
            db.update_lobby_message(lid, msg.id)
            active_lobby_messages[msg.id] = lid
            db.get_or_create_player(user.id, guild.id, user.display_name)
            lobby_timeout_timers[lid] = asyncio.create_task(auto_lobby_timeout(lid, guild))
            await interaction.response.send_message(
                embed=discord.Embed(title="✅ Lobby Created!", description=f"Lobby #{lid}!\n💡 Players press Join Team 1/2." + (f"\n🔒 Private Key required to join." if private_key else ""), color=COLORS["success"]),
                ephemeral=True
            )
        except Exception as e:
            logger.exception(f"LobbyCreateModal failed: {e}")


class RematchView(discord.ui.View):
    def __init__(self, lobby_id, game_mode, guild_id, original_players):
        super().__init__(timeout=120)
        self.lobby_id = lobby_id
        self.game_mode = game_mode or DEFAULT_MODE
        self.guild_id = guild_id
        self.original_players = original_players or []
        self.accepted = set()

    @discord.ui.button(label="🔄 Rematch", style=discord.ButtonStyle.success, custom_id="rematch_btn")
    async def rematch_btn(self, interaction, button):
        uid = interaction.user.id
        if uid not in self.original_players:
            await interaction.response.send_message("❌ Not in this match!", ephemeral=True)
            return
        self.accepted.add(uid)
        await interaction.response.send_message(f"✅ <@{uid}> accepted! ({len(self.accepted)}/{len(self.original_players)})", ephemeral=False)
        if len(self.accepted) >= len(self.original_players) // 2 + 1:
            guild = interaction.guild
            mode_info = GAME_MODES.get(self.game_mode, GAME_MODES[DEFAULT_MODE])
            play_channels = db.get_play_channels(guild.id)
            stable_channel_id = play_channels[0] if play_channels else interaction.channel.id
            lid = db.create_lobby(guild.id, self.original_players[0], stable_channel_id, mode=self.game_mode)
            for i, pid in enumerate(self.original_players):
                if i == 0: continue
                team = "team1" if i < len(self.original_players) // 2 else "team2"
                db.add_player_to_lobby(lid, pid, team)
            lobby = db.get_lobby(lid)
            target_channel = guild.get_channel(stable_channel_id) or interaction.channel
            embed = create_lobby_embed(lobby, guild)
            view = LobbyButtonsView(lid, self.original_players[0], guild.id)
            msg = await target_channel.send(embed=embed, view=view)
            db.update_lobby_message(lid, msg.id)
            active_lobby_messages[msg.id] = lid
            lobby_timeout_timers[lid] = asyncio.create_task(auto_lobby_timeout(lid, guild))
            for item in self.children:
                item.disabled = True
            try: await interaction.message.edit(view=self)
            except: pass


# ============================================================
# BOT SETUP
# ============================================================
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.voice_states = True
intents.reactions = True
intents.dm_messages = True

bot = commands.Bot(command_prefix=PREFIX, intents=intents, help_command=None)


def is_admin_check(ctx):
    return ctx.author.guild_permissions.administrator

def is_bot_owner_check(ctx):
    return ctx.author.id == BOT_OWNER_ID

def is_bot_owner_or_admin_check(ctx):
    return ctx.author.id == BOT_OWNER_ID or ctx.author.guild_permissions.administrator


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send(embed=discord.Embed(title="⏳ Cooldown", description=f"Wait {error.retry_after:.1f}s", color=COLORS["warning"]))
    elif isinstance(error, commands.CheckFailure):
        await ctx.send(embed=discord.Embed(title="❌ No permission", color=COLORS["error"]))
    elif isinstance(error, commands.CommandNotFound):
        pass
    else:
        logger.exception(f"Command error: {error}")


@bot.event
async def on_ready():
    logger.info(f"✅ {bot.user} online!")
    logger.info(f"📌 Prefix: {PREFIX}")
    logger.info(f"👑 Owner: {BOT_OWNER_NAME}")
    logger.info(f"🏠 Servers: {len(bot.guilds)}")
    bot.add_view(VoteView())
    bot.add_view(RematchView())
    bot.add_view(LobbyButtonsView(0, 0, 0))
    bot.add_view(StartVoteView(0, 0, 0))
    bot.add_view(CreateLobbyView(None, DEFAULT_MODE))
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=f"Free Fire | {PREFIX}play"))
    if GUILD_WHITELIST_ENABLED:
        for guild in bot.guilds:
            if not db.is_guild_allowed(guild.id):
                logger.warning(f"🚫 Leaving unauthorized guild: {guild.name}")
                try: await guild.leave()
                except: pass


@bot.event
async def on_guild_join(guild):
    logger.info(f"🏠 Added to: {guild.name}")
    if GUILD_WHITELIST_ENABLED and not db.is_guild_allowed(guild.id):
        try:
            first_ch = guild.text_channels[0] if guild.text_channels else None
            if first_ch:
                await first_ch.send(embed=discord.Embed(title="🚫 Not authorized", description=f"This bot is private. Contact {BOT_OWNER_NAME}.", color=COLORS["error"]))
            await asyncio.sleep(2)
            await guild.leave()
        except: pass


@bot.event
async def on_member_join(member):
    if member.bot:
        return
    await asyncio.sleep(2)
    player = db.get_or_create_player(member.id, member.guild.id, member.display_name)
    await update_member_nickname(member, player.get("level", STARTING_LEVEL))


@bot.event
async def on_message(message):
    if message.author.bot:
        return
    if isinstance(message.channel, discord.DMChannel):
        await bot.process_commands(message)
        return
    if not message.guild:
        return
    if not db.is_bot_allowed_channel(message.guild.id, message.channel.id):
        is_admin = False
        member = message.guild.get_member(message.author.id)
        if member and member.guild_permissions.administrator:
            is_admin = True
        content_stripped = message.content.strip()
        command_name = content_stripped.split()[0] if content_stripped.split() else ""
        allowed_anywhere = [f"{PREFIX}general", f"{PREFIX}help", f"{PREFIX}fixrank", f"{PREFIX}myrank", f"{PREFIX}mylevel", f"{PREFIX}p", f"{PREFIX}setup", f"{PREFIX}botinfo", f"{PREFIX}cleanup", f"{PREFIX}fixrankall", f"{PREFIX}setcommandschannel", f"{PREFIX}allowguild", f"{PREFIX}removeguild", f"{PREFIX}listguilds", f"{PREFIX}leaveserver", f"{PREFIX}card", f"{PREFIX}scan", f"{PREFIX}deletecat", f"{PREFIX}delcat", f"{PREFIX}confirmcat"]
        is_allowed = command_name in allowed_anywhere
        if content_stripped.startswith(PREFIX):
            if is_admin or is_allowed:
                await bot.process_commands(message)
                return
            try:
                await message.reply(embed=discord.Embed(title="❌ Not allowed here", description=f"Use in: apostada-play, highlight-play, zelika-play\n💡 `{PREFIX}general` for help", color=COLORS["error"]), delete_after=10)
            except: pass
        return
    await bot.process_commands(message)

# ============================================================
# PLAYER COMMANDS
# ============================================================

async def create_mode_lobby(ctx, mode):
    guild = ctx.guild
    user = ctx.author
    if not db.is_bot_allowed_channel(guild.id, ctx.channel.id):
        await ctx.send(embed=discord.Embed(title="❌ Not allowed here", description=f"Use in: apostada-play, highlight-play, zelika-play", color=COLORS["error"]), delete_after=15)
        return
    member = guild.get_member(user.id)
    if not member or not member.voice or not member.voice.channel:
        waiting_rooms = db.get_waiting_rooms(guild.id)
        available = [guild.get_channel(wr).mention for wr in waiting_rooms if guild.get_channel(wr) and guild.get_channel(wr).permissions_for(member).connect]
        rooms_text = "\n".join([f"• {r}" for r in available[:10]]) if available else "• None"
        await ctx.send(embed=discord.Embed(title="⏳ Must be in waiting room", description=f"🔊 Available:\n{rooms_text}", color=COLORS["warning"]), delete_after=20)
        return
    else:
        waiting_rooms = db.get_waiting_rooms(guild.id)
        if member.voice.channel.id not in waiting_rooms:
            available = [guild.get_channel(wr).mention for wr in waiting_rooms if guild.get_channel(wr) and guild.get_channel(wr).permissions_for(member).connect]
            rooms_text = "\n".join([f"• {r}" for r in available[:10]]) if available else "• None"
            await ctx.send(embed=discord.Embed(title="⏳ Must be in waiting room", description=f"You're in `{member.voice.channel.name}`\n🔊 Available:\n{rooms_text}", color=COLORS["warning"]), delete_after=20)
            return
    existing = db.get_player_active_lobby(user.id, guild.id)
    if existing:
        await ctx.send(embed=discord.Embed(title="❌ Already in lobby", description=f"Leave first: `{PREFIX}leave`", color=COLORS["error"]), delete_after=10)
        return
    create_view = CreateLobbyView(ctx, mode)
    await ctx.send(embed=discord.Embed(title=f"🎮 Create {mode.upper()} Lobby", description="Press the button to enter Room Info and create the lobby.\n\n💡 You'll need:\n• Room ID (numbers)\n• Password (optional)\n• Private Key (optional)", color=COLORS["info"]), view=create_view)


@bot.command(name="play")
@commands.cooldown(1, 30, commands.BucketType.user)
async def play_cmd(ctx):
    await create_mode_lobby(ctx, "4v4")

@bot.command(name="play1v1")
@commands.cooldown(1, 30, commands.BucketType.user)
async def play1v1_cmd(ctx):
    await create_mode_lobby(ctx, "1v1")

@bot.command(name="play2v2")
@commands.cooldown(1, 30, commands.BucketType.user)
async def play2v2_cmd(ctx):
    await create_mode_lobby(ctx, "2v2")

@bot.command(name="play3v3")
@commands.cooldown(1, 30, commands.BucketType.user)
async def play3v3_cmd(ctx):
    await create_mode_lobby(ctx, "3v3")

@bot.command(name="play4v4")
@commands.cooldown(1, 30, commands.BucketType.user)
async def play4v4_cmd(ctx):
    await create_mode_lobby(ctx, "4v4")


@bot.command(name="p")
@commands.cooldown(1, 5, commands.BucketType.user)
async def profile_cmd(ctx, member: discord.Member = None):
    target = member or ctx.author
    player = db.get_or_create_player(target.id, ctx.guild.id, target.display_name)
    await update_member_nickname(target, player.get("level", STARTING_LEVEL))
    await ctx.send(embed=create_profile_embed(player, target))


@bot.command(name="card")
@commands.cooldown(1, 5, commands.BucketType.user)
async def card_cmd(ctx, member: discord.Member = None):
    """🃏 !!card — بطاقة اللاب (zelika-play فقط)"""
    channel_name = ctx.channel.name.lower() if ctx.channel.name else ""
    if "zelika" not in channel_name:
        await ctx.send(embed=discord.Embed(title="❌ Not allowed here", description=f"This command works only in `zelika-play`\n💡 Use `{PREFIX}p` elsewhere.", color=COLORS["error"]), delete_after=10)
        return
    target = member or ctx.author
    player = db.get_or_create_player(target.id, ctx.guild.id, target.display_name)
    await update_member_nickname(target, player.get("level", STARTING_LEVEL))
    await ctx.send(embed=create_profile_embed(player, target))


@bot.command(name="top")
@commands.cooldown(1, 10, commands.BucketType.user)
async def top_cmd(ctx):
    lb = db.get_leaderboard(ctx.guild.id, 10)
    if not lb:
        await ctx.send(embed=discord.Embed(title="🏆 Leaderboard", description=f"No players! Use `{PREFIX}play`", color=COLORS["leaderboard"]))
        return
    embed = discord.Embed(title="🏆 Free Fire Leaderboard — Top 10", color=0xFFD700)
    medals = ["🥇", "🥈", "🥉"]
    desc = ""
    for i, p in enumerate(lb):
        m = medals[i] if i < 3 else f"`#{i+1}`"
        mem = ctx.guild.get_member(p["user_id"])
        name = mem.display_name if mem else p["username"]
        level = p.get("level", STARTING_LEVEL)
        wr = round((p["wins"] / max(p["matches_played"], 1)) * 100, 1)
        desc += f"{m} **{name}**\n   📊 {p['points']} pts | 🏅 RANK {level} | 🎮 {p['matches_played']}M | ✅ {p['wins']}W | ❌ {p['losses']}L | 📈 {wr}%\n\n"
    embed.description = desc
    embed.set_footer(text="Free Fire Bot v4.0 🤖")
    await ctx.send(embed=embed)
    await update_leaderboard_channel(ctx.guild)


@bot.command(name="leave")
@commands.cooldown(1, 5, commands.BucketType.user)
async def leave_cmd(ctx):
    lobby = db.get_player_active_lobby(ctx.author.id, ctx.guild.id)
    if not lobby:
        await ctx.send(embed=discord.Embed(title="❌ Not in lobby", color=COLORS["error"]))
        return
    if lobby["creator_id"] == ctx.author.id and lobby["status"] == "waiting":
        total = len(lobby["team1_players"]) + len(lobby["team2_players"])
        if total <= 1:
            db.update_lobby_status(lobby["id"], "cancelled")
            cleanup_lobby_memory(lobby["id"])
            await ctx.send(embed=discord.Embed(title="🗑️ Lobby Cancelled", color=COLORS["warning"]))
            return
        remaining = [p for p in (lobby["team1_players"] + lobby["team2_players"]) if p != ctx.author.id]
        if remaining:
            db.reassign_creator(lobby["id"], remaining[0])
    db.remove_player_from_lobby(lobby["id"], ctx.author.id)
    await ctx.send(embed=discord.Embed(title="✅ Left Lobby", description=f"Lobby #{lobby['id']}", color=COLORS["success"]))


@bot.command(name="matches")
@commands.cooldown(1, 10, commands.BucketType.user)
async def matches_cmd(ctx):
    lobbies = db.get_active_lobbies(ctx.guild.id)
    if not lobbies:
        await ctx.send(embed=discord.Embed(title="🎮 Active Lobbies", description=f"None. Use `{PREFIX}play`", color=COLORS["info"]))
        return
    embed = discord.Embed(title="🎮 Active Lobbies", color=COLORS["match"])
    for l in lobbies[:5]:
        mode = l.get("game_mode", DEFAULT_MODE)
        mi = GAME_MODES.get(mode, GAME_MODES[DEFAULT_MODE])
        t1c = len(l["team1_players"]); t2c = len(l["team2_players"])
        se = {"waiting": "⏳", "started": "🎮", "voting": "🗳️"}.get(l["status"], "❓")
        embed.add_field(name=f"Lobby #{l['id']} {mi['emoji']} {mode.upper()} — {se}", value=f"🟠 {t1c}/{mi['team_size']} | 🟢 {t2c}/{mi['team_size']}", inline=False)
    await ctx.send(embed=embed)


@bot.command(name="mylevel")
@commands.cooldown(1, 5, commands.BucketType.user)
async def mylevel_cmd(ctx, member: discord.Member = None):
    target = member or ctx.author
    player = db.get_or_create_player(target.id, ctx.guild.id, target.display_name)
    level = player.get("level", STARTING_LEVEL)
    await update_member_nickname(target, level)
    embed = discord.Embed(title=f"🏅 RANK — {target.display_name}", description=f"RANK: **#{level}**\nPoints: {player['points']}\nWins: {player['wins']} | Losses: {player['losses']}", color=COLORS["profile"])
    await ctx.send(embed=embed)


@bot.command(name="myrank")
@commands.cooldown(1, 5, commands.BucketType.user)
async def myrank_cmd(ctx):
    target = ctx.author
    player = db.get_or_create_player(target.id, ctx.guild.id, target.display_name)
    level = player.get("level", STARTING_LEVEL)
    original = player.get("original_nickname") or extract_original_nickname(target.display_name)
    target_nick = build_nickname_with_level(original, level)
    is_owner = (target.id == ctx.guild.owner_id)
    embed = discord.Embed(title="📝 Your Rank", description=f"👤 {target.mention}\n🏅 RANK: #{level}\n📝 Current: `{target.display_name}`\n🎯 Target: `{target_nick}`", color=COLORS["profile"])
    if is_owner:
        embed.add_field(name="👑 Owner", value="Bot can't change your nickname. Apply manually.", inline=False)
    await ctx.send(embed=embed)


@bot.command(name="fixrank")
@commands.cooldown(1, 5, commands.BucketType.user)
async def fixrank_cmd(ctx, member: discord.Member = None):
    target = member or ctx.author
    player = db.get_or_create_player(target.id, ctx.guild.id, target.display_name)
    level = player.get("level", STARTING_LEVEL)
    if target.id == ctx.guild.owner_id:
        original = player.get("original_nickname") or extract_original_nickname(target.display_name)
        target_nick = build_nickname_with_level(original, level)
        await ctx.send(embed=discord.Embed(title="👑 Server Owner", description=f"{target.mention} → **RANK #{level}**\n\n📝 Target: `{target_nick}`\nApply manually: Right-click → Edit Profile → Nickname", color=COLORS["warning"]))
        return
    await update_member_nickname(target, level)
    await ctx.send(embed=discord.Embed(title="🔧 Rank Applied", description=f"{target.mention} → **RANK #{level}**", color=COLORS["success"]))


@bot.command(name="matchinfo")
@commands.cooldown(1, 5, commands.BucketType.user)
async def matchinfo_cmd(ctx, lobby_id: int = None):
    if lobby_id is None:
        await ctx.send(embed=discord.Embed(title="❌ Missing ID", description=f"Usage: `{PREFIX}matchinfo <id>`", color=COLORS["error"]))
        return
    lobby = db.get_lobby(lobby_id)
    if not lobby:
        await ctx.send(embed=discord.Embed(title="❌ Not found", color=COLORS["error"]))
        return
    embed = discord.Embed(title=f"📋 Match #{lobby_id}", color=COLORS["info"])
    t1m = " ".join([f"<@{p}>" for p in lobby["team1_players"]]) or "None"
    t2m = " ".join([f"<@{p}>" for p in lobby["team2_players"]]) or "None"
    embed.add_field(name=f"🟠 Team 1 ({len(lobby['team1_players'])})", value=t1m, inline=True)
    embed.add_field(name=f"🟢 Team 2 ({len(lobby['team2_players'])})", value=t2m, inline=True)
    embed.add_field(name="Status", value=lobby["status"], inline=True)
    await ctx.send(embed=embed)


# ============================================================
# ADMIN COMMANDS
# ============================================================

@bot.command(name="setup")
@commands.check(is_bot_owner_or_admin_check)
@commands.cooldown(1, 60, commands.BucketType.guild)
async def setup_cmd(ctx):
    guild = ctx.guild
    created = []
    if ctx.author.id == BOT_OWNER_ID:
        db.add_allowed_guild(guild.id, guild.name, ctx.author.id)
    cat = discord.utils.get(guild.categories, name="🎮 FREE FIRE")
    if not cat:
        cat = await guild.create_category("🎮 FREE FIRE", overwrites={guild.default_role: discord.PermissionOverwrite(read_messages=True), guild.me: discord.PermissionOverwrite(manage_channels=True, manage_messages=True)})
    for ch_name, topic in [("🎮・apostada-play", "Play"), ("🎮・highlight-play", "Play"), ("🎮・zelika-play", "Cards"), ("📊・match-results", "Results"), ("🏆・leaderboard", "Leaderboard"), ("👤・profiles", "Profiles")]:
        if not discord.utils.get(guild.text_channels, name=ch_name):
            ch = await guild.create_text_channel(ch_name, category=cat, topic=topic)
            db.add_commands_channel(guild.id, ch.id)
            db.add_play_channel(guild.id, ch.id)
            if "leaderboard" in ch_name:
                db.set_guild_setting(guild.id, "leaderboard_channel_id", ch.id)
            created.append(ch_name)
    for ch_name in ["⏳・Waiting 1", "⏳・Waiting 2", "⏳・Waiting 3", "⏳・Waiting 4", "⏳・Waiting 5", "🔒・Waiting Prv 1", "🔒・Waiting Prv 2", "🔒・Waiting Prv 3", "🔒・Waiting Staff"]:
        if not discord.utils.get(guild.voice_channels, name=ch_name):
            overwrites = {guild.me: discord.PermissionOverwrite(connect=True, manage_channels=True)}
            if "Prv" in ch_name or "Staff" in ch_name:
                overwrites[guild.default_role] = discord.PermissionOverwrite(connect=False)
            ch = await guild.create_voice_channel(ch_name, category=cat, overwrites=overwrites)
            db.add_waiting_room(guild.id, ch.id)
            created.append(ch_name)
    try: await update_leaderboard_channel(guild)
    except: pass
    await ctx.send(embed=discord.Embed(title="✅ Setup Complete!", description=f"Created {len(created)} channels.\n\nUse `{PREFIX}play` in play channels.", color=COLORS["success"]))


@bot.command(name="cleanup")
@commands.check(is_bot_owner_or_admin_check)
@commands.cooldown(1, 30, commands.BucketType.guild)
async def cleanup_cmd(ctx):
    guild = ctx.guild
    deleted = 0
    for cat in guild.categories:
        if cat.name.startswith("🎮 Match #"):
            for ch in cat.channels:
                try: await ch.delete()
                except: pass
            try: await cat.delete(); deleted += 1
            except: pass
    await ctx.send(embed=discord.Embed(title="🧹 Cleanup Complete!", description=f"Deleted {deleted} categories.", color=COLORS["success"]))


@bot.command(name="scan")
@commands.check(is_bot_owner_or_admin_check)
@commands.cooldown(1, 15, commands.BucketType.guild)
async def scan_cmd(ctx, page: int = 1):
    """🔍 !!scan [page] — سكان كل كاتيجوريات السيرفر"""
    guild = ctx.guild
    categories = sorted(guild.categories, key=lambda c: c.name.lower())
    per_page = 10
    total_pages = max(1, (len(categories) + per_page - 1) // per_page)
    if page < 1: page = 1
    if page > total_pages: page = total_pages
    start = (page - 1) * per_page
    end = start + per_page
    page_cats = categories[start:end]

    embed = discord.Embed(
        title=f"🔍 Server Categories — {len(categories)} total",
        description=f"Page {page}/{total_pages}\nUse `{PREFIX}deletecat <name>` to delete a category.",
        color=COLORS["info"]
    )
    for i, cat in enumerate(page_cats, start + 1):
        text_count = len(cat.text_channels)
        voice_count = len(cat.voice_channels)
        embed.add_field(
            name=f"{i}. {cat.name}",
            value=f"📝 {text_count} text | 🔊 {voice_count} voice | ID: `{cat.id}`",
            inline=False
        )
    embed.set_footer(text=f"Page {page}/{total_pages} | {PREFIX}scan <page> | {PREFIX}deletecat <name>")
    await ctx.send(embed=embed)


@bot.command(name="deletecat", aliases=["delcat"])
@commands.check(is_bot_owner_or_admin_check)
@commands.cooldown(1, 10, commands.BucketType.guild)
async def deletecat_cmd(ctx, *, category_name: str = None):
    """🗑️ !!deletecat <name> — حذف كاتيجوري بكل قنواتها"""
    if not category_name:
        await ctx.send(embed=discord.Embed(
            title="❌ Missing name",
            description=f"Usage: `{PREFIX}deletecat <category name>`\nUse `{PREFIX}scan` to see all categories.",
            color=COLORS["error"]
        ))
        return

    guild = ctx.guild
    # ابحث عن الكاتيجوري بالاسم (تطابق كامل أو جزئي)
    target = None
    for cat in guild.categories:
        if cat.name.lower() == category_name.lower():
            target = cat
            break
    if not target:
        for cat in guild.categories:
            if category_name.lower() in cat.name.lower():
                target = cat
                break

    if not target:
        await ctx.send(embed=discord.Embed(
            title="❌ Not found",
            description=f"No category matching `{category_name}`.\nUse `{PREFIX}scan` to see all categories.",
            color=COLORS["error"]
        ))
        return

    # اعرض تأكيد قبل الحذف
    text_count = len(target.text_channels)
    voice_count = len(target.voice_channels)
    total_channels = text_count + voice_count

    confirm_embed = discord.Embed(
        title="⚠️ Confirm Deletion",
        description=(
            f"**Category:** {target.name}\n"
            f"**Channels:** {total_channels} ({text_count} text + {voice_count} voice)\n\n"
            f"⚠️ **This will delete ALL channels inside!**\n"
            f"Type `{PREFIX}confirmcat {target.name}` to confirm."
        ),
        color=COLORS["warning"]
    )
    await ctx.send(embed=confirm_embed)


@bot.command(name="confirmcat")
@commands.check(is_bot_owner_or_admin_check)
@commands.cooldown(1, 10, commands.BucketType.guild)
async def confirmcat_cmd(ctx, *, category_name: str = None):
    """✅ !!confirmcat <name> — تأكيد حذف الكاتيجوري"""
    if not category_name:
        await ctx.send(embed=discord.Embed(title="❌ Missing name", description=f"Usage: `{PREFIX}confirmcat <name>`", color=COLORS["error"]))
        return

    guild = ctx.guild
    target = None
    for cat in guild.categories:
        if cat.name.lower() == category_name.lower() or category_name.lower() in cat.name.lower():
            target = cat
            break

    if not target:
        await ctx.send(embed=discord.Embed(title="❌ Not found", color=COLORS["error"]))
        return

    # احذف كل القنوات داخل الكاتيجوري
    deleted = 0
    errors = 0
    for ch in target.channels:
        try:
            await ch.delete()
            deleted += 1
        except (discord.NotFound, discord.Forbidden):
            errors += 1
        except Exception as e:
            logger.warning(f"Failed to delete {ch.name}: {e}")
            errors += 1

    # احذف الكاتيجوري نفسها
    cat_name = target.name
    try:
        await target.delete()
        await ctx.send(embed=discord.Embed(
            title="🗑️ Category Deleted!",
            description=f"**{cat_name}** deleted!\n✅ Channels deleted: {deleted}\n❌ Errors: {errors}",
            color=COLORS["success"]
        ))
    except (discord.NotFound, discord.Forbidden) as e:
        await ctx.send(embed=discord.Embed(
            title="⚠️ Partial Delete",
            description=f"Deleted {deleted} channels but couldn't delete the category itself.\nError: {e}",
            color=COLORS["warning"]
        ))


@bot.command(name="fixrankall", aliases=["forcerankall"])
@commands.check(is_admin_check)
@commands.cooldown(1, 60, commands.BucketType.guild)
async def fixrankall_cmd(ctx):
    guild = ctx.guild
    progress = await ctx.send(embed=discord.Embed(title="🚀 Applying ranks...", description=f"Members: {len(guild.members)}", color=COLORS["warning"]))
    updated = 0
    for member in guild.members:
        if member.bot: continue
        try:
            player = db.get_or_create_player(member.id, guild.id, member.display_name)
            await update_member_nickname(member, player.get("level", STARTING_LEVEL))
            updated += 1
            await asyncio.sleep(0.3)
        except: pass
    await progress.edit(embed=discord.Embed(title="✅ Done!", description=f"Updated: {updated}", color=COLORS["success"]))


@bot.command(name="botinfo")
async def botinfo_cmd(ctx):
    embed = discord.Embed(title="🤖 Bot Info", description=f"**Name:** {bot.user.name}\n**Version:** v4.0 CLEAN\n**Prefix:** `{PREFIX}`\n**👑 Owner:** {BOT_OWNER_NAME}\n**🏠 Servers:** {len(bot.guilds)}\n**👥 Users:** {sum(g.member_count for g in bot.guilds)}", color=COLORS["info"])
    await ctx.send(embed=embed)


@bot.command(name="allowguild")
@commands.check(is_bot_owner_check)
async def allowguild_cmd(ctx, *, guild_name: str = None):
    if not guild_name:
        guilds_list = "\n".join([f"• {g.name}" for g in bot.guilds[:15]])
        await ctx.send(embed=discord.Embed(title="➕ Allow Guild", description=f"Usage: `{PREFIX}allowguild <name>`\n\n{guilds_list}", color=COLORS["info"]))
        return
    guild = None
    for g in bot.guilds:
        if g.name.lower() == guild_name.lower() or guild_name.lower() in g.name.lower():
            guild = g; break
    if not guild:
        await ctx.send(embed=discord.Embed(title="❌ Not found", color=COLORS["error"]))
        return
    db.add_allowed_guild(guild.id, guild.name, ctx.author.id)
    await ctx.send(embed=discord.Embed(title="✅ Added", description=f"**{guild.name}** allowed.", color=COLORS["success"]))


@bot.command(name="removeguild")
@commands.check(is_bot_owner_check)
async def removeguild_cmd(ctx, *, guild_name: str = None):
    if not guild_name:
        await ctx.send(embed=discord.Embed(title="❌ Missing name", description=f"Usage: `{PREFIX}removeguild <name>`", color=COLORS["error"]))
        return
    guilds = db.get_allowed_guilds()
    target = None
    for g in guilds:
        if guild_name.lower() in g["guild_name"].lower():
            target = g; break
    if not target:
        await ctx.send(embed=discord.Embed(title="❌ Not found", color=COLORS["error"]))
        return
    db.remove_allowed_guild(target["guild_id"])
    g = bot.get_guild(target["guild_id"])
    if g: await g.leave()
    await ctx.send(embed=discord.Embed(title="✅ Removed", description=f"**{target['guild_name']}** removed.", color=COLORS["success"]))


@bot.command(name="listguilds")
@commands.check(is_bot_owner_check)
async def listguilds_cmd(ctx):
    guilds = db.get_allowed_guilds()
    embed = discord.Embed(title="📋 Allowed Guilds", color=COLORS["info"])
    if not guilds:
        embed.description = "None."
    else:
        embed.description = "\n".join([f"• {g['guild_name']}" for g in guilds])
    await ctx.send(embed=embed)


@bot.command(name="leaveserver")
@commands.check(is_bot_owner_check)
async def leaveserver_cmd(ctx, *, guild_name: str = None):
    if not guild_name:
        guilds_list = "\n".join([f"• {g.name}" for g in bot.guilds[:15]])
        await ctx.send(embed=discord.Embed(title="🚪 Leave Server", description=f"Usage: `{PREFIX}leaveserver <name>`\n\n{guilds_list}", color=COLORS["info"]))
        return
    guild = None
    for g in bot.guilds:
        if g.name.lower() == guild_name.lower() or guild_name.lower() in g.name.lower():
            guild = g; break
    if not guild:
        await ctx.send(embed=discord.Embed(title="❌ Not found", color=COLORS["error"]))
        return
    name = guild.name
    await guild.leave()
    await ctx.send(embed=discord.Embed(title="🚪 Left", description=f"Left **{name}**", color=COLORS["success"]))


@bot.command(name="setcommandschannel")
@commands.check(is_admin_check)
async def setcommandschannel_cmd(ctx, channel: discord.TextChannel = None):
    channel = channel or ctx.channel
    if channel.id in db.get_commands_channels(ctx.guild.id):
        db.remove_commands_channel(ctx.guild.id, channel.id)
        await ctx.send(embed=discord.Embed(title="✅ Removed", description=f"{channel.mention}", color=COLORS["success"]))
    else:
        db.add_commands_channel(ctx.guild.id, channel.id)
        await ctx.send(embed=discord.Embed(title="✅ Added", description=f"{channel.mention}", color=COLORS["success"]))


@bot.command(name="setleaderboard")
@commands.check(is_admin_check)
async def setleaderboard_cmd(ctx):
    db.set_guild_setting(ctx.guild.id, "leaderboard_channel_id", ctx.channel.id)
    await update_leaderboard_channel(ctx.guild)
    await ctx.send(embed=discord.Embed(title="✅ Leaderboard Set", color=COLORS["success"]))


@bot.command(name="resolve")
@commands.check(is_admin_check)
async def resolve_cmd(ctx, lobby_id: int = None, winner: str = None):
    if lobby_id is None or winner is None:
        await ctx.send(embed=discord.Embed(title="❌ Missing", description=f"Usage: `{PREFIX}resolve <id> <team1|team2>`", color=COLORS["error"]))
        return
    winner = winner.lower()
    if winner not in ["team1", "team2"]:
        await ctx.send(embed=discord.Embed(title="❌ Invalid", color=COLORS["error"]))
        return
    lobby = db.get_lobby(lobby_id)
    if not lobby or lobby["status"] != "voting":
        await ctx.send(embed=discord.Embed(title="❌ No dispute", color=COLORS["error"]))
        return
    await ctx.send(embed=discord.Embed(title="⚖️ Resolved!", description=f"**{ctx.author.mention}** decided: **{'🟠 Team 1' if winner=='team1' else '🟢 Team 2'}**", color=COLORS["success"]))
    await process_match_result(ctx.guild, lobby_id, winner, ctx.channel)


@bot.command(name="resetstats")
@commands.check(is_admin_check)
async def resetstats_cmd(ctx, member: discord.Member = None):
    if not member:
        await ctx.send(embed=discord.Embed(title="❌ Missing user", description=f"Usage: `{PREFIX}resetstats @user`", color=COLORS["error"]))
        return
    db.reset_stats(member.id, ctx.guild.id)
    await update_member_nickname(member, STARTING_LEVEL)
    await ctx.send(embed=discord.Embed(title="✅ Reset", description=f"{member.mention} — RANK #{STARTING_LEVEL}", color=COLORS["success"]))


@bot.command(name="setlevel")
@commands.check(is_admin_check)
async def setlevel_cmd(ctx, member: discord.Member = None, level: int = None):
    if not member or level is None:
        await ctx.send(embed=discord.Embed(title="❌ Missing", description=f"Usage: `{PREFIX}setlevel @user <level>`", color=COLORS["error"]))
        return
    if level < 1 or level > 9999:
        await ctx.send(embed=discord.Embed(title="❌ Invalid level", color=COLORS["error"]))
        return
    db.get_or_create_player(member.id, ctx.guild.id, member.display_name)
    db.update_player_stats(member.id, ctx.guild.id, level=level)
    await update_member_nickname(member, level)
    await ctx.send(embed=discord.Embed(title="✅ Updated", description=f"{member.mention} → **RANK #{level}**", color=COLORS["success"]))


@bot.command(name="syncnicknames")
@commands.check(is_admin_check)
@commands.cooldown(1, 60, commands.BucketType.guild)
async def syncnicknames_cmd(ctx):
    guild = ctx.guild
    updated = 0
    for member in guild.members:
        if member.bot: continue
        player = db.get_or_create_player(member.id, guild.id, member.display_name)
        await update_member_nickname(member, player.get("level", STARTING_LEVEL))
        updated += 1
        await asyncio.sleep(0.3)
    await ctx.send(embed=discord.Embed(title="✅ Synced", description=f"{updated} members", color=COLORS["success"]))


# ============================================================
# HELP COMMANDS
# ============================================================

@bot.command(name="general")
@commands.cooldown(1, 5, commands.BucketType.user)
async def general_cmd(ctx):
    embed = discord.Embed(title="🎮 Player Commands", description=f"**Prefix:** `{PREFIX}`", color=0xFF6B00)
    embed.add_field(name="🚀 Play", value=f"• `{PREFIX}play` — 4v4\n• `{PREFIX}play1v1` / `play2v2` / `play3v3`", inline=False)
    embed.add_field(name="📊 Stats", value=f"• `{PREFIX}p` — Profile\n• `{PREFIX}card` — Card (zelika-play)\n• `{PREFIX}top` — Leaderboard\n• `{PREFIX}mylevel` — Your rank\n• `{PREFIX}matches` — Active lobbies", inline=False)
    embed.add_field(name="🎮 Control", value=f"• `{PREFIX}leave` — Leave lobby\n• `{PREFIX}fixrank` — Apply rank", inline=False)
    embed.add_field(name="🤖 How to play", value=f"1️⃣ Join a ⏳ Waiting room\n2️⃣ `{PREFIX}play` in play channel\n3️⃣ Press **Create Lobby** → Enter Room Info\n4️⃣ Players press **Join Team 1/2**\n5️⃣ Lobby fills → Match starts\n6️⃣ Host presses **Start Vote**\n7️⃣ Vote → Result → RANK updates\n8️⃣ Players return to waiting rooms", inline=False)
    embed.set_footer(text=f"Free Fire Bot v4.0 | {PREFIX}help (admin)")
    await ctx.send(embed=embed)


@bot.command(name="help")
@commands.cooldown(1, 5, commands.BucketType.user)
async def help_cmd(ctx):
    # 🆕 رسالة 1: أوامر اللاعبين
    embed1 = discord.Embed(title="🔥 Free Fire Bot v4.0 — Player Commands", description=f"**Prefix:** `{PREFIX}`\n━━━━━━━━━━━━━━━━━━━━━━━━━━━", color=0xFF6B00)
    embed1.add_field(name="🎮 Play", value=(
        f"• `{PREFIX}play` — 4v4 (default)\n"
        f"• `{PREFIX}play1v1` — 1v1\n"
        f"• `{PREFIX}play2v2` — 2v2\n"
        f"• `{PREFIX}play3v3` — 3v3\n"
        f"• `{PREFIX}play4v4` — 4v4"
    ), inline=False)
    embed1.add_field(name="📊 Stats", value=(
        f"• `{PREFIX}p` — Your profile\n"
        f"• `{PREFIX}p @user` — Other profile\n"
        f"• `{PREFIX}card` — Card (zelika-play only)\n"
        f"• `{PREFIX}card @user` — Other card\n"
        f"• `{PREFIX}top` — Leaderboard Top 10\n"
        f"• `{PREFIX}mylevel` — Your rank\n"
        f"• `{PREFIX}myrank` — Target nickname\n"
        f"• `{PREFIX}matches` — Active lobbies\n"
        f"• `{PREFIX}matchinfo <id>` — Match details"
    ), inline=False)
    embed1.add_field(name="🎮 Control", value=(
        f"• `{PREFIX}leave` — Leave lobby\n"
        f"• `{PREFIX}fixrank` — Apply rank to name\n"
        f"• `{PREFIX}fixrank @user` — Apply to other"
    ), inline=False)
    embed1.set_footer(text=f"Page 1/2 | {PREFIX}help for admin commands")
    await ctx.send(embed=embed1)

    # 🆕 رسالة 2: أوامر الأدمن
    embed2 = discord.Embed(title="🔧 Free Fire Bot v4.0 — Admin Commands", description=f"**Prefix:** `{PREFIX}`\n━━━━━━━━━━━━━━━━━━━━━━━━━━━", color=0xE74C3C)
    embed2.add_field(name="🔧 Setup & Channels", value=(
        f"• `{PREFIX}setup` — Create all channels\n"
        f"• `{PREFIX}cleanup` — Delete match categories\n"
        f"• `{PREFIX}setcommandschannel #ch` — Add/remove command channel\n"
        f"• `{PREFIX}setleaderboard` — Set leaderboard channel"
    ), inline=False)
    embed2.add_field(name="🔍 Scan & Delete", value=(
        f"• `{PREFIX}scan` — List all categories\n"
        f"• `{PREFIX}scan 2` — Page 2\n"
        f"• `{PREFIX}deletecat <name>` — Mark category for deletion\n"
        f"• `{PREFIX}confirmcat <name>` — Confirm deletion"
    ), inline=False)
    embed2.add_field(name="🏅 Ranks", value=(
        f"• `{PREFIX}fixrankall` — Apply ranks to ALL members\n"
        f"• `{PREFIX}syncnicknames` — Sync all nicknames\n"
        f"• `{PREFIX}setlevel @user <n>` — Set level (1-9999)\n"
        f"• `{PREFIX}resetstats @user` — Reset player stats"
    ), inline=False)
    embed2.add_field(name="🏠 Guilds", value=(
        f"• `{PREFIX}allowguild <name>` — Allow server\n"
        f"• `{PREFIX}removeguild <name>` — Remove server\n"
        f"• `{PREFIX}listguilds` — List allowed servers\n"
        f"• `{PREFIX}leaveserver <name>` — Leave server\n"
        f"• `{PREFIX}botinfo` — Bot info"
    ), inline=False)
    embed2.add_field(name="⚖️ Match Admin", value=(
        f"• `{PREFIX}resolve <id> <team1|team2>` — Resolve vote dispute"
    ), inline=False)
    embed2.add_field(name="ℹ️ Info", value=(
        f"• `{PREFIX}general` — Player guide (any channel)\n"
        f"• `{PREFIX}help` — This message (any channel)"
    ), inline=False)
    embed2.set_footer(text=f"Page 2/2 | Free Fire Bot v4.0 CLEAN | 33 commands")
    await ctx.send(embed=embed2)


# ============================================================
# RUN
# ============================================================
if __name__ == "__main__":
    TOKEN = os.getenv("DISCORD_TOKEN") or "MTUxNzU4NjA4MTk3NTg5NDAxNw.GJpInx.Ohmp-CCc9nb8Uid8B5_h4M6W4_zW8OnI0d0IUA"
    if not TOKEN:
        raise RuntimeError("DISCORD_TOKEN required")
    logger.info("🚀 Starting Free Fire Bot v4.0 CLEAN...")
    bot.run(TOKEN)
