import streamlit as st
from utils import authenticate_gdrive, fetch_data_from_db, connect_db
from pandas import DataFrame
from config import DB_NAME


def main():
    st.title("Purchase Entry Page")

    creds = authenticate_gdrive()
    db_name = DB_NAME
    conn = connect_db(db_name)
    cursor = conn.cursor()

    if 'project_id_selected' in st.session_state:
        project_id = st.session_state['project_id_selected']

        categories = fetch_data_from_db(db_name, 'SELECT category FROM category')
        payment_options = fetch_data_from_db(db_name, 'SELECT mode_of_payment FROM mode_of_payment')
        stage_options = fetch_data_from_db(db_name, 'SELECT stage FROM stages')

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
            if not item_name or vendor == "" or purchase_amount <= 0 or mode_of_payment == "" or category == "":
                st.error("All fields are mandatory! Please fill in all fields.")
            else:
                cursor.execute('''
                    INSERT INTO purchases 
                    (project_id, item_name, item_qty, vendor, stage, category, date, purchase_amount, mode_of_payment, paid_amount, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (project_id, item_name, item_qty, vendor, stage, category, date, purchase_amount, mode_of_payment, paid_amount, notes))
                conn.commit()
            st.success("Data submitted successfully!")

        if st.button("View Purchases"):
            cursor.execute('SELECT * FROM purchases')
            data = cursor.fetchall()
            if data:
                results_df = DataFrame(data, columns=[desc[0] for desc in cursor.description])
                st.dataframe(results_df)
            else:
                st.write("No data found for the selected criteria.")


if __name__ == "__main__":
    main()
