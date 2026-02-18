import logging
import aiohttp
import json
from telegram import (
    Update, LabeledPrice,
    InlineKeyboardButton as IKB, InlineKeyboardMarkup as IKM,
    ReplyKeyboardMarkup as RKM, KeyboardButton as KB
)
from telegram.ext import (
    Application, CommandHandler as CH, MessageHandler as MH,
    CallbackQueryHandler as CQ, ConversationHandler as CV,
    PreCheckoutQueryHandler, filters
)
from config import *
from database import *

logging.basicConfig(level=logging.INFO)
TF = filters.TEXT & ~filters.COMMAND

def menu_kb():
    return RKM([[KB("💬 Чат"),KB("🎨 Фото")],[KB("👤 Профиль"),KB("📊 Стата")],[KB("🤖 Модель"),KB("⭐ Премиум")],[KB("🗑 Очистить"),KB("❓ Помощь")]],resize_keyboard=True)

def models_kb(cur,prem):
    kb=[]
    for k,m in MODELS.items():
        ch=" ✅" if k==cur else ""
        lo=" 🔒" if m["prem"] and not prem else ""
        kb.append([IKB(f"{m['name']}{ch}{lo}",callback_data=f"m_{k}")])
    kb.append([IKB("🔙",callback_data="close")])
    return IKM(kb)

def profile_kb():
    return IKM([[IKB("⭐ Премиум",callback_data="buy_prem"),IKB("🎁 Промокод",callback_data="use_promo")],[IKB("🤖 Модель",callback_data="models"),IKB("🗑 Очистить",callback_data="clear")]])

def prem_kb():
    return IKM([[IKB(f"⭐ {PREM_PRICE} Stars",callback_data="pay")],[IKB("🎁 Промокод",callback_data="use_promo")],[IKB("🔙",callback_data="close")]])

def adm_kb():
    return IKM([[IKB("📊 Стата",callback_data="a_stats"),IKB("👥 Юзеры",callback_data="a_users")],[IKB("🔨 Бан",callback_data="a_ban"),IKB("✅ Разбан",callback_data="a_unban")],[IKB("🔇 Мут",callback_data="a_mute"),IKB("🔊 Размут",callback_data="a_unmute")],[IKB("🎁 Промо+",callback_data="a_promo"),IKB("📋 Промо",callback_data="a_promos")],[IKB("⭐ Дать",callback_data="a_give"),IKB("❌ Снять",callback_data="a_rm")],[IKB("📢 Рассылка",callback_data="a_bc"),IKB("🔍 Найти",callback_data="a_find")]])

def back_kb():
    return IKM([[IKB("🔙 Админка",callback_data="a_back")]])

