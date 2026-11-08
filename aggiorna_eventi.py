#!/usr/bin/env python3
# aggiorna_eventi.py v1.3 (link diretti alle pagine degli spettacoli + locandine) - Legge i siti dei teatri e aggiorna events-data.json (solo libreria standard Python)
# Regola di sicurezza: se un sito cambia e il programma legge troppo poco, i dati vecchi di quel teatro restano.
import os, unicodedata, json, re, sys, subprocess, tempfile, collections, datetime as dt, urllib.request, urllib.parse
from html.parser import HTMLParser

FILE = "events-data.json"
UA = {"User-Agent": "Mozilla/5.0 (compatible; GenovaStageBot/1.0)"}
TODAY = dt.date.today()
MESI = ["gennaio","febbraio","marzo","aprile","maggio","giugno","luglio","agosto","settembre","ottobre","novembre","dicembre"]
MN = [m.capitalize() for m in MESI]

def mese(w):
    w = (w or "").lower().strip(".")
    for i, m in enumerate(MESI, 1):
        if w == m or (len(w) == 3 and m.startswith(w)): return i
    return None

def data_vicina(g, m):
    """Anno giusto: la prima data che cade da 60 giorni fa in avanti (le stagioni teatrali scavalcano l'anno)."""
    for y in (TODAY.year - 1, TODAY.year, TODAY.year + 1):
        try: d = dt.date(y, m, g)
        except ValueError: continue
        if d >= TODAY - dt.timedelta(days=60): return d
    return None

def fmt(s, e):
    a, b = dt.date.fromisoformat(s), dt.date.fromisoformat(e)
    if a == b: return f"{a.day} {MN[a.month-1]} {a.year}"
    if (a.year, a.month) == (b.year, b.month): return f"{a.day} - {b.day} {MN[a.month-1]} {a.year}"
    if a.year == b.year: return f"{a.day} {MN[a.month-1]} - {b.day} {MN[b.month-1]} {a.year}"
    return f"{a.day} {MN[a.month-1]} {a.year} - {b.day} {MN[b.month-1]} {b.year}"

R_RANGE = re.compile(r"^(?:dall?[’']?\s*)?(\d{1,2})\s*(?:([a-zà]+)\s*)?(?:-|–|al)\s*(\d{1,2})\s*([a-zà]+)(?:\s+(\d{4}))?$", re.I)
R_SINGLE = re.compile(r"^(?:dall?[’']?\s*)?(\d{1,2})\s*([a-zà]+)(?:\s+(\d{4}))?$", re.I)

def parse_date(txt):
    """'dal 6 al 18 ottobre', '4-5 novembre', '29 Dicembre - 06 Gennaio', '22 ottobre 2026' -> (inizio, fine) ISO"""
    t = re.sub(r"\s+", " ", txt.strip().strip(":,;"))
    m = R_RANGE.match(t)
    if m:
        g1, m1, g2, m2, y = m.groups(); mm2 = mese(m2); mm1 = mese(m1) if m1 else mm2
        if not mm2 or not mm1: return None
        a = dt.date(int(y), mm1, int(g1)) if y else data_vicina(int(g1), mm1)
        if not a: return None
        try: b = dt.date(a.year, mm2, int(g2))
        except ValueError: return None
        if b < a: b = b.replace(year=b.year + 1)
        return a.isoformat(), b.isoformat()
    m = R_SINGLE.match(t)
    if m:
        g, mo, y = m.groups(); mm = mese(mo)
        if not mm: return None
        a = dt.date(int(y), mm, int(g)) if y else data_vicina(int(g), mm)
        return (a.isoformat(),) * 2 if a else None
    return None

class Righe(HTMLParser):
    """Testo visibile, una riga per ogni elemento HTML."""
    def __init__(self): super().__init__(); self.out = []; self.skip = 0
    def handle_starttag(self, t, a):
        if t in ("script", "style"): self.skip += 1
        self.out.append("\n")
    def handle_endtag(self, t):
        if t in ("script", "style"): self.skip = max(0, self.skip - 1)
        self.out.append("\n")
    def handle_data(self, d):
        if not self.skip: self.out.append(d)

def righe(html):
    p = Righe(); p.feed(html)
    return [re.sub(r"\s+", " ", l).strip() for l in "".join(p.out).split("\n") if l.strip()]

