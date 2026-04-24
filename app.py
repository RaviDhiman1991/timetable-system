import streamlit as st
import pandas as pd
import os
import re
from datetime import datetime
import io

# --- Google Drive ---
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google.oauth2 import service_account
from googleapiclient.errors import HttpError

st.set_page_config(layout="centered")

FILE = "issues.csv"
USER_FILE = "users.csv"
FOLDER_ID = "1uTIAmpkvbhdyipJSUBtQlTJWV2GygKmE"

# ---------- VALIDATION ----------
def validate_course_code(code):
    code = code.strip().upper()
    pattern = r'^(2[2-9]|30)[A-Z]{2}[PTRNH]-\d{3}$'
    return re.match(pattern, code) is not None

# ---------- GOOGLE DRIVE ----------
def get_drive_service():
    try:
        creds = service_account.Credentials.from_service_account_info(
            st.secrets["gdrive"],
            scopes=["https://www.googleapis.com/auth/drive"]
        )
    except:
        creds = service_account.Credentials.from_service_account_file(
            "credentials.json",
            scopes=["https://www.googleapis.com/auth/drive"]
        )
    return build("drive", "v3", credentials=creds)

def upload_to_drive(uploaded_file):
    service = get_drive_service()

    file_metadata = {
        "name": uploaded_file.name.replace(" ", "_"),
        "parents": [FOLDER_ID]
    }

    uploaded_file.seek(0)
    media = MediaIoBaseUpload(io.BytesIO(uploaded_file.read()), mimetype=uploaded_file.type)

    try:
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields="id",
            supportsAllDrives=True
        ).execute()

        file_id = file.get("id")

        service.permissions().create(
            fileId=file_id,
            body={"role": "reader", "type": "anyone"},
            supportsAllDrives=True
        ).execute()

        return f"https://drive.google.com/uc?id={file_id}"

    except HttpError as e:
        st.error(f"❌ Drive Error: {e}")
        return ""

# ---------- EXCEL ----------
def convert_df_to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='All Issues')
        df[df["Status"]=="Pending"].to_excel(writer, index=False, sheet_name='Pending')
        df[df["Status"]=="Resolved"].to_excel(writer, index=False, sheet_name='Resolved')
    return output.getvalue()

# ---------- USERS ----------
def load_users():
    if os.path.exists(USER_FILE):
        df = pd.read_csv(USER_FILE, dtype=str).fillna("")
        df.columns = df.columns.str.strip().str.lower()
        return df
    return pd.DataFrame(columns=["username","password","role"])

# ---------- SESSION ----------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.role = ""

if "submitted" not in st.session_state:
    st.session_state.submitted = False

# ---------- LOGIN ----------
def login():
    st.title("🎨 Fine Arts Timetable Management System")

    username = st.text_input("Username").strip().lower()
    password = st.text_input("Password", type="password").strip()

    if st.button("Login"):
        users_df = load_users()
        user = users_df[
            (users_df["username"] == username) &
            (users_df["password"] == password)
        ]

        if not user.empty:
            st.session_state.logged_in = True
            st.session_state.username = username
            st.session_state.role = user.iloc[0]["role"]
            st.rerun()
        else:
            st.error("❌ Invalid credentials")

def logout():
    st.session_state.logged_in = False
    st.rerun()

# ---------- MAIN ----------
if not st.session_state.logged_in:
    login()

else:
    st.sidebar.title("Menu")
    st.sidebar.write(f"👤 {st.session_state.username} ({st.session_state.role})")

    if st.sidebar.button("Logout"):
        logout()

    menu = ["Submit Issue", "Dashboard"]
    choice = st.sidebar.selectbox("Navigation", menu)

    # ================= SUBMIT =================
    if choice == "Submit Issue":

        st.title("📅 Submit Timetable Issue")

        with st.form("issue_form", clear_on_submit=False):

            name = st.session_state.username.capitalize()

            col1, col2 = st.columns(2)

            with col1:
                course_code = st.text_input("Course Code")
                semester = st.selectbox("Semester", ["1","2","3","4","5","6","7","8"])
                issue_type = st.selectbox("Issue Type", ["Time Clash","Room Issue","Overload","Other"])

            with col2:
                course_name = st.text_input("Course Name")
                day = st.selectbox("Day", ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday"])
                urgency = st.selectbox("Urgency", ["Low","Medium","High"])

            time_slot = st.selectbox("Time Slot", [
                "9:30 – 10:20","10:20 – 11:10","11:10 – 12:00",
                "12:00 – 12:50","12:50 – 1:50 (Break)",
                "1:50 – 2:40","2:40 – 3:30","3:30 – 4:20"
            ])

            description = st.text_area("Description")
            uploaded_file = st.file_uploader("Upload Screenshot", type=["png","jpg","jpeg"])

            submit = st.form_submit_button("Submit")

        # ✅ Message placeholder (AFTER form)
        message_placeholder = st.empty()

        # Show success message near button
        if st.session_state.submitted:
            message_placeholder.success("✅ Issue submitted successfully!")
            st.session_state.submitted = False

        if submit:

            if not validate_course_code(course_code):
                message_placeholder.error("❌ Invalid Course Code format")
            
            else:
                file_link = ""

                if uploaded_file is not None:
                    file_link = upload_to_drive(uploaded_file)

                new_data = pd.DataFrame([[
                    name, course_code.upper(), course_name, semester, day, time_slot,
                    issue_type, description, urgency,
                    file_link, "Pending","",datetime.now()
                ]],
                columns=[
                    "Name","Course Code","Course Name","Semester","Day","Time Slot",
                    "Issue Type","Description","Urgency",
                    "Image","Status","Remarks","Submission Date"
                ])

                if os.path.exists(FILE):
                    new_data.to_csv(FILE, mode="a", header=False, index=False)
                else:
                    new_data.to_csv(FILE, index=False)

                st.session_state.submitted = True
                st.rerun()

    # ================= DASHBOARD =================
    elif choice == "Dashboard":

        st.title("📊 Dashboard")

        if os.path.exists(FILE):
            df = pd.read_csv(FILE, dtype=str).fillna("")

            excel_data = convert_df_to_excel(df)
            st.download_button(
                "📥 Download Excel Report",
                data=excel_data,
                file_name="timetable_issues.xlsx"
            )

            for i in df.index:
                with st.container(border=True):
                    st.markdown(f"### {df.loc[i,'Course Code']} ({df.loc[i,'Course Name']})")
                    st.write(df.loc[i,"Description"])

                    if df.loc[i,"Image"]:
                        st.image(df.loc[i,"Image"], use_column_width=True)
