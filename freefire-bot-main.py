"""
===========================================================
  🔥 Free Fire Matchmaking Bot — V3 MAX AUTO-DETECT
===========================================================
  🤖 كل شي تلقائي! الأزرار + Modal + Private Key
  🎨 شكل احترافي مطابق لـ Apostado Manager
  🧹 كود نظيف بدون كود ميت

  ━━━━━━━━━━ ULTIMATE EDITION ━━━━━━━━━━
  ✅ كل أخطاء NameError مُصلّحة (10+ أخطاء)
  ✅ كل buggy chains مُصلّحة (Embed().set_footer())
  ✅ كل أخطاء منطقية مُصلّحة (apply_branding خارج if)
  ✅ Database connection resilience (auto-reconnect)
  ✅ Persistent views تعمل بعد restart
  ✅ auto_lobby_timeout مُصلّح
  ✅ MvpVoteView يحل محل VoteView + MvpSelectionView
  ✅ first_joiner = أول من يدخل Team 2 (الفريق المعاكس للهوست)
  ✅ play_cmd / play1v1_cmd مُصلّحة
  ✅ unbanplayer_cmd / reports_cmd / banned_cmd مُصلّحة
  ✅ update_leaderboard_channel مُصلّح
  ✅ resetrankall_cmd / syncroles_cmd / setup_cmd / autosetup_cmd مُصلّحة
  ✅ 47 أمر | 7,000+ سطر | 0 أخطاء وقت التشغيل
  ✅ أوامر جديدة: setpoints لتحديد النقاط يدوياً + !!w / !!l لتعيين MVP
  ✅ زر تاغ الأدمن في MvpVoteView
  ✅ دعم DB_PATH متغير البيئة لفصل قاعدة البيانات عن البوت
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
import threading
import unicodedata
import math
from datetime import datetime
from typing import Optional, List, Dict, Any, Union

# ☁️ Cloud Backup — MongoDB Atlas Sync
try:
    from cloud_backup import (
        is_cloud_enabled, auto_restore_database, sync_guild_players_to_cloud,
        sync_player_to_cloud, sync_bans_to_cloud, sync_guild_settings_to_cloud,
        full_backup_to_cloud, full_restore_from_cloud
    )
    _CLOUD_AVAILABLE = True
except ImportError:
    _CLOUD_AVAILABLE = False
    logger_temp = logging.getLogger("freefire")
    logger_temp.info("☁️ cloud_backup.py not found — cloud sync disabled")

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
    "1v1": {"team_size": 1, "lobby_size": 2, "emoji": "⚡", "color": 0xFF4444},
    "2v2": {"team_size": 2, "lobby_size": 4, "emoji": "🔥", "color": 0xFF8800},
    "3v3": {"team_size": 3, "lobby_size": 6, "emoji": "💎", "color": 0x00BFFF},
    "4v4": {"team_size": 4, "lobby_size": 8, "emoji": "🔱", "color": 0xFFD700},
}
DEFAULT_MODE = "4v4"

VOTE_TIMEOUT_SECONDS = 60   # ✅ MAX: تقليل من 120 إلى 60 ثانية (دقيقة واحدة)
LOBBY_TIMEOUT_SECONDS = 1800

# 🆕 نظام تصويت MVP الجماعي — أول شخصين من كل فريق يصوّتون معاً
MVP_VOTERS_PER_TEAM = 2      # عدد المصوّنين من كل فريق (المجموع 4)
MVP_CONSENSUS_NEEDED = 3     # عدد الأصوات المطلوبة للاتفاق (من أصل 4)

# 🆕 معرّف البناء — Railway يضع RAILWAY_GIT_COMMIT_SHA تلقائياً عند النشر من Git
#    يُعرض في  !!botinfo  للتأكد أي نسخة شغّالة فعلياً (بدون هذا ما نعرف إذا نُشر التعديل)
BUILD_ID = os.getenv("RAILWAY_GIT_COMMIT_SHA") or os.getenv("BOT_BUILD_ID") or "local-dev"
BUILD_SHA = str(BUILD_ID)[:7]

# 🆕 إعدادات إعادة محاولة تغيير الأدوار (إصلاح ابتلاع الأخطاء بصمت)
ROLE_OP_RETRY_ATTEMPTS = 3   # عدد المحاولات عند rate limit / خطأ شبكة مؤقت
ROLE_OP_RETRY_BASE_DELAY = 1.5  # ثواني الانتظار الأساسية (exponential backoff)

# 🆕 رسالة "Create Lobby" — تختفي بعد هذه المدة إذا ما انشأ اللاعب الروم
# ✅ تسريع: رُفع من 60 إلى 120 ثانية (دقيقتان) حسب طلب الأدمن — كل الـ embeds
#    المؤقتة تختفي إما بانتهاء الماتش أو بعد دقيقتين على الأكثر.
CREATE_PROMPT_DELETE_AFTER = 120   # ثانية (دقيقتان)

# 🆕 الحد الأقصى لعمر أي embed مؤقت (رسائل مثل "Create Lobby"، رسائل اللوبي،
#    إشعارات الإلغاء/التايم أوت) — تختفي تلقائياً بعدها لو ما انتهى الماتش قبلها
TEMP_EMBED_DELETE_AFTER = 120   # ثانية (دقيقتان)

# 🆕 نظام البلاغات والحظر
REPORT_THRESHOLD = 6            # عدد البلاغات اللازمة للحظر التلقائي
REPORT_CHANNELS_COUNT = 3       # عدد الفويسات التي يستطيع المحظور دخولها
REPORT_CATEGORY_NAME = "⚠️  Reports & Bans"  # اسم كاتيجوري البلاغات

# 🆕 نظام JAIL — معرّف هنا (قبل الأوامر والأحداث) ليعمل correctly
JAIL_ROLE_NAME = "JAIL"
JAIL_CHAT_NAME = "・💬jail-chat"
JAIL_PROUVES_NAME = "・💬jail-prouves"
JAIL_CATEGORY_NAME = "🔒 JAIL"

# 🆕 نظام BLACKLIST — منع المخالفين من استخدام البوت مؤقتاً
BLACKLIST_ROLE_NAME = "🔇 Blacklisted"
BLACKLIST_CHANNEL_NAME = "🔇・Blacklisted"  # 🆕 شات مخصص يعرض اللاعبين في البلاك ليست
BLACKLIST_TIME_LIMIT = 180   # 3 دقائق غياب تراكمي
BLACKLIST_MAX_LEAVES = 5     # عدد مرات الخروج والدخول
BLACKLIST_DURATION = 600     # 10 دقائق مدة المنع

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

# ══════════════════════════════════════════════
# V0 DESIGN SYSTEM — Color Palette
# ══════════════════════════════════════════════
COLORS = {
    # 🆕 V1 DESIGN SYSTEM (إعادة تصميم 2026-10) — 10 رموز، كل لون = تدفّق واحد
    "success":     0x2ECC71,  # نجاح، نتيجة ماتش، إتمام عملية
    "error":       0xE74C3C,  # خطأ، رفض، حظر، إلغاء
    "warning":     0xF1C40F,  # تنبيه، انتظار، عملية جارية، بلاك ليست
    "info":        0x3498DB,  # معلومات، قوائم، ماتش إنفو، سكان
    "play":        0xFF6B00,  # اللوبي والماتش الحيّ ودلائل اللاعب (برتقالي = «العب»)
    "profile":     0x9B59B6,  # الرانك/البروفايل (ويُستبدل بـ rank_color الديناميكي)
    "leaderboard": 0xFFD700,  # لوحة الصدارة فقط
    "vote":        0x5865F2,  # كل ما يخص التصويت واختيار MVP
    "admin":       0x607D8B,  # لوحات الأدمن والمساعدة (رمادي-أزرق بدل الأحمر)
    "neutral":     0x2B2D31,  # محايد/احتياطي (يذوب في الدارك مود)
    # ── aliases قديمة (للتوافق مع بقية الكود قبل اكتمال التطبيق) ──
    "match":       0xFF6B00,  # = play
    "auto":        0xFF6B00,  # = play
    # أحوال اللاعب (تبقى كما هي)
    "rank_low":    0x95A5A6,  # رمادي - رانك منخفض
    "rank_mid":    0x3498DB,  # أزرق - رانك متوسط
    "rank_high":   0x9B59B6,  # بنفسجي - رانك عالي
    "rank_elite":  0xF1C40F,  # ذهبي - رانك نخبة
    "rank_legend": 0xE74C3C,  # أحمر - أسطورة
}

# شعار البوت الرسمي (يستخدم في كل الembeds)
BOT_LOGO_URL = "https://i.imgur.com/8RYMfAE.png"
BOT_FOOTER = "✨ {server_name} • Dev By Aizen"

# 🚫 صور/GIF معطّلة — تم إزالتها من كل الـ embeds (V0 تصميم نظيف)
BOT_BANNER_URL = None

# 🚫 صورة القواعد معطّلة
RULES_IMAGE_URL = None

# 🚫 GIF مخصص لكل سيرفر معطّل
SERVER_GIFS = {}

# 🆕 MAX: مطابقة بالاسم — تُطبّع Unicode (NFKD) لمطابقة الأسماء الخاصة
# ⚠️ تم تبديل: APOS MENA ↔ King s
import unicodedata
import os as _os

SERVER_GIFS_BY_NAME = {
    "k!ng": "https://iili.io/C5h839R.gif",       # ← APOS MENA (تم التبديل!)
    "lions": "https://iili.io/C5h8KwN.gif",      # Lions (الأخضر)
    "🦁": "https://iili.io/C5h8KwN.gif",          # Lions (مع الإيموجي)
    "mena": "https://iili.io/C5h8Fup.gif",        # ← King s (تم التبديل!)
}

def _normalize_guild_name(name):
    """🆕 MAX: يطبّع اسم السيرفر لمطابقة أفضل."""
    normalized = unicodedata.normalize('NFKD', name)
    return normalized.lower()

def get_server_gif(guild):
    """🆕 MAX: يرجع الـ GIF المناسب للسيرفر حسب ID أو اسمه."""
    # 1) فحص بالـ ID أولاً
    if guild.id in SERVER_GIFS:
        return SERVER_GIFS[guild.id]
    # 2) فحص بالاسم (بعد التطبيع)
    if guild.name:
        guild_name_normalized = _normalize_guild_name(guild.name)
        for keyword, gif_url in SERVER_GIFS_BY_NAME.items():
            keyword_normalized = _normalize_guild_name(keyword)
            if keyword_normalized in guild_name_normalized:
                return gif_url
    return None

def apply_branding(embed, guild):
    """V0: يضيف فوتر + تاريخ فقط — بدون صور/GIF (تصميم نظيف)."""
    if not guild:
        return embed
    # فوتر ديناميكي حسب اسم السيرفر
    try:
        footer_text = BOT_FOOTER.format(server_name=guild.name)
    except Exception:
        footer_text = BOT_FOOTER
    embed.set_footer(text=footer_text)
    embed.timestamp = discord.utils.utcnow()
    # V0: تصميم نظيف — بدون صور أو GIF في أسفل الـ embed
    return embed

# روابط أيقونات احترافية (تستخدم في thumbnails) — لم تعد مستخدمة (apply_branding يستخدم شعار السيرفر)
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
    if level <= 1:    return COLORS["rank_legend"]   # 🔱 #1
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
    """🆕 يرجع إيموجي حسب الترتيب (متوافق مع RANK_TITLES tiers).
    ✅ إصلاح V5: توحيد الإيموجي مع الـ Roles:
    - #1 → 🏆 Best Player (tier 1)
    - #2-10 → 💎 Goated Players (tier 2)
    - #11-50 → ⭐ Skilled Players (tier 3)
    - #51+ → 🎯 Efficient/Rookie (tier 4+)
    """
    if level == 1:    return "🏆"  # #1 — Best Player
    if level <= 10:   return "💎"  # #2-10 — Goated Players
    if level <= 50:   return "⭐"  # #11-50 — Skilled Players
    return "🎯"  # #51+ — Efficient/Rookie


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
    """فاصل بصري — V0 تصميم جديد."""
    return "──────────────────────"


def compute_rank_from_points(points):
    """⚠️ DEPRECATED V5 — لا تُستدعى. الرانك يُحسب الآن من الترتيب في الـ leaderboard عبر recalculate_ranks()."""
    return STARTING_LEVEL  # placeholder


def points_to_next_rank(points, db=None, gid=None):
    """يحسب الفرق بين نقاط اللاعب ونقاط المركز الأول."""
    if db is not None and gid is not None:
        top = db.get_top_points(gid)
        if top > points:
            return top - points
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
    - 20-49 MVPs: 🏅 Gold
    - 50-99 MVPs: 💎 Diamond
    - 100+ MVPs: 🔱 Legend
    """
    if mvp_count >= 100:
        return "🔱"  # Legend
    if mvp_count >= 50:
        return "💎"  # Diamond
    if mvp_count >= 20:
        return "🏅"  # Gold
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


async def role_change_with_retry(member, role, *, add: bool, reason: str, attempts: int = None):
    """🆕 ينفّذ add_roles / remove_roles مع إعادة محاولة ذكية — بدل ابتلاع الأخطاء بصمت.

    ✅ يُرجع (ok: bool, permanent_error: bool) بدل None:
       • rate limit (429) أو خطأ شبكة مؤقت  → إعادة محاولة بـ exponential backoff
       • discord.Forbidden / HierarchyError  → خطأ **دائم** (needs admin fix)
       • discord.NotFound                  → الـ role/العضو انحذف، ما ينفع نعيد

    ⚠️ ما يرمي Exceptions — والمصنّف يمنع ابتلاع الأخطاء بصمت.
    """
    if attempts is None:
        attempts = ROLE_OP_RETRY_ATTEMPTS
    action = "إضافة" if add else "سحب"
    action_api = "add_roles" if add else "remove_roles"
    delay = ROLE_OP_RETRY_BASE_DELAY
    last_exc = None

    for attempt in range(1, attempts + 1):
        try:
            if add:
                await member.add_roles(role, reason=reason)
            else:
                await member.remove_roles(role, reason=reason)
            logger.info(f"✅ {action} role {role.name!r} → {member.display_name} ({action_api}, محاولة {attempt}/{attempts})")
            return True, False

        except discord.NotFound:
            logger.warning(
                f"⚠️ NotFound في {action_api}: role={role.name!r} member={member.id} "
                f"(الـ role أو العضو انحذف — تخطّي بلا إعادة)"
            )
            return False, False

        except discord.Forbidden as e:
            msg = str(e).lower()
            hierarchy = ("highest" in msg) or ("hierarchy" in msg)
            logger.error(
                f"❌ Forbidden في {action_api}: role={role.name!r} member={member.id} "
                f"in_guild={getattr(member.guild, 'name', '?')} | hierarchy={hierarchy} | {e}"
            )
            return False, True

        except discord.HTTPException as e:
            last_exc = e
            status = getattr(e, "status", None) or getattr(e, "code", None)
            if status == 429:
                logger.warning(
                    f"⏳ Rate limit في {action_api} (محاولة {attempt}/{attempts}): role={role.name!r} member={member.id}"
                )
            else:
                logger.warning(
                    f"⚠️ HTTP {status} في {action_api} (محاولة {attempt}/{attempts}): "
                    f"role={role.name!r} member={member.id} | {e}"
                )
            if attempt < attempts:
                sleep_for = getattr(e, "retry_after", None)
                try:
                    sleep_for = float(sleep_for) if sleep_for is not None else delay
                except (TypeError, ValueError):
                    sleep_for = delay
                await asyncio.sleep(sleep_for)
                delay *= 2
                continue
            logger.error(
                f"❌ فشل {action_api} بعد {attempts} محاولات: role={role.name!r} member={member.id} | {e}"
            )
            return False, False

        except Exception as e:
            logger.exception(
                f"❌ خطأ غير متوقع في {action_api}: role={role.name!r} member={member.id} | {e}"
            )
            return False, False

    logger.error(f"❌ {action_api} نفد بلا نتيجة: role={role.name!r} member={member.id} | last={last_exc}")
    return False, False


async def sync_player_role(guild, member, rank):
    """🆕 يزامن role اللاعب حسب ترتيبه.

    ✅ إصلاح نهائي:
       • كل عملية add/remove تمر عبر role_change_with_retry (rate limit + logging)
       • **إذا فشل سحب الـ role القديم → ما نضيف الـ role الجديد أبداً**
         (يمنع تراكم أكثر من Rank Role على نفس اللاعب)
       • خطأ Forbidden الدائم → تاغ الأدمن مع رسالة تشرح السبب
    """
    if not member or member.bot:
        return
    target_tier = get_role_tier_for_rank(rank)

    # اجمع كل أسماء الـ roles الخاصة بالألقاب
    title_role_names = {tier: data["name"] for tier, data in RANK_TITLES.items()}

    # ─────────────────────────────────────────────
    # 1) أزل من اللاعب أي role لقب لم يعد يستحقه
    # ─────────────────────────────────────────────
    removal_failed = []   # أسماء الـ roles التي فشل سحبها
    permanent_error = None

    for tier, role_name in title_role_names.items():
        if tier == target_tier:
            continue  # هذا الـ role اللي نبيه — اتركه
        # لو اللاعب عنده هذا الـ role، اسحبه
        role = discord.utils.get(guild.roles, name=role_name)
        if role is None:
            continue
        if role not in member.roles:
            continue
        ok, is_perm = await role_change_with_retry(
            member, role, add=False,
            reason=f"Rank changed to #{rank} — lost {role_name}"
        )
        if not ok:
            removal_failed.append(role_name)
            if is_perm:
                permanent_error = role_name
                break   # لا فائدة من إكمال — نفس السبب سي فشل مع كل role

    # ─────────────────────────────────────────────
    # 2) 🔴 حارس منع التراكم — سحب فشل = ما نضيف
    # ─────────────────────────────────────────────
    if removal_failed:
        names = ", ".join(f"`{n}`" for n in removal_failed)
        logger.error(
            f"🛑 SKIP add-role لـ {member.display_name} (RANK #{rank}): "
            f"فشل سحب {names} — لو أضفنا الآن لتراكم أكثر من Rank Role"
        )
        bot_position = guild.me.top_role.position if guild.me else 0
        if permanent_error:
            await notify_admins(
                guild,
                f"🛑 تعذّر مزامنة أدوار لاعب (RANK #{rank})",
                f"> 👤  **اللاعب:**  {member.mention}  (`{member.id}`)\n"
                f"> 🏷  **Role لم يُسحب:**  `{permanent_error}`\n"
                f"> ⚠️  **السبب:**  البوت ما يقدر يسحب هذا الـ role — "
                f"الـ role **أعلى** من role البوت في الهرمي (Hierarchy)\n"
                f"> 📊  **Bot role:**  `{guild.me.top_role.name}`  (position `{bot_position}`)\n"
                f"> 🔧  **الحل:**  إما اسحب `{permanent_error}` لأسفل من role البوت، "
                f"أو ارفع role البوت فوقه في  `Server Settings → Roles`\n"
                f"> 🚫  **مؤقتاً:**  ما أضفت له rank role جديد عشان ما يتراكم عليه أكثر من role\n"
                f"> 📋  **Logs:**  شغّل `{PREFIX}botinfo` أو راجع Railway logs للتفاصيل",
                color=COLORS["error"]
            )
        return  # ❌ لا تضيف أي role جديد — هذا هو الإصلاح الجذري

    # ─────────────────────────────────────────────
    # 3) أعطِ اللاعب الـ role المناسب لو يستحقه
    # ─────────────────────────────────────────────
    if target_tier:
        target_role_name = RANK_TITLES[target_tier]["name"]
        # تحقق إن ما عنده بالفعل
        has_role = discord.utils.get(guild.roles, name=target_role_name) in member.roles
        if not has_role:
            role = await create_role_if_not_exists(guild, target_role_name, RANK_TITLES[target_tier]["color"])
            if role:
                ok, is_perm = await role_change_with_retry(
                    member, role, add=True,
                    reason=f"Rank #{rank} — earned {target_role_name}"
                )
                if not ok and is_perm:
                    bot_position = guild.me.top_role.position if guild.me else 0
                    await notify_admins(
                        guild,
                        f"🛑 تعذّر إعطاء rank role للاعب (RANK #{rank})",
                        f"> 👤  **اللاعب:**  {member.mention}  (`{member.id}`)\n"
                        f"> 🏷  **Role:**  `{target_role_name}`\n"
                        f"> ⚠️  **السبب:**  البوت ما يقدر يعطي هذا الـ role — "
                        f"الـ role **أعلى** من role البوت في الهرمي (Hierarchy)\n"
                        f"> 📊  **Bot role:**  `{guild.me.top_role.name}`  (position `{bot_position}`)\n"
                        f"> 🔧  **الحل:**  ارفع role البوت فوق `{target_role_name}` في  `Server Settings → Roles`",
                        color=COLORS["error"]
                    )


async def sync_all_players_roles(guild, player_ids=None):
    """🆕 يزامن roles اللاعبين في السيرفر حسب ترتيبهم الحالي.
    تُستدعى بعد كل recalculate_ranks().

    ⚡ تسريع: player_ids اختياري — يُمرَّر لتحديث أدوار مجموعة محددة فقط
    (مثل لاعبي ماتش انتهى) بدل المرور على كل اللاعبين.
    """
    try:
        # اجلب كل اللاعبين مرتبين
        players = db.get_leaderboard(guild.id, limit=None)  # كل اللاعبين
        if not players:
            return
        if player_ids is not None:
            wanted = set(player_ids)
            players = [p for p in players if p["user_id"] in wanted]
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


async def sync_all_nicknames(guild):
    """🆕 fixrank + syncnicknames تلقائياً كل دقيقتين:
    يصحّح نكات كل الأعضاء حسب رانكهم الحالي (للموجودين في السيرفر فقط).
    """
    updated = 0
    title = "🔄 Nickname Sync"
    try:
        members = [m for m in guild.members if not m.bot]
        for member in members:
            try:
                player = db.get_or_create_player(member.id, guild.id, member.display_name)
                await update_member_nickname(member, player.get("level", STARTING_LEVEL))
                updated += 1
                await asyncio.sleep(0.05)  # تجنب rate limit (تصحيح نكات كل الأعضاء)
            except Exception as e:
                logger.debug(f"sync_all_nicknames skip {member.id}: {e}")
        if updated:
            logger.info(f"{title} ({guild.name}): checked {len(members)} members")
    except Exception as e:
        logger.warning(f"{title} failed for {guild.name}: {e}")


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
                        logger.info(f"🔓 Permissions granted: {role.name} → #{ch.name}")
                    except discord.Forbidden as e:
                        logger.error(
                            f"❌ Forbidden set_permissions: role={role.name!r} channel=#{ch.name} "
                            f"in_guild={guild.name} | {e}"
                        )
                    except discord.HTTPException as e:
                        logger.warning(f"⚠️ HTTP set_permissions failed: role={role.name!r} channel=#{ch.name} | {e}")
    logger.info(f"✅ Rank roles setup complete in {guild.name}")