async def ask_ai(messages, model_id):
    headers = {"Content-Type": "application/json"}
    payload = {
        "model": model_id,
        "messages": messages,
        "max_tokens": 2048,
        "temperature": 0.7
    }
    async with aiohttp.ClientSession() as session:
        for url in API_URLS:
            try:
                async with session.post(url, json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        answer = data["choices"][0]["message"]["content"]
                        if answer and len(answer) > 2:
                            return answer
            except:
                continue
        try:
            import g4f
            r = await g4f.ChatCompletion.create_async(model="gpt-4o-mini", messages=messages, timeout=30)
            if r and len(str(r)) > 5:
                return r
        except:
            pass
    return "⚠️ AI временно недоступен. Попробуйте через минуту или смените модель /model"

async def cmd_start(u,c):
    usr=u.effective_user
    await add_user(usr.id,usr.username,usr.first_name)
    await u.message.reply_text(f"🤖 <b>FreeGPT</b>\n\nПривет, <b>{usr.first_name}</b>! 👋\n\n<b>Возможности:</b>\n├ 💬 Чат с AI\n├ 🎨 Генерация\n├ 📝 Код и тексты\n└ 🧮 Задачи\n\n📦 Бесплатно: {FREE_MSG} сообщений/день\n⭐ Премиум: {PREM_MSG} сообщений/день\n\nПишите! 👇",parse_mode="HTML",reply_markup=menu_kb())

async def cmd_help(u,c):
    await u.message.reply_text("❓ <b>Помощь</b>\n\n/start — запуск\n/profile — профиль\n/model — модель\n/image текст — картинка\n/premium — премиум\n/promo — промокод\n/stats — стата\n/clear — очистить\n/admin — админка\n\n🔐 <code>/login adm9912</code>",parse_mode="HTML")

async def cmd_profile(u,c):
    uid=u.effective_user.id
    usr=await get_user(uid)
    if not usr:
        if u.callback_query:
            await u.callback_query.edit_message_text("❌ /start")
        else:
            await u.message.reply_text("❌ /start")
        return
    prem=await is_prem(uid)
    usage=await get_usage(uid)
    ml=PREM_MSG if prem else FREE_MSG
    il=PREM_IMG if prem else FREE_IMG
    def bar(x,t):
        if t==0: return "░"*10
        p=min(x/t,1)
        return "█"*int(p*10)+"░"*(10-int(p*10))
    st="🚫 Бан" if usr["banned"] else "🔇 Мут" if usr["muted"] else "⭐ Premium" if prem else "🆓 Free"
    mn=MODELS.get(usr["model"],{}).get("name","?")
    t=f"👤 <b>Профиль</b>\n\n🆔 <code>{uid}</code>\n👤 <b>{usr['fname']}</b>\n📛 @{usr['uname'] or '—'}\n🏷 {st}\n🤖 {mn}\n\n💬 {usage['msgs']}/{ml}\n[{bar(usage['msgs'],ml)}]\n\n🎨 {usage['imgs']}/{il}\n[{bar(usage['imgs'],il)}]\n\n📈 💬{usr['msgs']} 🎨{usr['imgs']}"
    if u.callback_query:
        await u.callback_query.edit_message_text(t,parse_mode="HTML",reply_markup=profile_kb())
    else:
        await u.message.reply_text(t,parse_mode="HTML",reply_markup=profile_kb())

async def cmd_models(u,c):
    uid=u.effective_user.id
    usr=await get_user(uid)
    prem=await is_prem(uid)
    cur=usr["model"] if usr else "gpt4o_mini"
    t="🤖 <b>Модели</b>\n\n✅ текущая | 🔒 Премиум"
    if u.callback_query:
        await u.callback_query.edit_message_text(t,parse_mode="HTML",reply_markup=models_kb(cur,prem))
    else:
        await u.message.reply_text(t,parse_mode="HTML",reply_markup=models_kb(cur,prem))

async def cmd_stats(u,c):
    uid=u.effective_user.id
    usr=await get_user(uid)
    usage=await get_usage(uid)
    tu=await total_users()
    pc=await prem_count()
    ta=await today_active()
    t=f"📊 <b>Статистика</b>\n\n👤 💬{usr['msgs'] if usr else 0} 🎨{usr['imgs'] if usr else 0}\nСегодня: 💬{usage['msgs']} 🎨{usage['imgs']}\n\n🌐 👥{tu} ⭐{pc} 🟢{ta}"
    await u.message.reply_text(t,parse_mode="HTML")

async def cmd_premium(u,c):
    uid=u.effective_user.id
    prem=await is_prem(uid)
    if prem:
        t="⭐ <b>Премиум активен!</b> 🎉"
        kb=None
    else:
        t=f"⭐ <b>Премиум</b>\n\n💬 {PREM_MSG}/день\n🎨 {PREM_IMG}/день\n🚀 GPT-4 Turbo\n\n💰 {PREM_PRICE} Stars | 📅 {PREM_DAYS} дней"
        kb=prem_kb()
    if u.callback_query:
        await u.callback_query.edit_message_text(t,parse_mode="HTML",reply_markup=kb)
    else:
        await u.message.reply_text(t,parse_mode="HTML",reply_markup=kb)

async def cmd_clear(u,c):
    await clear_hist(u.effective_user.id)
    if u.callback_query:
        await u.callback_query.answer("✅ Очищено!",show_alert=True)
    else:
        await u.message.reply_text("🗑 Очищено!")

async def cmd_image(u,c):
    uid=u.effective_user.id
    usr=await get_user(uid)
    if not usr:
        await u.message.reply_text("❌ /start")
        return
    if usr["banned"]:
        await u.message.reply_text("🚫")
        return
    if not c.args:
        await u.message.reply_text("🎨 <code>/image описание</code>",parse_mode="HTML")
        return
    ok,left=await can_img(uid)
    if not ok:
        await u.message.reply_text("⚠️ Лимит! Купите ⭐")
        return
    prompt=" ".join(c.args)
    msg=await u.message.reply_text("🎨 Генерирую... ⏳")
    try:
        r=await ask_ai([{"role":"user","content":f"Create a very detailed, vivid image description in English for an artist to draw: {prompt}. Describe colors, lighting, style, composition, mood in detail."}],"gpt-4o-mini")
        await inc_imgs(uid)
        await msg.edit_text(f"🎨 <b>Готово!</b>\n\n📝 Запрос: <i>{prompt}</i>\n\n🖼 Описание:\n{r[:800]}\n\n🎨 Осталось: {left-1}",parse_mode="HTML")
    except Exception as e:
        await msg.edit_text(f"❌ {e}")

async def handle_ai(u,c):
    uid=u.effective_user.id
    usr=await get_user(uid)
    if not usr:
        await u.message.reply_text("❌ /start")
        return
    if usr["banned"]:
        await u.message.reply_text(f"🚫 Бан: {usr['ban_reason'] or '—'}")
        return
    if usr["muted"]:
        await u.message.reply_text(f"🔇 Мут: {usr['mute_reason'] or '—'}")
        return
    ok,left=await can_msg(uid)
    if not ok:
        await u.message.reply_text("⚠️ <b>Лимит!</b> Купите ⭐ Премиум",parse_mode="HTML")
        return
    text=u.message.text
    mk=usr["model"]
    mi=MODELS.get(mk,MODELS["gpt4o_mini"])
    await c.bot.send_chat_action(uid,"typing")
    hist=await get_hist(uid,10)
    msgs=[{"role":"system","content":"Ты FreeGPT, AI-ассистент. Отвечай кратко, полезно, дружелюбно. Используй русский язык и эмодзи."}]
    msgs.extend(hist)
    msgs.append({"role":"user","content":text})
    answer=await ask_ai(msgs,mi["id"])
    await add_hist(uid,"user",text)
    await add_hist(uid,"assistant",answer)
    await inc_msgs(uid)
    left-=1
    try:
        await u.message.reply_text(f"{answer}\n\n<i>💬 {left} | {mi['name']}</i>",parse_mode="HTML")
    except:
        await u.message.reply_text(f"{answer}\n\n💬 {left}")

async def pay_cb(u,c):
    q=u.callback_query
    await q.answer()
    await c.bot.send_invoice(q.from_user.id,"⭐ Премиум",f"Премиум {PREM_DAYS} дней","prem","XTR",[LabeledPrice("Premium",PREM_PRICE)])

async def precheckout_h(u,c):
    await u.pre_checkout_query.answer(ok=True)

async def payment_ok(u,c):
    await give_prem(u.effective_user.id,PREM_DAYS)
    await u.message.reply_text(f"🎉 <b>Премиум на {PREM_DAYS} дней!</b>",parse_mode="HTML")

async def cmd_login(u,c):
    try:
        await u.message.delete()
    except:
        pass
    if not c.args:
        await c.bot.send_message(u.effective_user.id,"🔐 /login пароль")
        return
    if c.args[0]==ADMIN_PASS:
        await set_admin(u.effective_user.id)
        await c.bot.send_message(u.effective_user.id,"✅ <b>Админ!</b> /admin",parse_mode="HTML")
    else:
        await c.bot.send_message(u.effective_user.id,"❌ Неверно")

async def cmd_logout(u,c):
    await set_admin(u.effective_user.id,False)
    await u.message.reply_text("🔓 Вышли")

async def cmd_admin(u,c):
    if not await is_admin(u.effective_user.id):
        await u.message.reply_text("❌ /login пароль")
        return
    await u.message.reply_text("🛡 <b>Админка</b>",parse_mode="HTML",reply_markup=adm_kb())

S_BAN,S_BAN_R,S_UNBAN,S_MUTE,S_MUTE_R,S_UNMUTE,S_PC,S_PD,S_PU,S_GP,S_GPD,S_RP,S_BC,S_FIND,S_UPROMO=range(15)

async def _f(t):
    t=t.strip()
    if t.startswith("@"):
        return await find_user(t)
    elif t.isdigit():
        return await get_user(int(t))
    return None

async def cancel_h(u,c):
    await u.message.reply_text("❌ /admin")
    return CV.END

async def a_ban_s(u,c):
    await u.callback_query.answer()
    await u.callback_query.edit_message_text("🔨 @username или ID:")
    return S_BAN

async def a_ban_1(u,c):
    usr=await _f(u.message.text)
    if not usr:
        await u.message.reply_text("❌")
        return S_BAN
    c.user_data["tid"]=usr["uid"]
    c.user_data["tn"]=usr["fname"]
    await u.message.reply_text(f"Причина для {usr['fname']}:")
    return S_BAN_R

async def a_ban_2(u,c):
    await ban(c.user_data["tid"],u.message.text)
    await u.message.reply_text(f"✅ {c.user_data['tn']} забанен!")
    try:
        await c.bot.send_message(c.user_data["tid"],f"🚫 Бан: {u.message.text}")
    except:
        pass
    return CV.END

async def a_unban_s(u,c):
    await u.callback_query.answer()
    await u.callback_query.edit_message_text("✅ @username или ID:")
    return S_UNBAN

async def a_unban_1(u,c):
    usr=await _f(u.message.text)
    if not usr:
        await u.message.reply_text("❌")
        return S_UNBAN
    await unban(usr["uid"])
    await u.message.reply_text(f"✅ {usr['fname']} разбанен!")
    try:
        await c.bot.send_message(usr["uid"],"✅ Разбанены!")
    except:
        pass
    return CV.END

async def a_mute_s(u,c):
    await u.callback_query.answer()
    await u.callback_query.edit_message_text("🔇 @username или ID:")
    return S_MUTE

async def a_mute_1(u,c):
    usr=await _f(u.message.text)
    if not usr:
        await u.message.reply_text("❌")
        return S_MUTE
    c.user_data["tid"]=usr["uid"]
    c.user_data["tn"]=usr["fname"]
    await u.message.reply_text(f"Причина для {usr['fname']}:")
    return S_MUTE_R

async def a_mute_2(u,c):
    await mute(c.user_data["tid"],u.message.text)
    await u.message.reply_text(f"✅ {c.user_data['tn']} замьючен!")
    try:
        await c.bot.send_message(c.user_data["tid"],f"🔇 Мут: {u.message.text}")
    except:
        pass
    return CV.END

async def a_unmute_s(u,c):
    await u.callback_query.answer()
    await u.callback_query.edit_message_text("🔊 @username или ID:")
    return S_UNMUTE

async def a_unmute_1(u,c):
    usr=await _f(u.message.text)
    if not usr:
        await u.message.reply_text("❌")
        return S_UNMUTE
    await unmute(usr["uid"])
    await u.message.reply_text("✅ Размьючен!")
    return CV.END

async def a_promo_s(u,c):
    await u.callback_query.answer()
    await u.callback_query.edit_message_text("🎁 Код:")
    return S_PC

async def a_promo_1(u,c):
    c.user_data["pc"]=u.message.text.upper()
    await u.message.reply_text("Дней?")
    return S_PD

async def a_promo_2(u,c):
    try:
        c.user_data["pd"]=int(u.message.text)
    except:
        await u.message.reply_text("Число!")
        return S_PD
    await u.message.reply_text("Использований?")
    return S_PU

async def a_promo_3(u,c):
    try:
        uses=int(u.message.text)
    except:
        await u.message.reply_text("Число!")
        return S_PU
    await create_promo(c.user_data["pc"],c.user_data["pd"],uses)
    await u.message.reply_text(f"✅ <code>{c.user_data['pc']}</code> {c.user_data['pd']}дн {uses}раз",parse_mode="HTML")
    return CV.END

async def a_give_s(u,c):
    await u.callback_query.answer()
    await u.callback_query.edit_message_text("⭐ @username или ID:")
    return S_GP

async def a_give_1(u,c):
    usr=await _f(u.message.text)
    if not usr:
        await u.message.reply_text("❌")
        return S_GP
    c.user_data["tid"]=usr["uid"]
    c.user_data["tn"]=usr["fname"]
    await u.message.reply_text("Дней?")
    return S_GPD

async def a_give_2(u,c):
    try:
        d=int(u.message.text)
    except:
        await u.message.reply_text("Число!")
        return S_GPD
    await give_prem(c.user_data["tid"],d)
    await u.message.reply_text(f"✅ {c.user_data['tn']} +{d}дн!")
    try:
        await c.bot.send_message(c.user_data["tid"],f"🎉 Премиум {d} дней!")
    except:
        pass
    return CV.END

async def a_rm_s(u,c):
    await u.callback_query.answer()
    await u.callback_query.edit_message_text("❌ @username или ID:")
    return S_RP

async def a_rm_1(u,c):
    usr=await _f(u.message.text)
    if not usr:
        await u.message.reply_text("❌")
        return S_RP
    await rm_prem(usr["uid"])
    await u.message.reply_text("✅ Снят!")
    return CV.END

async def a_bc_s(u,c):
    await u.callback_query.answer()
    await u.callback_query.edit_message_text("📢 Текст:")
    return S_BC

async def a_bc_1(u,c):
    text=u.message.text
    users=await all_users_list()
    s=0
    f=0
    for usr in users:
        try:
            await c.bot.send_message(usr["uid"],f"📢 <b>FreeGPT</b>\n\n{text}",parse_mode="HTML")
            s+=1
        except:
            f+=1
    await u.message.reply_text(f"✅ {s} отправлено, {f} ошибок")
    return CV.END

async def a_find_s(u,c):
    await u.callback_query.answer()
    await u.callback_query.edit_message_text("🔍 @username или ID:")
    return S_FIND

async def a_find_1(u,c):
    usr=await _f(u.message.text)
    if not usr:
        await u.message.reply_text("❌")
        return CV.END
    st="🚫" if usr["banned"] else "🔇" if usr["muted"] else "⭐" if usr["premium"] else "🆓"
    await u.message.reply_text(f"🔍 <code>{usr['uid']}</code>\n{usr['fname']} @{usr['uname'] or '—'}\n{st} 💬{usr['msgs']} 🎨{usr['imgs']}",parse_mode="HTML")
    return CV.END

async def a_stats_cb(u,c):
    await u.callback_query.answer()
    tu=await total_users()
    pc=await prem_count()
    ta=await today_active()
    await u.callback_query.edit_message_text(f"📊 👥{tu} ⭐{pc} 🟢{ta}",reply_markup=back_kb())

async def a_users_cb(u,c):
    await u.callback_query.answer()
    users=await all_users_list(20)
    t="👥 <b>Юзеры:</b>\n\n"
    for usr in users:
        ic="🚫" if usr["banned"] else "🔇" if usr["muted"] else "⭐" if usr["premium"] else "👤"
        t+=f"{ic} {usr['fname']} <code>{usr['uid']}</code>\n"
    await u.callback_query.edit_message_text(t,parse_mode="HTML",reply_markup=back_kb())

async def a_promos_cb(u,c):
    await u.callback_query.answer()
    ps=await all_promos()
    if not ps:
        t="📋 Нет промокодов"
    else:
        t="📋 <b>Промокоды:</b>\n\n"
        for p in ps:
            t+=f"<code>{p['code']}</code> {p['days']}дн {p['used']}/{p['max_use']}\n"
    await u.callback_query.edit_message_text(t,parse_mode="HTML",reply_markup=back_kb())

async def a_back_cb(u,c):
    await u.callback_query.answer()
    await u.callback_query.edit_message_text("🛡 <b>Админка</b>",parse_mode="HTML",reply_markup=adm_kb())

async def use_promo_s(u,c):
    await u.callback_query.answer()
    await u.callback_query.edit_message_text("🎁 Промокод:")
    return S_UPROMO

async def use_promo_1(u,c):
    ok,msg=await use_promo(u.effective_user.id,u.message.text.strip().upper())
    await u.message.reply_text(msg)
    return CV.END

async def cmd_promo(u,c):
    await u.message.reply_text("🎁 Промокод:")
    return S_UPROMO

async def gen_cb(u,c):
    q=u.callback_query
    d=q.data
    if d=="close":
        await q.answer()
        await q.edit_message_text("✅ Меню 👇")
    elif d=="buy_prem":
        await q.answer()
        await cmd_premium(u,c)
    elif d=="models":
        await q.answer()
        await cmd_models(u,c)
    elif d=="clear":
        await cmd_clear(u,c)
    elif d=="pay":
        await pay_cb(u,c)
    elif d.startswith("m_"):
        k=d[2:]
        if k not in MODELS:
            await q.answer("❌",show_alert=True)
            return
        m=MODELS[k]
        prem=await is_prem(q.from_user.id)
        if m["prem"] and not prem:
            await q.answer("🔒 Премиум!",show_alert=True)
            return
        await set_model(q.from_user.id,k)
        await q.answer(f"✅ {m['name']}",show_alert=True)
        await q.edit_message_reply_markup(reply_markup=models_kb(k,prem))
    else:
        await q.answer()

async def menu_h(u,c):
    t=u.message.text
    if t=="💬 Чат":
        await u.message.reply_text("💬 Пишите!")
    elif t=="🎨 Фото":
        await u.message.reply_text("🎨 /image описание")
    elif t=="👤 Профиль":
        await cmd_profile(u,c)
    elif t=="📊 Стата":
        await cmd_stats(u,c)
    elif t=="🤖 Модель":
        await cmd_models(u,c)
    elif t=="⭐ Премиум":
        await cmd_premium(u,c)
    elif t=="🗑 Очистить":
        await cmd_clear(u,c)
    elif t=="❓ Помощь":
        await cmd_help(u,c)
    else:
        await handle_ai(u,c)

def main():
    app=Application.builder().token(BOT_TOKEN).build()
    cn=CH("cancel",cancel_h)
    for name,fn in [("start",cmd_start),("help",cmd_help),("profile",cmd_profile),("model",cmd_models),("image",cmd_image),("premium",cmd_premium),("stats",cmd_stats),("clear",cmd_clear),("login",cmd_login),("logout",cmd_logout),("admin",cmd_admin)]:
        app.add_handler(CH(name,fn))
    app.add_handler(PreCheckoutQueryHandler(precheckout_h))
    app.add_handler(MH(filters.SUCCESSFUL_PAYMENT,payment_ok))
    convs=[
        ([CQ(use_promo_s,pattern="^use_promo$"),CH("promo",cmd_promo)],{S_UPROMO:[MH(TF,use_promo_1)]}),
        ([CQ(a_ban_s,pattern="^a_ban$")],{S_BAN:[MH(TF,a_ban_1)],S_BAN_R:[MH(TF,a_ban_2)]}),
        ([CQ(a_unban_s,pattern="^a_unban$")],{S_UNBAN:[MH(TF,a_unban_1)]}),
        ([CQ(a_mute_s,pattern="^a_mute$")],{S_MUTE:[MH(TF,a_mute_1)],S_MUTE_R:[MH(TF,a_mute_2)]}),
        ([CQ(a_unmute_s,pattern="^a_unmute$")],{S_UNMUTE:[MH(TF,a_unmute_1)]}),
        ([CQ(a_promo_s,pattern="^a_promo$")],{S_PC:[MH(TF,a_promo_1)],S_PD:[MH(TF,a_promo_2)],S_PU:[MH(TF,a_promo_3)]}),
        ([CQ(a_give_s,pattern="^a_give$")],{S_GP:[MH(TF,a_give_1)],S_G
