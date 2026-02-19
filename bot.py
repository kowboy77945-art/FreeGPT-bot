from part1 import *

ST_BAN,ST_BAN_R,ST_UNBAN,ST_MUTE,ST_MUTE_R,ST_UNMUTE=range(6)
ST_PC,ST_PD,ST_PU,ST_GP,ST_GPD,ST_RP,ST_BC,ST_FIND,ST_PROMO=range(6,15)

async def cancel(u,c):
    await u.message.reply_text("❌ Отменено. /admin")
    return ConversationHandler.END

async def adm_ban_s(u,c):
    await u.callback_query.answer()
    await u.callback_query.edit_message_text("🔨 <b>Бан</b>\n\n@username или ID:",parse_mode="HTML")
    return ST_BAN
async def adm_ban_u(u,c):
    x=await db.lookup(u.message.text)
    if not x:await u.message.reply_text("❌ Не найден");return ST_BAN
    c.user_data["tid"]=x["uid"];c.user_data["tn"]=x["fname"]
    await u.message.reply_text(f"Причина бана для <b>{x['fname']}</b>:",parse_mode="HTML")
    return ST_BAN_R
async def adm_ban_r(u,c):
    await db.ban_user(c.user_data["tid"],u.message.text)
    await u.message.reply_text(f"✅ <b>{c.user_data['tn']}</b> забанен!\nПричина: {u.message.text}",parse_mode="HTML")
    try:await c.bot.send_message(c.user_data["tid"],f"🚫 <b>Вы заблокированы</b>\nПричина: {u.message.text}",parse_mode="HTML")
    except:pass
    return ConversationHandler.END

async def adm_unban_s(u,c):
    await u.callback_query.answer()
    await u.callback_query.edit_message_text("✅ <b>Разбан</b>\n\n@username или ID:",parse_mode="HTML")
    return ST_UNBAN
async def adm_unban_d(u,c):
    x=await db.lookup(u.message.text)
    if not x:await u.message.reply_text("❌");return ST_UNBAN
    await db.unban_user(x["uid"])
    await u.message.reply_text(f"✅ <b>{x['fname']}</b> разбанен!",parse_mode="HTML")
    try:await c.bot.send_message(x["uid"],"✅ Вы разблокированы!")
    except:pass
    return ConversationHandler.END

async def adm_mute_s(u,c):
    await u.callback_query.answer()
    await u.callback_query.edit_message_text("🔇 <b>Мут</b>\n\n@username или ID:",parse_mode="HTML")
    return ST_MUTE
async def adm_mute_u(u,c):
    x=await db.lookup(u.message.text)
    if not x:await u.message.reply_text("❌");return ST_MUTE
    c.user_data["tid"]=x["uid"];c.user_data["tn"]=x["fname"]
    await u.message.reply_text(f"Причина мута для <b>{x['fname']}</b>:",parse_mode="HTML")
    return ST_MUTE_R
async def adm_mute_r(u,c):
    await db.mute_user(c.user_data["tid"],u.message.text)
    await u.message.reply_text(f"✅ <b>{c.user_data['tn']}</b> замьючен!",parse_mode="HTML")
    try:await c.bot.send_message(c.user_data["tid"],f"🔇 Замьючены: {u.message.text}")
    except:pass
    return ConversationHandler.END

async def adm_unmute_s(u,c):
    await u.callback_query.answer()
    await u.callback_query.edit_message_text("🔊 <b>Размут</b>\n\n@username или ID:",parse_mode="HTML")
    return ST_UNMUTE
async def adm_unmute_d(u,c):
    x=await db.lookup(u.message.text)
    if not x:await u.message.reply_text("❌");return ST_UNMUTE
    await db.unmute_user(x["uid"])
    await u.message.reply_text("✅ Размьючен!")
    return ConversationHandler.END

async def adm_promo_s(u,c):
    await u.callback_query.answer()
    await u.callback_query.edit_message_text("🎁 <b>Новый промокод</b>\n\nВведите код:",parse_mode="HTML")
    return ST_PC
