import logging, g4f
from telegram import (
    Update, LabeledPrice,
    InlineKeyboardButton as IKB, InlineKeyboardMarkup as IKM,
    ReplyKeyboardMarkup as RKM, KeyboardButton as KB
)
from telegram.ext import (
    Application, CommandHandler as CH, MessageHandler as MH,
    CallbackQueryHandler as CQ, ConversationHandler as CV,
    PreCheckoutQueryHandler, filters, ContextTypes
)
from config import *
from database import *

logging.basicConfig(level=logging.INFO)
TF = filters.TEXT & ~filters.COMMAND

# ═══ KEYBOARDS ═══

def menu_kb():
    return RKM([
        [KB("💬 Чат"), KB("🎨 Фото")],
        [KB("👤 Профиль"), KB("📊 Стата")],
        [KB("🤖 Модель"), KB("⭐ Премиум")],
        [KB("🗑 Очистить"), KB("❓ Помощь")]
    ], resize_keyboard=True)

def models_kb(cur, prem):
    kb = []
    for k, m in MODELS.items():
        ch = " ✅" if k == cur else ""
        lo = " 🔒" if m["prem"] and not prem else ""
        kb.append([IKB(f"{m['name']}{ch}{lo}", callback_data=f"m_{k}")])
    kb.append([IKB("🔙 Назад", callback_data="close")])
    return IKM(kb)

def profile_kb():
    return IKM([
        [IKB("⭐ Премиум", callback_data="buy_prem"),
         IKB("🎁 Промокод", callback_data="use_promo")],
        [IKB("🤖 Модель", callback_data="models"),
         IKB("🗑 Очистить", callback_data="clear")]
    ])

def prem_kb():
    return IKM([
        [IKB(f"⭐ {PREM_PRICE} Stars", callback_data="pay")],
        [IKB("🎁 Промокод", callback_data="use_promo")],
        [IKB("🔙", callback_data="close")]
    ])

def adm_kb():
    return IKM([
        [IKB("📊 Стата", callback_data="a_stats"),
         IKB("👥 Юзеры", callback_data="a_users")],
        [IKB("🔨 Бан", callback_data="a_ban"),
         IKB("✅ Разбан", callback_data="a_unban")],
        [IKB("🔇 Мут", callback_data="a_mute"),
         IKB("🔊 Размут", callback_data="a_unmute")],
        [IKB("🎁 Промо+", callback_data="a_promo"),
         IKB("📋 Промо", callback_data="a_promos")],
        [IKB("⭐ Дать", callback_data="a_give"),
         IKB("❌ Снять", callback_data="a_rm")],
        [IKB("📢 Рассылка", callback_data="a_bc"),
         IKB("🔍 Найти", callback_data="a_find")]
    ])

def back_kb():
    return IKM([[IKB("🔙 Админка", callback_data="a_back")]])

# ═══ AI ═══

async def ask_ai(messages, model_id):
    try:
        r = await g4f.ChatCompletion.create_async(
            model=model_id, messages=messages)
        return r or "🤔 Пустой ответ"
    except:
        try:
            return await g4f.ChatCompletion.create_async(
                model="gpt-3.5-turbo", messages=messages)
        except Exception as e:
            return f"❌ Ошибка AI: {str(e)[:100]}"

# ═══ COMMANDS ═══

async def cmd_start(u: Update, c):
    usr = u.effective_user
    await add_user(usr.id, usr.username, usr.first_name)
    await u.message.reply_text(
        f"🤖 <b>Добро пожаловать в FreeGPT!</b>\n\n"
        f"Привет, <b>{usr.first_name}</b>! 👋\n\n"
        f"<b>🎯 Возможности:</b>\n"
        f"├ 💬 Чат с AI (GPT-4o, GPT-3.5)\n"
        f"├ 🎨 Генерация описаний\n"
        f"├ 📝 Код, тексты, переводы\n"
        f"└ 🧮 Решение задач\n\n"
        f"<b>📦 Бесплатно:</b> {FREE_MSG} сообщений/день\n"
        f"<b>⭐ Премиум:</b> {PREM_MSG} сообщений/день\n\n"
        f"Просто напишите сообщение! 👇",
        parse_mode="HTML", reply_markup=menu_kb())

