import requests
import streamlit as st
import pandas as pd
import time
from typing import List, Dict, Any

class PosterClient:
    """
    Extracts data from Poster API.
    Handles Pagination, Rate Limiting, and Data Flattening.
    """

    BASE_URL = "https://joinposter.com/api"

    def __init__(self):
        try:
            self.token = st.secrets["poster"]["token"]
        except KeyError:
            st.error("❌ API Config Error: Token not found.")
            st.stop()

    def _fetch_all(self, endpoint: str, params: Dict[str, Any] = None) -> List[Dict]:
        """
        Robust Pagination Engine.
        Fetches ALL pages until data is exhausted.
        """
        if params is None: params = {}
        params["token"] = self.token
        params["limit"] = 1000
        
        all_items = []
        offset = 0
        
        # Status container for long operations (optional UI feedback)
        status = st.empty()

        while True:
            params["offset"] = offset
            try:
                response = requests.get(f"{self.BASE_URL}/{endpoint}", params=params, timeout=30)
                response.raise_for_status()
                data = response.json()

                if "error" in data:
                    st.warning(f"⚠️ API Error ({endpoint}): {data['error'].get('message')}")
                    break

                # Extract data safely
                batch = data.get("response", [])
                if isinstance(batch, dict):
                    if 'data' in batch: batch = batch['data']
                    else: batch = list(batch.values())

                if not batch:
                    break

                all_items.extend(batch)
                status.caption(f"📥 {endpoint}: Fetched {len(all_items)} rows...")

                if len(batch) < params["limit"]:
                    break

                offset += params["limit"]
                time.sleep(0.3) # Rate limit protection

            except Exception as e:
                st.error(f"❌ Network Error ({endpoint}): {e}")
                break
        
        status.empty()
        return all_items

    # --- Public Transformation Methods ---

    def get_transactions(self, date_from: str, date_to: str) -> pd.DataFrame:
        """Endpoint: dash.getTransactions"""
        # API requires YYYYMMDD
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
        CRITICAL: Flattens nested 'ingredients' list into separate rows.
        """
        params = {"dateFrom": date_from, "dateTo": date_to}
        raw_data = self._fetch_all("storage.getSupplies", params)
        
        flattened_rows = []
        
        for supply in raw_data:
            s_id = supply.get("supply_id")
            s_date = supply.get("date")
            s_supplier = supply.get("supplier_id")
            
            ingredients = supply.get("ingredients", [])
            
            # Handle API variations where ingredients might be missing
            if not ingredients:
                continue
                
            for item in ingredients:
                # Poster sends money in cents (strings). Convert to float.
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
                    "ingredient_name": item.get("ingredient_name"), # Optional but helpful
                    "quantity": num,
                    "unit_price": price,
                    "total_sum": total_sum
                })
        
        return pd.DataFrame(flattened_rows)
