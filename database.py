import aiosqlite
from datetime import datetime, timedelta

DB = "bot.db"

async def init_db():
    async with aiosqlite.connect(DB) as db:
        await db.execute("""CREATE TABLE IF NOT EXISTS users(
            uid INTEGER PRIMARY KEY, uname TEXT DEFAULT '',
            fname TEXT DEFAULT '', joined TEXT DEFAULT CURRENT_TIMESTAMP,
            model TEXT DEFAULT 'gpt4o_mini', premium INTEGER DEFAULT 0,
            prem_until TEXT, banned INTEGER DEFAULT 0, muted INTEGER DEFAULT 0,
            ban_reason TEXT, mute_reason TEXT, admin INTEGER DEFAULT 0,
            msgs INTEGER DEFAULT 0, imgs INTEGER DEFAULT 0)""")
        await db.execute("""CREATE TABLE IF NOT EXISTS daily(
            uid INTEGER, day TEXT, msgs INTEGER DEFAULT 0,
            imgs INTEGER DEFAULT 0, PRIMARY KEY(uid,day))""")
        await db.execute("""CREATE TABLE IF NOT EXISTS history(
            id INTEGER PRIMARY KEY AUTOINCREMENT, uid INTEGER,
            role TEXT, content TEXT)""")
        await db.execute("""CREATE TABLE IF NOT EXISTS promos(
            code TEXT PRIMARY KEY, days INTEGER DEFAULT 30,
            max_use INTEGER DEFAULT 1, used INTEGER DEFAULT 0,
            active INTEGER DEFAULT 1)""")
        await db.execute("""CREATE TABLE IF NOT EXISTS used_promos(
            uid INTEGER, code TEXT, PRIMARY KEY(uid,code))""")
        await db.commit()
    print("✅ DB OK")

async def add_user(uid, uname, fname):
    async with aiosqlite.connect(DB) as db:
        await db.execute("INSERT OR IGNORE INTO users(uid,uname,fname) VALUES(?,?,?)",
            (uid, uname or "", fname or ""))
        await db.execute("UPDATE users SET uname=?,fname=? WHERE uid=?",
            (uname or "", fname or "", uid))
        await db.commit()

async def get_user(uid):
    async with aiosqlite.connect(DB) as db:
        db.row_factory = aiosqlite.Row
        c = await db.execute("SELECT * FROM users WHERE uid=?", (uid,))
        return await c.fetchone()

async def find_user(uname):
    uname = uname.lstrip("@")
    async with aiosqlite.connect(DB) as db:
        db.row_factory = aiosqlite.Row
        c = await db.execute("SELECT * FROM users WHERE uname=?", (uname,))
        return await c.fetchone()

async def set_model(uid, m):
    async with aiosqlite.connect(DB) as db:
        await db.execute("UPDATE users SET model=? WHERE uid=?", (m, uid))
        await db.commit()

async def is_prem(uid):
    u = await get_user(uid)
    if not u or not u["premium"]: return False
    if u["prem_until"]:
        if datetime.fromisoformat(u["prem_until"]) < datetime.now():
            async with aiosqlite.connect(DB) as db:
                await db.execute("UPDATE users SET premium=0,prem_until=NULL WHERE uid=?", (uid,))
                await db.commit()
            return False
    return True

async def give_prem(uid, days=30):
    until = (datetime.now() + timedelta(days=days)).isoformat()
    async with aiosqlite.connect(DB) as db:
        await db.execute("UPDATE users SET premium=1,prem_until=? WHERE uid=?", (until, uid))
        await db.commit()

async def rm_prem(uid):
    async with aiosqlite.connect(DB) as db:
        await db.execute("UPDATE users SET premium=0,prem_until=NULL WHERE uid=?", (uid,))
        await db.commit()

async def ban(uid, reason=None):
    async with aiosqlite.connect(DB) as db:
        await db.execute("UPDATE users SET banned=1,ban_reason=? WHERE uid=?", (reason, uid))
        await db.commit()

async def unban(uid):
    async with aiosqlite.connect(DB) as db:
        await db.execute("UPDATE users SET banned=0,ban_reason=NULL WHERE uid=?", (uid,))
        await db.commit()

async def mute(uid, reason=None):
    async with aiosqlite.connect(DB) as db:
        await db.execute("UPDATE users SET muted=1,mute_reason=? WHERE uid=?", (reason, uid))
        await db.commit()

async def unmute(uid):
    async with aiosqlite.connect(DB) as db:
        await db.execute("UPDATE users SET muted=0,mute_reason=NULL WHERE uid=?", (uid,))
        await db.commit()

async def set_admin(uid, val=True):
    async with aiosqlite.connect(DB) as db:
        await db.execute("UPDATE users SET admin=? WHERE uid=?", (1 if val else 0, uid))
        await db.commit()

async def is_admin(uid):
    u = await get_user(uid)
    return bool(u and u["admin"])