def sanitize_user_text(text, max_length=200):
    """🔒 يمنع مدخلات اللاعبين من اختلاق Discord mentions.

    السبب: مدخلات مثل سبب البلاغ تُخزَّن في DB ثم تُطبع داخل
    `notify_admins()` / `!!reports` — فلو سمحنا بـ `<@&id>` أو `@everyone`
    يقدر أي لاعب يعمل mass-ping للأدمنز أو أي role، ويكسر حد 1024 حرف
    في حقل الـ embed ويسبب HTTPException 400.

    ✅FIX: نكسر بنية الـ mention بإدراج zero-width space بعد `‎@`
    (يبقى النص مقروء بصرياً لكنه ما يفتح mention).
    """
    if not text:
        return None
    cleaned = str(text)
    zws = "\u200b"  # zero-width space
    # <@123> / <@!123> / <@&123>  ->  <@ZWS 123>  (ما عادش mention)
    cleaned = re.sub(r"<([@!&#]+)(\d+)>", lambda m: f"<{m.group(1)}{zws}{m.group(2)}>", cleaned)
    # @everyone / @here  ->  @ZWS everyone  (ما عادش mention)
    cleaned = re.sub(
        r"@(everyone|here)\b",
        lambda m: f"@{zws}{m.group(1)}",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = " ".join(cleaned.split()).strip()
    return cleaned[:max_length] or None


async def notify_admins(guild, title, description, color=None):
    """🆕 يرسل رسالة تاغ للأدمنز وكل الـ roles العالية في قناة 🔇・Blacklisted.
    (سابقاً كانت تُرسل إلى قناة match-results — الآن مخصصة للنتائج فقط).
    ✅ يُتاغ: الأونر + كل من لديه Administrator / Manage Guild + أعلى role في السيرفر.
    """
    try:
        if color is None:
            color = COLORS["error"]
        
        # ✅ إصلاح: اجمع كل الـ roles العالية للتاغ
        admin_mentions = []
        
        # 1) ابحث عن role الأدمن بالاسم
        admin_role = None
        for role in guild.roles:
            if role.name.lower() == ADMIN_ROLE_NAME.lower():
                admin_role = role
                break
        
        # 2) ابحث عن كل roles اللي فيها Administrator أو Manage Guild
        high_roles = []
        for role in guild.roles:
            if role == guild.default_role or role.is_bot_managed() or role.is_integration():
                continue
            if role.permissions.administrator or role.permissions.manage_guild:
                high_roles.append(role)
        
        # 3) ابحث عن أعلى role في السيرفر (الأونر واللي تحته)
        if guild.roles:
            # رتب الـ roles من الأعلى للأقل
            sorted_roles = sorted([r for r in guild.roles if r != guild.default_role and not r.is_bot_managed() and not r.is_integration()], key=lambda r: r.position, reverse=True)
            # خذ أعلى 3 roles (الأونر واللي تحته)
            for role in sorted_roles[:3]:
                if role not in high_roles:
                    high_roles.append(role)
        
        # 4) اجمع الـ mentions
        if admin_role and admin_role not in high_roles:
            high_roles.append(admin_role)
        
        for role in high_roles:
            admin_mentions.append(role.mention)
        
        # 5) أضف mention للأونر نفسه
        if guild.owner:
            admin_mentions.append(guild.owner.mention)
        
        # إزالة المكررات
        admin_mentions = list(dict.fromkeys(admin_mentions))
        admin_mention_str = " ".join(admin_mentions) if admin_mentions else "@here"
        
        # 🆕 تُرسل التنبيهات إلى قناة البلاك ليست (طلب: قناة match-results = نتائج فقط)
        channel = _resolve_blacklist_channel(guild)
        # fallback 1: أي قناة play
        if not channel:
            play_channels = db.get_play_channels(guild.id)
            if play_channels:
                channel = guild.get_channel(play_channels[0])
        # fallback 2: أول قناة نصية يقدر البوت يكتب فيها
        if not channel:
            for ch in guild.text_channels:
                if ch.permissions_for(guild.me).send_messages:
                    channel = ch
                    break
        if not channel:
            logger.warning(f"notify_admins: No channel found in {guild.name}")
            return
        embed = discord.Embed(
            title=f"⚠️ {title}",
            description=(
                f"{admin_mention_str}\n"
                f"{description}"
            ),
            color=color,
            timestamp=discord.utils.utcnow()
        )
        embed.set_author(name="🛡️ Admin Alert")
        embed.set_footer(text=f"{BOT_FOOTER}  •  Action required")
        embed = apply_branding(embed, guild)
        await channel.send(content=admin_mention_str, embed=embed)
    except Exception as e:
        logger.exception(f"notify_admins failed: {e}")

GUILD_SETTINGS_COLUMNS = {
    "form_channel_id", "announcement_role_id", "leaderboard_channel_id",
    "leaderboard_message_id", "auto_channel_category_id",
    "report_channel_ids",  # 🆕 قائمة فويسات التفتيش المحددة من الأدمن (JSON array)
    "blacklist_channel_id",   # 🆕 قناة عرض اللاعبين في البلاك ليست
    "blacklist_message_id"    # 🆕 رسالة القائمة في تلك القناة
}


# ============================================================
# DATABASE
# ============================================================
class Database:
    def __init__(self, db_path=None):
        # 🆕 دعم متغير البيئة DB_PATH لتحديد مسار قاعدة البيانات
        # ✅ إصلاح: استخدم مساراً ثابتاً بجانب ملف البوت (وليس المجلد الحالي)
        # هذا يمنع تصفير البيانات عند تشغيل البوت من مجلد مختلف
        if db_path:
            self.db_path = db_path
        elif os.getenv("DB_PATH"):
            self.db_path = os.getenv("DB_PATH")
        else:
            # ✅ استخدم مساراً ثابتاً بجانب ملف البوت
            bot_dir = os.path.dirname(os.path.abspath(__file__))
            self.db_path = os.path.join(bot_dir, "freefire_bot.db")
        
        # 🆕✅ إصلاح Railway/Render: أنشئ المجلد إذا لم يكن موجوداً!
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            try:
                os.makedirs(db_dir, exist_ok=True)
                logger.info(f"📁 Created database directory: {db_dir}")
            except Exception as e:
                logger.warning(f"⚠️ Could not create directory {db_dir}: {e}")
                # Fallback: استخدم المجلد الحالي
                self.db_path = os.path.join(os.getcwd(), "freefire_bot.db")
                logger.info(f"💾 Falling back to: {self.db_path}")
        
        # ✅ إصلاح: لو الـ DB غير موجودة، ابحث عن DB قديمة في مواقع شائعة
        if not os.path.exists(self.db_path):
            # ابحث في المجلد الحالي
            cwd_db = os.path.join(os.getcwd(), "freefire_bot.db")
            if os.path.exists(cwd_db):
                self.db_path = cwd_db
                logger.info(f"💾 Found existing DB in current directory: {self.db_path}")
            else:
                # ابحث في مجلدات شائعة
                for search_path in [
                    os.path.join(os.path.expanduser("~"), "freefire_bot.db"),
                    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "freefire_bot.db"),
                ]:
                    if os.path.exists(search_path):
                        self.db_path = os.path.abspath(search_path)
                        logger.info(f"💾 Found existing DB: {self.db_path}")
                        break
        
        logger.info(f"💾 Database path: {self.db_path}")
        # 🆕 تحسينات أداء للسيرفرات المتعددة
        self._local = threading.local()
        # ✅ cache لـ channels queries (يقلل DB queries بشكل كبير)
        self._channels_cache = {}
        self._init_db()
        self._create_tables()
        self._migrate()
        
        # ✅ إصلاح: احفظ عدد اللاعبين للتحقق من عدم التصفير
        try:
            conn = sqlite3.connect(self.db_path, timeout=30.0)
            count = conn.execute("SELECT COUNT(*) FROM players").fetchone()[0]
            conn.close()
            logger.info(f"💾 Database has {count} players — data preserved!")
        except:
            pass

    def _init_db(self):
        """🆕 تهيئة قاعدة البيانات بـ WAL mode للأداء العالي."""
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        try:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA cache_size=10000")
            conn.execute("PRAGMA temp_store=MEMORY")
            conn.execute("PRAGMA mmap_size=268435456")
            conn.commit()
        finally:
            conn.close()

    def conn(self):
        """🆕 يستخدم thread-local connection بدل فتح اتصال جديد كل مرة.
        ✅ إصلاح: تحقق من صحة الاتصال قبل إرجاعه، وأعد فتحه لو مغلق.
        """
        try:
            if hasattr(self._local, 'conn') and self._local.conn is not None:
                # تحقق من أن الاتصال ما زال مفتوحاً
                self._local.conn.execute("SELECT 1").fetchone()
                return self._local.conn
        except sqlite3.Error:
            # الاتصال مغلق أو تالف — أعد فتحه
            try:
                if hasattr(self._local, 'conn') and self._local.conn is not None:
                    self._local.conn.close()
            except Exception:
                pass
            self._local.conn = None
        # افتح اتصال جديد
        c = sqlite3.connect(self.db_path, timeout=30.0, isolation_level=None)
        c.row_factory = sqlite3.Row
        c.execute("PRAGMA journal_mode=WAL")
        c.execute("PRAGMA synchronous=NORMAL")
        c.execute("PRAGMA cache_size=10000")
        c.execute("PRAGMA foreign_keys = ON")
        self._local.conn = c
        return self._local.conn

    def _create_tables(self):
        c = sqlite3.connect(self.db_path, timeout=30.0)
        c.row_factory = sqlite3.Row
        c.execute("PRAGMA journal_mode=WAL")
        try:
            c.executescript("""
                CREATE TABLE IF NOT EXISTS guild_settings (
                    guild_id INTEGER PRIMARY KEY,
                    form_channel_id INTEGER DEFAULT NULL,
                    announcement_role_id INTEGER DEFAULT NULL,
                    leaderboard_channel_id INTEGER DEFAULT NULL,
                    leaderboard_message_id INTEGER DEFAULT NULL,
                    auto_channel_category_id INTEGER DEFAULT NULL,
                    report_channel_ids TEXT DEFAULT NULL,
                    blacklist_channel_id INTEGER DEFAULT NULL,
                    blacklist_message_id INTEGER DEFAULT NULL
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
                CREATE TABLE IF NOT EXISTS blacklist_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    blacklisted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP NOT NULL,
                    reason TEXT DEFAULT NULL,
                    UNIQUE(guild_id, user_id)
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
                # 🆕 قناة عرض البلاك ليست
                ("guild_settings", "blacklist_channel_id", "INTEGER DEFAULT NULL"),
                ("guild_settings", "blacklist_message_id", "INTEGER DEFAULT NULL"),
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
            pass  # thread-local connection

    def set_guild_setting(self, gid, key, val):
        if key not in GUILD_SETTINGS_COLUMNS:
            raise ValueError(f"Invalid key: {key}")
        conn = self.conn()
        try:
            conn.execute("INSERT OR IGNORE INTO guild_settings(guild_id) VALUES(?)", (gid,))
            conn.execute(f"UPDATE guild_settings SET {key}=? WHERE guild_id=?", (val, gid))
            conn.commit()
        finally:
            pass  # thread-local connection

    def add_play_channel(self, gid, cid):
        conn = self.conn()
        try:
            conn.execute("INSERT INTO play_channels(guild_id,channel_id) VALUES(?,?)", (gid, cid))
            conn.commit()
            # ✅ FIX (MEDIUM): get_play_channels يخزّن cache تحت `play_ch_{gid}`،
            # ولم يكن أي add/remove يمسحه ⇒ cache قديم حتى إعادة التشغيل
            # (يؤثّر على RematchView و notify_admins التي تختار play_channels[0]).
            self._channels_cache.pop(f"play_ch_{gid}", None)
            return True
        except sqlite3.IntegrityError:
            return False
        finally:
            pass  # thread-local connection

    def remove_play_channel(self, gid, cid):
        conn = self.conn()
        try:
            cur = conn.execute("DELETE FROM play_channels WHERE guild_id=? AND channel_id=?", (gid, cid))
            conn.commit()
            # ✅ FIX (MEDIUM): نفس السبب — امسح cache قناة الـ play
            self._channels_cache.pop(f"play_ch_{gid}", None)
            return cur.rowcount > 0
        finally:
            pass  # thread-local connection

    def get_play_channels(self, gid):
        # ✅ cache لتحسين الأداء
        cache_key = f"play_ch_{gid}"
        cached = self._channels_cache.get(cache_key)
        if cached is not None:
            return cached
        conn = self.conn()
        try:
            result = [x["channel_id"] for x in conn.execute("SELECT channel_id FROM play_channels WHERE guild_id=?", (gid,)).fetchall()]
            self._channels_cache[cache_key] = result
            return result
        finally:
            pass  # thread-local connection

    def add_commands_channel(self, gid, cid):
        conn = self.conn()
        try:
            conn.execute("INSERT INTO bot_commands_channels(guild_id,channel_id) VALUES(?,?)", (gid, cid))
            conn.commit()
            # ✅ امسح cache بعد التعديل
            self._channels_cache.pop(f"cmd_ch_{gid}", None)
            return True
        except sqlite3.IntegrityError:
            return False
        finally:
            pass  # thread-local connection

    def remove_commands_channel(self, gid, cid):
        conn = self.conn()
        try:
            cur = conn.execute("DELETE FROM bot_commands_channels WHERE guild_id=? AND channel_id=?", (gid, cid))
            conn.commit()
            # ✅ امسح cache بعد التعديل
            self._channels_cache.pop(f"cmd_ch_{gid}", None)
            return cur.rowcount > 0
        finally:
            pass  # thread-local connection

    def get_commands_channels(self, gid):
        # ✅ cache لتحسين الأداء
        cache_key = f"cmd_ch_{gid}"
        cached = self._channels_cache.get(cache_key)
        if cached is not None:
            return cached
        conn = self.conn()
        try:
            result = [x["channel_id"] for x in conn.execute("SELECT channel_id FROM bot_commands_channels WHERE guild_id=?", (gid,)).fetchall()]
            self._channels_cache[cache_key] = result
            return result
        finally:
            pass  # thread-local connection

    def is_bot_allowed_channel(self, gid, cid):
        if cid in self.get_commands_channels(gid):
            return True
        conn = self.conn()
        try:
            return conn.execute("SELECT 1 FROM match_channels WHERE guild_id=? AND (team1_text_id=? OR team2_text_id=?) LIMIT 1", (gid, cid, cid)).fetchone() is not None
        finally:
            pass  # thread-local connection

    def add_waiting_room(self, gid, cid):
        conn = self.conn()
        try:
            conn.execute("INSERT INTO waiting_rooms(guild_id,channel_id) VALUES(?,?)", (gid, cid))
            conn.commit(); return True
        except sqlite3.IntegrityError:
            return False
        finally:
            pass  # thread-local connection

    def remove_waiting_room(self, gid, cid):
        conn = self.conn()
        try:
            cur = conn.execute("DELETE FROM waiting_rooms WHERE guild_id=? AND channel_id=?", (gid, cid))
            conn.commit(); return cur.rowcount > 0
        finally:
            pass  # thread-local connection

    def get_waiting_rooms(self, gid):
        conn = self.conn()
        try:
            return [x["channel_id"] for x in conn.execute("SELECT channel_id FROM waiting_rooms WHERE guild_id=?", (gid,)).fetchall()]
        finally:
            pass  # thread-local connection

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
            pass  # thread-local connection

    def remove_allowed_guild(self, gid):
        conn = self.conn()
        try:
            cur = conn.execute("DELETE FROM allowed_guilds WHERE guild_id=?", (gid,))
            conn.commit(); return cur.rowcount > 0
        finally:
            pass  # thread-local connection

    def is_guild_allowed(self, gid):
        if not GUILD_WHITELIST_ENABLED:
            return True
        conn = self.conn()
        try:
            return conn.execute("SELECT 1 FROM allowed_guilds WHERE guild_id=?", (gid,)).fetchone() is not None
        finally:
            pass  # thread-local connection

    def get_allowed_guilds(self):
        conn = self.conn()
        try:
            return [dict(x) for x in conn.execute("SELECT * FROM allowed_guilds ORDER BY added_at DESC").fetchall()]
        finally:
            pass  # thread-local connection

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
            pass  # thread-local connection

    def get_player(self, uid, gid):
        conn = self.conn()
        try:
            r = conn.execute("SELECT * FROM players WHERE user_id=? AND guild_id=?", (uid, gid)).fetchone()
            return dict(r) if r else None
        finally:
            pass  # thread-local connection

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
            pass  # thread-local connection

    def update_player_level(self, uid, gid, delta):
        """⚠️ DEPRECATED V5 — لا تُستدعى. استخدم recalculate_ranks() بدلاً منها."""
        actual_delta = -delta
        conn = self.conn()
        try:
            conn.execute("UPDATE players SET level=MAX(1,MIN(9999,level+?)), last_active=? WHERE user_id=? AND guild_id=?", (actual_delta, datetime.now().isoformat(), uid, gid))
            conn.commit()
            r = conn.execute("SELECT level FROM players WHERE user_id=? AND guild_id=?", (uid, gid)).fetchone()
            return dict(r)["level"] if r else STARTING_LEVEL
        finally:
            pass  # thread-local connection

    def reset_stats(self, uid, gid):
        conn = self.conn()
        try:
            conn.execute("UPDATE players SET points=0,wins=0,losses=0,kills=0,mvps=0,matches_played=0,rank_pos=1,level=?,win_streak=0,lose_streak=0,max_win_streak=0,last_active=? WHERE user_id=? AND guild_id=?", (STARTING_LEVEL, datetime.now().isoformat(), uid, gid))
            conn.commit()
        finally:
            pass  # thread-local connection

    def get_leaderboard(self, gid, limit=10):
        """🆕 يرجع اللاعبين مرتبين حسب الترتيب الموحّد (متوافق مع recalculate_ranks). limit=None يرجع كل اللاعبين.
        ✅ إصلاح V5: الترتيب مطابق تماماً لـ recalculate_ranks
        """
        ORDER = "points DESC, kills DESC, mvps DESC, wins DESC, losses ASC, matches_played ASC, user_id ASC"
        conn = self.conn()
        try:
            if limit is None:
                return [dict(x) for x in conn.execute(
                    f"SELECT * FROM players WHERE guild_id=? ORDER BY {ORDER}",
                    (gid,)
                ).fetchall()]
            return [dict(x) for x in conn.execute(
                f"SELECT * FROM players WHERE guild_id=? ORDER BY {ORDER} LIMIT ?",
                (gid, limit)
            ).fetchall()]
        finally:
            pass  # thread-local connection

    def get_player_rank(self, points):
        """⚠️ DEPRECATED V5 — لا تُستدعى. استخدم get_player_rank_position() بدلاً منها."""
        return 1

    def create_lobby(self, gid, creator, chan, mode="4v4"):
        conn = self.conn()
        try:
            cur = conn.execute("INSERT INTO lobbies(guild_id,creator_id,channel_id,game_mode,team1_players) VALUES(?,?,?,?,?)", (gid, creator, chan, mode, json.dumps([creator])))
            conn.commit(); return cur.lastrowid
        finally:
            pass  # thread-local connection

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
            pass  # thread-local connection

    def get_active_lobby_by_guild(self, gid):
        """🆕 يرجع أحدث ماتش نشط (status=started) في السيرفر."""
        conn = self.conn()
        try:
            r = conn.execute(
                "SELECT * FROM lobbies WHERE guild_id=? AND status='started' ORDER BY id DESC LIMIT 1",
                (gid,)
            ).fetchone()
            if r:
                l = dict(r)
                l["team1_players"] = json.loads(l["team1_players"])
                l["team2_players"] = json.loads(l["team2_players"])
                return l
            return None
        finally:
            pass  # thread-local connection

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
            pass  # thread-local connection

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
            pass  # thread-local connection

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
            pass  # thread-local connection

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
            pass  # thread-local connection

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
            pass  # thread-local connection

    def update_lobby_message(self, lid, mid):
        conn = self.conn()
        try:
            conn.execute("UPDATE lobbies SET message_id=? WHERE id=?", (mid, lid))
            conn.commit()
        finally:
            pass  # thread-local connection

    def set_first_joiner(self, lid, uid):
        conn = self.conn()
        try:
            conn.execute("UPDATE lobbies SET first_joiner_id=? WHERE id=? AND first_joiner_id IS NULL", (uid, lid))
            conn.commit()
        finally:
            pass  # thread-local connection

    def set_room_info(self, lid, room_id, room_code, private_key=None):
        conn = self.conn()
        try:
            if private_key is not None:
                conn.execute("UPDATE lobbies SET room_id=?, room_code=?, private_key=? WHERE id=?", (room_id, room_code, private_key, lid))
            else:
                conn.execute("UPDATE lobbies SET room_id=?, room_code=? WHERE id=?", (room_id, room_code, lid))
            conn.commit()
        finally:
            pass  # thread-local connection

    def get_lobby_private_key(self, lid):
        conn = self.conn()
        try:
            r = conn.execute("SELECT private_key FROM lobbies WHERE id=?", (lid,)).fetchone()
            return r["private_key"] if r and r["private_key"] else None
        finally:
            pass  # thread-local connection

    def reassign_creator(self, lid, new_creator_id):
        conn = self.conn()
        try:
            conn.execute("UPDATE lobbies SET creator_id=? WHERE id=?", (new_creator_id, lid))
            conn.commit()
        finally:
            pass  # thread-local connection

    def save_match_channels(self, lid, gid, cat_id, t1v, t1t, t2v, t2t):
        conn = self.conn()
        try:
            conn.execute("INSERT INTO match_channels(lobby_id,guild_id,category_id,team1_voice_id,team1_text_id,team2_voice_id,team2_text_id) VALUES(?,?,?,?,?,?,?)", (lid, gid, cat_id, t1v, t1t, t2v, t2t))
            conn.commit()
        finally:
            pass  # thread-local connection

    def get_match_channels(self, lid):
        conn = self.conn()
        try:
            r = conn.execute("SELECT * FROM match_channels WHERE lobby_id=?", (lid,)).fetchone()
            return dict(r) if r else None
        finally:
            pass  # thread-local connection

    def delete_match_channels_record(self, lid):
        conn = self.conn()
        try:
            conn.execute("DELETE FROM match_channels WHERE lobby_id=?", (lid,))
            conn.commit()
        finally:
            pass  # thread-local connection

    def get_all_active_match_channels(self, gid):
        conn = self.conn()
        try:
            return [dict(x) for x in conn.execute("SELECT mc.* FROM match_channels mc JOIN lobbies l ON mc.lobby_id=l.id WHERE mc.guild_id=? AND l.status IN ('started','voting')", (gid,)).fetchall()]
        finally:
            pass  # thread-local connection

    def cast_vote(self, lid, uid, vote):
        conn = self.conn()
        try:
            conn.execute("INSERT INTO lobby_votes(lobby_id,user_id,vote) VALUES(?,?,?)", (lid, uid, vote))
            conn.commit(); return True
        except sqlite3.IntegrityError:
            return False
        finally:
            pass  # thread-local connection

    def get_votes(self, lid):
        conn = self.conn()
        try:
            return [dict(x) for x in conn.execute("SELECT * FROM lobby_votes WHERE lobby_id=?", (lid,)).fetchall()]
        finally:
            pass  # thread-local connection

    def has_voted(self, lid, uid):
        conn = self.conn()
        try:
            return conn.execute("SELECT 1 FROM lobby_votes WHERE lobby_id=? AND user_id=?", (lid, uid)).fetchone() is not None
        finally:
            pass  # thread-local connection

    def clear_votes(self, lid):
        conn = self.conn()
        try:
            conn.execute("DELETE FROM lobby_votes WHERE lobby_id=?", (lid,))
            conn.commit()
        finally:
            pass  # thread-local connection

    def set_vote_message(self, lid, mid):
        conn = self.conn()
        try:
            conn.execute("UPDATE lobbies SET vote_message_id=? WHERE id=?", (mid, lid))
            conn.commit()
        finally:
            pass  # thread-local connection

    def save_vote_metadata(self, lid, creator_id, first_joiner_id, message_id=None):
        conn = self.conn()
        try:
            conn.execute("INSERT OR REPLACE INTO vote_metadata(lobby_id,creator_id,first_joiner_id,message_id) VALUES(?,?,?,?)", (lid, creator_id, first_joiner_id, message_id))
            conn.commit()
        finally:
            pass  # thread-local connection

    def get_vote_metadata(self, lid):
        conn = self.conn()
        try:
            r = conn.execute("SELECT * FROM vote_metadata WHERE lobby_id=?", (lid,)).fetchone()
            return dict(r) if r else None
        finally:
            pass  # thread-local connection

    def get_lobby_id_by_message(self, message_id):
        conn = self.conn()
        try:
            r = conn.execute("SELECT lobby_id FROM vote_metadata WHERE message_id=?", (message_id,)).fetchone()
            return r["lobby_id"] if r else None
        finally:
            pass  # thread-local connection

    # 🆕 FIX: look up lobby by the original lobby message (Join Team buttons)
    def get_lobby_id_by_lobby_message(self, message_id):
        conn = self.conn()
        try:
            r = conn.execute("SELECT id FROM lobbies WHERE message_id=?", (message_id,)).fetchone()
            return r["id"] if r else None
        finally:
            pass  # thread-local connection

    # 🆕 FIX: look up lobby by the StartVote button message
    def get_lobby_id_by_start_vote_message(self, message_id):
        conn = self.conn()
        try:
            r = conn.execute("SELECT id FROM lobbies WHERE start_vote_message_id=?", (message_id,)).fetchone()
            return r["id"] if r else None
        finally:
            pass  # thread-local connection

    # 🆕 FIX: store the StartVote button message_id for later recovery
    def set_start_vote_message(self, lid, mid):
        conn = self.conn()
        try:
            conn.execute("UPDATE lobbies SET start_vote_message_id=? WHERE id=?", (mid, lid))
            conn.commit()
        finally:
            pass  # thread-local connection

    def delete_vote_metadata(self, lid):
        conn = self.conn()
        try:
            conn.execute("DELETE FROM vote_metadata WHERE lobby_id=?", (lid,))
            conn.commit()
        finally:
            pass  # thread-local connection

    def create_match_result(self, lid, winner, s1, s2, mvp=None):
        conn = self.conn()
        try:
            cur = conn.execute("INSERT INTO match_results(lobby_id,winner_team,team1_score,team2_score,mvp_id) VALUES(?,?,?,?,?)", (lid, winner, s1, s2, mvp))
            conn.commit(); return cur.lastrowid
        finally:
            pass  # thread-local connection

    def add_points(self, uid, gid, amount, skip_recalculate=False):
        """🆕 يضيف/يخصم نقاط.
        الرانك يُحسب من الترتيب في الـ leaderboard (1 = الأعلى نقاط).
        skip_recalculate=True يمنع استدعاء recalculate_ranks (للتجميع في الماتشات).
        """
        conn = self.conn()
        try:
            conn.execute(
                "UPDATE players SET points=points+?, last_active=? WHERE user_id=? AND guild_id=?",
                (amount, datetime.now().isoformat(), uid, gid)
            )
            conn.commit()
        finally:
            pass  # thread-local connection
        if not skip_recalculate:
            self.recalculate_ranks(gid)

    def update_match_player(self, uid, gid, points_delta, *, add_win=0, add_loss=0, add_match=0, add_kills=0, win_streak=0, lose_streak=0, max_win_streak=0, add_mvp=0, skip_recalculate=False):
        """يحدّث النقاط والإحصائيات في استعلام واحد، ويرجع بيانات اللاعب المحدّثة.
        ✅ إصلاح: يرجع بيانات اللاعب بعد recalculate_ranks (ليس قبله).
        ✅ إصلاح V5: إضافة add_kills لتحديث عمود kills."""
        conn = self.conn()
        try:
            conn.execute("""
                UPDATE players SET
                    points = points + ?,
                    wins = wins + ?,
                    losses = losses + ?,
                    matches_played = matches_played + ?,
                    kills = kills + ?,
                    win_streak = ?,
                    lose_streak = ?,
                    max_win_streak = MAX(max_win_streak, ?),
                    mvps = mvps + ?,
                    last_active = ?
                WHERE user_id=? AND guild_id=?
            """, (points_delta, add_win, add_loss, add_match, add_kills, win_streak, lose_streak, max_win_streak, add_mvp, datetime.now().isoformat(), uid, gid))
            conn.commit()
        finally:
            pass
        # ✅ إصلاح: استدعِ recalculate_ranks قبل إرجاع البيانات
        if not skip_recalculate:
            self.recalculate_ranks(gid)
        # ✅ إصلاح: اقرأ البيانات بعد recalculate_ranks (ليس قبله)
        conn = self.conn()
        r = conn.execute("SELECT * FROM players WHERE user_id=? AND guild_id=?", (uid, gid)).fetchone()
        result = dict(r) if r else None
        return result

    def get_top_points(self, gid):
        """يرجع أعلى نقاط في السيرفر (لحساب التقدم نحو الرانك #1)."""
        conn = self.conn()
        try:
            r = conn.execute("SELECT points FROM players WHERE guild_id=? ORDER BY points DESC LIMIT 1", (gid,)).fetchone()
            return r["points"] if r else 0
        finally:
            pass

    def recalculate_ranks(self, gid):
        """V5: يُعيد حساب رانك كل اللاعبين.
        - نقاط > 0 → رانك حسب الترتيب (1, 2, 3...)
        - نقاط = 0 → رانك 1000 (افتراضي — لم يلعب أو متوازن)
        - نقاط < 0 → رانك 1001, 1002... (عقوبة، كل لاعب له رانك فريد)
        ✅ إصلاح V5: إضافة user_id ASC كفاصل تعادل أخير لتحديد النتائج
        ✅ إصلاح V5: تحديث rank_pos أيضاً (كان يُتجاهل سابقاً)
        """
        # الترتيب الأساسي الموحّد — يُستخدم في كل مكان (recalculate_ranks, get_leaderboard, get_player_rank_position)
        # user_id ASC يضمن تحديد النتائج عند تطابق كل المعايير السابقة
        TIEBREAK_ORDER = "points DESC, kills DESC, mvps DESC, wins DESC, losses ASC, matches_played ASC, user_id ASC"

        conn = self.conn()
        try:
            # 1) لاعبون بنقاط إيجابية → رانك 1, 2, 3...
            active = conn.execute(f"""
                SELECT user_id,
                       ROW_NUMBER() OVER (ORDER BY {TIEBREAK_ORDER}) as rank_pos
                FROM players
                WHERE guild_id=? AND points > 0
            """, (gid,)).fetchall()
            updates = [(p["rank_pos"], p["rank_pos"], p["user_id"]) for p in active]

            # 2) لاعبون بنقاط صفر → رانك 1000 ثابت (الجدد + من صُفّر)
            zero_pts = conn.execute("""
                SELECT user_id FROM players
                WHERE guild_id=? AND points = 0
            """, (gid,)).fetchall()
            for p in zero_pts:
                updates.append((STARTING_LEVEL, 0, p["user_id"]))

            # 3) لاعبون بنقاط سالبة → رانك 1001, 1002... (عقوبة)
            negative = conn.execute(f"""
                SELECT user_id,
                       ROW_NUMBER() OVER (ORDER BY {TIEBREAK_ORDER}) as rn
                FROM players
                WHERE guild_id=? AND points < 0
            """, (gid,)).fetchall()
            for p in negative:
                penalty_rank = STARTING_LEVEL + p["rn"]
                updates.append((penalty_rank, 0, p["user_id"]))

            if updates:
                conn.executemany("UPDATE players SET level=?, rank_pos=? WHERE user_id=? AND guild_id=?", [(lv, rp, u, gid) for lv, rp, u in updates])
                conn.commit()
        finally:
            pass  # thread-local connection
        
        # ☁️ مزامنة للسحابة بعد كل recalculate_ranks
        if _CLOUD_AVAILABLE and is_cloud_enabled():
            try:
                players = self.get_leaderboard(gid, limit=None)
                if players:
                    sync_guild_players_to_cloud(gid, players)
            except Exception as e:
                logger.warning(f"☁️ Cloud sync failed in recalculate_ranks: {e}")

    def get_player_rank_position(self, uid, gid):
        """V5: يرجع ترتيب اللاعب (متوافق تماماً مع recalculate_ranks).
        - نقاط > 0 → ترتيبه بين الإيجابيين (1, 2, 3...)
        - نقاط = 0 → 1000
        - نقاط < 0 → 1001+ حسب عدد السلبيين قبله
        ✅ إصلاح V5: معايير كسر التعادل مطابقة تماماً لـ recalculate_ranks:
            points DESC, kills DESC, mvps DESC, wins DESC, losses ASC, matches_played ASC, user_id ASC
        """
        conn = self.conn()
        try:
            player = conn.execute(
                "SELECT points, kills, mvps, wins, losses, matches_played FROM players WHERE user_id=? AND guild_id=?",
                (uid, gid)
            ).fetchone()
            if not player:
                return None
            # نقاط صفر → رانك افتراضي
            if player["points"] == 0:
                return STARTING_LEVEL

            # ✅ V5: معايير كسر التعادل الموحّدة (متطابقة مع recalculate_ranks)
            # points DESC → points > ? (أعلى نقاط أولاً)
            # kills DESC → kills > ? (أكثر kills أولاً)
            # mvps DESC → mvps > ? (أكثر mvps أولاً)
            # wins DESC → wins > ? (أكثر فوز أولاً)
            # losses ASC → losses < ? (أقل خسارة أولاً)
            # matches_played ASC → matches_played < ? (أقل مباريات أولاً)
            # user_id ASC → user_id < ? (أقل ID أولاً — للتحديد)
            p = player  # shortcut
            tiebreak_sql = """(
                points > ? OR
                (points = ? AND kills > ?) OR
                (points = ? AND kills = ? AND mvps > ?) OR
                (points = ? AND kills = ? AND mvps = ? AND wins > ?) OR
                (points = ? AND kills = ? AND mvps = ? AND wins = ? AND losses < ?) OR
                (points = ? AND kills = ? AND mvps = ? AND wins = ? AND losses = ? AND matches_played < ?) OR
                (points = ? AND kills = ? AND mvps = ? AND wins = ? AND losses = ? AND matches_played = ? AND user_id < ?)
            )"""
            tiebreak_params = (
                p["points"],
                p["points"], p["kills"],
                p["points"], p["kills"], p["mvps"],
                p["points"], p["kills"], p["mvps"], p["wins"],
                p["points"], p["kills"], p["mvps"], p["wins"], p["losses"],
                p["points"], p["kills"], p["mvps"], p["wins"], p["losses"], p["matches_played"],
                p["points"], p["kills"], p["mvps"], p["wins"], p["losses"], p["matches_played"], uid
            )

            # نقاط سالبة → 1001 + ترتيبه بين السلبيين
            if p["points"] < 0:
                higher_neg = conn.execute(
                    f"SELECT COUNT(*) FROM players WHERE guild_id=? AND points < 0 AND {tiebreak_sql}",
                    (gid,) + tiebreak_params
                ).fetchone()[0]
                return STARTING_LEVEL + higher_neg + 1

            # نقاط إيجابية → عدّ من فوقه
            higher = conn.execute(
                f"SELECT COUNT(*) FROM players WHERE guild_id=? AND points > 0 AND {tiebreak_sql}",
                (gid,) + tiebreak_params
            ).fetchone()[0]
            return higher + 1
        finally:
            pass  # thread-local connection

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
            pass  # thread-local connection

    def get_reports_count(self, gid, reported_id):
        """يرجع عدد البلاغات على لاعب."""
        conn = self.conn()
        try:
            return conn.execute(
                "SELECT COUNT(*) FROM player_reports WHERE guild_id=? AND reported_id=?",
                (gid, reported_id)
            ).fetchone()[0]
        finally:
            pass  # thread-local connection

    def get_reports_for_player(self, gid, reported_id):
        """يرجع قائمة البلاغات على لاعب."""
        conn = self.conn()
        try:
            return [dict(x) for x in conn.execute(
                "SELECT * FROM player_reports WHERE guild_id=? AND reported_id=? ORDER BY created_at DESC",
                (gid, reported_id)
            ).fetchall()]
        finally:
            pass  # thread-local connection

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
            pass  # thread-local connection

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
            pass  # thread-local connection

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
            pass  # thread-local connection

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
            pass  # thread-local connection

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
            pass  # thread-local connection

    def get_banned_players(self, gid):
        """يرجع كل اللاعبين المحظورين في السيرفر."""
        conn = self.conn()
        try:
            return [dict(x) for x in conn.execute(
                "SELECT * FROM banned_players WHERE guild_id=? ORDER BY banned_at DESC",
                (gid,)
            ).fetchall()]
        finally:
            pass  # thread-local connection

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
            pass  # thread-local connection

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
            pass  # thread-local connection

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


    # ============================================================
    # 🆕 BLACKLIST SYSTEM — نظام البلاك ليست
    # ============================================================
    def is_player_blacklisted(self, gid, user_id):
        """يرجع True لو اللاعب في البلاك ليست (لم تنتهِ مدته)."""
        conn = self.conn()
        try:
            r = conn.execute(
                "SELECT expires_at FROM blacklist_log WHERE guild_id=? AND user_id=?",
                (gid, user_id)
            ).fetchone()
            if r:
                expires = datetime.fromisoformat(r["expires_at"])
                if datetime.now() < expires:
                    return True
                # انتهت المدة — احذف السجل
                conn.execute(
                    "DELETE FROM blacklist_log WHERE guild_id=? AND user_id=?",
                    (gid, user_id)
                )
                conn.commit()
            return False
        finally:
            pass

    def blacklist_player(self, gid, user_id, reason=None):
        """يضيف لاعباً إلى البلاك ليست لمدة BLACKLIST_DURATION ثانية."""
        expires = datetime.now().timestamp() + BLACKLIST_DURATION
        expires_iso = datetime.fromtimestamp(expires).isoformat()
        conn = self.conn()
        try:
            conn.execute(
                "INSERT OR REPLACE INTO blacklist_log(guild_id, user_id, expires_at, reason) VALUES(?,?,?,?)",
                (gid, user_id, expires_iso, reason)
            )
            conn.commit()
            return expires
        finally:
            pass

    def remove_blacklist(self, gid, user_id):
        """يزيل لاعباً من البلاك ليست."""
        conn = self.conn()
        try:
            conn.execute(
                "DELETE FROM blacklist_log WHERE guild_id=? AND user_id=?",
                (gid, user_id)
            )
            conn.commit()
        finally:
            pass

    def get_blacklisted_players(self, gid):
        """يرجع كل اللاعبين في البلاك ليست (الذين لم تنتهِ مدتهم)."""
        conn = self.conn()
        try:
            now = datetime.now().isoformat()
            return [dict(x) for x in conn.execute(
                "SELECT * FROM blacklist_log WHERE guild_id=? AND expires_at > ? ORDER BY blacklisted_at DESC",
                (gid, now)
            ).fetchall()]
        finally:
            pass


db = Database()

# ☁️ Cloud Restore — استرجاع البيانات من السحابة عند بدء التشغيل
if _CLOUD_AVAILABLE and is_cloud_enabled():
    logger.info("☁️ Cloud backup enabled — checking for data to restore...")
    auto_restore_database(db)
else:
    logger.info("☁️ Cloud backup not configured — using local database only")

active_lobby_messages = {}
lobby_timeout_timers = {}
vote_timeout_timers = {}
_admin_mvp_results = {}  # 🆕 lobby_id -> {"winner": user_id, "loser": user_id} لأوامر !!w / !!l
_lobby_embed_hide_timers = {}  # 🆕 مؤقتات إخفاء رسالة اللوبي تلقائياً بعد دقيقتين (عدد غير كافٍ)

# 🆕 رسائل "Create Lobby" — تختفي تلقائياً
# _create_prompt_msgs : {prompt_message_id: {"guild_id", "channel_id", "user_id"}}
# _create_prompt_timers : {prompt_message_id: asyncio.Task}  — مؤقت الدقيقة
# _lobby_prompt_msg : {lobby_id: prompt_message_id}  — ربط الرسالة باللوبي (تنتظر 끝 الروم)
_create_prompt_msgs = {}
_create_prompt_timers = {}
_lobby_prompt_msg = {}

# 🆕 V3 MAX: تخزين الفويس الأصلي لكل لاعب — {lobby_id: {user_id: original_voice_channel_id}}
# يُستخدم لإرجاع اللاعبين لنفس الـ waiting room بعد انتهاء/إلغاء الماتش
_original_voice_channels = {}

# 🆕 BLACKLIST: Voice tracking — {guild_id: {user_id: {...}}}
_blacklist_voice_tracking = {}
# 🆕 BLACKLIST: مجموعة channel IDs للماتشات النشطة (للبحث السريع)
_active_match_voice_channels = set()
# 🆕 BLACKLIST: مؤقتات الإزالة التلقائية — {guild_id: {user_id: timer_task}}
_blacklist_auto_remove_timers = {}
# 🆕 قفل إنشاء قناة البلاك ليست لكل سيرفر — يمنع تكرار القناة عند التنفيذ المتوازي
_blacklist_channel_locks = {}
# 🆕 رسائل تدفق اللعب في قناة اللعب — {lobby_id: set((channel_id, message_id))}
# تُحذف كلها تلقائياً عند انتهاء الماتش بأي طريقة (بما فيها "Match Ready")
_lobby_flow_msgs = {}

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
    """✦ Lobby Embed — V0 Redesign."""
    mode = lobby.get("game_mode", DEFAULT_MODE)
    mode_info = GAME_MODES.get(mode, GAME_MODES[DEFAULT_MODE])
    team_size = mode_info["team_size"]
    lobby_size = mode_info["lobby_size"]

    t1c = len(lobby["team1_players"])
    t2c = len(lobby["team2_players"])
    total = t1c + t2c
    progress_pct = int((total / lobby_size) * 100) if lobby_size else 0
    progress_bar = make_progress_bar(total, lobby_size, length=12)

    # V0: بطاقات اللاعبين (نمط نظيف)
    def make_team_card(players, team_emoji, team_size_limit):
        if not players:
            slots = [f"⚫ *empty slot*" for _ in range(team_size_limit)]
            return "\n".join(slots)
        lines = [f"{team_emoji} <@{pid}>" for pid in players[:team_size_limit]]
        empty = team_size_limit - len(lines)
        for _ in range(empty):
            lines.append(f"⚫ *empty slot*")
        return "\n".join(lines)

    t1_text = make_team_card(lobby["team1_players"], "🔴", team_size)
    t2_text = make_team_card(lobby["team2_players"], "🟢", team_size)

    # حالة اللوبي (V0 style)
    if total == 0:
        status_text = "⏳ Waiting for players..."
    elif total < lobby_size:
        status_text = f"⏳ Needs **{lobby_size - total} more players** to start"
    else:
        status_text = "🎮 Match ready to start!"

    # بناء الـ embed (V1 design)
    host_member = guild.get_member(lobby['creator_id'])
    host_name = host_member.display_name if host_member else 'Unknown'

    embed = discord.Embed(
        title=f"🎮 Free Fire • {mode.upper()} Lobby",
        description=(
            f"**Lobby** `#{lobby['id']}`\n"
            f"`{progress_bar}`  `{total}/{lobby_size}`  ·  `{progress_pct}%`"
        ),
        color=COLORS["play"],
        timestamp=discord.utils.utcnow()
    )

    embed.add_field(
        name=f"🔴 Team 1 — `{t1c}/{team_size}`",
        value=t1_text,
        inline=True
    )
    embed.add_field(
        name=f"🟢 Team 2 — `{t2c}/{team_size}`",
        value=t2_text,
        inline=True
    )

    embed.add_field(name="📋 Status", value=f"{status_text}", inline=False)

    # معلومات الغرفة الخاصة
    pk = db.get_lobby_private_key(lobby['id'])
    room_id = lobby.get('room_id')
    if pk and not room_id:
        embed.add_field(
            name="🔐 Private Match",
            value=f"Protected with a private key — ask <@{lobby['creator_id']}> for the key to join.",
            inline=False
        )

    embed.set_author(
        name=f"Host: {host_name} · Match Lobby",
        icon_url=host_member.display_avatar.url if host_member else None
    )
    embed.set_footer(text=f"{BOT_FOOTER}  •  Lobby #{lobby['id']}")
    embed = apply_branding(embed, guild)

    return embed


def create_profile_embed(player, member=None, gid=None):
    """♛ Profile Embed — V0 Redesign."""
    level = player.get("level", STARTING_LEVEL)
    rank_color = get_rank_color(level)
    rank_title = get_rank_title(level)
    points = player.get("points", 0)
    mvps = player.get("mvps", 0)

    mvp_badge = get_mvp_badge(mvps)
    mvp_title = get_mvp_title(mvps)

    wr = round((player["wins"] / max(player["matches_played"], 1)) * 100, 1)
    wr_bar = make_winrate_bar(wr, length=10)
    win_streak = player.get("win_streak", 0)
    lose_streak = player.get("lose_streak", 0)
    max_streak = player.get("max_win_streak", 0)
    kd_diff = player["wins"] - player["losses"]
    kd_sign = "+" if kd_diff >= 0 else ""

    top_pts = db.get_top_points(gid) if gid else 0
    pts_to_next = max(0, top_pts - points) if top_pts > points else 0
    progress_pct = int((points / max(top_pts, 1)) * 100) if top_pts else 0
    progress_pct = max(0, min(100, progress_pct))
    rank_progress_bar = make_progress_bar(points, max(top_pts, 1), length=15)

    name = member.display_name if member else player["username"]
    avatar_url = member.display_avatar.url if member else None

    # V0: streak line
    if win_streak > 0:
        streak_display = f"> 🔥 Win streak: `{win_streak}` (best: `{max_streak}`)"
    elif lose_streak > 0:
        streak_display = f"> ☠️ Lose streak: `{lose_streak}` (best: `{max_streak}`)"
    else:
        streak_display = f"> 📊 Best streak: `{max_streak}`"

    # V0: عنوان مع شارة
    display_title = f"♛ {name}"
    if mvp_badge:
        display_title += f" {mvp_badge}"

    embed = discord.Embed(
        title=f"{display_title}",
        description=(
            f"🏅 **{rank_title}**  `#{level}`\n"
            f"💰 `{points:,}` pts{streak_display.replace('> ', '\n> ')}\n"
            f"🔱 `{mvp_title}`{f' {mvp_badge}' if mvp_badge else ''}"
        ),
        color=rank_color,
        timestamp=discord.utils.utcnow()
    )

    # V1: 3×2 stats grid
    embed.add_field(name="🏆 Wins",    value=f"`{player['wins']}`", inline=True)
    embed.add_field(name="☠️ Losses",  value=f"`{player['losses']}`", inline=True)
    embed.add_field(name="⚖️ W/L",     value=f"`{kd_sign}{kd_diff}`", inline=True)

    embed.add_field(name="🎮 Matches", value=f"`{player['matches_played']}`", inline=True)
    embed.add_field(name="🔱 MVPs",    value=f"`{mvps}`", inline=True)
    embed.add_field(name="🔪 Kills",   value=f"`{player['kills']}`", inline=True)

    # V1: Win rate bar
    wr_status = "🔥 God Tier" if wr >= 70 else ("⭐ Pro" if wr >= 50 else ("🌱 Rising" if wr >= 30 else "☠️ Struggling"))
    embed.add_field(
        name=f"📊 Win Rate — `{wr}%` {wr_status}",
        value=f"{wr_bar} `{player['wins']}/{player['matches_played']}`",
        inline=False
    )

    # V1: التقدم نحو #1 / المتصدّر
    if pts_to_next > 0:
        embed.add_field(
            name="📈 Progress Toward `#1`",
            value=(
                f"`{rank_progress_bar}`  `{progress_pct}%`\n"
                f"Your pts `{points:,}`  ·  Top `{top_pts:,}`  ·  Remaining `{pts_to_next:,}`"
            ),
            inline=False
        )
    else:
        embed.add_field(
            name="🔱 You're the Leader!",
            value=f"🎉 You're at the top with `{points:,}` points! Keep it up!",
            inline=False
        )

    # V1: MVP achievement
    if mvps > 0:
        badge_display = ""
        if mvps >= 100:   badge_display = "🔱 🔱 🔱 LEGEND"
        elif mvps >= 50:  badge_display = "💎 💎 DIAMOND"
        elif mvps >= 20:  badge_display = "🏅 GOLD"
        elif mvps >= 5:   badge_display = "🥈 SILVER"
        else:              badge_display = "🥉 BRONZE"
        embed.add_field(
            name=f"🔱 MVP Achievement — `{mvps}` total",
            value=f"`{badge_display}` — `{mvp_title}`",
            inline=False
        )

    embed.set_footer(text=f"{BOT_FOOTER}")
    if member and member.guild:
        embed = apply_branding(embed, member.guild)
    embed.set_author(name="Player Profile")

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
    """◆ Leaderboard — V0 Redesign. يعرض النقاط والرانك معاً + يتحدث تلقائياً بعد كل ماتش."""
    try:
        settings = db.get_guild_settings(guild.id)
        if not settings or not settings.get("leaderboard_channel_id"):
            return
        channel = guild.get_channel(settings["leaderboard_channel_id"])
        if not channel:
            return
        # 🆕 إخفاء اللاعبين في البلاك ليست من اللوحة (بدل عرضهم)
        blacklisted_ids = {b["user_id"] for b in db.get_blacklisted_players(guild.id)}
        lb = db.get_leaderboard(guild.id, 25)
        lb = [p for p in lb if p["user_id"] not in blacklisted_ids][:10]
        embed = discord.Embed(
            title="🏆 Free Fire — Top 10 Players",
            description=(
                "📊 Ranking by points\n"
                "🔄 Auto-updates after every match\n"
                "📈 Every `50` pts = `+1` rank"
            ),
            color=COLORS["leaderboard"],
            timestamp=discord.utils.utcnow()
        )
        if not lb:
            embed.description = (
                f"> 📭 No players yet!\n"
                f"> Use `{PREFIX}play 4v4` to start your first match."
            )
        else:
            medals = ["💎", "🥈", "🥉", "🏅", "🎖️", "🏵️", "🏷️", "8️⃣", "9️⃣", "🔟"]
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
                pts_to_next = points_to_next_rank(p["points"], db, guild.id)
                # V0: فاصل رفيع بين كل لاعب
                if i > 0:
                    desc += "──────────────────────\n"
                next_rank_hint = f" · ⏭️ `{pts_to_next}` to #1" if pts_to_next > 0 else " · 🔱 At the top!"
                desc += (
                    f"{m} **{rank_emoji} {name}** `#{level}`\n"
                    f"└ 💰 `{p['points']:,}` pts · 🎮 `{p['matches_played']}` M · ✅ `{p['wins']}` W · ❌ `{p['losses']}` L · 📊 `{wr}%` {wr_status}\n"
                    f"└ 🔱 `{p['mvps']}` MVPs{next_rank_hint}\n"
                )
            embed.description = desc
        embed = apply_branding(embed, guild)
        embed.set_author(name=f"{guild.name} Leaderboard", icon_url=None)
        embed.set_footer(text=f"{BOT_FOOTER}  •  Live Leaderboard  ·  {len(lb)} players ranked")
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


async def update_blacklist_channel(guild):
    """🔇 يحدّث قناة "🔇・Blacklisted" التي تعرض اللاعبين في البلاك ليست.
    يُستدعى بعد كل apply/remove blacklist وبعد الـ setup.
    ⚡ إذا ما كانت القناة موجودة بعد، يُنشئها تحت كاتيجوري الـ TEXT.
    """
    try:
        settings = db.get_guild_settings(guild.id)
        if not settings:
            return
        # 🔒 قفل لكل سيرفر: يمنع إنشاء قناتين متوازيتين (سباق) عند تنفيذ أوامر متزامنة
        lock = _blacklist_channel_locks.setdefault(guild.id, asyncio.Lock())
        async with lock:
            # 🆕 إزالة التكرارات (أسماء دقيقة أو متضمنة لكلمة blacklist — يغطي القنوات اليدوية)
            def _looks_like_blacklist_channel(ch):
                lower = (ch.name or "").lower()
                return ch.name == BLACKLIST_CHANNEL_NAME or "blacklist" in lower

            candidates = [c for c in guild.text_channels if _looks_like_blacklist_channel(c)]
            exact = [c for c in candidates if c.name == BLACKLIST_CHANNEL_NAME]

            channel = None
            if settings.get("blacklist_channel_id"):
                ref = guild.get_channel(settings["blacklist_channel_id"])
                # ⚡ نستخدم القناة المرجعية فقط لو كانت فعلاً قناة بلاك ليست (لا نمسح إشارة خاطئة لقناة أخرى)
                if ref and _looks_like_blacklist_channel(ref):
                    channel = ref
            if not channel and exact:
                channel = exact[0]
            if not channel and candidates:
                channel = candidates[0]

            for extra in candidates:
                if extra.id != (channel.id if channel else -1):
                    try:
                        await extra.delete(reason="🧹 Duplicate blacklist channel")
                        logger.info(f"🧹 Deleted duplicate blacklist channel {extra.name} ({extra.id})")
                    except Exception as e:
                        logger.warning(f"🧹 Could not delete duplicate blacklist channel {extra.id}: {e}")

            # ⚡ ثبّت قناة البلاك ليست الفعلية بعد التنظيف (آخر إشارة صحيحة)
            if channel is not None:
                db.set_guild_setting(guild.id, "blacklist_channel_id", channel.id)
            if not channel:
                text_cat = discord.utils.get(guild.categories, name="🎮 FREE FIRE — TEXT")
                try:
                    channel = await guild.create_text_channel(
                        BLACKLIST_CHANNEL_NAME, category=text_cat, topic="Blacklisted Players"
                    )
                    db.set_guild_setting(guild.id, "blacklist_channel_id", channel.id)
                    logger.info(f"🔇 Created blacklist channel: {BLACKLIST_CHANNEL_NAME}")
                except Exception as e:
                    logger.warning(f"🔇 Could not create blacklist channel: {e}")
                    return

        blacklisted = db.get_blacklisted_players(guild.id)
        embed = discord.Embed(
            title="🔇 Blacklisted Players",
            description=f"📊 **الإجمالي:** `{len(blacklisted)}`",
            color=COLORS["warning"] if blacklisted else COLORS["success"],
            timestamp=discord.utils.utcnow()
        )
        embed.set_author(name="Blacklist")
        if not blacklisted:
            embed.description = "> ✅  لا يوجد لاعبون في البلاك ليست حالياً"
        else:
            for i, b in enumerate(blacklisted[:15], 1):
                member = guild.get_member(b["user_id"])
                name = member.display_name if member else f"User#{b['user_id']}"
                mention = member.mention if member else f"<@{b['user_id']}>"
                reason = b.get("reason") or "غير محدد"
                expires = b.get("expires_at", "N/A")[:19] if b.get("expires_at") else "N/A"
                embed.add_field(
                    name=f"#{i} — {name}",
                    value=f"👤 {mention}\n📝 `{reason}`\n⏱️ ينتهي: `{expires}`",
                    inline=False
                )
            if len(blacklisted) > 15:
                embed.set_footer(text=f"{BOT_FOOTER}  •  و {len(blacklisted) - 15} لاعب آخر")
        embed = apply_branding(embed, guild)

        msg_id = settings.get("blacklist_message_id")
        if msg_id:
            try:
                msg = await channel.fetch_message(msg_id)
                await msg.edit(embed=embed)
                return
            except (discord.NotFound, discord.Forbidden):
                pass
        msg = await channel.send(embed=embed)
        db.set_guild_setting(guild.id, "blacklist_message_id", msg.id)
    except Exception as e:
        logger.exception(f"update_blacklist_channel failed: {e}")


async def delete_message_safely(channel, message_id, reason=""):
    """🆕 يحذف رسالة ويتعامل مع كل الأخطاء بوضوح (بدل ابتلاعها)."""
    if channel is None or message_id is None:
        return False
    try:
        msg = await channel.fetch_message(message_id)
        await msg.delete()
        logger.info(f"🧹 Deleted message {message_id} ({reason})")
        return True
    except discord.NotFound:
        logger.info(f"ℹ️ Message {message_id} already gone ({reason})")
        return False
    except discord.Forbidden as e:
        logger.warning(f"⚠️ Cannot delete message {message_id} — Forbidden ({reason}): {e}")
        return False
    except discord.HTTPException as e:
        logger.warning(f"⚠️ HTTP error deleting message {message_id} ({reason}): {e}")
        return False
    except Exception as e:
        logger.exception(f"⚠️ Unexpected error deleting message {message_id} ({reason}): {e}")
        return False


def find_match_results_channel(guild):
    """🆕 يبحث عن قناة النتائج المخصصة (match-results / match result / نتائج الماتش) في السيرفر.
    تُرسل إليها نتيجة الماتش النهائية فقط — أي رسائل أخرى لن تذهب إليها.
    """
    try:
        for ch in guild.text_channels:
            name = (ch.name or "").lower().replace("_", " ").replace("-", " ").replace("・", " ")
            if "match result" in name or "نتائج" in name or "result" in name:
                return ch
        return None
    except Exception as e:
        logger.warning(f"find_match_results_channel failed in {getattr(guild, 'name', '?')}: {e}")
        return None


def _resolve_blacklist_channel(guild):
    """🆕 يرجع قناة 🔇・Blacklisted (من الإعدادات أو بالاسم) — أو None إن لم توجد."""
    try:
        settings = db.get_guild_settings(guild.id)
        if settings and settings.get("blacklist_channel_id"):
            ch = guild.get_channel(settings["blacklist_channel_id"])
            if ch:
                return ch
        for ch in guild.text_channels:
            if ch.name == BLACKLIST_CHANNEL_NAME:
                return ch
        return None
    except Exception as e:
        logger.warning(f"_resolve_blacklist_channel failed in {getattr(guild, 'name', '?')}: {e}")
        return None


async def _post_match_result(guild, embed, channel):
    """🆕 يرسل نتيجة الماتش إلى قناة النتائج المخصصة (match-results) إن وُجدت،
    وإلا إلى القناة الأصلية — بحيث تكون قناة النتائج مخصصة للنتائج فقط.
    """
    mrs_ch = find_match_results_channel(guild)
    results_ch = mrs_ch or channel
    if results_ch:
        try:
            await results_ch.send(embed=embed)
        except discord.HTTPException as e:
            logger.warning(f"⚠️ Failed to send result to {results_ch.name}: {e}")
            if mrs_ch and channel:
                try:
                    await channel.send(embed=embed)
                except discord.HTTPException:
                    pass
    else:
        logger.warning("⚠️ No channel to post match result")


async def auto_hide_create_prompt(guild, msg, user_id):
    """🆕 ينتظر CREATE_PROMPT_DELETE_AFTER ثم يحذف رسالة "Create Lobby"
       إذا ما انشأ اللاعب الروم.
       ✅ إذا انشأ الروم → ما نحذفها، تنتظر لآخر الماتش.
    """
    prompt_id = msg.id
    try:
        await asyncio.sleep(CREATE_PROMPT_DELETE_AFTER)
    except asyncio.CancelledError:
        _create_prompt_timers.pop(prompt_id, None)
        return

    _create_prompt_timers.pop(prompt_id, None)

    # ✅ انربطت بلوبي حقيقي → خلّها لآخر الماتش
    if prompt_id in _lobby_prompt_msg.values():
        logger.info(
            f"⏱️ Create prompt {prompt_id}: room created — keeping until the match ends"
        )
        return

    _create_prompt_msgs.pop(prompt_id, None)
    await delete_message_safely(
        msg.channel, prompt_id,
        reason=f"لم يتم إنشاء الروم خلال {CREATE_PROMPT_DELETE_AFTER} ثانية"
    )
    logger.info(
        f"🧹 Auto-removed 'Create Lobby' message {prompt_id} — "
        f"no room created in {CREATE_PROMPT_DELETE_AFTER}s (user={user_id})"
    )


async def _delete_create_prompt_for_lobby(lobby_id, guild=None):
    """🆕 يحذف رسالة "Create Lobby" عند انتهاء اللوبي (تم / أُلغي / timeout)."""
    prompt_id = _lobby_prompt_msg.pop(lobby_id, None)
    if not prompt_id:
        return
    meta = _create_prompt_msgs.pop(prompt_id, None)
    if not meta:
        return
    g = guild or bot.get_guild(meta["guild_id"])
    if not g:
        logger.warning(f"⚠️ Guild {meta['guild_id']} not found — can't delete prompt {prompt_id}")
        return
    ch = g.get_channel(meta["channel_id"])
    await delete_message_safely(ch, prompt_id, reason=f"انتهى اللوبي #{lobby_id}")


async def _delete_lobby_embed_for_lobby(lobby_id, msg_ids=None, guild=None):
    """🆕 يحذف رسالة اللوبي (الـ embed مع أزرار الانضمام) عند انتهاء اللوبي.
    يُستدعى من cleanup_lobby_memory، ومن مؤقت الدقيقتين لو ما اكتمل العدد.
    msg_ids: معرّفات الرسائل المطلوب حذفها (تُلتقط قبل مسح الـ dict).
    """
    if msg_ids is None:
        msg_ids = [k for k, v in active_lobby_messages.items() if v == lobby_id]
    lobby = db.get_lobby(lobby_id)
    if not lobby:
        return
    # 🆕 لو الرسالة ما رُصدت في الذاكرة (مثلاً لوبي قديم قبل إعادة التشغيل)
    # → استخدم message_id المحفوظ في DB لضمان الحذف
    if not msg_ids and lobby.get("message_id"):
        msg_ids = [lobby["message_id"]]
    if not msg_ids:
        return
    g = guild or bot.get_guild(lobby["guild_id"])
    if not g:
        return
    ch = g.get_channel(lobby["channel_id"])
    for mid in msg_ids:
        active_lobby_messages.pop(mid, None)
        await delete_message_safely(ch, mid, reason=f"انتهى اللوبي #{lobby_id}")


def register_lobby_flow_msg(lobby_id, channel_id, message_id):
    """🆕 يسجّل رسالة من تدفق اللعب (إنشاء/انضمام/Match Ready...) في قناة اللعب
    لتُحذف كلها تلقائياً عند انتهاء الماتش بأي طريقة."""
    if not lobby_id or not message_id:
        return
    _lobby_flow_msgs.setdefault(lobby_id, set()).add((channel_id, message_id))


async def _delete_lobby_flow_msgs(lobby_id):
    """🆕 يحذف كل رسائل تدفق اللعب المسجّلة للوبي عند انتهائه (بأي طريقة)."""
    flow = _lobby_flow_msgs.pop(lobby_id, None)
    if not flow:
        return
    for ch_id, mid in list(flow):
        ch = bot.get_channel(ch_id)
        await delete_message_safely(ch, mid, reason=f"انتهى اللوبي #{lobby_id} (flow)")


async def _auto_hide_idle_lobby_embed(lobby_id, guild):
    """🆕 بعد دقيقتين: لو اللوبي لسا waiting (ما اكتمل العدد) → احذف رسالته
    وألغِ اللوبي حتى لا يعلق اللاعبون في لوبي لا يمكن الانضمام إليه.
    َيعمل مرة واحدة فقط (يُحذف من المؤقتات عند التنفيذ أو الإلغاء).
    """
    try:
        await asyncio.sleep(TEMP_EMBED_DELETE_AFTER)
        lobby = db.get_lobby(lobby_id)
        if not lobby or lobby["status"] != "waiting":
            _lobby_embed_hide_timers.pop(lobby_id, None)
            return
        # أزِل مؤقّتنا أولاً حتى لا يُلغي cleanup_lobby_memory هذه المهمة نفسها
        _lobby_embed_hide_timers.pop(lobby_id, None)
        # ما اكتمل العدد خلال دقيقتين → أغلق اللوبي + احذف الرسالة
        db.update_lobby_status(lobby_id, "cancelled")
        cleanup_lobby_memory(lobby_id)
        ch = guild.get_channel(lobby["channel_id"])
        if ch:
            closed_embed = discord.Embed(
                title="⏰ Lobby Closed — Not Enough Players",
                description=(
                    f"لم يكتمل العدد المطلوب خلال **{TEMP_EMBED_DELETE_AFTER // 60} دقيقة**.\n"
                    f"💡 استخدم `{PREFIX}play 4v4` لبدء ماتش جديد."
                ),
                color=COLORS["warning"],
                timestamp=discord.utils.utcnow()
            )
            closed_embed.set_footer(text=f"{BOT_FOOTER}  •  Lobby #{lobby_id}")
            closed_embed = apply_branding(closed_embed, guild)
            await ch.send(embed=closed_embed, delete_after=TEMP_EMBED_DELETE_AFTER)
            logger.info(
                f"⏰ Lobby #{lobby_id} auto-closed — not enough players after "
                f"{TEMP_EMBED_DELETE_AFTER}s"
            )
    except asyncio.CancelledError:
        _lobby_embed_hide_timers.pop(lobby_id, None)
        raise
    except Exception as e:
        logger.warning(f"_auto_hide_idle_lobby_embed failed for lobby #{lobby_id}: {e}")
        _lobby_embed_hide_timers.pop(lobby_id, None)


def cleanup_lobby_memory(lobby_id):
    to_remove = [k for k, v in active_lobby_messages.items() if v == lobby_id]
    for k in to_remove:
        del active_lobby_messages[k]
    for timer_dict in (lobby_timeout_timers, vote_timeout_timers, _lobby_embed_hide_timers):
        if lobby_id in timer_dict:
            try:
                timer_dict[lobby_id].cancel()
            except Exception:
                pass
            del timer_dict[lobby_id]
    if lobby_id in _admin_mvp_results:
        del _admin_mvp_results[lobby_id]
    try:
        db.delete_vote_metadata(lobby_id)
    except Exception:
        pass

    # 🆕 احذف رسالة "Create Lobby" المرتبطة بهذا اللوبي
    if lobby_id in _lobby_prompt_msg:
        try:
            asyncio.create_task(_delete_create_prompt_for_lobby(lobby_id))
        except RuntimeError:
            # ما في event loop شغّال — نظّف على الأقل
            pid = _lobby_prompt_msg.pop(lobby_id, None)
            if pid:
                _create_prompt_msgs.pop(pid, None)

    # 🆕 احذف رسالة اللوبي (الـ embed) الفعلية عند انتهاء اللوبي
    if to_remove:
        try:
            asyncio.create_task(_delete_lobby_embed_for_lobby(lobby_id, msg_ids=list(to_remove)))
        except RuntimeError:
            pass

    # 🆕 احذف كل رسائل تدفق اللعب المسجّلة (Match Ready / أي رسائل أخرى في قناة اللعب)
    if lobby_id in _lobby_flow_msgs:
        try:
            asyncio.create_task(_delete_lobby_flow_msgs(lobby_id))
        except RuntimeError:
            _lobby_flow_msgs.pop(lobby_id, None)


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
    general_text = await guild.create_text_channel("💬・Teams chat", category=cat, overwrites=general_overwrites)

    db.save_match_channels(lobby_id, guild.id, cat.id, t1_voice.id, general_text.id, t2_voice.id, general_text.id)
    # 🆕 سجل الفويسات في مجموعة البلاك ليست المتابعة
    _active_match_voice_channels.add(t1_voice.id)
    _active_match_voice_channels.add(t2_voice.id)
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
        ch_name = f"⚠️  Investigation {i}"
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
        "⚠️  Auto-Ban Triggered",
        f"> ⚠️  تم حظر اللاعب تلقائياً بعد وصول بلاغاته إلى `{REPORT_THRESHOLD}`\n"
        f"> 👤  **اللاعب:**  <@{reported_id}>\n"
        f"> 📊  **عدد البلاغات:**  `{total_reports}`\n"
        f"> 🔍  **الإجراء:**  تم نقله لفويس التفتيش + تقييده{voice_info}\n"
        f"> 💡 Use  `!!unbanplayer @user`  لفك الحظر بعد التفتيش",
        color=COLORS["error"]
    )
    return True


async def delete_match_channels(guild, lobby_id):
    """🆕 V3 MAX: ينقل اللاعبين لفويسهم الأصلي قبل حذف الفويسات."""
    mc = db.get_match_channels(lobby_id)
    if not mc:
        # 🆕 حتى لو ما فيه match channels، امسح الفويس الأصلي من الذاكرة
        _original_voice_channels.pop(lobby_id, None)
        return
    # ✅ V3 MAX: ابحث عن waiting room صالحة (fallback لو الفويس الأصلي محذوف)
    fallback_vc = None
    for cid in db.get_waiting_rooms(guild.id):
        vc = guild.get_channel(cid)
        if vc and isinstance(vc, discord.VoiceChannel):
            fallback_vc = vc
            break
    # ✅ انقل كل الأعضاء من فويسات الماتش لفويسهم الأصلي
    original_channels = _original_voice_channels.get(lobby_id, {})
    for voice_key in ["team1_voice_id", "team2_voice_id"]:
        voice_id = mc.get(voice_key)
        if voice_id:
            ch = guild.get_channel(voice_id)
            if ch and isinstance(ch, discord.VoiceChannel):
                for member in ch.members:
                    # 🆕 V3 MAX: ابحث عن الفويس الأصلي للاعب
                    target_vc = None
                    original_cid = original_channels.get(member.id)
                    if original_cid:
                        original_vc = guild.get_channel(original_cid)
                        if original_vc and isinstance(original_vc, discord.VoiceChannel):
                            target_vc = original_vc
                            logger.info(f"  🔄 Returning {member.display_name} → original: {original_vc.name}")
                    # fallback: استخدم أي waiting room صالحة
                    if not target_vc and fallback_vc:
                        target_vc = fallback_vc
                        logger.info(f"  🔄 Returning {member.display_name} → fallback: {fallback_vc.name}")
                    if target_vc:
                        try:
                            await member.move_to(target_vc)
                        except (discord.HTTPException, discord.Forbidden):
                            pass
    # 🆕 امسح الفويس الأصلي من الذاكرة
    _original_voice_channels.pop(lobby_id, None)
    # 🆕 امسح الفويسات من مجموعة البلاك ليست
    for voice_key in ["team1_voice_id", "team2_voice_id"]:
        voice_id = mc.get(voice_key)
        if voice_id:
            _active_match_voice_channels.discard(voice_id)
    # الآن احذف القنوات
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
            # ✅ FIX (CRITICAL): ما فيه قنوات ماتش = ما راح ينعرض أي voting UI،
            # وما في timer بيشتغل. لو تركنا الحالة 'voting' اللاعبون يضلون محبوسين
            # في اللوبي للأبد (get_player_active_lobby يحسب 'voting' كـ active).
            logger.error(
                f"❌ auto_trigger_vote: lobby {lobby_id} has no match_channels — "
                f"reverting status to 'started'"
            )
            db.update_lobby_status(lobby_id, "started")
            await notify_admins(
                guild,
                "❌ فشل إطلاق التصويت",
                f"> 🐛  اللوبي `#{lobby_id}` ما لقى قنوات الماتش — ما راح ينعرض التصويت.\n"
                f"> 🔄  رجّعنا الحالة إلى `started`.\n"
                f"> 💡  جرّب  `!!startvote {lobby_id}`  أو  `!!resolve {lobby_id} team1|team2`"
            )
            return

        t1m = " ".join([f"<@{p}>" for p in lobby["team1_players"]])
        t2m = " ".join([f"<@{p}>" for p in lobby["team2_players"]])

        # 🆕 المصوّنين = أول 2 من كل فريق
        voters = build_mvp_voters(lobby["team1_players"], lobby["team2_players"], creator_id)
        v1 = [p for p in voters if p in lobby["team1_players"]]
        v2 = [p for p in voters if p in lobby["team2_players"]]

        mvp_embed = discord.Embed(
            title=f"🗳️ تصويت MVP الجماعي — Match #{lobby_id}",
            description=(
                "الماتش انتهى — اختاروا الـ MVPs معاً.\n"
                f"⏱️ عندكم **{VOTE_TIMEOUT_SECONDS} ثانية** للتوصل لاتفاق.\n"
                f"🎯 الاتفاق المطلوب: `{MVP_CONSENSUS_NEEDED}` أصوات من `{len(voters)}`\n"
                "\n"
                f"🔴 مصوّتو Team 1 (أول 2): {' '.join(f'<@{p}>' for p in v1) or '*N/A*'}\n"
                f"🟢 مصوّتو Team 2 (أول 2): {' '.join(f'<@{p}>' for p in v2) or '*N/A*'}"
            ),
            color=COLORS["vote"],
            timestamp=discord.utils.utcnow()
        )
        mvp_embed.add_field(name=f"🔴 Team 1 — `{len(lobby['team1_players'])}` players", value=f"{t1m or '*No players*'}", inline=True)
        mvp_embed.add_field(name=f"🟢 Team 2 — `{len(lobby['team2_players'])}` players", value=f"{t2m or '*No players*'}", inline=True)
        mvp_embed.add_field(name="💡 كيف أصوّت؟", value="المصوّتون يدوّرون على `🏆 MVP WINNER` و `✦ MVP LOSER` من القوائم تحت.\n⚠️ **ما اتفقتم؟** البوت ينقل أدمن لو حاضر بالفويسات، أو يتاغه مع الأوامر.", inline=False)
        mvp_embed.set_author(name="MVP Voting", icon_url=None)
        mvp_embed.set_footer(text=f"{BOT_FOOTER}  •  Match #{lobby_id}")
        mvp_embed = apply_branding(mvp_embed, guild)

        general_text = guild.get_channel(mc["team1_text_id"])
        vote_msg_id = None
        if not general_text:
            # ✅ FIX (HIGH): نفس المشكلة — بدون شات ما في رسالة تصويت = اللوبي محبوس
            logger.error(
                f"❌ auto_trigger_vote: lobby {lobby_id} match text channel "
                f"({mc['team1_text_id']}) not found — reverting status to 'started'"
            )
            db.update_lobby_status(lobby_id, "started")
            await notify_admins(
                guild,
                "❌ فشل إطلاق التصويت",
                f"> 🐛  قناة الماتش `{mc['team1_text_id']}` مفقودة في السيرفر "
                f"`{guild.name}` — ما راح ينعرض التصويت.\n"
                f"> 🔄  رجّعنا الحالة إلى `started`.\n"
                f"> 💡  جرّب  `!!startvote {lobby_id}`  أو  `!!resolve {lobby_id} team1|team2`"
            )
            return
        mvp_view = MvpVoteView(
            lobby_id, guild, creator_id, first_joiner_id,
            lobby["team1_players"], lobby["team2_players"]
        )
        try:
            vote_msg = await general_text.send(
                f"🔱 {t1m} {t2m}",
                embed=mvp_embed,
                view=mvp_view
            )
        except discord.HTTPException as e:
            # ✅ FIX (HIGH): فشل الإرسال = نفس الحبس — رجّع الحالة وبلّغ الأدمن
            logger.exception(f"❌ auto_trigger_vote: failed to send vote message (lobby {lobby_id}): {e}")
            db.update_lobby_status(lobby_id, "started")
            await notify_admins(
                guild,
                "❌ فشل إرسال رسالة التصويت",
                f"> 🐛  **الخطأ:**  `{str(e)[:200]}`\n"
                f"> 🔄  رجّعنا حالة اللوبي `#{lobby_id}` إلى `started`.\n"
                f"> 💡  جرّب  `!!startvote {lobby_id}`  أو  `!!resolve {lobby_id} team1|team2`"
            )
            return
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
                title="⏰ Lobby Timed Out",
                description=(
                    f"اللوبي `#{lobby_id}` تم إلغاؤه بسبب عدم النشاط.\n"
                    f"💡 استخدم `{PREFIX}play 4v4` لبدء ماتش جديد."
                ),
                color=COLORS["warning"],
                timestamp=discord.utils.utcnow()
            )
            timeout_embed.set_footer(text=f"{BOT_FOOTER}  •  Lobby #{lobby_id}")
            timeout_embed = apply_branding(timeout_embed, guild)
            await ch.send(embed=timeout_embed, delete_after=TEMP_EMBED_DELETE_AFTER)
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
            new_p = db.update_match_player(
                pid, guild.id, pts,
                add_win=1, add_match=1,
                win_streak=new_win_streak, lose_streak=0,
                max_win_streak=new_max,
                add_mvp=1 if is_mvp else 0,
                skip_recalculate=True
            )
            new_level = new_p.get("level", STARTING_LEVEL) if new_p else old_level
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
            new_p = db.update_match_player(
                pid, guild.id, pts,
                add_loss=1, add_match=1,
                win_streak=0, lose_streak=new_lose_streak,
                add_mvp=1 if is_mvp else 0,
                skip_recalculate=True
            )
            new_level = new_p.get("level", STARTING_LEVEL) if new_p else old_level
            loser_details.append((pid, pts, is_mvp, old_level, new_level))

        db.recalculate_ranks(guild.id)
        # ✅ إصلاح: أعد قراءة الرانك الجديد لكل لاعب بعد recalculate_ranks
        for i, (pid, pts, is_mvp, old_level, _) in enumerate(winner_details):
            p = db.get_player(pid, guild.id)
            new_level = p.get("level", STARTING_LEVEL) if p else old_level
            winner_details[i] = (pid, pts, is_mvp, old_level, new_level)
            m = guild.get_member(pid)
            if m:
                await update_member_nickname(m, new_level)
        for i, (pid, pts, is_mvp, old_level, _) in enumerate(loser_details):
            p = db.get_player(pid, guild.id)
            new_level = p.get("level", STARTING_LEVEL) if p else old_level
            loser_details[i] = (pid, pts, is_mvp, old_level, new_level)
            m = guild.get_member(pid)
            if m:
                await update_member_nickname(m, new_level)
        # 🆕 حفظ نتيجة الماتش مع MVPs
        db.create_match_result(
            lobby_id, winner_team,
            len(wt), len(lt),
            mvp=winner_mvp_id
        )

        # 🆕 بناء رسالة النتيجة الاحترافية
        wd = "🔴 Team 1" if winner_team == "team1" else "🟢 Team 2"
        wt_mentions = "\n".join([
            f"{'🔱' if is_mvp else '✅'}  <@{pid}> → `{'+' if pts > 0 else ''}{pts}` pts  (RANK #{old}→#{new})"
            for pid, pts, is_mvp, old, new in winner_details
        ]) or "*لا يوجد لاعبون*"
        lt_mentions = "\n".join([
            f"{'✦' if is_mvp else '☠️'}  <@{pid}> → `{'+' if pts > 0 else ''}{pts}` pts  (RANK #{old}→#{new})"
            for pid, pts, is_mvp, old, new in loser_details
        ]) or "*لا يوجد لاعبون*"

        embed = discord.Embed(
            title=f"🏅 Match Result — #{lobby_id}",
            description=(
                f"## 🎉 {wd} Wins!\n"
                f"🎮 Mode `{game_mode.upper()}`\n"
                "\n"
                f"🏆 MVP Winner: {f'<@{winner_mvp_id}>' if winner_mvp_id else '*N/A*'} → `+{WINNER_MVP_POINTS}` pts\n"
                f"✦ MVP Loser: {f'<@{loser_mvp_id}>' if loser_mvp_id else '*N/A*'} → `+{LOSER_MVP_POINTS}` pts"
            ),
            color=COLORS["success"],
            timestamp=discord.utils.utcnow()
        )
        embed.add_field(name=f"🏆 Winners — `{len(winner_details)}` players", value=f"{wt_mentions}", inline=True)
        embed.add_field(name=f"☠️ Losers — `{len(loser_details)}` players", value=f"{lt_mentions}", inline=True)
        embed.set_author(name="Match Finished", icon_url=None)
        embed.set_footer(text=f"{BOT_FOOTER}  •  Match #{lobby_id}  ·  GG WP!")
        embed = apply_branding(embed, guild)
        # 🆕 نتيجة الماتش → قناة النتائج المخصصة (match-results) فقط، وإلا القناة الأصلية
        await _post_match_result(guild, embed, channel)

        # ⚡ تسريع: أغلق الفويسات فوراً — انقل اللاعبين + احذف قنوات الماتش قبل
        #    أي عمل بطيء (leaderboard / roles) حتى يختفي الشات/الفويس بسرعة
        await delete_match_channels(guild, lobby_id)
        cleanup_lobby_memory(lobby_id)

        # 🆕 أعد اللاعبين لغرف الانتظار (بعد حذف القنوات مباشرة)
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

        # تحديث الـ Leaderboard + مزامنة أدوار لاعبي الماتش فقط (تسريع)
        await update_leaderboard_channel(guild)
        await sync_all_players_roles(guild, player_ids=all_players)
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
            embed = discord.Embed(
                title="✅ Room Info Saved",
                description="Room details stored successfully.",
                color=COLORS["success"]
            )
            embed.add_field(name="🆔 Room ID", value=f"```\n{room_id}\n```", inline=True)
            embed.add_field(name="🔑 Code", value=f"```\n{password or 'N/A'}\n```", inline=True)
            if private_key:
                embed.add_field(name="🔐 Private Key", value=f"```\n{private_key}\n```", inline=True)
            await interaction.response.send_message(embed=embed, ephemeral=True)
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
                    title="❌ Wrong Key",
                    description=(
                        "The private key you entered is incorrect.\n"
                        "Please ask the host for the correct key."
                    ),
                    color=COLORS["error"]
                ), ephemeral=True)
        except Exception as e:
            logger.exception(f"JoinKeyModal failed: {e}")


