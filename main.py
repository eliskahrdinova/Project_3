"""
main.py: třetí projekt do Engeto Online Python Akademie

author: Eliška Hrdinová
email: eliskahrdinova@email.cz
"""
import csv
import sys
import requests
from requests.compat import urljoin
from bs4 import BeautifulSoup

# pomocné proměnné

DISTRICT_NAME = "Benešov"

# pomocné funkce

def die(msg, code=1):
    """ v případě chyby ukončí program se zadaným textem """
    print(msg)
    sys.exit(code)

def get_soup(url):
    """ Funkce parsuje url """
    r = requests.get(url)
    return BeautifulSoup(r.text, "html.parser")

def find_ps32_for_district(ps3_soup, base_url, district_name):
    """
    Funkce projde tabulky → najde řádek s názvem okresu
    → z něj vytáhne odkaz na „ps32“ → vrátí absolutní URL.
    """
    target = district_name.strip().lower()
    for table in ps3_soup.find_all("table"):
        for tr in table.find_all("tr"):
            row = " ".join(td.get_text(" ", strip=True).lower()
                           for td in tr.find_all("td"))
            if not row or target not in row:
                continue
            for a in tr.find_all("a"):
                href = a.get("href", "")
                if "ps32" in href:
                    return urljoin(base_url, href)
    die("Okres '{d}' se nenašel nebo nemá odkaz na 'Výběr obce'."
        .format(d=district_name))

def find_municipal_tables(soup):
    """
    Projde všechny <table> na stránce a vrátí jen ty,
    ve kterých se nachází odkazy s parametrem xobec=
    """
    return [t for t in soup.find_all("table")
            if t.find("a", href=lambda h: h and "xobec=" in h)]

def parse_municipal_rows(table, base_url):
    """
    Projde tabulku obcí, z řádku vytáhne kód, název a odkazy „Číslo“/„X“.
    Odkazy převádí na absolutní, vrací seznam slovníků.
    """
    out = []
    for tr in table.find_all("tr"):
        a_code = None
        for a in tr.find_all("a"):
            txt = (a.get_text(strip=True) or "")
            href = a.get("href", "")
            if txt.isdigit() and "xobec=" in href:
                a_code = a; break
        if not a_code:
            continue
        code = a_code.get_text(strip=True)
        num_link = urljoin(base_url, a_code.get("href"))

        a_x = None
        for a in tr.find_all("a"):
            if a.get_text(strip=True) == "X":
                a_x = a; break
        x_link = (urljoin(base_url, a_x.get("href"))
                  if a_x and a_x.get("href") else None)

        name = ""
        for td in tr.find_all("td"):
            if a_code in td.descendants:
                continue
            if a_x and a_x in td.descendants:
                continue
            t = td.get_text(" ", strip=True)
            if t:
                name = t; break

        if code and name and (num_link or x_link):
            out.append({"code": code, "name": name,
                        "num_link": num_link, "x_link": x_link})
    return out

def extract_summary_counts(soup):
    """
    Získej (voliči, obálky, platné) ze souhrnné tabulky na stránce obce.
    Najdi řádek s nejvíce čísly; z posledních 6 hodnot vezmi pořadí:
    [voliči, obálky, %účast, odevzdané, platné, %platných].
    """
    summary = None
    node = soup.find(string=lambda s: s and "Voliči v seznamu" in s)
    if node:
        summary = node.find_parent("table")
    if not summary:
        for t in soup.find_all("table"):
            tx = t.get_text(" ", strip=True)
            if "Voliči v seznamu" in tx and "Platné" in tx:
                summary = t; break
    if not summary:
        return None

    best_nums, best_cnt = None, -1
    for tr in summary.find_all("tr"):
        nums = []
        for c in tr.find_all(["td", "th"]):
            t = c.get_text(" ", strip=True)
            if any(ch.isdigit() for ch in t):
                nums.append(t)
        if len(nums) > best_cnt:
            best_nums, best_cnt = nums, len(nums)
    if not best_nums or len(best_nums) < 6:
        return None

    last6 = best_nums[-6:]
    return last6[0], last6[1], last6[4]

def extract_party_votes(soup):
    """
    Vrátí {strana: hlasy} — vezmi PRVNÍ číslo za názvem strany (hlasy),
    ne procenta.
    """
    parties = {}
    for tr in soup.find_all("tr"):
        cells = tr.find_all("td")
        if not cells:
            continue
        idx_name = None
        for i, td in enumerate(cells):
            cls = " ".join(td.get("class") or [])
            txt = td.get_text(strip=True)
            cond = (txt and any(ch.isalpha() for ch in txt) and
                    txt not in ("Voliči v seznamu",
                                "Vydané obálky",
                                "Platné hlasy"))
            if ("overflow" in cls) or cond:
                idx_name = i; break
        if idx_name is None:
            continue

        party = cells[idx_name].get_text(strip=True)
        if (not party) or ("Okrsek" in party) or ("Název" in party):
            continue

        votes = None
        for j in range(idx_name + 1, len(cells)):
            s = cells[j].get_text(" ", strip=True)
            if any(ch.isdigit() for ch in s):
                votes = s; break
        if votes is not None:
            parties[party] = parties.get(party, 0) + votes
    return parties if parties else None

