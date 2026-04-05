import discord
from discord.ext import commands
import requests
import asyncio
import os
import random
import string
from datetime import datetime

# ===== CONFIG =====
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
API_TOKEN = "8202824165:ZL7jSQTQ"

API_URL = "https://leakosintapi.com/"
LANG = "fr"
LIMIT = 300
ALLOWED_ROLE_ID = 1469989510514217023
LOG_CHANNEL_ID = 1490343808385155072

# Couleurs et design
RED = 0x4B2861
DARK_RED = 0x795F8A
BLACK = 0x000000
DARK_GRAY = 0x2C2F33
BANNER_URL = "https://i.postimg.cc/0j0kNGXv/AC2F549E-38F6-4DBA-BA15-42EC5A90CAEC.png"
FOOTER_IMAGE_URL = "https://i.postimg.cc/xjLM3ZFR/0180126546a03a790de6176e7af430d2-Copie.webp"

# Émojis personnalisés du serveur
EMOJI_LOUPE = "<:Loupe:1490347933672145016>"
EMOJI_PNG = "<:tasklist:1490348552428322908>"  # Pour 📋
EMOJI_ECLAIR = "<:eclair:1490351385588273323>"
EMOJI_DROITE = "<:droite:1490349416811593872>"
EMOJI_GAUCHE = "<:gauche:1490349479210254448>"
EMOJI_BAS = "<:download:1490348971703668828>"  # Nouvel émoji pour la flèche de téléchargement
EMOJI_GEAR = "<:gear:1490350298659819791>"
EMOJI_PUSHPIN = "<:puchpin:1490351192365338674>"  # Pour 📥
EMOJI_INTERROGATION = "<:interrogation:1490350639635628084>"
EMOJI_TELEPHONE = "<:phonte:1490349928315097259>"
EMOJI_MAIL = "<:mail:1490350123820253185>"
EMOJI_USER = "<:mec:1490350919550763109>"
# ==================

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.reactions = True
intents.emojis = True
bot = commands.Bot(command_prefix="!", intents=intents)

cache_reports = {}
report_files = {}
user_sessions = {}

def generate_random_filename(length=12):
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))

def format_preview_embed(results, query, total_count, has_results):
    """Crée un embed d'aperçu des résultats"""
    
    if not has_results:
        embed = discord.Embed(
            title=f"{EMOJI_LOUPE} **AUCUN RÉSULTAT**",
            description=f"Aucun résultat trouvé pour : **{query}**",
            color=RED,
            timestamp=datetime.utcnow()
        )
        embed.set_thumbnail(url=BANNER_URL)
        embed.set_image(url=FOOTER_IMAGE_URL)
        embed.set_footer(text="OSINT • by Nyyrax", icon_url=FOOTER_IMAGE_URL)
        return embed
    
    # Extraire seulement les données (sans les descriptions)
    lines = results.split('\n')
    preview_lines = []
    
    for line in lines:
        if line.startswith('[ Alien TxtBase ]') or line.startswith('════════════════════════════════════════'):
            continue
        if line.startswith('Au début de 2025') or 'contenait 23 milliards' in line:
            continue
        if line.strip() and not line.startswith('['):
            preview_lines.append(line)
        if len(preview_lines) >= 15:  # Limiter l'aperçu
            preview_lines.append("\n[...]")
            break
    
    preview = '\n'.join(preview_lines)
    
    embed = discord.Embed(
        title=f"{EMOJI_LOUPE} **RÉSULTATS TROUVÉS**",
        description=f"Des résultats à votre recherche ont été trouvés, voici un avant-goût :",
        color=RED,
        timestamp=datetime.utcnow()
    )
    
    embed.set_thumbnail(url=BANNER_URL)
    embed.set_image(url=FOOTER_IMAGE_URL)
    
    embed.add_field(
        name=f"{EMOJI_PNG} **APERÇU DES DONNÉES**",
        value=f"```\n{preview[:950]}{'...' if len(preview) > 950 else ''}\n```",
        inline=False
    )
    
    embed.add_field(
        name=f"{EMOJI_PUSHPIN} **TÉLÉCHARGEMENT**",
        value=f"Pour voir la suite des résultats, cliquez sur **\"Télécharger les résultats\"** ci-dessous.",
        inline=False
    )
    
    embed.set_footer(text=f"Total: {total_count} entrées • OSINT • by Nyyrax", icon_url=FOOTER_IMAGE_URL)
    
    return embed

