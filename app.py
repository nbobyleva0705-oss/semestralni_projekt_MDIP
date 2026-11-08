"""Návrat turistů do Česka po covidu (kdy → kde → odkud).

Semestrální práce MDIP – Interpretace a prezentace dat (ZS 2026/2027).
Autoři: Jirka Urban, Natalia Bobyleva, Maryia Shmatava.
Jedna příběhová linka kdy → kde → odkud, srovnávací základna rok 2019; nadpis každé
záložky je zjištění (akční nadpis) a počítá se z dat.

Data: ČSÚ 020063 + DataStat CRU02MT2, leden 2012 – srpen 2026 (viz priprava_dat.py).
Spuštění: Run v PyCharmu, potom http://127.0.0.1:8051
Mapa souboru: 1. data, 2. pomocné funkce a vzhled, 3. výpočty, 4. grafy, 5. layout,
6. callback, 7. server.
"""

import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import Dash, Input, Output, dcc, html

# 1. Data -----------------------------------------------------------------------
SLOZKA = Path(__file__).resolve().parent
df = pd.read_csv(SLOZKA / "data" / "HUZ_podle_zemi_2012-2026_spojeno.csv",
                 parse_dates=["datum"])
with open(SLOZKA / "data" / "kraje_CR.geojson", encoding="utf-8") as soubor:
    KRAJE_GEO = json.load(soubor)

PORT = 8051
POSLEDNI_DATUM = df["datum"].max()                      # srpen 2026
POSLEDNI_ROK = int(POSLEDNI_DATUM.year)
POSLEDNI_MESIC = int(POSLEDNI_DATUM.month)
NEUPLNY_ROK = POSLEDNI_ROK if POSLEDNI_MESIC < 12 else None
POSLEDNI_UPLNY_ROK = POSLEDNI_ROK - 1 if NEUPLNY_ROK else POSLEDNI_ROK
PRVNI_ROK = int(df["rok"].min())
ZAKLAD = 2019                                           # poslední rok před pandemií

KRAJE = sorted(df.loc[df["uroven_uzemi"] == "kraj", "uzemi"].unique())
MOZNOSTI_UZEMI = [{"label": "Česko celkem", "value": "Česko"}] + \
                 [{"label": k, "value": k} for k in KRAJE]
AUTORI = ["Jirka Urban", "Natalia Bobyleva", "Maryia Shmatava"]
UKAZATELE = {"hoste": "Počet hostů", "prenocovani": "Počet přenocování"}
# Dashboard pracuje jen s počtem hostů (příběh i papírové listy stojí na hostech).
# Funkce níže ukazatel dál přijímají, takže jde snadno přepnout na "prenocovani".
UKAZATEL = "hoste"
JEDNOTKA = {"hoste": "hostů", "prenocovani": "přenocování"}
MESICE = ["leden", "únor", "březen", "duben", "květen", "červen", "červenec",
          "srpen", "září", "říjen", "listopad", "prosinec"]
MESICE_ZKR = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII"]

# Vzhled: jedna barva = jeden význam (šalvějová = všichni / ovládání, modrá = rezidenti, oranžová = nerezidenti).
BARVA_REZIDENTI = "#174f94"     # modrá = rezidenti
BARVA_NEREZIDENTI = "#eb6834"   # oranžová = nerezidenti
BARVA_CELKEM = "#5c7264"        # šalvějová = všichni hosté
BARVA_AKCENT = "#34443a"        # tmavá šalvějová = ovládací prvky
BARVA_POKLES = "#a8998a"        # teplá šedá = pod úrovní 2019 / pokles
BARVA_KONTEXT = "#b9b8b2"       # šedá = kontext (ostatní, rok 2026)
TMAVA = "#0b0b0b"
SEDY_TEXT = "#52514e"
POZADI = "#f4f4f1"
PLOCHA = "#fcfcfb"
# Třídy kartogramu: podíl zahraničních hostů (%), divergentní škála se středem 50 %.
# Modrá = převažují domácí hosté (rezidenti), oranžová = převažují zahraniční (nerezidenti).
# Poslední položka: bílé písmo popisku na tmavé třídě.
# Popisky tříd mluví o skupině, která v kraji převažuje (stejně jako barva a číslo v kraji).
TRIDY = [(0, 20, "domácí nad 80 %", BARVA_REZIDENTI, True),
         (20, 35, "domácí 65–80 %", "#6f97cc", False),
         (35, 50, "domácí 50–65 %", "#c9d8ee", False),
         (50, 65, "zahraniční 50–65 %", "#f5b48f", False),
         (65, 101, "zahraniční nad 65 %", BARVA_NEREZIDENTI, True)]



# 2. Pomocné funkce -------------------------------------------------------------
def format_cislo(hodnota, desetinna=0):
    """Český zápis: mezera mezi tisíci, desetinná čárka. Chybějící hodnota = pomlčka."""
    if pd.isna(hodnota):
        return "—"
    return f"{hodnota:,.{desetinna}f}".replace(",", " ").replace(".", ",")


def format_zmena(hodnota, desetinna=0):
    """Číslo se znaménkem; skutečné minus místo spojovníku."""
    if pd.isna(hodnota):
        return "—"
    return ("+" if hodnota > 0 else "−" if hodnota < 0 else "") + format_cislo(abs(hodnota), desetinna)


def nazev_uzemi(uzemi):
    return "Česko" if uzemi == "Česko" else uzemi


def kratky_kraj(kraj):
    return (kraj.replace(" kraj", "").replace("Kraj ", "")
            .replace("Hlavní město ", ""))


def uprav_graf(fig, legenda=False):
    """Společný vzhled. Výšku neurčujeme: graf vyplní svou kartu (dcc.Graph responsive)."""
    fig.update_layout(
        template="plotly_white", autosize=True, separators=", ",
        font=dict(family="Arial", color=TMAVA, size=12),
        paper_bgcolor=PLOCHA, plot_bgcolor=PLOCHA,
        margin=dict(l=60, r=20, t=64, b=40), title_font_size=15,
        showlegend=legenda,
        # Legenda pod grafem, aby se nepřekrývala s podtitulem.
        legend=dict(orientation="h", yanchor="top", y=-0.12, xanchor="left", x=0,
                    title_text=""),
        hoverlabel=dict(bgcolor="white", font_size=13),
    )
    fig.update_xaxes(gridcolor="#ebebe7", linecolor="#c9c8c2")
    fig.update_yaxes(gridcolor="#ebebe7", linecolor="#c9c8c2")
    return fig


