import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date

# Безпечний імпорт модулів
try:
    from modules.db_handler import DatabaseHandler
    from modules.api_client import PosterClient
except ImportError:
    st.error("❌ Критична помилка: Не знайдено модулі (modules/). Перевірте структуру файлів.")
    st.stop()

st.set_page_config(page_title="Poster SQL Analytics", page_icon="🐘", layout="wide")

# --- АВТОРИЗАЦІЯ ---
def check_auth():
    """Проста перевірка пароля."""
    if "user_role" not in st.session_state:
        st.session_state["user_role"] = None

    if st.session_state["user_role"]:
        return True

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.title("🔐 Вхід у систему")
        pwd = st.text_input("Введіть пароль", type="password")
        if pwd:
            # Перевірка паролів із secrets.toml
            if pwd == st.secrets["auth"]["admin_password"]:
                st.session_state["user_role"] = "Admin"
                st.rerun()
            elif pwd == st.secrets["auth"]["user_password"]:
                st.session_state["user_role"] = "User"
                st.rerun()
            else:
                st.error("Невірний пароль")
    return False

# --- БЕЗПЕЧНЕ ЗАВАНТАЖЕННЯ СТОРІНОК ---
def safe_load_page(page_function):
    try:
        page_function()
    except Exception as e:
        st.error(f"💥 Сталася помилка на сторінці: {e}")

# --- СТОРІНКА: ДАШБОРД (Тільки читання з БД) ---
def page_dashboard():
    st.title("📊 Аналітика (з бази Neon)")
    
    db = DatabaseHandler()
    
    # 1. Завантаження даних
    with st.spinner("Отримання даних з PostgreSQL..."):
        df_trans = db.load_data("transactions")
    
    if df_trans.empty:
        st.info("📭 У базі даних немає транзакцій. Перейдіть на вкладку 'Синхронізація', щоб завантажити дані.")
        return

    # 2. Обробка даних (KPI)
    try:
        # Конвертуємо типи, бо з SQL все може прийти як текст
        df_trans['date_close'] = pd.to_datetime(df_trans['date_close'])
        df_trans['payed_sum'] = pd.to_numeric(df_trans['payed_sum'], errors='coerce') / 100.0
        
        # Фільтр дат на дашборді
        min_date = df_trans['date_close'].min().date()
        max_date = df_trans['date_close'].max().date()
        
        col_d1, col_d2 = st.columns([1, 3])
        with col_d1:
            date_range = st.date_input("Період відображення", value=(min_date, max_date))
        
        if len(date_range) == 2:
            mask = (df_trans['date_close'].dt.date >= date_range[0]) & (df_trans['date_close'].dt.date <= date_range[1])
            df_filtered = df_trans.loc[mask]
        else:
            df_filtered = df_trans

        # Метрики
        total_rev = df_filtered['payed_sum'].sum()
        total_checks = df_filtered['transaction_id'].nunique()
        avg_check = total_rev / total_checks if total_checks > 0 else 0
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Виторг", f"{total_rev:,.0f} ₴")
        m2.metric("Кількість чеків", total_checks)
        m3.metric("Середній чек", f"{avg_check:.0f} ₴")
        
        # Графік
        st.subheader("Динаміка продажів")
        daily_sales = df_filtered.groupby(df_filtered['date_close'].dt.date)['payed_sum'].sum().reset_index()
        daily_sales.columns = ['Дата', 'Виторг']
        
        fig = px.bar(daily_sales, x='Дата', y='Виторг')
        st.plotly_chart(fig, use_container_width=True)
        
    except Exception as e:
        st.error(f"Помилка при обробці даних для графіків: {e}")

# --- СТОРІНКА: СИНХРОНІЗАЦІЯ (Запис у БД) ---
def page_sync():
    st.title("⚙️ Синхронізація даних")
    st.info("Цей модуль завантажує НОВІ дані з Poster API в базу Neon. Якщо запис вже є в базі — він буде проігнорований.")
    
    col1, col2 = st.columns(2)
    with col1:
        d_range = st.date_input("Період синхронізації", value=(date.today(), date.today()))
    
    with col2:
        st.write("") # Відступ
        st.write("") 
        sync_btn = st.button("🚀 Запустити оновлення", type="primary")

    if sync_btn and len(d_range) == 2:
        d_start, d_end = str(d_range[0]), str(d_range[1])
        
        api = PosterClient()
        db = DatabaseHandler()
        
        # Контейнер для логів
        status_log = st.status("⏳ Виконується синхронізація...", expanded=True)
        
        # СПИСОК ЗАВДАНЬ
        # Формат: (Назва таблиці, Функція API, Аргументи, УНІКАЛЬНА КОЛОНКА ID)
        steps = [
            ("transactions", api.get_transactions, [d_start, d_end], "transaction_id"),
            ("products", api.get_menu_products, [], "product_id"),
            ("ingredients", api.get_menu_ingredients, [], "ingredient_id"),
            ("employees", api.get_employees, [], "user_id"),
            ("supplies", api.get_supplies, [d_start, d_end], "supply_id"),
            ("wastes", api.get_wastes, [d_start, d_end], "waste_id"),
            ("inventories", api.get_inventories, [d_start, d_end], "inventory_id")
        ]
        
        total_steps = len(steps)
        progress_bar = st.progress(0)
        
        for i, (table_name, api_func, args, unique_id) in enumerate(steps):
            status_log.write(f"📥 Завантаження {table_name}...")
            
            # 1. Отримуємо дані з Poster
            df = api_func(*args)
            
            # 2. Зберігаємо в БД з перевіркою дублікатів
            if not df.empty:
                # Передаємо unique_col, щоб db_handler міг відфільтрувати існуючі записи
                success = db.save_data(df, table_name, unique_col=unique_id)
                
                if success:
                    status_log.write(f"✅ {table_name}: Оброблено {len(df)} записів.")
                else:
                    status_log.write(f"❌ {table_name}: Помилка запису в базу.")
            else:
                status_log.write(f"⚠️ {table_name}: API не повернуло даних.")
            
            progress_bar.progress((i + 1) / total_steps)
            
        status_log.update(label="🎉 Синхронізацію завершено!", state="complete", expanded=False)
        st.success("База даних успішно оновлена новими записами.")

# --- ГОЛОВНИЙ РОУТЕР ---
def main():
    if not check_auth():
        return

    # Сайдбар навігації
    st.sidebar.title("Навігація")
    role = st.session_state.get("user_role")
    
    pages = {"📊 Дашборд": page_dashboard}
    
    if role == "Admin":
        pages["⚙️ Синхронізація"] = page_sync
        
    selection = st.sidebar.radio("Перейти до", list(pages.keys()))
    
    st.sidebar.divider()
    if st.sidebar.button("Вийти"):
        st.session_state["user_role"] = None
        st.rerun()

    # Запуск вибраної сторінки
    safe_load_page(pages[selection])

if __name__ == "__main__":
    main()
