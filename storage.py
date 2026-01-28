import os
from azure.data.tables import TableClient, UpdateMode
from azure.core.exceptions import ResourceNotFoundError
from datetime import datetime
import hashlib

class AzureTableManager:
    def __init__(self, connection_string):
        self.connection_string = connection_string

    def _get_client(self, table_name):
        # Automatyczne tworzenie tabeli, jeśli nie istnieje
        client = TableClient.from_connection_string(self.connection_string, table_name=table_name)
        try:
            client.create_table()
        except:
            pass
        return client

    def save_offers(self, offers, group_name, user_email):
        """
        Zapisuje oferty do tabeli przypisanej do grupy (np. 'OffersHR' lub 'OffersSales').
        """
        if not offers:
            return
            
        table_name = f"Offers{group_name}"
        client = self._get_client(table_name)
        
        for offer in offers:
            # PartitionKey: Słowo kluczowe
            # RowKey: Hash z linku (musi być unikalny i nie może mieć znaków specjalnych)
            row_key = hashlib.md5(offer['Link'].encode()).hexdigest()
            
            entity = {
                "PartitionKey": offer['Keyword'],
                "RowKey": row_key,
                "Title": offer['Title'],
                "Company": offer['Company'],
                "Salary": offer['Salary'],
                "Location": offer['Location'],
                "Link": offer['Link'],
                "Requirements": offer['Requirements'],
                "ScrapedAt": datetime.utcnow().isoformat(),
                "CreatedBy": user_email
            }
            
            # Upsert (Update or Insert)
            client.upsert_entity(mode=UpdateMode.MERGE, entity=entity)

    # def get_all_offers(self, group_name):
    #     """Pobiera wszystkie historyczne oferty dla danej grupy."""
    #     table_name = f"Offers{group_name}"
    #     client = TableClient.from_connection_string(self.connection_string, table_name=table_name)
        
    #     try:
    #         # Pobieramy wszystkie encje z tabeli
    #         entities = client.query_entities(query_filter="")
    #         return list(entities)
    #     except Exception as e:
    #         print(f"Błąd podczas pobierania danych: {e}")
    #         return []
    def get_offers_paginated(self, group_name, results_per_page=100, offset_token=None):
        """Pobiera paczkę ofert korzystając z iteratora stron (pager)."""
        table_name = f"Offers{group_name}"
        client = TableClient.from_connection_string(self.connection_string, table_name=table_name)
        
        try:
            # 1. Tworzymy iterator stron
            pager = client.query_entities(
                query_filter="", 
                results_per_page=results_per_page
            ).by_page(continuation_token=offset_token)
            
            # 2. Pobieramy bieżącą stronę
            current_page = next(pager)
            offers = list(current_page)
            
            # 3. WYCIĄGAMY TOKEN z iteratora (pager), a nie z wyników
            next_token = pager.continuation_token 
            
            return {
                "offers": offers,
                "next_token": next_token
            }
        except StopIteration:
            # Jeśli nie ma więcej stron
            return {"offers": [], "next_token": None}
        except Exception as e:
            print(f"Błąd paginacji: {e}")
            return {"offers": [], "next_token": None}