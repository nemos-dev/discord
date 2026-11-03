import discord
from discord.ext import commands
import time
import os
import random
import asyncio
import wikipediaapi
from datetime import timedelta

# Bot sozlamalari
intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents)

start_time = time.time()
afk_users = {}
user_messages = {} # Anti-spam uchun
user_mentions = {} # Mention tarixi uchun
user_offenses = {} # Qoidabuzarliklar soni (1-marta, 2-marta)

@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="!yordam"))
    print(f'======================================')
    print(f'Bot ishga tushdi: {bot.user.name}')
    print(f'Serverlar soni: {len(bot.guilds)}')
    print(f'======================================')

# --- MUKAMMAL OGOHLANTIRISH VA MUTE TIZIMI ---
async def apply_warning(member, channel, reason):
    user_id = member.id
    user_offenses[user_id] = user_offenses.get(user_id, 0) + 1
    count = user_offenses[user_id]

    if count == 1:
        embed = discord.Embed(
            title="⚠️ OGOHLANTIRISH (1/3)",
            description=f"{member.mention}, iltimos qoidalarga amal qiling!\n**Sabab:** {reason}\n\n💡 *Eslatma: 3/3 Ogohlantirish olsangiz, 24 soatga (1 kun) Mute olasiz!*",
            color=discord.Color.gold()
        )
        await channel.send(embed=embed)

    elif count == 2:
        mute_ok = False
        try:
            await member.timeout(timedelta(minutes=10), reason=f"Ogohlantirish 2/3: {reason}")
            mute_ok = True
        except:
            pass

        mute_status = " va **10 daqiqaga Mute** qilindi!" if mute_ok else "!"
        embed = discord.Embed(
            title="🚨 RASMIY OGOHLANTIRISH (2/3)",
            description=f"{member.mention} 2-marta qoidani buzdi{mute_status}\n**Sabab:** {reason}\n\n⚠️ *Diqqat: Yana 1 marta takrorlasangiz (3/3), 24 soatga (1 kun) Mute olasiz!*",
            color=discord.Color.orange()
        )
        await channel.send(embed=embed)

    else: # 3-marta (3/3)
        mute_ok = False
        try:
            await member.timeout(timedelta(hours=24), reason=f"Ogohlantirish 3/3: {reason}")
            mute_ok = True
        except:
            pass

        embed = discord.Embed(
            title="⛔ LIMITGA YETILDI! OGOHLANTIRISH (3/3)",
            description=f"{member.mention} 3 marta qoidani buzgani uchun **24 SOATGA (1 KUN) MUTE** qilindi!\n**Sabab:** {reason}\n**Aksiya:** 24 soatlik chat cheklovi.",
            color=discord.Color.red()
        )
        await channel.send(embed=embed)

        # DM orqali xabarnoma
        try:
            dm_embed = discord.Embed(
                title="⛔ Serverda Mute bo'ldingiz!",
                description=f"Siz **{channel.guild.name}** serverida 3/3 Ogohlantirish oldingiz va **24 soatga Mute** qilindingiz.\n**Sabab:** {reason}\n\nIltimos, keyinroq qoidalarga amal qiling!",
                color=discord.Color.red()
            )
            await member.send(embed=dm_embed)
        except:
            pass

        user_offenses[user_id] = 0 # Nollash

# --- AVTOMATIK HIMOYA VA AFK TIZIMI ---
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    user_id = message.author.id
    current_time = time.time()

    # 1. ANTI-SPAM (Flood)
    if user_id not in user_messages:
        user_messages[user_id] = []

    user_messages[user_id].append(current_time)
    user_messages[user_id] = [t for t in user_messages[user_id] if current_time - t < 3]

    if len(user_messages[user_id]) > 3:
        try: await message.delete()
        except: pass
        await apply_warning(message.author, message.channel, "Flood / Spam qilish")
        return

    # 2. KO'P TEG (MENTION) - 30 soniya ichida 3 marta teg qilsa
    import re
    mention_pattern = r'<@!?\d+>'
    current_mentions = re.findall(mention_pattern, message.content)

    if current_mentions:
        if user_id not in user_mentions:
            user_mentions[user_id] = []

        for _ in current_mentions:
            user_mentions[user_id].append(current_time)

        user_mentions[user_id] = [t for t in user_mentions[user_id] if current_time - t < 30]

        if len(user_mentions[user_id]) >= 3:
            user_mentions[user_id] = []
            await apply_warning(message.author, message.channel, "Ko'p teg (mention) qilish")

    # 3. ANTI-REKLAMA
    if ("discord.gg/" in message.content.lower() or "discord.com/invite/" in message.content.lower()) and not message.author.guild_permissions.administrator:
        await message.delete()
        await apply_warning(message.author, message.channel, "Server havolasi (reklama) tarqatish")
        return

    # 4. AFK
    for mention in message.mentions:
        if mention.id in afk_users:
            reason = afk_users[mention.id]
            embed = discord.Embed(title="⚠️ Foydalanuvchi band!", description=f"**{mention.display_name}** hozir AFK rejimida.\n**Sabab:** {reason}", color=discord.Color.orange())
            await message.channel.send(embed=embed, delete_after=8)

    if message.author.id in afk_users:
        del afk_users[message.author.id]
        await message.channel.send(f"👋 Qaytganingiz bilan, **{message.author.display_name}**! Siz AFK rejimidan chiqdingiz.", delete_after=5)

    # KOMANDALARNI ISHLATISH
    await bot.process_commands(message)


