import os
import requests
import random
from bs4 import BeautifulSoup

from database import save_price

# ─────────────────────────────────────────
# API KEYS
# ─────────────────────────────────────────
RAPIDAPI_KEY = "88e78500b1mshb2e5af9e1d8d6aap130790jsna228ee3b0e21"
SCRAPINGBEE_KEY = "ANZXN9IG1OSZLL4PN6QZN6AI1W2BG2Z0DTS80R1M4S4LMT8JBAS1NKFIN5LEKSGENG6D3U2R9NCXEBX9"

# ─────────────────────────────────────────
# HELPER — Format price with ₹ symbol
# ─────────────────────────────────────────
def fmt_price(price):
    if price is None:
        return "Not available"
    s = str(price).strip()
    if not s or s.lower() in ["none", "not available", "null", "0"]:
        return "Not available"
    s = s.replace(",", "").replace("₹", "").replace(" ", "").strip()
    try:
        return f"₹{int(float(s)):,}"
    except Exception:
        return str(price)


# ─────────────────────────────────────────
# HELPER — Price string to number
# ─────────────────────────────────────────
def price_to_num(price_str):
    try:
        s = str(price_str).replace("₹", "").replace(",", "").strip()
        n = "".join(c for c in s if c.isdigit() or c == ".")
        return float(n) if n else float("inf")
    except Exception:
        return float("inf")


# ─────────────────────────────────────────
# HELPER — ScrapingBee fetch
# ─────────────────────────────────────────
def scrapingbee_get(url, render_js=False):
    if not SCRAPINGBEE_KEY:
        raise RuntimeError("Missing SCRAPINGBEE_KEY env var")
    if SCRAPINGBEE_KEY == "paste_your_scrapingbee_key_here":
        raise RuntimeError("SCRAPINGBEE_KEY is placeholder")

    r = requests.get(
        "https://app.scrapingbee.com/api/v1/",
        params={
            "api_key": SCRAPINGBEE_KEY,
            "url": url,
            "render_js": "true" if render_js else "false",
            "country_code": "in",
            "premium_proxy": "false",
        },
        timeout=45,
    )
    return r


# ─────────────────────────────────────────
# SCRAPER 1 — Amazon India (RapidAPI) → 5 products
# ─────────────────────────────────────────
def scrape_amazon(query):
    print("  [1/4] Amazon India...")

    if not RAPIDAPI_KEY:
        print("       ⚠️  RAPIDAPI_KEY missing -> skipping Amazon")
        return []

    try:
        r = requests.get(
            "https://real-time-amazon-data.p.rapidapi.com/search",
            headers={
                "X-RapidAPI-Key": RAPIDAPI_KEY,
                "X-RapidAPI-Host": "real-time-amazon-data.p.rapidapi.com",
            },
            params={
                "query": query,
                "page": "1",
                "country": "IN",
                "sort_by": "RELEVANCE",
            },
            timeout=20,
        )

        if r.status_code != 200:
            print(f"       ❌ HTTP {r.status_code}")
            return []

        products = r.json().get("data", {}).get("products", [])
        results = []

        for p in products[:5]:   # ← 5 products
            name  = p.get("product_title", "Unknown")
            price = fmt_price(p.get("product_price", "Not available"))
            link  = p.get("product_url", "https://www.amazon.in")
            stock = p.get("product_availability", "In Stock")
            stars = str(p.get("product_star_rating", "N/A"))

            save_price(name, price, "Amazon", link)
            results.append({
                "name": name, "price": price,
                "real_price": f"{price} — Free delivery (Prime)",
                "shipping": "Free (Prime)", "stock": stock,
                "rating": stars, "app": "Amazon",
                "url": link, "estimated": False,
            })

        print(f"       ✅ {len(results)} products found")
        return results

    except Exception as e:
        print(f"       ❌ Failed: {e}")
        return []