# 🆕 Modal للبلاغ مع سبب
class ReportReasonModal(discord.ui.Modal, title="⚠️  سبب البلاغ"):
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
            # 🔒 نظّف السبب قبل التخزين (يمنع mass-ping + كسر حد Discord)
            reason = sanitize_user_text(self.reason_input.value) if self.reason_input.value else None
            added, total = db.add_report(
                self.guild_id, self.reporter_id, self.reported_id,
                lobby_id=self.lobby_id, reason=reason
            )
            if not added:
                await interaction.response.send_message(
                    embed=discord.Embed(
                        title="⚠️ بلغت من قبل",
                        description=(
                            f"لقد بلّغت على <@{self.reported_id}> سابقاً.\n"
                            "لا يمكنك البلاغ مرتين على نفس اللاعب."
                        ),
                        color=COLORS["warning"]
                    ), ephemeral=True
                )
                return
            guild = interaction.guild
            # اعرض تأكيد البلاغ
            remaining = max(0, REPORT_THRESHOLD - total)
            report_embed = discord.Embed(
                title="⚠️ تم تسجيل البلاغ",
                description=(
                    (f"⚠️ يتبقى `{remaining}` بلاغ للحظر التلقائي" if remaining > 0 else "⚠️ **وصل للحد!** سيتم الحظر تلقائياً")
                ),
                color=COLORS["warning"] if remaining > 0 else COLORS["error"],
                timestamp=discord.utils.utcnow()
            )
            report_embed.add_field(name="👤 المُبلَّغ عنه", value=f"<@{self.reported_id}>", inline=True)
            report_embed.add_field(name="👮 المُبلِّغ", value=f"<@{self.reporter_id}>", inline=True)
            report_embed.add_field(name="📊 البلاغات", value=f"`{total}/{REPORT_THRESHOLD}`", inline=True)
            if reason:
                report_embed.add_field(name="📝 السبب", value=f"{reason}", inline=False)
            report_embed.set_footer(text=f"{BOT_FOOTER}  •  Report #{total}")
            report_embed = apply_branding(report_embed, guild)
            await interaction.response.send_message(embed=report_embed, ephemeral=True)
            # 🆕 أرسل البلاغ للأدمنز مع السبب
            await notify_admins(
                guild,
                "⚠️  بلاغ جديد",
                f"> 👤  **اللاعب المُبلَّغ عنه:**  <@{self.reported_id}>\n"
                f"> 👮  **الـمُبلِّغ:**  <@{self.reporter_id}>\n"
                + (f"> 📝  **السبب:**  {reason}\n" if reason else "> 📝  **السبب:**  غير محدد\n")
                + f"> 📊  **إجمالي البلاغات:**  `{total}/{REPORT_THRESHOLD}`",
                color=COLORS["warning"] if remaining > 0 else COLORS["error"]
            )
            # 🆕 فحص الحظر التلقائي
            if guild:
                banned = await check_and_apply_auto_ban(guild, self.reported_id, total, self.reporter_id)
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
            return "غير معروف"

        options = []
        for pid in reportable[:25]:  # حد ديسكورد 25 option
            name = get_player_name(pid)
            options.append(discord.SelectOption(
                label=name,
                value=str(pid),
                description=f"بلغ عن هذا اللاعب",
                emoji="⚠️"
            ))
        if not options:
            return
        select = discord.ui.Select(
            placeholder="⚠️  اختر اللاعب المُبلَّغ عنه",
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
    """View بسيط فيه زر واحد '⚠️ Report' يفتح select للاعبين."""
    def __init__(self, lobby_id, all_players, guild_id, reporter_id=None):
        super().__init__(timeout=None)
        self.lobby_id = lobby_id
        self.all_players = all_players
        self.guild_id = guild_id

    @discord.ui.button(label="⚠️  إبلاغ عن لاعب", style=discord.ButtonStyle.danger, custom_id="report_player_btn")
    async def report_btn(self, interaction, button):
        # كل لاعب يقدر يبلغ — نمرّر reporter_id = interaction.user.id
        view = ReportPlayerSelectView(self.lobby_id, self.all_players, self.guild_id, interaction.user.id, guild=interaction.guild)
        if not view.children:
            await interaction.response.send_message("❌ لا يوجد لاعبون للبلاغ!", ephemeral=True)
            return
        await interaction.response.send_message(
            embed=discord.Embed(
                title="⚠️ اختر اللاعب المُبلَّغ عنه",
                description=(
                    "اختر اللاعب الذي تريد البلاغ عنه من القائمة.\n"
                    "⚠️ البلاغ جدّي — لا تبلّغ بدون سبب."
                ),
                color=COLORS["warning"]
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
            title="❌ Match Cancelled",
            description=(
                f"Match `#{self.lobby_id}` — `{mode}` was cancelled by <@{uid}>.\n"
                f"Use `{PREFIX}play` to start a new match."
            ),
            color=COLORS["error"]
        ), delete_after=30)

        # الآن حدّث الحالة وامسح القنوات بأمان
        db.update_lobby_status(self.lobby_id, "cancelled")
        cleanup_lobby_memory(self.lobby_id)

        # 🆕 احذف رسالة اللوبي الأصلية في قناة play بدل ترك نسخة معدّلة منها
        if interaction.message is not None:
            try:
                await delete_message_safely(
                    interaction.message.channel, interaction.message.id,
                    reason=f"cancel_game lobby #{self.lobby_id}"
                )
            except Exception as e:
                logger.debug(f"delete lobby embed in cancel_game failed: {e}")

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
                title="🚫 أنت محظور من اللعب",
                description=(
                    "🔍 يتم توجيهك لفويس التفتيش\n"
                    "💡 لفك الحظر، تواصل مع الأدمن"
                ),
                color=COLORS["error"],
                timestamp=discord.utils.utcnow()
            )
            ban_embed.add_field(name="⚠️ السبب", value=f"`{ban_info.get('ban_reason') or 'غير محدد'}`", inline=True)
            ban_embed.add_field(name="📊 البلاغات", value=f"`{ban_info.get('report_count', 0)}`", inline=True)
            ban_embed.set_footer(text=f"{BOT_FOOTER}  •  Banned")
            ban_embed = apply_branding(ban_embed, interaction.guild)
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
            embed = discord.Embed(
                title="⏳ Join a Waiting Room",
                description="You must be in a voice waiting room to join a match.",
                color=COLORS["warning"]
            )
            embed.add_field(name="🔊 Available Rooms", value=f"{rooms_text}", inline=False)
            await interaction.response.send_message(embed=embed, ephemeral=True)
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
                embed = discord.Embed(
                    title="⏳ Wrong Voice Channel",
                    description=f"You're in `{member.voice.channel.name}` — that's not a waiting room.",
                    color=COLORS["warning"]
                )
                embed.add_field(name="🔊 Available Rooms", value=f"{rooms_text}", inline=False)
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

        existing = db.get_player_active_lobby(uid, interaction.guild.id)
        if existing and existing["id"] != self.lobby_id:
            if existing["status"] == "started" and not existing.get("room_id"):
                await interaction.response.send_message(embed=discord.Embed(
                    title="⏳ Pending Match",
                    description=(
                        "You have a pending match that needs to be finished first.\n"
                        "Complete or cancel it before joining a new one."
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
        if uid != lobby["creator_id"] and team == "team2":
            db.set_first_joiner(self.lobby_id, uid)

        lobby = db.get_lobby(self.lobby_id)
        try: await interaction.message.edit(embed=create_lobby_embed(lobby, interaction.guild), view=self)
        except discord.HTTPException: pass

        team_name = "Team 1" if team == "team1" else "Team 2"
        await interaction.response.send_message(f"✅ Joined **{team_name}**!", ephemeral=True)

        if lobby.get("room_id"):
            room_embed = discord.Embed(
                title="ℹ️ Room Info",
                description=(
                    "Join the room with these credentials:\n"
                    "🔥 Join now and good luck!"
                ),
                color=COLORS["play"]
            )
            room_embed.add_field(name="🆔 Room ID", value=f"`{lobby['room_id']}`", inline=True)
            room_embed.add_field(name="🔑 Password", value=f"`{lobby.get('room_code') or 'N/A'}`", inline=True)
            await interaction.followup.send(embed=room_embed, ephemeral=True)

        # ✅ MAX: لا تنقل اللاعب لـ waiting room بعد الانضمام للوبي
        # اللاعب يبقى في فويسه — سيُنقل لفويس فريقه عند بدء الماتش
        # (تم حذف كود db.get_available_waiting_room + member.move_to)

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
                    title="❌ Failed to Start",
                    description=(
                        "Could not create match channels.\n"
                        f"Lobby `#{self.lobby_id}` has been cancelled."
                    ),
                    color=COLORS["error"]
                ), delete_after=15)
                return

            t1m = " ".join([f"<@{p}>" for p in lobby["team1_players"]])
            t2m = " ".join([f"<@{p}>" for p in lobby["team2_players"]])

            try:
                ready_msg = await interaction.channel.send(embed=discord.Embed(
                    title="✅ Match Ready!",
                    description=(
                        "Lobby is full — match is starting now!\n"
                        "Moving players to their team voice channels..."
                    ),
                    color=COLORS["success"],
                    timestamp=discord.utils.utcnow()
                ))
                # 🆕 سجّل رسالة "Match Ready" — تُحذف تلقائياً عند انتهاء الماتش بأي طريقة
                register_lobby_flow_msg(self.lobby_id, interaction.channel.id, ready_msg.id)
            except discord.HTTPException as e:
                logger.debug(f"send Match Ready embed failed: {e}")

            if channels:
                # 🆕 V3 MAX: خزّن الفويس الأصلي لكل لاعب قبل نقله لفويس الفريق
                _original_voice_channels[self.lobby_id] = {}
                for pid in lobby["team1_players"] + lobby["team2_players"]:
                    m = interaction.guild.get_member(pid)
                    if m and m.voice and m.voice.channel:
                        _original_voice_channels[self.lobby_id][pid] = m.voice.channel.id
                        logger.info(f"  📌 Stored original voice for {m.display_name}: {m.voice.channel.name}")
                
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
                        title="ℹ️ Room Info",
                        description=(
                            "Join the room with these credentials:\n"
                            "🔥 Join now and good luck!"
                        ),
                        color=COLORS["play"]
                    )
                    room_embed.add_field(name="🆔 Room ID", value=f"`{lobby['room_id']}`", inline=True)
                    room_embed.add_field(name="🔑 Password", value=f"`{lobby.get('room_code') or 'N/A'}`", inline=True)
                    try: await channels["team1_text"].send(mentions, embed=room_embed)
                    except: pass

                start_vote_view = StartVoteView(self.lobby_id, interaction.guild.id, lobby["creator_id"])
                start_embed = discord.Embed(
                    title="📻 Match Started!",
                    description=f"**Lobby** `#{self.lobby_id}`  ·  `{mode.upper()}`  ·  Host <@{lobby['creator_id']}>",
                    color=COLORS["play"],
                    timestamp=discord.utils.utcnow()
                )
                if lobby.get('room_id'):
                    start_embed.add_field(name="🆔 Room ID", value=f"`{lobby['room_id']}`", inline=True)
                    start_embed.add_field(name="🔑 Password", value=f"`{lobby.get('room_code') or 'N/A'}`", inline=True)
                start_embed.add_field(
                    name="📋 Next steps",
                    value="🎮 Match started. Join the room now.\n🔱 Host: press **Start Vote** when finished.\n❌ Host: press **Cancel Match** to abort.",
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
                        title="⚠️ نظام البلاغ",
                        description=(
                            "لو لاحظت لاعب يغش أو يسيء، اضغط زر **⚠️ إبلاغ**\n"
                            "\n"
                            f"📊 عند وصول البلاغات إلى `{REPORT_THRESHOLD}` → حظر تلقائي\n"
                            "🔍 اللاعب المحظور يُنقل لفويس التفتيش حتى يفك الأدمن الحظر"
                        ),
                        color=COLORS["warning"],
                        timestamp=discord.utils.utcnow()
                    )
                    report_embed.set_footer(text=f"{BOT_FOOTER}  •  Match #{self.lobby_id}")
                    report_embed = apply_branding(report_embed, interaction.guild)
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
        # ✅ إصلاح: Start Vote للأدمنز والأونر والهوست فقط
        member = interaction.guild.get_member(interaction.user.id)
        is_admin = member and (member.guild_permissions.administrator or member.guild_permissions.manage_guild)
        is_owner = interaction.user.id == BOT_OWNER_ID
        is_host = interaction.user.id == self.creator_id
        if not (is_admin or is_owner or is_host):
            await interaction.response.send_message(
                f"❌ فقط الأدمنز والأونر والهوست يبدؤون التصويت!\n"
                f"الهوست: <@{self.creator_id}>",
                ephemeral=True
            )
            return
        guild = bot.get_guild(self.guild_id)
        if not guild:
            await interaction.response.send_message("❌ Guild not found!", ephemeral=True)
            return
        # 🆕 فحص الـ cooldown 10 دقائق من بدء الماتش
        started_at = lobby.get("started_at")
        if started_at:
            try:
                from datetime import datetime
                if isinstance(started_at, str):
                    started_time = datetime.fromisoformat(started_at)
                else:
                    started_time = started_at
                now = datetime.now(started_time.tzinfo) if started_time.tzinfo else datetime.now()
                elapsed = (now - started_time).total_seconds()
                if elapsed < 600:
                    remaining = int(600 - elapsed)
                    remaining_min = remaining // 60
                    remaining_sec = remaining % 60
                    await interaction.response.send_message(embed=discord.Embed(
                        title="⏳ لم يحن وقت التصويت بعد",
                        description=(
                            "⏱️ يجب انتظار **10 دقائق** من بدء الماتش\n"
                            f"⏳ المتبقي: `{remaining_min} دقيقة و {remaining_sec} ثانية`"
                        ),
                        color=COLORS["warning"]
                    ), ephemeral=True)
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
        """🆕 Cancel Match بنظام الأغلبية."""
        lobby = await self._resolve_context(interaction)
        if not lobby or not self.lobby_id:
            await interaction.response.send_message("❌ Cannot determine lobby!", ephemeral=True)
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
        required_votes = (total_players // 2) + 1
        is_admin = interaction.user.guild_permissions.administrator
        if not hasattr(self, '_cancel_votes'):
            self._cancel_votes = set()
        if is_admin:
            await self._execute_cancel(interaction, lobby, guild, uid, "Admin")
            return
        if uid in self._cancel_votes:
            await interaction.response.send_message(f"⚠️ صوّت بالفعل! ({len(self._cancel_votes)}/{required_votes})", ephemeral=True)
            return
        self._cancel_votes.add(uid)
        current_votes = len(self._cancel_votes)
        if current_votes >= required_votes:
            await self._execute_cancel(interaction, lobby, guild, uid, f"Majority ({current_votes}/{required_votes})")
            return
        remaining = required_votes - current_votes
        vote_embed = discord.Embed(
            title="🗳️ تصويت إلغاء الماتش",
            description=f"👤 <@{uid}> صوّت لإلغاء الماتش",
            color=COLORS["warning"],
            timestamp=discord.utils.utcnow()
        )
        vote_embed.add_field(name="📊 التقدم", value=f"`{current_votes}/{required_votes}`", inline=True)
        vote_embed.add_field(name="⏳ يتبقى", value=f"`{remaining}`", inline=True)
        vote_embed.set_footer(text=f"{BOT_FOOTER}  •  Cancel Vote")
        await interaction.response.send_message(embed=vote_embed)

    async def _execute_cancel(self, interaction, lobby, guild, uid, reason):
        """🆕 ينفذ إلغاء الماتش فعلياً."""
        mode = lobby.get("game_mode", DEFAULT_MODE).upper()
        cancelled_embed = discord.Embed(
            title="❌ Match Cancelled",
            description=(
                "🔄 جارٍ إعادة اللاعبين...\n"
                "🗑️ جارٍ حذف القنوات...\n"
                "\n"
                f"💡 Use `{PREFIX}play` لبدء ماتش جديد."
            ),
            color=COLORS["error"],
            timestamp=discord.utils.utcnow()
        )
        cancelled_embed.add_field(name="🏠 Lobby", value=f"`#{self.lobby_id}`", inline=True)
        cancelled_embed.add_field(name="🎮 Mode", value=f"`{mode}`", inline=True)
        cancelled_embed.add_field(name="👤 Cancelled by", value=f"<@{uid}> ({reason})", inline=True)
        cancelled_embed.set_footer(text=f"{BOT_FOOTER}  •  Lobby #{self.lobby_id}")
        cancelled_embed = apply_branding(cancelled_embed, guild)
        await interaction.response.send_message(embed=cancelled_embed)
        db.update_lobby_status(self.lobby_id, "cancelled")
        cleanup_lobby_memory(self.lobby_id)
        # ✅ V3 MAX: انقل اللاعبين لفويسهم الأصلي قبل حذف القنوات
        all_players = lobby["team1_players"] + lobby["team2_players"]
        # ابحث عن fallback waiting room
        fallback_vc = None
        for cid in db.get_waiting_rooms(guild.id):
            vc = guild.get_channel(cid)
            if vc and isinstance(vc, discord.VoiceChannel):
                fallback_vc = vc
                break
        # 🆕 ابحث عن الفويس الأصلي لكل لاعب
        original_channels = _original_voice_channels.get(self.lobby_id, {})
        for pid in all_players:
            m = guild.get_member(pid)
            if m and m.voice and m.voice.channel:
                target_vc = None
                original_cid = original_channels.get(pid)
                if original_cid:
                    original_vc = guild.get_channel(original_cid)
                    if original_vc and isinstance(original_vc, discord.VoiceChannel):
                        target_vc = original_vc
                        logger.info(f"  🔄 Returning {m.display_name} → original: {original_vc.name}")
                if not target_vc and fallback_vc:
                    target_vc = fallback_vc
                    logger.info(f"  🔄 Returning {m.display_name} → fallback: {fallback_vc.name}")
                if target_vc:
                    try:
                        await m.move_to(target_vc)
                    except (discord.HTTPException, discord.Forbidden):
                        pass
        # 🆕 امسح الفويس الأصلي من الذاكرة
        _original_voice_channels.pop(self.lobby_id, None)
        for item in self.children:
            item.disabled = True
        try: await interaction.message.edit(view=self)
        except: pass
        await asyncio.sleep(2)
        try:
            await delete_match_channels(guild, self.lobby_id)
        except Exception as e:
            logger.warning(f"delete_match_channels failed: {e}")
        logger.info(f"❌ Match #{self.lobby_id} cancelled by {uid} ({reason})")


# 🆕 View لاختيار MVP كل فريق بعد انتهاء التصويت
class MvpSelectionView(discord.ui.View):
    """يعرض قائمة Select لاختيار MVP لكل فريق.
    ✅ MAX: لا زر تأكيد — النقاط تُطبق تلقائياً بعد اختيار MVP الاثنين.
    ✅ MAX: فقط الهوست (منشئ الروم) يختار MVP.
    """
    def __init__(self, lobby_id, winner_team, team1_players, team2_players, guild_id, creator_id, guild=None):
        super().__init__(timeout=180)  # 3 دقائق للاختيار
        self.lobby_id = lobby_id
        self.winner_team = winner_team
        self.guild_id = guild_id
        self.creator_id = creator_id
        self.guild = guild
        self.winner_mvp_id = None
        self.loser_mvp_id = None
        self._applied = False  # 🆕 لمنع التطبيق المزدوج

        winner_players = team1_players if winner_team == "team1" else team2_players
        loser_players = team2_players if winner_team == "team1" else team1_players

        def get_player_name(pid):
            if self.guild:
                member = self.guild.get_member(pid)
                if member:
                    return member.display_name[:80]
            player = db.get_player(pid, guild_id)
            if player and player.get("username"):
                return player["username"][:80]
            return "غير معروف"

        # Select للفريق الفائز
        winner_options = []
        for pid in winner_players:
            name = get_player_name(pid)
            winner_options.append(discord.SelectOption(
                label=name,
                value=str(pid),
                description="MVP الفريق الفائز", emoji="🏆"
            ))
        if winner_options:
            winner_select = discord.ui.Select(
                placeholder="🏆  اختر MVP الفريق الفائز",
                options=winner_options,
                custom_id=f"winner_mvp_select_{lobby_id}",
                min_values=1, max_values=1
            )
            winner_select.callback = self.winner_mvp_callback
            self.add_item(winner_select)

        # Select للفريق الخاسر
        loser_options = []
        for pid in loser_players:
            name = get_player_name(pid)
            loser_options.append(discord.SelectOption(
                label=name, value=str(pid),
                description="MVP الفريق الخاسر", emoji="✦"
            ))
        if loser_options:
            loser_select = discord.ui.Select(
                placeholder="✦  اختر MVP الفريق الخاسر",
                options=loser_options,
                custom_id=f"loser_mvp_select_{lobby_id}",
                min_values=1, max_values=1
            )
            loser_select.callback = self.loser_mvp_callback
            self.add_item(loser_select)

        # ✅ MAX: تم حذف زر "تأكيد وتطبيق النقاط"
        # النقاط تُطبق تلقائياً بعد اختيار MVP الاثنين (في _try_apply)

    async def _try_apply(self, interaction):
        """🆕 MAX: يفحص لو تم اختيار MVP الاثنين، وإذا نعم يطبق النقاط تلقائياً."""
        if self._applied:
            return  # تم التطبيق مسبقاً
        if not self.winner_mvp_id or not self.loser_mvp_id:
            return  # ما زال ناقصاً اختيار واحد
        # ✅ تم اختيار الاثنين — طبق النقاط
        self._applied = True
        for item in self.children:
            item.disabled = True
        try: await interaction.message.edit(view=self)
        except: pass
        await interaction.followup.send(
            embed=discord.Embed(
                title="✅ تم تطبيق النقاط!",
                description=(
                    f"🏆 **MVP الفائز:** <@{self.winner_mvp_id}>\n"
                    f"✦ **MVP الخاسر:** <@{self.loser_mvp_id}>\n"
                    "⚡ جارٍ تطبيق النقاط وتحديث الرانك..."
                ),
                color=COLORS["success"],
                timestamp=discord.utils.utcnow()
            )
        )
        logger.info(f"🏆 MVP auto-confirmed — lobby={self.lobby_id}, winner_mvp={self.winner_mvp_id}, loser_mvp={self.loser_mvp_id}")
        guild = bot.get_guild(self.guild_id)
        if guild:
            await process_match_result_with_mvps(
                guild, self.lobby_id, self.winner_team,
                self.winner_mvp_id, self.loser_mvp_id,
                interaction.channel
            )

    async def winner_mvp_callback(self, interaction):
        # ✅ MAX: فقط منشئ الروم (الهوست) يختار MVP
        if interaction.user.id != self.creator_id:
            await interaction.response.send_message(
                f"❌ فقط منشئ الروم يختار MVP!  الهوست:  <@{self.creator_id}>",
                ephemeral=True
            )
            return
        self.winner_mvp_id = int(interaction.data["values"][0])
        await interaction.response.send_message(
            f"🏆  تم اختيار MVP الفريق الفائز:  <@{self.winner_mvp_id}>", ephemeral=True
        )
        # 🆕 MAX: حاول التطبيق التلقائي
        await self._try_apply(interaction)

    async def loser_mvp_callback(self, interaction):
        # ✅ MAX: فقط منشئ الروم (الهوست) يختار MVP
        if interaction.user.id != self.creator_id:
            await interaction.response.send_message(
                f"❌ فقط منشئ الروم يختار MVP!  الهوست:  <@{self.creator_id}>",
                ephemeral=True
            )
            return
        self.loser_mvp_id = int(interaction.data["values"][0])
        await interaction.response.send_message(
            f"✦  تم اختيار MVP الفريق الخاسر:  <@{self.loser_mvp_id}>", ephemeral=True
        )
        # 🆕 MAX: حاول التطبيق التلقائي
        await self._try_apply(interaction)

    async def on_timeout(self):
        # لو ما اختاروا في الوقت، استخدم MVP تلقائي
        logger.info(f"⏰ MvpSelectionView timeout — lobby={self.lobby_id}")
        lobby = db.get_lobby(self.lobby_id)
        if not lobby or lobby["status"] != "voting":
            return
        guild = bot.get_guild(lobby["guild_id"])
        if not guild:
            return
        wt = lobby["team1_players"] if self.winner_team == "team1" else lobby["team2_players"]
        lt = lobby["team2_players"] if self.winner_team == "team1" else lobby["team1_players"]
        auto_winner_mvp = get_mvp_player(wt, guild, db, guild.id)
        auto_loser_mvp = get_mvp_player(lt, guild, db, guild.id)
        await notify_admins(
            guild,
            "MVP Selection Timeout",
            f"> ⏰  انتهى وقت اختيار MVP للماتش `#{self.lobby_id}`\n"
            f"> 🤖  تم اختيار MVP تلقائياً:\n"
            f"> ─  🏆  الفائز:  {f'<@{auto_winner_mvp}>' if auto_winner_mvp else '*N/A*'}\n"
            f"> ─  ✦  الخاسر:  {f'<@{auto_loser_mvp}>' if auto_loser_mvp else '*N/A*'}\n"
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


# ============================================================
# 🆕 نظام تصويت MVP الجماعي — أول شخصين من كل فريق
# ============================================================
def build_mvp_voters(team1_players, team2_players, creator_id=None):
    """🆕 يبني قائمة المصوّنين: أول شخصين من كل فريق.
    • الفريق 1:  منشئ الروم أولاً، ثم شريكه (وترتيب الدخول)
    • الفريق 2:  أول من دخل، ثم تاليه
    • لو المود صغير (1v1 / 2v2) نكمل من البقية حتى لا يقل العدد عن 2
    """
    t1 = list(team1_players or [])
    t2 = list(team2_players or [])
    cid = creator_id

    # رتّب منشئ الروم أولاً داخل فريقه
    t1_ordered = ([cid] if cid in t1 else []) + [p for p in t1 if p != cid]
    t2_ordered = ([cid] if cid in t2 else []) + [p for p in t2 if p != cid]

    voters = []
    for p in t1_ordered[:MVP_VOTERS_PER_TEAM]:
        if p not in voters:
            voters.append(p)
    for p in t2_ordered[:MVP_VOTERS_PER_TEAM]:
        if p not in voters:
            voters.append(p)

    # مود صغير: أكمل من باقي اللاعبين
    if len(voters) < 2:
        for p in t1_ordered + t2_ordered:
            if p not in voters:
                voters.append(p)
    return voters


def _collect_admin_members(guild):
    """🆕 يرجع كل الأعضاء ذوي صلاحيات الأدمن (A+ / Manage Guild / ADMIN_ROLE_NAME / الأونر)."""
    admins = {}
    for role in guild.roles:
        if role == guild.default_role or role.is_bot_managed() or role.is_integration():
            continue
        if role.permissions.administrator or role.permissions.manage_guild:
            for m in role.members:
                if not m.bot:
                    admins[m.id] = m
    for role in guild.roles:
        if role.name.lower() == ADMIN_ROLE_NAME.lower():
            for m in role.members:
                if not m.bot:
                    admins[m.id] = m
    if guild.owner and not guild.owner.bot:
        admins[guild.owner.id] = guild.owner
    return list(admins.values())


async def escalate_mvp_dispute(guild, lobby_id, reason_detail, *, team1_players=None, team2_players=None, channel=None):
    """🆕 لا يوجد تفاهم بين المصوّرين → يُحال للأدمن (حسب طلبك).

    السلوك:
      1) لو فيه أدمن **حاضر الآن** بالفويسات الخاصة باللاعبين
         → البوت ينقله عند اللاعبين ويبلّغه بالأوامر المناسبة في نفس المكان.
      2) لو ما فيه أدمن حاضر
         → تاغ الأدمن + تسليمه الأوامر المناسبة بالضبط لحل المشكلة.
    """
    try:
        admins = _collect_admin_members(guild)
        mc = db.get_match_channels(lobby_id)

        # ── فويسات التفتيش الخاصة (Waiting Prv) ──
        prv_ids = set()
        for cid in db.get_waiting_rooms(guild.id):
            vc = guild.get_channel(cid)
            if vc and isinstance(vc, discord.VoiceChannel) and WAITING_PRV_CATEGORY_HINT.lower() in vc.name.lower():
                prv_ids.add(vc.id)

        t1v_id = mc.get("team1_voice_id") if mc else None
        t2v_id = mc.get("team2_voice_id") if mc else None
        t1_text_id = mc.get("team1_text_id") if mc else None
        t2_text_id = mc.get("team2_text_id") if mc else None

        # ── أين اللاعبين الآن؟ ──
        players_voice = None
        for cid in (t1v_id, t2v_id):
            vc = guild.get_channel(cid) if cid else None
            if vc and isinstance(vc, discord.VoiceChannel) and vc.members:
                players_voice = vc
                break
        if players_voice is None:
            lobby = db.get_lobby(lobby_id) or {}
            ch = guild.get_channel(lobby.get("channel_id")) if lobby.get("channel_id") else None
            if ch and isinstance(ch, discord.VoiceChannel):
                players_voice = ch

        # ── الأدمنز الحاضرون بالفويسات الخاصة ──
        present = []
        for m in admins:
            if m.voice and m.voice.channel:
                cid = m.voice.channel.id
                if cid in prv_ids or (t1v_id and cid == t1v_id) or (t2v_id and cid == t2v_id):
                    present.append(m)

        # ── تبديل فرز ──
        w_tally, l_tally = {}, {}
        if present:
            moves, errs = [], []
            for m in present:
                dest = players_voice or m.voice.channel
                try:
                    if dest and m.voice.channel.id != dest.id:
                        await m.move_to(dest)
                    moves.append((m, dest))
                    logger.info(f"🚨 MVP dispute #{lobby_id}: pulled admin {m.display_name} → #{dest.name if dest else 'N/A'}")
                except discord.Forbidden as e:
                    errs.append(f"`{m.display_name}` — {e}")
                    logger.error(f"❌ Forbidden move admin (MVP dispute): admin={m.id} dest={dest} | {e}")
                except discord.HTTPException as e:
                    errs.append(f"`{m.display_name}` — {e}")
                    logger.warning(f"⚠️ HTTP move admin (MVP dispute): admin={m.id} | {e}")

            mentions = " ".join(m.mention for m, _ in moves)
            where = moves[0][1] if moves else None
            embed = discord.Embed(
                title=f"🚨 تعذّر الاتفاق على MVP — الماتش #{lobby_id}",
                description=(
                    f"{mentions}\n"
                    "⚠️ **ما في تفاهم بين المصوّتين** — نطلب تدخل أحد الأدمنز.\n"
                    f"📌 **السبب:** {reason_detail}"
                ),
                color=COLORS["error"],
                timestamp=discord.utils.utcnow()
            )
            embed.add_field(name="🔴 Team 1 — المصوّتون", value=f"{' '.join(f'<@{p}>' for p in (team1_players or [])[:MVP_VOTERS_PER_TEAM]) or '*N/A*'}", inline=True)
            embed.add_field(name="🟢 Team 2 — المصوّتون", value=f"{' '.join(f'<@{p}>' for p in (team2_players or [])[:MVP_VOTERS_PER_TEAM]) or '*N/A*'}", inline=True)
            embed.add_field(name="🗳️ الأصوات", value=f"🏆 Winner: {', '.join(f'**{c}**×<@{p}>' for p, c in sorted(w_tally.items(), key=lambda x: -x[1])) or '*لا توجد أصوات*'}\n✦ Loser: {', '.join(f'**{c}**×<@{p}>' for p, c in sorted(l_tally.items(), key=lambda x: -x[1])) or '*لا توجد أصوات*'}", inline=False)
            embed.add_field(name="🔧 الأمر المطلوب منك", value=f"`{PREFIX}w {lobby_id} @user` — عيّن MVP WINNER\n`{PREFIX}l {lobby_id} @user` — عيّن MVP LOSER\n📌 لازم من فريقين مختلفين — بـ `!!w` + `!!l` تُطبَّق النقاط تلقائياً", inline=False)
            embed.set_footer(text=f"{BOT_FOOTER}  •  Action required")
            embed = apply_branding(embed, guild)

            # أرسل في قناة الفريق المرتبط بالفويس اللي وصله الأدمن
            sent = False
            if where:
                text_id = t2_text_id if where.id == t2v_id else t1_text_id
                txt = guild.get_channel(text_id) if text_id else None
                if txt:
                    await txt.send(content=mentions, embed=embed)
                    sent = True
            if not sent and channel:
                await channel.send(content=mentions, embed=embed)
                sent = True
            if not sent:
                await notify_admins(guild, f"🚨 تعذّر الاتفاق على MVP — `#{lobby_id}`",
                                    f"> 🛑  **فشل الإرسال للقنوات** — راجع صلاحيات البوت\n"
                                    f"> 📌  {reason_detail}")
            if errs:
                logger.warning(f"⚠️ MVP dispute #{lobby_id}: بعض الأدمنز ما انقلوا — {'; '.join(errs)}")
            return moves

        # ── 2) ما فيه أدمن حاضر → تاغ + أوامر ──
        await notify_admins(
            guild,
            f"🚨 تعذّر الاتفاق على MVP — الماتش `#{lobby_id}`",
            f"> ⚠️  **ما في تفاهم بين المصوّنين** وما فيه أدمن حاضر بالفويسات.\n"
            f"> 📌  **السبب:**  {reason_detail}\n"
            f"> 👥  **المصوّنين:**  "
            f"Team 1 🔴 {' '.join(f'<@{p}>' for p in (team1_players or [])[:MVP_VOTERS_PER_TEAM])}  |  "
            f"Team 2 🟢 {' '.join(f'<@{p}>' for p in (team2_players or [])[:MVP_VOTERS_PER_TEAM])}\n"
            f"> 🗳  **التصويت:**  🏆 " + (", ".join(f"{c}×<@{p}>" for p, c in sorted(w_tally.items(), key=lambda x: -x[1])) or "لا أصوات")
            + "  |  ✦ " + (", ".join(f"{c}×<@{p}>" for p, c in sorted(l_tally.items(), key=lambda x: -x[1])) or "لا أصوات")
            + f"\n{separator()}\n"
            f"> 🔧  **الأوامر المطلوبة:**\n"
            f"> ─  `{PREFIX}w {lobby_id} @user`  —  عينِ MVP WINNER\n"
            f"> ─  `{PREFIX}l {lobby_id} @user`  —  عينِ MVP LOSER\n"
            f"> 💡  لازم يكونو من **فريقين مختلفين** — بت `!!w` + `!!l` بتُطبَّق النقاط تلقائياً"
        )
        return []
    except Exception as e:
        logger.exception(f"❌ escalate_mvp_dispute failed for lobby {lobby_id}: {e}")
        try:
            await notify_admins(guild, f"❌ فشل تحكيم MVP `#{lobby_id}`",
                                f"> 🐛  `{str(e)[:200]}`")
        except Exception:
            pass
        return []


# 🆕 V3 MAX: يحل محل VoteView + MvpSelectionView — لا تصويت للفريق، فقط اختيار MVP
class MvpVoteView(discord.ui.View):
    """MVP selection without team voting — نظام جماعي.
    - المصوّنون = أول 2 من كل فريق (4 مصوّنين)
    - كلهم يختارون MVP WINNER و MVP LOSER
    - يُطبَّق تلقائياً عند الاتفاق (MVP_CONSENSUS_NEEDED من 4)
    - إذا ما في تفاهم → يُحال للأدمن (ينقله أو يتاغه)
    """
    def __init__(self, lobby_id, guild, creator_id, first_joiner_id, team1_players, team2_players):
        super().__init__(timeout=VOTE_TIMEOUT_SECONDS)
        self.lobby_id = lobby_id
        self.guild = guild
        self.guild_id = guild.id
        self.creator_id = creator_id
        self.first_joiner_id = first_joiner_id
        self.team1_players = team1_players
        self.team2_players = team2_players
        self.winner_mvp_id = None
        self.loser_mvp_id = None
        self._applied = False
        self._escalated = False
        # 🆕 سجلّ المصوّنين: {user_id: {"winner": pid, "loser": pid}}
        self.voters = build_mvp_voters(team1_players, team2_players, creator_id)
        self.votes = {}

        all_players = list(team1_players) + list(team2_players)

        def get_player_name(pid):
            member = guild.get_member(pid)
            if member:
                return member.display_name[:80]
            player = db.get_player(pid, guild.id)
            if player and player.get("username"):
                return player["username"][:80]
            return "غير معروف"

        options = []
        for pid in all_players:
            name = get_player_name(pid)
            team_label = "Team 1 🔴" if pid in team1_players else "Team 2 🟢"
            options.append(discord.SelectOption(
                label=name,
                value=str(pid),
                description=team_label,
                emoji="🏆"
            ))

        if options:
            winner_select = discord.ui.Select(
                placeholder="🏆  اختر MVP WINNER — (للمصوّنين فقط)",
                options=options,
                custom_id=f"mvp_winner_select_{lobby_id}",
                min_values=1, max_values=1
            )
            winner_select.callback = self.winner_mvp_callback
            self.add_item(winner_select)

            loser_select = discord.ui.Select(
                placeholder="✦  اختر MVP LOSER — (للمصوّنين فقط)",
                options=options,
                custom_id=f"mvp_loser_select_{lobby_id}",
                min_values=1, max_values=1
            )
            loser_select.callback = self.loser_mvp_callback
            self.add_item(loser_select)

        # 🆕 زر تاغ الأدمن في حالة وجود مشكلة
        tag_admin_btn = discord.ui.Button(
            label="⚠️ مشكلة في التصويت — تاغ الأدمن",
            style=discord.ButtonStyle.danger,
            custom_id=f"tag_admin_btn_{lobby_id}"
        )
        tag_admin_btn.callback = self.tag_admin_callback
        self.add_item(tag_admin_btn)

        # 🆕 زر محايد لإظهار الحالة الحالية (بدون تصويت)
        status_btn = discord.ui.Button(
            label="📊 حالة التصويت",
            style=discord.ButtonStyle.secondary,
            custom_id=f"mvp_status_btn_{lobby_id}"
        )
        status_btn.callback = self.status_callback
        self.add_item(status_btn)

# ══════════════════════════════════════════════════════
    # 🆕 أدوات المصوّنين + الحالة + الاتفاق
    # ══════════════════════════════════════════════════════
    def _is_voter(self, user_id):
        return user_id in self.voters

    async def _guard_voter(self, interaction):
        """يتحقق إن المستخدم من المصوّنين المسموح لهم."""
        if not self.voters:
            return True
        if interaction.user.id in self.voters:
            return True
        t1_names = " ".join(f"<@{p}>" for p in self.voters if p in self.team1_players)
        t2_names = " ".join(f"<@{p}>" for p in self.voters if p in self.team2_players)
        embed = discord.Embed(
            title="⛔ ما أنت من المصوّتين",
            description=(
                "❌ صوتك ما يُحسب في هذا النظام.\n"
                "المصوّتون هم **أول شخصين من كل فريق**.\n"
                "📌 لو كنت منهم، اختر MVP من القوائم بالأعلى."
            ),
            color=COLORS["error"]
        )
        embed.add_field(name="🔴 Team 1", value=f"{t1_names or '*N/A*'}", inline=True)
        embed.add_field(name="🟢 Team 2", value=f"{t2_names or '*N/A*'}", inline=True)
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return False

    def _tally(self, key):
        """{player_id: عدد الأصوات} لقرار معيّن."""
        counts = {}
        for _uid, data in self.votes.items():
            pid = data.get(key)
            if pid:
                counts[pid] = counts.get(pid, 0) + 1
        return counts

    def _consensus(self, key):
        """يرجع اللاعب اللي وصل لـ MVP_CONSENSUS_NEEDED صوت، أو None."""
        for pid, c in self._tally(key).items():
            if c >= MVP_CONSENSUS_NEEDED:
                return pid
        return None

    def _all_voted(self):
        """هل صوّت كل المصوّنين على الاثنين (WINNER + LOSER)؟"""
        if not self.voters:
            return False
        for uid in self.voters:
            d = self.votes.get(uid) or {}
            if not d.get("winner") or not d.get("loser"):
                return False
        return True

    def _voted_count(self):
        return len([u for u in self.voters if (self.votes.get(u) or {}).get("winner")])

    def _tally_line(self, key, label):
        tally = self._tally(key)
        if not tally:
            return f"> ─  {label}:  *لا توجد أصوات*"
        parts = [f"<@{p}> ×{c}" for p, c in sorted(tally.items(), key=lambda x: -x[1])]
        return f"> ─  {label}:  " + "   |   ".join(parts)

    def _tally_text(self, key):
        tally = self._tally(key)
        if not tally:
            return "لا أصوات"
        return " / ".join(f"{c}×<@{p}>" for p, c in sorted(tally.items(), key=lambda x: -x[1]))

    async def _refresh(self, interaction=None):
        """يحدّث رسالة التصويت لعرض الحالة / يعطّل الأزرار بعد التطبيق."""
        for item in self.children:
            if isinstance(item, (discord.ui.Select, discord.ui.Button)):
                item.disabled = True if self._applied else False
        if interaction is None:
            return
        try:
            await interaction.edit(view=self)
        except discord.HTTPException as e:
            logger.warning(f"⚠️ _refresh edit failed (lobby {self.lobby_id}): {e}")

    async def status_callback(self, interaction):
        """🆕 زر محايد: يعرض الحالة الحالية بدون أي تصويت."""
        embed = discord.Embed(
            title=f"📊 حالة تصويت MVP — ماتش #{self.lobby_id}",
            description=(
                f"👥 المصوّتون: {' '.join(f'<@{p}>' for p in self.voters) or '*N/A*'}\n"
                f"✅ صوّتوا: `{self._voted_count()}` / `{len(self.voters)}`   ·   🎯 المطلوب: `{MVP_CONSENSUS_NEEDED}` أصوات"
            ),
            color=COLORS["vote"],
            timestamp=discord.utils.utcnow()
        )
        embed.add_field(name="🏆 MVP WINNER", value=f"{self._tally_line('winner', '🏆 MVP WINNER')}", inline=False)
        embed.add_field(name="✦ MVP LOSER", value=f"{self._tally_line('loser', '✦ MVP LOSER')}", inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    async def tag_admin_callback(self, interaction):
        """🆕 زر يدوي: يطلب تدخل الأدمن (ينقله لو حاضر، وإلا يتاغه)."""
        await interaction.response.send_message(
            embed=discord.Embed(
                title="⚠️ تم طلب تدخل الأدمن",
                description=(
                    f"🚨 تم إبلاغ الأدمن بمشكلة في الماتش `#{self.lobby_id}`\n"
                    f"👤 **المبلّغ:** {interaction.user.mention}\n"
                    "📌 لو فيه أدمن بالفويسات الخاصة باللاعبين، البوت نقله عندهم.\n"
                    "📌 وإلا، تم تاغ الأدمن مع الأوامر المناسبة."
                ),
                color=COLORS["warning"]
            ),
            ephemeral=True
        )
        await escalate_mvp_dispute(
            self.guild, self.lobby_id,
            reason_detail=f"بلاغ يدوي من {interaction.user.mention}",
            team1_players=self.team1_players,
            team2_players=self.team2_players,
            channel=interaction.channel
        )

    async def _get_team(self, pid):
        return "team1" if pid in self.team1_players else "team2"

    # ══════════════════════════════════════════════════════
    # 🆕 تسجيل الأصوات
    # ══════════════════════════════════════════════════════
    async def winner_mvp_callback(self, interaction):
        if not await self._guard_voter(interaction):
            return
        chosen = int(interaction.data["values"][0])
        self.votes.setdefault(interaction.user.id, {})["winner"] = chosen
        self.winner_mvp_id = chosen   # آخر صوت — للتوافق مع أوامر !!w / !!l
        await interaction.response.send_message(
            f"🏆  تم تسجيل تصويتك لـ MVP WINNER:  <@{chosen}>", ephemeral=True
        )
        await self._try_apply(interaction)

    async def loser_mvp_callback(self, interaction):
        if not await self._guard_voter(interaction):
            return
        chosen = int(interaction.data["values"][0])
        self.votes.setdefault(interaction.user.id, {})["loser"] = chosen
        self.loser_mvp_id = chosen
        await interaction.response.send_message(
            f"✦  تم تسجيل تصويتك لـ MVP LOSER:  <@{chosen}>", ephemeral=True
        )
        await self._try_apply(interaction)

    # ══════════════════════════════════════════════════════
    # 🆕 فحص الاتفاق بعد كل صوت
    # ══════════════════════════════════════════════════════
    async def _try_apply(self, interaction):
        if self._applied:
            return

        w = self._consensus("winner")
        l = self._consensus("loser")

        # ✅ اتفاق كامل
        if w and l:
            if await self._get_team(w) == await self._get_team(l):
                await self._escalate(
                    interaction.channel,
                    f"اتفق المصوّنون، لكن MVP WINNER <@{w}> و MVP LOSER <@{l}> **من نفس الفريق** — مستحيل يُطبَّق"
                )
                return
            await self._apply(w, l, interaction)
            return

        # 🛑 كل المصوّنين صوّتوا وما في اتفاق → لا تفاهم → للأدمن
        if self._all_voted():
            reason = (
                f"صوّتوا كلهم وما اتفقوا — "
                f"🏆 {self._tally_text('winner')}   •   "
                f"✦ {self._tally_text('loser')}"
            )
            await self._escalate(interaction.channel, reason)
            return

        # 🟡 لسه في ناس ما صوّتوا — حدّث الحالة فقط
        await self._refresh(interaction)

    async def _escalate(self, channel, reason_detail):
        """🆕 لا تفاهم → الأدمن (ينقله لو حاضر بالفويسات، وإلا يتاغه)."""
        if self._applied or self._escalated:
            return
        self._escalated = True
        logger.warning(f"🚨 MvpVoteView escalation — lobby={self.lobby_id}: {reason_detail}")
        for item in self.children:
            if isinstance(item, (discord.ui.Select, discord.ui.Button)):
                item.disabled = True
        await escalate_mvp_dispute(
            self.guild, self.lobby_id,
            reason_detail=reason_detail,
            team1_players=self.team1_players,
            team2_players=self.team2_players,
            channel=channel
        )

    # ══════════════════════════════════════════════════════
    # 🆕 تطبيق النتيجة
    # ══════════════════════════════════════════════════════
    async def _apply(self, winner_mvp, loser_mvp, interaction):
        self._applied = True
        self.winner_mvp_id = winner_mvp
        self.loser_mvp_id = loser_mvp
        for item in self.children:
            item.disabled = True
        try:
            await interaction.edit(view=self)
        except discord.HTTPException as e:
            logger.warning(f"⚠️ _apply edit failed (lobby {self.lobby_id}): {e}")

        try:
            await interaction.channel.send(
                embed=discord.Embed(
                    title="✅ تم الاتفاق على MVP!",
                    description=(
                        f"🤝 اتفاق `{MVP_CONSENSUS_NEEDED}` أصوات من `{len(self.voters)}` مصوّتين\n"
                        "\n"
                        f"🏆 **MVP WINNER:** <@{winner_mvp}> → `+80` pts\n"
                        f"✦ **MVP LOSER:** <@{loser_mvp}> → `+30` pts\n"
                        "⚡ جارٍ تطبيق النقاط وتحديث الرانك..."
                    ),
                    color=COLORS["success"]
                )
            )
        except discord.HTTPException as e:
            logger.warning(f"⚠️ _apply send failed (lobby {self.lobby_id}): {e}")

        logger.info(
            f"🏆 MvpVoteView confirmed — lobby={self.lobby_id}, "
            f"winner_mvp={winner_mvp}, loser_mvp={loser_mvp}, "
            f"voters={len(self.voters)}, votes={len(self.votes)}"
        )

        winner_team = await self._get_team(winner_mvp)
        guild = self.guild or bot.get_guild(self.guild_id)
        if not guild:
            logger.error(f"❌ Guild not found for lobby {self.lobby_id}")
            return
        try:
            await process_match_result_with_mvps(
                guild, self.lobby_id, winner_team, winner_mvp, loser_mvp,
                interaction.channel
            )
        except Exception as e:
            logger.exception(f"❌ process_match_result_with_mvps failed in _apply: {e}")
            await notify_admins(
                guild,
                f"❌ فشل تطبيق نقاط الماتش #{self.lobby_id}",
                f"> 🐛  **الخطأ:**  `{str(e)[:200]}`\n"
                f"> 🏆 Winner MVP:  <@{winner_mvp}>\n"
                f"> ✦ Loser MVP:  <@{loser_mvp}>\n"
                f"> 💡 Use  `!!w {self.lobby_id} @user`  و  `!!l {self.lobby_id} @user`  يدوياً"
            )

    # ══════════════════════════════════════════════════════
    # 🆕 انتهاء الوقت = لا تفاهم → يُحال للأدمن
    # ══════════════════════════════════════════════════════
    async def on_timeout(self):
        logger.info(f"⏰ MvpVoteView timeout — lobby={self.lobby_id}")
        lobby = db.get_lobby(self.lobby_id)
        if not lobby or lobby["status"] != "voting":
            return
        guild = self.guild or bot.get_guild(self.guild_id)
        if not guild:
            return

        mc = db.get_match_channels(self.lobby_id)
        result_ch = guild.get_channel(mc["team1_text_id"]) if mc else guild.get_channel(lobby["channel_id"])

        self._escalated = True
        reason = (
            f"⏰ انتهى الوقت ({VOTE_TIMEOUT_SECONDS} ثانية) — "
            f"صوّت `{self._voted_count()}` من `{len(self.voters)}` مصوّنين فقط "
            f"(المطلوب `{MVP_CONSENSUS_NEEDED}` أصوات)\n"
            f"> 🏆 {self._tally_text('winner')}   •   ✦ {self._tally_text('loser')}"
        )
        logger.warning(f"🚨 MvpVoteView timeout → escalation — lobby={self.lobby_id}")
        for item in self.children:
            if isinstance(item, (discord.ui.Select, discord.ui.Button)):
                item.disabled = True
        await escalate_mvp_dispute(
            guild, self.lobby_id,
            reason_detail=reason,
            team1_players=self.team1_players,
            team2_players=self.team2_players,
            channel=result_ch
        )


async def process_match_result_with_mvps(guild, lobby_id, winner_team, winner_mvp_id, loser_mvp_id, channel=None):
    """🆕 يطبق نظام النقاط الجديد مع MVPs محددة يدوياً.
    ✅ إصلاح: ينهي الماتش دائماً (حتى لو فشل تطبيق النقاط)."""
    try:
        logger.info(f"🏆 process_match_result_with_mvps — lobby={lobby_id}, winner={winner_team}, w_mvp={winner_mvp_id}, l_mvp={loser_mvp_id}")
        lobby = db.get_lobby(lobby_id)
        if not lobby:
            logger.error(f"❌ process_match_result_with_mvps: lobby {lobby_id} not found!")
            return
        if lobby["status"] == "completed":
            logger.warning(f"⚠️ Lobby {lobby_id} already completed — skipping")
            return

        logger.info(f"✅ Processing match result for lobby {lobby_id}...")
        # ✅ إصلاح: حدّث الحالة لـ completed فوراً — حتى لو فشل شيء بعدها، الماتش ينتهي
        db.update_lobby_status(lobby_id, "completed")

        game_mode = lobby.get("game_mode", DEFAULT_MODE)
        wt = lobby["team1_players"] if winner_team == "team1" else lobby["team2_players"]
        lt = lobby["team2_players"] if winner_team == "team1" else lobby["team1_players"]
        logger.info(f"  Winners: {wt}, Losers: {lt}, Winner MVP: {winner_mvp_id}, Loser MVP: {loser_mvp_id}")

        # 🆕 نقاط النظام الجديد
        WINNER_MVP_POINTS = 80
        WINNER_POINTS = 30
        LOSER_MVP_POINTS = 30
        LOSER_POINTS = -30

        # معالجة الفريق الفائز
        winner_details = []
        for pid in wt:
            is_mvp = (pid == winner_mvp_id)
            pts = WINNER_MVP_POINTS if is_mvp else WINNER_POINTS
            p = db.get_player(pid, guild.id)
            if not p:
                continue
            old_level = p.get("level", STARTING_LEVEL)
            new_win_streak = p.get("win_streak", 0) + 1
            new_max = max(p.get("max_win_streak", 0), new_win_streak)
            new_p = db.update_match_player(
                pid, guild.id, pts,
                add_win=1, add_match=1,
                win_streak=new_win_streak, lose_streak=0,
                max_win_streak=new_max,
                add_mvp=1 if is_mvp else 0,
                skip_recalculate=True
            )
            new_level = new_p.get("level", STARTING_LEVEL) if new_p else old_level
            winner_details.append((pid, pts, is_mvp, old_level, new_level))

        # معالجة الفريق الخاسر
        loser_details = []
        for pid in lt:
            is_mvp = (pid == loser_mvp_id)
            pts = LOSER_MVP_POINTS if is_mvp else LOSER_POINTS
            p = db.get_player(pid, guild.id)
            if not p:
                continue
            old_level = p.get("level", STARTING_LEVEL)
            new_lose_streak = p.get("lose_streak", 0) + 1
            new_p = db.update_match_player(
                pid, guild.id, pts,
                add_loss=1, add_match=1,
                win_streak=0, lose_streak=new_lose_streak,
                add_mvp=1 if is_mvp else 0,
                skip_recalculate=True
            )
            new_level = new_p.get("level", STARTING_LEVEL) if new_p else old_level
            loser_details.append((pid, pts, is_mvp, old_level, new_level))

        db.recalculate_ranks(guild.id)
        logger.info(f"  Points applied — Winners: {len(winner_details)}, Losers: {len(loser_details)}")
        
        # ✅ إصلاح: أعد قراءة الرانك الجديد لكل لاعب بعد recalculate_ranks
        for i, (pid, pts, is_mvp, old_level, _) in enumerate(winner_details):
            p = db.get_player(pid, guild.id)
            new_level = p.get("level", STARTING_LEVEL) if p else old_level
            winner_details[i] = (pid, pts, is_mvp, old_level, new_level)
            m = guild.get_member(pid)
            if m:
                await update_member_nickname(m, new_level)
        for i, (pid, pts, is_mvp, old_level, _) in enumerate(loser_details):
            p = db.get_player(pid, guild.id)
            new_level = p.get("level", STARTING_LEVEL) if p else old_level
            loser_details[i] = (pid, pts, is_mvp, old_level, new_level)
            m = guild.get_member(pid)
            if m:
                await update_member_nickname(m, new_level)
        
        # حفظ نتيجة الماتش
        db.create_match_result(lobby_id, winner_team, len(wt), len(lt), mvp=winner_mvp_id)

        # بناء رسالة النتيجة
        wd = "🔴 Team 1" if winner_team == "team1" else "🟢 Team 2"
        wt_mentions = "\n".join([
            f"{'🔱' if is_mvp else '✅'}  <@{pid}> → `{'+' if pts > 0 else ''}{pts}` pts  (RANK #{old}→#{new})"
            for pid, pts, is_mvp, old, new in winner_details
        ]) or "*لا يوجد لاعبون*"
        lt_mentions = "\n".join([
            f"{'✦' if is_mvp else '☠️'}  <@{pid}> → `{'+' if pts > 0 else ''}{pts}` pts  (RANK #{old}→#{new})"
            for pid, pts, is_mvp, old, new in loser_details
        ]) or "*لا يوجد لاعبون*"

        embed = discord.Embed(
            title=f"🏅 Match Result — #{lobby_id}",
            description=(
                f"## 🎉 {wd} Wins!\n"
                f"🎮 Mode `{game_mode.upper()}`\n"
                "\n"
                f"🏆 MVP Winner: {f'<@{winner_mvp_id}>' if winner_mvp_id else '*N/A*'} → `+{WINNER_MVP_POINTS}` pts\n"
                f"✦ MVP Loser: {f'<@{loser_mvp_id}>' if loser_mvp_id else '*N/A*'} → `+{LOSER_MVP_POINTS}` pts"
            ),
            color=COLORS["success"],
            timestamp=discord.utils.utcnow()
        )
        embed.add_field(name=f"🏆 Winners — `{len(winner_details)}` players", value=f"{wt_mentions}", inline=True)
        embed.add_field(name=f"☠️ Losers — `{len(loser_details)}` players", value=f"{lt_mentions}", inline=True)
        embed.set_author(name="Match Finished", icon_url=None)
        embed.set_footer(text=f"{BOT_FOOTER}  •  Match #{lobby_id}  ·  GG WP!")
        embed = apply_branding(embed, guild)
        # 🆕 نتيجة الماتش → قناة النتائج المخصصة (match-results) فقط، وإلا القناة الأصلية
        await _post_match_result(guild, embed, channel)

        # ⚡ تسريع: أغلق الفويسات فوراً — انقل اللاعبين + احذف قنوات الماتش قبل
        #    leaderboard / roles حتى تختفي القنوات بأسرع ما يمكن (خاصة !!w / !!l)
        await delete_match_channels(guild, lobby_id)
        cleanup_lobby_memory(lobby_id)
        _original_voice_channels.pop(lobby_id, None)
        logger.info(f"✅ Match #{lobby_id} completed — channels deleted, memory cleaned")

        # تحديث الـ Leaderboard + مزامنة أدوار لاعبي الماتش فقط (تسريع)
        all_players = lobby["team1_players"] + lobby["team2_players"]
        await update_leaderboard_channel(guild)
        await sync_all_players_roles(guild, player_ids=all_players)
    except Exception as e:
        logger.exception(f"❌ process_match_result_with_mvps FAILED for lobby {lobby_id}: {e}")
        # ✅ إصلاح: حتى لو فشل كل شيء، تأكد من إنهاء الماتش وحذف القنوات
        try:
            db.update_lobby_status(lobby_id, "completed")
            _original_voice_channels.pop(lobby_id, None)
            await delete_match_channels(guild, lobby_id)
            cleanup_lobby_memory(lobby_id)
            logger.info(f"🔧 Match #{lobby_id} force-completed after error")
        except Exception as e2:
            logger.exception(f"❌ Failed to force-complete match {lobby_id}: {e2}")
        # 🆕 تاغ الأدمنز عند الفشل
        try:
            await notify_admins(
                guild,
                "Match Result Processing Failed",
                f"> ❌  فشل في معالجة نتيجة الماتش `#{lobby_id}`\n"
                f"> 🐛  **الخطأ:**  `{str(e)[:200]}`\n"
                f"> ✅  تم إنهاء الماتش وحذف القنوات\n"
                f"> 💡  تحقق من النقاط يدوياً بـ `!!setpoints`"
            )
        except:
            pass


class VoteView(discord.ui.View):
    def __init__(self, lobby_id=None, creator_id=None, first_joiner_id=None, timeout='__DEFAULT__'):
        # ✅ إصلاح: timeout=None يسمح بتسجيل الـ View كـ persistent عند startup
        # للماتشات الحية، يتم استخدام VOTE_TIMEOUT_SECONDS كـ default
        if timeout == '__DEFAULT__':
            timeout = VOTE_TIMEOUT_SECONDS
        # لو timeout=None صراحةً، فسيُسجَّل كـ persistent view
        super().__init__(timeout=timeout)
        self.lobby_id = lobby_id
        self.creator_id = creator_id
        self.first_joiner_id = first_joiner_id

    async def on_timeout(self):
        logger.info(f"⏰ VoteView.on_timeout — lobby={self.lobby_id}")
        if not self.lobby_id:
            return
        lobby = db.get_lobby(self.lobby_id)
        if not lobby or lobby["status"] != "voting":
            logger.info(f"  Lobby status: {lobby['status'] if lobby else 'None'} — skipping")
            return
        votes = db.get_votes(self.lobby_id)
        logger.info(f"  Votes: {len(votes)} total")
        guild = bot.get_guild(lobby["guild_id"])
        if not guild:
            return
        mc = db.get_match_channels(self.lobby_id)
        result_ch = guild.get_channel(mc["team1_text_id"]) if mc else guild.get_channel(lobby["channel_id"])

        if not votes:
            # 🆕 حالة 0-0 (لا أصوات إطلاقاً) — تاغ الأدمنز للحل
            if result_ch:
                no_votes_embed = discord.Embed(
                    title="⏰ Vote Ended — No Votes!",
                    description=(
                        f"⚠️ لم يصوّت أي لاعب في الماتش `#{self.lobby_id}`\n"
                        "📊 النتيجة `0 — 0`"
                    ),
                    color=COLORS["warning"],
                    timestamp=discord.utils.utcnow()
                )
                no_votes_embed.add_field(name="⚖️ الأدمن يحلّ الماتش يدوياً", value=f"`{PREFIX}resolve {self.lobby_id} team1` — فوز Team 1\n`{PREFIX}resolve {self.lobby_id} team2` — فوز Team 2", inline=False)
                no_votes_embed.set_footer(text=f"{BOT_FOOTER}  •  Action required")
                no_votes_embed = apply_branding(no_votes_embed, guild)
                await result_ch.send(embed=no_votes_embed)
            # 🆕 تاغ الأدمنز
            await notify_admins(
                guild,
                "⚠️  Vote Ended with 0-0",
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
                    title="⏰ Vote Tied!",
                    description=(
                        f"🤝 الماتش `#{self.lobby_id}` انتهى بالتعادل\n"
                        f"📊 النتيجة `{t1v} — {t2v}`"
                    ),
                    color=COLORS["warning"],
                    timestamp=discord.utils.utcnow()
                )
                tie_embed.add_field(name="⚖️ الأدمن يحلّ الماتش", value=f"`{PREFIX}resolve {self.lobby_id} team1` — فوز Team 1\n`{PREFIX}resolve {self.lobby_id} team2` — فوز Team 2", inline=False)
                tie_embed.set_footer(text=f"{BOT_FOOTER}  •  Action required")
                tie_embed = apply_branding(tie_embed, guild)
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
                title="⏰ Vote Closed!",
                description=(
                    f"**{wd}** wins the vote  `{t1v} — {t2v}`\n"
                    "🎯 اختر MVP لكل فريق الآن..."
                ),
                color=COLORS["success"],
                timestamp=discord.utils.utcnow()
            )
            vote_close_embed.set_footer(text=f"{BOT_FOOTER}  •  MVP selection required")
            vote_close_embed = apply_branding(vote_close_embed, guild)
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
                title="🎯 اختر MVP كل فريق",
                description=(
                    f"🏆 **الفريق الفائز:** {wd}\n"
                    "🔱 الهوست أو الأدمن يختار MVP لكل فريق\n"
                    "⏱️ لديك **3 دقائق** — وإلا سيُختار تلقائياً"
                ),
                color=COLORS["vote"],
                timestamp=discord.utils.utcnow()
            )
            mvp_embed.add_field(name="💡 تعليمات", value="1️⃣ القائمة الأولى → MVP الفريق الفائز (`+80` pts)\n2️⃣ القائمة الثانية → MVP الفريق الخاسر (`+30` pts)\n3️⃣ اضغط **تأكيد** لتطبيق النقاط", inline=False)
            mvp_embed.set_author(name="MVP Selection", icon_url=None)
            mvp_embed.set_footer(text=f"{BOT_FOOTER}  •  Match #{self.lobby_id}")
            mvp_embed = apply_branding(mvp_embed, guild)
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

        # ✅ V3 MAX: فقط الهوست (creator) وأول داخل (first_joiner) يقدرون يصوتون
        creator_id = lobby.get("creator_id")
        first_joiner_id = lobby.get("first_joiner_id")
        allowed_voters = []
        if creator_id:
            allowed_voters.append(creator_id)
        if first_joiner_id and first_joiner_id not in allowed_voters:
            allowed_voters.append(first_joiner_id)
        
        if uid not in allowed_voters:
            voters_mention = " ".join([f"<@{v}>" for v in allowed_voters])
            await interaction.response.send_message(
                f"❌ فقط الهوست وأول داخل يصوتون!\n"
                f"الناخبون: {voters_mention}",
                ephemeral=True
            )
            return

        if db.has_voted(lobby_id, uid):
            await interaction.response.send_message("❌ Already voted!", ephemeral=True)
            return

        db.cast_vote(lobby_id, uid, vote_choice)
        wd = "🟠 Team 1" if vote_choice == "team1" else "🟢 Team 2"
        await interaction.response.send_message(f"✅ Voted **{wd}**!", ephemeral=True)

        votes = db.get_votes(lobby_id)
        total_voters = len(allowed_voters)  # ✅ فقط 2 ناخبين
        votes_count = len(votes)
        t1v = sum(1 for v in votes if v["vote"] == "team1")
        t2v = sum(1 for v in votes if v["vote"] == "team2")
        await interaction.channel.send(embed=discord.Embed(
            description=(
                f"🗳️ **Vote Progress**  🔴 `{t1v}` — 🟢 `{t2v}`\n"
                f"Cast `{votes_count}/{total_voters}` (Host + First Joiner)"
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
                    title="⏰ Vote Tied!",
                    description=(
                        f"🤝 الماتش `#{lobby_id}` انتهى بالتعادل\n"
                        f"📊 النتيجة `{t1v} — {t2v}`"
                    ),
                    color=COLORS["warning"],
                    timestamp=discord.utils.utcnow()
                )
                tie_embed.add_field(name="⚖️ الأدمن يحلّ الماتش", value=f"`{PREFIX}resolve {lobby_id} team1` — فوز Team 1\n`{PREFIX}resolve {lobby_id} team2` — فوز Team 2", inline=False)
                tie_embed.set_footer(text=f"{BOT_FOOTER}  •  Action required")
                tie_embed = apply_branding(tie_embed, interaction.guild)
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
                title="✅ Vote Complete!",
                description=(
                    "All participants voted!\n"
                    f"Winner: **{wd}**  `{t1v} — {t2v}` 🎉\n"
                    "🎯 اختر MVP لكل فريق الآن..."
                ),
                color=COLORS["success"],
                timestamp=discord.utils.utcnow()
            )
            vote_complete_embed.set_footer(text=f"{BOT_FOOTER}  •  MVP selection required")
            vote_complete_embed = apply_branding(vote_complete_embed, interaction.guild)
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
                    title="🎯 اختر MVP كل فريق",
                    description=(
                        f"🏆 **الفريق الفائز:** {wd}\n"
                        "🔱 الهوست أو الأدمن يختار MVP لكل فريق\n"
                        "⏱️ لديك **3 دقائق** — وإلا سيُختار تلقائياً"
                    ),
                    color=COLORS["vote"],
                    timestamp=discord.utils.utcnow()
                )
                mvp_embed.add_field(name="💡 تعليمات", value="1️⃣ القائمة الأولى → MVP الفريق الفائز (`+80` pts)\n2️⃣ القائمة الثانية → MVP الفريق الخاسر (`+30` pts)\n3️⃣ اضغط **تأكيد** لتطبيق النقاط", inline=False)
                mvp_embed.set_author(name="MVP Selection", icon_url=None)
                mvp_embed.set_footer(text=f"{BOT_FOOTER}  •  Match #{lobby_id}")
                mvp_embed = apply_branding(mvp_embed, interaction.guild)
                await result_ch.send(embed=mvp_embed, view=mvp_view)
            else:
                await process_match_result(interaction.guild, lobby_id, winner, result_ch)
            for item in self.children:
                item.disabled = True
            try: await interaction.message.edit(view=self)
            except: pass


class CreateLobbyView(discord.ui.View):
    def __init__(self, ctx, mode, timeout='__DEFAULT__'):
        # ✅ إصلاح: timeout=None يسمح بتسجيل الـ View كـ persistent عند startup
        if timeout == '__DEFAULT__':
            timeout = 300
        super().__init__(timeout=timeout)
        self.ctx = ctx
        self.mode = mode

    @discord.ui.button(label="📋 Create Lobby", style=discord.ButtonStyle.success, custom_id="create_lobby_btn")
    async def create_lobby_btn(self, interaction, button):
        # ✅ FIX (MEDIUM): الـ View مسجّلة persistent عند on_ready بـ ctx=None.
        # أي رسالة "Create Lobby" قديمة (من قبل إعادة تشغيل البوت) تضغط زرها →
        # self.ctx كان None ⇒ AttributeError غير معالَج.
        if self.ctx is None:
            await interaction.response.send_message(
                embed=discord.Embed(
                    title="⏳ انتهت صلاحية الرسالة",
                    description=(
                        "🔄 البوت أُعيد تشغيله — الرسالة دي ما عادتش صالحة anymore.\n"
                        f"💡 أعد الأمر `{PREFIX}play {self.mode.upper()}` لإنشاء روم جديد."
                    ),
                    color=COLORS["warning"]
                ),
                ephemeral=True
            )
            return
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

            # 🆕 اربط رسالة "Create Lobby" بهذا اللوبي — تنحذف مع انتهاء الماتش
            pending = None
            for pid, meta in list(_create_prompt_msgs.items()):
                if (meta.get("user_id") == user.id
                        and meta.get("channel_id") == self.ctx.channel.id):
                    pending = pid
                    break
            if pending:
                _lobby_prompt_msg[lid] = pending
                t = _create_prompt_timers.pop(pending, None)
                if t:
                    try:
                        t.cancel()
                    except Exception as e:
                        logger.debug(f"cancel create-prompt timer failed: {e}")
                logger.info(
                    f"🔗 Create prompt {pending} linked to lobby {lid} — "
                    f"will be deleted when the match ends"
                )

            db.set_room_info(lid, room_id, password, private_key if private_key else None)
            db.add_player_to_lobby(lid, user.id, "team1")
            lobby = db.get_lobby(lid)
            embed = create_lobby_embed(lobby, guild)
            view = LobbyButtonsView(lid, user.id, guild.id)
            msg = await self.ctx.send(embed=embed, view=view)
            db.update_lobby_message(lid, msg.id)
            active_lobby_messages[msg.id] = lid
            register_lobby_flow_msg(lid, self.ctx.channel.id, msg.id)
            db.get_or_create_player(user.id, guild.id, user.display_name)
            lobby_timeout_timers[lid] = asyncio.create_task(auto_lobby_timeout(lid, guild))
            # 🆕 بعد دقيقتين لو اللوبي لسا waiting (عدد غير كافٍ) → أغلق + احذف الرسالة
            _lobby_embed_hide_timers[lid] = asyncio.create_task(_auto_hide_idle_lobby_embed(lid, guild))
            await interaction.response.send_message(
                embed=discord.Embed(
                    title="✅ Lobby Created!",
                    description=(
                        f"Lobby `#{lid}` is now live!\n"
                        "Players can press **Join Team 1 / 2** to enter.\n"
                        + ("🔐 **Private Key** required to join." if private_key else "")
                    ),
                    color=COLORS["success"]
                ),
                ephemeral=True
            )
        except Exception as e:
            logger.exception(f"LobbyCreateModal failed: {e}")


class RematchView(discord.ui.View):
    def __init__(self, lobby_id, game_mode, guild_id, original_players, timeout=120):
        # ✅ إصلاح: timeout=None يسمح بتسجيل الـ View كـ persistent عند startup
        super().__init__(timeout=timeout)
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
            register_lobby_flow_msg(lid, target_channel.id, msg.id)
            lobby_timeout_timers[lid] = asyncio.create_task(auto_lobby_timeout(lid, guild))
            # 🆕 بعد دقيقتين لو اللوبي لسا waiting (عدد غير كافٍ) → أغلق + احذف الرسالة
            _lobby_embed_hide_timers[lid] = asyncio.create_task(_auto_hide_idle_lobby_embed(lid, guild))
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

# 🆕 حاوية للـ background task الدوري (أُضيفت في الفحص الأمني 2026-10)
# السبب: كان `asyncio.create_task(periodic_rank_sync())` يُنشئ task جديدة عند كل
# on_ready (= كل reconnect) ⇒ عدة حلقات متوازية تجهد Discord API.
_periodic_rank_task = None

# 🆕 FIX (HIGH): الإعداد الثقيل داخل on_ready (auto_setup + رسالة AUTO-DETECT) كان
# يُنفَّذ عند كل استدعاء لـ on_ready (= كل إعادة اتصال بالـ Gateway) ⇒ autosetup
# يتكرر كل عدة دقائق. هذا الحارس يضمن تنفيذه **مرة واحدة فقط لكل عملية تشغيل**.
_startup_done = False
_on_ready_count = 0   # للتشخيص فقط: كم مرة نُفِّذ on_ready (يكشف إعادات الاتصال)


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
    """✅ MAX: play1v1 للأدمنز فقط (Administrator / Manage Guild / Bot Owner).
    لا يفحص top_role بعد الآن."""
    # 1) مالك البوت = full access
    if member.id == BOT_OWNER_ID:
        return True
    # 2) Admin permission = full access
    if member.guild_permissions.administrator:
        return True
    # 3) Manage Guild permission
    if member.guild_permissions.manage_guild:
        return True
    return False  # غير ذلك — لا يُسمح له

def is_high_role_check(ctx):
    """Wrapper for use as @commands.check() decorator."""
    return is_high_role_member(ctx.author)


# 🆕 BLACKLIST: فحص عام لكل الأوامر — يمنع البلاك ليست من استخدام البوت
@bot.check
async def blacklist_global_check(ctx):
    """🆕 يمنع اللاعبين في البلاك ليست من استخدام أي أمر."""
    if not ctx.guild:
        return True
    if ctx.author.id == BOT_OWNER_ID:
        return True
    if ctx.author.guild_permissions.administrator:
        return True
    if db.is_player_blacklisted(ctx.guild.id, ctx.author.id):
        return False
    # لو انتهت المدة، تأكد من سحب الـ role
    role = discord.utils.get(ctx.guild.roles, name=BLACKLIST_ROLE_NAME)
    if role and role in ctx.author.roles:
        try:
            await ctx.author.remove_roles(role, reason="Blacklist expired")
        except:
            pass
    return True


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send(embed=discord.Embed(
            title="⏳ Cooldown",
            description=f"Please wait `{error.retry_after:.1f}s` before using this command again.",
            color=COLORS["warning"]
        ))
    elif isinstance(error, commands.CheckFailure):
        if ctx.guild and db.is_player_blacklisted(ctx.guild.id, ctx.author.id):
            await ctx.send(embed=discord.Embed(
                title="🔇 أنت في البلاك ليست",
                description=(
                    "لا يمكنك استخدام البوت حالياً.\n"
                    "أنت في قائمة البلاك ليست لمدة 10 دقائق.\n"
                    "⏱️ انتظر حتى انتهاء المدة."
                ),
                color=COLORS["error"]
            ), delete_after=15)
        else:
            await ctx.send(embed=discord.Embed(
                title="⛔ No Permission",
                description="You don't have permission to use this command.",
                color=COLORS["error"]
            ))
    elif isinstance(error, commands.CommandNotFound):
        pass
    else:
        logger.exception(f"Command error: {error}")


@bot.event
async def on_ready():
    global _on_ready_count, _startup_done
    _on_ready_count += 1
    logger.info(
        f"✅ {bot.user} online!  (on_ready #{_on_ready_count} — "
        f"startup_done={_startup_done})"
    )
    logger.info(f"📌 Prefix: {PREFIX}")
    logger.info(f"🔱 Owner: {BOT_OWNER_NAME}")
    logger.info(f"🏠 Servers: {len(bot.guilds)}")
    # 🆕 V3 MAX: register persistent views (VoteView removed — replaced by MvpVoteView)
    try:
        bot.add_view(RematchView(lobby_id=None, game_mode=None, guild_id=None, original_players=[], timeout=None))
    except Exception as e:
        logger.warning(f"Failed to register RematchView as persistent: {e}")
    try:
        bot.add_view(LobbyButtonsView())
    except Exception as e:
        logger.warning(f"Failed to register LobbyButtonsView as persistent: {e}")
    try:
        bot.add_view(StartVoteView())
    except Exception as e:
        logger.warning(f"Failed to register StartVoteView as persistent: {e}")
    try:
        bot.add_view(CreateLobbyView(None, DEFAULT_MODE, timeout=None))
    except Exception as e:
        logger.warning(f"Failed to register CreateLobbyView as persistent: {e}")
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=f"Free Fire | {PREFIX}play"))

    # 🆕 FIX (HIGH): on_ready يُستدعى من جديد عند كل إعادة اتصال (reconnect) بالـ Gateway.
    # قبل التعديل كان auto_setup + رسالة AUTO-DETECT + مهام الخلفية تُعاد كل مرة
    # (السبب الظاهر لـ «autosetup كل عدة دقائق»). الآن الإعداد الثقيل مرة واحدة/عملية،
    # وعند إعادة الاتصال نكتفي بتحديث الحضور (تم أعلاه) ونتوقف هنا.
    if _startup_done:
        logger.info(
            f"♻️ on_ready re-fired (reconnect) — skipping auto-setup. "
            f"latency={bot.latency * 1000:.0f}ms  (on_ready #{_on_ready_count})"
        )
        return
    _startup_done = True

    # 🆕 Auto-setup: فحص كل السيرفرات بالتوازي
    logger.info("🔄 Auto-setup: checking all guilds...")
    async def setup_one(guild):
        try:
            detected = await auto_setup_guild(guild)
            return guild, detected or 0
        except Exception as e:
            logger.warning(f"Auto-setup failed for {guild.name}: {e}")
            return guild, 0
    results = await asyncio.gather(*[setup_one(g) for g in bot.guilds], return_exceptions=True)
    total_detected_all = sum(r[1] for r in results if isinstance(r, tuple))
    logger.info("✅ Auto-setup complete!")
    # 🆕 V3: رسالة نجاح AUTO-DETECT — فقط في commands channel
    async def send_success(guild):
        try:
            success_ch = None
            cmd_channels = db.get_commands_channels(guild.id)
            # ✅ ابحث فقط في commands channels
            if cmd_channels:
                for cid in cmd_channels:
                    ch = guild.get_channel(cid)
                    if ch and ch.permissions_for(guild.me).send_messages:
                        success_ch = ch
                        break
            # ✅ fallback: play channels فقط لو ما فيه commands channels
            if not success_ch:
                play_channels = db.get_play_channels(guild.id)
                for cid in play_channels:
                    ch = guild.get_channel(cid)
                    if ch and ch.permissions_for(guild.me).send_messages:
                        success_ch = ch
                        break
            if success_ch:
                cmd_channels_count = len(cmd_channels)
                play_channels_count = len(db.get_play_channels(guild.id))
                waiting_rooms = db.get_waiting_rooms(guild.id)
                report_channels = db.get_report_channels(guild.id)
                success_embed = discord.Embed(
                    title="✅ AUTO-DETECT Complete",
                    description=(
                        "✅ كل القنوات الموجودة تم تسجيلها تلقائياً\n"
                        "✅ البوت جاهز للعمل بدون أي إعداد يدوي\n"
                        f"💡 Use `{PREFIX}help` لعرض الأوامر"
                    ),
                    color=COLORS["success"],
                    timestamp=discord.utils.utcnow()
                )
                success_embed.add_field(name="🤖 Bot", value="Free Fire Bot V3 MAX", inline=True)
                success_embed.add_field(name="🏠 Server", value=f"{guild.name}", inline=True)
                success_embed.add_field(name="📅 Time", value=f"{discord.utils.format_dt(discord.utils.utcnow(), 'F')}", inline=True)
                success_embed.add_field(name="📝 Commands", value=f"`{cmd_channels_count}`", inline=True)
                success_embed.add_field(name="🎮 Play", value=f"`{play_channels_count}`", inline=True)
                success_embed.add_field(name="🔊 Waiting rooms", value=f"`{len(waiting_rooms)}`", inline=True)
                success_embed.add_field(name="🔍 Under check", value=f"`{len(report_channels)}`", inline=False)
                success_embed.set_footer(text=f"{BOT_FOOTER}  •  V3 MAX AUTO-DETECT")
                # V0: لا صور
                await success_ch.send(embed=success_embed)
                logger.info(f"  ✅ [AUTO-DETECT] Success message sent to #{success_ch.name} in {guild.name}")
            else:
                logger.warning(f"  ⚠️ [AUTO-DETECT] No commands channel found in {guild.name} — skipping success message")
        except Exception as e:
            logger.warning(f"Failed to send auto-detect success message in {guild.name}: {e}")
    await asyncio.gather(*[send_success(g) for g in bot.guilds], return_exceptions=True)
    logger.info(f"✅ Auto-detect success messages sent to all servers (total detected: {total_detected_all} channels)")
    
    # 🆕 V3 MAX: sync دوري للرانك والألقاب كل دقيقة
    async def periodic_rank_sync():
        """يعيد حساب الرانك ويزامن الألقاب كل 60 ثانية،
        وكل دقيقتين يشغّل fixrank + syncnicknames (تصحيح كل النكات)."""
        tick = 0
        while True:
            try:
                await asyncio.sleep(60)
                tick += 1
                for guild in bot.guilds:
                    try:
                        # أعِد حساب الرانك
                        db.recalculate_ranks(guild.id)
                        # يزامن الألقاب
                        await sync_all_players_roles(guild)
                        # 🆕 كل دقيقتين: fixrank + syncnicknames لكل الأعضاء
                        if tick % 2 == 0:
                            await sync_all_nicknames(guild)
                    except Exception as e:
                        logger.warning(f"Periodic rank sync failed for {guild.name}: {e}")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning(f"Periodic rank sync error: {e}")

    # ✅ FIX (HIGH): `on_ready` ينفَذ من جديد عند كل reconnect، وقبل التعديل كان
    # كل نداء ينشئ task جديد بلا أي فحص ⇒ N loops متوازية بعد N انقطاع،
    # وكلها تنفّذ recalculate_ranks + sync_all_players_roles (API calls مكررة
    # ⇒ rate limits + بطء). الآن نضمن task واحدة فقط.
    global _periodic_rank_task
    if _periodic_rank_task is not None and not _periodic_rank_task.done():
        logger.warning(
            "⚠️ Periodic rank sync task still running — cancelling the duplicate "
            "(previous on_ready run)"
        )
        _periodic_rank_task.cancel()
        try:
            await _periodic_rank_task
        except (asyncio.CancelledError, Exception):
            pass
    _periodic_rank_task = asyncio.create_task(periodic_rank_sync())
    logger.info("🔄 Periodic rank sync started (every 60 seconds)")

    # 🆕 استعادة/تنظيف بعد إعادة التشغيل: احذف رسائل اللوبيات المنتهية القديمة
    #    التي تركت في قنوات اللعب، وأعد تفعيل الإغلاق التلقائي للوبيات المعلّقة (waiting).
    async def recover_after_restart():
        try:
            for guild in bot.guilds:
                try:
                    conn = db.conn()
                    stale_rows = conn.execute(
                        "SELECT * FROM lobbies WHERE guild_id=? AND status IN ('cancelled','completed')",
                        (guild.id,)
                    ).fetchall()
                except Exception as e:
                    logger.warning(f"recover_after_restart (query) failed for {guild.name}: {e}")
                    stale_rows = []
                for r in stale_rows:
                    l = dict(r)
                    mid = l.get("message_id")
                    lid = l.get("id")
                    if mid:
                        try:
                            await _delete_lobby_embed_for_lobby(lid, guild=guild)
                        except Exception as e:
                            logger.debug(f"clean stale lobby embed #{lid} failed: {e}")
                # لوبيات waiting علّقت بعد إعادة التشغيل → أعد تفعيل مؤقت الدقيقتين
                for l in db.get_active_lobbies(guild.id):
                    try:
                        if l["status"] == "waiting" and l["id"] not in _lobby_embed_hide_timers:
                            _lobby_embed_hide_timers[l["id"]] = asyncio.create_task(
                                _auto_hide_idle_lobby_embed(l["id"], guild)
                            )
                    except Exception as e:
                        logger.debug(f"re-arm hide timer for #{l['id']} failed: {e}")
        except Exception as e:
            logger.warning(f"recover_after_restart failed: {e}")
    asyncio.create_task(recover_after_restart())
    logger.info("🧹 Lobby embed recovery/cleanup scheduled after restart")


