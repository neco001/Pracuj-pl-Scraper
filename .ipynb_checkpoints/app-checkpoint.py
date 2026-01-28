from flask import Flask, render_template, jsonify, request, session, redirect, url_for
import asyncio
from curl_cffi.requests import AsyncSession
from scraper import PracujScraper
from storage import AzureTableManager
import os
from dotenv import load_dotenv
from auth import AuthManager, create_password_hash # Importujemy nasz moduł
import json
import base64
app = Flask(__name__)

load_dotenv()

# Konfiguracja (na Azure pobierana ze zmiennych środowiskowych)
AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
if not AZURE_STORAGE_CONNECTION_STRING:
    raise ValueError("Brak AZURE_STORAGE_CONNECTION_STRING w konfiguracji środowiskowej!")

app.secret_key = os.getenv("FLASK_SECRET_KEY")
if not app.secret_key:
    raise ValueError("Brak FLASK_SECRET_KEY w konfiguracji środowiskowej!")


storage_manager = AzureTableManager(AZURE_STORAGE_CONNECTION_STRING)
auth_manager = AuthManager(AZURE_STORAGE_CONNECTION_STRING)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = auth_manager.verify_user(email, password)
        if user:
            session['user'] = user # Zapisujemy dane użytkownika w sesji
            return redirect(url_for('index'))
        
        return render_template('login.html', error="Błędny login lub hasło")
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

@app.route('/')
def index():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('index.html', user=session['user'])

@app.route('/scrape', methods=['POST'])
async def scrape():
    if 'user' not in session:
        return jsonify({"error": "Brak autoryzacji"}), 401
        
    data = request.json
    keywords = list(set([k.strip() for k in data.get('keywords', '').split('\n') if k.strip()]))
    
    # Symulacja grupy użytkownika (później pobierane z modułu logowania)
    user_group = session['user']['group'] # Domyślnie HR
    user_email = session['user']['email']
    
    scraper = PracujScraper()
    all_results = []
    
    async with AsyncSession() as client:
        tasks = [scraper.scrape_keyword(client, kw) for kw in keywords]
        results = await asyncio.gather(*tasks)
        for r in results:
            all_results.extend(r)
    
    # Zapis do bazy danych Azure
    try:
        storage_manager.save_offers(all_results, user_group, user_email)
    except Exception as e:
        print(f"Błąd zapisu do Azure Table Storage: {e}")

    # Mapowanie na polskie nazwy dla frontendu (zgodnie z Twoim poprzednim wymogiem)
    formatted_results = []
    for o in all_results:
        formatted_results.append({
            'Szukana fraza': o['Keyword'],
            'Stanowisko': o['Title'],
            'Firma': o['Company'],
            'Wynagrodzenie': o['Salary'],
            'Lokalizacja': o['Location'],
            'Link': o['Link'],
            'Wymagania (AI)': o['Requirements']
        })

    # Usuwanie duplikatów przed wysłaniem na frontend
    unique_results = {o['Link']: o for o in formatted_results}.values()
    return jsonify(list(unique_results))

def encode_token(token):
    """Zmienia słownik Azure na bezpieczny ciąg znaków Base64."""
    if not token:
        return None
    # Azure token to zazwyczaj słownik, zamieniamy go na JSON, potem na bajty
    token_json = json.dumps(token)
    return base64.urlsafe_b64encode(token_json.encode()).decode()

def decode_token(encoded_str):
    """Zmienia ciąg Base64 z powrotem na słownik dla Azure."""
    if not encoded_str:
        return None
    try:
        # Dekodujemy z formatu bezpiecznego dla URL
        decoded_bytes = base64.urlsafe_b64decode(encoded_str.encode())
        return json.loads(decoded_bytes.decode())
    except Exception as e:
        print(f"Błąd dekodowania tokena: {e}")
        return None

@app.route('/history')
def history():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    # 1. Pobieramy zakodowany (bezpieczny) string z adresu URL
    raw_token = request.args.get('token')
    
    # 2. Dekodujemy go na słownik, który rozumie biblioteka Azure
    azure_token = decode_token(raw_token)
    
    group = session['user']['group']
    
    # 3. Pobieramy dane z bazy używając zdekodowanego tokena
    result = storage_manager.get_offers_paginated(
        group, 
        results_per_page=100, 
        offset_token=azure_token
    )
    
    # 4. NOWY token z Azure znów kodujemy w Base64 przed wysłaniem do guzika "Następne"
    safe_next_token = encode_token(result['next_token'])
    
    return render_template(
        'history.html', 
        offers=result['offers'], 
        next_token=safe_next_token,
        user=session['user']
    )

if __name__ == "__main__":
    app.run(debug=True)