def generate_report(query, query_id):
    data = {"token": API_TOKEN, "request": query.split("\n")[0], "limit": LIMIT, "lang": LANG}
    
    try:
        response = requests.post(API_URL, json=data, timeout=30)
        response.raise_for_status()
        response = response.json()
    except requests.exceptions.RequestException as e:
        print(f"Erreur API: {e}")
        return None, 0, False
    
    if "Error code" in response:
        return None, 0, False

    cache_reports[str(query_id)] = []
    
    # Vérifier si des résultats existent
    has_results = False
    total_entries = 0
    
    for db_name in response["List"].keys():
        if db_name != "No results found" and response["List"][db_name].get("Data"):
            has_results = True
        
        text_lines = [f"\n[ {db_name} ]", "═" * 40]
        text_lines.append(response["List"][db_name]["InfoLeak"] + "\n")
        
        if db_name == "No results found":
            text_lines = ["[ No results found ]", "════════════════════════════════════════", " aucun résultat n'a été trouvé a votre recherche"]
        else:
            data_count = 0
            for report_data in response["List"][db_name]["Data"]:
                entry_lines = []
                for col_name, value in report_data.items():
                    entry_lines.append(f"• {col_name}: {value}")
                    data_count += 1
                text_lines.extend(entry_lines)
                text_lines.append("─" * 30)
                total_entries += len(entry_lines)
        
        page_text = "\n".join(text_lines)
        
        if len(page_text) > 1900:
            page_text = page_text[:1900] + "\n\n[!] TRONQUÉ - Trop de données..."
        
        cache_reports[str(query_id)].append(page_text)
    
    # Créer le fichier texte ASCII art seulement s'il y a des résultats
    if has_results:
        ascii_art = """
________          _________                         ________         .__        __   
\_____  \ ______ /   _____/ ____   ____             \_____  \   _____|__| _____/  |_ 
 /   |   \\____ \\_____  \_/ __ \_/ ___\    ______   /   |   \ /  ___/  |/    \   __\
/    |    \  |_> >        \  ___/\  \___   /_____/  /    |    \\___ \|  |   |  \  |  
\_______  /   __/_______  /\___  >\___  >           \_______  /____  >__|___|  /__|  
        \/|__|          \/     \/     \/                    \/     \/        \/      
        """
        
        all_results = ascii_art + "\n\n"
        all_results += f"RECHERCHE OSINT - {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n"
        all_results += "=" * 60 + "\n\n"
        all_results += f"Requête : {query}\n"
        all_results += "=" * 60 + "\n\n"
        
        for db_name in response["List"].keys():
            all_results += f"\n{'='*60}\n"
            all_results += f"[ {db_name} ]\n"
            all_results += f"{'='*60}\n"
            all_results += response["List"][db_name]["InfoLeak"] + "\n\n"
            
            if db_name != "No results found":
                for report_data in response["List"][db_name]["Data"]:
                    for col_name, value in report_data.items():
                        all_results += f"• {col_name}: {value}\n"
                    all_results += "-" * 30 + "\n"
        
        filename = f"OSINT_{generate_random_filename()}.txt"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(all_results)
        
        report_files[str(query_id)] = filename
    
    return cache_reports[str(query_id)], total_entries, has_results

async def log_search(user, query, result_status="Succès", has_results=True):
    log_channel = bot.get_channel(LOG_CHANNEL_ID)
    if log_channel is None:
        print(f"Salon de logs {LOG_CHANNEL_ID} introuvable")
        return

    status_text = "✅ Succès" if has_results else "❌ Aucun résultat"
    
    embed = discord.Embed(
        title=f"{EMOJI_LOUPE} **NOUVELLE RECHERCHE**",
        color=RED,
        timestamp=datetime.utcnow()
    )
    embed.set_thumbnail(url=BANNER_URL)
    embed.add_field(name=f"{EMOJI_PNG} **Utilisateur**", value=f"{user.mention}\n`{user.id}`", inline=True)
    embed.add_field(name=f"{EMOJI_LOUPE} **Requête**", value=f"```{query[:100]}{'...' if len(query) > 100 else ''}```", inline=True)
    embed.add_field(name=f"{EMOJI_GEAR} **Statut**", value=f"```{status_text}```", inline=False)
    embed.set_footer(text="OSINT Bot • Surveillance", icon_url=FOOTER_IMAGE_URL)

    await log_channel.send(embed=embed)

