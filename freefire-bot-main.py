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
GUILD_WHITELIST_ENABLED = False

# 🆕 اسم الـ role الذي يتم تاغه عند حدوث مشاكل
ADMIN_ROLE_NAME = "Admin"  # غيّر هذا حسب اسم الـ role في سيرفرك

STARTING_LEVEL = 1000
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

# 🆕 نظام البلاغات والحظر
REPORT_THRESHOLD = 6            # عدد البلاغات اللازمة للحظر التلقائي
REPORT_CHANNELS_COUNT = 3       # عدد الفويسات التي يستطيع المحظور دخولها
REPORT_CATEGORY_NAME = "🚨  Reports & Bans"  # اسم كاتيجوري البلاغات

# 🆕 نظام الألقاب الديناميكي (Roles)
# البوت يصنع هذه الـ Roles ويعطيها/يسحبها تلقائياً حسب الترتيب
RANK_TITLES = {
    1: {
        "name": "🏆 Best Player",
        "arabic": "أفضل لاعب",
        "color": 0xE74C3C,  # أحمر
        "permissions": ["soundboard", "waiting_prv"],
        "max_rank": 1,  # فقط الـ #1
    },
    2: {
        "name": "💎 Goated Players",
        "arabic": "لاعبون أسطوريون",
        "color": 0xF1C40F,  # ذهبي
        "permissions": ["soundboard", "waiting_prv"],
        "max_rank": 10,  # من #1 إلى #10
    },
    3: {
        "name": "⭐ Skilled Players",
        "arabic": "لاعبون مهاريون",
        "color": 0x9B59B6,  # بنفسجي
        "permissions": ["soundboard"],
        "max_rank": 50,  # من #11 إلى #50
    },
    4: {
        "name": "🎯 Efficient Players",
        "arabic": "لاعبون فعّالون",
        "color": 0x3498DB,  # أزرق
        "permissions": [],
        "max_rank": 100,  # من #51 إلى #100
    },
}

# 🆕 أسماء كاتيجوري غرف الانتظار الخاصة (للتحقق منها عند إعطاء الصلاحية)
WAITING_PRV_CATEGORY_HINT = "Waiting Prv"

COLORS = {
    # الأساسية
    "success": 0x2ECC71,   # أخضر زمردي
    "error":   0xE74C3C,   # أحمر فاتح
    "warning": 0xF1C40F,   # أصفر ذهبي
    "info":    0x3498DB,   # أزرق سماوي
    # الخاصة بالبوت
    "play":        0xE67E22,  # برتقالي ناري
    "profile":     0x9B59B6,  # بنفسجي ملكي
    "leaderboard": 0xF1C40F,  # ذهبي
    "match":       0x3498DB,  # أزرق محيطي
    "admin":       0xC0392B,  # أحمر داكن
    "vote":        0x8E44AD,  # بنفسجي داكن
    "auto":        0x16A085,  # أخضر فيروزي
    # أحوال اللاعب
    "rank_low":    0x95A5A6,  # رمادي - رانك منخفض
    "rank_mid":    0x3498DB,  # أزرق - رانك متوسط
    "rank_high":   0x9B59B6,  # بنفسجي - رانك عالي
    "rank_elite":  0xF1C40F,  # ذهبي - رانك نخبة
    "rank_legend": 0xE74C3C,  # أحمر - أسطورة
}

# شعار البوت الرسمي (يستخدم في كل الـ embeds)
BOT_LOGO_URL = "https://i.imgur.com/8RYMfAE.png"
BOT_FOOTER = "Free Fire Bot v4.0  •  Matchmaking System"

# 🆕 صورة ثابتة تظهر في كل ردود البوت (في كل السيرفرات)
BOT_BANNER_URL = "https://iili.io/CRNXkFe.png"

# 🆕 صورة القواعد — تظهر في أسفل رسالة !!rules وفي قناة rules
RULES_IMAGE_URL = "https://iili.io/CRepLH7.png"

# 🆕 GIF مخصص لكل سيرفر — يظهر بدل الصورة الثابتة في السيرفرات المحددة
# أضف أي سيرفر: SERVER_GIFS[guild_id] = "gif_url"
SERVER_GIFS = {
    1504736689610821711: "https://iili.io/CRNXNM7.gif",  # السيرفر الأول
    1516566061820936242: "https://iili.io/CRObS8F.gif",  # السيرفر الثاني
}

def apply_branding(embed, guild):
    """🆕 يضيف شعار السيرفر أو الـ GIF المخصص في كل ردود البوت."""
    if not guild:
        return embed
    # 🆕 لو السيرفر عنده GIF مخصص → استخدمه
    if guild.id in SERVER_GIFS:
        embed.set_image(url=SERVER_GIFS[guild.id])
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
    else:
        # 🆕 استخدم شعار السيرفر كصورة أسفل كل رد
        if BOT_BANNER_URL:
            embed.set_image(url=BOT_BANNER_URL)
        elif guild.icon:
            embed.set_image(url=guild.icon.url)
        # استخدم شعار السيرفر كـ thumbnail أيضاً
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
    return embed

# روابط أيقونات احترافية (تستخدم في thumbnails)
ICONS = {
    "lobby":     "https://i.imgur.com/8RYMfAE.png",
    "match":     "https://i.imgur.com/8RYMfAE.png",
    "profile":   "https://i.imgur.com/8RYMfAE.png",
    "leaderboard": "https://i.imgur.com/8RYMfAE.png",
    "vote":      "https://i.imgur.com/8RYMfAE.png",
    "win":       "https://i.imgur.com/8RYMfAE.png",
    "lose":      "https://i.imgur.com/8RYMfAE.png",
    "info":      "https://i.imgur.com/8RYMfAE.png",
    "warning":   "https://i.imgur.com/8RYMfAE.png",
    "error":     "https://i.imgur.com/8RYMfAE.png",
    "admin":     "https://i.imgur.com/8RYMfAE.png",
}


def get_rank_color(level):
    """🆕 يرجع لون حسب الترتيب — 1 = الأفضل (ذهبي)، الأعلى رقماً = الأسوأ (رمادي)."""
    if level <= 1:    return COLORS["rank_legend"]   # 👑 #1
    if level <= 3:    return COLORS["rank_elite"]    # 💎 Top 3
    if level <= 10:   return COLORS["rank_high"]     # 🔥 Top 10
    if level <= 50:   return COLORS["rank_mid"]      # ⭐ Top 50
    return COLORS["rank_low"]                        # 🎯 باقي اللاعبين


def get_rank_title(level):
    """🆕 يرجع لقب اللاعب حسب الترتيب (متوافق مع أسماء الـ Roles)."""
    if level == 1:   return "Best Player"
    if level <= 10:  return "Goated Player"
    if level <= 50:  return "Skilled Player"
    if level <= 100: return "Efficient Player"
    return "Rookie"


def get_rank_emoji(level):
    """🆕 يرجع إيموجي حسب الترتيب."""
    if level <= 1:    return "👑"  # #1
    if level <= 3:    return "💎"  # Top 3
    if level <= 10:   return "🔥"  # Top 10
    if level <= 50:   return "⭐"  # Top 50
    return "🎯"  # باقي اللاعبين


def make_progress_bar(current, total, length=10):
    """يصنع شريط تقدم بصري احترافي."""
    if total == 0:
        return "░" * length
    filled = int((current / total) * length)
    filled = min(filled, length)
    return "█" * filled + "░" * (length - filled)


def make_winrate_bar(winrate, length=10):
    """شريط نسبة الفوز بألوان متدرجة."""
    filled = round(winrate / 10)
    filled = min(filled, length)
    if winrate >= 70:
        return "🟩" * filled + "⬛" * (length - filled)
    elif winrate >= 40:
        return "🟨" * filled + "⬛" * (length - filled)
    else:
        return "🟥" * filled + "⬛" * (length - filled)


def separator():
    """فاصل بصري احترافي."""
    return "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"


def compute_rank_from_points(points):
    """🆕 deprecated — الرانك الآن يُحسب من الترتيب في الـ leaderboard."""
    return STARTING_LEVEL  # placeholder


def points_to_next_rank(points):
    """🆕 deprecated — لا يوجد "رانك تالي" بنظام ثابت الآن.
    الرانك يعتمد على ترتيبك مقابل اللاعبين الآخرين.
    """
    return 0


def get_mvp_player(players_list, guild, db, gid):
    """🆕 يحدد MVP الفريق — أعلى رانك (أي أقل رقم رانك)، ولو تعادل → أعلى streak.
    يعالج حالة الفريق الفارغ بإرجاع None.
    """
    if not players_list:
        return None
    best = None
    best_score = -1
    for pid in players_list:
        player = db.get_player(pid, gid)
        if not player:
            continue
        # 🆕 في النظام الجديد: رانك أقل = أفضل. نضرب في -1 لنحوّله لأعلى = أفضل
        # Score = -level (لأن level أقل = أفضل) + win_streak (للتفريق بين المتعادلين)
        score = -player.get("level", 9999) * 1000 + player.get("win_streak", 0)
        if score > best_score:
            best_score = score
            best = pid
    return best


def get_mvp_badge(mvp_count):
    """🆕 يرجع شارة MVP حسب عدد MVPs.
    - 0 MVPs: لا شارة
    - 1-4 MVPs: 🥉 Bronze
    - 5-19 MVPs: 🥈 Silver
    - 20-49 MVPs: 🥇 Gold
    - 50-99 MVPs: 💎 Diamond
    - 100+ MVPs: 👑 Legend
    """
    if mvp_count >= 100:
        return "👑"  # Legend
    if mvp_count >= 50:
        return "💎"  # Diamond
    if mvp_count >= 20:
        return "🥇"  # Gold
    if mvp_count >= 5:
        return "🥈"  # Silver
    if mvp_count >= 1:
        return "🥉"  # Bronze
    return ""


def get_mvp_title(mvp_count):
    """🆕 يرجع لقب MVP حسب العدد."""
    if mvp_count >= 100:
        return "MVP Legend"
    if mvp_count >= 50:
        return "MVP Diamond"
    if mvp_count >= 20:
        return "MVP Gold"
    if mvp_count >= 5:
        return "MVP Silver"
    if mvp_count >= 1:
        return "MVP Bronze"
    return "Rookie"


# ============================================================
# 🆕 RANK-BASED ROLES — نظام الألقاب الديناميكي
# ============================================================

def get_role_tier_for_rank(rank):
    """🆕 يحدد أي tier من الـ Roles يجب أن يحصل عليه اللاعب حسب ترتيبه.
    يرجع رقم الـ tier (1=Best, 2=Goated, 3=Skilled, 4=Efficient) أو None لو فوق #100.
    """
    if rank == 1:
        return 1  # Best Player
    if rank <= 10:
        return 2  # Goated Players
    if rank <= 50:
        return 3  # Skilled Players
    if rank <= 100:
        return 4  # Efficient Players
    return None  # فوق #100 = لا role


async def create_role_if_not_exists(guild, role_name, color):
    """🆕 ينشئ role لو غير موجود، ويرجعه."""
    # ابحث عن role موجود بنفس الاسم
    for role in guild.roles:
        if role.name == role_name:
            return role
    # أنشئ role جديد
    try:
        new_role = await guild.create_role(
            name=role_name,
            color=discord.Color(color),
            reason=f"Free Fire Bot — Rank title role"
        )
        logger.info(f"✅ Created role: {role_name}")
        return new_role
    except discord.Forbidden:
        logger.warning(f"❌ No permission to create role: {role_name}")
        return None
    except discord.HTTPException as e:
        logger.warning(f"❌ Failed to create role {role_name}: {e}")
        return None


async def sync_player_role(guild, member, rank):
    """🆕 يزامن role اللاعب حسب ترتيبه.
    - يعطيه الـ role المناسب لترتيبه
    - يسحب منه أي role من tiers أعلى/أقل لم يعد يستحقه
    - يحدّث صلاحيات SoundBoard و Waiting Prv
    """
    if not member or member.bot:
        return
    target_tier = get_role_tier_for_rank(rank)

    # اجمع كل أسماء الـ roles الخاصة بالألقاب
    title_role_names = {tier: data["name"] for tier, data in RANK_TITLES.items()}

    # أزل من اللاعب أي role لقب لم يعد يستحقه
    for tier, role_name in title_role_names.items():
        if tier == target_tier:
            continue  # هذا الـ role اللي نبيه — اتركه
        # لو اللاعب عنده هذا الـ role، اسحبه
        for role in member.roles:
            if role.name == role_name:
                try:
                    await member.remove_roles(role, reason=f"Rank changed to #{rank} — lost {role_name}")
                    logger.info(f"📤 Removed role {role_name} from {member.display_name} (now RANK #{rank})")
                except (discord.HTTPException, discord.Forbidden):
                    pass
                break

    # أعطِ اللاعب الـ role المناسب لو يستحقه
    if target_tier:
        target_role_name = RANK_TITLES[target_tier]["name"]
        # تحقق إن ما عنده بالفعل
        has_role = any(r.name == target_role_name for r in member.roles)
        if not has_role:
            role = await create_role_if_not_exists(guild, target_role_name, RANK_TITLES[target_tier]["color"])
            if role:
                try:
                    await member.add_roles(role, reason=f"Rank #{rank} — earned {target_role_name}")
                    logger.info(f"📥 Added role {target_role_name} to {member.display_name} (now RANK #{rank})")
                except (discord.HTTPException, discord.Forbidden):
                    pass


async def sync_all_players_roles(guild):
    """🆕 يزامن roles كل اللاعبين في السيرفر حسب ترتيبهم الحالي.
    تُستدعى بعد كل recalculate_ranks().
    """
    try:
        # اجلب كل اللاعبين مرتبين
        players = db.get_leaderboard(guild.id, limit=None)  # كل اللاعبين
        if not players:
            return
        for player in players:
            member = guild.get_member(player["user_id"])
            if member and not member.bot:
                rank = player.get("level", 9999)
                await sync_player_role(guild, member, rank)
                await asyncio.sleep(0.1)  # تجنب rate limit
    except Exception as e:
        logger.exception(f"sync_all_players_roles failed: {e}")


async def setup_rank_roles_permissions(guild):
    """🆕 ينشئ كل الـ roles ويحدّث صلاحيات Waiting Prv و SoundBoard.
    تُستدعى من !!setup.
    """
    # أنشئ الـ roles
    for tier, data in RANK_TITLES.items():
        await create_role_if_not_exists(guild, data["name"], data["color"])

    # 🆕 حدّث صلاحيات غرف Waiting Prv — أعطِ Best Player + Goated صلاحية Connect
    for role in guild.roles:
        if role.name in [RANK_TITLES[1]["name"], RANK_TITLES[2]["name"]]:
            # اجلب كل غرف Waiting Prv
            for ch in guild.voice_channels:
                if WAITING_PRV_CATEGORY_HINT.lower() in ch.name.lower():
                    try:
                        # أعطِ role صلاحية Connect
                        overwrite = ch.overwrites_for(role)
                        overwrite.connect = True
                        overwrite.view_channel = True
                        await ch.set_permissions(role, overwrite=overwrite, reason="Free Fire Bot — Rank title permissions")
                    except (discord.HTTPException, discord.Forbidden):
                        pass
    logger.info(f"✅ Rank roles setup complete in {guild.name}")


async def notify_admins(guild, title, description, color=None):
    """🆕 يرسل رسالة تاغ للأدمنز في قناة match-results.
    يُستخدم عند حدوث مشاكل (vote timeout، خطأ في create_match_channels، إلخ).
    """
    try:
        if color is None:
            color = COLORS["error"]
        # ابحث عن role الأدمن
        admin_role = None
        for role in guild.roles:
            if role.name.lower() == ADMIN_ROLE_NAME.lower():
                admin_role = role
                break
        admin_mention = admin_role.mention if admin_role else f"@{ADMIN_ROLE_NAME}"
        # ابحث عن قناة match-results
        settings = db.get_guild_settings(guild.id)
        channel = None
        if settings:
            for cid in db.get_commands_channels(guild.id):
                ch = guild.get_channel(cid)
                if ch and "match-results" in ch.name.lower():
                    channel = ch
                    break
        if not channel:
            # fallback: أول قناة play
            play_channels = db.get_play_channels(guild.id)
            if play_channels:
                channel = guild.get_channel(play_channels[0])
        if not channel:
            return
        embed = discord.Embed(
            title=f"⚠️  {title}",
            description=f"{admin_mention}\n{description}",
            color=color,
            timestamp=discord.utils.utcnow()
        )
        embed.set_author(name="Admin Alert", icon_url=None)
        embed.set_footer(text=f"{BOT_FOOTER}  •  Action required")
        embed = apply_branding(embed, guild)
        await channel.send(content=admin_mention, embed=embed)
    except Exception as e:
        logger.exception(f"notify_admins failed: {e}")

