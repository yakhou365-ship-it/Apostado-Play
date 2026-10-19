"""
===========================================================
  ☁️ Cloud Backup — MongoDB Atlas Sync Layer
===========================================================
  يحفظ بيانات اللاعبين (نقاط، رانك، إحصائيات) في MongoDB Atlas
  بحيث تبقى البيانات محفوظة حتى لو عملت deploy جديد

  الاستخدام:
  1. أنشئ حساب في MongoDB Atlas (مجاني)
  2. أنشئ Cluster واطلب Connection String
  3. ضع Connection String في متغير البيئة MONGODB_URI
  4. البوت سيتزامن تلقائياً
===========================================================
"""

import os
import json
import logging
from datetime import datetime
from typing import Optional, Dict, List, Any

logger = logging.getLogger("freefire.cloud")

# ============================================================
# MongoDB Connection
# ============================================================
_client = None
_db = None


def _get_mongo_uri():
    """يرجع رابط MongoDB من متغير البيئة."""
    return os.getenv("MONGODB_URI", "")


def is_cloud_enabled():
    """يرجع True لو MongoDB مفعّل (موجود MONGODB_URI)."""
    return bool(_get_mongo_uri())


def _get_client():
    """يرجع MongoDB client (singleton)."""
    global _client, _db
    if _client is not None:
        return _client, _db
    
    uri = _get_mongo_uri()
    if not uri:
        return None, None
    
    try:
        from pymongo import MongoClient
        from pymongo.server_api import ServerApi
        
        _client = MongoClient(uri, server_api=ServerApi('1'),
                             connectTimeoutMS=10000, serverSelectionTimeoutMS=10000)
        # اختبار الاتصال
        _client.admin.command('ping')
        _db = _client.get_database("freefire_bot")
        logger.info("☁️ Connected to MongoDB Atlas successfully!")
        return _client, _db
    except Exception as e:
        logger.warning(f"☁️ MongoDB connection failed: {e}")
        _client = None
        _db = None
        return None, None


def _get_collection(name: str):
    """يرجع MongoDB collection."""
    _, db = _get_client()
    if db is None:
        return None
    return db[name]


# ============================================================
# PLAYERS — بيانات اللاعبين (الأساسية)
# ============================================================

def sync_player_to_cloud(player_data: dict):
    """حفظ بيانات لاعب واحد في السحابة.
    
    player_data يجب أن يحتوي:
      user_id, guild_id, username, points, level, wins, losses,
      kills, mvps, matches_played, win_streak, lose_streak,
      max_win_streak, original_nickname, last_active
    """
    if not is_cloud_enabled():
        return
    
    col = _get_collection("players")
    if col is None:
        return
    
    try:
        key = {"user_id": player_data["user_id"], "guild_id": player_data["guild_id"]}
        # نحوّل كل القيم لـ types متوافقة مع JSON
        doc = {}
        for k, v in player_data.items():
            if v is None:
                doc[k] = None
            elif isinstance(v, (int, float, str, bool)):
                doc[k] = v
            else:
                doc[k] = str(v)
        doc["_cloud_updated"] = datetime.utcnow().isoformat()
        
        col.update_one(key, {"$set": doc}, upsert=True)
    except Exception as e:
        logger.warning(f"☁️ Failed to sync player {player_data.get('user_id')}: {e}")


def sync_guild_players_to_cloud(guild_id: int, players_list: list):
    """حفظ كل لاعبين سيرفر في السحابة (batch).
    يُستدعى بعد كل recalculate_ranks.
    """
    if not is_cloud_enabled():
        return
    
    col = _get_collection("players")
    if col is None:
        return
    
    if not players_list:
        return
    
    try:
        operations = []
        for p in players_list:
            key = {"user_id": p["user_id"], "guild_id": p["guild_id"]}
            doc = {"$set": {}}
            for k, v in p.items():
                if v is None:
                    doc["$set"][k] = None
                elif isinstance(v, (int, float, str, bool)):
                    doc["$set"][k] = v
                else:
                    doc["$set"][k] = str(v)
            doc["$set"]["_cloud_updated"] = datetime.utcnow().isoformat()
            operations.append(("update_one", key, doc))
        
        # Bulk write
        from pymongo import UpdateOne
        bulk_ops = [
            UpdateOne(key, {"$set": doc["$set"]}, upsert=True)
            for key, _, doc in operations
        ]
        if bulk_ops:
            col.bulk_write(bulk_ops, ordered=False)
            logger.info(f"☁️ Synced {len(bulk_ops)} players from guild {guild_id} to cloud")
    except Exception as e:
        logger.warning(f"☁️ Failed to batch sync guild {guild_id}: {e}")


def restore_players_from_cloud(guild_id: int) -> list:
    """يرجع كل بيانات اللاعبين من السحابة لسيرفر معين.
    يُستدعى عند بدء التشغيل لو الـ DB المحلي فاضي.
    """
    if not is_cloud_enabled():
        return []
    
    col = _get_collection("players")
    if col is None:
        return []
    
    try:
        players = list(col.find({"guild_id": guild_id}))
        # أزل _id و _cloud_updated
        result = []
        for p in players:
            p.pop("_id", None)
            p.pop("_cloud_updated", None)
            result.append(p)
        
        if result:
            logger.info(f"☁️ Restored {len(result)} players for guild {guild_id} from cloud")
        return result
    except Exception as e:
        logger.warning(f"☁️ Failed to restore players for guild {guild_id}: {e}")
        return []


