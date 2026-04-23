import streamlit as st
import pandas as pd
import os
from datetime import datetime

FILE = "issues.csv"
USER_FILE = "users.csv"

# ---------- LOAD USERS ---------- #
def load_users():
    if os.path.exists(USER_FILE):
        df = pd.read_csv(USER_FILE, dtype=str).fillna("")
        df.columns = df.columns.str.strip().str.lower()

        for col in ["username", "password", "role"]:
            if col not in df.columns:
                df[col] = ""

        df["username"] = df["username"].str.strip().str.lower()
        df["password"] = df["password"].str.strip()
        df["role"] = df["role"].str.strip().str.lower()

        return df
    else:
        return pd.DataFrame(columns=["username", "password", "role"])

# ---------- SESSION ---------- #
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.role = ""

# ---------- LOGIN ---------- #
def login():
    st.title("🔐 Login")

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
            st.success("Login successful!")
            st.rerun()
        else:
            st.error("❌ Invalid credentials")

# ---------- LOGOUT ---------- #
def logout():
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.role = ""
    st.rerun()

# ---------- MAIN ---------- #
if not st.session_state.logged_in:
    login()

else:
    st.sidebar.write(f"👤 {st.session_state.username} ({st.session_state.role})")

    if st.sidebar.button("Logout"):
        logout()

    if st.session_state.role == "faculty":
        menu = ["Submit Issue", "My Issues"]
    else:
        menu = ["Submit Issue", "Dashboard"]

    choice = st.sidebar.selectbox("Navigation", menu)

    # =========================================================
    # ------------------ SUBMIT ISSUE --------------------------
    # =========================================================
    if choice == "Submit Issue":

        st.title("📅 Timetable Issue System")

        with st.form("issue_form"):
            name = st.session_state.username.capitalize()

            course = st.text_input("Course")
            semester = st.selectbox("Semester", ["1","2","3","4","5","6","7","8"])
            day = st.selectbox("Day", ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday"])
            time_slot = st.selectbox("Time Slot", ["9–10 AM","10–11 AM","11–12 PM","12–1 PM","2–3 PM","3–4 PM"])

            issue_type = st.selectbox("Issue Type", ["Time Clash","Room Issue","Overload","Back-to-back","Other"])
            description = st.text_area("Description")
            urgency = st.selectbox("Urgency", ["Low","Medium","High"])

            submit = st.form_submit_button("Submit Issue")

        if submit:
            if course.strip() == "" or description.strip() == "":
                st.warning("⚠️ Please fill required fields")
            else:
                new_data = pd.DataFrame([[
                    name, course, semester, day, time_slot,
                    issue_type, description, urgency,
                    "Pending", "", datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                ]],
                columns=[
                    "Name","Course","Semester","Day","Time Slot",
                    "Issue Type","Description","Urgency",
                    "Status","Remarks","Submission Date"
                ])

                if os.path.exists(FILE):
                    new_data.to_csv(FILE, mode='a', header=False, index=False)
                else:
                    new_data.to_csv(FILE, index=False)

                st.success("✅ Issue submitted successfully!")

    # =========================================================
    # ------------------ DASHBOARD WITH FILTERS ----------------
    # =========================================================
    elif choice == "Dashboard":

        st.title("📊 Admin Dashboard")

        if os.path.exists(FILE):
            df = pd.read_csv(FILE, dtype=str).fillna("")

            # SUMMARY
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Total", len(df))
            col2.metric("Pending", len(df[df["Status"] == "Pending"]))
            col3.metric("In Review", len(df[df["Status"] == "In Review"]))
            col4.metric("Resolved", len(df[df["Status"] == "Resolved"]))

            st.markdown("---")

            # FILTERS
            col1, col2, col3 = st.columns(3)

            with col1:
                faculty_filter = st.selectbox("Faculty", ["All"] + sorted(df["Name"].unique().tolist()))

            with col2:
                status_filter = st.selectbox("Status", ["All"] + sorted(df["Status"].unique().tolist()))

            with col3:
                urgency_filter = st.selectbox("Urgency", ["All"] + sorted(df["Urgency"].unique().tolist()))

            filtered_df = df.copy()

            if faculty_filter != "All":
                filtered_df = filtered_df[filtered_df["Name"] == faculty_filter]

            if status_filter != "All":
                filtered_df = filtered_df[filtered_df["Status"] == status_filter]

            if urgency_filter != "All":
                filtered_df = filtered_df[filtered_df["Urgency"] == urgency_filter]

            st.markdown("---")

            # SORT
            priority_order = {"High": 0, "Medium": 1, "Low": 2}
            status_order = {"Pending": 0, "In Review": 1, "Resolved": 2}

            filtered_df["priority_sort"] = filtered_df["Urgency"].map(priority_order)
            filtered_df["status_sort"] = filtered_df["Status"].map(status_order)

            filtered_df = filtered_df.sort_values(by=["status_sort", "priority_sort"])

            def get_icon(status):
                return {"Pending": "🔴", "In Review": "🟡", "Resolved": "🟢"}.get(status, "⚪")

            if not filtered_df.empty:

                for i in filtered_df.index:

                    icon = get_icon(filtered_df.loc[i, "Status"])

                    st.markdown(f"""
                    ### {icon} {filtered_df.loc[i, 'Name']} — {filtered_df.loc[i, 'Issue Type']}
                    **{filtered_df.loc[i, 'Day']} | {filtered_df.loc[i, 'Time Slot']}**
                    Course: {filtered_df.loc[i, 'Course']} | Semester: {filtered_df.loc[i, 'Semester']}
                    Urgency: **{filtered_df.loc[i, 'Urgency']}**
                    """)

                    with st.expander("View Details & Update"):

                        st.write(f"Description: {filtered_df.loc[i, 'Description']}")
                        st.write(f"Submitted: {filtered_df.loc[i, 'Submission Date']}")

                        status = st.selectbox(
                            "Update Status",
                            ["Pending", "In Review", "Resolved"],
                            index=["Pending","In Review","Resolved"].index(filtered_df.loc[i,"Status"]),
                            key=f"s{i}"
                        )

                        remarks = st.text_area(
                            "Remarks",
                            value=filtered_df.loc[i,"Remarks"],
                            key=f"r{i}"
                        )

                        if st.button("💾 Save Update", key=f"b{i}"):
                            df.loc[i,"Status"] = status
                            df.loc[i,"Remarks"] = remarks
                            df.to_csv(FILE, index=False)
                            st.success("✅ Updated successfully")

                    st.markdown("---")

            else:
                st.info("No issues match selected filters.")

        else:
            st.info("No issues submitted yet.")

    # =========================================================
    # ------------------ MY ISSUES (FACULTY EDIT) --------------
    # =========================================================
    elif choice == "My Issues":

        st.title("📌 My Submitted Issues")

        if os.path.exists(FILE):
            df = pd.read_csv(FILE, dtype=str).fillna("")

            user_df = df[df["Name"].str.lower() == st.session_state.username.lower()]

            if not user_df.empty:

                for i in user_df.index:

                    status = user_df.loc[i, "Status"]

                    st.markdown(f"""
                    ### {user_df.loc[i, 'Issue Type']} — {user_df.loc[i, 'Course']}
                    **{user_df.loc[i, 'Day']} | {user_df.loc[i, 'Time Slot']}**
                    Status: **{status}**
                    """)

                    with st.expander("View / Edit"):

                        if status == "Pending":

                            course = st.text_input("Course", value=user_df.loc[i, "Course"], key=f"c{i}")
                            semester = st.selectbox("Semester", ["1","2","3","4","5","6","7","8"],
                                index=["1","2","3","4","5","6","7","8"].index(user_df.loc[i, "Semester"]), key=f"s{i}")
                            description = st.text_area("Description", value=user_df.loc[i, "Description"], key=f"d{i}")
                            urgency = st.selectbox("Urgency", ["Low","Medium","High"],
                                index=["Low","Medium","High"].index(user_df.loc[i, "Urgency"]), key=f"u{i}")

                            if st.button("✏️ Update Issue", key=f"btn{i}"):

                                df.loc[i, "Course"] = course
                                df.loc[i, "Semester"] = semester
                                df.loc[i, "Description"] = description
                                df.loc[i, "Urgency"] = urgency

                                df.to_csv(FILE, index=False)
                                st.success("✅ Issue updated!")

                        else:
                            st.write(user_df.loc[i])
                            st.warning("🔒 Editing disabled (under review or resolved)")

                    st.markdown("---")

            else:
                st.info("You have not submitted any issues yet.")

        else:
            st.info("No data available.")