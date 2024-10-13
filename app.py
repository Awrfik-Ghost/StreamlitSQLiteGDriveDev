import streamlit as st
from utils import authenticate_gdrive, fetch_data_from_db, list_files, connect_db, check_existing_file, upload_db_to_drive, share_file_with_user, download_db_from_drive
from config import DB_NAME
from pandas import DataFrame
from googleapiclient.discovery import build

st.set_page_config(page_title="Tracking Expenses App", page_icon="🧾", layout="wide")

st.title("📚 Welcome to the Expense Tracker App")
st.sidebar.success("Select a page from the sidebar to get started.")


def main():
    st.header("Project Selection Page")
    creds = authenticate_gdrive()
    conn = connect_db(DB_NAME)
    cursor = conn.cursor()
    service = build('drive', 'v3', credentials=creds)   

    project_query = "SELECT project_id || ' - ' || project_name AS project FROM projects;"
    project = fetch_data_from_db(DB_NAME, project_query)

    # Adding a blank option to the project selection
    project_with_blank = ["Project Names with Project ID"] + project

    project_selection = st.selectbox("Select the project:", project_with_blank)
    project_id_selected = project_selection.split(' - ')[0]

    if project_selection != "Project Names with Project ID":
        st.success(f"You have selected the project: {project_selection}")
        # Store the project ID in session state
        st.session_state['project_id_selected'] = project_id_selected
        project_id = st.session_state['project_id_selected']

        categories = fetch_data_from_db(DB_NAME, 'SELECT category FROM category')
        payment_options = fetch_data_from_db(DB_NAME, 'SELECT mode_of_payment FROM mode_of_payment')
        stage_options = fetch_data_from_db(DB_NAME, 'SELECT stage FROM stages')

        # Create a simple form for user data input
        with st.form("purchases_data_entry"):
            item_name = st.text_input("Enter the item name:")
            item_qty = st.number_input("Enter the item quantity:", min_value=0, max_value=1000000)
            stage = st.selectbox("Select stage:", stage_options)
            category = st.selectbox("Select category:", categories)
            vendor = st.text_input("Enter the vendor name:")
            date = st.date_input("Select the date:")
            purchase_amount = st.number_input("Enter the purchase amount:", min_value=0, max_value=1000000)
            mode_of_payment = st.selectbox("Select mode of payment:", payment_options)
            paid_amount = st.number_input("Enter the paid amount:", min_value=0, max_value=1000000)
            notes = st.text_input("Add notes if necessary:")
            submitted = st.form_submit_button("Submit")

        if submitted:
            # Check if any fields are empty
            required_fields = [item_name, vendor, mode_of_payment, category, stage, date]
            if all(required_fields) and purchase_amount >= 0:
                cursor.execute('''
                        INSERT INTO purchases 
                        (project_id, item_name, item_qty, vendor, stage, category, date, purchase_amount, mode_of_payment, paid_amount, notes)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (project_id, item_name, item_qty, vendor, stage, category, date, purchase_amount, mode_of_payment, paid_amount, notes))
                conn.commit()
                st.success("Data submitted successfully!")
            else:
                st.error("All fields are mandatory! Please fill in all fields.")

        if st.button("View Purchases"):
            cursor.execute(f'''
                SELECT 
                    purchase_id as Purchase_ID, 
                    item_name as Item_Name, 
                    item_qty as Item_Quantity, 
                    vendor as Vendor, 
                    stage as Stage, 
                    category as Category,
                    date as Date, 
                    purchase_amount as Purchase_Amount, 
                    mode_of_payment as Mode_of_Payment,
                    paid_amount as Paid_Amount,
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

        if st.button("Upload DB to Google Drive"):
            existing_file_id = check_existing_file(service, DB_NAME)
            if existing_file_id:
                result_id = upload_db_to_drive(service, DB_NAME, existing_file_id)
                st.write(f"Updated existing file with ID: {result_id}")
            else:
                result_id = upload_db_to_drive(service, DB_NAME, None)  # Create new file
                st.write(f"Created new file with ID: {result_id}")

            # Share the file with your email
            if result_id:
                share_file_with_user(service, result_id, "awrfikghost@gmail.com")

    if st.button("List Files"):
        list_files(service)

    # Close the connection at the end
    cursor.close()
    conn.close()


if __name__ == "__main__":
    main()