async def adm_promo_c(u,c):
    c.user_data["pc"]=u.message.text.strip().upper()
    await u.message.reply_text(f"Код: <code>{c.user_data['pc']}</code>\n\nСколько дней премиума?",parse_mode="HTML")
    return ST_PD
async def adm_promo_d(u,c):
    try:c.user_data["pd"]=int(u.message.text)
    except:await u.message.reply_text("❌ Число!");return ST_PD
    await u.message.reply_text("Макс использований?")
    return ST_PU
async def adm_promo_u(u,c):
    try:n=int(u.message.text)
    except:await u.message.reply_text("❌ Число!");return ST_PU
    await db.create_promo(c.user_data["pc"],c.user_data["pd"],n)
    await u.message.reply_text(f"✅ <b>Промокод создан!</b>\n\n🎁 <code>{c.user_data['pc']}</code>\n📅 {c.user_data['pd']} дней\n👥 {n} использований",parse_mode="HTML")
    return ConversationHandler.END

async def adm_givep_s(u,c):
    await u.callback_query.answer()
    await u.callback_query.edit_message_text("⭐ <b>Выдать премиум</b>\n\n@username или ID:",parse_mode="HTML")
    return ST_GP
async def adm_givep_u(u,c):
    x=await db.lookup(u.message.text)
    if not x:await u.message.reply_text("❌");return ST_GP
    c.user_data["tid"]=x["uid"];c.user_data["tn"]=x["fname"]
    await u.message.reply_text(f"Дней для <b>{x['fname']}</b>?",parse_mode="HTML")
    return ST_GPD
async def adm_givep_d(u,c):
    try:d=int(u.message.text)
    except:await u.message.reply_text("❌ Число!");return ST_GPD
    await db.give_premium(c.user_data["tid"],d)
    await u.message.reply_text(f"✅ Премиум для <b>{c.user_data['tn']}</b> на {d} дней!",parse_mode="HTML")
    try:await c.bot.send_message(c.user_data["tid"],f"🎉 Вам выдан ⭐ Премиум на {d} дней!")
    except:pass
    return ConversationHandler.END

async def adm_remp_s(u,c):
    await u.callback_query.answer()
    await u.callback_query.edit_message_text("❌ <b>Снять премиум</b>\n\n@username или ID:",parse_mode="HTML")
    return ST_RP
async def adm_remp_d(u,c):
    x=await db.lookup(u.message.text)
    if not x:await u.message.reply_text("❌");return ST_RP
    await db.remove_premium(x["uid"])
    await u.message.reply_text(f"✅ Премиум снят у <b>{x['fname']}</b>",parse_mode="HTML")
    return ConversationHandler.END

async def adm_bc_s(u,c):
    await u.callback_query.answer()
    await u.callback_query.edit_message_text("📢 <b>Рассылка</b>\n\nВведите текст:",parse_mode="HTML")
    return ST_BC
async def adm_bc_d(u,c):
    text=u.message.text;users=await db.all_users();sent=err=0
    st=await u.message.reply_text("📢 Отправляю...")
    for x in users:
        try:await c.bot.send_message(x["uid"],f"📢 <b>FreeGPT</b>\n\n{text}",parse_mode="HTML");sent+=1
        except:err+=1
    await st.edit_text(f"✅ Отправлено: {sent} | Ошибок: {err}")
    return ConversationHandler.END

async def adm_find_s(u,c):
    await u.callback_query.answer()
    await u.callback_query.edit_message_text("🔍 <b>Поиск</b>\n\n@username или ID:",parse_mode="HTML")
    return ST_FIND
