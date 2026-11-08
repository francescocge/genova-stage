import aggiorna_eventi as A, datetime as dt
A.TODAY = dt.date(2026, 11, 7)
# date
assert A.parse_date("dal 6 al 18 ottobre") == ("2026-10-06","2026-10-18")
assert A.parse_date("4-5 novembre") == ("2026-11-04","2026-11-05")
assert A.parse_date("29 Dicembre - 06 Gennaio") == ("2026-12-29","2027-01-06")
assert A.parse_date("03 - 08 Novembre") == ("2026-11-03","2026-11-08")
assert A.parse_date("Dall’11 al 13 dicembre 2026") == ("2026-12-11","2026-12-13")
assert A.parse_date("22 ottobre 2026") == ("2026-10-22","2026-10-22")
assert A.parse_date("13 febbraio") == ("2027-02-13","2027-02-13")
# Nazionale
h = '''<a href="/eventi/2026-2027/starman.htm"><span>Starman</span> <span>10 - 15 Novembre</span> <span>Teatro Gustavo Modena</span></a>
<a href="/eventi/2026-2027/x.htm">Le Dieu du carnage 30 Dicembre - 06 Gennaio Teatro Eleonora Duse</a>
<a href="/eventi/2026-2027/y.htm">Acoustic Night 27 20 - 22 Maggio Teatro Ivo Chiesa</a>
<a href="/eventi/2026-2027/z.htm">M/T Moby Prince 3.0 02 - 03 Marzo Sala Mercato</a>
<a href="/eventi/2026-2027/w.htm">Crave 26 Novembre Sala Mercato</a><a href="/altro.htm">Contatti</a>'''
n = A.parse_nazionale(h); r = {e["a"]: e for e in n}
assert len(n) == 5, n
assert r["Starman"]["s"] == "2026-11-10" and r["Starman"]["t"] == "Teatro Gustavo Modena"
assert r["Le Dieu du carnage"]["e"] == "2027-01-06"
assert r["Acoustic Night 27"]["c"] == "concerto" and r["Acoustic Night 27"]["s"] == "2027-05-20"
assert r["M/T Moby Prince 3.0"]["e"] == "2027-03-03" and r["Crave"]["s"] == "2026-11-26"
# Carlo Felice (titolo+data in righe separate, titolo senza data, data senza titolo)
cf = A.righe('<div><h3>I CAPULETI E I MONTECCHI</h3><p>Dal 20 al 27 novembre 2026</p></div><div><p>22 ottobre 2026</p></div><div><h3>LO SCHIACCIANOCI</h3><p>Dal 3 al 6 dicembre 2026</p></div><div><h3>Merry christmas</h3><p>20 dicembre 2026</p></div><div>Gran Concerto di capodanno 1 gennaio 2027</div>')
c = {e["a"]: e for e in A.parse_carlofelice(cf)}
assert set(c) == {"I Capuleti e i Montecchi","Lo Schiaccianoci","Merry christmas","Gran Concerto di capodanno"}, set(c)
assert c["Lo Schiaccianoci"]["k"] == "Danza" and c["I Capuleti e i Montecchi"]["k"] == "Opera" and c["Merry christmas"]["c"] == "concerto"
assert c["I Capuleti e i Montecchi"]["e"] == "2026-11-27" and c["Gran Concerto di capodanno"]["s"] == "2027-01-01"
# GOG
g = A.parse_gog(["Wanderer Trio Teatro Carlo Felice Lunedì 16 novembre", "Lucas Debargue", "Teatro Carlo Felice Lunedì 30 novembre"])
assert [(e["a"], e["s"]) for e in g] == [("Wanderer Trio","2026-11-16"),("Lucas Debargue","2026-11-30")], g
# Tosse
t = A.parse_tosse('<a href="/eventi/il-donatore-stag.htm">Nov 03 - 08 sala Dino Campana Il donatore Cosa significa</a><a href="/eventi/aljazzeera.htm">Nov 07 La Claque AlJazzeera</a><a href="/eventi/x.htm">Nov 30 - Dic 02 Prova</a>')
assert [(x["s"], x["e"]) for x in t] == [("2026-11-03","2026-11-08"),("2026-11-07","2026-11-07"),("2026-11-30","2026-12-02")], t
# Politeama (testo del PDF ufficiale, estratto)
pdf = """1-2 ottobre
Cavalli Marci - Campa Cavallo
con Alessandro Bianchi, Carlo Denei
dal 6 al 18 ottobre
TKC - Rumors
di Neil Simon, regia Massimo Chiesa
Dal 27 al 29 novembre
Pirati dei Caruggi - Sert du Soleil
Risate scorrette.
31 dicembre (fuori carnet) e dal 2 al 5 gennaio
Maurizio Lastrico
Maurizio Lastrico torna come ogni anno.
3 marzo
Gioele Dix - Arrivato a questo punto
Una dichiarazione d’amore al teatro.
Fuori carnet 
21 ottobre Hans Zimmer Tribute by Ensemble Symphony Orchestra
dal 22 ottobre Angelo Pintus - Loro non sanno niente
31 dicembre Maurizio Lastrico 
5-6 marzo Pink Floyd Legend - The Dark Side of the Moon
5 Aprile Eleazaro Rossi - Kamikaze
21-22 aprile Angelo Duro - Chiedo scusa a tutti
11maggio Dire Straits Reload
Carnet
8 o più spettacoli a scelta
PREZZI BIGLIETTI:
Cavalli Marci € 46/40/34,50
Rumors martedì, mercoledì e giovedì € 26 – venerdì, sabato e domenica € 30
Pirati dei Caruggi € 37/31
Gioele Dix € 34,50/29
FUORI STAGIONE:
Pink Floyd Legend € 50/42/35
Angelo Duro € 55/45/40
Dire Straits Reload € 49/44/38
"""
p = A.parse_politeama(pdf); q = {(e["a"], e["s"]): e for e in p}
assert ("Cavalli Marci","2026-10-01") in q and q[("Cavalli Marci","2026-10-01")]["p"] == "46/40/34,50" and q[("Cavalli Marci","2026-10-01")]["e"] == "2026-10-02"
assert ("Rumors","2026-10-06") in q and q[("Rumors","2026-10-06")]["p"] == ""
assert q[("Pirati dei Caruggi","2026-11-27")]["t"] == "Sert du Soleil" and q[("Pirati dei Caruggi","2026-11-27")]["e"] == "2026-11-29"
assert ("Maurizio Lastrico","2026-12-31") in q and q[("Maurizio Lastrico","2027-01-02")]["e"] == "2027-01-05"
assert len([k for k in q if k[0] == "Maurizio Lastrico"]) == 2          # nessun doppione
assert q[("Pink Floyd Legend","2027-03-05")]["c"] == "concerto" and q[("Pink Floyd Legend","2027-03-05")]["p"] == "50/42/35"
assert q[("Angelo Duro","2027-04-21")]["e"] == "2027-04-22" and q[("Dire Straits Reload","2027-05-11")]["p"] == "49/44/38"
assert q[("Eleazaro Rossi","2027-04-05")]["t"] == "Kamikaze"
# Locandine
assert A.og_image('<meta property="og:image" content="/img/a.jpg?x=1&amp;y=2">', "https://t.it/eventi/a.htm") == "https://t.it/img/a.jpg?x=1&y=2"
assert A.og_image('<meta content="https://t.it/b.jpg" property="og:image" />', "https://t.it/") == "https://t.it/b.jpg"
assert A.og_image('<meta name="description" content="x">', "https://t.it/") == ""
import os, tempfile, json
os.chdir(tempfile.mkdtemp())
json.dump({"Manuale": "https://x.it/m.jpg", "Rotto": "non-un-link"}, open("locandine.json", "w"))
pagine = {"https://t.it/eventi/a.htm": '<meta property="og:image" content="/a.jpg">'}
A.get = lambda u, b=False: pagine.get(u) if u in pagine else '<meta property="og:image" content="/logo.png">'
E = [A.ev("A","","V","https://t.it/eventi/a.htm","2026-12-01","2026-12-01","t","T",src="nazionale")]
E += [A.ev(f"G{i}","","V",f"https://t.it/eventi/g{i}.htm","2026-12-0%d"%(i+2),"2026-12-0%d"%(i+2),"t","T",src="nazionale") for i in range(5)]
E += [A.ev("Manuale","","V","","2026-12-09","2026-12-09","t","T",src="manuale"), A.ev("Rotto","","V","","2026-12-10","2026-12-10","t","T",src="manuale")]
A.locandine(E, [])
im = {e["a"]: e["img"] for e in E}
assert im["A"] == "https://t.it/a.jpg" and im["G0"] == "" and im["Manuale"] == "https://x.it/m.jpg" and im["Rotto"] == ""
assert A.slug("Günther Groissböck e Julius Drake") == "gunther-groissbock-e-julius-drake" and A.slug("Fratello Sole, Sorella Luna") == "fratello-sole-sorella-luna"
os.makedirs("locandine"); open("locandine/arisa.png", "w").write("x")
E2 = [A.ev("Arisa","","V","","2026-12-09","2026-12-09","c","C",src="manuale"), A.ev("Altro","","V","","2026-12-10","2026-12-10","c","C",src="manuale")]
A.locandine(E2, [], rete=False)
assert E2[0]["img"] == "locandine/arisa.png" and E2[1]["img"] == ""
pag = {"https://www.politeamagenovese.it/": '<a href="/spettacolo/arisa/">Arisa Live Tour</a><a href="/contatti/">Contatti</a><a href="/">Home</a>'}
A.get = lambda u, b=False: pag.get(u, "")
E3 = [A.ev("Arisa","Live Tour","Politeama Genovese","https://www.politeamagenovese.it","2026-12-09","2026-12-09","c","C",src="politeama"),
      A.ev("Elio","","Politeama Genovese","https://www.politeamagenovese.it","2026-12-10","2026-12-10","c","C",src="politeama")]
A.link_spettacoli(E3, [])
assert E3[0]["u"] == "https://www.politeamagenovese.it/spettacolo/arisa/" and E3[1]["u"] == "https://www.politeamagenovese.it"
print("TUTTI I TEST OK:", len(n), "Nazionale,", len(c), "Carlo Felice,", len(g), "GOG,", len(t), "Tosse,", len(p), "Politeama")
