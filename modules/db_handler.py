import gspread
import json
import pandas as pd
import streamlit as st
from oauth2client.service_account import ServiceAccountCredentials
from gspread_dataframe import set_with_dataframe

class GoogleSheetHandler:
    """
    Клас для роботи з Google Sheets.
    """
    
    SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

    def __init__(self):
        try:
            creds_json = st.secrets["google"]["credentials_json"]
            creds_dict = json.loads(creds_json)
            if "private_key" in creds_dict:
                creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
            
            self.creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, self.SCOPE)
            self.client = gspread.authorize(self.creds)

        except Exception as e:
            st.error(f"Google Auth Error: {e}")
            st.stop()

    def _write_generic(self, df: pd.DataFrame, sheet_name: str, tab_name: str) -> bool:
        """Внутрішній метод запису."""
        try:
            try:
                spreadsheet = self.client.open(sheet_name)
            except gspread.SpreadsheetNotFound:
                st.error(f"Таблицю '{sheet_name}' не знайдено.")
                return False

            try:
                worksheet = spreadsheet.worksheet(tab_name)
            except gspread.WorksheetNotFound:
                worksheet = spreadsheet.add_worksheet(title=tab_name, rows=1000, cols=20)

            worksheet.clear()
            # Конвертуємо все в string для надійності
            set_with_dataframe(worksheet, df.astype(str))
            return True
        except Exception as e:
            st.error(f"Error writing to {tab_name}: {e}")
            return False

    # --- Specialized Savers ---

    def save_transactions(self, df: pd.DataFrame, sheet_name: str) -> bool:
        return self._write_generic(df, sheet_name, "Transactions")

    def save_menu(self, df: pd.DataFrame, sheet_name: str) -> bool:
        return self._write_generic(df, sheet_name, "Menu")

    def save_categories(self, df: pd.DataFrame, sheet_name: str) -> bool:
        return self._write_generic(df, sheet_name, "Categories")
        
    def read_data(self, sheet_name: str, tab_name: str) -> pd.DataFrame:
        """Читання даних."""
        try:
            spreadsheet = self.client.open(sheet_name)
            worksheet = spreadsheet.worksheet(tab_name)
            data = worksheet.get_all_records()
            return pd.DataFrame(data)
        except Exception:
            return pd.DataFrame()