GUILD_SETTINGS_COLUMNS = {
    "form_channel_id", "announcement_role_id", "leaderboard_channel_id",
    "leaderboard_message_id", "auto_channel_category_id",
    "report_channel_ids"  # 🆕 قائمة فويسات التفتيش المحددة من الأدمن (JSON array)
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
                    auto_channel_category_id INTEGER DEFAULT NULL,
                    report_channel_ids TEXT DEFAULT NULL
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
                CREATE TABLE IF NOT EXISTS player_reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER NOT NULL,
                    reporter_id INTEGER NOT NULL,
                    reported_id INTEGER NOT NULL,
                    lobby_id INTEGER DEFAULT NULL,
                    reason TEXT DEFAULT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(guild_id, reporter_id, reported_id)
                );
                CREATE TABLE IF NOT EXISTS banned_players (
                    guild_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    ban_reason TEXT DEFAULT NULL,
                    report_count INTEGER DEFAULT 0,
                    banned_by INTEGER DEFAULT NULL,
                    banned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    assigned_voice_id INTEGER DEFAULT NULL,
                    PRIMARY KEY (guild_id, user_id)
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
                # 🆕 FIX: store the StartVote button message_id so the
                # persistent StartVoteView can recover lobby_id after restart.
                ("lobbies", "start_vote_message_id", "INTEGER DEFAULT NULL"),
                # 🆕 FIX: store the assigned investigation voice for each banned player
                ("banned_players", "assigned_voice_id", "INTEGER DEFAULT NULL"),
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
                # 🆕 كل لاعب جديد يبدأ بـ RANK 1000 ونقاط 0
                conn.execute("INSERT INTO players(user_id,guild_id,username,level,points) VALUES(?,?,?,?,0)", (uid, gid, name, STARTING_LEVEL))
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
        """🆕 يرجع اللاعبين مرتبين حسب النقاط. limit=None يرجع كل اللاعبين."""
        conn = self.conn()
        try:
            if limit is None:
                return [dict(x) for x in conn.execute(
                    "SELECT * FROM players WHERE guild_id=? ORDER BY points DESC, wins DESC, matches_played ASC",
                    (gid,)
                ).fetchall()]
            return [dict(x) for x in conn.execute(
                "SELECT * FROM players WHERE guild_id=? ORDER BY points DESC, wins DESC, matches_played ASC LIMIT ?",
                (gid, limit)
            ).fetchall()]
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

    # 🆕 FIX: look up lobby by the original lobby message (Join Team buttons)
    def get_lobby_id_by_lobby_message(self, message_id):
        conn = self.conn()
        try:
            r = conn.execute("SELECT id FROM lobbies WHERE message_id=?", (message_id,)).fetchone()
            return r["id"] if r else None
        finally:
            conn.close()

    # 🆕 FIX: look up lobby by the StartVote button message
    def get_lobby_id_by_start_vote_message(self, message_id):
        conn = self.conn()
        try:
            r = conn.execute("SELECT id FROM lobbies WHERE start_vote_message_id=?", (message_id,)).fetchone()
            return r["id"] if r else None
        finally:
            conn.close()

    # 🆕 FIX: store the StartVote button message_id for later recovery
    def set_start_vote_message(self, lid, mid):
        conn = self.conn()
        try:
            conn.execute("UPDATE lobbies SET start_vote_message_id=? WHERE id=?", (mid, lid))
            conn.commit()
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
        """🆕 يضيف/يخصم نقاط.
        الرانك يُحسب من الترتيب في الـ leaderboard (1 = الأعلى نقاط).
        يتم تحديث الرانك لكل اللاعبين بعد كل تغيير عبر recalculate_ranks().
        """
        conn = self.conn()
        try:
            # 1) تحديث النقاط (لا تنزل تحت 0)
            conn.execute(
                "UPDATE players SET points=MAX(0,points+?), last_active=? WHERE user_id=? AND guild_id=?",
                (amount, datetime.now().isoformat(), uid, gid)
            )
            conn.commit()
        finally:
            conn.close()
        # 2) 🆕 أعِد حساب رانك كل اللاعبين (الرانك = الترتيب في الـ leaderboard)
        self.recalculate_ranks(gid)

    def recalculate_ranks(self, gid):
        """🆕 يُعيد حساب رانك كل اللاعبين في السيرفر.
        - اللاعبون بنقاط 0 → RANK 1000 (لم يبدأوا بعد)
        - اللاعبون بنقاط > 0 → يُرتبون حسب النقاط (1 = الأعلى)
        """
        conn = self.conn()
        try:
            # اللاعبون الذين لديهم نقاط > 0 — رتبهم
            active_players = conn.execute(
                "SELECT user_id, points FROM players WHERE guild_id=? AND points > 0 ORDER BY points DESC, wins DESC, matches_played ASC",
                (gid,)
            ).fetchall()
            
            updates = []
            # رتّب اللاعبين النشطين (1 = الأعلى نقاط)
            current_rank = 1
            prev_points = None
            for i, p in enumerate(active_players):
                if prev_points is not None and p["points"] == prev_points:
                    pass  # نفس الرانك السابق
                else:
                    current_rank = i + 1
                updates.append((current_rank, p["user_id"]))
                prev_points = p["points"]
            
            # اللاعبون بنقاط 0 → RANK 1000
            zero_players = conn.execute(
                "SELECT user_id FROM players WHERE guild_id=? AND points = 0",
                (gid,)
            ).fetchall()
            for p in zero_players:
                updates.append((STARTING_LEVEL, p["user_id"]))
            
            if updates:
                conn.executemany(
                    "UPDATE players SET level=? WHERE user_id=? AND guild_id=?",
                    [(rank, uid, gid) for rank, uid in updates]
                )
                conn.commit()
        finally:
            conn.close()

    def get_player_rank_position(self, uid, gid):
        """🆕 يرجع ترتيب اللاعب في السيرفر (1 = الأعلى نقاط)."""
        conn = self.conn()
        try:
            player = conn.execute(
                "SELECT points FROM players WHERE user_id=? AND guild_id=?",
                (uid, gid)
            ).fetchone()
            if not player:
                return None
            # عدّ اللاعبين الذين نقاطهم أعلى
            higher = conn.execute(
                "SELECT COUNT(*) FROM players WHERE guild_id=? AND points > ?",
                (gid, player["points"])
            ).fetchone()[0]
            return higher + 1  # ترتيبه = عدد من فوقه + 1
        finally:
            conn.close()

    # ============================================================
    # 🆕 REPORTS & BANS — نظام البلاغات والحظر
    # ============================================================
    def add_report(self, gid, reporter_id, reported_id, lobby_id=None, reason=None):
        """يسجل بلاغ. يرجع (True, total_count) لو نجح، (False, total_count) لو مكرر."""
        conn = self.conn()
        try:
            try:
                conn.execute(
                    "INSERT INTO player_reports(guild_id, reporter_id, reported_id, lobby_id, reason) VALUES(?,?,?,?,?)",
                    (gid, reporter_id, reported_id, lobby_id, reason)
                )
                conn.commit()
                added = True
            except sqlite3.IntegrityError:
                added = False  # بلّغ من قبل على نفس اللاعب
            total = conn.execute(
                "SELECT COUNT(*) FROM player_reports WHERE guild_id=? AND reported_id=?",
                (gid, reported_id)
            ).fetchone()[0]
            return added, total
        finally:
            conn.close()

    def get_reports_count(self, gid, reported_id):
        """يرجع عدد البلاغات على لاعب."""
        conn = self.conn()
        try:
            return conn.execute(
                "SELECT COUNT(*) FROM player_reports WHERE guild_id=? AND reported_id=?",
                (gid, reported_id)
            ).fetchone()[0]
        finally:
            conn.close()

    def get_reports_for_player(self, gid, reported_id):
        """يرجع قائمة البلاغات على لاعب."""
        conn = self.conn()
        try:
            return [dict(x) for x in conn.execute(
                "SELECT * FROM player_reports WHERE guild_id=? AND reported_id=? ORDER BY created_at DESC",
                (gid, reported_id)
            ).fetchall()]
        finally:
            conn.close()

    def clear_reports(self, gid, reported_id):
        """يحذف كل البلاغات على لاعب (بعد فك الحظر مثلاً)."""
        conn = self.conn()
        try:
            conn.execute(
                "DELETE FROM player_reports WHERE guild_id=? AND reported_id=?",
                (gid, reported_id)
            )
            conn.commit()
        finally:
            conn.close()

    def ban_player(self, gid, user_id, reason=None, banned_by=None, report_count=0, assigned_voice_id=None):
        """يحظر لاعب من استخدام البوت + يحدد فويس التفتيش المخصص."""
        conn = self.conn()
        try:
            # 🆕 احفظ الـ assigned_voice_id لو موجود، وإلا احتفظ بالقديم
            existing = conn.execute(
                "SELECT assigned_voice_id FROM banned_players WHERE guild_id=? AND user_id=?",
                (gid, user_id)
            ).fetchone()
            old_voice = existing["assigned_voice_id"] if existing else None
            final_voice = assigned_voice_id if assigned_voice_id is not None else old_voice
            conn.execute(
                "INSERT OR REPLACE INTO banned_players(guild_id, user_id, ban_reason, report_count, banned_by, assigned_voice_id) VALUES(?,?,?,?,?,?)",
                (gid, user_id, reason, report_count, banned_by, final_voice)
            )
            conn.commit()
        finally:
            conn.close()

    def set_banned_voice(self, gid, user_id, voice_id):
        """🆕 يحدد فويس التفتيش المخصص للاعب المحظور."""
        conn = self.conn()
        try:
            conn.execute(
                "UPDATE banned_players SET assigned_voice_id=? WHERE guild_id=? AND user_id=?",
                (voice_id, gid, user_id)
            )
            conn.commit()
        finally:
            conn.close()

    def unban_player(self, gid, user_id):
        """يفك حظر لاعب."""
        conn = self.conn()
        try:
            conn.execute(
                "DELETE FROM banned_players WHERE guild_id=? AND user_id=?",
                (gid, user_id)
            )
            conn.commit()
        finally:
            conn.close()

    def is_player_banned(self, gid, user_id):
        """يرجع True لو اللاعب محظور + بيانات الحظر (بما فيها assigned_voice_id)."""
        conn = self.conn()
        try:
            r = conn.execute(
                "SELECT * FROM banned_players WHERE guild_id=? AND user_id=?",
                (gid, user_id)
            ).fetchone()
            return dict(r) if r else None
        finally:
            conn.close()

    def get_banned_players(self, gid):
        """يرجع كل اللاعبين المحظورين في السيرفر."""
        conn = self.conn()
        try:
            return [dict(x) for x in conn.execute(
                "SELECT * FROM banned_players WHERE guild_id=? ORDER BY banned_at DESC",
                (gid,)
            ).fetchall()]
        finally:
            conn.close()

    # ============================================================
    # 🆕 REPORT CHANNELS — فويسات التفتيش المحددة من الأدمن
    # ============================================================
    def get_report_channels(self, gid):
        """يرجع قائمة فويسات التفتيش المحددة من الأدمن."""
        conn = self.conn()
        try:
            r = conn.execute(
                "SELECT report_channel_ids FROM guild_settings WHERE guild_id=?",
                (gid,)
            ).fetchone()
            if r and r["report_channel_ids"]:
                try:
                    return json.loads(r["report_channel_ids"])
                except (json.JSONDecodeError, TypeError):
                    return []
            return []
        finally:
            conn.close()

    def set_report_channels(self, gid, channel_ids):
        """يحفظ قائمة فويسات التفتيش."""
        conn = self.conn()
        try:
            conn.execute("INSERT OR IGNORE INTO guild_settings(guild_id) VALUES(?)", (gid,))
            conn.execute(
                "UPDATE guild_settings SET report_channel_ids=? WHERE guild_id=?",
                (json.dumps(channel_ids), gid)
            )
            conn.commit()
        finally:
            conn.close()

    def add_report_channel(self, gid, channel_id):
        """يضيف فويس تفتيش للقائمة."""
        channels = self.get_report_channels(gid)
        if channel_id not in channels:
            channels.append(channel_id)
            self.set_report_channels(gid, channels)
            return True
        return False

    def remove_report_channel(self, gid, channel_id):
        """يحذف فويس تفتيش من القائمة."""
        channels = self.get_report_channels(gid)
        if channel_id in channels:
            channels.remove(channel_id)
            self.set_report_channels(gid, channels)
            return True
        return False


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
    """🎮 Lobby Embed — تصميم احترافي جديد."""
    mode = lobby.get("game_mode", DEFAULT_MODE)
    mode_info = GAME_MODES.get(mode, GAME_MODES[DEFAULT_MODE])
    team_size = mode_info["team_size"]
    lobby_size = mode_info["lobby_size"]
    mode_emoji = mode_info["emoji"]
    mode_color = mode_info["color"]

    t1 = lobby.get("team1_players", [])
    t2 = lobby.get("team2_players", [])
    total = len(t1) + len(t2)

    embed = discord.Embed(
        title=f"{mode_emoji}  لوبي جديد متاح",
        description=(
            f"{separator()}\n"
            f"**🆔 Lobby ID:** `#{lobby['id']}`\n"
            f"**👑 Host:** <@{lobby['creator_id']}>\n"
            f"**⚔️ Mode:** `{mode.upper()}` ({team_size}v{team_size})\n"
            f"**📊 التقدم:** {make_progress_bar(total, lobby_size, length=12)} `{total}/{lobby_size}`\n"
            f"{separator()}"
        ),
        color=mode_color,
        timestamp=discord.utils.utcnow()
    )

    def format_team(team_list, size):
        lines = []
        for i in range(size):
            if i < len(team_list):
                lines.append(f"`{i+1}.` <@{team_list[i]}>")
            else:
                lines.append(f"`{i+1}.` *فارغ - متاح*")
        return "\n".join(lines)

    embed.add_field(
        name=f"🔴 Team 1 ({len(t1)}/{team_size})",
        value=format_team(t1, team_size),
        inline=True
    )
    embed.add_field(
        name=f"🟢 Team 2 ({len(t2)}/{team_size})",
        value=format_team(t2, team_size),
        inline=True
    )

    # حالة اللوبي
    if total == 0:
        status = "⏳ في انتظار اللاعبين..."
    elif total < lobby_size:
        status = f"⏳ يحتاج `{lobby_size - total}` لاعب آخر للبدء"
    else:
        status = "🎮 الماتش جاهز للبدء!"
    embed.add_field(name="📌 الحالة", value=f"> {status}", inline=False)

    # معلومات الغرفة الخاصة
    pk = db.get_lobby_private_key(lobby['id'])
    if pk and not lobby.get('room_id'):
        embed.add_field(
            name="🔐 Private Match",
            value=f"> هذا الماتش محمي بمفتاح خاص.\n> اطلب المفتاح من <@{lobby['creator_id']}> للدخول.",
            inline=False
        )

    host_member = guild.get_member(lobby['creator_id']) if guild else None
    embed.set_author(
        name=f"Host: {host_member.display_name}" if host_member else "Host",
        icon_url=host_member.display_avatar.url if host_member else None
    )
    embed.set_footer(text=f"{BOT_FOOTER}  •  Lobby #{lobby['id']}")
    embed = apply_branding(embed, guild)

    return embed


def create_profile_embed(player, member=None):
    """🪪 Profile Embed — بطاقة لاعب احترافية بتصميم جديد."""
    level = player.get("level", STARTING_LEVEL)
    rank_title = get_rank_title(level)
    rank_emoji = get_rank_emoji(level)
    rank_color = get_rank_color(level)
    points = player.get("points", 0)

    wins = player.get("wins", 0)
    losses = player.get("losses", 0)
    mvps = player.get("mvps", 0)
    matches_played = player.get("matches_played", 0)
    win_streak = player.get("win_streak", 0)
    max_win_streak = player.get("max_win_streak", 0)
    wr = round((wins / max(matches_played, 1)) * 100, 1)

    mvp_badge = get_mvp_badge(mvps)
    mvp_title = get_mvp_title(mvps)

    display_name = member.display_name if member else player.get("username", "لاعب مجهول")
    avatar_url = member.display_avatar.url if member else None

    embed = discord.Embed(
        title=f"🪪 بطاقة اللاعب — {display_name}",
        description=(
            f"{separator()}\n"
            f"**{rank_emoji} الرانك:** `#{level}` — **{rank_title}**\n"
            f"**⭐ النقاط:** `{points:,}`\n"
            f"**{mvp_badge} شارة الإنجاز:** {mvp_badge} ({mvp_title})\n"
            f"{separator()}"
        ),
        color=rank_color,
        timestamp=discord.utils.utcnow()
    )

    # الإحصائيات (3×2 grid)
    embed.add_field(name="✅ Wins", value=f"```fix\n{wins}\n```", inline=True)
    embed.add_field(name="❌ Losses", value=f"```fix\n{losses}\n```", inline=True)
    embed.add_field(name="👑 MVPs", value=f"```fix\n{mvps}\n```", inline=True)
    embed.add_field(name="🎮 Matches", value=f"```fix\n{matches_played}\n```", inline=True)
    embed.add_field(name="🔥 Streak", value=f"```fix\n{win_streak}\n```", inline=True)
    embed.add_field(name="🏆 Best Streak", value=f"```fix\n{max_win_streak}\n```", inline=True)

    # شريط Win Rate
    wr_status = "🔥 God Tier" if wr >= 70 else ("⭐ Pro" if wr >= 50 else ("🌱 Rising" if wr >= 30 else "💀 Struggling"))
    embed.add_field(
        name=f"📊 Win Rate — `{wr}%` {wr_status}",
        value=f"{make_winrate_bar(wr)} `{wins}/{matches_played}`",
        inline=False
    )

    embed.set_author(name=f"{display_name} • {rank_title}", icon_url=avatar_url if avatar_url else None)
    if avatar_url:
        embed.set_thumbnail(url=avatar_url)
    embed.set_footer(text=f"{BOT_FOOTER}  •  {rank_title} #{level}  •  {mvp_title}")

    # 🆕 أضف الـ branding (GIF + شعار السيرفر) لو عضو في السيرفر المحدد
    if member and member.guild:
        embed = apply_branding(embed, member.guild)

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
    """🆕 Leaderboard محدّث — يعرض النقاط والرانك معاً + يتحدث تلقائياً بعد كل ماتش."""
    try:
        settings = db.get_guild_settings(guild.id)
        if not settings or not settings.get("leaderboard_channel_id"):
            return
        channel = guild.get_channel(settings["leaderboard_channel_id"])
        if not channel:
            return
        lb = db.get_leaderboard(guild.id, 10)
        embed = discord.Embed(
            title="🏆  Free Fire  —  Top 10 Players",
            description=(
                f"> 📊  ترتيب اللاعبين حسب النقاط\n"
                f"> 🔄  يتحدث تلقائياً بعد كل مباراة\n"
                f"> 📈  كل `50` نقطة = `+1` رانك\n"
                f"{separator()}"
            ),
            color=COLORS["leaderboard"],
            timestamp=discord.utils.utcnow()
        )
        if not lb:
            embed.description = (
                f"> 📭  لا يوجد لاعبون بعد!\n"
                f"> استخدم  `{PREFIX}play 4v4`  لبدء أول ماتش.\n"
                f"{separator()}"
            )
        else:
            medals = ["🥇", "🥈", "🥉", "🏅", "🎖️", "🏵️", "🏷️", "8️⃣", "9️⃣", "🔟"]
            desc = ""
            for i, p in enumerate(lb):
                m = medals[i] if i < len(medals) else f"`#{i+1}`"
                mem = guild.get_member(p["user_id"])
                name = mem.display_name if mem else p["username"]
                level = p.get("level", STARTING_LEVEL)
                rank_emoji = get_rank_emoji(level)
                rank_title = get_rank_title(level)
                wr = round((p["wins"] / max(p["matches_played"], 1)) * 100, 1)
                wr_status = "🔥" if wr >= 70 else ("⭐" if wr >= 50 else "🌱")
                pts_to_next = points_to_next_rank(p["points"])
                # خط فاصل بين كل لاعب
                if i > 0:
                    desc += "─" * 28 + "\n"
                next_rank_hint = f"  •  ⏭️ `{pts_to_next}` للرانك التالي" if pts_to_next > 0 else "  •  🎯 رانك جديد!"
                desc += (
                    f"{m}  **{rank_emoji} {name}**\n"
                    f"└ 💰 `{p['points']:,}` pts  •  🏅 `RANK #{level}` ({rank_title})\n"
                    f"└ 🎮 `{p['matches_played']}` M  •  ✅ `{p['wins']}` W  ❌ `{p['losses']}` L  •  📊 `{wr}%` {wr_status}\n"
                    f"└ 👑 `{p['mvps']}` MVPs{next_rank_hint}\n"
                )
            embed.description = desc
        embed.set_footer(text=f"{BOT_FOOTER}  •  Live Leaderboard  •  {len(lb)} players")
        embed.set_author(name=f"{guild.name} Leaderboard", icon_url=None)
        embed = apply_branding(embed, guild)
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


async def create_banned_voice_channels(guild):
    """🆕 ينشئ كاتيجوري + 3 فويسات للمحظورين (للتفتيش).
    يستخدم db لـ cache الـ channel IDs في guild_settings.
    """
    cat = discord.utils.get(guild.categories, name=REPORT_CATEGORY_NAME)
    if not cat:
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False, connect=False),
            guild.me: discord.PermissionOverwrite(view_channel=True, connect=True, manage_channels=True, move_members=True),
        }
        # الأدمن يقدر يدخل
        for role in guild.roles:
            if role.permissions.administrator or role.permissions.manage_guild:
                overwrites[role] = discord.PermissionOverwrite(view_channel=True, connect=True, move_members=True)
        cat = await guild.create_category(REPORT_CATEGORY_NAME, overwrites=overwrites)
    # انشئ الفويسات إن لم تكن موجودة
    channel_ids = []
    for i in range(1, REPORT_CHANNELS_COUNT + 1):
        ch_name = f"🚨  Investigation {i}"
        ch = discord.utils.get(guild.voice_channels, name=ch_name)
        if not ch:
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(view_channel=False, connect=False),
                guild.me: discord.PermissionOverwrite(view_channel=True, connect=True, manage_channels=True, move_members=True),
            }
            for role in guild.roles:
                if role.permissions.administrator or role.permissions.manage_guild:
                    overwrites[role] = discord.PermissionOverwrite(view_channel=True, connect=True, move_members=True)
            ch = await guild.create_voice_channel(ch_name, category=cat, overwrites=overwrites)
        channel_ids.append(ch.id)
    return channel_ids


async def move_to_banned_channels(guild, member, assign_permanent=False):
    """🆕 ينقل لاعب محظور لأول فويس تفتيش متاح.
    أولوية: الفويسات المحددة من الأدمن (db.get_report_channels)
    fallback: إنشاء فويسات تلقائية لو ما فيه فويسات محددة
    لو assign_permanent=True، يحفظ الفويس المخصص للاعب في الـ DB
    """
    # 🆕 لو اللاعب عنده فويس مخصص محفوظ، استخدمه أولاً
    ban_info = db.is_player_banned(guild.id, member.id)
    if ban_info and ban_info.get("assigned_voice_id"):
        assigned_ch = guild.get_channel(ban_info["assigned_voice_id"])
        if assigned_ch and isinstance(assigned_ch, discord.VoiceChannel):
            try:
                await member.move_to(assigned_ch)
                return assigned_ch
            except (discord.HTTPException, discord.Forbidden):
                pass  # وقع للبحث عن فويس جديد

    # 🆕 استخدم الفويسات المحددة من الأدمن أولاً
    admin_channel_ids = db.get_report_channels(guild.id)
    chosen_channel = None
    if admin_channel_ids:
        for cid in admin_channel_ids:
            ch = guild.get_channel(cid)
            if ch and isinstance(ch, discord.VoiceChannel):
                try:
                    await member.move_to(ch)
                    chosen_channel = ch
                    break
                except (discord.HTTPException, discord.Forbidden):
                    continue
        if not chosen_channel:
            logger.warning(f"All admin-set report channels failed for guild {guild.id}, falling back to auto-create")
    # fallback: أنشئ فويسات تلقائية
    if not chosen_channel:
        channel_ids = await create_banned_voice_channels(guild)
        for cid in channel_ids:
            ch = guild.get_channel(cid)
            if ch:
                try:
                    await member.move_to(ch)
                    chosen_channel = ch
                    break
                except (discord.HTTPException, discord.Forbidden):
                    continue
    # 🆕 احفظ الفويس المخصص للاعب (لو طُلب ذلك)
    if chosen_channel and assign_permanent:
        db.set_banned_voice(guild.id, member.id, chosen_channel.id)
    return chosen_channel


async def check_and_apply_auto_ban(guild, reported_id, total_reports, reported_by=None):
    """🆕 يفحص لو وصلت البلاغات لـ REPORT_THRESHOLD → حظر تلقائي + نقل لفويس التفتيش + تقييد.
    يرجع True لو تم الحظر.
    """
    if total_reports < REPORT_THRESHOLD:
        return False
    # حظر اللاعب
    db.ban_player(
        guild.id, reported_id,
        reason=f"Auto-ban: {total_reports} reports",
        banned_by=reported_by,
        report_count=total_reports
    )
    # نقل لفويس التفتيش + تعيين فويس دائم
    member = guild.get_member(reported_id)
    assigned_channel = None
    if member:
        # لو اللاعب في فويس، انقله
        if member.voice and member.voice.channel:
            assigned_channel = await move_to_banned_channels(guild, member, assign_permanent=True)
        else:
            # لو ما هو في فويس، حدد له فويس مقدمًا (سيُنقل لما يدخل فويس)
            admin_channel_ids = db.get_report_channels(guild.id)
            if admin_channel_ids:
                ch = guild.get_channel(admin_channel_ids[0])
                if ch and isinstance(ch, discord.VoiceChannel):
                    assigned_channel = ch
                    db.set_banned_voice(guild.id, reported_id, ch.id)
    # تاغ الأدمنز
    voice_info = ""
    if assigned_channel:
        voice_info = f"\n> 🔍  **فويس التفتيش:**  {assigned_channel.mention}\n> 🔒  **مقيّد:**  لا يمكنه مغادرة هذا الفويس"
    await notify_admins(
        guild,
        "🚨  Auto-Ban Triggered",
        f"> 🚨  تم حظر اللاعب تلقائياً بعد وصول بلاغاته إلى `{REPORT_THRESHOLD}`\n"
        f"> 👤  **اللاعب:**  <@{reported_id}>\n"
        f"> 📊  **عدد البلاغات:**  `{total_reports}`\n"
        f"> 🔍  **الإجراء:**  تم نقله لفويس التفتيش + تقييده{voice_info}\n"
        f"> 💡  استخدم  `!!unbanplayer @user`  لفك الحظر بعد التفتيش",
        color=COLORS["error"]
    )
    return True


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

        t1m = " ".join([f"<@{p}>" for p in lobby["team1_players"]])
        t2m = " ".join([f"<@{p}>" for p in lobby["team2_players"]])
        vote_embed = discord.Embed(
            title=f"🗳️  Vote  —  Match `#{lobby_id}`",
            description=(
                f"> انتهت المباراة! صوّت للفريق الفائز.\n"
                f"> ⏱️  لديك  **2 دقيقة**  للتصويت.\n"
                f"> 🎯  فقط لاعبو الماتش يقدرون يصوتون.\n"
                f"{separator()}"
            ),
            color=COLORS["vote"],
            timestamp=discord.utils.utcnow()
        )
        vote_embed.add_field(
            name=f"🔴  Team 1  —  `{len(lobby['team1_players'])}` players",
            value=t1m or "*لا يوجد لاعبون*",
            inline=True
        )
        vote_embed.add_field(
            name=f"🟢  Team 2  —  `{len(lobby['team2_players'])}` players",
            value=t2m or "*لا يوجد لاعبون*",
            inline=True
        )
        vote_embed.add_field(
            name="📋  How to Vote",
            value=(
                f"> اضغط زر  **🟠 Team 1**  أو  **🟢 Team 2**\n"
                f"> صوت واحد لكل لاعب.\n"
                f"> الأكثر أصواتاً = الفائز."
            ),
            inline=False
        )
        vote_embed.set_author(name="Match Vote", icon_url=None)
        vote_embed.set_footer(text=f"{BOT_FOOTER}  •  Vote ends in 2 minutes")
        vote_embed = apply_branding(vote_embed, guild)

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
            timeout_embed = discord.Embed(
                title="⏰  Lobby Timed Out",
                description=(
                    f"> اللوبي `#{lobby_id}` تم إلغاؤه بسبب عدم النشاط.\n"
                    f"> استخدم `{PREFIX}play 4v4` لبدء ماتش جديد."
                ),
                color=COLORS["warning"],
                timestamp=discord.utils.utcnow()
            )
            timeout_embed.set_footer(text=f"{BOT_FOOTER}  •  Lobby #{lobby_id}")
            embed = apply_branding(embed, guild)
            await ch.send(embed=timeout_embed)
    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.exception(f"auto_lobby_timeout failed: {e}")
        # 🆕 تاغ الأدمنز عند الفشل
        await notify_admins(
            guild,
            "Lobby Timeout Error",
            f"> ❌  خطأ في timeout اللوبي `#{lobby_id}`\n"
            f"> 🐛  **الخطأ:**  `{str(e)[:200]}`"
        )


# ============================================================
# PROCESS MATCH RESULT
# ============================================================

async def process_match_result(guild, lobby_id, winner_team, channel=None):
    """🆕 نظام النقاط الجديد:
    - الفائز MVP: +80 نقطة
    - الفائزون الآخرون: +30 نقطة
    - الخاسر MVP: +30 نقطة
    - الخاسرون الآخرون: -30 نقطة
    - الرانك يُحسب من النقاط تلقائياً (كل 50 نقطة = رانك واحد)
    """
    try:
        logger.info(f"🏆 process_match_result — lobby={lobby_id}, winner={winner_team}")
        lobby = db.get_lobby(lobby_id)
        if not lobby:
            return
        if lobby["status"] == "completed":
            logger.warning(f"Already completed: {lobby_id}")
            return

        db.update_lobby_status(lobby_id, "completed")

        game_mode = lobby.get("game_mode", DEFAULT_MODE)
        wt = lobby["team1_players"] if winner_team == "team1" else lobby["team2_players"]
        lt = lobby["team2_players"] if winner_team == "team1" else lobby["team1_players"]

        # 🆕 تحديد MVP لكل فريق (أعلى رانك، ثم أعلى streak عند التعادل)
        winner_mvp_id = get_mvp_player(wt, guild, db, guild.id)
        loser_mvp_id = get_mvp_player(lt, guild, db, guild.id)

        # 🆕 نقاط النظام الجديد
        WINNER_MVP_POINTS = 80
        WINNER_POINTS = 30
        LOSER_MVP_POINTS = 30
        LOSER_POINTS = -30

        # معالجة الفريق الفائز
        winner_details = []  # [(pid, points_awarded, is_mvp), ...]
        for pid in wt:
            p = db.get_player(pid, guild.id)
            if not p:
                continue
            is_mvp = (pid == winner_mvp_id)
            pts = WINNER_MVP_POINTS if is_mvp else WINNER_POINTS
            old_level = p.get("level", STARTING_LEVEL)
            new_win_streak = p.get("win_streak", 0) + 1
            new_max = max(p.get("max_win_streak", 0), new_win_streak)

            # تحديث النقاط + الإحصائيات (add_points يزامن الرانك تلقائياً)
            db.add_points(pid, guild.id, pts)
            db.update_player_stats(
                pid, guild.id,
                wins=p["wins"] + 1,
                matches_played=p["matches_played"] + 1,
                win_streak=new_win_streak,
                lose_streak=0,
                max_win_streak=new_max,
                mvps=p["mvps"] + (1 if is_mvp else 0)
            )
            # حدّث النك نيم بالرانك الجديد
            new_p = db.get_player(pid, guild.id)
            new_level = new_p.get("level", STARTING_LEVEL) if new_p else old_level
            m = guild.get_member(pid)
            if m:
                await update_member_nickname(m, new_level)
            winner_details.append((pid, pts, is_mvp, old_level, new_level))

        # معالجة الفريق الخاسر
        loser_details = []
        for pid in lt:
            p = db.get_player(pid, guild.id)
            if not p:
                continue
            is_mvp = (pid == loser_mvp_id)
            pts = LOSER_MVP_POINTS if is_mvp else LOSER_POINTS
            old_level = p.get("level", STARTING_LEVEL)
            new_lose_streak = p.get("lose_streak", 0) + 1

            db.add_points(pid, guild.id, pts)
            db.update_player_stats(
                pid, guild.id,
                losses=p["losses"] + 1,
                matches_played=p["matches_played"] + 1,
                win_streak=0,
                lose_streak=new_lose_streak,
                mvps=p["mvps"] + (1 if is_mvp else 0)
            )
            new_p = db.get_player(pid, guild.id)
            new_level = new_p.get("level", STARTING_LEVEL) if new_p else old_level
            m = guild.get_member(pid)
            if m:
                await update_member_nickname(m, new_level)
            loser_details.append((pid, pts, is_mvp, old_level, new_level))

        # 🆕 حفظ نتيجة الماتش مع MVPs
        db.create_match_result(
            lobby_id, winner_team,
            len(wt), len(lt),
            mvp=winner_mvp_id
        )

        # 🆕 بناء رسالة النتيجة الاحترافية
        wd = "🔴  Team 1" if winner_team == "team1" else "🟢  Team 2"
        wt_mentions = "\n".join([
            f"{'👑' if is_mvp else '✅'}  <@{pid}>  →  `{'+' if pts > 0 else ''}{pts}` pts  (RANK #{old}→#{new})"
            for pid, pts, is_mvp, old, new in winner_details
        ]) or "*لا يوجد لاعبون*"
        lt_mentions = "\n".join([
            f"{'🌟' if is_mvp else '💀'}  <@{pid}>  →  `{'+' if pts > 0 else ''}{pts}` pts  (RANK #{old}→#{new})"
            for pid, pts, is_mvp, old, new in loser_details
        ]) or "*لا يوجد لاعبون*"

        embed = discord.Embed(
            title=f"🏆  Match Result  —  `#{lobby_id}`",
            description=(
                f"## 🎉  {wd}  Wins!\n"
                f"{separator()}\n"
                f"> 🎮  **Mode:**  `{game_mode.upper()}`\n"
                f"> 🏆  **Winner MVP:**  {f'<@{winner_mvp_id}>' if winner_mvp_id else '*N/A*'}  →  `+{WINNER_MVP_POINTS}` pts\n"
                f"> 🌟  **Loser MVP:**  {f'<@{loser_mvp_id}>' if loser_mvp_id else '*N/A*'}  →  `+{LOSER_MVP_POINTS}` pts"
            ),
            color=COLORS["success"],
            timestamp=discord.utils.utcnow()
        )
        embed.add_field(
            name=f"🏆  Winners  —  `{len(winner_details)}` players",
            value=wt_mentions,
            inline=True
        )
        embed.add_field(
            name=f"💀  Losers  —  `{len(loser_details)}` players",
            value=lt_mentions,
            inline=True
        )
        embed.add_field(
            name="📊  Points System",
            value=(
                f"> 👑  **Winner MVP:**  `+{WINNER_MVP_POINTS}` pts\n"
                f"> ✅  **Winners:**  `+{WINNER_POINTS}` pts\n"
                f"> 🌟  **Loser MVP:**  `+{LOSER_MVP_POINTS}` pts\n"
                f"> 💀  **Losers:**  `{LOSER_POINTS}` pts\n"
                f"> 📈  **Rank:**  كل `50` نقطة = `+1` رانك"
            ),
            inline=False
        )
        embed.set_author(name="Match Finished", icon_url=None)
        embed.set_footer(text=f"{BOT_FOOTER}  •  GG WP!  •  Match #{lobby_id}")
        embed = apply_branding(embed, guild)
        if channel:
            await channel.send(embed=embed)

        # تحديث الـ Leaderboard
        await update_leaderboard_channel(guild)
        # 🆕 يزامن الـ Roles لكل اللاعبين حسب ترتيبهم الجديد
        await sync_all_players_roles(guild)

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
                embed=discord.Embed(
                    title="✅  Room Info Saved",
                    description=(
                        f"> Room details stored successfully.\n"
                        f"──────────────────────\n"
                        f"🆔  **Room ID:**  `{room_id}`\n"
                        f"🔑  **Code:**  `{password or 'N/A'}`\n"
                        + (f"🔐  **Private Key:**  `{private_key}`" if private_key else "")
                    ),
                    color=COLORS["success"]
                ),
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
                await interaction.response.send_message(embed=discord.Embed(
                    title="❌  Wrong Key",
                    description=(
                        f"> The private key you entered is incorrect.\n"
                        f"> Please ask the host for the correct key."
                    ),
                    color=COLORS["error"]
                ), ephemeral=True)
        except Exception as e:
            logger.exception(f"JoinKeyModal failed: {e}")


