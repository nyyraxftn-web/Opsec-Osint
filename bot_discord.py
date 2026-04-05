import discord
from discord.ext import commands
import requests
import os
import random
import string
from datetime import datetime, timezone

# =====================================================
#                     CONFIG
# =====================================================
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
API_TOKEN     = "8202824165:ZL7jSQTQ"
API_URL       = "https://leakosintapi.com/"
LANG          = "fr"
LIMIT         = 300
ALLOWED_ROLE_ID  = 1469989510514217023
LOG_CHANNEL_ID   = 1490343808385155072

RED              = 0x4B2861
BANNER_URL       = "https://i.postimg.cc/0j0kNGXv/AC2F549E-38F6-4DBA-BA15-42EC5A90CAEC.png"
FOOTER_IMAGE_URL = ""

EMOJI_LOUPE         = "<:Loupe:1490347933672145016>"
EMOJI_PNG           = "<:tasklist:1490348552428322908>"
EMOJI_PUSHPIN       = "<:puchpin:1490351192365338674>"
EMOJI_INTERROGATION = "<:interrogation:1490350639635628084>"
EMOJI_GEAR          = "<:gear:1490350298659819791>"
EMOJI_FLECHE        = "<a:fleche_anime:1490396918336192542>"
# =====================================================

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.reactions = True
intents.emojis = True
bot = commands.Bot(command_prefix="!", intents=intents)

cache_reports = {}
report_files  = {}

def now_utc():
    return datetime.now(timezone.utc)

def random_filename(length=12):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

# =====================================================
#                  GENERATION RAPPORT
# =====================================================
def generate_report(query, query_id):
    payload = {
        "token": API_TOKEN,
        "request": query.split("\n")[0],
        "limit": LIMIT,
        "lang": LANG
    }
    try:
        r = requests.post(API_URL, json=payload, timeout=30)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        print(f"Erreur API: {e}")
        return None, 0, False

    if "Error code" in data:
        return None, 0, False

    cache_reports[str(query_id)] = []
    has_results   = False
    total_entries = 0
    all_lines     = []  # toutes les lignes [+] pour la pagination

    for db_name, db_data in data["List"].items():
        if db_name != "No results found" and db_data.get("Data"):
            has_results = True
            for entry in db_data.get("Data", []):
                for col, val in entry.items():
                    all_lines.append(f"[+] {col}: {val}")
                    total_entries += 1

    # Stocker les lignes plates pour la pagination
    cache_reports[str(query_id)] = all_lines

    if has_results:
        all_results  = "OpSec SEARCHER - RESULTATS\n"
        all_results += "=" * 60 + "\n"
        all_results += f"Recherche : {query}\n"
        all_results += f"Date      : {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n"
        all_results += "=" * 60 + "\n\n"

        for db_name, db_data in data["List"].items():
            all_results += f"\n{'='*60}\n[ {db_name} ]\n{'='*60}\n"
            if db_name != "No results found":
                for entry in db_data.get("Data", []):
                    for col, val in entry.items():
                        all_results += f"[+] {col}: {val}\n"
                    all_results += "-" * 30 + "\n"

        filename = f"OSINT_{random_filename()}.txt"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(all_results)
        report_files[str(query_id)] = filename

    return all_lines, total_entries, has_results

# =====================================================
#                  EMBEDS
# =====================================================
LINES_PER_PAGE = 10
LIGHT_PURPLE   = 0x9B59B6

