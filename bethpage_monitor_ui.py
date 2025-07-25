import streamlit as st
import requests
import datetime
import time
import threading
import smtplib
from email.mime.text import MIMEText

# ========================= EMAIL SETTINGS =========================
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL_ADDRESS = "jamesutkovic@gmail.com"  # your Gmail address
EMAIL_PASSWORD = "gytckevcovrzimws"   # your Gmail App Password (not your main password)
TO_EMAIL = "jamesutkovic@gmail.com"       # where to send the alerts
# ==================================================================

COURSE_OPTIONS = {
    "Bethpage (All Courses)": "19765",
}

# Default values (will be overridden by UI selections)
POLL_INTERVAL = 30  # seconds

# Email alert function
def send_email_alert(times):
    subject = "🔥 Tee Times Found!"
    body = f"Tee times found: {', '.join(times)}\n\nGo to Bethpage ForeUp booking page now!"
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = TO_EMAIL
    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.send_message(msg)
        print("✅ Email alert sent!")
    except Exception as e:
        print(f"❌ Failed to send email: {e}")

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

def monitor(date, holes, course_id, start_time, end_time):
    while st.session_state['monitoring']:
        times = check_day(date, holes, course_id, start_time, end_time)
        if times:
            st.session_state['last_result'] = f"🔥 Tee times found! {times}"
            send_email_alert(times)
        else:
            st.session_state['last_result'] = "No times yet..."
        time.sleep(POLL_INTERVAL)

st.title("Bethpage Tee Time Monitor")

# UI Inputs
date_input = st.date_input("Select Date (MM/DD/YYYY)", datetime.date.today() + datetime.timedelta(days=7))
holes_input = st.selectbox("Number of Holes", [9, 18])
course_input = st.selectbox("Course", list(COURSE_OPTIONS.keys()))

# Timeframe selection
hours = [f"{h:02d}:00" for h in range(0, 24)]
start_time_str = st.selectbox("Start Time", hours, index=5)  # default 05:00
end_time_str = st.selectbox("End Time", hours, index=7)      # default 07:00
start_time = datetime.datetime.strptime(start_time_str, "%H:%M").time()
end_time = datetime.datetime.strptime(end_time_str, "%H:%M").time()

if 'monitoring' not in st.session_state:
    st.session_state['monitoring'] = False
if 'last_result' not in st.session_state:
    st.session_state['last_result'] = ""

if st.button("Start Monitoring"):
    st.session_state['monitoring'] = True
    # Format date as YYYY-MM-DD for API
    api_date = date_input.strftime("%Y-%m-%d")
    threading.Thread(target=monitor, args=(api_date, holes_input, COURSE_OPTIONS[course_input], start_time, end_time), daemon=True).start()
    st.success("Monitoring started!")

if st.button("Stop Monitoring"):
    st.session_state['monitoring'] = False
    st.warning("Monitoring stopped.")

st.write(st.session_state['last_result'])