async def get_usage(uid):
    day = datetime.now().strftime("%Y-%m-%d")
    async with aiosqlite.connect(DB) as db:
        db.row_factory = aiosqlite.Row
        c = await db.execute("SELECT * FROM daily WHERE uid=? AND day=?", (uid, day))
        r = await c.fetchone()
        if not r:
            await db.execute("INSERT INTO daily(uid,day) VALUES(?,?)", (uid, day))
            await db.commit()
            return {"msgs": 0, "imgs": 0}
        return {"msgs": r["msgs"], "imgs": r["imgs"]}

async def inc_msgs(uid):
    day = datetime.now().strftime("%Y-%m-%d")
    async with aiosqlite.connect(DB) as db:
        await db.execute("""INSERT INTO daily(uid,day,msgs) VALUES(?,?,1)
            ON CONFLICT(uid,day) DO UPDATE SET msgs=msgs+1""", (uid, day))
        await db.execute("UPDATE users SET msgs=msgs+1 WHERE uid=?", (uid,))
        await db.commit()

async def inc_imgs(uid):
    day = datetime.now().strftime("%Y-%m-%d")
    async with aiosqlite.connect(DB) as db:
        await db.execute("""INSERT INTO daily(uid,day,imgs) VALUES(?,?,1)
            ON CONFLICT(uid,day) DO UPDATE SET imgs=imgs+1""", (uid, day))
        await db.execute("UPDATE users SET imgs=imgs+1 WHERE uid=?", (uid,))
        await db.commit()

async def can_msg(uid):
    from config import FREE_MSG, PREM_MSG
    p = await is_prem(uid)
    lim = PREM_MSG if p else FREE_MSG
    u = await get_usage(uid)
    left = max(0, lim - u["msgs"])
    return left > 0, left

async def can_img(uid):
    from config import FREE_IMG, PREM_IMG
    p = await is_prem(uid)
    lim = PREM_IMG if p else FREE_IMG
    u = await get_usage(uid)
    left = max(0, lim - u["imgs"])
    return left > 0, left

async def add_hist(uid, role, text):
    async with aiosqlite.connect(DB) as db:
        await db.execute("INSERT INTO history(uid,role,content) VALUES(?,?,?)", (uid, role, text))
        await db.commit()

async def get_hist(uid, n=10):
    async with aiosqlite.connect(DB) as db:
        db.row_factory = aiosqlite.Row
        c = await db.execute("SELECT role,content FROM history WHERE uid=? ORDER BY id DESC LIMIT ?", (uid, n))
        rows = await c.fetchall()
        return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]

async def clear_hist(uid):
    async with aiosqlite.connect(DB) as db:
        await db.execute("DELETE FROM history WHERE uid=?", (uid,))
        await db.commit()

async def create_promo(code, days, uses):
    async with aiosqlite.connect(DB) as db:
        await db.execute("INSERT OR REPLACE INTO promos(code,days,max_use) VALUES(?,?,?)", (code, days, uses))
        await db.commit()

async def use_promo(uid, code):
    async with aiosqlite.connect(DB) as db:
        db.row_factory = aiosqlite.Row
        c = await db.execute("SELECT * FROM promos WHERE code=? AND active=1", (code,))
        p = await c.fetchone()
        if not p: return False, "❌ Не найден"
        if p["used"] >= p["max_use"]: return False, "❌ Исчерпан"
        c = await db.execute("SELECT * FROM used_promos WHERE uid=? AND code=?", (uid, code))
        if await c.fetchone(): return False, "❌ Уже использован"
        await db.execute("INSERT INTO used_promos(uid,code) VALUES(?,?)", (uid, code))
        await db.execute("UPDATE promos SET used=used+1 WHERE code=?", (code,))
        await db.commit()
    await give_prem(uid, p["days"])
    return True, f"✅ Премиум на {p['days']} дней!"

async def all_promos():
    async with aiosqlite.connect(DB) as db:
        db.row_factory = aiosqlite.Row
        c = await db.execute("SELECT * FROM promos")
        return await c.fetchall()

async def total_users():
    async with aiosqlite.connect(DB) as db:
        return (await (await db.execute("SELECT COUNT(*) FROM users")).fetchone())[0]

async def prem_count():
    async with aiosqlite.connect(DB) as db:
        return (await (await db.execute("SELECT COUNT(*) FROM users WHERE premium=1")).fetchone())[0]

async def today_active():
    day = datetime.now().strftime("%Y-%m-%d")
    async with aiosqlite.connect(DB) as db:
        return (await (await db.execute("SELECT COUNT(DISTINCT uid) FROM daily WHERE day=?", (day,))).fetchone())[0]

async def all_users_list(n=10000):
    async with aiosqlite.connect(DB) as db:
        db.row_factory = aiosqlite.Row
        c = await db.execute("SELECT * FROM users ORDER BY joined DESC LIMIT ?", (n,))
        return await c.fetchall()
