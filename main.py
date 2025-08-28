# main.py
import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
import datetime
from flask import Flask
from threading import Thread
import asyncio

# -----------------------------
# ENVIRONMENT
# -----------------------------
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID"))
FEEDBACK_CHANNEL_ID = int(os.getenv("FEEDBACK_CHANNEL_ID"))
WRITING_SHOWCASE_CHANNEL_ID = int(os.getenv("WRITING_SHOWCASE_CHANNEL_ID"))
BOT_COMMANDS_ID = int(os.getenv("BOT_COMMANDS_ID"))

# -----------------------------
# DISCORD BOT SETUP
# -----------------------------
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Track last booking requests for 1-per-day restriction
last_booking_requests = {}

# Channel check
def is_allowed_channel(ctx):
    return isinstance(ctx.channel, discord.DMChannel) or (ctx.guild and ctx.channel.id == BOT_COMMANDS_ID)

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} (ID: {bot.user.id})")

# -----------------------------
# BOOKING COMMAND
# -----------------------------
@bot.command(name="requestbooking")
async def request_booking(ctx):
    if not is_allowed_channel(ctx):
        return

    user = ctx.author
    now = datetime.datetime.now()

    if user.id in last_booking_requests:
        delta = now - last_booking_requests[user.id]
        if delta.total_seconds() < 86400:
            await ctx.send("You can only make one booking request per day.")
            return

    last_booking_requests[user.id] = now

    while True:
        await ctx.send("Explain your booking in less than 50 words. We will provide you with a quote in 24 hours.")
        try:
            msg_booking = await bot.wait_for(
                "message",
                check=lambda m: m.author == user and m.channel == ctx.channel,
                timeout=250,
            )
        except asyncio.TimeoutError:
            await ctx.send("⌛ Booking timed out. Please try again.")
            last_booking_requests.pop(user.id, None)
            return

        booking_details = msg_booking.content.strip()
        if len(booking_details.split()) > 50:
            await ctx.send("Too long! Please limit to 50 words and try again.")
            continue
        else:
            break

    try:
        owner = await bot.fetch_user(OWNER_ID)
        await owner.send(
            f"📩 **Booking Request**\n"
            f"👤 From: {user.name}#{user.discriminator}\n"
            f"💬 Booking Details: {booking_details}"
        )
    except discord.HTTPException as e:
        print(f"Failed to send booking DM: {e}")

    await ctx.send("Your booking request has been sent! You’ll receive a quote within 24 hours.")

# -----------------------------
# FEEDBACK COMMANDS
# -----------------------------
@bot.command()
@commands.cooldown(1, 900, commands.BucketType.user)
async def feedback(ctx, *, message: str):
    if not is_allowed_channel(ctx):
        return

    if len(message.split()) > 50:
        await ctx.send("Too long! Please limit to 50 words.")
        return

    feedback_channel = bot.get_channel(FEEDBACK_CHANNEL_ID)
    if not feedback_channel:
        await ctx.send("Feedback channel not found.")
        return

    embed = discord.Embed(title="Feedback", description=message, color=discord.Color.blue())
    embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
    await feedback_channel.send(embed=embed)
    await ctx.send("Your feedback has been sent!")

@bot.command()
@commands.cooldown(1, 900, commands.BucketType.user)
async def anonymousfeedback(ctx, *, message: str):
    if not is_allowed_channel(ctx):
        return

    if len(message.split()) > 50:
        await ctx.send("Too long! Please limit to 50 words.")
        return

    feedback_channel = bot.get_channel(FEEDBACK_CHANNEL_ID)
    if not feedback_channel:
        await ctx.send("Feedback channel not found.")
        return

    embed = discord.Embed(title="📩 Anonymous Feedback", description=message, color=discord.Color.purple())
    await feedback_channel.send(embed=embed)
    await ctx.send("Your anonymous feedback has been sent!")

# -----------------------------
# SHOWCASE COMMAND
# -----------------------------
@bot.command(name="showcase")
async def showcase(ctx):
    if not is_allowed_channel(ctx):
        return

    user = ctx.author
    channel = bot.get_channel(WRITING_SHOWCASE_CHANNEL_ID)
    if not channel:
        await ctx.send("Showcase channel not found.")
        return

    await ctx.send("Enter your **pen name**:")
    try:
        pen_name_msg = await bot.wait_for(
            "message",
            check=lambda m: m.author == user and m.channel == ctx.channel,
            timeout=120
        )
    except asyncio.TimeoutError:
        await ctx.send("⌛ Showcase timed out. Please try again.")
        return
    pen_name = pen_name_msg.content.strip()
    if not pen_name:
        await ctx.send("Pen name cannot be empty.")
        return

    await ctx.send("📖 Enter the **title** of your writing:")
    try:
        title_msg = await bot.wait_for(
            "message",
            check=lambda m: m.author == user and m.channel == ctx.channel,
            timeout=120
        )
    except asyncio.TimeoutError:
        await ctx.send("⌛ Showcase timed out. Please try again.")
        return
    title = title_msg.content.strip()
    if not title:
        await ctx.send("Title cannot be empty.")
        return

    await ctx.send("Enter your **writing** (up to 2000 words):")
    try:
        writing_msg = await bot.wait_for(
            "message",
            check=lambda m: m.author == user and m.channel == ctx.channel,
            timeout=600
        )
    except asyncio.TimeoutError:
        await ctx.send("Showcase timed out. Please try again.")
        return
    writing_content = writing_msg.content.strip()
    if len(writing_content.split()) > 2000:
        await ctx.send("Too long! Please limit to 2000 words.")
        return

    showcase_post = await channel.send(f"**{title}** by *{pen_name}*\n\n{writing_content}")
    await showcase_post.create_thread(
        name=f"Feedback for {title} by {pen_name}",
        auto_archive_duration=1440
    )
    await ctx.send(f"Your writing has been posted in {channel.mention} and a review thread was created!")

# -----------------------------
# ERROR HANDLER
# -----------------------------
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"You can use this command again in {round(error.retry_after / 60, 1)} minutes.")
    else:
        raise error

# -----------------------------
# FLASK KEEP ALIVE
# -----------------------------
app = Flask('')

@app.route('/')
def home():
    return 'Bot is alive!'

def run():
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()

# -----------------------------
# RUN BOT
# -----------------------------
keep_alive()
bot.run(TOKEN)
