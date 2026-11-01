"""Návrat turistů do Česka: návštěvnost hromadných ubytovacích zařízení 2012–2026.

Semestrální práce MDIP – Interpretace a prezentace dat (ZS 2026/2027).
Autoři: Jirka Urban, Natalia Bobyleva, Maryia Shmatava.
Dashboard v Dash + Plotly podle postupu z příkladů Dash01–Dash12.

Data: ČSÚ, Hosté a přenocování v hromadných ubytovacích zařízeních podle zemí
(020063, DataStat CRU02MT2), měsíčně leden 2012 – srpen 2026, Česko a 14 krajů.
Soubor data/HUZ_podle_zemi_2012-2026_spojeno.csv vytváří skript priprava_dat.py.
Jeden řádek = jeden měsíc × jedno území × jedna skupina hostů (celkem,
rezidenti, nerezidenti, jedna země nebo skupina zemí).

Spuštění: Run v PyCharmu, potom http://127.0.0.1:8050. Po úpravě kódu Stop a znovu Run.
Mapa souboru: 1. data, 2. pomocné funkce a vzhled, 3. grafy, 4. layout, 5. callback, 6. server.
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

POSLEDNI_DATUM = df["datum"].max()          # srpen 2026
POSLEDNI_ROK = int(POSLEDNI_DATUM.year)
NEUPLNY_ROK = POSLEDNI_ROK if POSLEDNI_DATUM.month < 12 else None
PRVNI_ROK = int(df["rok"].min())
SROVNAVACI_ROK = 2019                       # poslední rok před pandemií
POSLEDNI_UPLNY_ROK = POSLEDNI_ROK - 1 if NEUPLNY_ROK else POSLEDNI_ROK

KRAJE = sorted(df.loc[df["uroven_uzemi"] == "kraj", "uzemi"].unique())
MOZNOSTI_UZEMI = [{"label": "Česko celkem", "value": "Česko"}] + \
                 [{"label": k, "value": k} for k in KRAJE]
AUTORI = ["Jirka Urban", "Natalia Bobyleva", "Maryia Shmatava"]
UKAZATELE = {"hoste": "Počet hostů", "prenocovani": "Počet přenocování"}
MESICE = ["leden", "únor", "březen", "duben", "květen", "červen", "červenec",
          "srpen", "září", "říjen", "listopad", "prosinec"]
MESICE_ZKR = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII"]

# Vzhled: barvy prověřené na rozlišitelnost i pro poruchy barvocitu.
BARVA_REZIDENTI = "#2a78d6"     # modrá
BARVA_NEREZIDENTI = "#eb6834"   # oranžová
BARVA_SEDA = "#b9b8b2"
TMAVA = "#0b0b0b"
SEDY_TEXT = "#52514e"
POZADI = "#f4f4f1"
PLOCHA = "#fcfcfb"
MODRA_SKALA = ["#e6f0fb", "#a9cbf2", "#5d9ee6", "#2a78d6", "#174f94", "#0b2e5c"]

STYL_RADKU = {"display": "flex", "flexWrap": "wrap", "gap": "18px"}
STYL_KARTY = {"backgroundColor": PLOCHA, "borderRadius": "12px", "padding": "20px",
              "flex": "1 1 200px", "minWidth": 0, "borderTop": f"4px solid {BARVA_REZIDENTI}",
              "boxShadow": "0 2px 8px #10243b10"}
STYL_PANELU = {"backgroundColor": PLOCHA, "borderRadius": "12px", "overflow": "hidden",
               "flex": "1 1 480px", "minWidth": 0}


# 2. Pomocné funkce -------------------------------------------------------------
def format_cislo(hodnota, desetinna=0):
    """Český zápis: mezera mezi tisíci, desetinná čárka. Chybějící hodnota = pomlčka."""
    if pd.isna(hodnota):
        return "—"
    text = f"{hodnota:,.{desetinna}f}".replace(",", " ").replace(".", ",")
    return text


def format_mil(hodnota):
    return "—" if pd.isna(hodnota) else format_cislo(hodnota / 1e6, 2) + " mil."


def soucet(rada):
    """Součet, který z úplně chybějících hodnot nevyrobí nulu (min_count=1)."""
    return rada.sum(min_count=1)


def popis_obdobi(od, do):
    konec = f"{MESICE[POSLEDNI_DATUM.month - 1]} {do}" if do == NEUPLNY_ROK else f"prosinec {do}"
    return f"leden {od} – {konec}"


def vyber(uzemi, od, do, typ=None, rezidence=None):
    """Řádky pro jedno území a období. Globální df neměníme."""
    maska = (df["uzemi"] == uzemi) & df["rok"].between(od, do)
    if typ is not None:
        maska &= df["typ_rezidence"].isin(typ if isinstance(typ, list) else [typ])
    if rezidence is not None:
        maska &= df["rezidence"] == rezidence
    return df.loc[maska]


def uprav_graf(fig, vyska=380, legenda=False):
    fig.update_layout(
        template="plotly_white", height=vyska, separators=", ",
        font=dict(family="Arial", color=TMAVA, size=13),
        paper_bgcolor=PLOCHA, plot_bgcolor=PLOCHA,
        margin=dict(l=70, r=25, t=70, b=55), title_font_size=18,
        showlegend=legenda,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0,
                    title_text="", traceorder="normal"),
        hoverlabel=dict(bgcolor="white", font_size=13),
    )
    if legenda:
        fig.update_layout(margin=dict(t=95))
    fig.update_xaxes(gridcolor="#ebebe7", linecolor="#c9c8c2")
    fig.update_yaxes(gridcolor="#ebebe7", linecolor="#c9c8c2")
    return fig


def prazdny_graf(nadpis, zprava="Pro tento výběr nejsou k dispozici data.<br>Změňte filtry."):
    fig = go.Figure()
    fig.add_annotation(text=zprava, x=0.5, y=0.5, xref="paper", yref="paper",
                       showarrow=False, font=dict(size=15, color=SEDY_TEXT))
    fig.update_layout(title=nadpis)
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    return uprav_graf(fig)


# 3. Grafy (každá funkce dostane parametry výběru a vrátí figure) ----------------
def graf_mesicni_vyvoj(uzemi, ukazatel, od, do):
    data = vyber(uzemi, od, do, typ=["rezidenti", "nerezidenti"])
    if data.empty:
        return prazdny_graf("Měsíční vývoj")
    data = data.assign(skupina=data["typ_rezidence"].map(
        {"rezidenti": "Rezidenti (hosté z Česka)", "nerezidenti": "Nerezidenti (zahraniční hosté)"}))
    fig = px.line(data, x="datum", y=ukazatel, color="skupina",
                  color_discrete_map={"Rezidenti (hosté z Česka)": BARVA_REZIDENTI,
                                      "Nerezidenti (zahraniční hosté)": BARVA_NEREZIDENTI},
                  category_orders={"skupina": ["Rezidenti (hosté z Česka)",
                                               "Nerezidenti (zahraniční hosté)"]},
                  title=f"{UKAZATELE[ukazatel]} po měsících",
                  labels={"datum": "Měsíc", ukazatel: UKAZATELE[ukazatel], "skupina": ""})
    fig.update_traces(line_width=2,
                      hovertemplate="%{x|%m/%Y}<br>%{y:,.0f}<extra>%{fullData.name}</extra>")
    if od <= 2020 <= do:
        fig.add_vrect(x0="2020-03-01", x1="2021-05-31", fillcolor="#9a9a95", opacity=0.12,
                      line_width=0, annotation_text="pandemie covid-19",
                      annotation_position="top left",
                      annotation_font=dict(size=11, color=SEDY_TEXT))
    fig.update_yaxes(rangemode="tozero", tickformat=",.0f")
    # Popisek osy pro každý rok (začátek ledna), ne automaticky po dvou letech.
    fig.update_xaxes(dtick="M12", tickformat="%Y", tickangle=-45 if do - od > 8 else 0)
    return uprav_graf(fig, legenda=True)


def graf_rocni_souhrn(uzemi, ukazatel, od, do):
    data = vyber(uzemi, od, do, typ="celkem")
    if data.empty:
        return prazdny_graf("Roční souhrn")
    rocne = data.groupby("rok", as_index=False)[ukazatel].agg(soucet)
    rocne["popisek"] = rocne["rok"].astype(str)
    rocne["neuplny"] = rocne["rok"] == NEUPLNY_ROK
    if NEUPLNY_ROK in rocne["rok"].values:
        rocne.loc[rocne["neuplny"], "popisek"] = f"{NEUPLNY_ROK}*"
    barvy = [BARVA_SEDA if n else BARVA_REZIDENTI for n in rocne["neuplny"]]
    fig = go.Figure(go.Bar(
        x=rocne["popisek"], y=rocne[ukazatel], marker_color=barvy,
        marker_pattern_shape=["/" if n else "" for n in rocne["neuplny"]],
        hovertemplate="%{x}<br>%{y:,.0f}<extra></extra>"))
    # Srovnávací čára: úroveň roku 2019 (před pandemií).
    uroven_2019 = soucet(vyber(uzemi, SROVNAVACI_ROK, SROVNAVACI_ROK, typ="celkem")[ukazatel])
    fig.add_hline(y=uroven_2019, line_dash="dash", line_color=SEDY_TEXT, line_width=1.5,
                  annotation_text=f"úroveň {SROVNAVACI_ROK}", annotation_position="top left",
                  annotation_font=dict(size=11, color=SEDY_TEXT))
    fig.update_layout(title=f"{UKAZATELE[ukazatel]} za rok", bargap=0.25)
    fig.update_xaxes(title_text="Rok", type="category")
    fig.update_yaxes(title_text=UKAZATELE[ukazatel], tickformat=",.0f", rangemode="tozero")
    if NEUPLNY_ROK and od <= NEUPLNY_ROK <= do:
        fig.add_annotation(text=f"* {NEUPLNY_ROK}: pouze leden–{MESICE[POSLEDNI_DATUM.month - 1]}, "
                                "předběžná data", x=1, y=-0.17, xref="paper", yref="paper",
                           xanchor="right", showarrow=False, font=dict(size=11, color=SEDY_TEXT))
    return uprav_graf(fig)


def graf_sezonnost(uzemi, ukazatel, od, do):
    data = vyber(uzemi, od, do, typ="celkem")
    if data.empty:
        return prazdny_graf("Sezónnost")
    tabulka = data.pivot_table(index="mesic", columns="rok", values=ukazatel, aggfunc="sum")
    tabulka = tabulka.reindex(range(1, 13))  # chybějící měsíce zůstanou prázdné, ne nulové
    fig = go.Figure(go.Heatmap(
        z=tabulka.values, x=[str(r) for r in tabulka.columns], y=MESICE,
        colorscale=MODRA_SKALA, xgap=2, ygap=2, hoverongaps=False,
        colorbar=dict(title=dict(text=UKAZATELE[ukazatel], side="right"), tickformat=",.0f"),
        hovertemplate="%{y} %{x}<br>%{z:,.0f}<extra></extra>"))
    fig.update_layout(title=f"{UKAZATELE[ukazatel]}: měsíc × rok")
    fig.update_yaxes(autorange="reversed", title_text="")
    fig.update_xaxes(title_text="Rok", type="category")
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=False)
    return uprav_graf(fig, vyska=460)


def graf_profil_mesicu(uzemi, ukazatel, od, do):
    """Průměrný měsíc přes vybrané roky: rezidenti a nerezidenti zvlášť."""
    data = vyber(uzemi, od, do, typ=["rezidenti", "nerezidenti"])
    if data.empty:
        return prazdny_graf("Průměrný rok")
    profil = data.groupby(["mesic", "typ_rezidence"], as_index=False)[ukazatel].mean()
    profil["mesic_txt"] = profil["mesic"].map(lambda m: MESICE_ZKR[m - 1])
    profil["skupina"] = profil["typ_rezidence"].map({"rezidenti": "Rezidenti",
                                                     "nerezidenti": "Nerezidenti"})
    fig = px.bar(profil, x="mesic_txt", y=ukazatel, color="skupina", barmode="stack",
                 color_discrete_map={"Rezidenti": BARVA_REZIDENTI,
                                     "Nerezidenti": BARVA_NEREZIDENTI},
                 category_orders={"mesic_txt": MESICE_ZKR,
                                  "skupina": ["Rezidenti", "Nerezidenti"]},
                 title=f"Průměrný měsíc ({od}–{do})",
                 labels={"mesic_txt": "Měsíc", ukazatel: f"Průměr: {UKAZATELE[ukazatel].lower()}",
                         "skupina": ""})
    fig.update_traces(marker_line_color=PLOCHA, marker_line_width=1,
                      hovertemplate="%{x}<br>%{y:,.0f}<extra>%{fullData.name}</extra>")
    fig.update_yaxes(tickformat=",.0f")
    return uprav_graf(fig, vyska=460, legenda=True)


def souhrn_kraju(ukazatel, od, do):
    data = df.loc[(df["uroven_uzemi"] == "kraj") & df["rok"].between(od, do)
                  & df["typ_rezidence"].isin(["celkem", "nerezidenti"])]
    tab = data.pivot_table(index="uzemi", columns="typ_rezidence", values=ukazatel,
                           aggfunc="sum").reset_index()
    tab["podil_nerez"] = tab["nerezidenti"] / tab["celkem"] * 100
    return tab


def graf_mapa_kraju(ukazatel, od, do, zvyrazneny):
    tab = souhrn_kraju(ukazatel, od, do)
    fig = px.choropleth_map(
        tab, geojson=KRAJE_GEO, locations="uzemi", featureidkey="properties.kraj",
        color="podil_nerez", color_continuous_scale=MODRA_SKALA, range_color=(0, 85),
        map_style="white-bg", center=dict(lat=49.8, lon=15.45), zoom=5.6, opacity=0.95,
        custom_data=["celkem", "nerezidenti"],
        title=f"Podíl zahraničních hostů podle krajů ({od}–{do})",
        labels={"podil_nerez": "Podíl nerezidentů (%)"})
    fig.update_traces(
        marker_line_color="white", marker_line_width=1,
        hovertemplate="<b>%{location}</b><br>Podíl nerezidentů: %{z:.1f} %<br>"
                      f"{UKAZATELE[ukazatel]} celkem: " + "%{customdata[0]:,.0f}<extra></extra>")
    if zvyrazneny != "Česko":
        vybrany = [f for f in KRAJE_GEO["features"] if f["properties"]["kraj"] == zvyrazneny]
        fig.add_trace(go.Choroplethmap(
            geojson={"type": "FeatureCollection", "features": vybrany},
            locations=[zvyrazneny], featureidkey="properties.kraj", z=[0],
            colorscale=[[0, "rgba(0,0,0,0)"], [1, "rgba(0,0,0,0)"]], showscale=False,
            marker_line_color=TMAVA, marker_line_width=3, hoverinfo="skip"))
    fig.update_layout(coloraxis_colorbar=dict(title="%", ticksuffix=" %"))
    fig = uprav_graf(fig, vyska=430)
    fig.update_layout(margin=dict(l=10, r=10, t=60, b=10))
    return fig


def graf_kraje_sloupce(ukazatel, od, do, zvyrazneny):
    tab = souhrn_kraju(ukazatel, od, do)
    tab["rezidenti"] = tab["celkem"] - tab["nerezidenti"]
    tab = tab.sort_values("celkem")
    fig = go.Figure()
    for sloupec, nazev, barva in [("rezidenti", "Rezidenti", BARVA_REZIDENTI),
                                  ("nerezidenti", "Nerezidenti", BARVA_NEREZIDENTI)]:
        fig.add_trace(go.Bar(
            y=tab["uzemi"], x=tab[sloupec], name=nazev, orientation="h", marker_color=barva,
            marker_line_color=PLOCHA, marker_line_width=1,
            marker_opacity=[1 if zvyrazneny in ("Česko", k) else 0.35 for k in tab["uzemi"]],
            hovertemplate="%{y}<br>" + nazev + ": %{x:,.0f}<extra></extra>"))
    fig.update_layout(barmode="stack", title=f"{UKAZATELE[ukazatel]} podle krajů ({od}–{do})")
    fig.update_xaxes(tickformat=",.0f", title_text=UKAZATELE[ukazatel])
    fig = uprav_graf(fig, vyska=430, legenda=True)
    fig.update_layout(margin=dict(l=160, r=25, t=95, b=55))
    return fig


def graf_top_zeme(uzemi, ukazatel, od, do):
    data = vyber(uzemi, od, do, typ="země")
    nadpis = f"10 nejčastějších zemí původu ({od}–{do})"
    if data.empty:
        return prazdny_graf(nadpis)
    top = data.groupby("rezidence", as_index=False)[ukazatel].agg(soucet).dropna()
    top = top.nlargest(10, ukazatel).sort_values(ukazatel)
    nerez = soucet(vyber(uzemi, od, do, typ="nerezidenti")[ukazatel])
    top["podil"] = top[ukazatel] / nerez * 100
    fig = go.Figure(go.Bar(
        y=top["rezidence"], x=top[ukazatel], orientation="h", marker_color=BARVA_NEREZIDENTI,
        customdata=top["podil"], text=top["podil"].map(lambda p: format_cislo(p, 1) + " %"),
        textposition="outside", cliponaxis=False, textfont=dict(color=SEDY_TEXT, size=12),
        hovertemplate="%{y}<br>%{x:,.0f}<br>%{customdata:.1f} % všech zahraničních<extra></extra>"))
    fig.update_layout(title=nadpis + "<br><sup>popisek = podíl na všech zahraničních "
                                     "hostech v daném území</sup>")
    fig.update_xaxes(tickformat=",.0f", title_text=UKAZATELE[ukazatel], nticks=5)
    fig = uprav_graf(fig, vyska=430)
    fig.update_layout(margin=dict(l=200, r=70, t=80, b=55))
    return fig


def graf_zmena_zemi(uzemi, ukazatel, od, do):
    """Činkový graf: první vs. poslední rok vybraného období pro 12 největších zemí.

    Neúplný poslední rok (2026) by se s celým rokem nedal férově srovnat,
    proto místo něj použijeme poslední úplný rok a v nadpisu to uvedeme.
    """
    a = od
    b = do - 1 if do == NEUPLNY_ROK else do
    poznamka = f"<br><sup>{NEUPLNY_ROK} je neúplný rok, proto srovnáváme s rokem {b}</sup>" \
        if do == NEUPLNY_ROK and b > a else ""
    if b <= a:
        return prazdny_graf("Jak se změnily trhy",
                            "Vyberte alespoň dva roky.<br>"
                            f"Neúplný rok {NEUPLNY_ROK} se do srovnání nepočítá.")
    nadpis = f"Jak se změnily trhy: {a} vs. {b}{poznamka}"
    data = vyber(uzemi, a, b, typ="země")
    data = data.loc[data["rok"].isin([a, b])]
    if data.empty:
        return prazdny_graf(nadpis)
    tab = data.pivot_table(index="rezidence", columns="rok", values=ukazatel, aggfunc="sum")
    # Země, které v jednom z let chybí (např. nové v číselníku od 2015/2022), nelze srovnat.
    tab = tab.reindex(columns=[a, b]).dropna()
    if tab.empty:
        return prazdny_graf(nadpis)
    tab = tab.loc[tab.max(axis=1).nlargest(12).index].sort_values(b)
    tab["zmena"] = (tab[b] / tab[a] - 1) * 100
    fig = go.Figure()
    for zeme, radek in tab.iterrows():
        fig.add_trace(go.Scatter(x=[radek[a], radek[b]], y=[zeme, zeme], mode="lines",
                                 line=dict(color="#d6d5cf", width=3), hoverinfo="skip",
                                 showlegend=False))
    fig.add_trace(go.Scatter(x=tab[a], y=tab.index, mode="markers", name=str(a),
                             marker=dict(color=BARVA_SEDA, size=11,
                                         line=dict(color=PLOCHA, width=2)),
                             hovertemplate="%{y}<br>" + str(a) + ": %{x:,.0f}<extra></extra>"))
    fig.add_trace(go.Scatter(x=tab[b], y=tab.index, mode="markers+text", name=str(b),
                             marker=dict(color=BARVA_NEREZIDENTI, size=11,
                                         line=dict(color=PLOCHA, width=2)),
                             text=tab["zmena"].map(lambda z: ("+" if z > 0 else "−")
                                                   + format_cislo(abs(z), 0) + " %"),
                             textposition="middle right", textfont=dict(size=11, color=SEDY_TEXT),
                             customdata=tab["zmena"],
                             hovertemplate="%{y}<br>" + str(b) + ": %{x:,.0f}"
                                           "<br>změna: %{customdata:+.1f} %<extra></extra>"))
    fig.update_layout(title=nadpis)
    fig.update_xaxes(tickformat=",.0f", title_text=UKAZATELE[ukazatel], nticks=5,
                     range=[0, tab[[a, b]].max().max() * 1.15])
    fig = uprav_graf(fig, vyska=430, legenda=True)
    fig.update_layout(margin=dict(l=200, r=30, t=115 if poznamka else 95, b=55))
    return fig


# Komentáře vypočtené z dat (mění se spolu s filtry) ---------------------------
def komentar_vyvoj(uzemi, ukazatel):
    def rok(r, typ):
        return soucet(vyber(uzemi, r, r, typ=typ)[ukazatel])
    a, b = SROVNAVACI_ROK, POSLEDNI_UPLNY_ROK
    celkem = rok(b, "celkem") / rok(a, "celkem") * 100 - 100
    rez = rok(b, "rezidenti") / rok(a, "rezidenti") * 100 - 100
    nerez = rok(b, "nerezidenti") / rok(a, "nerezidenti") * 100 - 100

    def pct(x):
        return ("+" if x >= 0 else "−") + format_cislo(abs(x), 1) + " %"
    return (f"{UKAZATELE[ukazatel]} ({'Česko' if uzemi == 'Česko' else uzemi}) v roce {b} "
            f"oproti předpandemickému roku {a}: celkem {pct(celkem)}, z toho rezidenti "
            f"{pct(rez)} a nerezidenti {pct(nerez)}.")


def komentar_sezonnost(uzemi, ukazatel, od, do):
    data = vyber(uzemi, od, do, typ="celkem")
    if data.empty:
        return ""
    prumer = data.groupby("mesic")[ukazatel].mean()
    nej, nejmene = prumer.idxmax(), prumer.idxmin()
    return (f"Nejsilnější měsíc ve vybraném období je v průměru {MESICE[nej - 1]}, "
            f"nejslabší {MESICE[nejmene - 1]}. Rozdíl mezi nimi je "
            f"{format_cislo(prumer.max() / prumer.min(), 1)}násobný.")


def komentar_kraje(ukazatel, od, do):
    tab = souhrn_kraju(ukazatel, od, do)
    praha = tab.loc[tab["uzemi"] == "Hlavní město Praha"].iloc[0]
    podil_prahy = praha["celkem"] / tab["celkem"].sum() * 100
    mimo = tab.loc[tab["uzemi"] != "Hlavní město Praha"].sort_values("podil_nerez")
    return (f"Praha má {format_cislo(podil_prahy, 1)} % všech "
            f"{'hostů' if ukazatel == 'hoste' else 'přenocování'} a "
            f"{format_cislo(praha['podil_nerez'], 1)} % z nich tvoří zahraniční hosté. "
            f"Mimo Prahu má nejvyšší podíl zahraničních hostů {mimo.iloc[-1]['uzemi']} "
            f"({format_cislo(mimo.iloc[-1]['podil_nerez'], 1)} %), nejnižší "
            f"{mimo.iloc[0]['uzemi']} ({format_cislo(mimo.iloc[0]['podil_nerez'], 1)} %).")


# 4. Komponenty a rozvržení ------------------------------------------------------
def vytvor_kartu(nazev, id_hodnoty, vysvetleni):
    return html.Div([
        html.P(nazev, style={"margin": "0 0 10px", "color": SEDY_TEXT}),
        html.Div(id=id_hodnoty, style={"fontSize": "30px", "fontWeight": "700",
                                       "color": TMAVA}),
        html.P(vysvetleni, id=f"{id_hodnoty}-popis",
               style={"fontSize": "13px", "color": SEDY_TEXT, "margin": "8px 0 0"}),
    ], style=STYL_KARTY)


def vytvor_filtr(nazev, ovladac, sirka="1 1 240px"):
    return html.Div([
        html.Label(nazev, style={"display": "block", "fontWeight": "700",
                                 "marginBottom": "8px"}),
        ovladac,
    ], style={"flex": sirka, "minWidth": 0})


def graf(id_grafu):
    return html.Div(dcc.Graph(id=id_grafu, config={"displaylogo": False}), style=STYL_PANELU)


def komentar(id_textu):
    return html.P(id=id_textu, role="status",
                  style={"backgroundColor": PLOCHA, "borderLeft": f"4px solid {BARVA_REZIDENTI}",
                         "padding": "14px 18px", "borderRadius": "8px", "margin": "0 0 18px",
                         "color": TMAVA, "fontSize": "15px"})


# Značka pro každý rok, aby byly vidět i roky jako 2019 (dříve jen každý druhý rok).
znacky_let = {r: {"label": str(r), "style": {"fontSize": "11px"}}
              for r in range(PRVNI_ROK, POSLEDNI_ROK + 1)}
if NEUPLNY_ROK:
    znacky_let[POSLEDNI_ROK]["label"] += "*"

app = Dash(__name__)
app.title = "Návrat turistů do Česka"
app.layout = html.Div([
    html.Header([
        html.P("MDIP · INTERPRETACE A PREZENTACE DAT · SEMESTRÁLNÍ PRÁCE",
               style={"color": "#a9cbf2", "fontSize": "13px", "fontWeight": "700",
                      "letterSpacing": "2px", "margin": 0}),
        html.H1("Návrat turistů do Česka", style={"fontSize": "36px", "margin": "10px 0"}),
        html.P(f"Hosté a přenocování v hromadných ubytovacích zařízeních, "
               f"{popis_obdobi(PRVNI_ROK, POSLEDNI_ROK)}. Zdroj: ČSÚ.",
               style={"color": "#d4dbe6", "margin": 0}),
        html.P(f"Autoři: {', '.join(AUTORI)}",
               style={"color": "#a9cbf2", "margin": "12px 0 0", "fontSize": "14px"}),
    ], style={"backgroundColor": "#0b2e5c", "color": "white", "padding": "28px",
              "borderRadius": "14px", "marginBottom": "20px"}),

    html.Div([
        html.Div([
            vytvor_filtr("Území", dcc.Dropdown(id="uzemi", options=MOZNOSTI_UZEMI,
                                               value="Česko", clearable=False)),
            vytvor_filtr("Ukazatel", dcc.RadioItems(
                id="ukazatel", value="hoste", inline=True,
                options=[{"label": f" {v}", "value": k} for k, v in UKAZATELE.items()],
                labelStyle={"marginRight": "18px"})),
            vytvor_filtr("Období (roky)", dcc.RangeSlider(
                id="roky", min=PRVNI_ROK, max=POSLEDNI_ROK, step=1,
                value=[PRVNI_ROK, POSLEDNI_ROK], marks=znacky_let, allowCross=True),
                sirka="2 1 420px"),
        ], style=STYL_RADKU),
        html.P(id="popis-vyberu", role="status",
               style={"fontSize": "14px", "color": SEDY_TEXT, "margin": "14px 0 0"}),
    ], style={"backgroundColor": PLOCHA, "padding": "20px", "borderRadius": "12px",
              "marginBottom": "20px"}),

    html.Div([
        vytvor_kartu("Hosté", "kpi-hoste", "Počet příjezdů do ubytovacích zařízení"),
        vytvor_kartu("Přenocování", "kpi-prenocovani", "Počet strávených nocí"),
        vytvor_kartu("Průměrná délka pobytu", "kpi-delka", "Přenocování na jednoho hosta"),
        vytvor_kartu("Zahraniční hosté", "kpi-nerez", "Podíl nerezidentů na všech hostech"),
    ], style=STYL_RADKU),

    dcc.Tabs(id="zalozky", value="vyvoj", style={"marginTop": "20px"}, children=[
        dcc.Tab(label="Vývoj v čase", value="vyvoj", children=[
            html.Div(style={"height": "18px"}),
            komentar("text-vyvoj"),
            html.Div([graf("graf-mesice"), graf("graf-roky")], style=STYL_RADKU),
        ]),
        dcc.Tab(label="Sezónnost", value="sezonnost", children=[
            html.Div(style={"height": "18px"}),
            komentar("text-sezonnost"),
            html.Div([graf("graf-heatmapa"), graf("graf-profil")], style=STYL_RADKU),
        ]),
        dcc.Tab(label="Kraje", value="kraje", children=[
            html.Div(style={"height": "18px"}),
            komentar("text-kraje"),
            html.Div([graf("graf-mapa"), graf("graf-kraje")], style=STYL_RADKU),
        ]),
        dcc.Tab(label="Země původu", value="zeme", children=[
            html.Div(style={"height": "18px"}),
            html.Div([graf("graf-top-zeme"), graf("graf-zmena-zemi")], style=STYL_RADKU),
        ]),
    ]),

    html.Details([
        html.Summary("Jak číst přehled a omezení dat",
                     style={"fontWeight": "700", "cursor": "pointer"}),
        html.Ul([
            html.Li("Hromadné ubytovací zařízení = minimálně 5 pokojů a 10 lůžek. "
                    "Soukromé ubytování a platformy typu Airbnb v datech nejsou."),
            html.Li("Host = jeden příjezd; tentýž člověk může být započten vícekrát. "
                    "Rezidenti jsou hosté s trvalým pobytem v Česku, nerezidenti ze zahraničí."),
            html.Li(f"Roky 2025–{POSLEDNI_ROK} jsou předběžné. "
                    + (f"Rok {NEUPLNY_ROK} obsahuje jen leden–"
                       f"{MESICE[POSLEDNI_DATUM.month - 1]}." if NEUPLNY_ROK else "")),
            html.Li("Část hodnot ČSÚ statisticky dopočítává za zařízení, která nevyplnila dotazník."),
            html.Li("Chybějící údaje (malé země v malých krajích, nové země v číselníku od "
                    "2015 a 2022) nedoplňujeme nulou, v grafech zůstávají prázdné."),
            html.Li("Skupiny zemí (např. Ostatní asijské země) do žebříčku zemí nezařazujeme."),
            html.Li("Mapa a graf krajů ukazují vždy všechny kraje; vybraný kraj je zvýrazněn."),
        ], style={"margin": "10px 0 0", "paddingLeft": "20px"}),
    ], style={"backgroundColor": PLOCHA, "padding": "16px 20px", "borderRadius": "12px",
              "marginTop": "20px", "fontSize": "14px", "color": SEDY_TEXT}),

    html.Footer([
        html.P("Zdroj dat: ČSÚ, Hosté a přenocování v hromadných ubytovacích zařízeních podle "
               "zemí (020063; DataStat CRU02MT2), stav k 9. 10. 2026. Hranice krajů: ČÚZK "
               "via geoBoundaries (CC BY 4.0)."),
        html.P(f"Semestrální práce MDIP, ZS 2026/2027. Autoři: {', '.join(AUTORI)}."),
    ], style={"fontSize": "12px", "color": SEDY_TEXT, "marginTop": "14px"}),
], style={"fontFamily": "Arial, sans-serif", "color": TMAVA, "backgroundColor": POZADI,
          "maxWidth": "1320px", "margin": "0 auto", "padding": "24px"})


# 5. Callback: všechny výstupy počítáme ze stejného výběru ------------------------
@app.callback(
    Output("kpi-hoste", "children"),
    Output("kpi-prenocovani", "children"),
    Output("kpi-delka", "children"),
    Output("kpi-nerez", "children"),
    Output("popis-vyberu", "children"),
    Output("text-vyvoj", "children"),
    Output("graf-mesice", "figure"),
    Output("graf-roky", "figure"),
    Output("text-sezonnost", "children"),
    Output("graf-heatmapa", "figure"),
    Output("graf-profil", "figure"),
    Output("text-kraje", "children"),
    Output("graf-mapa", "figure"),
    Output("graf-kraje", "figure"),
    Output("graf-top-zeme", "figure"),
    Output("graf-zmena-zemi", "figure"),
    Input("uzemi", "value"),
    Input("ukazatel", "value"),
    Input("roky", "value"),
)
def aktualizuj_dashboard(uzemi, ukazatel, roky):
    od, do = sorted(roky)
    celkem = vyber(uzemi, od, do, typ="celkem")
    nerez = vyber(uzemi, od, do, typ="nerezidenti")
    hoste = soucet(celkem["hoste"])
    noci = soucet(celkem["prenocovani"])
    delka = noci / hoste if hoste else float("nan")
    podil = soucet(nerez["hoste"]) / hoste * 100 if hoste else float("nan")

    popis = (f"Území: {'Česko celkem' if uzemi == 'Česko' else uzemi}. "
             f"Období: {popis_obdobi(od, do)}"
             + (" (poslední rok neúplný, předběžná data)." if do == NEUPLNY_ROK else "."))
    return (
        format_mil(hoste),
        format_mil(noci),
        "—" if pd.isna(delka) else format_cislo(delka, 2) + " noci",
        "—" if pd.isna(podil) else format_cislo(podil, 1) + " %",
        popis,
        komentar_vyvoj(uzemi, ukazatel),
        graf_mesicni_vyvoj(uzemi, ukazatel, od, do),
        graf_rocni_souhrn(uzemi, ukazatel, od, do),
        komentar_sezonnost(uzemi, ukazatel, od, do),
        graf_sezonnost(uzemi, ukazatel, od, do),
        graf_profil_mesicu(uzemi, ukazatel, od, do),
        komentar_kraje(ukazatel, od, do),
        graf_mapa_kraju(ukazatel, od, do, uzemi),
        graf_kraje_sloupce(ukazatel, od, do, uzemi),
        graf_top_zeme(uzemi, ukazatel, od, do),
        graf_zmena_zemi(uzemi, ukazatel, od, do),
    )


# 6. Spuštění místního serveru ---------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)
