import asyncio
import json
from curl_cffi.requests import AsyncSession
from bs4 import BeautifulSoup

async def debug_offer_structure(url):
    """Debug - wyświetla surową strukturę JSON oferty"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }
    
    async with AsyncSession() as client:
        try:
            print(f"🔍 Pobieram dane...")
            response = await client.get(url, impersonate="chrome110", timeout=30)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, "html.parser")
                script_tag = soup.find("script", id="__NEXT_DATA__")
                
                if script_tag:
                    data = json.loads(script_tag.string)
                    
                    # Zapisujemy do pliku, żeby zobaczyć strukturę
                    with open("offer_structure_debug.json", "w", encoding="utf-8") as f:
                        json.dump(data, f, indent=2, ensure_ascii=False)
                    
                    print("✅ Struktura zapisana do: offer_structure_debug.json")
                    print("\nPodgląd pierwszych kluczy:")
                    print(json.dumps(list(data.keys()), indent=2))
                else:
                    print("❌ Nie znaleziono __NEXT_DATA__")
            else:
                print(f"❌ Status code: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Błąd: {e}")

async def main():
    url = "https://www.pracuj.pl/praca/dyrektor-zakupow-i-sprzedazy-k-m-inni-lodz,oferta,1004574330"
    await debug_offer_structure(url)

if __name__ == "__main__":
    asyncio.run(main())
