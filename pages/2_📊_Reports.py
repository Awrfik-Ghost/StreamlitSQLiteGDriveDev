import streamlit as st
from utils import to_title_case, fetch_data_from_db, connect_db, to_lower_case
from config import DB_NAME
from pandas import DataFrame


def main():
    st.set_page_config(
        page_title='Reports',
        page_icon='📊',
        layout="wide"
    )

    st.title("📊 Reports")

    conn = connect_db(DB_NAME)
    cursor = conn.cursor()

    # Requested column names
    column_names = ['category', 'vendor', 'stage', 'mode_of_payment']

    # Converting column names to title case
    column_names_title_case = to_title_case(column_names)

    # Dropdown to select the column in title case
    selected_column = st.selectbox("Select the column:", column_names_title_case)
    selected_column_in_lower_case = to_lower_case(selected_column)
    column_data = fetch_data_from_db(DB_NAME, f'select distinct trim(upper({selected_column})) as columns from purchases')

    # Convert each value to title case
    column_data_title_case = to_title_case(column_data)
    selected_item = st.selectbox("Select the item name:", column_data_title_case)

    if st.button("Show Purchase Data for selected column"):
        purchase_data = f"""
            SELECT purchase_id as Purchase_ID, 
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
            WHERE {selected_column_in_lower_case} = '{selected_item}'
            and project_id = {st.session_state['project_id_selected']}
        """

        cursor.execute(purchase_data)
        rows = cursor.fetchall()

        # Convert rows to a pandas DataFrame for better display
        df = DataFrame(rows, columns=[desc[0] for desc in cursor.description])

        # Display the DataFrame in tabular format
        st.dataframe(df)  # You can also use st.table(df) if you prefer a static table


if __name__ == "__main__":
    main()
