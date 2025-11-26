import requests
import streamlit as st
import time
from typing import Dict, List, Any, Optional

class PosterClient:
    """
    Клієнт для Poster POS API (v3).
    Включає безпечну пагінацію (Offset-based pagination).
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
        Виконує одиничний запит до API.
        """
        # Створюємо копію, щоб не змінювати оригінальний словник зовні
        request_params = params.copy()
        request_params["token"] = self.token
        
        url = f"{self.BASE_URL}/{endpoint}"
        
        try:
            # Таймаут 30 сек
            response = requests.get(url, params=request_params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            if "error" in data:
                # Логуємо помилку, але повертаємо None, щоб цикл міг це обробити
                st.warning(f"⚠️ API Error [{endpoint}]: {data['error'].get('message')}")
                return None
            
            return data.get("response", data)

        except Exception as e:
            st.error(f"❌ Connection Error [{endpoint}]: {e}")
            return None

    def _get_all_items(self, endpoint: str, base_params: Dict[str, Any] = None) -> List[Dict]:
        """
        Універсальний метод завантаження всіх даних (Pagination Loop).
        """
        if base_params is None:
            base_params = {}

        all_items = []
        limit = 100
        offset = 0
        iteration = 0
        MAX_ITERATIONS = 500  # Safety Break: Максимум 50,000 записів (500 * 100)

        # Копіюємо параметри, щоб не змінювати вхідний об'єкт
        params = base_params.copy()
        params['limit'] = limit

        # Створюємо пустий елемент для відображення прогресу в реальному часі
        progress_text = st.empty()

        while True:
            # Оновлюємо offset
            params['offset'] = offset
            
            # Робимо запит
            response_data = self._make_raw_request(endpoint, params)
            
            # Якщо помилка запиту — перериваємо, але повертаємо те, що вже є
            if response_data is None:
                break

            # Нормалізація відповіді (Poster може повернути list або dict)
            batch = []
            if isinstance(response_data, list):
                batch = response_data
            elif isinstance(response_data, dict):
                # Часто буває {'data': [...], 'meta': ...}
                if 'data' in response_data:
                    batch = response_data['data']
                else:
                    # Рідкісний випадок, коли повертається dict як список
                    batch = list(response_data.values()) if response_data else []

            # Якщо батч порожній — даних більше немає
            if not batch:
                break

            # Додаємо до загального списку
            all_items.extend(batch)
            
            # Оновлюємо статус (опціонально)
            iteration += 1
            if iteration % 2 == 0: # Оновлюємо текст кожні 2 запити, щоб не миготіло
                progress_text.caption(f"⏳ Завантажено {len(all_items)} записів з {endpoint}...")

            # --- УМОВИ ВИХОДУ ---
            
            # 1. Якщо отримали менше, ніж ліміт -> це остання сторінка
            if len(batch) < limit:
                break
            
            # 2. Safety Break: Захист від нескінченного циклу
            if iteration >= MAX_ITERATIONS:
                st.warning(f"⚠️ Досягнуто ліміту безпеки ({len(all_items)} записів). Синхронізацію зупинено примусово.")
                break

            # Зсуваємо курсор для наступного запиту
            offset += limit
            
            # Коротка пауза для ввічливості до API
            time.sleep(0.1)

        progress_text.empty() # Прибираємо напис
        return all_items

    # --- ПУБЛІЧНІ МЕТОДИ ---

    def get_transactions(self, date_from: str, date_to: str) -> List[Dict]:
        """Чеки з товарами."""
        params = {
            "date_from": date_from,
            "date_to": date_to,
            "include_products": 1,
            "status": 2  # Тільки успішні
        }
        return self._get_all_items("transactions.getTransactions", params)

    def get_products(self) -> List[Dict]:
        """Меню та техкарти."""
        return self._get_all_items("menu.getProducts")

    def get_ingredients(self) -> List[Dict]:
        """Інгредієнти."""
        return self._get_all_items("menu.getIngredients")

    def get_suppliers(self) -> List[Dict]:
        """Постачальники."""
        return self._get_all_items("access.getSuppliers")

    def get_supplies(self, date_from: str, date_to: str) -> List[Dict]:
        """Постачання."""
        params = {
            "date_from": date_from,
            "date_to": date_to
        }
        return self._get_all_items("storage.getSupplies", params)
