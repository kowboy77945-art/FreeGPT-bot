import os,logging,aiohttp
from telegram import Update,LabeledPrice
from telegram import InlineKeyboardButton as Btn,InlineKeyboardMarkup as Inline
from telegram import ReplyKeyboardMarkup as Reply,KeyboardButton as Key
from telegram.ext import Application,CommandHandler,MessageHandler
from telegram.ext import CallbackQueryHandler,ConversationHandler,PreCheckoutQueryHandler,filters
import db

logging.basicConfig(level=logging.INFO)
TOKEN=os.environ["BOT_TOKEN"]
APASS=os.environ.get("ADMIN_PASS","adm9912")
FREE_MSG=15;FREE_IMG=1;PREM_MSG=999;PREM_IMG=20
STARS_PRICE=100;PREM_DAYS=30
TXT=filters.TEXT&~filters.COMMAND

MODELS={
    "mini":{"name":"⚡ GPT-4o Mini","id":"gpt-4o-mini","lock":False},
    "4o":{"name":"🧠 GPT-4o","id":"gpt-4o","lock":False},
    "turbo":{"name":"🚀 GPT-4 Turbo","id":"gpt-4-turbo","lock":True},
    "35":{"name":"💬 GPT-3.5 Turbo","id":"gpt-3.5-turbo","lock":False}
}

APIS=[
    "https://api.openai4.chat/v1/chat/completions",
    "https://free.gpt.ge/v1/chat/completions"
]

def kb_menu():
    return Reply([
        [Key("💬 Чат с AI"),Key("🎨 Генерация")],
        [Key("👤 Профиль"),Key("📊 Статистика")],
        [Key("🤖 Выбрать модель"),Key("⭐ Премиум")],
        [Key("🗑 Очистить чат"),Key("❓ Помощь")]
    ],resize_keyboard=True)

def kb_models(cur,prem):
    rows=[]
    for k,m in MODELS.items():
        mark=" ✅" if k==cur else ""
        lock=" 🔒" if m["lock"] and not prem else ""
        rows.append([Btn(f"{m['name']}{mark}{lock}",callback_data=f"model:{k}")])
    rows.append([Btn("🔙 Назад",callback_data="close")])
    return Inline(rows)

def kb_profile():
    return Inline([
        [Btn("⭐ Купить Премиум",callback_data="goprem")],
        [Btn("🎁 Ввести промокод",callback_data="promo")],
        [Btn("🤖 Сменить модель",callback_data="gomodel")]
    ])

def kb_premium():
    return Inline([
        [Btn(f"💫 Купить за {STARS_PRICE} Stars",callback_data="pay")],
        [Btn("🎁 У меня есть промокод",callback_data="promo")],
        [Btn("🔙 Назад",callback_data="close")]
    ])

def kb_admin():
    return Inline([
        [Btn("📊 Статистика бота",callback_data="adm:stats")],
        [Btn("👥 Пользователи",callback_data="adm:users")],
        [Btn("🔨 Забанить",callback_data="adm:ban"),Btn("✅ Разбанить",callback_data="adm:unban")],
        [Btn("🔇 Замутить",callback_data="adm:mute"),Btn("🔊 Размутить",callback_data="adm:unmute")],
        [Btn("🎁 Создать промокод",callback_data="adm:mkpromo")],
        [Btn("📋 Список промокодов",callback_data="adm:promos")],
        [Btn("⭐ Выдать премиум",callback_data="adm:givep")],
        [Btn("❌ Снять премиум",callback_data="adm:remp")],
        [Btn("📢 Рассылка",callback_data="adm:broadcast")],
        [Btn("🔍 Найти юзера",callback_data="adm:find")]
    ])

def kb_back():
    return Inline([[Btn("🔙 Назад в админку",callback_data="adm:back")]])

async def ask_ai(messages,model_id):
    headers={"Content-Type":"application/json"}
    body={"model":model_id,"messages":messages,"max_tokens":2048,"temperature":0.7}
    async with aiohttp.ClientSession() as session:
        for url in APIS:
            try:
                async with session.post(url,json=body,headers=headers,timeout=aiohttp.ClientTimeout(total=30)) as resp:
                    if resp.status==200:
                        data=await resp.json()
                        text=data["choices"][0]["message"]["content"]
                        if text and len(text)>3:
                            return text
            except:
                continue
    return "⚠️ AI временно недоступен. Попробуйте через минуту или смените модель."

