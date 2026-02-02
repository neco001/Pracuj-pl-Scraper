
import duckdb
import argparse
import sys
import os
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from tabulate import tabulate

# Configuration - Używamy ścieżek relatywnych, żeby skrypt działał u każdego
BASE_DIR = Path(__file__).parent
DB_PATH = os.path.join(BASE_DIR, 'job_crusher.duckdb')
CV_MOJE_PATH = os.path.join(BASE_DIR, 'CV Moje')
ARCHIVE_PATH = os.path.join(CV_MOJE_PATH, '99_Arichwum')

ACTIVE_STATUSES = ['New', 'Lead', 'Applied', 'Under Review', 'Interview', 'Offer']

def get_conn():
    """Zwraca połączenie i inicjalizuje schemat jeśli trzeba."""
    conn = duckdb.connect(DB_PATH)
    
    # Inicjalizacja schematu (żeby nowy user nie musiał nic robić)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS companies (
            id INTEGER PRIMARY KEY,
            name VARCHAR UNIQUE,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS offers (
            id INTEGER PRIMARY KEY,
            company_id INTEGER,
            title VARCHAR,
            location VARCHAR,
            source_url VARCHAR UNIQUE,
            status VARCHAR DEFAULT 'Lead',
            note TEXT,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (company_id) REFERENCES companies(id)
        );
    """)
    return conn

def add_offer(company_name, title, location, source_url, status='New'):
    with get_conn() as conn:
        conn.execute("INSERT INTO companies (name) VALUES (?) ON CONFLICT (name) DO NOTHING", (company_name,))
        comp_id = conn.execute("SELECT id FROM companies WHERE name = ?", (company_name,)).fetchone()[0]
        conn.execute("""
            INSERT INTO offers (company_id, title, location, source_url, status)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT (source_url) DO NOTHING
        """, (comp_id, title, location, source_url, status))
        
        result = conn.execute("SELECT id FROM offers WHERE source_url = ?", (source_url,)).fetchone()
        if result:
            print(f"✅ Added/Exists [ID:{result[0]}] {title} at {company_name}")

def update_offer(offer_id, status=None, note=None):
    with get_conn() as conn:
        if status:
            conn.execute("UPDATE offers SET status = ? WHERE id = ?", (status, offer_id))
        if note:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
            conn.execute("UPDATE offers SET note = COALESCE(note, '') || '\n' || ? || ': ' || ? WHERE id = ?", (timestamp, note, offer_id))
        print(f"✅ Updated ID:{offer_id}")

def show_stats():
    with get_conn() as conn:
        stats = conn.execute("SELECT status, count(*) FROM offers GROUP BY status ORDER BY count(*) DESC").fetchall()
        print("\n--- JOB CRUSHER STATS ---")
        if not stats:
            print("Baza jest pusta.")
        else:
            print(tabulate(stats, headers=["Status", "Count"], tablefmt="fancy_grid"))

def list_offers(query=None, show_all=False, limit=25):
    with get_conn() as conn:
        sql = """
            SELECT o.id, c.name, o.title, o.status, CAST(o.added_at AS DATE)
            FROM offers o JOIN companies c ON o.company_id = c.id
        """
        params = []
        where_clauses = []
        if not show_all and not query:
            placeholders = ",".join(["?"] * len(ACTIVE_STATUSES))
            where_clauses.append(f"o.status IN ({placeholders})")
            params.extend(ACTIVE_STATUSES)
        if query:
            where_clauses.append("(o.title LIKE ? OR c.name LIKE ? OR o.status LIKE ?)")
            params.extend([f"%{query}%", f"%{query}%", f"%{query}%"])
        if where_clauses:
            sql += " WHERE " + " AND ".join(where_clauses)
        sql += " ORDER BY o.added_at DESC LIMIT ?"
        params.append(limit)
        
        data = conn.execute(sql, params).fetchall()
        print(f"\n--- OFFERS ({'ALL' if show_all else 'ACTIVE ONLY'}) ---")
        if not data:
            print("Brak pasujących ofert.")
        else:
            print(tabulate(data, headers=["ID", "Company", "Title", "Status", "Date"], tablefmt="simple"))

def cleanup_and_archive():
    print("--- STARTING CLEANUP & ARCHIVE PROTOCOL ---")
    with get_conn() as conn:
        limit_date = (datetime.now() - timedelta(days=60))
        affected = conn.execute("""
            UPDATE offers 
            SET status = 'No Response' 
            WHERE status IN ('New', 'Applied', 'Lead') 
            AND added_at < ?
        """, (limit_date,)).rowcount
        print(f"Baza: Zmieniono status na 'No Response' dla {affected} starych ofert.")

    # Archiwizacja folderów (tylko w obrębie lokalnego folderu)
    if not os.path.exists(CV_MOJE_PATH): 
        print("Folder CV Moje nie istnieje lokalnie.")
        return

    # To wymaga pełnej implementacji bazy - zostawiam wersję bezpieczną
    print("--- ARCHIVE SKIP (Manual check recommended) ---")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--add', action='store_true')
    parser.add_argument('--update', type=int)
    parser.add_argument('--status', type=str)
    parser.add_argument('--note', type=str)
    parser.add_argument('--list', action='store_true')
    parser.add_argument('--all', action='store_true')
    parser.add_argument('--search', type=str)
    parser.add_argument('--stats', action='store_true')
    parser.add_argument('--cleanup', action='store_true')
    parser.add_argument('--company', help='Company name')
    parser.add_argument('--title', help='Job title')
    parser.add_argument('--url', default='')
    
    args = parser.parse_args()
    if args.add: add_offer(args.company, args.title, 'Uknown', args.url)
    elif args.update: update_offer(args.update, args.status, args.note)
    elif args.stats: show_stats()
    elif args.list: list_offers(show_all=args.all)
    elif args.search: list_offers(args.search, show_all=True)
    elif args.cleanup: cleanup_and_archive()
    else: parser.print_help()
