import json, os, re, requests
TOPIC = os.environ["NTFY_TOPIC"]
MAX_PRICE = 500
URL = f"https://www.willhaben.at/iad/kaufen-und-verkaufen/marktplatz?keyword=ps5&PRICE_TO={MAX_PRICE}&sort=1&rows=60"
H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"}

def attr(ad, n):
    for a in ad.get("attributes", {}).get("attribute", []):
        if a.get("name") == n and a.get("values"):
            return a["values"][0]

html = requests.get(URL, headers=H, timeout=30).text
data = json.loads(re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.S).group(1))
ads = data["props"]["pageProps"]["searchResult"]["advertSummaryList"]["advertSummary"]

try: seen = set(json.load(open("seen.json")))
except Exception: seen = None
first = seen is None
seen = seen or set()

for ad in ads:
    try: price = float(attr(ad, "PRICE") or 0)
    except ValueError: continue
    if not (0 < price <= MAX_PRICE) or ad["id"] in seen: continue
    seen.add(ad["id"])
    if not first:
        link = "https://www.willhaben.at/iad/" + (attr(ad, "SEO_URL") or "")
        requests.post(f"https://ntfy.sh/{TOPIC}", data=f"{price:.0f} € – {ad.get('description','PS5')}".encode(),
                      headers={"Title": "Neue PS5 auf willhaben", "Click": link, "Priority": "high"})
        print("NEU:", price, link)

json.dump(sorted(seen)[-500:], open("seen.json", "w"))
