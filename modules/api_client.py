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

        e
