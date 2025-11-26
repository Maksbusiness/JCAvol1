import requests
import streamlit as st
import time
from typing import Dict, List, Any, Optional
import json

class PosterClient:
    """
    Клієнт для взаємодії з Poster POS API (v3).
    Реалізовано автоматичну пагінацію для отримання всіх записів.
    """
    
    BASE_URL = "https://joinposter.com/api"

    def __init__(self):
        try:
            self.token = st.secrets["poster"]["token"]
        except KeyError:
            st.error("❌ Критична помилка: Токен Poster API не знайдено у secrets.toml")
            st.stop()

    def _make_raw_request(self, endpoint: str, params: Dict[str, Any]) -> Optional[Any]:
        """
        Виконує один HTTP запит. Повертає "сиру" відповідь (JSON об'єкт).
        """
        params["token"] = self.token
        url = f"{self.BASE_URL}/{endpoint}"
        
        try:
            # Таймаут 30 сек, бо запити можуть бути важкими
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            # Перевірка на помилки API
            if "error" in data:
                error_msg = data['error'].get('message', 'Unknown error')
                st.warning(f"⚠️ API Warning [{endpoint}]: {error_msg}")
                return None
            
            return data.get("response", data)

        except Exception as e:
            st.error(f"❌ Connection Error [{endpoint}]: {e}")
            return None

    def _get_all_items(self, endpoint: str, params: Dict[str, Any] = None) -> List[Dict]:
        """
        Універсальний метод з пагінацією.
        Викачує ВСІ дані, перебираючи offset.
        """
        if params is None:
            params = {}
        
        all_items = []
        limit = 100
        offset = 0
        
        # Налаштовуємо параметри пагінації
        params['limit'] = limit
        
        # Створюємо плейсхолдер для статусу завантаження (щоб не спамити логами)
        status_text = st.empty()
        
        while True:
            params['offset'] = offset
            
            # Виконуємо запит
            response_data = self._make_raw_request(endpoint, params)
            
            # Якщо запит впав (None), повертаємо те, що встигли скачати
            if response_data is None:
                break
            
            # Нормалізація даних (Poster може повертати список або словник з ключем data)
            batch = []
            if isinstance(response_data, list):
                batch = response_data
            elif isinstance(response_data, dict):
                # Часто буває format: {'data': [...], 'meta': ...}
                if 'data' in response_data:
                    batch = response_data['data']
                else:
                    # Якщо це словник без 'data', можливо це просто values (напр. settings)
                    # Але для списків зазвичай це помилка структури, або кінець даних
                    batch = list(response_data.values()) if response_data else []

            # Якщо порція пуста — виходимо
            if not batch:
                break
                
            all_items.extend(batch)
            status_text.text(f"📥 Завантажено {len(all_items)} записів з {endpoint}...")
            
            # Логіка виходу з циклу:
            # Якщо отримали менше ліміту, значить це остання сторінка
            if len(batch) < limit:
                break
            
            # Зсуваємо курсор
            offset += limit
            
            # Пауза, щоб не отримати 429 Too Many Requests
            time.sleep(0.1)

        status_text.empty() # Очищаємо текст статусу після завершення
        return all_items

    def get_transactions(self, date_from: str, date_to: str) -> List[Dict]:
        """
        Отримання всіх чеків за період.
        """
        params = {
            "date_from": date_from,
            "date_to": date_to,
            "include_products": 1, # Обов'язково для товарної аналітики
            "status": 2            # Тільки закриті (успішні) чеки
        }
        return self._get_all_items("transactions.getTransactions", params)

    def get_products(self) -> List[Dict]:
        """
        Отримання всього меню (товари + техкарти).
        """
        return self._get_all_items("menu.getProducts")

    def get_ingredients(self) -> List[Dict]:
        """
        Отримання всіх інгредієнтів.
        """
        return self._get_all_items("menu.getIngredients")

    def get_suppliers(self) -> List[Dict]:
        """
        Отримання всіх постачальників.
        """
        return self._get_all_items("access.getSuppliers")

    def get_supplies(self, date_from: str, date_to: str) -> List[Dict]:
        """
        Отримання всіх поставок за період.
        """
        params = {
            "date_from": date_from,
            "date_to": date_to
        }
        return self._get_all_items("storage.getSupplies", params)
