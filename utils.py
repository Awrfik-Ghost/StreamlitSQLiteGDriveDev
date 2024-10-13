import sqlite3
import streamlit as st
from google.oauth2 import service_account
# from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from config import SCOPES


def authenticate_gdrive():
    creds = service_account.Credentials.from_service_account_info(
        st.secrets["gdrive"],
        scopes=SCOPES
    )
    return creds


def connect_db(db_name):
    return sqlite3.connect(db_name)


def fetch_data_from_db(db_name, query):
    conn = connect_db(db_name)
    cursor = conn.cursor()
    cursor.execute(query)
    data = [row[0] for row in cursor.fetchall()]
    cursor.close()
    conn.close()
    return data


def list_files(service):
    """Lists the files in Google Drive to help verify file IDs."""
    try:
        results = service.files().list(pageSize=10, fields="nextPageToken, files(id, name)").execute()
        items = results.get('files', [])
        if not items:
            st.write("No files found.")
        else:
            st.write("Files:")
            for item in items:
                st.write(f"{item['name']} ({item['id']})")
    except HttpError as error:
        st.error(f"An error occurred while listing files: {error}")
