import sqlite3
import streamlit as st
import os
import io
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from googleapiclient.errors import HttpError

SCOPES = ['https://www.googleapis.com/auth/drive.file']

# Authenticate using the service account from Streamlit secrets
def authenticate_gdrive():
    # Load the service account credentials from secrets
    creds = service_account.Credentials.from_service_account_info(
        st.secrets["gdrive"],  # Assuming your key is stored here
        scopes=SCOPES
    )
    return creds

# Download SQLite database from Google Drive
def download_db_from_drive(service, file_id, file_name=None):
    request = service.files().get_media(fileId=file_id)
    fh = io.FileIO(file_name, 'wb')
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        status, done = downloader.next_chunk()

# Upload or update the SQLite database file to Google Drive
def upload_db_to_drive(service, db_name, file_id=None):
    try:
        file_metadata = {
            'name': db_name,
            'mimeType': 'application/x-sqlite3'  # SQLite file MIME type
        }

        media = MediaFileUpload(db_name, mimetype='application/x-sqlite3')

        if file_id:  # If updating an existing file
            try:
                service.files().get(fileId=file_id).execute()
                file = service.files().update(
                    fileId=file_id,
                    body=file_metadata,
                    media_body=media
                ).execute()
                st.success(f"Database updated successfully! File ID: {file.get('id')}")
            except HttpError as e:
                if e.resp.status == 404:
                    st.error("File not found. Please check the file ID.")
                    return None
                else:
                    st.error(f"An error occurred: {e}")
                    return None
        else:  # If creating a new file
            file = service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()
            st.success(f"Database uploaded successfully! File ID: {file.get('id')}")

        return file.get('id')  # Return the file ID

    except HttpError as error:
        st.error(f"An error occurred: {error}")
        return None

# Connect to SQLite database
def connect_db(db_name):
    return sqlite3.connect(db_name)

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


def get_file_location(service, file_id):
    try:
        # Get the file metadata
        file_metadata = service.files().get(fileId=file_id, fields='id, name, parents').execute()
        
        # Get the file name and parent IDs
        file_name = file_metadata.get('name')
        parent_ids = file_metadata.get('parents', [])

        # Retrieve parent folder names
        parent_names = []
        for parent_id in parent_ids:
            parent_metadata = service.files().get(fileId=parent_id, fields='id, name').execute()
            parent_names.append(parent_metadata.get('name'))

        return file_name, parent_names

    except Exception as e:
        st.error(f"An error occurred: {e}")
        return None


def main():
    st.title("SQLite Database with Google Drive Storage")

    # Build the Drive service
    creds = authenticate_gdrive()
    service = build('drive', 'v3', credentials=creds)

    # File ID of the SQLite database in Google Drive
    file_id = '1PZa4c0s53yYCIuJMxDzFAcY3AN7O4sa1'  # Replace with your actual file ID
    db_name = 'tracking_expenses_app2.db'

    # Download the SQLite file from Google Drive
    if not os.path.exists(db_name):
        download_db_from_drive(service, file_id, db_name)

    # Connect to the SQLite database
    conn = connect_db(db_name)
    c = conn.cursor()

    # Create table if it doesn't exist
    c.execute('''
        CREATE TABLE IF NOT EXISTS purchases_x (
            purchase_id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_name TEXT NOT NULL,
            category TEXT NOT NULL,
            purchase_amount REAL NOT NULL
        )
    ''')

    # Streamlit UI for adding data
    item_name = st.text_input("Item Name")
    category = st.text_input("Category")
    purchase_amount = st.number_input("Purchase Amount", min_value=0.0, step=0.01)

    if st.button("List Files"):
        list_files(service)

    if st.button("Add Purchase"):
        c.execute('''
            INSERT INTO purchases_x (item_name, category, purchase_amount)
            VALUES (?, ?, ?)
        ''', (item_name, category, purchase_amount))
        conn.commit()
        st.success("Purchase added!")

    if st.button("View Purchases"):
        c.execute('SELECT * FROM purchases_x')
        data = c.fetchall()
        st.write(data)

    if st.button("Upload DB to Google Drive"):
        file_id = file_id  # Replace with the actual file ID
        db_name = db_name  # The name of your database file
        result_id = upload_db_to_drive(service, db_name, file_id)

        if result_id is None:
            st.error("Failed to upload or update the database.")

    
    if st.button("Get File Location"):
    locations = get_file_location(service, file_id)  # Ensure you pass the right number of arguments
    if locations:
        for location in locations:
            st.write(f"- {location}")
    else:
        st.error("File not found or couldn't retrieve location.")

    # Close the connection
    conn.close()

if __name__ == "__main__":
    main()
