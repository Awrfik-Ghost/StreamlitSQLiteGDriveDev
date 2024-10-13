import streamlit as st
from utils import authenticate_gdrive, fetch_data_from_db, list_files
from googleapiclient.discovery import build

st.set_page_config(page_title="Tracking Expenses App", page_icon="🧾", layout="wide")

st.title("📚 Welcome to the Expense Tracker App")
st.sidebar.success("Select a page from the sidebar to get started.")


def main():
    st.header("Project Selection Page")

    creds = authenticate_gdrive()
    db_name = 'Tracking_Expenses_Schema.db'

    service = build('drive', 'v3', credentials=creds)



    if st.button("List Files"):
        list_files(service)


if __name__ == "__main__":
    main()