class Link(HTMLParser):
    def __init__(self): super().__init__(); self.cur = None; self.out = []
    def handle_starttag(self, t, a):
        if t == "a": self.cur = [dict(a).get("href", ""), []]
    def handle_data(self, d):
        if self.cur is not None: self.cur[1].append(d)
    def handle_endtag(self, t):
        if t == "a" and self.cur:
            self.out.append((self.cur[0], re.sub(r"\s+", " ", " ".join(self.cur[1])).strip())); self.cur = None

def links(html):
    p = Link(); p.feed(html); return p.out

def ev(a, t, v, u, s, e, c, k, p="", src=""):
    return {"a": a, "t": t, "v": v, "u": u, "s": s, "e": e or s, "c": "concerto" if c == "c" else "teatro", "k": k, "p": p, "d": fmt(s, e or s), "src": src, "img": ""}

def bel(t):  # TITOLO IN MAIUSCOLO -> Titolo
    pic = {"di", "e", "i", "il", "la", "le", "dei", "del", "in", "a", "da", "ed"}
    return " ".join(w if (i and w in pic) else w.capitalize() for i, w in enumerate(t.lower().split()))

# ---------- Teatro Nazionale ----------
SALE = ["Teatro Eleonora Duse", "Teatro Gustavo Modena", "Sala Mercato", "Teatro Ivo Chiesa", "Foyer Teatro Gustavo Modena", "Foyer Teatro Ivo Chiesa", "Foyer Teatro Eleonora Duse", "Semplicemente Parco - Pegli"]
R_NAZ = re.compile(r"^(.*?)\s+(\d{1,2}(?:\s+[A-Za-zà]+)?(?:\s*-\s*\d{1,2}\s+[A-Za-zà]+)?)$")

def parse_nazionale(html, base="https://www.teatronazionalegenova.it"):
    out = []
    for href, txt in links(html):
        if "/eventi/" not in href: continue
        sala = next((s for s in sorted(SALE, key=len, reverse=True) if txt.endswith(s)), None)
        if not sala: continue
        m = R_NAZ.match(txt[: -len(sala)].strip())
        if not m: continue
        d = parse_date(m.group(2))
        if not d: continue
        titolo = m.group(1).strip()
        musica = bool(re.search(r"big band|acoustic night|jazz|concerto", titolo, re.I))
        out.append(ev(titolo, sala, "Teatro Nazionale di Genova", href if href.startswith("http") else base + href, d[0], d[1], "c" if musica else "t", "Concerto" if musica else "Teatro", src="nazionale"))
    return out

# ---------- Teatro Carlo Felice ----------
R_FIN = re.compile(r"^(.*\S)\s+((?:dall?[’']?\s*\d.*|\d{1,2}\s+[A-Za-zà]+\s+\d{4}))$", re.I)

def tipo_cf(t):
    l = t.lower()
    if re.search(r"schiaccianoci|giselle|lago dei cigni|dance|bernal|ballet", l): return "t", "Danza"
    if re.search(r"phantom|musical", l): return "t", "Musical"
    if t.isupper() and not re.search(r"deledda|requiem", l): return "t", "Opera"
    return "c", "Concerto"

def parse_carlofelice(lines):
    out, prev, used = [], None, True
    for l in lines:
        d = parse_date(l) if re.match(r"^(dall?[’']?\s*)?\d", l, re.I) else None
        titolo = None
        if d:
            if prev and not used: titolo = prev
        else:
            m = R_FIN.match(l)
            if m and parse_date(m.group(2)): d, titolo = parse_date(m.group(2)), m.group(1)
        if d and titolo:
            c, k = tipo_cf(titolo)
            out.append(ev(bel(titolo) if titolo.isupper() else titolo, "", "Teatro Carlo Felice", "https://www.carlofelice.it", d[0], d[1], c, k, src="carlofelice")); used = True
        elif d: used = True   # data senza titolo: non indovino
        else: prev, used = l, False
    return out

R_GOG = re.compile(r"^(.+?)\s+Teatro Carlo Felice\s+[A-Za-zì]+\s+(\d{1,2})\s+([A-Za-zà]+)$")
R_GOG2 = re.compile(r"^Teatro Carlo Felice\s+[A-Za-zì]+\s+(\d{1,2})\s+([A-Za-zà]+)$")

