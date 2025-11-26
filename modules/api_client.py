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
        Універсальний метод для запитів до API.
        """
        if params is None:
            params = {}
        
        params["token"] = self.token
        url = f"{self.BASE_URL}/{endpoint}"
        
        try:
            response = requests.get(url, params=params, timeout=15)
            response.raise_for_status()
            
            data = response.json()
            
            if "error" in data:
                st.error(f"⚠️ Помилка API Poster ({data['error'].get('code')}): {data['error'].get('message')}")
                return None
                
            return data.get("response", data)

        except requests.exceptions.RequestException as e:
            st.error(f"❌ Мережева помилка: {e}")
            return None
        except json.JSONDecodeError:
            st.error("❌ Помилка: Невалідний JSON від API")
            return None

    def get_transactions(self, date_from: str, date_to: str) -> List[Dict]:
        """
        Отримання списку транзакцій з товарами.
        """
        params = {
            "date_from": date_from,
            "date_to": date_to,
            "type": "waiters",
            "include_products": 1,  # <--- ВМИКАЄМО ТОВАРИ
            "status": 2  # Беремо тільки закриті чеки (опціонально)
        }
        
        # Використовуємо transactions.getTransactions замість dash, 
        # бо він дає кращу деталізацію товарів
        result = self.make_request("transactions.getTransactions", params)
        
        if result is None:
            return []
            
        if isinstance(result, list):
            return result
        elif isinstance(result, dict):
            # Обробка різних форматів відповіді Poster
            return list(result.values()) if not result.get('data') else result['data']
            
        return []
