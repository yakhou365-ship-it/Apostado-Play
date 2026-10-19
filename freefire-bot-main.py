"""
===========================================================
  Free Fire Matchmaking Bot
===========================================================
  Manage Free Fire matches (1v1/2v2/3v3/4v4) + MVP voting + dynamic ranks

  ✅ 55 commands | 8,600+ lines
  ✅ Vote: all players + half+1 + cross-team + no timeout
  ✅ 1v1 has dedicated system (TeamWinnerVoteView)
  ✅ Soft Blacklist (warnings + reset + admin exemption)
  ✅ MongoDB Atlas optional cloud backup
  ✅ Health server on $PORT (Railway/Render compatible)
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
import time
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Union

# ☁️ Cloud Backup — MongoDB Atlas Sync
try:
    from cloud_backup import (
        is_cloud_enabled, auto_restore_database, sync_guild_players_to_cloud,
        sync_player_to_cloud, sync_bans_to_cloud, sync_guild_settings_to_cloud,
        sync_blacklist_to_cloud, sync_reports_to_cloud,
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

# 🆕 Name of the role that gets tagged when an issue occurs
ADMIN_ROLE_NAME = "Admin"  # change this to match the role name in your server

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

LOBBY_TIMEOUT_SECONDS = 1800

# 🆕 Group MVP voting system — every player votes (no timeout)
# The threshold is dynamic (half the voter count) inside MvpVoteView
# ✅ Removed VOTE_TIMEOUT_SECONDS, MVP_VOTERS_PER_TEAM and MVP_CONSENSUS_NEEDED
# ✅ Cross-team rule: need one vote from each team on the same player (WINNER and LOSER)
# ✅ 1v1 has its own dedicated system: TeamWinnerVoteView with a single Select for the winning team

# 🆕 Build identifier — Railway sets RAILWAY_GIT_COMMIT_SHA automatically on deploy from Git
#    Shown in !!botinfo to confirm exactly which version is running (otherwise we can't tell if a change was deployed)
BUILD_ID = os.getenv("RAILWAY_GIT_COMMIT_SHA") or os.getenv("BOT_BUILD_ID") or "local-dev"
BUILD_SHA = str(BUILD_ID)[:7]

# 🆕 Role-change retry settings (fixes errors being silently swallowed)
ROLE_OP_RETRY_ATTEMPTS = 3   # number of retries on rate limit / temporary network error
ROLE_OP_RETRY_BASE_DELAY = 1.5  # base wait in seconds (exponential backoff)

# 🆕 "Create Lobby" message — disappears after this duration if no one created the room
# ✅ Sped up: raised from 60 to 120 seconds (two minutes) per admin request — all
#    temporary embeds disappear either when the match ends or after two minutes at most.
CREATE_PROMPT_DELETE_AFTER = 120   # seconds (two minutes)

# 🆕 Maximum lifetime of any temporary embed (messages like "Create Lobby", lobby messages,
#    cancel/timeout notifications) — disappears automatically even if the match hasn't ended yet
TEMP_EMBED_DELETE_AFTER = 120   # seconds (two minutes)

# 🆕 Reports & Bans System
REPORT_THRESHOLD = 6            # number of reports needed for an automatic ban
REPORT_CHANNELS_COUNT = 3       # number of voice channels the banned player can still access
REPORT_CATEGORY_NAME = "⚠️ Reports & Bans"  # name of the reports category

# 🆕 JAIL system — defined here (before commands and events) to work correctly
JAIL_ROLE_NAME = "JAIL"
JAIL_CHAT_NAME = "・💬jail-chat"
JAIL_PROUVES_NAME = "・💬jail-prouves"
JAIL_CATEGORY_NAME = "🔒 JAIL"

# 🆕 BLACKLIST system — temporarily blocks offenders from using the bot
# Softened as much as possible:
#    - raised thresholds: 180→300s cumulative, 5→8 leave count
#    - shortened ban duration: 600→300s (5 minutes instead of 10)
#    - gradual reset after 60 seconds staying in a match (zeroes the cumulative counter)
#    - admins and the Owner are excluded from tracking
#    - staged warnings at 50% and 80% of the threshold before it's applied
BLACKLIST_ROLE_NAME = "🔇 Blacklisted"
BLACKLIST_CHANNEL_NAME = "🔇 Blacklisted"  # 🆕 dedicated channel listing blacklisted players
BLACKLIST_TIME_LIMIT = 300   # 5 minutes cumulative absence (was 180s)
BLACKLIST_MAX_LEAVES = 8     # 8 leave/join cycles (was 5)
BLACKLIST_DURATION = 300     # 5 minute ban duration (was 600s)
BLACKLIST_RESET_AFTER_STAY = 60  # 🆕 time staying in a match before the tracking resets (seconds)
BLACKLIST_WARN_LEVEL_1_TIME = 150   # 🆕 first warning at 150s cumulative (50% of 300)
BLACKLIST_WARN_LEVEL_2_TIME = 240   # 🆕 final warning at 240s cumulative (80% of 300)
BLACKLIST_WARN_LEVEL_1_LEAVES = 4   # 🆕 first warning at 4 leaves (50% of 8)
BLACKLIST_WARN_LEVEL_2_LEAVES = 6   # 🆕 final warning at 6 leaves (75% of 8)

# 🆕 Dynamic Title Roles System
# Bot creates these Roles and grants/revokes automatically based on rank
RANK_TITLES = {
    1: {
        "name": "🏆 Best Player",
        "arabic": "",
        "color": 0xE74C3C,  # red
        "permissions": ["soundboard", "waiting_prv"],
        "max_rank": 1,  # only the #1
    },
    2: {
        "name": "💎 Goated Players",
        "arabic": "",
        "color": 0xF1C40F,  # gold
        "permissions": ["soundboard", "waiting_prv"],
        "max_rank": 10,  # from #1 to #10
    },
    3: {
        "name": "⭐ Skilled Players",
        "arabic": "",
        "color": 0x9B59B6,  # purple
        "permissions": ["soundboard"],
        "max_rank": 50,  # from #11 to #50
    },
    4: {
        "name": "🎯 Efficient Players",
        "arabic": "",
        "color": 0x3498DB,  # blue
        "permissions": [],
        "max_rank": 100,  # from #51 to #100
    },
}

# names of the private waiting-room categories (used to verify them when granting permissions)
WAITING_PRV_CATEGORY_HINT = "Waiting Prv"

# ══════════════════════════════════════════════
# V0 DESIGN SYSTEM — Color Palette
# ══════════════════════════════════════════════
# 🎨 Unified color palette (6 base + 5 rank)
# ══════════════════════════════════════════════
COLORS = {
    "success":     0x57F287,  # success
    "error":       0xED4245,  # error
    "warning":     0xFEE75C,  # warning
    "info":        0x5865F2,  # info
    "play":        0xFF6B00,  # play
    "vote":        0x5865F2,  # vote (= info)
    "leaderboard": 0xFAA61A,  # leaderboard
    "admin":       0x4752C4,  # admin
    "neutral":     0x2B2D31,  # neutral
    # player rank colors (dynamic, by rank)
    "rank_low":    0x95A5A6,  # gray - low rank
    "rank_mid":    0x3498DB,  # blue - mid rank
    "rank_high":   0x9B59B6,  # purple - high rank
    "rank_elite":  0xF1C40F,  # gold - elite rank
    "rank_legend": 0xE74C3C,  # red - legend
    # aliases (for compatibility with old code)
    "match":       0xFF6B00,  # = play
    "auto":        0xFF6B00,  # = play
    "profile":     0x9B59B6,  # = rank_high
}

# official bot branding (used in all embeds)
BOT_LOGO_URL = "https://i.imgur.com/8RYMfAE.png"
BOT_FOOTER = "{server_name}"   # simple footer: server name only

# images/GIFs disabled - removed from all embeds (V0 clean design)
BOT_BANNER_URL = None

# rules image disabled
RULES_IMAGE_URL = None

# per-server custom GIF disabled
# (SERVER_GIFS and SERVER_GIFS_BY_NAME removed - no longer used after the V0 redesign)


def apply_branding(embed, guild):
    """V0: Adds footer + timestamp only — no images/GIFs (clean design)."""
    if not guild:
        return embed
    # Dynamic footer based on server name
    try:
        footer_text = BOT_FOOTER.format(server_name=guild.name)
    except Exception:
        footer_text = BOT_FOOTER
    embed.set_footer(text=footer_text)
    embed.timestamp = discord.utils.utcnow()
    # Clean design — no images or GIFs at the bottom of the embed
    return embed

def get_rank_color(level):
    """🆕 Returns a color based on rank."""
    if level <= 1:    return COLORS["rank_legend"]   # 🔱 #1
    if level <= 3:    return COLORS["rank_elite"]    # 💎 Top 3
    if level <= 10:   return COLORS["rank_high"]     # 🔥 Top 10
    if level <= 50:   return COLORS["rank_mid"]      # ⭐ Top 50
    return COLORS["rank_low"]                        # 🎯 remaining players

def get_rank_title(level):
    """🆕 Returns player title based on rank ( Roles)."""
    if level == 1:   return "Best Player"
    if level <= 10:  return "Goated Player"
    if level <= 50:  return "Skilled Player"
    if level <= 100: return "Efficient Player"
    return "Rookie"

def get_rank_emoji(level):
    """🆕 Returns emoji based on rank ( RANK_TITLES tiers).
✅ V5: Roles:
- #1 → 🏆 Best Player (tier 1)
- #2-10 → 💎 Goated Players (tier 2)
- #11-50 → ⭐ Skilled Players (tier 3)
- #51+ → 🎯 Efficient/Rookie (tier 4+)"""
    if level == 1:    return "🏆"  # #1 — Best Player
    if level <= 10:   return "💎"  # #2-10 — Goated Players
    if level <= 50:   return "⭐"  # #11-50 — Skilled Players
    return "🎯"  # #51+ — Efficient/Rookie

def make_progress_bar(current, total, length=10):
    """Creates professional visual progress bar."""
    if total == 0:
        return "░" * length
    filled = int((current / total) * length)
    filled = min(filled, length)
    return "█" * filled + "░" * (length - filled)

def make_winrate_bar(winrate, length=10):
    """Win-rate bar with gradient colors."""
    filled = round(winrate / 10)
    filled = min(filled, length)
    if winrate >= 70:
        return "🟩" * filled + "⬛" * (length - filled)
    elif winrate >= 40:
        return "🟨" * filled + "⬛" * (length - filled)
    else:
        return "🟥" * filled + "⬛" * (length - filled)

def separator():
    """Visual separator — V0 new design."""
    return "──────────────────────"

def points_to_next_rank(points, db=None, gid=None):
    """Calculates difference between player points and top points."""
    if db is not None and gid is not None:
        top = db.get_top_points(gid)
        if top > points:
            return top - points
    return 0

def get_mvp_player(players_list, guild, db, gid):
    """🆕 Determines team MVP — highest rank (lowest rank number), tie broken by highest streak.
None."""
    if not players_list:
        return None
    best = None
    best_score = -1
    for pid in players_list:
        player = db.get_player(pid, gid)
        if not player:
            continue
        # in the new system a lower rank number is better; multiply by -1 so higher = better
        # Score = -level (lower level is better) + win_streak (tiebreaker between equal players)
        score = -player.get("level", 9999) * 1000 + player.get("win_streak", 0)
        if score > best_score:
            best_score = score
            best = pid
    return best

def get_mvp_badge(mvp_count):
    """🆕 Returns MVP badge based on MVP count.
    - 0 MVPs: no badge
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
    """🆕 Returns MVP title based on count."""
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
# RANK-BASED ROLES - dynamic title roles
# ============================================================

def get_role_tier_for_rank(rank):
    """🆕 Determines which Role tier a player should get based on rank.
tier (1=Best, 2=Goated, 3=Skilled, 4=Efficient) None #100."""
    if rank == 1:
        return 1  # Best Player
    if rank <= 10:
        return 2  # Goated Players
    if rank <= 50:
        return 3  # Skilled Players
    if rank <= 100:
        return 4  # Efficient Players
    return None  # beyond #100 = no role

async def create_role_if_not_exists(guild, role_name, color):
    """🆕 Creates role if not exists, returns it."""
    # look for an existing role with the same name
    for role in guild.roles:
        if role.name == role_name:
            return role
    # create a new role
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
    """🆕 Executes add_roles / remove_roles with smart retry — instead of silently swallowing errors.

✅ (ok: bool, permanent_error: bool) None:
• rate limit (429) → exponential backoff
• discord.Forbidden / HierarchyError → **** (needs admin fix)
• discord.NotFound → role/

⚠️ Exceptions — ."""
    if attempts is None:
        attempts = ROLE_OP_RETRY_ATTEMPTS
    action = "" if add else ""
    action_api = "add_roles" if add else "remove_roles"
    delay = ROLE_OP_RETRY_BASE_DELAY
    last_exc = None

    for attempt in range(1, attempts + 1):
        try:
            if add:
                await member.add_roles(role, reason=reason)
            else:
                await member.remove_roles(role, reason=reason)
            logger.info(f"✅ {action} role {role.name!r} → {member.display_name} ({action_api}, {attempt}/{attempts})")
            return True, False

        except discord.NotFound:
            logger.warning(
                f"⚠️ NotFound {action_api}: role={role.name!r} member={member.id}"
                f"(role not on the member - harmless)"
            )
            return False, False

        except discord.Forbidden as e:
            msg = str(e).lower()
            hierarchy = ("highest" in msg) or ("hierarchy" in msg)
            logger.error(
                f"❌ Forbidden {action_api}: role={role.name!r} member={member.id}"
                f"in_guild={getattr(member.guild, 'name', '?')} | hierarchy={hierarchy} | {e}"
            )
            return False, True

        except discord.HTTPException as e:
            last_exc = e
            status = getattr(e, "status", None) or getattr(e, "code", None)
            if status == 429:
                logger.warning(
                    f"⏳ Rate limit on {action_api} (attempt {attempt}/{attempts}): role={role.name!r} member={member.id}"
                )
            else:
                logger.warning(
                    f"⚠️ HTTP {status} {action_api} (attempt {attempt}/{attempts}):"
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
                f"❌ Failed {action_api} after {attempts} attempts: role={role.name!r} member={member.id} | {e}"
            )
            return False, False

        except Exception as e:
            logger.exception(
                f"❌ Unexpected error in {action_api}: role={role.name!r} member={member.id} | {e}"
            )
            return False, False

    logger.error(f"❌ {action_api} exhausted: role={role.name!r} member={member.id} | last={last_exc}")
    return False, False

async def sync_player_role(guild, member, rank):
    """🆕 Syncs player role based on rank.

✅ :
• add/remove role_change_with_retry (rate limit + logging)
• ** role → role **
( Rank Role )
• Forbidden →"""
    if not member or member.bot:
        return
    target_tier = get_role_tier_for_rank(rank)

    # collect the names of all title roles
    title_role_names = {tier: data["name"] for tier, data in RANK_TITLES.items()}

    # ─────────────────────────────────────────────
    # 1) remove from the player any title role they no longer qualify for
    # ─────────────────────────────────────────────
    removal_failed = []   # names of roles that failed to be removed
    permanent_error = None

    for tier, role_name in title_role_names.items():
        if tier == target_tier:
            continue  # this is the role we want - keep it
        # if the player has this role, remove it
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
                break   # no point continuing - the same failure reason would apply to every role

    # ─────────────────────────────────────────────
    # 2) guard against accumulation - if a removal failed, do not add a new role
    # ─────────────────────────────────────────────
    if removal_failed:
        names = ", ".join(f"`{n}`" for n in removal_failed)
        logger.error(
            f"🛑 SKIP add-role {member.display_name} (RANK #{rank}):"
            f"{names} — Rank Role"
        )
        bot_position = guild.me.top_role.position if guild.me else 0
        if permanent_error:
            await notify_admins(
                guild,
                f"🛑 Cannot remove rank role (RANK #{rank})",
                f"> 👤 **Player:** {member.mention} (`{member.id}`)\n"
                f"> 🏷 **Role:** `{permanent_error}`\n"
                f"> ⚠️  **Reason:**  Bot cannot remove this role — "
                f"the role is **higher** than bot role in hierarchy\n"
                f"> 📊  **Bot role:**  `{guild.me.top_role.name}`  (position `{bot_position}`)\n"
                f"> 🔧 **Fix:** remove the `{permanent_error}` role manually "
                f"or move bot role above it in `Server Settings → Roles`\n"
                f"> 🚫  **Temporarily:**  Did not add new rank role to avoid accumulation\n"
                f"> 📋 **Logs:** `{PREFIX}botinfo` Railway logs",
                color=COLORS["error"]
            )
        return  # do not add any new role - this is the root fix

    # ─────────────────────────────────────────────
    # 3) give the player the appropriate role if they qualify
    # ─────────────────────────────────────────────
    if target_tier:
        target_role_name = RANK_TITLES[target_tier]["name"]
        # check whether they already have it
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
                        f"🛑 Cannot grant rank role (RANK #{rank})",
                        f"> 👤 **Player:** {member.mention} (`{member.id}`)\n"
                        f"> 🏷  **Role:**  `{target_role_name}`\n"
                        f"> ⚠️  **Reason:**  Bot cannot grant this role — "
                        f"the role is **higher** than bot role in hierarchy\n"
                        f"> 📊  **Bot role:**  `{guild.me.top_role.name}`  (position `{bot_position}`)\n"
                        f"> 🔧  **Fix:**  Move bot role above `{target_role_name}` in `Server Settings → Roles`",
                        color=COLORS["error"]
                    )

async def sync_all_players_roles(guild, player_ids=None):
    """🆕 Syncs player roles in server based on current ranking.
recalculate_ranks().

⚡ : player_ids —
( ) ."""
    try:
        # fetch all players, ranked
        players = db.get_leaderboard(guild.id, limit=None)  # all players
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
                await asyncio.sleep(0.1)  # avoid rate limit
    except Exception as e:
        logger.exception(f"sync_all_players_roles failed: {e}")

async def sync_all_nicknames(guild):
    """🆕 fixrank + syncnicknames :
( )."""
    updated = 0
    title = "🔄 Nickname Sync"
    try:
        members = [m for m in guild.members if not m.bot]
        for member in members:
            try:
                player = db.get_or_create_player(member.id, guild.id, member.display_name)
                await update_member_nickname(member, player.get("level", STARTING_LEVEL))
                updated += 1
                await asyncio.sleep(0.05)  # avoid rate limit (fix for large member lists)
            except Exception as e:
                logger.debug(f"sync_all_nicknames skip {member.id}: {e}")
        if updated:
            logger.info(f"{title} ({guild.name}): checked {len(members)} members")
    except Exception as e:
        logger.warning(f"{title} failed for {guild.name}: {e}")

async def setup_rank_roles_permissions(guild):
    """🆕 roles Waiting Prv SoundBoard.
!!setup."""
    # create the roles
    for tier, data in RANK_TITLES.items():
        await create_role_if_not_exists(guild, data["name"], data["color"])

    # update Waiting Prv permissions - grant Best Player + Goated the Connect permission
    for role in guild.roles:
        if role.name in [RANK_TITLES[1]["name"], RANK_TITLES[2]["name"]]:
            # fetch all Waiting Prv rooms
            for ch in guild.voice_channels:
                if WAITING_PRV_CATEGORY_HINT.lower() in ch.name.lower():
                    try:
                        # grant the role Connect permission
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
    """🔒 Prevents player input from creating Discord mentions.

: DB
`notify_admins()` / `!!reports` — `<@&id>` `@everyone`
mass-ping role 1024
embed HTTPException 400.

✅FIX: mention zero-width space `‎@`
( mention)."""
    if not text:
        return None
    cleaned = str(text)
    zws = "\u200b"  # zero-width space
    # <@123> / <@!123> / <@&123>  ->  <@ZWS 123>  (no longer triggers a mention)
    cleaned = re.sub(r"<([@!&#]+)(\d+)>", lambda m: f"<{m.group(1)}{zws}{m.group(2)}>", cleaned)
    # @everyone / @here  ->  @ZWS everyone  (no longer triggers a mention)
    cleaned = re.sub(
        r"@(everyone|here)\b",
        lambda m: f"@{zws}{m.group(1)}",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = " ".join(cleaned.split()).strip()
    return cleaned[:max_length] or None

async def notify_admins(guild, title, description, color=None):
    """🆕 roles 🔇 Blacklisted.
( match-results — ).
✅ : + Administrator / Manage Guild + role ."""
    try:
        if color is None:
            color = COLORS["error"]
        
        # fix: collect all relevant roles for the tag
        admin_mentions = []
        
        # 1) look up the admin role by name
        admin_role = None
        for role in guild.roles:
            if role.name.lower() == ADMIN_ROLE_NAME.lower():
                admin_role = role
                break
        
        # 2) find all roles with Administrator or Manage Guild
        high_roles = []
        for role in guild.roles:
            if role == guild.default_role or role.is_bot_managed() or role.is_integration():
                continue
            if role.permissions.administrator or role.permissions.manage_guild:
                high_roles.append(role)
        
        # 3) find the highest role in the server (the owner and those below it)
        if guild.roles:
            # sort roles from highest to lowest
            sorted_roles = sorted([r for r in guild.roles if r != guild.default_role and not r.is_bot_managed() and not r.is_integration()], key=lambda r: r.position, reverse=True)
            # take the top 3 roles (the owner and those below)
            for role in sorted_roles[:3]:
                if role not in high_roles:
                    high_roles.append(role)
        
        # 4) collect the mentions
        if admin_role and admin_role not in high_roles:
            high_roles.append(admin_role)
        
        for role in high_roles:
            admin_mentions.append(role.mention)
        
        # 5) add a mention for the owner as well
        if guild.owner:
            admin_mentions.append(guild.owner.mention)
        
        # remove duplicates
        admin_mentions = list(dict.fromkeys(admin_mentions))
        admin_mention_str = " ".join(admin_mentions) if admin_mentions else "@here"
        
        # alerts are sent to the blacklist channel (request: match-results channel = results only)
        channel = _resolve_blacklist_channel(guild)
        # fallback 1: any play channel
        if not channel:
            play_channels = db.get_play_channels(guild.id)
            if play_channels:
                channel = guild.get_channel(play_channels[0])
        # fallback 2: first text channel the bot can write to
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
    "report_channel_ids",  # list of investigation voice channels selected by an admin (JSON array)
    "blacklist_channel_id",   # channel that displays blacklisted players
    "blacklist_message_id",    # message holding the list in that channel
    # P1: speeds up setup_jail_system and setup_blacklist_role by storing a "setup done" flag
    "jail_setup_done",         # 1 if role + category + channels are created, 0/NULL otherwise
    "blacklist_setup_done",    # 1 if Done Creating role black list
}

