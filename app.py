from flask import Flask, render_template, jsonify, request
import json
import asyncio
import urllib.parse
import random
import time
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from curl_cffi.requests import AsyncSession

app = Flask(__name__)

# --- KONFIGURACJA SYSTEMU ---
# Globalny limit jednoczesnych zapytań do Pracuj.pl (wszyscy użytkownicy razem)
SCRAPE_SEMAPHORE = asyncio.Semaphore(2) 
# Pamięć podręczna: { "fraza": {"timestamp": data, "results": [...]} }
SCRAPER_CACHE = {}
CACHE_DURATION = timedelta(minutes=20) # Jak długo trzymać wyniki w pamięci

class PracujScraper:
    def __init__(self):
        self.headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "pl-PL,pl;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Cache-Control": "max-age=0",
}

    def parse_data(self, json_data, search_term):
        parsed_offers = []
        try:
            queries = json_data.get('props', {}).get('pageProps', {}).get('dehydratedState', {}).get('queries', [])
            for query in queries:
                query_data = query.get('state', {}).get('data', {})
                if not isinstance(query_data, dict): continue
                
                grouped_offers = query_data.get('groupedOffers', [])
                for group in grouped_offers:
                    title = group.get('jobTitle')
                    company = group.get('companyName')
                    salary = group.get('salaryDisplayText') or "Nie podano"
                    
                    ai_summary_raw = group.get('aiSummary', '')
                    reqs = ""
                    if ai_summary_raw:
                        soup_ai = BeautifulSoup(ai_summary_raw, "html.parser")
                        reqs = " | ".join([li.get_text() for li in soup_ai.find_all('li')])

                    for offer in group.get('offers', []):
                        link = offer.get('offerAbsoluteUri')
                        if link:
                            parsed_offers.append({
                                'Szukana fraza': search_term,
                                'Stanowisko': title,
                                'Firma': company,
                                'Wynagrodzenie': salary,
                                'Lokalizacja': offer.get('displayWorkplace'),
                                'Link': link,
                                'Wymagania (AI)': reqs
                            })
        except Exception as e:
            print(f"Błąd parsowania: {e}")
        return parsed_offers

    async def scrape_keyword(self, client, keyword, max_pages=1):
        # 1. Sprawdzenie Cache
        if keyword in SCRAPER_CACHE:
            cache_entry = SCRAPER_CACHE[keyword]
            if datetime.now() - cache_entry['timestamp'] < CACHE_DURATION:
                print(f"--- Cache Hit dla: {keyword} ---")
                return cache_entry['results']

        encoded_keyword = urllib.parse.quote(keyword)
        keyword_results = []
        
        # 2. Użycie semafora - tylko ograniczona liczba zapytań naraz
        async with SCRAPE_SEMAPHORE:
            for page_num in range(1, max_pages + 1):
                url = f"https://www.pracuj.pl/praca/{encoded_keyword};kw?pn={page_num}"
                
                # 3. Mechanizm Retry (maksymalnie 3 próby na stronę)
                for attempt in range(3):
                    try:
                        print(f"Szukanie: [{keyword}] (Próba {attempt+1})")
                        response = await client.get(url, impersonate="chrome110", timeout=30)
                        
                        if response.status_code == 200:
                            soup = BeautifulSoup(response.text, "html.parser")
                            script_tag = soup.find("script", id="__NEXT_DATA__")
                            if script_tag:
                                results = self.parse_data(json.loads(script_tag.string), keyword)
                                keyword_results.extend(results)
                                break # Sukces, wychodzimy z pętli prób
                        
                        elif response.status_code == 403:
                            print(f"  Blokada 403 dla {keyword}. Czekam przed ponowieniem...")
                            await asyncio.sleep(random.uniform(5, 10)) # Dłuższy sleep po 403
                        
                    except Exception as e:
                        print(f"  Błąd sieciowy: {e}")
                    
                    # Losowe opóźnienie (Jitter) między próbami
                    await asyncio.sleep(random.uniform(1, 3))

        # 4. Zapis do Cache po pobraniu danych
        if keyword_results:
            SCRAPER_CACHE[keyword] = {
                'timestamp': datetime.now(),
                'results': keyword_results
            }
        
        return keyword_results

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/scrape', methods=['POST'])
async def scrape():
    data = request.json
    keywords = list(set([k.strip() for k in data.get('keywords', '').split('\n') if k.strip()]))
    
    scraper = PracujScraper()
    all_results = []
    
    async with AsyncSession() as client:
        # Tworzymy listę zadań do wykonania
        tasks = [scraper.scrape_keyword(client, kw) for kw in keywords]
        results = await asyncio.gather(*tasks)
        for r in results:
            all_results.extend(r)
    
    # Usuwanie duplikatów globalnie
    unique_results = {o.get('Link'): o for o in all_results if o.get('Link')}.values()
    return jsonify(list(unique_results))

if __name__ == "__main__":
    app.run(debug=True)