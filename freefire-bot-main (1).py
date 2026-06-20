"""
===========================================================
  🔥 Free Fire Matchmaking Bot — v3.1 ULTRA AUTO (FIXED)
===========================================================
  🤖 كل شي تلقائي! اللاعبين ما يحتاجون يكتبون أوامر:

  AUTO FLOW:
  1. /play → اللوبي ينشأ تلقائياً
  2. React 🔴🔵 → اللاعبين ينضمون + ينقلون للانتظار
  3. اللوبي يمتلي → الماتش يبدأ تلقائياً
  4. الفويسات والشاتات تنشأ تلقائياً لكل تيم
  5. البوت يرسل DM لصاحب الروم يطلب الآيدي والكود
  6. صاحب الروم يرد بالآيدي والكود في DM → ينرسل تلقائياً
  7. اللاعبين يخلصون → يطلعون من الفويسات
  8. البوت يكشف تلقائياً → يدخل وضع التصويت
  9. يبينق الناخبين (صاحب الروم + أول داخل) يطلب تصويت
  10. الناخبين يضغطون أزرار ✅ Team 1 أو ✅ Team 2
  11. لو اتفقوا → النتيجة تُحسب + Level يتحدث + الاسم يتغير
  12. لو اختلفوا → البوت يبينق Owner تلقائياً
  13. الفويسات والشاتات تنحذف تلقائياً
  14. لو ما صوتوا 3 دقايق → البوت يبينق Owner
  15. لو اللوبي منتظر 30 دقيقة → يلغيه تلقائياً
  16. بعد النتيجة → البوت يعرض زر إعادة الماتش 🔄
===========================================================
  Just run: python main.py
===========================================================
"""

import discord
from discord.ext import commands
import sqlite3
import json
import os
import asyncio
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

# ============================================================
# LOGGING SETUP
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler("bot.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("freefire_bot")


# ============================================================
# CONFIGURATION
# ============================================================

PREFIX = "!!"

GAME_MODES = {
    "1v1": {"team_size": 1, "lobby_size": 2,  "emoji": "⚔️", "color": 0xFF4444},
    "2v2": {"team_size": 2, "lobby_size": 4,  "emoji": "🔥", "color": 0xFF8800},
    "3v3": {"team_size": 3, "lobby_size": 6,  "emoji": "💎", "color": 0x00BFFF},
    "4v4": {"team_size": 4, "lobby_size": 8,  "emoji": "👑", "color": 0xFFD700},
}

DEFAULT_MODE = "4v4"

RANKS = {
    1:  {"name": "Bronze I",      "emoji": "🥉", "color": "#CD7F32", "min_points": 0},
    2:  {"name": "Bronze II",     "emoji": "🥉", "color": "#CD7F32", "min_points": 100},
    3:  {"name": "Bronze III",    "emoji": "🥉", "color": "#CD7F32", "min_points": 200},
    4:  {"name": "Silver I",      "emoji": "🥈", "color": "#C0C0C0", "min_points": 350},
    5:  {"name": "Silver II",     "emoji": "🥈", "color": "#C0C0C0", "min_points": 500},
    6:  {"name": "Silver III",    "emoji": "🥈", "color": "#C0C0C0", "min_points": 650},
    7:  {"name": "Gold I",        "emoji": "🥇", "color": "#FFD700", "min_points": 850},
    8:  {"name": "Gold II",       "emoji": "🥇", "color": "#FFD700", "min_points": 1050},
    9:  {"name": "Gold III",      "emoji": "🥇", "color": "#FFD700", "min_points": 1250},
    10: {"name": "Platinum I",    "emoji": "💎", "color": "#00BFFF", "min_points": 1500},
    11: {"name": "Platinum II",   "emoji": "💎", "color": "#00BFFF", "min_points": 1750},
    12: {"name": "Platinum III",  "emoji": "💎", "color": "#00BFFF", "min_points": 2000},
    13: {"name": "Diamond I",     "emoji": "💠", "color": "#B9F2FF", "min_points": 2300},
    14: {"name": "Diamond II",    "emoji": "💠", "color": "#B9F2FF", "min_points": 2600},
    15: {"name": "Diamond III",   "emoji": "💠", "color": "#B9F2FF", "min_points": 2900},
    16: {"name": "Heroic",        "emoji": "🔥", "color": "#FF4500", "min_points": 3300},
    17: {"name": "Grandmaster",   "emoji": "👑", "color": "#FF0000", "min_points": 3800},
}

MATCH_POINTS = {
    "win": 30,        # نقاط الفوز الأساسية
    "lose": 10,       # نقاط الخسارة الأساسية
    "kill": 5,        # (مستقبلاً)
    "mvp": 15,        # (مستقبلاً)
}
# 🆕 نقاط حسب حجم الماتش
MATCH_POINTS_BY_MODE = {
    "1v1": {"win": 20, "lose": 5},   # أقل نقاط (ماتش صغير)
    "2v2": {"win": 30, "lose": 10},  # متوسط
    "3v3": {"win": 40, "lose": 12},  # أعلى
    "4v4": {"win": 50, "lose": 15},  # الأعلى (ماتش كبير)
}
# 🆕 streaks: مكافآت الانتصارات المتتالية
STREAK_BONUS = {
    3: 10,   # 3 انتصارات متتالية → +10 نقاط إضافية
    5: 25,   # 5 انتصارات متتالية → +25 نقاط إضافية
    10: 50,  # 10 انتصارات متتالية → +50 نقاط إضافية
}
# 🆕 Rank changes (عدد الرتب اللي تزيد/تنقص)
# الفوز العادي → -1 rank
# الفوز مع streak ≥ 3 → -2 rank
# الفوز مع streak ≥ 5 → -3 rank
# الخسارة العادية → +1 rank
# الخسارة مع streak خسارة ≥ 3 → +2 rank
RANK_CHANGE_WIN_NORMAL = -1
RANK_CHANGE_WIN_STREAK_3 = -2
RANK_CHANGE_WIN_STREAK_5 = -3
RANK_CHANGE_LOSE_NORMAL = +1
RANK_CHANGE_LOSE_STREAK_3 = +2

STARTING_LEVEL = 100
MIN_RANK = 1       # 🆕 الحد الأعلى (الأفضل)
MAX_RANK = 9999    # 🆕 الحد الأدنى (الأسوأ)

# ⏱️ Auto timeouts
# 🆕 VOTE: مفتوح indefinitely — ما فيه timeout
# 🆕 VOTE_DELAY_AFTER_MATCH: ننتظر 5 دقايق بعد بداية الماتش قبل بدء التصويت
# 🆕 MAX_DISPUTES: 3 اختلافات قبل استدعاء الأدمن
VOTE_TIMEOUT_SECONDS = None  # 🆕 مفتوح (ما فيه timeout)
LOBBY_TIMEOUT_SECONDS = 1800
VOICE_EMPTY_DELAY = 60
DM_ROOM_PROMPT_DELAY = 5
VOTE_DELAY_AFTER_MATCH = 300  # 🆕 5 دقايق بعد بداية الماتش
MAX_DISPUTES = 3  # 🆕 3 محاولات تصويت قبل استدعاء الأدمن

# Discord limit
NICKNAME_MAX_LENGTH = 32
PREFIX_NICKNAME_LEN = 12  # "Rank 100 " = ~10 chars max

# 🆕 حد عدد غرف الانتظار — مفتوح (البوت ينشئ غرف متعددة)
MAX_WAITING_ROOMS = 20  # حد أقصى مرتفع

# 🆕 إعدادات الأمان — المالك الوحيد للبوت
# 🚨 غيّر هذا الـ ID إلى ID حسابك في Discord
# (تشوفه بتفعيل Developer Mode في Discord، ثم Right-click على نفسك → Copy ID)
# 🆕 مالك البوت: aizenx000 — ضع ID حسابك هنا
BOT_OWNER_ID = 1077949215772250143  # ← ID حسابك (aizenx000)!

# 🆕 اسم مالك البوت (للعرض في الرسائل)
BOT_OWNER_NAME = "aizenx000"

# 🆕 وضع القائمة البيضاء للسيرفرات
# True = البوت يشتغل فقط في السيرفرات المضافة للقائمة البيضاء
# False = البوت يشتغل في أي سيرفر (السلوك الافتراضي)
GUILD_WHITELIST_ENABLED = True

COLORS = {
    "default": 0x2B2D31, "success": 0x00FF7F, "error": 0xFF0000,
    "warning": 0xFFD700, "info": 0x00BFFF, "play": 0xFF6B00,
    "profile": 0x9B59B6, "leaderboard": 0xFFD700, "match": 0x3498DB,
    "admin": 0xE74C3C, "vote": 0x9B59B6, "dispute": 0xFF0000,
    "auto": 0x00FF7F,
}

# Whitelisted columns for guild_settings (defense-in-depth against SQL injection)
GUILD_SETTINGS_COLUMNS = {
    "form_channel_id", "announcement_role_id", "leaderboard_channel_id",
    "leaderboard_message_id", "auto_channel_category_id"
}


# ============================================================
# DATABASE
# ============================================================

class Database:
    def __init__(self, db_path: str = "freefire_bot.db"):
        self.db_path = db_path
        self._create_tables()
        self._migrate()
        self._create_indexes()

    def conn(self) -> sqlite3.Connection:
        c = sqlite3.connect(self.db_path, timeout=30.0)
        c.row_factory = sqlite3.Row
        c.execute("PRAGMA foreign_keys = ON")
        c.execute("PRAGMA journal_mode=WAL")
        return c

    def _create_tables(self) -> None:
        c = self.conn()
        try:
            c.executescript("""
                CREATE TABLE IF NOT EXISTS guild_settings (
                    guild_id INTEGER PRIMARY KEY,
                    form_channel_id INTEGER DEFAULT NULL,
                    announcement_role_id INTEGER DEFAULT NULL,
                    leaderboard_channel_id INTEGER DEFAULT NULL,
                    leaderboard_message_id INTEGER DEFAULT NULL,
                    auto_channel_category_id INTEGER DEFAULT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS play_channels (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER NOT NULL, channel_id INTEGER NOT NULL,
                    UNIQUE(guild_id, channel_id)
                );
                CREATE TABLE IF NOT EXISTS waiting_rooms (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER NOT NULL, channel_id INTEGER NOT NULL,
                    team TEXT DEFAULT 'any',
                    UNIQUE(guild_id, channel_id)
                );
                CREATE TABLE IF NOT EXISTS bot_commands_channels (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER NOT NULL, channel_id INTEGER NOT NULL,
                    UNIQUE(guild_id, channel_id)
                );
                CREATE TABLE IF NOT EXISTS allowed_guilds (
                    guild_id INTEGER PRIMARY KEY,
                    guild_name TEXT,
                    added_by INTEGER,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS linked_rooms (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER NOT NULL, lobby_id INTEGER NOT NULL,
                    team TEXT NOT NULL CHECK(team IN ('team1','team2')),
                    channel_id INTEGER NOT NULL,
                    UNIQUE(guild_id, lobby_id, team)
                );
                CREATE TABLE IF NOT EXISTS players (
                    user_id INTEGER, guild_id INTEGER NOT NULL,
                    username TEXT NOT NULL, points INTEGER DEFAULT 0,
                    rank_pos INTEGER DEFAULT 1, wins INTEGER DEFAULT 0,
                    losses INTEGER DEFAULT 0, kills INTEGER DEFAULT 0,
                    mvps INTEGER DEFAULT 0, matches_played INTEGER DEFAULT 0,
                    level INTEGER DEFAULT 100,
                    win_streak INTEGER DEFAULT 0,
                    lose_streak INTEGER DEFAULT 0,
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
                    status TEXT DEFAULT 'waiting'
                        CHECK(status IN ('waiting','started','voting','completed','cancelled')),
                    team1_players TEXT DEFAULT '[]', team2_players TEXT DEFAULT '[]',
                    first_joiner_id INTEGER DEFAULT NULL,
                    room_id TEXT DEFAULT NULL,
                    room_code TEXT DEFAULT NULL,
                    vote_message_id INTEGER DEFAULT NULL,
                    message_id INTEGER DEFAULT NULL, channel_id INTEGER DEFAULT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    started_at TIMESTAMP DEFAULT NULL, completed_at TIMESTAMP DEFAULT NULL
                );
                CREATE TABLE IF NOT EXISTS match_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    lobby_id INTEGER NOT NULL,
                    winner_team TEXT NOT NULL CHECK(winner_team IN ('team1','team2')),
                    team1_score INTEGER DEFAULT 0, team2_score INTEGER DEFAULT 0,
                    mvp_id INTEGER DEFAULT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (lobby_id) REFERENCES lobbies(id)
                );
                CREATE TABLE IF NOT EXISTS match_channels (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    lobby_id INTEGER NOT NULL,
                    guild_id INTEGER NOT NULL,
                    category_id INTEGER DEFAULT NULL,
                    team1_voice_id INTEGER DEFAULT NULL,
                    team1_text_id INTEGER DEFAULT NULL,
                    team2_voice_id INTEGER DEFAULT NULL,
                    team2_text_id INTEGER DEFAULT NULL,
                    FOREIGN KEY (lobby_id) REFERENCES lobbies(id)
                );
                CREATE TABLE IF NOT EXISTS lobby_votes (
                    lobby_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    vote TEXT NOT NULL CHECK(vote IN ('team1', 'team2')),
                    voted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (lobby_id, user_id)
                );
                CREATE TABLE IF NOT EXISTS vote_metadata (
                    lobby_id INTEGER PRIMARY KEY,
                    creator_id INTEGER NOT NULL,
                    first_joiner_id INTEGER,
                    message_id INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS match_voice_channels (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER NOT NULL,
                    channel_id INTEGER NOT NULL,
                    team TEXT NOT NULL CHECK(team IN ('team1','team2','any')),
                    UNIQUE(guild_id, channel_id)
                );
            """)
            c.commit()
        finally:
            c.close()

    def _create_indexes(self) -> None:
        c = self.conn()
        try:
            c.executescript("""
                CREATE INDEX IF NOT EXISTS idx_players_guild_points ON players(guild_id, points DESC);
                CREATE INDEX IF NOT EXISTS idx_lobbies_guild_status ON lobbies(guild_id, status);
                CREATE INDEX IF NOT EXISTS idx_match_channels_guild ON match_channels(guild_id);
                CREATE INDEX IF NOT EXISTS idx_match_channels_lobby ON match_channels(lobby_id);
                CREATE INDEX IF NOT EXISTS idx_lobby_votes_lobby ON lobby_votes(lobby_id);
            """)
            c.commit()
        finally:
            c.close()

    def _migrate(self) -> None:
        c = self.conn()
        try:
            migrations = [
                ("players", "level", "INTEGER DEFAULT 100"),
                ("players", "original_nickname", "TEXT DEFAULT NULL"),
                ("players", "win_streak", "INTEGER DEFAULT 0"),
                ("players", "lose_streak", "INTEGER DEFAULT 0"),
                ("players", "max_win_streak", "INTEGER DEFAULT 0"),
                ("lobbies", "first_joiner_id", "INTEGER DEFAULT NULL"),
                ("lobbies", "room_id", "TEXT DEFAULT NULL"),
                ("lobbies", "room_code", "TEXT DEFAULT NULL"),
                ("lobbies", "vote_message_id", "INTEGER DEFAULT NULL"),
                ("lobbies", "vote_attempts", "INTEGER DEFAULT 0"),
                ("lobbies", "private_key", "TEXT DEFAULT NULL"),
                ("guild_settings", "auto_channel_category_id", "INTEGER DEFAULT NULL"),
                ("waiting_rooms", "team", "TEXT DEFAULT 'any'"),
            ]
            for table, col, col_type in migrations:
                try:
                    c.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_type}")
                except sqlite3.OperationalError:
                    pass
            # 🆕 جدول vote_disputes لتتبع محاولات التصويت
            c.execute("""
                CREATE TABLE IF NOT EXISTS vote_disputes (
                    lobby_id INTEGER PRIMARY KEY,
                    disputes_count INTEGER DEFAULT 0,
                    last_dispute_at TIMESTAMP
                )
            """)
            c.commit()
        finally:
            c.close()

    # --- Guild Settings ---
    def get_guild_settings(self, gid: int) -> Optional[Dict[str, Any]]:
        conn = self.conn()
        try:
            cur = conn.execute("SELECT * FROM guild_settings WHERE guild_id=?", (gid,))
            r = cur.fetchone()
            return dict(r) if r else None
        finally:
            conn.close()

    def set_guild_setting(self, gid: int, key: str, val: Any) -> None:
        if key not in GUILD_SETTINGS_COLUMNS:
            raise ValueError(f"Invalid guild setting key: {key}")
        conn = self.conn()
        try:
            conn.execute(
                "INSERT INTO guild_settings(guild_id) VALUES(?) "
                "ON CONFLICT(guild_id) DO UPDATE SET guild_id=guild_id",
                (gid,)
            )
            conn.execute(f"UPDATE guild_settings SET {key}=? WHERE guild_id=?", (val, gid))
            conn.commit()
        finally:
            conn.close()

    # --- Play Channels ---
    def add_play_channel(self, gid: int, cid: int) -> bool:
        conn = self.conn()
        try:
            conn.execute("INSERT INTO play_channels(guild_id,channel_id) VALUES(?,?)", (gid, cid))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()

    def remove_play_channel(self, gid: int, cid: int) -> bool:
        conn = self.conn()
        try:
            cur = conn.execute("DELETE FROM play_channels WHERE guild_id=? AND channel_id=?", (gid, cid))
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()

    def get_play_channels(self, gid: int) -> List[int]:
        conn = self.conn()
        try:
            cur = conn.execute("SELECT channel_id FROM play_channels WHERE guild_id=?", (gid,))
            return [x["channel_id"] for x in cur.fetchall()]
        finally:
            conn.close()

    def is_play_channel(self, gid: int, cid: int) -> bool:
        return cid in self.get_play_channels(gid)

    # --- Waiting Rooms (general — both teams wait together) ---
    def add_waiting_room(self, gid: int, cid: int) -> bool:
        """🆕 يضيف غرفة انتظار عامة (للفريقين مع بعض)."""
        conn = self.conn()
        try:
            conn.execute(
                "INSERT INTO waiting_rooms(guild_id,channel_id,team) VALUES(?,?,?)",
                (gid, cid, "any")
            )
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()

    def remove_waiting_room(self, gid: int, cid: int) -> bool:
        conn = self.conn()
        try:
            cur = conn.execute("DELETE FROM waiting_rooms WHERE guild_id=? AND channel_id=?", (gid, cid))
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()

    def get_waiting_rooms(self, gid: int) -> List[int]:
        """🆕 يرجع كل channel_ids لغرف الانتظار العامة."""
        conn = self.conn()
        try:
            cur = conn.execute("SELECT channel_id FROM waiting_rooms WHERE guild_id=?", (gid,))
            return [x["channel_id"] for x in cur.fetchall()]
        finally:
            conn.close()

    def get_first_waiting_room(self, gid: int) -> Optional[int]:
        """🆕 يرجع أول غرفة انتظار متوفرة (أو None).
        اللاعبين من كل التيمات ينتظرون مع بعض — ما يهم الازدحام.
        الهدف من غرف الانتظار = جمع اللاعبين الذين يريدون اللعب في مكان واحد."""
        rooms = self.get_waiting_rooms(gid)
        return rooms[0] if rooms else None

    def get_available_waiting_room(self, gid: int, guild=None) -> Optional[int]:
        """🆕 يرجع أول غرفة انتظار متوفرة.
        اللاعبين من كل التيمات ينتظرون مع بعض في نفس الغرفة.
        لا يهم عدد اللاعبين — الهدف جمع كل من يريد اللعب.
        """
        rooms = self.get_waiting_rooms(gid)
        if not rooms:
            return None
        # رجّع أول غرفة موجودة فعلياً في Discord
        if guild is not None:
            for cid in rooms:
                ch = guild.get_channel(cid)
                if ch:
                    return cid
        # fallback: رجّع الأولى من القاعدة
        return rooms[0]

    def get_all_waiting_rooms(self, gid: int) -> List[Dict[str, Any]]:
        """🆕 يرجع كل غرف الانتظار بصيغة dicts."""
        conn = self.conn()
        try:
            cur = conn.execute("SELECT * FROM waiting_rooms WHERE guild_id=?", (gid,))
            return [dict(x) for x in cur.fetchall()]
        finally:
            conn.close()

    # --- Bot Commands Channels (الغرف اللي البوت يشتغل فيها) ---
    def add_commands_channel(self, gid: int, cid: int) -> bool:
        """🆕 يضيف قناة أوامر مسموحة للبوت."""
        conn = self.conn()
        try:
            conn.execute(
                "INSERT INTO bot_commands_channels(guild_id,channel_id) VALUES(?,?)",
                (gid, cid)
            )
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()

    def remove_commands_channel(self, gid: int, cid: int) -> bool:
        """🆕 يحذف قناة أوامر."""
        conn = self.conn()
        try:
            cur = conn.execute(
                "DELETE FROM bot_commands_channels WHERE guild_id=? AND channel_id=?",
                (gid, cid)
            )
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()

    def get_commands_channels(self, gid: int) -> List[int]:
        """🆕 يرجع كل قنوات الأوامر المسموحة."""
        conn = self.conn()
        try:
            cur = conn.execute(
                "SELECT channel_id FROM bot_commands_channels WHERE guild_id=?",
                (gid,)
            )
            return [x["channel_id"] for x in cur.fetchall()]
        finally:
            conn.close()

    def is_commands_channel(self, gid: int, cid: int) -> bool:
        """🆕 يتحقق إذا القناة مسموحة للأوامر."""
        return cid in self.get_commands_channels(gid)

    def is_bot_allowed_channel(self, gid: int, cid: int) -> bool:
        """🆕 يتحقق إذا البوت مسموح له يشتغل في هذي القناة.
        البوت يشتغل فقط في:
        - قنوات Play المحددة (apostada-play, highlight-play, zelika-play)
        - قنوات الأوامر (bot_commands_channels)
        - غرف الانتظار (waiting_rooms) — بس للانتقال
        - DM messages (دائماً مسموحة)
        - قنوات الماتش الخاصة (match_channels) — للتصويت
        """
        # 1. قنوات الأوامر (تشمل Play channels + bot-commands)
        if cid in self.get_commands_channels(gid):
            return True
        # 2. قنوات الماتش (team1_text, team2_text)
        conn = self.conn()
        try:
            cur = conn.execute(
                "SELECT 1 FROM match_channels WHERE guild_id=? AND (team1_text_id=? OR team2_text_id=?) LIMIT 1",
                (gid, cid, cid)
            )
            if cur.fetchone():
                return True
        finally:
            conn.close()
        return False

    # --- Guild Whitelist (🆕 للتحكم بالسيرفرات المسموحة) ---
    def add_allowed_guild(self, gid: int, guild_name: str, added_by: int) -> bool:
        """🆕 يضيف سيرفر للقائمة البيضاء."""
        conn = self.conn()
        try:
            conn.execute(
                "INSERT OR REPLACE INTO allowed_guilds(guild_id, guild_name, added_by) VALUES(?,?,?)",
                (gid, guild_name, added_by)
            )
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()

    def remove_allowed_guild(self, gid: int) -> bool:
        """🆕 يحذف سيرفر من القائمة البيضاء."""
        conn = self.conn()
        try:
            cur = conn.execute("DELETE FROM allowed_guilds WHERE guild_id=?", (gid,))
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()

    def is_guild_allowed(self, gid: int) -> bool:
        """🆕 يتحقق إذا السيرفر مسموح."""
        # لو الـ whitelist معطّل → كل السيرفرات مسموحة
        if not GUILD_WHITELIST_ENABLED:
            return True
        conn = self.conn()
        try:
            cur = conn.execute("SELECT 1 FROM allowed_guilds WHERE guild_id=?", (gid,))
            return cur.fetchone() is not None
        finally:
            conn.close()

    def get_allowed_guilds(self) -> list:
        """🆕 يرجع كل السيرفرات المسموحة."""
        conn = self.conn()
        try:
            cur = conn.execute("SELECT * FROM allowed_guilds ORDER BY added_at DESC")
            return [dict(x) for x in cur.fetchall()]
        finally:
            conn.close()

    # --- Match Voice Channels (fixed: now supports both single & list API) ---
    def add_match_voice(self, gid: int, team: str, cid: int) -> bool:
        """🆕 إضافة فويسة مسموحة لتيم معين. يرفض التكرار."""
        conn = self.conn()
        try:
            conn.execute(
                "INSERT INTO match_voice_channels(guild_id,channel_id,team) VALUES(?,?,?)",
                (gid, cid, team)
            )
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()

    def set_match_voice(self, gid: int, team: str, cid: int) -> bool:
        """حفظ فويسة محددة لتيم (يستبدل لو موجودة) — يحافظ على التوافق."""
        conn = self.conn()
        try:
            conn.execute("DELETE FROM match_voice_channels WHERE guild_id=? AND team=?", (gid, team))
            conn.execute("INSERT INTO match_voice_channels(guild_id,channel_id,team) VALUES(?,?,?)", (gid, cid, team))
            conn.commit()
            return True
        finally:
            conn.close()

    def remove_match_voice(self, gid: int, cid: int) -> bool:
        """🆕 يحذف بالـ channel_id (بدون الحاجة لتحديد team)."""
        conn = self.conn()
        try:
            cur = conn.execute("DELETE FROM match_voice_channels WHERE guild_id=? AND channel_id=?", (gid, cid))
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()

    def remove_match_voice_by_team(self, gid: int, team: str) -> bool:
        conn = self.conn()
        try:
            cur = conn.execute("DELETE FROM match_voice_channels WHERE guild_id=? AND team=?", (gid, team))
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()

    def get_match_voice(self, gid: int, team: str) -> Optional[int]:
        """يرجع فويسة واحدة للتيم المحدد أو None (للتوافق مع الكود القديم)."""
        conn = self.conn()
        try:
            cur = conn.execute(
                "SELECT channel_id FROM match_voice_channels WHERE guild_id=? AND team=? LIMIT 1",
                (gid, team)
            )
            r = cur.fetchone()
            return r["channel_id"] if r else None
        finally:
            conn.close()

    def get_match_voices(self, gid: int, team: Optional[str] = None) -> List[int]:
        """🆕 يرجع LIST من channel_ids للتيم المحدد.
        لو team=None → يرجع كل الفويسات المسموحة في الجيلد.
        """
        conn = self.conn()
        try:
            if team is None:
                cur = conn.execute(
                    "SELECT channel_id FROM match_voice_channels WHERE guild_id=?",
                    (gid,)
                )
            else:
                cur = conn.execute(
                    "SELECT channel_id FROM match_voice_channels WHERE guild_id=? AND team=?",
                    (gid, team)
                )
            return [x["channel_id"] for x in cur.fetchall()]
        finally:
            conn.close()

    def get_all_match_voices(self, gid: int) -> List[Dict[str, Any]]:
        """يرجع كل الفويسات المسموحة في الجيلد بصيغة list of dicts."""
        conn = self.conn()
        try:
            cur = conn.execute("SELECT * FROM match_voice_channels WHERE guild_id=?", (gid,))
            return [dict(x) for x in cur.fetchall()]
        finally:
            conn.close()

    def get_all_match_voices_info(self, gid: int) -> List[Dict[str, Any]]:
        """🆕 alias لـ get_all_match_voices (للتوافق مع الكود اللي يستدعيها)."""
        return self.get_all_match_voices(gid)

    def has_match_voices(self, gid: int) -> bool:
        t1 = self.get_match_voice(gid, "team1")
        t2 = self.get_match_voice(gid, "team2")
        return t1 is not None and t2 is not None

    # --- Linked Rooms ---
    def add_linked_room(self, gid: int, lid: int, team: str, cid: int) -> bool:
        conn = self.conn()
        try:
            conn.execute("INSERT INTO linked_rooms(guild_id,lobby_id,team,channel_id) VALUES(?,?,?,?)", (gid, lid, team, cid))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()

    def remove_linked_room(self, gid: int, lid: int, team: str) -> bool:
        conn = self.conn()
        try:
            cur = conn.execute("DELETE FROM linked_rooms WHERE guild_id=? AND lobby_id=? AND team=?", (gid, lid, team))
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()

    def get_linked_rooms(self, gid: int) -> List[Dict[str, Any]]:
        conn = self.conn()
        try:
            cur = conn.execute("SELECT * FROM linked_rooms WHERE guild_id=?", (gid,))
            return [dict(x) for x in cur.fetchall()]
        finally:
            conn.close()

    def get_lobby_linked_rooms(self, gid: int, lid: int) -> List[Dict[str, Any]]:
        conn = self.conn()
        try:
            cur = conn.execute("SELECT * FROM linked_rooms WHERE guild_id=? AND lobby_id=?", (gid, lid))
            return [dict(x) for x in cur.fetchall()]
        finally:
            conn.close()

    # --- Players ---
    def get_or_create_player(self, uid: int, gid: int, name: str) -> Dict[str, Any]:
        conn = self.conn()
        try:
            cur = conn.execute("SELECT * FROM players WHERE user_id=? AND guild_id=?", (uid, gid))
            r = cur.fetchone()
            if r:
                conn.execute(
                    "UPDATE players SET last_active=?, username=? WHERE user_id=? AND guild_id=?",
                    (datetime.now().isoformat(), name, uid, gid)
                )
                conn.commit()
                return dict(conn.execute("SELECT * FROM players WHERE user_id=? AND guild_id=?", (uid, gid)).fetchone())
            else:
                conn.execute(
                    "INSERT INTO players(user_id,guild_id,username,level) VALUES(?,?,?,?)",
                    (uid, gid, name, STARTING_LEVEL)
                )
                conn.commit()
                return dict(conn.execute("SELECT * FROM players WHERE user_id=? AND guild_id=?", (uid, gid)).fetchone())
        finally:
            conn.close()

    def get_player(self, uid: int, gid: int) -> Optional[Dict[str, Any]]:
        conn = self.conn()
        try:
            cur = conn.execute("SELECT * FROM players WHERE user_id=? AND guild_id=?", (uid, gid))
            r = cur.fetchone()
            return dict(r) if r else None
        finally:
            conn.close()

    def update_player_stats(self, uid: int, gid: int, **kw) -> None:
        """🆕 محمي ضد kw الفاضي + whitelist الأعمدة المسموح بها."""
        ALLOWED = {
            "points", "rank_pos", "wins", "losses", "kills", "mvps",
            "matches_played", "level", "username", "original_nickname",
            "win_streak", "lose_streak", "max_win_streak"
        }
        # Filter to allowed keys only
        safe = {k: v for k, v in kw.items() if k in ALLOWED}
        if not safe:
            # Nothing to update — just refresh last_active
            conn = self.conn()
            try:
                conn.execute(
                    "UPDATE players SET last_active=? WHERE user_id=? AND guild_id=?",
                    (datetime.now().isoformat(), uid, gid)
                )
                conn.commit()
            finally:
                conn.close()
            return
        sets = ", ".join([f"{k}=?" for k in safe.keys()])
        vals = list(safe.values()) + [datetime.now().isoformat(), uid, gid]
        conn = self.conn()
        try:
            conn.execute(f"UPDATE players SET {sets}, last_active=? WHERE user_id=? AND guild_id=?", vals)
            conn.commit()
        finally:
            conn.close()

    def add_points(self, uid: int, gid: int, amount: int) -> None:
        conn = self.conn()
        try:
            conn.execute(
                "UPDATE players SET points=MAX(0, points+?), last_active=? WHERE user_id=? AND guild_id=?",
                (amount, datetime.now().isoformat(), uid, gid)
            )
            conn.commit()
        finally:
            conn.close()

    def update_player_level(self, uid: int, gid: int, delta: int) -> int:
        """🆕 يحدّث مستوى اللاعب.
        delta = +1 يعني تحسّن (الفوز) → الرقم ينقص (نقترب من 1 = الأعلى)
        delta = -1 يعني تدهور (الهزيمة) → الرقم يزيد (نبتعد عن 1)
        الحد الأقصى = 1 (أعلى مستوى)
        الحد الأدنى = 9999 (أدنى مستوى)
        """
        conn = self.conn()
        try:
            # 🆕 منطق معكوس: delta موجب → ينقص الرقم (تحسّن)
            #                 delta سالب → يزيد الرقم (تدهور)
            # مثال: delta=+1, level=100 → 99 (تحسّن)
            # مثال: delta=-1, level=100 → 101 (تدهور)
            actual_delta = -delta  # عكس الإشارة
            conn.execute(
                "UPDATE players SET level=MAX(1, MIN(9999, level+?)), last_active=? WHERE user_id=? AND guild_id=?",
                (actual_delta, datetime.now().isoformat(), uid, gid)
            )
            conn.commit()
            cur = conn.execute("SELECT level FROM players WHERE user_id=? AND guild_id=?", (uid, gid))
            r = cur.fetchone()
            return dict(r)["level"] if r else STARTING_LEVEL
        finally:
            conn.close()

    def reset_stats(self, uid: int, gid: int) -> None:
        conn = self.conn()
        try:
            conn.execute(
                "UPDATE players SET points=0,wins=0,losses=0,kills=0,mvps=0,matches_played=0,rank_pos=1,level=?,win_streak=0,lose_streak=0,max_win_streak=0,last_active=? WHERE user_id=? AND guild_id=?",
                (STARTING_LEVEL, datetime.now().isoformat(), uid, gid)
            )
            conn.commit()
        finally:
            conn.close()

    def get_leaderboard(self, gid: int, limit: int = 10) -> List[Dict[str, Any]]:
        conn = self.conn()
        try:
            cur = conn.execute("SELECT * FROM players WHERE guild_id=? ORDER BY points DESC LIMIT ?", (gid, limit))
            return [dict(x) for x in cur.fetchall()]
        finally:
            conn.close()

    def get_player_rank(self, points: int) -> int:
        cur = 1
        for rid, rd in RANKS.items():
            if points >= rd["min_points"]:
                cur = rid
        return cur

    # --- Lobbies ---
    def create_lobby(self, gid: int, creator: int, chan: int, mode: str = "4v4") -> int:
        conn = self.conn()
        try:
            cur = conn.execute(
                "INSERT INTO lobbies(guild_id,creator_id,channel_id,game_mode,team1_players) VALUES(?,?,?,?,?)",
                (gid, creator, chan, mode, json.dumps([creator]))
            )
            lid = cur.lastrowid
            conn.commit()
            return lid
        finally:
            conn.close()

    def get_lobby(self, lid: int) -> Optional[Dict[str, Any]]:
        conn = self.conn()
        try:
            cur = conn.execute("SELECT * FROM lobbies WHERE id=?", (lid,))
            r = cur.fetchone()
            if r:
                l = dict(r)
                l["team1_players"] = json.loads(l["team1_players"])
                l["team2_players"] = json.loads(l["team2_players"])
                return l
            return None
        finally:
            conn.close()

    def get_active_lobbies(self, gid: int) -> List[Dict[str, Any]]:
        conn = self.conn()
        try:
            cur = conn.execute(
                "SELECT * FROM lobbies WHERE guild_id=? AND status IN ('waiting','started','voting') ORDER BY created_at DESC",
                (gid,)
            )
            rows = cur.fetchall()
            res = []
            for r in rows:
                l = dict(r)
                l["team1_players"] = json.loads(l["team1_players"])
                l["team2_players"] = json.loads(l["team2_players"])
                res.append(l)
            return res
        finally:
            conn.close()

    def get_all_waiting_lobbies(self, gid: int) -> List[Dict[str, Any]]:
        conn = self.conn()
        try:
            cur = conn.execute("SELECT * FROM lobbies WHERE guild_id=? AND status='waiting'", (gid,))
            return [dict(r) for r in cur.fetchall()]
        finally:
            conn.close()

    def get_player_active_lobby(self, uid: int, gid: int) -> Optional[Dict[str, Any]]:
        conn = self.conn()
        try:
            cur = conn.execute(
                "SELECT * FROM lobbies WHERE guild_id=? AND status IN ('waiting','started','voting')",
                (gid,)
            )
            for r in cur.fetchall():
                l = dict(r)
                t1 = json.loads(l["team1_players"])
                t2 = json.loads(l["team2_players"])
                if uid in t1 or uid in t2:
                    l["team1_players"] = t1
                    l["team2_players"] = t2
                    return l
            return None
        finally:
            conn.close()

    def add_player_to_lobby(self, lid: int, uid: int, team: str) -> bool:
        conn = self.conn()
        try:
            cur = conn.execute("SELECT * FROM lobbies WHERE id=?", (lid,))
            r = cur.fetchone()
            if not r:
                return False
            l = dict(r)
            t1 = json.loads(l["team1_players"])
            t2 = json.loads(l["team2_players"])
            mode = l.get("game_mode", DEFAULT_MODE)
            team_size = GAME_MODES.get(mode, GAME_MODES[DEFAULT_MODE])["team_size"]
            if team == "team1":
                if len(t1) >= team_size:
                    return False
                if uid not in t1:
                    t1.append(uid)
            elif team == "team2":
                if len(t2) >= team_size:
                    return False
                if uid not in t2:
                    t2.append(uid)
            else:
                return False
            conn.execute(
                "UPDATE lobbies SET team1_players=?, team2_players=? WHERE id=?",
                (json.dumps(t1), json.dumps(t2), lid)
            )
            conn.commit()
            return True
        finally:
            conn.close()

    def remove_player_from_lobby(self, lid: int, uid: int) -> bool:
        conn = self.conn()
        try:
            cur = conn.execute("SELECT * FROM lobbies WHERE id=?", (lid,))
            r = cur.fetchone()
            if not r:
                return False
            l = dict(r)
            t1 = json.loads(l["team1_players"])
            t2 = json.loads(l["team2_players"])
            removed = False
            if uid in t1:
                t1.remove(uid)
                removed = True
            if uid in t2:
                t2.remove(uid)
                removed = True
            if removed:
                conn.execute(
                    "UPDATE lobbies SET team1_players=?, team2_players=? WHERE id=?",
                    (json.dumps(t1), json.dumps(t2), lid)
                )
                conn.commit()
            return removed
        finally:
            conn.close()

    def update_lobby_status(self, lid: int, status: str) -> None:
        conn = self.conn()
        try:
            if status == "started":
                conn.execute(
                    "UPDATE lobbies SET status=?, started_at=? WHERE id=?",
                    (status, datetime.now().isoformat(), lid)
                )
            elif status in ("completed", "cancelled"):
                conn.execute(
                    "UPDATE lobbies SET status=?, completed_at=? WHERE id=?",
                    (status, datetime.now().isoformat(), lid)
                )
            else:
                conn.execute("UPDATE lobbies SET status=? WHERE id=?", (status, lid))
            conn.commit()
        finally:
            conn.close()

    def update_lobby_message(self, lid: int, mid: int) -> None:
        conn = self.conn()
        try:
            conn.execute("UPDATE lobbies SET message_id=? WHERE id=?", (mid, lid))
            conn.commit()
        finally:
            conn.close()

    def set_first_joiner(self, lid: int, uid: int) -> None:
        conn = self.conn()
        try:
            conn.execute(
                "UPDATE lobbies SET first_joiner_id=? WHERE id=? AND first_joiner_id IS NULL",
                (uid, lid)
            )
            conn.commit()
        finally:
            conn.close()

    def reassign_creator(self, lid: int, new_creator_id: int) -> None:
        """🆕 H10 fix: يعيد تعيين الـ creator للوبي للاعب ثاني."""
        conn = self.conn()
        try:
            conn.execute("UPDATE lobbies SET creator_id=? WHERE id=?", (new_creator_id, lid))
            conn.commit()
        finally:
            conn.close()

    def set_room_info(self, lid: int, room_id: str, room_code: str, private_key: str = None) -> None:
        conn = self.conn()
        try:
            conn.execute("UPDATE lobbies SET room_id=?, room_code=?, private_key=? WHERE id=?", (room_id, room_code, private_key, lid))
            conn.commit()
        finally:
            conn.close()

    def set_vote_message(self, lid: int, mid: int) -> None:
        conn = self.conn()
        try:
            conn.execute("UPDATE lobbies SET vote_message_id=? WHERE id=?", (mid, lid))
            conn.commit()
        finally:
            conn.close()

    def create_match_result(self, lid: int, winner: str, s1: int, s2: int, mvp: Optional[int] = None) -> int:
        conn = self.conn()
        try:
            cur = conn.execute(
                "INSERT INTO match_results(lobby_id,winner_team,team1_score,team2_score,mvp_id) VALUES(?,?,?,?,?)",
                (lid, winner, s1, s2, mvp)
            )
            rid = cur.lastrowid
            conn.commit()
            return rid
        finally:
            conn.close()

    # --- Match Channels ---
    def save_match_channels(self, lid: int, gid: int, cat_id: Optional[int], t1v: int, t1t: int, t2v: int, t2t: int) -> None:
        conn = self.conn()
        try:
            conn.execute(
                "INSERT INTO match_channels(lobby_id,guild_id,category_id,team1_voice_id,team1_text_id,team2_voice_id,team2_text_id) VALUES(?,?,?,?,?,?,?)",
                (lid, gid, cat_id, t1v, t1t, t2v, t2t)
            )
            conn.commit()
        finally:
            conn.close()

    def get_match_channels(self, lid: int) -> Optional[Dict[str, Any]]:
        conn = self.conn()
        try:
            cur = conn.execute("SELECT * FROM match_channels WHERE lobby_id=?", (lid,))
            r = cur.fetchone()
            return dict(r) if r else None
        finally:
            conn.close()

    def get_match_channels_by_voice(self, gid: int, voice_id: int) -> Optional[Dict[str, Any]]:
        """🆕 يرجع match_channels اللي يحتوي على فويسة معينة."""
        conn = self.conn()
        try:
            cur = conn.execute(
                "SELECT * FROM match_channels WHERE guild_id=? AND (team1_voice_id=? OR team2_voice_id=?)",
                (gid, voice_id, voice_id)
            )
            r = cur.fetchone()
            return dict(r) if r else None
        finally:
            conn.close()

    def delete_match_channels_record(self, lid: int) -> None:
        conn = self.conn()
        try:
            conn.execute("DELETE FROM match_channels WHERE lobby_id=?", (lid,))
            conn.commit()
        finally:
            conn.close()

    def get_all_active_match_channels(self, gid: int) -> List[Dict[str, Any]]:
        """🆕 لاستخدامه في cleanup عند الإقلاع."""
        conn = self.conn()
        try:
            cur = conn.execute(
                "SELECT mc.* FROM match_channels mc "
                "JOIN lobbies l ON mc.lobby_id = l.id "
                "WHERE mc.guild_id=? AND l.status IN ('started','voting')",
                (gid,)
            )
            return [dict(x) for x in cur.fetchall()]
        finally:
            conn.close()

    # --- Votes ---
    def cast_vote(self, lid: int, uid: int, vote: str) -> bool:
        conn = self.conn()
        try:
            conn.execute("INSERT INTO lobby_votes(lobby_id,user_id,vote) VALUES(?,?,?)", (lid, uid, vote))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()

    def get_votes(self, lid: int) -> List[Dict[str, Any]]:
        conn = self.conn()
        try:
            cur = conn.execute("SELECT * FROM lobby_votes WHERE lobby_id=?", (lid,))
            return [dict(x) for x in cur.fetchall()]
        finally:
            conn.close()

    def clear_votes(self, lid: int) -> None:
        conn = self.conn()
        try:
            conn.execute("DELETE FROM lobby_votes WHERE lobby_id=?", (lid,))
            conn.commit()
        finally:
            conn.close()

    def has_voted(self, lid: int, uid: int) -> bool:
        conn = self.conn()
        try:
            cur = conn.execute("SELECT 1 FROM lobby_votes WHERE lobby_id=? AND user_id=?", (lid, uid))
            return cur.fetchone() is not None
        finally:
            conn.close()

    # --- Vote Metadata (🆕 لاسترجاع بيانات VoteView بعد restart البوت) ---
    def save_vote_metadata(self, lid: int, creator_id: int, first_joiner_id: Optional[int], message_id: Optional[int] = None) -> None:
        """🆕 يخزّن بيانات التصويت عشان نسترجعوها بعد restart البوت."""
        conn = self.conn()
        try:
            conn.execute(
                "INSERT OR REPLACE INTO vote_metadata(lobby_id, creator_id, first_joiner_id, message_id) VALUES(?,?,?,?)",
                (lid, creator_id, first_joiner_id, message_id)
            )
            conn.commit()
        finally:
            conn.close()

    def get_vote_metadata(self, lid: int) -> Optional[Dict[str, Any]]:
        """🆕 يرجع بيانات التصويت المحفوظة."""
        conn = self.conn()
        try:
            cur = conn.execute("SELECT * FROM vote_metadata WHERE lobby_id=?", (lid,))
            r = cur.fetchone()
            return dict(r) if r else None
        finally:
            conn.close()

    def delete_vote_metadata(self, lid: int) -> None:
        """🆕 يحذف بيانات التصويت بعد انتهاء الماتش."""
        conn = self.conn()
        try:
            conn.execute("DELETE FROM vote_metadata WHERE lobby_id=?", (lid,))
            conn.commit()
        finally:
            conn.close()

    def get_lobby_id_by_message(self, message_id: int) -> Optional[int]:
        """🆕 يرجع lobby_id من message_id (للـ persistent views)."""
        conn = self.conn()
        try:
            cur = conn.execute("SELECT lobby_id FROM vote_metadata WHERE message_id=?", (message_id,))
            r = cur.fetchone()
            return r["lobby_id"] if r else None
        finally:
            conn.close()

    # --- Vote Disputes (🆕 لتتبع 3 محاولات قبل استدعاء الأدمن) ---
    def get_dispute_count(self, lid: int) -> int:
        """🆕 يرجع عدد محاولات التصويت الفاشلة (الاختلافات)."""
        conn = self.conn()
        try:
            cur = conn.execute("SELECT disputes_count FROM vote_disputes WHERE lobby_id=?", (lid,))
            r = cur.fetchone()
            return r["disputes_count"] if r else 0
        finally:
            conn.close()

    def increment_dispute_count(self, lid: int) -> int:
        """🆕 يزيد عدد الاختلافات بمقدار 1 ويرجّع العدد الجديد."""
        conn = self.conn()
        try:
            # لو ما فيه سجل، أنشئه
            conn.execute(
                "INSERT OR IGNORE INTO vote_disputes(lobby_id, disputes_count, last_dispute_at) VALUES(?,0,NULL)",
                (lid,)
            )
            conn.execute(
                "UPDATE vote_disputes SET disputes_count=disputes_count+1, last_dispute_at=? WHERE lobby_id=?",
                (datetime.now().isoformat(), lid)
            )
            conn.commit()
            cur = conn.execute("SELECT disputes_count FROM vote_disputes WHERE lobby_id=?", (lid,))
            r = cur.fetchone()
            return r["disputes_count"] if r else 0
        finally:
            conn.close()

    def reset_dispute_count(self, lid: int) -> None:
        """🆕 يصفّر عدّاد الاختلافات (لو اللاعبين صوتوا صح)."""
        conn = self.conn()
        try:
            conn.execute("DELETE FROM vote_disputes WHERE lobby_id=?", (lid,))
            conn.commit()
        finally:
            conn.close()

    def get_streak(self, uid: int, gid: int) -> Dict[str, int]:
        """🆕 يرجع win_streak, lose_streak, max_win_streak للاعب."""
        conn = self.conn()
        try:
            cur = conn.execute(
                "SELECT win_streak, lose_streak, max_win_streak FROM players WHERE user_id=? AND guild_id=?",
                (uid, gid)
            )
            r = cur.fetchone()
            if r:
                return {
                    "win_streak": r["win_streak"],
                    "lose_streak": r["lose_streak"],
                    "max_win_streak": r["max_win_streak"]
                }
            return {"win_streak": 0, "lose_streak": 0, "max_win_streak": 0}
        finally:
            conn.close()