async def cmd_help(u: Update, c):
    await u.message.reply_text(
        "❓ <b>Помощь FreeGPT</b>\n\n"
        "<b>Команды:</b>\n"
        "├ /start — запуск\n"
        "├ /help — помощь\n"
        "├ /profile — профиль\n"
        "├ /model — модель AI\n"
        "├ /image текст — картинка\n"
        "├ /premium — премиум\n"
        "├ /promo — промокод\n"
        "├ /stats — статистика\n"
        "├ /clear — очистить чат\n"
        "└ /admin — админка\n\n"
        "🔐 <code>/login adm9912</code>",
        parse_mode="HTML")

async def cmd_profile(u: Update, c):
    uid = u.effective_user.id
    usr = await get_user(uid)
    if not usr:
        t = "❌ Нажмите /start"
        if u.callback_query: await u.callback_query.edit_message_text(t)
        else: await u.message.reply_text(t)
        return
    prem = await is_prem(uid)
    usage = await get_usage(uid)
    ml = PREM_MSG if prem else FREE_MSG
    il = PREM_IMG if prem else FREE_IMG
    bar = lambda x,t: "█"*int(min(x/t,1)*10)+"░"*(10-int(min(x/t,1)*10)) if t else "░"*10
    st = "🚫 Бан" if usr["banned"] else "🔇 Мут" if usr["muted"] else "⭐ Premium" if prem else "🆓 Free"
    mn = MODELS.get(usr["model"],{}).get("name","?")
    pu = str(usr["prem_until"])[:10] if prem and usr["prem_until"] else ""
    pu_line = f"\n📅 До: <b>{pu}</b>" if pu else ""

    t = (f"👤 <b>Ваш профиль</b>\n\n"
         f"├ 🆔 <code>{uid}</code>\n"
         f"├ 👤 <b>{usr['fname']}</b>\n"
         f"├ 📛 @{usr['uname'] or '—'}\n"
         f"├ 🏷 {st}{pu_line}\n"
         f"└ 🤖 {mn}\n\n"
         f"<b>💬 Сообщения:</b> {usage['msgs']}/{ml}\n"
         f"[{bar(usage['msgs'],ml)}]\n\n"
         f"<b>🎨 Изображения:</b> {usage['imgs']}/{il}\n"
         f"[{bar(usage['imgs'],il)}]\n\n"
         f"📈 Всего: 💬 {usr['msgs']} | 🎨 {usr['imgs']}")
    if u.callback_query:
        await u.callback_query.edit_message_text(t, parse_mode="HTML", reply_markup=profile_kb())
    else:
        await u.message.reply_text(t, parse_mode="HTML", reply_markup=profile_kb())

async def cmd_models(u: Update, c):
    uid = u.effective_user.id
    usr = await get_user(uid)
    prem = await is_prem(uid)
    cur = usr["model"] if usr else "gpt4o_mini"
    t = "🤖 <b>Выберите модель AI</b>\n\n✅ = текущая | 🔒 = Премиум"
    if u.callback_query:
        await u.callback_query.edit_message_text(t, parse_mode="HTML", reply_markup=models_kb(cur, prem))
    else:
        await u.message.reply_text(t, parse_mode="HTML", reply_markup=models_kb(cur, prem))

async def cmd_stats(u: Update, c):
    uid = u.effective_user.id
    usr = await get_user(uid)
    usage = await get_usage(uid)
    t = (f"📊 <b>Статистика</b>\n\n"
         f"<b>👤 Вы:</b>\n"
         f"├ 💬 Всего: {usr['msgs'] if usr else 0}\n"
         f"├ 🎨 Всего: {usr['imgs'] if usr else 0}\n"
         f"├ 💬 Сегодня: {usage['msgs']}\n"
         f"└ 🎨 Сегодня: {usage['imgs']}\n\n"
         f"<b>🌐 Бот:</b>\n"
         f"├ 👥 Юзеров: {await total_users()}\n"
         f"├ ⭐ Премиум: {await prem_count()}\n"
         f"└ 🟢 Сегодня: {await today_active()}")
    await u.message.reply_text(t, parse_mode="HTML")

