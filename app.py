import streamlit as st
import pandas as pd
import os
import re
from datetime import datetime

# --- Google Drive ---
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google.oauth2 import service_account
import io

FILE = "issues.csv"
USER_FILE = "users.csv"

# 👉 YOUR FOLDER ID
FOLDER_ID = "1zMNyfonzqne5cGml4y2aS9ZUrKXjglLP"

# ---------- VALIDATION ----------
def validate_course_code(code):
    pattern = r'^\d{2}FA[PTRNH]-\d{3}$'
    return re.match(pattern, code) is not None

# ---------- GOOGLE DRIVE ----------
def get_drive_service():
    try:
        # Streamlit Cloud (Secrets)
        creds = service_account.Credentials.from_service_account_info(
            st.secrets["gdrive"],
            scopes=["https://www.googleapis.com/auth/drive"]
        )
    except:
        # Local fallback
        creds = service_account.Credentials.from_service_account_file(
            "credentials.json",
            scopes=["https://www.googleapis.com/auth/drive"]
        )

    return build("drive", "v3", credentials=creds)


def upload_to_drive(uploaded_file):
    service = get_drive_service()

    file_metadata = {
        "name": uploaded_file.name,
        "parents": [FOLDER_ID]
    }

    file_bytes = uploaded_file.read()
    media = MediaIoBaseUpload(io.BytesIO(file_bytes), mimetype=uploaded_file.type)

    file = service.files().create(
        body=file_metadata,
        media_body=media,
        fields="id"
    ).execute()

    file_id = file.get("id")

    # Make file public
    service.permissions().create(
        fileId=file_id,
        body={"role": "reader", "type": "anyone"}
    ).execute()

    return f"https://drive.google.com/uc?id={file_id}"

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

# ---------- LOGOUT ----------
def logout():
    st.session_state.logged_in = False
    st.rerun()

# ---------- MAIN ----------
if not st.session_state.logged_in:
    login()

else:
    st.sidebar.write(f"👤 {st.session_state.username} ({st.session_state.role})")

    if st.sidebar.button("Logout"):
        logout()

    if st.session_state.role == "faculty":
        menu = ["Submit Issue", "My Issues"]
    else:
        menu = ["Submit Issue", "Dashboard", "User Management"]

    choice = st.sidebar.selectbox("Navigation", menu)

    # ================= SUBMIT ISSUE =================
    if choice == "Submit Issue":

        st.title("📅 Submit Timetable Issue")

        with st.form("issue_form"):

            name = st.session_state.username.capitalize()

            course_code = st.text_input("Course Code (e.g., 25FAP-123)")
            course_name = st.text_input("Course Name")

            semester = st.selectbox("Semester", ["1","2","3","4","5","6","7","8"])
            day = st.selectbox("Day", ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday"])

            time_slot = st.selectbox("Time Slot", [
                "9:30 – 10:20",
                "10:20 – 11:10",
                "11:10 – 12:00",
                "12:00 – 12:50",
                "12:50 – 1:50 (Break)",
                "1:50 – 2:40",
                "2:40 – 3:30",
                "3:30 – 4:20"
            ])

            issue_type = st.selectbox("Issue Type", ["Time Clash","Room Issue","Overload","Other"])
            description = st.text_area("Description")
            urgency = st.selectbox("Urgency", ["Low","Medium","High"])

            uploaded_file = st.file_uploader("Upload Screenshot", type=["png","jpg","jpeg"])

            submit = st.form_submit_button("Submit")

        if submit:

            if not validate_course_code(course_code):
                st.error("❌ Invalid Course Code (Use: 25FAP-123)")

            else:
                file_link = ""

                if uploaded_file is not None:
                    file_link = upload_to_drive(uploaded_file)

                new_data = pd.DataFrame([[
                    name, course_code, course_name, semester, day, time_slot,
                    issue_type, description, urgency,
                    file_link,
                    "Pending","",datetime.now()
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

                st.success("✅ Issue submitted successfully!")

    # ================= DASHBOARD =================
    elif choice == "Dashboard":

        st.title("📊 Dashboard")

        if os.path.exists(FILE):
            df = pd.read_csv(FILE, dtype=str).fillna("")

            faculty = st.selectbox("Faculty", ["All"] + list(df["Name"].unique()))
            status = st.selectbox("Status", ["All"] + list(df["Status"].unique()))

            if faculty != "All":
                df = df[df["Name"] == faculty]
            if status != "All":
                df = df[df["Status"] == status]

            for i in df.index:

                st.markdown(f"### {df.loc[i,'Course Code']} ({df.loc[i,'Course Name']})")

                if df.loc[i,"Image"]:
                    st.image(df.loc[i,"Image"], width=300)

                new_status = st.selectbox(
                    "Update Status",
                    ["Pending","In Review","Resolved"],
                    index=["Pending","In Review","Resolved"].index(df.loc[i,"Status"]),
                    key=f"s{i}"
                )

                if st.button("Update", key=f"b{i}"):
                    df.loc[i,"Status"] = new_status
                    df.to_csv(FILE, index=False)
                    st.success("Updated")

    # ================= USER MANAGEMENT =================
    elif choice == "User Management":

        st.title("👥 User Management")

        users_df = load_users()

        for i in users_df.index:
            st.write(f"{users_df.loc[i,'username']} ({users_df.loc[i,'role']})")

            new_pass = st.text_input("New Password", key=f"p{i}")

            if st.button("Reset", key=f"r{i}"):
                users_df.loc[i,"password"] = new_pass
                users_df.to_csv(USER_FILE, index=False)
                st.success("Password updated")

        st.markdown("## ➕ Add User")

        new_user = st.text_input("Username")
        new_pass = st.text_input("Password", type="password")
        role = st.selectbox("Role", ["faculty","admin"])

        if st.button("Add User"):
            users_df = pd.concat([users_df,
                pd.DataFrame([[new_user,new_pass,role]],
                columns=["username","password","role"])
            ])
            users_df.to_csv(USER_FILE, index=False)
            st.success("User added")

    # ================= MY ISSUES =================
    elif choice == "My Issues":

        st.title("📌 My Issues")

        if os.path.exists(FILE):
            df = pd.read_csv(FILE, dtype=str).fillna("")
            df = df[df["Name"].str.lower() == st.session_state.username.lower()]

            for i in df.index:
                st.write(f"{df.loc[i,'Course Code']} - {df.loc[i,'Status']}")
