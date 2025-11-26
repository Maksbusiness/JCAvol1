import gspread
import json
import pandas as pd
import streamlit as st
from oauth2client.service_account import ServiceAccountCredentials
from gspread_dataframe import set_with_dataframe

class GoogleSheetHandler:
    """
    Оптимізований хендлер для Google Sheets.
    Стратегія: Overwrite (Очищення -> Запис).
    Економить квоту Google Drive, не створюючи бекапів.
    """
    
    SCOPE = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]

    def __init__(self):
        try:
            creds_json = st.secrets["google"]["credentials_json"]
            creds_dict = json.loads(creds_json)
            
            # Виправлення формату приватного ключа
            if "private_key" in creds_dict:
                creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
            
            self.creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, self.SCOPE)
            self.client = gspread.authorize(self.creds)
            
            # Відкриваємо або створюємо таблицю
            self.spreadsheet_name = "Poster Data Lake" 
            try:
                self.spreadsheet = self.client.open(self.spreadsheet_name)
            except gspread.SpreadsheetNotFound:
                self.spreadsheet = self.client.create(self.spreadsheet_name)
                self.spreadsheet.share(creds_dict['client_email'], perm_type='user', role='writer')
                st.info(f"Створено нову таблицю: {self.spreadsheet_name}")

        except Exception as e:
            st.error(f"Google Auth Error: {e}")
            st.stop()

    def save_data(self, df: pd.DataFrame, sheet_name: str) -> bool:
        """
        Перезаписує дані в аркуші.
        Якщо аркуша немає - створює. Якщо є - очищає і пише нові.
        """
        if df.empty:
            return False

        try:
            # 1. Спроба відкрити існуючий аркуш
            try:
                worksheet = self.spreadsheet.worksheet(sheet_name)
                worksheet.clear() # Повне очищення
            except gspread.WorksheetNotFound:
                # 2. Створення нового, якщо не знайдено
                # Розраховуємо розмір, щоб не витрачати ліміт комірок даремно
                rows = len(df) + 20
                cols = len(df.columns)
                worksheet = self.spreadsheet.add_worksheet(title=sheet_name, rows=rows, cols=cols)

            # 3. Запис даних
            # astype(str) критично важливий для серіалізації вкладених списків/словників з Poster
            set_with_dataframe(worksheet, df.astype(str))
            return True

        except Exception as e:
            st.error(f"Помилка запису в '{sheet_name}': {e}")
            return False

    def save_all_data(self, client, date_from: str, date_to: str):
        """
        Оркестратор: витягує дані з PosterClient і пише в Sheets.
        """
        log = st.status("🚀 Початок синхронізації...", expanded=True)

        def process_entity(name, fetch_func, *args):
            log.write(f"📥 Завантаження: {name}...")
            try:
                data = fetch_func(*args)
                
                # Конвертація в DataFrame
                if isinstance(data, list):
                    df = pd.DataFrame(data)
                elif isinstance(data, pd.DataFrame):
                    df = data
                else:
                    df = pd.DataFrame()

                if not df.empty:
                    success = self.save_data(df, name)
                    if success:
                        log.write(f"✅ {name}: збережено {len(df)} записів.")
                    else:
                        log.write(f"❌ {name}: помилка запису.")
                else:
                    log.write(f"⚠️ {name}: немає даних.")
            except Exception as e:
                log.write(f"❌ Помилка при обробці {name}: {e}")

        # --- ЗАПУСК ПО ЧЕРЗІ ---
        
        # 1. Транзакції
        process_entity("Transactions", client.get_transactions, date_from, date_to)

        # 2. Довідники
        process_entity("Products", client.get_menu_products)
        process_entity("Ingredients", client.get_menu_ingredients)
        process_entity("Suppliers", client.get_suppliers)
        process_entity("Employees", client.get_employees)
        process_entity("WasteReasons", client.get_waste_reasons)
        process_entity("Leftovers", client.get_leftovers)

        # 3. Документи (за період)
        process_entity("Supplies", client.get_supplies, date_from, date_to)
        process_entity("Wastes", client.get_wastes, date_from, date_to)
        process_entity("WriteOffs", client.get_ingredient_write_offs, date_from, date_to)
        process_entity("Inventories", client.get_inventories, date_from, date_to)

        log.update(label="🎉 Синхронізацію завершено!", state="complete", expanded=False)