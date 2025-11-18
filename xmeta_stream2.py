import streamlit as st
import pandas as pd
import psycopg2
from psycopg2 import sql

# Judul aplikasi
st.title("Pencarian dalam Data PostgreSQL Xmeta CLOB, Created by: Vito Muhammad -MIS")

# Define PostgreSQL connection parameters
db_user = "........"
db_password = "Mu@......"
db_host = "........"
db_port = "5432"
db_name = "......"

# Establish PostgreSQL connection
conn = psycopg2.connect(
    dbname=db_name,
    user=db_user,
    password=db_password,
    host=db_host,
    port=db_port
)

# Create a cursor object
cursor = conn.cursor()

# Query untuk mengambil data dari table ds_source
query = "SELECT * FROM ds_source_new"

# Read the data from PostgreSQL into a DataFrame
df = pd.read_sql(query, conn)

# Close the connection
cursor.close()
conn.close()

# Convert column names to lowercase
df.columns = df.columns.str.lower()

# Menampilkan beberapa data awal
st.write("Pratinjau Data:")
st.dataframe(df.head())

# Input kata kunci pencarian
keyword1 = st.text_input("Masukkan kata kunci pertama", "mismartprd")
keyword2 = st.text_input("Masukkan kata kunci kedua", "bmidwh")

# Pastikan kolom yang dicari ada di dalam data
if "orchestratecode_xmeta" in df.columns:
    # Filter data berdasarkan kata kunci
    filtered_df = df[
        df["orchestratecode_xmeta"].astype(str).str.contains(keyword1, na=False, case=False) &
        df["orchestratecode_xmeta"].astype(str).str.contains(keyword2, na=False, case=False)
    ]

    # Menampilkan jumlah hasil pencarian
    st.write(f"Jumlah hasil pencarian: {filtered_df.shape[0]}")

    # Menampilkan hasil pencarian
    st.write("Hasil Pencarian:")
    st.dataframe(filtered_df)

    # Menyediakan dua opsi tombol download
    col1, col2 = st.columns(2)

    # Menambahkan header deskriptif ke file CSV
    search_description = f"found table related to {keyword1} and {keyword2}"

    with col1:
        if not filtered_df.empty and "name_xmeta" in filtered_df.columns:
            name_xmeta_df = filtered_df[["name_xmeta"]]
            name_xmeta_df.to_csv("temp_name_xmeta.csv", index=False, encoding="utf-8-sig")

            # Membuka file untuk menambahkan header keterangan
            with open("temp_name_xmeta.csv", "r", encoding="utf-8-sig") as f:
                csv_content = f.read()
            
            csv_final = f"{search_description}\n{csv_content}".encode("utf-8-sig")

            st.download_button(
                "Download hanya NAME_XMETA",
                data=csv_final,
                file_name="name_xmeta.csv",
                mime="text/csv"
            )

    with col2:
        if not filtered_df.empty:
            filtered_df.to_csv("temp_hasil_pencarian.csv", index=False, encoding="utf-8-sig")

            # Membuka file untuk menambahkan header keterangan
            with open("temp_hasil_pencarian.csv", "r", encoding="utf-8-sig") as f:
                csv_content = f.read()
            
            csv_final = f"{search_description}\n{csv_content}".encode("utf-8-sig")

            st.download_button(
                "Download semua kolom",
                data=csv_final,
                file_name="hasil_pencarian.csv",
                mime="text/csv"
            )

else:
    st.error("Kolom 'ORCHESTRATECODE_XMETA' tidak ditemukan dalam data.")
