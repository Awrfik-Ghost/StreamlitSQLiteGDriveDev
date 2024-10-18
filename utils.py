import sqlite3
import io
import streamlit as st
import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from config import SCOPES
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from datetime import datetime
import pandas as pd
from config import DB_NAME


# ----------------------------------------------------------------------------------------------------
# Google Drive Connection
# ----------------------------------------------------------------------------------------------------

def authenticate_gdrive():
    creds = service_account.Credentials.from_service_account_info(
        st.secrets["gdrive"],
        scopes=SCOPES
    )
    return creds


def establish_connections():
    """
    Establishes a connection to Google Drive.

    Returns:
        tuple: A tuple containing the Google Drive service.
    """
    try:
        # Authenticate and create Google Drive service
        creds = authenticate_gdrive()  # Replace with your actual authentication function
        service = build('drive', 'v3', credentials=creds)
        return service

    except Exception as e:
        # Handle exceptions and provide feedback
        st.error(f"Error establishing connections: {e}")
        return None, None, None

# ----------------------------------------------------------------------------------------------------
# Database File Connection
# ----------------------------------------------------------------------------------------------------


def connect_db(db_name):
    return sqlite3.connect(db_name)


def db_cursor():
    # Try connecting to the database and executing the query
    connection = connect_db(DB_NAME)
    conn_cursor = connection.cursor()
    return connection, conn_cursor


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
                # st.write("Updating the existing file...")

                # Proceed to update the file
                file = service.files().update(
                    fileId=file_id,
                    body=file_metadata,
                    media_body=media
                ).execute()

                st.success("Data saved")
                # st.success("Database updated successfully!")
                # st.write(f"File ID: {file.get('id')}")
                # st.write(f"File metadata after update: {file}")

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


def download_db_from_drive(service, file_id, file_name):
    """Download a file from Google Drive."""
    request = service.files().get_media(fileId=file_id)
    fh = io.FileIO(file_name, 'wb')  # Create a file handle for writing
    downloader = MediaIoBaseDownload(fh, request)

    done = False
    while not done:
        status, done = downloader.next_chunk()  # Download in chunks
        # st.write(f"Download progress: {int(status.progress() * 100)}%")
    st.success(f"Data refreshed")

# ----------------------------------------------------------------------------------------------------
# Fetching data and displaying data from Database
# ----------------------------------------------------------------------------------------------------


def fetch_data_from_db(query):
    try:
        # Try connecting to the database and executing the query
        conn, cursor = db_cursor()
        row = cursor.execute(query)
        data = [row[0] for row in cursor.fetchall()]
        return data

    except sqlite3.DatabaseError:
        # Catch database-related errors
        st.info("Try refresh button above")
        return None

    except Exception as e:
        # Catch any other exceptions
        st.error("Try refresh button above")
        return None


def fetch_and_display_data(query):
    """
    Execute the given SQL query, fetch the results, and display them in a Streamlit app.
    Handles any SQL syntax errors and displays appropriate messages.

    Args:
        query (str): The SQL query to be executed.
    """
    try:
        # Execute the SQL query
        connection, cursor = db_cursor()
        cursor.execute(query)

        # Fetch all rows from the executed query
        results = cursor.fetchall()

        # Check if there are any results
        if results:
            # Convert rows to a pandas DataFrame for better display
            results_df = pd.DataFrame(results, columns=[desc[0] for desc in cursor.description])

            # Display the DataFrame in tabular format
            st.dataframe(results_df)  # You can also use st.table(df) for a static table
        else:
            # Inform the user if no data was found
            st.warning("No data found for the selected criteria.")

    except sqlite3.OperationalError as err:
        # Catch and handle specific MySQL errors
        st.warning("Please check if you've selected a valid project")

    except Exception as e:
        # Catch any other exceptions
        st.error(f"An unexpected error occurred: {e}")


# Function to store the selected value in session state
def store_session_state(key, value):
    if key == 'project_selection' and value == "Project Names with Project ID" or value == 'Null' or value == '':
        st.warning("Please select a valid project")
    else:
        st.session_state[key] = value


# ----------------------------------------------------------------------------------------------------
# Formatting data values
# ----------------------------------------------------------------------------------------------------

# Display all purchases data for each
def to_title_case(column_values):
    return [str(value).title() for value in column_values]


# Display all purchases data for each
def to_lower_case(column_values):
    return str(column_values).lower()


def format_currency(value):
    """Format value as Indian Rupees with commas."""
    if isinstance(value, (int, float)):
        return f"₹{value:,.2f}"
    return value


def format_percentage(value):
    """Format value as a percentage."""
    if isinstance(value, (int, float)):
        return f"{value:.2f}%"
    return value


