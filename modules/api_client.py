import requests
import streamlit as st
import time
from typing import Dict, List, Any, Optional

class PosterClient:
    """
    Клієнт для Poster POS API (v3) з підтримкою Data Lake (пагінація).
    """
    
    BASE_URL = "https://joinposter.com/api"

    def __init__(self):
        try:
            self.token = st.secrets["poster"]["token"]
        except KeyError:
            st.error("❌ Критична помилка: Токен Poster API не знайдено у secrets.toml")
            st.stop()

    def _make_raw_request(self, endpoint: str, params: Dict[str, Any]) -> Optional[Any]:
        """Виконує один запит до API."""
        params_copy = params.copy()
        params_copy["token"] = self.token
        url = f"{self.BASE_URL}/{endpoint}"
        
        try:
            response = requests.get(url, params=params_copy, timeout=45)
            response.raise_for_status()
            data = response.json()
            
            if "error" in data:
                st.warning(f"⚠️ API Error [{endpoint}]: {data['error'].get('message')}")
                return None
            
            return data.get("response", data)

        except Exception as e:
            st.error(f"❌ Connection Error [{endpoint}]: {e}")
            return None

    def _get_all_items(self, endpoint: str, base_params: Dict[str, Any] = None) -> List[Dict]:
        """
        Універсальний метод пагінації. Витягує ВСІ дані циклом.
        """
        if base_params is None: base_params = {}
        
        all_items = []
        limit = 100
        offset = 0
        
        params = base_params.copy()
        params['limit'] = limit
        
        # Для візуалізації у Streamlit (щоб користувач бачив процес)
        status_container = st.empty()
        
        while True:
            params['offset'] = offset
            response = self._make_raw_request(endpoint, params)
            
            if response is None:
                break

            # Нормалізація відповіді
            batch = []
            if isinstance(response, list):
                batch = response
            elif isinstance(response, dict):
                # Poster іноді повертає {'data': [...]} або об'єкт зі списком у values
                batch = response.get('data', list(response.values()) if response else [])
            
            if not batch:
                break
                
            all_items.extend(batch)
            status_container.caption(f"🔄 Завантажено {len(all_items)} записів з {endpoint}...")
            
            # Якщо завантажили менше ліміту — це кінець
            if len(batch) < limit:
                break
                
            offset += limit
            time.sleep(0.1) # Rate limit protection

        status_container.empty()
        return all_items

    # --- Data Lake Methods ---

    def get_transactions(self, date_from: str, date_to: str) -> List[Dict]:
        """Всі чеки з товарами."""
        params = {
            "date_from": date_from,
            "date_to": date_to,
            "include_products": 1,
            "status": 2
        }
        return self._get_all_items("transactions.getTransactions", params)

    def get_menu(self) -> List[Dict]:
        """Всі товари (меню) з цінами та собівартістю."""
        return self._get_all_items("menu.getProducts")

    def get_categories(self) -> List[Dict]:
        """Категорії товарів."""
        return self._get_all_items("menu.getCategories")

    def get_employees(self) -> List[Dict]:
        """Співробітники."""
        return self._get_all_items("access.getEmployees")