import aiosqlite
from datetime import datetime,timedelta
DB="bot.db"

async def init():
    async with aiosqlite.connect(DB) as d:
        await d.execute("""CREATE TABLE IF NOT EXISTS users(
            uid INT PRIMARY KEY,uname TEXT DEFAULT '',fname TEXT DEFAULT '',
            model TEXT DEFAULT 'mini',premium INT DEFAULT 0,prem_until TEXT,
            banned INT DEFAULT 0,muted INT DEFAULT 0,ban_reason TEXT,
            mute_reason TEXT,admin INT DEFAULT 0,total_msg INT DEFAULT 0,
            total_img INT DEFAULT 0,joined TEXT DEFAULT CURRENT_TIMESTAMP)""")
        await d.execute("""CREATE TABLE IF NOT EXISTS daily(
            uid INT,day TEXT,msgs INT DEFAULT 0,imgs INT DEFAULT 0,
            PRIMARY KEY(uid,day))""")
        await d.execute("""CREATE TABLE IF NOT EXISTS history(
            id INTEGER PRIMARY KEY AUTOINCREMENT,uid INT,role TEXT,content TEXT)""")
        await d.execute("""CREATE TABLE IF NOT EXISTS promos(
            code TEXT PRIMARY KEY,days INT DEFAULT 30,max_use INT DEFAULT 1,
            used INT DEFAULT 0,active INT DEFAULT 1)""")
        await d.execute("""CREATE TABLE IF NOT EXISTS used_promos(
            uid INT,code TEXT,PRIMARY KEY(uid,code))""")
        await d.commit()
    print("✅ Database ready")

async def add_user(uid,uname,fname):
    async with aiosqlite.connect(DB) as d:
        await d.execute("INSERT OR IGNORE INTO users(uid,uname,fname) VALUES(?,?,?)",(uid,uname or"",fname or""))
        await d.execute("UPDATE users SET uname=?,fname=? WHERE uid=?",(uname or"",fname or"",uid))
        await d.commit()

async def get_user(uid):
    async with aiosqlite.connect(DB) as d:
        d.row_factory=aiosqlite.Row
        r=await d.execute("SELECT * FROM users WHERE uid=?",(uid,))
        return await r.fetchone()

async def find_user(uname):
    async with aiosqlite.connect(DB) as d:
        d.row_factory=aiosqlite.Row
        r=await d.execute("SELECT * FROM users WHERE uname=?",(uname.lstrip("@"),))
        return await r.fetchone()

async def set_model(uid,model):
    async with aiosqlite.connect(DB) as d:
        await d.execute("UPDATE users SET model=? WHERE uid=?",(model,uid))
        await d.commit()

async def check_premium(uid):
    u=await get_user(uid)
    if not u or not u["premium"]:return False
    if u["prem_until"]:
        if datetime.fromisoformat(u["prem_until"])<datetime.now():
            async with aiosqlite.connect(DB) as d:
                await d.execute("UPDATE users SET premium=0,prem_until=NULL WHERE uid=?",(uid,))
                await d.commit()
            return False
    return True

async def give_premium(uid,days=30):
    until=(datetime.now()+timedelta(days=days)).isoformat()
    async with aiosqlite.connect(DB) as d:
        await d.execute("UPDATE users SET premium=1,prem_until=? WHERE uid=?",(until,uid))
        await d.commit()

async def remove_premium(uid):
    async with aiosqlite.connect(DB) as d:
        await d.execute("UPDATE users SET premium=0,prem_until=NULL WHERE uid=?",(uid,))
        await d.commit()

async def ban_user(uid,reason=None):
    async with aiosqlite.connect(DB) as d:
        await d.execute("UPDATE users SET banned=1,ban_reason=? WHERE uid=?",(reason,uid))
        await d.commit()

async def unban_user(uid):
    async with aiosqlite.connect(DB) as d:
        await d.execute("UPDATE users SET banned=0,ban_reason=NULL WHERE uid=?",(uid,))
        await d.commit()

async def mute_user(uid,reason=None):
    async with aiosqlite.connect(DB) as d:
        await d.execute("UPDATE users SET muted=1,mute_reason=? WHERE uid=?",(reason,uid))
        await d.commit()

async def unmute_user(uid):
    async with aiosqlite.connect(DB) as d:
        await d.execute("UPDATE users SET muted=0,mute_reason=NULL WHERE uid=?",(uid,))
        await d.commit()

async def set_admin(uid,val=True):
    async with aiosqlite.connect(DB) as d:
        await d.execute("UPDATE users SET admin=? WHERE uid=?",(1 if val else 0,uid))
        await d.commit()

async def is_admin(uid):
    u=await get_user(uid)
    return bool(u and u["admin"])

async def get_usage(uid):
    day=datetime.now().strftime("%Y-%m-%d")
    async with aiosqlite.connect(DB) as d:
        d.row_factory=aiosqlite.Row
        r=await d.execute("SELECT * FROM daily WHERE uid=? AND day=?",(uid,day))
        row=await r.fetchone()
        if not row:
            await d.execute("INSERT INTO daily(uid,day) VALUES(?,?)",(uid,day))
            await d.commit()
            return{"msgs":0,"imgs":0}
        return{"msgs":row["msgs"],"imgs":row["imgs"]}