async def cmd_start(u,c):
    user=u.effective_user
    await db.add_user(user.id,user.username,user.first_name)
    await u.message.reply_text(
        f"🤖 <b>Добро пожаловать в FreeGPT!</b>\n\n"
        f"Привет, <b>{user.first_name}</b>! 👋\n\n"
        f"<b>🎯 Что я умею:</b>\n"
        f"├ 💬 Отвечать на любые вопросы\n"
        f"├ 🎨 Генерировать описания картинок\n"
        f"├ 📝 Писать тексты и код\n"
        f"├ 🌐 Переводить языки\n"
        f"└ 🧮 Решать задачи\n\n"
        f"<b>📦 Бесплатно:</b> {FREE_MSG} сообщений/день\n"
        f"<b>⭐ Премиум:</b> {PREM_MSG} сообщений/день\n\n"
        f"Просто напишите мне сообщение! 👇",
        parse_mode="HTML",reply_markup=kb_menu())

async def cmd_help(u,c):
    await u.message.reply_text(
        "❓ <b>Помощь — FreeGPT</b>\n\n"
        "<b>📋 Команды:</b>\n"
        "├ /start — Перезапуск бота\n"
        "├ /help — Помощь\n"
        "├ /profile — Ваш профиль\n"
        "├ /model — Выбор модели AI\n"
        "├ /image описание — Генерация\n"
        "├ /premium — О премиуме\n"
        "├ /promo — Ввести промокод\n"
        "├ /stats — Статистика\n"
        "├ /clear — Очистить историю\n"
        "└ /admin — Админ-панель\n\n"
        "🔐 Вход для админа:\n"
        "<code>/login adm9912</code>",
        parse_mode="HTML")

async def cmd_profile(u,c):
    uid=u.effective_user.id
    user=await db.get_user(uid)
    if not user:
        t="❌ Нажмите /start для начала"
        if u.callback_query:await u.callback_query.edit_message_text(t)
        else:await u.message.reply_text(t)
        return
    prem=await db.check_premium(uid)
    usage=await db.get_usage(uid)
    msg_lim=PREM_MSG if prem else FREE_MSG
    img_lim=PREM_IMG if prem else FREE_IMG
    def bar(used,total):
        if total==0:return "░"*10
        pct=min(used/total,1.0)
        return "█"*int(pct*10)+"░"*(10-int(pct*10))
    if user["banned"]:status="🚫 Заблокирован"
    elif user["muted"]:status="🔇 Замьючен"
    elif prem:status="⭐ Премиум"
    else:status="🆓 Бесплатный"
    mn=MODELS.get(user["model"],{}).get("name","⚡ GPT-4o Mini")
    pu=""
    if prem and user["prem_until"]:
        pu=f"\n├ 📅 До: <b>{str(user['prem_until'])[:10]}</b>"
    t=(
        f"👤 <b>Ваш профиль</b>\n\n"
        f"├ 🆔 ID: <code>{uid}</code>\n"
        f"├ 👤 Имя: <b>{user['fname']}</b>\n"
        f"├ 📛 Username: @{user['uname'] or 'не указан'}\n"
        f"├ 🏷 Статус: <b>{status}</b>{pu}\n"
        f"└ 🤖 Модель: <b>{mn}</b>\n\n"
        f"<b>📊 Лимиты на сегодня:</b>\n\n"
        f"💬 Сообщения: {usage['msgs']}/{msg_lim}\n"
        f"[{bar(usage['msgs'],msg_lim)}]\n\n"
        f"🎨 Изображения: {usage['imgs']}/{img_lim}\n"
        f"[{bar(usage['imgs'],img_lim)}]\n\n"
        f"<b>📈 За всё время:</b>\n"
        f"├ 💬 Сообщений: <b>{user['total_msg']}</b>\n"
        f"└ 🎨 Изображений: <b>{user['total_img']}</b>")
    if u.callback_query:await u.callback_query.edit_message_text(t,parse_mode="HTML",reply_markup=kb_profile())
    else:await u.message.reply_text(t,parse_mode="HTML",reply_markup=kb_profile())