# ============================================================
# HELPERS
# ============================================================

db = Database()
active_lobby_messages: Dict[int, int] = {}     # message_id -> lobby_id
channel_cleanup_timers: Dict[int, asyncio.Task] = {}   # lobby_id -> asyncio.Task
lobby_timeout_timers: Dict[int, asyncio.Task] = {}     # lobby_id -> asyncio.Task
vote_timeout_timers: Dict[int, asyncio.Task] = {}      # lobby_id -> asyncio.Task
# dm_room_sessions: تم حذفه (استخدام Modal بدلاً من DM)


def get_rank_info(points: int) -> Dict[str, Any]:
    cur = 1
    for rid, rd in RANKS.items():
        if points >= rd["min_points"]:
            cur = rid
    return RANKS.get(cur, RANKS[1])


def extract_original_nickname(nickname: Optional[str]) -> str:
    """🆕 محسّن: يزيل أي صيغة Rank من الاسم.
    يدعم الصيغ القديمة [Lv.X]، Rank X، والجديدة RANK X |.
    لو الاسم يصير فاضي بعد التنظيف → يرجّع "Player" كـ fallback."""
    if not nickname:
        return "Player"
    import re
    # إزالة أي [Lv.XXX] (صيغة قديمة) من الاسم
    cleaned = re.sub(r"\[Lv\.\d+\]\s*", "", nickname)
    # 🆕 إزالة صيغة Rank X (القديمة)
    cleaned = re.sub(r"Rank\s+\d+\s*", "", cleaned)
    # 🆕 إزالة صيغة RANK X | (الجديدة مثل Apostado)
    cleaned = re.sub(r"RANK\s+\d+\s*\|\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = cleaned.strip()
    # 🆕 fallback آمن لو الاسم فاضي
    return cleaned if cleaned else "Player"


def build_nickname_with_level(original_name: str, level: int) -> str:
    """🆕 يبني الـ nickname بصيغة 'RANK X | Name' (مثل Apostado) ويحترم حد 32 حرف."""
    clean = extract_original_nickname(original_name)
    # 🆕 تأكد إن clean ما يكون فاضي
    if not clean:
        clean = "Player"
    # 🆕 صيغة جديدة: RANK X | Name (مثل Apostado Manager)
    prefix = f"RANK {level} | "
    # لو الـ prefix نفسه أطول من الحد
    if len(prefix) >= NICKNAME_MAX_LENGTH:
        return prefix[:NICKNAME_MAX_LENGTH]
    max_name_len = NICKNAME_MAX_LENGTH - len(prefix)
    truncated = clean[:max_name_len]
    return f"{prefix}{truncated}"


def create_lobby_embed(lobby: Dict[str, Any], guild: discord.Guild) -> discord.Embed:
    """🆕 شكل مطابق لـ Apostado Manager تماماً."""
    mode = lobby.get("game_mode", DEFAULT_MODE)
    mode_info = GAME_MODES.get(mode, GAME_MODES[DEFAULT_MODE])
    team_size = mode_info["team_size"]
    lobby_size = mode_info["lobby_size"]
    mode_emoji = mode_info["emoji"]
    mode_color = mode_info["color"]

    t1c = len(lobby["team1_players"]); t2c = len(lobby["team2_players"])
    total = t1c + t2c

    # 🆕 عنوان مثل Apostado: "🐺 Free Fire 3V3 Match"
    embed = discord.Embed(
        title=f"{mode_emoji} Free Fire {mode.upper()} Match",
        color=mode_color
    )
    # 🆕 نص: Match started by @user
    embed.description = f"Match started by <@{lobby['creator_id']}>"

    # 🆕 عرض اللاعبين بدوائر ملونة (● مثل Apostado)
    t1_text = ""
    for pid in lobby["team1_players"][:team_size]:
        t1_text += f"<@{pid}>\n"
    if not t1_text:
        t1_text = "Empty"

    t2_text = ""
    for pid in lobby["team2_players"][:team_size]:
        t2_text += f"<@{pid}>\n"
    if not t2_text:
        t2_text = "Empty"

    # 🆕 ● بدائرة حمراء للفريق 1، ● بدائرة خضراء للفريق 2
    embed.add_field(name=f"🔴 Team 1 ({t1c}/{team_size})", value=t1_text, inline=True)
    embed.add_field(name=f"🟢 Team 2 ({t2c}/{team_size})", value=t2_text, inline=True)

    # 🆕 Room info (إذا موجود)
    if lobby.get("room_id"):
        embed.add_field(name="🆔 Room ID", value=f"`{lobby['room_id']}`", inline=True)
    if lobby.get("room_code"):
        embed.add_field(name="🔑 Password", value=f"`{lobby['room_code']}`", inline=True)

    embed.set_footer(text=f"Match #{lobby['id']} | {total}/{lobby_size} players")
    return embed


def create_profile_embed(player: Dict[str, Any], member: Optional[discord.Member] = None) -> discord.Embed:
    """🆕 شكل جديد مثل Apostado — Points, Wins, Losses, MVPs, Matches, Organize, Winrate, Rank."""
    level = player.get("level", STARTING_LEVEL)
    kd = round(player["kills"] / max(player["losses"], 1), 2)
    wr = round((player["wins"] / max(player["matches_played"], 1)) * 100, 1)
    # 🆕 Organize = نسبة الانتصارات - نسبة الهزائم
    organize = player["wins"] - player["losses"]

    # 🆕 عنوان: اسم اللاعب + RANK
    embed = discord.Embed(
        title=f"{player['username']}",
        description=f"**RANK #{level}**",
        color=0x2B2D31
    )
    if member:
        embed.set_thumbnail(url=member.display_avatar.url)

    # 🆕 حقول مثل Apostado بالضبط
    embed.add_field(name="POINTS", value=str(player["points"]), inline=True)
    embed.add_field(name="WINS", value=str(player["wins"]), inline=True)
    embed.add_field(name="LOSSES", value=str(player["losses"]), inline=True)
    embed.add_field(name="MVPS", value=str(player["mvps"]), inline=True)
    embed.add_field(name="MATCHES", value=str(player["matches_played"]), inline=True)
    embed.add_field(name="ORGANIZE", value=str(organize), inline=True)
    embed.add_field(name="WINRATE", value=f"{wr}%", inline=True)
    embed.add_field(name="RANK", value=f"#{level}", inline=True)

    # 🆕 Streaks (إضافي)
    win_streak = player.get("win_streak", 0)
    lose_streak = player.get("lose_streak", 0)
    if win_streak >= 3:
        embed.add_field(name="🔥 WIN STREAK", value=str(win_streak), inline=True)
    if lose_streak >= 3:
        embed.add_field(name="❄️ LOSE STREAK", value=str(lose_streak), inline=True)

    embed.set_footer(text=f"Free Fire Bot | {PREFIX}p @user")
    return embed


async def update_leaderboard_channel(guild: discord.Guild) -> None:
    try:
        settings = db.get_guild_settings(guild.id)
        if not settings or not settings.get("leaderboard_channel_id"):
            return
        channel = guild.get_channel(settings["leaderboard_channel_id"])
        if not channel:
            return
        lb = db.get_leaderboard(guild.id, 10)
        embed = discord.Embed(
            title="🏆 Free Fire Leaderboard — Top 10",
            color=COLORS["leaderboard"],
            timestamp=discord.utils.utcnow()
        )
        if not lb:
            embed.description = f"No players yet! Start playing with `{PREFIX}play`"
        else:
            medals = ["🥇", "🥈", "🥉"]; desc = ""
            for i, p in enumerate(lb):
                ri = get_rank_info(p["points"])
                m = medals[i] if i < 3 else f"`#{i+1}`"
                mem = guild.get_member(p["user_id"])
                name = mem.display_name if mem else p["username"]
                level = p.get("level", STARTING_LEVEL)
                desc += f"{m} **{name}** — {ri['emoji']} {ri['name']}\n    📊 {p['points']} pts | 🎮 {p['matches_played']} matches | ✅ {p['wins']}W | 💀 {p['kills']}K | 🏅 RANK {level}\n\n"
            embed.description = desc
        embed.set_footer(text="Auto-updated • Free Fire Bot v3.1 🤖")
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


async def update_member_nickname(member: discord.Member, level: int) -> None:
    """🆕 يطبّق صيغة 'Rank X Name' على نَك العضو.
    - لو الاسم الأصلي مخزن في DB → يستخدمه
    - لو لأ → يستخرجه من member.display_name ويخزّنه
    - يحترم حد 32 حرف
    - يتجاوز الأونر بهدوء (Discord ما يسمح بتغيير نَك الأونر)
    """
    try:
        logger.info(f"update_member_nickname called for {member.id} ({member.display_name}), level={level}")

        # تحقق من الصلاحية
        if not member.guild.me.guild_permissions.manage_nicknames:
            logger.warning(f"❌ Bot lacks 'Manage Nicknames' permission in guild {member.guild.id} — cannot change {member.display_name}'s nickname")
            return

        # ما نقدر نغيّر نَك الأونر (قيد في Discord)
        if member.id == member.guild.owner_id:
            logger.info(f"⚠️ Cannot change nickname for guild owner {member.id} (Discord restriction)")
            return

        # 🆕 H1 fix: استخدم extract_original_nickname على display_name (يحذف "Rank X" prefix)
        original_from_display = extract_original_nickname(member.display_name)
        logger.info(f"  Original name extracted: '{original_from_display}' (from '{member.display_name}')")

        # جلب أو إنشاء player
        player = db.get_or_create_player(member.id, member.guild.id, original_from_display)

        # 🆕 منطق الاسم الأصلي:
        if player.get("original_nickname") and player["original_nickname"] != "Player":
            original = player["original_nickname"]
            logger.info(f"  Using stored original_nickname: '{original}'")
        else:
            original = original_from_display
            db.update_player_stats(member.id, member.guild.id, original_nickname=original)
            logger.info(f"  Stored new original_nickname: '{original}'")

        # بناء النَك الجديد
        new_nick = build_nickname_with_level(original, level)
        logger.info(f"  New nick: '{new_nick}' (current: '{member.display_name}')")

        # طبّق لو مختلف
        if member.display_name != new_nick:
            old_nick = member.display_name
            try:
                await member.edit(nick=new_nick)
                logger.info(f"✅ Updated nickname for {member.id}: '{old_nick}' → '{new_nick}'")
            except discord.Forbidden:
                logger.warning(f"❌ Forbidden to change nickname for {member.id} (role hierarchy? bot role too low?)")
            except discord.HTTPException as e:
                logger.warning(f"❌ HTTP error changing nickname for {member.id}: {e}")
        else:
            logger.info(f"  Nickname already correct: '{member.display_name}'")
    except Exception as e:
        logger.exception(f"update_member_nickname failed: {e}")


def cleanup_lobby_memory(lobby_id: int) -> None:
    """🆕 ينظّف كل الـ dicts الخاصة بلوبي معين."""
    # active_lobby_messages
    to_remove = [k for k, v in active_lobby_messages.items() if v == lobby_id]
    for k in to_remove:
        del active_lobby_messages[k]
    # timers
    for timer_dict in (channel_cleanup_timers, lobby_timeout_timers, vote_timeout_timers):
        if lobby_id in timer_dict:
            try:
                timer_dict[lobby_id].cancel()
            except Exception:
                pass
            del timer_dict[lobby_id]
    # 🆕 vote metadata (نشّفها بعد انتهاء الماتش)
    try:
        db.delete_vote_metadata(lobby_id)
    except Exception as e:
        logger.warning(f"Failed to delete vote metadata for lobby {lobby_id}: {e}")


# ============================================================
# 🤖 AUTO CHANNEL CREATION
# ============================================================

async def create_match_channels(guild: discord.Guild, lobby: Dict[str, Any], lobby_id: int) -> Dict[str, Any]:
    """🆕 ينشئ Category جديدة لكل ماتش + فويسات + شات عام.
    كل ماتش يحصل على كاتيجوري مستقلة."""
    mode = lobby.get("game_mode", DEFAULT_MODE)
    mode_info = GAME_MODES.get(mode, GAME_MODES[DEFAULT_MODE])

    # 🆕 دائماً أنشئ كاتيجوري جديدة لهذا الماتش
    cat_name = f"🎮 Match #{lobby_id}"
    cat_overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False, connect=False),
        guild.me: discord.PermissionOverwrite(read_messages=True, connect=True, manage_channels=True, manage_messages=True)
    }
    cat = await guild.create_category(cat_name, overwrites=cat_overwrites)
    logger.info(f"📁 Created new category '{cat_name}' for lobby {lobby_id}")

    # 🆕 صلاحيات الفريقين على الشات العام
    general_overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False, connect=False),
        guild.me: discord.PermissionOverwrite(read_messages=True, connect=True, manage_channels=True, manage_messages=True)
    }
    for pid in lobby["team1_players"] + lobby["team2_players"]:
        m = guild.get_member(pid)
        if m:
            general_overwrites[m] = discord.PermissionOverwrite(
                read_messages=True, connect=True, speak=True, stream=True,
                send_messages=True, view_channel=True
            )

    # 🆕 صلاحيات فويس Team 1 (Team 1 فقط)
    t1_overwrites = {
        guild.default_role: discord.PermissionOverwrite(connect=False),
        guild.me: discord.PermissionOverwrite(connect=True, manage_channels=True)
    }
    for pid in lobby["team1_players"]:
        m = guild.get_member(pid)
        if m:
            t1_overwrites[m] = discord.PermissionOverwrite(connect=True, speak=True, stream=True)

    # 🆕 صلاحيات فويس Team 2 (Team 2 فقط)
    t2_overwrites = {
        guild.default_role: discord.PermissionOverwrite(connect=False),
        guild.me: discord.PermissionOverwrite(connect=True, manage_channels=True)
    }
    for pid in lobby["team2_players"]:
        m = guild.get_member(pid)
        if m:
            t2_overwrites[m] = discord.PermissionOverwrite(connect=True, speak=True, stream=True)

    # 🆕 إنشاء الفويسات بأسماء مثل Apostado
    t1_voice = await guild.create_voice_channel(
        f"『🎮』︱ᴛᴇᴀᴍ ɪ", category=cat, overwrites=t1_overwrites
    )
    t2_voice = await guild.create_voice_channel(
        f"『🎮』︱ᴛᴇᴀᴍ ɪɪ", category=cat, overwrites=t2_overwrites
    )
    # 🆕 شات عام واحد فقط
    general_text = await guild.create_text_channel(
        f"💬・general-chat", category=cat, overwrites=general_overwrites,
        topic=f"General chat for Match #{lobby_id}"
    )

    db.save_match_channels(lobby_id, guild.id, cat.id, t1_voice.id, general_text.id, t2_voice.id, general_text.id)

    return {
        "category": cat,
        "team1_voice": t1_voice, "team1_text": general_text,
        "team2_voice": t2_voice, "team2_text": general_text,
        "general_text": general_text,
        "used_existing_voices": False
    }