# ----------------------------------------------------------------------------------------------------
# Local file and GDrive file modified time
# ----------------------------------------------------------------------------------------------------


def get_google_drive_modified_time(service, file_id):
    """Fetches the last modified time of a file in Google Drive."""
    file = service.files().get(fileId=file_id, fields='modifiedTime').execute()
    modified_time = file['modifiedTime']

    # Parse the modified time and convert it to a datetime object
    gdrive_modified_time = datetime.strptime(modified_time, '%Y-%m-%dT%H:%M:%S.%fZ')
    return gdrive_modified_time


def get_local_file_modified_time(file_path):
    """Fetches the last modified time of a local file."""
    if os.path.exists(file_path):
        last_modified_time = os.path.getmtime(file_path)
        return datetime.fromtimestamp(last_modified_time)  # Return as UTC
    else:
        return None  # If the file does not exist


def list_files_in_directory(directory):
    """Lists file names, their IDs (if applicable), and last modified datetime in the specified directory."""
    # Initialize a list to hold the file information
    file_info = []

    # Iterate through the files in the specified directory
    for filename in os.listdir(directory):
        file_path = os.path.join(directory, filename)

        # Check if it's a file
        if os.path.isfile(file_path):
            # Get the last modified time
            last_modified_time = os.path.getmtime(file_path)
            last_modified_datetime = datetime.fromtimestamp(last_modified_time)

            # Optionally, you can generate a unique file ID (e.g., using the file's path hash)
            file_id = hash(file_path)  # Simple hash as a unique identifier

            # Append the file info as a dictionary
            file_info.append({
                'file_name': filename,
                'file_id': file_id,
                'last_modified': last_modified_datetime.strftime('%Y-%m-%d %H:%M:%S')
            })

    return file_info


# ----------------------------------------------------------------------------------------------------
# Overall Expenses report
# ----------------------------------------------------------------------------------------------------

def get_purchase_amounts():
    # Establish the database connection
    conn, cursor = db_cursor()

    try:
        # Fetch distinct categories from the category table
        cursor.execute("SELECT category FROM category")
        categories = cursor.fetchall()

        # Check if categories exist
        if not categories:
            st.error("No categories found.")
            return

        # Start building the SQL query for each stage and category
        sql_query = "SELECT stage as Stage"

        # Add dynamic category columns to the SQL query
        for (category,) in categories:
            sql_query += f", COALESCE(SUM(CASE WHEN p.category = '{category}' THEN p.purchase_amount ELSE 0 END), 0) AS '{category}'"

        # Add grand total column for each stage
        sql_query += ", COALESCE(SUM(p.purchase_amount), 0) AS 'Purchase Amount'"

        # Complete the main SQL query
        sql_query += " FROM purchases p GROUP BY stage"

        # Start building the UNION query for totals
        union_query = " UNION ALL SELECT 'Total'"

        # Add totals for each category
        for (category,) in categories:
            union_query += f", COALESCE(SUM(CASE WHEN p.category = '{category}' THEN p.purchase_amount ELSE 0 END), 0)"

        # Add grand total
        union_query += ", COALESCE(SUM(p.purchase_amount), 0) FROM purchases p"

        # Add the row for percentage
        percentage_query = " UNION ALL SELECT 'Percentage'"

        # First, fetch the grand total to use for percentage calculation
        cursor.execute("SELECT COALESCE(SUM(purchase_amount), 0) FROM purchases")
        grand_total = cursor.fetchone()[0]

        # Check if grand total is fetched
        if grand_total is None:
            st.error("Failed to fetch grand total.")
            return

        # Calculate percentage for each category and grand total
        for (category,) in categories:
            percentage_query += f", CASE WHEN {grand_total} > 0 THEN ROUND(100 * SUM(CASE WHEN p.category = '{category}' THEN p.purchase_amount ELSE 0 END) / {grand_total}, 2) ELSE 0 END"

        # Grand total percentage (which will always be 100%)
        percentage_query += f", CASE WHEN {grand_total} > 0 THEN 100 ELSE 0 END FROM purchases p"

        # Combine the main query, totals, and percentage rows
        final_query = sql_query + union_query + percentage_query

        # Display the final query for debugging
        #st.write("Executing SQL Query:")
        #st.code(final_query)

        # Execute the dynamic SQL query
        cursor.execute(final_query)

        results = cursor.fetchall()

        # Get column names
        column_names = [desc[0] for desc in cursor.description]

        # Check if results were fetched
        if not results:
            st.error("No results found for the query.")
            return

        # Convert the results into a pandas DataFrame
        df = pd.DataFrame(results, columns=column_names)

        # Ensure numeric columns are correctly typed
        for col in df.columns[1:]:  # All columns except 'stage'
            df[col] = pd.to_numeric(df[col], errors='coerce')

        # Create a copy for formatted display
        formatted_df = df.copy()

        # Format all numeric columns (except 'stage') as currency
        for col in formatted_df.columns[1:-1]:  # All category columns (excluding Grand_Total)
            formatted_df[col] = formatted_df[col].apply(format_currency)

        grand_total_col = formatted_df.columns[-1]  # Get the last column name (Grand_Total)

        # Change the dtype of the 'Grand_Total' column to 'object' to avoid dtype incompatibility warning
        formatted_df[grand_total_col] = formatted_df[grand_total_col].astype('object')

        for i in range(len(formatted_df) - 1):  # Loop through all rows except the last one
            formatted_df.at[i, grand_total_col] = format_currency(df.at[i, grand_total_col])

        # Format the last row (percentage row) correctly
        last_row_index = formatted_df.index[-1]  # Index of the percentage row
        for col in formatted_df.columns[1:]:  # All columns except 'stage'
            if col != 'Stage':
                raw_value = df.at[last_row_index, col]  # Get the raw numeric value
                formatted_df.at[last_row_index, col] = format_percentage(raw_value)  # Format for display

        # Highlight Total and Percentage rows
        def highlight_rows(row):
            if row['Stage'] == 'Total':
                return ['background-color: #FF4B4B'] * len(row)
            elif row['Stage'] == 'Percentage':
                return ['background-color: #4B0082'] * len(row)
            else:
                return [''] * len(row)

        # Apply highlighting
        styled_df = formatted_df.style.apply(highlight_rows, axis=1)

        # Display the styled DataFrame in Streamlit
        st.dataframe(styled_df, use_container_width=True)

    except sqlite3.Error as err:
        st.error(f"Database Error: {err}")


