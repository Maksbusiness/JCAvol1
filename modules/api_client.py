import requests
import streamlit as st
import pandas as pd
import time
from typing import List, Dict, Any

class PosterClient:
    """
    Extracts data from Poster API.
    Features:
    - Robust Type Checking (Safe JSON parsing).
    - Pagination & Rate Limiting.
    - Data Flattening.
    """

    BASE_URL = "https://joinposter.com/api"

    def __init__(self):
        try:
            self.token = st.secrets["poster"]["token"]
        except KeyError:
            st.error("❌ API Config Error: Token not found in secrets.")
            st.stop()

    def _fetch_all(self, endpoint, params=None):
        """
        Забирає всі сторінки даних, ігноруючи не-dict відповіді від Poster.
        """
        if params is None:
            params = {}
        
        params['limit'] = 1000
        params['offset'] = 0
        all_data = []
        
        while True:
            try:
                response = requests.get(f"{self.base_url}/{endpoint}", params={**self.base_params, **params})
                response.raise_for_status()
                
                data = response.json()

                # --- ФІКС КРИТИЧНОГО БАГУ ---
                # Якщо Poster повернув 0, False, True, або будь-що, що не є словником,
                # ми просто виходимо з циклу. Це і є помилка 'int' object has no attribute "get".
                if not isinstance(data, dict):
                    break
                # ---------------------------

                # Шукаємо список даних всередині 'response'
                result = data.get('response')

                if not result:
                    break
                
                # Якщо result це список (чеки, поставки)
                if isinstance(result, list):
                    all_data.extend(result)
                    if len(result) < 1000: # Остання сторінка
                        break
                
                # Якщо це словник (наприклад, налаштування)
                elif isinstance(result, dict):
                    all_data.append(result)
                    break
                
                params['offset'] += 1000
                time.sleep(0.2)

            except Exception as e:
                # Наприклад, помилка JSON або timeout. Просто зупиняємось.
                print(f"Error fetching {endpoint}: {e}")
                break
        
        return all_data

    # --- Public Transformation Methods ---

    def get_transactions(self, date_from: str, date_to: str) -> pd.DataFrame:
        """Endpoint: dash.getTransactions"""
        params = {
            "dateFrom": date_from.replace("-", ""),
            "dateTo": date_to.replace("-", ""),
            "include_products": 1,
            "status": 2
        }
        data = self._fetch_all("dash.getTransactions", params)
        return pd.DataFrame(data)

    def get_menu_products(self) -> pd.DataFrame:
        """Endpoint: menu.getProducts"""
        data = self._fetch_all("menu.getProducts")
        return pd.DataFrame(data)

    def get_menu_ingredients(self) -> pd.DataFrame:
        """Endpoint: menu.getIngredients"""
        data = self._fetch_all("menu.getIngredients")
        return pd.DataFrame(data)

    def get_employees(self) -> pd.DataFrame:
        """Endpoint: access.getEmployees"""
        data = self._fetch_all("access.getEmployees")
        return pd.DataFrame(data)

    def get_wastes(self, date_from: str, date_to: str) -> pd.DataFrame:
        """Endpoint: storage.getWastes"""
        params = {"dateFrom": date_from, "dateTo": date_to}
        data = self._fetch_all("storage.getWastes", params)
        return pd.DataFrame(data)

    def get_inventories(self, date_from: str, date_to: str) -> pd.DataFrame:
        """Endpoint: storage.getStorageInventories"""
        params = {"dateFrom": date_from, "dateTo": date_to}
        data = self._fetch_all("storage.getStorageInventories", params)
        return pd.DataFrame(data)

    def get_supplies(self, date_from: str, date_to: str) -> pd.DataFrame:
        """
        Endpoint: storage.getSupplies
        Flattens nested 'ingredients' list.
        """
        params = {"dateFrom": date_from, "dateTo": date_to}
        raw_data = self._fetch_all("storage.getSupplies", params)
        
        flattened_rows = []
        
        for supply in raw_data:
            s_id = supply.get("supply_id")
            s_date = supply.get("date")
            s_supplier = supply.get("supplier_id")
            
            ingredients = supply.get("ingredients", [])
            
            # Additional safety check for ingredients
            if not ingredients or isinstance(ingredients, (int, bool)):
                continue
                
            for item in ingredients:
                try:
                    price = float(item.get("price", 0)) / 100.0
                    total_sum = float(item.get("sum", 0)) / 100.0
                    num = float(item.get("num", 0))
                except (ValueError, TypeError):
                    price, total_sum, num = 0, 0, 0

                flattened_rows.append({
                    "supply_id": s_id,
                    "date": s_date,
                    "supplier_id": s_supplier,
                    "ingredient_id": item.get("ingredient_id"),
                    "ingredient_name": item.get("ingredient_name"), 
                    "quantity": num,
                    "unit_price": price,
                    "total_sum": total_sum
                })
        
        return pd.DataFrame(flattened_rows)