async def delete_match_channels(guild: discord.Guild, lobby_id: int) -> None:
    """حذف كل القنوات بعد الماتش.
    🆕 محسّن: استخدام get_match_voices (ترجع list) بشكل صحيح.
    """
    mc = db.get_match_channels(lobby_id)
    if not mc:
        return

    # 🆕 كل الفويسات المسموحة في الجيلد (list)
    allowed_voices = db.get_match_voices(guild.id)  # returns list of ints

    # لو الفويسات محددة من الأدمن → ما نحذفها، بس نرجع صلاحياتها
    for voice_key in ["team1_voice_id", "team2_voice_id"]:
        voice_id = mc.get(voice_key)
        if voice_id and voice_id in allowed_voices:
            voice_ch = guild.get_channel(voice_id)
            if voice_ch:
                try:
                    await voice_ch.set_permissions(guild.default_role, overwrite=None)
                    # احذف صلاحيات الأعضاء المحددين اللي أضفناها
                    for target in list(voice_ch.overwrites.keys()):
                        if isinstance(target, discord.Member) and target != guild.me:
                            try:
                                await voice_ch.set_permissions(target, overwrite=None)
                            except discord.HTTPException:
                                pass
                except discord.Forbidden:
                    logger.warning(f"Missing permissions to reset voice overwrites in guild {guild.id}")

    # احذف الشاتات بس
    text_ids = [mc.get("team1_text_id"), mc.get("team2_text_id")]
    for cid in text_ids:
        if cid:
            ch = guild.get_channel(cid)
            if ch:
                try:
                    await ch.delete()
                except (discord.NotFound, discord.Forbidden) as e:
                    logger.warning(f"Failed to delete text channel {cid}: {e}")

    # 🆕 C8 fix: احذف الفويسات غير المسموحة أولاً (قبل التحقق من الكاتيجوري)
    for voice_key in ["team1_voice_id", "team2_voice_id"]:
        voice_id = mc.get(voice_key)
        if voice_id and voice_id not in allowed_voices:
            ch = guild.get_channel(voice_id)
            if ch:
                try:
                    await ch.delete()
                except (discord.NotFound, discord.Forbidden) as e:
                    logger.warning(f"Failed to delete voice channel {voice_id}: {e}")

    # احذف الكاتيجوري لو فاضي (بعد حذف الفويسات)
    cat_id = mc.get("category_id")
    if cat_id:
        cat = guild.get_channel(cat_id)
        if cat and isinstance(cat, discord.CategoryChannel):
            remaining = [ch for ch in cat.channels if ch.id not in allowed_voices]
            if len(remaining) == 0:
                try:
                    await cat.delete()
                except (discord.NotFound, discord.Forbidden) as e:
                    logger.warning(f"Failed to delete category {cat_id}: {e}")

    db.delete_match_channels_record(lobby_id)


# ============================================================
# 🤖 AUTO ROOM INFO — DM لصاحب الروم
# ============================================================


async def auto_trigger_vote(lobby_id: int, guild: discord.Guild) -> None:
    """🤖 يبدأ التصويت تلقائياً عندما يفرغ الفويسات ويرسل أزرار."""
    try:
        lobby = db.get_lobby(lobby_id)
        if not lobby or lobby["status"] not in ("started",):
            return

        db.update_lobby_status(lobby_id, "voting")
        lobby = db.get_lobby(lobby_id)

        creator_id = lobby["creator_id"]
        first_joiner_id = lobby.get("first_joiner_id")

        mc = db.get_match_channels(lobby_id)
        if not mc:
            return

        vote_embed = discord.Embed(
            title="🗳️ وقت التصويت! — Match #" + str(lobby_id),
            description=f"الماتش خلص! صوّتوا للفريق الرابح:\n\n"
                       f"👥 **الناخبين:**\n"
                       f"👑 <@{creator_id}> (صاحب الروم)\n"
                       f"🎯 {'<@'+str(first_joiner_id)+'>' if first_joiner_id else 'N/A'} (أول داخل)\n\n"
                       f"⏱️ **الوقت مفتوح** — صوّتوا براحتكم!",
            color=COLORS["vote"]
        )

        t1m = " ".join([f"<@{p}>" for p in lobby["team1_players"]])
        t2m = " ".join([f"<@{p}>" for p in lobby["team2_players"]])
        vote_embed.add_field(name="🟠 Team 1", value=t1m, inline=True)
        vote_embed.add_field(name="🔵 Team 2", value=t2m, inline=True)

        view = VoteView(lobby_id, creator_id, first_joiner_id)

        # 🆕 C2 fix: إنشاء VoteView منفصل لكل رسالة (clone() غير موجود في discord.py)
        t1_text = guild.get_channel(mc["team1_text_id"])
        if t1_text:
            await t1_text.send(
                f"<@{creator_id}> {'<@'+str(first_joiner_id)+'>' if first_joiner_id else ''}",
                embed=vote_embed, view=VoteView(lobby_id, creator_id, first_joiner_id)
            )

        t2_text = guild.get_channel(mc["team2_text_id"])
        if t2_text:
            await t2_text.send(
                f"<@{creator_id}> {'<@'+str(first_joiner_id)+'>' if first_joiner_id else ''}",
                embed=vote_embed, view=VoteView(lobby_id, creator_id, first_joiner_id)
            )

        orig_channel = guild.get_channel(lobby["channel_id"])
        vote_msg_id = None
        if orig_channel:
            vote_msg = await orig_channel.send(
                f"<@{creator_id}> {'<@'+str(first_joiner_id)+'>' if first_joiner_id else ''} 🗳️",
                embed=vote_embed, view=VoteView(lobby_id, creator_id, first_joiner_id)
            )
            db.set_vote_message(lobby_id, vote_msg.id)
            vote_msg_id = vote_msg.id

        # 🆕 حفظ vote metadata عشان نسترجعوها بعد restart البوت
        db.save_vote_metadata(lobby_id, creator_id, first_joiner_id, vote_msg_id)
        logger.info(f"💾 Saved vote metadata for lobby {lobby_id}: creator={creator_id}, first_joiner={first_joiner_id}, msg={vote_msg_id}")

        # 🆕 ما فيه auto timeout — التصويت مفتوح indefinitely
        # 🆕 فقط نظّف timer القديم لو موجود
        if lobby_id in vote_timeout_timers:
            vote_timeout_timers[lobby_id].cancel()
            if lobby_id in vote_timeout_timers:
                del vote_timeout_timers[lobby_id]
    except Exception as e:
        logger.exception(f"auto_trigger_vote failed: {e}")


async def auto_vote_timeout(lobby_id: int, guild: discord.Guild) -> None:
    """🆕 تم تعطيل timeout — التصويت مفتوح indefinitely.
    نخلي الدالة بس للتوافق مع الكود القديم."""
    # 🆕 ما نسوي شي — التصويت مفتوح
    logger.info(f"ℹ️ Vote timeout disabled for lobby {lobby_id} (vote is open indefinitely)")
    return


# ============================================================
# 🤖 AUTO LOBBY TIMEOUT — إلغاء اللوبيات القديمة
# ============================================================

async def auto_lobby_timeout(lobby_id: int, guild: discord.Guild) -> None:
    """🤖 يلغي اللوبي لو انتظر أكثر من 30 دقيقة."""
    try:
        await asyncio.sleep(LOBBY_TIMEOUT_SECONDS)

        lobby = db.get_lobby(lobby_id)
        if not lobby or lobby["status"] != "waiting":
            return

        db.update_lobby_status(lobby_id, "cancelled")
        cleanup_lobby_memory(lobby_id)

        ch = guild.get_channel(lobby["channel_id"])
        if ch:
            await ch.send(embed=discord.Embed(
                title="⏰ Lobby Cancelled — Timeout",
                description=f"Lobby #{lobby_id} تم إلغاؤه تلقائياً لأنه انتظر أكثر من 30 دقيقة بدون أن يمتلي.",
                color=COLORS["warning"]
            ))
    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.exception(f"auto_lobby_timeout failed: {e}")


# ============================================================
# 🤖 VOICE STATE MONITOR — كشف فراغ الفويسات
# ============================================================

async def check_voice_and_trigger_vote(lobby_id: int, guild: discord.Guild) -> None:
    """🤖 🆕 تم تعطيله — التصويت الآن يبدأ بعد 5 دقايق من بداية الماتش.
    نخلي الدالة بس للتوافق مع الكود القديم."""
    logger.info(f"ℹ️ Voice-empty vote trigger disabled for lobby {lobby_id} (using 5-min delay instead)")
    return


async def auto_trigger_vote_after_delay(lobby_id: int, guild: discord.Guild) -> None:
    """🆕 يبدأ التصويت بعد 5 دقايق (VOTE_DELAY_AFTER_MATCH) من بداية الماتش.
    التصويت مفتوح indefinitely — ما فيه timeout."""
    try:
        logger.info(f"⏱️ Vote will start in {VOTE_DELAY_AFTER_MATCH} seconds for lobby {lobby_id}")
        await asyncio.sleep(VOTE_DELAY_AFTER_MATCH)

        lobby = db.get_lobby(lobby_id)
        if not lobby:
            logger.warning(f"Lobby {lobby_id} not found — skipping vote trigger")
            return
        if lobby["status"] != "started":
            logger.info(f"Lobby {lobby_id} status is '{lobby['status']}' (not 'started') — skipping vote trigger")
            return

        # 🆕 أرسل تنبيه قبل التصويت بدقيقة
        try:
            orig_channel = guild.get_channel(lobby["channel_id"])
            if orig_channel:
                await orig_channel.send(embed=discord.Embed(
                    title="⏰ التصويت يبدأ بعد دقيقة!",
                    description=(
                        f"الماتش #{lobby_id} — التصويت رح يبدأ بعد **دقيقة من الحين**.\n"
                        f"👥 **الناخبون:**\n"
                        f"👑 <@{lobby['creator_id']}>\n"
                        f"🎯 {'<@' + str(lobby.get('first_joiner_id')) + '>' if lobby.get('first_joiner_id') else 'N/A'}\n\n"
                        f"💡 جهّزوا أنفسكم — رح تختارون الفريق الرابح."
                    ),
                    color=COLORS["warning"]
                ))
            await asyncio.sleep(60)  # انتظر دقيقة
        except Exception as e:
            logger.warning(f"Failed to send pre-vote warning: {e}")

        # تحقق مرة أخيرة
        lobby = db.get_lobby(lobby_id)
        if not lobby or lobby["status"] != "started":
            logger.info(f"Lobby {lobby_id} no longer 'started' — skipping vote trigger")
            return

        logger.info(f"🗳️ Starting vote for lobby {lobby_id} (after 5-min delay)")
        await auto_trigger_vote(lobby_id, guild)
    except asyncio.CancelledError:
        logger.info(f"Vote trigger cancelled for lobby {lobby_id}")
    except Exception as e:
        logger.exception(f"auto_trigger_vote_after_delay failed: {e}")


# ============================================================
# 🆕 ROOM INFO MODAL (مثل Apostado — نافذة إدخال الآيدي والكود)
# ============================================================

class RoomInfoModal(discord.ui.Modal, title="📋 Enter Room Information"):
    """🆕 Modal لإدخال Room ID + Password + Private Key (مثل Apostado)."""
    room_id_input = discord.ui.TextInput(
        label="Room ID (Numbers Only)",
        placeholder="Enter the game room ID (numbers only)",
        required=True,
        min_length=3,
        max_length=20
    )
    password_input = discord.ui.TextInput(
        label="Password (Optional)",
        placeholder="Enter room password if any",
        required=False,
        max_length=20
    )
    private_key_input = discord.ui.TextInput(
        label="Private Match Key (Optional)",
        placeholder="If set, players must enter this key to join",
        required=False,
        max_length=20
    )

    def __init__(self, lobby_id: int, guild_id: int):
        super().__init__(timeout=300)
        self.lobby_id = lobby_id
        self.guild_id = guild_id

    async def on_submit(self, interaction: discord.Interaction):
        try:
            room_id = str(self.room_id_input.value).strip()
            password = str(self.password_input.value).strip() if self.password_input.value else ""
            private_key = str(self.private_key_input.value).strip() if self.private_key_input.value else ""

            # تحقق إن اللوبي ما زال نشط
            lobby = db.get_lobby(self.lobby_id)
            if not lobby or lobby["status"] != "started":
                await interaction.response.send_message(
                    "❌ الماتش ما عاد نشط!", ephemeral=True
                )
                return

            # تحقق إن المستخدم هو صاحب الروم
            if lobby["creator_id"] != interaction.user.id:
                await interaction.response.send_message(
                    "❌ بس صاحب الروم يقدر يدخل المعلومات!", ephemeral=True
                )
                return

            # حفظ room info
            db.set_room_info(self.lobby_id, room_id, password, private_key if private_key else None)

            # إرسال المعلومات للاعبين
            guild = bot.get_guild(self.guild_id)
            if guild:
                mc = db.get_match_channels(self.lobby_id)
                if mc:
                    general_text = guild.get_channel(mc["team1_text_id"])  # نفس الشات العام
                    if general_text:
                        all_players = lobby["team1_players"] + lobby["team2_players"]
                        mentions = " ".join([f"<@{pid}>" for pid in all_players])

                        # 🆕 لو فيه Private Key → أرسل رسالة مقفولة + زر Enter Key
                        if private_key:
                            locked_embed = discord.Embed(
                                title="🔒 Private Match",
                                description=(
                                    f"**This is a private match!**\n\n"
                                    f"🔐 لعرض الـ Room Info، يجب إدخال الـ Private Key.\n"
                                    f"اضغط الزر بالأسفل لإدخال المفتاح."
                                ),
                                color=COLORS["warning"]
                            )
                            enter_key_view = EnterKeyView(self.lobby_id, self.guild_id, private_key)
                            await general_text.send(mentions, embed=locked_embed, view=enter_key_view)
                        else:
                            # 🆕 ما فيه Private Key → أرسل Room Info مباشرة
                            embed = discord.Embed(
                                title="📡 Room Info",
                                description=(
                                    f"**Room ID:** `{room_id}`\n"
                                    f"**Password:** `{password or 'لا يوجد'}`\n\n"
                                    f"ادخلوا بسرعة! 🔥"
                                ),
                                color=COLORS["auto"]
                            )
                            await general_text.send(mentions, embed=embed)

            await interaction.response.send_message(
                embed=discord.Embed(
                    title="✅ Room Info Sent!",
                    description=(
                        f"ID: `{room_id}` | Code: `{password or 'N/A'}`\n"
                        + (f"🔒 Private Key: `{private_key}`\n" if private_key else "")
                        + f"🗳️ التصويت رح يبدأ الآن!"
                    ),
                    color=COLORS["success"]
                ),
                ephemeral=True
            )

            # أطلق التصويت مباشرة بعد room info
            logger.info(f"🗳️ Room info submitted via Modal for lobby {self.lobby_id} — starting vote NOW")
            asyncio.create_task(auto_trigger_vote(self.lobby_id, guild))

        except Exception as e:
            logger.exception(f"RoomInfoModal on_submit failed: {e}")
            try:
                await interaction.response.send_message(
                    f"❌ صار خطأ: {e}", ephemeral=True
                )
            except discord.HTTPException:
                pass


# ============================================================
# 🆕 ENTER ROOM INFO BUTTON (يفتح الـ Modal)
# ============================================================

class EnterRoomInfoView(discord.ui.View):
    """🆕 زر 'Enter Room Info' يفتح Modal (مثل Apostado)."""
    def __init__(self, lobby_id: int, guild_id: int, creator_id: int):
        super().__init__(timeout=None)
        self.lobby_id = lobby_id
        self.guild_id = guild_id
        self.creator_id = creator_id

    @discord.ui.button(label="📋 Enter Room Info", style=discord.ButtonStyle.primary, custom_id="enter_room_info_btn")
    async def enter_room_info_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        # تحقق إن المستخدم هو صاحب الروم
        if interaction.user.id != self.creator_id:
            await interaction.response.send_message(
                f"❌ بس صاحب الروم يقدر يدخل المعلومات! صاحب الروم: <@{self.creator_id}>",
                ephemeral=True
            )
            return
        # افتح الـ Modal
        await interaction.response.send_modal(RoomInfoModal(self.lobby_id, self.guild_id))


# ============================================================
# 🆕 PRIVATE KEY MODAL (للاعبين اللي يبون يدخلون الماتش الخاص)
# ============================================================

class PrivateKeyModal(discord.ui.Modal, title="🔑 Enter Private Match Key"):
    """🆕 Modal لإدخال الـ Private Key عشان يشوف اللاعب الـ Room Info."""
    key_input = discord.ui.TextInput(
        label="Private Match Key",
        placeholder="Enter the private match key",
        required=True,
        min_length=1,
        max_length=20
    )

    def __init__(self, lobby_id: int, guild_id: int, private_key: str):
        super().__init__(timeout=120)
        self.lobby_id = lobby_id
        self.guild_id = guild_id
        self.private_key = private_key

    async def on_submit(self, interaction: discord.Interaction):
        try:
            entered_key = str(self.key_input.value).strip()
            if entered_key == self.private_key:
                # ✅ المفتاح صحيح → اعرض Room Info
                lobby = db.get_lobby(self.lobby_id)
                if lobby:
                    room_id = lobby.get("room_id", "N/A")
                    password = lobby.get("room_code", "N/A")
                    embed = discord.Embed(
                        title="📡 Room Info",
                        description=(
                            f"**Room ID:** `{room_id}`\n"
                            f"**Password:** `{password or 'لا يوجد'}`\n"
                            f"**Private Key:** `{self.private_key}`\n\n"
                            f"ادخل بسرعة! 🔥"
                        ),
                        color=COLORS["success"]
                    )
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                else:
                    await interaction.response.send_message("❌ الماتش ما عاد نشط!", ephemeral=True)
            else:
                # ❌ المفتاح خاطئ
                await interaction.response.send_message(
                    embed=discord.Embed(
                        title="❌ Wrong Key",
                        description="المفتاح اللي دخلت غير صحيح!",
                        color=COLORS["error"]
                    ),
                    ephemeral=True
                )
        except Exception as e:
            logger.exception(f"PrivateKeyModal on_submit failed: {e}")


# ============================================================
# 🆕 ENTER KEY BUTTON (للاعبين اللي يبون يشوفون الـ Room Info)
# ============================================================

class EnterKeyView(discord.ui.View):
    """🆕 زر 'Enter Key' للاعبين عشان يدخلون الـ Private Key."""
    def __init__(self, lobby_id: int, guild_id: int, private_key: str):
        super().__init__(timeout=None)
        self.lobby_id = lobby_id
        self.guild_id = guild_id
        self.private_key = private_key

    @discord.ui.button(label="🔑 Enter Key to View Room Info", style=discord.ButtonStyle.secondary, custom_id="enter_key_btn")
    async def enter_key_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        # تحقق إن المستخدم في الماتش
        lobby = db.get_lobby(self.lobby_id)
        if not lobby:
            await interaction.response.send_message("❌ الماتش ما عاد نشط!", ephemeral=True)
            return
        all_players = lobby["team1_players"] + lobby["team2_players"]
        if interaction.user.id not in all_players:
            await interaction.response.send_message(
                "❌ ما أنت في هالماتش!",
                ephemeral=True
            )
            return
        # افتح الـ Modal
        await interaction.response.send_modal(PrivateKeyModal(self.lobby_id, self.guild_id, self.private_key))


# ============================================================
# 🆕 LOBBY BUTTONS VIEW (Join Team 1/2, Leave, Cancel Game)
# ============================================================

class LobbyButtonsView(discord.ui.View):
    """🆕 أزرار الانضمام للفريق (مثل Apostado)."""
    def __init__(self, lobby_id: int, creator_id: int, guild_id: int):
        super().__init__(timeout=None)
        self.lobby_id = lobby_id
        self.creator_id = creator_id
        self.guild_id = guild_id

    @discord.ui.button(label="Join Team 1", style=discord.ButtonStyle.danger, custom_id="join_team1_btn")
    async def join_team1_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._handle_join(interaction, "team1")

    @discord.ui.button(label="Join Team 2", style=discord.ButtonStyle.success, custom_id="join_team2_btn")
    async def join_team2_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._handle_join(interaction, "team2")

    @discord.ui.button(label="Leave", style=discord.ButtonStyle.secondary, custom_id="leave_lobby_btn")
    async def leave_lobby_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        uid = interaction.user.id
        # امسح اللاعب من اللوبي
        removed = db.remove_player_from_lobby(self.lobby_id, uid)
        if removed:
            lobby = db.get_lobby(self.lobby_id)
            if lobby:
                embed = create_lobby_embed(lobby, interaction.guild)
                try:
                    await interaction.message.edit(embed=embed, view=self)
                except discord.HTTPException:
                    pass
            await interaction.response.send_message(
                f"✅ خرجت من اللوبي #{self.lobby_id}", ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "❌ ما أنت في هاللوبي!", ephemeral=True
            )

    @discord.ui.button(label="Cancel Game", style=discord.ButtonStyle.danger, custom_id="cancel_game_btn")
    async def cancel_game_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        uid = interaction.user.id
        # تحقق إن المستخدم هو صاحب الروم
        lobby = db.get_lobby(self.lobby_id)
        if not lobby:
            await interaction.response.send_message("❌ اللوبي ما موجود!", ephemeral=True)
            return
        creator_id = self.creator_id or lobby["creator_id"]
        if uid != creator_id and not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                f"❌ بس صاحب الروم يقدر يلغي الماتش! صاحب الروم: <@{creator_id}>",
                ephemeral=True
            )
            return
        # ألغِ اللوبي
        db.update_lobby_status(self.lobby_id, "cancelled")
        cleanup_lobby_memory(self.lobby_id)
        await delete_match_channels(interaction.guild, self.lobby_id)
        # أرسل رسالة إلغاء
        mode = lobby.get("game_mode", DEFAULT_MODE).upper()
        cancel_embed = discord.Embed(
            title="❌ Match Cancelled",
            description=(
                f"{mode} match created by <@{creator_id}> was cancelled by the host.\n"
                f"Use `{PREFIX}play` to start a new match."
            ),
            color=COLORS["error"]
        )
        try:
            await interaction.message.edit(embed=cancel_embed, view=None)
        except discord.HTTPException:
            pass
        await interaction.response.send_message("✅ تم إلغاء الماتش.", ephemeral=True)

    async def _handle_join(self, interaction: discord.Interaction, team: str):
        uid = interaction.user.id
        lobby = db.get_lobby(self.lobby_id)
        if not lobby or lobby["status"] != "waiting":
            await interaction.response.send_message(
                "❌ هذا اللوبي ما عاد نشط!", ephemeral=True
            )
            return

        # تحقق إن اللاعب ما في لوبي ثاني
        existing = db.get_player_active_lobby(uid, interaction.guild.id)
        if existing and existing["id"] != self.lobby_id:
            # 🆕 فحص Pending Match
            if existing["status"] == "started" and not existing.get("room_id"):
                await interaction.response.send_message(
                    embed=discord.Embed(
                        title="⏳ Pending Match",
                        description=(
                            f"**You already have a pending match waiting for room info.**\n"
                            f"Please finish it first.\n\n"
                            f"Match #{existing['id']}"
                        ),
                        color=COLORS["warning"]
                    ),
                    ephemeral=True
                )
                return
            await interaction.response.send_message(
                f"❌ أنت في لوبي ثاني #{existing['id']}! اخرج منه أولًا.",
                ephemeral=True
            )
            return

        mode = lobby.get("game_mode", DEFAULT_MODE)
        team_size = GAME_MODES.get(mode, GAME_MODES[DEFAULT_MODE])["team_size"]
        target_team_players = lobby["team1_players"] if team == "team1" else lobby["team2_players"]
        if len(target_team_players) >= team_size:
            await interaction.response.send_message(
                f"❌ الفريق ممتلي! ({len(target_team_players)}/{team_size})",
                ephemeral=True
            )
            return

        # لو في فريق ثاني → احذفه
        other_team = "team2" if team == "team1" else "team1"
        if uid in (lobby["team2_players"] if team == "team1" else lobby["team1_players"]):
            db.remove_player_from_lobby(self.lobby_id, uid)
        # أضفه للفريق
        db.add_player_to_lobby(self.lobby_id, uid, team)
        if uid != lobby["creator_id"]:
            db.set_first_joiner(self.lobby_id, uid)

        # حدّث الـ embed
        lobby = db.get_lobby(self.lobby_id)
        embed = create_lobby_embed(lobby, interaction.guild)
        try:
            await interaction.message.edit(embed=embed, view=self)
        except discord.HTTPException:
            pass

        team_name = "Team 1" if team == "team1" else "Team 2"
        await interaction.response.send_message(
            f"✅ انضممت لـ **{team_name}**!", ephemeral=True
        )

        # 🆕 انقل اللاعب لغرفة انتظار
        waiting_cid = db.get_available_waiting_room(interaction.guild.id, interaction.guild)
        if waiting_cid:
            vc = interaction.guild.get_channel(waiting_cid)
            member = interaction.guild.get_member(uid)
            if vc and member and member.voice:
                try:
                    await member.move_to(vc)
                except (discord.HTTPException, discord.Forbidden):
                    pass

        db.get_or_create_player(uid, interaction.guild.id, interaction.user.display_name)

        # 🆕 طبّق الرتبة على اسم اللاعب
        player = db.get_or_create_player(uid, interaction.guild.id, interaction.user.display_name)
        member = interaction.guild.get_member(uid)
        if member:
            await update_member_nickname(member, player.get("level", STARTING_LEVEL))

        # ===== 🤖 AUTO-START =====
        mode_info = GAME_MODES.get(mode, GAME_MODES[DEFAULT_MODE])
        team_size = mode_info["team_size"]
        lobby_size = mode_info["lobby_size"]
        t1c = len(lobby["team1_players"]); t2c = len(lobby["team2_players"])
        total = t1c + t2c

        if total >= lobby_size and t1c >= team_size and t2c >= team_size and lobby["status"] == "waiting":
            if self.lobby_id in lobby_timeout_timers:
                lobby_timeout_timers[self.lobby_id].cancel()

            db.update_lobby_status(self.lobby_id, "started")
            lobby = db.get_lobby(self.lobby_id)

            # عطّل الأزرار
            for item in self.children:
                item.disabled = True
            try:
                await interaction.message.edit(view=self)
            except discord.HTTPException:
                pass

            # أنشئ قنوات الماتش
            try:
                channels = await create_match_channels(interaction.guild, lobby, self.lobby_id)
            except Exception as e:
                logger.exception(f"Error creating match channels for lobby {self.lobby_id}: {e}")
                channels = None

            if not channels:
                db.update_lobby_status(self.lobby_id, "cancelled")
                cleanup_lobby_memory(self.lobby_id)
                await interaction.channel.send(embed=discord.Embed(
                    title="❌ فشل بدء الماتش",
                    description=f"ما قدرت أنشئ قنوات الماتش. اللوبي #{self.lobby_id} أُلغي.",
                    color=COLORS["error"]
                ))
                return

            # أرسل رسالة Match Ready! (مثل Apostado)
            t1m = " ".join([f"<@{pid}>" for pid in lobby["team1_players"]])
            t2m = " ".join([f"<@{pid}>" for pid in lobby["team2_players"]])
            ready_embed = discord.Embed(
                title="✅ Match Ready!",
                description=f"Moving players to voice channels...",
                color=COLORS["success"],
                timestamp=discord.utils.utcnow()
            )
            await interaction.channel.send(embed=ready_embed)

            # اعرض الأزرار + Enter Room Info
            start_embed = discord.Embed(
                title=f"🎮 {mode_info['emoji']} الماتش بدأ تلقائياً! — {mode.upper()}",
                description=f"Lobby #{self.lobby_id} ممتلي! يلا نلعب 🔥",
                color=COLORS["auto"]
            )
            start_embed.add_field(name="🟠 Team 1", value=t1m, inline=True)
            start_embed.add_field(name="🔵 Team 2", value=t2m, inline=True)
            if channels:
                start_embed.add_field(
                    name="📢 القنوات",
                    value=(
                        f"🔴 <#{channels['team1_voice'].id}>\n"
                        f"🔵 <#{channels['team2_voice'].id}>\n"
                        f"💬 <#{channels['team1_text'].id}>"
                    ),
                    inline=False
                )
            # 🆕 أضف زر Enter Room Info (لصاحب الروم)
            enter_room_view = EnterRoomInfoView(self.lobby_id, interaction.guild.id, lobby["creator_id"])
            await interaction.channel.send(embed=start_embed, view=enter_room_view)

            # نقل اللاعبين للفويسات
            if channels:
                for pid in lobby["team1_players"]:
                    m = interaction.guild.get_member(pid)
                    if m and m.voice:
                        try: await m.move_to(channels["team1_voice"])
                        except (discord.HTTPException, discord.Forbidden): pass
                for pid in lobby["team2_players"]:
                    m = interaction.guild.get_member(pid)
                    if m and m.voice:
                        try: await m.move_to(channels["team2_voice"])
                        except (discord.HTTPException, discord.Forbidden): pass

            # أرسل رسالة في الشات العام
            if channels:
                try:
                    await channels["team1_text"].send(
                        f"🎮 **الماتش بدأ!** {t1m} {t2m}\n📡 صاحب الروم يضغط زر **Enter Room Info**!"
                    )
                except discord.HTTPException as e:
                    logger.warning(f"Failed to send team messages: {e}")


