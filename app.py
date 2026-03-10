import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import hashlib
import matplotlib.pyplot as plt

# Page config
st.set_page_config(page_title="Expense Tracker", page_icon="💸", layout="centered")

# Custom CSS for bac\kground image
page_bg_img = """
<style>
[data-testid="stAppViewContainer"] {
    background-image: url("Expense Tracker\PythonProject\image.jpg");
    background-size: cover;
    background-position: center;
    background-repeat: no-repeat;
}
[data-testid="stSidebar"] {
    background-color: rgba(255, 255, 255, 0.8);
}
[data-testid="stHeader"] {
    background: rgba(255, 255, 255, 0.0);
}
</style>
"""
st.markdown(page_bg_img, unsafe_allow_html=True)

# Database setup
conn = sqlite3.connect('expenses.db', check_same_thread=False)
cursor = conn.cursor()

# Create users table
cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password_hash TEXT
    )
''')

# Create expenses table
cursor.execute('''
    CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        date TEXT,
        category TEXT,
        amount REAL,
        note TEXT,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
''')
conn.commit()

# Password hash function
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Create new user
def create_user(username, password):
    try:
        cursor.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (username, hash_password(password)))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False

# Login user
def login_user(username, password):
    cursor.execute("SELECT id, password_hash FROM users WHERE username = ?", (username,))
    result = cursor.fetchone()
    if result and hash_password(password) == result[1]:
        return result[0]
    return None

# Add expense
def add_expense(user_id, date, category, amount, note):
    cursor.execute("INSERT INTO expenses (user_id, date, category, amount, note) VALUES (?, ?, ?, ?, ?)",
                   (user_id, date, category, amount, note))
    conn.commit()

# Get expenses
def get_expenses(user_id, query="SELECT * FROM expenses WHERE user_id = ?", params=()):
    df = pd.read_sql_query(query, conn, params=(user_id, *params))
    return df

# Delete expense
def delete_expense(user_id, expense_id):
    cursor.execute("DELETE FROM expenses WHERE id = ? AND user_id = ?", (expense_id, user_id))
    conn.commit()

# Session state initialization
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_id = None
    st.session_state.username = None

# Logout function
def logout():
    st.session_state.logged_in = False
    st.session_state.user_id = None
    st.session_state.username = None

# Login and signup page
def login_page():
    st.title("🔐 Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        user_id = login_user(username, password)
        if user_id:
            st.session_state.logged_in = True
            st.session_state.user_id = user_id
            st.session_state.username = username
            st.success(f"Welcome back, {username}!")
        else:
            st.error("Invalid username or password")

    st.write("---")
    st.write("Don't have an account? Signup below.")
    new_user = st.text_input("New username")
    new_pass = st.text_input("New password", type="password")

    if st.button("Signup"):
        if new_user and new_pass:
            success = create_user(new_user, new_pass)
            if success:
                st.success("User created! Please login above.")
            else:
                st.error("Username already exists.")
        else:
            st.warning("Please enter a username and password to signup.")

# Notifications based on monthly spending
def check_notifications(df):
    if df.empty:
        return
    current_month = datetime.today().strftime("%Y-%m")
    monthly_total = df[df['date'].str.startswith(current_month)]['amount'].sum()
    if monthly_total > 10000:
        st.error(f"⚠️ You have exceeded your budget of ₹10,000 for {current_month}!")
    elif monthly_total > 8000:
        st.warning(f"⚠️ You are nearing your budget limit for {current_month}.")

# Main application
def main_app():
    st.title(f"💸 Expense Tracker - Welcome {st.session_state.username}")
    menu = ["Add Expense", "View Expenses", "Delete Expense", "Summary", "Logout"]
    choice = st.sidebar.selectbox("📑 Navigation", menu)
    user_id = st.session_state.user_id

    if choice == "Add Expense":
        st.subheader("➕ Add a New Expense")
        col1, col2 = st.columns(2)
        with col1:
            date = st.date_input("Date", datetime.today())
            category = st.selectbox("Category", ["Food", "Travel", "Shopping", "Bills", "Other"])
        with col2:
            amount = st.number_input("Amount ₹", min_value=0.01, format="%.2f")
            note = st.text_input("Note")

        if st.button("Add Expense"):
            if note.strip() == "":
                st.warning("⚠️ Please enter a note for this expense.")
            else:
                add_expense(user_id, date.strftime("%Y-%m-%d"), category, amount, note)
                st.success("✅ Expense added successfully!")
                st.balloons()

    elif choice == "View Expenses":
        st.subheader("📋 All Expenses")
        with st.expander("📆 Filter by Date"):
            start_date = st.date_input("Start Date", datetime(2024, 1, 1))
            end_date = st.date_input("End Date", datetime.today())
        start_date_str = start_date.strftime("%Y-%m-%d")
        end_date_str = end_date.strftime("%Y-%m-%d")

        df = get_expenses(user_id, "SELECT * FROM expenses WHERE user_id = ? AND date BETWEEN ? AND ?", (start_date_str, end_date_str))
        if df.empty:
            st.warning("No expenses found for selected dates.")
        else:
            st.dataframe(df)
            total = df['amount'].sum()
            st.info(f"💰 Total Expenses: ₹{total:.2f}")
            if st.button("📥 Download as CSV"):
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button("Download CSV", data=csv, file_name='expenses.csv', mime='text/csv')
            check_notifications(df)

    elif choice == "Delete Expense":
        st.subheader("🗑️ Delete an Expense")
        df = get_expenses(user_id)
        if df.empty:
            st.warning("No expenses to delete.")
        else:
            st.dataframe(df)
            delete_id = st.selectbox("Select Expense ID to delete", df['id'])
            confirm = st.checkbox("Confirm delete")
            if st.button("Delete Expense"):
                if confirm:
                    delete_expense(user_id, delete_id)
                    st.success(f"✅ Expense ID {delete_id} deleted!")
                else:
                    st.warning("⚠️ Please confirm deletion before proceeding.")

    elif choice == "Summary":
        st.subheader("📊 Expense Summary")
        df = get_expenses(user_id)
        if df.empty:
            st.warning("No data to summarize.")
        else:
            total = df['amount'].sum()
            st.write(f"💰 **Total Expenses:** ₹{total:.2f}")
            category_summary = df.groupby('category')['amount'].sum().reset_index()
            st.write("### 📈 Expenses by Category")
            st.dataframe(category_summary)
            st.bar_chart(category_summary.set_index('category'))

            fig, ax = plt.subplots()
            ax.pie(category_summary['amount'], labels=category_summary['category'], autopct='%1.1f%%', startangle=140)
            ax.axis('equal')
            st.pyplot(fig)

    elif choice == "Logout":
        logout()
        st.rerun()

# App flow control
if not st.session_state.logged_in:
    login_page()
else:
    main_app()