# ============================================================
# DATABASE
# ============================================================
class Database:
    def __init__(self, db_path=None):
        # support the DB_PATH environment variable to set the database path
        # fix: use a fixed path next to the bot file (not the current working directory)
        # this prevents data loss when the bot is started from a different directory
        if db_path:
            self.db_path = db_path
        elif os.getenv("DB_PATH"):
            self.db_path = os.getenv("DB_PATH")
        else:
            # use a fixed path next to the bot file
            bot_dir = os.path.dirname(os.path.abspath(__file__))
            self.db_path = os.path.join(bot_dir, "freefire_bot.db")
        
        # Railway/Render fix: create the directory if it does not exist
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            try:
                os.makedirs(db_dir, exist_ok=True)
                logger.info(f"📁 Created database directory: {db_dir}")
            except Exception as e:
                logger.warning(f"⚠️ Could not create directory {db_dir}: {e}")
                # fallback: use the current directory
                self.db_path = os.path.join(os.getcwd(), "freefire_bot.db")
                logger.info(f"💾 Falling back to: {self.db_path}")
        
        # fix: if the DB does not exist, look for an old DB in common locations
        if not os.path.exists(self.db_path):
            # look in the current directory
            cwd_db = os.path.join(os.getcwd(), "freefire_bot.db")
            if os.path.exists(cwd_db):
                self.db_path = cwd_db
                logger.info(f"💾 Found existing DB in current directory: {self.db_path}")
            else:
                # look in common directories
                for search_path in [
                    os.path.join(os.path.expanduser("~"), "freefire_bot.db"),
                    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "freefire_bot.db"),
                ]:
                    if os.path.exists(search_path):
                        self.db_path = os.path.abspath(search_path)
                        logger.info(f"💾 Found existing DB: {self.db_path}")
                        break
        
        logger.info(f"💾 Database path: {self.db_path}")
        # performance improvements for multi-server setups
        self._local = threading.local()
        # cache for channel queries (greatly reduces DB queries)
        self._channels_cache = {}
        self._init_db()
        self._create_tables()
        self._migrate()
        
        # fix: remember the player count to detect data loss
        try:
            conn = sqlite3.connect(self.db_path, timeout=30.0)
            count = conn.execute("SELECT COUNT(*) FROM players").fetchone()[0]
            conn.close()
            logger.info(f"💾 Database has {count} players — data preserved!")
        except:
            pass

    def _init_db(self):
        """🆕 WAL mode ."""
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
        """🆕 thread-local connection .
✅ : ."""
        try:
            if hasattr(self._local, 'conn') and self._local.conn is not None:
                # check that the connection is still open
                self._local.conn.execute("SELECT 1").fetchone()
                return self._local.conn
        except sqlite3.Error:
            # connection closed or broken - reopen it
            try:
                if hasattr(self._local, 'conn') and self._local.conn is not None:
                    self._local.conn.close()
            except Exception:
                pass
            self._local.conn = None
        # open a new connection
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
                    matches_hosted INTEGER DEFAULT 0,
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
                ("players", "matches_hosted", "INTEGER DEFAULT 0"),
                ("players", "original_nickname", "TEXT DEFAULT NULL"),
                ("lobbies", "private_key", "TEXT DEFAULT NULL"),
                ("lobbies", "first_joiner_id", "INTEGER DEFAULT NULL"),
                # 🆕 FIX: store the StartVote button message_id so the
                # persistent StartVoteView can recover lobby_id after restart.
                ("lobbies", "start_vote_message_id", "INTEGER DEFAULT NULL"),
                # 🆕 FIX: store the assigned investigation voice for each banned player
                ("banned_players", "assigned_voice_id", "INTEGER DEFAULT NULL"),
                # blacklist display channel
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
        # ✅ P1: sync guild settings to cloud (for persistence across deploys)
        if _CLOUD_AVAILABLE and is_cloud_enabled():
            try:
                settings = self.get_guild_settings(gid) or {}
                settings["guild_id"] = gid
                sync_guild_settings_to_cloud(gid, settings)
            except Exception as e:
                logger.warning(f"☁️ Failed to sync guild setting {key}: {e}")

    def add_play_channel(self, gid, cid):
        conn = self.conn()
        try:
            conn.execute("INSERT INTO play_channels(guild_id,channel_id) VALUES(?,?)", (gid, cid))
            conn.commit()
            # FIX (MEDIUM): get_play_channels caches under `play_ch_{gid}`,
            # and no add/remove cleared it, so the cache stayed stale until restart
            # (affects RematchView and notify_admins, which pick play_channels[0]).
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
            # FIX (MEDIUM): same reason - clear the play channel cache
            self._channels_cache.pop(f"play_ch_{gid}", None)
            return cur.rowcount > 0
        finally:
            pass  # thread-local connection

    def get_play_channels(self, gid):
        # cache for better performance
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
            # clear the cache after the update
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
            # clear the cache after the update
            self._channels_cache.pop(f"cmd_ch_{gid}", None)
            return cur.rowcount > 0
        finally:
            pass  # thread-local connection

    def get_commands_channels(self, gid):
        # cache for better performance
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
                # every new player starts at RANK 1000 with 0 points
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
        ALLOWED = {"points","rank_pos","wins","losses","kills","mvps","matches_played","matches_hosted","level","username","original_nickname","win_streak","lose_streak","max_win_streak"}
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

    def reset_stats(self, uid, gid):
        conn = self.conn()
        try:
            conn.execute("UPDATE players SET points=0,wins=0,losses=0,kills=0,mvps=0,matches_played=0,rank_pos=1,level=?,win_streak=0,lose_streak=0,max_win_streak=0,last_active=? WHERE user_id=? AND guild_id=?", (STARTING_LEVEL, datetime.now().isoformat(), uid, gid))
            conn.commit()
        finally:
            pass  # thread-local connection

    def get_leaderboard(self, gid, limit=10):
        """🆕 Returns all players sorted by unified ranking (compatible with recalculate_ranks). limit=None returns all players.
✅ V5: recalculate_ranks"""
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

    def create_lobby(self, gid, creator, chan, mode="4v4"):
        conn = self.conn()
        try:
            cur = conn.execute("INSERT INTO lobbies(guild_id,creator_id,channel_id,game_mode,team1_players) VALUES(?,?,?,?,?)", (gid, creator, chan, mode, json.dumps([creator])))
            # ✅ FIX: increment matches_hosted counter for the creator
            conn.execute("UPDATE players SET matches_hosted = matches_hosted + 1 WHERE user_id=? AND guild_id=?", (creator, gid))
            conn.commit()
            return cur.lastrowid
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
        """🆕 (status=started) ."""
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
        """🆕 Adds/subtracts points.
leaderboard (1 = ).
skip_recalculate=True recalculate_ranks ( )."""
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
        """Updates points and stats in a single query, returns updated player data.
✅ : recalculate_ranks ( ).
✅ V5: add_kills kills."""
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
        # fix: call recalculate_ranks before returning the data
        if not skip_recalculate:
            self.recalculate_ranks(gid)
        # fix: read the data after recalculate_ranks (not before)
        conn = self.conn()
        r = conn.execute("SELECT * FROM players WHERE user_id=? AND guild_id=?", (uid, gid)).fetchone()
        result = dict(r) if r else None
        return result

    def get_top_points(self, gid):
        """ ( #1)."""
        conn = self.conn()
        try:
            r = conn.execute("SELECT points FROM players WHERE guild_id=? ORDER BY points DESC LIMIT 1", (gid,)).fetchone()
            return r["points"] if r else 0
        finally:
            pass

    def recalculate_ranks(self, gid):
        """V5: Recalculates rank for all players.
- > 0 → (1, 2, 3...)
- = 0 → 1000 ( — )
- < 0 → 1001, 1002... ( )
✅ V5: user_id ASC
✅ V5: rank_pos ( )"""
        # the single canonical ordering, used everywhere (recalculate_ranks, get_leaderboard, get_player_rank_position)
        # user_id ASC gives a deterministic result when all previous criteria tie
        TIEBREAK_ORDER = "points DESC, kills DESC, mvps DESC, wins DESC, losses ASC, matches_played ASC, user_id ASC"

        conn = self.conn()
        try:
            # 1) players with positive points -> ranks 1, 2, 3...
            active = conn.execute(f"""
                SELECT user_id,
                       ROW_NUMBER() OVER (ORDER BY {TIEBREAK_ORDER}) as rank_pos
                FROM players
                WHERE guild_id=? AND points > 0
            """, (gid,)).fetchall()
            updates = [(p["rank_pos"], p["rank_pos"], p["user_id"]) for p in active]

            # 2) players with zero points -> fixed rank 1000 (new or reset players)
            zero_pts = conn.execute("""
                SELECT user_id FROM players
                WHERE guild_id=? AND points = 0
            """, (gid,)).fetchall()
            for p in zero_pts:
                updates.append((STARTING_LEVEL, 0, p["user_id"]))

            # 3) players with negative points -> ranks 1001, 1002... (penalty)
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
        
        # cloud sync after every recalculate_ranks
        if _CLOUD_AVAILABLE and is_cloud_enabled():
            try:
                players = self.get_leaderboard(gid, limit=None)
                if players:
                    sync_guild_players_to_cloud(gid, players)
            except Exception as e:
                logger.warning(f"☁️ Cloud sync failed in recalculate_ranks: {e}")

    def get_player_rank_position(self, uid, gid):
        """V5: Returns player rank (fully compatible with recalculate_ranks).
- > 0 → (1, 2, 3...)
- = 0 → 1000
- < 0 → 1001+
✅ V5: recalculate_ranks:
points DESC, kills DESC, mvps DESC, wins DESC, losses ASC, matches_played ASC, user_id ASC"""
        conn = self.conn()
        try:
            player = conn.execute(
                "SELECT points, kills, mvps, wins, losses, matches_played FROM players WHERE user_id=? AND guild_id=?",
                (uid, gid)
            ).fetchone()
            if not player:
                return None
            # zero points -> default rank
            if player["points"] == 0:
                return STARTING_LEVEL

            # V5: unified tiebreak criteria (identical to recalculate_ranks)
            # points DESC -> points > ? (higher points first)
            # kills DESC -> kills > ? (more kills first)
            # mvps DESC -> mvps > ? (more MVPs first)
            # wins DESC -> wins > ? (more wins first)
            # losses ASC -> losses < ? (fewer losses first)
            # matches_played ASC -> matches_played < ? (fewer matches first)
            # user_id ASC -> user_id < ? (lower ID first - deterministic)
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

            # negative points -> 1001 + position among the negatives
            if p["points"] < 0:
                higher_neg = conn.execute(
                    f"SELECT COUNT(*) FROM players WHERE guild_id=? AND points < 0 AND {tiebreak_sql}",
                    (gid,) + tiebreak_params
                ).fetchone()[0]
                return STARTING_LEVEL + higher_neg + 1

            # positive points -> count the players above
            higher = conn.execute(
                f"SELECT COUNT(*) FROM players WHERE guild_id=? AND points > 0 AND {tiebreak_sql}",
                (gid,) + tiebreak_params
            ).fetchone()[0]
            return higher + 1
        finally:
            pass  # thread-local connection

    # ============================================================
    # 🆕 REPORTS & BANS — Reports & Bans System
    # ============================================================
    def add_report(self, gid, reporter_id, reported_id, lobby_id=None, reason=None):
        """Logs a report. Returns (True, total_count) on success, (False, total_count) if duplicate.
        ✅ P1: sync reports to cloud after each successful report."""
        conn = self.conn()
        added = False
        total = 0
        try:
            try:
                conn.execute(
                    "INSERT INTO player_reports(guild_id, reporter_id, reported_id, lobby_id, reason) VALUES(?,?,?,?,?)",
                    (gid, reporter_id, reported_id, lobby_id, reason)
                )
                conn.commit()
                added = True
            except sqlite3.IntegrityError:
                added = False  # already reported by the same player
            total = conn.execute(
                "SELECT COUNT(*) FROM player_reports WHERE guild_id=? AND reported_id=?",
                (gid, reported_id)
            ).fetchone()[0]
        finally:
            pass  # thread-local connection
        # ✅ P1: sync reports to cloud (best-effort, after DB write)
        if added and _CLOUD_AVAILABLE and is_cloud_enabled():
            try:
                all_reports = conn.execute(
                    "SELECT * FROM player_reports WHERE guild_id=?",
                    (gid,)
                ).fetchall()
                reports_list = [dict(r) for r in all_reports]
                sync_reports_to_cloud(gid, reports_list)
            except Exception as e:
                logger.warning(f"☁️ Failed to sync reports (after add): {e}")
        return added, total

    def get_reports_count(self, gid, reported_id):
        """Returns report count for a player."""
        conn = self.conn()
        try:
            return conn.execute(
                "SELECT COUNT(*) FROM player_reports WHERE guild_id=? AND reported_id=?",
                (gid, reported_id)
            ).fetchone()[0]
        finally:
            pass  # thread-local connection

    def get_reports_for_player(self, gid, reported_id):
        """Returns report list for a player."""
        conn = self.conn()
        try:
            return [dict(x) for x in conn.execute(
                "SELECT * FROM player_reports WHERE guild_id=? AND reported_id=? ORDER BY created_at DESC",
                (gid, reported_id)
            ).fetchall()]
        finally:
            pass  # thread-local connection

    def clear_reports(self, gid, reported_id):
        """Deletes all reports on a player (e.g., after unban).
        ✅ P1: sync reports to cloud after clearing."""
        conn = self.conn()
        try:
            conn.execute(
                "DELETE FROM player_reports WHERE guild_id=? AND reported_id=?",
                (gid, reported_id)
            )
            conn.commit()
        finally:
            pass  # thread-local connection
        # ✅ P1: sync reports to cloud
        if _CLOUD_AVAILABLE and is_cloud_enabled():
            try:
                all_reports = conn.execute(
                    "SELECT * FROM player_reports WHERE guild_id=?",
                    (gid,)
                ).fetchall()
                reports_list = [dict(r) for r in all_reports]
                sync_reports_to_cloud(gid, reports_list)
            except Exception as e:
                logger.warning(f"☁️ Failed to sync reports (after clear): {e}")

    def ban_player(self, gid, user_id, reason=None, banned_by=None, report_count=0, assigned_voice_id=None):
        """Bans player from using bot + sets custom investigation voice.
        ✅ P1: sync bans to cloud after each ban."""
        conn = self.conn()
        try:
            # keep the assigned_voice_id if it exists, otherwise keep the old one
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
        # ✅ P1: sync bans to cloud
        if _CLOUD_AVAILABLE and is_cloud_enabled():
            try:
                bans = self.get_banned_players(gid)
                sync_bans_to_cloud(gid, bans)
            except Exception as e:
                logger.warning(f"☁️ Failed to sync bans (after ban): {e}")

    def set_banned_voice(self, gid, user_id, voice_id):
        """🆕 ."""
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
        """Unbans player.
        ✅ P1: sync bans to cloud after unban."""
        conn = self.conn()
        try:
            conn.execute(
                "DELETE FROM banned_players WHERE guild_id=? AND user_id=?",
                (gid, user_id)
            )
            conn.commit()
        finally:
            pass  # thread-local connection
        # ✅ P1: sync bans to cloud
        if _CLOUD_AVAILABLE and is_cloud_enabled():
            try:
                bans = self.get_banned_players(gid)
                sync_bans_to_cloud(gid, bans)
            except Exception as e:
                logger.warning(f"☁️ Failed to sync bans (after unban): {e}")

    def is_player_banned(self, gid, user_id):
        """Returns True if player is banned + ban info (including assigned_voice_id)."""
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
        """ ."""
        conn = self.conn()
        try:
            return [dict(x) for x in conn.execute(
                "SELECT * FROM banned_players WHERE guild_id=? ORDER BY banned_at DESC",
                (gid,)
            ).fetchall()]
        finally:
            pass  # thread-local connection

    # ============================================================
    # REPORT CHANNELS - investigation voice channels selected by an admin
    # ============================================================
    def get_report_channels(self, gid):
        """ ."""
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
        """ ."""
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
        """ ."""
        channels = self.get_report_channels(gid)
        if channel_id not in channels:
            channels.append(channel_id)
            self.set_report_channels(gid, channels)
            return True
        return False

    def remove_report_channel(self, gid, channel_id):
        """ ."""
        channels = self.get_report_channels(gid)
        if channel_id in channels:
            channels.remove(channel_id)
            self.set_report_channels(gid, channels)
            return True
        return False

    # ============================================================
    # 🆕 BLACKLIST SYSTEM — Blacklist System
    # ============================================================
    def is_player_blacklisted(self, gid, user_id):
        """Returns True if player is blacklisted (duration not expired).
✅ P1: time.time() datetime.now() — timezone-independent."""
        conn = self.conn()
        try:
            r = conn.execute(
                "SELECT expires_at FROM blacklist_log WHERE guild_id=? AND user_id=?",
                (gid, user_id)
            ).fetchone()
            if r:
                # expires_at is stored as ISO from datetime.fromtimestamp(expires).isoformat()
                # compare with now() in the same local timezone
                try:
                    expires = datetime.fromisoformat(r["expires_at"])
                    if datetime.now() < expires:
                        return True
                except (ValueError, TypeError):
                    pass
                # duration expired - delete the record
                conn.execute(
                    "DELETE FROM blacklist_log WHERE guild_id=? AND user_id=?",
                    (gid, user_id)
                )
                conn.commit()
            return False
        finally:
            pass

    def blacklist_player(self, gid, user_id, reason=None):
        """Adds player to blacklist for BLACKLIST_DURATION seconds.
✅ P1: time.time() expires — timezone-independent.
✅ P1: sync blacklist to cloud after each addition."""
        expires_unix = time.time() + BLACKLIST_DURATION
        expires_iso = datetime.fromtimestamp(expires_unix).isoformat()
        conn = self.conn()
        try:
            conn.execute(
                "INSERT OR REPLACE INTO blacklist_log(guild_id, user_id, expires_at, reason) VALUES(?,?,?,?)",
                (gid, user_id, expires_iso, reason)
            )
            conn.commit()
            return expires_unix
        finally:
            pass
        # ✅ P1: sync blacklist to cloud (best-effort, after DB write)
        if _CLOUD_AVAILABLE and is_cloud_enabled():
            try:
                blacklisted = self.get_blacklisted_players(gid)
                sync_blacklist_to_cloud(gid, blacklisted)
            except Exception as e:
                logger.warning(f"☁️ Failed to sync blacklist (after add): {e}")

    def remove_blacklist(self, gid, user_id):
        """Removes player from blacklist.
        ✅ P1: sync blacklist to cloud after removal."""
        conn = self.conn()
        try:
            conn.execute(
                "DELETE FROM blacklist_log WHERE guild_id=? AND user_id=?",
                (gid, user_id)
            )
            conn.commit()
        finally:
            pass
        # ✅ P1: sync blacklist to cloud
        if _CLOUD_AVAILABLE and is_cloud_enabled():
            try:
                blacklisted = self.get_blacklisted_players(gid)
                sync_blacklist_to_cloud(gid, blacklisted)
            except Exception as e:
                logger.warning(f"☁️ Failed to sync blacklist (after remove): {e}")

    def get_blacklisted_players(self, gid):
        """Returns all blacklisted players (whose duration hasn't expired)."""
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

# Cloud Restore - restore data from the cloud at startup
if _CLOUD_AVAILABLE and is_cloud_enabled():
    logger.info("☁️ Cloud backup enabled — checking for data to restore...")
    auto_restore_database(db)
else:
    logger.info("☁️ Cloud backup not configured — using local database only")

active_lobby_messages = {}
lobby_timeout_timers = {}
vote_timeout_timers = {}
_admin_mvp_results = {}  # lobby_id -> {"winner": user_id, "loser": user_id} for the !!w / !!l commands
_lobby_embed_hide_timers = {}  # timers that automatically hide the lobby message after 2 minutes (not enough players)

# "Create Lobby" prompt messages - auto-deleted
# _create_prompt_msgs : {prompt_message_id: {"guild_id", "channel_id", "user_id"}}
# _create_prompt_timers : {prompt_message_id: asyncio.Task}  - one-minute timer
# _lobby_prompt_msg : {lobby_id: prompt_message_id}  - links the prompt to the lobby (waiting for the end of the match)
_create_prompt_msgs = {}
_create_prompt_timers = {}
_lobby_prompt_msg = {}

# stores each player's original voice channel - {lobby_id: {user_id: original_voice_channel_id}}
# used to return players to the same waiting room after a match ends or is cancelled
_original_voice_channels = {}

# 🆕 BLACKLIST: Voice tracking — {guild_id: {user_id: {...}}}
_blacklist_voice_tracking = {}
# BLACKLIST: set of channel IDs of active matches (fast lookup)
_active_match_voice_channels = set()
# BLACKLIST: auto-removal timers - {guild_id: {user_id: timer_task}}
_blacklist_auto_remove_timers = {}
# lock for blacklist channel creation per server - prevents duplicate channels under concurrent execution
_blacklist_channel_locks = {}
# play-flow messages in the play channel - {lobby_id: set((channel_id, message_id))}
# all are deleted automatically when the match ends, however it ends (including "Match Ready")
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
    """✦ Lobby Embed — V2 design matching reference video."""
    mode = lobby.get("game_mode", DEFAULT_MODE)
    mode_info = GAME_MODES.get(mode, GAME_MODES[DEFAULT_MODE])
    team_size = mode_info["team_size"]
    lobby_size = mode_info["lobby_size"]

    t1c = len(lobby["team1_players"])
    t2c = len(lobby["team2_players"])
    total = t1c + t2c
    progress_pct = int((total / lobby_size) * 100) if lobby_size else 0
    progress_bar = make_progress_bar(total, lobby_size, length=12)

    # Player cards (clean style)
    def make_team_card(players, team_emoji, team_size_limit):
        if not players:
            slots = [f"⚫ *empty slot*" for _ in range(team_size_limit)]
            return "\n".join(slots)
        lines = [f"<@{pid}>" for pid in players[:team_size_limit]]
        empty = team_size_limit - len(lines)
        for _ in range(empty):
            lines.append(f"⚫ *empty slot*")
        return "\n".join(lines)

    t1_text = make_team_card(lobby["team1_players"], "🔴", team_size)
    t2_text = make_team_card(lobby["team2_players"], "🟢", team_size)

    # Lobby status
    if total == 0:
        status_text = "⏳ Waiting for players..."
    elif total < lobby_size:
        status_text = f"⏳ Needs **{lobby_size - total} more players** to start"
    else:
        status_text = "🎮 Match ready to start!"

    # Build embed — V2 matching reference video
    host_member = guild.get_member(lobby['creator_id'])
    host_name = host_member.display_name if host_member else 'Unknown'

    embed = discord.Embed(
        title=f"🎮 Free Fire {mode.upper()} Match",
        description=(
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"| Match started by <@{lobby['creator_id']}>\n"
            f"\n"
            f"🔴 **Team 1 ({t1c}/{team_size})**\n"
            f"{t1_text}\n"
            f"\n"
            f"🟢 **Team 2 ({t2c}/{team_size})**\n"
            f"{t2_text}\n"
            f"\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📋 **Status:** {status_text}"
        ),
        color=COLORS["play"],
        timestamp=discord.utils.utcnow()
    )

    # Room private info
    pk = db.get_lobby_private_key(lobby['id'])
    room_id = lobby.get('room_id')
    if pk and not room_id:
        embed.add_field(
            name="🔐 Private Match",
            value=f"Protected with a private key — ask <@{lobby['creator_id']}> for the key to join.",
            inline=False
        )

    embed.set_author(
        name=f"Host: {host_name}",
        icon_url=host_member.display_avatar.url if host_member else None
    )
    embed.set_footer(text=f"{BOT_FOOTER}  •  Lobby #{lobby['id']}")
    embed = apply_branding(embed, guild)

    return embed

def create_profile_embed(player, member=None, gid=None):
    """✦ Profile Embed — V2 design matching reference video (2x4 stats grid)."""
    level = player.get("level", STARTING_LEVEL)
    rank_color = get_rank_color(level)
    rank_title = get_rank_title(level)
    points = player.get("points", 0)
    mvps = player.get("mvps", 0)

    mvp_badge = get_mvp_badge(mvps)
    mvp_title = get_mvp_title(mvps)

    wr = round((player["wins"] / max(player["matches_played"], 1)) * 100, 1)
    win_streak = player.get("win_streak", 0)
    lose_streak = player.get("lose_streak", 0)
    max_streak = player.get("max_win_streak", 0)

    top_pts = db.get_top_points(gid) if gid else 0
    pts_to_next = max(0, top_pts - points) if top_pts > points else 0
    progress_pct = int((points / max(top_pts, 1)) * 100) if top_pts else 0
    progress_pct = max(0, min(100, progress_pct))
    rank_progress_bar = make_progress_bar(points, max(top_pts, 1), length=15)

    name = member.display_name if member else player["username"]
    avatar_url = member.display_avatar.url if member else None

    # Streak line
    if win_streak > 0:
        streak_display = f"> 🔥 Win streak: `{win_streak}` (best: `{max_streak}`)"
    elif lose_streak > 0:
        streak_display = f"> ☠️ Lose streak: `{lose_streak}` (best: `{max_streak}`)"
    else:
        streak_display = f"> 📊 Best streak: `{max_streak}`"

    # Title with badge
    display_title = f"👑 {name}"
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

    # ✅ V2: 2×4 stats grid (8 metrics) — matching reference video
    # Row 1: POINTS (large), WINS, LOSSES, MVPS
    embed.add_field(name="💰 POINTS",  value=f"`{points:,}`",  inline=True)
    embed.add_field(name="🏆 WINS",    value=f"`{player['wins']}`",  inline=True)
    embed.add_field(name="☠️ LOSSES",  value=f"`{player['losses']}`", inline=True)
    embed.add_field(name="🔱 MVPS",   value=f"`{mvps}`",  inline=True)

    # Row 2: MATCHES, HOSTED, WINRATE, RANK
    hosted = player.get("matches_hosted", 0)  # if not tracked, will be 0
    embed.add_field(name="🎮 MATCHES", value=f"`{player['matches_played']}`", inline=True)
    embed.add_field(name="📋 HOSTED",  value=f"`{hosted}`",  inline=True)
    embed.add_field(name="📊 WINRATE", value=f"`{wr}%`",  inline=True)
    embed.add_field(name="🏅 RANK",    value=f"`#{level}`", inline=True)

    # Win rate status
    wr_status = "🔥 God Tier" if wr >= 70 else ("⭐ Pro" if wr >= 50 else ("🌱 Rising" if wr >= 30 else "☠️ Struggling"))
    embed.add_field(
        name=f"📊 Win Rate — `{wr}%` {wr_status}",
        value=f"{streak_display}",
        inline=False
    )

    # V1: progress toward #1 / the leader
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

    # MVP achievement
    if mvps > 0:
        badge_display = ""
        if mvps >= 100:   badge_display = "🔱 LEGEND"
        elif mvps >= 50:  badge_display = "💎 DIAMOND"
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
    embed.set_author(name="Player Profile", icon_url=avatar_url)
    if avatar_url:
        embed.set_thumbnail(url=avatar_url)  # ✅ bigger, more prominent player avatar

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
    """◆ Leaderboard — V0 Redesign. + ."""
    try:
        settings = db.get_guild_settings(guild.id)
        if not settings or not settings.get("leaderboard_channel_id"):
            return
        channel = guild.get_channel(settings["leaderboard_channel_id"])
        if not channel:
            return
        # hide blacklisted players from the leaderboard (instead of showing them)
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
                # V0: thin separator between players
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
    """🔇"🔇 Blacklisted" .
apply/remove blacklist setup.
⚡ TEXT."""
    try:
        settings = db.get_guild_settings(guild.id)
        if not settings:
            return
        # per-server lock: prevents two concurrent channel creations (race) when commands run simultaneously
        lock = _blacklist_channel_locks.setdefault(guild.id, asyncio.Lock())
        async with lock:
            # remove duplicates (exact or nested names containing the blacklist keyword - covers manually created channels)
            def _looks_like_blacklist_channel(ch):
                lower = (ch.name or "").lower()
                return ch.name == BLACKLIST_CHANNEL_NAME or "blacklist" in lower

            candidates = [c for c in guild.text_channels if _looks_like_blacklist_channel(c)]
            exact = [c for c in candidates if c.name == BLACKLIST_CHANNEL_NAME]

            channel = None
            if settings.get("blacklist_channel_id"):
                ref = guild.get_channel(settings["blacklist_channel_id"])
                # use the reference channel only if it is actually a blacklist channel (do not wipe a valid reference to another channel)
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

            # pin the actual blacklist channel after cleanup (last valid reference)
            if channel is not None:
                db.set_guild_setting(guild.id, "blacklist_channel_id", channel.id)
            if not channel:
                text_cat = discord.utils.get(guild.categories, name="🎮 Free Fire Text")
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
            description=f"📊 **Total:** `{len(blacklisted)}`",
            color=COLORS["warning"] if blacklisted else COLORS["success"],
            timestamp=discord.utils.utcnow()
        )
        embed.set_author(name="Blacklist")
        if not blacklisted:
            embed.description = "> ✅"
        else:
            for i, b in enumerate(blacklisted[:15], 1):
                member = guild.get_member(b["user_id"])
                name = member.display_name if member else f"User#{b['user_id']}"
                mention = member.mention if member else f"<@{b['user_id']}>"
                reason = b.get("reason") or ""
                expires = b.get("expires_at", "N/A")[:19] if b.get("expires_at") else "N/A"
                embed.add_field(
                    name=f"#{i} — {name}",
                    value=f"👤 {mention}\n📝 `{reason}`\n⏱️ Expires: `{expires}`",
                    inline=False
                )
            if len(blacklisted) > 15:
                embed.set_footer(text=f"{BOT_FOOTER} • +{len(blacklisted) - 15} more")
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
    """🆕 ( )."""
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
    """🆕 (match-results / match result / ) .
— ."""
    try:
        for ch in guild.text_channels:
            name = (ch.name or "").lower().replace("_", " ").replace("-", " ").replace("・", " ")
            if "match result" in name or "" in name or "result" in name:
                return ch
        return None
    except Exception as e:
        logger.warning(f"find_match_results_channel failed in {getattr(guild, 'name', '?')}: {e}")
        return None