def is_precinct_list(soup):
    """ Vrátí tabulku se seznamem okrsků na stránce """
    for t in soup.find_all("table"):
        head = t.find("tr")
        if not head:
            continue
        hdr = [" ".join(c.get_text(" ", strip=True).lower().split())
               for c in head.find_all(["th", "td"])]
        if any("okrsek" in h for h in hdr):
            return t
    for t in soup.find_all("table"):
        if t.find("a", href=lambda h: h and "xokrsek=" in h):
            return t
    return None

def parse_precinct_links(table, base_url):
    """ Z dodané tabulky vyparsuje všechny odkazy na okrsky """
    links = []
    for tr in table.find_all("tr"):
        for a in tr.find_all("a"):
            href = a.get("href", "")
            if "xokrsek=" in href:
                links.append(urljoin(base_url, href))
    return links

def aggregate_over_precincts(links):
    """
    Stáhne výsledky okrsků a sečte voliče, obálky, platné a hlasy stran.
    """
    voters = envelopes = valid = 0
    parties_sum = {}
    for link in links:
        s = get_soup(link)
        c = extract_summary_counts(s)
        p = extract_party_votes(s)
        if c:
            voters += c[0]; envelopes += c[1]; valid += c[2]
        if p:
            for k, v in p.items():
                parties_sum[k] = parties_sum.get(k, 0) + v
    return voters, envelopes, valid, parties_sum

def fetch_municipality_result(num_link, x_link):
    """
    Z výsledkové stránky obce zkusí rovnou souhrny a hlasy; pokud je
    seznam okrsků, sečte je přes aggregate_over_precincts.
    """
    if num_link:
        s = get_soup(num_link)
        c = extract_summary_counts(s); p = extract_party_votes(s)
        if c and p:
            return c[0], c[1], c[2], p
        tbl = is_precinct_list(s)
        if tbl:
            return aggregate_over_precincts(
                parse_precinct_links(tbl, num_link)
            )
    if x_link:
        s = get_soup(x_link)
        tbl = is_precinct_list(s)
        if tbl:
            return aggregate_over_precincts(
                parse_precinct_links(tbl, x_link)
            )
    return 0, 0, 0, {}

def write_csv(csv_name, rows, party_order):
    """ Vytvoří csv soubor s požadovanými údaji """
    header = ["kód obce", "název obce", "voliči v seznamu",
              "vydané obálky", "platné hlasy"] + party_order
    with open(csv_name, mode = "w") as f:
        w = csv.DictWriter(f, fieldnames=header, delimiter=";")
        w.writeheader()
        for r in rows:
            row = {"kód obce": r["code"], "název obce": r["name"],
                   "voliči v seznamu": r["voters"],
                   "vydané obálky": r["envelopes"],
                   "platné hlasy": r["valid"]}
            for p in party_order:
                row[p] = r["parties"].get(p, 0)
            w.writerow(row)

# main funkce

def main():
    if len(sys.argv) != 3:
        die("Použití: python3 main.py <URL_ps3> <jméno_souboru.csv>")
    url_ps3, csv_name = sys.argv[1].strip(), sys.argv[2].strip()

    print(f"Výchozí stránka: {url_ps3}")
    s3 = get_soup(url_ps3)

    ps32_url = find_ps32_for_district(s3, url_ps3, DISTRICT_NAME)
    print(f"Okres '{DISTRICT_NAME}' -> {ps32_url}")

    s32 = get_soup(ps32_url)

    municipalities = []
    for t in find_municipal_tables(s32):
        municipalities.extend(parse_municipal_rows(t, ps32_url))
    if not municipalities:
        die("Na stránce okresu se nepodařilo najít obce (xobec=).")

    results, party_order = [], []
    for m in municipalities:
        voters, envelopes, valid, parties = fetch_municipality_result(
            m["num_link"], m["x_link"]
        )
        for p in parties.keys():
            if p not in party_order:
                party_order.append(p)
        results.append({"code": m["code"], "name": m["name"],
                        "voters": voters, "envelopes": envelopes,
                        "valid": valid, "parties": parties})
        print(f"Hotovo: {m['code']} {m['name']}")

    write_csv(csv_name, results, party_order)
    print(f"Uloženo do: {csv_name}")

if __name__ == "__main__":
    main()