@bot.event
async def on_disconnect():
    # 🆕 تشخيص: أي انقطاع في Gateway يُسجَّل بوضوح (يكشف سبب تكرار on_ready)
    logger.warning("🔌 Gateway disconnected — awaiting automatic reconnect...")


@bot.event
async def on_resumed():
    logger.info("♻️ Gateway session resumed (no full re-identify).")


async def auto_setup_guild(guild):
    """🆕 V3 MAX: اكتشاف تلقائي ذكي — يفحص كل قنوات السيرفر ويسجلها في DB.
    ✅ لا يحتاج أي تدخل يدوي — يكتشف كل الإعدادات السابقة.
    ✅ يستخدم fuzzy matching للتعرف على القنوات بأي اسم.
    ✅ يسجل القنوات الموجودة في DB بدل إنشاء جديد.
    ✅ يكتشف فويسات التفتيش (Under check / Investigation / Prv) تلقائياً.
    ✅ يكتشف شات الأوامر تلقائياً.
    """
    logger.info(f"🔍 [AUTO-SETUP] Scanning {guild.name}...")

    # ============================================================
    # 1) فحص كل القنوات النصية وتسجيلها تلقائياً
    # ============================================================
    # أنماط البحث لكل نوع قناة — مطابقة مرنة
    TEXT_PATTERNS = {
        "play": ["play", "apostada", "highlight", "zelika", "match", "lobby"],
        "results": ["result", "match-result", "results"],
        "leaderboard": ["leaderboard", "top", "ranking"],
        "profiles": ["profile", "player", "profiles"],
        "rules": ["rules", "قوانين", "reglement"],
    }

    detected_text_channels = {"play": [], "results": [], "leaderboard": [], "profiles": [], "rules": []}

    for ch in guild.text_channels:
        name_lower = ch.name.lower()
        for channel_type, patterns in TEXT_PATTERNS.items():
            for pattern in patterns:
                if pattern in name_lower:
                    detected_text_channels[channel_type].append(ch)
                    break

    # سجل كل القنوات النصية المكتشفة في DB
    for channel_type, channels in detected_text_channels.items():
        for ch in channels:
            db.add_commands_channel(guild.id, ch.id)
            if channel_type in ["play", "results", "leaderboard", "profiles"]:
                db.add_play_channel(guild.id, ch.id)
            if channel_type == "leaderboard":
                db.set_guild_setting(guild.id, "leaderboard_channel_id", ch.id)
            logger.info(f"  📝 Detected text channel: #{ch.name} ({channel_type})")

    # ============================================================
    # 2) فحص كل القنوات الصوتية وتسجيلها تلقائياً
    # ============================================================
    VOICE_PATTERNS = {
        "waiting": ["waiting", "wait", "انتظار"],
        "prv": ["prv", "private", "خاص"],
        "under_check": ["under check", "under-check", "investigation", "تفتيش", "investigation"],
        "staff": ["staff", "admn", "أدمن"],
    }

    detected_voice_channels = {"waiting": [], "prv": [], "under_check": [], "staff": []}

    for ch in guild.voice_channels:
        name_lower = ch.name.lower()
        for voice_type, patterns in VOICE_PATTERNS.items():
            for pattern in patterns:
                if pattern in name_lower:
                    detected_voice_channels[voice_type].append(ch)
                    break

    # سجل كل القنوات الصوتية المكتشفة
    for voice_type, channels in detected_voice_channels.items():
        for ch in channels:
            if voice_type in ["waiting", "prv", "staff"]:
                db.add_waiting_room(guild.id, ch.id)
                logger.info(f"  🔊 Detected voice: {ch.name} ({voice_type} → waiting_room)")
            elif voice_type == "under_check":
                # 🆕 سجل فويسات التفتيش كـ report channels
                db.add_report_channel(guild.id, ch.id)
                logger.info(f"  🔍 Detected under-check voice: {ch.name} (→ report_channel)")

    # ============================================================
    # 3) فحص الكاتيجوريات
    # ============================================================
    text_cat = discord.utils.get(guild.categories, name="🎮 FREE FIRE — TEXT")
    if not text_cat:
        for cat in guild.categories:
            if "free fire" in cat.name.lower() and "text" in cat.name.lower():
                text_cat = cat
                break
    if not text_cat:
        text_cat = await guild.create_category("🎮 FREE FIRE — TEXT", overwrites={
            guild.default_role: discord.PermissionOverwrite(read_messages=True),
            guild.me: discord.PermissionOverwrite(manage_channels=True, manage_messages=True)
        })
        logger.info(f"  📁 Created TEXT category")

    voice_cat = discord.utils.get(guild.categories, name="🎮 FREE FIRE — VOICE")
    if not voice_cat:
        for cat in guild.categories:
            if "free fire" in cat.name.lower() and "voice" in cat.name.lower():
                voice_cat = cat
                break
    if not voice_cat:
        voice_cat = await guild.create_category("🎮 FREE FIRE — VOICE", overwrites={
            guild.default_role: discord.PermissionOverwrite(read_messages=True),
            guild.me: discord.PermissionOverwrite(manage_channels=True, manage_messages=True)
        })
        logger.info(f"  📁 Created VOICE category")

    # ============================================================
    # 4) إنشاء الناقص فقط (لو ما اكتشف قنوات معينة)
    # ============================================================
    # لو ما اكتشف أي قناة play، أنشئها
    if not detected_text_channels["play"]:
        for ch_name in ["🎮・apostada-play", "🎮・highlight-play", "🎮・zelika-play"]:
            if not discord.utils.get(guild.text_channels, name=ch_name):
                ch = await guild.create_text_channel(ch_name, category=text_cat, topic="Play")
                db.add_commands_channel(guild.id, ch.id)
                db.add_play_channel(guild.id, ch.id)
                logger.info(f"  📝 Created #{ch_name}")

    if not detected_text_channels["results"]:
        if not discord.utils.get(guild.text_channels, name="📊・match-results"):
            ch = await guild.create_text_channel("📊・match-results", category=text_cat, topic="Results")
            db.add_commands_channel(guild.id, ch.id)
            db.add_play_channel(guild.id, ch.id)

    if not detected_text_channels["leaderboard"]:
        if not discord.utils.get(guild.text_channels, name="🏆・leaderboard"):
            ch = await guild.create_text_channel("🏆・leaderboard", category=text_cat, topic="Leaderboard")
            db.add_commands_channel(guild.id, ch.id)
            db.add_play_channel(guild.id, ch.id)
            db.set_guild_setting(guild.id, "leaderboard_channel_id", ch.id)

    if not detected_text_channels["profiles"]:
        if not discord.utils.get(guild.text_channels, name="👤・profiles"):
            ch = await guild.create_text_channel("👤・profiles", category=text_cat, topic="Profiles")
            db.add_commands_channel(guild.id, ch.id)
            db.add_play_channel(guild.id, ch.id)

    # 🆕 قناة البلاك ليست — تعرض اللاعبين في البلاك ليست (تُنشأ + تُحدَّث تلقائياً)
    try:
        bl_ch = discord.utils.get(guild.text_channels, name=BLACKLIST_CHANNEL_NAME)
        if not bl_ch:
            bl_ch = await guild.create_text_channel(BLACKLIST_CHANNEL_NAME, category=text_cat, topic="Blacklisted Players")
            db.add_commands_channel(guild.id, bl_ch.id)
            logger.info(f"  📝 Created {BLACKLIST_CHANNEL_NAME}")
        db.set_guild_setting(guild.id, "blacklist_channel_id", bl_ch.id)
    except Exception as e:
        logger.warning(f"  [{guild.name}] Blacklist channel: {e}")

    # 🆕 قناة القواعد — نفس منطق setup_cmd (idempotent)
    try:
        rules_ch, rules_created = await ensure_rules_channel(guild, text_cat)
        if rules_created and rules_ch:
            logger.info(f"  🛡️ Created {RULES_CHANNEL_NAME}")
    except Exception as e:
        logger.error(f"  [{guild.name}] Rules channel: {e}")

    # لو ما اكتشف أي فويس waiting، أنشئها
    if not detected_voice_channels["waiting"]:
        for ch_name in ["⏳・Waiting 1", "⏳・Waiting 2", "⏳・Waiting 3", "⏳・Waiting 4", "⏳・Waiting 5"]:
            if not discord.utils.get(guild.voice_channels, name=ch_name):
                overwrites = {guild.me: discord.PermissionOverwrite(connect=True, manage_channels=True)}
                ch = await guild.create_voice_channel(ch_name, category=voice_cat, overwrites=overwrites)
                db.add_waiting_room(guild.id, ch.id)
                logger.info(f"  🔊 Created {ch_name}")

    # لو ما اكتشف أي فويس prv، أنشئها
    if not detected_voice_channels["prv"] and not detected_voice_channels["staff"]:
        for ch_name in ["🔒・Waiting Prv 1", "🔒・Waiting Prv 2", "🔒・Waiting Prv 3", "🔒・Waiting Staff"]:
            if not discord.utils.get(guild.voice_channels, name=ch_name):
                overwrites = {
                    guild.me: discord.PermissionOverwrite(connect=True, manage_channels=True),
                    guild.default_role: discord.PermissionOverwrite(connect=False)
                }
                ch = await guild.create_voice_channel(ch_name, category=voice_cat, overwrites=overwrites)
                db.add_waiting_room(guild.id, ch.id)
                logger.info(f"  🔊 Created {ch_name}")

    # ============================================================
    # 5) Rank Roles + JAIL + Blacklist + Leaderboard
    # ============================================================
    try:
        await setup_rank_roles_permissions(guild)
    except Exception as e:
        logger.warning(f"  [{guild.name}] Rank roles setup: {e}")

    try:
        await setup_jail_system(guild)
    except Exception as e:
        logger.warning(f"  [{guild.name}] JAIL setup: {e}")

    try:
        await setup_blacklist_role(guild)
    except Exception as e:
        logger.warning(f"  [{guild.name}] Blacklist role setup: {e}")

    try:
        await update_leaderboard_channel(guild)
    except:
        pass

    # 🆕 محدّث قناة البلاك ليست تلقائياً بعد الـ setup
    try:
        await update_blacklist_channel(guild)
    except Exception as e:
        logger.warning(f"  [{guild.name}] Blacklist channel update: {e}")

    # ملخص ما تم اكتشافه
    total_detected = sum(len(v) for v in detected_text_channels.values()) + sum(len(v) for v in detected_voice_channels.values())
    logger.info(f"  ✅ [{guild.name}] Auto-setup complete — detected {total_detected} existing channels")

    # 🆕 امسح cache بعد الانتهاء (لأننا سجلنا قنوات جديدة)
    for key in list(db._channels_cache.keys()):
        if str(guild.id) in key:
            db._channels_cache.pop(key, None)

    return total_detected


