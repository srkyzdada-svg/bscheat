import discord
from discord.ext import commands
from discord.ui import Button, View
import json
import os

# ─── CONFIGURARE ──────────────────────────────────────────────
# Înlocuiește cu ID-ul serverului tău
# Cum să obții ID-ul: Settings → Advanced → Developer Mode (ON)
# Click dreapta pe numele serverului → Copy ID
ALLOWED_GUILD_ID = 123456789012345678  # ⚠️ ÎNLOCUIEȘTE CU ID-UL SERVERULUI TĂU

DATA_FILE = 'data.json'

# ─── Verificare server autorizat ─────────────────────────────
def is_allowed_guild(interaction: discord.Interaction):
    return interaction.guild_id == ALLOWED_GUILD_ID

# ─── JSON storage for invites ──────────────────────────────
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)

# ─── Bot ──────────────────────────────────────────────────────
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix='/', intents=intents)

# ─── Command /send_cheat ────────────────────────────────────
@bot.tree.command(name='send_cheat', description='Sends the Free Cheat embed with claim button')
async def send_cheat(interaction: discord.Interaction):
    # Verificare server autorizat
    if not is_allowed_guild(interaction):
        await interaction.response.send_message('❌ What are you trying to do bro', ephemeral=True)
        return
    
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message('❌ Only admins can use this command.', ephemeral=True)
        return

    embed = discord.Embed(
        title='🎮 **Free Cheat**',
        description='Click the button below to claim your free cheat.',
        color=discord.Color.gold()
    )
    embed.add_field(
        name='📌 Requirement',
        value='**8 invites** on this server.',
        inline=False
    )
    embed.add_field(
        name='⚠️ Limit',
        value='One claim per person.',
        inline=False
    )
    embed.set_footer(text='Free Cheat • 2026')

    view = View()
    button = Button(label='🎁 Claim Free Cheat', style=discord.ButtonStyle.success, custom_id='claim_cheat')
    view.add_item(button)

    await interaction.response.send_message(embed=embed, view=view)

# ─── Button callback ────────────────────────────────────────
@bot.event
async def on_interaction(interaction: discord.Interaction):
    if interaction.type != discord.InteractionType.component:
        return

    if interaction.data.get('custom_id') != 'claim_cheat':
        return

    # Verificare server autorizat
    if not is_allowed_guild(interaction):
        await interaction.response.send_message('❌ Acest bot poate fi folosit doar pe serverul oficial.', ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)

    user_id = str(interaction.user.id)
    data = load_data()

    if user_id not in data:
        data[user_id] = {'invites': 0, 'claimed': False}

    user = data[user_id]

    if user['claimed']:
        await interaction.followup.send('❌ You already claimed! Invite 8 more people to claim again.', ephemeral=True)
        return

    if user['invites'] < 8:
        await interaction.followup.send(f'❌ You need {8 - user["invites"]} more invites. You have {user["invites"]}/8.', ephemeral=True)
        return

    # ─── EDITEAZĂ AICI ──────────────────────────────────────
    # Înlocuiește link-ul și parola cu cele reale
    try:
        await interaction.user.send(
            "🎮 **FREE BRAWL STARS CHEAT** 🎮\n\n"
            "📥 **Download:** https://gofile.io/d/YMjyOavW"
            "🔑 **Password:** INTRODU_PAROLA_AICI"
        )
    except:
        await interaction.followup.send('⚠️ Cannot send DM. Please enable DMs from server members.', ephemeral=True)
        return

    user['claimed'] = True
    user['invites'] = 0
    save_data(data)

    await interaction.followup.send('✅ **Cheat sent to your DMs!** Invites reset to 0.', ephemeral=True)

# ─── Admin command: manually add invites ───────────────────
@bot.tree.command(name='add_invites', description='[Admin] Add invites to a user')
async def add_invites(interaction: discord.Interaction, member: discord.Member, count: int):
    # Verificare server autorizat
    if not is_allowed_guild(interaction):
        await interaction.response.send_message('❌ Acest bot poate fi folosit doar pe serverul oficial.', ephemeral=True)
        return
    
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message('❌ Only admins.', ephemeral=True)
        return

    data = load_data()
    uid = str(member.id)
    if uid not in data:
        data[uid] = {'invites': 0, 'claimed': False}
    data[uid]['invites'] += count
    save_data(data)

    await interaction.response.send_message(f'✅ {member.mention} now has {data[uid]["invites"]} invites.', ephemeral=True)

