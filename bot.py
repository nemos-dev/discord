import discord
from discord.ext import commands
from discord import app_commands
import time
import os
import random
import asyncio
import aiohttp
import wikipediaapi
from datetime import timedelta
from flask import Flask
from threading import Thread
from dotenv import load_dotenv

# --- BEPUL HOSTING (RENDER) UCHUN KEEPALIVE WEBSERVER ---
app = Flask('')

@app.route('/')
def home():
    return "Bot 24/7 rejimida ishlamoqda!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    try:
        app.run(host='0.0.0.0', port=port)
    except Exception as e:
        print(f"Web server xatosi: {e}")

def keep_alive():
    t = Thread(target=run_web)
    t.daemon = True
    t.start()

# --- BOT SOZLAMALARI ---
class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(command_prefix='!', intents=intents)

    async def setup_hook(self):
        await self.tree.sync()
        print("Barcha Slash komandalar sinxronizatsiya qilindi!")

bot = MyBot()
start_time = time.time()
afk_users = {}
user_messages = {}
user_mentions = {}
user_offenses = {}

@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="/yordam"))
    print(f'======================================')
    print(f'Bot muvaffaqiyatli ishga tushdi: {bot.user.name}')
    print(f'======================================')

# --- AVTOMATIK HIMOYA VA AFK TIZIMI ---
@bot.event
async def on_message(message):
    if message.author.bot: return

    user_id = message.author.id
    current_time = time.time()

    # 1. Anti-Spam
    if user_id not in user_messages: user_messages[user_id] = []
    user_messages[user_id].append(current_time)
    user_messages[user_id] = [t for t in user_messages[user_id] if current_time - t < 3]
    if len(user_messages[user_id]) > 4:
        try: await message.delete()
        except: pass
        return

    # 2. AFK tekshiruvi
    for mention in message.mentions:
        if mention.id in afk_users:
            reason = afk_users[mention.id]
            embed = discord.Embed(title="⚠️ Foydalanuvchi band", description=f"**{mention.display_name}** hozir AFK.\n**Sabab:** {reason}", color=discord.Color.orange())
            await message.channel.send(embed=embed, delete_after=6)

    if message.author.id in afk_users:
        del afk_users[message.author.id]
        await message.channel.send(f"👋 Xush kelibsiz, **{message.author.display_name}**! AFK rejimi o'chirildi.", delete_after=5)

    await bot.process_commands(message)

@bot.event
async def on_member_join(member):
    embed = discord.Embed(
        title="Yangi mehmon! 🎉",
        description=f"Xush kelibsiz, {member.mention}! Qoidalar bilan tanishib chiqing.",
        color=discord.Color.green()
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.set_footer(text=f"Jami a'zolar: {member.guild.member_count}")
    for channel in member.guild.text_channels:
        if any(name in channel.name.lower() for name in ["chat", "umumiy", "general", "welcome"]):
            await channel.send(embed=embed)
            break


# =========================================================================
# 🚀 TO'LIQ SLASH KOMANDALAR (Dizaynli va Yengil)
# =========================================================================

@bot.tree.command(name="yordam", description="Botning barcha komandalari ro'yxati")
async def yordam(interaction: discord.Interaction):
    embed = discord.Embed(title="📜 Bot Komandalari Markazi", description="Barcha komandalar **Slash (/)** orqali ishlaydi.", color=discord.Color.purple())
    embed.add_field(name="🌐 Umumiy & Foydali", value="`/ping`, `/yordam`, `/avatar`, `/server`, `/zar`, `/sorov`", inline=False)
    embed.add_field(name="✨ Yangi Imkoniyatlar", value="`/ob-havo`, `/wiki`, `/eslatma`", inline=False)
    embed.add_field(name="🛡️ Moderatsiya", value="`/tozala`, `/kick`, `/ban`, `/mute`, `/slow`", inline=False)
    embed.set_footer(text=f"So'rovchi: {interaction.user.display_name}")
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="ping", description="Botning tarmoq tezligini ko'rsatadi")
async def ping(interaction: discord.Interaction):
    latency = round(bot.latency * 1000)
    embed = discord.Embed(title="🏓 Pong!", description=f"Bot kechikishi: **{latency} ms**", color=discord.Color.green())
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="avatar", description="Foydalanuvchi profil rasmini ko'rsatadi")
@app_commands.describe(user="Kimning avatari kerak?")
async def avatar(interaction: discord.Interaction, user: discord.Member = None):
    user = user or interaction.user
    embed = discord.Embed(title=f"🖼️ {user.display_name} ning avatari", color=discord.Color.teal())
    embed.set_image(url=user.display_avatar.url)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="server", description="Server haqida qisqacha ma'lumot")