async def cmd_premium(u: Update, c):
    uid = u.effective_user.id
    prem = await is_prem(uid)
    if prem:
        t = "⭐ <b>Премиум активен!</b> 🎉\n\nНаслаждайтесь!"
        kb = None
    else:
        t = (f"⭐ <b>FreeGPT Премиум</b>\n\n"
             f"<b>Включает:</b>\n"
             f"├ 💬 {PREM_MSG} сообщений/день\n"
             f"├ 🎨 {PREM_IMG} изображений/день\n"
             f"├ 🚀 GPT-4 Turbo доступ\n"
             f"└ ⚡ Без ограничений\n\n"
             f"💰 <b>{PREM_PRICE} ⭐ Stars</b> | 📅 {PREM_DAYS} дней")
        kb = prem_kb()
    if u.callback_query:
        await u.callback_query.edit_message_text(t, parse_mode="HTML", reply_markup=kb)
    else:
        await u.message.reply_text(t, parse_mode="HTML", reply_markup=kb)

async def cmd_clear(u: Update, c):
    await clear_hist(u.effective_user.id)
    if u.callback_query:
        await u.callback_query.answer("✅ Очищено!", show_alert=True)
    else:
        await u.message.reply_text("🗑 <b>История очищена!</b>", parse_mode="HTML")

async def cmd_image(u: Update, c):
    uid = u.effective_user.id
    usr = await get_user(uid)
    if not usr: return await u.message.reply_text("❌ /start")
    if usr["banned"]: return await u.message.reply_text("🚫 Забанены")
    if not c.args:
        return await u.message.reply_text(
            "🎨 <b>Генерация</b>\n\n"
            "Пример:\n<code>/image кот в космосе</code>",
            parse_mode="HTML")
    ok, left = await can_img(uid)
    if not ok:
        return await u.message.reply_text("⚠️ Лимит! Купите ⭐ Премиум")
    prompt = " ".join(c.args)
    msg = await u.message.reply_text("🎨 <b>Генерирую...</b> ⏳", parse_mode="HTML")
    try:
        r = await ask_ai([{"role":"user",
            "content":f"Create detailed image description for: {prompt}"}],
            "gpt-4o-mini")
        await inc_imgs(uid)
        await msg.edit_text(
            f"🎨 <b>Готово!</b>\n\n"
            f"📝 Запрос: <i>{prompt}</i>\n\n"
            f"🖼 {r[:500]}\n\n"
            f"Осталось: {left-1}",
            parse_mode="HTML")
    except Exception as e:
        await msg.edit_text(f"❌ {e}")

# ═══ AI CHAT ═══

async def handle_ai(u: Update, c):
    uid = u.effective_user.id
    usr = await get_user(uid)
    if not usr: return await u.message.reply_text("❌ /start")
    if usr["banned"]:
        return await u.message.reply_text(
            f"🚫 <b>Забанены</b>\nПричина: {usr['ban_reason'] or '—'}",
            parse_mode="HTML")
    if usr["muted"]:
        return await u.message.reply_text(
            f"🔇 <b>Замьючены</b>\nПричина: {usr['mute_reason'] or '—'}",
            parse_mode="HTML")
    ok, left = await can_msg(uid)
    if not ok:
        return await u.message.reply_text(
            "⚠️ <b>Лимит исчерпан!</b>\n\n"
            f"Бесплатно: {FREE_MSG} сообщений/день\n"
            "Купите ⭐ Премиум!",
            parse_mode="HTML")

    text = u.message.text
    mk = usr["model"]
    mi = MODELS.get(mk, MODELS["gpt4o_mini"])
    await c.bot.send_chat_action(uid, "typing")

    hist = await get_hist(uid, 10)
    msgs = [{"role": "system", "content":
        "Ты — FreeGPT, умный AI-ассистент в Telegram. "
        "Отвечай кратко, полезно и дружелюбно. "
        "Используй русский язык. Используй эмодзи."}]
    msgs.extend(hist)
    msgs.append({"role": "user", "content": text})

    answer = await ask_ai(msgs, mi["id"])
    await add_hist(uid, "user", text)
    await add_hist(uid, "assistant", answer)
    await inc_msgs(uid)
    left -= 1

    footer = f"\n\n<i>💬 {left} | {mi['name']}</i>"
    try:
        full = answer + footer
        if len(full) > 4096:
            for i in range(0, len(answer), 4000):
                chunk = answer[i:i+4000]
                if i + 4000 >= len(answer): chunk += footer
                await u.message.reply_text(chunk, parse_mode="HTML")
        else:
            await u.message.reply_text(full, parse_mode="HTML")
    except:
        await u.message.reply_text(answer + f"\n\n💬 {left}")

