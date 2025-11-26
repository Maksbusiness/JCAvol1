import requests
import streamlit as st
from typing import Dict, List, Any, Optional
import json

class PosterClient:
    """
    Клієнт для взаємодії з Poster POS API (v3).
    """
    
    BASE_URL = "https://joinposter.com/api"

    def __init__(self):
        try:
            self.token = st.secrets["poster"]["token"]
        except KeyError:
            st.error("❌ Помилка: Токен Poster API не знайдено у secrets.toml")
            st.stop()

    def make_request(self, endpoint: str, params: Dict[str, Any] = None) -> Optional[Dict | List]:
        """
        Універсальний метод запиту.
        """
        if params is None:
            params = {}
        
        params["token"] = self.token
        url = f"{self.BASE_URL}/{endpoint}"
        
        try:
            response = requests.get(url, params=params, timeout=20)
            response.raise_for_status()
            
            data = response.json()
            
            if "error" in data:
                st.error(f"⚠️ API Error ({endpoint}): {data['error'].get('message')}")
                return None
                
            return data.get("response", data)

        except Exception as e:
            st.error(f"❌ Connection Error: {e}")
            return None

    def get_transactions(self, date_from: str, date_to: str) -> List[Dict]:
        """
        Отримання чеків (з товарами).
        """
        params = {
            "date_from": date_from,
            "date_to": date_to,
            "include_products": 1,
            "status": 2
        }
        result = self.make_request("transactions.getTransactions", params)
        
        # Стандартна обробка результату Poster
        if isinstance(result, list): return result
        if isinstance(result, dict): return result.get('data', [])
        return []

    def get_menu_products(self) -> List[Dict]:
        """
        Отримання списку всіх товарів меню.
        """
        result = self.make_request("menu.getProducts")
        
        if isinstance(result, list): return result
        if isinstance(result, dict): return result.get('data', [])
        return []

    def get_supplies(self, date_from: str, date_to: str) -> List[Dict]:
        """
        Отримання поставок (заглушка або реальний запит).
        """
        params = {
            "date_from": date_from,
            "date_to": date_to
        }
        result = self.make_request("storage.getSupplies", params)
        
        if isinstance(result, list): return result
        if isinstance(result, dict): return result.get('data', [])
        return []