# 🆕 Modal للبلاغ مع سبب
class ReportReasonModal(discord.ui.Modal, title="🚨  سبب البلاغ"):
    reason_input = discord.ui.TextInput(
        label="اكتب سبب البلاغ (اختياري)",
        placeholder="مثال: يستخدم هاك، يغش، يسيء، إلخ.",
        required=False,
        max_length=200
    )

    def __init__(self, lobby_id, reported_id, guild_id, reporter_id):
        super().__init__(timeout=120)
        self.lobby_id = lobby_id
        self.reported_id = reported_id
        self.guild_id = guild_id
        self.reporter_id = reporter_id

    async def on_submit(self, interaction):
        try:
            reason = str(self.reason_input.value).strip() if self.reason_input.value else None
            added, total = db.add_report(
                self.guild_id, self.reporter_id, self.reported_id,
                lobby_id=self.lobby_id, reason=reason
            )
            if not added:
                await interaction.response.send_message(
                    embed=discord.Embed(
                        title="⚠️  بلغت من قبل",
                        description=f"> لقد بلّغت على <@{self.reported_id}> سابقاً.\n> لا يمكنك البلاغ مرتين على نفس اللاعب.",
                        color=COLORS["warning"]
                    ), ephemeral=True
                )
                return
            # اعرض تأكيد البلاغ
            remaining = max(0, REPORT_THRESHOLD - total)
            report_embed = discord.Embed(
                title="🚨  تم تسجيل البلاغ",
                description=(
                    f"> 👤  **اللاعب المُبلَّغ عنه:**  <@{self.reported_id}>\n"
                    f"> 👮  **الـمُبلَّغ:**  <@{self.reporter_id}>\n"
                    + (f"> 📝  **السبب:**  {reason}\n" if reason else "")
                    + f"> 📊  **إجمالي البلاغات:**  `{total}/{REPORT_THRESHOLD}`\n"
                    + (f"> ⚠️  **يتبقى:**  `{remaining}`  بلاغ للحظر التلقائي" if remaining > 0 else f"> 🚨  **وصل للحد!**  سيتم الحظر تلقائياً")
                ),
                color=COLORS["warning"] if remaining > 0 else COLORS["error"],
                timestamp=discord.utils.utcnow()
            )
            report_embed.set_footer(text=f"{BOT_FOOTER}  •  Report #{total}")
            embed = apply_branding(embed, guild)
            await interaction.response.send_message(embed=report_embed, ephemeral=True)
            # 🆕 فحص الحظر التلقائي
            guild = bot.get_guild(self.guild_id)
            if guild:
                banned = await check_and_apply_auto_ban(guild, self.reported_id, total, self.reporter_id)
                if banned:
                    # أبلغ الأدمنز في قناة match-results (notify_admins مُفعّل داخل الدالة)
                    pass
        except Exception as e:
            logger.exception(f"ReportReasonModal failed: {e}")


# 🆕 View لاختيار اللاعب المُبلَّغ عنه (داخل الماتش)
class ReportPlayerSelectView(discord.ui.View):
    """يعرض Select باسماء لاعبي الماتش لاختيار من تريد البلاغ عليه."""
    def __init__(self, lobby_id, all_players, guild_id, reporter_id, guild=None):
        super().__init__(timeout=120)
        self.lobby_id = lobby_id
        self.guild_id = guild_id
        self.reporter_id = reporter_id
        self.guild = guild  # 🆕 لجلب أسماء اللاعبين

        # فلتر اللاعبين (احذف المُبلِّغ من القائمة)
        reportable = [pid for pid in all_players if pid != reporter_id]
        if not reportable:
            return

        # 🆕 helper لجلب اسم اللاعب
        def get_player_name(pid):
            if self.guild:
                member = self.guild.get_member(pid)
                if member:
                    return member.display_name[:80]
            player = db.get_player(pid, guild_id)
            if player and player.get("username"):
                return player["username"][:80]
            return f"Player {pid}"

        options = []
        for pid in reportable[:25]:  # حد ديسكورد 25 option
            name = get_player_name(pid)
            options.append(discord.SelectOption(
                label=name,
                value=str(pid),
                description=f"بلغ عن هذا اللاعب",
                emoji="🚨"
            ))
        if not options:
            return
        select = discord.ui.Select(
            placeholder="🚨  اختر اللاعب المُبلَّغ عنه",
            options=options,
            custom_id=f"report_select_{lobby_id}",
            min_values=1,
            max_values=1
        )
        select.callback = self.select_callback
        self.add_item(select)

    async def select_callback(self, interaction):
        if interaction.user.id != self.reporter_id:
            await interaction.response.send_message("❌ ليست قائمتك!", ephemeral=True)
            return
        reported_id = int(interaction.data["values"][0])
        # اعرض Modal لإدخال السبب
        await interaction.response.send_modal(
            ReportReasonModal(self.lobby_id, reported_id, self.guild_id, self.reporter_id)
        )


# 🆕 زر البلاغ يُضاف لكل message في الماتش
class ReportButtonView(discord.ui.View):
    """View بسيط فيه زر واحد '🚨 Report' يفتح select للاعبين."""
    def __init__(self, lobby_id, all_players, guild_id, reporter_id=None):
        super().__init__(timeout=None)
        self.lobby_id = lobby_id
        self.all_players = all_players
        self.guild_id = guild_id

    @discord.ui.button(label="🚨  إبلاغ عن لاعب", style=discord.ButtonStyle.danger, custom_id="report_player_btn")
    async def report_btn(self, interaction, button):
        # كل لاعب يقدر يبلغ — نمرّر reporter_id = interaction.user.id
        view = ReportPlayerSelectView(self.lobby_id, self.all_players, self.guild_id, interaction.user.id, guild=interaction.guild)
        if not view.children:
            await interaction.response.send_message("❌ لا يوجد لاعبون للبلاغ!", ephemeral=True)
            return
        await interaction.response.send_message(
            embed=discord.Embed(
                title="🚨  اختر اللاعب المُبلَّغ عنه",
                description=(
                    f"> اختر اللاعب الذي تريد البلاغ عنه من القائمة\n"
                    f"> ⚠️  البلاغ جدّي — لا تبلغ بدون سبب"
                ),
                color=COLORS["error"]
            ), view=view, ephemeral=True
        )


class LobbyButtonsView(discord.ui.View):
    def __init__(self, lobby_id=None, creator_id=None, guild_id=None):
        super().__init__(timeout=None)
        self.lobby_id = lobby_id
        self.creator_id = creator_id
        self.guild_id = guild_id

    # 🆕 FIX: recover lobby_id from the lobby message_id after a bot restart.
    async def _ensure_lobby_id(self, interaction):
        if not self.lobby_id and interaction.message:
            self.lobby_id = db.get_lobby_id_by_lobby_message(interaction.message.id)
        return self.lobby_id

    async def _refresh_creator_id(self, interaction):
        """Refresh creator_id from DB (handles reassignment)."""
        if not self.lobby_id:
            await self._ensure_lobby_id(interaction)
        if self.lobby_id:
            lobby = db.get_lobby(self.lobby_id)
            if lobby:
                self.creator_id = lobby["creator_id"]
                self.guild_id = lobby["guild_id"]
        return self.creator_id

    @discord.ui.button(label="Join Team 1", style=discord.ButtonStyle.danger, custom_id="join_team1_btn")
    async def join_team1_btn(self, interaction, button):
        await self._ensure_lobby_id(interaction)
        await self._handle_join(interaction, "team1")

    @discord.ui.button(label="Join Team 2", style=discord.ButtonStyle.success, custom_id="join_team2_btn")
    async def join_team2_btn(self, interaction, button):
        await self._ensure_lobby_id(interaction)
        await self._handle_join(interaction, "team2")

    @discord.ui.button(label="Leave", style=discord.ButtonStyle.secondary, custom_id="leave_lobby_btn")
    async def leave_lobby_btn(self, interaction, button):
        await self._ensure_lobby_id(interaction)
        uid = interaction.user.id
        if not self.lobby_id:
            await interaction.response.send_message("❌ Lobby not found!", ephemeral=True)
            return
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
        await self._ensure_lobby_id(interaction)
        await self._refresh_creator_id(interaction)
        uid = interaction.user.id
        if not self.lobby_id:
            await interaction.response.send_message("❌ Lobby not found!", ephemeral=True)
            return
        lobby = db.get_lobby(self.lobby_id)
        if not lobby:
            await interaction.response.send_message("❌ Lobby not found!", ephemeral=True)
            return
        # 🆕 FIX: always read creator_id from DB (handles reassignment + restart)
        creator_id = lobby["creator_id"]
        if uid != creator_id and not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(f"❌ Only the host! Host: <@{creator_id}>", ephemeral=True)
            return

        # 🆕 FIX: رد على التفاعل أولاً قبل حذف القنوات (تجنب فشل الاستجابة)
        mode = lobby.get("game_mode", DEFAULT_MODE).upper()
        await interaction.response.send_message(embed=discord.Embed(
            title="❌  Match Cancelled",
            description=(
                f"> Match `#{self.lobby_id}` — `{mode}`  was cancelled by <@{uid}>.\n"
                f"> Use `{PREFIX}play` to start a new match."
            ),
            color=COLORS["error"]
        ))

        # الآن حدّث الحالة وامسح القنوات بأمان
        db.update_lobby_status(self.lobby_id, "cancelled")
        cleanup_lobby_memory(self.lobby_id)

        # عدّل رسالة اللوبي الأصلية (في قناة play — لم تُحذف)
        try: await interaction.message.edit(embed=discord.Embed(
            title="❌  Match Cancelled",
            description=(
                f"> This `{mode}` match was cancelled by the host.\n"
                f"> Use `{PREFIX}play` to start a new match."
            ),
            color=COLORS["error"]
        ), view=None)
        except discord.HTTPException: pass

        # احذف قنوات الماتش (إن وُجدت — اللوبي قد يكون waiting بدون قنوات)
        try:
            await delete_match_channels(interaction.guild, self.lobby_id)
        except Exception as e:
            logger.warning(f"delete_match_channels (cancel_game) failed: {e}")

    async def _handle_join(self, interaction, team):
        await self._ensure_lobby_id(interaction)
        uid = interaction.user.id
        if not self.lobby_id:
            await interaction.response.send_message("❌ Lobby not found!", ephemeral=True)
            return
        lobby = db.get_lobby(self.lobby_id)
        if not lobby or lobby["status"] != "waiting":
            await interaction.response.send_message("❌ Lobby not active!", ephemeral=True)
            return

        # 🆕 فحص الحظر
        ban_info = db.is_player_banned(interaction.guild.id, uid)
        if ban_info:
            ban_embed = discord.Embed(
                title="🚫  أنت محظور من اللعب",
                description=(
                    f"> 🚨  **السبب:**  `{ban_info.get('ban_reason') or 'غير محدد'}`\n"
                    f"> 📊  **عدد البلاغات:**  `{ban_info.get('report_count', 0)}`\n"
                    f"{separator()}\n"
                    f"> 🔍  يتم توجيهك لفويس التفتيش\n"
                    f"> 💡  لفك الحظر، تواصل مع الأدمن"
                ),
                color=COLORS["error"],
                timestamp=discord.utils.utcnow()
            )
            ban_embed.set_footer(text=f"{BOT_FOOTER}  •  Banned")
            embed = apply_branding(embed, interaction.guild)
            await interaction.response.send_message(embed=ban_embed, ephemeral=True)
            # انقل لفويس التفتيش
            member_check = interaction.guild.get_member(uid)
            if member_check and member_check.voice and member_check.voice.channel:
                await move_to_banned_channels(interaction.guild, member_check)
            return

        member = interaction.guild.get_member(uid)
        if not member or not member.voice or not member.voice.channel:
            waiting_rooms = db.get_waiting_rooms(interaction.guild.id)
            available = []
            for wr_id in waiting_rooms:
                wr = interaction.guild.get_channel(wr_id)
                if wr and wr.permissions_for(member).connect:
                    available.append(wr.mention)
            rooms_text = "\n".join([f"› {r}" for r in available[:10]]) if available else "> *None available*"
            await interaction.response.send_message(embed=discord.Embed(
                title="⏳  Join a Waiting Room",
                description=(
                    f"> You must be in a voice waiting room to join a match.\n"
                    f"──────────────────────\n"
                    f"🔊  **Available Rooms:**\n{rooms_text}"
                ),
                color=COLORS["warning"]
            ), ephemeral=True)
            return
        else:
            waiting_rooms = db.get_waiting_rooms(interaction.guild.id)
            if member.voice.channel.id not in waiting_rooms:
                available = []
                for wr_id in waiting_rooms:
                    wr = interaction.guild.get_channel(wr_id)
                    if wr and wr.permissions_for(member).connect:
                        available.append(wr.mention)
                rooms_text = "\n".join([f"› {r}" for r in available[:10]]) if available else "> *None*"
                await interaction.response.send_message(embed=discord.Embed(
                    title="⏳  Wrong Voice Channel",
                    description=(
                        f"> You're in `{member.voice.channel.name}` — that's not a waiting room.\n"
                        f"──────────────────────\n"
                        f"🔊  **Available Rooms:**\n{rooms_text}"
                    ),
                    color=COLORS["warning"]
                ), ephemeral=True)
                return

        existing = db.get_player_active_lobby(uid, interaction.guild.id)
        if existing and existing["id"] != self.lobby_id:
            if existing["status"] == "started" and not existing.get("room_id"):
                await interaction.response.send_message(embed=discord.Embed(
                    title="⏳  Pending Match",
                    description=(
                        f"> You have a pending match that needs to be finished first.\n"
                        f"> Complete or cancel it before joining a new one."
                    ),
                    color=COLORS["warning"]
                ), ephemeral=True)
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
            room_embed = discord.Embed(
                title="📡  Room Info",
                description=(
                    f"> Join the room with these credentials:\n"
                    f"──────────────────────\n"
                    f"🆔  **Room ID:**  `{lobby['room_id']}`\n"
                    f"🔑  **Password:**  `{lobby.get('room_code') or 'N/A'}`\n"
                    f"──────────────────────\n"
                    f"🔥  Join now and good luck!"
                ),
                color=COLORS["auto"]
            )
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
                # 🆕 تاغ الأدمنز عند فشل إنشاء القنوات
                await notify_admins(
                    interaction.guild,
                    "Match Channels Creation Failed",
                    f"> ❌  فشل في إنشاء قنوات الماتش `#{self.lobby_id}`\n"
                    f"> 🐛  **الخطأ:**  `{str(e)[:200]}`\n"
                    f"> 💡  تحقق من صلاحيات البوت  (Manage Channels)"
                )

            if not channels:
                db.update_lobby_status(self.lobby_id, "cancelled")
                cleanup_lobby_memory(self.lobby_id)
                await interaction.channel.send(embed=discord.Embed(
                    title="❌  Failed to Start",
                    description=(
                        f"> Could not create match channels.\n"
                        f"> Lobby `#{self.lobby_id}` has been cancelled."
                    ),
                    color=COLORS["error"]
                ))
                return

            t1m = " ".join([f"<@{p}>" for p in lobby["team1_players"]])
            t2m = " ".join([f"<@{p}>" for p in lobby["team2_players"]])

            await interaction.channel.send(embed=discord.Embed(
                title="✅  Match Ready!",
                description=(
                    f"> Lobby is full — match is starting now!\n"
                    f"> Moving players to their team voice channels..."
                ),
                color=COLORS["success"],
                timestamp=discord.utils.utcnow()
            ))

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
                    room_embed = discord.Embed(
                        title="📡  Room Info",
                        description=(
                            f"> Join the room with these credentials:\n"
                            f"──────────────────────\n"
                            f"🆔  **Room ID:**  `{lobby['room_id']}`\n"
                            f"🔑  **Password:**  `{lobby.get('room_code') or 'N/A'}`\n"
                            f"──────────────────────\n"
                            f"🔥  Join now and good luck!"
                        ),
                        color=COLORS["auto"]
                    )
                    try: await channels["team1_text"].send(mentions, embed=room_embed)
                    except: pass

                start_vote_view = StartVoteView(self.lobby_id, interaction.guild.id, lobby["creator_id"])
                start_embed = discord.Embed(
                    title="🎮  Match Started!",
                    description=(
                        f"> **Lobby:**  `#{self.lobby_id}`\n"
                        f"> **Mode:**  `{mode.upper()}`  ({mode_info['team_size']}v{mode_info['team_size']})\n"
                        f"> **Host:**  <@{lobby['creator_id']}>\n"
                        f"{separator()}\n"
                        f"> 🎮  الماتش بدأ! ادخلوا الغرفة في اللعبة الآن.\n"
                        f"> 👑  **Host:**  اضغط  **Start Vote**  عند انتهاء الماتش.\n"
                        f"> ❌  **Host:**  اضغط  **Cancel Match**  للإلغاء وإعادة اللاعبين."
                    ),
                    color=COLORS["auto"],
                    timestamp=discord.utils.utcnow()
                )
                # أضف معلومات الغرفة إذا موجودة
                if lobby.get('room_id'):
                    start_embed.add_field(
                        name="📡  Room Info",
                        value=(
                            f"> 🆔  **Room ID:**  `{lobby['room_id']}`\n"
                            f"> 🔑  **Password:**  `{lobby.get('room_code') or 'N/A'}`"
                        ),
                        inline=False
                    )
                start_embed.set_author(name="Match Live", icon_url=None)
                start_embed.set_footer(text=f"{BOT_FOOTER}  •  Match #{self.lobby_id}")
                start_embed = apply_branding(start_embed, interaction.guild)
                # 🆕 FIX: store the StartVote message_id so the persistent view
                # can recover lobby_id after a bot restart.
                try:
                    sv_msg = await channels["team1_text"].send(embed=start_embed, view=start_vote_view)
                    db.set_start_vote_message(self.lobby_id, sv_msg.id)
                except: pass
                # 🆕 أرسل زر البلاغ في رسالة منفصلة
                try:
                    all_players = lobby["team1_players"] + lobby["team2_players"]
                    report_view = ReportButtonView(self.lobby_id, all_players, interaction.guild.id)
                    report_embed = discord.Embed(
                        title="🚨  نظام البلاغ",
                        description=(
                            f"> لو لاحظت لاعب يغش أو يسيء، اضغط زر  **🚨 إبلاغ**\n"
                            f"> 📊  عند وصول البلاغات إلى  `{REPORT_THRESHOLD}`  → حظر تلقائي\n"
                            f"> 🔍  اللاعب المحظور يُنقل لفويس التفتيش حتى يفك الأدمن الحظر"
                        ),
                        color=COLORS["error"],
                        timestamp=discord.utils.utcnow()
                    )
                    report_embed.set_footer(text=f"{BOT_FOOTER}  •  Match #{self.lobby_id}")
                    embed = apply_branding(embed, interaction.guild)
                    await channels["team1_text"].send(embed=report_embed, view=report_view)
                except Exception as e:
                    logger.warning(f"Failed to send report button: {e}")