def nadpis_grafu(text, podtitul):
    """Nadpis grafu + šedý podtitul (jak číst graf)."""
    return dict(text=f"{text}<br><span style='font-size:11px;color:{SEDY_TEXT}'>{podtitul}</span>",
                x=0.01, xanchor="left")


def prazdny_graf(nadpis, zprava):
    fig = go.Figure()
    fig.add_annotation(text=zprava, x=0.5, y=0.5, xref="paper", yref="paper",
                       showarrow=False, font=dict(size=15, color=SEDY_TEXT))
    fig.update_layout(title=nadpis)
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    return uprav_graf(fig)


# 3. Výpočty (všechno je „rok X v % roku 2019“) -----------------------------------
def rocne(uzemi, ukazatel, typ, do_mesice=12):
    """Roční součty jednoho území a jedné skupiny; do_mesice omezí měsíce (leden–srpen)."""
    data = df.loc[(df["uzemi"] == uzemi) & (df["typ_rezidence"] == typ)
                  & (df["mesic"] <= do_mesice)]
    return data.groupby("rok")[ukazatel].sum(min_count=1)


def index_2019(uzemi, ukazatel, typ):
    """Roční index 2019 = 100 za úplné roky."""
    r = rocne(uzemi, ukazatel, typ).loc[:POSLEDNI_UPLNY_ROK]
    return r / r.loc[ZAKLAD] * 100


def index_neuplny(uzemi, ukazatel, typ):
    """Neúplný rok: leden–poslední měsíc proti stejnému období 2019 a proti předchozímu roku."""
    if not NEUPLNY_ROK:
        return None, None
    r = rocne(uzemi, ukazatel, typ, POSLEDNI_MESIC)
    return r.loc[NEUPLNY_ROK] / r.loc[ZAKLAD] * 100, (r.loc[NEUPLNY_ROK] / r.loc[NEUPLNY_ROK - 1] - 1) * 100


def kraje_tabulka(ukazatel, cil):
    """Pro každý kraj: podíl nerezidentů 2019 a index cílového roku pro všechny skupiny."""
    data = df.loc[(df["uroven_uzemi"] == "kraj") & df["rok"].isin([ZAKLAD, cil])
                  & df["typ_rezidence"].isin(["celkem", "rezidenti", "nerezidenti"])]
    p = data.pivot_table(index="uzemi", columns=["typ_rezidence", "rok"], values=ukazatel,
                         aggfunc="sum")
    tab = pd.DataFrame(index=p.index)
    tab["podil_nerez"] = p[("nerezidenti", ZAKLAD)] / p[("celkem", ZAKLAD)] * 100
    for typ in ["celkem", "rezidenti", "nerezidenti"]:
        tab[typ] = p[(typ, cil)] / p[(typ, ZAKLAD)] * 100
    return tab.sort_values("podil_nerez", ascending=False)


def index_kraju_v_case(ukazatel, skupina, cil):
    data = df.loc[(df["uroven_uzemi"] == "kraj") & df["rok"].between(ZAKLAD, cil)
                  & (df["typ_rezidence"] == skupina)]
    p = data.pivot_table(index="uzemi", columns="rok", values=ukazatel, aggfunc="sum")
    return p.div(p[ZAKLAD], axis=0) * 100


def rok_navratu(radek):
    """První rok po 2019, kdy kraj dosáhl aspoň 100 %, jinak None."""
    nad = [r for r, v in radek.items() if r > ZAKLAD and v >= 100]
    return nad[0] if nad else None


def zmena_zemi(uzemi, ukazatel, cil):
    """Změna počtu nerezidentů podle zemí mezi 2019 a cílovým rokem (jen země v obou letech)."""
    data = df.loc[(df["uzemi"] == uzemi) & (df["typ_rezidence"] == "země")
                  & df["rok"].isin([ZAKLAD, cil])]
    p = data.pivot_table(index="rezidence", columns="rok", values=ukazatel, aggfunc="sum")
    p = p.dropna()
    p["zmena"] = p[cil] - p[ZAKLAD]
    p["zmena_pct"] = p["zmena"] / p[ZAKLAD] * 100
    return p