async def add_msg(uid):
    day=datetime.now().strftime("%Y-%m-%d")
    async with aiosqlite.connect(DB) as d:
        await d.execute("INSERT INTO daily(uid,day,msgs) VALUES(?,?,1) ON CONFLICT(uid,day) DO UPDATE SET msgs=msgs+1",(uid,day))
        await d.execute("UPDATE users SET total_msg=total_msg+1 WHERE uid=?",(uid,))
        await d.commit()

async def add_img(uid):
    day=datetime.now().strftime("%Y-%m-%d")
    async with aiosqlite.connect(DB) as d:
        await d.execute("INSERT INTO daily(uid,day,imgs) VALUES(?,?,1) ON CONFLICT(uid,day) DO UPDATE SET imgs=imgs+1",(uid,day))
        await d.execute("UPDATE users SET total_img=total_img+1 WHERE uid=?",(uid,))
        await d.commit()

async def can_msg(uid,free,prem_limit):
    p=await check_premium(uid)
    lim=prem_limit if p else free
    u=await get_usage(uid)
    left=max(0,lim-u["msgs"])
    return left>0,left

async def can_img(uid,free,prem_limit):
    p=await check_premium(uid)
    lim=prem_limit if p else free
    u=await get_usage(uid)
    left=max(0,lim-u["imgs"])
    return left>0,left

async def save_hist(uid,role,text):
    async with aiosqlite.connect(DB) as d:
        await d.execute("INSERT INTO history(uid,role,content) VALUES(?,?,?)",(uid,role,text))
        await d.commit()

async def get_hist(uid,n=10):
    async with aiosqlite.connect(DB) as d:
        d.row_factory=aiosqlite.Row
        r=await d.execute("SELECT role,content FROM history WHERE uid=? ORDER BY id DESC LIMIT ?",(uid,n))
        rows=await r.fetchall()
        return[{"role":r["role"],"content":r["content"]}for r in reversed(rows)]

async def clear_hist(uid):
    async with aiosqlite.connect(DB) as d:
        await d.execute("DELETE FROM history WHERE uid=?",(uid,))
        await d.commit()

async def create_promo(code,days,max_use):
    async with aiosqlite.connect(DB) as d:
        await d.execute("INSERT OR REPLACE INTO promos(code,days,max_use) VALUES(?,?,?)",(code,days,max_use))
        await d.commit()

async def use_promo(uid,code):
    async with aiosqlite.connect(DB) as d:
        d.row_factory=aiosqlite.Row
        r=await d.execute("SELECT * FROM promos WHERE code=? AND active=1",(code,))
        p=await r.fetchone()
        if not p:return False,"❌ Промокод не найден или неактивен"
        if p["used"]>=p["max_use"]:return False,"❌ Промокод уже использован максимальное число раз"
        r=await d.execute("SELECT * FROM used_promos WHERE uid=? AND code=?",(uid,code))
        if await r.fetchone():return False,"❌ Вы уже активировали этот промокод"
        await d.execute("INSERT INTO used_promos(uid,code) VALUES(?,?)",(uid,code))
        await d.execute("UPDATE promos SET used=used+1 WHERE code=?",(code,))
        await d.commit()
    await give_premium(uid,p["days"])
    return True,f"✅ Премиум активирован на {p['days']} дней! 🎉"

async def get_promos():
    async with aiosqlite.connect(DB) as d:
        d.row_factory=aiosqlite.Row
        r=await d.execute("SELECT * FROM promos")
        return await r.fetchall()

async def count_users():
    async with aiosqlite.connect(DB) as d:
        return(await(await d.execute("SELECT COUNT(*) FROM users")).fetchone())[0]

async def count_premium():
    async with aiosqlite.connect(DB) as d:
        return(await(await d.execute("SELECT COUNT(*) FROM users WHERE premium=1")).fetchone())[0]

async def count_active():
    day=datetime.now().strftime("%Y-%m-%d")
    async with aiosqlite.connect(DB) as d:
        return(await(await d.execute("SELECT COUNT(DISTINCT uid) FROM daily WHERE day=?",(day,))).fetchone())[0]

async def count_banned():
    async with aiosqlite.connect(DB) as d:
        return(await(await d.execute("SELECT COUNT(*) FROM users WHERE banned=1")).fetchone())[0]

async def list_users(n=20):
    async with aiosqlite.connect(DB) as d:
        d.row_factory=aiosqlite.Row
        r=await d.execute("SELECT * FROM users ORDER BY joined DESC LIMIT ?",(n,))
        return await r.fetchall()

async def all_users():
    async with aiosqlite.connect(DB) as d:
        d.row_factory=aiosqlite.Row
        r=await d.execute("SELECT uid FROM users")
        return await r.fetchall()

async def lookup(text):
    text=text.strip()
    if text.startswith("@"):return await find_user(text)
    elif text.isdigit():return await get_user(int(text))
    return None