# ─────────────────────────────────────────
# SCRAPER 2 — Flipkart (ScrapingBee) → 4 products
# ─────────────────────────────────────────
def scrape_flipkart(query):
    print("  [2/4] Flipkart (via ScrapingBee)...")
    url = f"https://www.flipkart.com/search?q={query.replace(' ', '+')}"

    try:
        r = scrapingbee_get(url, render_js=False)
        print(f"       ScrapingBee status: {r.status_code}")

        if r.status_code != 200:
            print(f"       ❌ Failed: HTTP {r.status_code}")
            return []

        soup    = BeautifulSoup(r.content, "html.parser")
        results = []

        cards = (
            soup.find_all("div", attrs={"data-id": True})
            or soup.find_all("div", class_="cPHDY")
            or soup.find_all("div", class_="_1AtVbE")
            or []
        )
        print(f"       Cards found: {len(cards)}")

        for card in cards[:10]:
            name_tag = (
                card.find("div", class_="KzDlHZ")
                or card.find("div", class_="_4rR01T")
                or card.find("a",   class_="s1Q9rs")
                or card.find("div", class_="syl9yP")
            )
            price_tag = (
                card.find("div", class_="Nx9bqj")
                or card.find("div", class_="_30jeq3")
                or card.find("div", class_="hl05eU")
            )
            link_tag = card.find("a", href=True)

            name  = name_tag.get_text(strip=True)  if name_tag  else None
            price = price_tag.get_text(strip=True) if price_tag else None
            link  = "https://www.flipkart.com" + link_tag["href"] if link_tag else ""

            if not name or not price:
                continue

            price = fmt_price(price)
            save_price(name, price, "Flipkart", link)
            results.append({
                "name": name, "price": price,
                "real_price": f"{price} — Free delivery above ₹499",
                "shipping": "Free above ₹499", "stock": "In Stock",
                "rating": "N/A", "app": "Flipkart",
                "url": link, "estimated": False,
            })

            if len(results) == 4:   # ← cap at 4
                break

        if not results:
            print("       ⚠️  0 products — retrying with JS render...")
            r2    = scrapingbee_get(url, render_js=True)
            soup2 = BeautifulSoup(r2.content, "html.parser")
            cards2 = soup2.find_all("div", attrs={"data-id": True})
            print(f"       JS Cards found: {len(cards2)}")

            for card in cards2[:10]:
                name_tag  = (
                    card.find("div", class_="KzDlHZ")
                    or card.find("div", class_="_4rR01T")
                    or card.find("a",   class_="s1Q9rs")
                )
                price_tag = card.find("div", class_="Nx9bqj") or card.find("div", class_="_30jeq3")
                link_tag  = card.find("a", href=True)

                name  = name_tag.get_text(strip=True)  if name_tag  else None
                price = price_tag.get_text(strip=True) if price_tag else None
                link  = "https://www.flipkart.com" + link_tag["href"] if link_tag else ""

                if not name or not price:
                    continue

                price = fmt_price(price)
                save_price(name, price, "Flipkart", link)
                results.append({
                    "name": name, "price": price,
                    "real_price": f"{price} — Free delivery above ₹499",
                    "shipping": "Free above ₹499", "stock": "In Stock",
                    "rating": "N/A", "app": "Flipkart",
                    "url": link, "estimated": False,
                })

                if len(results) == 4:   # ← cap at 4
                    break

        print(f"       ✅ {len(results)} products found")
        return results

    except Exception as e:
        print(f"       ❌ Flipkart failed: {e}")
        return []


