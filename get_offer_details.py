import asyncio
import json
from curl_cffi.requests import AsyncSession
from bs4 import BeautifulSoup

async def get_offer_details(url):
    """
    Pobiera szczegółowe informacje o ofercie pracy z Pracuj.pl
    
    Args:
        url: Link do oferty na Pracuj.pl
        
    Returns:
        dict: Słownik ze szczegółami oferty
    """
    async with AsyncSession() as session:
        try:
            response = await session.get(
                url,
                impersonate="chrome110",
                timeout=30
            )
            
            if response.status_code != 200:
                return {"error": f"HTTP {response.status_code}"}
            
            soup = BeautifulSoup(response.text, 'html.parser')
            script_tag = soup.find("script", id="__NEXT_DATA__")
            
            if not script_tag:
                return {"error": "Nie znaleziono __NEXT_DATA__"}
            
            data = json.loads(script_tag.string)
            
            # Nawigacja do danych oferty
            queries = data.get('props', {}).get('pageProps', {}).get('dehydratedState', {}).get('queries', [])
            
            if not queries:
                return {"error": "Brak danych w queries"}
            
            # Pierwszy element queries zawiera dane oferty
            offer_data = queries[0].get('state', {}).get('data', {})
            
            if not offer_data:
                return {"error": "Brak danych oferty"}
            
            # Ekstrakcja danych
            attributes = offer_data.get('attributes', {})
            sections = offer_data.get('sections', [])
            employment = attributes.get('employment', {})
            
            # Podstawowe informacje
            result = {
                'title': attributes.get('jobTitle', 'N/A'),
                'company': attributes.get('displayEmployerName', 'N/A'),
                'url': url,
                'offer_id': offer_data.get('jobOfferWebId', 'N/A'),
                'publication_date': offer_data.get('publicationDetails', {}).get('dateOfInitialPublicationUtc', 'N/A'),
                'expiration_date': offer_data.get('publicationDetails', {}).get('expirationDateUtc', 'N/A'),
                'is_active': offer_data.get('publicationDetails', {}).get('isActive', False),
            }
            
            # Lokalizacja
            workplaces = attributes.get('workplaces', [])
            if workplaces:
                wp = workplaces[0]
                result['location'] = wp.get('displayAddress', 'N/A')
                result['region'] = wp.get('region', {}).get('name', 'N/A')
            else:
                result['location'] = 'N/A'
                result['region'] = 'N/A'
            
            # Zatrudnienie
            result['position_levels'] = [p.get('name', '') for p in employment.get('positionLevels', [])]
            result['work_schedules'] = [w.get('name', '') for w in employment.get('workSchedules', [])]
            result['contract_types'] = [c.get('name', '') for c in employment.get('typesOfContracts', [])]
            result['work_modes'] = [m.get('name', '') for m in employment.get('workModes', [])]
            result['remote_work'] = employment.get('entirelyRemoteWork', False)
            
            # Wynagrodzenie (jeśli dostępne)
            contracts = employment.get('typesOfContracts', [])
            salaries = []
            for contract in contracts:
                salary = contract.get('salary')
                if salary:
                    salaries.append(f"{contract.get('name')}: {salary}")
            result['salary'] = ', '.join(salaries) if salaries else 'Nie podano'
            
            # Kategorie
            categories = attributes.get('categories', [])
            result['categories'] = [f"{c.get('parent', {}).get('name', '')} > {c.get('name', '')}" for c in categories]
            
            # Sekcje oferty
            for section in sections:
                section_type = section.get('sectionType')
                model = section.get('model', {})
                
                if section_type == 'responsibilities':
                    result['responsibilities'] = model.get('bullets', [])
                
                elif section_type == 'requirements':
                    # Wymagania są w subsekcjach
                    subsections = section.get('subSections', [])
                    for subsection in subsections:
                        if subsection.get('sectionType') == 'requirements-expected':
                            result['requirements'] = subsection.get('model', {}).get('bullets', [])
                
                elif section_type == 'offered':
                    result['offered'] = model.get('bullets', [])
                
                elif section_type == 'benefits':
                    items = model.get('items', [])
                    result['benefits'] = [item.get('name', '') for item in items]
                
                elif section_type == 'about-hr-consulting-agency-client':
                    result['about_company'] = model.get('paragraphs', [])
            
            return result
            
        except Exception as e:
            return {"error": str(e)}

async def main():
    # Test URL - przykładowa oferta
    test_url = "https://www.pracuj.pl/praca/dyrektor-zakupow-i-sprzedazy-k-m-inni-lodz,oferta,1004574330"
    
    print("🔍 Pobieranie szczegółów oferty...")
    print(f"URL: {test_url}\n")
    
    details = await get_offer_details(test_url)
    
    if 'error' in details:
        print(f"❌ Błąd: {details['error']}")
        return
    
    # Wyświetlenie wyników
    print("=" * 100)
    print(f"TYTUŁ: {details['title']}")
    print(f"FIRMA: {details['company']}")
    print(f"LOKALIZACJA: {details['location']} ({details['region']})")
    print(f"WYNAGRODZENIE: {details['salary']}")
    print(f"POZIOM: {', '.join(details['position_levels'])}")
    print(f"TRYB PRACY: {', '.join(details['work_modes'])}")
    print(f"UMOWA: {', '.join(details['contract_types'])}")
    print(f"KATEGORIE: {', '.join(details['categories'])}")
    print("=" * 100)
    
    if 'responsibilities' in details:
        print("\n📋 OBOWIĄZKI:")
        for i, resp in enumerate(details['responsibilities'], 1):
            print(f"  {i}. {resp}")
    
    if 'requirements' in details:
        print("\n✅ WYMAGANIA:")
        for i, req in enumerate(details['requirements'], 1):
            print(f"  {i}. {req}")
    
    if 'offered' in details:
        print("\n🎁 OFERUJEMY:")
        for i, off in enumerate(details['offered'], 1):
            print(f"  {i}. {off}")
    
    if 'benefits' in details:
        print("\n💎 BENEFITY:")
        for i, ben in enumerate(details['benefits'], 1):
            print(f"  {i}. {ben}")
    
    print("\n" + "=" * 100)

if __name__ == "__main__":
    asyncio.run(main())
