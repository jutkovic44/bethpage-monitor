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

CHECK_WINDOW = ("05:00", "07:00")
POLL_INTERVAL = 30  # seconds

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

def within_window(t):
    start = datetime.datetime.strptime(CHECK_WINDOW[0], "%H:%M").time()
    end = datetime.datetime.strptime(CHECK_WINDOW[1], "%H:%M").time()
    return start <= t <= end

def check_day(date, holes, course_id):
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
            if within_window(t):
                available.append(slot['time'])
    return available

def monitor(date, holes, course_id):
    while st.session_state['monitoring']:
        times = check_day(date, holes, course_id)
        if times:
            st.session_state['last_result'] = f"🔥 Tee times found! {times}"
            send_email_alert(times)
        else:
            st.session_state['last_result'] = "No times yet..."
        time.sleep(POLL_INTERVAL)

st.title("Bethpage Tee Time Monitor")

# Test email button
if st.button("Send Test Email"):
    send_email_alert(["TEST 06:00"])
    st.success("Test email sent!")

date_input = st.date_input("Select Date", datetime.date.today() + datetime.timedelta(days=7))
holes_input = st.selectbox("Number of Holes", [9, 18])
course_input = st.selectbox("Course", list(COURSE_OPTIONS.keys()))

if 'monitoring' not in st.session_state:
    st.session_state['monitoring'] = False
if 'last_result' not in st.session_state:
    st.session_state['last_result'] = ""

if st.button("Start Monitoring"):
    st.session_state['monitoring'] = True
    threading.Thread(target=monitor, args=(date_input.strftime("%Y-%m-%d"), holes_input, COURSE_OPTIONS[course_input]), daemon=True).start()
    st.success("Monitoring started!")

if st.button("Stop Monitoring"):
    st.session_state['monitoring'] = False
    st.warning("Monitoring stopped.")

st.write(st.session_state['last_result'])