def purchase_amounts():
    # Establish the database connection
    conn, cursor = db_cursor()

    try:
        # Fetch distinct categories from the category table
        cursor.execute("SELECT category FROM category")
        categories = cursor.fetchall()

        # Fetch distinct stages from the stages table
        cursor.execute("SELECT stage FROM stages")
        stages = cursor.fetchall()

        # Check if categories or stages exist
        if not categories or not stages:
            st.error("No categories or stages found.")
            return

        # Create a list of stages and categories
        stages_list = [stage[0] for stage in stages]
        categories_list = [category[0] for category in categories]

        # Build SQL query to get purchase amounts per category and stage
        sql_query = "SELECT p.category as Category"

        # Add dynamic stage columns
        for stage in stages_list:
            sql_query += f", COALESCE(SUM(CASE WHEN p.stage = '{stage}' THEN p.purchase_amount ELSE 0 END), 0) AS '{stage}'"

        # Add grand total for each category
        sql_query += ", COALESCE(SUM(p.purchase_amount), 0) AS 'Total'"

        # Complete the SQL query
        sql_query += " FROM purchases p GROUP BY p.category"

        # Execute the main SQL query
        cursor.execute(sql_query)
        results = cursor.fetchall()

        # Convert the results into a pandas DataFrame
        column_names = ['Category'] + stages_list + ['Total']
        df = pd.DataFrame(results, columns=column_names)

        # Ensure all categories are included, even if they have no purchases
        all_categories_df = pd.DataFrame(categories_list, columns=['Category'])
        df = pd.merge(all_categories_df, df, on='Category', how='left').fillna(0)

        # Calculate the grand total for each stage (column total)
        grand_total_row = df.sum(numeric_only=True).to_frame().T
        grand_total_row.insert(0, 'Category', 'Grand Total')

        # Append the grand total row to the DataFrame
        df = pd.concat([df, grand_total_row], ignore_index=True)

        # Calculate percentage for each category based on the grand total
        grand_total = grand_total_row['Total'].iloc[0]

        if grand_total > 0:
            df['Percentage'] = (df['Total'] / grand_total * 100).round(2)
        else:
            df['Percentage'] = 0

        # Calculate the percentage for each stage (column percentage)
        percentage_row = pd.DataFrame(columns=df.columns)
        percentage_row.loc[0] = ['Percentage'] + [
            (df[stage].iloc[:-1].sum() / grand_total * 100).round(2) if grand_total > 0 else 0
            for stage in stages_list
        ] + [100, '']

        # Append the percentage row to the DataFrame
        df = pd.concat([df, percentage_row], ignore_index=True)

        # Ensure numeric columns are correctly typed
        for col in df.columns[1:]:  # All columns except 'Category'
            df[col] = pd.to_numeric(df[col], errors='coerce')

        # Create a copy for formatted display
        formatted_df = df.copy()

        # Format all numeric columns (except 'Category') as currency
        for col in formatted_df.columns[1:-2]:  # All columns except 'Category', 'Total', and 'Percentage'
            formatted_df[col] = formatted_df[col].apply(format_currency)

        # Format Total column
        formatted_df['Total'] = formatted_df['Total'].apply(format_currency)

        # Format Percentage column (ensure no currency formatting)
        formatted_df['Percentage'] = formatted_df['Percentage'].apply(format_percentage)

        grand_total_col = formatted_df.columns[-2]
        # Change the dtype of the 'Grand_Total' column to 'object' to avoid dtype incompatibility warning
        formatted_df[grand_total_col] = formatted_df[grand_total_col].astype('object')

        for i in range(len(formatted_df) - 1):  # Loop through all rows except the last one
            formatted_df.at[i, grand_total_col] = format_currency(df.at[i, grand_total_col])

        # Format the last row (percentage row) correctly
        last_row_index = formatted_df.index[-1]  # Index of the percentage row
        for col in formatted_df.columns[1:]:  # All columns except 'stage'
            if col != 'Stage':
                raw_value = df.at[last_row_index, col]  # Get the raw numeric value
                formatted_df.at[last_row_index, col] = format_percentage(raw_value)


        def highlight_rows(row):
            styles = [''] * len(row)

            # Highlight entire row for Grand Total
            if row['Category'] == 'Grand Total':
                styles = ['background-color: #DAA520'] * len(row)  # Gold for Grand Total
            # Highlight entire row for Percentage
            elif row['Category'] == 'Percentage':
                styles = ['background-color: #FF0000'] * len(row)  # Indigo for Percentage

            return styles

        def highlight_last_column(s):
            # Create a default style
            styles = pd.DataFrame('', index=s.index, columns=s.columns)

            styles.iloc[:, -1] = ['background-color: #FF0000']
            styles.iloc[:, -2] = ['background-color: #DAA520']
            return styles

        # Function to highlight the last value of the second-to-last column
        def highlight_last_value(s):
            # Create a default style DataFrame with empty strings
            styles = pd.DataFrame('', index=s.index, columns=s.columns)

            # Get the index of the last row
            last_row_index = s.index[-1]

            # Apply color to the last value of the second-to-last column
            styles.iloc[last_row_index, -2] = 'background-color: #FF0000'  # Change color (Tomato)

            return styles

        # Apply row highlighting
        styled_df = formatted_df.style.apply(highlight_rows, axis=1)
        styled_df = styled_df.apply(highlight_last_column, axis=None)
        styled_df = styled_df.apply(highlight_last_value, axis=None)

        # Display the styled DataFrame in Streamlit
        st.dataframe(styled_df, use_container_width=True)

    except sqlite3.Error as err:
        st.error(f"Database Error: {err}")