def _resolve_blacklist_channel(guild):
    """🆕 🔇 Blacklisted ( ) — None ."""
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
    """🆕 (match-results)
— ."""
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
    """🆕 Waits CREATE_PROMPT_DELETE_AFTER then deletes "Create Lobby" message
.
✅ → ."""
    prompt_id = msg.id
    try:
        await asyncio.sleep(CREATE_PROMPT_DELETE_AFTER)
    except asyncio.CancelledError:
        _create_prompt_timers.pop(prompt_id, None)
        return

    _create_prompt_timers.pop(prompt_id, None)

    # linked to a real lobby - keep it until the match ends
    if prompt_id in _lobby_prompt_msg.values():
        logger.info(
            f"⏱️ Create prompt {prompt_id}: room created — keeping until the match ends"
        )
        return

    _create_prompt_msgs.pop(prompt_id, None)
    await delete_message_safely(
        msg.channel, prompt_id,
        reason=f"{CREATE_PROMPT_DELETE_AFTER}"
    )
    logger.info(
        f"🧹 Auto-removed 'Create Lobby' message {prompt_id} — "
        f"no room created in {CREATE_PROMPT_DELETE_AFTER}s (user={user_id})"
    )

async def _delete_create_prompt_for_lobby(lobby_id, guild=None):
    """🆕"Create Lobby"( / / timeout)."""
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
    await delete_message_safely(ch, prompt_id, reason=f"#{lobby_id}")

async def _delete_lobby_embed_for_lobby(lobby_id, msg_ids=None, guild=None):
    """🆕 Deletes lobby message (embed with join buttons) when lobby ends.
cleanup_lobby_memory .
msg_ids: ( dict)."""
    if msg_ids is None:
        msg_ids = [k for k, v in active_lobby_messages.items() if v == lobby_id]
    lobby = db.get_lobby(lobby_id)
    if not lobby:
        return
    # if the message was not found in memory (e.g. an old lobby from before a restart)
    # -> use the message_id stored in the DB to guarantee deletion
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
        await delete_message_safely(ch, mid, reason=f"#{lobby_id}")

def register_lobby_flow_msg(lobby_id, channel_id, message_id):
    """🆕 (//Match Ready...)
."""
    if not lobby_id or not message_id:
        return
    _lobby_flow_msgs.setdefault(lobby_id, set()).add((channel_id, message_id))

async def _delete_lobby_flow_msgs(lobby_id):
    """🆕 ( )."""
    flow = _lobby_flow_msgs.pop(lobby_id, None)
    if not flow:
        return
    for ch_id, mid in list(flow):
        ch = bot.get_channel(ch_id)
        await delete_message_safely(ch, mid, reason=f"#{lobby_id} (flow)")

async def _auto_hide_idle_lobby_embed(lobby_id, guild):
    """🆕 After 2 minutes: if lobby is still waiting (not full) → delete its message
.
( )."""
    try:
        await asyncio.sleep(TEMP_EMBED_DELETE_AFTER)
        lobby = db.get_lobby(lobby_id)
        if not lobby or lobby["status"] != "waiting":
            _lobby_embed_hide_timers.pop(lobby_id, None)
            return
        # remove our timer first so cleanup_lobby_memory does not cancel this same task
        _lobby_embed_hide_timers.pop(lobby_id, None)
        # if the player count did not complete within 2 minutes -> close the lobby and delete the message
        db.update_lobby_status(lobby_id, "cancelled")
        cleanup_lobby_memory(lobby_id)
        ch = guild.get_channel(lobby["channel_id"])
        if ch:
            closed_embed = discord.Embed(
                title="⏰ Lobby Closed — Not Enough Players",
                description=(
                    f"Required player count not reached within **{TEMP_EMBED_DELETE_AFTER // 60} minutes**.\n"
                    f"💡 Use `{PREFIX}play 4v4` to open a new lobby."
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

    # delete the "Create Lobby" message linked to this lobby
    if lobby_id in _lobby_prompt_msg:
        try:
            asyncio.create_task(_delete_create_prompt_for_lobby(lobby_id))
        except RuntimeError:
            # no running event loop - clean up at least the memory
            pid = _lobby_prompt_msg.pop(lobby_id, None)
            if pid:
                _create_prompt_msgs.pop(pid, None)

    # delete the actual lobby message (the embed) when the lobby ends
    if to_remove:
        try:
            asyncio.create_task(_delete_lobby_embed_for_lobby(lobby_id, msg_ids=list(to_remove)))
        except RuntimeError:
            pass

    # delete all registered play-flow messages (Match Ready / any other messages in the play channel)
    if lobby_id in _lobby_flow_msgs:
        try:
            asyncio.create_task(_delete_lobby_flow_msgs(lobby_id))
        except RuntimeError:
            _lobby_flow_msgs.pop(lobby_id, None)

# ============================================================
# CHANNEL CREATION
# ============================================================

async def create_match_channels(guild, lobby, lobby_id):
    """ Category + + ."""
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

    t1_voice = await guild.create_voice_channel("🔴 Team 1", category=cat, overwrites=t1_overwrites)
    t2_voice = await guild.create_voice_channel("🟢 Team 2", category=cat, overwrites=t2_overwrites)
    general_text = await guild.create_text_channel("💬 Teams Chat", category=cat, overwrites=general_overwrites)

    db.save_match_channels(lobby_id, guild.id, cat.id, t1_voice.id, general_text.id, t2_voice.id, general_text.id)
    # register voices in the tracked blacklist set
    _active_match_voice_channels.add(t1_voice.id)
    _active_match_voice_channels.add(t2_voice.id)
    return {"category": cat, "team1_voice": t1_voice, "team1_text": general_text, "team2_voice": t2_voice, "team2_text": general_text, "general_text": general_text}

async def create_banned_voice_channels(guild):
    """🆕 Creates category + 3 voices for banned players (investigation).
db cache channel IDs guild_settings."""
    cat = discord.utils.get(guild.categories, name=REPORT_CATEGORY_NAME)
    if not cat:
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False, connect=False),
            guild.me: discord.PermissionOverwrite(view_channel=True, connect=True, manage_channels=True, move_members=True),
        }
        # admins can join
        for role in guild.roles:
            if role.permissions.administrator or role.permissions.manage_guild:
                overwrites[role] = discord.PermissionOverwrite(view_channel=True, connect=True, move_members=True)
        cat = await guild.create_category(REPORT_CATEGORY_NAME, overwrites=overwrites)
    # create the voices if they do not exist
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
    """🆕 Moves banned player to first available investigation voice.
: (db.get_report_channels)
fallback:
assign_permanent=True DB"""
    # if the player has a saved custom voice, use it first
    ban_info = db.is_player_banned(guild.id, member.id)
    if ban_info and ban_info.get("assigned_voice_id"):
        assigned_ch = guild.get_channel(ban_info["assigned_voice_id"])
        if assigned_ch and isinstance(assigned_ch, discord.VoiceChannel):
            try:
                await member.move_to(assigned_ch)
                return assigned_ch
            except (discord.HTTPException, discord.Forbidden):
                pass  # fall through to searching for a new voice

    # use the voices selected by an admin first
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
    # fallback: create voices automatically
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
    # save the custom voice for the player (if requested)
    if chosen_channel and assign_permanent:
        db.set_banned_voice(guild.id, member.id, chosen_channel.id)
    return chosen_channel

async def check_and_apply_auto_ban(guild, reported_id, total_reports, reported_by=None):
    """🆕 REPORT_THRESHOLD → + + .
True ."""
    if total_reports < REPORT_THRESHOLD:
        return False
    # ban the player
    db.ban_player(
        guild.id, reported_id,
        reason=f"Auto-ban: {total_reports} reports",
        banned_by=reported_by,
        report_count=total_reports
    )
    # move to the investigation voice + assign a permanent voice
    member = guild.get_member(reported_id)
    assigned_channel = None
    if member:
        # if the player is in a voice channel, move them
        if member.voice and member.voice.channel:
            assigned_channel = await move_to_banned_channels(guild, member, assign_permanent=True)
        else:
            # if not in a voice channel, assign one in advance (they will be moved when they join voice)
            admin_channel_ids = db.get_report_channels(guild.id)
            if admin_channel_ids:
                ch = guild.get_channel(admin_channel_ids[0])
                if ch and isinstance(ch, discord.VoiceChannel):
                    assigned_channel = ch
                    db.set_banned_voice(guild.id, reported_id, ch.id)
    # tag the admins
    voice_info = ""
    if assigned_channel:
        voice_info = f"\n> 🔍 **Investigation voice:** {assigned_channel.mention}\n> 🔒 **Assigned automatically**"
    await notify_admins(
        guild,
        "⚠️  Auto-Ban Triggered",
        f"> ⚠️  Player auto-banned after reaching `{REPORT_THRESHOLD}` reports\n"
        f"> 👤 **Player:** <@{reported_id}>\n"
        f"> 📊 **Total reports:** `{total_reports}`\n"
        f"> 🔍 **Action:** banned from playing{voice_info}\n"
        f"> 💡 Use  `!!unbanplayer @user`  to unban after investigation",
        color=COLORS["error"]
    )
    return True