# ─────────────────────────────────────────
# SCRAPER 3 — Meesho (ScrapingBee) → 3 products
# ─────────────────────────────────────────
def scrape_meesho(query):
    print("  [3/4] Meesho (via ScrapingBee)...")
    url = f"https://www.meesho.com/search?q={query.replace(' ', '%20')}"

    try:
        r = scrapingbee_get(url, render_js=True)
        print(f"       ScrapingBee status: {r.status_code}")

        if r.status_code != 200:
            print(f"       ❌ Failed: HTTP {r.status_code}")
            return []

        soup    = BeautifulSoup(r.content, "html.parser")
        results = []

        cards = (
            soup.find_all("div", class_="NewProductCardstyled__CardContainer")
            or soup.find_all("div", attrs={"data-testid": "product-container"})
            or soup.find_all("div", class_="sc-eDvSVe")
            or soup.find_all("div", class_="ProductList__GridCol")
            or []
        )
        print(f"       Cards found: {len(cards)}")

        for card in cards[:10]:
            name_tag = (
                card.find("p",    class_="NewProductCardstyled__ProductTitle")
                or card.find("span", class_="product-title")
                or card.find("p")
            )
            price_tag = (
                card.find("h5")
                or card.find("span", class_="price")
                or card.find("p",    class_="NewProductCardstyled__DiscountPrice")
            )
            link_tag = card.find("a", href=True)

            name  = name_tag.get_text(strip=True)  if name_tag  else None
            price = price_tag.get_text(strip=True) if price_tag else None
            link  = "https://www.meesho.com" + link_tag["href"] if link_tag else "https://www.meesho.com"

            if not name or not price:
                continue

            price = fmt_price(price)
            save_price(name, price, "Meesho", link)
            results.append({
                "name": name, "price": price,
                "real_price": f"{price} + ₹49 shipping",
                "shipping": "₹49", "stock": "In Stock",
                "rating": "N/A", "app": "Meesho",
                "url": link, "estimated": False,
            })

            if len(results) == 3:   # ← cap at 3
                break

        print(f"       ✅ {len(results)} products found" if results else "       ⚠️  0 products found")
        return results

    except Exception as e:
        print(f"       ❌ Meesho failed: {e}")
        return []


# ─────────────────────────────────────────
# SCRAPER 4 — Myntra (ScrapingBee) → 6 products
# ─────────────────────────────────────────
def scrape_myntra(query):
    print("  [4/4] Myntra (via ScrapingBee)...")
    url = f"https://www.myntra.com/{query.replace(' ', '-')}"

    try:
        r = scrapingbee_get(url, render_js=True)
        print(f"       ScrapingBee status: {r.status_code}")

        if r.status_code != 200:
            print(f"       ❌ Failed: HTTP {r.status_code}")
            return []

        soup    = BeautifulSoup(r.content, "html.parser")
        results = []

        # Myntra product cards
        cards = (
            soup.find_all("li", class_="product-base")
            or soup.find_all("div", class_="product-base")
            or []
        )
        print(f"       Cards found: {len(cards)}")

        for card in cards[:10]:
            # Brand + name combined
            brand_tag = card.find("h3", class_="product-brand")
            name_tag  = card.find("h4", class_="product-product")
            brand = brand_tag.get_text(strip=True) if brand_tag else ""
            pname = name_tag.get_text(strip=True)  if name_tag  else ""
            name  = f"{brand} {pname}".strip() or None

            price_tag = (
                card.find("span", class_="product-discountedPrice")
                or card.find("span", class_="product-price")
            )
            price = price_tag.get_text(strip=True) if price_tag else None

            link_tag = card.find("a", href=True)
            link = "https://www.myntra.com/" + link_tag["href"].lstrip("/") if link_tag else "https://www.myntra.com"

            if not name or not price:
                continue

            price = fmt_price(price)
            save_price(name, price, "Myntra", link)
            results.append({
                "name": name, "price": price,
                "real_price": f"{price} — Free delivery above ₹799",
                "shipping": "Free above ₹799", "stock": "In Stock",
                "rating": "N/A", "app": "Myntra",
                "url": link, "estimated": False,
            })

            if len(results) == 6:   # ← cap at 6
                break

        print(f"       ✅ {len(results)} products found" if results else "       ⚠️  0 products found")
        return results

    except Exception as e:
        print(f"       ❌ Myntra failed: {e}")
        return []