# ----------------------------------------------------------------------------------------------------
# Delete Record Function
# ----------------------------------------------------------------------------------------------------

def delete_purchase_record():
    # Establish the database connection
    conn, cursor = db_cursor()

    # Fetch existing purchase IDs for deletion
    purchases_query = "SELECT purchase_id FROM purchases"
    purchases = fetch_data_from_db(purchases_query)

    # Convert list of tuples to a list of IDs for the select box
    purchases_with_blank = ["Select Purchase ID to delete"] + purchases  # Flatten the list of tuples

    with st.form("delete_form"):
        purchase_id = st.selectbox("Select Purchase ID", purchases_with_blank)
        submitted = st.form_submit_button("Delete")

        if submitted and purchase_id != "Select Purchase ID to delete":
            # Set the purchase ID in session state for confirmation
            st.session_state.purchase_id_to_delete = purchase_id
            st.session_state.confirm_delete = True

    # Confirmation message and action
    if st.session_state.get("confirm_delete", False):
        st.warning(f"Are you sure you want to delete Purchase ID: {st.session_state.purchase_id_to_delete}?", icon="⚠️")
        fetch_and_display_data(f'select * from purchases where purchase_id = {st.session_state.purchase_id_to_delete}')

        # Buttons for confirmation
        if st.button("Yes, delete"):
            try:
                cursor.execute("DELETE FROM purchases WHERE purchase_id = ?", (st.session_state.purchase_id_to_delete,))
                conn.commit()
                st.success(f"Purchase ID {st.session_state.purchase_id_to_delete} deleted successfully.")
                # Reset the session state
                st.session_state.confirm_delete = False
            except sqlite3.Error as e:
                st.error(f"An error occurred while deleting: {e}")

        if st.button("No, cancel"):
            st.info("Deletion canceled.")
            # Reset the session state
            st.session_state.confirm_delete = False

        # Reset the form if needed after the operation
        if not st.session_state.get("confirm_delete", False):
            st.rerun()