def get_all_cloud_guilds() -> list:
    """يرجع كل guild_ids الموجودة في السحابة."""
    if not is_cloud_enabled():
        return []
    
    col = _get_collection("players")
    if col is None:
        return []
    
    try:
        guilds = col.distinct("guild_id")
        return guilds
    except Exception as e:
        logger.warning(f"☁️ Failed to get cloud guilds: {e}")
        return []


# ============================================================
# GUILD SETTINGS — إعدادات السيرفر
# ============================================================

def sync_guild_settings_to_cloud(guild_id: int, settings: dict):
    """حفظ إعدادات سيرفر في السحابة."""
    if not is_cloud_enabled():
        return
    
    col = _get_collection("guild_settings")
    if col is None:
        return
    
    try:
        key = {"guild_id": guild_id}
        doc = {"$set": settings}
        doc["$set"]["_cloud_updated"] = datetime.utcnow().isoformat()
        col.update_one(key, doc["$set"], upsert=True)
    except Exception as e:
        logger.warning(f"☁️ Failed to sync guild settings {guild_id}: {e}")


def restore_guild_settings_from_cloud(guild_id: int) -> Optional[dict]:
    """يرجع إعدادات سيرفر من السحابة."""
    if not is_cloud_enabled():
        return None
    
    col = _get_collection("guild_settings")
    if col is None:
        return None
    
    try:
        data = col.find_one({"guild_id": guild_id})
        if data:
            data.pop("_id", None)
            data.pop("_cloud_updated", None)
            logger.info(f"☁️ Restored guild settings for {guild_id} from cloud")
            return data
        return None
    except Exception as e:
        logger.warning(f"☁️ Failed to restore guild settings {guild_id}: {e}")
        return None


# ============================================================
# CHANNELS — قنوات البوت (play, commands, waiting)
# ============================================================

def sync_channels_to_cloud(guild_id: int, channel_type: str, channel_ids: list):
    """حفظ قنوات سيرفر في السحابة.
    channel_type: 'play', 'commands', 'waiting'
    """
    if not is_cloud_enabled():
        return
    
    col = _get_collection("channels")
    if col is None:
        return
    
    try:
        key = {"guild_id": guild_id, "type": channel_type}
        col.update_one(key, {
            "$set": {"channel_ids": channel_ids, "_cloud_updated": datetime.utcnow().isoformat()}
        }, upsert=True)
    except Exception as e:
        logger.warning(f"☁️ Failed to sync {channel_type} channels: {e}")


def restore_channels_from_cloud(guild_id: int, channel_type: str) -> list:
    """يرجع قنوات سيرفر من السحابة."""
    if not is_cloud_enabled():
        return []
    
    col = _get_collection("channels")
    if col is None:
        return []
    
    try:
        data = col.find_one({"guild_id": guild_id, "type": channel_type})
        if data:
            return data.get("channel_ids", [])
        return []
    except Exception as e:
        logger.warning(f"☁️ Failed to restore {channel_type} channels: {e}")
        return []


# ============================================================
# BANS — المحظورين
# ============================================================

def sync_bans_to_cloud(guild_id: int, banned_players: list):
    """حفظ قائمة المحظورين في السحابة."""
    if not is_cloud_enabled():
        return
    
    col = _get_collection("banned_players")
    if col is None:
        return
    
    try:
        # احذف القديم واحفظ الجديد
        col.delete_many({"guild_id": guild_id})
        if banned_players:
            for p in banned_players:
                p.pop("_id", None) if "_id" in p else None
            col.insert_many(banned_players)
    except Exception as e:
        logger.warning(f"☁️ Failed to sync bans: {e}")


def restore_bans_from_cloud(guild_id: int) -> list:
    """يرجع قائمة المحظورين من السحابة."""
    if not is_cloud_enabled():
        return []
    
    col = _get_collection("banned_players")
    if col is None:
        return []
    
    try:
        data = list(col.find({"guild_id": guild_id}))
        for d in data:
            d.pop("_id", None)
        return data
    except Exception as e:
        logger.warning(f"☁️ Failed to restore bans: {e}")
        return []


# ============================================================
# AUTO-RESTORE ON STARTUP
# ============================================================

