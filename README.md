# Project_3 - Election Scraper

Tento skript stáhne a zpracuje výsledky voleb z portálu **volby.cz** pro zvolený **okres** a uloží je do CSV. Vstupem je URL stránky typu **ps3** (seznam okresů pro dané volby) a výstupní název CSV.

## Co skript dělá (stručně)

1. Načte stránku **ps3** (seznam okresů) a najde řádek s požadovaným okresem.
2. Z něj si vezme odkaz **ps32 – Výběr obce**.
3. Projde **všechny obce** v okrese a u každé:

   * zkusí přímo načíst souhrnnou tabulku (voliči, obálky, platné + hlasy stran),
   * pokud obec obsahuje **seznam okrsků**, projde jednotlivé okrsky a **sečte** jejich výsledky.
4. Vše uloží do **CSV** 

## Požadavky

* Knihovny Pythonu:

  * `requests`
  * `beautifulsoup4`
    
## Instalace

### 1) Klon projektu / stažení souboru

Uložte si skript `main.py` do svého projektu.

### 2) Vytvoření a aktivace virtuálního prostředí

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3) Instalace knihoven

```bash
pip install requests beautifulsoup4
```
## Jak skript spustit

Syntaxe:

```bash
python3 main.py <URL_ps3> <vystupni_soubor.csv>
```

### Příklad:

```bash
python3 main.py "https://www.volby.cz/pls/ps2017nss/ps3?xjazyk=CZ" "vysledky_benesov.csv"
```

Očekávaný průběh v terminálu (zkráceno):

```
Výchozí stránka: https://www.volby.cz/pls/ps2017nss/ps3?xjazyk=CZ
Okres 'Benešov' -> https://www.volby.cz/pls/ps2017nss/ps32?xjazyk=CZ&xkraj=2&xnumnuts=2101
Hotovo: 529303 Benešov
Hotovo: 529301 Bystřice
... (další obce)
Uloženo do: vysledky_benesov.csv
```

## Formát výstupu (CSV)

* Oddělovač: `;`

Ukázka hlavičky a prvních řádků (kvůli přehlednosti jen prvních 6 sloupců):

```csv
kód obce;název obce;voliči v seznamu;vydané obálky;platné hlasy;Občanská demokratická strana
529303;Benešov;13104;8485;8437;1052
532568;Bernartice;191;148;148;4
```
