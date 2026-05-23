#!/usr/bin/env python3
"""
██╗███╗   ██╗████████╗███████╗██████╗ ██████╗  ██████╗ ██╗     
██║████╗  ██║╚══██╔══╝██╔════╝██╔══██╗██╔══██╗██╔═══██╗██║     
██║██╔██╗ ██║   ██║   █████╗  ██████╔╝██████╔╝██║   ██║██║     
██║██║╚██╗██║   ██║   ██╔══╝  ██╔══██╗██╔═══╝ ██║   ██║██║     
██║██║ ╚████║   ██║   ███████╗██║  ██║██║     ╚██████╔╝███████╗
╚═╝╚═╝  ╚═══╝   ╚═╝   ╚══════╝╚═╝  ╚═╝╚═╝      ╚═════╝ ╚══════╝
         CENTRAL HQ ADVANCED MULTI-PLATFORM CYBER DETECTOR v6.0
"""

import os, sys, json, socket, re, time, hashlib, random, sqlite3
import argparse, ssl, webbrowser, urllib.request, urllib.error, urllib.parse
import ipaddress, base64, struct, zlib
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# ──────────────────────────────────────────────────────────
#  INITIALISATION BDD & CONFIG
# ──────────────────────────────────────────────────────────
DB_FILE    = "interpol_cases.db"
CONFIG_FILE = "config.json"

