import streamlit as st
from utils import (download_db_from_drive, fetch_data_from_db, check_existing_file, upload_db_to_drive,
                   share_file_with_user, db_cursor, establish_connections, store_session_state, delete_purchase_record,
                   clear_input, register_date_adapter_converter)
from config import DB_NAME, FILE_ID, access_list
from pandas import DataFrame
from authlib.integrations.requests_client import OAuth2Session
import datetime

st.set_page_config(page_title="Construction Expenses Tracking App", page_icon="📚", layout="wide")
st.title("📚 Construction Expenses Tracking App")
st.sidebar.success("Navigate yourself")

# Define client ID and client secret from Google OAuth
client_id = st.secrets['gdrive']['client_id_key']
client_secret = st.secrets['gdrive']['client_secret_key']
redirect_uri = st.secrets['gdrive']['redirect_uri']  # Ensure this matches the Google Cloud Console settings

# Google OAuth 2.0 configuration
authorize_url = "https://accounts.google.com/o/oauth2/auth"
token_url = "https://oauth2.googleapis.com/token"
userinfo_url = "https://www.googleapis.com/oauth2/v3/userinfo"
scope = "openid email profile"

# Initialize OAuth session
oauth = OAuth2Session(client_id, client_secret, redirect_uri=redirect_uri, scope=scope)


def main():
    #st.header("Expenses Data Entry")
    service = establish_connections()
    conn, cursor = db_cursor()

    # Check for existing token in session state
    if "token" not in st.session_state:
        # Redirect to Google OAuth login
        authorization_url, state = oauth.create_authorization_url(authorize_url)
        st.link_button("Login with Google", url=authorization_url)
    else:
        # Load the token
        token = st.session_state["token"]
        oauth.token = token

        # Fetch user info from Google
        response = oauth.get(userinfo_url)

        if response.status_code == 200:
            userinfo = response.json()
            user_email = userinfo.get("email")
            user_name = userinfo.get("name")
            if user_email in access_list:
                # st.success(f"Logged in as: {user_email}")
                st.success(f"Hi {user_name}!!, 📚 Welcome to Expense Tracker App")
                # st.write(f"{userinfo}")
                # Continue to the main functionality
                show_main_functionality(service, conn, cursor)
            else:
                st.error("You don't have access 😥!!")
        else:
            st.error("Failed to recognize the user 😥!!")
            # st.error("Failed to fetch user information. Status Code: " + str(response.status_code))

    # Handle the authorization code if present
    code = st.query_params.get("code")
    if code and "token" not in st.session_state:
        try:
            # Fetch the token using the code
            token = oauth.fetch_token(token_url, code=code, grant_type="authorization_code")
            st.session_state["token"] = token
            st.success("Authentication completed successfully.")
            st.rerun()  # Refresh the app to show user info
        except Exception as e:
            st.error(f"An error occurred during authentication")


