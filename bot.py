import discord
from discord.ext import commands
import time
import os
import random
import asyncio
import wikipediaapi
from datetime import timedelta
from flask import Flask
from threading import Thread
from dotenv import load_dotenv

# --- BEPUL HOSTING UCHUN KEEPALIVE WEBSERVER ---
app = Flask('')

@app.route('/')
def home():
    return "Bot 24/7 rejimida ishlamoqda!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_web)
    t.daemon = True
    t.start()

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

        try:
            dm_embed = discord.Embed(
                title="⛔ Serverda Mute bo'ldingiz!",
                description=f"Siz **{channel.guild.name}** serverida 3/3 Ogohlantirish oldingiz va **24 soatga Mute** qilindingiz.\n**Sabab:** {reason}\n\nIltimos, keyinroq qoidalarga amal qiling!",
                color=discord.Color.red()
            )
            await member.send(embed=dm_embed)
        except:
            pass

        user_offenses[user_id] = 0

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

    # 2. KO'P TEG (MENTION)
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

    await bot.process_commands(message)

# --- KOMANDALAR ---
@bot.command()
async def yordam(ctx):
    embed = discord.Embed(title="📜 Bot Komandalari", color=discord.Color.purple())
    embed.set_thumbnail(url=bot.user.display_avatar.url)

    embed.add_field(
        name="👤 Foydalanuvchilar uchun",
        value="`!salom` — Salomlashish\n"
              "`!ping` — Tezlikni ko'rish\n"
              "`!afk [sabab]` — AFK\n"
              "`!wiki <so'z>` — Wikipedia qidiruvi\n"
              "`!avatar [@user]` — Profil rasmini ko'rish\n"
              "`!user [@user]` — Foydalanuvchi profili\n"
              "`!server` — Server ma'lumotlari\n"
              "`!zar` — Zar tashlash\n"
              "`!sorov <savol>` — So'rovnoma\n"
              "`!eslat <daqiqa> <matn>` — Eslatma",
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
              "`!warn @user [sabab]` — Ogohlantirish\n"
              "`!rol @user @rol` — Rol berish/olish\n"
              "`!say <matn>` — Bot nomidan xabar\n"
              "`!dm @user <matn>` — DM xabar\n"
              "`!slow <son>` — Slowmode\n"
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
        await ctx.author.send(f"🤫 **{ctx.author.display_name}**, serverda AFK rejimiga o'tdingiz.\n**Sabab:** {sabab}")
    except:
        await ctx.send(f"🤫 {ctx.author.mention}, siz AFK rejimiga o'tdingiz.", delete_after=5)

@bot.command()
async def wiki(ctx, *, qidiruv):
    wiki_uz = wikipediaapi.Wikipedia(user_agent='MyDiscordBot/1.0', language='uz')
    page = wiki_uz.page(qidiruv)
    if page.exists():
        text = page.summary[0:500] + "..." if len(page.summary) > 500 else page.summary
        embed = discord.Embed(title=page.title, description=text, color=discord.Color.blue(), url=page.fullurl)
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
    await ctx.send(embed=embed)

@bot.command()
async def server(ctx):
    guild = ctx.guild
    embed = discord.Embed(title=f"📊 {guild.name}", color=discord.Color.gold())
    embed.add_field(name="👥 A'zolar:", value=f"{guild.member_count} ta", inline=True)
    await ctx.send(embed=embed)

@bot.command()
async def sorov(ctx, *, savol):
    await ctx.message.delete()
    embed = discord.Embed(title="📊 So'rovnoma", description=savol, color=discord.Color.green())
    poll = await ctx.send(embed=embed)
    await poll.add_reaction("👍")
    await poll.add_reaction("👎")

@bot.command()
async def zar(ctx):
    await ctx.send(f"🎲 Zar: **{random.randint(1, 6)}**!")

@bot.command()
async def eslat(ctx, vaqt: int, *, matn):
    await ctx.send(f"⏰ **{vaqt}** daqiqadan so'ng sizga eslataman.")
    await asyncio.sleep(vaqt * 60)
    await ctx.send(f"🔔 {ctx.author.mention}, eslatma: **{matn}**")

# ADMIN KOMANDALARI
@bot.command()
@commands.has_permissions(manage_messages=True)
async def say(ctx, *, xabar):
    await ctx.message.delete()
    await ctx.send(xabar)

@bot.command()
@commands.has_permissions(manage_messages=True)
async def tozala(ctx, limit: int = 5):
    await ctx.channel.purge(limit=limit + 1)
    await ctx.send(f"🧹 **{limit}** ta xabar tozalandi.", delete_after=3)

# =========================================================================
# BOTNI ISHGA TUSHIRISH
# =========================================================================
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

if __name__ == '__main__':
    keep_alive() # Web serverni ishga tushirish
    if TOKEN:
        bot.run(TOKEN)
    else:
        print("XATOLIK: DISCORD_TOKEN topilmadi!")