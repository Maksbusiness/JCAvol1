import requests
import streamlit as st
import time
import pandas as pd
from typing import List, Dict, Any, Optional

class PosterClient:
    """
    Advanced Client for Poster POS API (v3) with Data Lake capabilities.
    Features:
    - Automatic Pagination (Offset/Limit loop).
    - Rate Limiting protection.
    - Error tolerance.
    - Data flattening and normalization.
    """

    BASE_URL = "https://joinposter.com/api"

    def __init__(self):
        try:
            self.token = st.secrets["poster"]["token"]
        except KeyError:
            st.error("❌ Critical Error: Poster API token not found in secrets.toml")
            st.stop()

    def _fetch_all(self, endpoint: str, params: Dict[str, Any] = None) -> List[Dict]:
        """
        Private engine to fetch ALL records using pagination.
        Stops when API returns fewer records than limit or an empty list.
        """
        if params is None:
            params = {}

        # Standardize params
        params["token"] = self.token
        limit = 1000
        params["limit"] = limit
        
        all_items = []
        offset = 0
        
        # UI Feedback for long operations
        status_placeholder = st.empty()
        
        while True:
            params["offset"] = offset
            url = f"{self.BASE_URL}/{endpoint}"

            try:
                response = requests.get(url, params=params, timeout=30)
                response.raise_for_status()
                data = response.json()

                # Error Handling from API logic
                if "error" in data:
                    # Log error but return what we have collected so far to save progress
                    st.error(f"⚠️ API Error at {endpoint} (offset {offset}): {data['error'].get('message')}")
                    break

                # Extract response data
                # Poster sometimes returns {'response': [...]} or {'response': {'data': [...]}}
                raw_response = data.get("response", [])
                
                batch = []
                if isinstance(raw_response, list):
                    batch = raw_response
                elif isinstance(raw_response, dict):
                    # Handle cases like {'data': [...], 'meta': ...}
                    if 'data' in raw_response:
                        batch = raw_response['data']
                    else:
                        # Fallback for dict-based responses (e.g. settings)
                        batch = list(raw_response.values())

                if not batch:
                    break

                all_items.extend(batch)
                
                # Update UI status
                status_placeholder.caption(f"🔄 Fetching {endpoint}... ({len(all_items)} records)")

                # Stop condition: Last page reached
                if len(batch) < limit:
                    break

                # Increment offset
                offset += limit

                # Rate Limiting (Crucial)
                time.sleep(0.3)

            except requests.exceptions.RequestException as e:
                st.error(f"❌ Network Error at {endpoint}: {e}")
                break
        
        status_placeholder.empty()
        return all_items

    # --- PUBLIC DATA LAKE METHODS ---

    def get_transactions(self, date_from: str, date_to: str) -> List[Dict]:
        """endpoint: dash.getTransactions"""
        # API Docs require YYYYMMDD for dash.getTransactions
        d_from = date_from.replace("-", "")
        d_to = date_to.replace("-", "")
        
        params = {
            "dateFrom": d_from,
            "dateTo": d_to,
            "include_products": 1,
            "status": 2 # Closed/Successful checks only
        }
        return self._fetch_all("dash.getTransactions", params)

    def get_menu_products(self) -> List[Dict]:
        """endpoint: menu.getProducts"""
        return self._fetch_all("menu.getProducts")

    def get_menu_ingredients(self) -> List[Dict]:
        """endpoint: menu.getIngredients"""
        return self._fetch_all("menu.getIngredients")

    def get_suppliers(self) -> List[Dict]:
        """endpoint: storage.getSuppliers"""
        return self._fetch_all("storage.getSuppliers")

    def get_employees(self) -> List[Dict]:
        """endpoint: access.getEmployees"""
        return self._fetch_all("access.getEmployees")

    def get_waste_reasons(self) -> List[Dict]:
        """endpoint: storage.getWasteReasons"""
        return self._fetch_all("storage.getWasteReasons")

    def get_leftovers(self) -> List[Dict]:
        """endpoint: storage.getStorageLeftovers"""
        return self._fetch_all("storage.getStorageLeftovers")

    def get_supplies(self, date_from: str, date_to: str) -> pd.DataFrame:
        """
        endpoint: storage.getSupplies
        Performs Flattening logic for nested ingredients.
        """
        params = {
            "dateFrom": date_from,
            "dateTo": date_to
        }
        
        # 1. Fetch Raw Nested Data
        raw_supplies = self._fetch_all("storage.getSupplies", params)
        
        flat_data = []

        # 2. Flattening Process
        for supply in raw_supplies:
            supply_id = supply.get("supply_id")
            supply_date = supply.get("date")
            supplier_id = supply.get("supplier_id")
            
            # Check if ingredients exist in the response (depends on API version/flags)
            # If API doesn't return ingredients in list, separate calls to storage.getSupplyIngredients might be needed.
            # Assuming prompt implies nested data is present or we handle the structure found.
            ingredients = supply.get("ingredients", []) 
            
            if not ingredients:
                continue

            for item in ingredients:
                # Poster returns sums in cents. We convert to main currency units.
                sum_cents = float(item.get("sum", 0))
                num = float(item.get("num", 0))
                
                row = {
                    "supply_id": supply_id,
                    "date": supply_date,
                    "supplier_id": supplier_id,
                    "ingredient_id": item.get("ingredient_id"),
                    "num": num,
                    "sum": sum_cents / 100.0, # Convert to currency
                    "price_per_unit": (sum_cents / 100.0) / num if num > 0 else 0
                }
                flat_data.append(row)

        return pd.DataFrame(flat_data)

    def get_wastes(self, date_from: str, date_to: str) -> List[Dict]:
        """endpoint: storage.getWastes"""
        params = {"dateFrom": date_from, "dateTo": date_to}
        return self._fetch_all("storage.getWastes", params)

    def get_ingredient_write_offs(self, date_from: str, date_to: str) -> List[Dict]:
        """endpoint: storage.getIngredientWriteOff"""
        params = {"dateFrom": date_from, "dateTo": date_to}
        return self._fetch_all("storage.getIngredientWriteOff", params)

    def get_inventories(self, date_from: str, date_to: str) -> List[Dict]:
        """endpoint: storage.getStorageInventories"""
        params = {"dateFrom": date_from, "dateTo": date_to}
        return self._fetch_all("storage.getStorageInventories", params)