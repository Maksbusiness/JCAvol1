import requests
import streamlit as st
from typing import Dict, List, Any, Optional
import json

class PosterClient:
    """
    Клієнт для взаємодії з Poster POS API (v3).
    Відповідає тільки за отримання даних.
    """
    
    BASE_URL = "https://joinposter.com/api"

    def __init__(self):
        try:
            self.token = st.secrets["poster"]["token"]
        except KeyError:
            st.error("❌ Критична помилка: Токен Poster API не знайдено у secrets.toml")
            st.stop()

    def _make_request(self, endpoint: str, params: Dict[str, Any] = None) -> Optional[List[Dict]]:
        """Внутрішній метод для виконання запитів."""
        if params is None:
            params = {}
        
        params["token"] = self.token
        url = f"{self.BASE_URL}/{endpoint}"
        
        try:
            # Збільшений таймаут для великих вивантажень
            response = requests.get(url, params=params, timeout=45)
            response.raise_for_status()
            
            data = response.json()
            
            if "error" in data:
                st.error(f"⚠️ API Error [{endpoint}]: {data['error'].get('message')}")
                return None
            
            # Poster може повертати: list, dict {'data': []}, або dict {1: {}, 2: {}}
            resp = data.get("response", data)
            
            if isinstance(resp, list):
                return resp
            elif isinstance(resp, dict):
                if 'data' in resp:
                    return resp['data']
                return list(resp.values())
            
            return []

        except Exception as e:
            st.error(f"❌ Мережева помилка [{endpoint}]: {e}")
            return None

    def get_transactions(self, date_from: str, date_to: str) -> List[Dict]:
        """Отримання чеків (з деталізацією товарів)."""
        params = {
            "date_from": date_from,
            "date_to": date_to,
            "include_products": 1,  # Критично для аналітики товарів
            "status": 2             # Запитуємо закриті чеки (але фільтруватимемо ще й в Pandas)
        }
        return self._make_request("transactions.getTransactions", params) or []

    def get_products(self) -> List[Dict]:
        """Отримання меню та техкарт."""
        return self._make_request("menu.getProducts") or []

    def get_ingredients(self) -> List[Dict]:
        """Отримання інгредієнтів."""
        return self._make_request("menu.getIngredients") or []

    def get_suppliers(self) -> List[Dict]:
        """Отримання довідника постачальників."""
        return self._make_request("access.getSuppliers") or []

    def get_supplies(self, date_from: str, date_to: str) -> List[Dict]:
        """Отримання накладних постачання."""
        params = {
            "date_from": date_from,
            "date_to": date_to
        }
        return self._make_request("storage.getSupplies", params) or []