# ===== MODALS (POP-UPS) =====
class PhoneModal(discord.ui.Modal, title="📱 Recherche par téléphone"):
    phone = discord.ui.TextInput(
        label="Numéro de téléphone",
        placeholder="Ex: +33612345678 ou 0612345678",
        required=True,
        max_length=20
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        await perform_search(interaction, self.phone.value, "téléphone")

class EmailModal(discord.ui.Modal, title="📧 Recherche par email"):
    email = discord.ui.TextInput(
        label="Adresse email",
        placeholder="Ex: utilisateur@email.com",
        required=True,
        max_length=100
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        await perform_search(interaction, self.email.value, "email")

class NameModal(discord.ui.Modal, title="👤 Recherche par nom/prénom"):
    name = discord.ui.TextInput(
        label="Nom et prénom",
        placeholder="Ex: Jean Dupont",
        required=True,
        max_length=100
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        await perform_search(interaction, self.name.value, "nom/prénom")

async def perform_search(interaction, query, search_type):
    """Fonction commune pour effectuer la recherche"""
    
    # Message de chargement
    loading_embed = discord.Embed(
        title=f"{EMOJI_LOUPE} **RECHERCHE EN COURS**",
        description=f"```\nType: {search_type}\nRequête: {query[:50]}{'...' if len(query) > 50 else ''}\n```\n⏳ Veuillez patienter...",
        color=RED
    )
    loading_embed.set_thumbnail(url=BANNER_URL)
    loading_embed.set_footer(text="Recherche OSINT en cours...", icon_url=FOOTER_IMAGE_URL)
    
    loading_msg = await interaction.followup.send(embed=loading_embed, ephemeral=True)
    
    # Générer l'ID de requête
    query_id = str(len(cache_reports) + 1)
    
    # Effectuer la recherche
    report_pages, total_entries, has_results = generate_report(query, query_id)
    
    if report_pages is None:
        error_embed = discord.Embed(
            title=f"{EMOJI_LOUPE} **ERREUR API**",
            description="L'API a renvoyé une erreur. Veuillez réessayer plus tard.",
            color=RED
        )
        await loading_msg.edit(embed=error_embed)
        await log_search(interaction.user, query, "Échec - Erreur API", False)
        return
    
    await loading_msg.delete()
    
    # Afficher l'aperçu
    preview_embed = format_preview_embed(report_pages[0] if report_pages else "", query, total_entries, has_results)
    
    if has_results:
        view = DownloadView(query_id)
        await interaction.followup.send(embed=preview_embed, view=view, ephemeral=True)
        
        # Envoyer le fichier complet en MP seulement s'il y a des résultats
        try:
            filename = report_files.get(query_id)
            if filename and os.path.exists(filename):
                # Créer un embed pour le MP
                mp_embed = discord.Embed(
                    title=f"{EMOJI_LOUPE} **RÉSULTATS COMPLETS**",
                    description=f"Voici les résultats complets pour votre recherche : **{query}**",
                    color=RED
                )
                mp_embed.set_thumbnail(url=BANNER_URL)
                mp_embed.set_image(url=FOOTER_IMAGE_URL)
                mp_embed.set_footer(text="OSINT • by Nyyrax", icon_url=FOOTER_IMAGE_URL)
                
                await interaction.user.send(embed=mp_embed)
                await interaction.user.send(file=discord.File(filename, filename=f"OSINT_Results_{query_id}.txt"))
        except Exception as e:
            print(f"Erreur envoi MP: {e}")
    else:
        # Pas de résultats, envoyer seulement l'embed d'aperçu
        await interaction.followup.send(embed=preview_embed, ephemeral=True)
    
    # Log de la recherche
    await log_search(interaction.user, query, "Succès" if has_results else "Aucun résultat", has_results)

# ===== BOUTONS =====
class ModuleButtons(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label="Téléphone", style=discord.ButtonStyle.danger, emoji=EMOJI_TELEPHONE, custom_id="phone_btn")
    async def phone_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        role = discord.utils.get(interaction.user.roles, id=ALLOWED_ROLE_ID)
        if role is None:
            await interaction.response.send_message(
                embed=discord.Embed(
                    title=f"{EMOJI_INTERROGATION} **ACCÈS REFUSÉ**",
                    description="Vous n'avez pas la permission d'utiliser cette commande.",
                    color=RED
                ),
                ephemeral=True
            )
            return
        await interaction.response.send_modal(PhoneModal())
    
    @discord.ui.button(label="Email", style=discord.ButtonStyle.danger, emoji=EMOJI_MAIL, custom_id="email_btn")
    async def email_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        role = discord.utils.get(interaction.user.roles, id=ALLOWED_ROLE_ID)
        if role is None:
            await interaction.response.send_message(
                embed=discord.Embed(
                    title=f"{EMOJI_INTERROGATION} **ACCÈS REFUSÉ**",
                    description="Vous n'avez pas la permission d'utiliser cette commande.",
                    color=RED
                ),
                ephemeral=True
            )
            return
        await interaction.response.send_modal(EmailModal())
    
    @discord.ui.button(label="Nom/Prénom", style=discord.ButtonStyle.danger, emoji=EMOJI_USER, custom_id="name_btn")
    async def name_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        role = discord.utils.get(interaction.user.roles, id=ALLOWED_ROLE_ID)
        if role is None:
            await interaction.response.send_message(
                embed=discord.Embed(
                    title=f"{EMOJI_INTERROGATION} **ACCÈS REFUSÉ**",
                    description="Vous n'avez pas la permission d'utiliser cette commande.",
                    color=RED
                ),
                ephemeral=True
            )
            return
        await interaction.response.send_modal(NameModal())

class DownloadView(discord.ui.View):
    def __init__(self, query_id, timeout=180):
        super().__init__(timeout=timeout)
        self.query_id = query_id
        self.message = None
    
    async def on_timeout(self):
        if self.message:
            try:
                for item in self.children:
                    item.disabled = True
                await self.message.edit(view=self)
            except:
                pass
    
    @discord.ui.button(label="TÉLÉCHARGER LES RÉSULTATS", style=discord.ButtonStyle.danger, emoji=EMOJI_BAS, custom_id="download_button")
    async def download_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        filename = report_files.get(self.query_id)
        if filename and os.path.exists(filename):
            await interaction.response.send_message(
                content=f"{EMOJI_BAS} **Fichier prêt !**",
                file=discord.File(filename, filename=f"OSINT_Results_{self.query_id}.txt"),
                ephemeral=True
            )
        else:
            embed = discord.Embed(
                title=f"{EMOJI_LOUPE} **ERREUR**",
                description="Le fichier n'est plus disponible. Veuillez relancer la recherche.",
                color=RED
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.event
async def on_ready():
    print(f'[✓] {bot.user} est maintenant connecté à Discord!')
    print(f'[✓] Design Rouge et Noir activé')
    print(f'[✓] Émojis personnalisés chargés avec succès')
    print(f'[✓] Salon des logs: {LOG_CHANNEL_ID}')
    
    # Changement de l'activité
    activity = discord.Activity(
        type=discord.ActivityType.watching,
        name="OpSec Searcher"
    )
    await bot.change_presence(activity=activity, status=discord.Status.online)

@bot.command()
async def menu(ctx):
    """Affiche le menu avec les boutons"""
    
    # Vérification des permissions
    role = discord.utils.get(ctx.author.roles, id=ALLOWED_ROLE_ID)
    if role is None:
        embed = discord.Embed(
            title=f"{EMOJI_INTERROGATION} **ACCÈS REFUSÉ**",
            description="Vous n'avez pas la permission d'utiliser cette commande.",
            color=RED
        )
        embed.set_thumbnail(url=BANNER_URL)
        embed.set_footer(text="Accès restreint", icon_url=FOOTER_IMAGE_URL)
        await ctx.send(embed=embed, delete_after=10)
        return
    
    # Créer l'embed principal
    embed = discord.Embed(
        title=f"{EMOJI_LOUPE} **Searcher OpSec**",
        description="Cliquez sur un bouton pour choisir le type de recherche :",
        color=RED,
        timestamp=datetime.utcnow()
    )
    
    embed.set_thumbnail(url=BANNER_URL)
    embed.set_image(url=FOOTER_IMAGE_URL)
    
    embed.add_field(
        name=f"{EMOJI_TELEPHONE} **Téléphone**",
        value="Recherche par numéro de téléphone",
        inline=False
    )
    
    embed.add_field(
        name=f"{EMOJI_MAIL} **Email**",
        value="Recherche par adresse email",
        inline=False
    )
    
    embed.add_field(
        name=f"{EMOJI_USER} **Nom/Prénom**",
        value="Recherche par nom et prénom",
        inline=False
    )
    
    embed.set_footer(text="By Nyyrax", icon_url=FOOTER_IMAGE_URL)
    
    # Envoyer le menu avec les boutons
    view = ModuleButtons()
    await ctx.send(embed=embed, view=view)

@bot.command()
async def start(ctx):
    """Alias pour menu"""
    await menu(ctx)

@bot.command()
async def aide(ctx):
    """Affiche l'aide"""
    embed = discord.Embed(
        title=f"{EMOJI_LOUPE} **AIDE**",
        description=f"Utilisez `!menu` ou `!start` pour accéder au menu de recherche.",
        color=RED
    )
    embed.set_thumbnail(url=BANNER_URL)
    embed.set_image(url=FOOTER_IMAGE_URL)
    await ctx.send(embed=embed, delete_after=10)

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        pass
    else:
        print(f"Erreur: {error}")

bot.run(DISCORD_TOKEN)