class StartVoteView(discord.ui.View):
    def __init__(self, lobby_id=None, guild_id=None, creator_id=None):
        super().__init__(timeout=None)
        self.lobby_id = lobby_id
        self.guild_id = guild_id
        self.creator_id = creator_id

    # 🆕 FIX: dynamically resolve lobby_id/creator_id/guild_id from the message
    async def _resolve_context(self, interaction):
        """Resolve lobby_id, guild_id, creator_id from DB (handles restart)."""
        if not self.lobby_id and interaction.message:
            self.lobby_id = db.get_lobby_id_by_start_vote_message(interaction.message.id)
        if self.lobby_id:
            lobby = db.get_lobby(self.lobby_id)
            if lobby:
                self.creator_id = lobby["creator_id"]
                self.guild_id = lobby["guild_id"]
                return lobby
        return None

    @discord.ui.button(label="🗳️ Start Vote", style=discord.ButtonStyle.success, custom_id="start_vote_btn")
    async def start_vote_btn(self, interaction, button):
        # 🆕 FIX: dynamically resolve context (critical after bot restart)
        lobby = await self._resolve_context(interaction)
        if not lobby or not self.lobby_id:
            await interaction.response.send_message("❌ Cannot determine lobby! (restart?)", ephemeral=True)
            return
        if lobby["status"] != "started":
            await interaction.response.send_message("❌ Match not active!", ephemeral=True)
            return
        if interaction.user.id != self.creator_id:
            await interaction.response.send_message(f"❌ Only host! Host: <@{self.creator_id}>", ephemeral=True)
            return
        guild = bot.get_guild(self.guild_id)
        if not guild:
            await interaction.response.send_message("❌ Guild not found!", ephemeral=True)
            return
        # 🆕 فحص الـ cooldown 10 دقائق من بدء الماتش
        started_at = lobby.get("started_at")
        if started_at:
            try:
                from datetime import datetime, timedelta
                if isinstance(started_at, str):
                    started_time = datetime.fromisoformat(started_at)
                else:
                    started_time = started_at
                now = datetime.now(started_time.tzinfo) if started_time.tzinfo else datetime.now()
                elapsed = (now - started_time).total_seconds()
                cooldown_seconds = 600  # 10 دقائق
                if elapsed < cooldown_seconds:
                    remaining = int(cooldown_seconds - elapsed)
                    remaining_min = remaining // 60
                    remaining_sec = remaining % 60
                    await interaction.response.send_message(
                        embed=discord.Embed(
                            title="⏳  لم يحن وقت التصويت بعد",
                            description=(
                                f"> ⏱️  يجب انتظار **10 دقائق** من بدء الماتش قبل التصويت\n"
                                f"> ⏳  الوقت المتبقي:  `{remaining_min} دقيقة و {remaining_sec} ثانية`"
                            ),
                            color=COLORS["warning"]
                        ), ephemeral=True
                    )
                    return
            except Exception as e:
                logger.warning(f"Start vote cooldown check failed: {e}")
        await interaction.response.send_message("✅ Vote started!", ephemeral=True)
        for item in self.children:
            item.disabled = True
        try: await interaction.message.edit(view=self)
        except: pass
        logger.info(f"🗳️ Vote started by creator for lobby {self.lobby_id}")
        asyncio.create_task(auto_trigger_vote(self.lobby_id, guild))

    @discord.ui.button(label="❌ Cancel Match", style=discord.ButtonStyle.danger, custom_id="cancel_match_btn")
    async def cancel_match_btn(self, interaction, button):
        """🆕 Cancel Match بنظام الأغلبية — يحتاج 5 أصوات من إجمالي اللاعبين."""
        lobby = await self._resolve_context(interaction)
        if not lobby or not self.lobby_id:
            await interaction.response.send_message("❌ Cannot determine lobby! (restart?)", ephemeral=True)
            return
        uid = interaction.user.id
        if lobby["status"] not in ("started", "voting"):
            await interaction.response.send_message("❌ Match not active!", ephemeral=True)
            return

        guild = bot.get_guild(self.guild_id) or interaction.guild
        if not guild:
            await interaction.response.send_message("❌ Guild not found!", ephemeral=True)
            return

        all_players = lobby["team1_players"] + lobby["team2_players"]
        total_players = len(all_players)
        # 🆕 أغلبية = نصف اللاعبين + 1 (مثلاً 8 لاعبين → 5 أصوات)
        required_votes = (total_players // 2) + 1
        # 🆕 الأدمن يقدر يلغي مباشرة بدون تصويت
        is_admin = interaction.user.guild_permissions.administrator

        # 🆕 تهيئة قائمة المصوتين لو ما موجودة
        if not hasattr(self, '_cancel_votes'):
            self._cancel_votes = set()

        # 🆕 لو أدمن → إلغاء مباشر
        if is_admin:
            await self._execute_cancel(interaction, lobby, guild, uid, "Admin")
            return

        # 🆕 لو اللاعب صوّت قبل كذا
        if uid in self._cancel_votes:
            await interaction.response.send_message(
                f"⚠️ لقد صوّت بالفعل! ({len(self._cancel_votes)}/{required_votes})",
                ephemeral=True
            )
            return

        # 🆕 سجّل الصوت
        self._cancel_votes.add(uid)
        current_votes = len(self._cancel_votes)

        # 🆕 لو وصل للأغلبية → إلغاء
        if current_votes >= required_votes:
            await self._execute_cancel(interaction, lobby, guild, uid, f"Majority ({current_votes}/{required_votes})")
            return

        # 🆕 لو ما وصل بعد → اعرض التقدم
        remaining = required_votes - current_votes
        vote_embed = discord.Embed(
            title="🗳️ تصويت إلغاء الماتش",
            description=(
                f"> 👤 <@{uid}> صوّت لإلغاء الماتش\n"
                f"> 📊 **التقدم:** `{current_votes}/{required_votes}` أصوات\n"
                f"> ⏳ **يتبقى:** `{remaining}` أصوات للإلغاء\n"
                f"> 💡 اضغط **❌ Cancel Match** للتصويت"
            ),
            color=COLORS["warning"],
            timestamp=discord.utils.utcnow()
        )
        vote_embed.set_footer(text=f"{BOT_FOOTER}  •  Cancel Vote")
        await interaction.response.send_message(embed=vote_embed)

    async def _execute_cancel(self, interaction, lobby, guild, uid, reason):
        """🆕 ينفذ إلغاء الماتش فعلياً."""
        mode = lobby.get("game_mode", DEFAULT_MODE).upper()
        cancelled_embed = discord.Embed(
            title="❌  Match Cancelled",
            description=(
                f"> **Lobby:**  `#{self.lobby_id}`\n"
                f"> **Mode:**  `{mode}`\n"
                f"> **Cancelled by:**  <@{uid}> ({reason})\n"
                f"{separator()}\n"
                f"> 🔄  جارٍ إعادة اللاعبين لغرف الانتظار...\n"
                f"> 🗑️  جارٍ حذف قنوات الماتش...\n"
                f"> 💡  استخدم  `{PREFIX}play`  لبدء ماتش جديد."
            ),
            color=COLORS["error"],
            timestamp=discord.utils.utcnow()
        )
        cancelled_embed.set_author(name="Match Cancelled", icon_url=None)
        cancelled_embed.set_footer(text=f"{BOT_FOOTER}  •  Lobby #{self.lobby_id}")
        cancelled_embed = apply_branding(cancelled_embed, guild)
        await interaction.response.send_message(embed=cancelled_embed)

        # 1) علّم اللوبي كملغى
        db.update_lobby_status(self.lobby_id, "cancelled")
        cleanup_lobby_memory(self.lobby_id)

        # 2) أعد اللاعبين لغرف الانتظار
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

        # 3) عطّل الأزرار
        for item in self.children:
            item.disabled = True
        try: await interaction.message.edit(view=self)
        except: pass

        # 4) احذف قنوات الماتش
        try:
            await delete_match_channels(guild, self.lobby_id)
        except Exception as e:
            logger.warning(f"delete_match_channels (cancel_match) failed: {e}")

        logger.info(f"❌ Match #{self.lobby_id} cancelled via Cancel Match by {uid} ({reason})")


# 🆕 View لاختيار MVP كل فريق بعد انتهاء التصويت
class MvpSelectionView(discord.ui.View):
    """يعرض قائمة Select لاختيار MVP لكل فريق.
    الفائز يختار MVP الفريق الفائز، الخاسر يختار MVP الفريق الخاسر.
    """
    def __init__(self, lobby_id, winner_team, team1_players, team2_players, guild_id, creator_id, guild=None):
        super().__init__(timeout=180)  # 3 دقائق للاختيار
        self.lobby_id = lobby_id
        self.winner_team = winner_team
        self.guild_id = guild_id
        self.creator_id = creator_id
        self.guild = guild  # 🆕 نمرّر الـ guild لجلب أسماء اللاعبين
        self.winner_mvp_id = None
        self.loser_mvp_id = None

        winner_players = team1_players if winner_team == "team1" else team2_players
        loser_players = team2_players if winner_team == "team1" else team1_players

        # 🆕 helper لجلب اسم اللاعب من الـ guild
        def get_player_name(pid):
            if self.guild:
                member = self.guild.get_member(pid)
                if member:
                    return member.display_name[:80]  # حد ديسكورد 100 حرف للـ label
            # fallback: استخدم username من الـ DB
            player = db.get_player(pid, guild_id)
            if player and player.get("username"):
                return player["username"][:80]
            return f"Player {pid}"

        # Select للفريق الفائز — يعرض أسماء اللاعبين الفعلية
        winner_options = []
        for pid in winner_players:
            name = get_player_name(pid)
            winner_options.append(discord.SelectOption(
                label=name,
                value=str(pid),
                description=f"MVP الفريق الفائز",
                emoji="🏆"
            ))
        if winner_options:
            winner_select = discord.ui.Select(
                placeholder="🏆  اختر MVP الفريق الفائز",
                options=winner_options,
                custom_id=f"winner_mvp_select_{lobby_id}",
                min_values=1,
                max_values=1
            )
            winner_select.callback = self.winner_mvp_callback
            self.add_item(winner_select)

        # Select للفريق الخاسر — يعرض أسماء اللاعبين الفعلية
        loser_options = []
        for pid in loser_players:
            name = get_player_name(pid)
            loser_options.append(discord.SelectOption(
                label=name,
                value=str(pid),
                description=f"MVP الفريق الخاسر",
                emoji="🌟"
            ))
        if loser_options:
            loser_select = discord.ui.Select(
                placeholder="🌟  اختر MVP الفريق الخاسر",
                options=loser_options,
                custom_id=f"loser_mvp_select_{lobby_id}",
                min_values=1,
                max_values=1
            )
            loser_select.callback = self.loser_mvp_callback
            self.add_item(loser_select)

        # زر تأكيد
        confirm_btn = discord.ui.Button(
            label="✅  تأكيد وتطبيق النقاط",
            style=discord.ButtonStyle.success,
            custom_id=f"confirm_mvp_{lobby_id}"
        )
        confirm_btn.callback = self.confirm_callback
        self.add_item(confirm_btn)

    async def winner_mvp_callback(self, interaction):
        if interaction.user.id != self.creator_id and not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ فقط الهوست أو الأدمن!", ephemeral=True)
            return
        self.winner_mvp_id = int(interaction.data["values"][0])
        await interaction.response.send_message(
            f"🏆  تم اختيار MVP الفريق الفائز:  <@{self.winner_mvp_id}>", ephemeral=True
        )

    async def loser_mvp_callback(self, interaction):
        if interaction.user.id != self.creator_id and not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ فقط الهوست أو الأدمن!", ephemeral=True)
            return
        self.loser_mvp_id = int(interaction.data["values"][0])
        await interaction.response.send_message(
            f"🌟  تم اختيار MVP الفريق الخاسر:  <@{self.loser_mvp_id}>", ephemeral=True
        )

    async def confirm_callback(self, interaction):
        if interaction.user.id != self.creator_id and not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ فقط الهوست أو الأدمن!", ephemeral=True)
            return
        if not self.winner_mvp_id or not self.loser_mvp_id:
            await interaction.response.send_message(
                "❌ يجب اختيار MVP لكلا الفريقين أولاً!", ephemeral=True
            )
            return
        # عطّل الأزرار
        for item in self.children:
            item.disabled = True
        try: await interaction.message.edit(view=self)
        except: pass
        await interaction.response.send_message("✅  جارٍ تطبيق النقاط...", ephemeral=True)
        # شغّل process_match_result مع الـ MVPs المختارة
        guild = bot.get_guild(self.guild_id)
        if guild:
            from types import SimpleNamespace
            # مرّر الـ MVPs عبر globals (طريقة بسيطة)
            await process_match_result_with_mvps(
                guild, self.lobby_id, self.winner_team,
                self.winner_mvp_id, self.loser_mvp_id,
                interaction.channel
            )

    async def on_timeout(self):
        # لو ما اختاروا في الوقت، استخدم MVP تلقائي
        lobby = db.get_lobby(self.lobby_id)
        if not lobby or lobby["status"] != "voting":
            return
        guild = bot.get_guild(lobby["guild_id"])
        if not guild:
            return
        # اختيار تلقائي
        wt = lobby["team1_players"] if self.winner_team == "team1" else lobby["team2_players"]
        lt = lobby["team2_players"] if self.winner_team == "team1" else lobby["team1_players"]
        auto_winner_mvp = get_mvp_player(wt, guild, db, guild.id)
        auto_loser_mvp = get_mvp_player(lt, guild, db, guild.id)
        # 🆕 تاغ الأدمنز
        await notify_admins(
            guild,
            "MVP Selection Timeout",
            f"> ⏰  انتهى وقت اختيار MVP للماتش `#{self.lobby_id}`\n"
            f"> 🤖  تم اختيار MVP تلقائياً:\n"
            f"> ─  🏆  الفائز:  {f'<@{auto_winner_mvp}>' if auto_winner_mvp else '*N/A*'}\n"
            f"> ─  🌟  الخاسر:  {f'<@{auto_loser_mvp}>' if auto_loser_mvp else '*N/A*'}\n"
            f"> 💡  يمكنك تعديل النقاط يدوياً بأمر  `!!setlevel`",
            color=COLORS["warning"]
        )
        mc = db.get_match_channels(self.lobby_id)
        result_ch = guild.get_channel(mc["team1_text_id"]) if mc else guild.get_channel(lobby["channel_id"])
        await process_match_result_with_mvps(
            guild, self.lobby_id, self.winner_team,
            auto_winner_mvp, auto_loser_mvp,
            result_ch
        )


async def process_match_result_with_mvps(guild, lobby_id, winner_team, winner_mvp_id, loser_mvp_id, channel=None):
    """🆕 يطبق نظام النقاط الجديد مع MVPs محددة يدوياً."""
    try:
        logger.info(f"🏆 process_match_result_with_mvps — lobby={lobby_id}, winner={winner_team}, w_mvp={winner_mvp_id}, l_mvp={loser_mvp_id}")
        lobby = db.get_lobby(lobby_id)
        if not lobby:
            return
        if lobby["status"] == "completed":
            logger.warning(f"Already completed: {lobby_id}")
            return

        db.update_lobby_status(lobby_id, "completed")

        game_mode = lobby.get("game_mode", DEFAULT_MODE)
        wt = lobby["team1_players"] if winner_team == "team1" else lobby["team2_players"]
        lt = lobby["team2_players"] if winner_team == "team1" else lobby["team1_players"]

        # 🆕 نقاط النظام الجديد
        WINNER_MVP_POINTS = 80
        WINNER_POINTS = 30
        LOSER_MVP_POINTS = 30
        LOSER_POINTS = -30

        # معالجة الفريق الفائز
        winner_details = []
        for pid in wt:
            p = db.get_player(pid, guild.id)
            if not p:
                continue
            is_mvp = (pid == winner_mvp_id)
            pts = WINNER_MVP_POINTS if is_mvp else WINNER_POINTS
            old_level = p.get("level", STARTING_LEVEL)
            new_win_streak = p.get("win_streak", 0) + 1
            new_max = max(p.get("max_win_streak", 0), new_win_streak)
            db.add_points(pid, guild.id, pts)
            db.update_player_stats(
                pid, guild.id,
                wins=p["wins"] + 1,
                matches_played=p["matches_played"] + 1,
                win_streak=new_win_streak,
                lose_streak=0,
                max_win_streak=new_max,
                mvps=p["mvps"] + (1 if is_mvp else 0)
            )
            new_p = db.get_player(pid, guild.id)
            new_level = new_p.get("level", STARTING_LEVEL) if new_p else old_level
            m = guild.get_member(pid)
            if m:
                await update_member_nickname(m, new_level)
            winner_details.append((pid, pts, is_mvp, old_level, new_level))

        # معالجة الفريق الخاسر
        loser_details = []
        for pid in lt:
            p = db.get_player(pid, guild.id)
            if not p:
                continue
            is_mvp = (pid == loser_mvp_id)
            pts = LOSER_MVP_POINTS if is_mvp else LOSER_POINTS
            old_level = p.get("level", STARTING_LEVEL)
            new_lose_streak = p.get("lose_streak", 0) + 1
            db.add_points(pid, guild.id, pts)
            db.update_player_stats(
                pid, guild.id,
                losses=p["losses"] + 1,
                matches_played=p["matches_played"] + 1,
                win_streak=0,
                lose_streak=new_lose_streak,
                mvps=p["mvps"] + (1 if is_mvp else 0)
            )
            new_p = db.get_player(pid, guild.id)
            new_level = new_p.get("level", STARTING_LEVEL) if new_p else old_level
            m = guild.get_member(pid)
            if m:
                await update_member_nickname(m, new_level)
            loser_details.append((pid, pts, is_mvp, old_level, new_level))

        # حفظ نتيجة الماتش
        db.create_match_result(lobby_id, winner_team, len(wt), len(lt), mvp=winner_mvp_id)

        # بناء رسالة النتيجة
        wd = "🔴  Team 1" if winner_team == "team1" else "🟢  Team 2"
        wt_mentions = "\n".join([
            f"{'👑' if is_mvp else '✅'}  <@{pid}>  →  `{'+' if pts > 0 else ''}{pts}` pts  (RANK #{old}→#{new})"
            for pid, pts, is_mvp, old, new in winner_details
        ]) or "*لا يوجد لاعبون*"
        lt_mentions = "\n".join([
            f"{'🌟' if is_mvp else '💀'}  <@{pid}>  →  `{'+' if pts > 0 else ''}{pts}` pts  (RANK #{old}→#{new})"
            for pid, pts, is_mvp, old, new in loser_details
        ]) or "*لا يوجد لاعبون*"

        embed = discord.Embed(
            title=f"🏆  Match Result  —  `#{lobby_id}`",
            description=(
                f"## 🎉  {wd}  Wins!\n"
                f"{separator()}\n"
                f"> 🎮  **Mode:**  `{game_mode.upper()}`\n"
                f"> 🏆  **Winner MVP:**  {f'<@{winner_mvp_id}>' if winner_mvp_id else '*N/A*'}  →  `+{WINNER_MVP_POINTS}` pts\n"
                f"> 🌟  **Loser MVP:**  {f'<@{loser_mvp_id}>' if loser_mvp_id else '*N/A*'}  →  `+{LOSER_MVP_POINTS}` pts"
            ),
            color=COLORS["success"],
            timestamp=discord.utils.utcnow()
        )
        embed.add_field(
            name=f"🏆  Winners  —  `{len(winner_details)}` players",
            value=wt_mentions,
            inline=True
        )
        embed.add_field(
            name=f"💀  Losers  —  `{len(loser_details)}` players",
            value=lt_mentions,
            inline=True
        )
        embed.add_field(
            name="📊  Points System",
            value=(
                f"> 👑  **Winner MVP:**  `+{WINNER_MVP_POINTS}` pts\n"
                f"> ✅  **Winners:**  `+{WINNER_POINTS}` pts\n"
                f"> 🌟  **Loser MVP:**  `+{LOSER_MVP_POINTS}` pts\n"
                f"> 💀  **Losers:**  `{LOSER_POINTS}` pts\n"
                f"> 📈  **Rank:**  كل `50` نقطة = `+1` رانك"
            ),
            inline=False
        )
        embed.set_author(name="Match Finished", icon_url=None)
        embed.set_footer(text=f"{BOT_FOOTER}  •  GG WP!  •  Match #{lobby_id}")
        embed = apply_branding(embed, guild)
        if channel:
            await channel.send(embed=embed)

        await update_leaderboard_channel(guild)
        # 🆕 يزامن الـ Roles لكل اللاعبين حسب ترتيبهم الجديد
        await sync_all_players_roles(guild)

        # أعد اللاعبين لغرف الانتظار
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
        logger.exception(f"process_match_result_with_mvps failed: {e}")
        # 🆕 تاغ الأدمنز عند الفشل
        await notify_admins(
            guild,
            "Match Result Processing Failed",
            f"> ❌  فشل في معالجة نتيجة الماتش `#{lobby_id}`\n"
            f"> 🐛  **الخطأ:**  `{str(e)[:200]}`\n"
            f"> 💡  تحقق من الـ logs وحاول حل المشكلة يدوياً"
        )


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
            # 🆕 حالة 0-0 (لا أصوات إطلاقاً) — تاغ الأدمنز للحل
            if result_ch:
                no_votes_embed = discord.Embed(
                    title="⏰  Vote Ended — No Votes!",
                    description=(
                        f"> 🚨  لم يصوت أي لاعب في الماتش  `#{self.lobby_id}`\n"
                        f"> 📊  **النتيجة:**  `0 — 0`\n"
                        f"> ⚖️  الأدمن يجب أن يحل الماتش يدوياً:\n"
                        f"> `{PREFIX}resolve {self.lobby_id} team1`\n"
                        f"> `{PREFIX}resolve {self.lobby_id} team2`\n"
                        f"> 💡  أو استخدم  `{PREFIX}resolve {self.lobby_id} team1`  لفوز Team 1"
                    ),
                    color=COLORS["warning"],
                    timestamp=discord.utils.utcnow()
                )
                no_votes_embed.set_footer(text=f"{BOT_FOOTER}  •  Action required")
                embed = apply_branding(embed, guild)
                await result_ch.send(embed=no_votes_embed)
            # 🆕 تاغ الأدمنز
            await notify_admins(
                guild,
                "🚨  Vote Ended with 0-0",
                f"> ⚠️  الماتش  `#{self.lobby_id}`  انتهى بدون أي أصوات\n"
                f"> 📊  **النتيجة:**  `0 — 0`\n"
                f"> ⚖️  يجب حل الماتش يدوياً:\n"
                f"> `{PREFIX}resolve {self.lobby_id} team1|team2`",
                color=COLORS["warning"]
            )
            return

        t1v = sum(1 for v in votes if v["vote"] == "team1")
        t2v = sum(1 for v in votes if v["vote"] == "team2")
        if t1v > t2v:
            winner = "team1"
        elif t2v > t1v:
            winner = "team2"
        else:
            # 🆕 حالة التعادل (مع أصوات) — تاغ الأدمنز
            if result_ch:
                tie_embed = discord.Embed(
                    title="⏰  Vote Tied!",
                    description=(
                        f"> 🤝  الماتش  `#{self.lobby_id}`  انتهى بالتعادل\n"
                        f"> 📊  **النتيجة:**  `{t1v} — {t2v}`\n"
                        f"> ⚖️  الأدمن يجب أن يحل الماتش:\n"
                        f"> `{PREFIX}resolve {self.lobby_id} team1`\n"
                        f"> `{PREFIX}resolve {self.lobby_id} team2`"
                    ),
                    color=COLORS["warning"],
                    timestamp=discord.utils.utcnow()
                )
                tie_embed.set_footer(text=f"{BOT_FOOTER}  •  Action required")
                embed = apply_branding(embed, guild)
                await result_ch.send(embed=tie_embed)
            await notify_admins(
                guild,
                "🤝  Vote Tied",
                f"> 🤝  الماتش  `#{self.lobby_id}`  انتهى بالتعادل\n"
                f"> 📊  **النتيجة:**  `{t1v} — {t2v}`\n"
                f"> ⚖️  يجب حل الماتش يدوياً:\n"
                f"> `{PREFIX}resolve {self.lobby_id} team1|team2`",
                color=COLORS["warning"]
            )
            return

        wd = "🔴  Team 1" if winner == "team1" else "🟢  Team 2"
        if result_ch:
            vote_close_embed = discord.Embed(
                title="⏰  Vote Closed!",
                description=(
                    f"> **{wd}**  wins the vote  `{t1v} — {t2v}`\n"
                    f"> 🎯  اختر MVP لكل فريق الآن..."
                ),
                color=COLORS["success"],
                timestamp=discord.utils.utcnow()
            )
            vote_close_embed.set_footer(text=f"{BOT_FOOTER}  •  MVP selection required")
            embed = apply_branding(embed, guild)
            await result_ch.send(embed=vote_close_embed)
        # 🆕 اعرض MvpSelectionView بدل استدعاء process_match_result مباشرة
        lobby_data = db.get_lobby(self.lobby_id)
        if lobby_data and result_ch:
            mvp_view = MvpSelectionView(
                self.lobby_id, winner,
                lobby_data["team1_players"], lobby_data["team2_players"],
                lobby_data["guild_id"], lobby_data["creator_id"],
                guild=guild  # 🆕 مرّر الـ guild لجلب أسماء اللاعبين
            )
            mvp_embed = discord.Embed(
                title="👑  اختر MVP كل فريق",
                description=(
                    f"> 🏆  **الفريق الفائز:**  {wd}\n"
                    f"> 👑  الهوست أو الأدمن يختار MVP لكل فريق\n"
                    f"> ⏱️  لديك **3 دقائق** — وإلا سيُختار تلقائياً\n"
                    f"{separator()}\n"
                    f"> 💡  **تعليمات:**\n"
                    f"> ─  استخدم القائمة الأولى لاختيار MVP الفريق الفائز  (`+80` pts)\n"
                    f"> ─  استخدم القائمة الثانية لاختيار MVP الفريق الخاسر  (`+30` pts)\n"
                    f"> ─  اضغط **تأكيد** لتطبيق النقاط"
                ),
                color=COLORS["vote"],
                timestamp=discord.utils.utcnow()
            )
            mvp_embed.set_author(name="MVP Selection", icon_url=None)
            mvp_embed.set_footer(text=f"{BOT_FOOTER}  •  Match #{self.lobby_id}")
            embed = apply_branding(embed, guild)
            await result_ch.send(embed=mvp_embed, view=mvp_view)
        else:
            # fallback: استخدم process_match_result القديم
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
        await interaction.channel.send(embed=discord.Embed(
            description=(
                f"> 🗳️  **Vote Progress:**  🟠 `{t1v}`  —  🟢 `{t2v}`\n"
                f"> Cast: `{votes_count}/{total_voters}`"
            ),
            color=COLORS["vote"]
        ))

        if votes_count >= total_voters:
            if lobby_id in vote_timeout_timers:
                vote_timeout_timers[lobby_id].cancel()
            if t1v > t2v:
                winner = "team1"
            elif t2v > t1v:
                winner = "team2"
            else:
                tie_embed = discord.Embed(
                    title="⏰  Vote Tied!",
                    description=(
                        f"> 🤝  الماتش  `#{lobby_id}`  انتهى بالتعادل\n"
                        f"> 📊  **النتيجة:**  `{t1v} — {t2v}`\n"
                        f"> ⚖️  الأدمن يجب أن يحل الماتش:\n"
                        f"> `{PREFIX}resolve {lobby_id} team1`\n"
                        f"> `{PREFIX}resolve {lobby_id} team2`"
                    ),
                    color=COLORS["warning"],
                    timestamp=discord.utils.utcnow()
                )
                tie_embed.set_footer(text=f"{BOT_FOOTER}  •  Action required")
                embed = apply_branding(embed, guild)
                await interaction.channel.send(embed=tie_embed)
                # 🆕 تاغ الأدمنز
                await notify_admins(
                    interaction.guild,
                    "🤝  Vote Tied",
                    f"> 🤝  الماتش  `#{lobby_id}`  انتهى بالتعادل\n"
                    f"> 📊  **النتيجة:**  `{t1v} — {t2v}`\n"
                    f"> ⚖️  يجب حل الماتش يدوياً:\n"
                    f"> `{PREFIX}resolve {lobby_id} team1|team2`",
                    color=COLORS["warning"]
                )
                return

            wd = "🟠 Team 1" if winner == "team1" else "🟢 Team 2"
            vote_complete_embed = discord.Embed(
                title="✅  Vote Complete!",
                description=(
                    f"> All participants voted!\n"
                    f"> Winner: **{wd}**  `{t1v} — {t2v}`  🎉\n"
                    f"> 🎯  اختر MVP لكل فريق الآن..."
                ),
                color=COLORS["success"],
                timestamp=discord.utils.utcnow()
            )
            vote_complete_embed.set_footer(text=f"{BOT_FOOTER}  •  MVP selection required")
            embed = apply_branding(embed, interaction.guild)
            await interaction.channel.send(embed=vote_complete_embed)
            mc = db.get_match_channels(lobby_id)
            result_ch = interaction.guild.get_channel(mc["team1_text_id"]) if mc else interaction.channel
            # 🆕 اعرض MvpSelectionView بدل استدعاء process_match_result مباشرة
            lobby_data = db.get_lobby(lobby_id)
            if lobby_data and result_ch:
                mvp_view = MvpSelectionView(
                    lobby_id, winner,
                    lobby_data["team1_players"], lobby_data["team2_players"],
                    lobby_data["guild_id"], lobby_data["creator_id"],
                    guild=interaction.guild  # 🆕 مرّر الـ guild لجلب أسماء اللاعبين
                )
                mvp_embed = discord.Embed(
                    title="👑  اختر MVP كل فريق",
                    description=(
                        f"> 🏆  **الفريق الفائز:**  {wd}\n"
                        f"> 👑  الهوست أو الأدمن يختار MVP لكل فريق\n"
                        f"> ⏱️  لديك **3 دقائق** — وإلا سيُختار تلقائياً\n"
                        f"{separator()}\n"
                        f"> 💡  **تعليمات:**\n"
                        f"> ─  استخدم القائمة الأولى لاختيار MVP الفريق الفائز  (`+80` pts)\n"
                        f"> ─  استخدم القائمة الثانية لاختيار MVP الفريق الخاسر  (`+30` pts)\n"
                        f"> ─  اضغط **تأكيد** لتطبيق النقاط"
                    ),
                    color=COLORS["vote"],
                    timestamp=discord.utils.utcnow()
                )
                mvp_embed.set_author(name="MVP Selection", icon_url=None)
                mvp_embed.set_footer(text=f"{BOT_FOOTER}  •  Match #{lobby_id}")
                embed = apply_branding(embed, interaction.guild)
                await result_ch.send(embed=mvp_embed, view=mvp_view)
            else:
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
                embed=discord.Embed(
                    title="✅  Lobby Created!",
                    description=(
                        f"> Lobby `#{lid}` is now live!\n"
                        f"> Players can press **Join Team 1 / 2** to enter.\n"
                        + (f"> 🔐  **Private Key** required to join." if private_key else "")
                    ),
                    color=COLORS["success"]
                ),
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

# 🆕 فحص الـ roles العالية للأعضاء — يستخدم لأمر play1v1
# يسمح للعضو بالاستخدام إذا تحقق أحد الشروط التالية:
#   1) عنده صلاحية Administrator في السيرفر
#   2) عنده صلاحية Manage Guild (إدارة السيرفر)
#   3) أعلى role تبع العضو في النصف العلوي من هرم الـ roles في السيرفر
def is_high_role_member(member):
    """يفحص إذا كان العضو يملك role عالي في السيرفر."""
    # 1) Admin permission = full access
    if member.guild_permissions.administrator:
        return True
    # 2) Manage Guild permission
    if member.guild_permissions.manage_guild:
        return True
    # 3) أعلى role في النصف العلوي من الهرم
    # نجمع الـ roles الـ hoisted (الظاهرة في قائمة الأعضاء)
    guild_roles = [r for r in member.guild.roles if r.hoist and r != member.guild.default_role]
    if not guild_roles:
        return False
    max_position = max(r.position for r in guild_roles)
    # النصف العلوي = position >= max_position / 2
    threshold = max(1, max_position // 2)
    member_top_position = member.top_role.position if member.top_role else 0
    return member_top_position >= threshold

def is_high_role_check(ctx):
    """Wrapper for use as @commands.check() decorator."""
    return is_high_role_member(ctx.author)


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send(embed=discord.Embed(
            title="⏳  Cooldown",
            description=(
                f"> Please wait  `{error.retry_after:.1f}s`  before using this command again."
            ),
            color=COLORS["warning"]
        ))
    elif isinstance(error, commands.CheckFailure):
        await ctx.send(embed=discord.Embed(
            title="❌  No Permission",
            description=(
                f"> You don't have permission to use this command."
            ),
            color=COLORS["error"]
        ))
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
    # 🆕 FIX: register persistent views with NO lobby_id — they will
    # dynamically resolve lobby_id from the message_id at click time.
    bot.add_view(VoteView())
    bot.add_view(RematchView())
    bot.add_view(LobbyButtonsView())
    bot.add_view(StartVoteView())
    bot.add_view(CreateLobbyView(None, DEFAULT_MODE))
    # 🆕 MvpSelectionView مع timeout (لن يُسجّل كـ persistent)
    # لأنه يُنشأ ديناميكياً بعد كل تصويت
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=f"Free Fire | {PREFIX}play"))
    # 🆕 Auto-setup: فحص كل سيرفر وإصلاح الناقص تلقائياً
    logger.info("🔄 Auto-setup: checking all guilds...")
    for guild in bot.guilds:
        try:
            await auto_setup_guild(guild)
        except Exception as e:
            logger.warning(f"Auto-setup failed for {guild.name}: {e}")
    logger.info("✅ Auto-setup complete!")


