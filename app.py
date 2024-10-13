import streamlit as st
import io
from googleapiclient.http import MediaIoBaseDownload
from utils import authenticate_gdrive, fetch_data_from_db, list_files, connect_db
from googleapiclient.discovery import build

st.set_page_config(page_title="Tracking Expenses App", page_icon="🧾", layout="wide")

st.title("📚 Welcome to the Expense Tracker App")
st.sidebar.success("Select a page from the sidebar to get started.")


def main():
    st.header("Project Selection Page")

    creds = authenticate_gdrive()
    db_name = 'Tracking_Expenses_Schema.db'

    service = build('drive', 'v3', credentials=creds)

    project_query = 'SELECT project_id || ' ' || project_name FROM projects'
    project = fetch_data_from_db(db_name, project_query)

    # Adding a blank option to the project selection
    project_with_blank = ["Project Names with Project ID"] + project

    project_selection = st.selectbox("Select the project:", project_with_blank)
    project_id_selected = project_selection.split(' - ')[0] if project_selection != "Project Names with Project ID" else None

    if project_selection != "Project Names with Project ID":
        st.success(f"You have selected the project: {project_selection}")

    # Store the project ID in session state
    st.session_state['project_id_selected'] = project_id_selected

    if st.button("List Files"):
        list_files(service)


if __name__ == "__main__":
    main()
