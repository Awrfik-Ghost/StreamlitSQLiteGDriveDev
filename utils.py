import sqlite3
import io
import streamlit as st
import os
from google.oauth2 import service_account
# from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from config import SCOPES
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload


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


# Display all purchases data for each
def to_title_case(column_values):
    return [str(value).title() for value in column_values]


# Display all purchases data for each
def to_lower_case(column_values):
    return str(column_values).lower()


# Function to download the SQLite DB file from Google Drive
def download_db_from_drive(service, file_id, file_name):
    """Download a file from Google Drive."""
    if os.path.exists(file_name):
        st.info(f"Database '{file_name}' already exists. Skipping download.")
        return  # Skip download if the file already exists

    request = service.files().get_media(fileId=file_id)
    fh = io.FileIO(file_name, 'wb')
    downloader = MediaIoBaseDownload(fh, request)

    done = False
    while not done:
        status, done = downloader.next_chunk()
        st.write(f"Download progress: {int(status.progress() * 100)}%")
    st.success(f"Database downloaded successfully: {file_name}")
    st.write(f"Database path: {os.path.abspath(file_name)}")