async def auto_setup_guild(guild):
    """🆕 يفحص السيرفر وينشئ أي شيء ناقص بدون حذف الموجود.
    - ينشئ الكاتيجوريات لو غير موجودة
    - ينشئ القنوات النصية والصوتية لو غير موجودة
    - ينشئ قناة Rules لو غير موجودة
    - ينشئ Rank Roles لو غير موجودة
    - ينشئ نظام JAIL لو غير موجود
    - يسجّل القنوات في الـ DB
    """
    # 1) كاتيجوري النصي
    text_cat = discord.utils.get(guild.categories, name="🎮 FREE FIRE — TEXT")
    if not text_cat:
        text_cat = await guild.create_category("🎮 FREE FIRE — TEXT", overwrites={
            guild.default_role: discord.PermissionOverwrite(read_messages=True),
            guild.me: discord.PermissionOverwrite(manage_channels=True, manage_messages=True)
        })
        logger.info(f"  [{guild.name}] Created TEXT category")

    # 2) كاتيجوري الصوتي
    voice_cat = discord.utils.get(guild.categories, name="🎮 FREE FIRE — VOICE")
    if not voice_cat:
        voice_cat = await guild.create_category("🎮 FREE FIRE — VOICE", overwrites={
            guild.default_role: discord.PermissionOverwrite(read_messages=True),
            guild.me: discord.PermissionOverwrite(manage_channels=True, manage_messages=True)
        })
        logger.info(f"  [{guild.name}] Created VOICE category")

    # 3) قناة Rules
    rules_name = "📜・rules"
    if not discord.utils.get(guild.text_channels, name=rules_name):
        rules_overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=True, send_messages=False, add_reactions=False),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_messages=True)
        }
        rules_ch = await guild.create_text_channel(rules_name, category=text_cat, topic="Rules", overwrites=rules_overwrites, position=0)
        try:
            rules_embed = discord.Embed(
                title="📜  قواعد السيرفر",
                description=(
                    f"> مرحباً بك في  **{guild.name}**  🔥\n"
                    f"> يرجى الالتزام بالقواعد التالية:\n"
                    f"{separator()}\n"
                    f"> **1️⃣  الاحترام المتبادل**\n"
                    f"> ─  احترم جميع اللاعبين والأدمنز.\n"
                    f"> ─  ممنوع السب، الشتم، أو الإساءة.\n\n"
                    f"> **2️⃣  قواعد اللعب**\n"
                    f"> ─  ادخل غرفة انتظار قبل اللعب.\n"
                    f"> ─  استخدم  `{PREFIX}play 4v4`  لبدء ماتش.\n"
                    f"> ─  التزم بنتيجة التصويت.\n\n"
                    f"> **3️⃣  عدم الغش**\n"
                    f"> ─  ممنوع التلاعب بالتصويت.\n"
                    f"> ─  ممنوع مغادرة الماتش في المنتصف.\n\n"
                    f"> **4️⃣  استخدام الأوامر**\n"
                    f"> ─  الأوامر تعمل فقط في قنوات play.\n"
                    f"> ─  انتظر الـ cooldown قبل التكرار.\n\n"
                    f"> **5️⃣  العقوبات**\n"
                    f"> ─  مخالفة القواعد = تحذير / كتم / طرد.\n"
                    f"> ─  القرار النهائي للأدمن.\n\n"
                    f"> 💬  لأي استفسار، تواصل مع الأدمن."
                ),
                color=COLORS["warning"],
                timestamp=discord.utils.utcnow()
            )
            rules_embed.set_author(name="Server Rules")
            rules_embed.set_footer(text=f"{BOT_FOOTER}  •  Read carefully")
            if RULES_IMAGE_URL:
                rules_embed.set_image(url=RULES_IMAGE_URL)
            elif guild.icon:
                rules_embed.set_image(url=guild.icon.url)
            await rules_ch.send(embed=rules_embed)
        except:
            pass
        logger.info(f"  [{guild.name}] Created rules channel")

    # 4) القنوات النصية
    for ch_name, topic in [("🎮・apostada-play", "Play"), ("🎮・highlight-play", "Play"), ("🎮・zelika-play", "Play"), ("📊・match-results", "Results"), ("🏆・leaderboard", "Leaderboard"), ("👤・profiles", "Profiles")]:
        if not discord.utils.get(guild.text_channels, name=ch_name):
            ch = await guild.create_text_channel(ch_name, category=text_cat, topic=topic)
            db.add_commands_channel(guild.id, ch.id)
            db.add_play_channel(guild.id, ch.id)
            if "leaderboard" in ch_name:
                db.set_guild_setting(guild.id, "leaderboard_channel_id", ch.id)
            logger.info(f"  [{guild.name}] Created {ch_name}")

    # 5) القنوات الصوتية
    for ch_name in ["⏳・Waiting 1", "⏳・Waiting 2", "⏳・Waiting 3", "⏳・Waiting 4", "⏳・Waiting 5", "🔒・Waiting Prv 1", "🔒・Waiting Prv 2", "🔒・Waiting Prv 3", "🔒・Waiting Staff"]:
        if not discord.utils.get(guild.voice_channels, name=ch_name):
            overwrites = {guild.me: discord.PermissionOverwrite(connect=True, manage_channels=True)}
            if "Prv" in ch_name or "Staff" in ch_name:
                overwrites[guild.default_role] = discord.PermissionOverwrite(connect=False)
            ch = await guild.create_voice_channel(ch_name, category=voice_cat, overwrites=overwrites)
            db.add_waiting_room(guild.id, ch.id)
            logger.info(f"  [{guild.name}] Created {ch_name}")

    # 6) Rank Roles
    try:
        await setup_rank_roles_permissions(guild)
    except Exception as e:
        logger.warning(f"  [{guild.name}] Rank roles setup failed: {e}")

    # 7) JAIL system
    try:
        await setup_jail_system(guild)
    except Exception as e:
        logger.warning(f"  [{guild.name}] JAIL setup failed: {e}")

    # 8) حدّث الـ Leaderboard
    try:
        await update_leaderboard_channel(guild)
    except:
        pass

    # 9) 🆕 أصلح رانك كل اللاعبين (تأكد إن اللي نقاطهم 0 = RANK 1000)
    try:
        db.recalculate_ranks(guild.id)
    except:
        pass

    logger.info(f"  [{guild.name}] Auto-setup complete ✅")


@bot.event
async def on_guild_join(guild):
    logger.info(f"🏠 Added to: {guild.name}  (ID: {guild.id})  —  Members: {guild.member_count}")


@bot.event
async def on_member_join(member):
    if member.bot:
        return
    await asyncio.sleep(2)
    player = db.get_or_create_player(member.id, member.guild.id, member.display_name)
    await update_member_nickname(member, player.get("level", STARTING_LEVEL))


# 🆕 منع المحظورين من مغادرة فويس التفتيش
@bot.event
async def on_voice_state_update(member, before, after):
    """🆕 يمنع المحظورين (ban) والمسجونين (JAIL) من مغادرة القنوات المخصصة."""
    if member.bot:
        return

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 1) فحص المحظورين (BAN system)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    ban_info = db.is_player_banned(member.guild.id, member.id)
    if ban_info:
        assigned_voice_id = ban_info.get("assigned_voice_id")
        # الحالة 1: اللاعب دخل فويس جديد
        if after.channel is not None:
            if not assigned_voice_id or after.channel.id != assigned_voice_id:
                assigned_ch = member.guild.get_channel(assigned_voice_id) if assigned_voice_id else None
                if assigned_ch and isinstance(assigned_ch, discord.VoiceChannel):
                    try:
                        await member.move_to(assigned_ch)
                        logger.info(f"🔒 Banned {member.id} tried #{after.channel.name} → back to investigation")
                        return
                    except (discord.HTTPException, discord.Forbidden):
                        pass
                new_ch = await move_to_banned_channels(member.guild, member, assign_permanent=True)
                if new_ch:
                    logger.info(f"🔒 Banned {member.id} → new investigation voice")
                    return
        # الحالة 2: اللاعب غادر فويس
        elif before.channel is not None and after.channel is None:
            assigned_ch = member.guild.get_channel(assigned_voice_id) if assigned_voice_id else None
            if assigned_ch and isinstance(assigned_ch, discord.VoiceChannel):
                try:
                    await member.move_to(assigned_ch)
                    logger.info(f"🔒 Banned {member.id} tried to leave → back to investigation")
                    return
                except (discord.HTTPException, discord.Forbidden):
                    pass
            new_ch = await move_to_banned_channels(member.guild, member, assign_permanent=True)
            if new_ch:
                logger.info(f"🔒 Banned {member.id} → investigation after leaving")
        return  # المحظور تم التعامل معه

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 2) 🆕 فحص المسجونين (JAIL system)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    jail_role = discord.utils.get(member.guild.roles, name=JAIL_ROLE_NAME)
    if not jail_role or jail_role not in member.roles:
        return  # ليس مسجوناً

    # اللاعب مسجون — يجب أن يبقى في فويس السجن الخاص به فقط
    jail_voice_name = f"🔒 Jail-{member.id}"
    jail_voice = discord.utils.get(member.guild.voice_channels, name=jail_voice_name)

    # الحالة 1: اللاعب دخل فويس
    if after.channel is not None:
        # لو الفويس اللي دخله ليس فويسه الخاص → ارده
        if after.channel.name != jail_voice_name:
            if jail_voice:
                try:
                    await member.move_to(jail_voice)
                    logger.info(f"🔒 JAIL {member.id} tried #{after.channel.name} → back to jail voice")
                    return
                except (discord.HTTPException, discord.Forbidden):
                    pass
            # لو فويسه غير موجود، اطرده
            try:
                await member.move_to(None)
                logger.info(f"🔒 JAIL {member.id} tried #{after.channel.name} → disconnected (no jail voice)")
            except (discord.HTTPException, discord.Forbidden):
                pass
    # الحالة 2: اللاعب غادر فويس (حاول يطلع)
    elif before.channel is not None and after.channel is None:
        # المسجون لا يمكنه مغادرة فويسه — ارد فوراً
        if jail_voice:
            try:
                await member.move_to(jail_voice)
                logger.info(f"🔒 JAIL {member.id} tried to leave → back to jail voice")
                return
            except (discord.HTTPException, discord.Forbidden):
                pass


@bot.event
async def on_message(message):
    if message.author.bot:
        return
    if isinstance(message.channel, discord.DMChannel):
        await bot.process_commands(message)
        return
    if not message.guild:
        return

    # 🆕 فحص المسجونين (JAIL) — منع الكتابة في غير شاتات السجن
    jail_role = discord.utils.get(message.guild.roles, name=JAIL_ROLE_NAME)
    if jail_role and message.author.id != message.guild.owner_id:
        member = message.guild.get_member(message.author.id)
        if member and jail_role in member.roles:
            # المسجون يقدر يكتب فقط في jail-chat و jail-prouves
            allowed_jail_channels = [JAIL_CHAT_NAME, JAIL_PROUVES_NAME]
            if message.channel.name not in allowed_jail_channels:
                # احذف الرسالة لو البوت يقدر
                try:
                    await message.delete()
                except (discord.HTTPException, discord.Forbidden):
                    pass
                return  # لا يعالج أوامر

    if not db.is_bot_allowed_channel(message.guild.id, message.channel.id):
        is_admin = False
        member = message.guild.get_member(message.author.id)
        if member and member.guild_permissions.administrator:
            is_admin = True
        content_stripped = message.content.strip()
        command_name = content_stripped.split()[0] if content_stripped.split() else ""
        allowed_anywhere = [f"{PREFIX}general", f"{PREFIX}help", f"{PREFIX}fixrank", f"{PREFIX}myrank", f"{PREFIX}mylevel", f"{PREFIX}p", f"{PREFIX}setup", f"{PREFIX}botinfo", f"{PREFIX}cleanup", f"{PREFIX}fixrankall", f"{PREFIX}setcommandschannel", f"{PREFIX}card", f"{PREFIX}scan", f"{PREFIX}deletecat", f"{PREFIX}delcat", f"{PREFIX}confirmcat", f"{PREFIX}rules", f"{PREFIX}points"]
        is_allowed = command_name in allowed_anywhere
        if content_stripped.startswith(PREFIX):
            if is_admin or is_allowed:
                await bot.process_commands(message)
                return
            try:
                await message.reply(embed=discord.Embed(
                    title="❌  Not Allowed Here",
                    description=(
                        f"> Commands can only be used in play channels.\n"
                        f"> Allowed:  `apostada-play`  •  `highlight-play`  •  `zelika-play`\n"
                        f"> 💡  Use  `{PREFIX}general`  for help."
                    ),
                    color=COLORS["error"]
                ), delete_after=10)
            except: pass
        return
    await bot.process_commands(message)

# ============================================================
# PLAYER COMMANDS
# ============================================================

async def create_mode_lobby(ctx, mode):
    guild = ctx.guild
    user = ctx.author
    member = guild.get_member(user.id)
    # 🆕 فحص الحظر أولاً
    ban_info = db.is_player_banned(guild.id, user.id)
    if ban_info:
        ban_embed = discord.Embed(
            title="🚫  أنت محظور من اللعب",
            description=(
                f"> 🚨  **السبب:**  `{ban_info.get('ban_reason') or 'غير محدد'}`\n"
                f"> 📊  **عدد البلاغات:**  `{ban_info.get('report_count', 0)}`\n"
                f"> 📅  **تاريخ الحظر:**  `{ban_info.get('banned_at', 'N/A')[:19]}`\n"
                f"{separator()}\n"
                f"> 🔍  يتم توجيهك لفويس التفتيش\n"
                f"> 💡  لفك الحظر، تواصل مع الأدمن"
            ),
            color=COLORS["error"],
            timestamp=discord.utils.utcnow()
        )
        ban_embed.set_footer(text=f"{BOT_FOOTER}  •  Banned")
        embed = apply_branding(embed, ctx.guild)
        await ctx.send(embed=ban_embed, delete_after=20)
        # انقل لفويس التفتيش لو في فويس
        if member and member.voice and member.voice.channel:
            await move_to_banned_channels(guild, member)
        return
    if not db.is_bot_allowed_channel(guild.id, ctx.channel.id):
        await ctx.send(embed=discord.Embed(
            title="❌  Not Allowed Here",
            description=(
                f"> This command can only be used in play channels.\n"
                f"> Allowed:  `apostada-play`  •  `highlight-play`  •  `zelika-play`"
            ),
            color=COLORS["error"]
        ), delete_after=15)
        return
    if not member or not member.voice or not member.voice.channel:
        waiting_rooms = db.get_waiting_rooms(guild.id)
        available = [guild.get_channel(wr).mention for wr in waiting_rooms if guild.get_channel(wr) and guild.get_channel(wr).permissions_for(member).connect]
        rooms_text = "\n".join([f"› {r}" for r in available[:10]]) if available else "> *None*"
        await ctx.send(embed=discord.Embed(
            title="⏳  Must Be in a Waiting Room",
            description=(
                f"> You need to be in a voice waiting room to create a lobby.\n"
                f"──────────────────────\n"
                f"🔊  **Available Rooms:**\n{rooms_text}"
            ),
            color=COLORS["warning"]
        ), delete_after=20)
        return
    else:
        waiting_rooms = db.get_waiting_rooms(guild.id)
        if member.voice.channel.id not in waiting_rooms:
            available = [guild.get_channel(wr).mention for wr in waiting_rooms if guild.get_channel(wr) and guild.get_channel(wr).permissions_for(member).connect]
            rooms_text = "\n".join([f"› {r}" for r in available[:10]]) if available else "> *None*"
            await ctx.send(embed=discord.Embed(
                title="⏳  Wrong Voice Channel",
                description=(
                    f"> You're in `{member.voice.channel.name}` — that's not a waiting room.\n"
                    f"──────────────────────\n"
                    f"🔊  **Available Rooms:**\n{rooms_text}"
                ),
                color=COLORS["warning"]
            ), delete_after=20)
            return
    existing = db.get_player_active_lobby(user.id, guild.id)
    if existing:
        await ctx.send(embed=discord.Embed(
            title="❌  Already in Lobby",
            description=(
                f"> You're already in a lobby. Leave it first.\n"
                f"> Use  `{PREFIX}leave`  to leave."
            ),
            color=COLORS["error"]
        ), delete_after=10)
        return
    create_view = CreateLobbyView(ctx, mode)
    await ctx.send(embed=discord.Embed(
        title=f"🎮  Create  {mode.upper()}  Lobby",
        description=(
            f"> Press the button below to enter Room Info and create the lobby.\n"
            f"──────────────────────\n"
            f"> 💡  **You'll need:**\n"
            f"> ›  Room ID  (numbers)\n"
            f"> ›  Password  (optional)\n"
            f"> ›  Private Key  (optional)"
        ),
        color=COLORS["info"]
    ), view=create_view)