def show_main_functionality(service,conn,cursor):
    # Your existing functionality for handling database operations, file uploads, etc.
    #st.info("Entering main functionality...")

    if st.button("Refresh"):
        existing_file_id = check_existing_file(service, DB_NAME)
        if existing_file_id:
            download_db_from_drive(service, FILE_ID, DB_NAME)
            print(f"Updated existing file with ID: {FILE_ID}")
        else:
            result_id = upload_db_to_drive(service, DB_NAME, None)
            share_file_with_user(service, result_id, access_list)
            st.write(f"Created new file with ID: {result_id}")

    # Fetch projects and display them
    project_query = "SELECT project_id || ' - ' || project_name AS project FROM projects;"
    project = fetch_data_from_db(project_query)
    if project:
        project_with_blank = ["Project Names with Project ID"] + project
        project_selection = st.selectbox("Select the project:", project_with_blank)
        project_id_selected = project_selection.split(' - ')[0]

        if project_selection != "Project Names with Project ID":
            st.success(f"You have selected the project: {project_selection}")
            st.session_state['project_id_selected'] = project_id_selected
            project_id = st.session_state['project_id_selected']

            store_session_state("project_id_selected", project_id_selected)
            store_session_state("project_selection", project_selection)

            categories = fetch_data_from_db('SELECT category FROM category')
            payment_options = fetch_data_from_db('SELECT mode_of_payment FROM mode_of_payment')
            stage_options = fetch_data_from_db('SELECT stage FROM stages')
            existing_vendors = fetch_data_from_db('SELECT distinct vendor FROM purchases')
            vendor_option = st.selectbox("Vendor Type:", ["Select Existing Vendor", "Enter New Vendor"], on_change=lambda: clear_input('vendor'))
            mode_of_payment = st.selectbox("Select mode of payment:", payment_options, on_change=lambda: clear_input('paid_amount'),
                                           key="mode_of_payment", placeholder="Select Mode of Payment")

            # Form for user data input
            with st.form("purchases_data_entry"):
                st.header("🧾 Purchase Data Entry Form")
                # Create two columns
                col1, col2, col3 = st.columns(3)

                # First column: Item name input
                with col1:
                    item_name = st.text_input("Enter the item name:")

                # Second column: Item quantity input
                with col2:
                    unit = st.selectbox("Select unit:", ["Nos", "MT", "Liters", "Units", "Kg", "Others"])

                # Second column: Selectbox for units or item type
                with col3:
                    item_qty = st.number_input("Enter the item quantity:", min_value=0.0, max_value=1000000.0, step=0.01)

                stage = st.selectbox("Select stage:", stage_options)
                category = st.selectbox("Select category:", categories)

                # Conditional input based on vendor option
                if vendor_option == "Select Existing Vendor":
                    vendor = st.selectbox("Select vendor:", existing_vendors, key="vendor")
                elif vendor_option == "Enter New Vendor":
                    vendor = st.text_input("Enter the new vendor name:", key="vendor")
                register_date_adapter_converter()
                date = st.date_input("Select the date:",datetime.date.today(), min_value=datetime.date(2000, 1, 1), max_value=datetime.date.today())
                purchase_amount = st.number_input("Enter the purchase amount:", min_value=-10000, max_value=1000000, value = 0)

                # Conditionally display the paid amount input
                if mode_of_payment != "No Payment":
                    paid_amount = st.number_input("Enter the paid amount:", min_value=0, max_value=1000000, value=0, key="paid_amount")
                    paid_by = st.text_input("Who paid the amount?:")
                else:
                    paid_amount = 0  # Default to 0 if 'No Payment' is selected
                    paid_by = None

                notes = st.text_input("Add notes if necessary:")
                submitted = st.form_submit_button("Submit")

            if submitted:
                # Check if any fields are empty
                required_fields = [item_name, vendor, mode_of_payment, category, stage, date]
                if all(required_fields) and (purchase_amount > -10000 or paid_amount > 0):
                    cursor.execute('''INSERT INTO purchases 
                                    (project_id, item_name, item_qty, unit, vendor, stage, category, date, purchase_amount, mode_of_payment, paid_amount, paid_by, notes)
                                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                                   (project_id, item_name, item_qty, unit, vendor, stage, category, date, purchase_amount, mode_of_payment, paid_amount, paid_by, notes))
                    conn.commit()
                    st.success("Data submitted successfully!")
                else:
                    st.error("All fields are mandatory! Please fill in all fields.")

            if st.button("View Purchases"):
                cursor.execute(f'''
                    SELECT 
                        purchase_id as 'Purchase ID', 
                        item_name as 'Item Name',
                        unit as 'Unit', 
                        item_qty as 'Item Qty',                        
                        CASE 
                        WHEN unit = 'Nos' or unit = 'Others' OR unit is null
                        THEN COALESCE(CAST(item_qty AS INTEGER),'') || ' ' || COALESCE(unit,'')
                        ELSE COALESCE(printf('%.2f', item_qty), '') || ' ' || COALESCE(unit,'')
                        END AS 'Item Quantity',
                        vendor as Vendor, 
                        stage as Stage, 
                        category as Category,
                        date as Date, 
                        purchase_amount as 'Purchase Amount', 
                        mode_of_payment as 'Mode of Payment',
                        paid_amount as 'Paid Amount',
                        paid_by as 'Paid By',
                        notes as Notes
                        FROM purchases
                        WHERE project_id = {project_id}    
                ''')
                data = cursor.fetchall()
                if data:
                    results_df = DataFrame(data, columns=[desc[0] for desc in cursor.description])
                    st.dataframe(results_df)
                else:
                    st.write("No data found for the selected criteria.")

            delete_purchase_record()

            if st.button("Save"):
                existing_file_id = check_existing_file(service, DB_NAME)
                if existing_file_id:
                    result_id = upload_db_to_drive(service, DB_NAME, FILE_ID)
                    print(f"Updated existing file with ID: {result_id}")
                else:
                    result_id = upload_db_to_drive(service, DB_NAME, None)  # Create new file
                    st.write(f"Created new file with ID: {result_id}")

                # Share the file with your email
                if result_id:
                    share_file_with_user(service, result_id, "awrfikghost@gmail.com")


if __name__ == "__main__":
    main()
