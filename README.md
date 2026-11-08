# Návrat turistů do Česka po covidu

Autoři: Jirka Urban, Natalia Bobyleva, Maryia Shmatava

Semestrální práce do předmětu **MDIP – Interpretace a prezentace dat** (ZS 2026/2027).
Interaktivní dashboard v Pythonu (Plotly + Dash) o tom, jak se turisté vrátili do českých
hromadných ubytovacích zařízení po pandemii covidu-19. Jedna příběhová linka
**kdy → kde → odkud** a jedna srovnávací základna: **rok 2019 proti zvolenému roku**
(výchozí poslední úplný rok 2025).

| Záložka | Akční nadpis (výchozí stav) | Grafy |
| --- | --- | --- |
| Kdy | Rekord táhnou domácí hosté | 4 KPI v % roku 2019, A roční index 2019 = 100, B sezónnost (tis. hostů v měsíci) |
| Kde | Domácí hosté rostou téměř všude, zahraniční ne | C kartogram podílu cizinců 2019 (5 tříd), D činky krajů, E kraj × rok |
| Odkud | Zahraniční hosté se vrátili, ale jiní | F změna podle zemí, H tabulka krajů |

Nadpisy záložek se počítají z dat a mění se s filtry (území, rok srovnání s 2019).

## Spuštění

1. Otevřít složku projektu v PyCharmu, Python 3.12, vlastní virtuální prostředí.
2. `python -m pip install -r requirements.txt`
3. Run na `app.py`, potom http://127.0.0.1:8051

## Data

`data/HUZ_podle_zemi_2012-2026_spojeno.csv` (výstup `priprava_dat.py` ze zdrojů ČSÚ
v `data/zdroje`) a `data/kraje_CR.geojson` (hranice krajů).
Jen hromadná ubytovací zařízení; 2025–2026 předběžná data; chybějící kombinace země × kraj
nedoplňujeme nulou.