# 4. Grafy ------------------------------------------------------------------------
# List 1 · KDY
def graf_index(uzemi, ukazatel, cil):
    """A: roční index 2019 = 100, rezidenti a nerezidenti, kroužek = neúplný rok."""
    fig = go.Figure()
    fig.add_vrect(x0=2019.5, x1=2021.5, fillcolor="#e6e5e0", opacity=0.6, line_width=0, layer="below",
                  annotation_text="pandemie", annotation_position="bottom left",
                  annotation_font=dict(size=12, color=SEDY_TEXT))
    fig.add_hline(y=100, line_dash="dash", line_color=SEDY_TEXT, line_width=1)
    # Obě srovnávané hodnoty: základ 2019 a zvolený rok (svislá čára s popiskem).
    fig.add_annotation(x=ZAKLAD, y=100, text=f"základ {ZAKLAD} = 100 %", showarrow=False,
                       yshift=16, font=dict(size=12, color=SEDY_TEXT))
    fig.add_vline(x=cil, line_color=SEDY_TEXT, line_width=1, line_dash="dot",
                  annotation_text=f"{cil} = srovnávaný rok", annotation_position="top",
                  annotation_font=dict(size=12, color=SEDY_TEXT))
    for typ, nazev, barva in [("rezidenti", "Rezidenti (z Česka)", BARVA_REZIDENTI),
                              ("nerezidenti", "Nerezidenti (ze zahraničí)", BARVA_NEREZIDENTI)]:
        idx = index_2019(uzemi, ukazatel, typ)
        fig.add_trace(go.Scatter(
            x=idx.index, y=idx.values, name=nazev, mode="lines+markers",
            line=dict(color=barva, width=3), marker=dict(size=6),
            hovertemplate="%{x}: %{y:.1f} % roku 2019<extra>" + nazev + "</extra>"))
        if pd.notna(idx.loc[cil]):
            fig.add_annotation(x=cil, y=idx.loc[cil], text=f"<b>{format_cislo(idx.loc[cil], 1)}</b>",
                               # vlevo od bodu, aby popisek nekřížil svislou čáru zvoleného roku
                               showarrow=False, xanchor="right", xshift=-6,
                               bgcolor="rgba(252, 252, 251, 0.85)",
                               yshift=12 if typ == "rezidenti" else -12,
                               font=dict(color=barva, size=13))
        neupl, _ = index_neuplny(uzemi, ukazatel, typ)
        if neupl is not None:
            fig.add_trace(go.Scatter(
                x=[NEUPLNY_ROK], y=[neupl], mode="markers", showlegend=False,
                marker=dict(size=11, color=PLOCHA, line=dict(color=barva, width=2.5)),
                hovertemplate=f"{NEUPLNY_ROK} leden–{MESICE[POSLEDNI_MESIC - 1]}: "
                              "%{y:.1f} % stejného období 2019<extra>" + nazev + "</extra>"))
    fig.update_layout(title=nadpis_grafu(
        f"A · {UKAZATELE[ukazatel]} v % roku 2019 (2019 = 100)",
        f"kroužek {NEUPLNY_ROK}* = leden–{MESICE[POSLEDNI_MESIC - 1]} proti stejnému období 2019"
        if NEUPLNY_ROK else "roční součty"))
    fig.update_xaxes(dtick=1, tickvals=list(range(PRVNI_ROK, POSLEDNI_ROK + 1)),
                     ticktext=[f"{r}*" if r == NEUPLNY_ROK else str(r)
                               for r in range(PRVNI_ROK, POSLEDNI_ROK + 1)])
    fig.update_yaxes(ticksuffix=" %", rangemode="tozero")
    return uprav_graf(fig, legenda=True).update_layout(margin=dict(t=64, b=70))


def graf_sezonnost(uzemi, ukazatel, cil):
    """B: sezónnost zvoleného roku proti roku 2019 – počet hostů v jednotlivých měsících (tis.).

    Plná čára = zvolený rok, tenká čárkovaná = 2019. Ukazuje, zda se tvar sezóny po covidu změnil.
    """
    data = df.loc[(df["uzemi"] == uzemi) & df["rok"].isin([ZAKLAD, cil])
                  & df["typ_rezidence"].isin(["rezidenti", "nerezidenti"])]
    mesice = data.pivot_table(index="mesic", columns=["typ_rezidence", "rok"], values=ukazatel,
                              aggfunc="sum") / 1000
    fig = go.Figure()
    for typ, nazev, barva in [("rezidenti", "Rezidenti", BARVA_REZIDENTI),
                              ("nerezidenti", "Nerezidenti", BARVA_NEREZIDENTI)]:
        for rok, sirka, cara in [(ZAKLAD, 1.5, "dash"), (cil, 3, "solid")]:
            if rok == ZAKLAD and cil == ZAKLAD:
                continue
            fig.add_trace(go.Scatter(
                x=MESICE_ZKR, y=mesice[(typ, rok)].values, name=f"{nazev} {rok}",
                mode="lines+markers" if rok == cil else "lines",
                line=dict(color=barva, width=sirka, dash=cara), marker=dict(size=5),
                customdata=MESICE,
                hovertemplate="%{customdata} " + str(rok) + ": %{y:,.0f} tis.<extra>"
                              + nazev + "</extra>"))
    fig.update_layout(title=nadpis_grafu(
        f"B · Sezónnost {cil} proti {ZAKLAD}",
        f"počet {JEDNOTKA[ukazatel]} v jednotlivých měsících (tis.); plná čára = {cil}, "
        f"čárkovaná = {ZAKLAD}"))
    fig.update_yaxes(rangemode="tozero", title_text=f"tis. {JEDNOTKA[ukazatel]}",
                     tickformat=",.0f")
    return uprav_graf(fig, legenda=True).update_layout(margin=dict(t=64, b=70))


# List 2 · KDE
def _stredy_kraju():
    """Přibližné středy krajů pro popisky (průměr bodů obrysu, Středočeský posunut z Prahy)."""
    stredy = {}
    for f in KRAJE_GEO["features"]:
        geo = f["geometry"]
        obrys = geo["coordinates"][0] if geo["type"] == "Polygon" else \
            max(geo["coordinates"], key=lambda p: len(p[0]))[0]
        lon = sum(b[0] for b in obrys) / len(obrys)
        lat = sum(b[1] for b in obrys) / len(obrys)
        stredy[f["properties"]["kraj"]] = (lat, lon)
    lat, lon = stredy["Středočeský kraj"]
    stredy["Středočeský kraj"] = (lat - 0.3, lon + 0.15)
    return stredy


STREDY = _stredy_kraju()


def trida(podil):
    for dolni, horni, nazev, _, _ in TRIDY:
        if dolni <= podil < horni:
            return nazev
    return TRIDY[-1][2]


def _obrysy_kraju():
    """Obrysy krajů jako seznamy (lon, lat); u více částí kraje bereme všechny části."""
    obrysy = {}
    for f in KRAJE_GEO["features"]:
        geo = f["geometry"]
        casti = [geo["coordinates"]] if geo["type"] == "Polygon" else geo["coordinates"]
        obrysy[f["properties"]["kraj"]] = [cast[0] for cast in casti]   # jen vnější okraj
    return obrysy


OBRYSY = _obrysy_kraju()