# ═══ PAYMENT ═══

async def pay_cb(u, c):
    q = u.callback_query; await q.answer()
    await c.bot.send_invoice(q.from_user.id, "⭐ FreeGPT Премиум",
        f"Премиум на {PREM_DAYS} дней", "prem", "XTR",
        [LabeledPrice("Premium", PREM_PRICE)])

async def precheckout_h(u, c):
    await u.pre_checkout_query.answer(ok=True)

async def payment_ok(u, c):
    await give_prem(u.effective_user.id, PREM_DAYS)
    await u.message.reply_text(
        f"🎉 <b>Премиум на {PREM_DAYS} дней!</b>\n\nСпасибо! ❤️",
        parse_mode="HTML")

# ═══ ADMIN ═══

async def cmd_login(u, c):
    try: await u.message.delete()
    except: pass
    if not c.args:
        return await c.bot.send_message(
            u.effective_user.id, "🔐 <code>/login пароль</code>",
            parse_mode="HTML")
    if c.args[0] == ADMIN_PASS:
        await set_admin(u.effective_user.id)
        await c.bot.send_message(u.effective_user.id,
            "✅ <b>Вы — администратор!</b>\n\n/admin — панель",
            parse_mode="HTML")
    else:
        await c.bot.send_message(u.effective_user.id, "❌ Неверный пароль")

async def cmd_logout(u, c):
    await set_admin(u.effective_user.id, False)
    await u.message.reply_text("🔓 Вышли из админки")

async def cmd_admin(u, c):
    if not await is_admin(u.effective_user.id):
        return await u.message.reply_text("❌ Нет доступа!\n/login пароль")
    await u.message.reply_text("🛡 <b>Админ панель FreeGPT</b>",
        parse_mode="HTML", reply_markup=adm_kb())

# Admin states
(S_BAN, S_BAN_R, S_UNBAN, S_MUTE, S_MUTE_R, S_UNMUTE,
 S_PC, S_PD, S_PU, S_GP, S_GPD, S_RP, S_BC, S_FIND, S_UPROMO) = range(15)

async def _f(t):
    t = t.strip()
    if t.startswith("@"): return await find_user(t)
    elif t.isdigit(): return await get_user(int(t))

async def cancel_h(u, c):
    await u.message.reply_text("❌ Отмена\n/admin — панель")
    return CV.END

# Ban flow
async def a_ban_s(u,c):
    await u.callback_query.answer()
    await u.callback_query.edit_message_text("🔨 <b>Бан</b>\n\nОтправьте @username или ID:", parse_mode="HTML")
    return S_BAN
async def a_ban_1(u,c):
    usr = await _f(u.message.text)
    if not usr: await u.message.reply_text("❌ Не найден. Ещё раз:"); return S_BAN
    c.user_data["tid"]=usr["uid"]; c.user_data["tn"]=usr["fname"]
    await u.message.reply_text(f"Причина бана для <b>{usr['fname']}</b>:", parse_mode="HTML")
    return S_BAN_R
async def a_ban_2(u,c):
    await ban(c.user_data["tid"], u.message.text)
    await u.message.reply_text(f"✅ <b>{c.user_data['tn']}</b> забанен!", parse_mode="HTML")
    try: await c.bot.send_message(c.user_data["tid"],
        f"🚫 <b>Вы забанены</b>\nПричина: {u.message.text}", parse_mode="HTML")
    except: pass
    return CV.END

