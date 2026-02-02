import asyncio
import json
from scraper import PracujScraper
from curl_cffi.requests import AsyncSession

async def main():
    # 1. Inicjalizacja
    scraper = PracujScraper()
    keywords = ["dyrektor fmcg", "head of retail", "dyrektor zakupów"] # Job Hunter keywords
    all_results = []
    
    print(f"🔍 Job Hunter - Rozpoczynam scraping dla: {keywords}")

    # 2. Sesja asynchroniczna
    async with AsyncSession() as client:
        # Uruchamiamy zadania równolegle
        tasks = [scraper.scrape_keyword(client, kw, max_pages=1) for kw in keywords]
        
        results = await asyncio.gather(*tasks)
        
        for r in results:
            all_results.extend(r)

    # 3. Wyświetlenie wyników
    print(f"\n✅ Scraping zakończony. Znaleziono łącznie: {len(all_results)} ofert.")
    
    if all_results:
        # Wyświetlamy wszystkie wyniki w formacie tabelarycznym
        print("\n--- RAPORT: OFERTY PRACY ---")
        for idx, offer in enumerate(all_results, 1):
            print(f"\n{idx}. {offer['Title']}")
            print(f"   Firma: {offer['Company']}")
            print(f"   Lokalizacja: {offer['Location']}")
            print(f"   Wynagrodzenie: {offer['Salary']}")
            print(f"   Link: {offer['Link']}")
    else:
        print("❌ Nie znaleziono żadnych wyników. Sprawdź, czy portal nie zmienił struktury lub czy nie masz blokady IP.")

if __name__ == "__main__":
    asyncio.run(main())
