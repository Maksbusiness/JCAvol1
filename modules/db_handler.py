import gspread
import json
import pandas as pd
import streamlit as st
from oauth2client.service_account import ServiceAccountCredentials
from gspread_dataframe import set_with_dataframe
import time

class GoogleSheetHandler:
    """
    Handles Google Sheets operations with 'Rolling Backup' logic.
    Ensures historical data is preserved by versioning sheets before writing new ones.
    """
    
    SCOPE = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]

    def __init__(self):
        try:
            creds_json = st.secrets["google"]["credentials_json"]
            creds_dict = json.loads(creds_json)
            # Fix newline escape issues common in TOML/Env vars
            if "private_key" in creds_dict:
                creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
            
            self.creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, self.SCOPE)
            self.client = gspread.authorize(self.creds)
            
            # Target Spreadsheet
            self.spreadsheet_name = "Poster Data Lake" 
            try:
                self.spreadsheet = self.client.open(self.spreadsheet_name)
            except gspread.SpreadsheetNotFound:
                # Create if doesn't exist
                self.spreadsheet = self.client.create(self.spreadsheet_name)
                self.spreadsheet.share(creds_dict['client_email'], perm_type='user', role='writer')
                st.info(f"Created new spreadsheet: {self.spreadsheet_name}")

        except Exception as e:
            st.error(f"Google Auth Error: {e}")
            st.stop()

    def _archive_sheet(self, sheet_name: str):
        """
        Renames an existing sheet to {sheet_name}_old_N to allow safe overwriting.
        """
        try:
            # Check if the main sheet exists
            worksheet = self.spreadsheet.worksheet(sheet_name)
        except gspread.WorksheetNotFound:
            # Nothing to archive
            return

        # Find a free name for the backup
        base_backup_name = f"{sheet_name}_old"
        new_name = base_backup_name
        counter = 1
        
        while True:
            try:
                self.spreadsheet.worksheet(new_name)
                # If we are here, it means the sheet exists, so we try next index
                new_name = f"{base_backup_name}_{counter}"
                counter += 1
            except gspread.WorksheetNotFound:
                # We found a free name!
                break
        
        # Rename the current sheet to the backup name
        try:
            worksheet.update_title(new_name)
            # st.toast(f"Archived '{sheet_name}' to '{new_name}'", icon="🗄️")
            time.sleep(1) # Safety pause for API propagation
        except Exception as e:
            st.warning(f"Failed to archive sheet {sheet_name}: {e}")

    def save_data(self, df: pd.DataFrame, sheet_name: str) -> bool:
        """
        Saves a DataFrame to a sheet with Rolling Backup.
        """
        if df.empty:
            return False

        try:
            # 1. Archive old data
            self._archive_sheet(sheet_name)
            
            # 2. Create new sheet
            try:
                worksheet = self.spreadsheet.add_worksheet(title=sheet_name, rows=len(df)+10, cols=len(df.columns)+5)
            except gspread.APIError:
                # In case race condition happened or it wasn't renamed properly, try getting it
                worksheet = self.spreadsheet.worksheet(sheet_name)
                worksheet.clear()

            # 3. Write new data (Convert to string to avoid JSON serialization errors)
            set_with_dataframe(worksheet, df.astype(str))
            return True
        
        except Exception as e:
            st.error(f"Error saving {sheet_name}: {e}")
            return False

    def save_all_data(self, client, date_from: str, date_to: str):
        """
        Orchestrator to fetch AND save all entities.
        """
        log = st.status("🚀 Starting Data Lake Extraction...", expanded=True)

        # Helper to process entities
        def process_entity(name, fetch_func, *args):
            log.write(f"📥 Fetching {name}...")
            data = fetch_func(*args)
            
            # Handle both list of dicts and pre-built DataFrames
            if isinstance(data, list):
                df = pd.DataFrame(data)
            else:
                df = data
                
            if not df.empty:
                self.save_data(df, name)
                log.write(f"✅ Saved {name} ({len(df)} rows)")
            else:
                log.write(f"⚠️ {name} is empty")

        # 1. Transactions
        process_entity("Transactions", client.get_transactions, date_from, date_to)

        # 2. Master Data
        process_entity("Products", client.get_menu_products)
        process_entity("Ingredients", client.get_menu_ingredients)
        process_entity("Suppliers", client.get_suppliers)
        process_entity("Employees", client.get_employees)
        process_entity("WasteReasons", client.get_waste_reasons)
        process_entity("Leftovers", client.get_leftovers)

        # 3. Documents (Date ranged)
        process_entity("Supplies", client.get_supplies, date_from, date_to)
        process_entity("Wastes", client.get_wastes, date_from, date_to)
        process_entity("WriteOffs", client.get_ingredient_write_offs, date_from, date_to)
        process_entity("Inventories", client.get_inventories, date_from, date_to)

        log.update(label="🎉 ETL Process Completed!", state="complete", expanded=False)