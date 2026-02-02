import asyncio
import json
from scraper import PracujScraper
from curl_cffi.requests import AsyncSession

async def main():
    # 1. Inicjalizacja
    scraper = PracujScraper()
    
    # Twoje keywords dla Job Hunter
    keywords = [
        "dyrektor sprzedaży",
        "commercial director",
        "head of sales",
        "dyrektor handlowy"
    ]
    
    all_results = []
    
    print(f"🔍 Job Hunter - Rozpoczynam scraping dla: {keywords}\n")

    # 2. Sesja asynchroniczna
    async with AsyncSession() as client:
        # Uruchamiamy zadania równolegle (1 strona na keyword)
        tasks = [scraper.scrape_keyword(client, kw, max_pages=1) for kw in keywords]
        
        results = await asyncio.gather(*tasks)
        
        for r in results:
            all_results.extend(r)

    # 3. Wyświetlenie wyników
    print(f"\n✅ Scraping zakończony. Znaleziono łącznie: {len(all_results)} ofert.\n")
    
    if all_results:
        # Wyświetlamy wszystkie wyniki w formacie tabelarycznym
        print("=" * 100)
        print("RAPORT: OFERTY PRACY (OSTATNIE 7 DNI)")
        print("=" * 100)
        
        for idx, offer in enumerate(all_results, 1):
            print(f"\n{idx}. {offer['Title']}")
            print(f"   🏢 Firma: {offer['Company']}")
            print(f"   📍 Lokalizacja: {offer['Location']}")
            print(f"   💰 Wynagrodzenie: {offer['Salary']}")
            print(f"   🔗 Link: {offer['Link']}")
            print("-" * 100)
    else:
        print("❌ Nie znaleziono żadnych wyników.")

if __name__ == "__main__":
    asyncio.run(main())