# Unban flow
async def a_unban_s(u,c):
    await u.callback_query.answer()
    await u.callback_query.edit_message_text("✅ <b>Разбан</b>\n\n@username или ID:", parse_mode="HTML")
    return S_UNBAN
async def a_unban_1(u,c):
    usr = await _f(u.message.text)
    if not usr: await u.message.reply_text("❌"); return S_UNBAN
    await unban(usr["uid"])
    await u.message.reply_text(f"✅ {usr['fname']} разбанен!")
    try: await c.bot.send_message(usr["uid"], "✅ Разбанены!")
    except: pass
    return CV.END

# Mute flow
async def a_mute_s(u,c):
    await u.callback_query.answer()
    await u.callback_query.edit_message_text("🔇 <b>Мут</b>\n\n@username или ID:", parse_mode="HTML")
    return S_MUTE
async def a_mute_1(u,c):
    usr = await _f(u.message.text)
    if not usr: await u.message.reply_text("❌"); return S_MUTE
    c.user_data["tid"]=usr["uid"]; c.user_data["tn"]=usr["fname"]
    await u.message.reply_text(f"Причина мута для <b>{usr['fname']}</b>:", parse_mode="HTML")
    return S_MUTE_R
async def a_mute_2(u,c):
    await mute(c.user_data["tid"], u.message.text)
    await u.message.reply_text(f"✅ {c.user_data['tn']} замьючен!")
    try: await c.bot.send_message(c.user_data["tid"],
        f"🔇 Замьючены: {u.message.text}")
    except: pass
    return CV.END

# Unmute flow
async def a_unmute_s(u,c):
    await u.callback_query.answer()
    await u.callback_query.edit_message_text("🔊 <b>Размут</b>\n\n@username или ID:", parse_mode="HTML")
    return S_UNMUTE
async def a_unmute_1(u,c):
    usr = await _f(u.message.text)
    if not usr: await u.message.reply_text("❌"); return S_UNMUTE
    await unmute(usr["uid"])
    await u.message.reply_text(f"✅ Размьючен!")
    return CV.END

# Create promo
async def a_promo_s(u,c):
    await u.callback_query.answer()
    await u.callback_query.edit_message_text("🎁 <b>Новый промокод</b>\n\nВведите код:", parse_mode="HTML")
    return S_PC
async def a_promo_1(u,c):
    c.user_data["pc"]=u.message.text.strip().upper()
    await u.message.reply_text(f"Код: <code>{c.user_data['pc']}</code>\n\nСколько дней премиума?", parse_mode="HTML")
    return S_PD
async def a_promo_2(u,c):
    try: c.user_data["pd"]=int(u.message.text)
    except: await u.message.reply_text("❌ Введите число!"); return S_PD
    await u.message.reply_text("Максимум использований?")
    return S_PU
async def a_promo_3(u,c):
    try: uses=int(u.message.text)
    except: await u.message.reply_text("❌ Число!"); return S_PU
    await create_promo(c.user_data["pc"], c.user_data["pd"], uses)
    await u.message.reply_text(
        f"✅ <b>Промокод создан!</b>\n\n"
        f"🎁 <code>{c.user_data['pc']}</code>\n"
        f"📅 {c.user_data['pd']} дней\n"
        f"👥 {uses} использований",
        parse_mode="HTML")
    return CV.END

# Give premium
async def a_give_s(u,c):
    await u.callback_query.answer()
    await u.callback_query.edit_message_text("⭐ <b>Выдать премиум</b>\n\n@username или ID:", parse_mode="HTML")
    return S_GP
async def a_give_1(u,c):
    usr = await _f(u.message.text)
    if not usr: await u.message.reply_text("❌"); return S_GP
    c.user_data["tid"]=usr["uid"]; c.user_data["tn"]=usr["fname"]
    await u.message.reply_text(f"Дней премиума для <b>{usr['fname']}</b>?", parse_mode="HTML")
    return S_GPD
