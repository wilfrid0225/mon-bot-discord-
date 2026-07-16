import discord
from discord.ext import commands, tasks
import datetime
import json
import os
import threading

# =========================================================
# CONFIGURATION
# =========================================================
# On récupère le token depuis les variables d'environnement de Render
TOKEN_DU_BOT = os.environ.get("DISCORD_TOKEN")
SALON_LOGS_ID = 1527049619396366416  

SALONS_INTERDITS = [
    1511489834458550332, 1511487655169364098, 1511815388789215262,
    1511478304711119118, 1511454369915207912, 1511454200247357701,
    1511557421821067324, 1511555809564430356, 1511454546067587212,
    1511388717817008171, 1520799390833315950, 1511395268333932554,
    1511396264091193505, 1511401176065900737, 1511395896242212926,
    1520775355097681980, 1520764093978513549, 1511450713279041556,
    1526540353325367407, 1526540051662770296
]

ROLES_AUTORISES = [
    "Admirateurs", "Fondateur", "RESPADMINS", 
    "admin", "headadmin", "coowner", "trial admin"
]
# =========================================================

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

def charger_donnees(fichier, par_defaut):
    if os.path.exists(fichier):
        try:
            with open(fichier, "r") as f:
                return json.load(f)
        except: return par_defaut
    return par_defaut

def sauvegarder_donnees(fichier, donnees):
    with open(fichier, "w") as f:
        json.dump(donnees, f, indent=4)

async def envoyer_log(embed):
    try:
        salon_logs = bot.get_channel(SALON_LOGS_ID)
        if salon_logs:
            await salon_logs.send(embed=embed)
    except Exception as e:
        print(f"Erreur log : {e}")

@bot.event
async def on_ready():
    print(f"Bot connecté : {bot.user}")
    if not verifier_debannissements.is_running():
        verifier_debannissements.start()

@tasks.loop(seconds=60)
async def verifier_debannissements():
    bans_temporaires = charger_donnees("bans.json", {})
    if not bans_temporaires: return
    
    maintenant = datetime.datetime.now(datetime.timezone.utc)
    a_retirer = []
    
    for uid, info in list(bans_temporaires.items()):
        try:
            expire_at = datetime.datetime.fromisoformat(info["expire_at"])
            if maintenant >= expire_at:
                guild = bot.get_guild(info["guild_id"])
                if guild:
                    await guild.unban(discord.Object(id=int(uid)), reason="Fin du tempban")
                a_retirer.append(uid)
        except: continue
        
    if a_retirer:
        for uid in a_retirer: del bans_temporaires[uid]
        sauvegarder_donnees("bans.json", bans_temporaires)

@bot.event
async def on_message(message):
    if message.author.bot: return
    canal = message.channel
    id_a_verifier = canal.parent_id if isinstance(canal, discord.Thread) else canal.id

    if id_a_verifier in SALONS_INTERDITS:
        membre = message.author
        est_admin = membre.guild_permissions.administrator
        a_role = any(role.name in ROLES_AUTORISES for role in membre.roles)

        if not (est_admin or a_role):
            try: await message.delete()
            except: pass

            infractions = charger_donnees("infractions.json", {})
            uid = str(membre.id)
            nb = infractions.get(uid, 0) + 1
            
            if nb >= 3:
                infractions[uid] = 0
                sauvegarder_donnees("infractions.json", infractions)
                fin_ban = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=1)
                bans = charger_donnees("bans.json", {})
                bans[uid] = {"guild_id": membre.guild.id, "expire_at": fin_ban.isoformat()}
                sauvegarder_donnees("bans.json", bans)
                await membre.ban(reason="3 infractions")
            else:
                infractions[uid] = nb
                sauvegarder_donnees("infractions.json", infractions)
                await membre.timeout(datetime.timedelta(minutes=10), reason=f"Infraction {nb}/3")

    await bot.process_commands(message)

bot.run(TOKEN_DU_BOT)
