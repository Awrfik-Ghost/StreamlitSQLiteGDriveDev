import streamlit as st
from utils import authenticate_gdrive, fetch_data_from_db, list_files
from googleapiclient.discovery import build

st.set_page_config(page_title="Tracking Expenses App", page_icon="🧾", layout="wide")

st.title("📚 Welcome to the Expense Tracker App")
st.sidebar.success("Select a page from the sidebar to get started.")


# At the start of your app, before connecting to the database

def download_db_from_drive(service, file_id, file_name):
    request = service.files().get_media(fileId=file_id)
    fh = io.FileIO(file_name, 'wb')
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        status, done = downloader.next_chunk()
    st.success(f"Database downloaded successfully: {file_name}")

# Authenticate and create Google Drive service
creds = authenticate_gdrive()
service = build('drive', 'v3', credentials=creds)

# Specify your database file name and file ID from Google Drive
db_name = 'Tracking_Expenses_Schema.db'
file_id = '1btD90XEnzZeCvQ42CTQkQORyWoTNhuNw'  # Replace with your actual file ID

# Download the database file from Google Drive
download_db_from_drive(service, file_id, db_name)

# Connect to the SQLite database
conn = connect_db(db_name)
cursor = conn.cursor()

# Check if the 'projects' table exists
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='projects';")
if cursor.fetchone() is None:
    st.error("The 'projects' table does not exist in the database.")
else:
    st.success("The 'projects' table exists.")