def init_system():
    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "w") as f:
            json.dump({"API_KEYS": {"SHODAN": "", "VIRUSTOTAL": "", "ABUSEIPDB": "", "HUNTER": ""}}, f, indent=4)
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS investigations
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, target TEXT, module TEXT, result TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS notes
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, content TEXT, tag TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS watchlist
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, target TEXT, type TEXT, added TEXT)''')
    # Migration : ajoute la colonne result si elle n'existe pas (ancienne BDD v5)
    try:
        c.execute("ALTER TABLE investigations ADD COLUMN result TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        pass  # colonne déjà présente
    conn.commit()
    conn.close()

def log_inv(target, module, result=""):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO investigations (date, target, module, result) VALUES (?, ?, ?, ?)",
              (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), str(target), str(module), str(result)[:500]))
    conn.commit()
    conn.close()

def load_config():
    try:
        with open(CONFIG_FILE) as f: return json.load(f)
    except: return {"API_KEYS": {}}

def save_config(cfg):
    with open(CONFIG_FILE, "w") as f: json.dump(cfg, f, indent=4)

# ──────────────────────────────────────────────────────────
#  CONFIG GRAPHIQUE
# ──────────────────────────────────────────────────────────
class C:
    RED    = "\033[38;5;196m"
    GREEN  = "\033[38;5;46m"
    YELLOW = "\033[38;5;226m"
    BLUE   = "\033[38;5;33m"
    CYAN   = "\033[38;5;51m"
    WHITE  = "\033[38;5;231m"
    ORANGE = "\033[38;5;208m"
    PURPLE = "\033[38;5;135m"
    PINK   = "\033[38;5;213m"
    DIM    = "\033[38;5;244m"
    BOLD   = "\033[1m"
    RESET  = "\033[0m"
    MAGENTA= "\033[38;5;201m"

def clr(): os.system("cls" if os.name == "nt" else "clear")
B_TL, B_TR, B_BL, B_BR, B_H, B_V, B_ML, B_MR = "╔","╗","╚","╝","═","║","╠","╣"
WIDTH = 84

def draw_sep(): print(f"{C.DIM}{B_H * WIDTH}{C.RESET}")
def field(label, value, color=C.WHITE):
    val = str(value).replace(chr(10), ' ')
    print(f"  {C.BLUE}{label:<28}{C.DIM}│{C.RESET} {color}{val}{C.RESET}")
def ok(msg):   print(f"  {C.GREEN}[✔] SUCCESS{C.RESET}  : {msg}")
def err(msg):  print(f"  {C.RED}[✘] ERROR{C.RESET}    : {msg}")
def info(msg): print(f"  {C.CYAN}[ℹ] INFO{C.RESET}     : {C.DIM}{msg}{C.RESET}")
def warn(msg): print(f"  {C.YELLOW}[⚠] WARNING{C.RESET}  : {C.BOLD}{msg}{C.RESET}")
def hit(msg):  print(f"  {C.ORANGE}[🎯] HIT{C.RESET}     : {C.BOLD}{msg}{C.RESET}")
def sec(msg):  print(f"  {C.RED}[🔒] VULN{C.RESET}    : {C.RED}{C.BOLD}{msg}{C.RESET}")

def progress_bar(current, total, width=40):
    pct = current / total
    filled = int(width * pct)
    bar = f"{C.GREEN}{'█' * filled}{C.DIM}{'░' * (width - filled)}{C.RESET}"
    print(f"\r  [{bar}] {C.YELLOW}{current}/{total}{C.RESET}", end="", flush=True)

def pause():
    print(f"\n{C.DIM}{B_H * WIDTH}{C.RESET}")
    input(f"  {C.BOLD}{C.BLUE}↩{C.RESET} {C.DIM}Appuyez sur [Entrée] pour revenir au hub...{C.RESET}")

BANNER = f"""{C.BLUE}{C.BOLD}
  ██╗███╗   ██╗████████╗███████╗██████╗ ██████╗  ██████╗ ██╗     
  ██║████╗  ██║╚══██╔══╝██╔════╝██╔══██╗██╔══██╗██╔═══██╗██║     
  ██║██╔██╗ ██║   ██║   █████╗  ██████╔╝██████╔╝██║   ██║██║     
  ██║██║╚██╗██║   ██║   ██╔══╝  ██╔══██╗██╔═══╝ ██║   ██║██║     
  ██║██║ ╚████║   ██║   ███████╗██║  ██║██║     ╚██████╔╝███████╗
  ╚═╝╚═╝  ╚═══╝   ╚═╝   ╚══════╝╚═╝  ╚═╝╚═╝      ╚═════╝ ╚══════╝
              {C.CYAN}— ULTIMATE CONTROL INFRASTRUCTURE v6.0 — 40 MODULES —{C.RESET}"""

def panel_header(title, subtitle=""):
    clr(); print(BANNER)
    pad = (WIDTH - len(title) - 4) // 2
    accent = f"{C.BLUE}{B_H * pad}{C.RESET}"
    extra = f"{C.BLUE}{B_H if (WIDTH - len(title) - 4) % 2 != 0 else ''}{C.RESET}"
    print(f"{accent}{C.BOLD}{C.WHITE}[ {title} ]{C.RESET}{accent}{extra}")
    if subtitle: print(f"  {C.DIM}{subtitle}{C.RESET}")
    print()

# ──────────────────────────────────────────────────────────
#  MOTEUR RÉSEAU
# ──────────────────────────────────────────────────────────
UAS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Edg/124.0.0.0 Safari/537.36",
]

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

def req_intel(url, headers=None, method="GET", timeout=8, json_parse=True, data=None):
    req = urllib.request.Request(url, method=method)
    req.add_header("User-Agent", random.choice(UAS))
    req.add_header("Accept-Language", "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7")
    if headers:
        for k, v in headers.items(): req.add_header(k, v)
    if data:
        req.data = data.encode() if isinstance(data, str) else data
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            raw = r.read().decode(errors="ignore")
            if json_parse:
                try: return json.loads(raw), r.status
                except: return {"_raw": raw}, r.status
            return raw, r.status
    except urllib.error.HTTPError as e:
        return {"_err": str(e), "_code": e.code}, e.code
    except Exception as e:
        return {"_err": str(e)}, 0

def resolve(target):
    """Résout un domaine ou IP, retourne (ip, is_domain)."""
    try:
        ipaddress.ip_address(target)
        return target, False
    except:
        try: return socket.gethostbyname(target), True
        except: return None, True

# ══════════════════════════════════════════════════════════
#  MODULES ORIGINAUX (améliorés)
# ══════════════════════════════════════════════════════════

def m01_username():
    panel_header("M01 — RECHERCHE PSEUDONYME", "Détection de présence sur 20+ plateformes")
    u = input(f"  {C.YELLOW}Identifiant cible >{C.RESET} ").strip().lstrip("@")
    if not u: return
    log_inv(u, "Username Search")
    platforms = {
        "GitHub":      f"https://github.com/{u}",
        "Twitter/X":   f"https://nitter.net/{u}",
        "Instagram":   f"https://imginn.com/{u}/",
        "Reddit":      f"https://www.reddit.com/user/{u}",
        "TikTok":      f"https://www.tiktok.com/@{u}",
        "Twitch":      f"https://www.twitch.tv/{u}",
        "YouTube":     f"https://www.youtube.com/@{u}",
        "Pinterest":   f"https://www.pinterest.com/{u}/",
        "Keybase":     f"https://keybase.io/{u}",
        "HackerNews":  f"https://news.ycombinator.com/user?id={u}",
        "GitLab":      f"https://gitlab.com/{u}",
        "Steam":       f"https://steamcommunity.com/id/{u}",
        "Pastebin":    f"https://pastebin.com/u/{u}",
        "Medium":      f"https://medium.com/@{u}",
        "Mastodon":    f"https://mastodon.social/@{u}",
        "Dev.to":      f"https://dev.to/{u}",
        "Gravatar":    f"https://en.gravatar.com/{u}",
    }
    found, not_found = [], []
    print(f"  {C.DIM}Scan en cours sur {len(platforms)} plateformes...{C.RESET}\n")
    
    def check(name, url):
        try:
            req = urllib.request.Request(url, method="GET")
            req.add_header("User-Agent", random.choice(UAS))
            with urllib.request.urlopen(req, timeout=4, context=ctx) as r:
                if r.status == 200: return (name, url, True)
        except: pass
        return (name, url, False)
    
    with ThreadPoolExecutor(max_workers=8) as ex:
        futures = {ex.submit(check, n, u): n for n, u in platforms.items()}
        done = 0
        for f in as_completed(futures):
            done += 1
            progress_bar(done, len(platforms))
            name, url, ok_ = f.result()
            if ok_: found.append((name, url))
            else: not_found.append(name)
    
    print(f"\n\n  {C.BOLD}{'━' * 50}{C.RESET}")
    print(f"  {C.GREEN}[✔] Trouvé ({len(found)}){C.RESET}")
    for name, url in sorted(found):
        print(f"      {C.CYAN}●{C.RESET} {name:<16} ➜ {C.CYAN}{url}{C.RESET}")
    print(f"  {C.DIM}[✘] Absent ({len(not_found)}) : {', '.join(not_found)}{C.RESET}")
    log_inv(u, "Username Search", f"Trouvé sur: {', '.join(n for n,_ in found)}")
    pause()

def m02_geo(t=None):
    if not t: panel_header("M02 — GÉOLOCALISATEUR TARGET IP", "Données réseau, FAI, VPN, ASN")
    target = t or input(f"  {C.YELLOW}Entrer IP ou Domaine >{C.RESET} ").strip()
    ip, is_domain = resolve(target)
    if not ip: err("Résolution DNS impossible."); pause() if not t else None; return
    log_inv(target, "GeoIP")
    
    if is_domain: field("Domaine → IP", ip, C.CYAN)
    
    # ip-api (gratuit, riche)
    d, c = req_intel(f"http://ip-api.com/json/{ip}?fields=status,country,countryCode,region,regionName,city,zip,lat,lon,timezone,isp,org,as,asname,proxy,hosting,mobile")
    if c == 200 and d.get("status") == "success":
        field("IP Analysée", ip, C.GREEN)
        field("Localisation", f"{d.get('city')}, {d.get('regionName')}, {d.get('country')} ({d.get('countryCode')})")
        field("Code Postal", d.get("zip", "N/A"))
        field("Coordonnées GPS", f"{d.get('lat')}, {d.get('lon')}", C.CYAN)
        field("Fuseau Horaire", d.get("timezone"))
        field("FAI", d.get("isp"))
        field("Organisation", d.get("org"))
        field("ASN", f"{d.get('as')} ({d.get('asname')})", C.PURPLE)
        
        flags = []
        if d.get("proxy"): flags.append("PROXY/VPN")
        if d.get("hosting"): flags.append("HÉBERGEUR/DATACENTER")
        if d.get("mobile"): flags.append("RÉSEAU MOBILE")
        color = C.RED if flags else C.GREEN
        field("Risque Réseau", " | ".join(flags) if flags else "Résidentiel — Faible risque", color)
        
        # Lien Maps
        lat, lon = d.get('lat'), d.get('lon')
        field("Google Maps", f"https://maps.google.com/?q={lat},{lon}", C.CYAN)
    else:
        err(f"Réponse invalide pour {ip}")
    if not t: pause()

def m03_leaks():
    panel_header("M03 — DATABREACHES MONDIAUX", "Dernières fuites connues via HIBP public API")
    log_inv("Global", "Data Breaches")
    d, c = req_intel("https://haveibeenpwned.com/api/v3/breaches",
                     headers={"hibp-api-key": load_config().get("API_KEYS", {}).get("HIBP", "")})
    if isinstance(d, list):
        print(f"  {C.BOLD}{'Nom':<30} {'Date':<12} {'Victimes':>15} {'Types de données'}{C.RESET}")
        draw_sep()
        for b in sorted(d, key=lambda x: x.get('BreachDate', ''), reverse=True)[:15]:
            name  = b.get('Name', 'Inconnu')[:28]
            date  = b.get('BreachDate', 'N/A')
            count = f"{b.get('PwnCount', 0):,}"
            types = ", ".join(b.get('DataClasses', [])[:3])
            color = C.RED if b.get('PwnCount', 0) > 1_000_000 else C.YELLOW
            print(f"  {color}{name:<30}{C.RESET} {C.DIM}{date:<12}{C.RESET} {C.CYAN}{count:>15}{C.RESET}  {C.DIM}{types}{C.RESET}")
    else: err("API indisponible (clé HIBP requise pour usage intensif).")
    pause()

def m03b_email_pwned():
    panel_header("M03B — EMAIL DANS LES FUITES", "Vérification via HaveIBeenPwned")
    email = input(f"  {C.YELLOW}Email cible >{C.RESET} ").strip()
    if not email: return
    cfg = load_config()
    key = cfg.get("API_KEYS", {}).get("HIBP", "")
    headers = {"hibp-api-key": key} if key else {}
    d, c = req_intel(f"https://haveibeenpwned.com/api/v3/breachedaccount/{urllib.parse.quote(email)}?truncateResponse=false",
                     headers=headers, timeout=10)
    log_inv(email, "HIBP Email Check")
    if c == 200 and isinstance(d, list):
        warn(f"{email} compromis dans {len(d)} breach(es) !")
        for b in d:
            print(f"  {C.RED}💀 {b.get('Name')}{C.RESET} ({b.get('BreachDate')}) — {', '.join(b.get('DataClasses', [])[:4])}")
    elif c == 404: ok(f"{email} non trouvé dans les fuites connues.")
    elif c == 401: err("Clé API HIBP requise. Ajoutez-la dans config.json → HIBP")
    else: err(f"Erreur HTTP {c}")
    pause()

def m04_metadata():
    panel_header("M04 — ANALYSE MÉTADONNÉES FICHIER", "Hash, entropie, magic bytes, structure")
    path = input(f"  {C.YELLOW}Chemin du fichier >{C.RESET} ").strip().strip('"')
    if not os.path.exists(path): err("Fichier introuvable."); pause(); return
    
    with open(path, "rb") as f: b = f.read()
    log_inv(path, "Metadata")
    
    field("Nom", os.path.basename(path))
    field("Taille", f"{len(b):,} octets ({len(b)/1024:.2f} Ko)")
    field("MD5", hashlib.md5(b).hexdigest(), C.YELLOW)
    field("SHA-1", hashlib.sha1(b).hexdigest(), C.ORANGE)
    field("SHA-256", hashlib.sha256(b).hexdigest(), C.CYAN)
    field("SHA-512", hashlib.sha512(b).hexdigest()[:64] + "…", C.DIM)
    
    # Magic bytes
    magic_map = {
        b'\x89PNG': "PNG Image", b'\xff\xd8\xff': "JPEG Image",
        b'PK\x03\x04': "ZIP / Office (docx, xlsx…)", b'%PDF': "PDF Document",
        b'\x7fELF': "ELF Executable", b'MZ': "PE/Windows Executable",
        b'GIF8': "GIF Image", b'\x1f\x8b': "GZIP Archive",
        b'BZh': "BZIP2 Archive", b'\xfd7zXZ\x00': "XZ Archive",
    }
    detected = "Inconnu / Texte"
    for sig, name in magic_map.items():
        if b.startswith(sig): detected = name; break
    field("Type Magic", detected, C.GREEN)
    
    # Entropie de Shannon
    if len(b) > 0:
        freq = [b.count(i) / len(b) for i in range(256) if b.count(i) > 0]
        entropy = -sum(p * (p.bit_length() - 1) for p in freq if p > 0)
        # Approximation simple
        from math import log2
        entropy = -sum(p * log2(p) for p in freq)
        e_color = C.RED if entropy > 7.5 else (C.YELLOW if entropy > 6 else C.GREEN)
        field("Entropie Shannon", f"{entropy:.4f} bits/octet", e_color)
        if entropy > 7.5: warn("Entropie élevée → fichier chiffré, compressé ou packé ?")
    
    # Strings ASCII
    strings = re.findall(rb'[ -~]{6,}', b)[:5]
    if strings:
        print(f"\n  {C.BOLD}{C.BLUE}Strings ASCII (5 premiers){C.RESET}")
        for s in strings: print(f"    {C.DIM}│{C.RESET} {C.WHITE}{s.decode(errors='replace')[:80]}{C.RESET}")
    pause()

def m05_github():
    panel_header("M05 — PROFILAGE GITHUB AVANCÉ", "Dépôts, langages, activité, emails exposés")
    u = input(f"  {C.YELLOW}GitHub ID >{C.RESET} ").strip()
    log_inv(u, "GitHub API")
    
    d, c = req_intel(f"https://api.github.com/users/{u}")
    if c != 200: err("Utilisateur introuvable."); pause(); return
    
    field("Nom / Entreprise", f"{d.get('name', 'N/A')} / {d.get('company', 'N/A')}")
    field("Email public", d.get("email") or "Masqué", C.YELLOW if d.get("email") else C.DIM)
    field("Bio", (d.get("bio") or "N/A")[:60])
    field("Localisation", d.get("location", "N/A"))
    field("Blog / Site", d.get("blog") or "N/A", C.CYAN)
    field("Followers / Following", f"{d.get('followers')} / {d.get('following')}", C.GREEN)
    field("Repos Publics", d.get("public_repos"), C.PURPLE)
    field("Gists Publics", d.get("public_gists"))
    field("Membre depuis", d.get("created_at", "N/A")[:10])
    field("Dernière activité", d.get("updated_at", "N/A")[:10])
    field("Profile URL", d.get("html_url"), C.CYAN)
    
    # Repos récents
    repos, rc = req_intel(f"https://api.github.com/users/{u}/repos?sort=updated&per_page=5")
    if rc == 200 and isinstance(repos, list):
        print(f"\n  {C.BOLD}{C.BLUE}5 Derniers Dépôts{C.RESET}")
        for r in repos:
            stars = r.get('stargazers_count', 0)
            lang  = r.get('language') or 'N/A'
            print(f"    {C.CYAN}●{C.RESET} {r['name']:<35} {C.YELLOW}★{stars:<6}{C.RESET} {C.DIM}{lang}{C.RESET}")
    
    # Tentative d'email via commits
    events, ec = req_intel(f"https://api.github.com/users/{u}/events/public?per_page=30")
    emails_found = set()
    if ec == 200 and isinstance(events, list):
        for ev in events:
            payload = ev.get("payload", {})
            for commit in payload.get("commits", []):
                email = commit.get("author", {}).get("email", "")
                if email and "noreply" not in email: emails_found.add(email)
    if emails_found:
        warn(f"Email(s) exposé(s) via commits publics :")
        for em in emails_found: print(f"    {C.RED}●{C.RESET} {em}")
    pause()

def m06_dns():
    panel_header("M06 — DNS COMPLET & SOUS-DOMAINES", "A, AAAA, MX, TXT, NS, CNAME, SOA, CAA")
    dom = input(f"  {C.YELLOW}Domaine cible >{C.RESET} ").strip()
    log_inv(dom, "DNS Scan")
    
    types = {1: "A", 28: "AAAA", 15: "MX", 16: "TXT", 2: "NS", 5: "CNAME", 6: "SOA", 257: "CAA"}
    print(f"  {C.BOLD}{'Type':<8} {'Données'}{C.RESET}")
    draw_sep()
    for rt, rname in types.items():
        d, c = req_intel(f"https://cloudflare-dns.com/dns-query?name={dom}&type={rt}",
                         headers={"accept": "application/dns-json"})
        if c == 200 and "Answer" in d:
            for a in d["Answer"]:
                color = C.GREEN if rname in ("A","AAAA") else (C.YELLOW if rname in ("MX","NS") else C.CYAN)
                print(f"  {color}{rname:<8}{C.RESET} {a.get('data', '')[:72]}")
    
    # Sous-domaines communs
    print(f"\n  {C.BOLD}{C.BLUE}Sous-domaines courants détectés{C.RESET}")
    common_subs = ["www","mail","smtp","pop","imap","ftp","cpanel","webmail","admin","api",
                   "dev","staging","test","vpn","remote","git","ns1","ns2","cdn","shop"]
    found_subs = []
    for sub in common_subs:
        fqdn = f"{sub}.{dom}"
        try:
            ip = socket.gethostbyname(fqdn)
            found_subs.append((fqdn, ip))
        except: pass
    if found_subs:
        for fqdn, ip in found_subs:
            print(f"    {C.GREEN}●{C.RESET} {fqdn:<35} {C.CYAN}→ {ip}{C.RESET}")
    else: info("Aucun sous-domaine standard résolu.")
    pause()

def m07_email():
    panel_header("M07 — EMPREINTE EMAIL MULTI-SOURCE", "Gravatar, format, permutations")
    email = input(f"  {C.YELLOW}Adresse mail >{C.RESET} ").strip()
    log_inv(email, "Email Recon")
    
    # Validation
    if not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email):
        warn("Format email invalide.")
    
    parts = email.split("@")
    local, domain = parts[0], parts[1] if len(parts) == 2 else ("", "")
    field("Local Part", local, C.CYAN)
    field("Domaine", domain, C.YELLOW)
    
    # Gravatar
    md5 = hashlib.md5(email.lower().encode()).hexdigest()
    field("Hash MD5 (Gravatar)", md5, C.DIM)
    d, c = req_intel(f"https://en.gravatar.com/{md5}.json")
    if c == 200 and "entry" in d:
        entry = d["entry"][0]
        field("Pseudo Gravatar", entry.get("displayName"), C.GREEN)
        field("Profils liés", ", ".join([p.get("url","") for p in entry.get("accounts",[])[:3]]), C.CYAN)
    else: info("Aucun profil Gravatar trouvé.")
    
    field("Avatar Gravatar", f"https://www.gravatar.com/avatar/{md5}?s=200", C.CYAN)
    
    # Permutations email
    name_parts = re.split(r'[\._\-\+]', local)
    perms = set()
    if len(name_parts) >= 2:
        a, b = name_parts[0], name_parts[1]
        for sep in [".", "_", "-", ""]:
            perms.add(f"{a}{sep}{b}@{domain}")
            perms.add(f"{b}{sep}{a}@{domain}")
            perms.add(f"{a[0]}{sep}{b}@{domain}")
            perms.add(f"{a}{sep}{b[0]}@{domain}")
    if perms:
        print(f"\n  {C.BOLD}{C.BLUE}Permutations possibles ({len(perms)}){C.RESET}")
        for p in list(perms)[:8]: print(f"    {C.DIM}●{C.RESET} {p}")
    pause()

def m08_phone():
    panel_header("M08 — PIVOT TÉLÉPHONIQUE AVANCÉ", "Format E.164, indicatif pays, liens OSINT")
    p_raw = input(f"  {C.YELLOW}Numéro (ex: +33612345678) >{C.RESET} ").strip()
    p = re.sub(r"\D", "", p_raw)
    log_inv(p, "Phone Pivot")
    
    field("Numéro nettoyé", p, C.CYAN)
    
    # Indicatifs pays courants
    cc_map = {"1":"États-Unis/Canada","33":"France","44":"Royaume-Uni","49":"Allemagne",
              "34":"Espagne","39":"Italie","7":"Russie","86":"Chine","81":"Japon",
              "55":"Brésil","91":"Inde","52":"Mexique","31":"Pays-Bas","32":"Belgique",
              "41":"Suisse","351":"Portugal","380":"Ukraine","48":"Pologne"}
    for code_len in [3, 2, 1]:
        prefix = p[:code_len] if not p.startswith("0") else p[2:2+code_len]
        if p.startswith("00"): prefix = p[2:2+code_len]
        if prefix in cc_map:
            field("Pays (indicatif)", f"+{prefix} → {cc_map[prefix]}", C.GREEN)
            break
    
    # Liens OSINT
    print(f"\n  {C.BOLD}{C.BLUE}Liens de recherche rapide{C.RESET}")
    links = {
        "WhatsApp (wa.me)":   f"https://wa.me/{p}",
        "Truecaller Web":     f"https://www.truecaller.com/search/fr/{p}",
        "Google Search":      f"https://www.google.com/search?q=%22{p}%22+OR+%22{p_raw}%22",
    }
    for name, url in links.items():
        print(f"    {C.CYAN}●{C.RESET} {name:<22} ➜ {C.CYAN}{url}{C.RESET}")
    pause()

def m09_insta():
    panel_header("M09 — INSTAGRAM ANONYMOUS", "Visualisation via miroirs publics")
    t = input(f"  {C.YELLOW}Alias IG >{C.RESET} ").strip().lstrip("@")
    log_inv(t, "Instagram OSINT")
    mirrors = {
        "Imginn":    f"https://imginn.com/{t}/",
        "StorySaver": f"https://storysaver.net/stories/{t}",
        "Insta Stories": f"https://insta-stories-viewer.com/@{t}",
    }
    for name, url in mirrors.items():
        field(name, url, C.CYAN)
    d, c = req_intel(f"https://imginn.com/{t}/", json_parse=False, timeout=6)
    if c == 200:
        followers = re.search(r'([\d,.]+)\s*[Ff]ollowers', d)
        posts = re.search(r'([\d,.]+)\s*[Pp]osts', d)
        if followers: field("Followers (approx)", followers.group(1), C.GREEN)
        if posts: field("Posts (approx)", posts.group(1), C.CYAN)
    pause()

def m10_dorks():
    panel_header("M10 — GOOGLE DORKS AVANCÉS", "15 catégories de dorks pré-configurés")
    t = input(f"  {C.YELLOW}Domaine ou terme cible >{C.RESET} ").strip()
    log_inv(t, "Google Dorks")
    
    dorks = {
        "1":  ("Fichiers exposés (.env, .log, .sql)",  f"site:{t} ext:env OR ext:log OR ext:sql OR ext:bak"),
        "2":  ("Index of /",                            f"site:{t} intitle:\"index of /\""),
        "3":  ("Panneaux d'admin",                      f"site:{t} inurl:admin OR inurl:login OR inurl:dashboard"),
        "4":  ("Cameras IP / Webcams",                  f"site:{t} inurl:view/index.shtml OR inurl:/mjpg/video.mjpg"),
        "5":  ("Erreurs PHP exposées",                  f"site:{t} \"PHP Parse error\" OR \"PHP Warning\" OR \"PHP Fatal\""),
        "6":  ("Config files (config.php, etc.)",       f"site:{t} inurl:config ext:php OR ext:ini OR ext:yml"),
        "7":  ("WordPress vulnérables",                 f"site:{t} inurl:wp-content OR inurl:wp-admin"),
        "8":  ("Fichiers Excel/CSV sensibles",          f"site:{t} ext:xls OR ext:xlsx OR ext:csv"),
        "9":  ("Emails exposés",                        f"site:{t} \"@{t.split('.')[-2] if '.' in t else t}\" intext:@"),
        "10": ("Documents PDF/DOC internes",            f"site:{t} ext:pdf OR ext:doc OR ext:docx"),
        "11": ("Gitignore / .git exposé",               f"site:{t} inurl:.git OR intitle:\"Index of /.git\""),
        "12": ("JWT Tokens dans URLs",                  f"site:{t} inurl:token OR inurl:jwt OR inurl:bearer"),
        "13": ("API Keys exposées",                     f"site:{t} intext:api_key OR intext:apikey OR intext:secret_key"),
        "14": ("Recherche Shodan",                      f"https://www.shodan.io/search?query=hostname:{t}"),
        "15": ("Certificats SSL (crt.sh)",              f"https://crt.sh/?q=%.{t}"),
    }
    
    for k, (desc, query) in dorks.items():
        print(f"  {C.CYAN}[{k:>2}]{C.RESET} {desc}")
    
    c = input(f"\n  {C.YELLOW}Choix (numéro) ou 'all' >{C.RESET} ").strip()
    targets = dorks.keys() if c == "all" else [c]
    for key in targets:
        if key in dorks:
            desc, query = dorks[key]
            url = query if query.startswith("http") else f"https://www.google.com/search?q={urllib.parse.quote(query)}"
            print(f"  {C.DIM}Ouverture : {desc}{C.RESET}")
            webbrowser.open_new_tab(url)
            time.sleep(0.5)
    pause()

def m11_report():
    panel_header("M11 — GÉNÉRER RAPPORT MULTI-FORMAT", "HTML + JSON + TXT")
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT * FROM investigations ORDER BY id DESC LIMIT 100")
    rows = c.fetchall()
    conn.close()
    
    ts = int(time.time())
    
    # HTML
    html_name = f"Rapport_1NTERPOL_{ts}.html"
    with open(html_name, "w", encoding="utf-8") as f:
        f.write(f"""<!DOCTYPE html>
<html lang="fr"><head><meta charset="utf-8">
<title>Rapport OSINT — 1NTERPOL</title>
<style>
  body {{background:#0a0f1a;color:#e2e8f0;font-family:'Courier New',monospace;margin:40px;}}
  h1 {{color:#38bdf8;border-bottom:2px solid #1e3a5f;padding-bottom:10px;}}
  h2 {{color:#94a3b8;margin-top:30px;}}
  table {{width:100%;border-collapse:collapse;margin-top:20px;}}
  th {{background:#1e3a5f;color:#38bdf8;padding:10px;text-align:left;}}
  td {{padding:8px 10px;border-bottom:1px solid #1e293b;}}
  tr:nth-child(even) {{background:#0d1b2a;}}
  .tag {{background:#1e3a5f;padding:2px 8px;border-radius:4px;font-size:0.85em;color:#7dd3fc;}}
  .footer {{color:#475569;margin-top:40px;font-size:0.85em;}}
</style></head><body>
<h1>🛰️ Rapport OSINT — 1NTERPOL v6.0</h1>
<p>Généré le : {datetime.now().strftime('%d/%m/%Y à %H:%M:%S')}</p>
<p>Total d'investigations : <strong>{len(rows)}</strong></p>
<h2>Journal des investigations</h2>
<table>
<tr><th>#</th><th>Date / Heure</th><th>Cible</th><th>Module</th><th>Résultat</th></tr>
""")
        for r in rows:
            f.write(f"<tr><td>{r[0]}</td><td>{r[1]}</td><td><strong>{r[2]}</strong></td>"
                    f"<td><span class='tag'>{r[3]}</span></td><td>{r[4] if len(r)>4 else ''}</td></tr>\n")
        f.write(f"</table><div class='footer'>1NTERPOL v6.0 — Usage légal uniquement</div></body></html>")
    ok(f"HTML exporté : {html_name}")
    
    # JSON
    json_name = f"Rapport_1NTERPOL_{ts}.json"
    with open(json_name, "w", encoding="utf-8") as f:
        json.dump({"generated": datetime.now().isoformat(), "total": len(rows),
                   "investigations": [{"id":r[0],"date":r[1],"target":r[2],"module":r[3],"result":r[4] if len(r)>4 else ""} for r in rows]}, f, indent=2, ensure_ascii=False)
    ok(f"JSON exporté : {json_name}")
    
    webbrowser.open_new_tab(html_name)
    pause()

def m12_ports(t=None):
    if not t: panel_header("M12 — SCANNER DE PORTS ÉTENDU", "150 ports courants, banner grabbing, service ID")
    host = t or input(f"  {C.YELLOW}IP/Domaine >{C.RESET} ").strip()
    log_inv(host, "Port Scan")
    
    # Ports étendus avec services
    port_map = {
        20:"FTP-DATA", 21:"FTP", 22:"SSH", 23:"Telnet", 25:"SMTP", 53:"DNS",
        80:"HTTP", 110:"POP3", 111:"RPC", 135:"MSRPC", 139:"NetBIOS", 143:"IMAP",
        389:"LDAP", 443:"HTTPS", 445:"SMB", 465:"SMTPS", 587:"SMTP-Auth",
        631:"IPP", 993:"IMAPS", 995:"POP3S", 1194:"OpenVPN", 1433:"MSSQL",
        1521:"Oracle", 2049:"NFS", 2181:"Zookeeper", 3000:"NodeJS/Dev",
        3306:"MySQL", 3389:"RDP", 4444:"Metasploit", 5000:"Flask/Docker",
        5432:"PostgreSQL", 5900:"VNC", 6379:"Redis", 6443:"K8s API",
        7001:"WebLogic", 8000:"HTTP-Alt", 8080:"HTTP-Proxy", 8443:"HTTPS-Alt",
        8888:"Jupyter", 9000:"Portainer/PHP-FPM", 9200:"Elasticsearch",
        9300:"Elasticsearch-Cluster", 11211:"Memcached", 27017:"MongoDB",
        27018:"MongoDB-Shard", 50000:"SAP", 50070:"Hadoop NameNode",
    }
    
    all_ports = list(port_map.keys())
    open_ports = []
    
    print(f"  {C.DIM}Scan de {len(all_ports)} ports sur {host}...{C.RESET}\n")
    
    def scan_port(p):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.6)
        result = s.connect_ex((host, p))
        banner = ""
        if result == 0:
            try:
                s.send(b"HEAD / HTTP/1.0\r\n\r\n")
                banner = s.recv(256).decode(errors="ignore").split("\r\n")[0][:50]
            except: pass
        s.close()
        return p, result == 0, banner
    
    done = 0
    with ThreadPoolExecutor(max_workers=30) as ex:
        futures = {ex.submit(scan_port, p): p for p in all_ports}
        for f in as_completed(futures):
            done += 1
            progress_bar(done, len(all_ports))
            p, is_open, banner = f.result()
            if is_open: open_ports.append((p, banner))
    
    print(f"\n\n  {C.BOLD}{'━' * 50}{C.RESET}")
    if open_ports:
        print(f"  {C.BOLD}{'Port':<8} {'Service':<20} {'Banner'}{C.RESET}")
        draw_sep()
        for p, banner in sorted(open_ports):
            svc = port_map.get(p, "Inconnu")
            alert = C.RED if p in [23,135,139,445,1433,3389,5900,6379,9200,11211,27017] else C.GREEN
            print(f"  {alert}{p:<8}{C.RESET} {C.CYAN}{svc:<20}{C.RESET} {C.DIM}{banner}{C.RESET}")
        
        # Alertes de sécurité
        risky = [p for p, _ in open_ports if p in [23,3389,5900,6379,9200,11211,27017]]
        if risky:
            print()
            sec(f"Ports critiques exposés : {', '.join(str(p) for p in risky)}")
    else:
        info("Aucun port ouvert détecté.")
    log_inv(host, "Port Scan", str([p for p,_ in open_ports]))
    if not t: pause()

def m13_mac():
    panel_header("M13 — MAC ADDRESS LOOKUP", "Fabricant OUI, format validation")
    mac = input(f"  {C.YELLOW}Adresse MAC >{C.RESET} ").strip()
    log_inv(mac, "MAC Lookup")
    
    # Validation et nettoyage
    clean_hex = re.sub(r"[^a-fA-F0-9]", "", mac)
    if len(clean_hex) < 6: err("MAC invalide (< 6 hex chars)."); pause(); return
    
    oui = clean_hex[:6].upper()
    field("OUI (3 octets)", f"{oui[:2]}:{oui[2:4]}:{oui[4:6]}", C.CYAN)
    
    # Bits spéciaux
    first_byte = int(oui[:2], 16)
    field("Multicast", "OUI" if first_byte & 0x01 else "NON")
    field("Localement admin.", "OUI (MAC randomisée ?)" if first_byte & 0x02 else "NON",
          C.YELLOW if first_byte & 0x02 else C.GREEN)
    
    d, c = req_intel(f"https://api.macvendors.com/{oui}", json_parse=False)
    if c == 200 and d: field("Constructeur", d.strip(), C.GREEN)
    else: info("OUI inconnu dans la base macvendors.")
    pause()

def m14_discord():
    panel_header("M14 — DISCORD SNOWFLAKE DECODER", "ID → timestamp + worker + process")
    dis_id = input(f"  {C.YELLOW}ID Discord >{C.RESET} ").strip()
    log_inv(dis_id, "Discord ID")
    if not dis_id.isdigit(): err("ID invalide."); pause(); return
    
    n = int(dis_id)
    discord_epoch = 1420070400000
    ts_ms = (n >> 22) + discord_epoch
    worker = (n & 0x3E0000) >> 17
    process = (n & 0x1F000) >> 12
    increment = n & 0xFFF
    dt = datetime.fromtimestamp(ts_ms / 1000)
    
    field("Timestamp Unix (ms)", ts_ms, C.CYAN)
    field("Date de Création", dt.strftime('%d/%m/%Y %H:%M:%S.') + str(ts_ms % 1000).zfill(3), C.GREEN)
    field("Worker ID interne", worker, C.DIM)
    field("Process ID interne", process, C.DIM)
    field("Incrément", increment, C.DIM)
    field("Âge du compte", f"{(datetime.now() - dt).days} jours", C.YELLOW)
    pause()

def m15_revdns():
    panel_header("M15 — REVERSE DNS & PTR", "Résolution inverse, multi-IP")
    ip = input(f"  {C.YELLOW}IP cible >{C.RESET} ").strip()
    log_inv(ip, "Reverse DNS")
    try:
        name, aliases, addrs = socket.gethostbyaddr(ip)
        field("Hôte PTR", name, C.GREEN)
        if aliases: field("Alias", ", ".join(aliases))
        if addrs:   field("Addrs associées", ", ".join(addrs), C.CYAN)
    except socket.herror: info("Aucun enregistrement PTR.")
    except Exception as e: err(str(e))
    
    # via DNS cloudflare aussi
    rev = ".".join(reversed(ip.split("."))) + ".in-addr.arpa"
    d, c = req_intel(f"https://cloudflare-dns.com/dns-query?name={rev}&type=PTR",
                     headers={"accept": "application/dns-json"})
    if c == 200 and "Answer" in d:
        for a in d["Answer"]: field("PTR (CF-DNS)", a.get("data", ""), C.CYAN)
    pause()

def m16_trackers():
    panel_header("M16 — ANALYSE TRACKERS & TECHNOLOGIES WEB", "Analytics, frameworks, CDN, cookies")
    url = input(f"  {C.YELLOW}URL (https://...) >{C.RESET} ").strip()
    log_inv(url, "Web Trackers")
    
    raw, c = req_intel(url, json_parse=False, timeout=10)
    if c != 200: err(f"HTTP {c}"); pause(); return
    
    checks = {
        "Google Analytics (GA4)": r"G-[A-Z0-9]{8,}",
        "Google Analytics (UA)":  r"UA-\d{4,}-\d+",
        "Google Tag Manager":     r"GTM-[A-Z0-9]{4,}",
        "Facebook Pixel":         r"fbq\(|facebook\.net/en_US/fbevents",
        "HotJar":                 r"hotjar\.com|hjid:\s*\d+",
        "Mixpanel":               r"mixpanel\.com",
        "Segment":                r"analytics\.js|segment\.io",
        "Hubspot":                r"hubspot\.com|_hsq",
        "Intercom":               r"intercom\.io|Intercom\(",
        "Crisp Chat":             r"crisp\.chat",
        "Cloudflare":             r"cloudflare\.com|cf-ray",
        "jQuery":                 r"jquery[.\-](\d[\d.]+)\.js",
        "React":                  r"react\.development|react\.production|__react",
        "Vue.js":                 r"vue\.js|__vue_",
        "Angular":                r"ng-version|angular\.min",
        "Bootstrap":              r"bootstrap\.min\.css|bootstrap@",
        "WordPress":              r"wp-content|wp-includes",
        "Drupal":                 r"drupal\.js|Drupal\.settings",
        "Shopify":                r"cdn\.shopify\.com|Shopify\.",
        "Stripe":                 r"js\.stripe\.com",
    }
    
    print(f"  {C.BOLD}{'Technologie':<28} {'Détecté'}{C.RESET}")
    draw_sep()
    detected_count = 0
    for name, pattern in checks.items():
        match = re.search(pattern, raw, re.IGNORECASE)
        if match:
            detected_count += 1
            snippet = match.group(0)[:40]
            print(f"  {C.GREEN}[✔]{C.RESET} {name:<28} {C.DIM}{snippet}{C.RESET}")
    
    if detected_count == 0: info("Aucun tracker/framework standard détecté.")
    else: print(f"\n  {C.CYAN}Total détecté : {detected_count}{C.RESET}")
    
    # Cookies
    cookies = re.findall(r'document\.cookie\s*=\s*["\']([^"\']+)', raw)
    if cookies:
        print(f"\n  {C.BOLD}{C.YELLOW}Cookies JS détectés :{C.RESET}")
        for ck in cookies[:5]: print(f"    {C.DIM}●{C.RESET} {ck[:80]}")
    pause()

def m17_hash():
    panel_header("M17 — HASH & ENCODAGE", "MD5, SHA-1/256/512, Base64, ROT13, CRC32")
    t = input(f"  {C.YELLOW}Texte >{C.RESET} ").strip()
    b = t.encode()
    log_inv("Hash Gen", "Crypto")
    field("MD5",     hashlib.md5(b).hexdigest(), C.YELLOW)
    field("SHA-1",   hashlib.sha1(b).hexdigest(), C.ORANGE)
    field("SHA-256", hashlib.sha256(b).hexdigest(), C.GREEN)
    field("SHA-512", hashlib.sha512(b).hexdigest()[:64] + "…", C.CYAN)
    field("Base64",  base64.b64encode(b).decode(), C.PURPLE)
    field("ROT13",   t.translate(str.maketrans('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz',
                                               'NOPQRSTUVWXYZABCDEFGHIJKLMnopqrstuvwxyzabcdefghijklm')), C.DIM)
    field("CRC32",   hex(zlib.crc32(b) & 0xFFFFFFFF), C.PINK)
    field("Longueur", f"{len(t)} chars / {len(b)} bytes")
    pause()

def m18_links():
    panel_header("M18 — EXTRACTEUR LIENS & ASSETS", "Liens, images, scripts, iframes, emails")
    url = input(f"  {C.YELLOW}URL >{C.RESET} ").strip()
    log_inv(url, "Link Scraper")
    raw, c = req_intel(url, json_parse=False, timeout=10)
    if c != 200: err(f"HTTP {c}"); pause(); return
    
    categories = {
        "Liens externes":  re.findall(r'href=["\'](https?://[^"\']+)["\']', raw),
        "Scripts JS":      re.findall(r'src=["\'](https?://[^"\']*\.js)["\']', raw),
        "Feuilles CSS":    re.findall(r'href=["\'](https?://[^"\']*\.css)["\']', raw),
        "Images":          re.findall(r'src=["\'](https?://[^"\']*\.(jpg|jpeg|png|gif|svg|webp))["\']', raw),
        "Emails":          re.findall(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}', raw),
        "Iframes":         re.findall(r'<iframe[^>]+src=["\'](https?://[^"\']+)["\']', raw),
    }
    
    for cat, items in categories.items():
        items = [i if isinstance(i, str) else i[0] for i in items]
        items = list(set(items))[:6]
        if items:
            print(f"\n  {C.BOLD}{C.BLUE}{cat} ({len(items)}){C.RESET}")
            for l in items: print(f"    {C.DIM}├─{C.RESET} {C.CYAN}{l[:90]}{C.RESET}")
    pause()

def m19_ua():
    panel_header("M19 — USER-AGENT ANALYZER AVANCÉ", "OS, navigateur, moteur, mobile, bot")
    ua = input(f"  {C.YELLOW}User-Agent >{C.RESET} ").strip()
    log_inv("UA Parse", "User Agent")
    
    # OS
    os_map = [("Windows NT 10.0","Windows 10/11"),("Windows NT 6.3","Windows 8.1"),
              ("Windows NT 6.1","Windows 7"),("Macintosh","macOS"),
              ("Android","Android"),("iPhone","iOS"),("iPad","iPadOS"),
              ("Linux","Linux"),("CrOS","ChromeOS"),("FreeBSD","FreeBSD")]
    for pattern, name in os_map:
        if pattern in ua: field("Système d'exploitation", name, C.CYAN); break
    
    # Navigateur
    browser_map = [("Edg/","Microsoft Edge"),("OPR/","Opera"),("Chrome/","Chrome"),
                   ("Firefox/","Firefox"),("Safari/","Safari (WebKit)"),("MSIE","Internet Explorer")]
    for pattern, name in browser_map:
        if pattern in ua: field("Navigateur", name, C.GREEN); break
    
    # Moteur
    engine_map = [("AppleWebKit","WebKit"),("Gecko","Gecko"),("Trident","Trident")]
    for pattern, name in engine_map:
        if pattern in ua: field("Moteur de rendu", name, C.YELLOW); break
    
    # Version Chrome
    cv = re.search(r"Chrome/(\d+\.\d+)", ua)
    if cv: field("Version Chrome", cv.group(1), C.DIM)
    
    field("Mobile", "OUI" if any(x in ua for x in ["Mobile","Android","iPhone","iPad"]) else "NON",
          C.ORANGE if any(x in ua for x in ["Mobile","Android","iPhone","iPad"]) else C.DIM)
    
    # Bots/crawlers
    bots = ["Googlebot","bingbot","Slurp","DuckDuckBot","Baiduspider","YandexBot","facebot","ia_archiver","Scrapy","python-requests","curl"]
    detected_bot = next((b for b in bots if b.lower() in ua.lower()), None)
    field("Bot / Crawler", detected_bot if detected_bot else "Non détecté",
          C.RED if detected_bot else C.GREEN)
    pause()

def m20_subnet():
    panel_header("M20 — CALCULATEUR RÉSEAU AVANCÉ", "CIDR, broadcast, plage, masque, nombre d'hôtes")
    entry = input(f"  {C.YELLOW}CIDR (ex: 192.168.1.0/24) ou IP >{C.RESET} ").strip()
    log_inv(entry, "Subnet")
    
    if "/" not in entry: entry += "/24"
    try:
        net = ipaddress.ip_network(entry, strict=False)
        field("Réseau",          str(net.network_address), C.GREEN)
        field("Broadcast",       str(net.broadcast_address), C.YELLOW)
        field("Masque de sous-réseau", str(net.netmask), C.CYAN)
        field("Masque wildcard", str(net.hostmask), C.DIM)
        field("Préfixe CIDR",   f"/{net.prefixlen}")
        num_hosts = net.num_addresses - 2 if net.prefixlen < 31 else net.num_addresses
        field("Hôtes utilisables", f"{max(num_hosts, 0):,}", C.GREEN)
        field("Plage d'hôtes",  f"{list(net.hosts())[0] if num_hosts > 0 else 'N/A'} → {list(net.hosts())[-1] if num_hosts > 0 else 'N/A'}")
        field("Classe",         "A" if net.prefixlen <= 8 else "B" if net.prefixlen <= 16 else "C" if net.prefixlen <= 24 else "Sous-réseau")
        field("IP Privée",      "OUI" if net.is_private else "NON — PUBLIQUE", C.YELLOW if net.is_private else C.GREEN)
        field("IPv4 / IPv6",    "IPv6" if isinstance(net, ipaddress.IPv6Network) else "IPv4")
    except ValueError as e: err(f"CIDR invalide : {e}")
    pause()

def m21_headers():
    panel_header("M21 — ANALYSE EN-TÊTES HTTP SÉCURITÉ", "CSP, HSTS, CORS, cookies, TLS")
    url = input(f"  {C.YELLOW}URL >{C.RESET} ").strip()
    log_inv(url, "HTTP Headers")
    
    try:
        req = urllib.request.Request(url, method="GET", headers={"User-Agent": random.choice(UAS)})
        r = urllib.request.urlopen(req, timeout=8, context=ctx)
        h = {k.lower(): v for k, v in r.info().items()}
    except Exception as e: err(f"Échec : {e}"); pause(); return
    
    field("Server", h.get("server", "Masqué"), C.CYAN)
    field("X-Powered-By", h.get("x-powered-by", "Masqué"), C.CYAN)
    field("Content-Type", h.get("content-type", "N/A"))
    
    sec_headers = {
        "strict-transport-security": ("HSTS", True),
        "content-security-policy":   ("CSP", True),
        "x-frame-options":           ("X-Frame-Options", True),
        "x-content-type-options":    ("X-Content-Type-Options", True),
        "x-xss-protection":          ("XSS Protection", True),
        "permissions-policy":        ("Permissions Policy", True),
        "referrer-policy":           ("Referrer Policy", True),
        "cross-origin-opener-policy":("COOP", True),
    }
    
    print(f"\n  {C.BOLD}{'En-tête de Sécurité':<32} {'Statut':<12} {'Valeur'}{C.RESET}")
    draw_sep()
    missing = []
    for header, (name, required) in sec_headers.items():
        val = h.get(header)
        if val:
            print(f"  {C.GREEN}✔{C.RESET}  {name:<32} {C.GREEN}PRÉSENT{C.RESET}    {C.DIM}{val[:40]}{C.RESET}")
        else:
            color = C.RED if required else C.YELLOW
            print(f"  {color}✘{C.RESET}  {name:<32} {color}ABSENT{C.RESET}")
            missing.append(name)
    
    if missing: print(f"\n"); sec(f"En-têtes manquants : {', '.join(missing)}")
    
    # Cookies
    cookies_raw = h.get("set-cookie", "")
    if cookies_raw:
        print(f"\n  {C.BOLD}{C.YELLOW}Cookie(s) Set-Cookie :{C.RESET}")
        for attr in ["Secure", "HttpOnly", "SameSite"]:
            present = attr.lower() in cookies_raw.lower()
            c_color = C.GREEN if present else C.RED
            print(f"    {c_color}{'✔' if present else '✘'}{C.RESET} {attr}")
    pause()

def m22_regex():
    panel_header("M22 — VALIDATEUR & EXTRACTEUR REGEX", "Email, IP, URL, carte bancaire, IBAN, hash")
    d = input(f"  {C.YELLOW}Donnée ou texte >{C.RESET} ").strip()
    log_inv(d, "Regex Test")
    
    patterns = {
        "IPv4":           r"^(\d{1,3}\.){3}\d{1,3}$",
        "IPv6":           r"^[0-9a-fA-F:]{7,39}$",
        "Email":          r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$",
        "URL HTTPS":      r"^https://[^\s]+$",
        "URL HTTP":       r"^http://[^\s]+$",
        "Carte Visa":     r"^4[0-9]{12}(?:[0-9]{3})?$",
        "Carte MC":       r"^5[1-5][0-9]{14}$",
        "Carte Amex":     r"^3[47][0-9]{13}$",
        "IBAN FR":        r"^FR\d{2}[A-Z0-9]{23}$",
        "Hash MD5":       r"^[a-fA-F0-9]{32}$",
        "Hash SHA-256":   r"^[a-fA-F0-9]{64}$",
        "Hash SHA-1":     r"^[a-fA-F0-9]{40}$",
        "MAC Address":    r"^([0-9A-Fa-f]{2}[:\-]){5}[0-9A-Fa-f]{2}$",
        "Num. Tél FR":    r"^(?:\+33|0033|0)[1-9](?:\d{8})$",
        "Code Postal FR": r"^\d{5}$",
        "Bitcoin (BTC)":  r"^[13][a-km-zA-HJ-NP-Z1-9]{25,34}$|^bc1[a-z0-9]{6,87}$",
        "Ethereum (ETH)": r"^0x[a-fA-F0-9]{40}$",
        "JWT Token":      r"^[A-Za-z0-9-_]+\.[A-Za-z0-9-_]+\.[A-Za-z0-9-_]*$",
    }
    
    matches = [(name, bool(re.match(pat, d))) for name, pat in patterns.items()]
    hits = [(n, v) for n, v in matches if v]
    
    if hits:
        for name, _ in hits: ok(f"Format reconnu : {C.BOLD}{name}{C.RESET}")
    else: warn("Format non reconnu dans les patterns standards.")
    
    # Si JWT, décoder
    if re.match(r"^[A-Za-z0-9-_]+\.[A-Za-z0-9-_]+\.[A-Za-z0-9-_]*$", d):
        try:
            parts = d.split(".")
            for i, part in enumerate(parts[:2]):
                pad = 4 - len(part) % 4
                decoded = json.loads(base64.urlsafe_b64decode(part + "=" * pad))
                label = "Header" if i == 0 else "Payload"
                print(f"\n  {C.BOLD}{C.CYAN}JWT {label} :{C.RESET}")
                for k, v in decoded.items():
                    ts_val = datetime.fromtimestamp(v).strftime('%d/%m/%Y %H:%M') if k in ("exp","iat","nbf") and isinstance(v,int) else str(v)
                    field(f"  {k}", ts_val, C.YELLOW)
        except: pass
    pause()

def m23_ping():
    panel_header("M23 — LATENCE & TRACEROUTE", "Ping multi-host, estimation TTL")
    h = input(f"  {C.YELLOW}Hôte >{C.RESET} ").strip()
    log_inv(h, "Ping")
    
    latencies = []
    for i in range(5):
        t0 = time.time()
        try:
            socket.gethostbyname(h)
            lat = (time.time() - t0) * 1000
            latencies.append(lat)
            color = C.GREEN if lat < 50 else (C.YELLOW if lat < 200 else C.RED)
            print(f"  {C.DIM}[{i+1}/5]{C.RESET} {color}{lat:.2f} ms{C.RESET}")
        except: print(f"  {C.DIM}[{i+1}/5]{C.RESET} {C.RED}Timeout{C.RESET}")
        time.sleep(0.2)
    
    if latencies:
        avg = sum(latencies) / len(latencies)
        field("Moyenne", f"{avg:.2f} ms", C.GREEN if avg < 50 else C.YELLOW)
        field("Min / Max", f"{min(latencies):.2f} ms / {max(latencies):.2f} ms")
        qual = "Excellente" if avg < 30 else "Bonne" if avg < 80 else "Correcte" if avg < 200 else "Mauvaise"
        field("Qualité réseau", qual, C.GREEN if avg < 80 else C.YELLOW)
    pause()

def m24_cms():
    panel_header("M24 — DÉTECTEUR CMS & FRAMEWORK", "WordPress, Joomla, Drupal, Shopify, Laravel…")
    url = input(f"  {C.YELLOW}URL >{C.RESET} ").strip().rstrip("/")
    log_inv(url, "CMS Detect")
    
    raw, c = req_intel(url, json_parse=False, timeout=8)
    if c == 0: err("Site inaccessible."); pause(); return
    
    # HTML-based detection
    cms_sigs = {
        "WordPress":    ["/wp-content/", "/wp-includes/", "wp-login.php"],
        "Joomla":       ["/media/jui/", "Joomla!", "joomla"],
        "Drupal":       ["Drupal.settings", "/sites/default/files/", "drupal.js"],
        "Shopify":      ["cdn.shopify.com", "Shopify.theme", "myshopify.com"],
        "Magento":      ["Mage.Cookies", "/skin/frontend/", "Magento"],
        "PrestaShop":   ["prestashop", "/themes/classic/"],
        "Wix":          ["wix.com", "wixstatic.com"],
        "Squarespace":  ["squarespace.com", "squarespace-cdn.com"],
        "Webflow":      ["webflow.com", "webflow.js"],
        "Ghost":        ["ghost.io", "ghost/api"],
        "Laravel":      ["laravel_session", "Laravel"],
        "Django":       ["csrfmiddlewaretoken", "django"],
        "Rails":        ["rails-ujs", "authenticity_token"],
        "Next.js":      ["__NEXT_DATA__", "_next/static"],
        "Nuxt.js":      ["__nuxt", "_nuxt/"],
    }
    
    detected = []
    for cms, sigs in cms_sigs.items():
        if any(s.lower() in raw.lower() for s in sigs): detected.append(cms)
    
    # Path-based detection
    path_checks = {
        "WordPress": "/wp-login.php", "Joomla": "/administrator/",
        "Drupal": "/user/login", "phpMyAdmin": "/phpmyadmin/",
    }
    for name, path in path_checks.items():
        _, sc = req_intel(url + path, json_parse=False, timeout=3)
        if sc in [200, 301, 302, 403] and name not in detected: detected.append(f"{name} (path)")
    
    if detected:
        for cms in detected: hit(f"CMS/Framework détecté : {cms}")
    else: info("Aucun CMS standard détecté.")
    pause()

def m25_vt(t=None):
    if not t: panel_header("M25 — VIRUSTOTAL SCAN AVANCÉ", "IP, domaine, hash, URL")
    cfg = load_config()
    k = cfg.get("API_KEYS", {}).get("VIRUSTOTAL", "")
    if not k: err("Clé API VT manquante (config.json → VIRUSTOTAL)"); pause() if not t else None; return
    
    target = t or input(f"  {C.YELLOW}IP/Hash/Domaine/URL >{C.RESET} ").strip()
    log_inv(target, "VirusTotal")
    
    # Détecter le type
    if re.match(r'^[a-fA-F0-9]{32,64}$', target):
        endpoint = f"https://www.virustotal.com/api/v3/files/{target}"
    elif re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', target):
        endpoint = f"https://www.virustotal.com/api/v3/ip_addresses/{target}"
    elif re.match(r'^https?://', target):
        import base64 as b64
        url_id = b64.urlsafe_b64encode(target.encode()).decode().rstrip("=")
        endpoint = f"https://www.virustotal.com/api/v3/urls/{url_id}"
    else:
        endpoint = f"https://www.virustotal.com/api/v3/domains/{target}"
    
    d, c = req_intel(endpoint, headers={"x-apikey": k})
    if c == 200:
        attrs = d.get("data", {}).get("attributes", {})
        stats = attrs.get("last_analysis_stats", {})
        malicious  = stats.get("malicious", 0)
        suspicious = stats.get("suspicious", 0)
        harmless   = stats.get("harmless", 0)
        undetected = stats.get("undetected", 0)
        total = malicious + suspicious + harmless + undetected
        
        color = C.RED if malicious > 0 else (C.YELLOW if suspicious > 0 else C.GREEN)
        field("Score",       f"{malicious}/{total} moteurs malveillants", color)
        field("Malveillants", malicious, C.RED if malicious > 0 else C.GREEN)
        field("Suspects",    suspicious, C.YELLOW if suspicious > 0 else C.GREEN)
        field("Inoffensifs", harmless, C.GREEN)
        field("Réputation VT", attrs.get("reputation", "N/A"), C.CYAN)
        
        # Noms de menaces
        results = attrs.get("last_analysis_results", {})
        threats = [v.get("result") for v in results.values() if v.get("category") == "malicious" and v.get("result")]
        if threats:
            unique_threats = list(set(threats))[:5]
            field("Menaces détectées", " | ".join(unique_threats), C.RED)
    else: err(f"Erreur API {c} — clé invalide ou quota dépassé.")
    if not t: pause()

def m26_shodan(t=None):
    if not t: panel_header("M26 — SHODAN INTELLIGENCE", "OS, ports, CVE, services, hostnames")
    cfg = load_config()
    k = cfg.get("API_KEYS", {}).get("SHODAN", "")
    if not k: err("Clé API Shodan manquante (config.json → SHODAN)"); pause() if not t else None; return
    
    target = t or input(f"  {C.YELLOW}IP cible >{C.RESET} ").strip()
    log_inv(target, "Shodan")
    d, c = req_intel(f"https://api.shodan.io/shodan/host/{target}?key={k}")
    if c == 200:
        field("IP", d.get("ip_str", target), C.GREEN)
        field("OS", d.get("os") or "Inconnu", C.CYAN)
        field("Hostnames", ", ".join(d.get("hostnames", [])) or "N/A", C.YELLOW)
        field("Organisation", d.get("org", "N/A"))
        field("ISP", d.get("isp", "N/A"))
        field("ASN", d.get("asn", "N/A"), C.PURPLE)
        field("Localisation", f"{d.get('city', 'N/A')}, {d.get('country_name', 'N/A')}")
        field("Ports ouverts", ", ".join(map(str, d.get("ports", []))), C.YELLOW)
        
        vulns = d.get("vulns", [])
        if vulns:
            sec(f"CVE détectés : {', '.join(list(vulns)[:8])}")
        
        # Services
        for svc in d.get("data", [])[:5]:
            port = svc.get("port")
            product = svc.get("product", "")
            version = svc.get("version", "")
            transport = svc.get("transport", "tcp")
            print(f"  {C.CYAN}[{transport.upper()}:{port}]{C.RESET} {C.WHITE}{product} {version}{C.RESET}")
    else: err(f"Aucune donnée Shodan (HTTP {c}).")
    if not t: pause()

def m27_db():
    panel_header("M27 — HISTORIQUE DES INVESTIGATIONS", "SQLite — 15 derniers enregistrements")
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT * FROM investigations ORDER BY id DESC LIMIT 20")
    rows = c.fetchall()
    conn.close()
    if not rows: info("Base de données vide."); pause(); return
    print(f"  {C.BOLD}{'ID':<4} │ {'DATE':<20} │ {'CIBLE':<22} │ {'MODULE':<22} │ {'RÉSULTAT'}{C.RESET}")
    draw_sep()
    for r in rows:
        result = (r[4][:25] + "…") if len(r) > 4 and len(str(r[4])) > 25 else (r[4] if len(r) > 4 else "")
        print(f"  {r[0]:<4} │ {C.DIM}{r[1]}{C.RESET} │ {C.YELLOW}{str(r[2])[:22]:<22}{C.RESET} │ {C.CYAN}{r[3]:<22}{C.RESET} │ {C.DIM}{result}{C.RESET}")
    
    print(f"\n  {C.DIM}[D] Supprimer un enregistrement  [C] Vider la base  [Entrée] Retour{C.RESET}")
    cmd = input(f"  {C.YELLOW}>{C.RESET} ").strip().upper()
    if cmd == "C":
        conn = sqlite3.connect(DB_FILE); conn.execute("DELETE FROM investigations"); conn.commit(); conn.close()
        ok("Base vidée.")
    elif cmd == "D":
        rid = input("  ID à supprimer > ").strip()
        conn = sqlite3.connect(DB_FILE); conn.execute("DELETE FROM investigations WHERE id=?", (rid,)); conn.commit(); conn.close()
        ok(f"Entrée {rid} supprimée.")
    pause()

# ══════════════════════════════════════════════════════════
#  NOUVEAUX MODULES v6.0
# ══════════════════════════════════════════════════════════

def m28_ssl():
    """Analyse complète du certificat SSL/TLS"""
    panel_header("M28 — ANALYSE CERTIFICAT SSL/TLS", "Validité, émetteur, SAN, algorithmes, grade")
    host = input(f"  {C.YELLOW}Domaine >{C.RESET} ").strip()
    port = int(input(f"  {C.YELLOW}Port [443] >{C.RESET} ").strip() or "443")
    log_inv(host, "SSL/TLS Analysis")
    
    try:
        ctx_check = ssl.create_default_context()
        with socket.create_connection((host, port), timeout=8) as sock:
            with ctx_check.wrap_socket(sock, server_hostname=host) as ssock:
                cert = ssock.getpeercert()
                cipher = ssock.cipher()
                version = ssock.version()
        
        field("Protocole TLS", version, C.GREEN if version in ("TLSv1.3","TLSv1.2") else C.RED)
        field("Cipher Suite", cipher[0] if cipher else "N/A", C.CYAN)
        field("Bits", cipher[2] if cipher else "N/A", C.GREEN if cipher and cipher[2] >= 128 else C.RED)
        
        # Sujet
        subject = dict(x[0] for x in cert.get("subject", []))
        issuer  = dict(x[0] for x in cert.get("issuer", []))
        field("Domaine (CN)", subject.get("commonName", "N/A"), C.WHITE)
        field("Organisation", subject.get("organizationName", "N/A"))
        field("Émetteur CA", issuer.get("commonName", "N/A"), C.YELLOW)
        field("Org. Émetteur", issuer.get("organizationName", "N/A"))
        
        # Validité
        not_before = datetime.strptime(cert["notBefore"], "%b %d %H:%M:%S %Y %Z")
        not_after  = datetime.strptime(cert["notAfter"],  "%b %d %H:%M:%S %Y %Z")
        days_left  = (not_after - datetime.now()).days
        field("Valide depuis", not_before.strftime("%d/%m/%Y"), C.DIM)
        field("Expire le", not_after.strftime("%d/%m/%Y"), C.RED if days_left < 30 else C.GREEN)
        field("Jours restants", days_left, C.RED if days_left < 30 else (C.YELLOW if days_left < 90 else C.GREEN))
        
        if days_left < 0: sec("CERTIFICAT EXPIRÉ !")
        elif days_left < 30: warn("Certificat expire bientôt.")
        
        # SAN
        san = cert.get("subjectAltName", [])
        if san:
            san_list = [v for t, v in san if t == "DNS"][:8]
            field("SAN (domaines couverts)", ", ".join(san_list), C.CYAN)
        
        # Auto-signé ?
        if subject == issuer: warn("Certificat AUTO-SIGNÉ détecté !")
        
        # Let's Encrypt ?
        if "Let's Encrypt" in issuer.get("organizationName", ""):
            info("Certificat Let's Encrypt (gratuit/automatisé).")
        
    except ssl.SSLCertVerificationError as e:
        sec(f"Certificat invalide : {e}")
    except Exception as e:
        err(f"Impossible de se connecter : {e}")
    pause()

def m29_whois():
    """WHOIS via API publique"""
    panel_header("M29 — WHOIS COMPLET", "Registrar, dates, nameservers, registrant")
    domain = input(f"  {C.YELLOW}Domaine >{C.RESET} ").strip().lower()
    log_inv(domain, "WHOIS")
    
    d, c = req_intel(f"https://api.whoapi.com/?domain={domain}&r=whois&apikey=demokey")
    
    # Utiliser whoisjson comme fallback
    d2, c2 = req_intel(f"https://whois.freeaiapi.xyz/?name={domain}")
    
    # rdap (standard moderne, remplace whois)
    d3, c3 = req_intel(f"https://rdap.org/domain/{domain}")
    if c3 == 200:
        field("Domaine", d3.get("ldhName", domain).lower(), C.GREEN)
        field("Statut", ", ".join([s.get("value","") if isinstance(s,dict) else s for s in d3.get("status",[])[:3]]), C.YELLOW)
        
        for event in d3.get("events", []):
            action = event.get("eventAction", "")
            date   = event.get("eventDate", "")[:10]
            if action == "registration": field("Enregistrement", date, C.GREEN)
            elif action == "expiration":
                exp = datetime.strptime(date, "%Y-%m-%d") if date else None
                days = (exp - datetime.now()).days if exp else 0
                field("Expiration", f"{date} ({days} jours)", C.RED if days < 30 else C.YELLOW)
            elif action == "last changed": field("Dernière modification", date, C.DIM)
        
        for ns in d3.get("nameservers", [])[:4]:
            print(f"  {C.CYAN}[NS]{C.RESET} {ns.get('ldhName', '').lower()}")
        
        for entity in d3.get("entities", []):
            roles = entity.get("roles", [])
            vcards = entity.get("vcardArray", [None, []])[1] if entity.get("vcardArray") else []
            name = next((v[3] for v in vcards if v[0] == "fn"), None)
            email = next((v[3] for v in vcards if v[0] == "email"), None)
            if "registrar" in roles and name: field("Registrar", name, C.PURPLE)
            if email: field("Email (WHOIS)", email, C.YELLOW)
    else:
        # Fallback: DNS-based info
        info("RDAP non disponible pour ce TLD. Tentative DNS…")
        for rt, rname in [(2,"NS"),(6,"SOA")]:
            d, c = req_intel(f"https://cloudflare-dns.com/dns-query?name={domain}&type={rt}",
                             headers={"accept": "application/dns-json"})
            if c == 200 and "Answer" in d:
                for a in d["Answer"]: field(rname, a.get("data","")[:60], C.CYAN)
    pause()

def m30_pastebin():
    """Recherche de données exposées sur Pastebin et sites similaires"""
    panel_header("M30 — RECHERCHE PASTES EXPOSÉS", "Pastebin, GitHub Gists, dépôts publics")
    query = input(f"  {C.YELLOW}Terme de recherche (email, domaine, IP…) >{C.RESET} ").strip()
    log_inv(query, "Pastebin/Paste Search")
    
    searches = {
        "Google (Pastebin)": f"site:pastebin.com {query}",
        "Google (Gist)":     f"site:gist.github.com {query}",
        "Google (Hastebin)": f"site:hastebin.com {query}",
        "Google (Ghostbin)": f"site:ghostbin.co {query}",
        "Google (Pastie)":   f"site:pastie.org {query}",
    }
    
    info("Ouverture des recherches Google pour chaque source…")
    for name, q in searches.items():
        print(f"  {C.CYAN}→{C.RESET} {name}")
        webbrowser.open_new_tab(f"https://www.google.com/search?q={urllib.parse.quote(q)}")
        time.sleep(0.8)
    
    warn("Vérifiez les onglets ouverts. Les pastes contenant vos termes apparaîtront.")
    pause()

def m31_wayback():
    """Wayback Machine — historique d'un site"""
    panel_header("M31 — WAYBACK MACHINE", "Historique, snapshots, premières apparitions")
    url = input(f"  {C.YELLOW}URL (ex: example.com) >{C.RESET} ").strip()
    clean = re.sub(r"^https?://", "", url).rstrip("/")
    log_inv(url, "Wayback Machine")
    
    # Availability API
    d, c = req_intel(f"https://archive.org/wayback/available?url={clean}")
    if c == 200 and d.get("archived_snapshots"):
        snap = d["archived_snapshots"].get("closest", {})
        ts = snap.get("timestamp", "")
        if ts:
            dt = datetime.strptime(ts, "%Y%m%d%H%M%S")
            field("Snapshot le plus proche", dt.strftime("%d/%m/%Y %H:%M"), C.GREEN)
            field("URL Archive", snap.get("url", ""), C.CYAN)
            field("Statut", snap.get("status", ""), C.YELLOW)
    
    # CDX API — nombre de snapshots
    cdx, cc = req_intel(f"http://web.archive.org/cdx/search/cdx?url={clean}&output=json&limit=3&fl=timestamp,statuscode,mimetype")
    if cc == 200 and isinstance(cdx, list) and len(cdx) > 1:
        first = cdx[1][0] if len(cdx) > 1 else None
        if first:
            dt_first = datetime.strptime(first[:14], "%Y%m%d%H%M%S")
            field("Premier snapshot", dt_first.strftime("%d/%m/%Y"), C.GREEN)
        field("Snapshots récupérés", f"{len(cdx)-1} (limité à 3)", C.CYAN)
    
    # Liens directs
    print(f"\n  {C.BOLD}{C.BLUE}Liens utiles{C.RESET}")
    links = {
        "Historique complet": f"https://web.archive.org/web/*/{clean}",
        "Timeline calendar":  f"https://web.archive.org/web/20*/{clean}",
    }
    for name, lnk in links.items():
        field(name, lnk, C.CYAN)
    pause()

def m32_abuseipdb():
    """AbuseIPDB — réputation d'une IP"""
    panel_header("M32 — ABUSEIPDB REPUTATION", "Score d'abus, pays, signalements, catégories")
    cfg = load_config()
    k = cfg.get("API_KEYS", {}).get("ABUSEIPDB", "")
    if not k: err("Clé API AbuseIPDB manquante (config.json → ABUSEIPDB)"); pause(); return
    
    ip = input(f"  {C.YELLOW}IP cible >{C.RESET} ").strip()
    log_inv(ip, "AbuseIPDB")
    
    d, c = req_intel(f"https://api.abuseipdb.com/api/v2/check?ipAddress={ip}&maxAgeInDays=90&verbose=true",
                     headers={"Key": k, "Accept": "application/json"})
    if c == 200:
        data = d.get("data", {})
        score = data.get("abuseConfidenceScore", 0)
        color = C.RED if score > 50 else (C.YELLOW if score > 10 else C.GREEN)
        field("IP",           data.get("ipAddress"), C.WHITE)
        field("Score d'abus", f"{score}/100", color)
        field("Total rapports", data.get("totalReports", 0), C.RED if score > 0 else C.GREEN)
        field("Dernière rapport", data.get("lastReportedAt", "Jamais")[:10])
        field("Pays", data.get("countryCode", "N/A"))
        field("ISP", data.get("isp", "N/A"), C.CYAN)
        field("Usage Type", data.get("usageType", "N/A"))
        field("Tor Node", "OUI" if data.get("isTor") else "NON", C.RED if data.get("isTor") else C.GREEN)
        
        # Catégories d'abus
        cat_map = {3:"Fraude/Phishing",4:"Email Spam",5:"Web Spam",7:"Credential Brute",
                   9:"Open Proxy",11:"Web Attack",14:"Port Scan",15:"Hacking",18:"SSH Brute",21:"FTP Brute",22:"SSH Brute (2)"}
        cats = set()
        for report in data.get("reports", [])[:20]:
            for cat in report.get("categories", []): cats.add(cat)
        if cats:
            cat_names = [cat_map.get(c, f"Cat.{c}") for c in cats]
            field("Catégories", " | ".join(cat_names), C.RED)
    else: err(f"Erreur API AbuseIPDB : {c}")
    pause()

def m33_bitcoin():
    """Analyse d'adresse Bitcoin/crypto"""
    panel_header("M33 — CRYPTO WALLET ANALYSIS", "BTC, ETH — balance, transactions, risque")
    print(f"  {C.CYAN}[1]{C.RESET} Bitcoin (BTC)  {C.CYAN}[2]{C.RESET} Ethereum (ETH)")
    choice = input(f"  {C.YELLOW}Choix >{C.RESET} ").strip()
    addr = input(f"  {C.YELLOW}Adresse wallet >{C.RESET} ").strip()
    log_inv(addr, "Crypto Wallet")
    
    if choice == "1" or re.match(r"^[13][a-km-zA-HJ-NP-Z1-9]{25,34}$|^bc1[a-z0-9]{6,87}$", addr):
        d, c = req_intel(f"https://blockchain.info/rawaddr/{addr}?limit=5")
        if c == 200:
            balance_btc = d.get("final_balance", 0) / 1e8
            total_recv  = d.get("total_received", 0) / 1e8
            n_tx        = d.get("n_tx", 0)
            field("Adresse BTC", addr, C.YELLOW)
            field("Balance", f"{balance_btc:.8f} BTC", C.GREEN if balance_btc > 0 else C.DIM)
            field("Total reçu", f"{total_recv:.8f} BTC")
            field("Nb transactions", n_tx, C.CYAN)
            field("Explorer", f"https://www.blockchain.com/explorer/addresses/btc/{addr}", C.CYAN)
            
            for tx in d.get("txs", [])[:3]:
                ts = datetime.fromtimestamp(tx.get("time", 0)).strftime("%d/%m/%Y %H:%M")
                val = sum(o.get("value",0) for o in tx.get("out",[])) / 1e8
                print(f"  {C.DIM}TX{C.RESET} {ts} : {C.YELLOW}{val:.8f} BTC{C.RESET}")
        else: err(f"Adresse inconnue ou API inaccessible (HTTP {c})")
    
    elif choice == "2" or re.match(r"^0x[a-fA-F0-9]{40}$", addr):
        d, c = req_intel(f"https://api.etherscan.io/api?module=account&action=balance&address={addr}&tag=latest&apikey=YourApiKeyToken")
        if c == 200 and d.get("status") == "1":
            balance_eth = int(d.get("result", 0)) / 1e18
            field("Adresse ETH", addr, C.PURPLE)
            field("Balance", f"{balance_eth:.6f} ETH", C.GREEN if balance_eth > 0 else C.DIM)
            field("Explorer", f"https://etherscan.io/address/{addr}", C.CYAN)
        else: info("Clé API Etherscan nécessaire pour données complètes (gratuite sur etherscan.io)")
    else:
        err("Format d'adresse non reconnu.")
    pause()

def m34_darkweb():
    """Vérification d'exposition sur le dark web (via sources publiques)"""
    panel_header("M34 — DARK WEB EXPOSURE CHECK", "Tor hidden services, Ahmia, indices publics")
    query = input(f"  {C.YELLOW}Terme à vérifier (email, domaine, pseudo…) >{C.RESET} ").strip()
    log_inv(query, "Dark Web Check")
    
    warn("Ce module utilise des moteurs d'indexation Tor légaux (Ahmia, Torch).")
    info("Aucune connexion directe à Tor — lecture d'index publics uniquement.")
    print()
    
    # Ahmia clearnet gateway
    ahmia_url = f"https://ahmia.fi/search/?q={urllib.parse.quote(query)}"
    field("Ahmia (index Tor)", ahmia_url, C.CYAN)
    
    # Intelligence X
    intelx_url = f"https://intelx.io/?s={urllib.parse.quote(query)}"
    field("Intelligence X", intelx_url, C.YELLOW)
    
    # Breach check indirect
    field("DeHashed Search", f"https://dehashed.com/search?query={urllib.parse.quote(query)}", C.ORANGE)
    field("Leak-Lookup", f"https://leak-lookup.com/search?q={urllib.parse.quote(query)}", C.CYAN)
    
    c = input(f"\n  {C.YELLOW}Ouvrir dans le navigateur ? [O/n] >{C.RESET} ").strip().lower()
    if c != "n":
        webbrowser.open_new_tab(ahmia_url)
        webbrowser.open_new_tab(intelx_url)
    pause()

def m35_cve():
    """Recherche CVE via NVD (NIST)"""
    panel_header("M35 — CVE VULNERABILITY LOOKUP", "Base NVD/NIST — CVSS, exploitabilité")
    query = input(f"  {C.YELLOW}CVE-ID, produit ou terme >{C.RESET} ").strip()
    log_inv(query, "CVE Lookup")
    
    # Si format CVE-XXXX-XXXXX
    if re.match(r'CVE-\d{4}-\d+', query, re.IGNORECASE):
        d, c = req_intel(f"https://services.nvd.nist.gov/rest/json/cves/2.0?cveId={query.upper()}")
    else:
        d, c = req_intel(f"https://services.nvd.nist.gov/rest/json/cves/2.0?keywordSearch={urllib.parse.quote(query)}&resultsPerPage=5")
    
    if c == 200:
        vulns = d.get("vulnerabilities", [])
        if not vulns: info("Aucune CVE trouvée."); pause(); return
        
        for item in vulns[:5]:
            cve = item.get("cve", {})
            cve_id = cve.get("id", "N/A")
            desc_list = cve.get("descriptions", [])
            desc = next((x["value"] for x in desc_list if x.get("lang") == "en"), "N/A")
            
            # CVSS score
            metrics = cve.get("metrics", {})
            cvss_score = None
            severity = "N/A"
            for version in ["cvssMetricV31", "cvssMetricV30", "cvssMetricV2"]:
                if version in metrics and metrics[version]:
                    cvss_data = metrics[version][0].get("cvssData", {})
                    cvss_score = cvss_data.get("baseScore")
                    severity   = cvss_data.get("baseSeverity", "N/A")
                    break
            
            draw_sep()
            s_color = C.RED if cvss_score and cvss_score >= 7 else (C.YELLOW if cvss_score and cvss_score >= 4 else C.GREEN)
            field("CVE ID", cve_id, C.RED)
            if cvss_score: field("CVSS Score / Sévérité", f"{cvss_score} — {severity}", s_color)
            field("Description", desc[:100] + "…" if len(desc) > 100 else desc, C.DIM)
            field("Détails NVD", f"https://nvd.nist.gov/vuln/detail/{cve_id}", C.CYAN)
    else: err(f"Erreur NVD API : HTTP {c}")
    pause()

def m36_social_links():
    """Construction d'un profil OSINT complet depuis un nom ou email"""
    panel_header("M36 — PROFIL OSINT COMPLET", "Génération de liens cross-plateformes automatique")
    print(f"  {C.CYAN}[1]{C.RESET} Depuis un nom  {C.CYAN}[2]{C.RESET} Depuis un email")
    mode = input(f"  {C.YELLOW}Mode >{C.RESET} ").strip()
    
    if mode == "1":
        name = input(f"  {C.YELLOW}Nom complet >{C.RESET} ").strip()
        log_inv(name, "Social Profile Build")
        q = urllib.parse.quote(f'"{name}"')
        q2 = urllib.parse.quote(name)
    else:
        email = input(f"  {C.YELLOW}Email >{C.RESET} ").strip()
        log_inv(email, "Social Profile Build")
        q = urllib.parse.quote(f'"{email}"')
        q2 = urllib.parse.quote(email)
    
    links = {
        "Google":         f"https://www.google.com/search?q={q}",
        "LinkedIn":       f"https://www.linkedin.com/search/results/all/?keywords={q2}",
        "Twitter/X":      f"https://twitter.com/search?q={q}&f=user",
        "Facebook":       f"https://www.facebook.com/search/people/?q={q2}",
        "Instagram":      f"https://www.instagram.com/explore/search/keyword/?q={q2}",
        "TikTok":         f"https://www.tiktok.com/search?q={q2}",
        "GitHub":         f"https://github.com/search?q={q2}&type=users",
        "PeopleFinder":   f"https://www.peoplefinder.com/search/?q={q2}",
        "Pipl":           f"https://pipl.com/search/?q={q2}",
        "Spokeo":         f"https://www.spokeo.com/search?q={q2}",
        "Intelius":       f"https://www.intelius.com/search?firstName={q2}",
        "BeenVerified":   f"https://www.beenverified.com/f/search/people?q={q2}",
    }
    
    print(f"\n  {C.BOLD}{'Source':<18} {'URL OSINT'}{C.RESET}")
    draw_sep()
    for name_, url in links.items():
        print(f"  {C.CYAN}●{C.RESET} {name_:<18} {C.DIM}{url[:65]}{C.RESET}")
    
    c = input(f"\n  {C.YELLOW}Ouvrir tous dans le navigateur ? [O/n] >{C.RESET} ").strip().lower()
    if c != "n":
        for _, url in links.items():
            webbrowser.open_new_tab(url)
            time.sleep(0.3)
    pause()

def m37_fullscan():
    """Full automated scan sur une cible (IP/domaine)"""
    panel_header("M37 — FULL AUTOMATED SCAN", "GeoIP + Ports + DNS + SSL + Headers + CMS en chaîne")
    target = input(f"  {C.YELLOW}Cible IP ou Domaine >{C.RESET} ").strip()
    log_inv(target, "Full Auto Scan")
    
    is_ip = re.match(r"^\d{1,3}(\.\d{1,3}){3}$", target)
    modules_to_run = []
    
    if not is_ip:
        modules_to_run = [
            ("GeoIP",    lambda: m02_geo(target)),
            ("DNS",      lambda: _auto_dns(target)),
            ("SSL/TLS",  lambda: _auto_ssl(target)),
            ("Headers",  lambda: _auto_headers(f"https://{target}")),
            ("CMS",      lambda: _auto_cms(f"https://{target}")),
            ("Ports",    lambda: m12_ports(target)),
        ]
    else:
        modules_to_run = [
            ("GeoIP",    lambda: m02_geo(target)),
            ("Ports",    lambda: m12_ports(target)),
            ("RevDNS",   lambda: _auto_revdns(target)),
        ]
        cfg = load_config()
        if cfg.get("API_KEYS", {}).get("VIRUSTOTAL"):
            modules_to_run.append(("VirusTotal", lambda: m25_vt(target)))
        if cfg.get("API_KEYS", {}).get("SHODAN"):
            modules_to_run.append(("Shodan", lambda: m26_shodan(target)))
        if cfg.get("API_KEYS", {}).get("ABUSEIPDB"):
            modules_to_run.append(("AbuseIPDB", lambda: m32_abuseipdb_auto(target)))
    
    results = {}
    for i, (name, fn) in enumerate(modules_to_run):
        print(f"\n  {C.BLUE}{'═'*70}{C.RESET}")
        print(f"  {C.BOLD}{C.CYAN}[{i+1}/{len(modules_to_run)}] Module : {name}{C.RESET}")
        print(f"  {C.BLUE}{'─'*70}{C.RESET}")
        try: fn()
        except Exception as e: err(f"Erreur dans {name} : {e}")
    
    ok(f"Full scan terminé — {len(modules_to_run)} modules exécutés sur {target}")
    pause()

def _auto_dns(domain):
    types = {1:"A", 28:"AAAA", 15:"MX", 2:"NS"}
    for rt, rname in types.items():
        d, c = req_intel(f"https://cloudflare-dns.com/dns-query?name={domain}&type={rt}",
                         headers={"accept": "application/dns-json"})
        if c == 200 and "Answer" in d:
            for a in d["Answer"]: field(f"DNS {rname}", a.get("data","")[:60], C.CYAN)

def _auto_ssl(host, port=443):
    try:
        ctx_check = ssl.create_default_context()
        with socket.create_connection((host, port), timeout=5) as sock:
            with ctx_check.wrap_socket(sock, server_hostname=host) as ssock:
                cert = ssock.getpeercert()
                version = ssock.version()
        not_after = datetime.strptime(cert["notAfter"], "%b %d %H:%M:%S %Y %Z")
        days_left = (not_after - datetime.now()).days
        field("TLS Version", version, C.GREEN if "1.3" in version else C.YELLOW)
        field("Cert expire dans", f"{days_left} jours", C.RED if days_left < 30 else C.GREEN)
    except Exception as e: err(f"SSL : {e}")

def _auto_headers(url):
    try:
        req = urllib.request.Request(url, method="GET", headers={"User-Agent": random.choice(UAS)})
        r = urllib.request.urlopen(req, timeout=5, context=ctx)
        h = {k.lower(): v for k, v in r.info().items()}
        field("Server",     h.get("server","Masqué"), C.CYAN)
        field("HSTS",       "ACTIF" if "strict-transport-security" in h else "ABSENT",
              C.GREEN if "strict-transport-security" in h else C.RED)
        field("CSP",        "ACTIF" if "content-security-policy" in h else "ABSENT",
              C.GREEN if "content-security-policy" in h else C.YELLOW)
    except Exception as e: err(f"Headers : {e}")

def _auto_cms(url):
    raw, c = req_intel(url, json_parse=False, timeout=6)
    if c == 200:
        for cms, sigs in {"WordPress":["/wp-content/"],
                          "Shopify":["cdn.shopify.com"],
                          "Drupal":["Drupal.settings"],
                          "Joomla":["Joomla!"]}.items():
            if any(s in raw for s in sigs): hit(f"CMS : {cms}")

def _auto_revdns(ip):
    try:
        name, _, _ = socket.gethostbyaddr(ip)
        field("Reverse DNS", name, C.GREEN)
    except: info("Aucun PTR.")

def m38_notes():
    """Bloc-notes d'investigation avec tags"""
    panel_header("M38 — BLOC-NOTES INVESTIGATION", "Persistance SQLite, tags, recherche")
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    print(f"  {C.CYAN}[1]{C.RESET} Ajouter note  {C.CYAN}[2]{C.RESET} Voir notes  {C.CYAN}[3]{C.RESET} Rechercher")
    mode = input(f"  {C.YELLOW}>{C.RESET} ").strip()
    
    if mode == "1":
        content = input(f"  {C.YELLOW}Contenu de la note >{C.RESET} ").strip()
        tag     = input(f"  {C.YELLOW}Tag (ex: suspect1, ip, mail…) >{C.RESET} ").strip()
        c.execute("INSERT INTO notes (date, content, tag) VALUES (?, ?, ?)",
                  (datetime.now().strftime("%Y-%m-%d %H:%M"), content, tag))
        conn.commit()
        ok("Note enregistrée.")
    elif mode == "2":
        c.execute("SELECT * FROM notes ORDER BY id DESC LIMIT 20")
        rows = c.fetchall()
        if not rows: info("Aucune note.")
        else:
            for r in rows:
                print(f"  {C.DIM}[{r[1]}]{C.RESET} {C.CYAN}[#{r[3]}]{C.RESET} {r[2]}")
    elif mode == "3":
        tag = input(f"  {C.YELLOW}Rechercher par tag >{C.RESET} ").strip()
        c.execute("SELECT * FROM notes WHERE tag LIKE ?", (f"%{tag}%",))
        rows = c.fetchall()
        for r in rows: print(f"  {C.DIM}[{r[1]}]{C.RESET} {r[2]}")
    conn.close()
    pause()

def m39_watchlist():
    """Watchlist de cibles à surveiller"""
    panel_header("M39 — WATCHLIST / CIBLES", "Ajout, gestion, scan groupé")
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    print(f"  {C.CYAN}[1]{C.RESET} Ajouter  {C.CYAN}[2]{C.RESET} Voir la liste  {C.CYAN}[3]{C.RESET} Scan GeoIP groupe  {C.CYAN}[4]{C.RESET} Supprimer")
    mode = input(f"  {C.YELLOW}>{C.RESET} ").strip()
    
    if mode == "1":
        target = input(f"  {C.YELLOW}Cible (IP/domaine/email/pseudo) >{C.RESET} ").strip()
        ttype  = input(f"  {C.YELLOW}Type (ip/domaine/email/pseudo) >{C.RESET} ").strip()
        c.execute("INSERT INTO watchlist (target, type, added) VALUES (?, ?, ?)",
                  (target, ttype, datetime.now().strftime("%Y-%m-%d")))
        conn.commit(); ok(f"{target} ajouté à la watchlist.")
    
    elif mode == "2":
        c.execute("SELECT * FROM watchlist ORDER BY id DESC")
        rows = c.fetchall()
        if not rows: info("Watchlist vide.")
        else:
            for r in rows:
                print(f"  {C.CYAN}[{r[0]}]{C.RESET} {C.YELLOW}{r[1]:<30}{C.RESET} {C.DIM}[{r[2]}]{C.RESET} ajouté le {r[3]}")
    
    elif mode == "3":
        c.execute("SELECT target FROM watchlist WHERE type='ip'")
        ips = [r[0] for r in c.fetchall()]
        if not ips: info("Aucune IP en watchlist.")
        else:
            for ip in ips:
                print(f"\n  {C.BOLD}→ GeoIP {ip}{C.RESET}")
                m02_geo(ip)
    
    elif mode == "4":
        wid = input(f"  {C.YELLOW}ID à supprimer >{C.RESET} ").strip()
        c.execute("DELETE FROM watchlist WHERE id=?", (wid,)); conn.commit()
        ok(f"Entrée {wid} supprimée.")
    
    conn.close()
    pause()

def m40_config():
    """Gestion des clés API"""
    panel_header("M40 — GESTION CLÉS API & CONFIG", "VirusTotal, Shodan, HIBP, AbuseIPDB")
    cfg = load_config()
    keys = cfg.setdefault("API_KEYS", {})
    
    api_info = {
        "VIRUSTOTAL": ("VirusTotal (m25)",   "https://www.virustotal.com/gui/my-apikey"),
        "SHODAN":     ("Shodan (m26)",        "https://account.shodan.io/"),
        "HIBP":       ("HaveIBeenPwned (m03b)","https://haveibeenpwned.com/API/Key"),
        "ABUSEIPDB":  ("AbuseIPDB (m32)",     "https://www.abuseipdb.com/account/api"),
        "HUNTER":     ("Hunter.io Email",     "https://hunter.io/api-keys"),
    }
    
    print(f"  {C.BOLD}{'Service':<28} {'Statut':<12} {'Obtenir la clé'}{C.RESET}")
    draw_sep()
    for key, (name, url) in api_info.items():
        val = keys.get(key, "")
        status = f"{C.GREEN}CONFIGURÉE{C.RESET}" if val else f"{C.RED}MANQUANTE{C.RESET}"
        masked = f"{'*' * (len(val)-4)}{val[-4:]}" if len(val) > 4 else ("N/A" if not val else val)
        print(f"  {name:<28} {status:<20} {C.DIM}{url}{C.RESET}")
        if val: print(f"  {' '*28} {C.DIM}Clé: {masked}{C.RESET}")
    
    print(f"\n  {C.CYAN}[1]{C.RESET} Modifier une clé  {C.CYAN}[2]{C.RESET} Retour")
    mode = input(f"  {C.YELLOW}>{C.RESET} ").strip()
    if mode == "1":
        key_name = input(f"  {C.YELLOW}Nom de la clé (VIRUSTOTAL/SHODAN/HIBP/ABUSEIPDB/HUNTER) >{C.RESET} ").strip().upper()
        if key_name in api_info:
            new_key = input(f"  {C.YELLOW}Nouvelle clé >{C.RESET} ").strip()
            keys[key_name] = new_key
            save_config(cfg)
            ok(f"Clé {key_name} mise à jour.")
        else: err("Nom de clé inconnu.")
    pause()

# ──────────────────────────────────────────────────────────
#  INTERFACE HUB
# ──────────────────────────────────────────────────────────
def menu():
    clr()
    print(BANNER)
    print(f"{C.BLUE}{B_TL}{B_H * (WIDTH-2)}{B_TR}{C.RESET}")
    print(f"{C.BLUE}{B_V}{C.RESET}  {C.BOLD}{C.WHITE}1NTERPOL MATRIX RADAR — 40 MODULES D'INVESTIGATION OSINT{C.RESET}{' ' * 8}{C.BLUE}{B_V}{C.RESET}")
    print(f"{C.BLUE}{B_ML}{B_H * (WIDTH-2)}{B_MR}{C.RESET}")
    
    opts = [
        ("01","Recherche Pseudo",      "21","En-têtes HTTP Sécu"),
        ("02","GeoIP Avancé",          "22","Validateur RegEx+"),
        ("03","DataBreaches Global",   "23","Latence Multi-Ping"),
        ("03B","Email HIBP Check",     "24","Détecteur CMS+"),
        ("04","Métadonnées+Entropie",  "25","VirusTotal API"),
        ("05","GitHub Profilage+",     "26","Shodan API"),
        ("06","DNS Complet+Subdomain", "27","Historique SQLite"),
        ("07","Email OSINT+Perms",     "28","SSL/TLS Analyse"),
        ("08","Pivot Téléphonique+",   "29","WHOIS / RDAP"),
        ("09","Instagram Anonyme",     "30","Pastes Exposés"),
        ("10","Google Dorks (15)",     "31","Wayback Machine"),
        ("11","Rapport HTML+JSON",     "32","AbuseIPDB (API)"),
        ("12","Scanner Ports 50+",     "33","Crypto Wallets"),
        ("13","MAC Lookup+",           "34","Dark Web Check"),
        ("14","Discord Snowflake+",    "35","CVE / NVD NIST"),
        ("15","Reverse DNS",           "36","Profil OSINT Full"),
        ("16","Trackers+Technologies", "37","FULL AUTO SCAN ★"),
        ("17","Hash+Base64+ROT13",     "38","Bloc-Notes OSINT"),
        ("18","Extracteur Liens+",     "39","Watchlist Cibles"),
        ("19","User-Agent Analyzer+",  "40","Config Clés API"),
        ("20","Subnet Calculator+",    "00","QUITTER L'OUTIL"),
    ]
    
    for n1, d1, n2, d2 in opts:
        sp1 = f" {C.CYAN}[{n1:>3}]{C.RESET} {C.WHITE}{d1:<22}{C.RESET}"
        is_exit  = n2 == "00"
        is_star  = "★" in d2
        c2_color = C.RED if is_exit else (C.ORANGE if is_star else C.CYAN)
        sp2 = f" {c2_color}[{n2:>3}]{C.RESET} {C.WHITE if not is_exit else C.RED}{C.BOLD if is_exit or is_star else ''}{d2:<24}{C.RESET}"
        
        comb = f" {sp1} {C.DIM}│{C.RESET} {sp2}"
        reg_len = len(re.sub(r'\033\[[0-9;]*m', '', comb))
        print(f"{C.BLUE}{B_V}{C.RESET}{comb}{' ' * max(0, WIDTH - reg_len - 2)}{C.BLUE}{B_V}{C.RESET}")
    
    print(f"{C.BLUE}{B_BL}{B_H * (WIDTH-2)}{B_BR}{C.RESET}")
    
    # Statut API keys
    cfg = load_config()
    keys = cfg.get("API_KEYS", {})
    active = sum(1 for v in keys.values() if v)
    total_keys = len(keys)
    kcolor = C.GREEN if active == total_keys else (C.YELLOW if active > 0 else C.RED)
    print(f"  {C.DIM}Clés API : {kcolor}{active}/{total_keys} configurées{C.RESET}  {C.DIM}Base de données : {DB_FILE}{C.RESET}")
    
    return input(f"\n  {C.BOLD}{C.BLUE}┌───({C.CYAN}operator@1nterpol{C.BLUE})─[{C.WHITE}🛰️  v6.0{C.BLUE}]\n  └─{C.YELLOW}$ Module >{C.RESET} ").strip()

def main():
    if os.name == 'nt': os.system('color')
    init_system()
    webbrowser.open_new_tab("https://discord.gg/jVRFMd2NJy")
    
    parser = argparse.ArgumentParser(description="1NTERPOL OSINT v6.0 — CLI Mode")
    parser.add_argument("-t", "--target", help="Cible IP/domaine")
    parser.add_argument("-m", "--module", help="Module: geo|ports|vt|shodan|ssl|whois|full")
    args = parser.parse_args()
    
    if args.target and args.module:
        dispatch = {
            "geo":    lambda: m02_geo(args.target),
            "ports":  lambda: m12_ports(args.target),
            "vt":     lambda: m25_vt(args.target),
            "shodan": lambda: m26_shodan(args.target),
            "full":   lambda: m37_fullscan(),
        }
        if args.module in dispatch: dispatch[args.module]()
        else: err(f"Module CLI inconnu : {args.module}")
        sys.exit(0)
    
    funcs = {
        "1":m01_username, "01":m01_username,
        "2":m02_geo, "02":m02_geo,
        "3":m03_leaks, "03":m03_leaks,
        "3b":m03b_email_pwned, "03b":m03b_email_pwned,
        "4":m04_metadata, "04":m04_metadata,
        "5":m05_github, "05":m05_github,
        "6":m06_dns, "06":m06_dns,
        "7":m07_email, "07":m07_email,
        "8":m08_phone, "08":m08_phone,
        "9":m09_insta, "09":m09_insta,
        "10":m10_dorks, "11":m11_report,
        "12":m12_ports, "13":m13_mac,
        "14":m14_discord, "15":m15_revdns,
        "16":m16_trackers, "17":m17_hash,
        "18":m18_links, "19":m19_ua,
        "20":m20_subnet, "21":m21_headers,
        "22":m22_regex, "23":m23_ping,
        "24":m24_cms, "25":m25_vt,
        "26":m26_shodan, "27":m27_db,
        "28":m28_ssl, "29":m29_whois,
        "30":m30_pastebin, "31":m31_wayback,
        "32":m32_abuseipdb, "33":m33_bitcoin,
        "34":m34_darkweb, "35":m35_cve,
        "36":m36_social_links, "37":m37_fullscan,
        "38":m38_notes, "39":m39_watchlist,
        "40":m40_config,
    }
    
    while True:
        cmd = menu().lower()
        if cmd in ("0", "00"):
            print(f"\n  {C.DIM}Session terminée. Données sauvegardées dans {DB_FILE}{C.RESET}\n")
            sys.exit(0)
        elif cmd in funcs:
            funcs[cmd]()
        else:
            warn(f"Module '{cmd}' inconnu. Entrez un numéro valide.")
            time.sleep(1)

if __name__ == "__main__":
    try: main()
    except KeyboardInterrupt:
        print(f"\n  {C.DIM}Interruption. Au revoir.{C.RESET}")
        sys.exit(0)