def podil_nerez_kraju(ukazatel, rok):
    """Podíl zahraničních hostů (%) v každém kraji za jeden rok."""
    data = df.loc[(df["uroven_uzemi"] == "kraj") & (df["rok"] == rok)
                  & df["typ_rezidence"].isin(["celkem", "nerezidenti"])]
    p = data.pivot_table(index="uzemi", columns="typ_rezidence", values=ukazatel, aggfunc="sum")
    return pd.DataFrame({"podil_nerez": p["nerezidenti"] / p["celkem"] * 100})


def graf_kartogram(tab, zvyrazneny, rok=ZAKLAD):
    """C: kdo v kraji převažuje – divergentní škála modrá ↔ oranžová, střed 50 %.
    tab = podíl zahraničních hostů v krajích za zvolený rok (posuvník pod mapou).

    Mapu kreslíme jako obyčejné vyplněné mnohoúhelníky (go.Scatter, fill="toself"):
    nepotřebuje internet ani mapové dlaždice a vždy se vejde do karty, ať je okno jakkoli velké.
    """
    t = tab.copy()
    t["trida"] = t["podil_nerez"].apply(trida)
    barvy = {x[2]: x[3] for x in TRIDY}
    bile_pismo = {x[2] for x in TRIDY if x[4]}
    fig = go.Figure()
    # Legenda: jedna položka za třídu, ve správném pořadí.
    for _, _, nazev, barva, _ in TRIDY:
        fig.add_trace(go.Scatter(x=[None], y=[None], mode="markers", name=nazev,
                                 marker=dict(size=12, color=barva, symbol="square")))
    # Praha leží uvnitř Středočeského kraje, proto ji kreslíme až nakonec.
    poradi = [k for k in t.index if k != "Hlavní město Praha"] + ["Hlavní město Praha"]
    for kraj in poradi:
        r = t.loc[kraj]
        popis = (f"<b>{kraj}</b> ({rok})<br>zahraniční hosté: {format_cislo(r['podil_nerez'], 1)} %"
                 f"<br>domácí hosté: {format_cislo(100 - r['podil_nerez'], 1)} %")
        for obrys in OBRYSY[kraj]:
            fig.add_trace(go.Scatter(
                x=[b[0] for b in obrys], y=[b[1] for b in obrys], mode="lines", fill="toself",
                fillcolor=barvy[r["trida"]], line=dict(color="white", width=1),
                hoveron="fills", text=popis, hoverinfo="text", showlegend=False))
    if zvyrazneny != "Česko":
        for obrys in OBRYSY[zvyrazneny]:
            fig.add_trace(go.Scatter(x=[b[0] for b in obrys], y=[b[1] for b in obrys],
                                     mode="lines", line=dict(color=TMAVA, width=3),
                                     hoverinfo="skip", showlegend=False))
    # Čísla v krajích: bílá na tmavých třídách, tmavá na světlých.
    for svetle, barva_textu in [(False, TMAVA), (True, "white")]:
        cast = t[t["trida"].isin(bile_pismo) == svetle]
        fig.add_trace(go.Scatter(
            x=[STREDY[k][1] for k in cast.index], y=[STREDY[k][0] for k in cast.index],
            # Číslo = podíl skupiny, která převažuje (modrá → domácí, oranžová → zahraniční).
            mode="text", text=[format_cislo(v if v >= 50 else 100 - v) for v in cast["podil_nerez"]],
            textfont=dict(size=12, color=barva_textu), hoverinfo="skip", showlegend=False))
    fig.update_layout(title=nadpis_grafu(
        f"C · Kdo v kraji převažuje ({rok})",
        "barva = která skupina převažuje, číslo = její podíl na všech hostech v %"))
    fig = uprav_graf(fig, legenda=True)
    # Zeměpisná délka je v Česku „kratší“ než šířka (cos 49,8° ≈ 0,65): poměr os 1 : 1,55.
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False, scaleanchor="x", scaleratio=1.55)
    fig.update_layout(margin=dict(l=8, r=8, t=64, b=40), legend=dict(y=0, yanchor="top"),
                      hovermode="closest")
    return fig


def graf_cinky_kraju(tab, ukazatel, cil, zvyrazneny):
    """D: index cílového roku v % roku 2019, rezidenti vs. nerezidenti.

    Kraje seřazené podle počtu všech hostů ve zvoleném roce (váha kraje); počet je šedě u názvu.
    """
    velikost = (df.loc[(df["uroven_uzemi"] == "kraj") & (df["rok"] == cil)
                       & (df["typ_rezidence"] == "celkem")].groupby("uzemi")[ukazatel].sum())
    # Osa y kreslí první kategorii dole, proto vzestupně: největší kraj bude nahoře.
    t = tab.loc[velikost.sort_values().index]
    popisky = [(f"<b>{kratky_kraj(k)}</b>" if k == zvyrazneny else kratky_kraj(k))
               + f" <span style='color:{SEDY_TEXT};font-size:10px'>"
                 f"{format_cislo(velikost[k] / 1e6, 1)} mil.</span>" for k in t.index]
    fig = go.Figure()
    for k, (_, r) in zip(popisky, t.iterrows()):
        fig.add_trace(go.Scatter(x=[r["rezidenti"], r["nerezidenti"]], y=[k, k], mode="lines",
                                 line=dict(color="#d6d4cd", width=4), hoverinfo="skip",
                                 showlegend=False))
    fig.add_vline(x=100, line_dash="dash", line_color=SEDY_TEXT, line_width=1)
    for typ, nazev, barva in [("rezidenti", "Rezidenti", BARVA_REZIDENTI),
                              ("nerezidenti", "Nerezidenti", BARVA_NEREZIDENTI)]:
        fig.add_trace(go.Scatter(
            x=t[typ], y=popisky, mode="markers", name=nazev,
            marker=dict(size=10, color=barva, line=dict(color=PLOCHA, width=1)),
            customdata=t.index, hovertemplate="%{customdata}: %{x:.1f} % roku 2019<extra>"
                                              + nazev + "</extra>"))
    # Vpravo dva sloupce: rok, kdy se kraj poprvé vrátil na úroveň 2019 (domácí / zahraniční).
    # Nahrazují dřívější teplotní mapu „Jak rychle se vraceli“.
    # Sloupce posunuté v pixelech (xshift), aby se nepřekrývaly ani v úzkém okně.
    for posun, typ, barva, hlavicka in [(8, "rezidenti", BARVA_REZIDENTI, "domácí"),
                                        (72, "nerezidenti", BARVA_NEREZIDENTI, "zahraniční")]:
        navrat = index_kraju_v_case(ukazatel, typ, cil).apply(rok_navratu, axis=1)
        fig.add_annotation(x=1, xref="paper", xshift=posun, y=1.0, yref="paper",
                           yanchor="bottom", xanchor="left", text=f"<b>{hlavicka}</b>", showarrow=False,
                           font=dict(size=10, color=barva))
        for kraj, popisek in zip(t.index, popisky):
            rok = navrat.get(kraj)
            fig.add_annotation(x=1, xref="paper", xshift=posun, y=popisek, yref="y", xanchor="left",
                               text="zatím ne" if pd.isna(rok) else str(int(rok)),
                               showarrow=False,
                               font=dict(size=11, color=SEDY_TEXT if pd.isna(rok) else barva))
    # Společný nadpis nad oběma sloupci s roky.
    fig.add_annotation(x=1, xref="paper", xshift=8, y=1.0, yref="paper", yshift=16,
                       yanchor="bottom", xanchor="left", showarrow=False,
                       text="<b>rok návratu<br>na úroveň 2019</b>", align="left",
                       font=dict(size=10, color=SEDY_TEXT))
    fig.update_layout(title=dict(text=f"D · Kraje v roce {cil} v % roku 2019", x=0.01,
                                 xanchor="left"))
    fig.update_xaxes(ticksuffix=" %", title_text="% roku 2019")
    fig.update_yaxes(categoryorder="array", categoryarray=popisky, gridcolor=PLOCHA)
    fig = uprav_graf(fig, legenda=True)
    fig.update_layout(margin=dict(l=150, r=140, t=84, b=80), legend=dict(y=-0.16))
    return fig


