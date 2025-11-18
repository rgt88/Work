import streamlit as st
import pandas as pd
from PIL import Image
import psycopg2
from psycopg2.extras import RealDictCursor

# Load and display logo
image_path = r"C:/Users/....../Documents/Coding/Muamalat/MCRS/Logo Muamalat.png"
image = Image.open(image_path)
st.image(
    image, 
    caption="Welcome to MCRS Finder! Below are the details of the available columns.", 
    width=300
)

st.text("""
Columns: emp_id, report_code, report_name, report_description, report_extension, document_pathkey, report_owner_name, status,
        status_login, last_login_date, level_name, group_name, div_code, div_name, title
""")

# Database connection parameters
DB_CONFIG = {
    "host": ".....",
    "port": "5435",
    "database": "......",
    "user": "....",
    "password": ".....",
}

# SQL Query
query = """
SELECT 
    a.emp_id, 
    b.report_code, 
    b.report_name, 
    b.report_description, 
    b.report_extension, 
    b.document_pathkey, 
    b.report_owner_name,
    c.status as status_employee,
    a.status_login, 
    a.last_login_date, 
    a.level_name, 
    a.group_name, 
    b.div_code, 
    b.div_name, 
    a.title
FROM 
    v_user_info a
LEFT JOIN 
    v_report_item b 
ON 
    a.emp_id = b.report_owner_nik
join
	t_dim_user_employee_vito c
on
	b.report_owner_nik = CAST(c.nik as TEXT)
"""

# Fetch data
@st.cache_data(show_spinner=True)
def fetch_data():
    try:
        with psycopg2.connect(**DB_CONFIG) as conn:
            df = pd.read_sql_query(query, conn)
        return df
    except Exception as e:
        st.error(f"Error connecting to database: {e}")
        return pd.DataFrame()

# Load data
df = fetch_data()

if df.empty:
    st.error("No data available to display.")
else:
    # Display all data in expander
    with st.expander("Klik untuk melihat semua report"):
        st.dataframe(df)

    # Sidebar Filters
    st.sidebar.header("Cari Report")
    search_query = st.sidebar.text_input("Masukkan Report Name / Owner NIK / Owner Name / Report Description:", "")
    selected_report_group = st.sidebar.selectbox("Report Group Name", ["All"] + df["group_name"].dropna().unique().tolist())
    selected_report_extension = st.sidebar.selectbox("Report Extension", ["All"] + df["report_extension"].dropna().unique().tolist())
    selected_report_name = st.sidebar.text_input("Masukkan Report Name / Code untuk filter (Opsional):", "")

    # Dropdown filter for status_employee
    status_options = ["All", "ACTIVE", "INACTIVE"]
    selected_status = st.sidebar.selectbox("Status Employee", status_options)

    # Apply Filters
    df_filtered = df.copy()
    
    if search_query:
        df_filtered = df_filtered[
            df_filtered["report_name"].str.contains(search_query, case=False, na=False) |
            df_filtered["report_code"].str.contains(search_query, case=False, na=False) |
            df_filtered["report_owner_name"].str.contains(search_query, case=False, na=False) |
            df_filtered["report_description"].str.contains(search_query, case=False, na=False)
        ]

    if selected_report_group != "All":
        df_filtered = df_filtered[df_filtered["group_name"] == selected_report_group]

    if selected_report_extension != "All":
        df_filtered = df_filtered[df_filtered["report_extension"] == selected_report_extension]

    if selected_report_name:
        df_filtered = df_filtered[
            df_filtered["report_name"].str.contains(selected_report_name, case=False, na=False) |
            df_filtered["report_code"].str.contains(selected_report_name, case=False, na=False)
        ]

    if selected_status != "All":
        df_filtered = df_filtered[df_filtered["status_employee"] == selected_status]

    # Display filtered results
    st.write("### Hasil Pencarian")
    st.dataframe(df_filtered)
