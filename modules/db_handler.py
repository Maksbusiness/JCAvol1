import gspread
import json
import pandas as pd
import streamlit as st
from oauth2client.service_account import ServiceAccountCredentials
from gspread_dataframe import set_with_dataframe

class GoogleSheetHandler:
    """
    Клас для роботи з Google Sheets API.
    """
    
    SCOPE = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]

    def __init__(self):
        try:
            # Отримуємо JSON-рядок із секретів
            creds_json_str = st.secrets["google"]["credentials_json"]
            
            # Парсимо рядок у словник
            creds_dict = json.loads(creds_json_str)
            
            # --- ВИПРАВЛЕННЯ КЛЮЧА ---
            # Streamlit secrets іноді передають \n як літеральні символи, а не як перенос рядка.
            # Для коректного RSA-парсингу замінюємо їх назад.
            if "private_key" in creds_dict:
                creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
            
            # Авторизація
            self.creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, self.SCOPE)
            self.client = gspread.authorize(self.creds)
            
            # Зберігаємо email бота
            self.service_email = creds_dict.get("client_email", "невідомий")

        except KeyError:
            st.error("❌ Помилка: Секція [google] або credentials_json не знайдена у secrets.toml")
            st.stop()
        except json.JSONDecodeError:
            st.error("❌ Помилка: Невірний формат JSON у secrets.toml")
            st.stop()
        except Exception as e:
            st.error(f"❌ Помилка авторизації Google: {e}")
            st.stop()

    def write_data(self, df: pd.DataFrame, sheet_name: str) -> bool:
        """
        Записує DataFrame у Google Таблицю (перезаписує перший аркуш).
        
        :param df: Pandas DataFrame з даними
        :param sheet_name: Назва існуючої таблиці в Google Drive
        :return: True, якщо успішно
        """
        try:
            # Відкриваємо таблицю за назвою
            spreadsheet = self.client.open(sheet_name)
            
            # Обираємо перший аркуш
            worksheet = spreadsheet.sheet1
            
            # Очищаємо старі дані
            worksheet.clear()
            
            # Записуємо нові дані разом із заголовками
            set_with_dataframe(worksheet, df)
            
            return True

        except gspread.exceptions.SpreadsheetNotFound:
            st.error(f"❌ Таблицю '{sheet_name}' не знайдено.")
            st.info(f"💡 Переконайтеся, що ви надали доступ редагування для: **{self.service_email}**")
            return False
        except Exception as e:
            st.error(f"❌ Помилка при запису в Google Sheets: {e}")
            return False
            
