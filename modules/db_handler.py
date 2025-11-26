import gspread
import json
import streamlit as st
from google.oauth2.service_account import Credentials # Нова бібліотека
from gspread_dataframe import set_with_dataframe

class GoogleSheetHandler:
    def __init__(self):
        # Отримуємо JSON-строку
        json_str = st.secrets["google"]["credentials_json"]
        
        # Парсимо рядок у словник
        creds_dict = json.loads(json_str)
        
        # Визначаємо права доступу
        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive"
        ]
        
        # Створюємо об'єкт авторизації (новий метод)
        self.creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        
        # Авторизуємо gspread
        self.client = gspread.authorize(self.creds)

    def write_data(self, df, sheet_name):
        try:
            # Відкриваємо таблицю
            spreadsheet = self.client.open(sheet_name)
            worksheet = spreadsheet.sheet1
            
            # Очищаємо і пишемо
            worksheet.clear()
            set_with_dataframe(worksheet, df)
            return True, "Успішно збережено!"
            
        except gspread.exceptions.SpreadsheetNotFound:
            return False, f"Таблицю '{sheet_name}' не знайдено. Перевірте назву."
        except Exception as e:
            return False, f"Помилка запису: {e}"