async def cmd_models(u,c):
    uid=u.effective_user.id
    user=await db.get_user(uid)
    prem=await db.check_premium(uid)
    cur=user["model"] if user else "mini"
    t="🤖 <b>Выбор модели AI</b>\n\n⚡ GPT-4o Mini — быстрая\n🧠 GPT-4o — мощная\n🚀 GPT-4 Turbo — максимум 🔒\n💬 GPT-3.5 — классика\n\n✅ текущая | 🔒 Премиум"
    if u.callback_query:await u.callback_query.edit_message_text(t,parse_mode="HTML",reply_markup=kb_models(cur,prem))
    else:await u.message.reply_text(t,parse_mode="HTML",reply_markup=kb_models(cur,prem))

async def cmd_stats(u,c):
    uid=u.effective_user.id
    user=await db.get_user(uid)
    usage=await db.get_usage(uid)
    prem=await db.check_premium(uid)
    t=(
        f"📊 <b>Статистика FreeGPT</b>\n\n"
        f"<b>👤 Вы:</b>\n"
        f"├ 💬 Всего: <b>{user['total_msg'] if user else 0}</b>\n"
        f"├ 🎨 Всего: <b>{user['total_img'] if user else 0}</b>\n"
        f"├ 💬 Сегодня: <b>{usage['msgs']}</b>\n"
        f"├ 🎨 Сегодня: <b>{usage['imgs']}</b>\n"
        f"└ ⭐ Премиум: <b>{'Да' if prem else 'Нет'}</b>\n\n"
        f"<b>🌐 Бот:</b>\n"
        f"├ 👥 Юзеров: <b>{await db.count_users()}</b>\n"
        f"├ ⭐ Премиум: <b>{await db.count_premium()}</b>\n"
        f"└ 🟢 Сегодня: <b>{await db.count_active()}</b>")
    await u.message.reply_text(t,parse_mode="HTML")

async def cmd_premium(u,c):
    uid=u.effective_user.id
    prem=await db.check_premium(uid)
    if prem:
        user=await db.get_user(uid)
        until=str(user['prem_until'])[:10] if user['prem_until'] else '—'
        t=f"⭐ <b>Премиум активен!</b>\n\n📅 До: <b>{until}</b>\n\n💬 {PREM_MSG}/день\n🎨 {PREM_IMG}/день\n🚀 GPT-4 Turbo\n\n🎉 Наслаждайтесь!"
        kb=None
    else:
        t=(
            f"⭐ <b>FreeGPT Премиум</b>\n\n"
            f"<b>Что входит:</b>\n"
            f"├ 💬 {PREM_MSG} сообщений/день\n"
            f"├ 🎨 {PREM_IMG} изображений/день\n"
            f"├ 🚀 GPT-4 Turbo\n"
            f"└ ⚡ Без ограничений\n\n"
            f"💰 <b>{STARS_PRICE} ⭐ Stars</b> | 📅 {PREM_DAYS} дней")
        kb=kb_premium()
    if u.callback_query:await u.callback_query.edit_message_text(t,parse_mode="HTML",reply_markup=kb)
    else:await u.message.reply_text(t,parse_mode="HTML",reply_markup=kb)

async def cmd_clear(u,c):
    await db.clear_hist(u.effective_user.id)
    if u.callback_query:await u.callback_query.answer("✅ Очищено!",show_alert=True)
    else:await u.message.reply_text("🗑 <b>История очищена!</b>",parse_mode="HTML")