def auto_restore_database(local_db):
    """يُستدعى عند بدء التشغيل.
    لو الـ DB المحلي فاضي والسحابة فيها بيانات → يرجعها.
    """
    if not is_cloud_enabled():
        logger.info("☁️ Cloud backup disabled (no MONGODB_URI)")
        return
    
    client, database = _get_client()
    if database is None:
        logger.warning("☁️ Could not connect to MongoDB Atlas — skipping restore")
        return
    
    # اجلب كل السيرفرات من السحابة
    cloud_guilds = get_all_cloud_guilds()
    if not cloud_guilds:
        logger.info("☁️ No cloud data found — starting fresh")
        return
    
    restored_total = 0
    for gid in cloud_guilds:
        # تحقق هل السيرفر لديه لاعبين محلياً
        try:
            conn = local_db.conn()
            local_count = conn.execute(
                "SELECT COUNT(*) FROM players WHERE guild_id=?", (gid,)
            ).fetchone()[0]
        except Exception:
            local_count = 0
        
        if local_count > 0:
            logger.info(f"☁️ Guild {gid}: {local_count} local players — skipping restore")
            continue
        
        # أرجع اللاعبين من السحابة
        players = restore_players_from_cloud(gid)
        if not players:
            continue
        
        # أدخلهم في SQLite المحلي
        try:
            conn = local_db.conn()
            for p in players:
                user_id = p["user_id"]
                guild_id = p["guild_id"]
                username = p.get("username", "Unknown")
                points = p.get("points", 0)
                level = p.get("level", 1000)
                wins = p.get("wins", 0)
                losses = p.get("losses", 0)
                kills = p.get("kills", 0)
                mvps = p.get("mvps", 0)
                matches_played = p.get("matches_played", 0)
                win_streak = p.get("win_streak", 0)
                lose_streak = p.get("lose_streak", 0)
                max_win_streak = p.get("max_win_streak", 0)
                original_nickname = p.get("original_nickname")
                last_active = p.get("last_active")
                
                conn.execute("""
                    INSERT OR REPLACE INTO players
                    (user_id, guild_id, username, points, level, wins, losses,
                     kills, mvps, matches_played, win_streak, lose_streak,
                     max_win_streak, original_nickname, last_active)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """, (user_id, guild_id, username, points, level, wins, losses,
                      kills, mvps, matches_played, win_streak, lose_streak,
                      max_win_streak, original_nickname, last_active))
            conn.commit()
            restored_total += len(players)
            logger.info(f"☁️ Restored {len(players)} players for guild {gid}")
        except Exception as e:
            logger.warning(f"☁️ Failed to restore guild {gid}: {e}")
    
    # أرجع المحظورين
    for gid in cloud_guilds:
        bans = restore_bans_from_cloud(gid)
        if bans:
            try:
                conn = local_db.conn()
                for b in bans:
                    conn.execute("""
                        INSERT OR REPLACE INTO banned_players
                        (guild_id, user_id, ban_reason, report_count, banned_by, assigned_voice_id)
                        VALUES (?,?,?,?,?,?)
                    """, (
                        b.get("guild_id"), b.get("user_id"), b.get("ban_reason"),
                        b.get("report_count", 0), b.get("banned_by"), b.get("assigned_voice_id")
                    ))
                conn.commit()
            except Exception as e:
                logger.warning(f"☁️ Failed to restore bans for guild {gid}: {e}")
    
    if restored_total > 0:
        logger.info(f"☁️ ========== CLOUD RESTORE COMPLETE: {restored_total} players ==========")


# ============================================================
# MANUAL SYNC COMMANDS (for bot owner)
# ============================================================

async def full_backup_to_cloud(local_db):
    """نسخ احتياطي كامل لكل البيانات إلى السحابة.
    يُستدعى من أمر !!cloudbackup.
    """
    if not is_cloud_enabled():
        return False, "Cloud backup not enabled (no MONGODB_URI)"
    
    client, database = _get_client()
    if database is None:
        return False, "Could not connect to MongoDB Atlas"
    
    total_players = 0
    total_guilds = 0
    
    try:
        # اجلب كل السيرفرات من الـ DB المحلي
        conn = local_db.conn()
        guilds = conn.execute("SELECT DISTINCT guild_id FROM players").fetchall()
        
        for g in guilds:
            gid = g["guild_id"]
            players = local_db.get_leaderboard(gid, limit=None)
            if players:
                sync_guild_players_to_cloud(gid, players)
                total_players += len(players)
                total_guilds += 1
            
            # sync bans
            bans = local_db.get_banned_players(gid)
            if bans:
                sync_bans_to_cloud(gid, bans)
        
        return True, f"Backed up {total_players} players from {total_guilds} guilds"
    except Exception as e:
        return False, f"Backup failed: {e}"


async def full_restore_from_cloud(local_db):
    """استرجاع كامل لكل البيانات من السحابة.
    يُستدعى من أمر !!cloudrestore.
    """
    if not is_cloud_enabled():
        return False, "Cloud backup not enabled (no MONGODB_URI)"
    
    client, database = _get_client()
    if database is None:
        return False, "Could not connect to MongoDB Atlas"
    
    try:
        # مسح اللاعبين المحليين
        conn = local_db.conn()
        conn.execute("DELETE FROM players")
        conn.commit()
        
        # استرجاع من السحابة
        auto_restore_database(local_db)
        
        cloud_guilds = get_all_cloud_guilds()
        total = 0
        for gid in cloud_guilds:
            count = conn.execute("SELECT COUNT(*) FROM players WHERE guild_id=?", (gid,)).fetchone()[0]
            total += count
        
        return True, f"Restored {total} players from cloud"
    except Exception as e:
        return False, f"Restore failed: {e}"
