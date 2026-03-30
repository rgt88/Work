import streamlit as st
import pandas as pd
import jaydebeapi
import pyarrow.parquet as pq
import pyarrow as pa
import os
from io import BytesIO
import time
import zipfile
import re

# Database connection details
dsn_database = "DWHDBPRD"
dsn_hostname = "10.55.53.70"
dsn_port = "5480"
dsn_uid = "etlprod"
dsn_pwd = "password"
jdbc_driver_name = "org.netezza.Driver"
jdbc_driver_loc = os.path.join('D:\\nzjdbc.jar')

# Function to connect to Netezza
def connect_to_netezza():
    conn = jaydebeapi.connect(
        jdbc_driver_name,
        f"jdbc:netezza://{dsn_hostname}:{dsn_port}/{dsn_database}", 
        {"user": dsn_uid, "password": dsn_pwd},
        jdbc_driver_loc
    )
    return conn

# Function to execute SQL queries
def execute_queries(queries):
    conn = connect_to_netezza()
    results = []
    try:
        for query in queries:
            df = pd.read_sql(query, conn)
            results.append((query, df))
    except Exception as e:
        st.error(f"Error executing query: {e}")
    finally:
        conn.close()
    return results

# Function to save DataFrame as Parquet file in buffer
def save_as_parquet_to_buffer(df):
    try:
        buffer = BytesIO()
        table = pa.Table.from_pandas(df)
        pq.write_table(table, buffer)
        return buffer
    except Exception as e:
        st.error(f"Error saving file: {e}")
        return None

# Function to create ZIP file from multiple Parquet files
def create_zip_file(parquet_buffers, file_names):
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for i, buffer in enumerate(parquet_buffers):
            zip_file.writestr(f"{file_names[i]}.parquet", buffer.getvalue())
    return zip_buffer

# Function to extract table names from queries
def extract_table_name(query):
    match = re.search(r'FROM\s+(\S+)', query, re.IGNORECASE)
    if match:
        return re.sub(r'[\\/*?:"<>|]', '', match.group(1))  # Sanitize table name
    return "unknown_table"

# Streamlit app
def main():
    st.title("Netezza to Parquet Converter - Multi-Query Execution")
    st.caption("Created by Vito Muhammad - MIS")

    query_input = st.text_area(
        "Enter SQL queries (separate with ;)",
        placeholder="SELECT * FROM BMIDWH.CIF_INDIVIDU_MASTER LIMIT 10; SELECT * FROM BMIDWH.ACCOUNT_MASTER LIMIT 10;",
        height=200
    )

    if st.button("Execute Queries"):
        queries = [q.strip() for q in query_input.split(';') if q.strip()]
        if not queries:
            st.error("Please enter at least one valid SQL query.")
            return

        parquet_buffers = []  # Buffer for all Parquet files
        file_names = []       # List for file names based on table names

        progress_bar = st.progress(0)
        progress_step = 100 / len(queries)
        current_progress = 0

        results = execute_queries(queries)
        
        for i, (query, df) in enumerate(results):
            if df is not None:
                st.write(f"Query {i + 1} Results:", df.head(5))
                table_name = extract_table_name(query)
                file_name = f"{table_name}_{i+1}"
                
                parquet_buffer = save_as_parquet_to_buffer(df)
                
                if parquet_buffer is not None:
                    parquet_buffers.append(parquet_buffer)
                    file_names.append(file_name)
                    
                    # Individual download button
                    st.download_button(
                        label=f"Download Parquet for Query {i + 1}",
                        data=parquet_buffer.getvalue(),
                        file_name=f"{file_name}.parquet",
                        mime="application/octet-stream"
                    )
            
            current_progress += progress_step
            progress_bar.progress(min(int(current_progress), 100))
            time.sleep(0.5)  # Simulate processing time

        progress_bar.progress(100)

        if parquet_buffers:
            zip_buffer = create_zip_file(parquet_buffers, file_names)
            st.download_button(
                label="Download All Parquet Files as ZIP",
                data=zip_buffer.getvalue(),
                file_name="all_queries_parquet.zip",
                mime="application/zip"
            )

if __name__ == "__main__":
    main()