# List 3 · ODKUD
def graf_mustek(uzemi, ukazatel, cil):
    """F: příspěvky zemí ke změně počtu nerezidentů 2019 → cíl (5 poklesů, 5 přírůstků, ostatní)."""
    p = zmena_zemi(uzemi, ukazatel, cil)
    celkem = rocne(uzemi, ukazatel, "nerezidenti")
    zmena_celkem = celkem.loc[cil] - celkem.loc[ZAKLAD]
    poklesy = p.nsmallest(5, "zmena")
    poklesy = poklesy[poklesy["zmena"] < 0]
    prirustky = p.nlargest(5, "zmena")
    prirustky = prirustky[prirustky["zmena"] > 0].iloc[::-1]
    ostatni = zmena_celkem - poklesy["zmena"].sum() - prirustky["zmena"].sum()
    nazvy = list(poklesy.index) + list(prirustky.index) + ["ostatní"]
    hodnoty = list(poklesy["zmena"]) + list(prirustky["zmena"]) + [ostatni]
    barvy = [BARVA_POKLES] * len(poklesy) + [BARVA_NEREZIDENTI] * len(prirustky) + [BARVA_KONTEXT]
    fig = go.Figure(go.Bar(
        x=nazvy, y=[h / 1000 for h in hodnoty], marker_color=barvy,
        marker_pattern_shape=[""] * (len(nazvy) - 1) + ["x"],
        marker_pattern_fgcolor="#8d8b85",
        text=[format_zmena(h / 1000) for h in hodnoty], textposition="outside",
        cliponaxis=False,
        customdata=[format_zmena(p.loc[n, "zmena_pct"]) + " %" if n in p.index else "—" for n in nazvy],
        hovertemplate="%{x}: %{text} tis. (%{customdata})<extra></extra>"))
    fig.add_hline(y=0, line_color=TMAVA, line_width=1)
    fig.update_layout(title=nadpis_grafu(
        f"F · Změna počtu zahraničních {JEDNOTKA[ukazatel]} {ZAKLAD} → {cil} (tis.)",
        f"{nazev_uzemi(uzemi)}: {format_cislo(celkem.loc[ZAKLAD] / 1e6, 2)} mil. → "
        f"{format_cislo(celkem.loc[cil] / 1e6, 2)} mil. ({format_zmena(zmena_celkem / 1000, 1)} tis.); "
        "šedě pokles, oranžově přírůstek, šrafovaně ostatní země a skupiny zemí"),
        bargap=0.35)
    fig.update_yaxes(title_text="tis.", zeroline=False)
    return uprav_graf(fig)


MALY_ZAKLAD = 1000      # trh s méně než 1 000 hosty v roce 2019: procenta jsou jen orientační