# --- XUSH KELIBSIZ XABARI ---
@bot.event
async def on_member_join(member):
    embed = discord.Embed(
        title="Yangi a'zo qo'shildi! 🎉",
        description=f"Xush kelibsiz {member.mention}! Serverimizda sizni ko'rganimizdan xursandmiz.",
        color=discord.Color.green()
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.set_footer(text=f"Server a'zolari: {member.guild.member_count} ta")

    for channel in member.guild.text_channels:
        if any(name in channel.name.lower() for name in ["chat", "umumiy", "general", "welcome"]):
            await channel.send(embed=embed)
            break

# =========================================================================
# ODDIY FOYDALANUVCHILAR UCHUN KOMANDALAR
# =========================================================================

@bot.command()
async def yordam(ctx):
    embed = discord.Embed(title="📜 Bot Komandalari", color=discord.Color.purple())
    embed.set_thumbnail(url=bot.user.display_avatar.url)

    embed.add_field(
        name="👤 Foydalanuvchilar uchun",
        value="`!salom` — Salomlashish\n"
              "`!ping` — Tezlikni ko'rish\n"
              "`!afk [sabab]` — AFK (shaxsiy DM orqali)\n"
              "`!wiki <so'z>` — Wikipedia qidiruvi\n"
              "`!avatar [@user]` — Profil rasmini ko'rish\n"
              "`!user [@user]` — Foydalanuvchi profili\n"
              "`!server` — Server ma'lumotlari\n"
              "`!zar` — 1-6 gacha zar tashlash\n"
              "`!sorov <savol>` — Ovoz berish so'rovi\n"
              "`!eslat <daqiqa> <matn>` — Vaqtli eslatma qo'yish",
        inline=False
    )

    embed.add_field(
        name="🛡️ Moderatsiya va Adminlar uchun",
        value="`!tozala <son>` — Xabarlarni o'chirish\n"
              "`!kick @user [sabab]` — Haydash\n"
              "`!ban @user [sabab]` — Bloklash\n"
              "`!unban <ism>` — Bandan chiqarish\n"
              "`!mute @user <minut>` — Gapirishni cheklash\n"
              "`!unmute @user` — Cheklovni olish\n"
              "`!warn @user [sabab]` — Ogohlantirish berish\n"
              "`!rol @user @rol` — Rol berish/olish\n"
              "`!say <matn>` — Bot nomidan xabar yozish\n"
              "`!dm @user <matn>` — Shaxsiyiga xabar yozish\n"
              "`!slow <son>` — Chat sekinligi (slowmode)\n"
              "`!holat` — Bot statistikasi",
        inline=False
    )
    embed.set_footer(text=f"So'rovchi: {ctx.author.display_name}")
    await ctx.send(embed=embed)

@bot.command()
async def salom(ctx):
    await ctx.send(f"Salom, {ctx.author.display_name}! 👋")

@bot.command()
async def ping(ctx):
    latency = round(bot.latency * 1000)
    await ctx.send(f"Pong! 🏓 {latency}ms")

@bot.command()
async def afk(ctx, *, sabab="Bandman"):
    try: await ctx.message.delete()
    except: pass

    afk_users[ctx.author.id] = sabab
    try:
        await ctx.author.send(f"🤫 **{ctx.author.display_name}**, serverda AFK rejimiga o'tdingiz.\n**Sabab:** {sabab}\nChatda sizni teg qilishsa, men ularga javob beraman.")
    except:
        await ctx.send(f"🤫 {ctx.author.mention}, siz AFK rejimiga o'tdingiz (DM yopiqligi uchun bu yerda yozdim).", delete_after=5)

@bot.command()
async def wiki(ctx, *, qidiruv):
    wiki_uz = wikipediaapi.Wikipedia(
        user_agent='MyDiscordBot/1.0 (https://discordapp.com/users/yourid)',
        language='uz'
    )
    page = wiki_uz.page(qidiruv)

    if page.exists():
        text = page.summary[0:500] + "..." if len(page.summary) > 500 else page.summary
        embed = discord.Embed(title=page.title, description=text, color=discord.Color.blue(), url=page.fullurl)
        embed.set_footer(text="Manba: Wikipedia")
        await ctx.send(embed=embed)
    else:
        wiki_en = wikipediaapi.Wikipedia(
            user_agent='MyDiscordBot/1.0 (https://discordapp.com/users/yourid)',
            language='en'
        )
        page_en = wiki_en.page(qidiruv)
        if page_en.exists():
            text = page_en.summary[0:500] + "..." if len(page_en.summary) > 500 else page_en.summary
            embed = discord.Embed(title=f"{page_en.title} (English)", description=text, color=discord.Color.blue(), url=page_en.fullurl)
            embed.set_footer(text="O'zbekchadan topilmadi, inglizcha natija ko'rsatilyapti.")
            await ctx.send(embed=embed)
        else:
            await ctx.send(f"❌ Kechirasiz, `{qidiruv}` haqida ma'lumot topilmadi.")

@bot.command()
async def avatar(ctx, member: discord.Member = None):
    member = member or ctx.author
    embed = discord.Embed(title=f"{member.display_name} ning avatari", color=discord.Color.teal())
    embed.set_image(url=member.display_avatar.url)
    await ctx.send(embed=embed)

@bot.command()
async def user(ctx, member: discord.Member = None):
    member = member or ctx.author
    embed = discord.Embed(title=f"👤 {member.display_name} haqida", color=discord.Color.blue())
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="Username:", value=member.name, inline=True)
    embed.add_field(name="ID:", value=member.id, inline=True)
    embed.add_field(name="Serverga kirdi:", value=member.joined_at.strftime("%d.%m.%Y"), inline=True)
    embed.add_field(name="Discord ochgan:", value=member.created_at.strftime("%d.%m.%Y"), inline=True)
    roles = [role.mention for role in member.roles[1:]]
    embed.add_field(name=f"Rollari ({len(roles)}):", value=" ".join(roles) if roles else "Yo'q", inline=False)
    await ctx.send(embed=embed)