async def cmd_image(u,c):
    uid=u.effective_user.id
    user=await db.get_user(uid)
    if not user:return await u.message.reply_text("❌ /start")
    if user["banned"]:return await u.message.reply_text("🚫 Заблокированы")
    if not c.args:
        return await u.message.reply_text("🎨 <b>Генерация</b>\n\n<code>/image кот в космосе</code>",parse_mode="HTML")
    ok,left=await db.can_img(uid,FREE_IMG,PREM_IMG)
    if not ok:return await u.message.reply_text(f"⚠️ Лимит! Бесплатно: {FREE_IMG}/день\n⭐ Премиум: {PREM_IMG}/день")
    prompt=" ".join(c.args)
    msg=await u.message.reply_text("🎨 <b>Генерирую...</b> ⏳",parse_mode="HTML")
    result=await ask_ai([{"role":"user","content":f"Create vivid image description: {prompt}"}],"gpt-4o-mini")
    await db.add_img(uid)
    await msg.edit_text(f"🎨 <b>Готово!</b>\n\n📝 <i>{prompt}</i>\n\n🖼 {result[:600]}\n\n🎨 Осталось: {left-1}",parse_mode="HTML")

async def handle_ai(u,c):
    uid=u.effective_user.id
    user=await db.get_user(uid)
    if not user:return await u.message.reply_text("❌ /start")
    if user["banned"]:return await u.message.reply_text(f"🚫 <b>Заблокированы</b>\nПричина: {user['ban_reason'] or '—'}",parse_mode="HTML")
    if user["muted"]:return await u.message.reply_text(f"🔇 <b>Замьючены</b>\nПричина: {user['mute_reason'] or '—'}",parse_mode="HTML")
    ok,left=await db.can_msg(uid,FREE_MSG,PREM_MSG)
    if not ok:return await u.message.reply_text(f"⚠️ <b>Лимит!</b>\n💬 {FREE_MSG}/день\n⭐ Премиум: {PREM_MSG}/день",parse_mode="HTML")
    text=u.message.text
    mi=MODELS.get(user["model"],MODELS["mini"])
    await c.bot.send_chat_action(uid,"typing")
    hist=await db.get_hist(uid,10)
    msgs=[{"role":"system","content":"Ты FreeGPT, AI-ассистент. Отвечай кратко, полезно, дружелюбно. Русский язык."}]
    msgs.extend(hist)
    msgs.append({"role":"user","content":text})
    answer=await ask_ai(msgs,mi["id"])
    await db.save_hist(uid,"user",text)
    await db.save_hist(uid,"assistant",answer)
    await db.add_msg(uid)
    left-=1
    try:await u.message.reply_text(f"{answer}\n\n<i>💬 {left} | {mi['name']}</i>",parse_mode="HTML")
    except:await u.message.reply_text(f"{answer}\n\n💬 {left}")

async def on_pay(u,c):
    q=u.callback_query;await q.answer()
    await c.bot.send_invoice(q.from_user.id,"⭐ FreeGPT Премиум",f"{PREM_DAYS} дней","prem","XTR",[LabeledPrice("Премиум",STARS_PRICE)])
async def on_precheckout(u,c):await u.pre_checkout_query.answer(ok=True)
async def on_payment(u,c):
    await db.give_premium(u.effective_user.id,PREM_DAYS)
    await u.message.reply_text(f"🎉 <b>Премиум на {PREM_DAYS} дней!</b>\n\n💬 {PREM_MSG}/день\n🎨 {PREM_IMG}/день\n🚀 GPT-4 Turbo\n\nСпасибо! ❤️",parse_mode="HTML")

async def cmd_login(u,c):
    try:await u.message.delete()
    except:pass
    if not c.args:return await c.bot.send_message(u.effective_user.id,"🔐 <code>/login пароль</code>",parse_mode="HTML")
    if c.args[0]==APASS:
        await db.set_admin(u.effective_user.id)
        await c.bot.send_message(u.effective_user.id,"✅ <b>Вы админ!</b>\n/admin — панель",parse_mode="HTML")
    else:await c.bot.send_message(u.effective_user.id,"❌ Неверный пароль")
async def cmd_logout(u,c):
    await db.set_admin(u.effective_user.id,False)
    await u.message.reply_text("🔓 Вышли из админки")
async def cmd_admin(u,c):
    if not await db.is_admin(u.effective_user.id):
        return await u.message.reply_text("❌ <b>Нет доступа!</b>\n<code>/login пароль</code>",parse_mode="HTML")
    await u.message.reply_text("🛡 <b>Панель администратора</b>",parse_mode="HTML",reply_markup=kb_admin())