def parse_gog(lines):
    out, prev = [], None
    for l in lines:
        m = R_GOG.match(l); g = None
        if m: nome, g, mo = m.groups()
        else:
            m2 = R_GOG2.match(l)
            if m2 and prev: nome, (g, mo) = prev, m2.groups()
        if g and mese(mo):
            d = data_vicina(int(g), mese(mo)).isoformat()
            out.append(ev(nome, "Stagione GOG", "Teatro Carlo Felice", "https://www.gog.it", d, d, "c", "Concerto", src="gog"))
        prev = l
    return out

# ---------- Teatro della Tosse (solo prossimi eventi in home: unione, non sostituzione) ----------
R_TOSSE = re.compile(r"^([A-Za-zà]{3})\s+(\d{1,2})(?:\s*-\s*(?:([A-Za-zà]{3})\s+)?(\d{1,2}))?\b")

def parse_tosse(html, base="https://teatrodellatosse.it"):
    out = []
    for href, txt in links(html):
        if "/eventi/" not in href: continue
        m = R_TOSSE.match(txt)
        if not m or not mese(m.group(1)): continue
        m1, g1, m2, g2 = m.groups(); a = data_vicina(int(g1), mese(m1))
        try: b = dt.date(a.year, mese(m2) if m2 else a.month, int(g2)) if g2 else a
        except ValueError: continue
        out.append({"url": href if href.startswith("http") else base + href, "s": a.isoformat(), "e": b.isoformat()})
    return out

# ---------- Politeama Genovese (PDF ufficiale della stagione) ----------
R_B = re.compile(r"^(?:dal\s+)?(\d{1,2})(?:\s*(?:-|al)\s*(\d{1,2}))?\s*([A-Za-zà]+)\s+(.+)$", re.I)
MUSICA = re.compile(r"choir|gospel|orchestra|tribute|capossela|ranieri|arisa|concato|allevi|giordana angi|dire straits|pink floyd|battiato|elio|genesis", re.I)

def norm(s): return re.sub(r"[^a-z0-9àèéìòù ]", "", s.lower()).strip()

def evp(nome, sub, s, e, prezzi):
    c = "c" if MUSICA.search(nome + " " + sub) else "t"
    p = ""
    for pt, pr in prezzi:
        if norm(nome).startswith(pt) or norm(nome + " " + sub).startswith(pt): p = pr; break
    return ev(nome, sub, "Politeama Genovese", "https://www.politeamagenovese.it", s, e, c, "Concerto" if c == "c" else "Spettacolo", p, "politeama")

def titolo_pol(tit):
    tit = re.sub(r"^TKC\s*-\s*", "", tit.strip())
    p = re.split(r"\s[-–]\s", tit, maxsplit=1)
    return (p[0].strip(), p[1].strip() if len(p) > 1 else "")

def parse_politeama(testo):
    L = [l.strip() for l in testo.splitlines()]
    fc = next((i for i, l in enumerate(L) if l.lower().startswith("fuori carnet")), None)
    pi = next((i for i, l in enumerate(L) if l.upper().startswith("PREZZI BIGLIETTI")), None)
    if fc is None or pi is None: return []
    prezzi = []
    for l in L[pi:]:
        m = re.match(r"^(.+?)\s+€\s*(\d[\d,\./ ]*)$", l)
        if m and re.fullmatch(r"[\d,/ ]+", m.group(2).strip()): prezzi.append((norm(m.group(1)), m.group(2).strip().replace(" ", "")))
    out = []
    i = 0
    while i < fc - 1:           # programma principale: riga data + riga titolo
        parti = re.sub(r"\(fuori carnet\)", "", L[i], flags=re.I).split(" e ")
        ds = [parse_date(p) for p in parti]
        if L[i] and all(ds) and L[i+1]:
            nome, sub = titolo_pol(L[i+1])
            for d in ds: out.append(evp(nome, sub, d[0], d[1], prezzi))
            i += 2
        else: i += 1
    for l in L[fc + 1:pi]:      # fuori carnet: una riga per evento
        if l.lower().startswith("carnet"): break
        m = R_B.match(l)
        if m and mese(m.group(3)):
            g1, g2, mo, tit = m.groups()
            d = parse_date(f"{g1}-{g2} {mo}" if g2 else f"{g1} {mo}")
            if d:
                nome, sub = titolo_pol(tit); out.append(evp(nome, sub, d[0], d[1], prezzi))
    visti, uniq = set(), []
    for e in out:
        k = (e["a"], e["s"])
        if k not in visti: visti.add(k); uniq.append(e)
    return uniq

# ---------- rete ----------
def get(url, binario=False):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=40) as r:
        b = r.read()
    return b if binario else b.decode("utf-8", "replace")