@bot.command()
async def server(ctx):
    guild = ctx.guild
    embed = discord.Embed(title=f"📊 {guild.name}", color=discord.Color.gold())
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    embed.add_field(name="👑 Egasi:", value=guild.owner.mention if guild.owner else "Noma'lum", inline=True)
    embed.add_field(name="👥 A'zolar:", value=f"{guild.member_count} ta", inline=True)
    embed.add_field(name="💬 Kanallar:", value=f"{len(guild.text_channels)} ta text | {len(guild.voice_channels)} ta voice", inline=False)
    await ctx.send(embed=embed)

@bot.command()
async def sorov(ctx, *, savol):
    await ctx.message.delete()
    embed = discord.Embed(title="📊 So'rovnoma", description=savol, color=discord.Color.green())
    embed.set_footer(text=f"Muallif: {ctx.author.display_name}")
    poll = await ctx.send(embed=embed)
    await poll.add_reaction("👍")
    await poll.add_reaction("👎")

@bot.command()
async def zar(ctx):
    natija = random.randint(1, 6)
    await ctx.send(f"🎲 Zar: **{natija}**!")

# --- YANGI FOYDALI KOMANDA: ESLATMA ---
@bot.command()
async def eslat(ctx, vaqt: int, *, matn):
    await ctx.send(f"⏰ Tushundim, {ctx.author.mention}! **{vaqt}** daqiqadan so'ng sizga eslataman.")
    await asyncio.sleep(vaqt * 60)
    await ctx.send(f"🔔 {ctx.author.mention}, vaqt bo'ldi! Eslatma: **{matn}**")

# =========================================================================
# MODERATSIYA VA ADMIN KOMANDALARI
# =========================================================================

# 1. Say (aytg o'rniga qisqa va qulay)
@bot.command()
@commands.has_permissions(manage_messages=True)
async def say(ctx, *, xabar):
    await ctx.message.delete()
    await ctx.send(xabar)

# 2. Slow (sekin o'rniga)
@bot.command()
@commands.has_permissions(manage_channels=True)
async def slow(ctx, son: int):
    await ctx.channel.edit(slowmode_delay=son)
    if son == 0:
        await ctx.send("⚡ Chatdagi cheklov o'chirildi.")
    else:
        await ctx.send(f"🐢 Chatga **{son}** soniyalik slowmode qo'yildi.")

# 3. Warn (Yangi: Ogohlantirish)
@bot.command()
@commands.has_permissions(kick_members=True)
async def warn(ctx, member: discord.Member, *, sabab="Qoidabuzarlik"):
    embed = discord.Embed(
        title="⚠️ Ogohlantirish berildi!",
        description=f"{member.mention} ogohlantirildi.\n**Sabab:** {sabab}\n**Moderator:** {ctx.author.display_name}",
        color=discord.Color.yellow()
    )
    await ctx.send(embed=embed)

