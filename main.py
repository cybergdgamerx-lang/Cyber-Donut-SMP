import os
import discord
from discord.ext import commands
from datetime import timedelta

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
TOKEN = os.getenv("Discord_Token", "YOUR_BOT_TOKEN_HERE")
COMMAND_PREFIX = ""  # Morse is parsed manually; no traditional prefix
OPERATOR_ROLE_NAME = "Operator"  # Members with this role can also run commands

# Morse -> Character dictionary
MORSE_TO_CHAR = {
    ".-": "A", "-...": "B", "-.-.": "C", "-..": "D", ".": "E",
    "..-.": "F", "--.": "G", "....": "H", "..": "I", ".---": "J",
    "-.-": "K", ".-..": "L", "--": "M", "-.": "N", "---": "O",
    ".--.": "P", "--.-": "Q", ".-.": "R", "...": "S", "-": "T",
    "..-": "U", "...-": "V", ".--": "W", "-..-": "X", "-.--": "Y",
    "--..": "Z",
    "-----": "0", ".----": "1", "..---": "2", "...--": "3",
    "....-": "4", ".....": "5", "-....": "6", "--...": "7",
    "---..": "8", "----.": "9",
    ".-.-.-": ".", "--..--": ",", "..--..": "?", ".----.": "'",
    "-.-.--": "!", "-..-.": "/", "-.--.": "(", "-.--.-": ")",
    ".-...": "&", "---...": ":", "-.-.-.": ";", "-...-": "=",
    ".-.-.": "+", "-....-": "-", "..--.-": "_", ".-..-.": '"',
    "...-..-": "$", ".--.-.": "@",
}

# Reverse lookup (character -> morse) used for optional encoding
CHAR_TO_MORSE = {v: k for k, v in MORSE_TO_CHAR.items()}

# ---------------------------------------------------------------------------
# Bot setup
# ---------------------------------------------------------------------------
intents = discord.Intents.default()
intents.message_content = True
intents.members = True  # required for kick/ban/mute

bot = commands.Bot(command_prefix=COMMAND_PREFIX, intents=intents)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def morse_to_text(morse: str) -> str | None:
    """
    Convert a Morse string to plain text.
    Letters are separated by single spaces.
    Words are separated by ' / ' (slash with spaces) or '/' alone.

    Returns None if the string contains invalid Morse characters.
    """
    if not morse or not morse.strip():
        return None

    # Reject anything that isn't . - space or /
    if any(c not in ".-/ " for c in morse):
        return None

    words = morse.strip().split("/")
    decoded_words = []

    for word in words:
        letters = word.strip().split()
        decoded_letters = []
        for letter in letters:
            if letter not in MORSE_TO_CHAR:
                return None
            decoded_letters.append(MORSE_TO_CHAR[letter])
        decoded_words.append("".join(decoded_letters))

    text = " ".join(w for w in decoded_words if w)
    # Must contain at least one letter/digit (i.e. real content)
    if not any(ch.isalnum() for ch in text):
        return None
    return text


def is_operator(member: discord.Member) -> bool:
    """Admins, server owner, or members with the Operator role."""
    if member.guild_permissions.administrator:
        return True
    if member == member.guild.owner:
        return True
    return any(role.name == OPERATOR_ROLE_NAME for role in member.roles)


def parse_target_and_reason(args: list[str], guild: discord.Guild):
    """
    Given decoded args (e.g. ['ban', '@User', 'spam', 'reason']),
    return (member, reason).
    """
    if not args:
        return None, None

    target_raw = args[0]
    reason = " ".join(args[1:]) if len(args) > 1 else "No reason provided"

    # Resolve target: mention, ID, or username
    member = None
    if target_raw.startswith("<@") and target_raw.endswith(">"):
        try:
            uid = int(target_raw.strip("<@!>"))
            member = guild.get_member(uid)
        except ValueError:
            pass
    elif target_raw.isdigit():
        member = guild.get_member(int(target_raw))
    else:
        member = discord.utils.find(
            lambda m: m.name.lower() == target_raw.lower()
            or m.display_name.lower() == target_raw.lower(),
            guild.members,
        )

    return member, reason


