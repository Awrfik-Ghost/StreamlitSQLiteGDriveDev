import sqlite3
import streamlit as st
import os
import io
from pandas import DataFrame
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


def upload_db_to_drive(service, db_name, file_id):
    """Uploads or updates the SQLite database file to Google Drive.

    Args:
        service: Authenticated Google Drive service instance.
        db_name: Name of the database file to upload.
        file_id: Optional; ID of the file to update. If None, a new file will be created.

    Returns:
        The ID of the uploaded or updated file.
    """
    try:
        # Define the metadata for the file (with correct MIME type for SQLite)
        file_metadata = {
            'name': db_name,
            'mimeType': 'application/x-sqlite3'  # SQLite file MIME type
        }

        # Create media file upload
        media = MediaFileUpload(db_name, mimetype='application/x-sqlite3')

        if file_id:  # If updating an existing file
            try:
                # Attempt to retrieve the file to ensure it exists
                service.files().get(fileId=file_id).execute()
                st.write("Updating the existing file...")

                # Proceed to update the file
                file = service.files().update(
                    fileId=file_id,
                    body=file_metadata,
                    media_body=media
                ).execute()

                st.success(f"Database updated successfully! File ID: {file.get('id')}")
                st.write(f"File metadata after update: {file}")

            except HttpError as e:
                if e.resp.status == 404:
                    st.error("File not found. Please check the file ID.")
                    return None
                else:
                    st.error(f"An error occurred: {e}")
                    return None
        else:  # If creating a new file
            # Create the file on Google Drive
            st.write("Creating a new file...")
            file = service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()
            st.success(f"Database uploaded successfully! File ID: {file.get('id')}")
            st.write(f"File metadata after creation: {file}{db_name}")

        return file.get('id')  # Return the file ID

    except HttpError as error:
        st.error(f"An error occurred during upload: {error}")
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


def list_files_with_location(service):
    """Lists the files and their parent folders in Google Drive."""
    try:
        results = service.files().list(pageSize=10, fields="nextPageToken, files(id, name, parents)").execute()
        items = results.get('files', [])
        if not items:
            st.write("No files found.")
        else:
            st.write("Files and locations:")
            for item in items:
                st.write(f"File: {item['name']} (ID: {item['id']})")

                # Get folder name if available
                parent_ids = item.get('parents', [])
                if parent_ids:
                    for parent_id in parent_ids:
                        parent_metadata = service.files().get(fileId=parent_id, fields='id, name').execute()
                        st.write(f"  Located in folder: {parent_metadata.get('name')} (ID: {parent_metadata.get('id')})")
                else:
                    st.write("  Located in: My Drive")
    except HttpError as error:
        st.error(f"An error occurred while listing files: {error}")


def share_file_with_user(service, file_id, user_email):
    """Shares the uploaded file with a specified user."""
    try:
        # Permission settings: granting view access to your email
        permission = {
            'type': 'user',
            'role': 'writer',  # Can change to 'reader' for read-only
            'emailAddress': user_email
        }
        service.permissions().create(fileId=file_id, body=permission).execute()
        st.success(f"File shared successfully with {user_email}")
    except HttpError as error:
        st.error(f"An error occurred while sharing the file: {error}")


def check_existing_file(service, file_name):
    """Check if a file with the given name already exists in Google Drive."""
    try:
        results = service.files().list(q=f"name='{file_name}'", fields="files(id, name)").execute()
        items = results.get('files', [])
        if items:
            return items[0]['id']  # Return the ID of the first match
        return None
    except HttpError as error:
        st.error(f"An error occurred while checking for existing files: {error}")
        return None


def main():
    st.title("SQLite Database with Google Drive Storage")

    # Build the Drive service
    creds = authenticate_gdrive()
    service = build('drive', 'v3', credentials=creds)

    # File ID of the SQLite database in Google Drive
    file_id = None  # Replace with your actual file ID
    db_name = 'tracking_expenses_app2.db'

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
        if data:
            results_df = DataFrame(data, columns=[desc[0] for desc in c.description])
            st.dataframe(results_df)
        else:
            st.write("No data found for the selected criteria.")

    if st.button("Upload DB to Google Drive"):
        existing_file_id = check_existing_file(service, db_name)
        if existing_file_id:
            result_id = upload_db_to_drive(service, db_name, existing_file_id)
            st.write(f"Updated existing file with ID: {result_id}")
        else:
            result_id = upload_db_to_drive(service, db_name, None)  # Create new file
            st.write(f"Created new file with ID: {result_id}")

        # Share the file with your email
        if result_id:
            share_file_with_user(service, result_id, "awrfikghost@gmail.com")

    # Close the connection
    conn.close()


if __name__ == "__main__":
    main()