# 4. Unban (Bandan chiqarish)
@bot.command()
@commands.has_permissions(ban_members=True)
async def unban(ctx, *, user_name):
    banned_users = [entry async for entry in ctx.guild.bans()]
    for ban_entry in banned_users:
        user = ban_entry.user
        if user.name.lower() == user_name.lower():
            await ctx.guild.unban(user)
            await ctx.send(f"🔓 **{user.name}** bandan chiqarildi!")
            return
    await ctx.send("❌ Bunday foydalanuvchi ban ro'yxatida topilmadi.")

@bot.command()
@commands.has_permissions(administrator=True)
async def holat(ctx):
    uptime = int(time.time() - start_time)
    hours, minutes = uptime // 3600, (uptime % 3600) // 60
    embed = discord.Embed(title="🤖 Bot Holati", color=discord.Color.gold())
    embed.add_field(name="🛡️ Serverlar", value=f"{len(bot.guilds)} ta", inline=True)
    embed.add_field(name="👥 Jami a'zolar", value=f"{sum(g.member_count for g in bot.guilds)} ta", inline=True)
    embed.add_field(name="⚡ Ping", value=f"{round(bot.latency * 1000)}ms", inline=True)
    embed.add_field(name="⏳ Uptime", value=f"{hours}s, {minutes}d", inline=True)
    embed.add_field(name="📌 Buyruqlar soni", value=f"{len(bot.commands)} ta", inline=True)
    await ctx.send(embed=embed)

@bot.command()
@commands.has_permissions(manage_roles=True)
async def rol(ctx, member: discord.Member, role: discord.Role):
    if role in member.roles:
        await member.remove_roles(role)
        embed = discord.Embed(description=f"❌ **{role.name}** roli **{member.display_name}**dan olib tashlandi.", color=discord.Color.red())
    else:
        await member.add_roles(role)
        embed = discord.Embed(description=f"✅ **{role.name}** roli **{member.display_name}**ga berildi.", color=discord.Color.green())
    await ctx.send(embed=embed)

@bot.command()
@commands.has_permissions(administrator=True)
async def dm(ctx, member: discord.Member, *, xabar):
    try:
        embed = discord.Embed(title="📩 Server Adminidan xabar", description=xabar, color=discord.Color.blue())
        embed.set_footer(text=f"Server: {ctx.guild.name}")
        await member.send(embed=embed)
        await ctx.send(f"✅ Xabar **{member.display_name}**ga yuborildi.", delete_after=4)
    except:
        await ctx.send(f"❌ Xabar yuborib bo'lmadi! (DM yopiq)", delete_after=4)

@bot.command()
@commands.has_permissions(manage_messages=True)
async def tozala(ctx, limit: int = 5):
    await ctx.channel.purge(limit=limit + 1)
    await ctx.send(f"🧹 **{limit}** ta xabar tozalandi.", delete_after=3)

@bot.command()
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, sabab="Ko'rsatilmadi"):
    await member.kick(reason=sabab)
    await ctx.send(f"👢 **{member.display_name}** serverdan haydaldi. Sabab: {sabab}")

@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, sabab="Ko'rsatilmadi"):
    await member.ban(reason=sabab)
    await ctx.send(f"🔨 **{member.display_name}** bloklandi. Sabab: {sabab}")

@bot.command()
@commands.has_permissions(moderate_members=True)
async def mute(ctx, member: discord.Member, vaqt: int, *, sabab="Ko'rsatilmadi"):
    duration = timedelta(minutes=vaqt)
    await member.timeout(duration, reason=sabab)
    await ctx.send(f"🔇 **{member.display_name}** {vaqt} daqiqaga mute qilindi.")

@bot.command()
@commands.has_permissions(moderate_members=True)
async def unmute(ctx, member: discord.Member):
    await member.timeout(None)
    await ctx.send(f"🔊 **{member.display_name}**dan mute olib tashlandi.")

# --- XATOLIKLARNI USHLASH ---
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ Bu komandani ishlatish uchun sizda yetarli huquq yo'q!", delete_after=4)
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("❌ Komandani noto'g'ri yozdingiz. Yordam uchun: `!yordam`", delete_after=4)
    elif isinstance(error, commands.CommandNotFound):
        pass

# =========================================================================
# BOTNI ISHGA TUSHIRISH
# =========================================================================
import os
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

if not TOKEN:
    print("XATOLIK: DISCORD_TOKEN topilmadi! .env faylni tekshiring.")
else:
    bot.run(TOKEN)