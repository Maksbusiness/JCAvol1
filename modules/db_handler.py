import gspread
import json
import streamlit as st
from oauth2client.service_account import ServiceAccountCredentials
from gspread_dataframe import set_with_dataframe

class GoogleSheetHandler:
    def __init__(self):
        # Отримуємо JSON-строку з секретів
        json_str = st.secrets["google"]["credentials_json"]
        
        # Визначаємо права доступу (scope)
        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive"
        ]
        
        # КРИТИЧНИЙ МОМЕНТ:
        # Використовуємо json.loads (з літерою 's' в кінці), 
        # щоб перетворити рядок тексту в словник Python
        creds_dict = json.loads(json_str)
        
        # Авторизуємось через словник
        self.creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        self.client = gspread.authorize(self.creds)

    def write_data(self, df, sheet_name):
        try:
            # Відкриваємо таблицю
            spreadsheet = self.client.open(sheet_name)
            # Беремо перший аркуш
            worksheet = spreadsheet.sheet1
            
            # Очищаємо старі дані
            worksheet.clear()
            
            # Записуємо нові (вимагає бібліотеку gspread-dataframe)
            set_with_dataframe(worksheet, df)
            return True, "Успішно збережено!"
            
        except gspread.exceptions.SpreadsheetNotFound:
            return False, f"Таблицю '{sheet_name}' не знайдено. Перевірте назву та чи дали ви доступ роботу."
        except Exception as e:
            return False, f"Помилка запису: {e}"