# ============================================================
# VOTE BUTTON VIEW (PERSISTENT)
# ============================================================

class VoteView(discord.ui.View):
    """🆕 Persistent View — يستعيد الأزرار بعد الريستارت."""

    def __init__(self, lobby_id: Optional[int] = None, creator_id: Optional[int] = None, first_joiner_id: Optional[int] = None):
        # 🆕 timeout=None يعني indefinitely (مفتوح)
        super().__init__(timeout=None)
        self.lobby_id = lobby_id
        self.creator_id = creator_id
        self.first_joiner_id = first_joiner_id

    @discord.ui.button(label="🟠 Team 1", style=discord.ButtonStyle.danger, custom_id="vote_team1")
    async def vote_team1(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._handle_vote(interaction, "team1")

    @discord.ui.button(label="🔵 Team 2", style=discord.ButtonStyle.primary, custom_id="vote_team2")
    async def vote_team2(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._handle_vote(interaction, "team2")

    async def _handle_vote(self, interaction: discord.Interaction, vote_choice: str):
        uid = interaction.user.id

        # 🆕 استرجع lobby_id من interaction.message.id أو self.lobby_id
        lobby_id = self.lobby_id
        if lobby_id is None and interaction.message:
            # 🆕 لو البوت اتعاد تشغيله، self.lobby_id يكون None
            # استرجع lobby_id من message_id
            lobby_id = db.get_lobby_id_by_message(interaction.message.id)

        if lobby_id is None:
            await interaction.response.send_message(f"❌ ما أقدر أحدد اللوبي! جرب استخدام `{PREFIX}votewin` يدوياً.", ephemeral=True)
            logger.warning(f"VoteView: Could not determine lobby_id for message {interaction.message.id if interaction.message else 'None'}")
            return

        lobby = db.get_lobby(lobby_id)

        if not lobby or lobby["status"] != "voting":
            await interaction.response.send_message("❌ هذا التصويت ما عاد فعال!", ephemeral=True)
            return

        # 🆕 استرجع creator_id و first_joiner_id من DB (لو self.creator_id = None)
        creator_id = self.creator_id
        first_joiner_id = self.first_joiner_id
        if creator_id is None:
            metadata = db.get_vote_metadata(lobby_id)
            if metadata:
                creator_id = metadata["creator_id"]
                first_joiner_id = metadata["first_joiner_id"]
            else:
                # fallback: استخدم بيانات اللوبي
                creator_id = lobby["creator_id"]
                first_joiner_id = lobby.get("first_joiner_id")

        logger.info(f"🗳️ Vote attempt by {uid} for lobby {lobby_id} (choice: {vote_choice})")
        logger.info(f"  creator_id={creator_id}, first_joiner_id={first_joiner_id}")

        if uid != creator_id and uid != first_joiner_id:
            await interaction.response.send_message("❌ ما عندك صلاحية التصويت! فقط صاحب الروم وأول داخل.", ephemeral=True)
            return

        if db.has_voted(lobby_id, uid):
            await interaction.response.send_message("❌ صوتيت من قبل!", ephemeral=True)
            return

        db.cast_vote(lobby_id, uid, vote_choice)
        wd = "🟠 Team 1" if vote_choice == "team1" else "🔵 Team 2"
        await interaction.response.send_message(f"✅ صوّت لـ **{wd}**!", ephemeral=True)
        logger.info(f"✅ Vote recorded: {uid} → {vote_choice} for lobby {lobby_id}")

        votes = db.get_votes(lobby_id)
        if len(votes) >= 2:
            vote1 = votes[0]["vote"]
            vote2 = votes[1]["vote"]

            if lobby_id in vote_timeout_timers:
                vote_timeout_timers[lobby_id].cancel()

            if vote1 == vote2:
                # 🆕 اتفقوا → صفّر عدّاد الاختلافات
                db.reset_dispute_count(lobby_id)
                wd_name = "🟠 Team 1" if vote1 == "team1" else "🔵 Team 2"
                result_embed = discord.Embed(
                    title="✅ الاتفاق تم!",
                    description=f"الاثنين صوتوا لـ **{wd_name}**! النتيجة تُحسب تلقائياً 🎉",
                    color=COLORS["success"]
                )
                await interaction.channel.send(embed=result_embed)
                logger.info(f"🏆 Both voted same ({vote1}) — calling process_match_result for lobby {lobby_id}")
                await process_match_result(interaction.guild, lobby_id, vote1, interaction.channel)
            else:
                # 🆕 disagreement: زيادة العدّاد والتحقق من الحد
                logger.info(f"⚠️ Disagreement: {vote1} vs {vote2} for lobby {lobby_id}")
                disputes_count = db.increment_dispute_count(lobby_id)
                logger.info(f"  Disputes count: {disputes_count}/{MAX_DISPUTES}")

                if disputes_count >= MAX_DISPUTES:
                    # 🆕 وصل 3 اختلافات → استدعِ الأدمن
                    await interaction.channel.send(embed=discord.Embed(
                        title=f"❌ وصلتم الحد الأقصى من الاختلافات ({MAX_DISPUTES})",
                        description=(
                            f"بعد {MAX_DISPUTES} محاولات تصويت بدون اتفاق، تم استدعاء الأدمن لحل الخلاف.\n\n"
                            f"💡 الأدمن يستخدم:\n"
                            f"`{PREFIX}resolve {lobby_id} team1`\nأو\n`{PREFIX}resolve {lobby_id} team2`"
                        ),
                        color=COLORS["error"]
                    ))
                    await auto_dispute_alert(lobby_id, interaction.guild, interaction.channel)
                else:
                    # 🆕 ما وصل 3 بعد → امسح الأصوات وخلّيهم يعيدون التصويت
                    db.clear_votes(lobby_id)
                    remaining = MAX_DISPUTES - disputes_count
                    await interaction.channel.send(embed=discord.Embed(
                        title=f"⚠️ اختلاف في التصويت ({disputes_count}/{MAX_DISPUTES})",
                        description=(
                            f"صاحب الروم وأول داخل اختلفوا في النتيجة!\n\n"
                            f"🗳️ **الرجاء إعادة التصويت** (باقي {remaining} محاولة).\n"
                            f"❌ لو وصلتم {MAX_DISPUTES} اختلافات → رح ينادى الأدمن.\n\n"
                            f"💡 **الناخبون:**\n"
                            f"👑 <@{creator_id}>\n"
                            f"🎯 {'<@' + str(first_joiner_id) + '>' if first_joiner_id else 'N/A'}"
                        ),
                        color=COLORS["warning"]
                    ))
                    # 🆕 أعد إرسال أزرار التصويت
                    vote_embed = discord.Embed(
                        title=f"🗳️ إعادة التصويت — Match #{lobby_id}",
                        description=(
                            f"اضغطوا الأزرار للتصويت للفريق الرابح:\n\n"
                            f"👥 **الناخبون:**\n"
                            f"👑 <@{creator_id}>\n"
                            f"🎯 {'<@' + str(first_joiner_id) + '>' if first_joiner_id else 'N/A'}\n\n"
                            f"⏱️ الوقت مفتوح — صوّتوا براحتكم."
                        ),
                        color=COLORS["vote"]
                    )
                    t1m = " ".join([f"<@{p}>" for p in lobby["team1_players"]])
                    t2m = " ".join([f"<@{p}>" for p in lobby["team2_players"]])
                    vote_embed.add_field(name="🟠 Team 1", value=t1m, inline=True)
                    vote_embed.add_field(name="🔵 Team 2", value=t2m, inline=True)
                    await interaction.channel.send(
                        f"<@{creator_id}> {'<@' + str(first_joiner_id) + '>' if first_joiner_id else ''} 🗳️",
                        embed=vote_embed,
                        view=VoteView(lobby_id, creator_id, first_joiner_id)
                    )

            for item in self.children:
                item.disabled = True
            try:
                await interaction.message.edit(view=self)
            except discord.HTTPException:
                pass


async def auto_dispute_alert(lobby_id: int, guild: discord.Guild, channel: Optional[discord.TextChannel] = None) -> None:
    """🤖 بينق Owner تلقائياً عند الاختلاف."""
    try:
        lobby = db.get_lobby(lobby_id)
        if not lobby:
            return

        owner = guild.owner
        owner_mention = owner.mention if owner else "Server Owner"

        co_owners = []
        for m in guild.members:
            if m.id != guild.owner_id and m.guild_permissions.administrator and not m.bot:
                co_owners.append(m)

        co_owners_mentions = " ".join([m.mention for m in co_owners[:3]]) if co_owners else ""

        votes = db.get_votes(lobby_id)
        vote_details = ""
        for v in votes:
            wd = "🟠 Team 1" if v["vote"] == "team1" else "🔵 Team 2"
            vote_details += f"<@{v['user_id']}> → **{wd}**\n"

        dispute_embed = discord.Embed(
            title="⚠️ اختلاف في النتيجة! — Match #" + str(lobby_id),
            description=f"حدث اختلاف في التصويت!\n\n{vote_details}\n🔔 **الأونر يحل الخلاف:**",
            color=COLORS["dispute"]
        )
        dispute_embed.add_field(
            name="🔧 حل الخلاف",
            value=f"`{PREFIX}resolve {lobby_id} team1`\nأو\n`{PREFIX}resolve {lobby_id} team2`",
            inline=False
        )

        ping_text = f"{owner_mention} {co_owners_mentions}"
        # 🆕 H14 fix: لو ما في channel، استخدم lobby channel الأصلي
        if not channel:
            ch = guild.get_channel(lobby["channel_id"]) if lobby else None
            channel = ch
        if channel:
            await channel.send(ping_text, embed=dispute_embed)
        else:
            logger.error(f"Could not send dispute alert for lobby {lobby_id} — no channel")
    except Exception as e:
        logger.exception(f"auto_dispute_alert failed: {e}")


# ============================================================
# REMATCH VIEW (PERSISTENT)
# ============================================================

class RematchView(discord.ui.View):
    """🆕 Persistent View — يستعيد الزر بعد الريستارت."""

    def __init__(self, lobby_id: Optional[int] = None, game_mode: Optional[str] = None,
                 guild_id: Optional[int] = None, original_players: Optional[List[int]] = None):
        super().__init__(timeout=120)
        self.lobby_id = lobby_id
        self.game_mode = game_mode or DEFAULT_MODE
        self.guild_id = guild_id
        self.original_players = original_players or []
        self.accepted: set = set()

    @discord.ui.button(label="🔄 Rematch", style=discord.ButtonStyle.success, custom_id="rematch_btn")
    async def rematch_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        uid = interaction.user.id
        if uid not in self.original_players:
            await interaction.response.send_message("❌ ما كنت في الماتش هذا!", ephemeral=True)
            return

        self.accepted.add(uid)

        await interaction.response.send_message(
            f"✅ <@{uid}> وافق على الإعادة! ({len(self.accepted)}/{len(self.original_players)})",
            ephemeral=False
        )

        if len(self.accepted) >= len(self.original_players) // 2 + 1:
            guild = interaction.guild
            mode_info = GAME_MODES.get(self.game_mode, GAME_MODES[DEFAULT_MODE])

            # 🆕 H4 fix: استخدم play channel بدل match channel (channel رح يتحذف)
            play_channels = db.get_play_channels(guild.id)
            stable_channel_id = play_channels[0] if play_channels else interaction.channel.id

            lid = db.create_lobby(guild.id, self.original_players[0], stable_channel_id, mode=self.game_mode)

            for i, pid in enumerate(self.original_players):
                if i == 0:
                    continue
                team = "team1" if i < len(self.original_players) // 2 else "team2"
                db.add_player_to_lobby(lid, pid, team)

            # 🆕 H3 fix: re-fetch lobby بعد إضافة كل اللاعبين
            lobby = db.get_lobby(lid)

            # أرسل embed اللوبي للـ play channel (مو match channel)
            target_channel = guild.get_channel(stable_channel_id) or interaction.channel
            embed = create_lobby_embed(lobby, guild)
            # 🆕 استخدم LobbyButtonsView بدل التفاعلات
            view = LobbyButtonsView(lid, self.original_players[0] if self.original_players else None, guild.id)
            msg = await target_channel.send(embed=embed, view=view)
            db.update_lobby_message(lid, msg.id)
            active_lobby_messages[msg.id] = lid

            lobby_timeout_timers[lid] = asyncio.create_task(auto_lobby_timeout(lid, guild))

            await target_channel.send(embed=discord.Embed(
                title="🔄 Rematch Created!",
                description=f"Lobby #{lid} — {mode_info['emoji']} {self.game_mode.upper()}",
                color=COLORS["success"]
            ))

            # 🆕 H5 fix: auto-start لو اللوبي ممتلي
            team_size = mode_info["team_size"]
            if (len(lobby["team1_players"]) >= team_size and
                len(lobby["team2_players"]) >= team_size and
                lobby["status"] == "waiting"):
                try:
                    # إلغاء timeout
                    if lid in lobby_timeout_timers:
                        lobby_timeout_timers[lid].cancel()
                    db.update_lobby_status(lid, "started")
                    # إنشاء قنوات الماتش
                    channels = await create_match_channels(guild, lobby, lid)
                    # نقل اللاعبين
                    if channels:
                        for pid in lobby["team1_players"]:
                            m = guild.get_member(pid)
                            if m and m.voice:
                                try: await m.move_to(channels["team1_voice"])
                                except (discord.HTTPException, discord.Forbidden): pass
                        for pid in lobby["team2_players"]:
                            m = guild.get_member(pid)
                            if m and m.voice:
                                try: await m.move_to(channels["team2_voice"])
                                except (discord.HTTPException, discord.Forbidden): pass
                    # 🆕 ابدأ التصويت بعد 5 دقايق من بداية الماتش
                    # 🆕 معطّل: التصويت يبدأ بعد room info (مو بعد 5 دقايق)
                    # asyncio.create_task(auto_trigger_vote_after_delay(lid, guild))
                    await target_channel.send(embed=discord.Embed(
                        title=f"🎮 Rematch Auto-Started — Lobby #{lid}",
                        color=COLORS["success"]
                    ))
                except Exception as e:
                    logger.exception(f"Rematch auto-start failed: {e}")

            for item in self.children:
                item.disabled = True
            try:
                await interaction.message.edit(view=self)
            except discord.HTTPException:
                pass


# ============================================================
# PROCESS MATCH RESULT
# ============================================================

async def process_match_result(guild: discord.Guild, lobby_id: int, winner_team: str,
                                channel: Optional[discord.TextChannel] = None) -> None:
    """🤖 يحسب النتيجة + يحدث المستوى + يغير الاسم + يعرض إعادة."""
    try:
        logger.info(f"🏆 process_match_result STARTED — lobby={lobby_id}, winner={winner_team}")
        lobby = db.get_lobby(lobby_id)
        if not lobby:
            logger.warning(f"❌ Lobby {lobby_id} not found!")
            return
        # 🆕 C6 fix: منع المعالجة المزدوجة — لو اللوبي مكتمل خلاص، اطلع
        if lobby["status"] == "completed":
            logger.warning(f"process_match_result called on already-completed lobby {lobby_id} — skipping")
            return

        logger.info(f"  Team1 players: {lobby['team1_players']}")
        logger.info(f"  Team2 players: {lobby['team2_players']}")
        logger.info(f"  Winner team: {winner_team}")

        db.update_lobby_status(lobby_id, "completed")
        db.create_match_result(
            lobby_id, winner_team,
            len(lobby["team1_players"]) if winner_team == "team1" else 0,
            len(lobby["team2_players"]) if winner_team == "team2" else 0
        )

        # 🆕 نقاط حسب حجم الماتش (1v1 أقل، 4v4 أعلى)
        game_mode = lobby.get("game_mode", DEFAULT_MODE)
        mode_points = MATCH_POINTS_BY_MODE.get(game_mode, MATCH_POINTS)
        wp = mode_points["win"]
        lp = mode_points["lose"]
        wt = lobby["team1_players"] if winner_team == "team1" else lobby["team2_players"]
        lt = lobby["team2_players"] if winner_team == "team1" else lobby["team1_players"]

        logger.info(f"  Game mode: {game_mode} → +{wp} pts/win, +{lp} pts/lose")
        logger.info(f"  Winners: {wt} (+{wp} pts each)")
        logger.info(f"  Losers: {lt} (+{lp} pts each)")

        for pid in wt:
            p = db.get_player(pid, guild.id)
            if p:
                # 🆕 تحديث streak: زيادة win_streak + تصفير lose_streak
                new_win_streak = p.get("win_streak", 0) + 1
                new_lose_streak = 0
                new_max_win_streak = max(p.get("max_win_streak", 0), new_win_streak)

                # 🆕 حساب النقاط مع streak bonus
                streak_bonus = 0
                if new_win_streak in STREAK_BONUS:
                    streak_bonus = STREAK_BONUS[new_win_streak]
                    logger.info(f"  🔥 {pid} hit {new_win_streak}-win streak! +{streak_bonus} bonus pts")
                elif new_win_streak >= 10:
                    # مكافأة خاصة لكل انتصار بعد 10
                    streak_bonus = 50
                    logger.info(f"  🔥 {pid} maintaining 10+ win streak! +{streak_bonus} bonus pts")

                total_points = wp + streak_bonus
                new_points = p["points"] + total_points
                rank = db.get_player_rank(new_points)

                # 🆕 حساب تغيير الرتبة حسب streak
                if new_win_streak >= 5:
                    rank_delta = +1  # 🆕 تحسّن 3 رتب (delta=+1 → ينقص 3)
                    rank_change = RANK_CHANGE_WIN_STREAK_5
                elif new_win_streak >= 3:
                    rank_delta = +1  # تحسّن 2 رتب
                    rank_change = RANK_CHANGE_WIN_STREAK_3
                else:
                    rank_delta = +1  # تحسّن رتبة وحدة
                    rank_change = RANK_CHANGE_WIN_NORMAL

                # 🆕 طبّق streak على stats
                db.update_player_stats(
                    pid, guild.id,
                    points=new_points, wins=p["wins"]+1,
                    matches_played=p["matches_played"]+1, rank_pos=rank,
                    win_streak=new_win_streak, lose_streak=new_lose_streak,
                    max_win_streak=new_max_win_streak
                )

                # 🆕 طبّق تغيير الرتبة (delta موجب = تحسّن = ينقص الرقم)
                # نطبّق التغيير مرتين/ثلاث حسب streak
                new_level = p["level"]
                for _ in range(abs(rank_change)):
                    new_level = db.update_player_level(pid, guild.id, +1)

                streak_emoji = "🔥" if new_win_streak >= 3 else ""
                logger.info(f"  ✅ Winner {pid}: points {p['points']}→{new_points} (+{total_points}, streak bonus: {streak_bonus}), wins {p['wins']}→{p['wins']+1}, win_streak {p.get('win_streak', 0)}→{new_win_streak} {streak_emoji}, level {p['level']}→{new_level}")
                m = guild.get_member(pid)
                if m:
                    await update_member_nickname(m, new_level)
                else:
                    logger.warning(f"  ⚠️ Member {pid} not found in guild {guild.id}")
            else:
                logger.warning(f"  ❌ Player {pid} not found in DB!")

        for pid in lt:
            p = db.get_player(pid, guild.id)
            if p:
                # 🆕 تحديث streak: زيادة lose_streak + تصفير win_streak
                new_lose_streak = p.get("lose_streak", 0) + 1
                new_win_streak = 0

                new_points = p["points"] + lp
                rank = db.get_player_rank(new_points)

                # 🆕 حساب تغيير الرتبة حسب lose streak
                if new_lose_streak >= 3:
                    rank_change = RANK_CHANGE_LOSE_STREAK_3  # +2 (تدهور أسرع)
                else:
                    rank_change = RANK_CHANGE_LOSE_NORMAL  # +1

                # 🆕 طبّق streak على stats
                db.update_player_stats(
                    pid, guild.id,
                    points=new_points, losses=p["losses"]+1,
                    matches_played=p["matches_played"]+1, rank_pos=rank,
                    win_streak=new_win_streak, lose_streak=new_lose_streak
                )

                # 🆕 طبّق تغيير الرتبة (delta سالب = تدهور = يزيد الرقم)
                new_level = p["level"]
                for _ in range(abs(rank_change)):
                    new_level = db.update_player_level(pid, guild.id, -1)

                logger.info(f"  ❌ Loser {pid}: points {p['points']}→{new_points}, losses {p['losses']}→{p['losses']+1}, lose_streak {p.get('lose_streak', 0)}→{new_lose_streak}, level {p['level']}→{new_level}")
                m = guild.get_member(pid)
                if m:
                    await update_member_nickname(m, new_level)
                else:
                    logger.warning(f"  ⚠️ Member {pid} not found in guild {guild.id}")
            else:
                logger.warning(f"  ❌ Player {pid} not found in DB!")

        wd = "🟠 Team 1" if winner_team == "team1" else "🔵 Team 2"
        embed = discord.Embed(
            title=f"🏆 Match Result — Lobby #{lobby_id}",
            description=f"**{wd} wins!** 🎉\n🎮 Mode: {game_mode.upper()}",
            color=COLORS["success"]
        )
        t1m = " ".join([f"<@{p}>" for p in lobby["team1_players"]])
        t2m = " ".join([f"<@{p}>" for p in lobby["team2_players"]])

        # 🆕 نحسب الـ streak لكل فريق لعرضه
        def get_streak_text(players, is_winner):
            text = ""
            for pid in players:
                p = db.get_player(pid, guild.id)
                if p:
                    if is_winner:
                        ws = p.get("win_streak", 0)
                        if ws >= 5:
                            text += f"\n🔥 <@{pid}>: {ws} wins streak!"
                        elif ws >= 3:
                            text += f"\n🔥 <@{pid}>: {ws} wins streak"
            return text

        # 🆕 عرض النقاط والـ Rank مع الـ streaks
        t1_streak = get_streak_text(lobby["team1_players"], winner_team == "team1")
        t2_streak = get_streak_text(lobby["team2_players"], winner_team == "team2")

        embed.add_field(
            name=f"🟠 Team 1 {'🏆' if winner_team=='team1' else ''}",
            value=f"{t1m}\n+{wp if winner_team=='team1' else lp} pts | Rank ⬆️{t1_streak}",
            inline=True
        )
        embed.add_field(
            name=f"🔵 Team 2 {'🏆' if winner_team=='team2' else ''}",
            value=f"{t2m}\n+{wp if winner_team=='team2' else lp} pts | Rank ⬆️{t2_streak}",
            inline=True
        )

        # 🆕 شرح نظام النقاط
        embed.add_field(
            name="📊 نظام النقاط",
            value=(
                f"• 🏆 فوز ({game_mode.upper()}): +{wp} نقطة\n"
                f"• ❌ خسارة: +{lp} نقطة\n"
                f"• 🔥 3 wins streak: +10 bonus\n"
                f"• 🔥 5 wins streak: +25 bonus\n"
                f"• 🔥 10 wins streak: +50 bonus"
            ),
            inline=False
        )

        if channel:
            await channel.send(embed=embed)

        await update_leaderboard_channel(guild)

        # 🤖 Offer rematch
        all_players = lobby["team1_players"] + lobby["team2_players"]
        rematch_view = RematchView(lobby_id, lobby.get("game_mode", DEFAULT_MODE), guild.id, all_players)
        rematch_embed = discord.Embed(
            title="🔄 Rematch?",
            description=f"اضغط الزر لو تبي إعادة بنفس اللاعبين!\nاللي يبي يعيد يضغط 🔄 (يحتاج أكثر من النص يوافقون)",
            color=COLORS["info"]
        )
        if channel:
            await channel.send(embed=rematch_embed, view=rematch_view)

        # 🤖 Auto cleanup channels after delay
        await asyncio.sleep(10)
        await delete_match_channels(guild, lobby_id)

        # 🆕 Cleanup memory
        cleanup_lobby_memory(lobby_id)
    except Exception as e:
        logger.exception(f"process_match_result failed: {e}")



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


# ============================================================
# GLOBAL ERROR HANDLER
# ============================================================

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send(embed=discord.Embed(
            title="⏳ انتظر شوي",
            description=f"حاول بعد {error.retry_after:.1f} ثانية.",
            color=COLORS["warning"]
        ))
    elif isinstance(error, commands.CheckFailure):
        await ctx.send(embed=discord.Embed(
            title="❌ ما عندك صلاحية",
            description="هذا الأمر للأدمن فقط!",
            color=COLORS["error"]
        ))
    elif isinstance(error, commands.CommandNotFound):
        await ctx.send(embed=discord.Embed(
            title="❌ أمر غير موجود",
            description=f"اكتب `{PREFIX}help` عشان تشوف كل الأوامر.",
            color=COLORS["error"]
        ))
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(embed=discord.Embed(
            title="❌ ناقص معلومات",
            description=f"اكتب `{PREFIX}help` عشان تشوف طريقة الاستخدام.",
            color=COLORS["error"]
        ))
    elif isinstance(error, commands.BadArgument):
        await ctx.send(embed=discord.Embed(
            title="❌ معلومات غلط",
            description="تأكد من المعلومات وحاول مرة ثانية.",
            color=COLORS["error"]
        ))
    else:
        logger.exception(f"Unhandled command error: {error}")
        await ctx.send(embed=discord.Embed(
            title="❌ خطأ",
            description=f"صار خطأ: `{str(error)}`",
            color=COLORS["error"]
        ))


# ============================================================
# EVENTS
# ============================================================

@bot.event
async def on_ready():
    """🆕 تسجيل Persistent Views + cleanup للقنوات اليتيمة + التحقق من السيرفرات المسموحة."""
    logger.info(f"✅ {bot.user} is online!")
    logger.info(f"📌 Prefix: {PREFIX}")
    logger.info(f"🤖 Version: 3.1 ULTRA AUTO (FIXED)")
    logger.info(f"🏠 Servers: {len(bot.guilds)}")
    logger.info(f"👑 Bot Owner: {BOT_OWNER_NAME} (ID: {BOT_OWNER_ID})")
    logger.info(f"🔒 Guild Whitelist: {'ENABLED' if GUILD_WHITELIST_ENABLED else 'DISABLED'}")

    # 🆕 Register persistent views (لازم قبل bot.run فعلياً، بس نضمن هنا)
    bot.add_view(VoteView())
    bot.add_view(RematchView())

    await bot.change_presence(
        activity=discord.Activity(type=discord.ActivityType.watching, name=f"Free Fire | {PREFIX}play | 🤖 AUTO")
    )

    # 🆕 التحقق من السيرفرات المسموحة — اخرج من السيرفرات غير المسموحة
    if GUILD_WHITELIST_ENABLED:
        logger.info("🔍 Checking guild whitelist...")
        for guild in bot.guilds:
            if not db.is_guild_allowed(guild.id):
                logger.warning(f"🚫 Guild '{guild.name}' ({guild.id}) is NOT in whitelist — leaving!")
                try:
                    # أرسل رسالة قبل الخروج
                    try:
                        first_channel = guild.text_channels[0] if guild.text_channels else None
                        if first_channel:
                            await first_channel.send(embed=discord.Embed(
                                title="🚫 البوت غير مسموح في هذا السيرفر",
                                description=(
                                    f"هذا البوت خاص بـ **{BOT_OWNER_NAME}**.\n"
                                    f"لو تبي تستخدم البوت، تواصل مع المالك."
                                ),
                                color=COLORS["error"]
                            ))
                    except discord.HTTPException:
                        pass
                    await guild.leave()
                    logger.info(f"✅ Left guild '{guild.name}' ({guild.id})")
                except discord.HTTPException as e:
                    logger.warning(f"Failed to leave guild {guild.id}: {e}")

    # 🆕 Cleanup orphan channels عند الإقلاع
    for guild in bot.guilds:
        try:
            orphan_channels = db.get_all_active_match_channels(guild.id)
            if orphan_channels:
                logger.warning(f"🧹 Found {len(orphan_channels)} orphan match channel sets in {guild.name}")
                for mc in orphan_channels:
                    lid = mc["lobby_id"]
                    lobby = db.get_lobby(lid)
                    if lobby and lobby["status"] in ("started", "voting"):
                        # 🆕 C5 fix: بدل ما نتخطى فقط، نعيد جدولة الـ timers المناسبة
                        logger.info(f"⏳ Lobby #{lid} still active — re-arming timers")
                        try:
                            if lobby["status"] == "started":
                                # لو اللوبي بدأ، أعد جدولة فحص الفويسات
                                channel_cleanup_timers[lid] = asyncio.create_task(
                                    check_voice_and_trigger_vote(lid, guild)
                                )
                            elif lobby["status"] == "voting":
                                # لو اللوبي في وضع التصويت، أعد جدولة timeout
                                vote_timeout_timers[lid] = asyncio.create_task(
                                    auto_vote_timeout(lid, guild)
                                )
                        except Exception as te:
                            logger.warning(f"Failed to re-arm timer for lobby #{lid}: {te}")
                        continue
                    try:
                        await delete_match_channels(guild, lid)
                        logger.info(f"🧹 Cleaned orphan channels for lobby #{lid}")
                    except Exception as e:
                        logger.warning(f"Failed to clean orphan lobby #{lid}: {e}")
        except Exception as e:
            logger.exception(f"Cleanup failed for guild {guild.id}: {e}")

    # 🆕 طبّق صيغة 'Rank X Name' على كل الأعضاء الحاليين (في الخلفية)
    asyncio.create_task(sync_all_nicknames_on_startup())


async def sync_all_nicknames_on_startup():
    """🆕 يطبّق صيغة 'Rank X Name' على كل الأعضاء عند بدء البوت.
    يشغل في الخلفية عشان ما يأخرّ on_ready.
    🆕 محسّن: تأخير أقل + رسائل تشخيص أوضح + retry logic."""
    try:
        await asyncio.sleep(5)  # انتظر شوي لين البوت يجهز
        logger.info("🏷️ Syncing nicknames for all members (Rank X Name)...")
        total_updated = 0
        total_failed = 0
        total_skipped = 0
        total_owner = 0

        for guild in bot.guilds:
            try:
                member_count = len(guild.members)
                logger.info(f"📋 Processing guild '{guild.name}' with {member_count} members")

                if member_count == 0:
                    logger.warning(
                        f"⚠️ Guild '{guild.name}' has 0 cached members! "
                        f"Make sure 'Server Members Intent' is enabled in Discord Developer Portal "
                        f"(https://discord.com/developers/applications → Bot → Privileged Gateway Intents)"
                    )
                    continue

                # 🆕 تحقق من صلاحية البوت
                bot_member = guild.me
                if not bot_member.guild_permissions.manage_nicknames:
                    logger.warning(
                        f"❌ Bot lacks 'Manage Nicknames' permission in guild '{guild.name}' "
                        f"({guild.id}) — cannot change any nicknames!"
                    )

                for member in guild.members:
                    if member.bot:
                        total_skipped += 1
                        continue
                    # 🆕 تخطّي الأونر (البوت ما يقدر يغيّر نَكه)
                    if member.id == guild.owner_id:
                        total_owner += 1
                        logger.info(f"👑 Skipping server owner {member.id} ({member.display_name}) — bot cannot change owner's nickname")
                        # 🆕 بس خزّن الرتبة في DB عشان الأونر يقدر يطبّقها بنفسه
                        try:
                            player = db.get_or_create_player(member.id, guild.id, member.display_name)
                            level = player.get("level", STARTING_LEVEL)
                            new_nick = build_nickname_with_level(
                                player.get("original_nickname") or extract_original_nickname(member.display_name),
                                level
                            )
                            logger.info(f"   👑 Owner's target nickname: '{new_nick}' (apply manually: change your nickname)")
                        except Exception as e:
                            logger.warning(f"   Failed to compute owner's nickname: {e}")
                        continue

                    try:
                        player = db.get_or_create_player(member.id, guild.id, member.display_name)
                        level = player.get("level", STARTING_LEVEL)

                        # 🆕 retry logic: جرب مرتين
                        success = False
                        for attempt in range(2):
                            try:
                                await update_member_nickname(member, level)
                                total_updated += 1
                                success = True
                                break
                            except Exception as e:
                                if attempt == 0:
                                    logger.warning(f"  Attempt 1 failed for {member.id}: {e} — retrying...")
                                    await asyncio.sleep(1)
                                else:
                                    raise

                        if not success:
                            total_failed += 1

                        # 🆕 تأخير قصير لتفادي rate limit (0.3s)
                        await asyncio.sleep(0.3)
                    except Exception as e:
                        total_failed += 1
                        logger.warning(f"Failed to sync nickname for {member.id} ({member.display_name}): {e}")
            except Exception as e:
                logger.exception(f"Sync failed for guild {guild.id}: {e}")

        logger.info(
            f"✅ Nickname sync complete — "
            f"✅ Updated: {total_updated} | "
            f"❌ Failed: {total_failed} | "
            f"👑 Owner (skipped): {total_owner} | "
            f"⏭️ Skipped (bots): {total_skipped}"
        )

        # 🆕 لو ما حدّثنا شي، نبه المستخدم
        if total_updated == 0 and total_failed == 0:
            logger.warning(
                "⚠️ No members were updated! Possible reasons:\n"
                "1. 'Server Members Intent' not enabled in Discord Developer Portal\n"
                "2. Bot lacks 'Manage Nicknames' permission\n"
                "3. Bot role is lower than member roles (role hierarchy)\n"
                "4. All members are bot accounts\n"
                "5. Bot is the server owner (cannot change own nickname)"
            )
    except Exception as e:
        logger.exception(f"sync_all_nicknames_on_startup failed: {e}")


async def force_apply_rank_to_all(guild: discord.Guild) -> dict:
    """🆕 يجبر تطبيق الرتبة على كل الأعضاء (للأدمن).
    يرجع dict بإحصائيات النتائج."""
    stats = {
        "total": 0,
        "updated": 0,
        "failed": 0,
        "skipped_bots": 0,
        "skipped_owner": 0,
        "failed_members": []
    }

    bot_member = guild.me
    if not bot_member.guild_permissions.manage_nicknames:
        logger.warning(f"❌ Bot lacks 'Manage Nicknames' permission in guild '{guild.name}'")
        stats["failed"] = -1  # special code: no permission
        return stats

    for member in guild.members:
        stats["total"] += 1
        if member.bot:
            stats["skipped_bots"] += 1
            continue
        if member.id == guild.owner_id:
            stats["skipped_owner"] += 1
            # 🆕 خزّن الرتبة في DB عشان الأونر يقدر يطبّقها بنفسه
            try:
                player = db.get_or_create_player(member.id, guild.id, member.display_name)
                level = player.get("level", STARTING_LEVEL)
                new_nick = build_nickname_with_level(
                    player.get("original_nickname") or extract_original_nickname(member.display_name),
                    level
                )
                stats.setdefault("owner_target_nick", new_nick)
            except Exception:
                pass
            continue

        try:
            player = db.get_or_create_player(member.id, guild.id, member.display_name)
            level = player.get("level", STARTING_LEVEL)

            # retry مرتين
            success = False
            for attempt in range(2):
                try:
                    await update_member_nickname(member, level)
                    stats["updated"] += 1
                    success = True
                    break
                except Exception as e:
                    if attempt == 0:
                        await asyncio.sleep(1)
                    else:
                        raise

            if not success:
                stats["failed"] += 1
                stats["failed_members"].append({"id": member.id, "name": member.display_name})

            await asyncio.sleep(0.3)
        except Exception as e:
            stats["failed"] += 1
            stats["failed_members"].append({"id": member.id, "name": member.display_name, "error": str(e)})
            logger.warning(f"Failed to apply rank to {member.id}: {e}")

    return stats


# 🆕 تعريف is_admin_check مبكراً (عشان كل الأوامر تقدر تستخدمه)
def is_admin_check(ctx):
    """🆕 يتحقق إذا المستخدم أدمن."""
    return ctx.author.guild_permissions.administrator


# 🆕 مالك البوت فقط (aizenx000)
def is_bot_owner_check(ctx):
    """🆕 يتحقق إذا المستخدم هو مالك البوت (aizenx000)."""
    return ctx.author.id == BOT_OWNER_ID


# 🆕 مالك البوت أو أدمن السيرفر
def is_bot_owner_or_admin_check(ctx):
    """🆕 يتحقق إذا المستخدم مالك البوت أو أدمن السيرفر."""
    return ctx.author.id == BOT_OWNER_ID or ctx.author.guild_permissions.administrator


@bot.event
async def on_message(message):
    """🤖 تمرير البوت (لا حاجة لـ DM room info — استخدام Modal)."""
    try:
        # 🆕 DM messages: اسمح بأوامر الـ DM
        if isinstance(message.channel, discord.DMChannel) and not message.author.bot:
            await bot.process_commands(message)
            return
    except Exception as e:
        logger.exception(f"on_message DM handler failed: {e}")

    # 🆕 تقييد البوت: يشتغل فقط في القنوات المسموحة (Waiting Rooms + Bot Commands Channel + DM)
    # تجاهل رسائل البوتات
    if message.author.bot:
        return
    # DM messages دائماً مسموحة (مثل messages رد صاحب الروم بـ room info)
    if isinstance(message.channel, discord.DMChannel):
        await bot.process_commands(message)
        return
    # تحقق إن الرسالة في سيرفر
    if not message.guild:
        return
    # 🆕 تحقق إن القناة مسموحة
    if not db.is_bot_allowed_channel(message.guild.id, message.channel.id):
        # 🆕 استثناء للأدمن: يقدر يستخدم أي أمر في أي قناة (للإعداد)
        is_admin = False
        member = message.guild.get_member(message.author.id)
        if member and member.guild_permissions.administrator:
            is_admin = True
        # 🆕 استثناء للأوامر المسموحة في كل القنوات (general, playerhelp, help, fixrank, myrank)
        content_stripped = message.content.strip()
        # 🆕 استخرج اسم الأمر فقط (مثلاً "!!general something" → "!!general")
        command_name = content_stripped.split()[0] if content_stripped.split() else ""
        allowed_anywhere_commands = [
            f"{PREFIX}general",
            f"{PREFIX}playerhelp",
            f"{PREFIX}help",
            f"{PREFIX}fixrank",
            f"{PREFIX}myrank",
            f"{PREFIX}mylevel",
            f"{PREFIX}p",
        ]
        # 🆕 تحسين: قارن اسم الأمر فقط (مو startswith) عشان نتجنب المطابقات الخاطئة
        is_allowed_anywhere = command_name in allowed_anywhere_commands
        # لو الرسالة تبدأ بالـ prefix
        if content_stripped.startswith(PREFIX):
            if is_admin or is_allowed_anywhere:
                # الأدمن + الأوامر المسموحة → يقدرون يستخدمونها في أي قناة
                await bot.process_commands(message)
                return
            try:
                await message.reply(
                    embed=discord.Embed(
                        title="❌ غير مسموح هنا",
                        description=(
                            f"البوت يشتغل فقط في:\n"
                            f"• 💬 قنوات Play (apostada-play, highlight-play, zelika-play)\n"
                            f"• 💬 غرف الأوامر المحددة\n\n"
                            f"💡 استخدم `{PREFIX}general` لعرض الأوامر المتاحة"
                        ),
                        color=COLORS["error"]
                    ),
                    delete_after=10
                )
            except discord.HTTPException:
                pass
        return

    await bot.process_commands(message)




@bot.event
async def on_guild_join(guild):
    """🆕 عند إضافة البوت لسيرفر جديد — تحقق من القائمة البيضاء."""
    logger.info(f"🏠 Bot added to guild: '{guild.name}' ({guild.id})")

    if GUILD_WHITELIST_ENABLED and not db.is_guild_allowed(guild.id):
        logger.warning(f"🚫 Guild '{guild.name}' ({guild.id}) is NOT in whitelist — leaving!")
        try:
            # أرسل رسالة قبل الخروج
            first_channel = guild.text_channels[0] if guild.text_channels else None
            if first_channel:
                await first_channel.send(embed=discord.Embed(
                    title="🚫 البوت غير مسموح في هذا السيرفر",
                    description=(
                        f"هذا البوت خاص بـ **{BOT_OWNER_NAME}**.\n\n"
                        f"لو تبي تستخدم البوت في سيرفرك، تواصل مع المالك:\n"
                        f"👑 {BOT_OWNER_NAME}\n\n"
                        f"البوت رح يخرج من السيرفر الآن."
                    ),
                    color=COLORS["error"]
                ))
            await asyncio.sleep(2)  # عشان المستخدم يقرأ الرسالة
            await guild.leave()
            logger.info(f"✅ Left unauthorized guild '{guild.name}' ({guild.id})")
        except discord.HTTPException as e:
            logger.warning(f"Failed to leave guild {guild.id}: {e}")
    else:
        logger.info(f"✅ Guild '{guild.name}' ({guild.id}) is allowed")
        # أرسل رسالة ترحيب
        try:
            first_channel = guild.text_channels[0] if guild.text_channels else None
            if first_channel:
                await first_channel.send(embed=discord.Embed(
                    title="🎉 تم إضافة البوت!",
                    description=(
                        f"شكراً لإضافة **{bot.user.name}** لسيرفرك!\n\n"
                        f"👑 **المالك:** {BOT_OWNER_NAME}\n"
                        f"📌 **البادئة:** `{PREFIX}`\n\n"
                        f"**ابدأ بـ:** `{PREFIX}setuprooms`\n"
                        f"**للمساعدة:** `{PREFIX}general`"
                    ),
                    color=COLORS["success"]
                ))
        except discord.HTTPException:
            pass


@bot.event
async def on_member_join(member):
    """🆕 يطبّق صيغة 'Rank X Name' على أي عضو ينضم للسيرفر.
    🆕 محسّن: retry 3 مرات + تأخير قبل التطبيق (member قد لا يكون جاهز)."""
    try:
        # تجاهل البوتات
        if member.bot:
            return

        # 🆕 تأخير قصير قبل التطبيق (عشان Discord يجهز العضو)
        await asyncio.sleep(2)

        # 🆕 H2 fix: استخدم player level الحقيقي (لو اللاعب رجع للسيرفر، يستخدم مستواه المحفوظ)
        player = db.get_or_create_player(member.id, member.guild.id, member.display_name)
        level = player.get("level", STARTING_LEVEL)

        # 🆕 retry logic: جرب 3 مرات
        for attempt in range(3):
            try:
                await update_member_nickname(member, level)
                logger.info(f"✅ on_member_join: Applied Rank {level} to {member.id} ({member.display_name}) on attempt {attempt+1}")
                return
            except Exception as e:
                logger.warning(f"⚠️ on_member_join attempt {attempt+1} failed for {member.id}: {e}")
                await asyncio.sleep(2)

        logger.warning(f"❌ on_member_join: All 3 attempts failed for {member.id} ({member.display_name})")
    except Exception as e:
        logger.exception(f"on_member_join nickname update failed: {e}")


@bot.event
async def on_voice_state_update(member, before, after):
    """🆕 🤖 تم تعطيله — التصويت الآن يبدأ بعد 5 دقايق من بداية الماتش (مو عند فراغ الفويس).
    نخلي الدالة بس للتوافق مع الكود القديم."""
    # 🆕 ما نسوي شي — التصويت يبدأ تلقائياً بعد 5 دقايق من بداية الماتش
    return


# ============================================================
# PLAYER COMMANDS
# ============================================================

async def create_mode_lobby(ctx, mode: str) -> None:
    guild = ctx.guild
    user = ctx.author
    mode_info = GAME_MODES.get(mode, GAME_MODES[DEFAULT_MODE])

    # 🆕 تحقق إن القناة مسموحة (قنوات Play + bot-commands)
    if not db.is_bot_allowed_channel(guild.id, ctx.channel.id):
        embed = discord.Embed(
            title="❌ غير مسموح هنا",
            description=(
                f"البوت يشتغل فقط في:\n"
                f"• 💬 قنوات Play (apostada-play, highlight-play, zelika-play)\n"
                f"• 💬 غرف الأوامر المحددة\n\n"
                f"💡 استخدم `{PREFIX}setcommandschannel #channel` لتحديد غرفة أوامر"
            ),
            color=COLORS["error"]
        )
        await ctx.send(embed=embed, delete_after=15)
        return

    # 🆕 تحقق إن المستخدم في غرفة انتظار
    if not user.voice or not user.voice.channel:
        # تحقق إن القناة الحالية للعضو هي غرفة انتظار
        waiting_rooms = db.get_waiting_rooms(guild.id)
        # محاولة العثور على غرفة انتظار للعضو
        in_waiting = False
        for wr_id in waiting_rooms:
            wr_channel = guild.get_channel(wr_id)
            if wr_channel and user in wr_channel.members:
                in_waiting = True
                break
        if not in_waiting:
            # اعرض رسالة: لازم تكون في غرفة انتظار
            embed = discord.Embed(
                title="⏳ يجب أن تكون في غرفة انتظار",
                description=(
                    f"**عذراً، لازم تكون في إحدى غرف الانتظار عشان تستخدم البوت.**\n\n"
                    f"🔊 **غرف الانتظار المتاحة:**\n"
                    f"• انضم لأي غرفة `⏳・Waiting` في السيرفر\n"
                    f"• بعدها استخدم `{PREFIX}{ctx.command.name}` مرة ثانية\n\n"
                    f"💡 لو ما تقدر تدخل غرفة انتظار، تواصل مع الأدمن."
                ),
                color=COLORS["warning"]
            )
            await ctx.send(embed=embed, delete_after=20)
            return

    existing = db.get_player_active_lobby(user.id, guild.id)
    if existing:
        embed = discord.Embed(
            title="❌ Already in a Lobby",
            description=f"You're in Lobby #{existing['id']}! Leave it first with `{PREFIX}leave`",
            color=COLORS["error"]
        )
        await ctx.send(embed=embed, delete_after=10)
        return
    lid = db.create_lobby(guild.id, user.id, ctx.channel.id, mode=mode)
    lobby = db.get_lobby(lid)
    embed = create_lobby_embed(lobby, guild)
    # 🆕 استخدم LobbyButtonsView بدل التفاعلات
    view = LobbyButtonsView(lid, user.id, guild.id)
    msg = await ctx.send(embed=embed, view=view)
    db.update_lobby_message(lid, msg.id)
    active_lobby_messages[msg.id] = lid
    db.get_or_create_player(user.id, guild.id, user.display_name)

    lobby_timeout_timers[lid] = asyncio.create_task(auto_lobby_timeout(lid, guild))

    settings = db.get_guild_settings(guild.id)
    if settings and settings.get("announcement_role_id"):
        role = guild.get_role(settings["announcement_role_id"])
        if role:
            await ctx.send(f"{role.mention} {mode_info['emoji']} New {mode.upper()} lobby created by {user.mention}!")


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
    guild = ctx.guild
    player = db.get_or_create_player(target.id, guild.id, target.display_name)
    # 🆕 ما نكتب rank_pos كل مرة — فقط لو متغير
    expected_rank = db.get_player_rank(player["points"])
    if player.get("rank_pos") != expected_rank:
        db.update_player_stats(target.id, guild.id, rank_pos=expected_rank)
        player = db.get_player(target.id, guild.id)
    # 🆕 طبّق صيغة 'Rank X Name' على نَك اللاعب
    await update_member_nickname(target, player.get("level", STARTING_LEVEL))
    await ctx.send(embed=create_profile_embed(player, target))


@bot.command(name="top")
@commands.cooldown(1, 10, commands.BucketType.user)
async def top_cmd(ctx):
    guild = ctx.guild
    lb = db.get_leaderboard(guild.id, 10)
    if not lb:
        await ctx.send(embed=discord.Embed(
            title="🏆 Leaderboard",
            description="No players yet!",
            color=COLORS["leaderboard"]
        ))
        return
    embed = discord.Embed(title="🏆 Free Fire Leaderboard — Top 10", color=COLORS["leaderboard"])
    medals = ["🥇", "🥈", "🥉"]; desc = ""
    for i, p in enumerate(lb):
        ri = get_rank_info(p["points"])
        m = medals[i] if i < 3 else f"`#{i+1}`"
        mem = guild.get_member(p["user_id"])
        name = mem.display_name if mem else p["username"]
        level = p.get("level", STARTING_LEVEL)
        desc += f"{m} **{name}** — {ri['emoji']} {ri['name']}\n    📊 {p['points']} pts | 🎮 {p['matches_played']} matches | ✅ {p['wins']}W | 💀 {p['kills']}K | 🏅 RANK {level}\n\n"
    embed.description = desc
    embed.set_footer(text="Free Fire Bot v3.1 🤖")
    await ctx.send(embed=embed)
    await update_leaderboard_channel(guild)


@bot.command(name="matches")
@commands.cooldown(1, 10, commands.BucketType.user)
async def matches_cmd(ctx):
    guild = ctx.guild
    lobbies = db.get_active_lobbies(guild.id)
    if not lobbies:
        await ctx.send(embed=discord.Embed(
            title="🎮 Active Lobbies",
            description=f"No active lobbies. Use `{PREFIX}play`!",
            color=COLORS["info"]
        ))
        return
    embed = discord.Embed(title="🎮 Active Lobbies", color=COLORS["match"])
    for l in lobbies[:5]:
        mode = l.get("game_mode", DEFAULT_MODE)
        mi = GAME_MODES.get(mode, GAME_MODES[DEFAULT_MODE])
        t1c = len(l["team1_players"]); t2c = len(l["team2_players"]); total = t1c + t2c
        cr = guild.get_member(l["creator_id"])
        cn = cr.display_name if cr else "Unknown"
        se = {"waiting": "⏳", "started": "🎮", "voting": "🗳️"}.get(l["status"], "❓")
        embed.add_field(
            name=f"Lobby #{l['id']} {mi['emoji']} {mode.upper()} — {se}",
            value=f"👑 {cn} | 🟠 {t1c}/{mi['team_size']} | 🔵 {t2c}/{mi['team_size']} | 👥 {total}/{mi['lobby_size']}",
            inline=False
        )
    await ctx.send(embed=embed)


@bot.command(name="startmatch")
@commands.cooldown(1, 10, commands.BucketType.user)
async def startmatch_cmd(ctx, lobby_id: int = None):
    if lobby_id is None:
        await ctx.send(embed=discord.Embed(
            title="❌ Missing Lobby ID",
            description=f"Usage: `{PREFIX}startmatch <id>`",
            color=COLORS["error"]
        ))
        return
    lobby = db.get_lobby(lobby_id)
    if not lobby or lobby["guild_id"] != ctx.guild.id:
        await ctx.send(embed=discord.Embed(title="❌ Lobby Not Found", color=COLORS["error"]))
        return
    if lobby["creator_id"] != ctx.author.id and not ctx.author.guild_permissions.administrator:
        await ctx.send(embed=discord.Embed(title="❌ No Permission", color=COLORS["error"]))
        return
    if lobby["status"] != "waiting":
        await ctx.send(embed=discord.Embed(title="❌ Already Started", color=COLORS["error"]))
        return
    t1c = len(lobby["team1_players"]); t2c = len(lobby["team2_players"])
    if t1c < 1 or t2c < 1:
        await ctx.send(embed=discord.Embed(title="❌ Not Enough Players", color=COLORS["error"]))
        return

    # 🆕 H9 fix: إلغاء lobby timeout قبل بدء الماتش
    if lobby_id in lobby_timeout_timers:
        lobby_timeout_timers[lobby_id].cancel()
        if lobby_id in lobby_timeout_timers:
            del lobby_timeout_timers[lobby_id]

    db.update_lobby_status(lobby_id, "started")
    guild = ctx.guild

    # 🆕 H9 fix: تحديث رسالة اللوبي الأصلية لتعكس STARTED
    if lobby.get("message_id"):
        try:
            orig_ch = guild.get_channel(lobby["channel_id"])
            if orig_ch:
                orig_msg = await orig_ch.fetch_message(lobby["message_id"])
                started_lobby = db.get_lobby(lobby_id)
                started_embed = create_lobby_embed(started_lobby, guild)
                started_embed.color = COLORS["success"]
                started_embed.title = f"🎮 Lobby #{lobby_id} ✅ STARTED!"
                await orig_msg.edit(embed=started_embed)
        except discord.HTTPException as e:
            logger.warning(f"Failed to update lobby message: {e}")

    try:
        channels = await create_match_channels(guild, lobby, lobby_id)
    except Exception as e:
        channels = None
        logger.exception(f"create_match_channels failed: {e}")

    # 🆕 C7 fix: rollback لو فشل إنشاء القنوات
    if not channels:
        db.update_lobby_status(lobby_id, "cancelled")
        cleanup_lobby_memory(lobby_id)
        await ctx.send(embed=discord.Embed(
            title="❌ فشل بدء الماتش",
            description=f"ما قدرت أنشئ قنوات الماتش. اللوبي #{lobby_id} أُلغي.",
            color=COLORS["error"]
        ))
        return

    if channels:
        for pid in lobby["team1_players"]:
            m = guild.get_member(pid)
            if m and m.voice:
                try: await m.move_to(channels["team1_voice"])
                except (discord.HTTPException, discord.Forbidden): pass
        for pid in lobby["team2_players"]:
            m = guild.get_member(pid)
            if m and m.voice:
                try: await m.move_to(channels["team2_voice"])
                except (discord.HTTPException, discord.Forbidden): pass
        t1m = " ".join([f"<@{pid}>" for pid in lobby["team1_players"]])
        t2m = " ".join([f"<@{pid}>" for pid in lobby["team2_players"]])
        try:
            await channels["team1_text"].send(f"🎮 **الماتش بدأ!** {t1m}\n📡 البوت بيرسل DM تلقائي لصاحب الروم!")
            await channels["team2_text"].send(f"🎮 **الماتش بدأ!** {t2m}")
        except discord.HTTPException as e:
            logger.warning(f"Failed to send team messages: {e}")
    # 🆕 ابدأ التصويت بعد 5 دقايق من بداية الماتش
    # 🆕 معطّل: التصويت يبدأ بعد room info (مو بعد 5 دقايق)
    # asyncio.create_task(auto_trigger_vote_after_delay(lobby_id, guild))

    embed = discord.Embed(title=f"🎮 Match Started — Lobby #{lobby_id}", color=COLORS["success"])
    t1m = " ".join([f"<@{p}>" for p in lobby["team1_players"]])
    t2m = " ".join([f"<@{p}>" for p in lobby["team2_players"]])
    embed.add_field(name="🟠 Team 1", value=t1m, inline=True)
    embed.add_field(name="🔵 Team 2", value=t2m, inline=True)
    embed.add_field(
        name="🤖 تلقائي",
        value="• DM يرسل لصاحب الروم تلقائياً\n• التصويت يبدأ لما تطلعون من الفويس",
        inline=False
    )
    await ctx.send(embed=embed)


@bot.command(name="leave")
@commands.cooldown(1, 5, commands.BucketType.user)
async def leave_cmd(ctx):
    guild = ctx.guild
    user = ctx.author
    lobby = db.get_player_active_lobby(user.id, guild.id)
    if not lobby:
        await ctx.send(embed=discord.Embed(title="❌ Not in a Lobby", color=COLORS["error"]))
        return
    if lobby["creator_id"] == user.id and lobby["status"] == "waiting":
        total = len(lobby["team1_players"]) + len(lobby["team2_players"])
        if total <= 1:
            db.update_lobby_status(lobby["id"], "cancelled")
            cleanup_lobby_memory(lobby["id"])
            await ctx.send(embed=discord.Embed(
                title="🗑️ Lobby Cancelled",
                description=f"Lobby #{lobby['id']} cancelled.",
                color=COLORS["warning"]
            ))
            return
        # 🆕 H10 fix: لو في لاعبين ثانين، أعِد تعيين الـ creator لأول لاعب باقي
        remaining = [p for p in (lobby["team1_players"] + lobby["team2_players"]) if p != user.id]
        if remaining:
            db.reassign_creator(lobby["id"], remaining[0])
            await ctx.send(embed=discord.Embed(
                title="👑 Creator Reassigned",
                description=f"<@{remaining[0]}> صار صاحب اللوبي #{lobby['id']} الجديد.",
                color=COLORS["info"]
            ))
    db.remove_player_from_lobby(lobby["id"], user.id)
    await ctx.send(embed=discord.Embed(
        title="✅ Left Lobby",
        description=f"You left Lobby #{lobby['id']}",
        color=COLORS["success"]
    ))
    if lobby["message_id"]:
        ch = guild.get_channel(lobby["channel_id"])
        if ch:
            try:
                msg = await ch.fetch_message(lobby["message_id"])
                ul = db.get_lobby(lobby["id"])
                if ul and ul["status"] == "waiting":
                    await msg.edit(embed=create_lobby_embed(ul, guild))
            except discord.HTTPException:
                pass


@bot.command(name="endmatch")
@commands.cooldown(1, 5, commands.BucketType.user)
async def endmatch_cmd(ctx, lobby_id: int = None, winner: str = None):
    if lobby_id is None or winner is None:
        await ctx.send(embed=discord.Embed(
            title="❌ Missing Arguments",
            description=f"Usage: `{PREFIX}endmatch <id> <team1|team2>`\n💡 الأفضل خلوا البوت يعمل كل شي تلقائي!",
            color=COLORS["error"]
        ))
        return
    if not ctx.author.guild_permissions.administrator:
        await ctx.send(embed=discord.Embed(
            title="❌ Admin Only",
            description=f"استخدموا التصويت التلقائي! البوت يبدأه لما تطلعون من الفويس.",
            color=COLORS["error"]
        ))
        return
    winner = winner.lower()
    if winner not in ["team1", "team2"]:
        await ctx.send(embed=discord.Embed(title="❌ Invalid Winner", color=COLORS["error"]))
        return
    lobby = db.get_lobby(lobby_id)
    if not lobby or lobby["status"] not in ("started", "voting"):
        await ctx.send(embed=discord.Embed(title="❌ Match Not Active", color=COLORS["error"]))
        return
    await process_match_result(ctx.guild, lobby_id, winner, ctx.channel)


@bot.command(name="cancelmatch")
@commands.cooldown(1, 5, commands.BucketType.user)
async def cancelmatch_cmd(ctx, lobby_id: int = None):
    if lobby_id is None:
        await ctx.send(embed=discord.Embed(
            title="❌ Missing Lobby ID",
            description=f"Usage: `{PREFIX}cancelmatch <id>`",
            color=COLORS["error"]
        ))
        return
    lobby = db.get_lobby(lobby_id)
    if not lobby:
        await ctx.send(embed=discord.Embed(title="❌ Lobby Not Found", color=COLORS["error"]))
        return
    if lobby["creator_id"] != ctx.author.id and not ctx.author.guild_permissions.administrator:
        await ctx.send(embed=discord.Embed(title="❌ No Permission", color=COLORS["error"]))
        return
    db.update_lobby_status(lobby_id, "cancelled")
    cleanup_lobby_memory(lobby_id)
    await delete_match_channels(ctx.guild, lobby_id)
    await ctx.send(embed=discord.Embed(
        title="🗑️ Match Cancelled",
        description=f"Lobby #{lobby_id} cancelled.",
        color=COLORS["warning"]
    ))


# ============================================================
# MANUAL COMMANDS (for edge cases)
# ============================================================

@bot.command(name="setroom")
@commands.cooldown(1, 5, commands.BucketType.user)
async def setroom_cmd(ctx, room_id: str = None, room_code: str = None):
    """📡 /setroom <id> <code> — يدوي"""
    if room_id is None or room_code is None:
        await ctx.send(embed=discord.Embed(
            title="❌ ناقص معلومات",
            description=f"الاستخدام: `{PREFIX}setroom <room_id> <room_code>`\n💡 **نصيحة:** البوت يرسلك DM تلقائياً يطلب الآيدي! بس رد عليه في الخاص.",
            color=COLORS["error"]
        ))
        return
    guild = ctx.guild
    lobby = db.get_player_active_lobby(ctx.author.id, guild.id)
    if not lobby:
        await ctx.send(embed=discord.Embed(title="❌ ما أنت في ماتش", color=COLORS["error"]))
        return
    if lobby["creator_id"] != ctx.author.id:
        await ctx.send(embed=discord.Embed(title="❌ فقط صاحب الروم", color=COLORS["error"]))
        return
    if lobby["status"] != "started":
        await ctx.send(embed=discord.Embed(title="❌ الماتش ما بدأ بعد", color=COLORS["error"]))
        return

    db.set_room_info(lobby["id"], room_id, room_code)

    mc = db.get_match_channels(lobby["id"])
    if mc:
        for team_key, text_key in [("team1", "team1_text_id"), ("team2", "team2_text_id")]:
            text_ch = guild.get_channel(mc[text_key])
            if text_ch:
                team_players = lobby["team1_players"] if team_key == "team1" else lobby["team2_players"]
                mentions = " ".join([f"<@{pid}>" for pid in team_players])
                embed = discord.Embed(
                    title="📡 Room Info",
                    description=f"**Room ID:** `{room_id}`\n**Room Code:** `{room_code}`\n\nادخلوا! 🔥",
                    color=COLORS["success"]
                )
                await text_ch.send(mentions, embed=embed)

    # 🆕 H11 fix: تحديث رسالة اللوبي الأصلية لإظهار room_id/room_code
    if lobby.get("message_id"):
        try:
            ch = guild.get_channel(lobby["channel_id"])
            if ch:
                msg = await ch.fetch_message(lobby["message_id"])
                updated_lobby = db.get_lobby(lobby["id"])
                await msg.edit(embed=create_lobby_embed(updated_lobby, guild))
        except discord.HTTPException as e:
            logger.warning(f"Failed to update lobby message after setroom: {e}")

    await ctx.send(embed=discord.Embed(
        title="✅ Room Info Set",
        description=f"ID: `{room_id}` | Code: `{room_code}`\n🗳️ التصويت رح يبدأ الآن!",
        color=COLORS["success"]
    ))


@bot.command(name="votewin")
@commands.cooldown(1, 5, commands.BucketType.user)
async def votewin_cmd(ctx, winner: str = None):
    """🗳️ /votewin <team1|team2> — يدوي"""
    if winner is None:
        await ctx.send(embed=discord.Embed(
            title="❌ ناقص فريق",
            description=f"الاستخدام: `{PREFIX}votewin <team1|team2>`\n💡 **نصيحة:** البوت يرسل أزرار تصويت تلقائياً لما تطلعون من الفويس!",
            color=COLORS["error"]
        ))
        return
    winner = winner.lower()
    if winner not in ["team1", "team2"]:
        await ctx.send(embed=discord.Embed(title="❌ فريق غلط", color=COLORS["error"]))
        return
    guild = ctx.guild
    lobby = db.get_player_active_lobby(ctx.author.id, guild.id)
    if not lobby or lobby["status"] not in ("started", "voting"):
        await ctx.send(embed=discord.Embed(title="❌ ما أنت في ماتش نشط", color=COLORS["error"]))
        return

    creator_id = lobby["creator_id"]
    first_joiner_id = lobby.get("first_joiner_id")
    if ctx.author.id != creator_id and ctx.author.id != first_joiner_id:
        await ctx.send(embed=discord.Embed(
            title="❌ ما عندك صلاحية التصويت",
            description="فقط صاحب الروم وأول داخل!",
            color=COLORS["error"]
        ))
        return
    if db.has_voted(lobby["id"], ctx.author.id):
        await ctx.send(embed=discord.Embed(title="❌ صوتيت من قبل!", color=COLORS["error"]))
        return

    db.cast_vote(lobby["id"], ctx.author.id, winner)
    if lobby["status"] == "started":
        db.update_lobby_status(lobby["id"], "voting")

    wd = "🟠 Team 1" if winner == "team1" else "🔵 Team 2"
    await ctx.send(embed=discord.Embed(
        title="🗳️ Vote Recorded",
        description=f"صوّت لـ **{wd}**",
        color=COLORS["vote"]
    ))

    votes = db.get_votes(lobby["id"])
    if len(votes) >= 2:
        vote1 = votes[0]["vote"]; vote2 = votes[1]["vote"]
        if lobby["id"] in vote_timeout_timers:
            vote_timeout_timers[lobby["id"]].cancel()
        if vote1 == vote2:
            await ctx.send(embed=discord.Embed(
                title="✅ الاتفاق تم!",
                description=f"الاثنين صوتوا لـ **{'Team 1' if vote1=='team1' else 'Team 2'}**!",
                color=COLORS["success"]
            ))
            await process_match_result(guild, lobby["id"], vote1, ctx.channel)
        else:
            await auto_dispute_alert(lobby["id"], guild, ctx.channel)


@bot.command(name="resolve")
@commands.cooldown(1, 5, commands.BucketType.user)
async def resolve_cmd(ctx, lobby_id: int = None, winner: str = None):
    """🔧 /resolve <lobby_id> <team1|team2> — حل الخلاف"""
    if lobby_id is None or winner is None:
        await ctx.send(embed=discord.Embed(
            title="❌ ناقص معلومات",
            description=f"الاستخدام: `{PREFIX}resolve <lobby_id> <team1|team2>`",
            color=COLORS["error"]
        ))
        return
    if not ctx.author.guild_permissions.administrator:
        await ctx.send(embed=discord.Embed(
            title="❌ ما عندك صلاحية",
            description="فقط Owner أو Co-Owner!",
            color=COLORS["error"]
        ))
        return
    winner = winner.lower()
    if winner not in ["team1", "team2"]:
        await ctx.send(embed=discord.Embed(title="❌ فريق غلط", color=COLORS["error"]))
        return
    lobby = db.get_lobby(lobby_id)
    if not lobby or lobby["status"] != "voting":
        await ctx.send(embed=discord.Embed(title="❌ ما في خلاف", color=COLORS["error"]))
        return
    if lobby_id in vote_timeout_timers:
        vote_timeout_timers[lobby_id].cancel()
    await ctx.send(embed=discord.Embed(
        title="⚖️ الخلاف تم حله!",
        description=f"**{ctx.author.mention}** قرر: **{'🟠 Team 1' if winner=='team1' else '🔵 Team 2'}**",
        color=COLORS["success"]
    ))
    await process_match_result(ctx.guild, lobby_id, winner, ctx.channel)


@bot.command(name="mylevel")
@commands.cooldown(1, 5, commands.BucketType.user)
async def mylevel_cmd(ctx, member: discord.Member = None):
    target = member or ctx.author
    guild = ctx.guild
    player = db.get_or_create_player(target.id, guild.id, target.display_name)
    level = player.get("level", STARTING_LEVEL)
    ri = get_rank_info(player["points"])
    embed = discord.Embed(
        title=f"🏅 Rank — {target.display_name}",
        description=f"الـ RANK: **RANK {level}** (1 = الأعلى، 9999 = الأدنى)\nالرتبة: {ri['emoji']} {ri['name']}",
        color=COLORS["profile"]
    )
    embed.add_field(name="📊 النقاط", value=str(player["points"]), inline=True)
    embed.add_field(name="✅ الانتصارات", value=str(player["wins"]), inline=True)
    embed.add_field(name="❌ الهزائم", value=str(player["losses"]), inline=True)
    # 🆕 طبّق الرتبة على النَك عند فتح mylevel
    await update_member_nickname(target, level)
    await ctx.send(embed=embed)


@bot.command(name="fixrank")
@commands.cooldown(1, 5, commands.BucketType.user)
async def fixrank_cmd(ctx, member: discord.Member = None):
    """🔧 /fixrank [@user] — يطبّق الرتبة على الاسم يدوياً"""
    target = member or ctx.author
    guild = ctx.guild
    player = db.get_or_create_player(target.id, guild.id, target.display_name)
    level = player.get("level", STARTING_LEVEL)

    # 🆕 حالة الأونر: البوت ما يقدر يغيّر نَكه، أعطه الرتبة المطلوبة
    if target.id == guild.owner_id:
        original = player.get("original_nickname") or extract_original_nickname(target.display_name)
        target_nick = build_nickname_with_level(original, level)
        await ctx.send(embed=discord.Embed(
            title="👑 Server Owner",
            description=(
                f"{target.mention} → **RANK {level}**\n\n"
                f"⚠️ **أنت الأونر** — البوت ما يقدر يغيّر نَكك تلقائياً (قيد Discord).\n\n"
                f"📝 **النَك المطلوب:** `{target_nick}`\n\n"
                f"**طبّقه يدوياً:**\n"
                f"1. Right-click على اسمك\n"
                f"2. Edit Profile → Nickname\n"
                f"3. الصق: `{target_nick}`\n"
                f"4. Save"
            ),
            color=COLORS["warning"]
        ))
        return

    # طبّق الرتبة
    await update_member_nickname(target, level)

    await ctx.send(embed=discord.Embed(
        title="🔧 Rank Applied",
        description=(
            f"{target.mention} → **RANK {level}**\n\n"
            f"💡 لو ما ظهر الـ Rank بجانب اسمك، تأكد من:\n"
            f"• البوت عنده صلاحية **Manage Nicknames**\n"
            f"• رتبة البوت **أعلى** من رتبتك\n"
            f"• ما أنت الأونر (البوت ما يقدر يغير نَك الأونر)"
        ),
        color=COLORS["success"]
    ))


@bot.command(name="myrank")
@commands.cooldown(1, 5, commands.BucketType.user)
async def myrank_cmd(ctx):
    """📝 /myrank — يعرض نَكك المطلوب (مفيد للأونر)"""
    target = ctx.author
    guild = ctx.guild
    player = db.get_or_create_player(target.id, guild.id, target.display_name)
    level = player.get("level", STARTING_LEVEL)
    original = player.get("original_nickname") or extract_original_nickname(target.display_name)
    target_nick = build_nickname_with_level(original, level)

    is_owner = (target.id == guild.owner_id)

    embed = discord.Embed(
        title="📝 Your Rank",
        description=(
            f"👤 **العضو:** {target.mention}\n"
            f"🏅 **الرتبة:** RANK {level}\n"
            f"📝 **النَك الحالي:** `{target.display_name}`\n"
            f"🎯 **النَك المطلوب:** `{target_nick}`\n"
        ),
        color=COLORS["profile"]
    )

    if is_owner:
        embed.add_field(
            name="👑 تنبيه: أنت الأونر",
            value=(
                f"البوت ما يقدر يغيّر نَكك تلقائياً (قيد Discord).\n"
                f"**طبّقه يدوياً:**\n"
                f"1. Right-click على اسمك → Edit Profile\n"
                f"2. غيّر الـ Nickname لـ: `{target_nick}`\n"
                f"3. Save"
            ),
            inline=False
        )
    elif target.display_name == target_nick:
        embed.add_field(
            name="✅ الحالة",
            value="النَك صحيح، ما يحتاج تغيير.",
            inline=False
        )
    else:
        embed.add_field(
            name="ℹ️ ملاحظة",
            value=f"استخدم `{PREFIX}fixrank` لتطبيق الرتبة تلقائياً.",
            inline=False
        )

    await ctx.send(embed=embed)


@bot.command(name="forcerankall")
@commands.check(is_admin_check)
@commands.cooldown(1, 60, commands.BucketType.guild)
async def forcerankall_cmd(ctx):
    """🚀 /forcerankall — يجبر تطبيق الرتبة على كل الأعضاء (للأدمن)"""
    guild = ctx.guild

    # تأكد إن في أعضاء
    if len(guild.members) == 0:
        await ctx.send(embed=discord.Embed(
            title="❌ ما في أعضاء",
            description=(
                "ما قدرة أجيب قائمة الأعضاء. تأكد من:\n"
                "• **Server Members Intent** مفعّل في Discord Developer Portal\n"
                "  (https://discord.com/developers/applications → Bot → Privileged Gateway Intents)"
            ),
            color=COLORS["error"]
        ))
        return

    # تأكد من صلاحية البوت
    if not guild.me.guild_permissions.manage_nicknames:
        await ctx.send(embed=discord.Embed(
            title="❌ البوت ما عنده صلاحية",
            description="البوت يحتاج صلاحية **Manage Nicknames** عشان يقدر يغيّر النَكات.",
            color=COLORS["error"]
        ))
        return

    # رسالة بدء
    progress_msg = await ctx.send(embed=discord.Embed(
        title="🚀 جاري تطبيق الرتبة على كل الأعضاء...",
        description=f"📊 عدد الأعضاء: {len(guild.members)}\n⏳ المرجو الانتظار...",
        color=COLORS["warning"]
    ))

    # شغّل التطبيق
    stats = await force_apply_rank_to_all(guild)

    # 🆕 حالة عدم وجود صلاحية
    if stats["failed"] == -1:
        await progress_msg.edit(embed=discord.Embed(
            title="❌ البوت ما عنده صلاحية",
            description="البوت يحتاج صلاحية **Manage Nicknames**.",
            color=COLORS["error"]
        ))
        return

    # جهّز رسالة النتيجة
    result_embed = discord.Embed(
        title="✅ تم تطبيق الرتبة على كل الأعضاء",
        description=(
            f"📊 **النتائج:**\n"
            f"• 👥 **الإجمالي:** {stats['total']}\n"
            f"• ✅ **ناجح:** {stats['updated']}\n"
            f"• ❌ **فاشل:** {stats['failed']}\n"
            f"• 👑 **الأونر (تخطّي):** {stats['skipped_owner']}\n"
            f"• 🤖 **بوتات (تخطّي):** {stats['skipped_bots']}"
        ),
        color=COLORS["success"]
    )

    # 🆕 لو فيه أونر، اعرض النَك المطلوب له
    if stats["skipped_owner"] > 0 and "owner_target_nick" in stats:
        result_embed.add_field(
            name="👑 الأونر — طبّق يدوياً",
            value=(
                f"البوت ما يقدر يغيّر نَك الأونر.\n"
                f"📝 **النَك المطلوب:** `{stats['owner_target_nick']}`\n"
                f"**طبّقه يدوياً:** Right-click اسمك → Edit Profile → Nickname"
            ),
            inline=False
        )

    # 🆕 لو فيه فشل، اعرض الأسماء
    if stats["failed"] > 0 and stats["failed_members"]:
        failed_text = ""
        for m in stats["failed_members"][:5]:  # أول 5
            failed_text += f"• <@{m['id']}> ({m.get('name', 'Unknown')})\n"
        if len(stats["failed_members"]) > 5:
            failed_text += f"• ... و {len(stats['failed_members']) - 5} آخرين"
        result_embed.add_field(
            name=f"❌ فشل ({stats['failed']})",
            value=failed_text + f"\n💡 السبب غالباً: role hierarchy (رتبة البوت أقل من رتبتهم)",
            inline=False
        )

    await progress_msg.edit(embed=result_embed)


@bot.command(name="matchinfo")
@commands.cooldown(1, 5, commands.BucketType.user)
async def matchinfo_cmd(ctx, lobby_id: int = None):
    if lobby_id is None:
        await ctx.send(embed=discord.Embed(
            title="❌ ناقص رقم الماتش",
            description=f"الاستخدام: `{PREFIX}matchinfo <lobby_id>`",
            color=COLORS["error"]
        ))
        return
    lobby = db.get_lobby(lobby_id)
    if not lobby:
        await ctx.send(embed=discord.Embed(title="❌ Lobby Not Found", color=COLORS["error"]))
        return
    guild = ctx.guild
    mode = lobby.get("game_mode", DEFAULT_MODE)
    mode_info = GAME_MODES.get(mode, GAME_MODES[DEFAULT_MODE])
    embed = discord.Embed(title=f"📋 Match Info — Lobby #{lobby_id}", color=COLORS["info"])
    t1m = " ".join([f"<@{pid}>" for pid in lobby["team1_players"]]) or "No players"
    t2m = " ".join([f"<@{pid}>" for pid in lobby["team2_players"]]) or "No players"
    embed.add_field(name=f"🟠 Team 1 ({len(lobby['team1_players'])}/{mode_info['team_size']})", value=t1m, inline=True)
    embed.add_field(name=f"🔵 Team 2 ({len(lobby['team2_players'])}/{mode_info['team_size']})", value=t2m, inline=True)
    se = {"waiting": "⏳", "started": "🎮", "voting": "🗳️", "completed": "✅", "cancelled": "❌"}
    embed.add_field(name="📊 الحالة", value=f"{se.get(lobby['status'], '❓')} {lobby['status'].capitalize()}", inline=True)
    embed.add_field(name="👑 صاحب الروم", value=f"<@{lobby['creator_id']}>", inline=True)
    if lobby.get("first_joiner_id"):
        embed.add_field(name="🎯 أول داخل", value=f"<@{lobby['first_joiner_id']}>", inline=True)
    if lobby.get("room_id"):
        embed.add_field(name="🆔 Room ID", value=f"`{lobby['room_id']}`", inline=True)
    if lobby.get("room_code"):
        embed.add_field(name="🔑 Room Code", value=f"`{lobby['room_code']}`", inline=True)
    await ctx.send(embed=embed)



# ============================================================
# ADMIN COMMANDS
# ============================================================

# ============================================================
# 🆕 BOT OWNER COMMANDS (aizenx000 only)
# ============================================================

@bot.command(name="allowguild")
@commands.check(is_bot_owner_check)
async def allowguild_cmd(ctx, guild_id: int = None):
    """➕ /allowguild <guild_id> — إضافة سيرفر للقائمة البيضاء (مالك البوت فقط)"""
    if guild_id is None:
        await ctx.send(embed=discord.Embed(
            title="❌ ناقص ID السيرفر",
            description=f"الاستخدام: `{PREFIX}allowguild <guild_id>`",
            color=COLORS["error"]
        ))
        return
    guild = bot.get_guild(guild_id)
    guild_name = guild.name if guild else f"Unknown ({guild_id})"
    db.add_allowed_guild(guild_id, guild_name, ctx.author.id)
    await ctx.send(embed=discord.Embed(
        title="✅ تمت إضافة السيرفر",
        description=f"**{guild_name}** (`{guild_id}`) أُضيف للقائمة البيضاء.",
        color=COLORS["success"]
    ))


@bot.command(name="removeguild")
@commands.check(is_bot_owner_check)
async def removeguild_cmd(ctx, guild_id: int = None):
    """➖ /removeguild <guild_id> — حذف سيرفر من القائمة البيضاء (مالك البوت فقط)"""
    if guild_id is None:
        await ctx.send(embed=discord.Embed(
            title="❌ ناقص ID السيرفر",
            description=f"الاستخدام: `{PREFIX}removeguild <guild_id>`",
            color=COLORS["error"]
        ))
        return
    success = db.remove_allowed_guild(guild_id)
    if success:
        await ctx.send(embed=discord.Embed(
            title="✅ تم حذف السيرفر",
            description=f"السيرفر `{guild_id}` حُذف من القائمة البيضاء.\n⚠️ البوت رح يطلع من السيرفر تلقائياً.",
            color=COLORS["success"]
        ))
        # 🆕 اخرج من السيرفر
        guild = bot.get_guild(guild_id)
        if guild:
            await guild.leave()
    else:
        await ctx.send(embed=discord.Embed(
            title="❌ السيرفر غير موجود",
            description=f"السيرفر `{guild_id}` ما هو في القائمة البيضاء.",
            color=COLORS["error"]
        ))


@bot.command(name="listguilds")
@commands.check(is_bot_owner_check)
async def listguilds_cmd(ctx):
    """📋 /listguilds — عرض السيرفرات المسموحة (مالك البوت فقط)"""
    guilds = db.get_allowed_guilds()
    embed = discord.Embed(title="📋 السيرفرات المسموحة", color=COLORS["info"])
    if not guilds:
        embed.description = "ما في سيرفرات مسموحة. البوت رح يطلع من أي سيرفر."
    else:
        guild_list = ""
        for i, g in enumerate(guilds, 1):
            guild_list += f"{i}. **{g['guild_name']}** (`{g['guild_id']}`)\n"
        embed.description = guild_list
    embed.set_footer(text=f"👑 Owner: {BOT_OWNER_NAME} | Total: {len(guilds)} guilds")
    await ctx.send(embed=embed)


@bot.command(name="botinfo")
async def botinfo_cmd(ctx):
    """ℹ️ /botinfo — معلومات البوت"""
    embed = discord.Embed(
        title="🤖 معلومات البوت",
        description=(
            f"**اسم البوت:** {bot.user.name}\n"
            f"**الإصدار:** v3.1 ULTRA AUTO\n"
            f"**البارتs:** `{PREFIX}`\n"
            f"**👑 المالك:** {BOT_OWNER_NAME}\n"
            f"**🏠 السيرفرات:** {len(bot.guilds)}\n"
            f"**👥 المستخدمين:** {sum(g.member_count for g in bot.guilds)}\n"
        ),
        color=COLORS["info"]
    )
    embed.add_field(
        name="📊 الإحصائيات",
        value=(
            f"• الأوامر: {len(bot.commands)}\n"
            f"• السيرفرات المسموحة: {len(db.get_allowed_guilds())}"
        ),
        inline=False
    )
    await ctx.send(embed=embed)


@bot.command(name="leaveserver")
@commands.check(is_bot_owner_check)
async def leaveserver_cmd(ctx, guild_id: int = None):
    """🚪 /leaveserver <guild_id> — إخراج البوت من سيرفر (مالك البوت فقط)"""
    if guild_id is None:
        await ctx.send(embed=discord.Embed(
            title="❌ ناقص ID السيرفر",
            description=f"الاستخدام: `{PREFIX}leaveserver <guild_id>`",
            color=COLORS["error"]
        ))
        return
    guild = bot.get_guild(guild_id)
    if not guild:
        await ctx.send(embed=discord.Embed(
            title="❌ السيرفر غير موجود",
            description=f"البوت ما هو في السيرفر `{guild_id}`.",
            color=COLORS["error"]
        ))
        return
    guild_name = guild.name
    await guild.leave()
    await ctx.send(embed=discord.Embed(
        title="🚪 تم الخروج من السيرفر",
        description=f"البوت خرج من **{guild_name}** (`{guild_id}`)",
        color=COLORS["success"]
    ))


@bot.command(name="setup")
@commands.check(is_bot_owner_or_admin_check)
@commands.cooldown(1, 60, commands.BucketType.guild)
async def setup_cmd(ctx):
    """🚀 /setup — ينشئ كل شيء بأمر واحد (مالك البوت أو أدمن فقط)"""
    guild = ctx.guild
    created = []
    errors = []

    # رسالة بدء
    progress_msg = await ctx.send(embed=discord.Embed(
        title="🚀 جاري إنشاء كل شيء...",
        description="⏳ المرجو الانتظار، البوت بينشئ كل القنوات والغرف اللازمة.",
        color=COLORS["warning"]
    ))

    # 🆕 1. أضف السيرفر للقائمة البيضاء تلقائياً (لو المالك هو اللي يشتغل)
    if ctx.author.id == BOT_OWNER_ID:
        db.add_allowed_guild(guild.id, guild.name, ctx.author.id)

    # 2. أنشئ كاتيجوري رئيسي لو ما موجود
    cat_name = "🎮 FREE FIRE"
    cat = discord.utils.get(guild.categories, name=cat_name)
    if not cat:
        cat = await guild.create_category(cat_name,
            overwrites={
                guild.default_role: discord.PermissionOverwrite(read_messages=True),
                guild.me: discord.PermissionOverwrite(manage_channels=True, manage_messages=True)
            })
    db.set_guild_setting(guild.id, "auto_channel_category_id", cat.id)
    created.append(f"📁 {cat_name} (Category)")

    # 3. أنشئ شاتات Play المتعددة (مثل Apostado)
    play_channels_to_create = [
        ("🎮・apostada-play", f"Apostada Play Channel — Use {PREFIX}play here!"),
        ("🎮・highlight-play", f"Highlight Play Channel — Use {PREFIX}play here!"),
        ("🎮・zelika-play", f"Zelika Play Channel — Use {PREFIX}play here!"),
    ]
    for ch_name, ch_topic in play_channels_to_create:
        existing = discord.utils.get(guild.text_channels, name=ch_name)
        if existing:
            db.add_commands_channel(guild.id, existing.id)
            db.add_play_channel(guild.id, existing.id)
            created.append(f"💬 {ch_name} (موجود)")
        else:
            try:
                ch = await guild.create_text_channel(ch_name, category=cat, topic=ch_topic)
                db.add_commands_channel(guild.id, ch.id)
                db.add_play_channel(guild.id, ch.id)
                created.append(f"💬 {ch_name}")
            except discord.HTTPException as e:
                errors.append(f"❌ فشل إنشاء {ch_name}: {e}")

    # 4. أنشئ شاتات إضافية
    extra_channels = [
        ("📊・match-results", "Match Results"),
        ("🏆・leaderboard", "Leaderboard"),
        ("👤・profiles", "Player Profiles"),
        ("📢・expose-cheaters", "Expose Cheaters"),
        ("🚀・ofc-dlls", "Official Deals"),
    ]
    for ch_name, ch_topic in extra_channels:
        existing = discord.utils.get(guild.text_channels, name=ch_name)
        if not existing:
            try:
                ch = await guild.create_text_channel(ch_name, category=cat, topic=ch_topic)
                if "leaderboard" in ch_name:
                    db.set_guild_setting(guild.id, "leaderboard_channel_id", ch.id)
                created.append(f"💬 {ch_name}")
            except discord.HTTPException as e:
                errors.append(f"❌ فشل إنشاء {ch_name}: {e}")

    # 5. أنشئ غرف انتظار متعددة (عامة + خاصة + ستاف)
    # أولاً: احذف القديمة
    existing_rooms = db.get_waiting_rooms(guild.id)
    for old_cid in existing_rooms:
        db.remove_waiting_room(guild.id, old_cid)
        old_ch = guild.get_channel(old_cid)
        if old_ch:
            try:
                await old_ch.delete()
            except (discord.NotFound, discord.Forbidden):
                pass

    # غرف انتظار عامة (5 غرف)
    waiting_general = [
        ("⏳・Waiting 1", None),
        ("⏳・Waiting 2", None),
        ("⏳・Waiting 3", None),
        ("⏳・Waiting 4", None),
        ("⏳・Waiting 5", None),
    ]
    # غرف انتظار خاصة (لأصحاب الرتب العالية)
    waiting_private = [
        ("🔒・Waiting Prv 1", None),
        ("🔒・Waiting Prv 2", None),
        ("🔒・Waiting Prv 3", None),
    ]
    # غرف استثنائية
    waiting_exceptional = [
        ("🔒・Exceptional Waiting 1", None),
        ("🔒・Exceptional Waiting 2", None),
    ]
    # غرف ستاف
    waiting_staff = [
        ("🔒・Waiting Staff", None),
        ("🔒・Waiting Staff 2", None),
    ]

    all_waiting = waiting_general + waiting_private + waiting_exceptional + waiting_staff

    for ch_name, _ in all_waiting:
        existing = discord.utils.get(guild.voice_channels, name=ch_name)
        if existing:
            db.add_waiting_room(guild.id, existing.id)
            created.append(f"🔊 {ch_name} (موجود)")
        else:
            try:
                overwrites = {
                    guild.me: discord.PermissionOverwrite(connect=True, manage_channels=True)
                }
                # لو خاصة أو ستاف → اعملها locked
                if "Prv" in ch_name or "Exceptional" in ch_name or "Staff" in ch_name:
                    overwrites[guild.default_role] = discord.PermissionOverwrite(connect=False)
                ch = await guild.create_voice_channel(ch_name, category=cat, overwrites=overwrites)
                db.add_waiting_room(guild.id, ch.id)
                created.append(f"🔊 {ch_name}")
            except discord.HTTPException as e:
                errors.append(f"❌ فشل إنشاء {ch_name}: {e}")

    # 6. حدّث leaderboard
    try:
        await update_leaderboard_channel(guild)
    except Exception as e:
        logger.warning(f"Failed to update leaderboard: {e}")

    # 7. أرسل رسالة النتيجة
    result_embed = discord.Embed(
        title="✅ تم إنشاء كل شيء بنجاح!",
        description=(
            f"🎉 تم تجهيز السيرفر بالكامل!\n\n"
            f"📊 **النتائج:**\n"
            f"• ✅ تم إنشاء: {len(created)} قناة\n"
            f"• ❌ أخطاء: {len(errors)}"
        ),
        color=COLORS["success"]
    )

    if created:
        created_text = "\n".join([f"✅ {c}" for c in created[:20]])
        if len(created) > 20:
            created_text += f"\n... و {len(created) - 20} أخرى"
        result_embed.add_field(name="📋 القنوات المُنشأة", value=created_text, inline=False)

    if errors:
        errors_text = "\n".join([f"❌ {e}" for e in errors[:5]])
        result_embed.add_field(name="⚠️ أخطاء", value=errors_text, inline=False)

    result_embed.add_field(
        name="🎯 الخطوات التالية",
        value=(
            f"1️⃣ اللاعبون يكتبون `{PREFIX}play` في أحدى قنوات Play\n"
            f"2️⃣ يضغطون الأزرار للانضمام للفريق\n"
            f"3️⃣ البوت ينقلهم لغرف الانتظار تلقائياً\n"
            f"4️⃣ لما يمتلي اللوبي → البوت ينشئ فويسات الماتش\n"
            f"5️⃣ صاحب الروم يدخل الآيدي والكود → التصويت يبدأ\n\n"
            f"**لللاعبين:** `{PREFIX}general` — عرض الأوامر\n"
            f"**للمساعدة:** `{PREFIX}help`"
        ),
        inline=False
    )

    result_embed.set_footer(text=f"👑 Owner: {BOT_OWNER_NAME} | Setup complete!")

    await progress_msg.edit(embed=result_embed)
    logger.info(f"✅ Setup completed for guild {guild.id} by {ctx.author.id}")


@bot.command(name="setuprooms")
@commands.check(is_bot_owner_or_admin_check)
@commands.cooldown(1, 30, commands.BucketType.guild)
async def setuprooms_cmd(ctx):
    """🔄 /setuprooms — اختصار لأمر setup"""
    await setup_cmd(ctx)



@bot.command(name="addvoice")
@commands.check(is_admin_check)
async def addvoice_cmd(ctx, team: str = None, channel: discord.VoiceChannel = None):
    """🔊 /addvoice <team1|team2|any> #voice_channel — أضف فويس مسموح"""
    if not team or not channel:
        await ctx.send(embed=discord.Embed(
            title="📖 Add Voice Help",
            description=f"**الاستخدام:** `{PREFIX}addvoice <team1|team2|any> #voice_channel`\n\n"
                       f"**الأنواع:**\n"
                       f"• `team1` — فويس مخصص لتيم 1 فقط\n"
                       f"• `team2` — فويس مخصص لتيم 2 فقط\n"
                       f"• `any` — فويس لأي تيم (البوت يوزعه تلقائياً)\n\n"
                       f"**أمثلة:**\n"
                       f"• `{PREFIX}addvoice team1 #🔴-Team-1`\n"
                       f"• `{PREFIX}addvoice team2 #🔵-Team-2`\n"
                       f"• `{PREFIX}addvoice any #Match-Voice`",
            color=COLORS["info"]
        ))
        return

    team = team.lower()
    if team not in ["team1", "team2", "any"]:
        await ctx.send(embed=discord.Embed(
            title="❌ نوع غلط",
            description="النوع لازم يكون `team1` أو `team2` أو `any`!",
            color=COLORS["error"]
        ))
        return

    success = db.add_match_voice(ctx.guild.id, team, channel.id)
    if success:
        team_name = {"team1": "🟠 Team 1", "team2": "🔵 Team 2", "any": "🔄 أي تيم"}[team]
        await ctx.send(embed=discord.Embed(
            title="✅ تمت إضافة الفويس!",
            description=f"{team_name} → {channel.mention}\n\nالبوت ب يستخدم هالفويس للماتشات بدل ما ينشئ فويسات جديدة!",
            color=COLORS["success"]
        ))
    else:
        await ctx.send(embed=discord.Embed(
            title="❌ الفويس موجود من قبل",
            description=f"{channel.mention} مضاف من قبل!",
            color=COLORS["error"]
        ))


@bot.command(name="removevoice")
@commands.check(is_admin_check)
async def removevoice_cmd(ctx, channel: discord.VoiceChannel = None):
    """🔇 /removevoice #voice_channel — شيل فويس من المسموحة"""
    if not channel:
        await ctx.send(embed=discord.Embed(
            title="❌ ناقص فويس",
            description=f"الاستخدام: `{PREFIX}removevoice #voice_channel`",
            color=COLORS["error"]
        ))
        return

    success = db.remove_match_voice(ctx.guild.id, channel.id)
    if success:
        await ctx.send(embed=discord.Embed(
            title="✅ تم حذف الفويس",
            description=f"{channel.mention} ما عاد مسموح. البوت ب ينشئ فويسات جديدة.",
            color=COLORS["success"]
        ))
    else:
        await ctx.send(embed=discord.Embed(
            title="❌ الفويس ما كان مسموح",
            description=f"{channel.mention} ما هو في القائمة!",
            color=COLORS["error"]
        ))


@bot.command(name="listvoices")
@commands.check(is_admin_check)
async def listvoices_cmd(ctx):
    """📋 /listvoices — عرض الفويسات المسموحة"""
    guild = ctx.guild
    voices = db.get_all_match_voices_info(guild.id)

    embed = discord.Embed(title="🔊 الفويسات المسموحة", color=COLORS["info"])

    if not voices:
        embed.description = f"ما في فويسات محددة! البوت ينشئ فويسات جديدة تلقائياً.\n\nأضف فويسات: `{PREFIX}addvoice <team1|team2|any> #voice_channel`"
    else:
        t1_list = ""; t2_list = ""; any_list = ""
        for v in voices:
            ch = guild.get_channel(v["channel_id"])
            ch_name = ch.name if ch else "❌ محذوف"
            ch_mention = ch.mention if ch else f"#{ch_name}"
            line = f"• {ch_mention}\n"

            if v["team"] == "team1":
                t1_list += line
            elif v["team"] == "team2":
                t2_list += line
            else:
                any_list += line

        if t1_list:
            embed.add_field(name="🟠 Team 1", value=t1_list, inline=True)
        if t2_list:
            embed.add_field(name="🔵 Team 2", value=t2_list, inline=True)
        if any_list:
            embed.add_field(name="🔄 أي تيم (Any)", value=any_list, inline=True)

        embed.add_field(
            name="\u200b",
            value=f"💡 البوت يستخدم هالفويسات بدل ما ينشئ جديدة!\nأضف: `{PREFIX}addvoice` | شيل: `{PREFIX}removevoice`",
            inline=False
        )

    embed.add_field(
        name="🤖 وضع الفويسات",
        value=f"**{'مخصص (فويسات أنت تحددها)' if voices else 'تلقائي (البوت ينشئ فويسات جديدة)'}**",
        inline=False
    )

    await ctx.send(embed=embed)


@bot.command(name="linkroom")
@commands.check(is_admin_check)
async def linkroom_cmd(ctx, team=None, channel: discord.VoiceChannel = None):
    if not team or not channel:
        await ctx.send(embed=discord.Embed(
            title="📖 Link Room Help",
            description=f"**Usage:** `{PREFIX}linkroom <team1|team2> #voice_channel`",
            color=COLORS["info"]
        ))
        return
    team = team.lower()
    if team not in ["team1", "team2"]:
        await ctx.send(embed=discord.Embed(title="❌ Invalid Team", color=COLORS["error"]))
        return
    lobbies = db.get_active_lobbies(ctx.guild.id)
    if not lobbies:
        await ctx.send(embed=discord.Embed(title="❌ No Active Lobby", color=COLORS["error"]))
        return
    db.add_linked_room(ctx.guild.id, lobbies[0]["id"], team, channel.id)
    td = "🟠 Team 1" if team == "team1" else "🔵 Team 2"
    await ctx.send(embed=discord.Embed(
        title="✅ Room Linked",
        description=f"{td} → {channel.mention}",
        color=COLORS["success"]
    ))


@bot.command(name="unlinkroom")
@commands.check(is_admin_check)
async def unlinkroom_cmd(ctx, team=None, channel: discord.VoiceChannel = None):
    if not team:
        await ctx.send(embed=discord.Embed(
            title="❌ Missing Arguments",
            description=f"Usage: `{PREFIX}unlinkroom <team1|team2> #channel`",
            color=COLORS["error"]
        ))
        return
    team = team.lower()
    if team not in ["team1", "team2"]:
        await ctx.send(embed=discord.Embed(title="❌ Invalid Team", color=COLORS["error"]))
        return
    lobbies = db.get_active_lobbies(ctx.guild.id)
    if lobbies:
        success = db.remove_linked_room(ctx.guild.id, lobbies[0]["id"], team)
        if success:
            await ctx.send(embed=discord.Embed(title="✅ Room Unlinked", color=COLORS["success"]))
        else:
            await ctx.send(embed=discord.Embed(title="❌ No Link Found", color=COLORS["error"]))
    else:
        await ctx.send(embed=discord.Embed(title="❌ No Active Lobby", color=COLORS["error"]))


@bot.command(name="listrooms")
@commands.check(is_admin_check)
async def listrooms_cmd(ctx):
    guild = ctx.guild
    lr = db.get_linked_rooms(guild.id)
    pc = db.get_play_channels(guild.id)
    wr = db.get_waiting_rooms(guild.id)
    settings = db.get_guild_settings(guild.id)
    embed = discord.Embed(title="🏠 Room Configuration", color=COLORS["info"])
    if lr:
        rt = ""
        for r in lr:
            ch = guild.get_channel(r["channel_id"])
            cn = ch.name if ch else "Unknown"
            tn = "🟠 Team 1" if r["team"] == "team1" else "🔵 Team 2"
            rt += f"{tn} → #{cn}\n"
        embed.add_field(name="🔗 Linked Rooms", value=rt, inline=False)
    else:
        embed.add_field(name="🔗 Linked Rooms", value="No rooms linked", inline=False)
    if pc:
        embed.add_field(name="🎮 Play Channels",
            value="\n".join([f"#{guild.get_channel(c).name}" if guild.get_channel(c) else "Unknown" for c in pc]),
            inline=True)
    else:
        embed.add_field(name="🎮 Play Channels", value="Not set", inline=True)
    # 🆕 عرض غرف الانتظار العامة
    wr = db.get_waiting_rooms(guild.id)
    if wr:
        wr_text = ""
        for cid in wr:
            ch = guild.get_channel(cid)
            ch_name = ch.name if ch else "Unknown"
            member_count = len(ch.members) if ch else 0
            wr_text += f"🔊 {ch_name} — 👥 {member_count}\n"
        embed.add_field(name="⏳ Waiting Rooms", value=wr_text, inline=True)
    else:
        embed.add_field(name="⏳ Waiting Rooms", value="Not set", inline=True)
    embed.add_field(
        name="🤖 Auto Channels",
        value="✅ Private Voice + Text auto-created per match\n✅ Auto DM for room info\n✅ Auto vote on voice empty\n✅ Auto timeout\n🆕 General waiting rooms (both teams together)",
        inline=False
    )
    await ctx.send(embed=embed)


@bot.command(name="setformchannel")
@commands.check(is_admin_check)
async def setformchannel_cmd(ctx, channel: discord.TextChannel = None):
    channel = channel or ctx.channel
    db.set_guild_setting(ctx.guild.id, "form_channel_id", channel.id)
    await ctx.send(embed=discord.Embed(
        title="✅ Form Channel Set",
        description=f"{channel.mention}",
        color=COLORS["success"]
    ))


@bot.command(name="setplaychannel")
@commands.check(is_admin_check)
async def setplaychannel_cmd(ctx, channel: discord.TextChannel = None):
    channel = channel or ctx.channel
    if db.is_play_channel(ctx.guild.id, channel.id):
        db.remove_play_channel(ctx.guild.id, channel.id)
        await ctx.send(embed=discord.Embed(
            title="✅ Removed",
            description=f"{channel.mention}",
            color=COLORS["success"]
        ))
    else:
        db.add_play_channel(ctx.guild.id, channel.id)
        await ctx.send(embed=discord.Embed(
            title="✅ Added",
            description=f"{channel.mention}",
            color=COLORS["success"]
        ))


@bot.command(name="setwaitingroom")
@commands.check(is_admin_check)
async def setwaitingroom_cmd(ctx, channel: discord.VoiceChannel = None):
    """⏳ /setwaitingroom #voice_channel — غرفة انتظار عامة (الحد = 2 بالضبط)"""
    if not channel:
        rooms = db.get_waiting_rooms(ctx.guild.id)
        await ctx.send(embed=discord.Embed(
            title="❌ ناقص فويس",
            description=(
                f"الاستخدام: `{PREFIX}setwaitingroom #voice_channel`\n\n"
                f"🔒 **الحد = {MAX_WAITING_ROOMS} غرف بالضبط** (اللي تنشئها إنت)\n"
                f"📊 الحالي: {len(rooms)}/{MAX_WAITING_ROOMS} غرف\n\n"
                f"💡 **الهدف:** جمع كل اللاعبين اللي يبون يلعبون في مكان واحد.\n"
                f"👥 في كل غرفة ممكن أكثر من تيم (مو مشكلة الازدحام).\n"
                f"🚀 لما اللوبي يمتلي → البوت ينقلهم لغرف الماتش الخاصة."
            ),
            color=COLORS["error"]
        ))
        return

    # toggle: لو موجودة → احذفها، لو لأ → أضفها
    wr = db.get_waiting_rooms(ctx.guild.id)
    if channel.id in wr:
        db.remove_waiting_room(ctx.guild.id, channel.id)
        remaining = len(db.get_waiting_rooms(ctx.guild.id))
        await ctx.send(embed=discord.Embed(
            title="✅ Removed",
            description=(
                f"{channel.mention} ما عاد غرفة انتظار.\n\n"
                f"📊 المتبقي: {remaining}/{MAX_WAITING_ROOMS} غرف"
            ),
            color=COLORS["success"]
        ))
    else:
        # 🆕 تحقق من الحد الأقصى
        if len(wr) >= MAX_WAITING_ROOMS:
            existing_text = ""
            for cid in wr:
                ch = ctx.guild.get_channel(cid)
                ch_mention = ch.mention if ch else f"`{cid}`"
                existing_text += f"• {ch_mention}\n"
            await ctx.send(embed=discord.Embed(
                title=f"❌ وصلت الحد الأقصى ({MAX_WAITING_ROOMS} غرف)",
                description=(
                    f"🔒 ما تقدر تضيف أكثر من **{MAX_WAITING_ROOMS} غرف انتظار**!\n\n"
                    f"📋 **الغرف الموجودة:**\n{existing_text}\n"
                    f"💡 احذف وحدة أولًا:\n"
                    f"`{PREFIX}setwaitingroom #الغرفة`\n"
                    f"ثم أضف الجديدة."
                ),
                color=COLORS["error"]
            ))
            return

        success = db.add_waiting_room(ctx.guild.id, channel.id)
        if success:
            new_count = len(db.get_waiting_rooms(ctx.guild.id))
            await ctx.send(embed=discord.Embed(
                title="✅ تم تحديد غرفة انتظار",
                description=(
                    f"{channel.mention}\n\n"
                    f"📊 العدد: {new_count}/{MAX_WAITING_ROOMS} غرف\n\n"
                    f"💡 **الهدف:** جمع كل اللاعبين اللي يبون يلعبون في مكان واحد.\n"
                    f"👥 في كل غرفة ممكن أكثر من تيم (مو مشكلة الازدحام).\n"
                    f"🚀 لما اللوبي يمتلي → البوت ينقلهم لغرف الماتش الخاصة."
                ),
                color=COLORS["success"]
            ))
        else:
            wr_after = db.get_waiting_rooms(ctx.guild.id)
            if len(wr_after) >= MAX_WAITING_ROOMS:
                await ctx.send(embed=discord.Embed(
                    title=f"❌ وصلت الحد الأقصى ({MAX_WAITING_ROOMS} غرف)",
                    description=(
                        f"🔒 ما تقدر تضيف أكثر من **{MAX_WAITING_ROOMS} غرف انتظار**!\n"
                        f"💡 احذف وحدة أولًا ثم أعد المحاولة."
                    ),
                    color=COLORS["error"]
                ))
            else:
                await ctx.send(embed=discord.Embed(
                    title="❌ الفويس موجود من قبل",
                    description=f"{channel.mention} مضاف من قبل!",
                    color=COLORS["error"]
                ))


@bot.command(name="listwaitingrooms")
@commands.check(is_admin_check)
async def listwaitingrooms_cmd(ctx):
    """📋 /listwaitingrooms — عرض كل غرف الانتظار"""
    guild = ctx.guild
    rooms = db.get_waiting_rooms(guild.id)
    embed = discord.Embed(title="⏳ غرف الانتظار", color=COLORS["info"])
    embed.set_footer(text=f"🔒 الحد: {MAX_WAITING_ROOMS} غرف بالضبط | الحالي: {len(rooms)}/{MAX_WAITING_ROOMS}")
    if not rooms:
        embed.description = (
            f"ما في غرف انتظار محددة!\n\n"
            f"🔒 **الحد الأقصى = {MAX_WAITING_ROOMS} غرف بالضبط** (لا أكثر ولا أقل)\n\n"
            f"أضف غرف انتظار:\n"
            f"• `{PREFIX}setwaitingroom #voice_channel`\n\n"
            f"💡 اللاعبين من الفريقين ينتظرون مع بعض، ولما اللوبي يمتلي → البوت ينشئ فويسات مخصصة لكل تيم."
        )
    else:
        room_list = ""
        for i, cid in enumerate(rooms, 1):
            ch = guild.get_channel(cid)
            ch_mention = ch.mention if ch else f"❌ محذوف (`{cid}`)"
            member_count = len(ch.members) if ch else 0
            room_list += f"{i}. {ch_mention} — 👥 {member_count} لاعب\n"
        embed.description = room_list
        embed.add_field(
            name="\u200b",
            value=(
                f"💡 **الهدف:** جمع كل اللاعبين اللي يبون يلعبون في مكان واحد.\n"
                f"👥 في كل غرفة ممكن أكثر من تيم (مو مشكلة الازدحام).\n"
                f"🚀 لما اللوبي يمتلي → البوت ينقلهم لغرف الماتش الخاصة."
            ),
            inline=False
        )
        if len(rooms) < MAX_WAITING_ROOMS:
            embed.add_field(
                name="⚠️ تنبيه",
                value=f"تحتاج **{MAX_WAITING_ROOMS - len(rooms)}** غرفة إضافية للوصول للحد المطلوب ({MAX_WAITING_ROOMS}).",
                inline=False
            )
    await ctx.send(embed=embed)


@bot.command(name="removewaitingroom")
@commands.check(is_admin_check)
async def removewaitingroom_cmd(ctx, channel: discord.VoiceChannel = None):
    """🗑️ /removewaitingroom #voice_channel — حذف غرفة انتظار"""
    if not channel:
        # عرض القائمة لو ما فيه argument
        rooms = db.get_waiting_rooms(ctx.guild.id)
        if not rooms:
            await ctx.send(embed=discord.Embed(
                title="❌ ما في غرف انتظار",
                description=f"الاستخدام: `{PREFIX}removewaitingroom #voice_channel`",
                color=COLORS["error"]
            ))
        else:
            room_list = "\n".join([
                f"{i}. <#{cid}>" for i, cid in enumerate(rooms, 1)
            ])
            await ctx.send(embed=discord.Embed(
                title="🗑️ احذف غرفة انتظار",
                description=f"الاستخدام: `{PREFIX}removewaitingroom #voice_channel`\n\n📋 **الغرف الحالية:**\n{room_list}",
                color=COLORS["info"]
            ))
        return

    success = db.remove_waiting_room(ctx.guild.id, channel.id)
    if success:
        await ctx.send(embed=discord.Embed(
            title="✅ تم حذف غرفة الانتظار",
            description=(
                f"{channel.mention} ما عاد غرفة انتظار.\n\n"
                f"📊 المتبقي: {len(db.get_waiting_rooms(ctx.guild.id))}/{MAX_WAITING_ROOMS} غرف"
            ),
            color=COLORS["success"]
        ))
    else:
        await ctx.send(embed=discord.Embed(
            title="❌ الفويس ما كان غرفة انتظار",
            description=f"{channel.mention} ما هو في قائمة غرف الانتظار!",
            color=COLORS["error"]
        ))


@bot.command(name="setcommandschannel")
@commands.check(is_admin_check)
async def setcommandschannel_cmd(ctx, channel: discord.TextChannel = None):
    """💬 /setcommandschannel #text_channel — تحديد غرفة أوامر البوت (toggle)"""
    if not channel:
        # عرض القائمة الحالية
        channels = db.get_commands_channels(ctx.guild.id)
        if channels:
            ch_list = "\n".join([f"• <#{c}>" for c in channels])
            await ctx.send(embed=discord.Embed(
                title="💬 غرف أوامر البوت الحالية",
                description=f"{ch_list}\n\n💡 البوت يشتغل في هذي القنوات + غرف الانتظار.",
                color=COLORS["info"]
            ))
        else:
            await ctx.send(embed=discord.Embed(
                title="❌ ناقص قناة",
                description=(
                    f"الاستخدام: `{PREFIX}setcommandschannel #text_channel`\n\n"
                    f"💡 **غرفة أوامر البوت** هي القناة اللي البوت يقبل فيها الأوامر.\n"
                    f"البوت يشتغل فقط في:\n"
                    f"• ⏳ غرف الانتظار (Waiting Rooms)\n"
                    f"• 💬 غرف أوامر البوت (Bot Commands Channels)"
                ),
                color=COLORS["error"]
            ))
        return

    # toggle: لو موجودة → احذفها، لو لأ → أضفها
    if db.is_commands_channel(ctx.guild.id, channel.id):
        db.remove_commands_channel(ctx.guild.id, channel.id)
        await ctx.send(embed=discord.Embed(
            title="✅ Removed",
            description=f"{channel.mention} ما عاد غرفة أوامر للبوت.",
            color=COLORS["success"]
        ))
    else:
        success = db.add_commands_channel(ctx.guild.id, channel.id)
        if success:
            await ctx.send(embed=discord.Embed(
                title="✅ تم تحديد غرفة أوامر البوت",
                description=(
                    f"{channel.mention}\n\n"
                    f"💡 البوت الآن يقبل الأوامر في هذه القناة.\n"
                    f"🔒 البوت يشتغل فقط في:\n"
                    f"• ⏳ غرف الانتظار (Waiting Rooms)\n"
                    f"• 💬 غرف أوامر البوت (Bot Commands Channels)"
                ),
                color=COLORS["success"]
            ))
        else:
            await ctx.send(embed=discord.Embed(
                title="❌ القناة موجودة من قبل",
                description=f"{channel.mention} مضافة من قبل!",
                color=COLORS["error"]
            ))


@bot.command(name="removecommandschannel")
@commands.check(is_admin_check)
async def removecommandschannel_cmd(ctx, channel: discord.TextChannel = None):
    """🗑️ /removecommandschannel #text_channel — حذف غرفة أوامر البوت"""
    if not channel:
        channels = db.get_commands_channels(ctx.guild.id)
        if not channels:
            await ctx.send(embed=discord.Embed(
                title="❌ ما في غرف أوامر",
                description=f"الاستخدام: `{PREFIX}removecommandschannel #text_channel`",
                color=COLORS["error"]
            ))
        else:
            ch_list = "\n".join([f"{i}. <#{c}>" for i, c in enumerate(channels, 1)])
            await ctx.send(embed=discord.Embed(
                title="🗑️ احذف غرفة أوامر",
                description=f"الاستخدام: `{PREFIX}removecommandschannel #text_channel`\n\n📋 **الغرف الحالية:**\n{ch_list}",
                color=COLORS["info"]
            ))
        return

    success = db.remove_commands_channel(ctx.guild.id, channel.id)
    if success:
        await ctx.send(embed=discord.Embed(
            title="✅ تم حذف غرفة الأوامر",
            description=f"{channel.mention} ما عاد غرفة أوامر للبوت.",
            color=COLORS["success"]
        ))
    else:
        await ctx.send(embed=discord.Embed(
            title="❌ القناة ما كانت غرفة أوامر",
            description=f"{channel.mention} ما هو في قائمة غرف الأوامر!",
            color=COLORS["error"]
        ))


@bot.command(name="listbotchannels")
@commands.check(is_admin_check)
async def listbotchannels_cmd(ctx):
    """📋 /listbotchannels — عرض كل القنوات اللي البوت يشتغل فيها"""
    guild = ctx.guild
    waiting_rooms = db.get_waiting_rooms(guild.id)
    commands_channels = db.get_commands_channels(guild.id)

    embed = discord.Embed(title="🔒 قنوات البوت المسموحة", color=COLORS["info"])

    # Waiting Rooms
    if waiting_rooms:
        wr_text = ""
        for i, cid in enumerate(waiting_rooms, 1):
            ch = guild.get_channel(cid)
            ch_mention = ch.mention if ch else f"❌ محذوف (`{cid}`)"
            wr_text += f"{i}. {ch_mention}\n"
        embed.add_field(name=f"⏳ غرف الانتظار ({len(waiting_rooms)}/{MAX_WAITING_ROOMS})", value=wr_text, inline=False)
    else:
        embed.add_field(name=f"⏳ غرف الانتظار (0/{MAX_WAITING_ROOMS})", value="ما في غرف انتظار محددة", inline=False)

    # Commands Channels
    if commands_channels:
        cc_text = ""
        for i, cid in enumerate(commands_channels, 1):
            ch = guild.get_channel(cid)
            ch_mention = ch.mention if ch else f"❌ محذوف (`{cid}`)"
            cc_text += f"{i}. {ch_mention}\n"
        embed.add_field(name=f"💬 غرف الأوامر ({len(commands_channels)})", value=cc_text, inline=False)
    else:
        embed.add_field(name="💬 غرف الأوامر (0)", value="ما في غرف أوامر محددة", inline=False)

    embed.add_field(
        name="ℹ️ ملاحظات",
        value=(
            f"• البوت يقبل الأوامر فقط في القنوات فوق\n"
            f"• DM messages دائماً مسموحة\n"
            f"• قنوات الماتش الخاصة مسموحة تلقائياً أثناء الماتش\n\n"
            f"**الأوامر:**\n"
            f"• `{PREFIX}setwaitingroom #voice` — إضافة/حذف غرفة انتظار\n"
            f"• `{PREFIX}removewaitingroom #voice` — حذف غرفة انتظار\n"
            f"• `{PREFIX}setcommandschannel #text` — إضافة/حذف غرفة أوامر\n"
            f"• `{PREFIX}removecommandschannel #text` — حذف غرفة أوامر"
        ),
        inline=False
    )
    await ctx.send(embed=embed)


@bot.command(name="resetstats")
@commands.check(is_admin_check)
async def resetstats_cmd(ctx, member: discord.Member = None):
    if not member:
        await ctx.send(embed=discord.Embed(
            title="❌ Missing User",
            description=f"Usage: `{PREFIX}resetstats @user`",
            color=COLORS["error"]
        ))
        return
    player = db.get_player(member.id, ctx.guild.id)
    if not player:
        await ctx.send(embed=discord.Embed(title="❌ Player Not Found", color=COLORS["error"]))
        return
    db.reset_stats(member.id, ctx.guild.id)
    await update_member_nickname(member, STARTING_LEVEL)
    await ctx.send(embed=discord.Embed(
        title="✅ Stats Reset",
        description=f"{member.mention} — Rank reset to {STARTING_LEVEL} (1 = الأعلى)",
        color=COLORS["success"]
    ))


@bot.command(name="setrank")
@commands.check(is_admin_check)
async def setrank_cmd(ctx, member: discord.Member = None, rank: int = None):
    if not member or rank is None:
        rl = "\n".join([f"`{rid}` — {rd['emoji']} {rd['name']} ({rd['min_points']}+ pts)" for rid, rd in RANKS.items()])
        await ctx.send(embed=discord.Embed(
            title="❌ Missing Arguments",
            description=f"Usage: `{PREFIX}setrank @user <rank>`\n\n{rl}",
            color=COLORS["error"]
        ))
        return
    if rank not in RANKS:
        await ctx.send(embed=discord.Embed(title="❌ Invalid Rank", color=COLORS["error"]))
        return
    db.get_or_create_player(member.id, ctx.guild.id, member.display_name)
    db.update_player_stats(member.id, ctx.guild.id, rank_pos=rank)
    ri = RANKS[rank]
    await ctx.send(embed=discord.Embed(
        title="✅ Rank Updated",
        description=f"{member.mention} → {ri['emoji']} **{ri['name']}**",
        color=COLORS["success"]
    ))


@bot.command(name="addpoints")
@commands.check(is_admin_check)
async def addpoints_cmd(ctx, member: discord.Member = None, amount: int = None):
    if not member or amount is None:
        await ctx.send(embed=discord.Embed(
            title="❌ Missing Arguments",
            description=f"Usage: `{PREFIX}addpoints @user <amount>`",
            color=COLORS["error"]
        ))
        return
    if amount <= 0:
        await ctx.send(embed=discord.Embed(title="❌ Invalid Amount", color=COLORS["error"]))
        return
    player = db.get_or_create_player(member.id, ctx.guild.id, member.display_name)
    db.add_points(member.id, ctx.guild.id, amount)
    np = player["points"] + amount
    ri = get_rank_info(np)
    embed = discord.Embed(
        title="✅ Points Added",
        description=f"+{amount} to {member.mention}",
        color=COLORS["success"]
    )
    embed.add_field(name="New", value=str(np), inline=True)
    embed.add_field(name="Rank", value=f"{ri['emoji']} {ri['name']}", inline=True)
    await ctx.send(embed=embed)


@bot.command(name="removepoints")
@commands.check(is_admin_check)
async def removepoints_cmd(ctx, member: discord.Member = None, amount: int = None):
    if not member or amount is None:
        await ctx.send(embed=discord.Embed(
            title="❌ Missing Arguments",
            description=f"Usage: `{PREFIX}removepoints @user <amount>`",
            color=COLORS["error"]
        ))
        return
    if amount <= 0:
        await ctx.send(embed=discord.Embed(title="❌ Invalid Amount", color=COLORS["error"]))
        return
    player = db.get_or_create_player(member.id, ctx.guild.id, member.display_name)
    db.add_points(member.id, ctx.guild.id, -amount)
    np = max(0, player["points"] - amount)
    ri = get_rank_info(np)
    embed = discord.Embed(
        title="✅ Points Removed",
        description=f"-{amount} from {member.mention}",
        color=COLORS["success"]
    )
    embed.add_field(name="New", value=str(np), inline=True)
    embed.add_field(name="Rank", value=f"{ri['emoji']} {ri['name']}", inline=True)
    await ctx.send(embed=embed)


@bot.command(name="setlevel")
@commands.check(is_admin_check)
async def setlevel_cmd(ctx, member: discord.Member = None, level: int = None):
    if not member or level is None:
        await ctx.send(embed=discord.Embed(
            title="❌ ناقص معلومات",
            description=f"Usage: `{PREFIX}setlevel @user <level>`\n💡 Rank 1 = الأعلى، Rank 9999 = الأدنى. ابدأ من 100.",
            color=COLORS["error"]
        ))
        return
    if level < 1 or level > 9999:
        await ctx.send(embed=discord.Embed(
            title="❌ مستوى غير صالح",
            description="الـ Rank لازم يكون بين 1 (الأعلى) و 9999 (الأدنى).",
            color=COLORS["error"]
        ))
        return
    db.get_or_create_player(member.id, ctx.guild.id, member.display_name)
    db.update_player_stats(member.id, ctx.guild.id, level=level)
    await update_member_nickname(member, level)
    await ctx.send(embed=discord.Embed(
        title="✅ Rank Updated",
        description=f"{member.mention} → **RANK {level}**",
        color=COLORS["success"]
    ))


@bot.command(name="setrole")
@commands.check(is_admin_check)
async def setrole_cmd(ctx, role: discord.Role = None):
    if not role:
        await ctx.send(embed=discord.Embed(
            title="❌ Missing Role",
            description=f"Usage: `{PREFIX}setrole @role`",
            color=COLORS["error"]
        ))
        return
    db.set_guild_setting(ctx.guild.id, "announcement_role_id", role.id)
    await ctx.send(embed=discord.Embed(
        title="✅ Announcement Role Set",
        description=f"{role.mention}",
        color=COLORS["success"]
    ))


@bot.command(name="setleaderboard")
@commands.check(is_admin_check)
async def setleaderboard_cmd(ctx):
    db.set_guild_setting(ctx.guild.id, "leaderboard_channel_id", ctx.channel.id)
    await update_leaderboard_channel(ctx.guild)
    await ctx.send(embed=discord.Embed(
        title="✅ Leaderboard Set",
        description=f"{ctx.channel.mention} auto-updates",
        color=COLORS["success"]
    ))


@bot.command(name="forcestartmatch")
@commands.check(is_admin_check)
async def forcestartmatch_cmd(ctx, lobby_id: int = None):
    if lobby_id is None:
        await ctx.send(embed=discord.Embed(
            title="❌ Missing Lobby ID",
            description=f"Usage: `{PREFIX}forcestartmatch <id>`",
            color=COLORS["error"]
        ))
        return
    lobby = db.get_lobby(lobby_id)
    if not lobby or lobby["status"] != "waiting":
        await ctx.send(embed=discord.Embed(title="❌ Not Waiting", color=COLORS["error"]))
        return
    # 🆕 M12 fix: إلغاء timeout قبل البدء
    if lobby_id in lobby_timeout_timers:
        lobby_timeout_timers[lobby_id].cancel()
        if lobby_id in lobby_timeout_timers:
            del lobby_timeout_timers[lobby_id]

    db.update_lobby_status(lobby_id, "started")
    guild = ctx.guild
    try:
        channels = await create_match_channels(guild, lobby, lobby_id)
    except Exception as e:
        channels = None
        logger.exception(f"create_match_channels failed: {e}")

    # 🆕 C7 fix: rollback لو فشل
    if not channels:
        db.update_lobby_status(lobby_id, "cancelled")
        cleanup_lobby_memory(lobby_id)
        await ctx.send(embed=discord.Embed(
            title="❌ فشل بدء الماتش",
            description=f"ما قدرت أنشئ قنوات الماتش. اللوبي #{lobby_id} أُلغي.",
            color=COLORS["error"]
        ))
        return

    embed = discord.Embed(title=f"🎮 Force Started — Lobby #{lobby_id}", color=COLORS["success"])
    t1m = " ".join([f"<@{p}>" for p in lobby["team1_players"]])
    t2m = " ".join([f"<@{p}>" for p in lobby["team2_players"]])
    embed.add_field(name="🟠 Team 1", value=t1m, inline=True)
    embed.add_field(name="🔵 Team 2", value=t2m, inline=True)
    await ctx.send(embed=embed)

    # 🆕 M12 fix: نقل اللاعبين لفويسات الماتش
    for pid in lobby["team1_players"]:
        m = guild.get_member(pid)
        if m and m.voice:
            try: await m.move_to(channels["team1_voice"])
            except (discord.HTTPException, discord.Forbidden): pass
    for pid in lobby["team2_players"]:
        m = guild.get_member(pid)
        if m and m.voice:
            try: await m.move_to(channels["team2_voice"])
            except (discord.HTTPException, discord.Forbidden): pass
    # 🆕 ابدأ التصويت بعد 5 دقايق من بداية الماتش
    # 🆕 معطّل: التصويت يبدأ بعد room info (مو بعد 5 دقايق)
    # asyncio.create_task(auto_trigger_vote_after_delay(lobby_id, guild))


@bot.command(name="syncnicknames")
@commands.check(is_admin_check)
@commands.cooldown(1, 60, commands.BucketType.guild)
async def syncnicknames_cmd(ctx):
    guild = ctx.guild
    conn = db.conn()
    try:
        cur = conn.execute("SELECT user_id, level FROM players WHERE guild_id=?", (guild.id,))
        players = cur.fetchall()
    finally:
        conn.close()
    updated = 0
    for p in players:
        member = guild.get_member(p["user_id"])
        if member:
            level = p["level"] if p["level"] else STARTING_LEVEL
            await update_member_nickname(member, level)
            updated += 1
    await ctx.send(embed=discord.Embed(
        title="✅ Nicknames Synced",
        description=f"**{updated}** لاعب تم تحديثه!",
        color=COLORS["success"]
    ))


# ============================================================
# HELP COMMAND
# ============================================================

@bot.command(name="general")
@commands.cooldown(1, 5, commands.BucketType.user)
async def general_cmd(ctx):
    """🎮 /general — الأوامر الأساسية للاعبين العاديين (يقدرون يستخدمونه في أي قناة)"""
    embed = discord.Embed(
        title="🎮 أوامر اللاعبين — Free Fire Bot",
        description=(
            f"**البادئة:** `{PREFIX}`\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        ),
        color=0xFF6B00
    )

    embed.add_field(
        name="🚀 بدء اللعب",
        value=(
            f"• `{PREFIX}play` — إنشاء لوبي 4v4 (افتراضي)\n"
            f"• `{PREFIX}play1v1` — لوبي 1 ضد 1\n"
            f"• `{PREFIX}play2v2` — لوبي 2 ضد 2\n"
            f"• `{PREFIX}play3v3` — لوبي 3 ضد 3\n"
            f"• `{PREFIX}play4v4` — لوبي 4 ضد 4"
        ),
        inline=False
    )

    embed.add_field(
        name="📊 معلوماتك",
        value=(
            f"• `{PREFIX}p` — شف برفايلك\n"
            f"• `{PREFIX}p @user` — شف برفايل لاعب ثاني\n"
            f"• `{PREFIX}mylevel` — شف مستوى الرتبة حقك\n"
            f"• `{PREFIX}myrank` — شف نَكك المطلوب\n"
            f"• `{PREFIX}top` — أفضل 10 لاعبين\n"
            f"• `{PREFIX}matches` — اللوبيات النشطة"
        ),
        inline=False
    )

    embed.add_field(
        name="🎮 التحكم باللعبة",
        value=(
            f"• `{PREFIX}leave` — اخرج من اللوبي\n"
            f"• `{PREFIX}matchinfo <id>` — معلومات ماتش معين\n"
            f"• `{PREFIX}setroom <id> <code>` — حط آيدي وكود الروم (لصاحب الروم)\n"
            f"• `{PREFIX}fixrank` — طبّق الرتبة على اسمك يدوياً"
        ),
        inline=False
    )

    embed.add_field(
        name="🤖 كيف تلعب؟",
        value=(
            f"1️⃣ اكتب `{PREFIX}play` في غرفة الأوامر\n"
            f"2️⃣ اضغط 🔴 (Team I) أو 🔵 (Team II) على رسالة اللوبي\n"
            f"3️⃣ البوت بينقلك لغرفة الانتظار ⏳\n"
            f"4️⃣ لما يمتلي اللوبي → البوت ينشئ فويسات لكل تيم + ينقلكم\n"
            f"5️⃣ صاحب الروم بيوصله DM بالآيدي والكود\n"
            f"6️⃣ صاحب الروم يرد على الـ DM بـ: `room_id room_code`\n"
            f"7️⃣ البوت يرسل الآيدي والكود للاعبين + يبدأ التصويت\n"
            f"8️⃣ صاحب الروم + أول داخل يصوتون للفريق الرابح\n"
            f"9️⃣ النتيجة تُحسب + Rank يتحدث + اسمك يتغير\n"
            f"🔟 البوت يعرض زر إعادة الماتش 🔄"
        ),
        inline=False
    )

    embed.add_field(
        name="🏅 نظام الرتبة (Rank)",
        value=(
            f"• **Rank 1** = الأعلى (الأفضل) 🏆\n"
            f"• **Rank 100** = البداية (افتراضي)\n"
            f"• **Rank 9999** = الأدنى\n\n"
            f"🏆 **الفوز** → Rank ينقص (تتقدم للأعلى) ⬆️\n"
            f"❌ **الهزيمة** → Rank يزيد (تنزل للأسفل) ⬇️\n\n"
            f"🔥 **Streaks (سلاسل الانتصارات):**\n"
            f"• 3 انتصارات متتالية → +10 نقاط + Rank -2\n"
            f"• 5 انتصارات متتالية → +25 نقطة + Rank -3\n"
            f"• 10+ انتصارات متتالية → +50 نقطة لكل فوز"
        ),
        inline=False
    )

    embed.add_field(
        name="🏆 النقاط حسب حجم الماتش",
        value=(
            f"• **1v1:** فوز +20 | خسارة +5\n"
            f"• **2v2:** فوز +30 | خسارة +10\n"
            f"• **3v3:** فوز +40 | خسارة +12\n"
            f"• **4v4:** فوز +50 | خسارة +15"
        ),
        inline=False
    )

    embed.add_field(
        name="🗳️ نظام التصويت",
        value=(
            f"• التصويت **مفتوح** — ما فيه timeout ⏱️\n"
            f"• يبدأ مباشرة بعد ما صاحب الروم يحط الآيدي والكود\n"
            f"• **3 فرص** قبل استدعاء الأدمن:\n"
            f"  - لو الناخبون اختلفوا 3 مرات → رح ينادى الأدمن\n"
            f"  - الأدمن يستخدم `{PREFIX}resolve <id> <team1|team2>`"
        ),
        inline=False
    )

    embed.add_field(
        name="⚠️ ملاحظات مهمة",
        value=(
            f"• البوت يشتغل فقط في **غرف الانتظار** و **غرفة الأوامر**\n"
            f"• لو كتبت أمر في قناة ثانية → البوت ما راح يرد\n"
            f"• لتغيير الفريق: اضغط الرمز الجديد (البوت يحذف القديم)\n"
            f"• للخروج من اللوبي: اضغط ❌ أو اكتب `{PREFIX}leave`\n"
            f"• لو ما ظهر الـ Rank بجانب اسمك → استخدم `{PREFIX}fixrank`"
        ),
        inline=False
    )

    embed.set_footer(
        text=f"Free Fire Matchmaking Bot v3.1 | {PREFIX}help (للأدمن) | استمتع باللعب! 🔥"
    )

    await ctx.send(embed=embed)


@bot.command(name="playerhelp")
@commands.cooldown(1, 5, commands.BucketType.user)
async def playerhelp_cmd(ctx):
    """📋 /playerhelp — دليل اللاعبين (يقدرون يستخدمونه في أي قناة)"""
    embed = discord.Embed(
        title="🎮 دليل اللاعبين — Free Fire Bot",
        description=(
            f"**البادئة:** `{PREFIX}`\n"
            f"**الأوامر الأساسية للاعبين:**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        ),
        color=0xFF6B00
    )

    embed.add_field(
        name="🚀 بدء اللعب",
        value=(
            f"• `{PREFIX}play` — إنشاء لوبي 4v4 (افتراضي)\n"
            f"• `{PREFIX}play1v1` — لوبي 1 ضد 1\n"
            f"• `{PREFIX}play2v2` — لوبي 2 ضد 2\n"
            f"• `{PREFIX}play3v3` — لوبي 3 ضد 3\n"
            f"• `{PREFIX}play4v4` — لوبي 4 ضد 4"
        ),
        inline=False
    )

    embed.add_field(
        name="📊 معلوماتك",
        value=(
            f"• `{PREFIX}p` — شف برفايلك\n"
            f"• `{PREFIX}p @user` — شف برفايل لاعب ثاني\n"
            f"• `{PREFIX}mylevel` — شف مستوى الرتبة حقك\n"
            f"• `{PREFIX}top` — أفضل 10 لاعبين\n"
            f"• `{PREFIX}matches` — اللوبيات النشطة الحالية"
        ),
        inline=False
    )

    embed.add_field(
        name="🎮 التحكم باللعبة",
        value=(
            f"• `{PREFIX}leave` — اخرج من اللوبي\n"
            f"• `{PREFIX}matchinfo <id>` — معلومات ماتش معين\n"
            f"• `{PREFIX}setroom <id> <code>` — حط آيدي وكود الروم (لصاحب الروم)"
        ),
        inline=False
    )

    embed.add_field(
        name="🤖 كيف تلعب؟ (تلقائي بالكامل)",
        value=(
            f"1️⃣ اكتب `{PREFIX}play` في غرفة الأوامر\n"
            f"2️⃣ اضغط 🔴 (Team 1) أو 🔵 (Team 2) على رسالة اللوبي\n"
            f"3️⃣ البوت بينقلك لغرفة الانتظار ⏳\n"
            f"4️⃣ لما يمتلي اللوبي → البوت ينشئ فويسات لكل تيم + ينقلكم\n"
            f"5️⃣ صاحب الروم بيوصله DM بالآيدي والكود\n"
            f"6️⃣ العبوا! لما تخلصون → اخرجوا من الفويس\n"
            f"7️⃣ البوت بيبدا التصويت تلقائياً\n"
            f"8️⃣ صاحب الروم + أول داخل يصوتون للفريق الرابح\n"
            f"9️⃣ النتيجة تُحسب + Rank يتحدث + اسمك يتغير\n"
            f"🔟 البوت يعرض زر إعادة الماتش 🔄"
        ),
        inline=False
    )

    embed.add_field(
        name="🏅 نظام الرتبة (Rank)",
        value=(
            f"• **Rank 1** = الأعلى (الأفضل)\n"
            f"• **Rank 100** = البداية (افتراضي)\n"
            f"• **Rank 9999** = الأدنى\n"
            f"• 🏆 **الفوز** → الرقم ينقص (تتقدم للأعلى) ⬆️\n"
            f"• ❌ **الهزيمة** → الرقم يزيد (تنزل للأسفل) ⬇️\n"
            f"• الاسم يتغير تلقائياً لـ `Rank X Name`"
        ),
        inline=False
    )

    embed.add_field(
        name="🏆 النقاط",
        value=(
            f"• 🏆 **الفوز:** +30 نقطة\n"
            f"• ❌ **الهزيمة:** +10 نقاط\n"
            f"• 💀 **Kill:** +5 نقاط (قريباً)\n"
            f"• ⭐ **MVP:** +15 نقطة (قريباً)"
        ),
        inline=False
    )

    embed.add_field(
        name="⚠️ ملاحظات مهمة",
        value=(
            f"• البوت يشتغل فقط في **غرف الانتظار** و **غرفة الأوامر**\n"
            f"• لو كتبت أمر في قناة ثانية → البوت ما راح يرد\n"
            f"• لتغيير الفريق: اضغط الرمز الجديد (البوت يحذف القديم)\n"
            f"• للخروج من اللوبي: اضغط ❌ أو اكتب `{PREFIX}leave`"
        ),
        inline=False
    )

    embed.set_footer(
        text=f"Free Fire Matchmaking Bot v3.1 | {PREFIX}help (للأدمن) | استمتع باللعب! 🔥"
    )

    await ctx.send(embed=embed)


@bot.command(name="help")
@commands.cooldown(1, 5, commands.BucketType.user)
async def help_cmd(ctx):
    embed = discord.Embed(
        title="🔥 Free Fire Bot v3.1 — ULTRA AUTO 🤖",
        description=f"Prefix: `{PREFIX}`",
        color=0xFF6B00
    )
    mc = (f"⚔️ `{PREFIX}play1v1` — Solo (1v1)\n🔥 `{PREFIX}play2v2` — Duo (2v2)\n"
          f"💎 `{PREFIX}play3v3` — Squad 3 (3v3)\n👑 `{PREFIX}play4v4` — Squad 4 (4v4)\n"
          f"🎮 `{PREFIX}play` — Default 4v4")
    pc = (f"`{PREFIX}p [@user]` — الملف الشخصي\n`{PREFIX}top` — أفضل 10\n"
          f"`{PREFIX}matches` — اللوبيات النشطة\n`{PREFIX}matchinfo <id>` — معلومات ماتش\n"
          f"`{PREFIX}leave` — مغادرة اللوبي\n`{PREFIX}mylevel` — مستواك")
    auto = (f"🤖 **كل شي تلقائي!** بس العبوا:\n"
            f"1️⃣ اكتب `{PREFIX}play` → اللوبي ينشأ\n"
            f"2️⃣ اضغط Join Team 1/2 → تنضم + تنقل لغرفة انتظار\n"
            f"3️⃣ الفريقين ينتظرون مع بعض لحد ما اللوبي يمتلي\n"
            f"4️⃣ اللوبي يمتلي → البوت ينشئ فويسات مخصصة لكل تيم + ينقلهم\n"
            f"5️⃣ اضغط Enter Room Info → أدخل الآيدي والكود\n"
            f"6️⃣ تخلصون وتطلعون → التصويت يبدأ تلقائي\n"
            f"7️⃣ تضغطون زر → النتيجة تُحسب تلقائي\n"
            f"8️⃣ الاسم يتغير + Rank يرتفع تلقائي\n"
            f"9️⃣ لو اختلاف → Owner يُنبّه تلقائي\n"
            f"🔟 لو ما صوتوا 3 دقايق → Owner يُنبّه تلقائي\n"
            f"1️⃣1️⃣ زر إعادة الماتش يظهر تلقائي 🔄")
    ac = (f"`{PREFIX}setuprooms` — إنشاء الغرف\n`{PREFIX}setroom <id> <code>` — يدوي\n"
          f"`{PREFIX}votewin <team>` — يدوي\n`{PREFIX}resolve <id> <team>` — حل خلاف\n"
          f"`{PREFIX}endmatch <id> <team>` — إنهاء إجباري\n`{PREFIX}cancelmatch <id>` — إلغاء\n"
          f"`{PREFIX}resetstats @user` | `{PREFIX}setrank @user <r>` | `{PREFIX}setlevel @user <l>`\n"
          f"`{PREFIX}addpoints @user <a>` | `{PREFIX}removepoints @user <a>`\n"
          f"`{PREFIX}setrole @role` | `{PREFIX}setleaderboard` | `{PREFIX}forcestartmatch <id>`\n"
          f"`{PREFIX}syncnicknames` | `{PREFIX}listrooms`")
    vc = (f"🔊 `{PREFIX}addvoice <team1|team2|any> #voice` — أضف فويس مسموح\n"
          f"🔇 `{PREFIX}removevoice #voice` — شيل فويس\n"
          f"📋 `{PREFIX}listvoices` — عرض الفويسات المسموحة\n\n"
          f"💡 **team1** = فويس مخصص لتيم 1 | **team2** = مخصص لتيم 2 | **any** = لأي تيم\n"
          f"🤖 لو ما حددت فويسات → البوت ينشئ تلقائياً")
    wr = (f"⏳ `{PREFIX}setwaitingroom #voice` — إضافة/حذف غرفة انتظار (toggle)\n"
          f"🗑️ `{PREFIX}removewaitingroom #voice` — حذف غرفة انتظار\n"
          f"📋 `{PREFIX}listwaitingrooms` — عرض كل غرف الانتظار\n\n"
          f"🔒 **الحد = {MAX_WAITING_ROOMS} غرف بالضبط** (اللي تنشئها إنت)\n"
          f"💡 **الهدف:** جمع كل اللاعبين اللي يبون يلعبون في مكان واحد\n"
          f"👥 في كل غرفة ممكن أكثر من تيم (مو مشكلة الازدحام)\n"
          f"🚀 لما اللوبي يمتلي → البوت ينقلهم لغرف الماتش الخاصة")
    bc = (f"💬 `{PREFIX}setcommandschannel #text` — إضافة/حذف غرفة أوامر (toggle)\n"
          f"🗑️ `{PREFIX}removecommandschannel #text` — حذف غرفة أوامر\n"
          f"📋 `{PREFIX}listbotchannels` — عرض كل القنوات المسموحة\n\n"
          f"🔒 **البوت يشتغل فقط في:**\n"
          f"• ⏳ غرف الانتظار (Waiting Rooms)\n"
          f"• 💬 غرف أوامر البوت (Bot Commands Channels)\n\n"
          f"⚠️ لو كتبت أمر في قناة ثانية → البوت ما راح يرد")
    embed.add_field(name="🎮 أوضاع اللعب", value=mc, inline=False)
    embed.add_field(name="📋 أوامر اللاعبين", value=pc, inline=False)
    embed.add_field(name="🤖 التدفق التلقائي", value=auto, inline=False)
    embed.add_field(name="⏳ غرف الانتظار", value=wr, inline=False)
    embed.add_field(name="💬 غرف أوامر البوت", value=bc, inline=False)
    embed.add_field(name="🔊 فويسات الماتش", value=vc, inline=False)
    embed.add_field(name="🔧 أوامر الأدمن", value=ac, inline=False)
    await ctx.send(embed=embed)


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    # 🆕 الطريقة الآمنة: اقرأ التوكن من متغير البيئة DISCORD_TOKEN
    # لو ما موجود، ارجع للتوكن الافتراضي (للتشغيل المحلي)
    TOKEN = os.getenv("DISCORD_TOKEN") or "MTUxNzU4NjA4MTk3NTg5NDAxNw.GJpInx.Ohmp-CCc9nb8Uid8B5_h4M6W4_zW8OnI0d0IUA"
    if not TOKEN:
        raise RuntimeError("DISCORD_TOKEN environment variable is required")

    logger.info("🚀 Starting Free Fire Bot v3.1 ULTRA AUTO (FIXED)...")
    logger.info("🤖 All features are automatic!")
    logger.info("   • Auto-create channels per match")
    logger.info("   • Auto DM for room info")
    logger.info("   • Auto vote trigger on voice empty")
    logger.info("   • Auto vote timeout → ping Owner")
    logger.info("   • Auto lobby timeout → cancel")
    logger.info("   • Auto level update in nickname")
    logger.info("   • Auto rematch button")
    logger.info("   • Auto leaderboard update")
    logger.info("   🆕 Persistent views (survive restarts)")
    logger.info("   🆕 Orphan channel cleanup on startup")
    logger.info("   🆕 Cooldowns on sensitive commands")
    logger.info("   🆕 Proper logging")
    logger.info("   🆕 Memory leak fixes")
    # bot.proxy = "http://127.0.0.1:7890"
    bot.run(TOKEN)