def src_nazionale(): return parse_nazionale(get("https://www.teatronazionalegenova.it/rassegne/cartellone-2026-27.htm"))
def src_carlofelice(): return parse_carlofelice(righe(get("https://www.carlofelice.it/")))
def src_gog(): return parse_gog(righe(get("https://www.gog.it/rassegne/430-stagione-gog-2026-2027.htm")))

def src_tosse():
    out = []
    for it in parse_tosse(get("https://teatrodellatosse.it/")):
        try:
            m = re.search(r"<title>(.*?)</title>", get(it["url"]), re.S | re.I)
            titolo = re.sub(r"\s*[-|–]\s*Teatro della Tosse.*$", "", re.sub(r"\s+", " ", m.group(1)).strip()) if m else ""
        except Exception: continue
        if titolo: out.append(ev(titolo, "", "Teatro della Tosse", it["url"], it["s"], it["e"], "t", "Teatro", src="tosse"))
    return out

def src_politeama():
    pdf = None
    for pag in ("https://www.politeamagenovese.it/carnet-2026-2027/", "https://www.politeamagenovese.it/stagione/"):
        try:
            m = re.findall(r'href="([^"]*Programma-Stagione[^"]*\.pdf)"', get(pag))
            if m: pdf = m[-1]; break
        except Exception: pass
    if not pdf: raise RuntimeError("PDF stagione non trovato")
    with tempfile.NamedTemporaryFile(suffix=".pdf") as f:
        f.write(get(pdf, True)); f.flush()
        testo = subprocess.run(["pdftotext", f.name, "-"], capture_output=True, text=True, check=True).stdout
    return parse_politeama(testo)

# modo: "sostituisci" = elenco completo del sito; "unisci" = il sito mostra solo i prossimi eventi
FONTI = [("politeama", src_politeama, "sostituisci"), ("nazionale", src_nazionale, "sostituisci"),
         ("carlofelice", src_carlofelice, "sostituisci"), ("gog", src_gog, "sostituisci"), ("tosse", src_tosse, "unisci")]

def og_image(html, url):
    """Immagine di anteprima (og:image) che il teatro stesso indica per lo spettacolo."""
    for m in re.finditer(r"<meta\b[^>]*>", html, re.I):
        if re.search(r'(?:property|name)=["\']og:image["\']', m.group(0), re.I):
            c = re.search(r'content=["\']([^"\']+)["\']', m.group(0), re.I)
            if c: return urllib.parse.urljoin(url, c.group(1).replace("&amp;", "&"))
    return ""

def slug(nome):
    n = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", n).strip("-")

def locandine(ev_all, prev, rete=True):
    vecchie = {(e["a"], e["s"]): e["img"] for e in prev if e.get("img")}
    for e in ev_all:
        if not e.get("img"): e["img"] = vecchie.get((e["a"], e["s"]), "")
    if rete:
        n = 0
        for e in ev_all:
            if e["src"] in ("nazionale", "tosse") and not e["img"] and e["u"].startswith("http") and e["u"].count("/") > 3 and n < 150:
                n += 1
                try: e["img"] = og_image(get(e["u"]), e["u"])
                except Exception: pass
    cont = collections.Counter(e["img"] for e in ev_all if e["img"])
    for e in ev_all:                      # stessa immagine su piu' di 3 eventi = logo generico, la scarto
        if e["img"] and cont[e["img"]] > 3: e["img"] = ""
    for e in ev_all:                      # file caricati nella cartella locandine/ (nome = nome evento con i trattini)
        for ext in ("jpg", "jpeg", "png", "webp"):
            f = f"locandine/{slug(e['a'])}.{ext}"
            if os.path.exists(f): e["img"] = f; break
    try: man = json.load(open("locandine.json", encoding="utf-8"))
    except Exception: man = {}
    for e in ev_all:                      # locandine scritte a mano: vincono sempre
        if isinstance(man.get(e["a"]), str) and man[e["a"]].startswith(("http", "locandine/")): e["img"] = man[e["a"]]
    print("Locandine presenti:", sum(1 for e in ev_all if e["img"]), "su", len(ev_all))

PAGINE = {"politeama": ["https://www.politeamagenovese.it/", "https://www.politeamagenovese.it/carnet-2026-2027/"],
          "carlofelice": ["https://www.carlofelice.it/"], "gog": ["https://www.gog.it/rassegne/430-stagione-gog-2026-2027.htm"]}