# ─── Admin command: reset all invites ──────────────────────
@bot.tree.command(name='reset_all', description='[Admin] Reset all invites for all users')
async def reset_all(interaction: discord.Interaction):
    # Verificare server autorizat
    if not is_allowed_guild(interaction):
        await interaction.response.send_message('❌ Acest bot poate fi folosit doar pe serverul oficial.', ephemeral=True)
        return
    
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message('❌ Only admins.', ephemeral=True)
        return

    data = {}
    save_data(data)
    await interaction.response.send_message('✅ All user data has been reset.', ephemeral=True)

# ─── Admin command: reset user invites ─────────────────────
@bot.tree.command(name='reset_user', description='[Admin] Reset invites for a specific user')
async def reset_user(interaction: discord.Interaction, member: discord.Member):
    # Verificare server autorizat
    if not is_allowed_guild(interaction):
        await interaction.response.send_message('❌ Acest bot poate fi folosit doar pe serverul oficial.', ephemeral=True)
        return
    
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message('❌ Only admins.', ephemeral=True)
        return

    data = load_data()
    uid = str(member.id)
    if uid in data:
        data[uid]['invites'] = 0
        data[uid]['claimed'] = False
        save_data(data)
        await interaction.response.send_message(f'✅ {member.mention}\'s invites have been reset to 0.', ephemeral=True)
    else:
        await interaction.response.send_message(f'❌ {member.mention} has no data.', ephemeral=True)

# ─── Admin command: check user invites ─────────────────────
@bot.tree.command(name='check_invites', description='[Admin] Check invites for a user')
async def check_invites(interaction: discord.Interaction, member: discord.Member):
    # Verificare server autorizat
    if not is_allowed_guild(interaction):
        await interaction.response.send_message('❌ Acest bot poate fi folosit doar pe serverul oficial.', ephemeral=True)
        return
    
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message('❌ Only admins.', ephemeral=True)
        return

    data = load_data()
    uid = str(member.id)
    if uid in data:
        user_data = data[uid]
        await interaction.response.send_message(
            f'📊 **{member.name}**\n'
            f'Invites: {user_data["invites"]}/8\n'
            f'Claimed: {user_data["claimed"]}',
            ephemeral=True
        )
    else:
        await interaction.response.send_message(f'❌ {member.mention} has no data.', ephemeral=True)

# ─── Admin command: view all data ──────────────────────────
@bot.tree.command(name='view_data', description='[Admin] View all user data')
async def view_data(interaction: discord.Interaction):
    # Verificare server autorizat
    if not is_allowed_guild(interaction):
        await interaction.response.send_message('What are you trying to do g?', ephemeral=True)
        return
    
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message('❌ Only admins.', ephemeral=True)
        return

    data = load_data()
    if not data:
        await interaction.response.send_message('📊 No data available.', ephemeral=True)
        return

    # Creează un mesaj cu toate datele
    message = "📊 **User Data:**\n```\n"
    for user_id, user_data in data.items():
        # Încearcă să obții numele utilizatorului
        try:
            user = await bot.fetch_user(int(user_id))
            name = user.name
        except:
            name = user_id
        
        message += f"{name}: {user_data['invites']} invites, Claimed: {user_data['claimed']}\n"
    
    message += "```"
    
    # Dacă mesajul e prea lung, trimite-l într-un fișier
    if len(message) > 2000:
        with open('data_export.txt', 'w') as f:
            f.write(message)
        await interaction.response.send_message(
            "📊 Data is too long to display. Here's a file:",
            file=discord.File('data_export.txt'),
            ephemeral=True
        )
        os.remove('data_export.txt')
    else:
        await interaction.response.send_message(message, ephemeral=True)

# ─── Start the bot ──────────────────────────────────────────
@bot.event
async def on_ready():
    print(f'🤖 Logged in as {bot.user}')
    
    # Verifică dacă botul e pe serverul corect
    guild = bot.get_guild(ALLOWED_GUILD_ID)
    if not guild:
        print(f'⚠️ Botul NU este pe serverul cu ID-ul {ALLOWED_GUILD_ID}!')
        print('⚠️ Botul NU va funcționa pe niciun server!')
        print('⚠️ Verifică ID-ul serverului și asigură-te că botul este invitat pe serverul corect.')
    else:
        print(f'✅ Botul este pe serverul: {guild.name} (ID: {guild.id})')
        print(f'✅ Members: {guild.member_count}')
    
    await bot.tree.sync()
    print('✅ Commands synced')

if __name__ == '__main__':
    token = os.getenv('DISCORD_TOKEN')
    if not token:
        raise ValueError('❌ DISCORD_TOKEN is not set!')
    bot.run(token)
