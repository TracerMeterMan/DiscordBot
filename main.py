import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
import datetime
from keep_alive import keep_alive

# -----------------------------
# LOAD CONFIG
# -----------------------------
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID"))
FEEDBACK_CHANNEL_ID = int(os.getenv("FEEDBACK_CHANNEL_ID"))
WRITING_SHOWCASE_CHANNEL_ID = int(os.getenv("WRITING_SHOWCASE_CHANNEL_ID"))
BOT_COMMANDS_ID = int(os.getenv("BOT_COMMANDS_ID"))

# -----------------------------
# SET UP BOT
# -----------------------------
intents = discord.Intents.default()
intents.message_content = True
intents.members = True  # Needed for auto role assignment
bot = commands.Bot(command_prefix="!", intents=intents)

# Track last booking requests for 1-per-day restriction
last_booking_requests = {}

# -----------------------------
# HELPER: CHECK ALLOWED CHANNEL
# -----------------------------
def is_allowed_channel(ctx):
    return isinstance(ctx.channel, discord.DMChannel) or (ctx.guild and ctx.channel.id == BOT_COMMANDS_ID)

# -----------------------------
# EVENT: ON READY
# -----------------------------
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} (ID: {bot.user.id})")

# -----------------------------
# EVENT: AUTO ASSIGN MEMBER ROLE
# -----------------------------
@bot.event
async def on_member_join(member):
    guild = member.guild
    role = discord.utils.get(guild.roles, name="Member")  # Hardcoded role name
    if role:
        try:
            await member.add_roles(role)
            print(f"✅ Assigned {role.name} role to {member.name}")
        except Exception as e:
            print(f"⚠️ Could not assign role: {e}")
    else:
        print("⚠️ 'Member' role not found in this server.")

# -----------------------------
# COMMAND: REQUEST BOOKING
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
            await ctx.send("⏳ You can only make one booking request per day.")
            return

    last_booking_requests[user.id] = now
    valid_types = ["CRT", "PRT", "Creative", "Other"]

    while True:
        await ctx.send("📚 What type of booking? Reply with CRT, PRT, Creative, or Other.")
        try:
            msg_type = await bot.wait_for(
                "message",
                check=lambda m: m.author == user and m.channel == ctx.channel,
                timeout=120,
            )
        except:
            await ctx.send("⌛ Booking timed out. Please try again.")
            last_booking_requests.pop(user.id, None)
            return
        if msg_type.content.strip() in valid_types:
            break
        await ctx.send("⚠️ Please enter a valid booking type: CRT, PRT, Creative, or Other.")

    while True:
        await ctx.send("💬 Any additional comments? (max 20 words, or type 'none')")
        try:
            msg_comments = await bot.wait_for(
                "message",
                check=lambda m: m.author == user and m.channel == ctx.channel,
                timeout=250,
            )
        except:
            await ctx.send("⌛ Booking timed out. Please try again.")
            last_booking_requests.pop(user.id, None)
            return

        comments = msg_comments.content.strip()
        if comments.lower() == "none":
            comments = "No additional comments."
            break
        elif len(comments.split()) > 20:
            await ctx.send("⚠️ Too long! Please limit to 20 words and try again.")
            continue
        else:
            break

    owner = await bot.fetch_user(OWNER_ID)
    await owner.send(
        f"📩 **Booking Request**\n"
        f"👤 From: {user.name}#{user.discriminator}\n"
        f"📘 Type: {msg_type.content.strip()}\n"
        f"💬 Comments: {comments}"
    )
    await ctx.send("✅ Your booking request has been sent!")

# -----------------------------
# COMMAND: FEEDBACK
# -----------------------------
@bot.command()
@commands.cooldown(1, 900, commands.BucketType.user)  # 1 use per 15 min per user
async def feedback(ctx, *, message: str):
    if not is_allowed_channel(ctx):
        return

    # Word limit
    if len(message.split()) > 50:
        await ctx.send("⚠️ Too long! Please limit to 50 words.")
        return

    feedback_channel = bot.get_channel(FEEDBACK_CHANNEL_ID)
    if not feedback_channel:
        await ctx.send("⚠️ Feedback channel not found.")
        return

    embed = discord.Embed(
        title="📩 New Feedback",
        description=message,
        color=discord.Color.blue()
    )
    embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
    await feedback_channel.send(embed=embed)
    await ctx.send("✅ Your feedback has been sent!")

# -----------------------------
# COMMAND: ANONYMOUS FEEDBACK
# -----------------------------
@bot.command()
@commands.cooldown(1, 900, commands.BucketType.user)  # 1 use per 15 min per user
async def anonymousfeedback(ctx, *, message: str):
    if not is_allowed_channel(ctx):
        return

    # Word limit
    if len(message.split()) > 50:
        await ctx.send("⚠️ Too long! Please limit to 50 words.")
        return

    feedback_channel = bot.get_channel(FEEDBACK_CHANNEL_ID)
    if not feedback_channel:
        await ctx.send("⚠️ Feedback channel not found.")
        return

    embed = discord.Embed(
        title="📩 Anonymous Feedback",
        description=message,
        color=discord.Color.purple()
    )
    await feedback_channel.send(embed=embed)
    await ctx.send("✅ Your anonymous feedback has been sent!")

# -----------------------------
# COMMAND: SHOWCASE
# -----------------------------
@bot.command(name="showcase")
async def showcase(ctx):
    if not is_allowed_channel(ctx):
        return

    user = ctx.author
    channel = bot.get_channel(WRITING_SHOWCASE_CHANNEL_ID)
    if not channel:
        await ctx.send("⚠️ Showcase channel not found.")
        return

    await ctx.send("✍️ Enter your **pen name**:")
    try:
        pen_name_msg = await bot.wait_for(
            "message",
            check=lambda m: m.author == user and m.channel == ctx.channel,
            timeout=120
        )
    except:
        await ctx.send("⌛ Showcase timed out. Please try again.")
        return
    pen_name = pen_name_msg.content.strip()
    if not pen_name:
        await ctx.send("⚠️ Pen name cannot be empty.")
        return

    await ctx.send("📖 Enter the **title** of your writing:")
    try:
        title_msg = await bot.wait_for(
            "message",
            check=lambda m: m.author == user and m.channel == ctx.channel,
            timeout=120
        )
    except:
        await ctx.send("⌛ Showcase timed out. Please try again.")
        return
    title = title_msg.content.strip()
    if not title:
        await ctx.send("⚠️ Title cannot be empty.")
        return

    await ctx.send("📝 Enter your **writing** (up to 2000 words):")
    try:
        writing_msg = await bot.wait_for(
            "message",
            check=lambda m: m.author == user and m.channel == ctx.channel,
            timeout=600
        )
    except:
        await ctx.send("⌛ Showcase timed out. Please try again.")
        return
    writing_content = writing_msg.content.strip()
    if len(writing_content.split()) > 2000:
        await ctx.send("⚠️ Too long! Please limit to 2000 words.")
        return

    showcase_post = await channel.send(
        f"**{title}** by *{pen_name}*\n\n{writing_content}"
    )
    await showcase_post.create_thread(
        name=f"Review of {title} by {pen_name}",
        auto_archive_duration=1440
    )
    await ctx.send(f"✅ Your writing has been posted in {channel.mention} and a review thread was created!")

# -----------------------------
# COOLDOWN ERROR HANDLER
# -----------------------------
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"⏳ You can use this command again in {round(error.retry_after / 60, 1)} minutes.")
    else:
        raise error

# -----------------------------
# RUN BOT
# -----------------------------
keep_alive()
bot.run(TOKEN)
