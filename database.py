import asyncio
import sqlite3
import datetime
import logging
from typing import Dict, List, Any, Optional
from decimal import Decimal
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
            
            # Profiles - matching exactly Supabase profiles schema
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS profiles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_id INTEGER NOT NULL UNIQUE,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    total_points INTEGER NOT NULL DEFAULT 0,
                    referral_count INTEGER NOT NULL DEFAULT 0,
                    referral_code TEXT UNIQUE,
                    is_subscribed BOOLEAN NOT NULL DEFAULT 0,
                    wallet_address TEXT,
                    language_code TEXT NOT NULL DEFAULT 'en',
                    notify_listing BOOLEAN NOT NULL DEFAULT 0,
                    avatar_url TEXT,
                    referred_by INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Tasks - matching exactly Supabase tasks schema
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL UNIQUE,
                    title_en TEXT NOT NULL,
                    title_ru TEXT NOT NULL,
                    description_en TEXT,
                    description_ru TEXT,
                    points INTEGER NOT NULL DEFAULT 0,
                    link TEXT,
                    is_active BOOLEAN NOT NULL DEFAULT 1,
                    icon TEXT DEFAULT 'sparkles',
                    sort_order INTEGER NOT NULL DEFAULT 0,
                    verify_type TEXT NOT NULL DEFAULT 'bot',
                    verify_chat TEXT,
                    verify_value INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # User Tasks - matching exactly Supabase user_tasks schema
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_id INTEGER NOT NULL REFERENCES profiles (telegram_id) ON DELETE CASCADE,
                    task_id TEXT NOT NULL,
                    completed BOOLEAN NOT NULL DEFAULT 0,
                    completed_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE (telegram_id, task_id)
                )
            """)
            
            # Settings
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key TEXT NOT NULL UNIQUE,
                    value TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Claim Snapshots Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS claim_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_id INTEGER NOT NULL UNIQUE REFERENCES profiles (telegram_id) ON DELETE CASCADE,
                    wallet_address TEXT NOT NULL,
                    points_snap INTEGER NOT NULL DEFAULT 0,
                    tokens_allocated REAL NOT NULL DEFAULT 0.0,
                    claimed BOOLEAN NOT NULL DEFAULT 0,
                    claimed_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Contests Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS contests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    reward_points INTEGER NOT NULL DEFAULT 0,
                    is_active BOOLEAN NOT NULL DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Contest Submissions Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS contest_submissions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    contest_id INTEGER NOT NULL REFERENCES contests (id) ON DELETE CASCADE,
                    telegram_id INTEGER NOT NULL REFERENCES profiles (telegram_id) ON DELETE CASCADE,
                    submission_link TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE (telegram_id, contest_id)
                )
            """)
            
            # Default Settings
            cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('token_status', 'prelaunch')")
            cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('listing_date', '2026-06-15T18:00:00Z')")
            cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('token_symbol', 'MOLUM')")
            cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('token_price', '0.0042')")
            cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('token_chart_url', 'https://pump.fun')")
            
            # Default Tasks seed
            cursor.execute("""
                INSERT OR IGNORE INTO tasks (
                    task_id, title_en, title_ru, description_en, description_ru,
                    points, link, is_active, icon, sort_order, verify_type, verify_chat, verify_value
                ) VALUES 
                ('subscribe', 'Subscribe to Molum channel', 'Подпишитесь на канал Molum', 'Join the official Telegram channel and stay updated.', 'Подпишитесь на официальный Telegram-канал.', 150, 'https://t.me/molum_chain_official', 1, 'subscribe', 1, 'channel', '@molum_chain_official', NULL),
                ('twitter', 'Follow Molum on X', 'Подпишитесь на Molum в X', 'Follow our X (Twitter) account for announcements.', 'Подпишитесь на наш аккаунт X для новостей.', 100, 'https://x.com/molum', 1, 'twitter', 2, 'bot', NULL, NULL),
                ('invite_3_friends', 'Invite 3 friends', 'Пригласите 3 друзей', 'Share your referral link and bring 3 friends.', 'Поделитесь реферальной ссылкой и пригласите 3 друзей.', 300, NULL, 1, 'invite', 3, 'referrals', NULL, 3),
                ('connect_wallet', 'Connect Solana wallet', 'Подключите Solana-кошелёк', 'Link Phantom or Solflare to your profile.', 'Привяжите Phantom или Solflare к профилю.', 200, NULL, 1, 'wallet', 4, 'wallet', NULL, NULL),
                ('boost', 'Boost the community post', 'Бустните пост сообщества', 'Join the community chat / boost the pinned post.', 'Вступите в чат сообщества / бустните закреплённый пост.', 120, 'https://t.me/molum_chat', 1, 'rocket', 5, 'chat', '@molum_chat', NULL),
                ('story', 'Share Molum story', 'Поделитесь сторис Molum', 'Post a Telegram story about Molum (verified by bot).', 'Опубликуйте Telegram-сторис о Molum (проверяет бот).', 80, NULL, 1, 'sparkles', 6, 'bot', NULL, NULL)
            """)
            
            conn.commit()
            logger.info("Local SQLite database initialized successfully with expanded features.")

    def get_profile(self, telegram_id: int) -> Optional[Dict[str, Any]]:
        with self._get_conn() as conn:
            row = conn.execute("SELECT * FROM profiles WHERE telegram_id = ?", (telegram_id,)).fetchone()
            return dict(row) if row else None

    def create_profile(self, telegram_id: int, username: str = None, first_name: str = None, last_name: str = None, referred_by: int = None, is_subscribed: bool = False, total_points: int = 0, language_code: str = 'en') -> Dict[str, Any]:
        ref_code = f"MOL{telegram_id}"
        with self._get_conn() as conn:
            conn.execute("""
                INSERT OR IGNORE INTO profiles (telegram_id, username, first_name, last_name, referral_code, referred_by, is_subscribed, total_points, language_code)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (telegram_id, username, first_name, last_name, ref_code, referred_by, int(is_subscribed), total_points, language_code))
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
            cursor = conn.execute("UPDATE profiles SET is_subscribed = ?, updated_at = CURRENT_TIMESTAMP WHERE telegram_id = ?", (int(status), telegram_id))
            conn.commit()
            return cursor.rowcount > 0

    def add_points(self, telegram_id: int, points: int) -> int:
        with self._get_conn() as conn:
            conn.execute("UPDATE profiles SET total_points = total_points + ?, updated_at = CURRENT_TIMESTAMP WHERE telegram_id = ?", (points, telegram_id))
            conn.commit()
            profile = self.get_profile(telegram_id)
            return profile["total_points"] if profile else 0

    def increment_referral_count(self, telegram_id: int) -> bool:
        with self._get_conn() as conn:
            cursor = conn.execute("UPDATE profiles SET referral_count = referral_count + 1, updated_at = CURRENT_TIMESTAMP WHERE telegram_id = ?", (telegram_id,))
            conn.commit()
            return cursor.rowcount > 0

    def get_referral_count(self, telegram_id: int) -> int:
        profile = self.get_profile(telegram_id)
        return profile.get("referral_count", 0) if profile else 0

    def get_referrals(self, telegram_id: int) -> List[Dict[str, Any]]:
        with self._get_conn() as conn:
            rows = conn.execute("SELECT * FROM profiles WHERE referred_by = ?", (telegram_id,)).fetchall()
            return [dict(r) for r in rows]

    def has_referred(self, referrer_id: int, referred_id: int) -> bool:
        with self._get_conn() as conn:
            row = conn.execute("SELECT 1 FROM profiles WHERE referred_by = ? AND telegram_id = ?", (referrer_id, referred_id)).fetchone()
            return row is not None

    def get_tasks(self) -> List[Dict[str, Any]]:
        with self._get_conn() as conn:
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
        except Exception as e:
            logger.error(f"Failed to complete SQLite task: {e}")
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
        with self._get_conn() as conn:
            cursor = conn.execute("UPDATE profiles SET notify_listing = 1 WHERE telegram_id = ?", (telegram_id,))
            conn.commit()
            return cursor.rowcount > 0

    def has_token_notification(self, telegram_id: int) -> bool:
        profile = self.get_profile(telegram_id)
        return bool(profile.get("notify_listing")) if profile else False

    def get_admin_stats(self) -> Dict[str, Any]:
        with self._get_conn() as conn:
            total_users = conn.execute("SELECT COUNT(*) as count FROM profiles").fetchone()["count"]
            total_referrals = conn.execute("SELECT SUM(referral_count) as sum FROM profiles").fetchone()["sum"] or 0
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
            cursor.execute("DELETE FROM claim_snapshots")
            cursor.execute("DELETE FROM contest_submissions")
            cursor.execute("DELETE FROM contests")
            cursor.execute("DELETE FROM user_tasks")
            cursor.execute("DELETE FROM profiles")
            conn.commit()
            return True

    def get_users_to_notify(self) -> List[Dict[str, Any]]:
        with self._get_conn() as conn:
            rows = conn.execute("SELECT telegram_id, language_code FROM profiles WHERE notify_listing = 1").fetchall()
            return [dict(r) for r in rows]

    # ---------- EXPANDED SNAPSHOT & CONTESTS (SQLite) ----------
    
    def create_claim_snapshot(self, conversion_rate: float) -> bool:
        with self._get_conn() as conn:
            # Drop previous snapshots to prevent conflicts during new run
            conn.execute("DELETE FROM claim_snapshots")
            
            # Fetch users with points > 0 and connected wallets
            users = conn.execute("SELECT telegram_id, wallet_address, total_points FROM profiles WHERE wallet_address IS NOT NULL AND total_points > 0").fetchall()
            for u in users:
                tokens = float(u["total_points"]) / conversion_rate
                conn.execute("""
                    INSERT INTO claim_snapshots (telegram_id, wallet_address, points_snap, tokens_allocated)
                    VALUES (?, ?, ?, ?)
                """, (u["telegram_id"], u["wallet_address"], u["total_points"], tokens))
            conn.commit()
            return True

    def get_claim_snapshot(self, telegram_id: int) -> Optional[Dict[str, Any]]:
        with self._get_conn() as conn:
            row = conn.execute("SELECT * FROM claim_snapshots WHERE telegram_id = ?", (telegram_id,)).fetchone()
            return dict(row) if row else None

    def claim_tokens(self, telegram_id: int) -> bool:
        with self._get_conn() as conn:
            cursor = conn.execute("UPDATE claim_snapshots SET claimed = 1, claimed_at = CURRENT_TIMESTAMP WHERE telegram_id = ?", (telegram_id,))
            conn.commit()
            return cursor.rowcount > 0

    def create_contest(self, title: str, description: str, reward_points: int) -> int:
        with self._get_conn() as conn:
            cursor = conn.execute("""
                INSERT INTO contests (title, description, reward_points, is_active)
                VALUES (?, ?, ?, 1)
            """, (title, description, reward_points))
            conn.commit()
            return cursor.lastrowid

    def get_active_contests(self) -> List[Dict[str, Any]]:
        with self._get_conn() as conn:
            rows = conn.execute("SELECT * FROM contests WHERE is_active = 1 ORDER BY created_at DESC").fetchall()
            return [dict(r) for r in rows]

    def submit_contest(self, contest_id: int, telegram_id: int, submission_link: str) -> bool:
        try:
            with self._get_conn() as conn:
                conn.execute("""
                    INSERT INTO contest_submissions (contest_id, telegram_id, submission_link, status)
                    VALUES (?, ?, ?, 'pending')
                    ON CONFLICT(telegram_id, contest_id) DO UPDATE SET submission_link = ?, status = 'pending'
                """, (contest_id, telegram_id, submission_link, submission_link))
                conn.commit()
                return True
        except Exception:
            return False

    def get_pending_submissions(self) -> List[Dict[str, Any]]:
        with self._get_conn() as conn:
            rows = conn.execute("""
                SELECT cs.id, cs.contest_id, cs.telegram_id, cs.submission_link, cs.status, c.title, c.reward_points, p.username
                FROM contest_submissions cs
                JOIN contests c ON cs.contest_id = c.id
                JOIN profiles p ON cs.telegram_id = p.telegram_id
                WHERE cs.status = 'pending'
            """).fetchall()
            return [dict(r) for r in rows]

    def approve_submission(self, submission_id: int) -> bool:
        with self._get_conn() as conn:
            # Fetch submission
            row = conn.execute("""
                SELECT cs.telegram_id, c.reward_points 
                FROM contest_submissions cs
                JOIN contests c ON cs.contest_id = c.id
                WHERE cs.id = ? AND cs.status = 'pending'
            """, (submission_id,)).fetchone()
            
            if not row:
                return False
                
            telegram_id = row["telegram_id"]
            reward = row["reward_points"]
            
            # Approve submission
            conn.execute("UPDATE contest_submissions SET status = 'approved' WHERE id = ?", (submission_id,))
            # Award points to profile
            conn.execute("UPDATE profiles SET total_points = total_points + ? WHERE telegram_id = ?", (reward, telegram_id))
            conn.commit()
            return True

    def reject_submission(self, submission_id: int) -> bool:
        with self._get_conn() as conn:
            cursor = conn.execute("UPDATE contest_submissions SET status = 'rejected' WHERE id = ? AND status = 'pending'", (submission_id,))
            conn.commit()
            return cursor.rowcount > 0


class SupabaseDatabase:
    """Real Database Integration with Supabase."""
    def __init__(self):
        from supabase import create_client, Client
        self.supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        logger.info("Supabase Client initialized successfully.")

    def get_profile(self, telegram_id: int) -> Optional[Dict[str, Any]]:
        res = self.supabase.table('profiles').select('*').eq('telegram_id', telegram_id).execute()
        return res.data[0] if res.data else None

    def create_profile(self, telegram_id: int, username: str = None, first_name: str = None, last_name: str = None, referred_by: int = None, is_subscribed: bool = False, total_points: int = 0, language_code: str = 'en') -> Dict[str, Any]:
        existing = self.get_profile(telegram_id)
        if existing:
            return existing
        ref_code = f"MOL{telegram_id}"
        data = {
            "telegram_id": telegram_id,
            "username": username,
            "first_name": first_name,
            "last_name": last_name,
            "referral_code": ref_code,
            "referred_by": referred_by,
            "is_subscribed": is_subscribed,
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
        res = self.supabase.table('profiles').update({"is_subscribed": status}).eq('telegram_id', telegram_id).execute()
        return len(res.data) > 0

    def add_points(self, telegram_id: int, points: int) -> int:
        profile = self.get_profile(telegram_id)
        if not profile:
            return 0
        new_points = profile.get("total_points", 0) + points
        res = self.supabase.table('profiles').update({"total_points": new_points}).eq('telegram_id', telegram_id).execute()
        return res.data[0]["total_points"] if res.data else 0

    def increment_referral_count(self, telegram_id: int) -> bool:
        profile = self.get_profile(telegram_id)
        if not profile:
            return False
        new_count = profile.get("referral_count", 0) + 1
        res = self.supabase.table('profiles').update({"referral_count": new_count}).eq('telegram_id', telegram_id).execute()
        return len(res.data) > 0

    def get_referral_count(self, telegram_id: int) -> int:
        profile = self.get_profile(telegram_id)
        return profile.get("referral_count", 0) if profile else 0

    def get_referrals(self, telegram_id: int) -> List[Dict[str, Any]]:
        res = self.supabase.table('profiles').select('*').eq('referred_by', telegram_id).execute()
        return res.data

    def has_referred(self, referrer_id: int, referred_id: int) -> bool:
        res = self.supabase.table('profiles').select('*').eq('referred_by', referrer_id).eq('telegram_id', referred_id).execute()
        return len(res.data) > 0

    def get_tasks(self) -> List[Dict[str, Any]]:
        res = self.supabase.table('tasks').select('*').eq('is_active', True).order('sort_order', desc=False).execute()
        return res.data

    def get_user_tasks(self, telegram_id: int) -> List[Dict[str, Any]]:
        res = self.supabase.table('user_tasks').select('*').eq('telegram_id', telegram_id).execute()
        return res.data

    def get_user_task_status(self, telegram_id: int, task_id: str) -> Optional[Dict[str, Any]]:
        res = self.supabase.table('user_tasks').select('*').eq('telegram_id', telegram_id).eq('task_id', task_id).execute()
        return res.data[0] if res.data else None

    def complete_user_task(self, telegram_id: int, task_id: str) -> bool:
        status = self.get_user_task_status(telegram_id, task_id)
        if status:
            if status.get("completed"):
                return True
            res = self.supabase.table('user_tasks').update({
                "completed": True,
                "completed_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
            }).eq('telegram_id', telegram_id).eq('task_id', task_id).execute()
            return len(res.data) > 0
        else:
            data = {
                "telegram_id": telegram_id,
                "task_id": task_id,
                "completed": True,
                "completed_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
            }
            res = self.supabase.table('user_tasks').insert(data).execute()
            return len(res.data) > 0

    def get_setting(self, key: str) -> Optional[str]:
        res = self.supabase.table('settings').select('value').eq('key', key).execute()
        return res.data[0]['value'] if res.data else None

    def update_setting(self, key: str, value: str) -> bool:
        existing = self.get_setting(key)
        if existing is not None:
            res = self.supabase.table('settings').update({
                "value": value,
                "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
            }).eq('key', key).execute()
            return len(res.data) > 0
        else:
            data = {
                "key": key,
                "value": value,
                "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
            }
            res = self.supabase.table('settings').insert(data).execute()
            return len(res.data) > 0

    def add_token_notification(self, telegram_id: int) -> bool:
        res = self.supabase.table('profiles').update({"notify_listing": True}).eq('telegram_id', telegram_id).execute()
        return len(res.data) > 0

    def has_token_notification(self, telegram_id: int) -> bool:
        profile = self.get_profile(telegram_id)
        return bool(profile.get("notify_listing")) if profile else False

    def get_admin_stats(self) -> Dict[str, Any]:
        profiles_res = self.supabase.table('profiles').select('telegram_id', count='exact').execute()
        total_users = profiles_res.count if profiles_res.count is not None else len(profiles_res.data)
        
        points_res = self.supabase.table('profiles').select('total_points', 'referral_count').execute()
        total_points = sum(r.get("total_points", 0) for r in points_res.data) if points_res.data else 0
        total_referrals = sum(r.get("referral_count", 0) for r in points_res.data) if points_res.data else 0
        
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
                self.supabase.table('user_tasks').delete().neq('id', 0).execute()
                self.supabase.table('profiles').delete().neq('id', 0).execute()
                return True
            except Exception as ex:
                logger.error(f"Fallback manual clean failed too: {ex}")
                return False

    def get_users_to_notify(self) -> List[Dict[str, Any]]:
        res = self.supabase.table('profiles').select('telegram_id', 'language_code').eq('notify_listing', True).execute()
        return res.data if res.data else []

    # ---------- EXPANDED SNAPSHOT & CONTESTS (Supabase) ----------

    def create_claim_snapshot(self, conversion_rate: float) -> bool:
        try:
            # 1. Clear older snapshots
            self.supabase.table('claim_snapshots').delete().neq('id', 0).execute()
            
            # 2. Fetch profiles with connected wallets and points > 0
            profiles_res = self.supabase.table('profiles').select('telegram_id', 'wallet_address', 'total_points').not_.is_('wallet_address', 'null').gt('total_points', 0).execute()
            
            if not profiles_res.data:
                return True
                
            # 3. Compile snapshot list
            snapshot_data = []
            for p in profiles_res.data:
                points = p.get("total_points", 0)
                tokens = float(points) / conversion_rate
                snapshot_data.append({
                    "telegram_id": p["telegram_id"],
                    "wallet_address": p["wallet_address"],
                    "points_snap": points,
                    "tokens_allocated": tokens
                })
                
            # 4. Insert bulk snapshot data
            res = self.supabase.table('claim_snapshots').insert(snapshot_data).execute()
            return len(res.data) > 0
        except Exception as e:
            logger.error(f"Failed to create claim snapshot in Supabase: {e}")
            return False

    def get_claim_snapshot(self, telegram_id: int) -> Optional[Dict[str, Any]]:
        res = self.supabase.table('claim_snapshots').select('*').eq('telegram_id', telegram_id).execute()
        return res.data[0] if res.data else None

    def claim_tokens(self, telegram_id: int) -> bool:
        res = self.supabase.table('claim_snapshots').update({
            "claimed": True,
            "claimed_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }).eq('telegram_id', telegram_id).execute()
        return len(res.data) > 0

    def create_contest(self, title: str, description: str, reward_points: int) -> int:
        data = {
            "title": title,
            "description": description,
            "reward_points": reward_points,
            "is_active": True
        }
        res = self.supabase.table('contests').insert(data).execute()
        return res.data[0]["id"] if res.data else 0

    def get_active_contests(self) -> List[Dict[str, Any]]:
        res = self.supabase.table('contests').select('*').eq('is_active', True).order('created_at', desc=True).execute()
        return res.data

    def submit_contest(self, contest_id: int, telegram_id: int, submission_link: str) -> bool:
        try:
            data = {
                "contest_id": contest_id,
                "telegram_id": telegram_id,
                "submission_link": submission_link,
                "status": "pending"
            }
            res = self.supabase.table('contest_submissions').upsert(data, on_conflict='telegram_id,contest_id').execute()
            return len(res.data) > 0
        except Exception as e:
            logger.error(f"Failed to submit contest in Supabase: {e}")
            return False

    def get_pending_submissions(self) -> List[Dict[str, Any]]:
        try:
            # Query joined tables or manually build relation
            subs_res = self.supabase.table('contest_submissions').select('*').eq('status', 'pending').execute()
            if not subs_res.data:
                return []
                
            # Populate joined information dynamically
            detailed_subs = []
            for s in subs_res.data:
                contest_res = self.supabase.table('contests').select('title', 'reward_points').eq('id', s["contest_id"]).execute()
                profile_res = self.supabase.table('profiles').select('username').eq('telegram_id', s["telegram_id"]).execute()
                
                c_title = contest_res.data[0]["title"] if contest_res.data else "Unknown"
                c_reward = contest_res.data[0]["reward_points"] if contest_res.data else 0
                u_name = profile_res.data[0]["username"] if profile_res.data else None
                
                detailed_subs.append({
                    "id": s["id"],
                    "contest_id": s["contest_id"],
                    "telegram_id": s["telegram_id"],
                    "submission_link": s["submission_link"],
                    "status": s["status"],
                    "title": c_title,
                    "reward_points": c_reward,
                    "username": u_name
                })
            return detailed_subs
        except Exception as e:
            logger.error(f"Failed to fetch pending submissions: {e}")
            return []

    def approve_submission(self, submission_id: int) -> bool:
        try:
            # Fetch submission details
            sub_res = self.supabase.table('contest_submissions').select('*').eq('id', submission_id).execute()
            if not sub_res.data or sub_res.data[0]["status"] != "pending":
                return False
                
            sub = sub_res.data[0]
            telegram_id = sub["telegram_id"]
            contest_id = sub["contest_id"]
            
            # Get reward points from contest
            contest_res = self.supabase.table('contests').select('reward_points').eq('id', contest_id).execute()
            reward = contest_res.data[0]["reward_points"] if contest_res.data else 0
            
            # Approve submission
            self.supabase.table('contest_submissions').update({"status": "approved"}).eq('id', submission_id).execute()
            # Award points to user profile
            self.add_points(telegram_id, reward)
            return True
        except Exception as e:
            logger.error(f"Failed to approve submission: {e}")
            return False

    def reject_submission(self, submission_id: int) -> bool:
        try:
            res = self.supabase.table('contest_submissions').update({"status": "rejected"}).eq('id', submission_id).execute()
            return len(res.data) > 0
        except Exception as e:
            logger.error(f"Failed to reject submission: {e}")
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

async def create_profile(telegram_id: int, username: str = None, first_name: str = None, last_name: str = None, referred_by: int = None, is_subscribed: bool = False, total_points: int = 0, language_code: str = 'en') -> Dict[str, Any]:
    return await asyncio.to_thread(_db_impl.create_profile, telegram_id, username, first_name, last_name, referred_by, is_subscribed, total_points, language_code)

async def update_profile_language(telegram_id: int, lang_code: str) -> bool:
    return await asyncio.to_thread(_db_impl.update_profile_language, telegram_id, lang_code)

async def update_profile_wallet(telegram_id: int, wallet_address: str) -> bool:
    return await asyncio.to_thread(_db_impl.update_profile_wallet, telegram_id, wallet_address)

async def update_profile_subscription(telegram_id: int, status: bool) -> bool:
    return await asyncio.to_thread(_db_impl.update_profile_subscription, telegram_id, status)

async def add_points(telegram_id: int, points: int) -> int:
    return await asyncio.to_thread(_db_impl.add_points, telegram_id, points)

async def increment_referral_count(telegram_id: int) -> bool:
    return await asyncio.to_thread(_db_impl.increment_referral_count, telegram_id)

async def get_referral_count(telegram_id: int) -> int:
    return await asyncio.to_thread(_db_impl.get_referral_count, telegram_id)

async def get_referrals(telegram_id: int) -> List[Dict[str, Any]]:
    return await asyncio.to_thread(_db_impl.get_referrals, telegram_id)

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

async def get_users_to_notify() -> List[Dict[str, Any]]:
    return await asyncio.to_thread(_db_impl.get_users_to_notify)

# --- EXPANDED SNAPSHOTS & CONTESTS ---

async def create_claim_snapshot(conversion_rate: float) -> bool:
    return await asyncio.to_thread(_db_impl.create_claim_snapshot, conversion_rate)

async def get_claim_snapshot(telegram_id: int) -> Optional[Dict[str, Any]]:
    return await asyncio.to_thread(_db_impl.get_claim_snapshot, telegram_id)

async def claim_tokens(telegram_id: int) -> bool:
    return await asyncio.to_thread(_db_impl.claim_tokens, telegram_id)

async def create_contest(title: str, description: str, reward_points: int) -> int:
    return await asyncio.to_thread(_db_impl.create_contest, title, description, reward_points)

async def get_active_contests() -> List[Dict[str, Any]]:
    return await asyncio.to_thread(_db_impl.get_active_contests)

async def submit_contest(contest_id: int, telegram_id: int, submission_link: str) -> bool:
    return await asyncio.to_thread(_db_impl.submit_contest, contest_id, telegram_id, submission_link)

async def get_pending_submissions() -> List[Dict[str, Any]]:
    return await asyncio.to_thread(_db_impl.get_pending_submissions)

async def approve_submission(submission_id: int) -> bool:
    return await asyncio.to_thread(_db_impl.approve_submission, submission_id)

async def reject_submission(submission_id: int) -> bool:
    return await asyncio.to_thread(_db_impl.reject_submission, submission_id)