# ---------------------------------------------------------------------------
# Command implementations
# ---------------------------------------------------------------------------
async def cmd_ban(ctx: commands.Context, args: list[str]):
    member, reason = parse_target_and_reason(args, ctx.guild)
    if member is None:
        await ctx.reply("⚠️ Target not found.")
        return
    if member == ctx.author:
        await ctx.reply("⚠️ You can't ban yourself.")
        return
    try:
        await member.ban(reason=f"[Morse] {reason} (by {ctx.author})")
        await ctx.reply(f"🔨 Banned **{member}** — {reason}")
    except discord.Forbidden:
        await ctx.reply("🚫 I don't have permission to ban that member.")


async def cmd_kick(ctx: commands.Context, args: list[str]):
    member, reason = parse_target_and_reason(args, ctx.guild)
    if member is None:
        await ctx.reply("⚠️ Target not found.")
        return
    if member == ctx.author:
        await ctx.reply("⚠️ You can't kick yourself.")
        return
    try:
        await member.kick(reason=f"[Morse] {reason} (by {ctx.author})")
        await ctx.reply(f"👢 Kicked **{member}** — {reason}")
    except discord.Forbidden:
        await ctx.reply("🚫 I don't have permission to kick that member.")


async def cmd_mute(ctx: commands.Context, args: list[str]):
    """Timeout a member for a given number of minutes (default 10)."""
    member, reason = parse_target_and_reason(args, ctx.guild)
    if member is None:
        await ctx.reply("⚠️ Target not found.")
        return

    # Try to read a numeric duration from the last arg
    duration_min = 10
    tokens = reason.split()
    if tokens and tokens[-1].isdigit():
        duration_min = int(tokens[-1])
        reason = " ".join(tokens[:-1]) or "No reason provided"

    duration = timedelta(minutes=duration_min)
    try:
        await member.timeout(duration, reason=f"[Morse] {reason} (by {ctx.author})")
        await ctx.reply(
            f"🔇 Muted **{member}** for {duration_min} min — {reason}"
        )
    except discord.Forbidden:
        await ctx.reply("🚫 I don't have permission to mute that member.")


async def cmd_warn(ctx: commands.Context, args: list[str]):
    member, reason = parse_target_and_reason(args, ctx.guild)
    if member is None:
        await ctx.reply("⚠️ Target not found.")
        return
    try:
        await member.send(
            f"⚠️ You have been warned in **{ctx.guild.name}**: {reason}"
        )
        sent = " (DM sent)"
    except discord.Forbidden:
        sent = " (couldn't DM user)"
    await ctx.reply(f"📢 Warned **{member}** — {reason}{sent}")


async def cmd_alert(ctx: commands.Context, args: list[str]):
    """Send an alert to the channel the command was issued in."""
    message = " ".join(args) if args else "No message provided."
    await ctx.send(f"🚨 **ALERT:** {message}")


async def cmd_clearah(ctx: commands.Context, args: list[str]):
    """
    'clearah' = clear a history of messages.
    Usage: clearah <count>   (default 10)
    """
    count = 10
    if args and args[0].isdigit():
        count = int(args[0])
    count = max(1, min(count, 100))  # Discord bulk-delete limit

    try:
        deleted = await ctx.channel.purge(limit=count + 1)  # +1 for the command
        await ctx.send(f"🧹 Cleared {len(deleted) - 1} message(s).", delete_after=5)
    except discord.Forbidden:
        await ctx.reply("🚫 I don't have permission to delete messages.")


COMMANDS = {
    "BAN": cmd_ban,
    "KICK": cmd_kick,
    "MUTE": cmd_mute,
    "WARN": cmd_warn,
    "ALERT": cmd_alert,
    "CLEARAH": cmd_clearah,
}


# ---------------------------------------------------------------------------
# Morse listener
# ---------------------------------------------------------------------------
@bot.event
async def on_message(message: discord.Message):
    if message.author.bot or not message.guild:
        return

    raw = message.content.strip()
    if not raw:
        return

    decoded = morse_to_text(raw)

    # If it doesn't decode into plain text, it isn't Morse — ignore it.
    if decoded is None:
        return

    tokens = decoded.upper().split()
    if not tokens:
        return

    cmd = tokens[1]
    if cmd not in COMMANDS:
        return  # valid Morse, but not one of our commands — ignore

    # Permission check
    if not is_operator(message.author):
        await message.reply("🚫 You are not authorized to run Morse commands.")
        return

    args = decoded.split()[1:]  # keep original case for reasons/usernames
    await COMMANDS[cmd](message, args)


@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} (ID: {bot.user.id})")
    print("Listening for Morse code commands…")


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    bot.run(TOKEN)
