import asyncio
import json
from scraper import PracujScraper
from curl_cffi.requests import AsyncSession

async def main():
    # 1. Inicjalizacja
    scraper = PracujScraper()
    keywords = ["Data Science"] # Przykładowe frazy
    all_results = []
    
    print(f"Rozpoczynam testowanie scrapera dla fraz: {keywords}")

    # 2. Sesja asynchroniczna
    async with AsyncSession() as client:
        # Uruchamiamy zadania równolegle
        # Dodajemy max_pages=1, żeby test był szybki
        tasks = [scraper.scrape_keyword(client, kw, max_pages=1) for kw in keywords]
        
        results = await asyncio.gather(*tasks)
        
        for r in results:
            all_results.extend(r)

    # 3. Wyświetlenie wyników
    print(f"Test zakończony. Znaleziono łącznie: {len(all_results)} ofert.")
    
    if all_results:
        # Wyświetlamy 2 pierwsze oferty, żeby sprawdzić strukturę
        print("\n--- PODGLĄD PIERWSZYCH 2 WYNIKÓW ---")
        print(json.dumps(all_results[:2], indent=4, ensure_ascii=False))
    else:
        print("Nie znaleziono żadnych wyników. Sprawdź, czy portal nie zmienił struktury lub czy nie masz blokady IP.")

if __name__ == "__main__":
    # To jest kluczowe dla poprawnego działania asynchronicznego
    asyncio.run(main())