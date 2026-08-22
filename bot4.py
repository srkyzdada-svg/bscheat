import discord
from discord.ext import commands
from discord.ui import Button, View
import json
import os
import DiscordUtils  # <-- Noua librărie

# ─── JSON storage ──────────────────────────────────────────────
DATA_FILE = 'data.json'

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
intents.invites = True  # Necesar pentru tracking

bot = commands.Bot(command_prefix='/', intents=intents)

# ─── Inițializează tracker-ul ───────────────────────────────
tracker = DiscordUtils.InviteTracker(bot)

@bot.event
async def on_ready():
    print(f'🤖 Logged in as {bot.user}')
    await tracker.cache_invites()  # Salvează toate invitațiile la pornire
    await bot.tree.sync()
    print('✅ Commands synced')

# ─── Evenimente necesare pentru tracker ─────────────────────
@bot.event
async def on_invite_create(invite):
    await tracker.update_invite_cache(invite)

@bot.event
async def on_invite_delete(invite):
    await tracker.remove_invite_cache(invite)

@bot.event
async def on_guild_join(guild):
    await tracker.update_guild_cache(guild)

@bot.event
async def on_guild_remove(guild):
    await tracker.remove_guild_cache(guild)

# ─── Tracking automat cu DiscordUtils ──────────────────────
@bot.event
async def on_member_join(member):
    inviter = await tracker.fetch_inviter(member)  # Găsește cine a invitat
    if inviter is not None:
        inviter_id = str(inviter.id)
        data = load_data()
        if inviter_id not in data:
            data[inviter_id] = {'invites': 0, 'claimed': False}
        data[inviter_id]['invites'] += 1
        save_data(data)
        print(f'📈 {inviter.name} now has {data[inviter_id]["invites"]} invites')

# ─── Comanda /send_cheat ──────────────────────────────────────
@bot.tree.command(name='send_cheat', description='Sends the Free Cheat embed with claim button')
async def send_cheat(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message('❌ Only admins can use this command.', ephemeral=True)
        return
    embed = discord.Embed(
        title='🎮 **Free Cheat**',
        description='Click the button below to claim your free cheat.',
        color=discord.Color.gold()
    )
    embed.add_field(name='📌 Requirement', value='**8 invites** on this server.', inline=False)
    embed.add_field(name='⚠️ Limit', value='One claim per person.', inline=False)
    embed.set_footer(text='Free Cheat • 2026')
    view = View()
    button = Button(label='🎁 Claim Free Cheat', style=discord.ButtonStyle.success, custom_id='claim_cheat')
    view.add_item(button)
    await interaction.response.send_message(embed=embed, view=view)

# ─── Callback pentru buton ────────────────────────────────────
@bot.event
async def on_interaction(interaction: discord.Interaction):
    if interaction.type != discord.InteractionType.component:
        return
    if interaction.data.get('custom_id') != 'claim_cheat':
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
    try:
        await interaction.user.send(
            "🎮 **FREE BRAWL STARS CHEAT** 🎮\n\n"
            "📥 **Download:** https://gofile.io/d/gSxhyqyq"
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

@bot.tree.command(name='reset_user', description='[Admin] Reset a user')
async def reset_user(interaction: discord.Interaction, member: discord.Member):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message('❌ Only admins.', ephemeral=True)
        return
    data = load_data()
    uid = str(member.id)
    if uid in data:
        data[uid] = {'invites': 0, 'claimed': False}
        save_data(data)
        await interaction.response.send_message(f'✅ {member.mention} has been reset.', ephemeral=True)
    else:
        await interaction.response.send_message(f'❌ {member.mention} not found.', ephemeral=True)

# ─── Start bot ────────────────────────────────────────────────
if __name__ == '__main__':
    token = os.getenv('DISCORD_TOKEN')
    if not token:
        raise ValueError('❌ DISCORD_TOKEN is not set!')
    bot.run(token)