def graf_trhy_kraju(ukazatel, cil, zvyrazneny):
    """H: teplotní mapa Česko + kraje × hlavní trhy, změna zahraničních hostů 2019 → cíl v %.

    Sloupce = 4 trhy s největším poklesem a 4 s největším přírůstkem v celém Česku.
    Šedá = pokles, oranžová = růst, bílá = beze změny. Bledé buňky mají malý základ
    (méně než 1 000 hostů v roce 2019), kde i malá změna dá velké procento.
    """
    cesko = zmena_zemi("Česko", ukazatel, cil)
    trhy = list(cesko.nsmallest(4, "zmena").index) + list(cesko.nlargest(4, "zmena").index[::-1])
    zkratky = {"Korejská republika": "Korea", "Velká Británie a Severní Irsko": "Velká Británie",
               "Spojené státy": "USA", "Nizozemské království": "Nizozemsko"}
    sloupce = [zkratky.get(z, z) for z in trhy]
    uzemi = ["Česko"] + list(kraje_tabulka(ukazatel, cil).index)      # kraje podle podílu cizinců
    radky = [("<b>Česko</b>" if u == "Česko" else
              f"<b>{kratky_kraj(u)}</b>" if u == zvyrazneny else kratky_kraj(u)) for u in uzemi]
    hodnoty, zaklad, popisky_bunek = [], [], []
    for u in uzemi:
        p = zmena_zemi(u, ukazatel, cil)
        hodnoty.append([p.loc[z, "zmena_pct"] if z in p.index else None for z in trhy])
        zaklad.append([p.loc[z, ZAKLAD] if z in p.index else None for z in trhy])
        # Text pro bublinu: počty v obou letech a změna v kusech.
        popisky_bunek.append([
            f"{ZAKLAD}: {format_cislo(p.loc[z, ZAKLAD])} {JEDNOTKA[ukazatel]}<br>"
            f"{cil}: {format_cislo(p.loc[z, cil])} {JEDNOTKA[ukazatel]}<br>"
            f"změna: {format_zmena(p.loc[z, 'zmena'])} ({format_zmena(p.loc[z, 'zmena_pct'])} %)"
            if z in p.index else "bez údajů" for z in trhy])
    skala = [[0, "#6f655c"], [0.25, BARVA_POKLES], [0.5, "#ffffff"],
             [0.75, "#f5b48f"], [1, BARVA_NEREZIDENTI]]
    fig = go.Figure(go.Heatmap(
        z=hodnoty, x=sloupce, y=radky, zmin=-100, zmax=100, zmid=0, colorscale=skala,
        xgap=3, ygap=3, showscale=False, customdata=popisky_bunek,
        hovertemplate="<b>%{y} · %{x}</b><br>%{customdata}<extra></extra>"))
    # Bledý závoj přes buňky s malým základem.
    zavoj = [[1 if (b is not None and b < MALY_ZAKLAD) else None for b in r] for r in zaklad]
    fig.add_trace(go.Heatmap(z=zavoj, x=sloupce, y=radky, xgap=3, ygap=3, showscale=False,
                             colorscale=[[0, "rgba(252,252,251,0.7)"], [1, "rgba(252,252,251,0.7)"]],
                             hoverinfo="skip"))
    for i, (radek, zaklady) in enumerate(zip(hodnoty, zaklad)):
        for j, (v, b) in enumerate(zip(radek, zaklady)):
            if v is None or pd.isna(v):
                continue
            maly = b is not None and b < MALY_ZAKLAD
            tmave = (v < -60 or v > 80) and not maly
            fig.add_annotation(x=j, y=i, text=format_zmena(v), showarrow=False,
                               font=dict(size=11, color="white" if tmave else
                                         (SEDY_TEXT if maly else TMAVA)))
    # Čára pod řádkem Česko.
    fig.add_shape(type="line", x0=-0.5, x1=len(trhy) - 0.5, y0=0.5, y1=0.5,
                  line=dict(color=TMAVA, width=2))
    fig.update_layout(title=nadpis_grafu(
        f"H · Jak se změnily hlavní trhy v krajích ({ZAKLAD} → {cil}, %)",
        "šedá = pokles, oranžová = růst; bledě = v roce 2019 méně než 1 000 hostů"))
    fig.update_yaxes(autorange="reversed", showgrid=False)
    # Názvy zemí jsou nahoře vždy šikmo (−45°). Plotly by je jinak natáčel podle šířky okna
    # a na menší obrazovce by vjely do podtitulu. Při pevném úhlu známe jejich výšku předem
    # (podle nejdelšího názvu), takže horní okraj = místo pro nadpis + místo pro názvy zemí.
    fig.update_xaxes(side="top", showgrid=False, tickangle=-45, tickfont_size=12, automargin=False)
    fig = uprav_graf(fig)
    vyska_nazvu = (max(len(z) for z in sloupce) * 7 + 12) * 0.71
    fig.update_layout(margin=dict(l=110, r=12, t=round(72 + vyska_nazvu), b=8),
                      title=dict(yref="container", y=1, yanchor="top", pad=dict(t=22)))
    return fig


# Akční nadpisy (zjištění místo tématu) -------------------------------------------
def nadpis_kdy(uzemi, ukazatel, cil):
    celkem = index_2019(uzemi, ukazatel, "celkem")
    c = celkem.loc[cil]
    r, n = (index_2019(uzemi, ukazatel, t).loc[cil] for t in ["rezidenti", "nerezidenti"])
    # „Rekord“ jen tehdy, když je zvolený rok opravdu nejvyšší v řadě do tohoto roku.
    rekord = c >= celkem.loc[:cil].max()
    zacatek = "Rekord" if rekord else "Růst nad úroveň 2019"
    if c < 100:
        hlavni = f"{nazev_uzemi(uzemi)} je v roce {cil} stále pod úrovní 2019"
    elif r - 100 > 2 * max(n - 100, 0):
        hlavni = f"{zacatek} táhnou domácí hosté"
    elif n - 100 > 2 * max(r - 100, 0):
        hlavni = f"{zacatek} táhnou zahraniční hosté"
    else:
        hlavni = "Domácí i zahraniční hosté nad úrovní 2019"
    podtitul = (f"{nazev_uzemi(uzemi)} {cil}: celkem {format_cislo(c, 1)} % roku 2019, "
                f"domácí {format_cislo(r, 1)} %, zahraniční {format_cislo(n, 1)} %.")
    return hlavni, podtitul


def nadpis_kde(tab, cil):
    r = int((tab["rezidenti"] >= 100).sum())
    n = int((tab["nerezidenti"] >= 100).sum())
    if r == 0 and n == 0:
        hlavni = f"V roce {cil} se žádný kraj nevrátil na úroveň 2019"
    elif r > n:
        hlavni = "Domácí hosté rostou téměř všude, zahraniční ne" if r >= 12 else \
            "Domácí hosté se vracejí rychleji než zahraniční"
    elif n > r:
        hlavni = "Zahraniční hosté se vracejí rychleji než domácí"
    else:
        hlavni = "Domácí i zahraniční hosté se vracejí stejně"
    pod = [kratky_kraj(k) for k in tab.index[tab["nerezidenti"] < 100]]
    if len(pod) == len(tab):
        pod_text = " Zahraniční jsou pod úrovní 2019 ve všech krajích."
    elif pod:
        pod_text = f" Zahraniční zatím pod úrovní: {', '.join(pod)}."
    else:
        pod_text = ""
    podtitul = (f"Rok {cil} proti roku 2019: kraje nad úrovní 2019 – u domácích hostů "
                f"{r} ze 14, u zahraničních {n} ze 14." + pod_text)
    return hlavni, podtitul


