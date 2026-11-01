"""Příprava dat: spojení dvou exportů ČSÚ do jedné tabulky pro dashboard.

Cíl: z původních souborů ČSÚ vytvořit jeden přehledný CSV soubor.
Vstupy (složka data/zdroje, soubory tak, jak byly staženy z ČSÚ):
  - 020063-25data020926.zip ... obsahuje 020063-25data020926.csv z Veřejné databáze ČSÚ,
    leden 2012 – prosinec 2025 (zabaleno do ZIP kvůli velikosti 68 MB; pandas čte ZIP přímo)
  - DataStat_HUZ_podle_zemi_2025-2026.xlsx ... DataStat ČSÚ (CRU02MT2), leden 2025 – srpen 2026
Výstup: data/HUZ_podle_zemi_2012-2026_spojeno.csv

Jeden řádek výstupu = jeden měsíc × jedno území × jedna rezidence
(Celkem, Rezidenti, Nerezidenti nebo jedna země / skupina zemí).
Roky 2012–2024 bereme z prvního souboru, roky 2025–2026 z DataStatu.
Rok 2025 je v obou souborech a hodnoty se shodují (ověřeno níže).

Spuštění: Run v PyCharmu. Skript stačí spustit jednou; dashboard čte už hotový výstup.
"""

import re
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

SLOZKA_PROJEKTU = Path(__file__).resolve().parent
SLOZKA_ZDROJU = SLOZKA_PROJEKTU / "data" / "zdroje"
SOUBOR_VDB = SLOZKA_ZDROJU / "020063-25data020926.zip"
SOUBOR_DATASTAT = SLOZKA_ZDROJU / "DataStat_HUZ_podle_zemi_2025-2026.xlsx"
VYSTUP = SLOZKA_PROJEKTU / "data" / "HUZ_podle_zemi_2012-2026_spojeno.csv"

KRAJE = {
    "Česko", "Hlavní město Praha", "Středočeský kraj", "Jihočeský kraj",
    "Plzeňský kraj", "Karlovarský kraj", "Ústecký kraj", "Liberecký kraj",
    "Královéhradecký kraj", "Pardubický kraj", "Kraj Vysočina",
    "Jihomoravský kraj", "Olomoucký kraj", "Zlínský kraj", "Moravskoslezský kraj",
}
MESICE = ["leden", "únor", "březen", "duben", "květen", "červen", "červenec",
          "srpen", "září", "říjen", "listopad", "prosinec"]
UKAZATELE_VDB = {"2654": "hoste", "2655": "prenocovani"}


def nacti_vdb():
    """Dlouhý formát VDB (jeden údaj na řádek) převedeme na sloupce hoste/prenocovani."""
    data = pd.read_csv(SOUBOR_VDB, dtype=str)
    data = data.loc[data["stapro_kod"].isin(UKAZATELE_VDB)].copy()
    data["hodnota"] = pd.to_numeric(data["hodnota"])
    # Prázdná země = úhrn; "Česko" jako země původu = rezidenti.
    data["rezidence"] = data["uzemiz_txt"].fillna("Celkem").replace({"Česko": "Rezidenti"})
    data["uzemi"] = data["uzemi_txt"].replace({"Česká republika": "Česko"})
    data["ukazatel"] = data["stapro_kod"].map(UKAZATELE_VDB)
    sirka = data.pivot_table(index=["rok", "mesic", "uzemi", "rezidence"],
                             columns="ukazatel", values="hodnota",
                             aggfunc="first").reset_index()
    sirka["rok"] = sirka["rok"].astype(int)
    sirka["mesic"] = sirka["mesic"].astype(int)
    return sirka


