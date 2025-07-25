import streamlit as st
import requests
import datetime
import time
import threading
import smtplib
from email.mime.text import MIMEText
import uuid

# ========================= EMAIL SETTINGS =========================
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL_ADDRESS = "jamesutkovic@gmail.com"
EMAIL_PASSWORD = "gytckevcovrzimws"
TO_EMAIL = "jamesutkovic@gmail.com"
# ==================================================================

COURSE_OPTIONS = {
    "Bethpage (All Courses)": "19765",
}

POLL_INTERVAL = 30  # seconds

def send_email(subject, body):
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = TO_EMAIL
    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.send_message(msg)
        print(f"✅ Email sent: {subject}")
    except Exception as e:
        print(f"❌ Failed to send email: {e}")

def send_email_alert(times, date, start_time_str, end_time_str):
    subject = "🔥 Tee Times Found!"
    times_str = ', '.join(times)
    body = (
        f"Tee times found for {date} between {start_time_str}-{end_time_str}:\n"
        f"{times_str}\n\nGo to Bethpage ForeUp booking page now!"
    )
    send_email(subject, body)

def within_window(t, start_time, end_time):
    return start_time <= t <= end_time

def check_day(date, holes, course_id, start_time, end_time):
    url = "https://foreupsoftware.com/index.php/api/booking/times"
    params = {
        "time": "00:00",
        "date": date,
        "holes": holes,
        "course_id": course_id,
        "api_key": "no_limits"
    }
    r = requests.get(url, params=params)
    r.raise_for_status()
    data = r.json()
    available = []
    for slot in data:
        if slot.get('is_bookable'):
            t = datetime.datetime.strptime(slot['time'], "%H:%M:%S").time()
            if within_window(t, start_time, end_time):
                available.append(slot['time'])
    return available

def monitor_task(task_id, date, holes, course_id, start_time, end_time, start_time_str, end_time_str):
    # Once monitoring actually starts searching, change status to "Started"
    st.session_state['monitors'][task_id]['status'] = "Started"
    while st.session_state['monitors'][task_id]['active']:
        times = check_day(date, holes, course_id, start_time, end_time)
        if times:
            st.session_state['monitors'][task_id]['status'] = f"🔥 Times found! {times}"
            send_email_alert(times, date, start_time_str, end_time_str)
        else:
            st.session_state['monitors'][task_id]['status'] = "No times yet..."
        time.sleep(POLL_INTERVAL)

# Initialize monitors dict
if 'monitors' not in st.session_state:
    st.session_state['monitors'] = {}

st.title("Bethpage Tee Time Monitor")

# UI Inputs
date_input = st.date_input("Select Date (MM/DD/YYYY)", datetime.date.today() + datetime.timedelta(days=7))
holes_input = st.selectbox("Number of Holes", [9, 18])
course_input = st.selectbox("Course", list(COURSE_OPTIONS.keys()))

hours = [f"{h:02d}:00" for h in range(0, 24)]
start_time_str = st.selectbox("Start Time", hours, index=5)
end_time_str = st.selectbox("End Time", hours, index=7)
start_time = datetime.datetime.strptime(start_time_str, "%H:%M").time()
end_time = datetime.datetime.strptime(end_time_str, "%H:%M").time()

# Start a new monitor
if st.button("Add Monitor"):
    task_id = str(uuid.uuid4())
    api_date = date_input.strftime("%Y-%m-%d")
    st.session_state['monitors'][task_id] = {
        'date': api_date,
        'holes': holes_input,
        'course_id': COURSE_OPTIONS[course_input],
        'start': start_time_str,
        'end': end_time_str,
        'active': True,
        'status': 'Starting...'
    }
    threading.Thread(target=monitor_task, args=(task_id, api_date, holes_input, COURSE_OPTIONS[course_input], start_time, end_time, start_time_str, end_time_str), daemon=True).start()
    st.success(f"Monitoring started for {date_input.strftime('%m/%d/%Y')} {start_time_str}-{end_time_str}")
    send_email("✅ Monitoring Started", f"Monitoring started for {date_input.strftime('%m/%d/%Y')} between {start_time_str} and {end_time_str}.")

# Display active monitors
st.subheader("Active Monitors")
to_delete = []
for task_id, task in st.session_state['monitors'].items():
    col1, col2, col3, col4 = st.columns([3,3,3,1])
    with col1:
        st.write(f"Date: {task['date']}")
    with col2:
        st.write(f"Time: {task['start']} - {task['end']}")
    with col3:
        st.write(task['status'])
    with col4:
        if task['active']:
            if st.button("Cancel", key=task_id):
                st.session_state['monitors'][task_id]['active'] = False
                send_email("🛑 Monitoring Stopped", f"Monitoring stopped for {task['date']} between {task['start']} and {task['end']}.")
                to_delete.append(task_id)

# Remove stopped monitors from view
for task_id in to_delete:
    del st.session_state['monitors'][task_id]