def nadpis_odkud(uzemi, ukazatel, cil):
    celkem = rocne(uzemi, ukazatel, "nerezidenti")
    zmena = (celkem.loc[cil] / celkem.loc[ZAKLAD] - 1) * 100
    p = zmena_zemi(uzemi, ukazatel, cil)
    ubytek = p.nsmallest(2, "zmena")
    prirustek = p.nlargest(3, "zmena")
    prirustek = prirustek[prirustek["zmena"] > 0]      # v roce 2020 nemusí přibýt nikdo
    if abs(zmena) < 3:
        hlavni = f"Zahraniční hosté se vrátili ({format_zmena(zmena, 1)} %), ale jiní"
    elif zmena > 0:
        hlavni = f"Zahraničních {JEDNOTKA[ukazatel]} přibylo o {format_cislo(zmena, 1)} %"
    else:
        hlavni = f"Zahraničních {JEDNOTKA[ukazatel]} ubylo o {format_cislo(abs(zmena), 1)} %"
    podtitul = (f"{nazev_uzemi(uzemi)}, {ZAKLAD} → {cil}: počet zahraničních {JEDNOTKA[ukazatel]} "
                f"{format_zmena(zmena, 1)} %. Nejvíc ubylo: {', '.join(ubytek.index)} "
                f"({format_zmena(ubytek['zmena'].sum() / 1000)} tis.)"
                + (f"; nejvíc přibylo: {', '.join(prirustek.index)} "
                   f"({format_zmena(prirustek['zmena'].sum() / 1000)} tis.)." if len(prirustek)
                   else "; žádná země nepřibyla."))
    return hlavni, podtitul


# 5. Layout -----------------------------------------------------------------------
# Celý dashboard se vejde na jednu obrazovku: stránka má výšku okna (100vh), řádek s grafy
# zabere zbytek místa a grafy se mu přizpůsobí (dcc.Graph responsive). Třídy (className)
# jsou popsané v assets/dashboard.css; tam je i úprava pro úzké obrazovky (telefon).
def karta(obsah, pomer=1, id_=None):
    """Bílá karta v řádku grafů; pomer = kolik šířky dostane proti ostatním."""
    vlastnosti = {"id": id_} if id_ else {}
    return html.Div(obsah, className="karta", style={"flex": f"{pomer} 1 0"}, **vlastnosti)


def graf(id_):
    return dcc.Graph(id=id_, className="graf", responsive=True,
                     config={"displaylogo": False, "responsive": True})


def kpi(nazev, id_, barva):
    return html.Div([
        html.Div([html.Span(nazev, className="kpi-nazev"),
                  html.Span(id=id_, className="kpi-hodnota")]),
        html.Div(id=id_ + "-popis", className="kpi-popis"),
    ], className="kpi", style={"borderTop": f"4px solid {barva}"})


def akcni_nadpis(id_):
    return html.Div([html.H2(id=id_, className="akcni-nadpis"),
                     html.P(id=id_ + "-pod", className="akcni-podtitul")])


def vyber(nadpis, prvek, sirka):
    return html.Div([html.Label(nadpis, className="vyber-nazev"), prvek],
                    className="vyber", style={"width": sirka})


app = Dash(__name__)
app.title = "Návrat turistů do Česka po covidu"
app.layout = html.Div([
    # Hlavička na jeden řádek; vysvětlení se rozbalí pod ikonou ⓘ.
    html.Header([
        html.Div([
            html.H1("Návrat turistů do Česka po covidu"),
            html.P(f"MDIP · Interpretace a prezentace dat · semestrální práce · {', '.join(AUTORI)}"),
        ]),
        html.Details([
            html.Summary("ⓘ O dashboardu"),
            html.Div([
                html.P(["Pandemie covidu-19 v letech 2020–2021 snížila počet hostů v českých "
                        "ubytovacích zařízeních na polovinu, zahraničních dokonce na čtvrtinu. "
                        "Dashboard ukazuje, ", html.B("kdy"), " se turisté vrátili, ", html.B("kde"),
                        " (kraje) a ", html.B("odkud"), f" (země původu). Každý rok srovnáváme "
                        f"s rokem {ZAKLAD}, posledním před pandemií ({ZAKLAD} = 100 %)."]),
                html.P(f"Hosté = příjezdy do hotelů, penzionů, kempů a dalších hromadných "
                       f"ubytovacích zařízení · rezidenti = hosté z Česka · nerezidenti = ze "
                       f"zahraničí · zdroj ČSÚ, leden {PRVNI_ROK} – "
                       f"{MESICE[POSLEDNI_MESIC - 1]} {POSLEDNI_ROK}.", className="drobne"),
            ], className="info-obsah"),
        ], className="info"),
    ], className="hlavicka"),

    # Záložky a filtry v jednom pruhu.
    html.Div([
        # Záložky jako přepínač (RadioItems) – v pruhu vedle filtrů drží tvar lépe než dcc.Tabs.
        dcc.RadioItems(id="listy", value="kdy", inline=True, className="zalozky",
                       options=[{"label": n, "value": v}
                                for n, v in [("Kdy", "kdy"), ("Kde", "kde"), ("Odkud", "odkud")]]),
        vyber("Území (Kdy a Odkud)", dcc.Dropdown(id="uzemi", options=MOZNOSTI_UZEMI,
                                                   value="Česko", clearable=False), "250px"),
        vyber(f"Rok srovnání s {ZAKLAD}", dcc.Dropdown(
            id="cil", clearable=False, value=POSLEDNI_UPLNY_ROK,
            options=[{"label": str(r), "value": r} for r in range(POSLEDNI_UPLNY_ROK, ZAKLAD, -1)]),
            "150px"),
    ], className="ovladani"),

    # Tři panely; viditelný je jen ten, jehož záložka je vybraná (callback přepni_panel).
    html.Div([
        akcni_nadpis("nadpis-kdy"),
        html.Div([
            kpi("Všichni hosté", "kpi-celkem", BARVA_CELKEM),
            kpi("Rezidenti", "kpi-rez", BARVA_REZIDENTI),
            kpi("Nerezidenti", "kpi-nerez", BARVA_NEREZIDENTI),
            kpi(f"Rok {NEUPLNY_ROK or POSLEDNI_ROK}*", "kpi-neupl", BARVA_KONTEXT),
        ], className="radek-kpi"),
        html.Div([karta(graf("graf-a"), 2), karta(graf("graf-b"), 1)], className="radek-grafu"),
    ], id="panel-kdy", className="panel"),

    html.Div([
        akcni_nadpis("nadpis-kde"),
        html.Div([
            karta([
                graf("graf-c"),
                # Kompaktní posuvník: rok mapy nezávisle na „Roku srovnání“ (výchozí 2019).
                html.Div(dcc.Slider(
                    id="rok-mapy", min=PRVNI_ROK, max=POSLEDNI_UPLNY_ROK, step=1, value=ZAKLAD,
                    marks={r: str(r) for r in [PRVNI_ROK, 2015, ZAKLAD, 2022, POSLEDNI_UPLNY_ROK]},
                    tooltip={"placement": "top", "always_visible": False}, updatemode="drag"),
                    className="posuvnik"),
            ], 1),
            karta(graf("graf-d"), 1),
        ], className="radek-grafu"),
    ], id="panel-kde", className="panel"),

    html.Div([
        akcni_nadpis("nadpis-odkud"),
        html.Div([karta(graf("graf-f"), 1.2),
                  karta(graf("graf-h"), 1)], className="radek-grafu"),
    ], id="panel-odkud", className="panel"),

    html.Footer("Zdroj: ČSÚ, Hosté a přenocování v HUZ podle zemí (020063, DataStat CRU02MT2), "
                "stav k 9. 10. 2026 · jen hromadná ubytovací zařízení · 2025–2026 předběžná data · "
                "host = příjezd · chybějící kombinace země × kraj nedoplňujeme nulou · hranice krajů "
                "ČÚZK via geoBoundaries (CC BY 4.0)", className="paticka"),
], className="stranka",
   style={"--Dash-Fill-Interactive-Strong": BARVA_AKCENT, "--Dash-Text-Primary": TMAVA})