def nacti_datastat():
    """Export z DataStatu má hierarchické řádky: rezidence → území → měsíc."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")  # export DataStatu nemá výchozí styl, varování je neškodné
        tabulka = pd.read_excel(SOUBOR_DATASTAT, header=None)
    # Data začínají pod řádkem se záhlavím ukazatelů ("Počet hostů" ve 2. sloupci).
    zacatek = tabulka.index[tabulka[1].astype(str).str.strip() == "Počet hostů"][0] + 1
    radky, rezidence, uzemi = [], None, None
    for popisek, hoste, prenocovani, _prumer in tabulka.iloc[zacatek:].itertuples(index=False):
        if pd.isna(popisek):
            continue
        popisek = str(popisek).strip()
        if popisek.startswith(("Vygenerováno", "Čas poslední", "http")):
            continue  # poznámky pod tabulkou
        mesic = re.fullmatch(r"(\S+) (\d{4})", popisek)
        if mesic and mesic.group(1) in MESICE:
            radky.append((int(mesic.group(2)), MESICE.index(mesic.group(1)) + 1,
                          uzemi, rezidence, hoste, prenocovani))
        elif popisek in KRAJE:
            uzemi = popisek
        else:
            rezidence, uzemi = popisek, None  # nový blok rezidence
    data = pd.DataFrame(radky, columns=["rok", "mesic", "uzemi", "rezidence",
                                        "hoste", "prenocovani"])
    # Znak ":" znamená, že údaj není k dispozici. Necháme prázdné, nenahrazujeme nulou.
    for sloupec in ["hoste", "prenocovani"]:
        data[sloupec] = pd.to_numeric(data[sloupec], errors="coerce")
    return data


def over_shodu_2025(vdb, datastat):
    """Rok 2025 je v obou zdrojích. Pokud se liší, spojení by nebylo spolehlivé."""
    klic = ["rok", "mesic", "uzemi", "rezidence"]
    a = vdb.loc[vdb["rok"] == 2025, klic + ["hoste"]]
    b = datastat.loc[datastat["rok"] == 2025, klic + ["hoste"]]
    spojeno = a.merge(b, on=klic, suffixes=("_vdb", "_ds"))
    rozdil = (spojeno["hoste_vdb"] - spojeno["hoste_ds"]).abs().max()
    print(f"Kontrola roku 2025: porovnáno {len(spojeno)} hodnot, max. rozdíl {rozdil}")
    if rozdil > 0:
        raise ValueError("Zdroje se pro rok 2025 liší. Zkontrolujte stažené soubory.")


def priprav():
    vdb = nacti_vdb()
    datastat = nacti_datastat()
    over_shodu_2025(vdb, datastat)

    data = pd.concat([vdb.loc[vdb["rok"] <= 2024], datastat], ignore_index=True)
    data["prumer_prenocovani"] = np.where(data["hoste"] > 0,
                                          (data["prenocovani"] / data["hoste"]).round(3),
                                          np.nan)
    data["uroven_uzemi"] = np.where(data["uzemi"] == "Česko", "stát", "kraj")
    souhrny = {"Celkem": "celkem", "Rezidenti": "rezidenti", "Nerezidenti": "nerezidenti"}
    skupina = pd.Series(np.where(data["rezidence"].str.startswith(("Ostatní", "Oceánie")),
                                 "skupina zemí", "země"), index=data.index)
    data["typ_rezidence"] = data["rezidence"].map(souhrny).fillna(skupina)
    data["datum"] = pd.to_datetime(dict(year=data["rok"], month=data["mesic"], day=1))
    data["predbezne"] = np.where(data["rok"] >= 2025, "ano", "ne")
    data["zdroj"] = np.where(data["rok"] >= 2025, "ČSÚ DataStat CRU02MT2",
                             "ČSÚ 020063 (Veřejná databáze)")

    data = data[["datum", "rok", "mesic", "uroven_uzemi", "uzemi", "typ_rezidence",
                 "rezidence", "hoste", "prenocovani", "prumer_prenocovani",
                 "predbezne", "zdroj"]].sort_values(["datum", "uzemi", "rezidence"])
    data["datum"] = data["datum"].dt.strftime("%Y-%m-%d")

    # Kontrola agregací: součet krajů = Česko.
    hoste = data.loc[data["rezidence"] == "Celkem"]
    kraje = hoste.loc[hoste["uroven_uzemi"] == "kraj"].groupby("datum")["hoste"].sum()
    cesko = hoste.loc[hoste["uroven_uzemi"] == "stát"].set_index("datum")["hoste"]
    print(f"Kontrola součtu krajů: max. rozdíl {(kraje - cesko).abs().max()}")

    VYSTUP.parent.mkdir(exist_ok=True)
    data.to_csv(VYSTUP, index=False, encoding="utf-8-sig")
    print(f"Uloženo: {VYSTUP} ({len(data)} řádků, {data['datum'].min()} až {data['datum'].max()})")


if __name__ == "__main__":
    priprav()
