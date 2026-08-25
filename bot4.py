import discord
from discord.ext import commands
from discord.ui import Button, View
import json
import os
import sys
import threading
import socket

# ─── SERVER HEALTHCHECK ──────────────────────────────────────
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
REQUIRED_INVITES = 8

DATA_FILE = 'data.json'
INVITE_CACHE = {}  # Cache pentru invitații

# ─── Verificare token ──────────────────────────────────────
if not DISCORD_TOKEN:
    print('❌ DISCORD_TOKEN is not set!')
    sys.exit(1)

# ─── JSON storage ──────────────────────────────────────────
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

# ─── Urmărește invitațiile la pornire ───────────────────────
@bot.event
async def on_ready():
    print(f'🤖 Logged in as {bot.user}')
    
    # Salvează invitațiile inițiale pentru fiecare server
    for guild in bot.guilds:
        try:
            invites = await guild.invites()
            for invite in invites:
                INVITE_CACHE[invite.code] = {
                    'uses': invite.uses,
                    'inviter_id': str(invite.inviter.id)
                }
            print(f'✅ Tracked {len(invites)} invites on {guild.name}')
        except Exception as e:
            print(f'⚠️ Could not fetch invites: {e}')
    
    print(f'✅ Required invites: {REQUIRED_INVITES}')
    
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

# ─── DETECTEAZĂ AUTOMAT CINE INVITĂ ─────────────────────────
@bot.event
async def on_member_join(member):
    """Când un membru nou intră, verifică cine l-a invitat"""
    try:
        # Verifică dacă e serverul corect
        if member.guild.id != ALLOWED_GUILD_ID:
            return
        
        # Așteaptă puțin să se actualizeze invitațiile
        await discord.utils.sleep(1)
        
        # Obține invitațiile actuale
        current_invites = await member.guild.invites()
        
        # Găsește invitația care a fost folosită
        found_inviter = None
        for invite in current_invites:
            old_data = INVITE_CACHE.get(invite.code)
            if old_data:
                old_uses = old_data.get('uses', 0)
                if invite.uses > old_uses:
                    # Această invitație a fost folosită!
                    found_inviter = old_data.get('inviter_id')
                    # Actualizează cache-ul
                    INVITE_CACHE[invite.code]['uses'] = invite.uses
                    break
        
        # Dacă nu am găsit prin cache, încearcă să găsești invitația cu cele mai multe folosiri
        if not found_inviter and current_invites:
            # Găsește invitația care a crescut cel mai mult
            max_diff = 0
            for invite in current_invites:
                old_data = INVITE_CACHE.get(invite.code)
                if old_data:
                    diff = invite.uses - old_data.get('uses', 0)
                    if diff > max_diff:
                        max_diff = diff
                        found_inviter = old_data.get('inviter_id')
                        INVITE_CACHE[invite.code]['uses'] = invite.uses
        
        # Dacă am găsit cine a invitat
        if found_inviter:
            # Încarcă datele
            data = load_data()
            if found_inviter not in data:
                data[found_inviter] = {'invites': 0, 'claimed': False}
            
            # Adaugă o invitație
            data[found_inviter]['invites'] += 1
            save_data(data)
            
            # Log
            try:
                inviter = await bot.fetch_user(int(found_inviter))
                print(f'✅ {inviter.name} invited {member.name} (Total: {data[found_inviter]["invites"]})')
            except:
                print(f'✅ User {found_inviter} invited {member.name}')
        else:
            print(f'⚠️ Could not determine who invited {member.name}')
            
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
        )
    except:
        await interaction.followup.send('⚠️ Cannot send DM. Please enable DMs from server members.', ephemeral=True)
        return

    user['claimed'] = True
    user['invites'] = 0
    save_data(data)

    await interaction.followup.send('✅ **Cheat sent to your DMs!** Invites reset to 0.', ephemeral=True)

# ─── Admin commands ──────────────────────────────────────────

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

@bot.tree.command(name='set_required', description='[Admin] Change the required invites amount')
async def set_required(interaction: discord.Interaction, amount: int):
    if interaction.guild_id != ALLOWED_GUILD_ID:
        await interaction.response.send_message('❌ This bot can only be used on the official server.', ephemeral=True)
        return
    
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message('❌ Only administrators can use this command.', ephemeral=True)
        return

    global REQUIRED_INVITES
    REQUIRED_INVITES = amount
    await interaction.response.send_message(f'✅ Required invites set to **{amount}**!', ephemeral=True)

# ─── Start ──────────────────────────────────────────────────
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