async def a_give_2(u,c):
    try: d=int(u.message.text)
    except: await u.message.reply_text("Число!"); return S_GPD
    await give_prem(c.user_data["tid"], d)
    await u.message.reply_text(f"✅ {c.user_data['tn']} получил ⭐ на {d} дней!")
    try: await c.bot.send_message(c.user_data["tid"],
        f"🎉 Вам выдан ⭐ Премиум на {d} дней!")
    except: pass
    return CV.END

# Remove premium
async def a_rm_s(u,c):
    await u.callback_query.answer()
    await u.callback_query.edit_message_text("❌ <b>Снять премиум</b>\n\n@username или ID:", parse_mode="HTML")
    return S_RP
async def a_rm_1(u,c):
    usr = await _f(u.message.text)
    if not usr: await u.message.reply_text("❌"); return S_RP
    await rm_prem(usr["uid"])
    await u.message.reply_text(f"✅ Премиум снят у {usr['fname']}")
    return CV.END

# Broadcast
async def a_bc_s(u,c):
    await u.callback_query.answer()
    await u.callback_query.edit_message_text("📢 <b>Рассылка</b>\n\nВведите текст сообщения:", parse_mode="HTML")
    return S_BC
async def a_bc_1(u,c):
    text = u.message.text
    users = await all_users_list()
    s = f = 0
    st = await u.message.reply_text("📢 Отправляю...")
    for usr in users:
        try:
            await c.bot.send_message(usr["uid"],
                f"📢 <b>FreeGPT</b>\n\n{text}", parse_mode="HTML")
            s += 1
        except: f += 1
    await st.edit_text(f"✅ Отправлено: {s} | Ошибки: {f}")
    return CV.END

# Find user
async def a_find_s(u,c):
    await u.callback_query.answer()
    await u.callback_query.edit_message_text("🔍 <b>Поиск</b>\n\n@username или ID:", parse_mode="HTML")
    return S_FIND
async def a_find_1(u,c):
    usr = await _f(u.message.text)
    if not usr:
        await u.message.reply_text("❌ Не найден")
        return CV.END
    st = "🚫 Бан" if usr["banned"] else "🔇 Мут" if usr["muted"] else "⭐ Prem" if usr["premium"] else "🆓 Free"
    await u.message.reply_text(
        f"🔍 <b>Найден</b>\n\n"
        f"├ 🆔 <code>{usr['uid']}</code>\n"
        f"├ 👤 {usr['fname']}\n"
        f"├ 📛 @{usr['uname'] or '—'}\n"
        f"├ 🏷 {st}\n"
        f"├ 👑 Админ: {'✅' if usr['admin'] else '❌'}\n"
        f"├ 💬 {usr['msgs']} 🎨 {usr['imgs']}\n"
        f"└ 🤖 {usr['model']}",
        parse_mode="HTML")
    return CV.END

# Admin callbacks (no conversation)
async def a_stats_cb(u,c):
    await u.callback_query.answer()
    t = await total_users(); p = await prem_count(); a = await today_active()
    await u.callback_query.edit_message_text(
        f"📊 <b>Статистика бота</b>\n\n"
        f"├ 👥 Юзеров: {t}\n├ ⭐ Премиум: {p}\n└ 🟢 Сегодня: {a}",
        parse_mode="HTML", reply_markup=back_kb())

async def a_users_cb(u,c):
    await u.callback_query.answer()
    users = await all_users_list(20)
    t = "👥 <b>Пользователи:</b>\n\n"
    for usr in users:
        ic = "🚫" if usr["banned"] else "🔇" if usr["muted"] else "⭐" if usr["premium"] else "👤"
        t += f"{ic} {usr['fname']} @{usr['uname'] or '—'} <code>{usr['uid']}</code>\n"
    await u.callback_query.edit_message_text(t, parse_mode="HTML", reply_markup=back_kb())

async def a_promos_cb(u,c):
    await u.callback_query.answer()
    ps = await all_promos()
    if not ps: t = "📋 Промокодов нет"
    else:
        t = "📋 <b>Промокоды:</b>\n\n"
        for p in ps:
            t += f"{'✅' if p['active'] else '❌'} <code>{p['code']}</code> — {p['days']}дн | {p['used']}/{p['max_use']}\n"
    await u.callback_query.edit_message_text(t, parse_mode="HTML", r