async def delete_match_channels(guild, lobby_id):
    """Moves players to their original voice before deleting channels."""
    mc = db.get_match_channels(lobby_id)
    if not mc:
        # unless the player is in match channels, clear the original voice from memory
        _original_voice_channels.pop(lobby_id, None)
        return
    # find a valid waiting room (fallback if the original voice was deleted)
    fallback_vc = None
    for cid in db.get_waiting_rooms(guild.id):
        vc = guild.get_channel(cid)
        if vc and isinstance(vc, discord.VoiceChannel):
            fallback_vc = vc
            break
    # move all members from the match voices to their original voice
    original_channels = _original_voice_channels.get(lobby_id, {})
    for voice_key in ["team1_voice_id", "team2_voice_id"]:
        voice_id = mc.get(voice_key)
        if voice_id:
            ch = guild.get_channel(voice_id)
            if ch and isinstance(ch, discord.VoiceChannel):
                for member in ch.members:
                    # look up the player's original voice
                    target_vc = None
                    original_cid = original_channels.get(member.id)
                    if original_cid:
                        original_vc = guild.get_channel(original_cid)
                        if original_vc and isinstance(original_vc, discord.VoiceChannel):
                            target_vc = original_vc
                            logger.info(f"  🔄 Returning {member.display_name} → original: {original_vc.name}")
                    # fallback: use any valid waiting room
                    if not target_vc and fallback_vc:
                        target_vc = fallback_vc
                        logger.info(f"  🔄 Returning {member.display_name} → fallback: {fallback_vc.name}")
                    if target_vc:
                        try:
                            await member.move_to(target_vc)
                        except (discord.HTTPException, discord.Forbidden):
                            pass
    # clear the original voice from memory
    _original_voice_channels.pop(lobby_id, None)
    # clear voices from the blacklist set
    for voice_key in ["team1_voice_id", "team2_voice_id"]:
        voice_id = mc.get(voice_key)
        if voice_id:
            _active_match_voice_channels.discard(voice_id)
    # now delete the channels
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
            # FIX (CRITICAL): if there are no match channels, no voting UI is shown
            # and no timer runs. If we left the state as 'voting', players would be stuck
            # in the lobby forever (get_player_active_lobby counts 'voting' as active).
            logger.error(
                f"❌ auto_trigger_vote: lobby {lobby_id} has no match_channels — "
                f"reverting status to 'started'"
            )
            db.update_lobby_status(lobby_id, "started")
            await notify_admins(
                guild,
                "❌ Failed",
                f"> 🐛  Lobby `#{lobby_id}` has no match channels — vote will not be displayed.\n"
                f"> 🔄  Reverted status to `started`.\n"
                f"> 💡  Try  `!!startvote {lobby_id}`  or  `!!resolve {lobby_id} team1|team2`"
            )
            return

        t1m = " ".join([f"<@{p}>" for p in lobby["team1_players"]])
        t2m = " ".join([f"<@{p}>" for p in lobby["team2_players"]])

        # all match players vote
        voters = build_mvp_voters(lobby["team1_players"], lobby["team2_players"], creator_id)
        threshold = max(1, len(voters) // 2)
        v1 = [p for p in voters if p in lobby["team1_players"]]
        v2 = [p for p in voters if p in lobby["team2_players"]]

        # Detect 1v1 — use TeamWinnerVoteView instead of MvpVoteView
        game_mode = lobby.get("game_mode", DEFAULT_MODE)
        team_size = GAME_MODES.get(game_mode, {}).get("team_size", 4)
        is_1v1 = (team_size == 1)

        if is_1v1:
            # 🆕 1v1: simplified embed for winning team
            mvp_embed = discord.Embed(
                title=f"🗳️ 1v1 Vote · `#{lobby_id}`",
                description=(
                    f"🎯 Required: **{threshold}** votes\n"
                    f"⚠️ Vote from each team on same winner"
                ),
                color=COLORS["vote"]
            )
            mvp_embed = apply_branding(mvp_embed, guild)
        else:
            # 🆕 2v2/3v3/4v4: simplified embed with all rules
            mvp_embed = discord.Embed(
                title=f"🗳️ MVP Vote · `#{lobby_id}`",
                description=(
                    f"🎯 Required: **{threshold}** votes (at least one from each team)\n"
                    f"⚠️ Vote from each team on same player"
                ),
                color=COLORS["vote"]
            )
            mvp_embed = apply_branding(mvp_embed, guild)

        general_text = guild.get_channel(mc["team1_text_id"])
        vote_msg_id = None
        if not general_text:
            # FIX (HIGH): same problem - without a chat to hold the voting message the lobby is stuck
            logger.error(
                f"❌ auto_trigger_vote: lobby {lobby_id} match text channel "
                f"({mc['team1_text_id']}) not found — reverting status to 'started'"
            )
            db.update_lobby_status(lobby_id, "started")
            await notify_admins(
                guild,
                "❌ Failed",
                f"> 🐛  Match text channel `{mc['team1_text_id']}` "
                f"was not found in `{guild.name}` — the vote could not be posted.\n"
                f"> 🔄  Reverted status to `started`.\n"
                f"> 💡  Try  `!!startvote {lobby_id}`  or  `!!resolve {lobby_id} team1|team2`"
            )
            return
        # Use TeamWinnerVoteView for 1v1, MvpVoteView for other modes
        if is_1v1:
            vote_view = TeamWinnerVoteView(
                lobby_id, guild,
                lobby["team1_players"], lobby["team2_players"]
            )
        else:
            vote_view = MvpVoteView(
                lobby_id, guild, creator_id, first_joiner_id,
                lobby["team1_players"], lobby["team2_players"]
            )
        try:
            vote_msg = await general_text.send(
                f"🔱 {t1m} {t2m}",
                embed=mvp_embed,
                view=vote_view
            )
        except discord.HTTPException as e:
            # FIX (HIGH): send failure = same stuck state - revert the state and notify an admin
            logger.exception(f"❌ auto_trigger_vote: failed to send vote message (lobby {lobby_id}): {e}")
            db.update_lobby_status(lobby_id, "started")
            await notify_admins(
                guild,
                "❌ Failed",
                f"> 🐛  **Error:**  `{str(e)[:200]}`\n"
                f"> 🔄  Reverted lobby `#{lobby_id}` status to `started`.\n"
                f"> 💡  Try  `!!startvote {lobby_id}`  or  `!!resolve {lobby_id} team1|team2`"
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
                    f"Lobby `#{lobby_id}` was closed automatically — not enough players joined in time.\n"
                    f"💡 Use `{PREFIX}play 4v4` to open a new lobby."
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
        # tag admins on failure
        await notify_admins(
            guild,
            "Lobby Timeout Error",
            f"> ❌ timeout `#{lobby_id}`\n"
            f"> 🐛  **Error:**  `{str(e)[:200]}`"
        )

# ============================================================
# PROCESS MATCH RESULT
# ============================================================

async def process_match_result(guild, lobby_id, winner_team, channel=None):
    """🆕 New points system:
- MVP: +80
- : +30
- MVP: +30
- : -30
- ( 50 = )"""
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

        # pick the MVP of each team (higher rank, then higher streak on a tie)
        winner_mvp_id = get_mvp_player(wt, guild, db, guild.id)
        loser_mvp_id = get_mvp_player(lt, guild, db, guild.id)

        # points for the new system
        WINNER_MVP_POINTS = 80
        WINNER_POINTS = 30
        LOSER_MVP_POINTS = 30
        LOSER_POINTS = -30

        # winning team handling
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

        # losing team handling
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
        # fix: re-read the new ranks of every player after recalculate_ranks
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
        # save the match result with MVPs
        db.create_match_result(
            lobby_id, winner_team,
            len(wt), len(lt),
            mvp=winner_mvp_id
        )

        # build the professional result message
        wd = "🔴 Team 1" if winner_team == "team1" else "🟢 Team 2"
        wt_mentions = "\n".join([
            f"{'🔱' if is_mvp else '✅'}  <@{pid}> → `{'+' if pts > 0 else ''}{pts}` pts  (RANK #{old}→#{new})"
            for pid, pts, is_mvp, old, new in winner_details
        ]) or "* *"
        lt_mentions = "\n".join([
            f"{'✦' if is_mvp else '☠️'}  <@{pid}> → `{'+' if pts > 0 else ''}{pts}` pts  (RANK #{old}→#{new})"
            for pid, pts, is_mvp, old, new in loser_details
        ]) or "* *"

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
        # match result -> dedicated results channel (match-results) only, otherwise the original channel
        await _post_match_result(guild, embed, channel)

        # speed-up: close voices immediately - move players + delete match channels before
        #    any slow work (leaderboard / roles) so the chat/voice closes quickly
        await delete_match_channels(guild, lobby_id)
        cleanup_lobby_memory(lobby_id)

        # return players to the waiting rooms (right after deleting the channels)
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

        # update the leaderboard + sync roles of the match players only (speed-up)
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

# Modal for a report with a reason
class ReportReasonModal(discord.ui.Modal, title="⚠️ Report Player"):
    reason_input = discord.ui.TextInput(
        label="Reason (optional)",
        placeholder="Example: cheating or abusive behavior.",
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
            # sanitize the reason before storing (prevents mass-ping + exceeding the Discord limit)
            reason = sanitize_user_text(self.reason_input.value) if self.reason_input.value else None
            added, total = db.add_report(
                self.guild_id, self.reporter_id, self.reported_id,
                lobby_id=self.lobby_id, reason=reason
            )
            if not added:
                await interaction.response.send_message(
                    embed=discord.Embed(
                        title="⚠️ Already reported",
                        description=(
                            f"<@{self.reported_id}> has already been reported by you.\n"
                            "You cannot report the same player twice."
                        ),
                        color=COLORS["warning"]
                    ), ephemeral=True
                )
                return
            guild = interaction.guild
            # show the report confirmation
            remaining = max(0, REPORT_THRESHOLD - total)
            report_embed = discord.Embed(
                title="⚠️ Report Registered",
                description=(
                    (f"⚠️ `{remaining}`" if remaining > 0 else "⚠️ ** !**")
                ),
                color=COLORS["warning"] if remaining > 0 else COLORS["error"],
                timestamp=discord.utils.utcnow()
            )
            report_embed.add_field(name="👤 Reported", value=f"<@{self.reported_id}>", inline=True)
            report_embed.add_field(name="👮 Reporter", value=f"<@{self.reporter_id}>", inline=True)
            report_embed.add_field(name="📊 Reports", value=f"`{total}/{REPORT_THRESHOLD}`", inline=True)
            if reason:
                report_embed.add_field(name="📝 Reason", value=f"{reason}", inline=False)
            report_embed.set_footer(text=f"{BOT_FOOTER}  •  Report #{total}")
            report_embed = apply_branding(report_embed, guild)
            await interaction.response.send_message(embed=report_embed, ephemeral=True)
            # send the report to the admins with the reason
            await notify_admins(
                guild,
                "⚠️ New Player Report",
                f"> 👤 **Reported:** <@{self.reported_id}>\n"
                f"> 👮  **Reporter:**  <@{self.reporter_id}>\n"
                + (f"> 📝 **Reason:** {reason}\n" if reason else "> 📝 **Reason:** none\n")
                + f"> 📊 **Total reports:** `{total}/{REPORT_THRESHOLD}`",
                color=COLORS["warning"] if remaining > 0 else COLORS["error"]
            )
            # automatic ban check
            if guild:
                banned = await check_and_apply_auto_ban(guild, self.reported_id, total, self.reporter_id)
        except Exception as e:
            logger.exception(f"ReportReasonModal failed: {e}")

# View for choosing the reported player (inside the match)
class ReportPlayerSelectView(discord.ui.View):
    """ Select ."""
    def __init__(self, lobby_id, all_players, guild_id, reporter_id, guild=None):
        super().__init__(timeout=120)
        self.lobby_id = lobby_id
        self.guild_id = guild_id
        self.reporter_id = reporter_id
        self.guild = guild  # used to look up player names

        # filter the players (remove the reporter from the list)
        reportable = [pid for pid in all_players if pid != reporter_id]
        if not reportable:
            return

        # helper to fetch a player's name
        def get_player_name(pid):
            if self.guild:
                member = self.guild.get_member(pid)
                if member:
                    return member.display_name[:80]
            player = db.get_player(pid, guild_id)
            if player and player.get("username"):
                return player["username"][:80]
            return ""

        options = []
        for pid in reportable[:25]:  # Discord limit of 25 options
            name = get_player_name(pid)
            options.append(discord.SelectOption(
                label=name,
                value=str(pid),
                description="Report this player",
                emoji="⚠️"
            ))
        if not options:
            return
        select = discord.ui.Select(
            placeholder="⚠️ Select the player to report",
            options=options,
            custom_id=f"report_select_{lobby_id}",
            min_values=1,
            max_values=1
        )
        select.callback = self.select_callback
        self.add_item(select)

    async def select_callback(self, interaction):
        if interaction.user.id != self.reporter_id:
            await interaction.response.send_message("❌ This menu is not for you!", ephemeral=True)
            return
        reported_id = int(interaction.data["values"][0])
        # show the Modal to enter the reason
        await interaction.response.send_modal(
            ReportReasonModal(self.lobby_id, reported_id, self.guild_id, self.reporter_id)
        )

# the report button is added to every message in the match
class ReportButtonView(discord.ui.View):
    """View '⚠️ Report' select ."""
    def __init__(self, lobby_id, all_players, guild_id, reporter_id=None):
        super().__init__(timeout=None)
        self.lobby_id = lobby_id
        self.all_players = all_players
        self.guild_id = guild_id

    @discord.ui.button(label="⚠️ Report Player", style=discord.ButtonStyle.danger, custom_id="report_player_btn")
    async def report_btn(self, interaction, button):
        # any player can report - pass reporter_id = interaction.user.id
        view = ReportPlayerSelectView(self.lobby_id, self.all_players, self.guild_id, interaction.user.id, guild=interaction.guild)
        if not view.children:
            await interaction.response.send_message("❌ There are no players available to report!", ephemeral=True)
            return
        await interaction.response.send_message(
            embed=discord.Embed(
                title="⚠️ Report Player",
                description=(
                    ".\n"
                    "⚠️ Reports are serious — don't report without reason."
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

        # FIX: respond to the interaction first, before deleting channels (avoids interaction failure)
        mode = lobby.get("game_mode", DEFAULT_MODE).upper()
        await interaction.response.send_message(embed=discord.Embed(
            title="❌ Match Cancelled",
            description=(
                f"Match `#{self.lobby_id}` — `{mode}` was cancelled by <@{uid}>.\n"
                f"Use `{PREFIX}play` to start a new match."
            ),
            color=COLORS["error"]
        ), delete_after=30)

        # now update the state and delete the channels safely
        db.update_lobby_status(self.lobby_id, "cancelled")
        cleanup_lobby_memory(self.lobby_id)

        # delete the original lobby message in the play channel instead of leaving an outdated copy
        if interaction.message is not None:
            try:
                await delete_message_safely(
                    interaction.message.channel, interaction.message.id,
                    reason=f"cancel_game lobby #{self.lobby_id}"
                )
            except Exception as e:
                logger.debug(f"delete lobby embed in cancel_game failed: {e}")

        # delete the match channels (if any - the lobby may be waiting with no channels)
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

        # ban check
        ban_info = db.is_player_banned(interaction.guild.id, uid)
        if ban_info:
            ban_embed = discord.Embed(
                title="🚫 You are banned from playing",
                description=(
                    "🔍 \n"
                    "💡 To unban, contact an admin"
                ),
                color=COLORS["error"],
                timestamp=discord.utils.utcnow()
            )
            ban_embed.add_field(name="⚠️ Ban Reason", value=f"`{ban_info.get('ban_reason') or 'No reason'}`", inline=True)
            ban_embed.add_field(name="📊 Reports", value=f"`{ban_info.get('report_count', 0)}`", inline=True)
            ban_embed.set_footer(text=f"{BOT_FOOTER}  •  Banned")
            ban_embed = apply_branding(ban_embed, interaction.guild)
            await interaction.response.send_message(embed=ban_embed, ephemeral=True)
            # move to the investigation voice
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

        # MAX: do not move the player to a waiting room after joining a lobby
        # the player stays in their voice - they are moved to their team voice when the match starts
        # (removed the db.get_available_waiting_room + member.move_to code)

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

            # ✅ Disable only Join buttons (lobby is full), keep Leave + Cancel active
            for item in self.children:
                if hasattr(item, 'label') and item.label and ('Join' in item.label):
                    item.disabled = True
            try: await interaction.message.edit(view=self)
            except: pass

            try:
                channels = await create_match_channels(interaction.guild, lobby, self.lobby_id)
            except Exception as e:
                logger.exception(f"create_match_channels failed: {e}")
                channels = None
                # tag admins when channel creation fails
                await notify_admins(
                    interaction.guild,
                    "Match Channels Creation Failed",
                    f"> ❌ `#{self.lobby_id}`\n"
                    f"> 🐛  **Error:**  `{str(e)[:200]}`\n"
                    f"> 💡  Check bot permissions (Manage Channels)"
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
                # register the "Match Ready" message - deleted automatically when the match ends, however it ends
                register_lobby_flow_msg(self.lobby_id, interaction.channel.id, ready_msg.id)
            except discord.HTTPException as e:
                logger.debug(f"send Match Ready embed failed: {e}")

            if channels:
                # store each player's original voice before moving them to the team voice
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
                # send the report button in a separate message
                try:
                    all_players = lobby["team1_players"] + lobby["team2_players"]
                    report_view = ReportButtonView(self.lobby_id, all_players, interaction.guild.id)
                    report_embed = discord.Embed(
                        title="⚠️ Report System",
                        description=(
                            "If you notice a player cheating or misbehaving, press **⚠️ Report**\n"
                            "\n"
                            f"📊 After `{REPORT_THRESHOLD}` reports → auto-ban\n"
                            "🔍 Banned player is moved to investigation voice until admin unbans"
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
        # fix: Start Vote for admins, the owner and the host only
        member = interaction.guild.get_member(interaction.user.id)
        is_admin = member and (member.guild_permissions.administrator or member.guild_permissions.manage_guild)
        is_owner = interaction.user.id == BOT_OWNER_ID
        is_host = interaction.user.id == self.creator_id
        if not (is_admin or is_owner or is_host):
            await interaction.response.send_message(
                f"❌ Only the host or an admin can do this!\n"
                f"Host: <@{self.creator_id}>",
                ephemeral=True
            )
            return
        guild = bot.get_guild(self.guild_id)
        if not guild:
            await interaction.response.send_message("❌ Guild not found!", ephemeral=True)
            return
        # check the 10-minute cooldown from the match start
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
                        title="⏳ Please Wait",
                        description=(
                            "⏱️ A match can be cancelled only **10 minutes** after it starts.\n"
                            f"⏳ Remaining: `{remaining_min} min {remaining_sec} sec`"
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
        """🆕 Cancel Match ."""
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
            await interaction.response.send_message(f"⚠️ You already voted to cancel! ({len(self._cancel_votes)}/{required_votes})", ephemeral=True)
            return
        self._cancel_votes.add(uid)
        current_votes = len(self._cancel_votes)
        if current_votes >= required_votes:
            await self._execute_cancel(interaction, lobby, guild, uid, f"Majority ({current_votes}/{required_votes})")
            return
        remaining = required_votes - current_votes
        vote_embed = discord.Embed(
            title="🗳️ Cancel Vote",
            description=f"👤 <@{uid}> voted to cancel the match",
            color=COLORS["warning"],
            timestamp=discord.utils.utcnow()
        )
        vote_embed.add_field(name="📊 Votes", value=f"`{current_votes}/{required_votes}`", inline=True)
        vote_embed.add_field(name="⏳ Remaining", value=f"`{remaining}`", inline=True)
        vote_embed.set_footer(text=f"{BOT_FOOTER}  •  Cancel Vote")
        await interaction.response.send_message(embed=vote_embed)

    async def _execute_cancel(self, interaction, lobby, guild, uid, reason):
        """🆕 ."""
        mode = lobby.get("game_mode", DEFAULT_MODE).upper()
        cancelled_embed = discord.Embed(
            title="❌ Match Cancelled",
            description=(
                "🔄 ...\n"
                "🗑️ Deleting channels...\n"
                "\n"
                f"💡 Use `{PREFIX}play` to start a new match."
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
        # move the players to their original voice before deleting the channels
        all_players = lobby["team1_players"] + lobby["team2_players"]
        # look for a fallback waiting room
        fallback_vc = None
        for cid in db.get_waiting_rooms(guild.id):
            vc = guild.get_channel(cid)
            if vc and isinstance(vc, discord.VoiceChannel):
                fallback_vc = vc
                break
        # look up each player's original voice
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
        # clear the original voice from memory
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

# ============================================================
# collective MVP voting system - top 2 of each team
# ============================================================
def build_mvp_voters(team1_players, team2_players, creator_id=None):
    """All match players are voters (8/6/4/2 depending on mode).
✅ : — .
✅ cross-team ( ).
✅ creator_id compatibility ( )."""
    voters = []
    for p in (team1_players or []) + (team2_players or []):
        if p not in voters:
            voters.append(p)
    return voters

def _collect_admin_members(guild):
    """🆕 Returns all members with admin permissions (A+ / Manage Guild / ADMIN_ROLE_NAME / Owner)."""
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
    """🆕 No consensus among voters → escalated to admin (as requested).

:
1) ** **
→ .
2)
→ + ."""
    try:
        admins = _collect_admin_members(guild)
        mc = db.get_match_channels(lobby_id)

        # private investigation voices (Waiting Prv)
        prv_ids = set()
        for cid in db.get_waiting_rooms(guild.id):
            vc = guild.get_channel(cid)
            if vc and isinstance(vc, discord.VoiceChannel) and WAITING_PRV_CATEGORY_HINT.lower() in vc.name.lower():
                prv_ids.add(vc.id)

        t1v_id = mc.get("team1_voice_id") if mc else None
        t2v_id = mc.get("team2_voice_id") if mc else None
        t1_text_id = mc.get("team1_text_id") if mc else None
        t2_text_id = mc.get("team2_text_id") if mc else None

        # where are the players now?
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

        # admins present in private voices
        present = []
        for m in admins:
            if m.voice and m.voice.channel:
                cid = m.voice.channel.id
                if cid in prv_ids or (t1v_id and cid == t1v_id) or (t2v_id and cid == t2v_id):
                    present.append(m)

        # toggle sort
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
                title=f"🚨 MVP Consensus Failed — Match #{lobby_id}",
                description=(
                    f"{mentions}\n"
                    "⚠️ **No consensus among voters** — requesting admin intervention.\n"
                    f"📌 **Reason:** {reason_detail}"
                ),
                color=COLORS["error"],
                timestamp=discord.utils.utcnow()
            )
            embed.add_field(name="🔴 Team 1 — All Players", value=f"{' '.join(f'<@{p}>' for p in (team1_players or [])) or '*N/A*'}", inline=True)
            embed.add_field(name="🟢 Team 2 — All Players", value=f"{' '.join(f'<@{p}>' for p in (team2_players or [])) or '*N/A*'}", inline=True)
            embed.add_field(name="🗳️", value=f"🏆 Winner: {', '.join(f'**{c}**×<@{p}>' for p, c in sorted(w_tally.items(), key=lambda x: -x[1])) or '*No votes*'}\n✦ Loser: {', '.join(f'**{c}**×<@{p}>' for p, c in sorted(l_tally.items(), key=lambda x: -x[1])) or '*No votes*'}", inline=False)
            embed.add_field(name="🔧 Required Action", value=f"`{PREFIX}w {lobby_id} @user` — MVP WINNER\n`{PREFIX}l {lobby_id} @user` — MVP LOSER\n📌 — `!!w` + `!!l`", inline=False)
            embed.set_footer(text=f"{BOT_FOOTER}  •  Action required")
            embed = apply_branding(embed, guild)

            # send to the team channel linked to the voice the admin joined
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
                await notify_admins(guild, f"🚨 MVP — `#{lobby_id}`",
                                    f"> 🛑 **No channel available to post the dispute** — manual review needed\n"
                                    f"> 📌  {reason_detail}")
            if errs:
                logger.warning(f"⚠️ MVP dispute #{lobby_id}: — {'; '.join(errs)}")
            return moves

        # 2) if an admin is present -> tag + commands
        await notify_admins(
            guild,
            f"🚨 MVP Consensus Failed — Match `#{lobby_id}`",
            f"> ⚠️ **Admin decision required** — the voters did not agree.\n"
            f"> 📌  **Reason:**  {reason_detail}\n"
            f"> 👥  **Voters:**  "
            f"Team 1 🔴 {' '.join(f'<@{p}>' for p in (team1_players or []))}  |  "
            f"Team 2 🟢 {' '.join(f'<@{p}>' for p in (team2_players or []))}\n"
            f"> 🗳  **Vote:**  🏆 " + (", ".join(f"{c}×<@{p}>" for p, c in sorted(w_tally.items(), key=lambda x: -x[1])) or "No votes")
            + "  |  ✦ " + (", ".join(f"{c}×<@{p}>" for p, c in sorted(l_tally.items(), key=lambda x: -x[1])) or "No votes")
            + f"\n{separator()}\n"
            f"> 🔧  **Required Commands:**\n"
            f"> ─ `{PREFIX}w {lobby_id} @user` — MVP WINNER\n"
            f"> ─ `{PREFIX}l {lobby_id} @user` — MVP LOSER\n"
            f"> 💡  Must be from **different teams** — using `!!w` + `!!l` applies points automatically"
        )
        return []
    except Exception as e:
        logger.exception(f"❌ escalate_mvp_dispute failed for lobby {lobby_id}: {e}")
        try:
            await notify_admins(guild, f"❌ Failed MVP `#{lobby_id}`",
                                f"> 🐛  `{str(e)[:200]}`")
        except Exception:
            pass
        return []

# replaces VoteView + MvpSelectionView - no team voting, only MVP selection
class MvpVoteView(discord.ui.View):
    """MVP selection without team voting — collective system.
✅ (8/6/4 mode)
✅ timeout —
✅ threshold = (dynamic)
✅ cross-team: (WINNER LOSER)
✅ (fire-and-forget UI + process_match_result_with_mvps)
✅ : ( mention )"""
    def __init__(self, lobby_id, guild, creator_id, first_joiner_id, team1_players, team2_players):
        super().__init__(timeout=None)   # no timeout - the vote stays open until completed
        self.lobby_id = lobby_id
        self.guild = guild
        self.guild_id = guild.id
        self.creator_id = creator_id
        self.first_joiner_id = first_joiner_id
        self.team1_players = list(team1_players or [])
        self.team2_players = list(team2_players or [])
        self.winner_mvp_id = None
        self.loser_mvp_id = None
        self._applied = False
        self._escalated = False
        # voter log: {user_id: {"winner": pid, "loser": pid}}
        self.voters = build_mvp_voters(team1_players, team2_players, creator_id)
        self.votes = {}
        # dynamic threshold = half the number of voters (at least 1)
        self.consensus_needed = max(1, len(self.voters) // 2)
        logger.info(f"🗳️ MvpVoteView init: lobby={lobby_id}, voters={len(self.voters)}, threshold={self.consensus_needed}")

        all_players = list(team1_players) + list(team2_players)

        def get_player_name(pid):
            member = guild.get_member(pid)
            if member:
                return member.display_name[:80]
            player = db.get_player(pid, guild.id)
            if player and player.get("username"):
                return player["username"][:80]
            return ""

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
                placeholder="🏆 MVP WINNER — choose a player",
                options=options,
                custom_id=f"mvp_winner_select_{lobby_id}",
                min_values=1, max_values=1
            )
            winner_select.callback = self.winner_mvp_callback
            self.add_item(winner_select)

            loser_select = discord.ui.Select(
                placeholder="✦ MVP LOSER — choose a player",
                options=options,
                custom_id=f"mvp_loser_select_{lobby_id}",
                min_values=1, max_values=1
            )
            loser_select.callback = self.loser_mvp_callback
            self.add_item(loser_select)

        # admin tag button when there is a problem
        tag_admin_btn = discord.ui.Button(
            label="⚠️ Tag Admin",
            style=discord.ButtonStyle.danger,
            custom_id=f"tag_admin_btn_{lobby_id}"
        )
        tag_admin_btn.callback = self.tag_admin_callback
        self.add_item(tag_admin_btn)

        # neutral button to show the current state (no voting)
        status_btn = discord.ui.Button(
            label="📊 Vote Status",
            style=discord.ButtonStyle.secondary,
            custom_id=f"mvp_status_btn_{lobby_id}"
        )
        status_btn.callback = self.status_callback
        self.add_item(status_btn)

# ══════════════════════════════════════════════════════
    # voter tools + state + agreement
    # ══════════════════════════════════════════════════════
    def _is_voter(self, user_id):
        return user_id in self.voters

    async def _guard_voter(self, interaction):
        """ ."""
        if not self.voters:
            return True
        if interaction.user.id in self.voters:
            return True
        t1_names = " ".join(f"<@{p}>" for p in self.voters if p in self.team1_players)
        t2_names = " ".join(f"<@{p}>" for p in self.voters if p in self.team2_players)
        embed = discord.Embed(
            title="⛔ You are not a voter",
            description=(
                "❌ Your vote doesn't count in this system.\n"
                "Voters are **first 2 from each team**.\n"
                "📌 If you're one of them, select MVP from the menus above."
            ),
            color=COLORS["error"]
        )
        embed.add_field(name="🔴 Team 1", value=f"{t1_names or '*N/A*'}", inline=True)
        embed.add_field(name="🟢 Team 2", value=f"{t2_names or '*N/A*'}", inline=True)
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return False

    def _tally(self, key):
        """{player_id: } ."""
        counts = {}
        for _uid, data in self.votes.items():
            pid = data.get(key)
            if pid:
                counts[pid] = counts.get(pid, 0) + 1
        return counts

    def _consensus(self, key):
        """Returns player who reached self.consensus_needed votes
** ** (cross-team validation) None.

key = "winner" "loser"
✅ :
✅ (4 team1 )
✅ 1v1 ( = cross-team)"""
        tally = self._tally(key)
        for pid, c in tally.items():
            if c < self.consensus_needed:
                continue
            # cross-team check
            team1_votes = 0
            team2_votes = 0
            for uid, data in self.votes.items():
                if data.get(key) == pid:
                    if uid in self.team1_players:
                        team1_votes += 1
                    elif uid in self.team2_players:
                        team2_votes += 1
            # at least one vote from each team is required
            if team1_votes >= 1 and team2_votes >= 1:
                return pid
            # if all votes are from one team -> try the next player
        return None

    def _all_voted(self):
        """ (WINNER + LOSER)"""
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
            return f"> ─  {label}:  *No votes*"
        parts = [f"<@{p}> ×{c}" for p, c in sorted(tally.items(), key=lambda x: -x[1])]
        return f"> ─  {label}:  " + "   |   ".join(parts)

    def _tally_text(self, key):
        tally = self._tally(key)
        if not tally:
            return "No votes"
        return " / ".join(f"{c}×<@{p}>" for p, c in sorted(tally.items(), key=lambda x: -x[1]))

    async def _refresh(self, interaction=None):
        """ / ."""
        for item in self.children:
            if isinstance(item, (discord.ui.Select, discord.ui.Button)):
                item.disabled = True if self._applied else False
        if interaction is None:
            return
        # fix: discord.Interaction has no .edit() - edit the voting message itself
        try:
            if interaction.message is not None:
                await interaction.message.edit(view=self)
        except discord.HTTPException as e:
            logger.warning(f"⚠️ _refresh edit failed (lobby {self.lobby_id}): {e}")
        except Exception as e:
            logger.warning(f"⚠️ _refresh edit failed (lobby {self.lobby_id}): {e}")

    async def status_callback(self, interaction):
        """🆕 Neutral button: shows current status without any vote."""
        embed = discord.Embed(
            title=f"📊 MVP Vote · `#{self.lobby_id}`",
            description=(
                f"✅ `{self._voted_count()}` / `{len(self.voters)}` voted\n"
                f"🎯 Required: `{self.consensus_needed}` matching votes\n"
                f"⚠️ Vote from each team"
            ),
            color=COLORS["vote"]
        )
        embed.add_field(name="🏆 WINNER", value=self._tally_line('winner', ''), inline=False)
        embed.add_field(name="✦ LOSER", value=self._tally_line('loser', ''), inline=False)
        embed = apply_branding(embed, interaction.guild)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    async def tag_admin_callback(self, interaction):
        """🆕 Simple button: moves available admin to players channel instantly, or short message without mention."""
        if self._applied or self._escalated:
            return
        guild = self.guild or bot.get_guild(self.guild_id)
        if not guild:
            return
        # 1. look for a present admin (online / idle / dnd)
        admin_members = _collect_admin_members(guild)
        available_admins = [
            m for m in admin_members
            if not m.bot and m.status in (discord.Status.online, discord.Status.idle, discord.Status.dnd)
        ]
        # 2. look up the players' voice
        mc = db.get_match_channels(self.lobby_id)
        players_voice = None
        if mc:
            for cid in (mc.get("team1_voice_id"), mc.get("team2_voice_id")):
                vc = guild.get_channel(cid) if cid else None
                if vc and isinstance(vc, discord.VoiceChannel) and vc.members:
                    players_voice = vc
                    break
        # 3. execute + ephemeral reply
        if available_admins:
            admin = available_admins[0]
            # path A: admin present + in voice -> move them directly
            if players_voice and admin.voice and admin.voice.channel:
                try:
                    if admin.voice.channel.id != players_voice.id:
                        await admin.move_to(players_voice)
                    await interaction.response.send_message(
                        f"✅ Admin **{admin.display_name}** moved.",
                        ephemeral=True
                    )
                    try:
                        await interaction.channel.send(
                            f"🚨 `#{self.lobby_id}` — Admin available · `!!w @user` + `!!l @user`"
                        )
                    except Exception:
                        pass
                    logger.info(f"🚨 tag_admin: moved {admin.display_name} (lobby {self.lobby_id})")
                    return
                except (discord.Forbidden, discord.HTTPException) as e:
                    await interaction.response.send_message(
                        f"⚠️ Could not move you: {e}",
                        ephemeral=True
                    )
                    return
            # path B: admin present but not in voice
            await interaction.response.send_message(
                f"✅ Admin **{admin.display_name}** is available.",
                ephemeral=True
            )
            try:
                await interaction.channel.send(
                    f"🚨 `#{self.lobby_id}` — `!!w @user` + `!!l @user`"
                )
            except Exception:
                pass
            return
        # path C: no admin present
        await interaction.response.send_message(
            "⚠️ No admin available right now.",
            ephemeral=True
        )
        try:
            await interaction.channel.send(
                f"⏳ `#{self.lobby_id}` — Waiting for admin."
            )
        except Exception:
            pass
        logger.info(f"⏳ tag_admin: no admin (lobby {self.lobby_id})")

    async def _get_team(self, pid):
        return "team1" if pid in self.team1_players else "team2"

    # ══════════════════════════════════════════════════════
    # register the votes
    # ══════════════════════════════════════════════════════
    async def winner_mvp_callback(self, interaction):
        if not await self._guard_voter(interaction):
            return
        chosen = int(interaction.data["values"][0])
        self.votes.setdefault(interaction.user.id, {})["winner"] = chosen
        self.winner_mvp_id = chosen   # last vote - kept for compatibility with the !!w / !!l commands
        await interaction.response.send_message(
            f"🏆  Your vote for MVP WINNER recorded:  <@{chosen}>", ephemeral=True
        )
        await self._try_apply(interaction)

    async def loser_mvp_callback(self, interaction):
        if not await self._guard_voter(interaction):
            return
        chosen = int(interaction.data["values"][0])
        self.votes.setdefault(interaction.user.id, {})["loser"] = chosen
        self.loser_mvp_id = chosen
        await interaction.response.send_message(
            f"✦  Your vote for MVP LOSER recorded:  <@{chosen}>", ephemeral=True
        )
        await self._try_apply(interaction)

    # ══════════════════════════════════════════════════════
    # check for agreement after each vote
    # ══════════════════════════════════════════════════════
    async def _try_apply(self, interaction):
        if self._applied:
            return

        w = self._consensus("winner")
        l = self._consensus("loser")

        # full agreement
        if w and l:
            if await self._get_team(w) == await self._get_team(l):
                await self._escalate(
                    interaction.channel,
                    f"Voters reached consensus, but MVP WINNER <@{w}> and MVP LOSER <@{l}> are **on the same team** — impossible to apply"
                )
                return
            await self._apply(w, l, interaction)
            return

        # all voters voted and there is no agreement -> no consensus -> escalate to an admin
        if self._all_voted():
            reason = (
                f"No cross-team consensus — "
                f"🏆 {self._tally_text('winner')}   •   ✦ {self._tally_text('loser')}\n"
                f"⚠️ At least one vote from each team on same player (WINNER and LOSER)"
            )
            await self._escalate(interaction.channel, reason)
            return

        # some people have not voted yet - update the state only
        await self._refresh(interaction)

    async def _escalate(self, channel, reason_detail):
        """🆕 → ( )."""
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
    # Apply result — fire-and-forget UI + immediate process_match_result_with_mvps call
    # the critical path (points calculation) runs instantly without waiting for the UI edit or confirmation message
    # the UI edit + confirmation message are fired in the background via asyncio.ensure_future
    # ══════════════════════════════════════════════════════
    async def _apply(self, winner_mvp, loser_mvp, interaction):
        self._applied = True
        self.winner_mvp_id = winner_mvp
        self.loser_mvp_id = loser_mvp
        # 1. disable the UI instantly (sync, no waiting)
        for item in self.children:
            item.disabled = True
        # 2. fire-and-forget UI tasks (we do not wait for them)
        async def _ui_tasks():
            try:
                if interaction is not None and interaction.message is not None:
                    await interaction.message.edit(view=self)
                target_ch = interaction.channel if interaction is not None else None
                if target_ch is not None:
                    await target_ch.send(
                        embed=discord.Embed(
                            title="✅ Consensus Reached",
                            description=(
                                f"🏆 **WINNER:** <@{winner_mvp}> `+80`\n"
                                f"✦ **LOSER:** <@{loser_mvp}> `+30`\n"
                                "⚡ Calculating points..."
                            ),
                            color=COLORS["success"]
                        )
                    )
            except Exception as e:
                logger.warning(f"⚠️ _apply UI tasks failed (lobby {self.lobby_id}): {e}")
        asyncio.ensure_future(_ui_tasks())
        # 3. critical path instantly: points calculation
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
            target_ch = interaction.channel if interaction is not None else None
            await process_match_result_with_mvps(
                guild, self.lobby_id, winner_team, winner_mvp, loser_mvp,
                target_ch
            )
        except Exception as e:
            logger.exception(f"❌ process_match_result_with_mvps failed in _apply: {e}")
            try:
                await notify_admins(
                    guild,
                    f"❌ Failed #{self.lobby_id}",
                    f"> 🐛  **Error:**  `{str(e)[:200]}`\n"
                    f"> 🏆 Winner MVP:  <@{winner_mvp}>\n"
                    f"> ✦ Loser MVP:  <@{loser_mvp}>\n"
                    f"> 💡 Use  `!!w {self.lobby_id} @user`  and  `!!l {self.lobby_id} @user`  manually"
                )
            except Exception:
                pass

    # ══════════════════════════════════════════════════════
    # No timeout — voting stays open until completion or manual admin intervention
    # ══════════════════════════════════════════════════════
    # removed on_timeout entirely - super().__init__(timeout=None) prevents it from being called
    # if players do not vote, they must press the "Tag admin" button to end the match

# ════════════════════════════════════════════════════════════════════════════════
# TeamWinnerVoteView - dedicated to 1v1 (vote on the winning team instead of an MVP)
# all match players vote (in 1v1 = 2 voters)
# threshold = half the number of voters (at least 1)
# cross-team: at least one vote from each team for the same winning team
# no timeout - the vote stays open until completed
# immediate application (fire-and-forget UI + immediate call to process_match_result_with_mvps)
# simplified admin tag button (same as MvpVoteView)
# ════════════════════════════════════════════════════════════════════════════════
class TeamWinnerVoteView(discord.ui.View):
    def __init__(self, lobby_id, guild, team1_players, team2_players):
        super().__init__(timeout=None)
        self.lobby_id = lobby_id
        self.guild = guild
        self.guild_id = guild.id
        self.team1_players = list(team1_players or [])
        self.team2_players = list(team2_players or [])
        self.winner_team = None
        self._applied = False
        self._escalated = False
        self.voters = build_mvp_voters(team1_players, team2_players)
        self.votes = {}   # {user_id: "team1" | "team2"}
        self.consensus_needed = max(1, len(self.voters) // 2)
        logger.info(f"🗳️ TeamWinnerVoteView init (1v1): lobby={lobby_id}, voters={len(self.voters)}, threshold={self.consensus_needed}")
        
        # a single select: the winning team
        options = [
            discord.SelectOption(
                label=f"🔴 Team 1 — {self._player_name(self.team1_players[0]) if self.team1_players else 'N/A'}",
                value="team1",
                emoji="🔴"
            ),
            discord.SelectOption(
                label=f"🟢 Team 2 — {self._player_name(self.team2_players[0]) if self.team2_players else 'N/A'}",
                value="team2",
                emoji="🟢"
            ),
        ]
        winner_select = discord.ui.Select(
            placeholder="🏆 Select the winning team",
            options=options,
            custom_id=f"team_winner_select_{lobby_id}",
            min_values=1, max_values=1
        )
        winner_select.callback = self.team_winner_callback
        self.add_item(winner_select)
        
        # simplified admin tag button
        tag_admin_btn = discord.ui.Button(
            label="⚠️ Issue — Tag Admin",
            style=discord.ButtonStyle.danger,
            custom_id=f"1v1_tag_admin_{lobby_id}"
        )
        tag_admin_btn.callback = self.tag_admin_callback
        self.add_item(tag_admin_btn)
        
        # vote status button
        status_btn = discord.ui.Button(
            label="📊 Vote Status",
            style=discord.ButtonStyle.secondary,
            custom_id=f"1v1_status_{lobby_id}"
        )
        status_btn.callback = self.status_callback
        self.add_item(status_btn)
    
    def _player_name(self, pid):
        if not pid:
            return "N/A"
        member = self.guild.get_member(pid) if self.guild else None
        if member:
            return member.display_name[:80]
        p = db.get_player(pid, self.guild_id) if db else None
        return (p.get("username") or "")[:80] if p else ""
    
    async def _guard_voter(self, interaction):
        if not self.voters or interaction.user.id in self.voters:
            return True
        await interaction.response.send_message(
            embed=discord.Embed(
                title="⛔ You are not a voter",
                description="In 1v1, both players are the voters.",
                color=COLORS["error"]
            ), ephemeral=True
        )
        return False
    
    async def team_winner_callback(self, interaction):
        if self._applied or self._escalated:
            return
        if not await self._guard_voter(interaction):
            return
        chosen = interaction.data["values"][0]   # "team1" or "team2"
        self.votes[interaction.user.id] = chosen
        await interaction.response.send_message(
            f"✅ Vote recorded: **{'🔴 Team 1' if chosen == 'team1' else '🟢 Team 2'}**",
            ephemeral=True
        )
        await self._try_apply(interaction)
    
    def _tally(self):
        """ counts + cross-team info."""
        counts = {"team1": 0, "team2": 0}
        cross = {
            "team1": {"team1": 0, "team2": 0},
            "team2": {"team1": 0, "team2": 0}
        }
        for uid, choice in self.votes.items():
            if choice not in counts:
                continue
            counts[choice] += 1
            voter_team = "team1" if uid in self.team1_players else "team2"
            cross[choice][voter_team] += 1
        return counts, cross
    
    def _consensus(self):
        """Returns winning team if reached threshold + cross-team, else None."""
        counts, cross = self._tally()
        for choice, c in counts.items():
            if c < self.consensus_needed:
                continue
            # cross-team: at least one vote from each team for the same winning team
            if cross[choice]["team1"] >= 1 and cross[choice]["team2"] >= 1:
                return choice
        return None
    
    def _all_voted(self):
        return len(self.votes) == len(self.voters)
    
    async def _try_apply(self, interaction):
        if self._applied:
            return
        winner = self._consensus()
        if winner:
            await self._apply(winner, interaction)
            return
        if self._all_voted():
            await self._escalate(
                interaction.channel,
                f"1v1 — no agreement (cross-team agreement required)"
            )
            return
        # still waiting - update the interface only
        try:
            if interaction.message is not None:
                await interaction.message.edit(view=self)
        except Exception:
            pass
    
    async def _apply(self, winner_team, interaction):
        self._applied = True
        self.winner_team = winner_team
        for item in self.children:
            item.disabled = True
        # fire-and-forget UI tasks
        async def _ui_tasks():
            try:
                if interaction is not None and interaction.message is not None:
                    await interaction.message.edit(view=self)
                target_ch = interaction.channel if interaction is not None else None
                if target_ch is not None:
                    winner_label = "🔴 Team 1" if winner_team == "team1" else "🟢 Team 2"
                    await target_ch.send(
                        embed=discord.Embed(
                            title="✅ Consensus Reached",
                            description=(
                                f"🏆 **Winner:** {winner_label}\n"
                                "⚡ Calculating points..."
                            ),
                            color=COLORS["success"]
                        )
                    )
            except Exception as e:
                logger.warning(f"⚠️ 1v1 _apply UI tasks failed (lobby {self.lobby_id}): {e}")
        asyncio.ensure_future(_ui_tasks())
        # critical path instantly
        logger.info(
            f"🏆 TeamWinnerVoteView confirmed — lobby={self.lobby_id}, "
            f"winner_team={winner_team}, voters={len(self.voters)}, votes={len(self.votes)}"
        )
        guild = self.guild or bot.get_guild(self.guild_id)
        if not guild:
            logger.error(f"❌ Guild not found for 1v1 lobby {self.lobby_id}")
            return
        # 1v1: winner_mvp = player of the winning team, loser_mvp = player of the losing team
        winner_mvp_id = self.team1_players[0] if winner_team == "team1" else self.team2_players[0]
        loser_mvp_id = self.team2_players[0] if winner_team == "team1" else self.team1_players[0]
        try:
            target_ch = interaction.channel if interaction is not None else None
            await process_match_result_with_mvps(
                guild, self.lobby_id, winner_team, winner_mvp_id, loser_mvp_id,
                target_ch
            )
        except Exception as e:
            logger.exception(f"❌ 1v1 process_match_result failed: {e}")
            try:
                await notify_admins(
                    guild,
                    f"❌ Failed 1v1 #{self.lobby_id}",
                    f"> 🐛  **Error:**  `{str(e)[:200]}`\n"
                    f"> 🏆 Winner: `{winner_team}`\n"
                    f"> 💡 Use `!!resolve {self.lobby_id} {winner_team}`"
                )
            except Exception:
                pass
    
    async def _escalate(self, channel, reason_detail):
        if self._applied or self._escalated:
            return
        self._escalated = True
        logger.warning(f"🚨 TeamWinnerVoteView escalation — lobby={self.lobby_id}: {reason_detail}")
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
    
    async def tag_admin_callback(self, interaction):
        """🆕 Simple button for 1v1 — same logic as MvpVoteView.tag_admin_callback."""
        if self._applied or self._escalated:
            return
        guild = self.guild or bot.get_guild(self.guild_id)
        if not guild:
            return
        admin_members = _collect_admin_members(guild)
        available_admins = [
            m for m in admin_members
            if not m.bot and m.status in (discord.Status.online, discord.Status.idle, discord.Status.dnd)
        ]
        mc = db.get_match_channels(self.lobby_id)
        players_voice = None
        if mc:
            for cid in (mc.get("team1_voice_id"), mc.get("team2_voice_id")):
                vc = guild.get_channel(cid) if cid else None
                if vc and isinstance(vc, discord.VoiceChannel) and vc.members:
                    players_voice = vc
                    break
        if available_admins:
            admin = available_admins[0]
            if players_voice and admin.voice and admin.voice.channel:
                try:
                    if admin.voice.channel.id != players_voice.id:
                        await admin.move_to(players_voice)
                    await interaction.response.send_message(
                        f"✅ Admin **{admin.display_name}** moved.",
                        ephemeral=True
                    )
                    try:
                        await interaction.channel.send(
                            f"🚨 `#{self.lobby_id}` — `!!resolve {self.lobby_id} team1|team2`"
                        )
                    except Exception:
                        pass
                    logger.info(f"🚨 1v1 tag_admin: moved {admin.display_name} (lobby {self.lobby_id})")
                    return
                except (discord.Forbidden, discord.HTTPException) as e:
                    await interaction.response.send_message(
                        f"⚠️ Could not move you: {e}",
                        ephemeral=True
                    )
                    return
            await interaction.response.send_message(
                f"✅ Admin **{admin.display_name}** is available.",
                ephemeral=True
            )
            try:
                await interaction.channel.send(
                    f"🚨 `#{self.lobby_id}` — `!!resolve {self.lobby_id} team1|team2`"
                )
            except Exception:
                pass
            return
        await interaction.response.send_message(
            "⚠️ No admin available right now.",
            ephemeral=True
        )
        try:
            await interaction.channel.send(
                f"⏳ `#{self.lobby_id}` — Waiting for admin."
            )
        except Exception:
            pass
        logger.info(f"⏳ 1v1 tag_admin: no admin (lobby {self.lobby_id})")
    
    async def status_callback(self, interaction):
        counts, cross = self._tally()
        embed = discord.Embed(
            title=f"📊 1v1 Vote · `#{self.lobby_id}`",
            description=(
                f"✅ `{len(self.votes)}` / `{len(self.voters)}` voted\n"
                f"🎯 Required: `{self.consensus_needed}` matching votes\n"
                f"⚠️ Vote from each team"
            ),
            color=COLORS["vote"]
        )
        embed.add_field(
            name="🏆 Votes",
            value=(
                f"🔴 `{counts['team1']}` · 🟢 `{counts['team2']}`"
            ),
            inline=False
        )
        embed = apply_branding(embed, interaction.guild)
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def process_match_result_with_mvps(guild, lobby_id, winner_team, winner_mvp_id, loser_mvp_id, channel=None):
    """🆕 Applies new points system with manually-specified MVPs.
✅ : Always ends match (even if applying points fails)."""
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
        # fix: set the state to completed immediately - so the match ends even if something after it fails
        db.update_lobby_status(lobby_id, "completed")

        game_mode = lobby.get("game_mode", DEFAULT_MODE)
        wt = lobby["team1_players"] if winner_team == "team1" else lobby["team2_players"]
        lt = lobby["team2_players"] if winner_team == "team1" else lobby["team1_players"]
        logger.info(f"  Winners: {wt}, Losers: {lt}, Winner MVP: {winner_mvp_id}, Loser MVP: {loser_mvp_id}")

        # points for the new system
        WINNER_MVP_POINTS = 80
        WINNER_POINTS = 30
        LOSER_MVP_POINTS = 30
        LOSER_POINTS = -30

        # winning team handling
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

        # losing team handling
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
        
        # fix: re-read the new ranks of every player after recalculate_ranks
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
        
        # save the match result
        db.create_match_result(lobby_id, winner_team, len(wt), len(lt), mvp=winner_mvp_id)

        # build the result message
        wd = "🔴 Team 1" if winner_team == "team1" else "🟢 Team 2"
        wt_mentions = "\n".join([
            f"{'🔱' if is_mvp else '✅'}  <@{pid}> → `{'+' if pts > 0 else ''}{pts}` pts  (RANK #{old}→#{new})"
            for pid, pts, is_mvp, old, new in winner_details
        ]) or "* *"
        lt_mentions = "\n".join([
            f"{'✦' if is_mvp else '☠️'}  <@{pid}> → `{'+' if pts > 0 else ''}{pts}` pts  (RANK #{old}→#{new})"
            for pid, pts, is_mvp, old, new in loser_details
        ]) or "* *"

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
        # match result -> dedicated results channel (match-results) only, otherwise the original channel
        await _post_match_result(guild, embed, channel)

        # speed-up: close voices immediately - move players + delete match channels before
        #    leaderboard / roles so channels close as fast as possible (especially !!w / !!l)
        await delete_match_channels(guild, lobby_id)
        cleanup_lobby_memory(lobby_id)
        _original_voice_channels.pop(lobby_id, None)
        logger.info(f"✅ Match #{lobby_id} completed — channels deleted, memory cleaned")

        # update the leaderboard + sync roles of the match players only (speed-up)
        all_players = lobby["team1_players"] + lobby["team2_players"]
        await update_leaderboard_channel(guild)
        await sync_all_players_roles(guild, player_ids=all_players)
    except Exception as e:
        logger.exception(f"❌ process_match_result_with_mvps FAILED for lobby {lobby_id}: {e}")
        # fix: even if everything fails, make sure the match ends and the channels are deleted
        try:
            db.update_lobby_status(lobby_id, "completed")
            _original_voice_channels.pop(lobby_id, None)
            await delete_match_channels(guild, lobby_id)
            cleanup_lobby_memory(lobby_id)
            logger.info(f"🔧 Match #{lobby_id} force-completed after error")
        except Exception as e2:
            logger.exception(f"❌ Failed to force-complete match {lobby_id}: {e2}")
        # tag admins on failure
        try:
            await notify_admins(
                guild,
                "Match Result Processing Failed",
                f"> ❌ `#{lobby_id}`\n"
                f"> 🐛  **Error:**  `{str(e)[:200]}`\n"
                f"> ✅  Match ended and channels deleted\n"
                f"> 💡  Check points manually with `!!setpoints`"
            )
        except:
            pass

class CreateLobbyView(discord.ui.View):
    def __init__(self, ctx, mode, timeout='__DEFAULT__'):
        # fix: timeout=None allows the View to be registered as persistent at startup
        if timeout == '__DEFAULT__':
            timeout = 300
        super().__init__(timeout=timeout)
        self.ctx = ctx
        self.mode = mode

    @discord.ui.button(label="📋 Create Lobby", style=discord.ButtonStyle.success, custom_id="create_lobby_btn")
    async def create_lobby_btn(self, interaction, button):
        # FIX (MEDIUM): the View is registered as persistent in on_ready with ctx=None.
        # Any old "Create Lobby" message (from before a bot restart) whose button is pressed ->
        # self.ctx was None => unhandled AttributeError.
        if self.ctx is None:
            await interaction.response.send_message(
                embed=discord.Embed(
                    title="⏳ Message expired",
                    description=(
                        "🔄 This lobby message is no longer active.\n"
                        f"💡 Use `{PREFIX}play {self.mode.upper()}` to create a new lobby."
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

            # link the "Create Lobby" message to this lobby - deleted when the match ends
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
            # after 2 minutes, if the lobby is still waiting (not enough players) -> close it and delete the message
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
        # fix: timeout=None allows the View to be registered as persistent at startup
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
            # after 2 minutes, if the lobby is still waiting (not enough players) -> close it and delete the message
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

# container for the periodic background task (added in the architecture review 2026-10)
# Reason: `asyncio.create_task(periodic_rank_sync())` created a new task on every
# on_ready (= every reconnect) => several parallel loops straining the Discord API.
_periodic_rank_task = None

# FIX (HIGH): the heavy setup inside on_ready (auto_setup + AUTO-DETECT message) ran
# on every on_ready call (= every Gateway reconnect) => autosetup
# repeated every few minutes. This guard makes it run **once per process**.
_startup_done = False
_on_ready_count = 0   # diagnostics only: how many times on_ready ran (reveals reconnects)

def is_admin_check(ctx):
    return ctx.author.guild_permissions.administrator

def is_bot_owner_check(ctx):
    return ctx.author.id == BOT_OWNER_ID

def is_bot_owner_or_admin_check(ctx):
    return ctx.author.id == BOT_OWNER_ID or ctx.author.guild_permissions.administrator

# check the privileged roles of members - used by the play1v1 command
# allows the member to use it if any of the following conditions holds:
#   1) has the Administrator permission in the server
#   2) has the Manage Guild permission
#   3) holds a role in the upper half of the server's role hierarchy
def is_high_role_member(member):
    """✅ MAX: play1v1 for admins only (Administrator / Manage Guild / Bot Owner).
    no longer checks top_role."""
    # 1) bot owner = full access
    if member.id == BOT_OWNER_ID:
        return True
    # 2) Admin permission = full access
    if member.guild_permissions.administrator:
        return True
    # 3) Manage Guild permission
    if member.guild_permissions.manage_guild:
        return True
    return False  # otherwise - not allowed

def is_high_role_check(ctx):
    """Wrapper for use as @commands.check() decorator."""
    return is_high_role_member(ctx.author)

# BLACKLIST: global check for all commands - prevents blacklisted players from using the bot
@bot.check
async def blacklist_global_check(ctx):
    """🆕 ."""
    if not ctx.guild:
        return True
    if ctx.author.id == BOT_OWNER_ID:
        return True
    if ctx.author.guild_permissions.administrator:
        return True
    if db.is_player_blacklisted(ctx.guild.id, ctx.author.id):
        return False
    # if the duration expired, make sure the role is removed
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
                title="🔇 You are blacklisted",
                description=(
                    ".\n"
                    "You are blacklisted for 10 minutes.\n"
                    "⏱️ Wait until the duration ends."
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
    # register persistent views (VoteView removed — replaced by MvpVoteView)
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

    # FIX (HIGH): on_ready is called again on every Gateway reconnect.
    # Before the fix, auto_setup + the AUTO-DETECT message + background tasks were repeated every time
    # (the visible cause of "autosetup every few minutes"). Now the heavy setup runs once per process,
    # and on reconnect we only refresh presence (see below) and stop here.
    if _startup_done:
        logger.info(
            f"♻️ on_ready re-fired (reconnect) — skipping auto-setup. "
            f"latency={bot.latency * 1000:.0f}ms  (on_ready #{_on_ready_count})"
        )
        return
    _startup_done = True

    # Auto-setup: check all servers in parallel
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
    # V3: AUTO-DETECT success message - in the commands channel only
    async def send_success(guild):
        try:
            success_ch = None
            cmd_channels = db.get_commands_channels(guild.id)
            # search only in commands channels
            if cmd_channels:
                for cid in cmd_channels:
                    ch = guild.get_channel(cid)
                    if ch and ch.permissions_for(guild.me).send_messages:
                        success_ch = ch
                        break
            # fallback: play channels only if there are no commands channels
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
                    title="✅ AUTO-DETECT",
                    description=(
                        f"📝 `{cmd_channels_count}` · 🎮 `{play_channels_count}` · "
                        f"🔊 `{len(waiting_rooms)}` · 🔍 `{len(report_channels)}`\n"
                        f"💡 `{PREFIX}help`"
                    ),
                    color=COLORS["success"]
                )
                success_embed.add_field(name="🏠 Server", value=f"{guild.name}", inline=True)
                success_embed.add_field(name="📅 Time", value=f"{discord.utils.format_dt(discord.utils.utcnow(), 'F')}", inline=True)
                success_embed = apply_branding(success_embed, guild)
                await success_ch.send(embed=success_embed)
                logger.info(f"  ✅ [AUTO-DETECT] Success message sent to #{success_ch.name} in {guild.name}")
            else:
                logger.warning(f"  ⚠️ [AUTO-DETECT] No commands channel found in {guild.name} — skipping success message")
        except Exception as e:
            logger.warning(f"Failed to send auto-detect success message in {guild.name}: {e}")
    await asyncio.gather(*[send_success(g) for g in bot.guilds], return_exceptions=True)
    logger.info(f"✅ Auto-detect success messages sent to all servers (total detected: {total_detected_all} channels)")
    
    # periodic rank and title sync every minute
    async def periodic_rank_sync():
        """60
fixrank + syncnicknames ( )."""
        tick = 0
        while True:
            try:
                await asyncio.sleep(60)
                tick += 1
                for guild in bot.guilds:
                    try:
                        # recalculate ranks
                        db.recalculate_ranks(guild.id)
                        # remove the titles
                        await sync_all_players_roles(guild)
                        # every 2 minutes: fixrank + sync nicknames for all members
                        if tick % 2 == 0:
                            await sync_all_nicknames(guild)
                    except Exception as e:
                        logger.warning(f"Periodic rank sync failed for {guild.name}: {e}")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning(f"Periodic rank sync error: {e}")

    # FIX (HIGH): `on_ready` runs again on every reconnect, and before the fix
    # every call created a new task with no check => N parallel loops after N disconnects,
    # each running recalculate_ranks + sync_all_players_roles (duplicate API calls
    # => rate limits + slowness). Now we guarantee a single task only.
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

    # restore/cleanup after a restart: delete stale lobby messages that ended
    #    and were left in the play channels, and re-enable the auto-close for stuck (waiting) lobbies.
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
                # lobbies stuck in waiting after a restart -> re-enable the 2-minute timer
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
    # diagnostics: any Gateway disconnect is logged clearly (reveals the cause of repeated on_ready)
    logger.warning("🔌 Gateway disconnected — awaiting automatic reconnect...")

@bot.event
async def on_resumed():
    logger.info("♻️ Gateway session resumed (no full re-identify).")

async def auto_setup_guild(guild):
    """Smart auto-detect — scans all server channels and registers them in DB.
    ✅ No manual setup needed — detects all prior configuration.
    ✅ Uses fuzzy matching to recognize channels by any name.
    ✅ Registers existing channels in DB instead of creating duplicates.
    ✅ Detects under-check voices (Under check / Investigation / Prv) automatically.
    ✅ Detects commands channel automatically.
    """
    logger.info(f"🔍 [AUTO-SETUP] Scanning {guild.name}...")

    # ============================================================
    # 1) Scan all text channels and register them automatically
    # ============================================================
    # Search patterns per channel type — flexible matching
    # ✅ FIX: removed "match", "lobby", "top", "player" — these caused false positives
    # "match" matched "match-results" channel → would register it as play channel
    # "lobby" matched any channel containing "lobby"
    # "top" matched "stop-spam", "topic" etc.
    # "player" matched "multiplayer", "replay" etc.
    TEXT_PATTERNS = {
        "play": ["play", "apostada", "highlight", "zelika"],
        "results": ["result", "match-result", "results"],
        "leaderboard": ["leaderboard", "ranking"],
        "profiles": ["profile", "profiles"],
        "rules": ["rules", "قوانين", "reglement"],
    }

    detected_text_channels = {"play": [], "results": [], "leaderboard": [], "profiles": [], "rules": []}

    for ch in guild.text_channels:
        name_lower = ch.name.lower()
        for channel_type, patterns in TEXT_PATTERNS.items():
            for pattern in patterns:
                # ✅ FIX: skip empty patterns + word-boundary-ish check
                if pattern and pattern in name_lower:
                    detected_text_channels[channel_type].append(ch)
                    break

    # Register all detected text channels in DB
    # ✅ FIX: do not register "results" as a play channel — only "play", "leaderboard" and "profiles"
    for channel_type, channels in detected_text_channels.items():
        for ch in channels:
            db.add_commands_channel(guild.id, ch.id)
            if channel_type in ["play", "leaderboard", "profiles"]:
                db.add_play_channel(guild.id, ch.id)
            if channel_type == "leaderboard":
                db.set_guild_setting(guild.id, "leaderboard_channel_id", ch.id)
            logger.info(f"  📝 Detected text channel: #{ch.name} ({channel_type})")

    # ============================================================
    # 2) Scan all voice channels and register them automatically
    # ============================================================
    VOICE_PATTERNS = {
        "waiting": ["waiting", "wait", "انتظار"],
        "prv": ["prv", "private", "خاص"],
        "under_check": ["under check", "under-check", "investigation", "تفتيش"],
        "staff": ["staff", "admn", "أدمن"],
    }

    detected_voice_channels = {"waiting": [], "prv": [], "under_check": [], "staff": []}

    for ch in guild.voice_channels:
        name_lower = ch.name.lower()
        for voice_type, patterns in VOICE_PATTERNS.items():
            for pattern in patterns:
                # ✅ FIX: skip empty patterns (caused EVERY channel to be detected as waiting)
                if pattern and pattern in name_lower:
                    detected_voice_channels[voice_type].append(ch)
                    break

    # Register all detected voice channels
    for voice_type, channels in detected_voice_channels.items():
        for ch in channels:
            if voice_type in ["waiting", "prv", "staff"]:
                db.add_waiting_room(guild.id, ch.id)
                logger.info(f"  🔊 Detected voice: {ch.name} ({voice_type} → waiting_room)")
            elif voice_type == "under_check":
                # 🆕 Register under-check voices as report channels
                db.add_report_channel(guild.id, ch.id)
                logger.info(f"  🔍 Detected under-check voice: {ch.name} (→ report_channel)")

    # ============================================================
    # 3) Scan categories
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
    # 4) Create only what's missing (if certain channels weren't detected)
    # ============================================================
    # If no play channel was detected, create one
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

    # blacklist channel - displays blacklisted players (created + updated automatically)
    try:
        bl_ch = discord.utils.get(guild.text_channels, name=BLACKLIST_CHANNEL_NAME)
        if not bl_ch:
            bl_ch = await guild.create_text_channel(BLACKLIST_CHANNEL_NAME, category=text_cat, topic="Blacklisted Players")
            db.add_commands_channel(guild.id, bl_ch.id)
            logger.info(f"  📝 Created {BLACKLIST_CHANNEL_NAME}")
        db.set_guild_setting(guild.id, "blacklist_channel_id", bl_ch.id)
    except Exception as e:
        logger.warning(f"  [{guild.name}] Blacklist channel: {e}")

    # rules channel - same logic as setup_cmd (idempotent)
    try:
        rules_ch, rules_created = await ensure_rules_channel(guild, text_cat)
        if rules_created and rules_ch:
            logger.info(f"  🛡️ Created {RULES_CHANNEL_NAME}")
    except Exception as e:
        logger.error(f"  [{guild.name}] Rules channel: {e}")

    # if no waiting voice was detected, create one
    if not detected_voice_channels["waiting"]:
        for ch_name in ["⏳・Waiting 1", "⏳・Waiting 2", "⏳・Waiting 3", "⏳・Waiting 4", "⏳・Waiting 5"]:
            if not discord.utils.get(guild.voice_channels, name=ch_name):
                overwrites = {guild.me: discord.PermissionOverwrite(connect=True, manage_channels=True)}
                ch = await guild.create_voice_channel(ch_name, category=voice_cat, overwrites=overwrites)
                db.add_waiting_room(guild.id, ch.id)
                logger.info(f"  🔊 Created {ch_name}")

    # if no prv voice was detected, create one
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

    # update the blacklist channel automatically after setup
    try:
        await update_blacklist_channel(guild)
    except Exception as e:
        logger.warning(f"  [{guild.name}] Blacklist channel update: {e}")

    # summary of what was detected
    total_detected = sum(len(v) for v in detected_text_channels.values()) + sum(len(v) for v in detected_voice_channels.values())
    logger.info(f"  ✅ [{guild.name}] Auto-setup complete — detected {total_detected} existing channels")

    # clear the cache when finished (we registered new channels)
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
    # update the nickname directly without calling update_member_nickname (avoids a second get_or_create_player)
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

def _find_match_text_channel_for_member(guild, member):
    """Finds match text channel the player belongs to (for warnings).
✅ active match channels lobby."""
    try:
        if not guild or not member or not db:
            return None
        # fetch all active match channels in the server
        active = db.get_all_active_match_channels(guild.id)
        for mc in active:
            # check whether the player is in either team of the linked lobby
            lobby = db.get_lobby(mc.get("lobby_id"))
            if not lobby:
                continue
            t1 = lobby.get("team1_players") or []
            t2 = lobby.get("team2_players") or []
            try:
                if member.id not in t1 and member.id not in t2:
                    continue
            except Exception:
                continue
            # try the linked text channel
            for cid_key in ("team1_text_id", "team2_text_id"):
                cid = mc.get(cid_key)
                if cid:
                    ch = guild.get_channel(cid)
                    if ch and ch.permissions_for(guild.me).send_messages:
                        return ch
        return None
    except Exception:
        return None

# helper functions for the blacklist
async def _reset_blacklist_after_stay(guild, member, uid, stay_seconds=None):
    """If player stays stay_seconds in match without leaving → reset tracking.
✅ (task.cancel on_voice_state_update)."""
    if stay_seconds is None:
        stay_seconds = BLACKLIST_RESET_AFTER_STAY
    try:
        await asyncio.sleep(stay_seconds)
        track = _blacklist_voice_tracking.get(guild.id, {})
        if uid in track and track[uid].get("in_match_voice"):
            # the player was in the match for stay_seconds -> reset the tracking
            old_total = track[uid].get("total_leave_time", 0)
            old_count = track[uid].get("leave_count", 0)
            track[uid]["total_leave_time"] = 0
            track[uid]["leave_count"] = 0
            track[uid]["warned_1"] = False
            track[uid]["warned_2"] = False
            track[uid]["reset_task"] = None
            if old_total > 0 or old_count > 0:
                logger.info(
                    f"✅ BLACKLIST RESET: {member.display_name} stayed {stay_seconds}s in match, "
                    f"cleared (was {old_total:.0f}s / {old_count} leaves)"
                )
    except asyncio.CancelledError:
        # normal: the player left before the duration completed
        pass
    except Exception as e:
        logger.warning(f"⚠️ _reset_blacklist_after_stay failed: {e}")

async def _maybe_warn_blacklist(guild, member, track_entry, total_time, leave_count):
    """Graduated warnings before applying blacklist.

Level 1 (50% ):
Level 2 (80% ):
✅ level (track_entry["warned_1"/"warned_2"]).
✅ ephemeral-style ( )."""
    try:
        # first warning: when 50% of the limit is exceeded
        if not track_entry.get("warned_1"):
            warn = False
            reason = ""
            if total_time >= BLACKLIST_WARN_LEVEL_1_TIME and total_time < BLACKLIST_WARN_LEVEL_2_TIME:
                warn = True
                reason = f"📊 Notice: Left for {total_time:.0f}s of {BLACKLIST_TIME_LIMIT}s — continued leaving may cause 5min blacklist."
            elif leave_count >= BLACKLIST_WARN_LEVEL_1_LEAVES and leave_count < BLACKLIST_WARN_LEVEL_2_LEAVES:
                warn = True
                reason = f"📊 Notice: Left {leave_count} times of {BLACKLIST_MAX_LEAVES} — continued leaving may cause blacklist."
            if warn:
                track_entry["warned_1"] = True
                logger.info(f"📢 BLACKLIST WARN 1: {member.display_name} (total={total_time:.0f}s, leaves={leave_count})")
                # find the match channel to send the warning to (player in an active match)
                target_ch = _find_match_text_channel_for_member(guild, member)
                if target_ch:
                    try:
                        await target_ch.send(
                            f"⚠️ {member.mention} — {reason}"
                        )
                    except Exception:
                        pass
    except Exception as e:
        logger.warning(f"⚠️ _maybe_warn_blacklist (level 1) failed: {e}")

    try:
        # final warning: when 80% of the limit is exceeded
        if not track_entry.get("warned_2"):
            warn = False
            reason = ""
            if total_time >= BLACKLIST_WARN_LEVEL_2_TIME and total_time < BLACKLIST_TIME_LIMIT:
                warn = True
                reason = f"🚨 Final warning: Left for {total_time:.0f}s of {BLACKLIST_TIME_LIMIT}s — one more long leave will trigger 5min blacklist!"
            elif leave_count >= BLACKLIST_WARN_LEVEL_2_LEAVES and leave_count < BLACKLIST_MAX_LEAVES:
                warn = True
                reason = f"🚨 Final warning: Left {leave_count} times of {BLACKLIST_MAX_LEAVES} — one more leave will trigger blacklist!"
            if warn:
                track_entry["warned_2"] = True
                logger.info(f"📢 BLACKLIST WARN 2: {member.display_name} (total={total_time:.0f}s, leaves={leave_count})")
                target_ch = _find_match_text_channel_for_member(guild, member)
                if target_ch:
                    try:
                        await target_ch.send(
                            f"🚨 {member.mention} — {reason}"
                        )
                    except Exception:
                        pass
    except Exception as e:
        logger.warning(f"⚠️ _maybe_warn_blacklist (level 2) failed: {e}")

# prevent banned players from leaving the investigation voice
@bot.event
async def on_voice_state_update(member, before, after):
    """🆕 + + ."""
    if member.bot:
        return

    guild = member.guild
    gid = guild.id

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 1) check banned players - prevent leaving the investigation voice
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    ban_info = db.is_player_banned(gid, member.id)
    if ban_info:
        assigned_voice_id = ban_info.get("assigned_voice_id")
        # case 1: the player joined a new voice
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
        # case 2: the player left a voice
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
    # 2) check jailed players (JAIL system)
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
    # 3) BLACKLIST TRACKING - tracking team departures (softened)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # P1 fix for leave counting:
    #    - use time.time() instead of datetime.now().timestamp() (timezone-independent)
    #    - ignore short leaves (< 10s) in leave_count (not counted as a "leave")
    #    - cancel reset_task when apply_blacklist runs (prevents a dangling task)
    #    - exclude BOT_OWNER_ID and Administrator from tracking
    #    - gradual reset after 60 seconds of staying in the match
    #    - graduated warnings at 50% and 80% of the limit before applying
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # exclude admins and the owner from tracking
    if member.id == BOT_OWNER_ID:
        return   # no tracking on the Owner
    try:
        if member.guild_permissions.administrator:
            return   # no tracking on admin
    except Exception:
        pass

    # only track players who leave/enter the match voices
    before_is_match = before.channel and before.channel.id in _active_match_voice_channels
    after_is_match = after.channel and after.channel.id in _active_match_voice_channels

    if not before_is_match and not after_is_match:
        return  # not in a match voice - no need to track

    # initialize the tracking dict for the server and the player
    if gid not in _blacklist_voice_tracking:
        _blacklist_voice_tracking[gid] = {}
    track = _blacklist_voice_tracking[gid]
    uid = member.id
    if uid not in track:
        track[uid] = {
            "leave_count": 0,
            "total_leave_time": 0.0,
            "in_match_voice": before_is_match,
            "leave_start": None,
            "warned_1": False,   # first warning
            "warned_2": False,   # final warning
            "reset_task": None,  # asyncio task for the gradual reset
        }

    # ✅ P1: time.time() timezone-independent (UTC seconds)
    now = time.time()
    # P1: short-leave threshold - leaves shorter than this are not counted in leave_count
    SHORT_LEAVE_THRESHOLD = 10  # seconds

    # case: left the match voice (was in the match and left)
    if before_is_match and not after_is_match:
        track[uid]["in_match_voice"] = False
        track[uid]["leave_start"] = now
        # P1: do not increment leave_count here - defer it until the player returns
        # if the leave was short (< 10s) it is not counted as a "real leave"
        # cancel any old reset task (the player left before the 60s)
        if track[uid].get("reset_task") and not track[uid]["reset_task"].done():
            track[uid]["reset_task"].cancel()
            track[uid]["reset_task"] = None
        logger.info(f"🔇 BLACKLIST TRACK: {member.display_name} left match voice (pending leave_count: {track[uid]['leave_count']})")

    # case: returned to the match voice (was outside the match and returned)
    elif after_is_match and not before_is_match:
        if track[uid]["leave_start"] is not None:
            elapsed = now - track[uid]["leave_start"]
            track[uid]["total_leave_time"] += elapsed
            track[uid]["leave_start"] = None
            # P1: only long leaves (>= SHORT_LEAVE_THRESHOLD) count toward leave_count
            if elapsed >= SHORT_LEAVE_THRESHOLD:
                track[uid]["leave_count"] += 1
                logger.info(f"🔇 BLACKLIST TRACK: {member.display_name} leave counted ({elapsed:.1f}s >= {SHORT_LEAVE_THRESHOLD}s)")
            else:
                logger.info(f"🔇 BLACKLIST TRACK: {member.display_name} short leave ignored ({elapsed:.1f}s < {SHORT_LEAVE_THRESHOLD}s)")
        track[uid]["in_match_voice"] = True
        total_time = track[uid]["total_leave_time"]
        leave_count = track[uid]["leave_count"]
        logger.info(f"🔇 BLACKLIST TRACK: {member.display_name} rejoined match voice (total leave: {total_time:.1f}s, leaves: {leave_count})")

        # graduated warnings before checking the limits
        await _maybe_warn_blacklist(guild, member, track[uid], total_time, leave_count)

        # check the limits
        if total_time >= BLACKLIST_TIME_LIMIT:
            logger.info(f"🔇 BLACKLIST: {member.display_name} exceeded time limit ({total_time:.1f}s >= {BLACKLIST_TIME_LIMIT}s)")
            reason = f"Automatic: left match voice for {total_time:.0f}s (limit: {BLACKLIST_TIME_LIMIT}s)"
            await apply_blacklist(guild, member, reason=reason)
            # P1: cancel reset_task before clearing tracking (prevents a dangling task)
            if track[uid].get("reset_task") and not track[uid]["reset_task"].done():
                track[uid]["reset_task"].cancel()
            # clear the tracking
            track.pop(uid, None)
            return
        if leave_count >= BLACKLIST_MAX_LEAVES:
            logger.info(f"🔇 BLACKLIST: {member.display_name} exceeded max leaves ({leave_count} >= {BLACKLIST_MAX_LEAVES})")
            reason = f"Automatic: left and rejoined {leave_count} times (limit: {BLACKLIST_MAX_LEAVES})"
            await apply_blacklist(guild, member, reason=reason)
            # P1: cancel reset_task before clearing tracking (prevents a dangling task)
            if track[uid].get("reset_task") and not track[uid]["reset_task"].done():
                track[uid]["reset_task"].cancel()
            # clear the tracking
            track.pop(uid, None)
            return

        # start the gradual reset after 60 seconds of staying in the match
        # if the player stays 60 seconds without leaving -> the tracking is reset
        if track[uid].get("reset_task") and not track[uid]["reset_task"].done():
            track[uid]["reset_task"].cancel()
        track[uid]["reset_task"] = asyncio.ensure_future(
            _reset_blacklist_after_stay(guild, member, uid)
        )

    # case: moved between voices (from one match voice to another) - still counts as in the match
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
        # FIX (MEDIUM): `ctx.guild is None` in DMs => any unprotected command would raise
        # AttributeError in the check with no message to the user. We block unsupported commands.
        content = message.content.strip()
        parts = content.split()
        invoked = parts[0].lower() if parts else ""
        # `!!serverleave` only: the only command intentionally designed for DMs.
        #    `!!help` calls apply_branding(ctx.guild) => None => AttributeError,
        #    so it stays outside the list (its previous behavior: error in the check with no reply - now blocked).
        dm_safe = {f"{PREFIX}serverleave"}
        if invoked in dm_safe:
            await bot.process_commands(message)
            return
        await message.channel.send(embed=discord.Embed(
            title="📡 Commands only inside server",
            description=(
                "This command works only inside a server (not in DMs).\n"
                f"💡 Use `{PREFIX}help` inside a server to see the command list.\n"
                f"📌 Commands available here: `{PREFIX}serverleave`"
            ),
            color=COLORS["info"]
        ), delete_after=20)
        return
    if not message.guild:
        return

    # check jailed players (JAIL) - prevent writing in channels other than the jail chats
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
    # ban check first
    ban_info = db.is_player_banned(guild.id, user.id)
    if ban_info:
        ban_embed = discord.Embed(
            title="🚫 You are banned from playing",
            description=(
                "🔍 \n"
                "💡 To unban, contact an admin"
            ),
            color=COLORS["error"],
            timestamp=discord.utils.utcnow()
        )
        ban_embed.add_field(name="⚠️ Ban Reason", value=f"`{ban_info.get('ban_reason') or 'No reason'}`", inline=True)
        ban_embed.add_field(name="📊 Reports", value=f"`{ban_info.get('report_count', 0)}`", inline=True)
        ban_embed.add_field(name="📅 Banned At", value=f"`{ban_info.get('banned_at', 'N/A')[:19]}`", inline=True)
        ban_embed.set_footer(text=f"{BOT_FOOTER}  •  Banned")
        ban_embed = apply_branding(ban_embed, ctx.guild)
        await ctx.send(embed=ban_embed, delete_after=20)
        # move to the investigation voice if in voice
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

    # if the player has an old "Create Lobby" message -> delete it (so messages do not pile up)
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
                ctx.channel, pid, reason="play"
            ))
        logger.info(f"🧹 Removed stale 'Create Lobby' message {pid} for user {user.id}")

    create_embed = discord.Embed(
        title=f"🎮 Create {mode.upper()} Lobby",
        description="Press the button below to enter room details and create the lobby.",
        color=COLORS["play"]
    )
    create_embed.add_field(name="💡 Required details", value="• Room ID\n• Password\n• Private Key", inline=False)
    create_embed.add_field(name="⏱️ Note", value=f"This message is deleted after `{CREATE_PROMPT_DELETE_AFTER}` seconds.\n✅ It is also removed automatically when the match ends.", inline=False)
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
    # smart !!play - accepts the mode as an argument
    # Example: !!play 1v1, !!play 4v4, !!play 2v2
    # if no argument -> show an error message with the alternatives
    # if the argument is valid -> start the match with this mode
    # if the argument is invalid -> show an error message

    if mode is None:
        # fix: build the embed as a variable correctly
        no_mode_embed = discord.Embed(
            title="❌ Invalid Command",
            description=(
                f"`{PREFIX}play` — you must specify a game mode.\n"
                f"💡 Example: `{PREFIX}play4v4`"
            ),
            color=COLORS["error"],
            timestamp=discord.utils.utcnow()
        )
        no_mode_embed.add_field(name="🎮 Available Modes", value=f"`{PREFIX}play1v1` — 1 vs 1 🔒 (high roles only)\n`{PREFIX}play2v2` — 2 vs 2\n`{PREFIX}play3v3` — 3 vs 3\n`{PREFIX}play4v4` — 4 vs 4 (standard)", inline=False)
        no_mode_embed.set_footer(text=f"{BOT_FOOTER}  •  Specify the game mode")
        no_mode_embed = apply_branding(no_mode_embed, ctx.guild)
        await ctx.send(embed=no_mode_embed, delete_after=15)
        return

    # convert the mode to lowercase and strip spaces
    mode = mode.strip().lower()

    # list of valid modes
    valid_modes = list(GAME_MODES.keys())  # ['1v1', '2v2', '3v3', '4v4']

    if mode not in valid_modes:
        # fix: build the embed as a variable correctly
        invalid_mode_embed = discord.Embed(
            title="❌ Invalid Mode",
            description=(
                f"`{mode}` is not a valid mode. Choose one of:\n"
                f"💡 Example: `{PREFIX}play 4v4`"
            ),
            color=COLORS["error"],
            timestamp=discord.utils.utcnow()
        )
        invalid_mode_embed.add_field(name="🎮 Available Modes", value=f"`{PREFIX}play 1v1` `{PREFIX}play1v1` 🔒\n`{PREFIX}play 2v2` `{PREFIX}play2v2`\n`{PREFIX}play 3v3` `{PREFIX}play3v3`\n`{PREFIX}play 4v4` `{PREFIX}play4v4`", inline=False)
        invalid_mode_embed.set_footer(text=f"{BOT_FOOTER}  •  Invalid mode")
        invalid_mode_embed = apply_branding(invalid_mode_embed, ctx.guild)
        await ctx.send(embed=invalid_mode_embed, delete_after=15)
        return

    # valid mode - start the match
    # special check for play1v1 (privileged roles only)
    if mode == "1v1" and not is_high_role_member(ctx.author):
        member = ctx.author
        guild_roles = [r for r in ctx.guild.roles if r.hoist and r != ctx.guild.default_role]
        max_position = max((r.position for r in guild_roles), default=0)
        threshold = max(1, max_position // 2) if max_position else 0
        member_top = member.top_role.position if member.top_role else 0
        # fix: build the embed as a variable correctly
        restricted_embed = discord.Embed(
            title="🔒 Protected Command",
            description=(
                f"**Command:** `{PREFIX}play 1v1`\n"
                "Only for members with **high roles** in the server.\n"
                f"💡 Use `{PREFIX}play 4v4` (available to everyone)."
            ),
            color=COLORS["error"],
            timestamp=discord.utils.utcnow()
        )
        restricted_embed.add_field(name="🎯 Requirements (any one of these)", value=f"• `Administrator` permission\n• `Manage Guild` permission (manage server)\n• A role at position `≥ {threshold}` (your top role position: `{member_top}`)", inline=False)
        restricted_embed.set_footer(text=f"{BOT_FOOTER}  •  Restricted Command")
        restricted_embed = apply_branding(restricted_embed, ctx.guild)
        await ctx.send(embed=restricted_embed, delete_after=20)
        return

    # start the match with this mode (same logic as play1v1_cmd / play2v2_cmd / etc.)
    await create_mode_lobby(ctx, mode)

@bot.command(name="play1v1")
async def play1v1_cmd(ctx):
    # play1v1 for members with privileged roles only (admin / manage_guild / higher role in the upper half)
    if not is_high_role_member(ctx.author):
        # show a professional message explaining the requirement
        member = ctx.author
        guild_roles = [r for r in ctx.guild.roles if r.hoist and r != ctx.guild.default_role]
        max_position = max((r.position for r in guild_roles), default=0)
        threshold = max(1, max_position // 2) if max_position else 0
        member_top = member.top_role.position if member.top_role else 0
        # fix: build the embed as a variable correctly
        restricted_embed = discord.Embed(
            title="🔒 Protected Command",
            description=(
                f"**Command:** `{PREFIX}play1v1`\n"
                "Only for members with **high roles** in the server.\n"
                f"💡 Use `{PREFIX}play 4v4` (available to everyone)."
            ),
            color=COLORS["error"],
            timestamp=discord.utils.utcnow()
        )
        restricted_embed.add_field(name="🎯 Requirements (any one of these)", value=f"• `Administrator` permission\n• `Manage Guild` permission (manage server)\n• A role at position `≥ {threshold}` (your top role position: `{member_top}`)", inline=False)
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
    """!!points — show your points and rank"""
    target = member or ctx.author
    player = db.get_or_create_player(target.id, ctx.guild.id, target.display_name)
    level = player.get("level", STARTING_LEVEL)
    points = player.get("points", 0)
    top_pts = db.get_top_points(ctx.guild.id)
    pts_to_next = max(0, top_pts - points) if top_pts > points else 0
    progress_pct = max(0, min(100, int((points / max(top_pts, 1)) * 100))) if top_pts else 0  # V5 fix: clamp the percentage between 0-100
    progress_bar = make_progress_bar(points, max(top_pts, 1), length=15)
    rank_color = get_rank_color(level)
    rank_title = get_rank_title(level)
    rank_emoji = get_rank_emoji(level)
    wr = round((player["wins"] / max(player["matches_played"], 1)) * 100, 1)
    wr_bar = make_winrate_bar(wr, length=10)

    embed = discord.Embed(
        title="💰 Player Points",
        description=(
            f"👤 {target.mention}\n"
            f"🏅 {rank_emoji} **{rank_title}**  `#{level}`\n"
            f"💰 `{points:,}` pts"
        ),
        color=rank_color,
        timestamp=discord.utils.utcnow()
    )
    # progress toward first place
    if pts_to_next > 0:
        embed.add_field(
            name="📈 Progress to #1",
            value=f"`{progress_bar}` `{progress_pct}%`\n💎 `{points:,}` · 🏆 `{top_pts:,}` · ⏭️ `{pts_to_next:,}`",
            inline=False
        )
    else:
        embed.add_field(
            name="🔱 You are #1!",
            value=f"🎉 `{points:,}` pts — you lead the leaderboard!\n🚀 Keep it up!",
            inline=False
        )

    # quick stats
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
    """!!card — show the player profile card"""
    target = member or ctx.author
    player = db.get_or_create_player(target.id, ctx.guild.id, target.display_name)
    await update_member_nickname(target, player.get("level", STARTING_LEVEL))
    await ctx.send(embed=create_profile_embed(player, target, ctx.guild.id))

@bot.command(name="top")
async def top_cmd(ctx):
    # hide blacklisted players from the leaderboard (instead of showing them)
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
# RULES - single source for the rules text
# ============================================================
# fixed name of the rules channel - if you change it, change it everywhere at once
RULES_CHANNEL_NAME = "🛡️ Rules"

def build_rules_embed(guild_name):
    """🆕 embed — !!setup !!autosetup !!rules.
✅ : 3 ."""
    embed = discord.Embed(
        title="🛡️ Server Rules",
        description=(
            f"**{guild_name}** 🔥\n"
            "Please follow these rules:"
        ),
        color=COLORS["info"],
        timestamp=discord.utils.utcnow()
    )
    embed.add_field(name="1️⃣ Mutual Respect", value="• Treat every member with respect.\n• No insults, harassment or toxic behavior.", inline=False)
    embed.add_field(name="2️⃣ Game Rules", value=f"• Only join a match you can finish.\n• Use `{PREFIX}play 4v4` to open a lobby.\n• Do not leave a match in progress.", inline=False)
    embed.add_field(name="3️⃣ No Cheating", value="• Cheating of any kind is forbidden.\n• Report suspected cheaters with the report button.", inline=False)
    embed.add_field(name="4️⃣ Use Commands Properly", value="• Use the `play` commands only in the play channels.", inline=False)
    embed.add_field(name="5️⃣ Penalties", value="• Violations lead to a warning / blacklist / ban.\n• Repeated reports lead to an automatic ban.", inline=False)
    embed.add_field(name="💬 Note", value="Admin decisions are final.", inline=False)
    embed.set_author(name="Server Rules")
    embed.set_footer(text=f"{BOT_FOOTER}  •  Read carefully")
    return embed

async def ensure_rules_channel(guild, text_cat=None):
    """🆕 Creates rules channel if missing, and posts rules in it.
✅ idempotent: .
✅ ( )."""
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

    # send the rules message (failed? the channel at least exists now)
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
    
    # separate category for text channels
    text_cat = discord.utils.get(guild.categories, name="🎮 Free Fire Text")
    if not text_cat:
        text_cat = await guild.create_category("🎮 Free Fire Text", overwrites={guild.default_role: discord.PermissionOverwrite(read_messages=True), guild.me: discord.PermissionOverwrite(manage_channels=True, manage_messages=True)})
        created.append("🎮 Free Fire Text")
    
    # separate category for voice channels
    voice_cat = discord.utils.get(guild.categories, name="🎮 Free Fire Voice")
    if not voice_cat:
        voice_cat = await guild.create_category("🎮 Free Fire Voice", overwrites={guild.default_role: discord.PermissionOverwrite(read_messages=True), guild.me: discord.PermissionOverwrite(manage_channels=True, manage_messages=True)})
        created.append("🎮 Free Fire Voice")

    # rules channel - created automatically (idempotent: not duplicated if it exists)
    rules_ch, rules_created = await ensure_rules_channel(guild, text_cat)
    if rules_created and rules_ch:
        created.append(RULES_CHANNEL_NAME)
    elif rules_ch:
        logger.info(f"ℹ️ [setup] {guild.name}: Rules channel already exists — skipping creation")

    # text channels in the text category
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
    
    # voice channels in the voice category
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
    # update the blacklist channel during setup
    try:
        await update_blacklist_channel(guild)
    except Exception as e:
        logger.warning(f"setup blacklist channel update failed: {e}")
    # create the title roles + update Waiting Prv permissions
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
    # fix: build the success embed as a variable correctly
    setup_embed = discord.Embed(
        title="✅ Setup Complete!",
        description=f"Created `{len(created)}` channels successfully.",
        color=COLORS["success"],
        timestamp=discord.utils.utcnow()
    )
    setup_embed.add_field(name="🛡️ Rules channel", value=f"`{RULES_CHANNEL_NAME}` — `{PREFIX}rules`", inline=False)
    setup_embed.add_field(name="🔇 Blacklist Role", value=f"`{BLACKLIST_ROLE_NAME}`", inline=False)
    setup_embed.add_field(name="🎮 Next", value=f"Use `{PREFIX}play4v4` in play channels to start.", inline=False)
    setup_embed.set_footer(text=f"{BOT_FOOTER}  •  Setup complete")
    setup_embed = apply_branding(setup_embed, ctx.guild)
    await ctx.send(embed=setup_embed)

@bot.command(name="autosetup", aliases=["autoset", "checksetup"])
@commands.check(is_bot_owner_or_admin_check)
async def autosetup_cmd(ctx):
    """!!autosetup — auto-detect and register channels"""
    # fix: build the embed as a variable, then set_footer, then apply_branding
    progress_embed = discord.Embed(
        title="🔄 Scanning server...",
        description=(
            "🔍 ...\n"
            "🔧 Creating Roles + JAIL if not exist...\n"
            "⏳ Please wait..."
        ),
        color=COLORS["warning"],
        timestamp=discord.utils.utcnow()
    )
    progress_embed.set_footer(text=f"{BOT_FOOTER}  •  Auto-setup")
    progress_embed = apply_branding(progress_embed, ctx.guild)
    progress = await ctx.send(embed=progress_embed)

    try:
        await auto_setup_guild(ctx.guild)
        # fix: build the success embed as a variable correctly
        success_embed = discord.Embed(
            title="✅ Scan & Repair Complete!",
            description=(
                "🔍 \n"
                "✅ All missing channels created\n"
                "✅ All categories updated (TEXT + VOICE separated)\n"
                "✅ Rank Roles updated\n"
                "✅ JAIL system enabled\n"
                f"✅ Blacklist Role `{BLACKLIST_ROLE_NAME}`\n"
                "✅ Leaderboard updated\n"
                "\n"
                "💡 No existing data wiped — points, ranks and voices preserved"
            ),
            color=COLORS["success"],
            timestamp=discord.utils.utcnow()
        )
        success_embed.set_footer(text=f"{BOT_FOOTER}  •  Auto-setup complete")
        success_embed = apply_branding(success_embed, ctx.guild)
        await progress.edit(embed=success_embed)
    except Exception as e:
        # fix: build the error embed as a variable correctly
        error_embed = discord.Embed(
            title="❌ Failed Auto-setup",
            description=f"🐛 **Error:** `{str(e)[:200]}`",
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
    """!!scan [page] — list server categories and channels"""
    guild = ctx.guild
    categories = sorted(guild.categories, key=lambda c: c.position)
    per_page = 3  # 3 categories per page (each one has a lot of detail)
    total_pages = max(1, (len(categories) + per_page - 1) // per_page)
    if page < 1: page = 1
    if page > total_pages: page = total_pages
    start = (page - 1) * per_page
    end = start + per_page
    page_cats = categories[start:end]

    # collect all channels without a category
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
        # details of each channel inside the category
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

    # show channels without a category (on the last page)
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
    """!!deletecat <name> — request deletion of a category (asks for confirmation)"""
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
    # look up the category by name (exact or partial match)
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

    # show a confirmation before deleting
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
    """!!confirmcat <name> — confirm deletion of a category"""
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

    # delete all channels inside the category
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

    # delete the category itself
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
    # FIX: member_count can be None in large servers -> do not break the command
    total_members = sum((g.member_count or 0) for g in bot.guilds)
    total_text_channels = sum(len(g.text_channels) for g in bot.guilds)
    total_voice_channels = sum(len(g.voice_channels) for g in bot.guilds)
    embed = discord.Embed(
        title="🤖 Bot Info",
        description=(
            "🔥 **Free Fire Matchmaking Bot**\n"
            "Complete matchmaking system for Free Fire matches"
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
    embed.add_field(name="🎮 Features", value=f"• 🏆 4 Modes (1v1/2v2/3v3/4v4)\n• 🗳️ Vote: all players · 50%+1\n• 🏅 Dynamic Ranks\n• 📊 Leaderboard\n• 🛡️ Auto Rules\n• ⏱️ Auto-hide Lobby\n• 🔇 Soft Blacklist", inline=False)
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
# REPORT & BAN COMMANDS - report and ban commands
# ============================================================

@bot.command(name="report")
async def report_cmd(ctx, member: discord.Member = None, *, reason: str = None):
    """!!report @user [reason] — report a player"""
    if not member:
        await ctx.send(embed=discord.Embed(
            title="❌ Missing User",
            description=(
                f"Usage: `{PREFIX}report @user [reason]`\n"
                f": `{PREFIX}report @user `"
            ),
            color=COLORS["error"]
        ), delete_after=15)
        return
    if member.id == ctx.author.id:
        await ctx.send(embed=discord.Embed(
            title="❌ Cannot report yourself",
            color=COLORS["error"]
        ), delete_after=10)
        return
    if member.bot:
        await ctx.send(embed=discord.Embed(
            title="❌ Cannot report a bot",
            color=COLORS["error"]
        ), delete_after=10)
        return
    # sanitize the reason before storing: prevents mass-ping via <@&id> / @everyone
    #    and prevents exceeding the 1024-character embed field limit (HTTPException 400)
    reason = sanitize_user_text(reason, max_length=200)
    # record the report
    added, total = db.add_report(ctx.guild.id, ctx.author.id, member.id, reason=reason)
    if not added:
        await ctx.send(embed=discord.Embed(
            title="⚠️ Already reported",
            description=f"{member.mention} has already been reported by you.",
            color=COLORS["warning"]
        ), delete_after=10)
        return
    remaining = max(0, REPORT_THRESHOLD - total)
    report_embed = discord.Embed(
        title="⚠️ Report Registered",
        description=(
            (f"⚠️ `{remaining}`" if remaining > 0 else "⚠️ ** !**")
        ),
        color=COLORS["warning"] if remaining > 0 else COLORS["error"],
        timestamp=discord.utils.utcnow()
    )
    report_embed.add_field(name="👤 Reported", value=f"{member.mention}", inline=True)
    report_embed.add_field(name="👮 Reporter", value=f"{ctx.author.mention}", inline=True)
    report_embed.add_field(name="📊 Reports", value=f"`{total}/{REPORT_THRESHOLD}`", inline=True)
    if reason:
        report_embed.add_field(name="📝 Reason", value=f"{reason}", inline=False)
    report_embed.set_footer(text=f"{BOT_FOOTER}  •  Report #{total}")
    report_embed = apply_branding(report_embed, ctx.guild)
    await ctx.send(embed=report_embed)
    # send the report to the admins with the reason
    await notify_admins(
        ctx.guild,
        "⚠️ New Player Report",
        f"> 👤 **Reported:** {member.mention}\n"
        f"> 👮  **Reporter:**  {ctx.author.mention}\n"
        + (f"> 📝 **Reason:** {reason}\n" if reason else "> 📝 **Reason:** none\n")
        + f"> 📊 **Total reports:** `{total}/{REPORT_THRESHOLD}`",
        color=COLORS["warning"] if remaining > 0 else COLORS["error"]
    )
    # automatic ban check
    await check_and_apply_auto_ban(ctx.guild, member.id, total, ctx.author.id)

@bot.command(name="reports")
async def reports_cmd(ctx, member: discord.Member = None):
    """!!reports @user — show reports against a player"""
    target = member or ctx.author
    reports = db.get_reports_for_player(ctx.guild.id, target.id)
    count = len(reports)
    embed = discord.Embed(
        title=f"⚠️ Player Reports — {target.display_name}",
        description=(
            f"👤 {target.mention}   ·   📊 `{count}/{REPORT_THRESHOLD}`\n"
            + ("⚠️ **Auto-ban threshold reached**" if count >= REPORT_THRESHOLD else f"⚠️ **Reports until auto-ban:** `{REPORT_THRESHOLD - count}`")
        ),
        color=COLORS["error"] if count >= REPORT_THRESHOLD else COLORS["warning"],
        timestamp=discord.utils.utcnow()
    )
    if reports:
        # show the last 10 reports
        for i, r in enumerate(reports[:10], 1):
            reporter = ctx.guild.get_member(r["reporter_id"])
            reporter_name = reporter.display_name if reporter else f"User#{r['reporter_id']}"
            reason = r.get("reason") or ""
            timestamp = r.get("created_at", "N/A")[:19] if r.get("created_at") else "N/A"
            embed.add_field(
                name=f"#{i} — {reporter_name}",
                value=f"📝 `{reason}`\n📅 `{timestamp}`",
                inline=False
            )
        if count > 10:
            embed.set_footer(text=f"{BOT_FOOTER} • +{count - 10} older reports")
    else:
        embed.description = f"> ✅ {target.mention}"
        embed.color = COLORS["success"]
    embed.set_author(name="Player Reports", icon_url=None)
    # fix: apply_branding must always be applied, not only when reports exceed 10
    embed = apply_branding(embed, ctx.guild)
    await ctx.send(embed=embed)

@bot.command(name="banplayer", aliases=["ban"])
@commands.check(is_admin_check)
async def banplayer_cmd(ctx, target: Union[discord.Member, int] = None, *, reason: str = None):
    """!!banplayer @user|ID [reason] — ban a player from playing"""
    if not target:
        await ctx.send(embed=discord.Embed(
            title="❌ Missing User",
            description=f"Usage: `{PREFIX}banplayer @user ID [reason]`",
            color=COLORS["error"]
        ), delete_after=15)
        return
    user_id = target.id if isinstance(target, discord.Member) else target
    if user_id == ctx.author.id:
        await ctx.send("❌ You cannot ban yourself!", delete_after=10)
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
        title="🚫 Player Banned",
        color=COLORS["error"],
        timestamp=discord.utils.utcnow()
    )
    ban_embed.add_field(name="👤 Player", value=f"<@{user_id}>", inline=True)
    ban_embed.add_field(name="👮 Banned by", value=f"{ctx.author.mention}", inline=True)
    ban_embed.add_field(name="📊 Reports", value=f"`{report_count}`", inline=True)
    if reason:
        ban_embed.add_field(name="📝 Reason", value=f"`{reason}`", inline=False)
    if assigned_channel:
        ban_embed.add_field(name="🔍 Investigation Voice", value=f"{assigned_channel.mention}\n🔒 Assigned voice", inline=False)
    ban_embed.set_footer(text=f"{BOT_FOOTER}  •  Banned")
    ban_embed = apply_branding(ban_embed, ctx.guild)
    await ctx.send(embed=ban_embed)

@bot.command(name="unbanplayer", aliases=["unban"])
@commands.check(is_admin_check)
async def unbanplayer_cmd(ctx, target: Union[discord.User, int] = None):
    """!!unbanplayer @user|ID — remove a player ban"""
    if not target:
        await ctx.send(embed=discord.Embed(
            title="❌ Missing User",
            description=f"Usage: `{PREFIX}unbanplayer @user ID`",
            color=COLORS["error"]
        ), delete_after=15)
        return
    user_id = target.id if isinstance(target, discord.User) else target
    ban_info = db.is_player_banned(ctx.guild.id, user_id)
    if not ban_info:
        await ctx.send(embed=discord.Embed(
            title="ℹ️ Player is not banned",
            description=f"<@{user_id}> is not banned.",
            color=COLORS["info"]
        ), delete_after=10)
        return
    db.unban_player(ctx.guild.id, user_id)
    db.clear_reports(ctx.guild.id, user_id)
    unban_embed = discord.Embed(
        title="✅ Player Unbanned",
        description=(
            "📊 \n"
            "🎮 Player can now play"
        ),
        color=COLORS["success"],
        timestamp=discord.utils.utcnow()
    )
    unban_embed.add_field(name="👤 Player", value=f"<@{user_id}>", inline=True)
    unban_embed.add_field(name="👮 Unbanned by", value=f"{ctx.author.mention}", inline=True)
    unban_embed.set_footer(text=f"{BOT_FOOTER}  •  Unbanned")
    unban_embed = apply_branding(unban_embed, ctx.guild)
    await ctx.send(embed=unban_embed)

@bot.command(name="banned")
@commands.check(is_admin_check)
async def banned_cmd(ctx):
    """!!banned — list banned players"""
    banned = db.get_banned_players(ctx.guild.id)
    embed = discord.Embed(
        title="📋 Banned Players",
        description=f"📊 **Total banned:** `{len(banned)}`",
        color=COLORS["error"] if banned else COLORS["success"],
        timestamp=discord.utils.utcnow()
    )
    embed.set_author(name="Banned Players", icon_url=None)
    if not banned:
        embed.description = "> ✅"
    else:
        for i, b in enumerate(banned[:15], 1):
            member = ctx.guild.get_member(b["user_id"])
            name = member.display_name if member else f"User#{b['user_id']}"
            mention = member.mention if member else f"<@{b['user_id']}>"
            reason = b.get("ban_reason") or ""
            report_count = b.get("report_count", 0)
            banned_at = b.get("banned_at", "N/A")[:19] if b.get("banned_at") else "N/A"
            embed.add_field(
                name=f"#{i} — {name}",
                value=f"👤 {mention}\n📝 `{reason}`\n📊 `{report_count}` reports · 📅 `{banned_at}`",
                inline=False
            )
        if len(banned) > 15:
            embed.set_footer(text=f"{BOT_FOOTER} • +{len(banned) - 15} more")
    # fix: apply_branding must always be applied, not only when banned players exceed 15
    embed = apply_branding(embed, ctx.guild)
    await ctx.send(embed=embed)

@bot.command(name="setreportchannel", aliases=["setreportch", "addreportch"])
@commands.check(is_admin_check)
async def setreportchannel_cmd(ctx, channel: discord.VoiceChannel = None):
    """!!setreportchannel #voice — set an investigation voice channel"""
    if not channel:
        await ctx.send(embed=discord.Embed(
            title="❌ Missing Voice Channel",
            description=(
                f"Usage: `{PREFIX}setreportchannel <#voice_channel>`\n"
                f": `{PREFIX}setreportchannel #Investigation-Room`\n"
                "💡 Must be an existing Voice Channel"
            ),
            color=COLORS["error"]
        ), delete_after=15)
        return
    # make sure it is a voice channel
    if not isinstance(channel, discord.VoiceChannel):
        await ctx.send(embed=discord.Embed(
            title="❌ Not a Voice Channel",
            description=(
                f"{channel.mention} is not a voice channel.\n"
                "Use a Voice Channel."
            ),
            color=COLORS["error"]
        ), delete_after=10)
        return
    added = db.add_report_channel(ctx.guild.id, channel.id)
    all_channels = db.get_report_channels(ctx.guild.id)
    channels_list = "\n".join([
        f"› {ctx.guild.get_channel(cid).mention} (`{cid}`)" if ctx.guild.get_channel(cid) else f"› ~~`{cid}`~~ (channel deleted)"
        for cid in all_channels
    ]) or "> *No voices set*"
    embed = discord.Embed(
        title="🎤 Investigation Voices",
        description=(
            f"🎤 {channel.mention}\n"
            + ("✅ **Voice added**\n" if added else "⚠️ **Already in the list**\n")
            + "\n"
            f"📊 **Total voices:** `{len(all_channels)}`\n"
            f"{channels_list}\n"
            "\n"
            "💡 Banned players will be moved to these voices automatically"
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
    """!!removereportchannel #voice — remove an investigation voice channel"""
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
        f"› {ctx.guild.get_channel(cid).mention} (`{cid}`)" if ctx.guild.get_channel(cid) else f"› ~~`{cid}`~~ (channel deleted)"
        for cid in all_channels
    ]) or "> *No voices left*"
    embed = discord.Embed(
        title="🗑️ Remove Investigation Voice",
        description=(
            f"🎤 {channel.mention}\n"
            + ("✅ **Voice removed**\n" if removed else "⚠️ **Not in the list**\n")
            + "\n"
            f"📊 **Remaining voices:** `{len(all_channels)}`\n"
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
    """!!reportchannels — list investigation voice channels"""
    all_channels = db.get_report_channels(ctx.guild.id)
    embed = discord.Embed(
        title="📋 Investigation Voice List",
        description=(
            f"📊 **Total voices:** `{len(all_channels)}`\n"
            + (f"⚠️ **No voices set** — use `{PREFIX}setreportchannel #voice`" if not all_channels else "")
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
                    name=f"#{i} — ⚠️ Deleted channel",
                    value=f"❌ Channel ID: `{cid}` (deleted)\n💡 Use `{PREFIX}removereportchannel`",
                    inline=False
                )
    embed.set_footer(text=f"{BOT_FOOTER}  •  Use !!setreportchannel to add")
    embed = apply_branding(embed, ctx.guild)
    await ctx.send(embed=embed)

# ============================================================
# 🆕 JAIL SYSTEM — jail system for cheaters
# ============================================================
# 🆕 JAIL system — definitions at the top of the file (lines 87-91)

# ✅ FIX: cache to speed up setup_jail_system — prevents re-scanning every channel in the server
# The cache is reset when the bot restarts or when the role goes missing
_jail_setup_done = set()  # set of guild.id where jail system is already configured
# Moved here so it works correctly with on_voice_state_update and on_message

async def setup_jail_system(guild):
    """Creates the JAIL role + a separate category + the two jail channels.
    FIX v2: the cache validates role + category + both channels (not just the role)."""
    if guild.id in _jail_setup_done:
        jail_role = discord.utils.get(guild.roles, name=JAIL_ROLE_NAME)
        jail_cat = discord.utils.get(guild.categories, name=JAIL_CATEGORY_NAME)
        jail_chat = discord.utils.get(guild.text_channels, name=JAIL_CHAT_NAME)
        jail_prouves = discord.utils.get(guild.text_channels, name=JAIL_PROUVES_NAME)
        if jail_role and jail_cat and jail_chat and jail_prouves:
            return jail_role
        _jail_setup_done.discard(guild.id)

    jail_role = discord.utils.get(guild.roles, name=JAIL_ROLE_NAME)
    if not jail_role:
        try:
            jail_role = await guild.create_role(
                name=JAIL_ROLE_NAME,
                color=discord.Color(0x36393F),
                permissions=discord.Permissions(
                    view_channel=True, send_messages=True,
                    read_messages=True, read_message_history=True,
                    attach_files=True, embed_links=True
                ),
                reason="Free Fire Bot — JAIL system"
            )
        except Exception as e:
            logger.warning(f"⚠️ JAIL role creation failed in {guild.name}: {e}")
            return None

    jail_cat = discord.utils.get(guild.categories, name=JAIL_CATEGORY_NAME)
    if not jail_cat:
        try:
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(view_channel=False),
                guild.me: discord.PermissionOverwrite(
                    view_channel=True, manage_channels=True,
                    manage_messages=True, move_members=True, connect=True
                ),
                jail_role: discord.PermissionOverwrite(view_channel=True)
            }
            for role in guild.roles:
                if role.permissions.administrator or role.permissions.manage_guild:
                    overwrites[role] = discord.PermissionOverwrite(
                        view_channel=True, manage_channels=True,
                        manage_messages=True, move_members=True, connect=True
                    )
            jail_cat = await guild.create_category(
                JAIL_CATEGORY_NAME, overwrites=overwrites, reason="JAIL system"
            )
            logger.info(f"🔒 Created JAIL category in {guild.name}")
        except Exception as e:
            logger.warning(f"⚠️ JAIL category creation failed in {guild.name}: {e}")
            jail_cat = None  # no fallback to an unrelated category

    if jail_cat is None:
        logger.warning(f"⚠️ Skipping JAIL channel creation in {guild.name} — no category")
    else:
        for ch_name, perms in [(JAIL_CHAT_NAME, True), (JAIL_PROUVES_NAME, True)]:
            if not discord.utils.get(guild.text_channels, name=ch_name):
                try:
                    overwrites = {
                        guild.default_role: discord.PermissionOverwrite(view_channel=False),
                        guild.me: discord.PermissionOverwrite(
                            view_channel=True, send_messages=True, manage_messages=True
                        ),
                        jail_role: discord.PermissionOverwrite(
                            view_channel=True, send_messages=True,
                            read_message_history=True, attach_files=perms
                        )
                    }
                    for role in guild.roles:
                        if role.permissions.administrator or role.permissions.manage_guild:
                            overwrites[role] = discord.PermissionOverwrite(
                                view_channel=True, send_messages=True, manage_messages=True
                            )
                    await guild.create_text_channel(
                        ch_name, category=jail_cat,
                        topic=f"JAIL — {ch_name}", overwrites=overwrites
                    )
                    logger.info(f"🔒 Created JAIL channel #{ch_name} in {guild.name}")
                except Exception as e:
                    logger.warning(f"⚠️ Failed to create JAIL channel #{ch_name} in {guild.name}: {e}")

    for ch in guild.text_channels:
        if ch.name in [JAIL_CHAT_NAME, JAIL_PROUVES_NAME] or ch.name == "🛡️ Rules":
            continue
        try:
            overwrite = ch.overwrites_for(jail_role)
            overwrite.view_channel = False
            overwrite.send_messages = False
            await ch.set_permissions(jail_role, overwrite=overwrite, reason="JAIL system")
        except Exception:
            pass

    for ch in guild.voice_channels:
        if ch.category and ch.category.name == JAIL_CATEGORY_NAME:
            continue
        try:
            overwrite = ch.overwrites_for(jail_role)
            overwrite.view_channel = False
            overwrite.connect = False
            overwrite.speak = False
            await ch.set_permissions(jail_role, overwrite=overwrite, reason="JAIL system")
        except Exception:
            pass

    # Persist the "setup done" marker (skips heavy re-setup on later calls)
    try:
        db.set_guild_setting(guild.id, "jail_setup_done", 1)
        logger.info(f"✅ setup_jail_system: marked done for guild {guild.id}")
    except Exception as e:
        logger.warning(f"⚠️ Failed to mark jail_setup_done: {e}")
    _jail_setup_done.add(guild.id)
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
    """!!jail <@user|ID> [reason] — send a player to JAIL (role + jail channels)"""
    if not target:
        await ctx.send(embed=discord.Embed(
            title="❌ Missing User",
            description=f"Usage: `{PREFIX}jail <@user|ID> [reason]`",
            color=COLORS["error"]
        ), delete_after=15); return
    user_id = target.id if isinstance(target, discord.Member) else target
    member = target if isinstance(target, discord.Member) else ctx.guild.get_member(user_id)
    if not member:
        await ctx.send(embed=discord.Embed(
            title="❌ Player not in server",
            description=f"<@{user_id}> is not a member of this server.",
            color=COLORS["error"]
        ), delete_after=10)
        return
    if member.bot: await ctx.send("❌ Cannot jail a bot!", delete_after=10); return
    jail_role = await setup_jail_system(ctx.guild)
    if not jail_role: await ctx.send("❌ Failed to create jail system!", delete_after=10); return
    try: await member.add_roles(jail_role, reason=f"Jailed by {ctx.author.name}: {reason or 'No reason'}")
    except Exception as e: await ctx.send(f"❌ Failed to assign role! ({e})", delete_after=15); return
    jail_cat = discord.utils.get(ctx.guild.categories, name=JAIL_CATEGORY_NAME)
    jail_voice = None
    if jail_cat:
        jail_voice = await create_jail_voice_for_player(ctx.guild, member, jail_role, jail_cat)
        if jail_voice and member.voice and member.voice.channel:
            try: await member.move_to(jail_voice)
            except: pass
    jail_embed = discord.Embed(
        title="🔒 Player sent to jail",
        description=(
            "🔒 Player is now in jail\n"
            f"💬 Can chat in `{JAIL_CHAT_NAME}` and `{JAIL_PROUVES_NAME}`\n"
            + (f"🎤 Jail voice: `{jail_voice.name}`\n" if jail_voice else "")
            + f"✅ To release: `{PREFIX}unjail @user`"
        ),
        color=COLORS["error"],
        timestamp=discord.utils.utcnow()
    )
    jail_embed.add_field(name="👤 Player", value=f"{member.mention}", inline=True)
    jail_embed.add_field(name="👮 Jailed by", value=f"{ctx.author.mention}", inline=True)
    if reason:
        jail_embed.add_field(name="📝 Reason", value=f"`{reason}`", inline=False)
    jail_embed.set_author(name="JAIL System")
    jail_embed.set_footer(text=f"{BOT_FOOTER}  •  Jailed")
    jail_embed = apply_branding(jail_embed, ctx.guild)
    await ctx.send(embed=jail_embed)
    jail_chat = discord.utils.get(ctx.guild.text_channels, name=JAIL_CHAT_NAME)
    if jail_chat:
        try:
            welcome = discord.Embed(
                title="🔒 Welcome to jail",
                description=(
                    f"{member.mention} you have been jailed.\n"
                    + (f"📝 **Reason:** {reason}\n" if reason else "")
                    + "\n"
                    "💬 You can only chat here\n"
                    f"📸 Upload your proofs in `#{JAIL_PROUVES_NAME}`\n"
                    "⏳ Wait for admin decision"
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
    """!!unjail <@user|ID> — release a player from JAIL"""
    if not target:
        await ctx.send(embed=discord.Embed(
            title="❌ Missing User",
            description=f"Usage: `{PREFIX}unjail <@user ID>`",
            color=COLORS["error"]
        ), delete_after=15); return
    user_id = target.id if isinstance(target, discord.Member) else target
    member = target if isinstance(target, discord.Member) else ctx.guild.get_member(user_id)
    if not member:
        await ctx.send(embed=discord.Embed(
            title="ℹ️ Player not found",
            description=f"<@{user_id}> is not in the server.",
            color=COLORS["info"]
        ), delete_after=10); return
    jail_role = discord.utils.get(ctx.guild.roles, name=JAIL_ROLE_NAME)
    if not jail_role: await ctx.send("❌ Jail system not enabled!", delete_after=10); return
    if jail_role not in member.roles: await ctx.send(f"ℹ️ {member.mention} is not in jail!", delete_after=10); return
    try: await member.remove_roles(jail_role, reason=f"Unjailed by {ctx.author.name}")
    except Exception as e: await ctx.send(f"❌ role! ({e})", delete_after=15); return
    await delete_jail_voice_for_player(ctx.guild, member)
    unjail_embed = discord.Embed(
        title="✅ Released from jail",
        description="🎮 Player is now free",
        color=COLORS["success"],
        timestamp=discord.utils.utcnow()
    )
    unjail_embed.add_field(name="👤 Player", value=f"{member.mention}", inline=True)
    unjail_embed.add_field(name="👮 Released by", value=f"{ctx.author.mention}", inline=True)
    unjail_embed.set_author(name="JAIL System")
    unjail_embed.set_footer(text=f"{BOT_FOOTER}  •  Released")
    unjail_embed = apply_branding(unjail_embed, ctx.guild)
    await ctx.send(embed=unjail_embed)

# ============================================================
# 🆕 BLACKLIST SYSTEM — Blacklist System
# ============================================================

async def setup_blacklist_role(guild):
    """🆕 Creates blacklist role if it doesn't exist.
✅ P1: guild_permissions.cache ( )."""
    role = discord.utils.get(guild.roles, name=BLACKLIST_ROLE_NAME)
    if not role:
        try:
            role = await guild.create_role(
                name=BLACKLIST_ROLE_NAME,
                color=discord.Color(0x2C3E50),
                reason="Free Fire Bot — Blacklist system"
            )
            # P1: record that the role was created (for quick reuse)
            try:
                db.set_guild_setting(guild.id, "blacklist_setup_done", 1)
            except Exception:
                pass
        except:
            return None
    return role

async def apply_blacklist(guild, member, reason=None):
    """🆕 Applies blacklist to player: gives role + logs in DB + starts 5-min timer.
✅ P1: tracking ( !!blacklist)."""
    if not member or member.bot:
        return False
    role = await setup_blacklist_role(guild)
    if not role:
        return False
    # clear any old timer for this player
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
    # start a timer for automatic removal after BLACKLIST_DURATION seconds
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
    # P1: reset tracking for this player (fixes the manual !!blacklist not touching tracking)
    try:
        track = _blacklist_voice_tracking.get(guild.id, {})
        if member.id in track:
            # cancel the pending reset_task
            reset_task = track[member.id].get("reset_task")
            if reset_task and not reset_task.done():
                reset_task.cancel()
            track.pop(member.id, None)
            logger.info(f"🔇 BLACKLIST: cleared tracking for {member.display_name} (manual or auto)")
    except Exception:
        pass
    # notify the admin
    await notify_admins(
        guild,
        "🔇 Blacklist Applied",
        f"> 👤 **Player:** {member.mention}\n"
        f"> 📝  **Reason:**  {reason or 'N/A'}\n"
        f"> ⏱️  **Duration:**  5 minutes\n"
        f"> 🔇  Bot access blocked for 5 minutes",
        color=COLORS["warning"]
    )
    # update the blacklist channel after applying
    try:
        await update_blacklist_channel(guild)
    except Exception as e:
        logger.warning(f"update_blacklist_channel (apply) failed: {e}")
    return True

async def remove_blacklist(guild, member):
    """🆕 Removes blacklist from player: removes role + deletes from DB + cancels timer."""
    if not member or member.bot:
        return
    role = discord.utils.get(guild.roles, name=BLACKLIST_ROLE_NAME)
    if role and role in member.roles:
        try:
            await member.remove_roles(role, reason="Blacklist expired / removed by admin")
        except:
            pass
    db.remove_blacklist(guild.id, member.id)
    # cancel the timer if it exists
    timers = _blacklist_auto_remove_timers.get(guild.id, {})
    timer = timers.pop(member.id, None)
    if timer and not timer.done():
        timer.cancel()
    # update the blacklist channel after removal
    try:
        await update_blacklist_channel(guild)
    except Exception as e:
        logger.warning(f"update_blacklist_channel (remove) failed: {e}")

def is_blacklisted_check(ctx):
    """🆕 — ."""
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
    """!!blacklist @user|ID [reason] — manually blacklist a player"""
    if not target:
        await ctx.send(embed=discord.Embed(
            title="❌ Missing User",
            description=f"Usage: `{PREFIX}blacklist @user ID [reason]`",
            color=COLORS["error"]
        ), delete_after=15)
        return
    user_id = target.id if isinstance(target, discord.Member) else target
    if user_id == ctx.author.id:
        await ctx.send("❌ You cannot blacklist yourself!", delete_after=10)
        return
    member = target if isinstance(target, discord.Member) else ctx.guild.get_member(user_id)
    if member and member.bot:
        await ctx.send("❌ You cannot blacklist a bot!", delete_after=10)
        return
    if member:
        success = await apply_blacklist(ctx.guild, member, reason=reason)
    else:
        db.blacklist_player(ctx.guild.id, user_id, reason=reason or "Manual blacklist by admin")
        success = True
    if not success:
        await ctx.send(embed=discord.Embed(
            title="❌ Failed",
            description="Could not apply the blacklist.",
            color=COLORS["error"]
        ), delete_after=10)
        return
    embed = discord.Embed(
        title="🔇 Player added to blacklist",
        color=COLORS["warning"],
        timestamp=discord.utils.utcnow()
    )
    embed.add_field(name="👤 Player", value=f"<@{user_id}>", inline=True)
    embed.add_field(name="👮 By", value=f"{ctx.author.mention}", inline=True)
    embed.add_field(name="⏱️ Duration", value=f"`{BLACKLIST_DURATION // 60}` minutes", inline=True)
    if reason:
        embed.add_field(name="📝 Reason", value=f"`{reason}`", inline=False)
    embed.set_footer(text=f"{BOT_FOOTER}  •  Blacklisted")
    embed = apply_branding(embed, ctx.guild)
    await ctx.send(embed=embed)
    # update the list in the blacklist channel
    try:
        await update_blacklist_channel(ctx.guild)
    except Exception as e:
        logger.warning(f"update_blacklist_channel (blacklist_cmd) failed: {e}")

@bot.command(name="unblacklist", aliases=["ubl", "removebl"])
@commands.check(is_admin_check)
async def unblacklist_cmd(ctx, target: Union[discord.User, int] = None):
    """!!unblacklist @user|ID — remove a player from the blacklist"""
    if not target:
        await ctx.send(embed=discord.Embed(
            title="❌ Missing User",
            description=f"Usage: `{PREFIX}unblacklist @user ID`",
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
        title="✅ Blacklist removed",
        description="🎮 The player can use the bot again.",
        color=COLORS["success"],
        timestamp=discord.utils.utcnow()
    )
    embed.add_field(name="👤 Player", value=f"<@{user_id}>", inline=True)
    embed.add_field(name="👮 By", value=f"{ctx.author.mention}", inline=True)
    embed.set_footer(text=f"{BOT_FOOTER}  •  Unblacklisted")
    embed = apply_branding(embed, ctx.guild)
    await ctx.send(embed=embed)
    # update the list in the blacklist channel
    try:
        await update_blacklist_channel(ctx.guild)
    except Exception as e:
        logger.warning(f"update_blacklist_channel (unblacklist_cmd) failed: {e}")

@bot.command(name="blacklisted", aliases=["bllist", "blacklistlist"])
@commands.check(is_admin_check)
async def blacklisted_cmd(ctx):
    """!!blacklisted — list currently blacklisted players"""
    blacklisted = db.get_blacklisted_players(ctx.guild.id)
    embed = discord.Embed(
        title="📋 Blacklist List",
        description=f"📊 **Total:** `{len(blacklisted)}`",
        color=COLORS["warning"] if blacklisted else COLORS["success"],
        timestamp=discord.utils.utcnow()
    )
    embed.set_author(name="Blacklisted Players")
    if not blacklisted:
        embed.description = "> ✅"
    else:
        for i, b in enumerate(blacklisted[:15], 1):
            member = ctx.guild.get_member(b["user_id"])
            name = member.display_name if member else f"User#{b['user_id']}"
            mention = member.mention if member else f"<@{b['user_id']}>"
            reason = b.get("reason") or ""
            expires = b.get("expires_at", "N/A")[:19] if b.get("expires_at") else "N/A"
            embed.add_field(
                name=f"#{i} — {name}",
                value=f"👤 {mention}\n📝 `{reason}`\n⏱️ Expires: `{expires}`",
                inline=False
            )
        if len(blacklisted) > 15:
            embed.set_footer(text=f"{BOT_FOOTER} • +{len(blacklisted) - 15} more")
    embed = apply_branding(embed, ctx.guild)
    await ctx.send(embed=embed)

@bot.command(name="rules")
async def rules_cmd(ctx):
    """!!rules — post the server rules"""
    # same function used in  !!setup  and  !!autosetup  - single source for the text
    rules_embed = build_rules_embed(ctx.guild.name)
    await ctx.send(embed=rules_embed)

@bot.command(name="w")
@commands.check(is_admin_check)
async def winner_mvp_cmd(ctx, lobby_id: int = None, target: Union[discord.User, int] = None):
    """🏆 !!w <lobby_id> <@user/ID> — MVP WINNER"""
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
            description=f"Lobby `#{lobby_id}` is not in a started or voting state.",
            color=COLORS["error"]
        ))
        return
    all_players = lobby["team1_players"] + lobby["team2_players"]
    if user_id not in all_players:
        await ctx.send(embed=discord.Embed(
            title="❌ Player not in this match",
            description=f"<@{user_id}> is not a player in this match.",
            color=COLORS["error"]
        ))
        return
    if lobby_id not in _admin_mvp_results:
        _admin_mvp_results[lobby_id] = {}
    _admin_mvp_results[lobby_id]["winner"] = user_id
    await ctx.send(embed=discord.Embed(
        title="✅ MVP WINNER set",
        description=(
            f"🏆 **MVP WINNER:** <@{user_id}>\n"
            f"📌 **Lobby:** `#{lobby_id}`"
        ),
        color=COLORS["success"]
    ))
    # if the loser is already set - apply the result
    if _admin_mvp_results[lobby_id].get("loser"):
        await _apply_admin_mvp(ctx, lobby_id)

@bot.command(name="l")
@commands.check(is_admin_check)
async def loser_mvp_cmd(ctx, lobby_id: int = None, target: Union[discord.User, int] = None):
    """✦ !!l <lobby_id> <@user/ID> — MVP LOSER"""
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
            description=f"Lobby `#{lobby_id}` is not in a started or voting state.",
            color=COLORS["error"]
        ))
        return
    all_players = lobby["team1_players"] + lobby["team2_players"]
    if user_id not in all_players:
        await ctx.send(embed=discord.Embed(
            title="❌ Player not in this match",
            description=f"<@{user_id}> is not a player in this match.",
            color=COLORS["error"]
        ))
        return
    if lobby_id not in _admin_mvp_results:
        _admin_mvp_results[lobby_id] = {}
    _admin_mvp_results[lobby_id]["loser"] = user_id
    await ctx.send(embed=discord.Embed(
        title="✅ MVP LOSER set",
        description=(
            f"✦ **MVP LOSER:** <@{user_id}>\n"
            f"📌 **Lobby:** `#{lobby_id}`"
        ),
        color=COLORS["success"]
    ))
    # if the winner is already set - apply the result
    if _admin_mvp_results[lobby_id].get("winner"):
        await _apply_admin_mvp(ctx, lobby_id)

async def _apply_admin_mvp(ctx, lobby_id):
    """Applies result from !!w and !!l after both are set.
✅ : Doesn't update status before process_match_result_with_mvps."""
    data = _admin_mvp_results.get(lobby_id)
    if not data or not data.get("winner") or not data.get("loser"):
        return
    winner_id = data["winner"]
    loser_id = data["loser"]
    lobby = db.get_lobby(lobby_id)
    if not lobby:
        return
    # check that they are not on the same team
    w_team = "team1" if winner_id in lobby["team1_players"] else "team2"
    l_team = "team1" if loser_id in lobby["team1_players"] else "team2"
    if w_team == l_team:
        await ctx.send(embed=discord.Embed(
            title="❌ MVP from same team!",
            description="The MVP WINNER and the MVP LOSER must come from different teams.",
            color=COLORS["error"]
        ))
        _admin_mvp_results.pop(lobby_id, None)
        return
    await ctx.send(embed=discord.Embed(
        title="⚙️ Applying points...",
        description=(
            f"🏆 **Winner Team:** {w_team}\n"
            f"🔱 **MVP WINNER:** <@{winner_id}>\n"
            f"✦ **MVP LOSER:** <@{loser_id}>"
        ),
        color=COLORS["warning"]
    ))
    guild = ctx.guild
    # fix: do not update the state here - process_match_result_with_mvps does that
    # if we updated it here, process_match_result_with_mvps would see "completed" and return!
    _admin_mvp_results.pop(lobby_id, None)
    try:
        await process_match_result_with_mvps(
            guild, lobby_id, w_team,
            winner_id, loser_id,
            ctx.channel
        )
    except Exception as e:
        logger.exception(f"❌ _apply_admin_mvp failed: {e}")
        # so that even on failure - the match ends
        try:
            db.update_lobby_status(lobby_id, "completed")
            _original_voice_channels.pop(lobby_id, None)
            await delete_match_channels(guild, lobby_id)
            cleanup_lobby_memory(lobby_id)
        except:
            pass
        await ctx.send(embed=discord.Embed(
            title="❌ Failed",
            description=(
                f"🐛 **Error:** `{str(e)[:200]}`\n"
                "✅ Match ended and channels deleted"
            ),
            color=COLORS["error"]
        ))

@bot.command(name="startvote", aliases=["forcevote", "sv"])
@commands.check(is_admin_check)
async def startvote_cmd(ctx, lobby_id: int = None):
    """🗳️ !!startvote <lobby_id> — Start vote immediately (Admin only)
bypasses cooldown 10 minutes."""
    if lobby_id is None:
        # look for the player's active match
        lobby = db.get_active_lobby_by_guild(ctx.guild.id)
        if lobby:
            lobby_id = lobby["id"]
        else:
            await ctx.send(embed=discord.Embed(
                title="❌ Missing Lobby ID",
                description=(
                    f"Usage: `{PREFIX}startvote <lobby_id>`\n"
                    f"`{PREFIX}startvote` \n"
                    f"💡 Use `{PREFIX}matches`"
                ),
                color=COLORS["error"]
            ), delete_after=15)
            return
    lobby = db.get_lobby(lobby_id)
    if not lobby:
        await ctx.send(embed=discord.Embed(
            title="❌ Not Found",
            description=f"Lobby `#{lobby_id}` was not found.",
            color=COLORS["error"]
        ), delete_after=10)
        return
    if lobby["status"] != "started":
        await ctx.send(embed=discord.Embed(
            title="❌ Not Active",
            description=(
                f"Lobby `#{lobby_id}` status: `{lobby['status']}`\n"
                "Must be `started`"
            ),
            color=COLORS["error"]
        ), delete_after=10)
        return
    guild = ctx.guild
    # start the vote immediately without a cooldown
    embed = discord.Embed(
        title="🗳️ Vote started!",
        description=(
            "⚡ Started without the 10-minute cooldown\n"
            "🗳️ Host and first joiner can now vote!"
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
            description=f"Usage: `{PREFIX}resetstats @user ID`",
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

# reset ranks + points of all server members to zero
@bot.command(name="resetrankall", aliases=["forceresetrankall", "resetallranks"])
@commands.check(is_admin_check)
async def resetrankall_cmd(ctx):
    """!!resetrankall — reset ranks and points of all members"""
    guild = ctx.guild
    # fix: build the progress embed as a variable correctly
    progress_embed = discord.Embed(
        title="🚀 Resetting points and ranks...",
        description=(
            "💰 **Points:** reset to `0`\n"
            f"🏅 **Rank:** `#{STARTING_LEVEL}` (points = 0)\n"
            "⏳ **Please wait...**"
        ),
        color=COLORS["warning"],
        timestamp=discord.utils.utcnow()
    )
    progress_embed.add_field(name="📊 Members", value=f"`{len(guild.members)}`", inline=False)
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
            # create the player if they do not exist
            db.get_or_create_player(member.id, guild.id, member.display_name)
            # reset points + ranks together
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
            # update the nickname
            await update_member_nickname(member, STARTING_LEVEL)
            reset_count += 1
            await asyncio.sleep(0.3)
        except Exception as e:
            logger.warning(f"resetrankall: failed for {member.id}: {e}")
            failed += 1
    # fix: build the success embed as a variable correctly
    success_embed = discord.Embed(
        title="✅ All data reset!",
        description=(
            f"🏅 `RANK #{STARTING_LEVEL}` ( = 0)\n"
            "💡 All stats (points/wins/losses/MVPs) also reset"
        ),
        color=COLORS["success"],
        timestamp=discord.utils.utcnow()
    )
    success_embed.add_field(name="✅ Players reset", value=f"`{reset_count}`", inline=True)
    success_embed.add_field(name="🤖 Bots skipped", value=f"`{skipped_bots}`", inline=True)
    success_embed.add_field(name="⚠️ Failed", value=f"`{failed}`", inline=True)
    success_embed.set_footer(text=f"{BOT_FOOTER}  •  Reset complete")
    success_embed = apply_branding(success_embed, ctx.guild)
    # V5 fix: remove the roles after the reset (they used to lag until the periodic sync)
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
            description=f"Usage: `{PREFIX}setlevel @user ID <level>`",
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
        # V5 fix: remove the role after setting ranks manually
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
            description=f"Usage: `{PREFIX}setpoints @user ID <points>`",
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
    """🔄 !!syncroles — Roles"""
    progress = await ctx.send(embed=discord.Embed(
        title="🔄 Syncing roles...",
        description=(
            "📊 ...\n"
            "⏳ Please wait..."
        ),
        color=COLORS["warning"],
        timestamp=discord.utils.utcnow()
    ))
    # recalculate ranks first
    db.recalculate_ranks(ctx.guild.id)
    # removes the roles
    await sync_all_players_roles(ctx.guild)
    # fix: build the success embed as a variable correctly
    synced_embed = discord.Embed(
        title="✅ Roles synced!",
        description="🔄 All player roles have been updated.",
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
    embed.add_field(name="🚀 Play", value=f"• `{PREFIX}play 4v4` `{PREFIX}play4v4` — 4v4 (default)\n• `{PREFIX}play 2v2` `{PREFIX}play2v2` — 2v2\n• `{PREFIX}play 3v3` `{PREFIX}play3v3` — 3v3\n• `{PREFIX}play 1v1` `{PREFIX}play1v1` 🔒 (high roles only)\n• ⚠️ `{PREFIX}play` → shows the mode list", inline=False)
    embed.add_field(name="📊 Stats", value=f"• `{PREFIX}p` — Profile (full stats)\n• `{PREFIX}points` — 💰 Points + progress to #1\n• `{PREFIX}card` — Card (zelika-play)\n• `{PREFIX}top` — Leaderboard (Top 10)\n• `{PREFIX}mylevel` — Your rank\n• `{PREFIX}matches` — Active lobbies", inline=False)
    embed.add_field(name="🎮 Control", value=f"• `{PREFIX}leave` — Leave lobby\n• `{PREFIX}fixrank` — Apply rank", inline=False)
    embed.add_field(name="🤖 How to Play", value=f"1️⃣ Join a ⏳ waiting room\n2️⃣ `{PREFIX}play 4v4` in a play channel (you become the host)\n3️⃣ Press **Create Lobby** → Enter Room Info\n4️⃣ Players press **Join Team 1 / 2**\n5️⃣ Lobby fills → Match starts\n6️⃣ Host presses **Start Vote** (or **Cancel Match** to abort)\n7️⃣ Vote → Result → Points + RANK updates\n8️⃣ Players return to waiting rooms", inline=False)
    embed.add_field(name="💰 Points System", value="🔱 Winner MVP: `+80` pts\n✅ Winners: `+30` pts\n✦ Loser MVP: `+30` pts\n☠️ Losers: `-30` pts\n📈 Every `50` pts = `+1` rank", inline=False)
    embed.set_footer(text=f"{BOT_FOOTER}  •  v4.0  ·  {PREFIX}help (admin)")
    embed = apply_branding(embed, ctx.guild)
    await ctx.send(embed=embed)

@bot.command(name="help")
async def help_cmd(ctx):
    # 📄 Message 1: Player Commands
    embed1 = discord.Embed(
        title="🔥 Free Fire Bot v4.0 — Player Commands",
        description=(
            f"📌 **Prefix:** `{PREFIX}`\n"
            "🎮 All commands work in play channels"
        ),
        color=COLORS["play"],
        timestamp=discord.utils.utcnow()
    )
    embed1.add_field(name="🎮 Play (9 commands)", value=f"• `{PREFIX}play 4v4` `{PREFIX}play4v4` — 4v4\n• `{PREFIX}play 3v3` `{PREFIX}play3v3` — 3v3\n• `{PREFIX}play 2v2` `{PREFIX}play2v2` — 2v2\n• `{PREFIX}play 1v1` `{PREFIX}play1v1` 🔒 (high roles only)\n• `{PREFIX}play` — shows the mode list\n• `{PREFIX}leave` — leave your lobby\n• `{PREFIX}matches` — list active lobbies\n• `{PREFIX}matchinfo <id>` — lobby details", inline=False)
    embed1.add_field(name="📊 Stats (7 commands)", value=f"• `{PREFIX}p` `{PREFIX}p @user` — full profile\n• `{PREFIX}points` `{PREFIX}points @user` — points + progress to #1\n• `{PREFIX}card` `{PREFIX}card @user` — profile card\n• `{PREFIX}top` — Leaderboard Top 10\n• `{PREFIX}mylevel` `{PREFIX}mylevel @user` — rank level\n• `{PREFIX}myrank` — rank position\n• `{PREFIX}fixrank` `{PREFIX}fixrank @user` — fix rank role and nickname", inline=False)
    embed1.add_field(name="⚠️ Reports (3 commands)", value=f"• `{PREFIX}report @user [reason]` — report a player (6 reports = auto-ban)\n• `{PREFIX}reports` `{PREFIX}reports @user` — show reports against a player\n• ⚠️ Use the Report button inside a match", inline=False)
    embed1.add_field(name="🛡️ Info (4 commands)", value=f"• `{PREFIX}rules` — server rules (read-only)\n• `{PREFIX}general` — player command list\n• `{PREFIX}help` — all commands\n• `{PREFIX}botinfo` — bot information", inline=False)
    embed1.set_footer(text=f"{BOT_FOOTER} • 1/2 · Player commands")
    embed1 = apply_branding(embed1, ctx.guild)
    await ctx.send(embed=embed1)

    # 📄 Message 2: Admin Commands
    embed2 = discord.Embed(
        title="🔧 Free Fire Bot v4.0 — Admin Commands",
        description=(
            f"📌 **Prefix:** `{PREFIX}`\n"
            "🔒 All following commands are admin-only"
        ),
        color=COLORS["admin"],
        timestamp=discord.utils.utcnow()
    )
    embed2.add_field(name="🔧 Setup (8 commands)", value=f"• `{PREFIX}setup` — create channels + Roles + JAIL\n• `{PREFIX}autosetup` — auto-detect existing channels\n• `{PREFIX}cleanup` — delete leftover match categories\n• `{PREFIX}scan [page]` — list categories and channels\n• `{PREFIX}deletecat <name>` — request category deletion\n• `{PREFIX}confirmcat <name>` — confirm category deletion\n• `{PREFIX}setcommandschannel #ch` — add/remove a commands channel\n• `{PREFIX}setleaderboard` — set the Leaderboard channel", inline=False)
    embed2.add_field(name="🏅 Roles (8 commands)", value=f"• `{PREFIX}fixrankall` — apply ranks to all members\n• `{PREFIX}syncnicknames` — sync nicknames\n• `{PREFIX}syncroles` — sync rank Roles\n• `{PREFIX}setlevel @user/ID <n>` — set a player's rank level\n• `{PREFIX}setpoints @user/ID <n>` — set a player's points\n• `{PREFIX}resetstats @user/ID` — reset a player's stats\n• `{PREFIX}resetrankall` — reset ranks and points for everyone", inline=False)
    embed2.add_field(name="⚠️ Reports & Bans (5 commands)", value=f"• `{PREFIX}banplayer @user/ID [reason]` — ban + investigation voice\n• `{PREFIX}unbanplayer @user/ID` — remove a ban\n• `{PREFIX}banned` — list banned players\n• `{PREFIX}setreportchannel #voice` — add an investigation voice\n• `{PREFIX}removereportchannel #voice` — remove an investigation voice", inline=False)
    embed2.add_field(name="🔒 JAIL System (2 commands)", value=f"• `{PREFIX}jail @user/ID [reason]` — role + private voice + chat\n• `{PREFIX}unjail @user/ID` — release a player", inline=False)
    embed2.add_field(name="🔇 Blacklist System (3 commands)", value=f"• `{PREFIX}blacklist @user/ID [reason]` — blacklist a player\n• `{PREFIX}unblacklist @user/ID` — remove from the blacklist\n• `{PREFIX}blacklisted` — list blacklisted players", inline=False)
    embed2.add_field(name="📋 Additional Info (6 commands)", value=f"• `{PREFIX}reportchannels` — list investigation voices\n• `{PREFIX}startvote [id]` — 🗳️ start the vote now (skips the 10-minute cooldown)\n• `{PREFIX}resolve <id> <team1|team2>` — decide the winner manually\n• `{PREFIX}w <id> <@user/ID>` — set MVP WINNER\n• `{PREFIX}l <id> <@user/ID>` — set MVP LOSER\n• `{PREFIX}botinfo` — bot information", inline=False)
    embed2.add_field(name="💡 System Info", value=f"💰 **Points:** +80 MVP · +30 Winner · +30 MVP Loser · -30 Loser\n🏅 **Rank:** Leaderboard order (1 = best)\n🗳️ **Vote:** All players · 50%+1 · Vote from each team\n🚨 **Disputes:** no consensus → an admin is tagged\n🏆 **Roles:** Best · Goated · Skilled · Efficient\n⚠️ **6 reports = auto-ban**\n🔒 **JAIL:** Private voice + chat\n🔇 **Blacklist:** 5min leave / 8 leaves = 5min ban\n🛡️ **Rules:** `{RULES_CHANNEL_NAME}` (read-only)", inline=False)
    embed2.set_footer(text=f"{BOT_FOOTER} • 2/2 · v4.0 · 55 commands")
    embed2 = apply_branding(embed2, ctx.guild)
    await ctx.send(embed=embed2)

@bot.command(name="cloudbackup")
@commands.is_owner()
async def cloudbackup_cmd(ctx):
    """Cloud command (owner/admin): see cloud_backup.py."""
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
    """Restore the local database from the cloud (owner only)."""
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
    """Cloud command (owner/admin): see cloud_backup.py."""
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
    """!!serverleave — owner-only: list servers and leave one (works in DM)."""
    # only in the DM
    if ctx.guild is not None:
        await ctx.send("❌ This command works in DMs only!")
        return
    # bot owner only
    if ctx.author.id != BOT_OWNER_ID:
        await ctx.send("❌ This command is for the bot owner only!")
        return
    # check permissions
    args = ctx.message.content.split()
    if len(args) < 2:
        # show the list of servers
        if not bot.guilds:
            await ctx.send("The bot is not in any server.")
            return
        msg = "**Servers the bot is in:**\n\n"
        for i, g in enumerate(bot.guilds, 1):
            msg += f"`{i}`. **{g.name}** (ID: `{g.id}`) — {g.member_count} members\n"
        msg += f"\nTo leave a server: `!!serverleave <ID>`."
        await ctx.send(msg)
        return
    # try to leave the server
    try:
        guild_id = int(args[1])
    except ValueError:
        await ctx.send("❌ Invalid ID. Enter the numeric server ID.")
        return
    guild = bot.get_guild(guild_id)
    if not guild:
        await ctx.send(f"❌ No server found with ID `{guild_id}`.")
        return
    try:
        await guild.leave()
        await ctx.send(f"✅ Left **{guild.name}** successfully!")
        logger.info(f"🔓 Owner left server: {guild.name} ({guild.id})")
    except Exception as e:
        await ctx.send(f"❌ Failed to leave the server: {e}")

# ============================================================
# RUN
# ============================================================
def _start_health_server():
    """🆕 FIX (Railway/Render): Bot is not a web service, but Procfile says `web:` —
PORT
( «autosetup » on_ready).
200 . PORT ."""
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
    # The token is read only from the DISCORD_TOKEN environment variable (never hard-code it).
    TOKEN = os.getenv("DISCORD_TOKEN")
    if not TOKEN:
        raise RuntimeError("❌ DISCORD_TOKEN environment variable is required! Set it on Railway/Render.")
    _start_health_server()
    logger.info("🚀 Starting Free Fire Bot v4.0 CLEAN...")
    bot.run(TOKEN)