async def adm_find_d(u,c):
    x=await db.lookup(u.message.text)
    if not x:await u.message.reply_text("❌ Не найден");return ConversationHandler.END
    if x["banned"]:st="🚫 Забанен"
    elif x["muted"]:st="🔇 Замьючен"
    elif x["premium"]:st="⭐ Премиум"
    else:st="🆓 Free"
    await u.message.reply_text(f"🔍 <b>Найден</b>\n\n🆔 <code>{x['uid']}</code>\n👤 {x['fname']} @{x['uname'] or '—'}\n🏷 {st}\n👑 Админ: {'✅' if x['admin'] else '❌'}\n💬 {x['total_msg']} 🎨 {x['total_img']}\n🤖 {x['model']}",parse_mode="HTML")
    return ConversationHandler.END

async def promo_cb(u,c):
    await u.callback_query.answer()
    await u.callback_query.edit_message_text("🎁 <b>Промокод</b>\n\nОтправьте код:",parse_mode="HTML")
    return ST_PROMO
async def promo_cmd(u,c):
    await u.message.reply_text("🎁 Отправьте промокод:")
    return ST_PROMO
async def promo_do(u,c):
    ok,msg=await db.use_promo(u.effective_user.id,u.message.text.strip().upper())
    await u.message.reply_text(msg)
    return ConversationHandler.END

async def adm_stats_cb(u,c):
    await u.callback_query.answer()
    await u.callback_query.edit_message_text(f"📊 <b>Статистика</b>\n\n👥 Юзеров: <b>{await db.count_users()}</b>\n⭐ Премиум: <b>{await db.count_premium()}</b>\n🟢 Сегодня: <b>{await db.count_active()}</b>\n🚫 Забанено: <b>{await db.count_banned()}</b>",parse_mode="HTML",reply_markup=kb_back())

async def adm_users_cb(u,c):
    await u.callback_query.answer()
    users=await db.list_users(20)
    t="👥 <b>Пользователи:</b>\n\n"
    for x in users:
        if x["banned"]:ic="🚫"
        elif x["premium"]:ic="⭐"
        elif x["admin"]:ic="👑"
        else:ic="👤"
        t+=f"{ic} {x['fname']} @{x['uname'] or '—'} <code>{x['uid']}</code>\n"
    await u.callback_query.edit_message_text(t,parse_mode="HTML",reply_markup=kb_back())

async def adm_promos_cb(u,c):
    await u.callback_query.answer()
    ps=await db.get_promos()
    if not ps:t="📋 Промокодов нет"
    else:
        t="📋 <b>Промокоды:</b>\n\n"
        for p in ps:t+=f"<code>{p['code']}</code> — {p['days']}дн | {p['used']}/{p['max_use']}\n"
    await u.callback_query.edit_message_text(t,parse_mode="HTML",reply_markup=kb_back())

async def adm_back_cb(u,c):
    await u.callback_query.answer()
    await u.callback_query.edit_message_text("🛡 <b>Админка</b>",parse_mode="HTML",reply_markup=kb_admin())

async def general_cb(u,c):
    q=u.callback_query;d=q.data
    if d=="close":await q.answer();await q.edit_message_text("✅ Меню внизу 👇")
    elif d=="goprem":await q.answer();await cmd_premium(u,c)
    elif d=="gomodel":await q.answer();await cmd_models(u,c)
    elif d=="pay":await on_pay(u,c)
    elif d.startswith("model:"):
        k=d.split(":")[1]
        if k not in MODELS:return await q.answer("❌",show_alert=True)
        m=MODELS[k];prem=await db.check_premium(q.from_user.id)
        if m["lock"] and not prem:return await q.answer("🔒 Только Премиум!",show_alert=True)
        await db.set_model(q.from_user.id,k)
        await q.answer(f"✅ {m['name']}",show_alert=True)
        await q.edit_message_reply_markup(reply_markup=kb_models(k,prem))
    else:await q.answer()

