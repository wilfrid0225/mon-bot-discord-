import os
import discord
from discord.ext import commands, tasks
import datetime
import json
from flask import Flask
from threading import Thread

# --- PARTIE WEB (KEEP-ALIVE) ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Le bot est en ligne !"

def run_web():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

Thread(target=run_web, daemon=True).start()

# --- CONFIGURATION ---
TOKEN_DU_BOT = os.environ.get("DISCORD_TOKEN")
SALON_LOGS_ID = 1527049619396366416  

SALONS_INTERDITS = [
    1511489834458550332, 1511487655169364098, 1511815388789215262, 1511478304711119118,
    1511454369915207912, 1511454200247357701, 1511557421821067324, 1511555809564430356,
    1511454546067587212, 1511388717817008171, 1520799390833315950, 1511395268333932554,
    1511396264091193505, 1511401176065900737, 1511395896242212926, 1520775355097681980,
    1520764093978513549, 1511450713279041556, 1526540353325367407, 1526540051662770296
]

# Ajout de toutes les variantes du rôle ADMIN
ROLES_AUTORISES = [
    "ADMIN", "[ ADMIN ]", "[ADMIN]", "admin", "Admirateurs", 
    "Fondateur", "RESPADMINS", "headadmin", "coowner", "trial admin"
]

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

# --- FONCTIONS UTILES ---
def charger_donnees(fichier, par_defaut):
    if os.path.exists(fichier):
        try:
            with open(fichier, "r") as f: 
                return json.load(f)
        except: 
            return par_defaut
    return par_defaut

def sauvegarder_donnees(fichier, donnees):
    with open(fichier, "w") as f: 
        json.dump(donnees, f, indent=4)

async def envoyer_log(embed):
    try:
        salon = bot.get_channel(SALON_LOGS_ID)
        if salon: 
            await salon.send(embed=embed)
    except Exception as e: 
        print(f"Erreur lors de l'envoi du log : {e}")

@bot.event
async def on_ready():
    print(f"Bot connecté avec succès : {bot.user}")

@bot.event
async def on_message(message):
    if message.author.bot: 
        return

    canal = message.channel
    id_a_verifier = canal.parent_id if isinstance(canal, discord.Thread) else canal.id

    if id_a_verifier in SALONS_INTERDITS:
        membre = message.author
        
        # 1. Vérification des permissions natives d'administrateur
        est_admin = membre.guild_permissions.administrator
        
        # 2. Vérification insensible à la casse des rôles autorisés
        roles_autorises_lower = [r.lower() for r in ROLES_AUTORISES]
        a_role = any(role.name.lower() in roles_autorises_lower for role in membre.roles)

        # Si le membre N'EST PAS administrateur ni autorisé
        if not (est_admin or a_role):
            try: 
                await message.delete()
            except: 
                pass

            infractions = charger_donnees("infractions.json", {})
            uid = str(membre.id)
            nb = infractions.get(uid, 0) + 1
            
            embed = discord.Embed(title="⚠️ Alerte Modération", color=discord.Color.red())
            embed.add_field(name="Membre", value=membre.mention, inline=False)
            embed.add_field(name="Infraction", value=f"{nb}/3", inline=False)
            await envoyer_log(embed)

            if nb >= 3:
                infractions[uid] = 0
                sauvegarder_donnees("infractions.json", infractions)
                await membre.timeout(datetime.timedelta(hours=24), reason="3 infractions accumulées")
                await envoyer_log(discord.Embed(description=f"🚫 {membre.name} a été exclu (timeout) pour 24 heures.", color=discord.Color.orange()))
            else:
                infractions[uid] = nb
                sauvegarder_donnees("infractions.json", infractions)
                await membre.timeout(datetime.timedelta(minutes=10), reason=f"Infraction {nb}/3")

    await bot.process_commands(message)

# --- LANCEMENT ---
if __name__ == "__main__":
    if TOKEN_DU_BOT:
        bot.run(TOKEN_DU_BOT)
    else:
        print("Erreur : La variable DISCORD_TOKEN est introuvable.")