@bot.command(name="play")
async def play_cmd(ctx, mode: str = None):
    # 🆕 !!play ذكي — يقبل المود كـ argument
    # مثال: !!play 1v1, !!play 4v4, !!play 2v2
    # لو ما فيه argument → اعرض رسالة خطأ مع البدائل
    # لو فيه argument صحيح → شغّل الماتش بهذا المود
    # لو فيه argument خاطئ → اعرض رسالة خطأ

    if mode is None:
        # ما فيه argument — اعرض رسالة الخطأ
        await ctx.send(embed=discord.Embed(
            title="❌  أمر غير صحيح",
            description=(
                f"> الأمر  `{PREFIX}play`  غير صالح.\n"
                f"> يجب تحديد نوع الماتش بوضوح.\n"
                f"{separator()}\n"
                f"> 🎮  **الأوامر الصحيحة:**\n"
                f"> ─  `{PREFIX}play1v1`  —  ماتش 1 ضد 1  🔒  (للـ roles العالية)\n"
                f"> ─  `{PREFIX}play2v2`  —  ماتش 2 ضد 2\n"
                f"> ─  `{PREFIX}play3v3`  —  ماتش 3 ضد 3\n"
                f"> ─  `{PREFIX}play4v4`  —  ماتش 4 ضد 4  (الافتراضي)\n"
                f"> 💡  مثال:  `{PREFIX}play4v4`"
            ),
            color=COLORS["error"],
            timestamp=discord.utils.utcnow()
        ).set_footer(text=f"{BOT_FOOTER}  •  Specify the game mode"), delete_after=15)
        return

    # تحويل المود لـ lowercase وإزالة المسافات
    mode = mode.strip().lower()

    # قائمة المودات الصحيحة
    valid_modes = list(GAME_MODES.keys())  # ['1v1', '2v2', '3v3', '4v4']

    if mode not in valid_modes:
        # المود غير صحيح — اعرض رسالة خطأ
        await ctx.send(embed=discord.Embed(
            title="❌  مود غير صحيح",
            description=(
                f"> المود  `{mode}`  غير صالح.\n"
                f"> يجب استخدام أحد المودات التالية:\n"
                f"{separator()}\n"
                f"> 🎮  **المودات الصحيحة:**\n"
                f"> ─  `{PREFIX}play 1v1`  أو  `{PREFIX}play1v1`  🔒\n"
                f"> ─  `{PREFIX}play 2v2`  أو  `{PREFIX}play2v2`\n"
                f"> ─  `{PREFIX}play 3v3`  أو  `{PREFIX}play3v3`\n"
                f"> ─  `{PREFIX}play 4v4`  أو  `{PREFIX}play4v4`\n"
                f"> 💡  مثال:  `{PREFIX}play 4v4`"
            ),
            color=COLORS["error"],
            timestamp=discord.utils.utcnow()
        ).set_footer(text=f"{BOT_FOOTER}  •  Invalid mode"), delete_after=15)
        return

    # المود صحيح — شغّل الماتش
    # 🆕 فحص خاص بـ play1v1 (للأدوار العالية فقط)
    if mode == "1v1" and not is_high_role_member(ctx.author):
        member = ctx.author
        guild_roles = [r for r in ctx.guild.roles if r.hoist and r != ctx.guild.default_role]
        max_position = max((r.position for r in guild_roles), default=0)
        threshold = max(1, max_position // 2) if max_position else 0
        member_top = member.top_role.position if member.top_role else 0
        await ctx.send(embed=discord.Embed(
            title="🔒  أمر محمي",
            description=(
                f"> **الأمر:**  `{PREFIX}play 1v1`\n"
                f"> هذا الأمر مخصص فقط للأعضاء ذوي **الـ roles العالية** في السيرفر.\n"
                f"{separator()}\n"
                f"> 🎯  **شروط الاستخدام:**  تحقق أحد الشروط التالية:\n"
                f"> ─  صلاحية  `Administrator`  في السيرفر\n"
                f"> ─  صلاحية  `Manage Guild`  (إدارة السيرفر)\n"
                f"> ─  role تبعك في النصف العلوي من الهرم\n"
                f">    (مطلوب position  `≥ {threshold}`  —  أنت حالياً  `{member_top}`)\n"
                f"> 💡  استخدم  `{PREFIX}play 4v4`  للعب العادي  (متاح للجميع)."
            ),
            color=COLORS["error"],
            timestamp=discord.utils.utcnow()
        ).set_footer(text=f"{BOT_FOOTER}  •  Restricted Command"), delete_after=20)
        return

    # شغّل الماتش بهذا المود (نفس منطق play1v1_cmd / play2v2_cmd / etc.)
    await create_mode_lobby(ctx, mode)

@bot.command(name="play1v1")
async def play1v1_cmd(ctx):
    # 🆕 play1v1 للأعضاء ذوي الـ roles العالية فقط (admin / manage_guild / أعلى role في النصف العلوي)
    if not is_high_role_member(ctx.author):
        # اعرض رسالة احترافية تشرح المطلوب
        member = ctx.author
        guild_roles = [r for r in ctx.guild.roles if r.hoist and r != ctx.guild.default_role]
        max_position = max((r.position for r in guild_roles), default=0)
        threshold = max(1, max_position // 2) if max_position else 0
        member_top = member.top_role.position if member.top_role else 0
        await ctx.send(embed=discord.Embed(
            title="🔒  أمر محمي",
            description=(
                f"> **الأمر:**  `{PREFIX}play1v1`\n"
                f"> هذا الأمر مخصص فقط للأعضاء ذوي **الـ roles العالية** في السيرفر.\n"
                f"{separator()}\n"
                f"> 🎯  **شروط الاستخدام:**  تحقق أحد الشروط التالية:\n"
                f"> ─  صلاحية  `Administrator`  في السيرفر\n"
                f"> ─  صلاحية  `Manage Guild`  (إدارة السيرفر)\n"
                f"> ─  role تبعك في النصف العلوي من الهرم\n"
                f">    (مطلوب position  `≥ {threshold}`  —  أنت حالياً  `{member_top}`)\n"
                f"> 💡  استخدم  `{PREFIX}play`  للعب 4v4 العادي  (متاح للجميع)."
            ),
            color=COLORS["error"],
            timestamp=discord.utils.utcnow()
        ).set_footer(text=f"{BOT_FOOTER}  •  Restricted Command"), delete_after=20)
        return
    await create_mode_lobby(ctx, "1v1")

@bot.command(name="play2v2")
async def play2v2_cmd(ctx):
    await create_mode_lobby(ctx, "2v2")

@bot.command(name="play3v3")
async def play3v3_cmd(ctx):
    await create_mode_lobby(ctx, "3v3")

@bot.command(name="play4v4")
async def play4v4_cmd(ctx):
    await create_mode_lobby(ctx, "4v4")


@bot.command(name="p")
async def profile_cmd(ctx, member: discord.Member = None):
    target = member or ctx.author
    player = db.get_or_create_player(target.id, ctx.guild.id, target.display_name)
    await update_member_nickname(target, player.get("level", STARTING_LEVEL))
    await ctx.send(embed=create_profile_embed(player, target))


@bot.command(name="points", aliases=["mypoints", "pts"])
async def points_cmd(ctx, member: discord.Member = None):
    """💰 !!points — عرض نقاطك الحالية + كم تحتاج للرانك التالي"""
    target = member or ctx.author
    player = db.get_or_create_player(target.id, ctx.guild.id, target.display_name)
    level = player.get("level", STARTING_LEVEL)
    points = player.get("points", 0)
    pts_to_next = points_to_next_rank(points)
    next_rank = level + 1
    current_rank_floor = level * 50  # الحد الأدنى من النقاط للرانك الحالي
    next_rank_floor = next_rank * 50  # الحد الأدنى للرانك التالي
    progress_pct = int(((points - current_rank_floor) / 50) * 100) if level >= STARTING_LEVEL else 0
    progress_bar = make_progress_bar(points - current_rank_floor, 50, length=15)
    rank_color = get_rank_color(level)
    rank_title = get_rank_title(level)
    rank_emoji = get_rank_emoji(level)
    wr = round((player["wins"] / max(player["matches_played"], 1)) * 100, 1)
    wr_bar = make_winrate_bar(wr, length=10)

    embed = discord.Embed(
        title=f"💰  نقاط اللاعب",
        description=(
            f"> 👤  **اللاعب:**  {target.mention}\n"
            f"> 🏅  **الرانك:**  {rank_emoji}  `{rank_title}`  —  `#{level}`\n"
            f"> 💰  **النقاط:**  `{points:,}`  pts\n"
            f"{separator()}"
        ),
        color=rank_color,
        timestamp=discord.utils.utcnow()
    )
    # شريط التقدم للرانك التالي
    if pts_to_next > 0:
        embed.add_field(
            name=f"📈  التقدم للرانك التالي  —  `#{next_rank}`",
            value=(
                f"`{progress_bar}`  `{progress_pct}%`\n"
                f"> 💎  **النقاط الحالية:**  `{points}`\n"
                f"> 🎯  **النقاط المطلوبة:**  `{next_rank_floor}`\n"
                f"> ⏭️  **يتبقى:**  `{pts_to_next}`  نقطة"
            ),
            inline=False
        )
    else:
        embed.add_field(
            name="🎯  رانك جديد مكتمل!",
            value=(
                f"> 🎉  وصلت للرانك `#{level}`\n"
                f"> 💎  **النقاط:**  `{points}`\n"
                f"> 🚀  استمر في الفوز للوصول للرانك `#{next_rank}`"
            ),
            inline=False
        )

    # إحصائيات سريعة
    embed.add_field(name="🏆  Wins", value=f"```fix\n{player['wins']}\n```", inline=True)
    embed.add_field(name="💀  Losses", value=f"```fix\n{player['losses']}\n```", inline=True)
    embed.add_field(name="👑  MVPs", value=f"```fix\n{player['mvps']}\n```", inline=True)

    embed.add_field(
        name=f"📊  Win Rate  —  `{wr}%`",
        value=f"`{wr_bar}`  `{player['wins']}/{player['matches_played']}`",
        inline=False
    )
    embed.set_thumbnail(url=target.display_avatar.url)
    embed.set_author(name="Player Points", icon_url=None)
    embed.set_footer(text=f"{BOT_FOOTER}  •  {rank_title} #{level}")
    embed = apply_branding(embed, ctx.guild)
    await ctx.send(embed=embed)


@bot.command(name="card")
async def card_cmd(ctx, member: discord.Member = None):
    """🃏 !!card — بطاقة اللاعب (تعمل في كل قنوات play مثل باقي الأوامر)"""
    target = member or ctx.author
    player = db.get_or_create_player(target.id, ctx.guild.id, target.display_name)
    await update_member_nickname(target, player.get("level", STARTING_LEVEL))
    await ctx.send(embed=create_profile_embed(player, target))


@bot.command(name="top")
async def top_cmd(ctx):
    lb = db.get_leaderboard(ctx.guild.id, 10)
    if not lb:
        await ctx.send(embed=discord.Embed(
            title="🏆  Leaderboard",
            description=(
                f"> No players yet!\n"
                f"> Use `{PREFIX}play` to start your first match.\n"
                f"{separator()}"
            ),
            color=COLORS["leaderboard"]
        ))
        return
    embed = discord.Embed(
        title="🏆  Free Fire  —  Top 10 Leaderboard",
        color=COLORS["leaderboard"],
        timestamp=discord.utils.utcnow()
    )
    medals = ["🥇", "🥈", "🥉", "🏅", "🎖️", "🏵️", "🏷️", "8️⃣", "9️⃣", "🔟"]
    desc = ""
    for i, p in enumerate(lb):
        m = medals[i] if i < len(medals) else f"`#{i+1}`"
        mem = ctx.guild.get_member(p["user_id"])
        name = mem.display_name if mem else p["username"]
        level = p.get("level", STARTING_LEVEL)
        rank_emoji = get_rank_emoji(level)
        wr = round((p["wins"] / max(p["matches_played"], 1)) * 100, 1)
        wr_status = "🔥" if wr >= 70 else ("⭐" if wr >= 50 else "🌱")
        if i > 0:
            desc += "─" * 28 + "\n"
        desc += (
            f"{m}  **{rank_emoji} {name}**\n"
            f"└ 💰 `{p['points']:,}` pts  •  🏅 `RANK #{level}`  •  "
            f"🎮 `{p['matches_played']}` M  •  ✅ `{p['wins']}` W  ❌ `{p['losses']}` L  •  📈 `{wr}%` {wr_status}\n"
        )
    embed.description = desc
    embed.set_author(name=f"{ctx.guild.name} Leaderboard", icon_url=ctx.guild.icon.url if ctx.guild.icon else None)
    embed.set_footer(text=f"{BOT_FOOTER}  •  {len(lb)} players ranked")
    embed = apply_branding(embed, ctx.guild)
    await ctx.send(embed=embed)
    await update_leaderboard_channel(ctx.guild)


@bot.command(name="leave")
async def leave_cmd(ctx):
    lobby = db.get_player_active_lobby(ctx.author.id, ctx.guild.id)
    if not lobby:
        await ctx.send(embed=discord.Embed(
            title="❌  Not in Lobby",
            description=(
                f"> You're not currently in any lobby.\n"
                f"> Use `{PREFIX}play` to create one."
            ),
            color=COLORS["error"]
        ))
        return
    if lobby["creator_id"] == ctx.author.id and lobby["status"] == "waiting":
        total = len(lobby["team1_players"]) + len(lobby["team2_players"])
        if total <= 1:
            db.update_lobby_status(lobby["id"], "cancelled")
            cleanup_lobby_memory(lobby["id"])
            await ctx.send(embed=discord.Embed(
                title="🗑️  Lobby Cancelled",
                description=(
                    f"> Lobby `#{lobby['id']}` was cancelled."
                ),
                color=COLORS["warning"]
            ))
            return
        remaining = [p for p in (lobby["team1_players"] + lobby["team2_players"]) if p != ctx.author.id]
        if remaining:
            db.reassign_creator(lobby["id"], remaining[0])
    db.remove_player_from_lobby(lobby["id"], ctx.author.id)
    await ctx.send(embed=discord.Embed(
        title="✅  Left Lobby",
        description=(
            f"> You left lobby `#{lobby['id']}`."
        ),
        color=COLORS["success"]
    ))


@bot.command(name="matches")
async def matches_cmd(ctx):
    lobbies = db.get_active_lobbies(ctx.guild.id)
    if not lobbies:
        await ctx.send(embed=discord.Embed(
            title="🎮  Active Lobbies",
            description=(
                f"> No active lobbies right now.\n"
                f"> Use `{PREFIX}play` to start one."
            ),
            color=COLORS["info"]
        ))
        return
    embed = discord.Embed(title="🎮  Active Lobbies", color=COLORS["match"])
    for l in lobbies[:5]:
        mode = l.get("game_mode", DEFAULT_MODE)
        mi = GAME_MODES.get(mode, GAME_MODES[DEFAULT_MODE])
        t1c = len(l["team1_players"]); t2c = len(l["team2_players"])
        se = {"waiting": "⏳", "started": "🎮", "voting": "🗳️"}.get(l["status"], "❓")
        embed.add_field(
            name=f"`#{l['id']}`  {mi['emoji']}  {mode.upper()}  —  {se}",
            value=f"> 🟠 `{t1c}/{mi['team_size']}`  •  🟢 `{t2c}/{mi['team_size']}`",
            inline=False
        )
    await ctx.send(embed=embed)


@bot.command(name="mylevel")
async def mylevel_cmd(ctx, member: discord.Member = None):
    target = member or ctx.author
    player = db.get_or_create_player(target.id, ctx.guild.id, target.display_name)
    level = player.get("level", STARTING_LEVEL)
    rank_color = get_rank_color(level)
    rank_title = get_rank_title(level)
    rank_emoji = get_rank_emoji(level)
    await update_member_nickname(target, level)
    wr = round((player["wins"] / max(player["matches_played"], 1)) * 100, 1)
    wr_bar = make_winrate_bar(wr, length=10)
    kd_diff = player["wins"] - player["losses"]
    kd_sign = "+" if kd_diff >= 0 else ""
    embed = discord.Embed(
        title=f"{rank_emoji}  RANK  —  {target.display_name}",
        description=(
            f"> 🏅  **Rank:**  `{rank_title}`  —  `#{level}`\n"
            f"> 💰  **Points:**  `{player['points']:,}`  pts\n"
            f"{separator()}"
        ),
        color=rank_color,
        timestamp=discord.utils.utcnow()
    )
    embed.add_field(name="✅  Wins", value=f"```fix\n{player['wins']}\n```", inline=True)
    embed.add_field(name="❌  Losses", value=f"```fix\n{player['losses']}\n```", inline=True)
    embed.add_field(name="⚖️  W/L Diff", value=f"```fix\n{kd_sign}{kd_diff}\n```", inline=True)
    embed.add_field(
        name=f"📊  Win Rate  —  `{wr}%`",
        value=f"`{wr_bar}`  `{player['wins']}/{player['matches_played']}`",
        inline=False
    )
    embed.set_thumbnail(url=target.display_avatar.url)
    embed.set_author(name="Player Rank", icon_url=None)
    embed.set_footer(text=f"{BOT_FOOTER}  •  {rank_title} #{level}")
    embed = apply_branding(embed, ctx.guild)
    await ctx.send(embed=embed)


@bot.command(name="myrank")
async def myrank_cmd(ctx):
    target = ctx.author
    player = db.get_or_create_player(target.id, ctx.guild.id, target.display_name)
    level = player.get("level", STARTING_LEVEL)
    original = player.get("original_nickname") or extract_original_nickname(target.display_name)
    target_nick = build_nickname_with_level(original, level)
    is_owner = (target.id == ctx.guild.owner_id)
    embed = discord.Embed(
        title="📝  Your Rank",
        description=(
            f"> 👤  **Member:**  {target.mention}\n"
            f"> 🏅  **RANK:**  `#{level}`\n"
            f"──────────────────────\n"
            f"📝  **Current Nickname:**  `{target.display_name}`\n"
            f"🎯  **Target Nickname:**  `{target_nick}`"
        ),
        color=COLORS["profile"]
    )
    if is_owner:
        embed.add_field(name="👑  Server Owner", value="> Bot can't change your nickname. Apply manually.", inline=False)
    await ctx.send(embed=embed)


@bot.command(name="fixrank")
async def fixrank_cmd(ctx, member: discord.Member = None):
    target = member or ctx.author
    player = db.get_or_create_player(target.id, ctx.guild.id, target.display_name)
    level = player.get("level", STARTING_LEVEL)
    if target.id == ctx.guild.owner_id:
        original = player.get("original_nickname") or extract_original_nickname(target.display_name)
        target_nick = build_nickname_with_level(original, level)
        await ctx.send(embed=discord.Embed(
            title="👑  Server Owner",
            description=(
                f"> {target.mention}  →  **RANK `#{level}`**\n"
                f"──────────────────────\n"
                f"> 📝  **Target Nickname:**  `{target_nick}`\n"
                f"> Apply manually:  *Right-click → Edit Profile → Nickname*"
            ),
            color=COLORS["warning"]
        ))
        return
    await update_member_nickname(target, level)
    await ctx.send(embed=discord.Embed(
        title="🔧  Rank Applied",
        description=(
            f"> {target.mention}  →  **RANK `#{level}`**"
        ),
        color=COLORS["success"]
    ))


@bot.command(name="matchinfo")
async def matchinfo_cmd(ctx, lobby_id: int = None):
    if lobby_id is None:
        await ctx.send(embed=discord.Embed(
            title="❌  Missing ID",
            description=(
                f"> Please provide a lobby ID.\n"
                f"> Usage:  `{PREFIX}matchinfo <id>`"
            ),
            color=COLORS["error"]
        ))
        return
    lobby = db.get_lobby(lobby_id)
    if not lobby:
        await ctx.send(embed=discord.Embed(
            title="❌  Not Found",
            description=(
                f"> Lobby `#{lobby_id}` doesn't exist."
            ),
            color=COLORS["error"]
        ))
        return
    embed = discord.Embed(
        title=f"📋  Match  —  `#{lobby_id}`",
        description=(
            f"> 📊  **Status:**  `{lobby['status']}`\n"
            f"> 🎮  **Mode:**  `{lobby.get('game_mode', DEFAULT_MODE).upper()}`\n"
            f"──────────────────────"
        ),
        color=COLORS["info"]
    )
    t1m = "\n".join([f"› <@{p}>" for p in lobby["team1_players"]]) or "> *Empty*"
    t2m = "\n".join([f"› <@{p}>" for p in lobby["team2_players"]]) or "> *Empty*"
    embed.add_field(name=f"🔴  Team 1  —  `{len(lobby['team1_players'])}`", value=t1m, inline=True)
    embed.add_field(name=f"🟢  Team 2  —  `{len(lobby['team2_players'])}`", value=t2m, inline=True)
    await ctx.send(embed=embed)


# ============================================================
# ADMIN COMMANDS
# ============================================================

@bot.command(name="setup")
@commands.check(is_bot_owner_or_admin_check)
async def setup_cmd(ctx):
    guild = ctx.guild
    created = []
    if ctx.author.id == BOT_OWNER_ID:
        db.add_allowed_guild(guild.id, guild.name, ctx.author.id)
    
    # 🆕 كاتيجوري منفصل للقنوات النصية
    text_cat_name = "🎮 FREE FIRE — TEXT"
    text_cat = discord.utils.get(guild.categories, name=text_cat_name)
    if not text_cat:
        text_cat = await guild.create_category(text_cat_name, overwrites={guild.default_role: discord.PermissionOverwrite(read_messages=True), guild.me: discord.PermissionOverwrite(manage_channels=True, manage_messages=True)})

    # 🆕 كاتيجوري منفصل للقنوات الصوتية
    voice_cat_name = "🎮 FREE FIRE — VOICE"
    voice_cat = discord.utils.get(guild.categories, name=voice_cat_name)
    if not voice_cat:
        voice_cat = await guild.create_category(voice_cat_name, overwrites={guild.default_role: discord.PermissionOverwrite(read_messages=True), guild.me: discord.PermissionOverwrite(manage_channels=True, manage_messages=True)})

    # 🆕 قناة القواعد تُنشأ أولاً (في كاتيجوري النصي)
    rules_channel_name = "📜・rules"
    if not discord.utils.get(guild.text_channels, name=rules_channel_name):
        rules_overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=True, send_messages=False, add_reactions=False),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_messages=True)
        }
        rules_ch = await guild.create_text_channel(rules_channel_name, category=text_cat, topic="Rules", overwrites=rules_overwrites, position=0)
        # أرسل رسالة القواعد الافتراضية
        try:
            rules_embed = discord.Embed(
                title="📜  قواعد السيرفر",
                description=(
                    f"> مرحباً بك في  **{guild.name}**  🔥\n"
                    f"> يرجى الالتزام بالقواعد التالية:\n"
                    f"{separator()}\n"
                    f"> **1️⃣  الاحترام المتبادل**\n"
                    f"> ─  احترم جميع اللاعبين والأدمنز.\n"
                    f"> ─  ممنوع السب، الشتم، أو الإساءة.\n\n"
                    f"> **2️⃣  قواعد اللعب**\n"
                    f"> ─  ادخل غرفة انتظار قبل اللعب.\n"
                    f"> ─  استخدم  `{PREFIX}play4v4`  لبدء ماتش.\n"
                    f"> ─  التزم بنتيجة التصويت.\n\n"
                    f"> **3️⃣  عدم الغش**\n"
                    f"> ─  ممنوع التلاعب بالتصويت.\n"
                    f"> ─  ممنوع مغادرة الماتش في المنتصف.\n\n"
                    f"> **4️⃣  استخدام الأوامر**\n"
                    f"> ─  الأوامر تعمل فقط في قنوات play.\n"
                    f"> ─  انتظر الـ cooldown قبل التكرار.\n\n"
                    f"> **5️⃣  العقوبات**\n"
                    f"> ─  مخالفة القواعد = تحذير / كتم / طرد.\n"
                    f"> ─  القرار النهائي للأدمن.\n\n"
                    f"> 💬  لأي استفسار، تواصل مع الأدمن."
                ),
                color=COLORS["warning"],
                timestamp=discord.utils.utcnow()
            )
            rules_embed.set_author(name="Server Rules", icon_url=None)
            rules_embed.set_footer(text=f"{BOT_FOOTER}  •  Read carefully")
            if RULES_IMAGE_URL:
                rules_embed.set_image(url=RULES_IMAGE_URL)
            elif guild.icon:
                rules_embed.set_image(url=guild.icon.url)
            await rules_ch.send(embed=rules_embed)
        except Exception as e:
            logger.warning(f"Failed to send rules embed: {e}")
        created.append(rules_channel_name)

    # 🆕 القنوات النصية في كاتيجوري النصي
    for ch_name, topic in [("🎮・apostada-play", "Play"), ("🎮・highlight-play", "Play"), ("🎮・zelika-play", "Play"), ("📊・match-results", "Results"), ("🏆・leaderboard", "Leaderboard"), ("👤・profiles", "Profiles")]:
        if not discord.utils.get(guild.text_channels, name=ch_name):
            ch = await guild.create_text_channel(ch_name, category=text_cat, topic=topic)
            db.add_commands_channel(guild.id, ch.id)
            db.add_play_channel(guild.id, ch.id)
            if "leaderboard" in ch_name:
                db.set_guild_setting(guild.id, "leaderboard_channel_id", ch.id)
            created.append(ch_name)
    
    # 🆕 القنوات الصوتية في كاتيجوري الصوتي
    for ch_name in ["⏳・Waiting 1", "⏳・Waiting 2", "⏳・Waiting 3", "⏳・Waiting 4", "⏳・Waiting 5", "🔒・Waiting Prv 1", "🔒・Waiting Prv 2", "🔒・Waiting Prv 3", "🔒・Waiting Staff"]:
        if not discord.utils.get(guild.voice_channels, name=ch_name):
            overwrites = {guild.me: discord.PermissionOverwrite(connect=True, manage_channels=True)}
            if "Prv" in ch_name or "Staff" in ch_name:
                overwrites[guild.default_role] = discord.PermissionOverwrite(connect=False)
            ch = await guild.create_voice_channel(ch_name, category=voice_cat, overwrites=overwrites)
            db.add_waiting_room(guild.id, ch.id)
            created.append(ch_name)
    try: await update_leaderboard_channel(guild)
    except: pass
    # 🆕 أنشئ الـ Roles الخاصة بالألقاب + حدّث صلاحيات Waiting Prv
    try:
        await setup_rank_roles_permissions(guild)
        created.append("Rank Roles (Best/Goated/Skilled/Efficient)")
    except Exception as e:
        logger.warning(f"setup_rank_roles_permissions failed: {e}")
    # 🆕 أنشئ نظام السجن (JAIL role + قناتي السجن)
    try:
        await setup_jail_system(guild)
        created.append("JAIL System (role + jail-chat + jail-prouves)")
    except Exception as e:
        logger.warning(f"setup_jail_system failed: {e}")
    await ctx.send(embed=discord.Embed(
        title="✅  Setup Complete!",
        description=(
            f"> Created  `{len(created)}`  channels successfully.\n"
            f"{separator()}\n"
            f"> 📜  **Rules channel:**  مفعّل (للقراءة فقط)\n"
            f"> 🎮  Use  `{PREFIX}play4v4`  in play channels to start."
        ),
        color=COLORS["success"],
        timestamp=discord.utils.utcnow()
    ).set_footer(text=f"{BOT_FOOTER}  •  Setup complete"))


@bot.command(name="cleanup")
@commands.check(is_bot_owner_or_admin_check)
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
    await ctx.send(embed=discord.Embed(
        title="🧹  Cleanup Complete!",
        description=(
            f"> Deleted  `{deleted}`  match categories."
        ),
        color=COLORS["success"]
    ))


@bot.command(name="scan")
@commands.check(is_bot_owner_or_admin_check)
async def scan_cmd(ctx, page: int = 1):
    """🔍 !!scan [page] — سكان تفصيلي لكل كاتيجوريات السيرفر"""
    guild = ctx.guild
    categories = sorted(guild.categories, key=lambda c: c.position)
    per_page = 3  # 3 كاتيجوري لكل صفحة (لأن كل وحدة فيها تفاصيل كثيرة)
    total_pages = max(1, (len(categories) + per_page - 1) // per_page)
    if page < 1: page = 1
    if page > total_pages: page = total_pages
    start = (page - 1) * per_page
    end = start + per_page
    page_cats = categories[start:end]

    # 🆕 اجمع كل القنوات بدون كاتيجوري
    no_cat_text = [ch for ch in guild.text_channels if ch.category is None]
    no_cat_voice = [ch for ch in guild.voice_channels if ch.category is None]

    embed = discord.Embed(
        title=f"🔍  Server Scan  —  `{len(categories)}`  Categories",
        description=(
            f"> 🏠  **Server:**  {guild.name}\n"
            f"> 📝  **Text Channels:**  `{len(guild.text_channels)}`\n"
            f"> 🔊  **Voice Channels:**  `{len(guild.voice_channels)}`\n"
            f"> 📄  **Page:**  `{page}/{total_pages}`\n"
            f"──────────────────────"
        ),
        color=COLORS["info"]
    )

    for i, cat in enumerate(page_cats, start + 1):
        # 🆕 تفاصيل كل قناة داخل الكاتيجوري
        text_chs = sorted(cat.text_channels, key=lambda c: c.position)
        voice_chs = sorted(cat.voice_channels, key=lambda c: c.position)

        detail = ""
        if text_chs:
            detail += "**📝  Text Channels:**\n"
            for ch in text_chs:
                topic = f"  —  `{ch.topic[:30]}...`" if ch.topic and len(ch.topic) > 30 else (f"  —  `{ch.topic}`" if ch.topic else "")
                detail += f"›  #{ch.name}{topic}\n"
        if voice_chs:
            detail += "**🔊  Voice Channels:**\n"
            for ch in voice_chs:
                members_count = len(ch.members)
                detail += f"›  🔊 {ch.name}  (`{members_count}` members)\n"

        if not detail:
            detail = "> *Empty category*"

        embed.add_field(
            name=f"📁  `{i}.`  {cat.name}",
            value=detail,
            inline=False
        )

    # 🆕 اعرض القنوات بدون كاتيجوري (في الصفحة الأخيرة)
    if page == total_pages and (no_cat_text or no_cat_voice):
        detail = ""
        if no_cat_text:
            detail += "**📝  Text (no category):**\n"
            for ch in no_cat_text:
                detail += f"›  #{ch.name}\n"
        if no_cat_voice:
            detail += "**🔊  Voice (no category):**\n"
            for ch in no_cat_voice:
                detail += f"›  🔊 {ch.name}\n"
        embed.add_field(name="📂  No Category", value=detail or "> *None*", inline=False)

    embed.set_footer(text=f"Page {page}/{total_pages}  •  {PREFIX}scan <page>  •  {PREFIX}deletecat <name>  •  {PREFIX}confirmcat <name>")
    embed = apply_branding(embed, ctx.guild)
    await ctx.send(embed=embed)


@bot.command(name="deletecat", aliases=["delcat"])
@commands.check(is_bot_owner_or_admin_check)
async def deletecat_cmd(ctx, *, category_name: str = None):
    """🗑️ !!deletecat <name> — حذف كاتيجوري بكل قنواتها"""
    if not category_name:
        await ctx.send(embed=discord.Embed(
            title="❌  Missing Name",
            description=(
                f"> Please provide a category name.\n"
                f"> Usage:  `{PREFIX}deletecat <category name>`\n"
                f"> Use  `{PREFIX}scan`  to see all categories."
            ),
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
            title="❌  Not Found",
            description=(
                f"> No category matching  `{category_name}`.\n"
                f"> Use  `{PREFIX}scan`  to see all categories."
            ),
            color=COLORS["error"]
        ))
        return

    # اعرض تأكيد قبل الحذف
    text_count = len(target.text_channels)
    voice_count = len(target.voice_channels)
    total_channels = text_count + voice_count

    confirm_embed = discord.Embed(
        title="⚠️  Confirm Deletion",
        description=(
            f"> 📁  **Category:**  `{target.name}`\n"
            f"> 📊  **Channels:**  `{total_channels}`  (`{text_count}` text  +  `{voice_count}` voice)\n"
            f"──────────────────────\n"
            f"> ⚠️  **This will delete ALL channels inside!**\n"
            f"> Type  `{PREFIX}confirmcat {target.name}`  to confirm."
        ),
        color=COLORS["warning"]
    )
    await ctx.send(embed=confirm_embed)


@bot.command(name="confirmcat")
@commands.check(is_bot_owner_or_admin_check)
async def confirmcat_cmd(ctx, *, category_name: str = None):
    """✅ !!confirmcat <name> — تأكيد حذف الكاتيجوري"""
    if not category_name:
        await ctx.send(embed=discord.Embed(
            title="❌  Missing Name",
            description=(
                f"> Usage:  `{PREFIX}confirmcat <name>`"
            ),
            color=COLORS["error"]
        ))
        return

    guild = ctx.guild
    target = None
    for cat in guild.categories:
        if cat.name.lower() == category_name.lower() or category_name.lower() in cat.name.lower():
            target = cat
            break

    if not target:
        await ctx.send(embed=discord.Embed(
            title="❌  Not Found",
            description=(
                f"> No category matching  `{category_name}`."
            ),
            color=COLORS["error"]
        ))
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
            title="🗑️  Category Deleted!",
            description=(
                f"> **{cat_name}** has been deleted.\n"
                f"──────────────────────\n"
                f"> ✅  **Channels deleted:**  `{deleted}`\n"
                f"> ❌  **Errors:**  `{errors}`"
            ),
            color=COLORS["success"]
        ))
    except (discord.NotFound, discord.Forbidden) as e:
        await ctx.send(embed=discord.Embed(
            title="⚠️  Partial Delete",
            description=(
                f"> Deleted  `{deleted}`  channels but couldn't delete the category itself.\n"
                f"> Error:  `{e}`"
            ),
            color=COLORS["warning"]
        ))


