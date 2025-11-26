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
        # Отримуємо токен з секретів Streamlit
        # Структура secrets.toml має бути:
        # [poster]
        # token = "ваш_токен"
        try:
            self.token = st.secrets["poster"]["token"]
        except KeyError:
            st.error("❌ Помилка: Токен Poster API не знайдено у secrets.toml")
            st.stop()

    def make_request(self, endpoint: str, params: Dict[str, Any] = None) -> Optional[Dict | List]:
        """
        Універсальний метод для запитів до API.
        
        :param endpoint: Назва методу API (наприклад, 'dash.getTransactions')
        :param params: Словник параметрів запиту
        :return: Відповідь API (JSON) або None у разі помилки
        """
        if params is None:
            params = {}
        
        # Додаємо токен до кожного запиту
        params["token"] = self.token
        
        url = f"{self.BASE_URL}/{endpoint}"
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status() # Перевірка на HTTP помилки (404, 500)
            
            data = response.json()
            
            # Перевірка на логічні помилки Poster API
            if "error" in data:
                st.error(f"⚠️ Помилка API Poster ({data['error'].get('code')}): {data['error'].get('message')}")
                return None
                
            # Poster зазвичай повертає дані у ключі 'response'
            return data.get("response", data)

        except requests.exceptions.RequestException as e:
            st.error(f"❌ Мережева помилка при запиті до {endpoint}: {e}")
            return None
        except json.JSONDecodeError:
            st.error(f"❌ Помилка обробки відповіді від {endpoint}: Невалідний JSON")
            return None

    def get_transactions(self, date_from: str, date_to: str) -> List[Dict]:
        """
        Отримання списку транзакцій за період.
        
        :param date_from: Дата початку (YYYY-MM-DD)
        :param date_to: Дата кінця (YYYY-MM-DD)
        :return: Список словників з даними чеків
        """
        params = {
            "date_from": date_from,
            "date_to": date_to,
            "type": "waiters", # Можливо знадобиться змінити залежно від типу чеків
            "include_products": 0 # Поки не вантажимо товари для швидкості
        }
        
        # Викликаємо endpoint
        # Увага: якщо dash.getTransactions не поверне очікувані дані,
        # спробуємо transactions.getTransactions
        result = self.make_request("dash.getTransactions", params)
        
        if result is None:
            return []
            
        # Poster іноді повертає порожній список або об'єкт. 
        # Переконаємось, що повертаємо список.
        if isinstance(result, list):
            return result
        elif isinstance(result, dict):
            # Іноді буває пагінація або обгортка
            return list(result.values()) if not result.get('data') else result['data']
            
        return []
