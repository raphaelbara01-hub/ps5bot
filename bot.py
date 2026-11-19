import json, os, re, math, requests
TOPIC = os.environ["NTFY_TOPIC"]
HOME = (48.047, 16.313)   # Guntramsdorf
RADIUS_KM = 150
SEARCHES = {
    "ps5":    {"keyword": "ps5",           "min": 200, "max": 554, "must": ["ps5", "playstation 5"]},
    "xboxss": {"keyword": "xbox series s", "min": 100, "max": 334, "must": ["series s"]},
}
H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"}

def attr(ad, n):
    for a in ad.get("attributes", {}).get("attribute", []):
        if a.get("name") == n and a.get("values"):
            return a["values"][0]

def dist_km(ad):
    c = attr(ad, "COORDINATES")
    if not c: return None
    try: lat, lon = map(float, c.split(","))
    except ValueError: return None
    p1, p2 = math.radians(HOME[0]), math.radians(lat)
    dp, dl = p2 - p1, math.radians(lon - HOME[1])
    a = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 6371 * 2 * math.asin(math.sqrt(a))

try: seen = json.load(open("seen.json"))
except Exception: seen = {}
if isinstance(seen, list): seen = {"ps5": seen}

for name, s in SEARCHES.items():
    url = ("https://www.willhaben.at/iad/kaufen-und-verkaufen/marktplatz"
           f"?keyword={s['keyword'].replace(' ', '+')}&PRICE_TO={s['max']}&sort=1&rows=60")
    html = requests.get(url, headers=H, timeout=30).text
    data = json.loads(re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.S).group(1))
    ads = data["props"]["pageProps"]["searchResult"]["advertSummaryList"]["advertSummary"]
    first = name not in seen
    old = set(seen.get(name, []))
    for ad in ads:
        title = ad.get("description", "")
        try: price = float(attr(ad, "PRICE") or 0)
        except ValueError: continue
        if ad["id"] in old: continue
        if not (s["min"] <= price <= s["max"]): continue
        if not any(m in title.lower() for m in s["must"]): continue
        d = dist_km(ad)
        if d is not None and d > RADIUS_KM: continue
        old.add(ad["id"])
        if not first:
            link = "https://www.willhaben.at/iad/" + (attr(ad, "SEO_URL") or "")
            ort = attr(ad, "LOCATION") or ""
            km = f" ({d:.0f} km)" if d is not None else ""
            requests.post(f"https://ntfy.sh/{TOPIC}", data=f"{price:.0f} € – {title}\n{ort}{km}".encode(),
                          headers={"Title": f"Neu auf willhaben: {name.upper()}", "Click": link, "Priority": "high"})
            print("NEU:", name, price, ort, km, link)
    seen[name] = sorted(old)[-500:]

json.dump(seen, open("seen.json", "w"))