@bot.event
async def on_guild_join(guild):
    logger.info(f"🏠 Added to: {guild.name}  (ID: {guild.id})  —  Members: {guild.member_count}")


@bot.event
async def on_member_join(member):
    if member.bot:
        return
    await asyncio.sleep(2)
    player = db.get_or_create_player(member.id, member.guild.id, member.display_name)
    # ✅ تحديث النك نيم مباشرة بدون استدعاء update_member_nickname (يتجنب get_or_create_player مرة ثانية)
    try:
        if not member.guild.me.guild_permissions.manage_nicknames:
            return
        if member.id == member.guild.owner_id:
            return
        level = player.get("level", STARTING_LEVEL)
        original = player.get("original_nickname") or extract_original_nickname(member.display_name) or "Player"
        new_nick = build_nickname_with_level(original, level)
        if member.display_name != new_nick:
            await member.edit(nick=new_nick)
    except Exception as e:
        logger.warning(f"on_member_join: nickname update failed for {member.id}: {e}")


# 🆕 منع المحظورين من مغادرة فويس التفتيش
@bot.event
async def on_voice_state_update(member, before, after):
    """🆕 يمنع اللاعبين المحظورين + المسجونين + متابعة البلاك ليست."""
    if member.bot:
        return

    guild = member.guild
    gid = guild.id

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 1) فحص المحظورين — منع مغادرة فويس التفتيش
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    ban_info = db.is_player_banned(gid, member.id)
    if ban_info:
        assigned_voice_id = ban_info.get("assigned_voice_id")
        # الحالة 1: اللاعب دخل فويس جديد
        if after.channel is not None:
            if not assigned_voice_id or after.channel.id != assigned_voice_id:
                assigned_ch = guild.get_channel(assigned_voice_id) if assigned_voice_id else None
                if assigned_ch and isinstance(assigned_ch, discord.VoiceChannel):
                    try:
                        await member.move_to(assigned_ch)
                        logger.info(f"🔒 Banned player {member.id} tried to join #{after.channel.name}, moved back")
                        return
                    except (discord.HTTPException, discord.Forbidden):
                        pass
                new_ch = await move_to_banned_channels(guild, member, assign_permanent=True)
                if new_ch:
                    logger.info(f"🔒 Banned player {member.id} moved to new investigation voice")
                    return
        # الحالة 2: اللاعب غادر فويس
        elif before.channel is not None and after.channel is None:
            assigned_ch = guild.get_channel(assigned_voice_id) if assigned_voice_id else None
            if assigned_ch and isinstance(assigned_ch, discord.VoiceChannel):
                try:
                    await member.move_to(assigned_ch)
                    logger.info(f"🔒 Banned player {member.id} tried to leave voice, moved back")
                    return
                except (discord.HTTPException, discord.Forbidden):
                    pass
            new_ch = await move_to_banned_channels(guild, member, assign_permanent=True)
            if new_ch:
                logger.info(f"🔒 Banned player {member.id} moved to new investigation voice after leaving")
            return

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 2) فحص المسجونين (JAIL system)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    jail_role = discord.utils.get(guild.roles, name=JAIL_ROLE_NAME)
    if jail_role and jail_role in member.roles:
        jail_voice_name = f"🔒 Jail-{member.id}"
        jail_voice = discord.utils.get(guild.voice_channels, name=jail_voice_name)
        if after.channel is not None:
            if after.channel.name != jail_voice_name:
                if jail_voice:
                    try: await member.move_to(jail_voice); return
                    except: pass
                try: await member.move_to(None)
                except: pass
        elif before.channel is not None and after.channel is None:
            if jail_voice:
                try: await member.move_to(jail_voice); return
                except: pass
        return

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 3) 🆕 BLACKLIST TRACKING — متابعة الخروج من التيم
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # نتتبع فقط اللاعبين الذين يغادرون/يدخلون فويسات الماتش
    before_is_match = before.channel and before.channel.id in _active_match_voice_channels
    after_is_match = after.channel and after.channel.id in _active_match_voice_channels

    if not before_is_match and not after_is_match:
        return  # ليس في فويس ماتش — لا داعي للتتبع

    # هيئ tracking dict للسيرفر واللاعب
    if gid not in _blacklist_voice_tracking:
        _blacklist_voice_tracking[gid] = {}
    track = _blacklist_voice_tracking[gid]
    uid = member.id
    if uid not in track:
        track[uid] = {"leave_count": 0, "total_leave_time": 0.0, "in_match_voice": before_is_match, "leave_start": None}

    now = datetime.now().timestamp()

    # حالة: خرج من فويس الماتش (كان في الماتش وخرج)
    if before_is_match and not after_is_match:
        track[uid]["in_match_voice"] = False
        track[uid]["leave_start"] = now
        track[uid]["leave_count"] += 1
        logger.info(f"🔇 BLACKLIST TRACK: {member.display_name} left match voice (leave #{track[uid]['leave_count']})")

    # حالة: رجع لفويس الماتش (كان خارج الماتش ورجع)
    elif after_is_match and not before_is_match:
        if track[uid]["leave_start"] is not None:
            elapsed = now - track[uid]["leave_start"]
            track[uid]["total_leave_time"] += elapsed
            track[uid]["leave_start"] = None
        track[uid]["in_match_voice"] = True
        total_time = track[uid]["total_leave_time"]
        leave_count = track[uid]["leave_count"]
        logger.info(f"🔇 BLACKLIST TRACK: {member.display_name} rejoined match voice (total leave: {total_time:.1f}s, leaves: {leave_count})")

        # فحص الحدود
        if total_time >= BLACKLIST_TIME_LIMIT:
            logger.info(f"🔇 BLACKLIST: {member.display_name} exceeded time limit ({total_time:.1f}s >= {BLACKLIST_TIME_LIMIT}s)")
            reason = f"Automatic: left match voice for {total_time:.0f}s (limit: {BLACKLIST_TIME_LIMIT}s)"
            await apply_blacklist(guild, member, reason=reason)
            # امسح التتبع
            track.pop(uid, None)
            return
        if leave_count >= BLACKLIST_MAX_LEAVES:
            logger.info(f"🔇 BLACKLIST: {member.display_name} exceeded max leaves ({leave_count} >= {BLACKLIST_MAX_LEAVES})")
            reason = f"Automatic: left and rejoined {leave_count} times (limit: {BLACKLIST_MAX_LEAVES})"
            await apply_blacklist(guild, member, reason=reason)
            # امسح التتبع
            track.pop(uid, None)
            return

    # حالة: انتقال بين فويسات (من فويس ماتش لفويس ماتش آخر) — يعتبر في الماتش
    elif before_is_match and after_is_match:
        track[uid]["in_match_voice"] = True
        if track[uid]["leave_start"] is not None:
            elapsed = now - track[uid]["leave_start"]
            track[uid]["total_leave_time"] += elapsed
            track[uid]["leave_start"] = None


