import asyncio
import sqlite3
import datetime
import logging
from typing import Dict, List, Any, Optional
from config import SUPABASE_URL, SUPABASE_SERVICE_KEY

logger = logging.getLogger("MolumBot.Database")

class SQLiteDatabase:
    """Fallback Local SQLite Database for Development and testing."""
    def __init__(self, db_path: str = "molum_local.db"):
        self.db_path = db_path
        self._init_db()

    def _get_conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_conn() as conn:
            cursor = conn.cursor()
            
            # Profiles - added first_name TEXT column
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS profiles (
                    telegram_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    wallet_address TEXT,
                    referred_by INTEGER,
                    total_points INTEGER DEFAULT 0,
                    subscription_status BOOLEAN DEFAULT 0,
                    language_code TEXT DEFAULT 'en',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Referrals
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS referrals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    referrer_id INTEGER,
                    referred_id INTEGER,
                    points_awarded INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(referrer_id, referred_id)
                )
            """)
            
            # Tasks - added sort_order INTEGER column
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    task_id TEXT PRIMARY KEY,
                    description_key TEXT NOT NULL,
                    points_reward INTEGER DEFAULT 0,
                    is_active BOOLEAN DEFAULT 1,
                    sort_order INTEGER DEFAULT 0
                )
            """)
            
            # User Tasks
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_tasks (
                    telegram_id INTEGER,
                    task_id TEXT,
                    completed BOOLEAN DEFAULT 0,
                    completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (telegram_id, task_id)
                )
            """)
            
            # Settings
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Token Notifications
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS token_notifications (
                    telegram_id INTEGER PRIMARY KEY,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Default Settings
            cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('token_status', 'pre-launch')")
            cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('listing_date', '2026-12-31T23:59:59Z')")
            
            # Default Tasks with sort_order
            cursor.execute("INSERT OR IGNORE INTO tasks (task_id, description_key, points_reward, is_active, sort_order) VALUES ('subscribe', 'task_subscribe_channel', 150, 1, 10)")
            cursor.execute("INSERT OR IGNORE INTO tasks (task_id, description_key, points_reward, is_active, sort_order) VALUES ('invite_3_friends', 'task_invite_3_friends', 300, 1, 20)")
            cursor.execute("INSERT OR IGNORE INTO tasks (task_id, description_key, points_reward, is_active, sort_order) VALUES ('connect_wallet', 'task_connect_wallet', 200, 1, 30)")
            
            conn.commit()
            logger.info("Local SQLite database initialized successfully.")

    def get_profile(self, telegram_id: int) -> Optional[Dict[str, Any]]:
        with self._get_conn() as conn:
            row = conn.execute("SELECT * FROM profiles WHERE telegram_id = ?", (telegram_id,)).fetchone()
            return dict(row) if row else None

    def create_profile(self, telegram_id: int, username: str = None, first_name: str = None, referred_by: int = None, subscription_status: bool = False, total_points: int = 0, language_code: str = 'en') -> Dict[str, Any]:
        with self._get_conn() as conn:
            conn.execute("""
                INSERT OR IGNORE INTO profiles (telegram_id, username, first_name, referred_by, subscription_status, total_points, language_code)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (telegram_id, username, first_name, referred_by, int(subscription_status), total_points, language_code))
            conn.commit()
            return self.get_profile(telegram_id)

    def update_profile_language(self, telegram_id: int, lang_code: str) -> bool:
        with self._get_conn() as conn:
            cursor = conn.execute("UPDATE profiles SET language_code = ?, updated_at = CURRENT_TIMESTAMP WHERE telegram_id = ?", (lang_code, telegram_id))
            conn.commit()
            return cursor.rowcount > 0

    def update_profile_wallet(self, telegram_id: int, wallet_address: str) -> bool:
        with self._get_conn() as conn:
            cursor = conn.execute("UPDATE profiles SET wallet_address = ?, updated_at = CURRENT_TIMESTAMP WHERE telegram_id = ?", (wallet_address, telegram_id))
            conn.commit()
            return cursor.rowcount > 0

    def update_profile_subscription(self, telegram_id: int, status: bool) -> bool:
        with self._get_conn() as conn:
            cursor = conn.execute("UPDATE profiles SET subscription_status = ?, updated_at = CURRENT_TIMESTAMP WHERE telegram_id = ?", (int(status), telegram_id))
            conn.commit()
            return cursor.rowcount > 0

    def add_points(self, telegram_id: int, points: int) -> int:
        with self._get_conn() as conn:
            conn.execute("UPDATE profiles SET total_points = total_points + ?, updated_at = CURRENT_TIMESTAMP WHERE telegram_id = ?", (points, telegram_id))
            conn.commit()
            profile = self.get_profile(telegram_id)
            return profile["total_points"] if profile else 0

    def get_referral_count(self, telegram_id: int) -> int:
        with self._get_conn() as conn:
            row = conn.execute("SELECT COUNT(*) as count FROM referrals WHERE referrer_id = ?", (telegram_id,)).fetchone()
            return row["count"] if row else 0

    def get_referrals(self, telegram_id: int) -> List[Dict[str, Any]]:
        with self._get_conn() as conn:
            rows = conn.execute("SELECT * FROM referrals WHERE referrer_id = ?", (telegram_id,)).fetchall()
            return [dict(r) for r in rows]

    def add_referral(self, referrer_id: int, referred_id: int, points_awarded: int) -> bool:
        try:
            with self._get_conn() as conn:
                conn.execute("""
                    INSERT INTO referrals (referrer_id, referred_id, points_awarded)
                    VALUES (?, ?, ?)
                """, (referrer_id, referred_id, points_awarded))
                conn.commit()
                return True
        except sqlite3.IntegrityError:
            return False

    def has_referred(self, referrer_id: int, referred_id: int) -> bool:
        with self._get_conn() as conn:
            row = conn.execute("SELECT 1 FROM referrals WHERE referrer_id = ? AND referred_id = ?", (referrer_id, referred_id)).fetchone()
            return row is not None

    def get_tasks(self) -> List[Dict[str, Any]]:
        with self._get_conn() as conn:
            # Added order by sort_order
            rows = conn.execute("SELECT * FROM tasks WHERE is_active = 1 ORDER BY sort_order ASC").fetchall()
            return [dict(r) for r in rows]

    def get_user_tasks(self, telegram_id: int) -> List[Dict[str, Any]]:
        with self._get_conn() as conn:
            rows = conn.execute("SELECT * FROM user_tasks WHERE telegram_id = ?", (telegram_id,)).fetchall()
            return [dict(r) for r in rows]

    def get_user_task_status(self, telegram_id: int, task_id: str) -> Optional[Dict[str, Any]]:
        with self._get_conn() as conn:
            row = conn.execute("SELECT * FROM user_tasks WHERE telegram_id = ? AND task_id = ?", (telegram_id, task_id)).fetchone()
            return dict(row) if row else None

    def complete_user_task(self, telegram_id: int, task_id: str) -> bool:
        try:
            with self._get_conn() as conn:
                conn.execute("""
                    INSERT INTO user_tasks (telegram_id, task_id, completed, completed_at)
                    VALUES (?, ?, 1, CURRENT_TIMESTAMP)
                    ON CONFLICT(telegram_id, task_id) DO UPDATE SET completed = 1, completed_at = CURRENT_TIMESTAMP
                """, (telegram_id, task_id))
                conn.commit()
                return True
        except Exception:
            return False

    def get_setting(self, key: str) -> Optional[str]:
        with self._get_conn() as conn:
            row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
            return row["value"] if row else None

    def update_setting(self, key: str, value: str) -> bool:
        with self._get_conn() as conn:
            conn.execute("""
                INSERT INTO settings (key, value, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(key) DO UPDATE SET value = ?, updated_at = CURRENT_TIMESTAMP
            """, (key, value, value))
            conn.commit()
            return True

    def add_token_notification(self, telegram_id: int) -> bool:
        try:
            with self._get_conn() as conn:
                conn.execute("INSERT OR IGNORE INTO token_notifications (telegram_id) VALUES (?)", (telegram_id,))
                conn.commit()
                return True
        except Exception:
            return False

    def has_token_notification(self, telegram_id: int) -> bool:
        with self._get_conn() as conn:
            row = conn.execute("SELECT 1 FROM token_notifications WHERE telegram_id = ?", (telegram_id,)).fetchone()
            return row is not None

    def get_admin_stats(self) -> Dict[str, Any]:
        with self._get_conn() as conn:
            total_users = conn.execute("SELECT COUNT(*) as count FROM profiles").fetchone()["count"]
            total_referrals = conn.execute("SELECT COUNT(*) as count FROM referrals").fetchone()["count"]
            total_points = conn.execute("SELECT SUM(total_points) as sum FROM profiles").fetchone()["sum"] or 0
            return {
                "total_users": total_users,
                "total_referrals": total_referrals,
                "total_points": total_points
            }

    def get_recent_users(self, limit: int = 20) -> List[Dict[str, Any]]:
        with self._get_conn() as conn:
            rows = conn.execute("SELECT telegram_id, username, total_points, created_at FROM profiles ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
            return [dict(r) for r in rows]

    def get_all_users(self) -> List[int]:
        with self._get_conn() as conn:
            rows = conn.execute("SELECT telegram_id FROM profiles").fetchall()
            return [r["telegram_id"] for r in rows]

    def clean_database(self) -> bool:
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM token_notifications")
            cursor.execute("DELETE FROM referrals")
            cursor.execute("DELETE FROM user_tasks")
            cursor.execute("DELETE FROM profiles")
            conn.commit()
            return True


class SupabaseDatabase:
    """Real Database Integration with Supabase."""
    def __init__(self):
        from supabase import create_client, Client
        self.supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        logger.info("Supabase Client initialized successfully.")

    def get_profile(self, telegram_id: int) -> Optional[Dict[str, Any]]:
        res = self.supabase.table('profiles').select('*').eq('telegram_id', telegram_id).execute()
        return res.data[0] if res.data else None

    def create_profile(self, telegram_id: int, username: str = None, first_name: str = None, referred_by: int = None, subscription_status: bool = False, total_points: int = 0, language_code: str = 'en') -> Dict[str, Any]:
        existing = self.get_profile(telegram_id)
        if existing:
            return existing
        data = {
            "telegram_id": telegram_id,
            "username": username,
            "first_name": first_name,
            "referred_by": referred_by,
            "subscription_status": subscription_status,
            "total_points": total_points,
            "language_code": language_code
        }
        res = self.supabase.table('profiles').insert(data).execute()
        return res.data[0] if res.data else None

    def update_profile_language(self, telegram_id: int, lang_code: str) -> bool:
        res = self.supabase.table('profiles').update({"language_code": lang_code}).eq('telegram_id', telegram_id).execute()
        return len(res.data) > 0

    def update_profile_wallet(self, telegram_id: int, wallet_address: str) -> bool:
        res = self.supabase.table('profiles').update({"wallet_address": wallet_address}).eq('telegram_id', telegram_id).execute()
        return len(res.data) > 0

    def update_profile_subscription(self, telegram_id: int, status: bool) -> bool:
        res = self.supabase.table('profiles').update({"subscription_status": status}).eq('telegram_id', telegram_id).execute()
        return len(res.data) > 0

    def add_points(self, telegram_id: int, points: int) -> int:
        profile = self.get_profile(telegram_id)
        if not profile:
            return 0
        new_points = profile.get("total_points", 0) + points
        res = self.supabase.table('profiles').update({"total_points": new_points}).eq('telegram_id', telegram_id).execute()
        return res.data[0]["total_points"] if res.data else 0

    def get_referral_count(self, telegram_id: int) -> int:
        res = self.supabase.table('referrals').select('id', count='exact').eq('referrer_id', telegram_id).execute()
        return res.count if res.count is not None else len(res.data)

    def get_referrals(self, telegram_id: int) -> List[Dict[str, Any]]:
        res = self.supabase.table('referrals').select('*').eq('referrer_id', telegram_id).execute()
        return res.data

    def add_referral(self, referrer_id: int, referred_id: int, points_awarded: int) -> bool:
        try:
            data = {
                "referrer_id": referrer_id,
                "referred_id": referred_id,
                "points_awarded": points_awarded
            }
            res = self.supabase.table('referrals').insert(data).execute()
            return len(res.data) > 0
        except Exception as e:
            logger.error(f"Error adding referral: {e}")
            return False

    def has_referred(self, referrer_id: int, referred_id: int) -> bool:
        res = self.supabase.table('referrals').select('*').eq('referrer_id', referrer_id).eq('referred_id', referred_id).execute()
        return len(res.data) > 0

    def get_tasks(self) -> List[Dict[str, Any]]:
        # Added ordering by sort_order
        res = self.supabase.table('tasks').select('*').eq('is_active', True).order('sort_order', desc=False).execute()
        return res.data

    def get_user_tasks(self, telegram_id: int) -> List[Dict[str, Any]]:
        res = self.supabase.table('user_tasks').select('*').eq('telegram_id', telegram_id).execute()
        return res.data

    def get_user_task_status(self, telegram_id: int, task_id: str) -> Optional[Dict[str, Any]]:
        res = self.supabase.table('user_tasks').select('*').eq('telegram_id', telegram_id).eq('task_id', task_id).execute()
        return res.data[0] if res.data else None

    def complete_user_task(self, telegram_id: int, task_id: str) -> bool:
        # Check if already completed
        status = self.get_user_task_status(telegram_id, task_id)
        if status and status.get("completed"):
            return True
        
        data = {
            "telegram_id": telegram_id,
            "task_id": task_id,
            "completed": True,
            "completed_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }
        res = self.supabase.table('user_tasks').upsert(data).execute()
        return len(res.data) > 0

    def get_setting(self, key: str) -> Optional[str]:
        res = self.supabase.table('settings').select('value').eq('key', key).execute()
        return res.data[0]['value'] if res.data else None

    def update_setting(self, key: str, value: str) -> bool:
        data = {
            "key": key,
            "value": value,
            "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }
        res = self.supabase.table('settings').upsert(data).execute()
        return len(res.data) > 0

    def add_token_notification(self, telegram_id: int) -> bool:
        try:
            data = {"telegram_id": telegram_id}
            res = self.supabase.table('token_notifications').upsert(data).execute()
            return len(res.data) > 0
        except Exception as e:
            logger.error(f"Error adding notification: {e}")
            return False

    def has_token_notification(self, telegram_id: int) -> bool:
        res = self.supabase.table('token_notifications').select('*').eq('telegram_id', telegram_id).execute()
        return len(res.data) > 0

    def get_admin_stats(self) -> Dict[str, Any]:
        profiles_res = self.supabase.table('profiles').select('telegram_id', count='exact').execute()
        total_users = profiles_res.count if profiles_res.count is not None else len(profiles_res.data)
        
        referrals_res = self.supabase.table('referrals').select('id', count='exact').execute()
        total_referrals = referrals_res.count if referrals_res.count is not None else len(referrals_res.data)
        
        points_res = self.supabase.table('profiles').select('total_points').execute()
        total_points = sum(r.get("total_points", 0) for r in points_res.data) if points_res.data else 0
        
        return {
            "total_users": total_users,
            "total_referrals": total_referrals,
            "total_points": total_points
        }

    def get_recent_users(self, limit: int = 20) -> List[Dict[str, Any]]:
        res = self.supabase.table('profiles').select('telegram_id', 'username', 'total_points', 'created_at').order('created_at', desc=True).limit(limit).execute()
        return res.data

    def get_all_users(self) -> List[int]:
        res = self.supabase.table('profiles').select('telegram_id').execute()
        return [r["telegram_id"] for r in res.data] if res.data else []

    def clean_database(self) -> bool:
        try:
            res = self.supabase.rpc('clean_database').execute()
            logger.info(f"Supabase RPC clean_database returned: {res.data}")
            return True
        except Exception as e:
            logger.error(f"Failed to clean Supabase database via RPC: {e}")
            try:
                self.supabase.table('token_notifications').delete().neq('telegram_id', 0).execute()
                self.supabase.table('referrals').delete().neq('id', 0).execute()
                self.supabase.table('user_tasks').delete().neq('telegram_id', 0).execute()
                self.supabase.table('profiles').delete().neq('telegram_id', 0).execute()
                return True
            except Exception as ex:
                logger.error(f"Fallback manual clean failed too: {ex}")
                return False


# Determine which DB client to instantiate
if SUPABASE_URL and SUPABASE_SERVICE_KEY:
    try:
        _db_impl = SupabaseDatabase()
    except Exception as err:
        logger.error(f"Failed to connect to Supabase: {err}. Falling back to SQLite.")
        _db_impl = SQLiteDatabase()
else:
    _db_impl = SQLiteDatabase()


# --- Public ASYNC Wrappers that run on thread pool ---

async def get_profile(telegram_id: int) -> Optional[Dict[str, Any]]:
    return await asyncio.to_thread(_db_impl.get_profile, telegram_id)

async def create_profile(telegram_id: int, username: str = None, first_name: str = None, referred_by: int = None, subscription_status: bool = False, total_points: int = 0, language_code: str = 'en') -> Dict[str, Any]:
    return await asyncio.to_thread(_db_impl.create_profile, telegram_id, username, first_name, referred_by, subscription_status, total_points, language_code)

async def update_profile_language(telegram_id: int, lang_code: str) -> bool:
    return await asyncio.to_thread(_db_impl.update_profile_language, telegram_id, lang_code)

async def update_profile_wallet(telegram_id: int, wallet_address: str) -> bool:
    return await asyncio.to_thread(_db_impl.update_profile_wallet, telegram_id, wallet_address)

async def update_profile_subscription(telegram_id: int, status: bool) -> bool:
    return await asyncio.to_thread(_db_impl.update_profile_subscription, telegram_id, status)

async def add_points(telegram_id: int, points: int) -> int:
    return await asyncio.to_thread(_db_impl.add_points, telegram_id, points)

async def get_referral_count(telegram_id: int) -> int:
    return await asyncio.to_thread(_db_impl.get_referral_count, telegram_id)

async def get_referrals(telegram_id: int) -> List[Dict[str, Any]]:
    return await asyncio.to_thread(_db_impl.get_referrals, telegram_id)

async def add_referral(referrer_id: int, referred_id: int, points_awarded: int) -> bool:
    return await asyncio.to_thread(_db_impl.add_referral, referrer_id, referred_id, points_awarded)

async def has_referred(referrer_id: int, referred_id: int) -> bool:
    return await asyncio.to_thread(_db_impl.has_referred, referrer_id, referred_id)

async def get_tasks() -> List[Dict[str, Any]]:
    return await asyncio.to_thread(_db_impl.get_tasks)

async def get_user_tasks(telegram_id: int) -> List[Dict[str, Any]]:
    return await asyncio.to_thread(_db_impl.get_user_tasks, telegram_id)

async def get_user_task_status(telegram_id: int, task_id: str) -> Optional[Dict[str, Any]]:
    return await asyncio.to_thread(_db_impl.get_user_task_status, telegram_id, task_id)

async def complete_user_task(telegram_id: int, task_id: str) -> bool:
    return await asyncio.to_thread(_db_impl.complete_user_task, telegram_id, task_id)

async def get_setting(key: str) -> Optional[str]:
    return await asyncio.to_thread(_db_impl.get_setting, key)

async def update_setting(key: str, value: str) -> bool:
    return await asyncio.to_thread(_db_impl.update_setting, key, value)

async def add_token_notification(telegram_id: int) -> bool:
    return await asyncio.to_thread(_db_impl.add_token_notification, telegram_id)

async def has_token_notification(telegram_id: int) -> bool:
    return await asyncio.to_thread(_db_impl.has_token_notification, telegram_id)

async def get_admin_stats() -> Dict[str, Any]:
    return await asyncio.to_thread(_db_impl.get_admin_stats)

async def get_recent_users(limit: int = 20) -> List[Dict[str, Any]]:
    return await asyncio.to_thread(_db_impl.get_recent_users, limit)

async def get_all_users() -> List[int]:
    return await asyncio.to_thread(_db_impl.get_all_users)

async def clean_database() -> bool:
    return await asyncio.to_thread(_db_impl.clean_database)
