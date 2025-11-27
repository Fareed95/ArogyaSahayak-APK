# main.py - REAL MENU SCRAPER WITH IMPROVED HELPERS (Option A)
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import os
from dotenv import load_dotenv
import requests
import json
import re
import time
import logging

# Selenium + webdriver-manager
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

app = FastAPI(
    title="Real Menu Dietary Finder API",
    description="Scrapes real restaurant menus using Selenium (improved helper functions)",
    version="9.1.1"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# CONFIG
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_CX = os.getenv("GOOGLE_CX")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")  # kept for optional AI fallback

if not GOOGLE_API_KEY or not GOOGLE_CX:
    logging.error("ERROR: GOOGLE_API_KEY and GOOGLE_CX required in .env")
    raise SystemExit("Missing Google Custom Search keys")

# MODELS
class SearchRequest(BaseModel):
    city: str
    text: str
    max_restaurants: Optional[int] = 5

class MenuItem(BaseModel):
    item: str
    safe_score: int
    notes: str
    price: Optional[str] = None

class Restaurant(BaseModel):
    name: str
    city: str
    cuisine: str
    link: str
    source: str
    rating: Optional[float] = None
    menu: List[MenuItem]

class SearchResponse(BaseModel):
    restaurants: List[Restaurant]
    dietary_restrictions: List[str]
    extracted_query: str
    total_found: int

# -----------------------
# Selenium driver helper
# -----------------------
def create_driver():
    """Create headless Chrome driver using webdriver-manager for compatibility."""
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--disable-features=VizDisplayCompositor")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.implicitly_wait(5)
    return driver

# -----------------------
# Improved helpers (Option A)
# -----------------------

def build_search_queries(city: str, restrictions: List[str]) -> List[str]:
    """
    Produce a set of Google queries that reliably return restaurant pages.
    IMPORTANT: avoid putting dietary restrictions directly into Google queries
    (Google often returns list/collection pages and not single restaurant pages).
    Instead we search for restaurant/menu pages in the city, then filter by restrictions later.
    """
    city = city.strip()
    queries = [
        f"restaurants in {city} site:zomato.com",
        f"menu {city} site:zomato.com/menu",
        f"restaurants in {city} site:swiggy.com",
        f"menu {city} site:swiggy.com/restaurant",
        f"best places to eat in {city} site:zomato.com",
    ]
    # return unique queries, keep top variety
    seen = set()
    out = []
    for q in queries:
        if q not in seen:
            seen.add(q)
            out.append(q)
    return out

def post_process_extraction(raw_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Deduplicate, sanitize, normalize menu items returned by scraper or AI fallback.
    - normalize whitespace
    - drop extremely short/long names
    - unify price format when possible
    - return up to 50 items (caller typically limits further)
    """
    seen = set()
    cleaned = []
    for it in raw_items:
        name = it.get("item") or it.get("name") or ""
        if not name:
            continue
        # sanitize whitespace and control characters
        name = re.sub(r"\s+", " ", name).strip()
        if len(name) < 3 or len(name) > 120:
            continue
        # remove emojis and unusual symbols (keep common punctuation)
        name = re.sub(r"[^\w\s\-\&\(\)\/\,\.\u20B9\u00A3\u0024]", "", name).strip()
        price = it.get("price") if it.get("price") else it.get("price_str") if it.get("price_str") else None
        if isinstance(price, str):
            # normalize rupee formats like '₹ 240' or '240' -> '₹240'
            m = re.search(r"₹\s*([\d,]+)", price)
            if m:
                price = f"₹{m.group(1).replace(',', '')}"
            else:
                m2 = re.search(r"([\d,]{2,6})", price)
                if m2:
                    price = f"₹{m2.group(1).replace(',', '')}"
                else:
                    # keep textual price if no digits
                    price = price.strip()
        elif isinstance(price, (int, float)):
            price = f"₹{int(price)}"
        else:
            price = price  # keep None or whatever

        key = name.lower()
        if key in seen:
            continue
        seen.add(key)
        cleaned.append({"item": name, "price": price})
    return cleaned

def improved_score_item(item_name: str, restrictions: List[str]) -> Dict[str, Any]:
    """
    Improved dietary scoring:
    - uses tiered penalties
    - returns integer score 0..10 and human notes
    - supports combination restrictions
    """
    name = item_name.lower()
    base_score = 10
    notes = []

    # trigger lists (kept concise, extendable)
    triggers = {
        "dairy": ["paneer", "cheese", "butter", "ghee", "curd", "cream", "malai", "lassi", "milk", "yogurt", "raita", "makhani"],
        "lactose": ["paneer", "cheese", "butter", "ghee", "curd", "cream", "milk", "lassi"],
        "gluten": ["naan", "roti", "paratha", "bread", "wheat", "puri", "bhatura", "kulcha"],
        "nuts": ["cashew", "kaju", "almond", "badam", "pista", "peanut", "groundnut", "walnut"],
        "peanuts": ["peanut", "groundnut"],
        "egg": ["egg", "omelette", "bhurji"],
        "nonveg": ["chicken", "mutton", "fish", "prawn", "meat", "keema", "gosht", "tikka"],
        "onion": ["onion", "pyaz"],
        "garlic": ["garlic", "lehsun"],
        "vegan": ["paneer", "cheese", "butter", "ghee", "curd", "cream", "milk", "egg", "honey"],
        "keto": ["rice", "potato", "aloo", "sugar"],
        "jain": ["onion", "garlic", "potato", "aloo"]
    }

    # normalize restrictions
    normalized = [r.lower().strip() for r in (restrictions or []) if r and r != "none"]

    # Apply rules: each matching trigger reduces score; severity depends on match type
    for r in normalized:
        toks = triggers.get(r, [])
        # vegan is special: check dairy + nonveg + egg
        if r == "vegan":
            composite = triggers.get("dairy", []) + triggers.get("nonveg", []) + triggers.get("egg", [])
            for t in composite:
                if t in name:
                    base_score -= 9
                    notes.append(f"Contains {t}")
                    break
            continue

        # standard checks
        for t in toks:
            if t in name:
                # stronger penalty for exact ingredient words, smaller for category words
                if len(t) <= 4:  # short tokens likely generic -> medium penalty
                    base_score -= 6
                else:
                    base_score -= 8
                notes.append(f"Contains {t}")
                break

        # keto: penalize carbs
        if r == "keto" and any(x in name for x in ["rice", "potato", "aloo", "sugar", "dal", "roti", "naan"]):
            base_score -= 7
            notes.append("High carb")

        # jain: avoid onion/garlic/potato
        if r == "jain" and any(x in name for x in triggers.get("jain", [])):
            base_score -= 9
            notes.append("Not Jain-compliant")

    # clamp score
    if base_score < 0:
        base_score = 0
    if base_score > 10:
        base_score = 10

    # build notes
    notes = list(dict.fromkeys(notes))  # dedupe while preserving order
    if not notes and base_score >= 8:
        notes = ["✓ Safe"]
    elif base_score >= 5:
        if not notes:
            notes = ["⚠ Check ingredients"]
        else:
            notes.append("⚠ Check ingredients")
    else:
        if not notes:
            notes = ["✗ Avoid"]
        else:
            notes.append("✗ Avoid")

    return {"score": base_score, "notes": " | ".join(notes)}

# -----------------------
# Google search helper
# -----------------------
def google_custom_search(query: str, num: int = 10):
    """Simple wrapper for Google Custom Search"""
    url = "https://www.googleapis.com/customsearch/v1"
    params = {"key": GOOGLE_API_KEY, "cx": GOOGLE_CX, "q": query, "num": min(num, 10)}
    try:
        res = requests.get(url, params=params, timeout=12)
        res.raise_for_status()
        data = res.json().get("items", [])
        logging.info(f"Google returned {len(data)} items for query: {query}")
        return data
    except Exception as e:
        logging.warning(f"Google Search Error for query '{query}': {e}")
        return []

# -----------------------
# Scrapers (Zomato / Swiggy) - keep your selectors but slightly improved
# -----------------------
def scrape_zomato_menu(driver, url: str, restaurant_name: str) -> List[dict]:
    logging.info(f"[ZOMATO] Scraping {url}")
    menu_items = []
    try:
        driver.get(url)
        time.sleep(4)
        # selectors prioritized: data-testid, then likely H-tags, then generic classes
        selectors = [
            "[data-testid='menu-item-name']",
            "h4[class*='sc-']",
            "h4[class*='name']",
            "div[class*='dishName']",
            "div[class*='item-name']",
            "p[class*='item-title']",
            ".zomato-dish-name"  # placeholder - keep fallback
        ]
        for sel in selectors:
            try:
                items = WebDriverWait(driver, 6).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, sel)))
                if len(items) > 2:
                    logging.info(f"[ZOMATO] Found {len(items)} items using selector: {sel}")
                    for el in items[:50]:
                        try:
                            text = el.text.strip()
                            if not text or len(text) < 3:
                                continue
                            # try find price nearby
                            price = None
                            try:
                                price_el = el.find_element(By.XPATH, ".//ancestor::div[1]//span[contains(text(),'₹')]|./following-sibling::*//span[contains(text(),'₹')]")
                                price_text = price_el.text
                                m = re.search(r"₹\s*([\d,]+)", price_text)
                                if m:
                                    price = f"₹{m.group(1).replace(',', '')}"
                            except Exception:
                                price = None
                            menu_items.append({"item": text, "price": price})
                        except Exception:
                            continue
                    break
            except Exception:
                continue

        # fallback: regex extraction from page source
        if len(menu_items) < 3:
            page_text = driver.page_source
            patterns = [r'"name":"([^"]{3,100})"', r'"dishName":"([^"]{3,100})"', r'>([^<]{3,100})<\/h4>']
            for p in patterns:
                matches = re.findall(p, page_text, re.IGNORECASE)
                for match in matches:
                    name = match.strip()
                    if len(name) > 3 and len(name) < 100:
                        menu_items.append({"item": name, "price": None})
            menu_items = post_process_extraction(menu_items)

        # dedupe & return
        unique = post_process_extraction(menu_items)
        logging.info(f"[ZOMATO] Final items: {len(unique)}")
        return unique[:25]
    except Exception as e:
        logging.error(f"[ZOMATO] Error scraping {url}: {e}")
        return []

def scrape_swiggy_menu(driver, url: str, restaurant_name: str) -> List[dict]:
    logging.info(f"[SWIGGY] Scraping {url}")
    menu_items = []
    try:
        driver.get(url)
        time.sleep(4)
        selectors = [
            "div[data-testid='menu-item-name']",
            "div[class*='ItemName']",
            "h3[class*='item']",
            "div[class*='dishName']",
            "div[class*='styles_itemName']",
        ]
        for sel in selectors:
            try:
                items = WebDriverWait(driver, 8).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, sel)))
                if len(items) > 2:
                    logging.info(f"[SWIGGY] Found {len(items)} items using selector: {sel}")
                    for el in items[:50]:
                        try:
                            text = el.text.strip()
                            if not text or len(text) < 3:
                                continue
                            # find price nearby
                            price = None
                            try:
                                price_el = el.find_element(By.XPATH, "./following-sibling::*//span[contains(text(),'₹')] | ../..//span[contains(text(),'₹')]")
                                price_text = price_el.text
                                m = re.search(r"₹\s*([\d,]+)", price_text)
                                if m:
                                    price = f"₹{m.group(1).replace(',', '')}"
                            except Exception:
                                price = None
                            menu_items.append({"item": text, "price": price})
                        except Exception:
                            continue
                    break
            except Exception:
                continue

        # fallback: regex extraction
        if len(menu_items) < 3:
            page_text = driver.page_source
            patterns = [r'"name":"([^"]{3,100})"', r'"dishName":"([^"]{3,100})"', r'"item_name":"([^"]{3,100})"']
            for p in patterns:
                matches = re.findall(p, page_text, re.IGNORECASE)
                for match in matches:
                    name = match.strip()
                    if len(name) > 3 and len(name) < 100:
                        menu_items.append({"item": name, "price": None})
            menu_items = post_process_extraction(menu_items)

        unique = post_process_extraction(menu_items)
        logging.info(f"[SWIGGY] Final items: {len(unique)}")
        return unique[:25]
    except Exception as e:
        logging.error(f"[SWIGGY] Error scraping {url}: {e}")
        return []

# Optional AI fallback already in your code; we keep it unchanged but call only when needed.
def extract_menu_with_ai(page_html: str, restaurant_name: str) -> List[dict]:
    """Use GROQ as last-resort - existing implementation preserved (if GROQ_API_KEY present)."""
    if not GROQ_API_KEY:
        return []

    text = re.sub(r'<[^>]+>', ' ', page_html)
    text = re.sub(r'\s+', ' ', text).strip()[:6000]

    prompt = f"""
Extract REAL menu dish names and prices from this restaurant page for "{restaurant_name}".

Content: {text}

Return ONLY valid JSON array with dish names and prices. Example:
[{{"item": "Paneer Butter Masala", "price": "₹280"}}]

Rules:
- Only actual food dish names
- Include prices if found (₹ symbol)
- Skip navigation, headers, buttons
- Max 10 items
- Return ONLY JSON, no other text
"""
    try:
        res = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
            json={
                "model": "llama-3.1-70b-versatile",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1,
                "max_tokens": 1000
            },
            timeout=30
        )
        if res.status_code == 200:
            content = res.json()["choices"][0]["message"]["content"]
            content = re.sub(r"```json|```", "", content).strip()
            items = json.loads(content)
            return post_process_extraction(items)
    except Exception as e:
        logging.error("AI extraction error: %s", e)
    return []

# -----------------------
# Simple regex fallback dietary parser (keeps your previous behavior)
# -----------------------
def parse_dietary_text_regex(text: str) -> List[str]:
    text_lower = (text or "").lower()
    restrictions = []
    patterns = {
        "vegan": [r"\bvegan\b", r"no animal products", r"plant-based"],
        "lactose": [r"\blactose\b", r"lactose intolerant", r"no dairy", r"dairy free"],
        "dairy": [r"\bdairy\b", r"no milk", r"milk free"],
        "gluten": [r"\bgluten\b", r"gluten free", r"no wheat", r"celiac"],
        "nuts": [r"\bnuts?\b", r"nut allergy", r"no nuts", r"nut-free"],
        "peanuts": [r"\bpeanuts?\b", r"peanut allergy", r"no peanuts"],
        "onion": [r"\bonions?\b", r"no onion", r"avoid onion", r"without onion"],
        "garlic": [r"\bgarlic\b", r"no garlic", r"avoid garlic", r"without garlic"],
        "egg": [r"\beggs?\b", r"no egg", r"egg free"],
        "nonveg": [r"vegetarian", r"no meat", r"veg only", r"no non-veg"],
        "keto": [r"\bketo\b", r"ketogenic", r"low carb"],
        "jain": [r"\bjain\b", r"jain food"],
    }
    for restriction, pattern_list in patterns.items():
        for pattern in pattern_list:
            if re.search(pattern, text_lower):
                if restriction not in restrictions:
                    restrictions.append(restriction)
                break
    return restrictions if restrictions else ["none"]

# Top-level parse function (keeps behavior but uses regex)
def parse_dietary_text(text: str) -> List[str]:
    return parse_dietary_text_regex(text)

# -----------------------
# MAIN ENDPOINT (uses improved helpers)
# -----------------------
@app.post("/api/search", response_model=SearchResponse)
def search_restaurants(request: SearchRequest):
    restrictions = parse_dietary_text(request.text)
    city = request.city.strip().title()
    logging.info(f"Searching in {city} for restrictions: {restrictions}")

    # Build safe queries (improved)
    queries = build_search_queries(city, restrictions)

    # Collect candidate links from Google Custom Search (prioritize Zomato & Swiggy)
    all_results = []
    for q in queries:
        results = google_custom_search(q, 8)
        for item in results:
            link = item.get("link", "")
            title = item.get("title", "") or ""
            snippet = item.get("snippet", "") or ""

            title_lower = title.lower()
            # filter obvious list/collection pages that won't be single-restaurant pages
            if any(x in title_lower for x in ["collection", "collection of", "top", "best", "list"]):
                continue

            # keep only plausible restaurant pages (zomato / swiggy menu structure)
            if "zomato.com" in link and ("/menu" in link or "/order" in link or "/restaurants/" in link):
                name = re.sub(r'( - zomato| - swiggy| - order online| menu).*$', '', title, flags=re.I).strip()
                key = name.lower() if name else link
                if key and key not in [r.get("name", "").lower() for r in all_results]:
                    all_results.append({"name": name or link, "link": link, "source": "Zomato", "snippet": snippet})
            elif "swiggy.com" in link and ("/restaurant" in link or "/menu" in link or "/order" in link):
                name = re.sub(r'( - zomato| - swiggy| - order online| menu).*$', '', title, flags=re.I).strip()
                key = name.lower() if name else link
                if key and key not in [r.get("name", "").lower() for r in all_results]:
                    all_results.append({"name": name or link, "link": link, "source": "Swiggy", "snippet": snippet})
            else:
                # ignore other domains for now
                continue

    logging.info(f"Found {len(all_results)} candidate restaurant links")

    # If no results found from Google, return early with helpful message
    if len(all_results) == 0:
        return SearchResponse(
            restaurants=[],
            dietary_restrictions=restrictions,
            extracted_query=f"Restaurants in {city} matching: {', '.join(restrictions)}",
            total_found=0
        )

    # Scrape menus with Selenium (existing flow, but using improved helpers)
    driver = create_driver()
    final_restaurants: List[Restaurant] = []
    try:
        for resto_candidate in all_results[: request.max_restaurants]:
            name = resto_candidate.get("name") or "Unknown"
            link = resto_candidate.get("link")
            source = resto_candidate.get("source", "Zomato")
            logging.info(f"Processing: {name} | {source} | {link}")

            # Choose scraper
            if source == "Zomato":
                raw_menu = scrape_zomato_menu(driver, link, name)
            else:
                raw_menu = scrape_swiggy_menu(driver, link, name)

            if not raw_menu or len(raw_menu) < 2:
                logging.warning(f"Insufficient menu data for {name} ({link}) - skipping")
                continue

            # normalize menu
            menu_normalized = post_process_extraction(raw_menu)

            # apply improved scoring
            menu_analyzed: List[MenuItem] = []
            for mi in menu_normalized:
                item_name = mi.get("item")
                price = mi.get("price")
                score_data = improved_score_item(item_name, restrictions)
                menu_analyzed.append(MenuItem(item=item_name, price=price, safe_score=score_data["score"], notes=score_data["notes"]))

            # sort by safe_score desc
            menu_analyzed.sort(key=lambda x: x.safe_score, reverse=True)

            final_restaurants.append(Restaurant(
                name=name,
                city=city,
                cuisine="Indian",  # placeholder; could extract from snippet
                link=link,
                source=source,
                rating=None,
                menu=menu_analyzed[:10]
            ))

            logging.info(f"Added {name} with {len(menu_analyzed)} items")
            time.sleep(2)  # be polite between sites

    except Exception as e:
        logging.error("Error in main scraping loop: %s", e)
    finally:
        try:
            driver.quit()
        except Exception:
            pass

    logging.info(f"Final result: {len(final_restaurants)} restaurants with menus")
    return SearchResponse(
        restaurants=final_restaurants,
        dietary_restrictions=restrictions,
        extracted_query=f"Restaurants in {city} matching: {', '.join(restrictions)}",
        total_found=len(final_restaurants)
    )

# Root + health
@app.get("/")
def root():
    return {
        "message": "Real Menu Dietary Finder API v9.1.1",
        "note": "Uses Selenium with improved helper functions (post_process_extraction, improved_score_item, build_search_queries)",
        "endpoints": {"POST /api/search": "Search for restaurants with dietary analysis"}
    }

@app.get("/health")
def health_check():
    return {"status": "healthy", "version": "9.1.1"}

if __name__ == "__main__":
    import uvicorn
    logging.info("Starting Real Menu Scraper API v9.1.1")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