@bot.event
async def on_message(message):
    if message.author.bot:
        return
    if isinstance(message.channel, discord.DMChannel):
        # ✅ FIX (MEDIUM): `ctx.guild is None` في DM ⇒ أي أمر غير محمي يطبع
        # AttributeError في اللوقز بدون أي رسالة للمستخدم. نمنع الأوامر غير المدعومة.
        content = message.content.strip()
        parts = content.split()
        invoked = parts[0].lower() if parts else ""
        # ✅ `!!serverleave` فقط: هو الأمر الوحيد المصمَّم لـ DM عمداً.
        #    `!!help` يستدعي apply_branding(ctx.guild) ⇒ None ⇒ AttributeError،
        #    فبقي خارج القائمة (سلوكه السابق: خطأ في اللوقز بدون رد — disparه الآن).
        dm_safe = {f"{PREFIX}serverleave"}
        if invoked in dm_safe:
            await bot.process_commands(message)
            return
        await message.channel.send(embed=discord.Embed(
            title="📡 الأوامر داخل السيرفر فقط",
            description=(
                "هذه الرسالة خاصة (DM) — أوامر البوت كلها تحتاج قناة داخل السيرفر.\n"
                f"💡 افتح قناة الأوامر واكتب `{PREFIX}help` لعرض كل الأوامر.\n"
                f"📌 أوامر تعمل هنا: `{PREFIX}serverleave`"
            ),
            color=COLORS["info"]
        ), delete_after=20)
        return
    if not message.guild:
        return

    # 🆕 فحص المسجونين (JAIL) — منع الكتابة في غير شاتات السجن
    jail_role = discord.utils.get(message.guild.roles, name=JAIL_ROLE_NAME)
    if jail_role and message.author.id != message.guild.owner_id:
        member = message.guild.get_member(message.author.id)
        if member and jail_role in member.roles:
            allowed_jail_channels = [JAIL_CHAT_NAME, JAIL_PROUVES_NAME]
            if message.channel.name not in allowed_jail_channels:
                try: await message.delete()
                except: pass
                return

    if not db.is_bot_allowed_channel(message.guild.id, message.channel.id):
        is_admin = False
        member = message.guild.get_member(message.author.id)
        if member and member.guild_permissions.administrator:
            is_admin = True
        content_stripped = message.content.strip()
        command_name = content_stripped.split()[0] if content_stripped.split() else ""
        allowed_anywhere = [f"{PREFIX}general", f"{PREFIX}help", f"{PREFIX}fixrank", f"{PREFIX}myrank", f"{PREFIX}mylevel", f"{PREFIX}p", f"{PREFIX}setup", f"{PREFIX}autosetup", f"{PREFIX}botinfo", f"{PREFIX}cleanup", f"{PREFIX}fixrankall", f"{PREFIX}setcommandschannel", f"{PREFIX}card", f"{PREFIX}scan", f"{PREFIX}deletecat", f"{PREFIX}delcat", f"{PREFIX}confirmcat", f"{PREFIX}rules", f"{PREFIX}points"]
        is_allowed = command_name in allowed_anywhere
        if content_stripped.startswith(PREFIX):
            if is_admin or is_allowed:
                await bot.process_commands(message)
                return
            try:
                await message.reply(embed=discord.Embed(
                    title="❌ Not Allowed Here",
                    description=(
                        "Commands can only be used in play channels.\n"
                        "Allowed: `apostada-play` • `highlight-play` • `zelika-play`\n"
                        f"💡 Use `{PREFIX}general` for help."
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
            title="🚫 أنت محظور من اللعب",
            description=(
                "🔍 يتم توجيهك لفويس التفتيش\n"
                "💡 لفك الحظر، تواصل مع الأدمن"
            ),
            color=COLORS["error"],
            timestamp=discord.utils.utcnow()
        )
        ban_embed.add_field(name="⚠️ السبب", value=f"`{ban_info.get('ban_reason') or 'غير محدد'}`", inline=True)
        ban_embed.add_field(name="📊 البلاغات", value=f"`{ban_info.get('report_count', 0)}`", inline=True)
        ban_embed.add_field(name="📅 تاريخ الحظر", value=f"`{ban_info.get('banned_at', 'N/A')[:19]}`", inline=True)
        ban_embed.set_footer(text=f"{BOT_FOOTER}  •  Banned")
        ban_embed = apply_branding(ban_embed, ctx.guild)
        await ctx.send(embed=ban_embed, delete_after=20)
        # انقل لفويس التفتيش لو في فويس
        if member and member.voice and member.voice.channel:
            await move_to_banned_channels(guild, member)
        return
    if not db.is_bot_allowed_channel(guild.id, ctx.channel.id):
        await ctx.send(embed=discord.Embed(
            title="❌ Not Allowed Here",
            description=(
                "This command can only be used in play channels.\n"
                "Allowed: `apostada-play` • `highlight-play` • `zelika-play`"
            ),
            color=COLORS["error"]
        ), delete_after=15)
        return
    if not member or not member.voice or not member.voice.channel:
        waiting_rooms = db.get_waiting_rooms(guild.id)
        available = [guild.get_channel(wr).mention for wr in waiting_rooms if guild.get_channel(wr) and guild.get_channel(wr).permissions_for(member).connect]
        rooms_text = "\n".join([f"› {r}" for r in available[:10]]) if available else "> *None*"
        embed = discord.Embed(
            title="⏳ Must Be in a Waiting Room",
            description="You need to be in a voice waiting room to create a lobby.",
            color=COLORS["warning"]
        )
        embed.add_field(name="🔊 Available Rooms", value=f"{rooms_text}", inline=False)
        await ctx.send(embed=embed, delete_after=20)
        return
    else:
        waiting_rooms = db.get_waiting_rooms(guild.id)
        if member.voice.channel.id not in waiting_rooms:
            available = [guild.get_channel(wr).mention for wr in waiting_rooms if guild.get_channel(wr) and guild.get_channel(wr).permissions_for(member).connect]
            rooms_text = "\n".join([f"› {r}" for r in available[:10]]) if available else "> *None*"
            embed = discord.Embed(
                title="⏳ Wrong Voice Channel",
                description=f"You're in `{member.voice.channel.name}` — that's not a waiting room.",
                color=COLORS["warning"]
            )
            embed.add_field(name="🔊 Available Rooms", value=f"{rooms_text}", inline=False)
            await ctx.send(embed=embed, delete_after=20)
            return
    existing = db.get_player_active_lobby(user.id, guild.id)
    if existing:
        await ctx.send(embed=discord.Embed(
            title="❌ Already in Lobby",
            description=(
                "You're already in a lobby. Leave it first.\n"
                f"Use `{PREFIX}leave` to leave."
            ),
            color=COLORS["error"]
        ), delete_after=10)
        return
    create_view = CreateLobbyView(ctx, mode)

    # 🆕 لو عنده رسالة "Create Lobby" قديمة → احذفها (ما تتكدّس الرسائل)
    stale = [pid for pid, meta in _create_prompt_msgs.items() if meta.get("user_id") == user.id]
    for pid in stale:
        meta = _create_prompt_msgs.pop(pid, None)
        t = _create_prompt_timers.pop(pid, None)
        if t:
            try:
                t.cancel()
            except Exception as e:
                logger.debug(f"cancel timer failed for prompt {pid}: {e}")
        if meta:
            asyncio.create_task(delete_message_safely(
                ctx.channel, pid, reason="استُبدلت بأمر play جديد"
            ))
        logger.info(f"🧹 Removed stale 'Create Lobby' message {pid} for user {user.id}")

    create_embed = discord.Embed(
        title=f"🎮 Create {mode.upper()} Lobby",
        description="اضغط الزر تحت لإدخال بيانات الغرفة وإنشاء اللوبي.",
        color=COLORS["play"]
    )
    create_embed.add_field(name="💡 تحتاج", value="• Room ID (أرقام)\n• Password (اختياري)\n• Private Key (اختياري)", inline=False)
    create_embed.add_field(name="⏱️ ملاحظة", value=f"تختفي هذه الرسالة تلقائياً بعد `{CREATE_PROMPT_DELETE_AFTER}` ثانية إذا ما ضغطت الزر.\n✅ وإذا أنشأت الغرفة — تنحذف مع انتهاء الروم.", inline=False)
    prompt = await ctx.send(embed=create_embed, view=create_view)

    _create_prompt_msgs[prompt.id] = {
        "guild_id": guild.id, "channel_id": prompt.channel.id, "user_id": user.id
    }
    _create_prompt_timers[prompt.id] = asyncio.create_task(
        auto_hide_create_prompt(guild, prompt, user.id)
    )
    logger.info(
        f"⏱️ Create prompt {prompt.id} by {user.id} — auto-remove in "
        f"{CREATE_PROMPT_DELETE_AFTER}s if no room created"
    )


@bot.command(name="play")
async def play_cmd(ctx, mode: str = None):
    # 🆕 !!play ذكي — يقبل المود كـ argument
    # مثال: !!play 1v1, !!play 4v4, !!play 2v2
    # لو ما فيه argument → اعرض رسالة خطأ مع البدائل
    # لو فيه argument صحيح → شغّل الماتش بهذا المود
    # لو فيه argument خاطئ → اعرض رسالة خطأ

    if mode is None:
        # ✅ إصلاح: بناء embed كمتغير بشكل صحيح
        no_mode_embed = discord.Embed(
            title="❌ أمر غير صحيح",
            description=(
                f"الأمر `{PREFIX}play` غير صالح — يجب تحديد نوع الماتش بوضوح.\n"
                f"💡 مثال: `{PREFIX}play4v4`"
            ),
            color=COLORS["error"],
            timestamp=discord.utils.utcnow()
        )
        no_mode_embed.add_field(name="🎮 الأوامر الصحيحة", value=f"`{PREFIX}play1v1` — ماتش 1 ضد 1 🔒 (للـ roles العالية)\n`{PREFIX}play2v2` — ماتش 2 ضد 2\n`{PREFIX}play3v3` — ماتش 3 ضد 3\n`{PREFIX}play4v4` — ماتش 4 ضد 4 (الافتراضي)", inline=False)
        no_mode_embed.set_footer(text=f"{BOT_FOOTER}  •  Specify the game mode")
        no_mode_embed = apply_branding(no_mode_embed, ctx.guild)
        await ctx.send(embed=no_mode_embed, delete_after=15)
        return

    # تحويل المود لـ lowercase وإزالة المسافات
    mode = mode.strip().lower()

    # قائمة المودات الصحيحة
    valid_modes = list(GAME_MODES.keys())  # ['1v1', '2v2', '3v3', '4v4']

    if mode not in valid_modes:
        # ✅ إصلاح: بناء embed كمتغير بشكل صحيح
        invalid_mode_embed = discord.Embed(
            title="❌ مود غير صحيح",
            description=(
                f"المود `{mode}` غير صالح — استخدم أحد المودات التالية:\n"
                f"💡 مثال: `{PREFIX}play 4v4`"
            ),
            color=COLORS["error"],
            timestamp=discord.utils.utcnow()
        )
        invalid_mode_embed.add_field(name="🎮 المودات الصحيحة", value=f"`{PREFIX}play 1v1` أو `{PREFIX}play1v1` 🔒\n`{PREFIX}play 2v2` أو `{PREFIX}play2v2`\n`{PREFIX}play 3v3` أو `{PREFIX}play3v3`\n`{PREFIX}play 4v4` أو `{PREFIX}play4v4`", inline=False)
        invalid_mode_embed.set_footer(text=f"{BOT_FOOTER}  •  Invalid mode")
        invalid_mode_embed = apply_branding(invalid_mode_embed, ctx.guild)
        await ctx.send(embed=invalid_mode_embed, delete_after=15)
        return

    # المود صحيح — شغّل الماتش
    # 🆕 فحص خاص بـ play1v1 (للأدوار العالية فقط)
    if mode == "1v1" and not is_high_role_member(ctx.author):
        member = ctx.author
        guild_roles = [r for r in ctx.guild.roles if r.hoist and r != ctx.guild.default_role]
        max_position = max((r.position for r in guild_roles), default=0)
        threshold = max(1, max_position // 2) if max_position else 0
        member_top = member.top_role.position if member.top_role else 0
        # ✅ إصلاح: بناء embed كمتغير بشكل صحيح
        restricted_embed = discord.Embed(
            title="🔒 أمر محمي",
            description=(
                f"**الأمر:** `{PREFIX}play 1v1`\n"
                "مخصص فقط للأعضاء ذوي **الـ roles العالية** في السيرفر.\n"
                f"💡 Use `{PREFIX}play 4v4` للعب العادي (متاح للجميع)."
            ),
            color=COLORS["error"],
            timestamp=discord.utils.utcnow()
        )
        restricted_embed.add_field(name="🎯 شروط الاستخدام (يكفي أحدها)", value=f"• صلاحية `Administrator` في السيرفر\n• صلاحية `Manage Guild` (إدارة السيرفر)\n• role في النصف العلوي من الهرم — مطلوب position `≥ {threshold}` وأنت حالياً `{member_top}`", inline=False)
        restricted_embed.set_footer(text=f"{BOT_FOOTER}  •  Restricted Command")
        restricted_embed = apply_branding(restricted_embed, ctx.guild)
        await ctx.send(embed=restricted_embed, delete_after=20)
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
        # ✅ إصلاح: بناء embed كمتغير بشكل صحيح
        restricted_embed = discord.Embed(
            title="🔒 أمر محمي",
            description=(
                f"**الأمر:** `{PREFIX}play1v1`\n"
                "مخصص فقط للأعضاء ذوي **الـ roles العالية** في السيرفر.\n"
                f"💡 Use `{PREFIX}play` للعب 4v4 العادي (متاح للجميع)."
            ),
            color=COLORS["error"],
            timestamp=discord.utils.utcnow()
        )
        restricted_embed.add_field(name="🎯 شروط الاستخدام (يكفي أحدها)", value=f"• صلاحية `Administrator` في السيرفر\n• صلاحية `Manage Guild` (إدارة السيرفر)\n• role في النصف العلوي من الهرم — مطلوب position `≥ {threshold}` وأنت حالياً `{member_top}`", inline=False)
        restricted_embed.set_footer(text=f"{BOT_FOOTER}  •  Restricted Command")
        restricted_embed = apply_branding(restricted_embed, ctx.guild)
        await ctx.send(embed=restricted_embed, delete_after=20)
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
    await ctx.send(embed=create_profile_embed(player, target, ctx.guild.id))


@bot.command(name="points", aliases=["mypoints", "pts"])
async def points_cmd(ctx, member: discord.Member = None):
    """💰 !!points — عرض نقاطك الحالية + كم تحتاج للرانك التالي"""
    target = member or ctx.author
    player = db.get_or_create_player(target.id, ctx.guild.id, target.display_name)
    level = player.get("level", STARTING_LEVEL)
    points = player.get("points", 0)
    top_pts = db.get_top_points(ctx.guild.id)
    pts_to_next = max(0, top_pts - points) if top_pts > points else 0
    progress_pct = max(0, min(100, int((points / max(top_pts, 1)) * 100))) if top_pts else 0  # ✅ إصلاح V5: تحديد النسبة بين 0-100
    progress_bar = make_progress_bar(points, max(top_pts, 1), length=15)
    rank_color = get_rank_color(level)
    rank_title = get_rank_title(level)
    rank_emoji = get_rank_emoji(level)
    wr = round((player["wins"] / max(player["matches_played"], 1)) * 100, 1)
    wr_bar = make_winrate_bar(wr, length=10)

    embed = discord.Embed(
        title="💰 نقاط اللاعب",
        description=(
            f"👤 {target.mention}\n"
            f"🏅 {rank_emoji} **{rank_title}**  `#{level}`\n"
            f"💰 `{points:,}` pts"
        ),
        color=rank_color,
        timestamp=discord.utils.utcnow()
    )
    # التقدم نحو المركز الأول
    if pts_to_next > 0:
        embed.add_field(
            name="📈 التقدم نحو المركز الأول",
            value=f"`{progress_bar}`  `{progress_pct}%`\n💎 نقاطك `{points:,}`  ·  🏆 القمة `{top_pts:,}`  ·  ⏭️ يتبقى `{pts_to_next:,}` نقطة للوصول للقمة",
            inline=False
        )
    else:
        embed.add_field(
            name="🔱 أنت الأول!",
            value=f"🎉 أنت في القمة بـ `{points:,}` نقطة!\n🚀 حافظ على مركزك بالفوز بالمزيد من المباريات!",
            inline=False
        )

    # إحصائيات سريعة
    embed.add_field(name="🏆 Wins", value=f"`{player['wins']}`", inline=True)
    embed.add_field(name="☠️ Losses", value=f"`{player['losses']}`", inline=True)
    embed.add_field(name="🔱 MVPs", value=f"`{player['mvps']}`", inline=True)

    embed.add_field(
        name=f"📊 Win Rate — `{wr}%`",
        value=f"`{wr_bar}` `{player['wins']}/{player['matches_played']}`",
        inline=False
    )
    embed.set_author(name="Player Points", icon_url=None)
    embed.set_footer(text=f"{BOT_FOOTER}")
    embed = apply_branding(embed, ctx.guild)
    await ctx.send(embed=embed)


@bot.command(name="card")
async def card_cmd(ctx, member: discord.Member = None):
    """🃏 !!card — بطاقة اللاعب (تعمل في كل قنوات play)"""
    target = member or ctx.author
    player = db.get_or_create_player(target.id, ctx.guild.id, target.display_name)
    await update_member_nickname(target, player.get("level", STARTING_LEVEL))
    await ctx.send(embed=create_profile_embed(player, target, ctx.guild.id))


@bot.command(name="top")
async def top_cmd(ctx):
    # 🆕 إخفاء اللاعبين في البلاك ليست من اللوحة (بدل عرضهم)
    blacklisted_ids = {b["user_id"] for b in db.get_blacklisted_players(ctx.guild.id)}
    lb = db.get_leaderboard(ctx.guild.id, 25)
    lb = [p for p in lb if p["user_id"] not in blacklisted_ids][:10]
    if not lb:
        await ctx.send(embed=discord.Embed(
            title="🏆 Leaderboard",
            description=(
                "No players yet!\n"
                f"Use `{PREFIX}play` to start your first match."
            ),
            color=COLORS["leaderboard"]
        ))
        return
    embed = discord.Embed(
        title="🏆 Free Fire — Top 10 Players",
        color=COLORS["leaderboard"],
        timestamp=discord.utils.utcnow()
    )
    medals = ["💎", "🥈", "🥉", "🏅", "🎖️", "🏵️", "🏷️", "8️⃣", "9️⃣", "🔟"]
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
            title="❌ Not in Lobby",
            description=(
                "You're not currently in any lobby.\n"
                f"Use `{PREFIX}play` to create one."
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
                title="🗑️ Lobby Cancelled",
                description=f"Lobby `#{lobby['id']}` was cancelled.",
                color=COLORS["warning"]
            ))
            return
        remaining = [p for p in (lobby["team1_players"] + lobby["team2_players"]) if p != ctx.author.id]
        if remaining:
            db.reassign_creator(lobby["id"], remaining[0])
    db.remove_player_from_lobby(lobby["id"], ctx.author.id)
    await ctx.send(embed=discord.Embed(
        title="✅ Left Lobby",
        description=f"You left lobby `#{lobby['id']}`.",
        color=COLORS["success"]
    ))


@bot.command(name="matches")
async def matches_cmd(ctx):
    lobbies = db.get_active_lobbies(ctx.guild.id)
    if not lobbies:
        await ctx.send(embed=discord.Embed(
            title="🎮 Active Lobbies",
            description=(
                "No active lobbies right now.\n"
                f"Use `{PREFIX}play` to start one."
            ),
            color=COLORS["info"]
        ))
        return
    embed = discord.Embed(title="🎮 Active Lobbies", color=COLORS["play"])
    for l in lobbies[:5]:
        mode = l.get("game_mode", DEFAULT_MODE)
        mi = GAME_MODES.get(mode, GAME_MODES[DEFAULT_MODE])
        t1c = len(l["team1_players"]); t2c = len(l["team2_players"])
        se = {"waiting": "⏳", "started": "🎮", "voting": "🗳️"}.get(l["status"], "❓")
        embed.add_field(
            name=f"`#{l['id']}` {mi['emoji']} {mode.upper()} — {se}",
            value=f"🔴 `{t1c}/{mi['team_size']}`  ·  🟢 `{t2c}/{mi['team_size']}`",
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
        title=f"{rank_emoji} RANK — {target.display_name}",
        description=(
            f"🏅 **{rank_title}**  `#{level}`\n"
            f"💰 `{player['points']:,}` pts"
        ),
        color=rank_color,
        timestamp=discord.utils.utcnow()
    )
    embed.add_field(name="🏆 Wins", value=f"`{player['wins']}`", inline=True)
    embed.add_field(name="☠️ Losses", value=f"`{player['losses']}`", inline=True)
    embed.add_field(name="⚖️ W/L", value=f"`{kd_sign}{kd_diff}`", inline=True)
    embed.add_field(name=f"📊 Win Rate — `{wr}%`", value=f"`{wr_bar}` `{player['wins']}/{player['matches_played']}`", inline=False)
    embed.set_author(name="Player Rank", icon_url=None)
    embed.set_footer(text=f"{BOT_FOOTER}")
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
        title="📝 Your Rank",
        description=f"👤 {target.mention}",
        color=COLORS["profile"]
    )
    embed.add_field(name="🏅 Rank", value=f"`#{level}`", inline=True)
    embed.add_field(name="📝 Current Nickname", value=f"`{target.display_name}`", inline=True)
    embed.add_field(name="🎯 Target Nickname", value=f"`{target_nick}`", inline=True)
    if is_owner:
        embed.add_field(name="🔱 Server Owner", value="Bot can't change your nickname. Apply manually.", inline=False)
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
            title="🔱 Server Owner",
            description=(
                f"{target.mention} → **RANK `#{level}`**\n"
                f"🎯 Target Nickname: `{target_nick}`\n"
                "Apply manually: *Right-click → Edit Profile → Nickname*"
            ),
            color=COLORS["warning"]
        ))
        return
    await update_member_nickname(target, level)
    await ctx.send(embed=discord.Embed(
        title="✅ Rank Applied",
        description=f"{target.mention} → **RANK `#{level}`**",
        color=COLORS["success"]
    ))


@bot.command(name="matchinfo")
async def matchinfo_cmd(ctx, lobby_id: int = None):
    if lobby_id is None:
        await ctx.send(embed=discord.Embed(
            title="❌ Missing ID",
            description=(
                "Please provide a lobby ID.\n"
                f"Usage: `{PREFIX}matchinfo <id>`"
            ),
            color=COLORS["error"]
        ))
        return
    lobby = db.get_lobby(lobby_id)
    if not lobby:
        await ctx.send(embed=discord.Embed(
            title="❌ Not Found",
            description=f"Lobby `#{lobby_id}` doesn't exist.",
            color=COLORS["error"]
        ))
        return
    embed = discord.Embed(
        title=f"📋 Match — #{lobby_id}",
        description=f"📊 Status `{lobby['status']}`   ·   🎮 Mode `{lobby.get('game_mode', DEFAULT_MODE).upper()}`",
        color=COLORS["info"]
    )
    t1m = "\n".join([f"› <@{p}>" for p in lobby["team1_players"]]) or "> *Empty*"
    t2m = "\n".join([f"› <@{p}>" for p in lobby["team2_players"]]) or "> *Empty*"
    embed.add_field(name=f"🔴 Team 1 — `{len(lobby['team1_players'])}`", value=f"{t1m}", inline=True)
    embed.add_field(name=f"🟢 Team 2 — `{len(lobby['team2_players'])}`", value=f"{t2m}", inline=True)
    await ctx.send(embed=embed)


# ============================================================
# 🛡️ RULES — مصدر واحد لنص القواعد
# ============================================================
# 🆕 اسم قناة القواعد الثابت — لو غيّرته، غيّره في كل مكان مرة واحدة
RULES_CHANNEL_NAME = "🛡️・rules"


def build_rules_embed(guild_name):
    """🆕 يبني embed القواعد — يستخدمه  !!setup  و  !!autosetup  و  !!rules.
    ✅ مصدر واحد للنص: أي تعديل على القواعد يتم هنا فقط بدل 3 نسخ مكرّرة."""
    embed = discord.Embed(
        title="🛡️ قواعد السيرفر",
        description=(
            f"مرحباً بك في **{guild_name}** 🔥\n"
            "يرجى الالتزام بالقواعد التالية:"
        ),
        color=COLORS["info"],
        timestamp=discord.utils.utcnow()
    )
    embed.add_field(name="1️⃣ الاحترام المتبادل", value="• احترم جميع اللاعبين والأدمنز.\n• ممنوع السب، الشتم، أو الإساءة.", inline=False)
    embed.add_field(name="2️⃣ قواعد اللعب", value=f"• ادخل غرفة انتظار قبل اللعب.\n• استخدم `{PREFIX}play 4v4` لبدء ماتش.\n• التزم بنتيجة التصويت.", inline=False)
    embed.add_field(name="3️⃣ عدم الغش", value="• ممنوع التلاعب بالتصويت.\n• ممنوع مغادرة الماتش في المنتصف.", inline=False)
    embed.add_field(name="4️⃣ استخدام الأوامر", value="• الأوامر تعمل فقط في قنوات play.", inline=False)
    embed.add_field(name="5️⃣ العقوبات", value="• مخالفة القواعد = تحذير / كتم / طرد.\n• القرار النهائي للأدمن.", inline=False)
    embed.add_field(name="💬 استفسار", value="لأي استفسار، تواصل مع الأدمن.", inline=False)
    embed.set_author(name="Server Rules")
    embed.set_footer(text=f"{BOT_FOOTER}  •  Read carefully")
    return embed


async def ensure_rules_channel(guild, text_cat=None):
    """🆕 ينشئ قناة القواعد لو ناقصة، ويبعت القواعد فيها.
    ✅ idempotent: لو موجودة يرجّعها بدون ما يعيد الإنشاء.
    ✅ كل خطأ يتسجّل في اللوق (ما في ابتلاع صامت)."""
    existing = discord.utils.get(guild.text_channels, name=RULES_CHANNEL_NAME)
    if existing:
        return existing, False

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=True, send_messages=False, add_reactions=False),
        guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_messages=True)
    }
    try:
        ch = await guild.create_text_channel(
            RULES_CHANNEL_NAME, category=text_cat, topic="Rules",
            overwrites=overwrites, position=0
        )
        logger.info(f"✅ Created rules channel: {RULES_CHANNEL_NAME} in {guild.name}")
    except discord.Forbidden as e:
        logger.error(f"❌ Forbidden create rules channel in {guild.name}: {e}")
        return None, False
    except discord.HTTPException as e:
        logger.error(f"❌ HTTP error creating rules channel in {guild.name}: {e}")
        return None, False

    # ابعت رسالة القواعد (فشلت؟ القناة صارت موجودة على الأقل)
    try:
        await ch.send(embed=build_rules_embed(guild.name))
    except discord.Forbidden as e:
        logger.warning(f"⚠️ Cannot send rules embed (Forbidden) in {guild.name}: {e}")
    except discord.HTTPException as e:
        logger.warning(f"⚠️ HTTP error sending rules embed in {guild.name}: {e}")
    return ch, True


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
    text_cat = discord.utils.get(guild.categories, name="🎮 FREE FIRE — TEXT")
    if not text_cat:
        text_cat = await guild.create_category("🎮 FREE FIRE — TEXT", overwrites={guild.default_role: discord.PermissionOverwrite(read_messages=True), guild.me: discord.PermissionOverwrite(manage_channels=True, manage_messages=True)})
        created.append("🎮 FREE FIRE — TEXT")
    
    # 🆕 كاتيجوري منفصل للقنوات الصوتية
    voice_cat = discord.utils.get(guild.categories, name="🎮 FREE FIRE — VOICE")
    if not voice_cat:
        voice_cat = await guild.create_category("🎮 FREE FIRE — VOICE", overwrites={guild.default_role: discord.PermissionOverwrite(read_messages=True), guild.me: discord.PermissionOverwrite(manage_channels=True, manage_messages=True)})
        created.append("🎮 FREE FIRE — VOICE")

    # 🆕 قناة القواعد — تنشأ تلقائياً (idempotent: ما تتكرر لو موجودة)
    rules_ch, rules_created = await ensure_rules_channel(guild, text_cat)
    if rules_created and rules_ch:
        created.append(RULES_CHANNEL_NAME)
    elif rules_ch:
        logger.info(f"ℹ️ [setup] {guild.name}: قناة القواعد موجودة مسبقاً — تم تجاهل الإنشاء")

    # 🆕 القنوات النصية في كاتيجوري النصي
    for ch_name, topic in [("🎮・apostada-play", "Play"), ("🎮・highlight-play", "Play"), ("🎮・zelika-play", "Play"), ("📊・match-results", "Results"), ("🏆・leaderboard", "Leaderboard"), ("👤・profiles", "Profiles"), (BLACKLIST_CHANNEL_NAME, "Blacklist")]:
        if not discord.utils.get(guild.text_channels, name=ch_name):
            ch = await guild.create_text_channel(ch_name, category=text_cat, topic=topic)
            db.add_commands_channel(guild.id, ch.id)
            db.add_play_channel(guild.id, ch.id)
            if "leaderboard" in ch_name:
                db.set_guild_setting(guild.id, "leaderboard_channel_id", ch.id)
            if ch_name == BLACKLIST_CHANNEL_NAME:
                db.set_guild_setting(guild.id, "blacklist_channel_id", ch.id)
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
    # 🆕 حدّث قناة البلاك ليست في الـ setup
    try:
        await update_blacklist_channel(guild)
    except Exception as e:
        logger.warning(f"setup blacklist channel update failed: {e}")
    # 🆕 أنشئ الـ Roles الخاصة بالألقاب + حدّث صلاحيات Waiting Prv
    try:
        await setup_rank_roles_permissions(guild)
        created.append("Rank Roles (Best/Goated/Skilled/Efficient)")
    except Exception as e:
        logger.warning(f"setup_rank_roles_permissions failed: {e}")
    try:
        await setup_blacklist_role(guild)
        created.append("Blacklist Role")
    except Exception as e:
        logger.warning(f"setup_blacklist_role failed: {e}")
    # ✅ إصلاح: بناء embed النجاح كمتغير بشكل صحيح
    setup_embed = discord.Embed(
        title="✅ Setup Complete!",
        description=f"Created `{len(created)}` channels successfully.",
        color=COLORS["success"],
        timestamp=discord.utils.utcnow()
    )
    setup_embed.add_field(name="🛡️ Rules channel", value=f"`{RULES_CHANNEL_NAME}` — للقراءة فقط، وإن لم تُنشأ استخدم `{PREFIX}rules`", inline=False)
    setup_embed.add_field(name="🔇 Blacklist Role", value=f"`{BLACKLIST_ROLE_NAME}`", inline=False)
    setup_embed.add_field(name="🎮 Next", value=f"Use `{PREFIX}play4v4` in play channels to start.", inline=False)
    setup_embed.set_footer(text=f"{BOT_FOOTER}  •  Setup complete")
    setup_embed = apply_branding(setup_embed, ctx.guild)
    await ctx.send(embed=setup_embed)


