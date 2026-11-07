# Návrat turistů do Česka

Autoři: Jirka Urban, Natalia Bobyleva, Maryia Shmatava

Semestrální práce do předmětu **MDIP – Interpretace a prezentace dat** (ZS 2026/2027).
Interaktivní dashboard v Pythonu (Plotly + Dash) o návštěvnosti hromadných ubytovacích
zařízení v Česku od ledna 2012 do srpna 2026.

## Otázky, na které dashboard odpovídá

1. Vrátil se cestovní ruch po pandemii na úroveň roku 2019? Kdo za rekordem stojí –
   domácí, nebo zahraniční hosté?
2. Jak silná je sezónnost a liší se mezi domácími a zahraničními hosty?
3. Které kraje jsou „zahraniční“ a které „domácí“?
4. Odkud hosté přijíždějí a jak se trhy změnily mezi prvním a posledním úplným rokem vybraného období?
5. Jak rychle se jednotlivé kraje po covidu vrátily na úroveň roku 2019 a které se tam ještě nedostaly?

## Struktura

Projekt je samostatný: všechna potřebná data jsou uvnitř této složky.

```
semestralni_projekt/
├─ app.py                  dashboard (Dash) – spouští se tímto souborem
├─ priprava_dat.py         ze zdrojů ČSÚ vytvoří spojený CSV pro dashboard
├─ requirements.txt        knihovny (stejné verze jako na workshopu)
├─ README.md
├─ nahledy/                snímky obrazovky jednotlivých záložek
└─ data/
   ├─ HUZ_podle_zemi_2012-2026_spojeno.csv   připravená data (výstup priprava_dat.py)
   ├─ kraje_CR.geojson                       hranice krajů pro mapu
   └─ zdroje/                                původní soubory stažené z ČSÚ
      ├─ 020063-25data020926.zip             CSV z Veřejné databáze ČSÚ, 01/2012–12/2025
      ├─ 020063-25schema020926.json          popis sloupců tohoto CSV
      ├─ 020063-22dds.docx                   dokumentace datové sady od ČSÚ
      └─ DataStat_HUZ_podle_zemi_2025-2026.xlsx   export z DataStatu, 01/2025–08/2026
```

Tok dat: `data/zdroje/*` → `priprava_dat.py` → `data/HUZ_podle_zemi_2012-2026_spojeno.csv` → `app.py`.

## Spuštění v PyCharmu

1. Otevřít složku `semestralni_projekt` jako projekt, zvolit Python 3.12 a vlastní virtuální prostředí.
2. V terminálu PyCharmu: `python -m pip install -r requirements.txt`
3. Run na `app.py`, potom otevřít http://127.0.0.1:8050

Dashboard čte už připravený CSV. `priprava_dat.py` ho vytvoří znovu ze zdrojů v `data/zdroje`
(např. po stažení nových měsíců z DataStatu); výsledek je při stejných zdrojích totožný.

## Ovládání a obsah

- **Filtry:** území (Česko nebo jeden ze 14 krajů), ukazatel (hosté / přenocování), období (roky).
- **Karty:** hosté, přenocování, průměrná délka pobytu, podíl zahraničních hostů.
- **Záložky:**
  - *Vývoj v čase* – měsíční řada rezidentů a nerezidentů, roční souhrn se srovnávací úrovní 2019.
  - *Sezónnost* – teplotní mapa měsíc × rok a průměrný měsíc.
  - *Kraje* – mapa podílu zahraničních hostů a pruhový graf krajů (vybraný kraj je zvýrazněn).
  - *Země původu* – 10 nejčastějších zemí a srovnání prvního a posledního úplného roku vybraného období
    (výchozí nastavení: 2012 vs. 2025; neúplný rok 2026 se do srovnání nebere).
  - *Obnova po covidu* – kraje v % roku 2019 v posledním úplném roce období a teplotní mapa let 2020–2025,
    ze které je vidět, jak rychle se který kraj vracel; přepínač všichni hosté / rezidenti / nerezidenti.
- Komentáře nad grafy se počítají z dat a mění se s filtry.

## Data

- **Zdroj:** ČSÚ, *Hosté a přenocování v hromadných ubytovacích zařízeních podle zemí*
  – Veřejná databáze, kód 020063 (leden 2012 – prosinec 2025):
    https://csu.gov.cz/produkty/hoste-a-prenocovani-v-hromadnych-ubytovacich-zarizenich-podle-zemi
  – DataStat, tabulka CRU02MT2 (leden 2025 – srpen 2026), stav k 9. 10. 2026:
    https://data.csu.gov.cz/datastat/data/VYBER/CRU02MT2
- Rok 2025 je v obou zdrojích a hodnoty se shodují (kontrola v `priprava_dat.py`).
- **Jeden řádek** = jeden měsíc × jedno území × jedna skupina hostů
  (celkem / rezidenti / nerezidenti / jedna země / skupina zemí).
- Součet krajů = Česko; rezidenti + nerezidenti = celkem; součet zemí = nerezidenti.
  Proto je nutné vždy filtrovat jednu úroveň, jinak by se hosté započetli vícekrát.
- **Hranice krajů:** ČÚZK přes geoBoundaries, CZE ADM1 (CC BY 4.0): https://www.geoboundaries.org

## Omezení dat

- Jen hromadná ubytovací zařízení (min. 5 pokojů a 10 lůžek); soukromé ubytování a Airbnb nejsou zahrnuty.
- Host = příjezd, ne unikátní osoba.
- 2025–2026 jsou předběžná data; 2026 obsahuje jen leden–srpen (v grafech označeno).
- Část hodnot ČSÚ dopočítává za zařízení bez vyplněného dotazníku.
- Některé země jsou v číselníku až od roku 2015 nebo 2022 (dříve ve skupinách „Ostatní…“).
- Chybějící kombinace (malé země × malé kraje) **nedoplňujeme nulou**.
- 2020–2021: propad kvůli pandemii covid-19 (v grafu vyznačeno).
