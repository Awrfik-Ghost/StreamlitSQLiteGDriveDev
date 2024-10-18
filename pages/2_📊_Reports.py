import streamlit as st
from utils import to_title_case, fetch_data_from_db, to_lower_case, fetch_and_display_data, get_purchase_amounts, purchase_amounts


def main():
    st.set_page_config(
        page_title='Reports',
        page_icon='📊',
        layout="wide"
    )

    st.title("📊 Reports")

    try:
        if st.session_state['project_id_selected']:

            st.success(f"You're now able to access this project: {st.session_state['project_selection']}")

            st.header("Construction Expenses")
            purchase_amounts()

            # Requested column names
            column_names = ['category', 'vendor', 'stage', 'mode_of_payment']

            # Converting column names to title case
            column_names_title_case = to_title_case(column_names)

            # Dropdown to select the column in title case
            selected_column = st.selectbox("Select the column:", column_names_title_case)
            column_data = fetch_data_from_db(f'select distinct trim(lower({selected_column})) as columns from purchases')
            column_data_title_case = to_title_case(column_data)

            # Convert each value to title case
            item_name = st.selectbox("Select the item name:", column_data_title_case)
            selected_item = to_lower_case(item_name)

            if st.button("Show Purchase Data for selected column"):
                purchase_data = f"""
                    SELECT purchase_id as 'Purchase ID', 
                            item_name as 'Item Name', 
                            item_qty as 'Item Quantity', 
                            vendor as Vendor, 
                            stage as Stage, 
                            category as Category,
                            date as Date, 
                            purchase_amount as 'Purchase Amount', 
                            mode_of_payment as 'Mode of Payment',
                            paid_amount as 'Paid Amount',
                            notes as Notes,
                            pr.project_name as 'Project Name'
                    FROM purchases p
                    join projects pr on pr.project_id = p.project_id
                    WHERE trim(lower({selected_column})) = '{selected_item}'
                    and p.project_id = {st.session_state['project_id_selected']}
                """

                fetch_and_display_data(purchase_data)

            if st.button("Show Expenditure for each category"):
                expenditure_on_each_category = f"""
                    SELECT 
                        c.category AS Category, 
                        COALESCE(SUM(p.purchase_amount), "Not Yet Started") AS 'Purchase Amount'
                    FROM 
                        category c
                    LEFT JOIN 
                        purchases p ON p.category = c.category 
                        AND p.project_id = {st.session_state['project_id_selected']}
                    GROUP BY 
                        c.category;
                """

                fetch_and_display_data(expenditure_on_each_category)

            if st.button("Show Expenditure for each stage"):
                expenditure_on_each_stage = F"""
                    SELECT s.stage as Stage, COALESCE(SUM(p.purchase_amount),"Not Yet Started") as Purchase_Amount
                    FROM purchases p
                    RIGHT JOIN stages s ON s.stage=p.stage
                    WHERE p.project_id = {st.session_state['project_id_selected']}
                    GROUP BY s.stage;
                """

                fetch_and_display_data(expenditure_on_each_stage)

            if st.button('Report'):
                get_purchase_amounts()

    except Exception as e:
        st.warning(f"Please select the project in Home Page !!")


if __name__ == "__main__":
    main()