@bot.command(name="fixrankall", aliases=["forcerankall"])
@commands.check(is_admin_check)
async def fixrankall_cmd(ctx):
    guild = ctx.guild
    progress = await ctx.send(embed=discord.Embed(
        title="🚀  Applying Ranks...",
        description=(
            f"> Processing  `{len(guild.members)}`  members.\n"
            f"> Please wait..."
        ),
        color=COLORS["warning"]
    ))
    updated = 0
    for member in guild.members:
        if member.bot: continue
        try:
            player = db.get_or_create_player(member.id, guild.id, member.display_name)
            await update_member_nickname(member, player.get("level", STARTING_LEVEL))
            updated += 1
            await asyncio.sleep(0.3)
        except: pass
    await progress.edit(embed=discord.Embed(
        title="✅  Done!",
        description=(
            f"> Updated  `{updated}`  members successfully."
        ),
        color=COLORS["success"]
    ))


@bot.command(name="botinfo")
async def botinfo_cmd(ctx):
    total_members = sum(g.member_count for g in bot.guilds)
    total_text_channels = sum(len(g.text_channels) for g in bot.guilds)
    total_voice_channels = sum(len(g.voice_channels) for g in bot.guilds)
    embed = discord.Embed(
        title="🤖  Bot Info",
        description=(
            f"> 🔥  **Free Fire Matchmaking Bot**\n"
            f"> نظام ماتشмейكنج متكامل لإدارة مباريات Free Fire\n"
            f"{separator()}"
        ),
        color=COLORS["info"],
        timestamp=discord.utils.utcnow()
    )
    embed.add_field(name="📛  Name", value=f"```fix\n{bot.user.name}\n```", inline=True)
    embed.add_field(name="🏷️  Version", value=f"```fix\nv4.0 CLEAN\n```", inline=True)
    embed.add_field(name="⌨️  Prefix", value=f"```fix\n{PREFIX}\n```", inline=True)
    embed.add_field(name="🏠  Servers", value=f"```fix\n{len(bot.guilds)}\n```", inline=True)
    embed.add_field(name="👥  Users", value=f"```fix\n{total_members:,}\n```", inline=True)
    embed.add_field(name="👑  Owner", value=f"```fix\n{BOT_OWNER_NAME}\n```", inline=True)
    embed.add_field(
        name="📡  Channels Coverage",
        value=(
            f"> 📝  **Text Channels:**  `{total_text_channels}`\n"
            f"> 🔊  **Voice Channels:**  `{total_voice_channels}`"
        ),
        inline=False
    )
    embed.add_field(
        name="🎮  Features",
        value=(
            f"> 🏆  4 Game Modes (1v1, 2v2, 3v3, 4v4)\n"
            f"> 🗳️  Auto Vote System\n"
            f"> 🏅  Dynamic Rank System\n"
            f"> 📊  Live Leaderboard\n"
            f"> ❌  Cancel Match Button"
        ),
        inline=False
    )
    embed.set_thumbnail(url=bot.user.display_avatar.url)
    embed.set_author(name="Bot Information", icon_url=bot.user.display_avatar.url)
    embed.set_footer(text=f"{BOT_FOOTER}  •  Online & Ready")
    embed = apply_branding(embed, ctx.guild)
    await ctx.send(embed=embed)


@bot.command(name="setcommandschannel")
@commands.check(is_admin_check)
async def setcommandschannel_cmd(ctx, channel: discord.TextChannel = None):
    channel = channel or ctx.channel
    if channel.id in db.get_commands_channels(ctx.guild.id):
        db.remove_commands_channel(ctx.guild.id, channel.id)
        await ctx.send(embed=discord.Embed(
            title="✅  Channel Removed",
            description=(
                f"> {channel.mention}  has been removed from allowed command channels."
            ),
            color=COLORS["success"]
        ))
    else:
        db.add_commands_channel(ctx.guild.id, channel.id)
        await ctx.send(embed=discord.Embed(
            title="✅  Channel Added",
            description=(
                f"> {channel.mention}  has been added to allowed command channels."
            ),
            color=COLORS["success"]
        ))


@bot.command(name="setleaderboard")
@commands.check(is_admin_check)
async def setleaderboard_cmd(ctx):
    db.set_guild_setting(ctx.guild.id, "leaderboard_channel_id", ctx.channel.id)
    await update_leaderboard_channel(ctx.guild)
    await ctx.send(embed=discord.Embed(
        title="✅  Leaderboard Set",
        description=(
            f"> {ctx.channel.mention}  is now the leaderboard channel.\n"
            f"> It will update automatically."
        ),
        color=COLORS["success"]
    ))


# ============================================================
# 🆕 REPORT & BAN COMMANDS — أوامر البلاغات والحظر
# ============================================================

@bot.command(name="report")
async def report_cmd(ctx, member: discord.Member = None, *, reason: str = None):
    """🚨 !!report @user [reason] — بلّغ عن لاعب"""
    if not member:
        await ctx.send(embed=discord.Embed(
            title="❌  Missing User",
            description=(
                f"> Usage:  `{PREFIX}report @user [reason]`\n"
                f"> مثال:  `{PREFIX}report @user يستخدم هاك`"
            ),
            color=COLORS["error"]
        ), delete_after=15)
        return
    if member.id == ctx.author.id:
        await ctx.send(embed=discord.Embed(
            title="❌  لا يمكنك البلاغ عن نفسك",
            color=COLORS["error"]
        ), delete_after=10)
        return
    if member.bot:
        await ctx.send(embed=discord.Embed(
            title="❌  لا يمكنك البلاغ عن بوت",
            color=COLORS["error"]
        ), delete_after=10)
        return
    # سجل البلاغ
    added, total = db.add_report(ctx.guild.id, ctx.author.id, member.id, reason=reason)
    if not added:
        await ctx.send(embed=discord.Embed(
            title="⚠️  بلغت من قبل",
            description=f"> لقد بلّغت على {member.mention} سابقاً.",
            color=COLORS["warning"]
        ), delete_after=10)
        return
    remaining = max(0, REPORT_THRESHOLD - total)
    report_embed = discord.Embed(
        title="🚨  تم تسجيل البلاغ",
        description=(
            f"> 👤  **اللاعب المُبلَّغ عنه:**  {member.mention}\n"
            f"> 👮  **الـمُبلَّغ:**  {ctx.author.mention}\n"
            + (f"> 📝  **السبب:**  {reason}\n" if reason else "")
            + f"> 📊  **إجمالي البلاغات:**  `{total}/{REPORT_THRESHOLD}`\n"
            + (f"> ⚠️  **يتبقى:**  `{remaining}`  بلاغ للحظر التلقائي" if remaining > 0 else f"> 🚨  **وصل للحد!**  سيتم الحظر تلقائياً")
        ),
        color=COLORS["warning"] if remaining > 0 else COLORS["error"],
        timestamp=discord.utils.utcnow()
    )
    report_embed.set_footer(text=f"{BOT_FOOTER}  •  Report #{total}")
    embed = apply_branding(embed, ctx.guild)
    await ctx.send(embed=report_embed)
    # فحص الحظر التلقائي
    await check_and_apply_auto_ban(ctx.guild, member.id, total, ctx.author.id)


@bot.command(name="reports")
async def reports_cmd(ctx, member: discord.Member = None):
    """📊 !!reports @user — عرض بلاغات لاعب"""
    target = member or ctx.author
    reports = db.get_reports_for_player(ctx.guild.id, target.id)
    count = len(reports)
    embed = discord.Embed(
        title=f"🚨  بلاغات اللاعب  —  {target.display_name}",
        description=(
            f"> 👤  **اللاعب:**  {target.mention}\n"
            f"> 📊  **إجمالي البلاغات:**  `{count}/{REPORT_THRESHOLD}`\n"
            + (f"> 🚨  **محظور تلقائياً**" if count >= REPORT_THRESHOLD else f"> ⚠️  **يتبقى:**  `{REPORT_THRESHOLD - count}`  بلاغ للحظر")
            + f"\n{separator()}"
        ),
        color=COLORS["error"] if count >= REPORT_THRESHOLD else COLORS["warning"],
        timestamp=discord.utils.utcnow()
    )
    embed.set_thumbnail(url=target.display_avatar.url)
    if reports:
        # اعرض آخر 10 بلاغات
        for i, r in enumerate(reports[:10], 1):
            reporter = ctx.guild.get_member(r["reporter_id"])
            reporter_name = reporter.display_name if reporter else f"User#{r['reporter_id']}"
            reason = r.get("reason") or "بدون سبب"
            timestamp = r.get("created_at", "N/A")[:19] if r.get("created_at") else "N/A"
            embed.add_field(
                name=f"#{i}  —  {reporter_name}",
                value=f"> 📝  `{reason}`\n> 📅  `{timestamp}`",
                inline=False
            )
        if count > 10:
            embed.set_footer(text=f"... و {count - 10} بلاغ آخر")
            embed = apply_branding(embed, ctx.guild)
    else:
        embed.description = f"> ✅  لا توجد بلاغات على {target.mention}"
        embed.color = COLORS["success"]
    embed.set_author(name="Player Reports", icon_url=None)
    await ctx.send(embed=embed)


# ============================================================
# 🆕 JAIL SYSTEM — نظام السجن للغشاشين
# ============================================================

JAIL_ROLE_NAME = "JAIL"
JAIL_CHAT_NAME = "・💬jail-chat"
JAIL_PROUVES_NAME = "・💬jail-prouves"
JAIL_CATEGORY_NAME = "🔒 JAIL"

async def setup_jail_system(guild):
    """🆕 ينشئ role الـ JAIL + كاتيجوري منفصل + قناتي السجن."""
    # 1) أنشئ role الـ JAIL لو غير موجود
    jail_role = discord.utils.get(guild.roles, name=JAIL_ROLE_NAME)
    if not jail_role:
        try:
            jail_role = await guild.create_role(
                name=JAIL_ROLE_NAME,
                color=discord.Color(0x36393F),  # رمادي داكن
                permissions=discord.Permissions(
                    view_channel=True,
                    send_messages=True,
                    read_messages=True,
                    read_message_history=True,
                    attach_files=True,
                    embed_links=True,
                ),
                reason="Free Fire Bot — JAIL system"
            )
            logger.info(f"✅ Created JAIL role in {guild.name}")
        except (discord.Forbidden, discord.HTTPException) as e:
            logger.warning(f"Failed to create JAIL role: {e}")
            return None

    # 2) 🆕 أنشئ كاتيجوري منفصل للسجن
    jail_cat = discord.utils.get(guild.categories, name=JAIL_CATEGORY_NAME)
    if not jail_cat:
        try:
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(view_channel=False),
                guild.me: discord.PermissionOverwrite(view_channel=True, manage_channels=True, manage_messages=True, move_members=True, connect=True),
                jail_role: discord.PermissionOverwrite(view_channel=True),
            }
            for role in guild.roles:
                if role.permissions.administrator or role.permissions.manage_guild:
                    overwrites[role] = discord.PermissionOverwrite(view_channel=True, manage_channels=True, manage_messages=True, move_members=True, connect=True)
            jail_cat = await guild.create_category(JAIL_CATEGORY_NAME, overwrites=overwrites, reason="JAIL system")
            logger.info(f"✅ Created JAIL category")
        except (discord.Forbidden, discord.HTTPException) as e:
            logger.warning(f"Failed to create JAIL category: {e}")
            # fallback: استخدم كاتيجوري النصي
            jail_cat = discord.utils.get(guild.categories, name="🎮 FREE FIRE — TEXT")

    # 3) أنشئ قناتي السجن في كاتيجوري السجن
    jail_chat = discord.utils.get(guild.text_channels, name=JAIL_CHAT_NAME)
    if not jail_chat:
        try:
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(view_channel=False),
                guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_messages=True),
                jail_role: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
            }
            for role in guild.roles:
                if role.permissions.administrator or role.permissions.manage_guild:
                    overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_messages=True)
            jail_chat = await guild.create_text_channel(
                JAIL_CHAT_NAME,
                category=jail_cat,
                topic="JAIL — chat for jailed players",
                overwrites=overwrites
            )
            logger.info(f"✅ Created {JAIL_CHAT_NAME}")
        except (discord.Forbidden, discord.HTTPException) as e:
            logger.warning(f"Failed to create jail-chat: {e}")
    elif jail_chat.category != jail_cat:
        # انقل القناة لكاتيجوري السجن لو موجودة في كاتيجوري ثاني
        try:
            await jail_chat.edit(category=jail_cat)
        except:
            pass

    jail_prouves = discord.utils.get(guild.text_channels, name=JAIL_PROUVES_NAME)
    if not jail_prouves:
        try:
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(view_channel=False),
                guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_messages=True),
                jail_role: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True, attach_files=True),
            }
            for role in guild.roles:
                if role.permissions.administrator or role.permissions.manage_guild:
                    overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_messages=True)
            jail_prouves = await guild.create_text_channel(
                JAIL_PROUVES_NAME,
                category=jail_cat,
                topic="JAIL — proofs for jailed players",
                overwrites=overwrites
            )
            logger.info(f"✅ Created {JAIL_PROUVES_NAME}")
        except (discord.Forbidden, discord.HTTPException) as e:
            logger.warning(f"Failed to create jail-prouves: {e}")
    elif jail_prouves.category != jail_cat:
        try:
            await jail_prouves.edit(category=jail_cat)
        except:
            pass

    # 4) حدّث كل القنوات الأخرى — امنع JAIL role من رؤيتها
    for ch in guild.text_channels:
        if ch.name in [JAIL_CHAT_NAME, JAIL_PROUVES_NAME]:
            continue
        if ch.name == "📜・rules":
            continue
        try:
            overwrite = ch.overwrites_for(jail_role)
            overwrite.view_channel = False
            overwrite.send_messages = False
            await ch.set_permissions(jail_role, overwrite=overwrite, reason="JAIL system — restrict access")
        except (discord.Forbidden, discord.HTTPException):
            pass
    # منع من الفويسات أيضاً (إلا فويس السجن الخاص باللاعب لو موجود)
    for ch in guild.voice_channels:
        # لا تمنع الفويسات داخل كاتيجوري السجن
        if ch.category and ch.category.name == JAIL_CATEGORY_NAME:
            continue
        try:
            overwrite = ch.overwrites_for(jail_role)
            overwrite.view_channel = False
            overwrite.connect = False
            overwrite.speak = False
            await ch.set_permissions(jail_role, overwrite=overwrite, reason="JAIL system — restrict voice")
        except (discord.Forbidden, discord.HTTPException):
            pass

    return jail_role


async def create_jail_voice_for_player(guild, member, jail_role, jail_cat):
    """🆕 ينشئ فويس خاص بالمسجون بإيديه داخل كاتيجوري السجن."""
    voice_name = f"🔒 Jail-{member.id}"
    # تحقق لو موجود
    existing = discord.utils.get(guild.voice_channels, name=voice_name)
    if existing:
        return existing
    try:
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False, connect=False),
            guild.me: discord.PermissionOverwrite(view_channel=True, connect=True, manage_channels=True, move_members=True),
            jail_role: discord.PermissionOverwrite(view_channel=False, connect=False),  # باقي المسجونين ما يدخلون
            member: discord.PermissionOverwrite(view_channel=True, connect=True, speak=True),
        }
        for role in guild.roles:
            if role.permissions.administrator or role.permissions.manage_guild:
                overwrites[role] = discord.PermissionOverwrite(view_channel=True, connect=True, move_members=True, manage_channels=True)
        ch = await guild.create_voice_channel(voice_name, category=jail_cat, overwrites=overwrites, reason=f"JAIL voice for {member}")
        logger.info(f"✅ Created JAIL voice for {member.id}")
        return ch
    except (discord.Forbidden, discord.HTTPException) as e:
        logger.warning(f"Failed to create JAIL voice: {e}")
        return None


async def delete_jail_voice_for_player(guild, member):
    """🆕 يحذف فويس السجن الخاص باللاعب عند فك السجن."""
    voice_name = f"🔒 Jail-{member.id}"
    existing = discord.utils.get(guild.voice_channels, name=voice_name)
    if existing:
        try:
            await existing.delete(reason=f"JAIL voice deleted — {member} unjailed")
            logger.info(f"✅ Deleted JAIL voice for {member.id}")
        except (discord.Forbidden, discord.HTTPException):
            pass


@bot.command(name="jail", aliases=["sendtojail", "cheater"])
@commands.check(is_admin_check)
async def jail_cmd(ctx, member: discord.Member = None, *, reason: str = None):
    """🔒 !!jail @user [reason] — إرسال لاعب للسجن (للغشاشين)"""
    if not member:
        await ctx.send(embed=discord.Embed(
            title="❌  Missing User",
            description=f"> Usage:  `{PREFIX}jail @user [reason]`",
            color=COLORS["error"]
        ), delete_after=15)
        return
    if member.bot:
        await ctx.send("❌ لا يمكنك سجن بوت!", delete_after=10)
        return

    # أنشئ نظام السجن لو غير موجود
    jail_role = await setup_jail_system(ctx.guild)
    if not jail_role:
        await ctx.send("❌ لم أستطع إنشاء نظام السجن! تأكد من صلاحياتي.", delete_after=10)
        return

    # أعطِ اللاعب role الـ JAIL
    try:
        await member.add_roles(jail_role, reason=f"Jailed by {ctx.author.name}: {reason or 'No reason'}")
    except (discord.Forbidden, discord.HTTPException) as e:
        await ctx.send(f"❌ لم أستطع إعطاء الـ role! تأكد من ترتيب الـ roles. ({e})", delete_after=15)
        return

    # 🆕 أنشئ فويس خاص بالمسجون بإيديه
    jail_cat = discord.utils.get(ctx.guild.categories, name=JAIL_CATEGORY_NAME)
    jail_voice = None
    if jail_cat:
        jail_voice = await create_jail_voice_for_player(ctx.guild, member, jail_role, jail_cat)
        # انقل اللاعب لفويسه لو هو في فويس
        if jail_voice and member.voice and member.voice.channel:
            try:
                await member.move_to(jail_voice)
            except (discord.HTTPException, discord.Forbidden):
                pass

    jail_embed = discord.Embed(
        title="🔒  تم إرسال اللاعب للسجن",
        description=(
            f"> 👤  **اللاعب:**  {member.mention}\n"
            f"> 👮  **الأدمن:**  {ctx.author.mention}\n"
            + (f"> 📝  **السبب:**  `{reason}`\n" if reason else "")
            + f"{separator()}\n"
            f"> 🔒  اللاعب الآن في السجن\n"
            f"> 💬  يمكنه الكتابة في `{JAIL_CHAT_NAME}` و `{JAIL_PROUVES_NAME}`\n"
            + (f"> 🎤  فويس السجن: `{jail_voice.name}`\n" if jail_voice else "")
            + f"> ✅  لفك السجن:  `{PREFIX}unjail @user`"
        ),
        color=COLORS["error"],
        timestamp=discord.utils.utcnow()
    )
    jail_embed.set_author(name="JAIL System", icon_url=None)
    jail_embed.set_footer(text=f"{BOT_FOOTER}  •  Jailed")
    jail_embed = apply_branding(jail_embed, ctx.guild)
    await ctx.send(embed=jail_embed)

    # أرسل رسالة في قناة jail-chat
    jail_chat = discord.utils.get(ctx.guild.text_channels, name=JAIL_CHAT_NAME)
    if jail_chat:
        welcome_embed = discord.Embed(
            title="🔒  مرحباً بك في السجن",
            description=(
                f"> {member.mention}  تم إرسالك للسجن\n"
                + (f"> 📝  **السبب:**  {reason}\n" if reason else "")
                + f"{separator()}\n"
                f"> 💬  يمكنك الكلام هنا فقط\n"
                f"> 📸  ارفع أدلتك في  `#{JAIL_PROUVES_NAME}`\n"
                f"> ⏳  انتظر قرار الأدمن"
            ),
            color=COLORS["warning"],
            timestamp=discord.utils.utcnow()
        )
        welcome_embed.set_footer(text=f"{BOT_FOOTER}  •  JAIL")
        try:
            await jail_chat.send(content=member.mention, embed=welcome_embed)
        except:
            pass

    logger.info(f"🔒 {member.id} jailed by {ctx.author.id} in {ctx.guild.id}: {reason}")


@bot.command(name="unjail", aliases=["release", "free"])
@commands.check(is_admin_check)
async def unjail_cmd(ctx, member: discord.Member = None):
    """✅ !!unjail @user — فك سجن لاعب"""
    if not member:
        await ctx.send(embed=discord.Embed(
            title="❌  Missing User",
            description=f"> Usage:  `{PREFIX}unjail @user`",
            color=COLORS["error"]
        ), delete_after=15)
        return

    jail_role = discord.utils.get(ctx.guild.roles, name=JAIL_ROLE_NAME)
    if not jail_role:
        await ctx.send("❌ نظام السجن غير مُفعّل! شغّل `!!setup` أولاً.", delete_after=10)
        return

    if jail_role not in member.roles:
        await ctx.send(f"ℹ️ {member.mention} ليس في السجن!", delete_after=10)
        return

    try:
        await member.remove_roles(jail_role, reason=f"Unjailed by {ctx.author.name}")
    except (discord.Forbidden, discord.HTTPException) as e:
        await ctx.send(f"❌ لم أستطع إزالة الـ role! ({e})", delete_after=15)
        return

    # 🆕 احذف فويس السجن الخاص باللاعب
    await delete_jail_voice_for_player(ctx.guild, member)

    unjail_embed = discord.Embed(
        title="✅  تم فك السجن",
        description=(
            f"> 👤  **اللاعب:**  {member.mention}\n"
            f"> 👮  **الأدمن:**  {ctx.author.mention}\n"
            f"> 🎮  اللاعب حر الآن ويستطيع اللعب"
        ),
        color=COLORS["success"],
        timestamp=discord.utils.utcnow()
    )
    unjail_embed.set_author(name="JAIL System", icon_url=None)
    unjail_embed.set_footer(text=f"{BOT_FOOTER}  •  Released")
    unjail_embed = apply_branding(unjail_embed, ctx.guild)
    await ctx.send(embed=unjail_embed)

    logger.info(f"✅ {member.id} unjailed by {ctx.author.id} in {ctx.guild.id}")


@bot.command(name="banplayer", aliases=["ban"])
@commands.check(is_admin_check)
async def banplayer_cmd(ctx, member: discord.Member = None, *, reason: str = None):
    """🚫 !!banplayer @user [reason] — حظر لاعب يدوياً"""
    if not member:
        await ctx.send(embed=discord.Embed(
            title="❌  Missing User",
            description=f"> Usage:  `{PREFIX}banplayer @user [reason]`",
            color=COLORS["error"]
        ), delete_after=15)
        return
    if member.id == ctx.author.id:
        await ctx.send("❌ لا يمكنك حظر نفسك!", delete_after=10)
        return
    report_count = db.get_reports_count(ctx.guild.id, member.id)
    db.ban_player(ctx.guild.id, member.id, reason=reason or "Manual ban by admin", banned_by=ctx.author.id, report_count=report_count)
    # انقل لفويس التفتيش لو في فويس
    moved = False
    assigned_channel = None
    if member.voice and member.voice.channel:
        assigned_channel = await move_to_banned_channels(ctx.guild, member, assign_permanent=True)
        if assigned_channel:
            moved = True
    else:
        # 🆕 حدد فويس مقدمًا (سيُنقل لما يدخل فويس)
        admin_channel_ids = db.get_report_channels(ctx.guild.id)
        if admin_channel_ids:
            ch = ctx.guild.get_channel(admin_channel_ids[0])
            if ch and isinstance(ch, discord.VoiceChannel):
                assigned_channel = ch
                db.set_banned_voice(ctx.guild.id, member.id, ch.id)
    ban_embed = discord.Embed(
        title="🚫  تم حظر اللاعب",
        description=(
            f"> 👤  **اللاعب:**  {member.mention}\n"
            f"> 👮  **حظره:**  {ctx.author.mention}\n"
            + (f"> 📝  **السبب:**  `{reason}`\n" if reason else "")
            + f"> 📊  **عدد البلاغات السابقة:**  `{report_count}`\n"
            + (f"> 🔍  **فويس التفتيش:**  {assigned_channel.mention}\n> 🔒  **مقيّد:**  لا يمكنه مغادرة هذا الفويس" if assigned_channel else "")
        ),
        color=COLORS["error"],
        timestamp=discord.utils.utcnow()
    )
    ban_embed.set_footer(text=f"{BOT_FOOTER}  •  Banned")
    embed = apply_branding(embed, ctx.guild)
    await ctx.send(embed=ban_embed)


@bot.command(name="unbanplayer", aliases=["unban"])
@commands.check(is_admin_check)
async def unbanplayer_cmd(ctx, member: discord.Member = None):
    """✅ !!unbanplayer @user — فك حظر لاعب"""
    if not member:
        await ctx.send(embed=discord.Embed(
            title="❌  Missing User",
            description=f"> Usage:  `{PREFIX}unbanplayer @user`",
            color=COLORS["error"]
        ), delete_after=15)
        return
    ban_info = db.is_player_banned(ctx.guild.id, member.id)
    if not ban_info:
        await ctx.send(embed=discord.Embed(
            title="ℹ️  اللاعب غير محظور",
            description=f"> {member.mention}  غير محظور أصلاً.",
            color=COLORS["info"]
        ), delete_after=10)
        return
    db.unban_player(ctx.guild.id, member.id)
    db.clear_reports(ctx.guild.id, member.id)
    unban_embed = discord.Embed(
        title="✅  تم فك الحظر",
        description=(
            f"> 👤  **اللاعب:**  {member.mention}\n"
            f"> 👮  **فك الحظر:**  {ctx.author.mention}\n"
            f"> 📊  **تم مسح كل البلاغات السابقة**\n"
            f"> 🎮  اللاعب يستطيع اللعب الآن"
        ),
        color=COLORS["success"],
        timestamp=discord.utils.utcnow()
    )
    unban_embed.set_footer(text=f"{BOT_FOOTER}  •  Unbanned")
    embed = apply_branding(embed, ctx.guild)
    await ctx.send(embed=unban_embed)


