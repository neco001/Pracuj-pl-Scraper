// --- KONFIGURACJA LIMITÓW ---
const MAX_KEYWORDS = 20; // Maksymalna liczba fraz na jedno zapytanie

let scrapedData = [];

async function startScraping() {
    const textarea = document.getElementById('keywords');
    const keywordsRaw = textarea.value;
    const btn = document.getElementById('btn-search');
    const spinner = document.getElementById('spinner');

    // 1. Przetworzenie i policzenie słów kluczowych
    const keywordList = keywordsRaw.split('\n')
        .map(k => k.trim())
        .filter(k => k.length > 0);

    // 2. Walidacja: Czy puste?
    if (keywordList.length === 0) {
        alert("⚠️ Proszę wpisać co najmniej jedno słowo kluczowe.");
        return;
    }

    // 3. Zabezpieczenie: Czy nie za dużo?
    if (keywordList.length > MAX_KEYWORDS) {
        alert(`🚫 Przekroczono limit! Maksymalna liczba fraz to ${MAX_KEYWORDS}.\nObecnie wpisano: ${keywordList.length}.`);
        return;
    }

    // UI State: Ładowanie
    btn.disabled = true;
    spinner.classList.remove('hidden');

    try {
        const response = await fetch('/scrape', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            // Przesyłamy już przefiltrowaną listę (jako string z nowymi liniami)
            body: JSON.stringify({ keywords: keywordList.join('\n') })
        });
        
        if (!response.ok) throw new Error("Server Error");

        scrapedData = await response.json();
        renderTable();
    } catch (e) {
        console.error("Scraping error:", e);
        alert("❌ Wystąpił błąd podczas pobierania danych. Spróbuj ponownie za chwilę.");
    } finally {
        btn.disabled = false;
        spinner.classList.add('hidden');
    }
}

function renderTable() {
    const container = document.getElementById('results-container');
    const tbody = document.getElementById('results-body');
    const count = document.getElementById('count');
    
    tbody.innerHTML = '';
    
    if (scrapedData.length === 0) {
        tbody.innerHTML = `<tr><td colspan="4" class="p-8 text-center text-slate-500 italic">Nie znaleziono żadnych ofert dla podanych fraz.</td></tr>`;
    } else {
        scrapedData.forEach(item => {
            const row = `
                <tr class="hover:bg-slate-800/50 transition-colors border-b border-slate-800/50">
                    <td class="p-4 font-medium text-blue-400">
                        <a href="${item['Link']}" target="_blank" class="hover:underline">${item['Stanowisko']}</a>
                    </td>
                    <td class="p-4 text-slate-300">${item['Firma']}</td>
                    <td class="p-4 text-slate-400 text-sm">${item['Lokalizacja']}</td>
                    <td class="p-4 text-emerald-400 font-mono text-sm">${item['Wynagrodzenie']}</td>
                </tr>
            `;
            tbody.innerHTML += row;
        });
    }

    count.innerText = scrapedData.length;
    container.classList.remove('hidden');
    // Scroll do wyników
    container.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function downloadCSV() {
    if (scrapedData.length === 0) return;

    const headers = ['Szukana fraza', 'Stanowisko', 'Firma', 'Wynagrodzenie', 'Lokalizacja', 'Link', 'Wymagania (AI)'];
    
    // Tworzenie treści CSV z obsługą cudzysłowów
    const csvContent = [
        headers.join(','),
        ...scrapedData.map(row => 
            headers.map(h => `"${(row[h] || '').toString().replace(/"/g, '""')}"`).join(',')
        )
    ].join('\n');

    const blob = new Blob(["\ufeff" + csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.setAttribute("download", `pracuj_export_${new Date().toISOString().slice(0,10)}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    clearResults();
}

function clearResults() {
    scrapedData = [];
    document.getElementById('results-container').classList.add('hidden');
    document.getElementById('keywords').value = '';
    window.scrollTo({ top: 0, behavior: 'smooth' });
}