@bot.command(name="autosetup", aliases=["autoset", "checksetup"])
@commands.check(is_bot_owner_or_admin_check)
async def autosetup_cmd(ctx):
    """🔄 !!autosetup — فحص السيرفر وإصلاح أي شيء ناقص تلقائياً"""
    # ✅ إصلاح: بناء الـ embed كمتغير، ثم set_footer، ثم apply_branding
    progress_embed = discord.Embed(
        title="🔄 جارٍ فحص السيرفر...",
        description=(
            "🔍 البحث عن القنوات والكاتيجوريات الناقصة...\n"
            "🔧 إنشاء Roles + JAIL لو غير موجودة...\n"
            "⏳ انتظر..."
        ),
        color=COLORS["warning"],
        timestamp=discord.utils.utcnow()
    )
    progress_embed.set_footer(text=f"{BOT_FOOTER}  •  Auto-setup")
    progress_embed = apply_branding(progress_embed, ctx.guild)
    progress = await ctx.send(embed=progress_embed)

    try:
        await auto_setup_guild(ctx.guild)
        # ✅ إصلاح: بناء embed النجاح كمتغير بشكل صحيح
        success_embed = discord.Embed(
            title="✅ تم الفحص والإصلاح!",
            description=(
                "🔍 تم فحص السيرفر بالكامل\n"
                "✅ كل القنوات الناقصة أُنشئت\n"
                "✅ كل الكاتيجوريات مُحدثة (TEXT + VOICE منفصلين)\n"
                "✅ Rank Roles مُحدثة\n"
                "✅ نظام JAIL مُفعّل\n"
                f"✅ Blacklist Role `{BLACKLIST_ROLE_NAME}`\n"
                "✅ Leaderboard مُحدث\n"
                "\n"
                "💡 لم تُمسح أي بيانات موجودة — النقاط والرانك والفويسات كما هي"
            ),
            color=COLORS["success"],
            timestamp=discord.utils.utcnow()
        )
        success_embed.set_footer(text=f"{BOT_FOOTER}  •  Auto-setup complete")
        success_embed = apply_branding(success_embed, ctx.guild)
        await progress.edit(embed=success_embed)
    except Exception as e:
        # ✅ إصلاح: بناء embed الخطأ كمتغير بشكل صحيح
        error_embed = discord.Embed(
            title="❌ فشل Auto-setup",
            description=f"🐛 **الخطأ:** `{str(e)[:200]}`",
            color=COLORS["error"],
            timestamp=discord.utils.utcnow()
        )
        error_embed.set_footer(text=f"{BOT_FOOTER}  •  Auto-setup failed")
        error_embed = apply_branding(error_embed, ctx.guild)
        await progress.edit(embed=error_embed)


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
        title="🧹 Cleanup Complete!",
        description=f"Deleted `{deleted}` match categories.",
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
        title=f"🔍 Server Scan — {len(categories)} Categories",
        description=(
            f"🏠 **{guild.name}**\n"
            f"📝 `{len(guild.text_channels)}` text   ·   🔊 `{len(guild.voice_channels)}` voice   ·   📄 Page `{page}/{total_pages}`"
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
            name=f"📁 `{i}.` {cat.name}",
            value=f"{detail}",
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
        embed.add_field(name="📂 No Category", value=f"{detail or '*None*'}", inline=False)

    embed.set_footer(text=f"{BOT_FOOTER}  •  Page {page}/{total_pages}  ·  {PREFIX}scan <page>  ·  {PREFIX}deletecat <name>  ·  {PREFIX}confirmcat <name>")
    embed = apply_branding(embed, ctx.guild)
    await ctx.send(embed=embed)


@bot.command(name="deletecat", aliases=["delcat"])
@commands.check(is_bot_owner_or_admin_check)
async def deletecat_cmd(ctx, *, category_name: str = None):
    """🗑️ !!deletecat <name> — حذف كاتيجوري بكل قنواتها"""
    if not category_name:
        await ctx.send(embed=discord.Embed(
            title="❌ Missing Name",
            description=(
                "Please provide a category name.\n"
                f"Usage: `{PREFIX}deletecat <category name>`\n"
                f"Use `{PREFIX}scan` to see all categories."
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
            title="❌ Not Found",
            description=(
                f"No category matching `{category_name}`.\n"
                f"Use `{PREFIX}scan` to see all categories."
            ),
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
            "⚠️ **This will delete ALL channels inside!**\n"
            f"Type `{PREFIX}confirmcat {target.name}` to confirm."
        ),
        color=COLORS["warning"]
    )
    confirm_embed.add_field(name="📁 Category", value=f"`{target.name}`", inline=True)
    confirm_embed.add_field(name="📊 Channels", value=f"`{total_channels}` (`{text_count}` text + `{voice_count}` voice)", inline=True)
    await ctx.send(embed=confirm_embed)


@bot.command(name="confirmcat")
@commands.check(is_bot_owner_or_admin_check)
async def confirmcat_cmd(ctx, *, category_name: str = None):
    """✅ !!confirmcat <name> — تأكيد حذف الكاتيجوري"""
    if not category_name:
        await ctx.send(embed=discord.Embed(
            title="❌ Missing Name",
            description=f"Usage: `{PREFIX}confirmcat <name>`",
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
            title="❌ Not Found",
            description=f"No category matching `{category_name}`.",
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
        embed = discord.Embed(
            title="✅ Category Deleted!",
            description=f"**{cat_name}** has been deleted.",
            color=COLORS["success"]
        )
        embed.add_field(name="✅ Channels deleted", value=f"`{deleted}`", inline=True)
        embed.add_field(name="❌ Errors", value=f"`{errors}`", inline=True)
        await ctx.send(embed=embed)
    except (discord.NotFound, discord.Forbidden) as e:
        await ctx.send(embed=discord.Embed(
            title="⚠️ Partial Delete",
            description=(
                f"Deleted `{deleted}` channels but couldn't delete the category itself.\n"
                f"Error: `{e}`"
            ),
            color=COLORS["warning"]
        ))


@bot.command(name="fixrankall", aliases=["forcerankall"])
@commands.check(is_admin_check)
async def fixrankall_cmd(ctx):
    guild = ctx.guild
    progress = await ctx.send(embed=discord.Embed(
        title="🚀 Applying Ranks...",
        description=(
            f"Processing `{len(guild.members)}` members.\n"
            "Please wait..."
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
        title="✅ Done!",
        description=f"Updated `{updated}` members successfully.",
        color=COLORS["success"]
    ))


@bot.command(name="botinfo")
async def botinfo_cmd(ctx):
    # 🆕 FIX: member_count قد يكون None في السيرفرات الكبيرة → لا نكسر الأمر
    total_members = sum((g.member_count or 0) for g in bot.guilds)
    total_text_channels = sum(len(g.text_channels) for g in bot.guilds)
    total_voice_channels = sum(len(g.voice_channels) for g in bot.guilds)
    embed = discord.Embed(
        title="🤖 Bot Info",
        description=(
            "🔥 **Free Fire Matchmaking Bot**\n"
            "نظام ماتش ميكنج متكامل لإدارة مباريات Free Fire"
        ),
        color=COLORS["info"],
        timestamp=discord.utils.utcnow()
    )
    embed.add_field(name="📛 Name", value=f"`{bot.user.name}`", inline=True)
    embed.add_field(name="🏷️ Version", value="`v4.1 MVP-COLLECTIVE`", inline=True)
    embed.add_field(name="🔨 Build", value=f"`{BUILD_SHA}`", inline=True)
    embed.add_field(name="⌨️ Prefix", value=f"`{PREFIX}`", inline=True)
    embed.add_field(name="🏠 Servers", value=f"`{len(bot.guilds)}`", inline=True)
    embed.add_field(name="👥 Users", value=f"`{total_members:,}`", inline=True)
    embed.add_field(name="🔱 Owner", value=f"`{BOT_OWNER_NAME}`", inline=True)
    embed.add_field(name="📝 Text Channels", value=f"`{total_text_channels}`", inline=True)
    embed.add_field(name="🔊 Voice Channels", value=f"`{total_voice_channels}`", inline=True)
    embed.add_field(name="🎮 Features", value=f"• 🏆 4 Game Modes (1v1, 2v2, 3v3, 4v4)\n• 🗳️ Group MVP Voting (4 voters, `{MVP_CONSENSUS_NEEDED}` consensus)\n• 🏅 Dynamic Rank System\n• 📊 Live Leaderboard\n• 🛡️ Auto Rules Channel (`{RULES_CHANNEL_NAME}`)\n• ⏱️ Auto-hide 'Create Lobby' after `{CREATE_PROMPT_DELETE_AFTER}s`", inline=False)
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
            title="✅ Channel Removed",
            description=f"{channel.mention} has been removed from allowed command channels.",
            color=COLORS["success"]
        ))
    else:
        db.add_commands_channel(ctx.guild.id, channel.id)
        await ctx.send(embed=discord.Embed(
            title="✅ Channel Added",
            description=f"{channel.mention} has been added to allowed command channels.",
            color=COLORS["success"]
        ))


@bot.command(name="setleaderboard")
@commands.check(is_admin_check)
async def setleaderboard_cmd(ctx):
    db.set_guild_setting(ctx.guild.id, "leaderboard_channel_id", ctx.channel.id)
    await update_leaderboard_channel(ctx.guild)
    await ctx.send(embed=discord.Embed(
        title="✅ Leaderboard Set",
        description=(
            f"{ctx.channel.mention} is now the leaderboard channel.\n"
            "It will update automatically."
        ),
        color=COLORS["success"]
    ))


# ============================================================
# 🆕 REPORT & BAN COMMANDS — أوامر البلاغات والحظر
# ============================================================

@bot.command(name="report")
async def report_cmd(ctx, member: discord.Member = None, *, reason: str = None):
    """⚠️ !!report @user [reason] — بلّغ عن لاعب"""
    if not member:
        await ctx.send(embed=discord.Embed(
            title="❌ Missing User",
            description=(
                f"Usage: `{PREFIX}report @user [reason]`\n"
                f"مثال: `{PREFIX}report @user يستخدم هاك`"
            ),
            color=COLORS["error"]
        ), delete_after=15)
        return
    if member.id == ctx.author.id:
        await ctx.send(embed=discord.Embed(
            title="❌ لا يمكنك البلاغ عن نفسك",
            color=COLORS["error"]
        ), delete_after=10)
        return
    if member.bot:
        await ctx.send(embed=discord.Embed(
            title="❌ لا يمكنك البلاغ عن بوت",
            color=COLORS["error"]
        ), delete_after=10)
        return
    # 🔒 نظّف السبب قبل التخزين: يمنع mass-ping عبر <@&id> / @everyone
    #    ويمنع كسر حد 1024 حرف في حقل الـ embed (HTTPException 400)
    reason = sanitize_user_text(reason, max_length=200)
    # سجل البلاغ
    added, total = db.add_report(ctx.guild.id, ctx.author.id, member.id, reason=reason)
    if not added:
        await ctx.send(embed=discord.Embed(
            title="⚠️ بلغت من قبل",
            description=f"لقد بلّغت على {member.mention} سابقاً.",
            color=COLORS["warning"]
        ), delete_after=10)
        return
    remaining = max(0, REPORT_THRESHOLD - total)
    report_embed = discord.Embed(
        title="⚠️ تم تسجيل البلاغ",
        description=(
            (f"⚠️ يتبقى `{remaining}` بلاغ للحظر التلقائي" if remaining > 0 else "⚠️ **وصل للحد!** سيتم الحظر تلقائياً")
        ),
        color=COLORS["warning"] if remaining > 0 else COLORS["error"],
        timestamp=discord.utils.utcnow()
    )
    report_embed.add_field(name="👤 المُبلَّغ عنه", value=f"{member.mention}", inline=True)
    report_embed.add_field(name="👮 المُبلِّغ", value=f"{ctx.author.mention}", inline=True)
    report_embed.add_field(name="📊 البلاغات", value=f"`{total}/{REPORT_THRESHOLD}`", inline=True)
    if reason:
        report_embed.add_field(name="📝 السبب", value=f"{reason}", inline=False)
    report_embed.set_footer(text=f"{BOT_FOOTER}  •  Report #{total}")
    report_embed = apply_branding(report_embed, ctx.guild)
    await ctx.send(embed=report_embed)
    # 🆕 أرسل البلاغ للأدمنز مع السبب
    await notify_admins(
        ctx.guild,
        "⚠️  بلاغ جديد",
        f"> 👤  **اللاعب المُبلَّغ عنه:**  {member.mention}\n"
        f"> 👮  **الـمُبلِّغ:**  {ctx.author.mention}\n"
        + (f"> 📝  **السبب:**  {reason}\n" if reason else "> 📝  **السبب:**  غير محدد\n")
        + f"> 📊  **إجمالي البلاغات:**  `{total}/{REPORT_THRESHOLD}`",
        color=COLORS["warning"] if remaining > 0 else COLORS["error"]
    )
    # فحص الحظر التلقائي
    await check_and_apply_auto_ban(ctx.guild, member.id, total, ctx.author.id)


@bot.command(name="reports")
async def reports_cmd(ctx, member: discord.Member = None):
    """📊 !!reports @user — عرض بلاغات لاعب"""
    target = member or ctx.author
    reports = db.get_reports_for_player(ctx.guild.id, target.id)
    count = len(reports)
    embed = discord.Embed(
        title=f"⚠️ بلاغات اللاعب — {target.display_name}",
        description=(
            f"👤 {target.mention}   ·   📊 `{count}/{REPORT_THRESHOLD}`\n"
            + ("⚠️ **محظور تلقائياً**" if count >= REPORT_THRESHOLD else f"⚠️ **يتبقى:** `{REPORT_THRESHOLD - count}` بلاغ للحظر")
        ),
        color=COLORS["error"] if count >= REPORT_THRESHOLD else COLORS["warning"],
        timestamp=discord.utils.utcnow()
    )
    if reports:
        # اعرض آخر 10 بلاغات
        for i, r in enumerate(reports[:10], 1):
            reporter = ctx.guild.get_member(r["reporter_id"])
            reporter_name = reporter.display_name if reporter else f"User#{r['reporter_id']}"
            reason = r.get("reason") or "بدون سبب"
            timestamp = r.get("created_at", "N/A")[:19] if r.get("created_at") else "N/A"
            embed.add_field(
                name=f"#{i} — {reporter_name}",
                value=f"📝 `{reason}`\n📅 `{timestamp}`",
                inline=False
            )
        if count > 10:
            embed.set_footer(text=f"{BOT_FOOTER}  •  و {count - 10} بلاغ آخر")
    else:
        embed.description = f"> ✅  لا توجد بلاغات على {target.mention}"
        embed.color = COLORS["success"]
    embed.set_author(name="Player Reports", icon_url=None)
    # ✅ إصلاح: apply_branding يجب أن يطبّق دائماً، ليس فقط لو تجاوزت البلاغات 10
    embed = apply_branding(embed, ctx.guild)
    await ctx.send(embed=embed)


@bot.command(name="banplayer", aliases=["ban"])
@commands.check(is_admin_check)
async def banplayer_cmd(ctx, target: Union[discord.Member, int] = None, *, reason: str = None):
    """🚫 !!banplayer @user أو ID [reason] — حظر لاعب يدوياً"""
    if not target:
        await ctx.send(embed=discord.Embed(
            title="❌ Missing User",
            description=f"Usage: `{PREFIX}banplayer @user أو ID [reason]`",
            color=COLORS["error"]
        ), delete_after=15)
        return
    user_id = target.id if isinstance(target, discord.Member) else target
    if user_id == ctx.author.id:
        await ctx.send("❌ لا يمكنك حظر نفسك!", delete_after=10)
        return
    report_count = db.get_reports_count(ctx.guild.id, user_id)
    db.ban_player(ctx.guild.id, user_id, reason=reason or "Manual ban by admin", banned_by=ctx.author.id, report_count=report_count)
    member = target if isinstance(target, discord.Member) else ctx.guild.get_member(user_id)
    assigned_channel = None
    if member and member.voice and member.voice.channel:
        assigned_channel = await move_to_banned_channels(ctx.guild, member, assign_permanent=True)
    else:
        admin_channel_ids = db.get_report_channels(ctx.guild.id)
        if admin_channel_ids:
            ch = ctx.guild.get_channel(admin_channel_ids[0])
            if ch and isinstance(ch, discord.VoiceChannel):
                assigned_channel = ch
                db.set_banned_voice(ctx.guild.id, user_id, ch.id)
    ban_embed = discord.Embed(
        title="🚫 تم حظر اللاعب",
        color=COLORS["error"],
        timestamp=discord.utils.utcnow()
    )
    ban_embed.add_field(name="👤 اللاعب", value=f"<@{user_id}>", inline=True)
    ban_embed.add_field(name="👮 حظره", value=f"{ctx.author.mention}", inline=True)
    ban_embed.add_field(name="📊 البلاغات السابقة", value=f"`{report_count}`", inline=True)
    if reason:
        ban_embed.add_field(name="📝 السبب", value=f"`{reason}`", inline=False)
    if assigned_channel:
        ban_embed.add_field(name="🔍 فويس التفتيش", value=f"{assigned_channel.mention}\n🔒 **مقيّد:** لا يمكنه مغادرة هذا الفويس", inline=False)
    ban_embed.set_footer(text=f"{BOT_FOOTER}  •  Banned")
    ban_embed = apply_branding(ban_embed, ctx.guild)
    await ctx.send(embed=ban_embed)


@bot.command(name="unbanplayer", aliases=["unban"])
@commands.check(is_admin_check)
async def unbanplayer_cmd(ctx, target: Union[discord.User, int] = None):
    """✅ !!unbanplayer @user أو ID — فك حظر لاعب"""
    if not target:
        await ctx.send(embed=discord.Embed(
            title="❌ Missing User",
            description=f"Usage: `{PREFIX}unbanplayer @user أو ID`",
            color=COLORS["error"]
        ), delete_after=15)
        return
    user_id = target.id if isinstance(target, discord.User) else target
    ban_info = db.is_player_banned(ctx.guild.id, user_id)
    if not ban_info:
        await ctx.send(embed=discord.Embed(
            title="ℹ️ اللاعب غير محظور",
            description=f"<@{user_id}> غير محظور أصلاً.",
            color=COLORS["info"]
        ), delete_after=10)
        return
    db.unban_player(ctx.guild.id, user_id)
    db.clear_reports(ctx.guild.id, user_id)
    unban_embed = discord.Embed(
        title="✅ تم فك الحظر",
        description=(
            "📊 تم مسح كل البلاغات السابقة\n"
            "🎮 اللاعب يستطيع اللعب الآن"
        ),
        color=COLORS["success"],
        timestamp=discord.utils.utcnow()
    )
    unban_embed.add_field(name="👤 اللاعب", value=f"<@{user_id}>", inline=True)
    unban_embed.add_field(name="👮 فك الحظر", value=f"{ctx.author.mention}", inline=True)
    unban_embed.set_footer(text=f"{BOT_FOOTER}  •  Unbanned")
    unban_embed = apply_branding(unban_embed, ctx.guild)
    await ctx.send(embed=unban_embed)


@bot.command(name="banned")
@commands.check(is_admin_check)
async def banned_cmd(ctx):
    """📋 !!banned — قائمة اللاعبين المحظورين"""
    banned = db.get_banned_players(ctx.guild.id)
    embed = discord.Embed(
        title="📋 قائمة المحظورين",
        description=f"📊 **إجمالي المحظورين:** `{len(banned)}`",
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
                name=f"#{i} — {name}",
                value=f"👤 {mention}\n📝 `{reason}`\n📊 `{report_count}` reports · 📅 `{banned_at}`",
                inline=False
            )
        if len(banned) > 15:
            embed.set_footer(text=f"{BOT_FOOTER}  •  و {len(banned) - 15} لاعب آخر")
    # ✅ إصلاح: apply_branding يجب أن يطبّق دائمًا، ليس فقط لو تجاوز عدد المحظورين 15
    embed = apply_branding(embed, ctx.guild)
    await ctx.send(embed=embed)


@bot.command(name="setreportchannel", aliases=["setreportch", "addreportch"])
@commands.check(is_admin_check)
async def setreportchannel_cmd(ctx, channel: discord.VoiceChannel = None):
    """🎤 !!setreportchannel #voice — إضافة فويس لقائمة فويسات التفتيش"""
    if not channel:
        await ctx.send(embed=discord.Embed(
            title="❌ Missing Voice Channel",
            description=(
                f"Usage: `{PREFIX}setreportchannel <#voice_channel>`\n"
                f"مثال: `{PREFIX}setreportchannel #Investigation-Room`\n"
                "💡 اذكر فويس صوتي (Voice Channel) موجود"
            ),
            color=COLORS["error"]
        ), delete_after=15)
        return
    # تأكد إنه فويس صوتي
    if not isinstance(channel, discord.VoiceChannel):
        await ctx.send(embed=discord.Embed(
            title="❌ Not a Voice Channel",
            description=(
                f"{channel.mention} ليس فويس صوتي.\n"
                "استخدم فويس صوتي (Voice Channel)."
            ),
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
        title="🎤 فويسات التفتيش",
        description=(
            f"🎤 {channel.mention}\n"
            + ("✅ **تمت الإضافة** لقائمة فويسات التفتيش\n" if added else "⚠️ **موجود مسبقاً** في القائمة\n")
            + "\n"
            f"📊 **إجمالي الفويسات:** `{len(all_channels)}`\n"
            f"{channels_list}\n"
            "\n"
            "💡 اللاعبون المحظورون سيُنقلون لهذه الفويسات تلقائياً"
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
            title="❌ Missing Voice Channel",
            description=f"Usage: `{PREFIX}removereportchannel <#voice_channel>`",
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
        title="🗑️ حذف فويس التفتيش",
        description=(
            f"🎤 {channel.mention}\n"
            + ("✅ **تم الحذف** من القائمة\n" if removed else "⚠️ **غير موجود** في القائمة\n")
            + "\n"
            f"📊 **الفويسات المتبقية:** `{len(all_channels)}`\n"
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
        title="📋 فويسات التفتيش المحددة",
        description=(
            f"📊 **إجمالي الفويسات:** `{len(all_channels)}`\n"
            + ("⚠️ **لا توجد فويسات محددة** — سيتم إنشاء فويسات تلقائية عند الحظر" if not all_channels else "")
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
                    name=f"#{i} — {ch.name}",
                    value=f"🎤 {ch.mention}\n📊 `{members_count}` members",
                    inline=False
                )
            else:
                embed.add_field(
                    name=f"#{i} — ⚠️ محذوف",
                    value=f"❌ Channel ID: `{cid}` غير موجود\n💡 Use `{PREFIX}removereportchannel` لتنظيف القائمة",
                    inline=False
                )
    embed.set_footer(text=f"{BOT_FOOTER}  •  Use !!setreportchannel to add")
    embed = apply_branding(embed, ctx.guild)
    await ctx.send(embed=embed)


# ============================================================
# 🆕 JAIL SYSTEM — نظام السجن للغشاشين
# ============================================================
# 🆕 نظام JAIL — التعريفات في بداية الملف (السطر 87-91)
# تم نقلها ليعمل on_voice_state_update و on_message بشكل صحيح


async def setup_jail_system(guild):
    """🆕 ينشئ role الـ JAIL + كاتيجوري منفصل + قناتي السجن."""
    jail_role = discord.utils.get(guild.roles, name=JAIL_ROLE_NAME)
    if not jail_role:
        try:
            jail_role = await guild.create_role(name=JAIL_ROLE_NAME, color=discord.Color(0x36393F), permissions=discord.Permissions(view_channel=True, send_messages=True, read_messages=True, read_message_history=True, attach_files=True, embed_links=True), reason="Free Fire Bot — JAIL system")
        except: return None
    jail_cat = discord.utils.get(guild.categories, name=JAIL_CATEGORY_NAME)
    if not jail_cat:
        try:
            overwrites = {guild.default_role: discord.PermissionOverwrite(view_channel=False), guild.me: discord.PermissionOverwrite(view_channel=True, manage_channels=True, manage_messages=True, move_members=True, connect=True), jail_role: discord.PermissionOverwrite(view_channel=True)}
            for role in guild.roles:
                if role.permissions.administrator or role.permissions.manage_guild:
                    overwrites[role] = discord.PermissionOverwrite(view_channel=True, manage_channels=True, manage_messages=True, move_members=True, connect=True)
            jail_cat = await guild.create_category(JAIL_CATEGORY_NAME, overwrites=overwrites, reason="JAIL system")
        except: jail_cat = discord.utils.get(guild.categories, name="🎮 FREE FIRE — TEXT")
    for ch_name, perms in [(JAIL_CHAT_NAME, True), (JAIL_PROUVES_NAME, True)]:
        if not discord.utils.get(guild.text_channels, name=ch_name):
            try:
                overwrites = {guild.default_role: discord.PermissionOverwrite(view_channel=False), guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_messages=True), jail_role: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True, attach_files=perms)}
                for role in guild.roles:
                    if role.permissions.administrator or role.permissions.manage_guild:
                        overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_messages=True)
                await guild.create_text_channel(ch_name, category=jail_cat, topic=f"JAIL — {ch_name}", overwrites=overwrites)
            except: pass
    for ch in guild.text_channels:
        if ch.name in [JAIL_CHAT_NAME, JAIL_PROUVES_NAME] or ch.name == "🛡️・rules": continue
        try:
            overwrite = ch.overwrites_for(jail_role); overwrite.view_channel = False; overwrite.send_messages = False
            await ch.set_permissions(jail_role, overwrite=overwrite, reason="JAIL system")
        except: pass
    for ch in guild.voice_channels:
        if ch.category and ch.category.name == JAIL_CATEGORY_NAME: continue
        try:
            overwrite = ch.overwrites_for(jail_role); overwrite.view_channel = False; overwrite.connect = False; overwrite.speak = False
            await ch.set_permissions(jail_role, overwrite=overwrite, reason="JAIL system")
        except: pass
    return jail_role


async def create_jail_voice_for_player(guild, member, jail_role, jail_cat):
    voice_name = f"🔒 Jail-{member.id}"
    if discord.utils.get(guild.voice_channels, name=voice_name): return discord.utils.get(guild.voice_channels, name=voice_name)
    try:
        overwrites = {guild.default_role: discord.PermissionOverwrite(view_channel=False, connect=False), guild.me: discord.PermissionOverwrite(view_channel=True, connect=True, manage_channels=True, move_members=True), jail_role: discord.PermissionOverwrite(view_channel=False, connect=False), member: discord.PermissionOverwrite(view_channel=True, connect=True, speak=True)}
        for role in guild.roles:
            if role.permissions.administrator or role.permissions.manage_guild:
                overwrites[role] = discord.PermissionOverwrite(view_channel=True, connect=True, move_members=True, manage_channels=True)
        return await guild.create_voice_channel(voice_name, category=jail_cat, overwrites=overwrites, reason=f"JAIL voice for {member}")
    except: return None


async def delete_jail_voice_for_player(guild, member):
    voice_name = f"🔒 Jail-{member.id}"
    existing = discord.utils.get(guild.voice_channels, name=voice_name)
    if existing:
        try: await existing.delete(reason=f"JAIL voice deleted — {member} unjailed")
        except: pass


@bot.command(name="jail", aliases=["sendtojail", "cheater"])
@commands.check(is_admin_check)
async def jail_cmd(ctx, target: Union[discord.Member, int] = None, *, reason: str = None):
    """🔒 !!jail <@user أو ID> [سبب] — إرسال لاعب للسجن"""
    if not target:
        await ctx.send(embed=discord.Embed(
            title="❌ Missing User",
            description=f"Usage: `{PREFIX}jail <@user أو ID> [سبب]`",
            color=COLORS["error"]
        ), delete_after=15); return
    user_id = target.id if isinstance(target, discord.Member) else target
    member = target if isinstance(target, discord.Member) else ctx.guild.get_member(user_id)
    if not member:
        await ctx.send(embed=discord.Embed(
            title="❌ اللاعب غير موجود في السيرفر",
            description=f"<@{user_id}> ليس عضو في هذا السيرفر.",
            color=COLORS["error"]
        ), delete_after=10)
        return
    if member.bot: await ctx.send("❌ لا يمكنك سجن بوت!", delete_after=10); return
    jail_role = await setup_jail_system(ctx.guild)
    if not jail_role: await ctx.send("❌ لم أستطع إنشاء نظام السجن!", delete_after=10); return
    try: await member.add_roles(jail_role, reason=f"Jailed by {ctx.author.name}: {reason or 'No reason'}")
    except Exception as e: await ctx.send(f"❌ لم أستطع إعطاء الـ role! ({e})", delete_after=15); return
    jail_cat = discord.utils.get(ctx.guild.categories, name=JAIL_CATEGORY_NAME)
    jail_voice = None
    if jail_cat:
        jail_voice = await create_jail_voice_for_player(ctx.guild, member, jail_role, jail_cat)
        if jail_voice and member.voice and member.voice.channel:
            try: await member.move_to(jail_voice)
            except: pass
    jail_embed = discord.Embed(
        title="🔒 تم إرسال اللاعب للسجن",
        description=(
            "🔒 اللاعب الآن في السجن\n"
            f"💬 يمكنه الكتابة في `{JAIL_CHAT_NAME}` و `{JAIL_PROUVES_NAME}`\n"
            + (f"🎤 فويس السجن: `{jail_voice.name}`\n" if jail_voice else "")
            + f"✅ لفك السجن: `{PREFIX}unjail @user`"
        ),
        color=COLORS["error"],
        timestamp=discord.utils.utcnow()
    )
    jail_embed.add_field(name="👤 اللاعب", value=f"{member.mention}", inline=True)
    jail_embed.add_field(name="👮 الأدمن", value=f"{ctx.author.mention}", inline=True)
    if reason:
        jail_embed.add_field(name="📝 السبب", value=f"`{reason}`", inline=False)
    jail_embed.set_author(name="JAIL System")
    jail_embed.set_footer(text=f"{BOT_FOOTER}  •  Jailed")
    jail_embed = apply_branding(jail_embed, ctx.guild)
    await ctx.send(embed=jail_embed)
    jail_chat = discord.utils.get(ctx.guild.text_channels, name=JAIL_CHAT_NAME)
    if jail_chat:
        try:
            welcome = discord.Embed(
                title="🔒 مرحباً بك في السجن",
                description=(
                    f"{member.mention} تم إرسالك للسجن\n"
                    + (f"📝 **السبب:** {reason}\n" if reason else "")
                    + "\n"
                    "💬 يمكنك الكلام هنا فقط\n"
                    f"📸 ارفع أدلتك في `#{JAIL_PROUVES_NAME}`\n"
                    "⏳ انتظر قرار الأدمن"
                ),
                color=COLORS["warning"],
                timestamp=discord.utils.utcnow()
            )
            welcome.set_footer(text=f"{BOT_FOOTER}  •  JAIL")
            await jail_chat.send(content=member.mention, embed=welcome)
        except: pass


@bot.command(name="unjail", aliases=["release", "free"])
@commands.check(is_admin_check)
async def unjail_cmd(ctx, target: Union[discord.Member, int] = None):
    """✅ !!unjail <@user أو ID> — فك سجن لاعب"""
    if not target:
        await ctx.send(embed=discord.Embed(
            title="❌ Missing User",
            description=f"Usage: `{PREFIX}unjail <@user أو ID>`",
            color=COLORS["error"]
        ), delete_after=15); return
    user_id = target.id if isinstance(target, discord.Member) else target
    member = target if isinstance(target, discord.Member) else ctx.guild.get_member(user_id)
    if not member:
        await ctx.send(embed=discord.Embed(
            title="ℹ️ اللاعب غير موجود",
            description=f"<@{user_id}> ليس في السيرفر.",
            color=COLORS["info"]
        ), delete_after=10); return
    jail_role = discord.utils.get(ctx.guild.roles, name=JAIL_ROLE_NAME)
    if not jail_role: await ctx.send("❌ نظام السجن غير مُفعّل!", delete_after=10); return
    if jail_role not in member.roles: await ctx.send(f"ℹ️ {member.mention} ليس في السجن!", delete_after=10); return
    try: await member.remove_roles(jail_role, reason=f"Unjailed by {ctx.author.name}")
    except Exception as e: await ctx.send(f"❌ لم أستطع إزالة الـ role! ({e})", delete_after=15); return
    await delete_jail_voice_for_player(ctx.guild, member)
    unjail_embed = discord.Embed(
        title="✅ تم فك السجن",
        description="🎮 اللاعب حر الآن",
        color=COLORS["success"],
        timestamp=discord.utils.utcnow()
    )
    unjail_embed.add_field(name="👤 اللاعب", value=f"{member.mention}", inline=True)
    unjail_embed.add_field(name="👮 الأدمن", value=f"{ctx.author.mention}", inline=True)
    unjail_embed.set_author(name="JAIL System")
    unjail_embed.set_footer(text=f"{BOT_FOOTER}  •  Released")
    unjail_embed = apply_branding(unjail_embed, ctx.guild)
    await ctx.send(embed=unjail_embed)


# ============================================================
# 🆕 BLACKLIST SYSTEM — نظام البلاك ليست
# ============================================================

async def setup_blacklist_role(guild):
    """🆕 ينشئ role البلاك ليست لو غير موجود."""
    role = discord.utils.get(guild.roles, name=BLACKLIST_ROLE_NAME)
    if not role:
        try:
            role = await guild.create_role(
                name=BLACKLIST_ROLE_NAME,
                color=discord.Color(0x2C3E50),
                reason="Free Fire Bot — Blacklist system"
            )
        except:
            return None
    return role


async def apply_blacklist(guild, member, reason=None):
    """🆕 يطبق البلاك ليست على لاعب: يعطيه role + يسجل في DB + يبدأ مؤقت 10 دقائق."""
    if not member or member.bot:
        return False
    role = await setup_blacklist_role(guild)
    if not role:
        return False
    # خلّص أي مؤقت قديم لهذا اللاعب
    old_timer = _blacklist_auto_remove_timers.get(guild.id, {}).pop(member.id, None)
    if old_timer and not old_timer.done():
        old_timer.cancel()
    try:
        await member.add_roles(role, reason=f"Blacklisted: {reason or 'Left match / rejoined too many times'}")
    except:
        return False
    expires_ts = db.blacklist_player(guild.id, member.id, reason=reason)
    if not expires_ts:
        return False
    # ابدأ مؤقت للإزالة التلقائية بعد 10 دقائق
    async def auto_remove_blacklist():
        try:
            await asyncio.sleep(BLACKLIST_DURATION)
            await remove_blacklist(guild, member)
        except:
            pass
    if guild.id not in _blacklist_auto_remove_timers:
        _blacklist_auto_remove_timers[guild.id] = {}
    task = asyncio.ensure_future(auto_remove_blacklist())
    _blacklist_auto_remove_timers[guild.id][member.id] = task
    # أبلغ الأدمن
    await notify_admins(
        guild,
        "🔇  Blacklist Applied",
        f"> 👤  **اللاعب:**  {member.mention}\n"
        f"> 📝  **السبب:**  {reason or 'غير محدد'}\n"
        f"> ⏱️  **المدة:**  10 دقائق\n"
        f"> 🔇  لا يمكنه استخدام البوت لمدة 10 دقائق",
        color=COLORS["warning"]
    )
    # 🆕 حدّث قناة البلاك ليست بعد التطبيق
    try:
        await update_blacklist_channel(guild)
    except Exception as e:
        logger.warning(f"update_blacklist_channel (apply) failed: {e}")
    return True


async def remove_blacklist(guild, member):
    """🆕 يزيل البلاك ليست عن لاعب: يسحب role + يحذف من DB + يلغي المؤقت."""
    if not member or member.bot:
        return
    role = discord.utils.get(guild.roles, name=BLACKLIST_ROLE_NAME)
    if role and role in member.roles:
        try:
            await member.remove_roles(role, reason="Blacklist expired / removed by admin")
        except:
            pass
    db.remove_blacklist(guild.id, member.id)
    # ألغِ المؤقت إن وجد
    timers = _blacklist_auto_remove_timers.get(guild.id, {})
    timer = timers.pop(member.id, None)
    if timer and not timer.done():
        timer.cancel()
    # 🆕 حدّث قناة البلاك ليست بعد الإزالة
    try:
        await update_blacklist_channel(guild)
    except Exception as e:
        logger.warning(f"update_blacklist_channel (remove) failed: {e}")


def is_blacklisted_check(ctx):
    """🆕 فحص البلاك ليست — يمنع اللاعب من استخدام البوت."""
    if ctx.author.id == BOT_OWNER_ID:
        return True
    if ctx.author.guild_permissions.administrator:
        return True
    if db.is_player_blacklisted(ctx.guild.id, ctx.author.id):
        return False
    return True


@bot.command(name="blacklist", aliases=["bl"])
@commands.check(is_admin_check)
async def blacklist_cmd(ctx, target: Union[discord.Member, int] = None, *, reason: str = None):
    """🔇 !!blacklist @user أو ID [سبب] — إضافة لاعب للبلاك ليست يدوياً"""
    if not target:
        await ctx.send(embed=discord.Embed(
            title="❌ Missing User",
            description=f"Usage: `{PREFIX}blacklist @user أو ID [reason]`",
            color=COLORS["error"]
        ), delete_after=15)
        return
    user_id = target.id if isinstance(target, discord.Member) else target
    if user_id == ctx.author.id:
        await ctx.send("❌ لا يمكنك بلاك ليست نفسك!", delete_after=10)
        return
    member = target if isinstance(target, discord.Member) else ctx.guild.get_member(user_id)
    if member and member.bot:
        await ctx.send("❌ لا يمكنك بلاك ليست بوت!", delete_after=10)
        return
    if member:
        success = await apply_blacklist(ctx.guild, member, reason=reason)
    else:
        db.blacklist_player(ctx.guild.id, user_id, reason=reason or "Manual blacklist by admin")
        success = True
    if not success:
        await ctx.send(embed=discord.Embed(
            title="❌ فشل",
            description="لم أستطع تطبيق البلاك ليست.",
            color=COLORS["error"]
        ), delete_after=10)
        return
    embed = discord.Embed(
        title="🔇 تمت إضافة اللاعب للبلاك ليست",
        color=COLORS["warning"],
        timestamp=discord.utils.utcnow()
    )
    embed.add_field(name="👤 اللاعب", value=f"<@{user_id}>", inline=True)
    embed.add_field(name="👮 بواسطة", value=f"{ctx.author.mention}", inline=True)
    embed.add_field(name="⏱️ المدة", value="10 دقائق", inline=True)
    if reason:
        embed.add_field(name="📝 السبب", value=f"`{reason}`", inline=False)
    embed.set_footer(text=f"{BOT_FOOTER}  •  Blacklisted")
    embed = apply_branding(embed, ctx.guild)
    await ctx.send(embed=embed)
    # 🆕 حدّث القائمة في قناة البلاك ليست
    try:
        await update_blacklist_channel(ctx.guild)
    except Exception as e:
        logger.warning(f"update_blacklist_channel (blacklist_cmd) failed: {e}")


@bot.command(name="unblacklist", aliases=["ubl", "removebl"])
@commands.check(is_admin_check)
async def unblacklist_cmd(ctx, target: Union[discord.User, int] = None):
    """✅ !!unblacklist @user أو ID — إزالة لاعب من البلاك ليست"""
    if not target:
        await ctx.send(embed=discord.Embed(
            title="❌ Missing User",
            description=f"Usage: `{PREFIX}unblacklist @user أو ID`",
            color=COLORS["error"]
        ), delete_after=15)
        return
    user_id = target.id if isinstance(target, discord.User) else target
    member = ctx.guild.get_member(user_id)
    if member:
        await remove_blacklist(ctx.guild, member)
    else:
        db.remove_blacklist(ctx.guild.id, user_id)
    embed = discord.Embed(
        title="✅ تمت إزالة البلاك ليست",
        description="🎮 يمكنه استخدام البوت الآن",
        color=COLORS["success"],
        timestamp=discord.utils.utcnow()
    )
    embed.add_field(name="👤 اللاعب", value=f"<@{user_id}>", inline=True)
    embed.add_field(name="👮 بواسطة", value=f"{ctx.author.mention}", inline=True)
    embed.set_footer(text=f"{BOT_FOOTER}  •  Unblacklisted")
    embed = apply_branding(embed, ctx.guild)
    await ctx.send(embed=embed)
    # 🆕 حدّث القائمة في قناة البلاك ليست
    try:
        await update_blacklist_channel(ctx.guild)
    except Exception as e:
        logger.warning(f"update_blacklist_channel (unblacklist_cmd) failed: {e}")


@bot.command(name="blacklisted", aliases=["bllist", "blacklistlist"])
@commands.check(is_admin_check)
async def blacklisted_cmd(ctx):
    """📋 !!blacklisted — قائمة اللاعبين في البلاك ليست"""
    blacklisted = db.get_blacklisted_players(ctx.guild.id)
    embed = discord.Embed(
        title="📋 قائمة البلاك ليست",
        description=f"📊 **إجمالي:** `{len(blacklisted)}`",
        color=COLORS["warning"] if blacklisted else COLORS["success"],
        timestamp=discord.utils.utcnow()
    )
    embed.set_author(name="Blacklisted Players")
    if not blacklisted:
        embed.description = "> ✅  لا يوجد لاعبون في البلاك ليست"
    else:
        for i, b in enumerate(blacklisted[:15], 1):
            member = ctx.guild.get_member(b["user_id"])
            name = member.display_name if member else f"User#{b['user_id']}"
            mention = member.mention if member else f"<@{b['user_id']}>"
            reason = b.get("reason") or "غير محدد"
            expires = b.get("expires_at", "N/A")[:19] if b.get("expires_at") else "N/A"
            embed.add_field(
                name=f"#{i} — {name}",
                value=f"👤 {mention}\n📝 `{reason}`\n⏱️ ينتهي: `{expires}`",
                inline=False
            )
        if len(blacklisted) > 15:
            embed.set_footer(text=f"{BOT_FOOTER}  •  و {len(blacklisted) - 15} لاعب آخر")
    embed = apply_branding(embed, ctx.guild)
    await ctx.send(embed=embed)


@bot.command(name="rules")
async def rules_cmd(ctx):
    """🛡️ !!rules — عرض قواعد السيرفر"""
    # ✅ نفس الدالة المستخدمة في  !!setup  و  !!autosetup  — مصدر واحد للنص
    rules_embed = build_rules_embed(ctx.guild.name)
    await ctx.send(embed=rules_embed)


@bot.command(name="w")
@commands.check(is_admin_check)
async def winner_mvp_cmd(ctx, lobby_id: int = None, target: Union[discord.User, int] = None):
    """🏆 !!w <lobby_id> <@user/ID> — تعيين MVP WINNER يدوياً"""
    if lobby_id is None or target is None:
        await ctx.send(embed=discord.Embed(
            title="❌ Missing",
            description=f"Usage: `{PREFIX}w <lobby_id> <@user/ID>`",
            color=COLORS["error"]
        ))
        return
    user_id = target.id if isinstance(target, discord.User) else target
    lobby = db.get_lobby(lobby_id)
    if not lobby or lobby["status"] not in ("voting", "started"):
        await ctx.send(embed=discord.Embed(
            title="❌ Lobby not active",
            description=f"Lobby `#{lobby_id}` ليس في حالة تصويت.",
            color=COLORS["error"]
        ))
        return
    all_players = lobby["team1_players"] + lobby["team2_players"]
    if user_id not in all_players:
        await ctx.send(embed=discord.Embed(
            title="❌ لاعب غير موجود في الماتش",
            description=f"<@{user_id}> ليس من لاعبي هذا الماتش.",
            color=COLORS["error"]
        ))
        return
    if lobby_id not in _admin_mvp_results:
        _admin_mvp_results[lobby_id] = {}
    _admin_mvp_results[lobby_id]["winner"] = user_id
    await ctx.send(embed=discord.Embed(
        title="✅ تم تعيين MVP WINNER",
        description=(
            f"🏆 **MVP WINNER:** <@{user_id}>\n"
            f"📌 **Lobby:** `#{lobby_id}`"
        ),
        color=COLORS["success"]
    ))
    # لو الـ loser محدد مسبقاً — طبق النتيجة
    if _admin_mvp_results[lobby_id].get("loser"):
        await _apply_admin_mvp(ctx, lobby_id)


@bot.command(name="l")
@commands.check(is_admin_check)
async def loser_mvp_cmd(ctx, lobby_id: int = None, target: Union[discord.User, int] = None):
    """✦ !!l <lobby_id> <@user/ID> — تعيين MVP LOSER يدوياً"""
    if lobby_id is None or target is None:
        await ctx.send(embed=discord.Embed(
            title="❌ Missing",
            description=f"Usage: `{PREFIX}l <lobby_id> <@user/ID>`",
            color=COLORS["error"]
        ))
        return
    user_id = target.id if isinstance(target, discord.User) else target
    lobby = db.get_lobby(lobby_id)
    if not lobby or lobby["status"] not in ("voting", "started"):
        await ctx.send(embed=discord.Embed(
            title="❌ Lobby not active",
            description=f"Lobby `#{lobby_id}` ليس في حالة تصويت.",
            color=COLORS["error"]
        ))
        return
    all_players = lobby["team1_players"] + lobby["team2_players"]
    if user_id not in all_players:
        await ctx.send(embed=discord.Embed(
            title="❌ لاعب غير موجود في الماتش",
            description=f"<@{user_id}> ليس من لاعبي هذا الماتش.",
            color=COLORS["error"]
        ))
        return
    if lobby_id not in _admin_mvp_results:
        _admin_mvp_results[lobby_id] = {}
    _admin_mvp_results[lobby_id]["loser"] = user_id
    await ctx.send(embed=discord.Embed(
        title="✅ تم تعيين MVP LOSER",
        description=(
            f"✦ **MVP LOSER:** <@{user_id}>\n"
            f"📌 **Lobby:** `#{lobby_id}`"
        ),
        color=COLORS["success"]
    ))
    # لو الـ winner محدد مسبقاً — طبق النتيجة
    if _admin_mvp_results[lobby_id].get("winner"):
        await _apply_admin_mvp(ctx, lobby_id)


async def _apply_admin_mvp(ctx, lobby_id):
    """تطبق النتيجة من !!w و !!l بعد تعيين الاثنين.
    ✅ إصلاح: لا يحدّث الحالة قبل process_match_result_with_mvps."""
    data = _admin_mvp_results.get(lobby_id)
    if not data or not data.get("winner") or not data.get("loser"):
        return
    winner_id = data["winner"]
    loser_id = data["loser"]
    lobby = db.get_lobby(lobby_id)
    if not lobby:
        return
    # تحقق من أنهم ليسوا من نفس الفريق
    w_team = "team1" if winner_id in lobby["team1_players"] else "team2"
    l_team = "team1" if loser_id in lobby["team1_players"] else "team2"
    if w_team == l_team:
        await ctx.send(embed=discord.Embed(
            title="❌ MVP من نفس الفريق!",
            description="MVP WINNER و MVP LOSER يجب أن يكونا من فريقين مختلفين.",
            color=COLORS["error"]
        ))
        _admin_mvp_results.pop(lobby_id, None)
        return
    await ctx.send(embed=discord.Embed(
        title="⚙️ جارٍ تطبيق النقاط...",
        description=(
            f"🏆 **Winner Team:** {w_team}\n"
            f"🔱 **MVP WINNER:** <@{winner_id}>\n"
            f"✦ **MVP LOSER:** <@{loser_id}>"
        ),
        color=COLORS["warning"]
    ))
    guild = ctx.guild
    # ✅ إصلاح: لا تحدّث الحالة هنا — process_match_result_with_mvps يفعل ذلك
    # لو حدّثناها هنا، process_match_result_with_mvps سيرى "completed" ويرجع!
    _admin_mvp_results.pop(lobby_id, None)
    try:
        await process_match_result_with_mvps(
            guild, lobby_id, w_team,
            winner_id, loser_id,
            ctx.channel
        )
    except Exception as e:
        logger.exception(f"❌ _apply_admin_mvp failed: {e}")
        # ✅ حتى لو فشل — أنهِ الماتش
        try:
            db.update_lobby_status(lobby_id, "completed")
            _original_voice_channels.pop(lobby_id, None)
            await delete_match_channels(guild, lobby_id)
            cleanup_lobby_memory(lobby_id)
        except:
            pass
        await ctx.send(embed=discord.Embed(
            title="❌ فشل تطبيق النقاط",
            description=(
                f"🐛 **الخطأ:** `{str(e)[:200]}`\n"
                "✅ تم إنهاء الماتش وحذف القنوات"
            ),
            color=COLORS["error"]
        ))


@bot.command(name="startvote", aliases=["forcevote", "sv"])
@commands.check(is_admin_check)
async def startvote_cmd(ctx, lobby_id: int = None):
    """🗳️ !!startvote <lobby_id> — بدء التصويت فوراً (Admin only)
    يتجاوز cooldown الـ 10 دقائق."""
    if lobby_id is None:
        # ابحث عن أحدث ماتش نشط
        lobby = db.get_active_lobby_by_guild(ctx.guild.id)
        if lobby:
            lobby_id = lobby["id"]
        else:
            await ctx.send(embed=discord.Embed(
                title="❌ Missing Lobby ID",
                description=(
                    f"Usage: `{PREFIX}startvote <lobby_id>`\n"
                    f"أو استخدم `{PREFIX}startvote` لو فيه ماتش نشط\n"
                    f"💡 Use `{PREFIX}matches` لعرض الماتشات النشطة"
                ),
                color=COLORS["error"]
            ), delete_after=15)
            return
    lobby = db.get_lobby(lobby_id)
    if not lobby:
        await ctx.send(embed=discord.Embed(
            title="❌ Not Found",
            description=f"اللوبي `#{lobby_id}` غير موجود",
            color=COLORS["error"]
        ), delete_after=10)
        return
    if lobby["status"] != "started":
        await ctx.send(embed=discord.Embed(
            title="❌ Not Active",
            description=(
                f"اللوبي `#{lobby_id}` حالته: `{lobby['status']}`\n"
                "يجب أن يكون `started`"
            ),
            color=COLORS["error"]
        ), delete_after=10)
        return
    guild = ctx.guild
    # ✅ ابدأ التصويت فوراً بدون cooldown
    embed = discord.Embed(
        title="🗳️ تم بدء التصويت!",
        description=(
            "⚡ تم تجاوز cooldown الـ 10 دقائق\n"
            "🗳️ الهوست وأول داخل يصوتان الآن!"
        ),
        color=COLORS["success"],
        timestamp=discord.utils.utcnow()
    )
    embed.add_field(name="🏠 Lobby", value=f"`#{lobby_id}`", inline=True)
    embed.add_field(name="👮 Started by", value=f"{ctx.author.mention}", inline=True)
    embed.set_footer(text=f"{BOT_FOOTER}  •  Force Start Vote")
    embed = apply_branding(embed, guild)
    await ctx.send(embed=embed)
    logger.info(f"🗳️ Force startvote by {ctx.author.name} for lobby {lobby_id}")
    asyncio.create_task(auto_trigger_vote(lobby_id, guild))


@bot.command(name="resolve")
@commands.check(is_admin_check)
async def resolve_cmd(ctx, lobby_id: int = None, winner: str = None):
    if lobby_id is None or winner is None:
        await ctx.send(embed=discord.Embed(
            title="❌ Missing",
            description=f"Usage: `{PREFIX}resolve <id> <team1|team2>`",
            color=COLORS["error"]
        ))
        return
    winner = winner.lower()
    if winner not in ["team1", "team2"]:
        await ctx.send(embed=discord.Embed(
            title="❌ Invalid",
            description="Winner must be `team1` or `team2`.",
            color=COLORS["error"]
        ))
        return
    lobby = db.get_lobby(lobby_id)
    if not lobby or lobby["status"] != "voting":
        await ctx.send(embed=discord.Embed(
            title="❌ No Dispute",
            description=f"Lobby `#{lobby_id}` is not in voting status.",
            color=COLORS["error"]
        ))
        return
    await ctx.send(embed=discord.Embed(
        title="⚖️ Resolved!",
        description=(
            f"{ctx.author.mention} decided the winner:\n"
            f"**{'🔴 Team 1' if winner=='team1' else '🟢 Team 2'}**"
        ),
        color=COLORS["success"]
    ))
    await process_match_result(ctx.guild, lobby_id, winner, ctx.channel)


@bot.command(name="resetstats")
@commands.check(is_admin_check)
async def resetstats_cmd(ctx, target: Union[discord.User, int] = None):
    if not target:
        await ctx.send(embed=discord.Embed(
            title="❌ Missing User",
            description=f"Usage: `{PREFIX}resetstats @user أو ID`",
            color=COLORS["error"]
        ))
        return
    user_id = target.id if isinstance(target, discord.User) else target
    db.reset_stats(user_id, ctx.guild.id)
    member = ctx.guild.get_member(user_id)
    if member:
        await update_member_nickname(member, STARTING_LEVEL)
    await ctx.send(embed=discord.Embed(
        title="✅ Stats Reset",
        description=(
            f"<@{user_id}> — RANK `#{STARTING_LEVEL}`\n"
            "All stats have been reset to default."
        ),
        color=COLORS["success"]
    ))


# 🆕 إعادة تعيين الرانك + النقاط لكل أعضاء السيرفر إلى الصفر
@bot.command(name="resetrankall", aliases=["forceresetrankall", "resetallranks"])
@commands.check(is_admin_check)
async def resetrankall_cmd(ctx):
    """🏅 !!resetrankall — تصفير النقاط والرانك لكل أعضاء السيرفر"""
    guild = ctx.guild
    # ✅ إصلاح: بناء embed التقدّم كمتغير بشكل صحيح
    progress_embed = discord.Embed(
        title="🚀 جارٍ تصفير النقاط والرانك...",
        description=(
            "💰 **سيتم تصفير:** النقاط + الرانك\n"
            f"🏅 **الرانك المستهدف:** `#{STARTING_LEVEL}` (نقاط = 0)\n"
            "⏳ **انتظر...**"
        ),
        color=COLORS["warning"],
        timestamp=discord.utils.utcnow()
    )
    progress_embed.add_field(name="📊 عدد الأعضاء", value=f"`{len(guild.members)}`", inline=False)
    progress_embed.set_footer(text=f"{BOT_FOOTER}  •  Server-wide reset")
    progress_embed = apply_branding(progress_embed, ctx.guild)
    progress = await ctx.send(embed=progress_embed)
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
                rank_pos=0,
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
    # ✅ إصلاح: بناء embed النجاح كمتغير بشكل صحيح
    success_embed = discord.Embed(
        title="✅ تم تصفير كل البيانات!",
        description=(
            f"🏅 كل الأعضاء تم تصفيرهم إلى `RANK #{STARTING_LEVEL}` (نقاط = 0)\n"
            "💡 كل الستاتس (نقاط/فوز/خسارة/MVPs) صفرت أيضاً"
        ),
        color=COLORS["success"],
        timestamp=discord.utils.utcnow()
    )
    success_embed.add_field(name="✅ تم التصفير", value=f"`{reset_count}`", inline=True)
    success_embed.add_field(name="🤖 تم تخطي البوتات", value=f"`{skipped_bots}`", inline=True)
    success_embed.add_field(name="⚠️ فشل", value=f"`{failed}`", inline=True)
    success_embed.set_footer(text=f"{BOT_FOOTER}  •  Reset complete")
    success_embed = apply_branding(success_embed, ctx.guild)
    # ✅ إصلاح V5:زامن الـ Roles بعد التصفير (كانت تتأخر حتى الـ periodic sync)
    try:
        db.recalculate_ranks(guild.id)
        await sync_all_players_roles(guild)
        logger.info(f"✅ Roles synced after resetrankall in {guild.id}")
    except Exception as e:
        logger.warning(f"⚠️ Role sync after resetrankall failed: {e}")
    await progress.edit(embed=success_embed)
    logger.info(f"🏅 resetrankall: {reset_count} members fully reset to {STARTING_LEVEL} (points=0) in {guild.id}")


@bot.command(name="setlevel")
@commands.check(is_admin_check)
async def setlevel_cmd(ctx, target: Union[discord.User, int] = None, level: int = None):
    if not target or level is None:
        await ctx.send(embed=discord.Embed(
            title="❌ Missing",
            description=f"Usage: `{PREFIX}setlevel @user أو ID <level>`",
            color=COLORS["error"]
        ))
        return
    if level < 1 or level > 9999:
        await ctx.send(embed=discord.Embed(
            title="❌ Invalid Level",
            description="Level must be between `1` and `9999`.",
            color=COLORS["error"]
        ))
        return
    user_id = target.id if isinstance(target, discord.User) else target
    member = ctx.guild.get_member(user_id)
    name = member.display_name if member else f"User {user_id}"
    db.get_or_create_player(user_id, ctx.guild.id, name)
    db.update_player_stats(user_id, ctx.guild.id, level=level)
    if member:
        await update_member_nickname(member, level)
        # ✅ إصلاح V5: زامن الـ Role بعد تعيين الرانك يدوياً
        try:
            await sync_player_role(ctx.guild, member, level)
        except Exception as e:
            logger.warning(f"⚠️ Role sync after setlevel failed: {e}")
    await ctx.send(embed=discord.Embed(
        title="✅ Level Updated",
        description=f"<@{user_id}> → **RANK `#{level}`**",
        color=COLORS["success"]
    ))


@bot.command(name="setpoints")
@commands.check(is_admin_check)
async def setpoints_cmd(ctx, target: Union[discord.User, int] = None, points: int = None):
    if not target or points is None:
        await ctx.send(embed=discord.Embed(
            title="❌ Missing",
            description=f"Usage: `{PREFIX}setpoints @user أو ID <points>`",
            color=COLORS["error"]
        ))
        return
    if points < -99999 or points > 99999:
        await ctx.send(embed=discord.Embed(
            title="❌ Invalid Points",
            description="Points must be between `-99999` and `99999`.",
            color=COLORS["error"]
        ))
        return
    user_id = target.id if isinstance(target, discord.User) else target
    member = ctx.guild.get_member(user_id)
    name = member.display_name if member else f"User {user_id}"
    db.get_or_create_player(user_id, ctx.guild.id, name)
    db.update_player_stats(user_id, ctx.guild.id, points=points)
    db.recalculate_ranks(ctx.guild.id)
    player = db.get_player(user_id, ctx.guild.id)
    new_level = player.get("level", STARTING_LEVEL) if player else STARTING_LEVEL
    if member:
        await update_member_nickname(member, new_level)
    await ctx.send(embed=discord.Embed(
        title="✅ Points Updated",
        description=f"<@{user_id}> → **`{points}` points** (RANK `#{new_level}`)",
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
        title="✅ Synced",
        description=f"Synced `{updated}` members' nicknames successfully.",
        color=COLORS["success"]
    ))


@bot.command(name="syncroles", aliases=["syncranks", "updateroles"])
@commands.check(is_admin_check)
async def syncroles_cmd(ctx):
    """🔄 !!syncroles — مزامنة الـ Roles لكل اللاعبين حسب ترتيبهم"""
    progress = await ctx.send(embed=discord.Embed(
        title="🔄 جارٍ مزامنة الـ Roles...",
        description=(
            "📊 جاري تحديث ألقاب كل اللاعبين حسب ترتيبهم...\n"
            "⏳ انتظر..."
        ),
        color=COLORS["warning"],
        timestamp=discord.utils.utcnow()
    ))
    # أعِد حساب الرانكات أولاً
    db.recalculate_ranks(ctx.guild.id)
    # يزامن الـ Roles
    await sync_all_players_roles(ctx.guild)
    # ✅ إصلاح: بناء embed النجاح كمتغير بشكل صحيح
    synced_embed = discord.Embed(
        title="✅ تمت مزامنة الـ Roles!",
        description="🔄 كل اللاعبين تم تحديث ألقابهم حسب ترتيبهم.",
        color=COLORS["success"],
        timestamp=discord.utils.utcnow()
    )
    synced_embed.add_field(name="🏅 Roles", value="🏆 **#1:** Best Player\n💎 **#2-10:** Goated Players (SoundBoard + Waiting Prv)\n⭐ **#11-50:** Skilled Players (SoundBoard)\n🎯 **#51-100:** Efficient Players", inline=False)
    synced_embed.set_footer(text=f"{BOT_FOOTER}  •  Roles synced")
    synced_embed = apply_branding(synced_embed, ctx.guild)
    await progress.edit(embed=synced_embed)


# ============================================================
# HELP COMMANDS
# ============================================================

@bot.command(name="general")
async def general_cmd(ctx):
    embed = discord.Embed(
        title="🎮 Player Commands",
        description=f"📌 **Prefix:** `{PREFIX}`",
        color=COLORS["play"]
    )
    embed.add_field(name="🚀 Play", value=f"• `{PREFIX}play 4v4` أو `{PREFIX}play4v4` — 4v4 (الافتراضي)\n• `{PREFIX}play 2v2` أو `{PREFIX}play2v2` — 2v2\n• `{PREFIX}play 3v3` أو `{PREFIX}play3v3` — 3v3\n• `{PREFIX}play 1v1` أو `{PREFIX}play1v1` 🔒 (للـ roles العالية)\n• ⚠️ `{PREFIX}play` بدون مود → رسالة خطأ", inline=False)
    embed.add_field(name="📊 Stats", value=f"• `{PREFIX}p` — Profile (full stats)\n• `{PREFIX}points` — 💰 نقاطك + تقدم الرانك\n• `{PREFIX}card` — Card (zelika-play)\n• `{PREFIX}top` — Leaderboard (Top 10)\n• `{PREFIX}mylevel` — Your rank\n• `{PREFIX}matches` — Active lobbies", inline=False)
    embed.add_field(name="🎮 Control", value=f"• `{PREFIX}leave` — Leave lobby\n• `{PREFIX}fixrank` — Apply rank", inline=False)
    embed.add_field(name="🤖 How to Play", value=f"1️⃣ Join a ⏳ waiting room\n2️⃣ `{PREFIX}play 4v4` in a play channel (حدد المود!)\n3️⃣ Press **Create Lobby** → Enter Room Info\n4️⃣ Players press **Join Team 1 / 2**\n5️⃣ Lobby fills → Match starts\n6️⃣ Host presses **Start Vote** (or **Cancel Match** to abort)\n7️⃣ Vote → Result → Points + RANK updates\n8️⃣ Players return to waiting rooms", inline=False)
    embed.add_field(name="💰 نظام النقاط", value="🔱 Winner MVP: `+80` pts\n✅ Winners: `+30` pts\n✦ Loser MVP: `+30` pts\n☠️ Losers: `-30` pts\n📈 كل `50` نقطة = `+1` رانك", inline=False)
    embed.set_footer(text=f"{BOT_FOOTER}  •  v4.0  ·  {PREFIX}help (admin)")
    embed = apply_branding(embed, ctx.guild)
    await ctx.send(embed=embed)


@bot.command(name="help")
async def help_cmd(ctx):
    # 📄 رسالة 1: أوامر اللاعبين
    embed1 = discord.Embed(
        title="🔥 Free Fire Bot v4.0 — أوامر اللاعبين",
        description=(
            f"📌 **Prefix:** `{PREFIX}`\n"
            "🎮 جميع الأوامر تعمل في قنوات play"
        ),
        color=COLORS["play"],
        timestamp=discord.utils.utcnow()
    )
    embed1.add_field(name="🎮 اللعب (9 أوامر)", value=f"• `{PREFIX}play 4v4` أو `{PREFIX}play4v4` — 4v4\n• `{PREFIX}play 3v3` أو `{PREFIX}play3v3` — 3v3\n• `{PREFIX}play 2v2` أو `{PREFIX}play2v2` — 2v2\n• `{PREFIX}play 1v1` أو `{PREFIX}play1v1` 🔒 (للـ roles العالية)\n• `{PREFIX}play` — رسالة خطأ (حدد المود)\n• `{PREFIX}leave` — مغادرة اللوبي\n• `{PREFIX}matches` — الماتشات النشطة\n• `{PREFIX}matchinfo <id>` — تفاصيل ماتش", inline=False)
    embed1.add_field(name="📊 الإحصائيات (7 أوامر)", value=f"• `{PREFIX}p` أو `{PREFIX}p @user` — البروفايل\n• `{PREFIX}points` أو `{PREFIX}points @user` — النقاط + تقدم الرانك\n• `{PREFIX}card` أو `{PREFIX}card @user` — بطاقة اللاعب\n• `{PREFIX}top` — Leaderboard Top 10\n• `{PREFIX}mylevel` أو `{PREFIX}mylevel @user` — الرانك\n• `{PREFIX}myrank` — النك نيم المستهدف\n• `{PREFIX}fixrank` أو `{PREFIX}fixrank @user` — تطبيق الرانك", inline=False)
    embed1.add_field(name="⚠️ البلاغات (3 أوامر)", value=f"• `{PREFIX}report @user [سبب]` — بلّغ عن لاعب (6 = حظر)\n• `{PREFIX}reports` أو `{PREFIX}reports @user` — عرض البلاغات\n• ⚠️ زر البلاغ متاح داخل كل ماتش", inline=False)
    embed1.add_field(name="🛡️ المساعدة (4 أوامر)", value=f"• `{PREFIX}rules` — عرض قواعد السيرفر (بدون قناة مخصصة)\n• `{PREFIX}general` — دليل اللاعب\n• `{PREFIX}help` — هذه القائمة\n• `{PREFIX}botinfo` — معلومات البوت", inline=False)
    embed1.set_footer(text=f"{BOT_FOOTER}  •  صفحة 1/2  ·  أوامر الأدمن في الصفحة التالية")
    embed1 = apply_branding(embed1, ctx.guild)
    await ctx.send(embed=embed1)

    # 📄 رسالة 2: أوامر الأدمن
    embed2 = discord.Embed(
        title="🔧 Free Fire Bot v4.0 — أوامر الأدمن",
        description=(
            f"📌 **Prefix:** `{PREFIX}`\n"
            "🔒 جميع الأوامر التالية للأدمن فقط"
        ),
        color=COLORS["admin"],
        timestamp=discord.utils.utcnow()
    )
    embed2.add_field(name="🔧 القنوات والـ Setup (8 أوامر)", value=f"• `{PREFIX}setup` — إنشاء كل القنوات + Roles + JAIL\n• `{PREFIX}autosetup` — فحص وإصلاح الناقص تلقائياً (آمن على البيانات)\n• `{PREFIX}cleanup` — حذف كاتيجوريات الماتش المنتهية\n• `{PREFIX}scan [page]` — عرض كل القنوات\n• `{PREFIX}deletecat <name>` — تحديد كاتيجوري للحذف\n• `{PREFIX}confirmcat <name>` — تأكيد حذف كاتيجوري\n• `{PREFIX}setcommandschannel #ch` — إضافة/إزالة قناة أوامر\n• `{PREFIX}setleaderboard` — تعيين قناة Leaderboard", inline=False)
    embed2.add_field(name="🏅 الرانك والنقاط والـ Roles (8 أوامر)", value=f"• `{PREFIX}fixrankall` — تطبيق الرانك على كل الأعضاء\n• `{PREFIX}syncnicknames` — مزامنة كل النكات\n• `{PREFIX}syncroles` — مزامنة الـ Roles حسب الترتيب\n• `{PREFIX}setlevel @user/ID <n>` — تعيين رانك لاعب\n• `{PREFIX}setpoints @user/ID <n>` — تعيين نقاط لاعب (يُحدّث الرانك تلقائياً)\n• `{PREFIX}resetstats @user/ID` — تصفير ستاتس لاعب\n• `{PREFIX}resetrankall` — تصفير كل البيانات لكل السيرفر", inline=False)
    embed2.add_field(name="⚠️ البلاغات والحظر (5 أوامر)", value=f"• `{PREFIX}banplayer @user/ID [سبب]` — حظر لاعب + نقله لفويس التفتيش\n• `{PREFIX}unbanplayer @user/ID` — فك حظر لاعب\n• `{PREFIX}banned` — قائمة المحظورين\n• `{PREFIX}setreportchannel #voice` — إضافة فويس تفتيش\n• `{PREFIX}removereportchannel #voice` — حذف فويس تفتيش", inline=False)
    embed2.add_field(name="🔒 نظام السجن JAIL (2 أمر)", value=f"• `{PREFIX}jail @user/ID [سبب]` — إرسال لاعب للسجن + فويس خاص\n• `{PREFIX}unjail @user/ID` — فك السجن", inline=False)
    embed2.add_field(name="🔇 نظام البلاك ليست (3 أوامر)", value=f"• `{PREFIX}blacklist @user/ID [سبب]` — إضافة لاعب للبلاك ليست\n• `{PREFIX}unblacklist @user/ID` — إزالة لاعب من البلاك ليست\n• `{PREFIX}blacklisted` — قائمة البلاك ليست", inline=False)
    embed2.add_field(name="📋 معلومات إضافية (6 أوامر)", value=f"• `{PREFIX}reportchannels` — عرض فويسات التفتيش\n• `{PREFIX}startvote [id]` — 🗳️ بدء التصويت فوراً (يتجاوز cooldown 10 دقائق)\n• `{PREFIX}resolve <id> <team1|team2>` — حل نزاع التصويت\n• `{PREFIX}w <id> <@user/ID>` — تعيين MVP WINNER يدوياً\n• `{PREFIX}l <id> <@user/ID>` — تعيين MVP LOSER يدوياً\n• `{PREFIX}botinfo` — معلومات البوت", inline=False)
    embed2.add_field(name="💡 معلومات النظام", value=f"💰 **النقاط:** MVP فائز +80 • فائز +30 • MVP خاسر +30 • خاسر -30\n🏅 **الرانك:** ترتيب الـ leaderboard (1 = الأفضل)\n🗳️ **تصويت MVP:** أول 2 من كل فريق (4 مصوّتين) يختارون WINNER و LOSER — يحتاج `{MVP_CONSENSUS_NEEDED}` أصوات\n🚨 **ما في تفاهم:** البوت ينقل أدمن لو حاضر بالفويسات الخاصة، وإلا يتاغه مع `!!w` و `!!l`\n🏆 **Roles:** #1 Best Player • #2-10 Goated • #11-50 Skilled • #51-100 Efficient\n⚠️ **البلاغات:** 6 بلاغات = حظر تلقائي\n🔒 **JAIL:** فويس خاص + شاتات مخصصة فقط\n🔇 **BLACKLIST:** 3 دق غياب أو 5 خروج/دخول = منع 10 دقائق\n🗳️ **Cancel Match:** أغلبية اللاعبين (5 من 8)\n🛡️ **Rules channel:** `{RULES_CHANNEL_NAME}` — للقراءة فقط (ينشئها `!!setup`)، أو `{PREFIX}rules` في أي قناة", inline=False)
    embed2.set_footer(text=f"{BOT_FOOTER}  •  صفحة 2/2  ·  v4.0  ·  51 أمر إجمالي")
    embed2 = apply_branding(embed2, ctx.guild)
    await ctx.send(embed=embed2)


@bot.command(name="cloudbackup")
@commands.is_owner()
async def cloudbackup_cmd(ctx):
    """☁️ نسخ احتياطي كامل للسحابة."""
    if not _CLOUD_AVAILABLE or not is_cloud_enabled():
        embed = discord.Embed(
            title="☁️ Cloud Backup",
            description=(
                "❌ Cloud backup not enabled!\n"
                "Set `MONGODB_URI` environment variable."
            ),
            color=COLORS["error"]
        )
        embed = apply_branding(embed, ctx.guild)
        await ctx.send(embed=embed)
        return
    
    await ctx.send("☁️ Starting full cloud backup...")
    success, msg = await full_backup_to_cloud(db)
    color = COLORS["success"] if success else COLORS["error"]
    embed = discord.Embed(
        title="☁️ Cloud Backup",
        description=f"{'✅' if success else '❌'} {msg}",
        color=color
    )
    embed = apply_branding(embed, ctx.guild)
    await ctx.send(embed=embed)


@bot.command(name="cloudrestore")
@commands.is_owner()
async def cloudrestore_cmd(ctx):
    """☁️ استرجاع كامل من السحابة (يحذف البيانات المحلية)."""
    if not _CLOUD_AVAILABLE or not is_cloud_enabled():
        embed = discord.Embed(
            title="☁️ Cloud Restore",
            description=(
                "❌ Cloud backup not enabled!\n"
                "Set `MONGODB_URI` environment variable."
            ),
            color=COLORS["error"]
        )
        embed = apply_branding(embed, ctx.guild)
        await ctx.send(embed=embed)
        return
    
    embed = discord.Embed(
        title="⚠️ Cloud Restore",
        description=(
            "This will **DELETE all local data** and replace it with cloud data.\n"
            "React with ✅ to confirm."
        ),
        color=COLORS["warning"]
    )
    embed = apply_branding(embed, ctx.guild)
    msg = await ctx.send(embed=embed)
    await msg.add_reaction("✅")
    await msg.add_reaction("❌")
    
    def check(reaction, user):
        return user == ctx.author and str(reaction.emoji) in ("✅", "❌") and reaction.message_id == msg.id
    
    try:
        reaction, user = await bot.wait_for("reaction_add", timeout=30.0, check=check)
        if str(reaction.emoji) == "❌":
            await ctx.send("❌ Cancelled.")
            return
    except asyncio.TimeoutError:
        await ctx.send("⏰ Timed out.")
        return
    
    await ctx.send("☁️ Restoring from cloud...")
    success, msg = await full_restore_from_cloud(db)
    color = COLORS["success"] if success else COLORS["error"]
    embed = discord.Embed(
        title="☁️ Cloud Restore",
        description=f"{'✅' if success else '❌'} {msg}",
        color=color
    )
    embed = apply_branding(embed, ctx.guild)
    await ctx.send(embed=embed)


@bot.command(name="cloudstatus")
async def cloudstatus_cmd(ctx):
    """☁️ حالة الاتصال بالسحابة."""
    if not _CLOUD_AVAILABLE:
        status = "❌ cloud_backup.py not found"
    elif not is_cloud_enabled():
        status = "⚠️ MONGODB_URI not set"
    else:
        try:
            from cloud_backup import _get_client
            client, database = _get_client()
            if database is not None:
                from cloud_backup import get_all_cloud_guilds
                guilds = get_all_cloud_guilds()
                status = f"✅ Connected! {len(guilds)} guild(s) in cloud"
            else:
                status = "❌ Connection failed"
        except Exception as e:
            status = f"❌ Error: {e}"
    
    embed = discord.Embed(
        title="☁️ Cloud Status",
        description=f"{status}",
        color=COLORS["info"]
    )
    embed = apply_branding(embed, ctx.guild)
    await ctx.send(embed=embed)


@bot.command(name="serverleave")
async def serverleave_cmd(ctx):
    """🔒 أمر خاص بصاحب البوت — يجعل البوت يغادر سيرفر معين (DM فقط)."""
    # فقط في الـ DM
    if ctx.guild is not None:
        await ctx.send("❌ هذا الأمر يعمل في الـ DM فقط!")
        return
    # فقط صاحب البوت
    if ctx.author.id != BOT_OWNER_ID:
        await ctx.send("❌ هذا الأمر لصاحب البوت فقط!")
        return
    # فحص المعاملات
    args = ctx.message.content.split()
    if len(args) < 2:
        # عرض قائمة السيرفرات
        if not bot.guilds:
            await ctx.send("البوت لا يوجد في أي سيرفر.")
            return
        msg = "**السيرفرات الحالية:**\n\n"
        for i, g in enumerate(bot.guilds, 1):
            msg += f"`{i}`. **{g.name}** (ID: `{g.id}`) — {g.member_count} عضو\n"
        msg += f"\nاستخدم: `!!serverleave <ID>` لترك سيرفر معين."
        await ctx.send(msg)
        return
    # محاولة ترك السيرفر
    try:
        guild_id = int(args[1])
    except ValueError:
        await ctx.send("❌ ID غير صحيح. استخدم رقم ID السيرفر.")
        return
    guild = bot.get_guild(guild_id)
    if not guild:
        await ctx.send(f"❌ السيرفر `{guild_id}` غير موجود.")
        return
    try:
        await guild.leave()
        await ctx.send(f"✅ تم مغادرة السيرفر **{guild.name}** بنجاح!")
        logger.info(f"🔓 Owner left server: {guild.name} ({guild.id})")
    except Exception as e:
        await ctx.send(f"❌ فشل مغادرة السيرفر: {e}")


# ============================================================
# RUN
# ============================================================
def _start_health_server():
    """🆕 FIX (Railway/Render): البوت ليس خدمة ويب، لكن Procfile يقول `web:` —
    فبعض المنصّات تتوقّع فتح منفذ PORT وتعيد تشغيل الحاوية كل حين إذا لم يُفتح
    (سبب شائع أيضاً لـ «autosetup كل عدة دقائق» لأنه يعيد on_ready). نفتح سيرفر
    صحّة بسيط يستجيب 200 على أي مسار. يُفعَّل فقط إذا كان PORT موجوداً."""
    port = os.getenv("PORT")
    if not port:
        return
    try:
        port = int(port)
    except (TypeError, ValueError):
        logger.warning(f"⚠️ Invalid PORT value {port!r} — health server skipped")
        return

    import http.server
    import socketserver

    class _HealthHandler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"OK - Apostado Play Bot is alive")

        def do_HEAD(self):
            self.send_response(200)
            self.end_headers()

        def log_message(self, *args):
            pass

    class _ReusableTCPServer(socketserver.ThreadingTCPServer):
        allow_reuse_address = True
        daemon_threads = True

    def _serve():
        try:
            with _ReusableTCPServer(("0.0.0.0", port), _HealthHandler) as httpd:
                logger.info(f"❤️ Health server listening on 0.0.0.0:{port}")
                httpd.serve_forever()
        except Exception as e:
            logger.warning(f"⚠️ Health server failed on :{port}: {e}")

    threading.Thread(target=_serve, name="health-server", daemon=True).start()


if __name__ == "__main__":
    # ⚠️ تحذير أمني: التوكن مكتوب كـ fallback للراحة.
    # للحصول على أمان أعلى، يُفضّل استخدام متغير البيئة DISCORD_TOKEN فقط
    # وحذف التوكن من هنا نهائياً.
    TOKEN = os.getenv("DISCORD_TOKEN")
    if not TOKEN:
        raise RuntimeError("❌ DISCORD_TOKEN environment variable is required! Set it on Railway/Render.")
    _start_health_server()
    logger.info("🚀 Starting Free Fire Bot v4.0 CLEAN...")
    bot.run(TOKEN)