async def server(interaction: discord.Interaction):
    guild = interaction.guild
    embed = discord.Embed(title=f"📊 {guild.name}", color=discord.Color.gold())
    if guild.icon: embed.set_thumbnail(url=guild.icon.url)
    embed.add_field(name="👑 Egasi:", value=guild.owner.mention if guild.owner else "Noma'lum", inline=True)
    embed.add_field(name="👥 A'zolar soni:", value=f"{guild.member_count} ta", inline=True)
    embed.add_field(name="💬 Kanallar:", value=f"{len(guild.text_channels)} text | {len(guild.voice_channels)} voice", inline=False)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="zar", description="1 dan 6 gacha tasodifiy son tashlaydi")
async def zar(interaction: discord.Interaction):
    natija = random.randint(1, 6)
    embed = discord.Embed(title="🎲 Zar tashlash", description=f"Natija: **{natija}**!", color=discord.Color.blue())
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="sorov", description="Ovoz berish (sorovnoma) yaratish")
@app_commands.describe(savol="So'rovnoma matni")
async def sorov(interaction: discord.Interaction, savol: str):
    embed = discord.Embed(title="📊 So'rovnoma", description=savol, color=discord.Color.green())
    embed.set_footer(text=f"Muallif: {interaction.user.display_name}")
    await interaction.response.send_message(embed=embed)
    message = await interaction.original_response()
    await message.add_reaction("👍")
    await message.add_reaction("👎")

@bot.tree.command(name="wiki", description="Wikipedia'dan ma'lumot qidirish")
@app_commands.describe(qidiruv="Nimani qidiramiz?")
async def wiki(interaction: discord.Interaction, qidiruv: str):
    await interaction.response.defer()
    wiki_uz = wikipediaapi.Wikipedia(user_agent='MyDiscordBot/2.0', language='uz')
    page = wiki_uz.page(qidiruv)
    if page.exists():
        text = page.summary[0:600] + "..." if len(page.summary) > 600 else page.summary
        embed = discord.Embed(title=page.title, description=text, color=discord.Color.blue(), url=page.fullurl)
        embed.set_footer(text="Manba: Wikipedia (O'zbekcha)")
        await interaction.followup.send(embed=embed)
    else:
        await interaction.followup.send(f"❌ `{qidiruv}` bo'yicha ma'lumot topilmadi.")

@bot.tree.command(name="ob-havo", description="Shahar bo'yicha ob-havo ma'lumotini olish")
@app_commands.describe(shahar="Shahar nomi (masalan: Toshkent, Samarkand, London)")
async def ob_havo(interaction: discord.Interaction, shahar: str):
    await interaction.response.defer()
    try:
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={shahar}&count=1"
        async with aiohttp.ClientSession() as session:
            async with session.get(geo_url) as resp:
                geo_data = await resp.json()
                if not geo_data.get("results"):
                    await interaction.followup.send(f"❌ `{shahar}` shahri topilmadi.")
                    return
                loc = geo_data["results"][0]
                lat, lon, name, country = loc["lat"], loc["lon"], loc["name"], loc.get("country", "")

            weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
            async with session.get(weather_url) as resp:
                w_data = await resp.json()
                current = w_data["current_weather"]
                temp = current["temperature"]
                wind = current["windspeed"]

        embed = discord.Embed(title=f"🌤️ {name}, {country} ob-havosi", color=discord.Color.orange())
        embed.add_field(name="🌡️ Harorat", value=f"{temp}°C", inline=True)
        embed.add_field(name="💨 Shamol tezligi", value=f"{wind} km/s", inline=True)
        embed.set_footer(text="Ma'lumot Open-Meteo dan olindi")
        await interaction.followup.send(embed=embed)
    except Exception as e:
        await interaction.followup.send("❌ Ob-havo ma'lumotini olishda xatolik yuz berdi.")