# ─────────────────────────────────────────
# HELPER — Smart Estimate fallback
# ─────────────────────────────────────────
def scrape_estimate(query, base_results, platform_name, factor_low, factor_high,
                    shipping, base_url, limit):
    print(f"       {platform_name} (smart estimate)...")

    if not base_results:
        print("       ⚠️  No base data for estimate")
        return []

    results = []
    for p in base_results[:limit]:
        base = price_to_num(p["price"])
        if base == float("inf"):
            continue

        estimated = int(base * random.uniform(factor_low, factor_high))
        estimated = (estimated // 10) * 10 - 1
        if estimated < 99:
            estimated = 99

        price = fmt_price(str(estimated))
        link  = base_url + query.replace(" ", "+")

        save_price(p["name"], price, platform_name, link)
        results.append({
            "name": p["name"], "price": price,
            "real_price": f"{price} — {shipping}",
            "shipping": shipping, "stock": "In Stock",
            "rating": "N/A", "app": f"{platform_name}*",
            "url": link, "estimated": True,
        })

    print(f"       📊 {len(results)} estimated prices")
    return results


# ─────────────────────────────────────────
# DISPLAY — Tabular output grouped by platform
# ─────────────────────────────────────────
def print_table(platform, results):
    if not results:
        print(f"\n  {platform}: No results found\n")
        return

    col_w = 55   # product name column width

    header = f"  {'PLATFORM':<12} | {'PRICE':<14} | {'MODEL / PRODUCT'}"
    divider = "  " + "-" * (12 + 3 + 14 + 3 + col_w)

    print(f"\n  ── {platform} ({len(results)} products) " + "─" * 30)
    print(header)
    print(divider)

    for r in results:
        live_tag = " [EST]" if r.get("estimated") else ""
        app_label = r["app"].ljust(12)
        price_col = r["price"].ljust(14)
        name_col  = r["name"][:col_w]
        print(f"  {app_label} | {price_col} | {name_col}{live_tag}")

    print(divider)


# ─────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────
def scrape_all(query):
    print(f"\n{'='*56}")
    print(f"  CrossCart  —  Searching: {query.upper()}")
    print(f"{'='*56}")

    amazon_results  = scrape_amazon(query)    # up to 5
    flipkart_results = scrape_flipkart(query) # up to 4
    meesho_results  = scrape_meesho(query)    # up to 3
    myntra_results  = scrape_myntra(query)    # up to 6

    # Fallbacks using estimates when live scrape fails
    if not flipkart_results:
        flipkart_results = scrape_estimate(
            query, amazon_results, "Flipkart",
            0.94, 0.98, "Free above ₹499",
            "https://www.flipkart.com/search?q=", limit=4,
        )

    if not meesho_results:
        meesho_results = scrape_estimate(
            query, amazon_results, "Meesho",
            0.55, 0.70, "₹49 shipping",
            "https://www.meesho.com/search?q=", limit=3,
        )

    if not myntra_results:
        myntra_results = scrape_estimate(
            query, amazon_results, "Myntra",
            0.85, 1.10, "Free above ₹799",
            "https://www.myntra.com/", limit=6,
        )

    # ── Grouped tabular output ──────────────────────────
    print_table("Amazon",   amazon_results)
    print_table("Flipkart", flipkart_results)
    print_table("Meesho",   meesho_results)
    print_table("Myntra",   myntra_results)

    # ── Summary ─────────────────────────────────────────
    all_results = amazon_results + flipkart_results + meesho_results + myntra_results
    all_results.sort(key=lambda x: price_to_num(x["price"]))

    best = all_results[0] if all_results else None
    print(f"\n  Total results : {len(all_results)}")
    if best:
        print(f"  Cheapest      : {best['price']} on {best['app']} — {best['name'][:45]}")
    print(f"  (* = estimated price, not live scraped)")
    print(f"{'='*56}\n")

    return all_results


# ─────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────
if __name__ == "__main__":
    scrape_all("NUDE LIPSTICK")