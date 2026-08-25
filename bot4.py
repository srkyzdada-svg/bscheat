import discord
from discord.ext import commands
from discord.ui import Button, View
import json
import os
import sys
import threading
import socket

# ─── SERVER HEALTHCHECK (pentru Railway) ────────────────────
def run_healthcheck_server():
    try:
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(('0.0.0.0', 8080))
        server.listen(1)
        print('✅ Healthcheck server running on port 8080')
        while True:
            try:
                client, addr = server.accept()
                client.send(b'HTTP/1.1 200 OK\r\nContent-Length: 2\r\n\r\nOK')
                client.close()
            except:
                pass
    except Exception as e:
        print(f'⚠️ Healthcheck server error: {e}')

healthcheck_thread = threading.Thread(target=run_healthcheck_server, daemon=True)
healthcheck_thread.start()

# ─── CONFIGURARE ──────────────────────────────────────────────
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
ALLOWED_GUILD_ID = 1464389143479058588  # ID-ul serverului tău
REQUIRED_INVITES = 8  # 8 invitații necesare

DATA_FILE = 'data.json'
INVITE_CACHE = {}  # Cache pentru invitații

# ─── Verificare token ──────────────────────────────────────
if not DISCORD_TOKEN:
    print('❌ DISCORD_TOKEN is not set!')
    sys.exit(1)

# ─── JSON storage for invites ──────────────────────────────
def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r') as f:
                content = f.read().strip()
                if not content:
                    return {}
                return json.loads(content)
        except json.JSONDecodeError:
            print('⚠️ data.json is corrupted, creating new one...')
            return {}
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

# ─── Urmărește invitațiile ──────────────────────────────────
@bot.event
async def on_ready():
    print(f'🤖 Logged in as {bot.user}')
    
    # Salvează invitațiile inițiale
    for guild in bot.guilds:
        try:
            invites = await guild.invites()
            for invite in invites:
                INVITE_CACHE[invite.code] = invite.uses
        except:
            pass
    
    print(f'✅ Required invites: {REQUIRED_INVITES}')
    print(f'✅ Server restriction: {"Enabled" if ALLOWED_GUILD_ID != 0 else "Disabled"}')
    
    if ALLOWED_GUILD_ID != 0:
        guild = bot.get_guild(ALLOWED_GUILD_ID)
        if not guild:
            print(f'⚠️ Bot is NOT on the server with ID {ALLOWED_GUILD_ID}!')
        else:
            print(f'✅ Bot is on server: {guild.name} (ID: {guild.id})')
            print(f'✅ Members: {guild.member_count}')
    
    try:
        await bot.tree.sync()
        print('✅ Commands synced')
    except Exception as e:
        print(f'❌ Failed to sync commands: {e}')

# ─── Detectează când cineva intră pe server ────────────────
@bot.event
async def on_member_join(member):
    """Când un membru nou intră, verifică cine l-a invitat"""
    try:
        # Verifică dacă botul e pe serverul corect
        if member.guild.id != ALLOWED_GUILD_ID:
            return
        
        # Obține invitațiile actuale
        invites = await member.guild.invites()
        
        # Găsește invitația care a fost folosită
        for invite in invites:
            old_uses = INVITE_CACHE.get(invite.code, 0)
            if invite.uses > old_uses:
                # Acest invitație a fost folosită
                inviter_id = str(invite.inviter.id)
                
                # Actualizează cache-ul
                INVITE_CACHE[invite.code] = invite.uses
                
                # Încarcă datele
                data = load_data()
                if inviter_id not in data:
                    data[inviter_id] = {'invites': 0, 'claimed': False}
                
                # Adaugă o invitație
                data[inviter_id]['invites'] += 1
                save_data(data)
                
                print(f'✅ {invite.inviter.name} invited {member.name} (Total: {data[inviter_id]["invites"]})')
                break
    except Exception as e:
        print(f'⚠️ Error tracking invite: {e}')