def build_result_embed(all_lines, query, page, query_id, duration_ms=0):
    total_lines = len(all_lines)
    total_pages = max(1, -(-total_lines // LINES_PER_PAGE))
    start = page * LINES_PER_PAGE
    end   = start + LINES_PER_PAGE
    chunk = all_lines[start:end]

    desc = "\n\n".join(chunk) if chunk else "Aucune donnee."

    e = discord.Embed(
        description=f"```\n{desc}\n```",
        color=LIGHT_PURPLE,
        timestamp=now_utc()
    )
    e.set_thumbnail(url=BANNER_URL)
    e.set_footer(text=f"Resultat {page+1}/{total_pages} · discord.gg/opsecs · {duration_ms}ms")
    return e

def format_no_result_embed(query):
    e = discord.Embed(
        title=f"{EMOJI_LOUPE} AUCUN RESULTAT",
        description=f"Aucun resultat pour : **{query}**",
        color=RED, timestamp=now_utc()
    )
    e.set_thumbnail(url=BANNER_URL)
    e.set_footer(text="OSINT - by Nyyrax")
    return e

# =====================================================
#                  LOG
# =====================================================
async def log_search(user, query, has_results):
    ch = bot.get_channel(LOG_CHANNEL_ID)
    if not ch:
        return
    status = "OK" if has_results else "Aucun resultat"
    e = discord.Embed(title=f"{EMOJI_LOUPE} NOUVELLE RECHERCHE", color=RED, timestamp=now_utc())
    e.set_thumbnail(url=BANNER_URL)
    e.add_field(name="Utilisateur", value=f"{user.mention} ({user.id})", inline=True)
    e.add_field(name="Requete",     value=f"```{query[:100]}```",         inline=True)
    e.add_field(name="Statut",      value=f"```{status}```",              inline=False)
    e.set_footer(text="OSINT Bot")
    await ch.send(embed=e)

# =====================================================
#                  RECHERCHE
# =====================================================
async def perform_search(interaction, query, search_type):
    loading = discord.Embed(
        title=f"{EMOJI_LOUPE} RECHERCHE EN COURS",
        description=f"```\nType    : {search_type}\nRequete : {query[:50]}\n```\nVeuillez patienter...",
        color=RED
    )
    loading.set_thumbnail(url=BANNER_URL)
    loading.set_footer(text="Recherche en cours...")
    msg = await interaction.followup.send(embed=loading, ephemeral=True)

    query_id = str(len(cache_reports) + 1)
    start_time = datetime.now()
    all_lines, total, has_results = generate_report(query, query_id)
    duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)

    if all_lines is None:
        err = discord.Embed(title="ERREUR API", description="Erreur API. Reessayez plus tard.", color=RED)
        await msg.edit(embed=err)
        await log_search(interaction.user, query, False)
        return

    await msg.delete()

    if not has_results:
        await interaction.followup.send(embed=format_no_result_embed(query), ephemeral=True)
    else:
        embed = build_result_embed(all_lines, query, 0, query_id, duration_ms)
        view  = PaginationView(all_lines, query, query_id, duration_ms)
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

    await log_search(interaction.user, query, has_results)

# =====================================================
#                  MODALS
# =====================================================
class PhoneModal(discord.ui.Modal, title="Recherche par telephone"):
    phone = discord.ui.TextInput(label="Telephone", placeholder="Ex: +33612345678", required=True, max_length=20)
    async def on_submit(self, i: discord.Interaction):
        await i.response.defer(ephemeral=True)
        await perform_search(i, self.phone.value, "Telephone")

class EmailModal(discord.ui.Modal, title="Recherche par email"):
    email = discord.ui.TextInput(label="Email", placeholder="exemple@email.com", required=True, max_length=100)
    async def on_submit(self, i: discord.Interaction):
        await i.response.defer(ephemeral=True)
        await perform_search(i, self.email.value, "Email")

class NameModal(discord.ui.Modal, title="Recherche par nom / prenom"):
    nom    = discord.ui.TextInput(label="Nom de naissance",  placeholder="Nom de naissance", required=True,  max_length=50)
    prenom = discord.ui.TextInput(label="Nom d'affichage",   placeholder="Display name",     required=False, max_length=50)
    async def on_submit(self, i: discord.Interaction):
        await i.response.defer(ephemeral=True)
        await perform_search(i, f"{self.nom.value} {self.prenom.value}".strip(), "Nom / Prenom")

class UsernameModal(discord.ui.Modal, title="Recherche par pseudo"):
    username = discord.ui.TextInput(label="Pseudo", placeholder="Username", required=True, max_length=100)
    async def on_submit(self, i: discord.Interaction):
        await i.response.defer(ephemeral=True)
        await perform_search(i, self.username.value, "Pseudo")

class AddressModal(discord.ui.Modal, title="Recherche par localisation"):
    ville = discord.ui.TextInput(label="Ville",        placeholder="Ville", required=False, max_length=100)
    cp    = discord.ui.TextInput(label="Code postal",  placeholder="CP",    required=False, max_length=20)
    pays  = discord.ui.TextInput(label="Pays",         placeholder="Pays",  required=False, max_length=100)
    async def on_submit(self, i: discord.Interaction):
        await i.response.defer(ephemeral=True)
        parts = [v for v in [self.ville.value, self.cp.value, self.pays.value] if v]
        await perform_search(i, " ".join(parts), "Localisation")

class IdentityModal(discord.ui.Modal, title="Recherche identite complete"):
    nom   = discord.ui.TextInput(label="Nom de naissance",     placeholder="Nom de naissance", required=True,  max_length=50)
    dob   = discord.ui.TextInput(label="Date de naissance",    placeholder="JJ/MM/AAAA",       required=False, max_length=20)
    secu  = discord.ui.TextInput(label="N Securite sociale",   placeholder="Numero secu",      required=False, max_length=20)
    async def on_submit(self, i: discord.Interaction):
        await i.response.defer(ephemeral=True)
        parts = [self.nom.value]
        if self.dob.value:  parts.append(f"DOB:{self.dob.value}")
        if self.secu.value: parts.append(f"SS:{self.secu.value}")
        await perform_search(i, " ".join(parts), "Identite")

# =====================================================
#                  MENU DEROULANT
# =====================================================

class GenericModal(discord.ui.Modal):
    def __init__(self, modal_title, field_label, field_placeholder, search_type, max_length=100):
        super().__init__(title=modal_title)
        self.search_type = search_type
        self.field = discord.ui.TextInput(label=field_label, placeholder=field_placeholder, required=True, max_length=max_length)
        self.add_item(self.field)
    async def on_submit(self, i: discord.Interaction):
        await i.response.defer(ephemeral=True)
        await perform_search(i, self.field.value, self.search_type)

class AdvancedModal(discord.ui.Modal, title="Recherche avancée"):
    query = discord.ui.TextInput(label="Recherche avancée", placeholder="Prénom, nom, ville, date, année...", required=True, max_length=200)
    async def on_submit(self, i: discord.Interaction):
        await i.response.defer(ephemeral=True)
        await perform_search(i, self.query.value, "Recherche avancée")

class FullNameModal(discord.ui.Modal, title="Prénom + Nom"):
    prenom = discord.ui.TextInput(label="Prénom", placeholder="Prénom", required=True, max_length=50)
    nom    = discord.ui.TextInput(label="Nom", placeholder="Nom", required=True, max_length=50)
    async def on_submit(self, i: discord.Interaction):
        await i.response.defer(ephemeral=True)
        await perform_search(i, f"{self.prenom.value} {self.nom.value}".strip(), "Prénom + Nom")

class SearchSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="→ Recherche avancée",    description="Prénom, nom, ville, date, année...", value="advanced"),
            discord.SelectOption(label="→ Prénom + Nom",           description="Identité complète",                  value="fullname"),
            discord.SelectOption(label="→ Nom de naissance",       description="Nom de naissance",                   value="birthname"),
            discord.SelectOption(label="→ Date de naissance",      description="JJ/MM/AAAA",                         value="dob"),
            discord.SelectOption(label="→ Nº Sécurité sociale",  description="Numéro sécu",                        value="secu"),
            discord.SelectOption(label="→ Email",                  description="Adresse email",                      value="email"),
            discord.SelectOption(label="→ Téléphone",              description="Numéro",                             value="phone"),
            discord.SelectOption(label="→ Pseudo",                 description="Username",                           value="username"),
            discord.SelectOption(label="→ Nom d'affichage",        description="Display name",                       value="displayname"),
            discord.SelectOption(label="→ Ville",                  description="Ville",                              value="ville"),
            discord.SelectOption(label="→ Bio",                    description="Biographie / fragment",              value="bio"),
            discord.SelectOption(label="→ Mot de passe",           description="Mot de passe ou fragment",           value="password"),
            discord.SelectOption(label="→ Hash",                   description="Hash / mot de passe haché",          value="hash"),
            discord.SelectOption(label="→ IBAN",                   description="IBAN",                               value="iban"),
            discord.SelectOption(label="→ VIN",                    description="Numéro VIN",                         value="vin"),
            discord.SelectOption(label="→ Code postal",            description="CP",                                 value="cp"),
            discord.SelectOption(label="→ Pays",                   description="Pays",                               value="pays"),
            discord.SelectOption(label="→ Adresse",                description="Adresse",                            value="adresse"),
            discord.SelectOption(label="→ IP",                     description="Adresse IPv4",                       value="ip"),
            discord.SelectOption(label="→ UID",                    description="Identifiant UID",                    value="uid"),
        ]
        super().__init__(
            placeholder="Selectionne un type de recherche...",
            min_values=1, max_values=1,
            options=options,
            custom_id="search_select"
        )

    async def callback(self, i: discord.Interaction):
        role = discord.utils.get(i.user.roles, id=ALLOWED_ROLE_ID)
        if role is None:
            await i.response.send_message(
                embed=discord.Embed(
                    title="**OpSec S€archer**",
                    description=(
                        "**OpSec** — Recherche & infos en un clic.\n"
                        "Choisis un outil dans le menu ci-dessous.\n\n"
                        "**Accès** — mets `/opsecs` dans ton **statut personnalisé** et reste "
                        "**en ligne** (pas invisible / hors ligne)."
                    ),
                    color=LIGHT_PURPLE
                ),
                ephemeral=True
            )
            return
        modals = {
            "advanced":    AdvancedModal(),
            "fullname":    FullNameModal(),
            "birthname":   GenericModal("Nom de naissance",      "Nom de naissance",       "Nom de naissance",         "Nom de naissance"),
            "dob":         GenericModal("Date de naissance",     "Date de naissance",      "JJ/MM/AAAA",               "Date de naissance", max_length=20),
            "secu":        GenericModal("Nº Sécurité sociale",   "Nº Sécurité sociale",    "Numéro sécu",              "N° Sécu",           max_length=20),
            "email":       EmailModal(),
            "phone":       PhoneModal(),
            "username":    UsernameModal(),
            "displayname": GenericModal("Nom d'affichage",       "Nom d'affichage",        "Display name",             "Display name"),
            "ville":       GenericModal("Ville",                 "Ville",                  "Ville",                    "Ville"),
            "bio":         GenericModal("Bio",                   "Biographie / fragment",  "Biographie ou fragment",   "Bio",               max_length=200),
            "password":    GenericModal("Mot de passe",          "Mot de passe",           "Mot de passe ou fragment", "Mot de passe",      max_length=100),
            "hash":        GenericModal("Hash",                  "Hash",                   "Hash / mot de passe haché","Hash",              max_length=200),
            "iban":        GenericModal("IBAN",                  "IBAN",                   "IBAN",                     "IBAN",              max_length=50),
            "vin":         GenericModal("VIN",                   "Numéro VIN",             "Numéro VIN",               "VIN",               max_length=20),
            "cp":          GenericModal("Code postal",           "Code postal",            "CP",                       "Code postal",       max_length=10),
            "pays":        GenericModal("Pays",                  "Pays",                   "Pays",                     "Pays"),
            "adresse":     GenericModal("Adresse",               "Adresse",                "Adresse complète",         "Adresse",           max_length=200),
            "ip":          GenericModal("Adresse IP",            "Adresse IPv4",           "Ex: 192.168.1.1",          "IP",                max_length=20),
            "uid":         GenericModal("UID",                   "Identifiant UID",        "UID",                      "UID"),
        }
        await i.response.send_modal(modals[self.values[0]])