GENERICI = {"politeama": "https://www.politeamagenovese.it", "carlofelice": "https://www.carlofelice.it", "gog": "https://www.gog.it"}

def link_spettacoli(ev_all, prev, rete=True):
    """Sostituisce il link generico del teatro con la pagina dello spettacolo, se la trova nel sito del teatro."""
    vecchi = {(e["a"], e["s"]): e["u"] for e in prev}
    ancore = {}
    if rete:
        for src, pagine in PAGINE.items():
            for pg in pagine:
                try: html = get(pg)
                except Exception: continue
                for h, t in links(html): ancore.setdefault(src, []).append((urllib.parse.urljoin(pg, h), norm(t), pg))
    for e in ev_all:
        gen = GENERICI.get(e["src"])
        if not gen or e["u"].rstrip("/") != gen: continue
        old = vecchi.get((e["a"], e["s"]), "")
        if old and old.rstrip("/") != gen: e["u"] = old; continue
        n = norm(e["a"])
        if len(n) < 4: continue
        for h, t, pg in ancore.get(e["src"], []):
            u, b = urllib.parse.urlparse(h), urllib.parse.urlparse(pg)
            if n in t and u.netloc == b.netloc and u.path.strip("/") and h.rstrip("/") != pg.rstrip("/") and "#" not in h:
                e["u"] = h; break
    print("Link diretti agli spettacoli:", sum(1 for e in ev_all if e["src"] in GENERICI and e["u"].rstrip("/") != GENERICI[e["src"]]), "su", sum(1 for e in ev_all if e["src"] in GENERICI))

def indovina_src(e):
    if e.get("src"): return e["src"]
    if e["v"] == "Politeama Genovese": return "politeama"
    if e["v"] == "Teatro Carlo Felice": return "gog" if e.get("t") == "Stagione GOG" else "carlofelice"
    if e["v"] == "Teatro Nazionale di Genova" and e["a"] not in ("Peppe Iodice", "Back to Hawkins"): return "nazionale"
    if e["v"] == "Teatro della Tosse": return "tosse"
    return "manuale"

def main():
    solo_norm = "--solo-normalizza" in sys.argv
    try: j = json.load(open(FILE, encoding="utf-8"))
    except Exception: j = {"events": []}
    prev = j["events"] if isinstance(j, dict) else j
    for e in prev: e["src"] = indovina_src(e)
    oggi = TODAY.isoformat()
    fonti, falliti = j.get("fonti", {}) if isinstance(j, dict) else {}, []
    ev_all = list(prev)
    if not solo_norm:
        for nome, fn, modo in FONTI:
            vecchi = [e for e in ev_all if e["src"] == nome]
            try: nuovi = fn()
            except Exception as x: nuovi = None; print(f"[{nome}] ERRORE: {x}")
            futuri = [e for e in vecchi if e["e"] >= oggi]
            if not nuovi: falliti.append(nome); print(f"[{nome}] nessun dato: tengo i vecchi ({len(vecchi)})"); continue
            if modo == "sostituisci" and len(nuovi) < 0.6 * len(futuri):
                falliti.append(nome); print(f"[{nome}] troppo pochi ({len(nuovi)} contro {len(futuri)}): tengo i vecchi"); continue
            if modo == "sostituisci": ev_all = [e for e in ev_all if e["src"] != nome] + nuovi
            else:
                chiavi = {(e["a"], e["s"]) for e in nuovi}
                ev_all = [e for e in ev_all if not (e["src"] == nome and (e["a"], e["s"]) in chiavi)] + nuovi
            fonti[nome] = {"ok": True, "n": len(nuovi), "data": oggi}; print(f"[{nome}] ok: {len(nuovi)} eventi")
    locandine(ev_all, prev, rete=not solo_norm)
    link_spettacoli(ev_all, prev, rete=not solo_norm)
    limite = (TODAY - dt.timedelta(days=2)).isoformat()
    ev_all = sorted([e for e in ev_all if e["e"] >= limite], key=lambda e: (e["s"], e["a"]))
    agg = j.get("updated", oggi) if isinstance(j, dict) else oggi
    if not solo_norm and not falliti: agg = oggi
    json.dump({"updated": agg, "version": "auto", "fonti": fonti, "events": ev_all}, open(FILE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"Totale {len(ev_all)} eventi. Fonti con problemi: {falliti or 'nessuna'}")

if __name__ == "__main__": main()