# ─── Command /send_cheat ────────────────────────────────────
@bot.tree.command(name='send_cheat', description='Sends the Free Cheat embed with claim button')
async def send_cheat(interaction: discord.Interaction):
    if interaction.guild_id != ALLOWED_GUILD_ID:
        await interaction.response.send_message('❌ This bot can only be used on the official server.', ephemeral=True)
        return
    
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message('❌ Only administrators can use this command.', ephemeral=True)
        return

    embed = discord.Embed(
        title='🎮 **Free Cheat**',
        description='Click the button below to claim your free cheat.',
        color=discord.Color.gold()
    )
    embed.add_field(
        name='📌 Requirement',
        value=f'**{REQUIRED_INVITES} invites** on this server.',
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

    if interaction.guild_id != ALLOWED_GUILD_ID:
        await interaction.response.send_message('❌ This bot can only be used on the official server.', ephemeral=True)
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

    if user['invites'] < REQUIRED_INVITES:
        await interaction.followup.send(
            f'❌ You need {REQUIRED_INVITES - user["invites"]} more invites. '
            f'You have {user["invites"]}/{REQUIRED_INVITES}.',
            ephemeral=True
        )
        return

    try:
        await interaction.user.send(
            "🎮 **FREE BRAWL STARS CHEAT** 🎮\n\n"
            "📥 **Download:** https://gofile.io/d/gSxhyqyq\n"
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
    if interaction.guild_id != ALLOWED_GUILD_ID:
        await interaction.response.send_message('❌ This bot can only be used on the official server.', ephemeral=True)
        return
    
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message('❌ Only administrators can use this command.', ephemeral=True)
        return

    data = load_data()
    uid = str(member.id)
    if uid not in data:
        data[uid] = {'invites': 0, 'claimed': False}
    data[uid]['invites'] += count
    save_data(data)

    await interaction.response.send_message(
        f'✅ {member.mention} now has {data[uid]["invites"]}/{REQUIRED_INVITES} invites.',
        ephemeral=True
    )

# ─── Admin command: reset all invites ──────────────────────
@bot.tree.command(name='reset_all', description='[Admin] Reset all invites for all users')
async def reset_all(interaction: discord.Interaction):
    if interaction.guild_id != ALLOWED_GUILD_ID:
        await interaction.response.send_message('❌ This bot can only be used on the official server.', ephemeral=True)
        return
    
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message('❌ Only administrators can use this command.', ephemeral=True)
        return

    data = {}
    save_data(data)
    await interaction.response.send_message('✅ All user data has been reset.', ephemeral=True)

# ─── Admin command: reset user invites ─────────────────────
@bot.tree.command(name='reset_user', description='[Admin] Reset invites for a specific user')
async def reset_user(interaction: discord.Interaction, member: discord.Member):
    if interaction.guild_id != ALLOWED_GUILD_ID:
        await interaction.response.send_message('❌ This bot can only be used on the official server.', ephemeral=True)
        return
    
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message('❌ Only administrators can use this command.', ephemeral=True)
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
    if interaction.guild_id != ALLOWED_GUILD_ID:
        await interaction.response.send_message('❌ This bot can only be used on the official server.', ephemeral=True)
        return
    
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message('❌ Only administrators can use this command.', ephemeral=True)
        return

    data = load_data()
    uid = str(member.id)
    if uid in data:
        user_data = data[uid]
        await interaction.response.send_message(
            f'📊 **{member.name}**\n'
            f'Invites: {user_data["invites"]}/{REQUIRED_INVITES}\n'
            f'Claimed: {user_data["claimed"]}',
            ephemeral=True
        )
    else:
        await interaction.response.send_message(f'❌ {member.mention} has no data.', ephemeral=True)

# ─── Admin command: view all data ──────────────────────────
@bot.tree.command(name='view_data', description='[Admin] View all user data')
async def view_data(interaction: discord.Interaction):
    if interaction.guild_id != ALLOWED_GUILD_ID:
        await interaction.response.send_message('❌ This bot can only be used on the official server.', ephemeral=True)
        return
    
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message('❌ Only administrators can use this command.', ephemeral=True)
        return

    data = load_data()
    if not data:
        await interaction.response.send_message('📊 No data available.', ephemeral=True)
        return

    message = f"📊 **User Data:** (Required: {REQUIRED_INVITES} invites)\n```\n"
    for user_id, user_data in data.items():
        try:
            user = await bot.fetch_user(int(user_id))
            name = user.name
        except:
            name = user_id
        message += f"{name}: {user_data['invites']} invites, Claimed: {user_data['claimed']}\n"
    message += "```"
    
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
if __name__ == '__main__':
    try:
        bot.run(DISCORD_TOKEN)
    except discord.errors.PrivilegedIntentsRequired:
        print('❌ Privileged Intents are not enabled!')
        print('📌 Go to: https://discord.com/developers/applications')
        print('📌 Select your app → Bot → Enable Server Members Intent and Message Content Intent')
        sys.exit(1)
    except Exception as e:
        print(f'❌ Error: {e}')
        sys.exit(1)
