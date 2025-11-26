import gspread
import json
import pandas as pd
import streamlit as st
from oauth2client.service_account import ServiceAccountCredentials
from gspread_dataframe import set_with_dataframe, get_as_dataframe

class GoogleSheetHandler:
    """
    Клас для роботи з Google Sheets API (Read/Write).
    """
    
    SCOPE = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]

    def __init__(self):
        try:
            creds_json = st.secrets["google"]["credentials_json"]
            creds_dict = json.loads(creds_json)
            
            if "private_key" in creds_dict:
                creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
            
            self.creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, self.SCOPE)
            self.client = gspread.authorize(self.creds)
            self.service_email = creds_dict.get("client_email", "невідомий")

        except Exception as e:
            st.error(f"Auth Error: {e}")
            st.stop()

    def _get_or_create_worksheet(self, spreadsheet, title: str):
        """Допоміжний метод: отримує аркуш або створює його, якщо немає."""
        try:
            return spreadsheet.worksheet(title)
        except gspread.exceptions.WorksheetNotFound:
            return spreadsheet.add_worksheet(title=title, rows=1000, cols=20)

    def write_data(self, df: pd.DataFrame, sheet_name: str, tab_name: str = "Sheet1") -> bool:
        """
        Записує DataFrame у конкретну вкладку (tab_name).
        """
        try:
            spreadsheet = self.client.open(sheet_name)
            worksheet = self._get_or_create_worksheet(spreadsheet, tab_name)
            
            worksheet.clear()
            # Записуємо, перетворюючи все в стрічки для надійності
            set_with_dataframe(worksheet, df.astype(str))
            return True
        except Exception as e:
            st.error(f"Write Error ({tab_name}): {e}")
            return False

    def read_data(self, sheet_name: str, tab_name: str = "Sheet1") -> pd.DataFrame:
        """
        Читає дані з вкладки у DataFrame.
        """
        try:
            spreadsheet = self.client.open(sheet_name)
            worksheet = spreadsheet.worksheet(tab_name)
            
            # Читаємо всі дані
            data = worksheet.get_all_records()
            
            if not data:
                return pd.DataFrame()
                
            return pd.DataFrame(data)
        except gspread.exceptions.WorksheetNotFound:
            st.warning(f"Вкладку '{tab_name}' ще не створено.")
            return pd.DataFrame()
        except Exception as e:
            st.error(f"Read Error ({tab_name}): {e}")
            return pd.DataFrame()
