import discord
from discord.ext import commands
from discord import app_commands
import time
import os
import random
import asyncio
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
        # Slash komandalarni Discord serverlari bilan sinxronizatsiya qilish
        await self.tree.sync()
        print("Slash komandalar sinxronizatsiya qilindi!")

bot = MyBot()
start_time = time.time()

@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="/yordam"))
    print(f'======================================')
    print(f'Bot ishga tushdi: {bot.user.name}')
    print(f'Slash komandalar tayyor!')
    print(f'======================================')

# --- SLASH KOMANDALAR ---

@bot.tree.command(name="ping", description="Bot tezligini tekshirish")
async def ping_slash(interaction: discord.Interaction):
    latency = round(bot.latency * 1000)
    await interaction.response.send_message(f"Pong! 🏓 {latency}ms")

@bot.tree.command(name="yordam", description="Bot komandalari ro'yxati")
async def yordam_slash(interaction: discord.Interaction):
    embed = discord.Embed(title="📜 Bot Komandalari", color=discord.Color.purple())
    embed.add_field(name="Slash Komandalar", value="`/ping`, `/yordam`, `/avatar`, `/holat`, `/tozala`", inline=False)
    embed.add_field(name="Prefiks Komandalar", value="Bot hali ham `!` prefiksli komandalarni ham tushunadi.", inline=False)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="avatar", description="Foydalanuvchi avatarini ko'rish")
@app_commands.describe(user="Avatarini ko'rmoqchi bo'lgan foydalanuvchingiz")
async def avatar_slash(interaction: discord.Interaction, user: discord.Member = None):
    user = user or interaction.user
    embed = discord.Embed(title=f"{user.display_name} avatari")
    embed.set_image(url=user.display_avatar.url)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="holat", description="Bot statistikasini ko'rish")
async def holat_slash(interaction: discord.Interaction):
    uptime = int(time.time() - start_time)
    embed = discord.Embed(title="🤖 Bot Holati", color=discord.Color.gold())
    embed.add_field(name="Serverlar", value=len(bot.guilds))
    embed.add_field(name="Ping", value=f"{round(bot.latency * 1000)}ms")
    embed.add_field(name="Uptime", value=f"{uptime//3600}s, {(uptime%3600)//60}d")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="tozala", description="Xabarlarni tozalash")
@app_commands.describe(son="Qancha xabar o'chirilsin?")
@app_commands.checks.has_permissions(manage_messages=True)
async def tozala_slash(interaction: discord.Interaction, son: int = 5):
    await interaction.response.defer(ephemeral=True) # Javobni kechiktirish (tozalash vaqt olishi mumkin)
    await interaction.channel.purge(limit=son)
    await interaction.followup.send(f"✅ {son} ta xabar tozalandi!", ephemeral=True)

# --- ESKI PREFIKS KOMANDALAR HAM ISHLAYVERADI ---
@bot.command()
async def salom(ctx): await ctx.send(f"Salom! Prefiks komandalar ham ishlayapti.")

# --- ISHGA TUSHIRISH ---
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

if __name__ == '__main__':
    keep_alive()
    if TOKEN:
        bot.run(TOKEN)
    else:
        print("XATOLIK: DISCORD_TOKEN topilmadi!")
