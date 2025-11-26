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

    def _fetch_all(self, endpoint: str, params: Dict[str, Any] = None) -> List[Dict]:
        """
        Robust Pagination Engine.
        Fetches ALL pages until data is exhausted.
        Fixes 'int object has no attribute get' error by strict type checking.
        """
        if params is None: params = {}
        params["token"] = self.token
        params["limit"] = 1000
        
        all_items = []
        offset = 0
        
        status = st.empty()

        while True:
            params["offset"] = offset
            try:
                url = f"{self.BASE_URL}/{endpoint}"
                response = requests.get(url, params=params, timeout=30)
                
                # 1. HTTP Check
                if response.status_code != 200:
                    st.warning(f"⚠️ HTTP Error {response.status_code} at {endpoint}")
                    break

                try:
                    data = response.json()
                except ValueError:
                    st.warning(f"⚠️ Invalid JSON received from {endpoint}")
                    break

                # 2. IMMEDIATE TYPE CHECK (The Fix)
                # Якщо API повернуло 0, False або null — це не словник, виходимо одразу.
                if not isinstance(data, dict):
                    # Poster часто повертає просто 0, якщо даних немає. Це нормальна поведінка.
                    if data in [0, False, None]:
                        break
                    # Якщо це список (рідко, але буває)
                    if isinstance(data, list):
                        all_items.extend(data)
                        if len(data) < params["limit"]: break
                        offset += params["limit"]
                        continue
                    
                    st.warning(f"⚠️ Unknown response format from {endpoint}: {type(data)}")
                    break

                # 3. Тепер ми впевнені, що data — це словник (dict)
                # Можна безпечно використовувати .get()
                
                if "error" in data:
                    err_msg = data['error'].get('message', 'Unknown Error')
                    st.warning(f"⚠️ API Error ({endpoint}): {err_msg}")
                    break

                # Отримуємо поле 'response'
                raw_response = data.get("response")

                # 4. Перевіряємо вміст 'response'
                # Він теж може бути 0, False або None
                if not raw_response or raw_response in [0, False]:
                    break

                # 5. Нормалізація батчу
                batch = []
                if isinstance(raw_response, list):
                    batch = raw_response
                elif isinstance(raw_response, dict):
                    if 'data' in raw_response:
                        batch = raw_response['data']
                    else:
                        batch = list(raw_response.values())
                
                if not batch:
                    break

                all_items.extend(batch)
                status.caption(f"📥 {endpoint}: Fetched {len(all_items)} rows...")

                if len(batch) < params["limit"]:
                    break

                offset += params["limit"]
                time.sleep(0.3)

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

