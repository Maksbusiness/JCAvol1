import requests
import streamlit as st
import pandas as pd
import time
from typing import List, Dict, Any

class PosterClient:
    """
    Extracts data from Poster API.
    Features:
    - Robust Type Checking (Handles '0', 'False', None responses).
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

    def _fetch_all(self, endpoint: str, params: Dict[str, Any] = None) -> List[Dict]:
        """
        Robust Pagination Engine.
        Fetches ALL pages until data is exhausted.
        Includes strict type checking to prevent crashes on malformed API responses.
        """
        if params is None: params = {}
        params["token"] = self.token
        params["limit"] = 1000
        
        all_items = []
        offset = 0
        
        # Status container for long operations
        status = st.empty()

        while True:
            params["offset"] = offset
            try:
                url = f"{self.BASE_URL}/{endpoint}"
                response = requests.get(url, params=params, timeout=30)
                
                # 1. HTTP Status Check
                if response.status_code != 200:
                    st.warning(f"⚠️ HTTP Error {response.status_code} at {endpoint}")
                    break

                try:
                    data = response.json()
                except ValueError:
                    st.warning(f"⚠️ Invalid JSON received from {endpoint}")
                    break

                # --- CRITICAL TYPE SAFETY CHECKS ---
                
                # 2. Top-level check: Poster sometimes returns raw 0 or False
                if isinstance(data, (int, bool)) or data is None:
                    # Treat as empty result / end of data
                    break

                # 3. Check for API-level errors (only if data is a dict)
                if isinstance(data, dict) and "error" in data:
                    # Log error but return what we have collected so far
                    err_msg = data['error'].get('message', 'Unknown Error')
                    st.warning(f"⚠️ API Error ({endpoint}): {err_msg}")
                    break

                # 4. Extract 'response' safely
                # If data is a list (very rare for Poster), use it directly
                raw_response = data if isinstance(data, list) else data.get("response")

                # 5. Check 'response' value type
                # It can be None, 0, False, or an empty list
                if isinstance(raw_response, (int, bool)) or raw_response is None:
                    break

                # 6. Normalize Batch
                batch = []
                if isinstance(raw_response, list):
                    batch = raw_response
                elif isinstance(raw_response, dict):
                    # Handle cases like {'data': [...], 'meta': ...}
                    if 'data' in raw_response:
                        batch = raw_response['data']
                    else:
                        # Fallback: Treat values as list (e.g. settings/associative arrays)
                        batch = list(raw_response.values())

                if not batch:
                    break

                all_items.extend(batch)
                status.caption(f"📥 {endpoint}: Fetched {len(all_items)} rows...")

                # Stop condition: Last page reached
                if len(batch) < params["limit"]:
                    break

                # Next page
                offset += params["limit"]
                time.sleep(0.3) # Rate limit protection

            except requests.exceptions.RequestException as e:
                st.error(f"❌ Network Error ({endpoint}): {e}")
                break
            except Exception as e:
                st.error(f"❌ Unexpected Error ({endpoint}): {e}")
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
            
            # Handle API variations where ingredients might be missing or explicitly False/None
            if not ingredients or isinstance(ingredients, (int, bool)):
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
                    "ingredient_name": item.get("ingredient_name"), 
                    "quantity": num,
                    "unit_price": price,
                    "total_sum": total_sum
                })
        
        return pd.DataFrame(flattened_rows)