@bot.tree.command(name="eslatma", description="Belgilangan vaqtdan so'ng sizga eslatma yuboradi")
@app_commands.describe(daqiqa="Necha daqiqadan so'ng?", eslatma="Eslatma matni")
async def eslatma(interaction: discord.Interaction, daqiqa: int, eslatma: str):
    await interaction.response.send_message(f"⏰ Tushundim! **{daqiqa}** daqiqadan so'ng sizga eslataman.", ephemeral=True)
    await asyncio.sleep(daqiqa * 60)
    try:
        embed = discord.Embed(title="🔔 Vaqt bo'ldi!", description=f"**Eslatma:** {eslatma}", color=discord.Color.gold())
        await interaction.user.send(embed=embed)
    except:
        pass

# --- MODERATSIYA SLASH KOMANDALARI ---

@bot.tree.command(name="tozala", description="Chatdagi xabarlarni o'chirish")
@app_commands.describe(son="Nechta xabar o'chirilsin?")
@app_commands.checks.has_permissions(manage_messages=True)
async def tozala(interaction: discord.Interaction, son: int = 5):
    await interaction.response.defer(ephemeral=True)
    deleted = await interaction.channel.purge(limit=son)
    await interaction.followup.send(f"🧹 Muvaffaqiyatli **{len(deleted)}** ta xabar tozalandi!", ephemeral=True)

@bot.tree.command(name="kick", description="Foydalanuvchini serverdan haydash")
@app_commands.describe(user="Kim haydalsin?", sabab="Sababi")
@app_commands.checks.has_permissions(kick_members=True)
async def kick(interaction: discord.Interaction, user: discord.Member, sabab: str = "Ko'rsatilmadi"):
    await user.kick(reason=sabab)
    embed = discord.Embed(title="👢 Foydalanuvchi haydaldi", description=f"**{user.display_name}** serverdan haydaldi.\n**Sabab:** {sabab}", color=discord.Color.red())
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="ban", description="Foydalanuvchini ban qilish")
@app_commands.describe(user="Kim ban qilinsin?", sabab="Sababi")
@app_commands.checks.has_permissions(ban_members=True)
async def ban(interaction: discord.Interaction, user: discord.Member, sabab: str = "Ko'rsatilmadi"):
    await user.ban(reason=sabab)
    embed = discord.Embed(title="🔨 Foydalanuvchi bloklandi", description=f"**{user.display_name}** ban qilindi.\n**Sabab:** {sabab}", color=discord.Color.dark_red())
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="mute", description="Foydalanuvchini vaqtincha gapirishdan cheklash")
@app_commands.describe(user="Kim mute qilinsin?", daqiqa="Necha daqiqa?", sabab="Sababi")
@app_commands.checks.has_permissions(moderate_members=True)
async def mute(interaction: discord.Interaction, user: discord.Member, daqiqa: int, sabab: str = "Ko'rsatilmadi"):
    duration = timedelta(minutes=daqiqa)
    await user.timeout(duration, reason=sabab)
    embed = discord.Embed(title="🔇 Mute qilindi", description=f"**{user.display_name}** {daqiqa} daqiqaga mute qilindi.\n**Sabab:** {sabab}", color=discord.Color.orange())
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="slow", description="Chatga sekinlik (slowmode) qo'yish")
@app_commands.describe(son="Soniya (0 - o'chirish uchun)")
@app_commands.checks.has_permissions(manage_channels=True)
async def slow(interaction: discord.Interaction, son: int):
    await interaction.channel.edit(slowmode_delay=son)
    if son == 0:
        await interaction.response.send_message("⚡ Chatdagi slowmode o'chirildi.")
    else:
        await interaction.response.send_message(f"🐢 Chatga **{son}** soniyalik slowmode o'rnatildi.")


# --- XATOLARNI USHLASH ---
@tozala.error
@kick.error
@ban.error
@mute.error
@slow.error
async def moderation_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.errors.MissingPermissions):
        await interaction.response.send_message("❌ Kechirasiz, bu komandani ishlatish uchun huquqingiz yetarli emas!", ephemeral=True)
    else:
        await interaction.response.send_message(f"❌ Xatolik yuz berdi: {error}", ephemeral=True)


# =========================================================================
# BOTNI ISHGA TUSHIRISH
# =========================================================================
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

if __name__ == '__main__':
    keep_alive()
    if TOKEN:
        bot.run(TOKEN)
    else:
        print("XATOLIK: DISCORD_TOKEN topilmadi!")