# 6. Callbacky ---------------------------------------------------------------------
@app.callback(
    Output("nadpis-kdy", "children"), Output("nadpis-kdy-pod", "children"),
    Output("kpi-celkem", "children"), Output("kpi-celkem-popis", "children"),
    Output("kpi-rez", "children"), Output("kpi-rez-popis", "children"),
    Output("kpi-nerez", "children"), Output("kpi-nerez-popis", "children"),
    Output("kpi-neupl", "children"), Output("kpi-neupl-popis", "children"),
    Output("graf-a", "figure"), Output("graf-b", "figure"),
    Input("uzemi", "value"), Input("cil", "value"),
)
def list_kdy(uzemi, cil):
    ukazatel = UKAZATEL
    hlavni, podtitul = nadpis_kdy(uzemi, ukazatel, cil)
    kpi_vystup = []
    for typ in ["celkem", "rezidenti", "nerezidenti"]:
        kpi_vystup += [format_cislo(index_2019(uzemi, ukazatel, typ).loc[cil], 1) + " %",
                       f"rok {cil} v % roku {ZAKLAD}"]
    proti_2019, mezirocne = index_neuplny(uzemi, ukazatel, "celkem")
    if proti_2019 is None:
        kpi_vystup += ["—", "rok je úplný"]
    else:
        kpi_vystup += [format_cislo(proti_2019, 1) + " %",
                       f"leden–{MESICE[POSLEDNI_MESIC - 1]} v % stejného období {ZAKLAD}; "
                       f"meziročně {format_zmena(mezirocne, 1)} %"]
    return (hlavni, podtitul, *kpi_vystup,
            graf_index(uzemi, ukazatel, cil), graf_sezonnost(uzemi, ukazatel, cil))


@app.callback(
    Output("nadpis-kde", "children"), Output("nadpis-kde-pod", "children"),
    Output("graf-d", "figure"),
    Input("uzemi", "value"), Input("cil", "value"),
)
def list_kde(uzemi, cil):
    ukazatel = UKAZATEL
    tab = kraje_tabulka(ukazatel, cil)
    hlavni, podtitul = nadpis_kde(tab, cil)
    return hlavni, podtitul, graf_cinky_kraju(tab, ukazatel, cil, uzemi)


@app.callback(Output("graf-c", "figure"), Input("uzemi", "value"), Input("rok-mapy", "value"))
def mapa_kde(uzemi, rok):
    """Mapa C má vlastní rok (posuvník), aby šly prohlížet i roky před covidem."""
    return graf_kartogram(podil_nerez_kraju(UKAZATEL, rok), uzemi, rok)


@app.callback(
    Output("nadpis-odkud", "children"), Output("nadpis-odkud-pod", "children"),
    Output("graf-f", "figure"), Output("graf-h", "figure"),
    Input("uzemi", "value"), Input("cil", "value"),
)
def list_odkud(uzemi, cil):
    ukazatel = UKAZATEL
    hlavni, podtitul = nadpis_odkud(uzemi, ukazatel, cil)
    return hlavni, podtitul, graf_mustek(uzemi, ukazatel, cil), graf_trhy_kraju(ukazatel, cil, uzemi)


@app.callback(
    Output("panel-kdy", "style"), Output("panel-kde", "style"), Output("panel-odkud", "style"),
    Input("listy", "value"),
)
def prepni_panel(zalozka):
    """Ukáže panel vybrané záložky, ostatní skryje."""
    return [{"display": "flex"} if zalozka == z else {"display": "none"}
            for z in ["kdy", "kde", "odkud"]]


# 7. Spuštění místního serveru (port 8051) ----------------------------------------------
if __name__ == "__main__":
    app.run(debug=True, use_reloader=False, port=PORT)