@bot.command(name="banned")
@commands.check(is_admin_check)
async def banned_cmd(ctx):
    """📋 !!banned — قائمة اللاعبين المحظورين"""
    banned = db.get_banned_players(ctx.guild.id)
    embed = discord.Embed(
        title="📋  قائمة المحظورين",
        description=(
            f"> 📊  **إجمالي المحظورين:**  `{len(banned)}`\n"
            f"{separator()}"
        ),
        color=COLORS["error"] if banned else COLORS["success"],
        timestamp=discord.utils.utcnow()
    )
    embed.set_author(name="Banned Players", icon_url=None)
    if not banned:
        embed.description = "> ✅  لا يوجد لاعبون محظورون"
    else:
        for i, b in enumerate(banned[:15], 1):
            member = ctx.guild.get_member(b["user_id"])
            name = member.display_name if member else f"User#{b['user_id']}"
            mention = member.mention if member else f"<@{b['user_id']}>"
            reason = b.get("ban_reason") or "غير محدد"
            report_count = b.get("report_count", 0)
            banned_at = b.get("banned_at", "N/A")[:19] if b.get("banned_at") else "N/A"
            embed.add_field(
                name=f"#{i}  —  {name}",
                value=(
                    f"> 👤  {mention}\n"
                    f"> 📝  `{reason}`\n"
                    f"> 📊  `{report_count}` reports  •  📅  `{banned_at}`"
                ),
                inline=False
            )
        if len(banned) > 15:
            embed.set_footer(text=f"... و {len(banned) - 15} لاعب آخر")
            embed = apply_branding(embed, ctx.guild)
    await ctx.send(embed=embed)


@bot.command(name="setreportchannel", aliases=["setreportch", "addreportch"])
@commands.check(is_admin_check)
async def setreportchannel_cmd(ctx, channel: discord.VoiceChannel = None):
    """🎤 !!setreportchannel #voice — إضافة فويس لقائمة فويسات التفتيش"""
    if not channel:
        await ctx.send(embed=discord.Embed(
            title="❌  Missing Voice Channel",
            description=(
                f"> Usage:  `{PREFIX}setreportchannel <#voice_channel>`\n"
                f"> مثال:  `{PREFIX}setreportchannel #Investigation-Room`\n\n"
                f"> 💡  اذكر فويس صوتي (Voice Channel) موجود"
            ),
            color=COLORS["error"]
        ), delete_after=15)
        return
    # تأكد إنه فويس صوتي
    if not isinstance(channel, discord.VoiceChannel):
        await ctx.send(embed=discord.Embed(
            title="❌  Not a Voice Channel",
            description=f"> {channel.mention}  ليس فويس صوتي.\n> استخدم فويس صوتي (Voice Channel).",
            color=COLORS["error"]
        ), delete_after=10)
        return
    added = db.add_report_channel(ctx.guild.id, channel.id)
    all_channels = db.get_report_channels(ctx.guild.id)
    channels_list = "\n".join([
        f"›  {ctx.guild.get_channel(cid).mention}  (`{cid}`)" if ctx.guild.get_channel(cid) else f"›  ~~`{cid}`~~  (محذوف)"
        for cid in all_channels
    ]) or "> *لا توجد فويسات*"
    embed = discord.Embed(
        title="🎤  فويسات التفتيش",
        description=(
            f"> 🎤  **الفويس:**  {channel.mention}\n"
            + (f"> ✅  **تمت الإضافة** لقائمة فويسات التفتيش\n" if added else f"> ⚠️  **موجود مسبقاً** في القائمة\n")
            + f"{separator()}\n"
            f"> 📊  **إجمالي الفويسات:**  `{len(all_channels)}`\n"
            f"{channels_list}\n"
            f"> 💡  اللاعبون المحظورون سيُنقلون لهذه الفويسات تلقائياً"
        ),
        color=COLORS["success"] if added else COLORS["warning"],
        timestamp=discord.utils.utcnow()
    )
    embed.set_author(name="Report Channel Set", icon_url=None)
    embed.set_footer(text=f"{BOT_FOOTER}  •  Admin setup")
    embed = apply_branding(embed, ctx.guild)
    await ctx.send(embed=embed)


@bot.command(name="removereportchannel", aliases=["delreportch", "rmreportch"])
@commands.check(is_admin_check)
async def removereportchannel_cmd(ctx, channel: discord.VoiceChannel = None):
    """🗑️ !!removereportchannel #voice — حذف فويس من قائمة التفتيش"""
    if not channel:
        await ctx.send(embed=discord.Embed(
            title="❌  Missing Voice Channel",
            description=f"> Usage:  `{PREFIX}removereportchannel <#voice_channel>`",
            color=COLORS["error"]
        ), delete_after=15)
        return
    removed = db.remove_report_channel(ctx.guild.id, channel.id)
    all_channels = db.get_report_channels(ctx.guild.id)
    channels_list = "\n".join([
        f"›  {ctx.guild.get_channel(cid).mention}  (`{cid}`)" if ctx.guild.get_channel(cid) else f"›  ~~`{cid}`~~  (محذوف)"
        for cid in all_channels
    ]) or "> *لا توجد فويسات — سيتم إنشاء فويسات تلقائية عند الحظر*"
    embed = discord.Embed(
        title="🗑️  حذف فويس التفتيش",
        description=(
            f"> 🎤  **الفويس:**  {channel.mention}\n"
            + (f"> ✅  **تم الحذف** من القائمة\n" if removed else f"> ⚠️  **غير موجود** في القائمة\n")
            + f"{separator()}\n"
            f"> 📊  **الفويسات المتبقية:**  `{len(all_channels)}`\n"
            f"{channels_list}"
        ),
        color=COLORS["success"] if removed else COLORS["warning"],
        timestamp=discord.utils.utcnow()
    )
    embed.set_author(name="Report Channel Removed", icon_url=None)
    embed.set_footer(text=f"{BOT_FOOTER}  •  Admin setup")
    embed = apply_branding(embed, ctx.guild)
    await ctx.send(embed=embed)


@bot.command(name="reportchannels", aliases=["reportch", "listreportch"])
@commands.check(is_admin_check)
async def reportchannels_cmd(ctx):
    """📋 !!reportchannels — عرض كل فويسات التفتيش المحددة"""
    all_channels = db.get_report_channels(ctx.guild.id)
    embed = discord.Embed(
        title="📋  فويسات التفتيش المحددة",
        description=(
            f"> 📊  **إجمالي الفويسات:**  `{len(all_channels)}`\n"
            + (f"> ⚠️  **لا توجد فويسات محددة** — سيتم إنشاء فويسات تلقائية عند الحظر\n" if not all_channels else "")
            + f"{separator()}"
        ),
        color=COLORS["info"],
        timestamp=discord.utils.utcnow()
    )
    embed.set_author(name="Report Channels List", icon_url=None)
    if all_channels:
        for i, cid in enumerate(all_channels, 1):
            ch = ctx.guild.get_channel(cid)
            if ch:
                members_count = len(ch.members) if hasattr(ch, 'members') else 0
                embed.add_field(
                    name=f"#{i}  —  {ch.name}",
                    value=f"> 🎤  {ch.mention}\n> 📊  `{members_count}` members",
                    inline=False
                )
            else:
                embed.add_field(
                    name=f"#{i}  —  ⚠️ محذوف",
                    value=f"> ❌  Channel ID:  `{cid}`  غير موجود\n> 💡  استخدم  `{PREFIX}removereportchannel`  لتنظيف القائمة",
                    inline=False
                )
    embed.set_footer(text=f"{BOT_FOOTER}  •  Use !!setreportchannel to add")
    embed = apply_branding(embed, ctx.guild)
    await ctx.send(embed=embed)


@bot.command(name="resolve")
@commands.check(is_admin_check)
async def resolve_cmd(ctx, lobby_id: int = None, winner: str = None):
    if lobby_id is None or winner is None:
        await ctx.send(embed=discord.Embed(
            title="❌  Missing",
            description=(
                f"> Usage:  `{PREFIX}resolve <id> <team1|team2>`"
            ),
            color=COLORS["error"]
        ))
        return
    winner = winner.lower()
    if winner not in ["team1", "team2"]:
        await ctx.send(embed=discord.Embed(
            title="❌  Invalid",
            description=(
                f"> Winner must be  `team1`  or  `team2`."
            ),
            color=COLORS["error"]
        ))
        return
    lobby = db.get_lobby(lobby_id)
    if not lobby or lobby["status"] != "voting":
        await ctx.send(embed=discord.Embed(
            title="❌  No Dispute",
            description=(
                f"> Lobby `#{lobby_id}` is not in voting status."
            ),
            color=COLORS["error"]
        ))
        return
    await ctx.send(embed=discord.Embed(
        title="⚖️  Resolved!",
        description=(
            f"> **{ctx.author.mention}**  decided the winner:\n"
            f"> **{'🟠 Team 1' if winner=='team1' else '🟢 Team 2'}**"
        ),
        color=COLORS["success"]
    ))
    await process_match_result(ctx.guild, lobby_id, winner, ctx.channel)


@bot.command(name="resetstats")
@commands.check(is_admin_check)
async def resetstats_cmd(ctx, member: discord.Member = None):
    if not member:
        await ctx.send(embed=discord.Embed(
            title="❌  Missing User",
            description=(
                f"> Usage:  `{PREFIX}resetstats @user`"
            ),
            color=COLORS["error"]
        ))
        return
    db.reset_stats(member.id, ctx.guild.id)
    await update_member_nickname(member, STARTING_LEVEL)
    await ctx.send(embed=discord.Embed(
        title="✅  Stats Reset",
        description=(
            f"> {member.mention}  —  RANK  `#{STARTING_LEVEL}`\n"
            f"> All stats have been reset to default."
        ),
        color=COLORS["success"]
    ))


# 🆕 إعادة تعيين الرانك + النقاط لكل أعضاء السيرفر إلى الصفر
@bot.command(name="resetrankall", aliases=["forceresetrankall", "resetallranks"])
@commands.check(is_admin_check)
async def resetrankall_cmd(ctx):
    """🏅 !!resetrankall — تصفير النقاط والرانك لكل أعضاء السيرفر"""
    guild = ctx.guild
    progress = await ctx.send(embed=discord.Embed(
        title="🚀  جارٍ تصفير النقاط والرانك...",
        description=(
            f"> 📊  **عدد الأعضاء:**  `{len(guild.members)}`\n"
            f"> 💰  **سيتم تصفير:**  النقاط + الرانك\n"
            f"> 🏅  **الرانك المستهدف:**  `#{STARTING_LEVEL}`  (نقاط = 0)\n"
            f"> ⏳  **انتظر...**"
        ),
        color=COLORS["warning"],
        timestamp=discord.utils.utcnow()
    ).set_footer(text=f"{BOT_FOOTER}  •  Server-wide reset"))
    reset_count = 0
    skipped_bots = 0
    failed = 0
    for member in guild.members:
        if member.bot:
            skipped_bots += 1
            continue
        try:
            # أنشئ اللاعب إن لم يكن موجوداً
            db.get_or_create_player(member.id, guild.id, member.display_name)
            # 🆕 صفّر النقاط + الرانك معاً
            db.update_player_stats(
                member.id, guild.id,
                points=0,
                level=STARTING_LEVEL,
                wins=0,
                losses=0,
                kills=0,
                mvps=0,
                matches_played=0,
                win_streak=0,
                lose_streak=0,
                max_win_streak=0
            )
            # حدّث النك نيم
            await update_member_nickname(member, STARTING_LEVEL)
            reset_count += 1
            await asyncio.sleep(0.3)
        except Exception as e:
            logger.warning(f"resetrankall: failed for {member.id}: {e}")
            failed += 1
    await progress.edit(embed=discord.Embed(
        title="✅  تم تصفير كل البيانات!",
        description=(
            f"> 🏅  كل الأعضاء تم تصفيرهم إلى  `RANK #{STARTING_LEVEL}`  (نقاط = 0)\n"
            f"{separator()}\n"
            f"> ✅  **تم التصفير:**  `{reset_count}`\n"
            f"> 🤖  **تم تخطي البوتات:**  `{skipped_bots}`\n"
            f"> ⚠️  **فشل:**  `{failed}`\n"
            f"> 💡  كل الستاتس (نقاط/فوز/خسارة/MVPs) صفرت أيضاً"
        ),
        color=COLORS["success"],
        timestamp=discord.utils.utcnow()
    ).set_footer(text=f"{BOT_FOOTER}  •  Reset complete"))
    logger.info(f"🏅 resetrankall: {reset_count} members fully reset to {STARTING_LEVEL} (points=0) in {guild.id}")


@bot.command(name="setlevel")
@commands.check(is_admin_check)
async def setlevel_cmd(ctx, member: discord.Member = None, level: int = None):
    if not member or level is None:
        await ctx.send(embed=discord.Embed(
            title="❌  Missing",
            description=(
                f"> Usage:  `{PREFIX}setlevel @user <level>`"
            ),
            color=COLORS["error"]
        ))
        return
    if level < 1 or level > 9999:
        await ctx.send(embed=discord.Embed(
            title="❌  Invalid Level",
            description=(
                f"> Level must be between  `1`  and  `9999`."
            ),
            color=COLORS["error"]
        ))
        return
    db.get_or_create_player(member.id, ctx.guild.id, member.display_name)
    db.update_player_stats(member.id, ctx.guild.id, level=level)
    await update_member_nickname(member, level)
    await ctx.send(embed=discord.Embed(
        title="✅  Level Updated",
        description=(
            f"> {member.mention}  →  **RANK  `#{level}`**"
        ),
        color=COLORS["success"]
    ))


@bot.command(name="syncnicknames")
@commands.check(is_admin_check)
async def syncnicknames_cmd(ctx):
    guild = ctx.guild
    updated = 0
    for member in guild.members:
        if member.bot: continue
        player = db.get_or_create_player(member.id, guild.id, member.display_name)
        await update_member_nickname(member, player.get("level", STARTING_LEVEL))
        updated += 1
        await asyncio.sleep(0.3)
    await ctx.send(embed=discord.Embed(
        title="✅  Synced",
        description=(
            f"> Synced  `{updated}`  members' nicknames successfully."
        ),
        color=COLORS["success"]
    ))


@bot.command(name="syncroles", aliases=["syncranks", "updateroles"])
@commands.check(is_admin_check)
async def syncroles_cmd(ctx):
    """🔄 !!syncroles — مزامنة الـ Roles لكل اللاعبين حسب ترتيبهم"""
    progress = await ctx.send(embed=discord.Embed(
        title="🔄  جارٍ مزامنة الـ Roles...",
        description=(
            f"> 📊  جاري تحديث ألقاب كل اللاعبين حسب ترتيبهم...\n"
            f"> ⏳  انتظر..."
        ),
        color=COLORS["warning"],
        timestamp=discord.utils.utcnow()
    ))
    # أعِد حساب الرانكات أولاً
    db.recalculate_ranks(ctx.guild.id)
    # يزامن الـ Roles
    await sync_all_players_roles(ctx.guild)
    await progress.edit(embed=discord.Embed(
        title="✅  تمت مزامنة الـ Roles!",
        description=(
            f"> 🔄  كل اللاعبين تم تحديث ألقابهم حسب ترتيبهم.\n"
            f"{separator()}\n"
            f"> 🏆  **#1:**  Best Player\n"
            f"> 💎  **#2-10:**  Goated Players  (SoundBoard + Waiting Prv)\n"
            f"> ⭐  **#11-50:**  Skilled Players  (SoundBoard)\n"
            f"> 🎯  **#51-100:**  Efficient Players"
        ),
        color=COLORS["success"],
        timestamp=discord.utils.utcnow()
    ).set_footer(text=f"{BOT_FOOTER}  •  Roles synced"))


# ============================================================
# HELP COMMANDS
# ============================================================

@bot.command(name="rules")
async def rules_cmd(ctx):
    """📜 !!rules — عرض قواعد السيرفر"""
    rules_embed = discord.Embed(
        title="📜  قواعد السيرفر",
        description=(
            f"> مرحباً بك في  **{ctx.guild.name}**  🔥\n"
            f"> يرجى الالتزام بالقواعد التالية:\n"
            f"{separator()}\n"
            f"> **1️⃣  الاحترام المتبادل**\n"
            f"> ─  احترم جميع اللاعبين والأدمنز.\n"
            f"> ─  ممنوع السب، الشتم، أو الإساءة.\n\n"
            f"> **2️⃣  قواعد اللعب**\n"
            f"> ─  ادخل غرفة انتظار قبل اللعب.\n"
            f"> ─  استخدم  `{PREFIX}play 4v4`  لبدء ماتش.\n"
            f"> ─  التزم بنتيجة التصويت.\n\n"
            f"> **3️⃣  عدم الغش**\n"
            f"> ─  ممنوع التلاعب بالتصويت.\n"
            f"> ─  ممنوع مغادرة الماتش في المنتصف.\n\n"
            f"> **4️⃣  استخدام الأوامر**\n"
            f"> ─  الأوامر تعمل فقط في قنوات play.\n"
            f"> ─  انتظر الـ cooldown قبل التكرار.\n\n"
            f"> **5️⃣  العقوبات**\n"
            f"> ─  مخالفة القواعد = تحذير / كتم / طرد.\n"
            f"> ─  القرار النهائي للأدمن.\n\n"
            f"> 💬  لأي استفسار، تواصل مع الأدمن."
        ),
        color=COLORS["warning"],
        timestamp=discord.utils.utcnow()
    )
    rules_embed.set_author(name="Server Rules", icon_url=None)
    rules_embed.set_footer(text=f"{BOT_FOOTER}  •  Read carefully")
    if RULES_IMAGE_URL:
        rules_embed.set_image(url=RULES_IMAGE_URL)
    elif ctx.guild.icon:
        rules_embed.set_image(url=ctx.guild.icon.url)
    await ctx.send(embed=rules_embed)


@bot.command(name="general")
async def general_cmd(ctx):
    embed = discord.Embed(
        title="🎮  Player Commands",
        description=(
            f"> 📌  **Prefix:**  `{PREFIX}`\n"
            f"──────────────────────"
        ),
        color=0xFF6B00
    )
    embed.add_field(name="🚀  Play", value=(
        f"›  `{PREFIX}play 4v4`  أو  `{PREFIX}play4v4`  —  4v4  (الافتراضي)\n"
        f"›  `{PREFIX}play 2v2`  أو  `{PREFIX}play2v2`  —  2v2\n"
        f"›  `{PREFIX}play 3v3`  أو  `{PREFIX}play3v3`  —  3v3\n"
        f"›  `{PREFIX}play 1v1`  أو  `{PREFIX}play1v1`  🔒  (للـ roles العالية)\n"
        f"›  ⚠️  `{PREFIX}play`  بدون مود  →  رسالة خطأ"
    ), inline=False)
    embed.add_field(name="📊  Stats", value=(
        f"›  `{PREFIX}p`  —  Profile (full stats)\n"
        f"›  `{PREFIX}points`  —  💰 نقاطك + تقدم الرانك\n"
        f"›  `{PREFIX}card`  —  Card  (zelika-play)\n"
        f"›  `{PREFIX}top`  —  Leaderboard (Top 10)\n"
        f"›  `{PREFIX}mylevel`  —  Your rank\n"
        f"›  `{PREFIX}matches`  —  Active lobbies"
    ), inline=False)
    embed.add_field(name="🎮  Control", value=(
        f"›  `{PREFIX}leave`  —  Leave lobby\n"
        f"›  `{PREFIX}fixrank`  —  Apply rank"
    ), inline=False)
    embed.add_field(name="🤖  How to Play", value=(
        f"> 1️⃣  Join a ⏳ waiting room\n"
        f"> 2️⃣  `{PREFIX}play 4v4`  in a play channel  (حدد المود!)\n"
        f"> 3️⃣  Press **Create Lobby**  →  Enter Room Info\n"
        f"> 4️⃣  Players press **Join Team 1 / 2**\n"
        f"> 5️⃣  Lobby fills  →  Match starts\n"
        f"> 6️⃣  Host presses **Start Vote**  (or **Cancel Match** to abort)\n"
        f"> 7️⃣  Vote  →  Result  →  Points + RANK updates\n"
        f"> 8️⃣  Players return to waiting rooms\n"
        f"\n"
        f"> 💰  **نظام النقاط:**\n"
        f"> ─  👑  Winner MVP:  `+80` pts\n"
        f"> ─  ✅  Winners:  `+30` pts\n"
        f"> ─  🌟  Loser MVP:  `+30` pts\n"
        f"> ─  💀  Losers:  `-30` pts\n"
        f"> ─  📈  كل `50` نقطة = `+1` رانك"
    ), inline=False)
    embed.set_footer(text=f"Free Fire Bot v4.0  •  {PREFIX}help (admin)")
    embed = apply_branding(embed, ctx.guild)
    await ctx.send(embed=embed)


@bot.command(name="help")
async def help_cmd(ctx):
    # 🆕 رسالة 1: أوامر اللاعبين
    embed1 = discord.Embed(
        title="🔥  Free Fire Bot v4.0  —  Player Commands",
        description=(
            f"> 📌  **Prefix:**  `{PREFIX}`\n"
            f"──────────────────────"
        ),
        color=0xFF6B00
    )
    embed1.add_field(name="🎮  Play", value=(
        f"›  `{PREFIX}play 4v4`  أو  `{PREFIX}play4v4`  —  4v4  (الافتراضي)\n"
        f"›  `{PREFIX}play 1v1`  أو  `{PREFIX}play1v1`  —  1v1  🔒  (للـ roles العالية)\n"
        f"›  `{PREFIX}play 2v2`  أو  `{PREFIX}play2v2`  —  2v2\n"
        f"›  `{PREFIX}play 3v3`  أو  `{PREFIX}play3v3`  —  3v3\n"
        f"›  ⚠️  `{PREFIX}play`  بدون مود  →  رسالة خطأ"
    ), inline=False)
    embed1.add_field(name="📊  Stats", value=(
        f"›  `{PREFIX}p`  —  Your profile (full stats)\n"
        f"›  `{PREFIX}p @user`  —  Other profile\n"
        f"›  `{PREFIX}points`  —  💰 نقاطك + تقدم الرانك\n"
        f"›  `{PREFIX}card`  —  Card (zelika-play only)\n"
        f"›  `{PREFIX}card @user`  —  Other card\n"
        f"›  `{PREFIX}top`  —  Leaderboard Top 10 (Points + Rank)\n"
        f"›  `{PREFIX}mylevel`  —  Your rank\n"
        f"›  `{PREFIX}myrank`  —  Target nickname\n"
        f"›  `{PREFIX}matches`  —  Active lobbies\n"
        f"›  `{PREFIX}matchinfo <id>`  —  Match details"
    ), inline=False)
    embed1.add_field(name="🎮  Control", value=(
        f"›  `{PREFIX}leave`  —  Leave lobby\n"
        f"›  `{PREFIX}fixrank`  —  Apply rank to name\n"
        f"›  `{PREFIX}fixrank @user`  —  Apply to other"
    ), inline=False)
    embed1.set_footer(text=f"Page 1/2  •  {PREFIX}help for admin commands")
    await ctx.send(embed=embed1)

    # 🆕 رسالة 2: أوامر الأدمن
    embed2 = discord.Embed(
        title="🔧  Free Fire Bot v4.0  —  Admin Commands",
        description=(
            f"> 📌  **Prefix:**  `{PREFIX}`\n"
            f"──────────────────────"
        ),
        color=0xE74C3C
    )
    embed2.add_field(name="🔧  Setup & Channels", value=(
        f"›  `{PREFIX}setup`  —  Create all channels\n"
        f"›  `{PREFIX}cleanup`  —  Delete match categories\n"
        f"›  `{PREFIX}setcommandschannel #ch`  —  Add/remove command channel\n"
        f"›  `{PREFIX}setleaderboard`  —  Set leaderboard channel"
    ), inline=False)
    embed2.add_field(name="🔍  Scan & Delete", value=(
        f"›  `{PREFIX}scan`  —  List all categories\n"
        f"›  `{PREFIX}scan 2`  —  Page 2\n"
        f"›  `{PREFIX}deletecat <name>`  —  Mark category for deletion\n"
        f"›  `{PREFIX}confirmcat <name>`  —  Confirm deletion"
    ), inline=False)
    embed2.add_field(name="🏅  Ranks", value=(
        f"›  `{PREFIX}fixrankall`  —  Apply ranks to ALL members\n"
        f"›  `{PREFIX}syncnicknames`  —  Sync all nicknames\n"
        f"›  `{PREFIX}setlevel @user <n>`  —  Set level (1-9999)\n"
        f"›  `{PREFIX}resetstats @user`  —  Reset player stats\n"
        f"›  `{PREFIX}resetrankall`  —  Reset ALL ranks to 1000 (server-wide)"
    ), inline=False)
    embed2.add_field(name="⚖️  Match Admin", value=(
        f"›  `{PREFIX}resolve <id> <team1|team2>`  —  Resolve vote dispute"
    ), inline=False)
    embed2.add_field(name="ℹ️  Info", value=(
        f"›  `{PREFIX}general`  —  Player guide (any channel)\n"
        f"›  `{PREFIX}help`  —  This message (any channel)\n"
        f"›  `{PREFIX}botinfo`  —  Bot info"
    ), inline=False)
    embed2.set_footer(text=f"Page 2/2  •  Free Fire Bot v4.0 CLEAN  •  30 commands")
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