async def menu_handler(u,c):
    t=u.message.text
    if t=="💬 Чат с AI":await u.message.reply_text("💬 <b>Просто напишите сообщение!</b>",parse_mode="HTML")
    elif t=="🎨 Генерация":await u.message.reply_text("🎨 <code>/image описание</code>",parse_mode="HTML")
    elif t=="👤 Профиль":await cmd_profile(u,c)
    elif t=="📊 Статистика":await cmd_stats(u,c)
    elif t=="🤖 Выбрать модель":await cmd_models(u,c)
    elif t=="⭐ Премиум":await cmd_premium(u,c)
    elif t=="🗑 Очистить чат":await cmd_clear(u,c)
    elif t=="❓ Помощь":await cmd_help(u,c)
    else:await handle_ai(u,c)

def main():
    app=Application.builder().token(TOKEN).build()
    cn=CommandHandler("cancel",cancel)
    for n,f in[("start",cmd_start),("help",cmd_help),("profile",cmd_profile),("model",cmd_models),("image",cmd_image),("premium",cmd_premium),("stats",cmd_stats),("clear",cmd_clear),("login",cmd_login),("logout",cmd_logout),("admin",cmd_admin)]:
        app.add_handler(CommandHandler(n,f))
    app.add_handler(PreCheckoutQueryHandler(on_precheckout))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT,on_payment))
    for e,s in[
        ([CallbackQueryHandler(promo_cb,pattern="^promo$"),CommandHandler("promo",promo_cmd)],{ST_PROMO:[MessageHandler(TXT,promo_do)]}),
        ([CallbackQueryHandler(adm_ban_s,pattern="^adm:ban$")],{ST_BAN:[MessageHandler(TXT,adm_ban_u)],ST_BAN_R:[MessageHandler(TXT,adm_ban_r)]}),
        ([CallbackQueryHandler(adm_unban_s,pattern="^adm:unban$")],{ST_UNBAN:[MessageHandler(TXT,adm_unban_d)]}),
        ([CallbackQueryHandler(adm_mute_s,pattern="^adm:mute$")],{ST_MUTE:[MessageHandler(TXT,adm_mute_u)],ST_MUTE_R:[MessageHandler(TXT,adm_mute_r)]}),
        ([CallbackQueryHandler(adm_unmute_s,pattern="^adm:unmute$")],{ST_UNMUTE:[MessageHandler(TXT,adm_unmute_d)]}),
        ([CallbackQueryHandler(adm_promo_s,pattern="^adm:mkpromo$")],{ST_PC:[MessageHandler(TXT,adm_promo_c)],ST_PD:[MessageHandler(TXT,adm_promo_d)],ST_PU:[MessageHandler(TXT,adm_promo_u)]}),
        ([CallbackQueryHandler(adm_givep_s,pattern="^adm:givep$")],{ST_GP:[MessageHandler(TXT,adm_givep_u)],ST_GPD:[MessageHandler(TXT,adm_givep_d)]}),
        ([CallbackQueryHandler(adm_remp_s,pattern="^adm:remp$")],{ST_RP:[MessageHandler(TXT,adm_remp_d)]}),
        ([CallbackQueryHandler(adm_bc_s,pattern="^adm:broadcast$")],{ST_BC:[MessageHandler(TXT,adm_bc_d)]}),
        ([CallbackQueryHandler(adm_find_s,pattern="^adm:find$")],{ST_FIND:[MessageHandler(TXT,adm_find_d)]}),
    ]:app.add_handler(ConversationHandler(entry_points=e,states=s,fallbacks=[cn]))
    app.add_handler(CallbackQueryHandler(adm_stats_cb,pattern="^adm:stats$"))
    app.add_handler(CallbackQueryHandler(adm_users_cb,pattern="^adm:users$"))
    app.add_handler(CallbackQueryHandler(adm_promos_cb,pattern="^adm:promos$"))
    app.add_handler(CallbackQueryHandler(adm_back_cb,pattern="^adm:back$"))
    app.add_handler(CallbackQueryHandler(general_cb))
    app.add_handler(MessageHandler(TXT,menu_handler))
    async def post_init(a):await db.init()
    app.post_init=post_init
    print("🤖 FreeGPT Bot Started!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__=="__main__":
    main()