class SearchMenuView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(SearchSelect())

# =====================================================
#                  PAGINATION VIEW
# =====================================================
class PaginationView(discord.ui.View):
    def __init__(self, all_lines, query, query_id, duration_ms=0, timeout=300):
        super().__init__(timeout=timeout)
        self.all_lines   = all_lines
        self.query       = query
        self.query_id    = query_id
        self.page        = 0
        self.duration_ms = duration_ms
        self.total_pages = max(1, -(-len(all_lines) // LINES_PER_PAGE))

    def get_embed(self):
        return build_result_embed(self.all_lines, self.query, self.page, self.query_id, self.duration_ms)

    @discord.ui.button(emoji="◀", style=discord.ButtonStyle.secondary, custom_id="page_left")
    async def go_left(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.page > 0:
            self.page -= 1
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.button(emoji="📄", style=discord.ButtonStyle.secondary, custom_id="download_all")
    async def download_all(self, interaction: discord.Interaction, button: discord.ui.Button):
        fn = report_files.get(self.query_id)
        if fn and os.path.exists(fn):
            await interaction.response.send_message(
                content="Fichier complet :",
                file=discord.File(fn, filename=f"OSINT_{self.query_id}.txt"),
                ephemeral=True
            )
        else:
            await interaction.response.send_message("Fichier indisponible.", ephemeral=True)

    @discord.ui.button(emoji="▶", style=discord.ButtonStyle.secondary, custom_id="page_right")
    async def go_right(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.page < self.total_pages - 1:
            self.page += 1
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

# =====================================================
#                  EVENTS & COMMANDES
# =====================================================
@bot.event
async def on_ready():
    print(f"[OK] {bot.user} connecte!")
    await bot.change_presence(
        activity=discord.Activity(type=discord.ActivityType.watching, name="OpSec Searcher"),
        status=discord.Status.online
    )

@bot.event
async def on_command_error(ctx, error):
    if not isinstance(error, commands.CommandNotFound):
        print(f"Erreur: {error}")

@bot.command()
async def menu(ctx):
    role = discord.utils.get(ctx.author.roles, id=ALLOWED_ROLE_ID)
    if role is None:
        e = discord.Embed(
            title="**OpSec S€archer**",
            description=(
                "**OpSec** — Recherche & infos en un clic.\n"
                "Choisis un outil dans le menu ci-dessous.\n\n"
                "**Accès** — mets `/opsecs` dans ton **statut personnalisé** et reste "
                "**en ligne** (pas invisible / hors ligne)."
            ),
            color=LIGHT_PURPLE
        )
        await ctx.send(embed=e, delete_after=15)
        return

    e = discord.Embed(
        description=(
            "```\n"
            "================================\n"
            "        OpSec S\u20acARCHER\n"
            "================================\n"
            "\n"
            " [+] 20 types de recherche\n"
            " [+] Export JSON\n"
            " [+] Multi-criteres\n"
            "```"
        ),
        color=RED,
        timestamp=now_utc()
    )
    e.set_thumbnail(url=BANNER_URL)
    e.set_footer(text="By Nyyrax")
    await ctx.send(embed=e, view=SearchMenuView())

@bot.command()
async def start(ctx):
    await menu(ctx)

@bot.command()
async def aide(ctx):
    e = discord.Embed(
        title=f"{EMOJI_LOUPE} AIDE",
        description="Utilisez `!menu` ou `!start` pour acceder au menu.",
        color=RED
    )
    e.set_thumbnail(url=BANNER_URL)
    await ctx.send(embed=e, delete_after=10)

bot.run(DISCORD_TOKEN)
