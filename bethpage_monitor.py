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
    "Bethpage Black Course": "2431",
    "Bethpage Red Course": "2432",
    "Bethpage Blue Course": "2433",
}

POLL_INTERVAL = 30  # seconds

FACILITY_ID = "19765"  # course_id for Bethpage facility

def send_email(subject, body):
    try:
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = EMAIL_ADDRESS
        msg["To"] = TO_EMAIL
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.send_message(msg)
        print(f"✅ Email sent: {subject}")
    except Exception as e:
        print(f"❌ Email send error: {e}")

def send_email_alert(times, date, start_time_str, end_time_str, course_name, players):
    times_lines = "\n".join(times)
    body = (
        f"Tee times found for {course_name} on {date} between {start_time_str}-{end_time_str} for {players} player(s):\n"
        f"{times_lines}\n\nBook ASAP!"
    )
    send_email(f"🔥 Tee Times Found on {course_name}!", body)

def within_window(t, start_time, end_time):
    return start_time <= t <= end_time

def check_day(date, holes, schedule_id, start_time, end_time, players):
    url = "https://foreupsoftware.com/index.php/api/booking/times"
    # include both facility id and schedule id
    params = {
        "time": "00:00",
        "date": date,
        "holes": holes,
        "course_id": FACILITY_ID,
        "schedule_id": schedule_id,
        "api_key": "no_limits"
    }
    r = requests.get(url, params=params)
    r.raise_for_status()
    data = r.json()
    print("DEBUG API DATA:", data)
    available = []
    for slot in data:
        if slot.get("is_bookable") and slot.get("available_spots", 4) >= players:
            t = datetime.datetime.strptime(slot["time"], "%H:%M:%S").time()
            if within_window(t, start_time, end_time):
                formatted_time = datetime.datetime.strptime(slot["time"][:5], "%H:%M").strftime("%I:%M %p")
                available.append(formatted_time)
    return available

def monitor_task(task_id, date, holes, schedule_id, course_name, start_time, end_time, start_time_str, end_time_str, players):
    st.session_state['monitors'][task_id]['status'] = "Started"
    while st.session_state['monitors'][task_id]['active']:
        try:
            times = check_day(date, holes, schedule_id, start_time, end_time, players)
            if times:
                st.session_state['monitors'][task_id]['status'] = f"🔥 Times found! {times}"
                send_email_alert(times, date, start_time_str, end_time_str, course_name, players)
            else:
                st.session_state['monitors'][task_id]['status'] = "No times yet..."
        except Exception as e:
            st.session_state['monitors'][task_id]['status'] = f"Error: {e}"
        time.sleep(POLL_INTERVAL)

if 'monitors' not in st.session_state:
    st.session_state['monitors'] = {}

st.title("Bethpage Tee Time Monitor")

date_input = st.date_input("Select Date (MM/DD/YYYY)", datetime.date.today() + datetime.timedelta(days=7), format="MM/DD/YYYY")
holes_input = st.selectbox("Number of Holes", [9, 18])
players_input = st.selectbox("Number of Players", [1, 2, 3, 4])
course_input = st.selectbox("Course", list(COURSE_OPTIONS.keys()))

# Time dropdown with AM/PM
hours_12 = []
for h in range(1, 13):
    for m in [0, 30]:
        hours_12.append(f"{h:02d}:{m:02d} AM")
for h in range(1, 13):
    for m in [0, 30]:
        hours_12.append(f"{h:02d}:{m:02d} PM")

start_time_str = st.selectbox("Start Time", hours_12, index=10)
end_time_str = st.selectbox("End Time", hours_12, index=14)
start_time = datetime.datetime.strptime(start_time_str, "%I:%M %p").time()
end_time = datetime.datetime.strptime(end_time_str, "%I:%M %p").time()

if st.button("Add Monitor"):
    task_id = str(uuid.uuid4())
    api_date = date_input.strftime("%Y-%m-%d")
    display_date = date_input.strftime("%m/%d/%Y")
    schedule_id = COURSE_OPTIONS[course_input]
    st.session_state['monitors'][task_id] = {
        'date': display_date,
        'holes': holes_input,
        'players': players_input,
        'course_id': schedule_id,
        'start': start_time_str,
        'end': end_time_str,
        'active': True,
        'status': 'Starting...'
    }
    threading.Thread(target=monitor_task, args=(task_id, api_date, holes_input, schedule_id, course_input, start_time, end_time, start_time_str, end_time_str, players_input), daemon=True).start()
    st.success(f"Monitoring started for {course_input} on {display_date} {start_time_str}-{end_time_str} for {players_input} player(s)")
    send_email("✅ Monitoring Started", f"Monitoring started for {course_input} on {display_date} between {start_time_str} and {end_time_str} for {players_input} player(s).")

st.subheader("Active Monitors")
to_delete = []
for task_id, task in st.session_state['monitors'].items():
    col1, col2, col3, col4 = st.columns([3,3,3,1])
    with col1:
        st.write(f"Date: {task['date']}")
    with col2:
        st.write(f"Time: {task['start']} - {task['end']}")
    with col3:
        st.write(f"{task['status']} (Players: {task['players']})")
    with col4:
        if task['active']:
            if st.button("Cancel", key=task_id):
                st.session_state['monitors'][task_id]['active'] = False
                send_email("🛑 Monitoring Stopped", f"Monitoring stopped for {task['date']} between {task['start']} and {task['end']} for {task['players']} player(s).")
                to_delete.append(task_id)

for task_id in to_delete:
    del st.session_state['monitors'][task_id]
