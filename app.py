from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import os
import smtplib
import schedule
import threading
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)
CORS(app)

SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "")
SENDER_PASSWORD = os.environ.get("SENDER_PASSWORD", "")
SENDER_NAME = "AuraCalendar"

def send_email(to_email, to_name, event_title, event_date, event_time):
    msg = MIMEMultipart()
    msg["From"] = f"AuraCalendar No-Reply <{SENDER_EMAIL}>"
    msg["To"] = to_email
    msg["Subject"] = f"Reminder: {event_title} is coming up!"
    body = f"""
    <html>
    <body style="margin:0;padding:0;background:#0d0d1a;font-family:'Poppins',Arial,sans-serif;">
      <div style="max-width:600px;margin:40px auto;background:#1a1a2e;border-radius:20px;overflow:hidden;border:1px solid rgba(255,255,255,0.1);">
        <div style="background:linear-gradient(135deg,#4a7cff,#764ba2);padding:32px;text-align:center;">
          <h1 style="color:#fff;font-size:26px;margin:0;letter-spacing:1px;">AuraCalendar</h1>
          <p style="color:rgba(255,255,255,0.8);margin:6px 0 0;font-size:13px;">Your Personal Event Reminder</p>
        </div>
        <div style="padding:36px 40px;">
          <p style="color:#f0f0ff;font-size:16px;margin:0 0 8px;">Hi <strong>{to_name}</strong>,</p>
          <p style="color:rgba(255,255,255,0.6);font-size:14px;margin:0 0 28px;">You have an upcoming event. Here are the details:</p>
          <div style="background:rgba(74,124,255,0.1);border:1px solid rgba(74,124,255,0.3);border-radius:14px;padding:24px;">
            <p style="color:#7fa8ff;font-size:12px;font-weight:600;margin:0 0 6px;text-transform:uppercase;letter-spacing:1px;">Event</p>
            <p style="color:#fff;font-size:20px;font-weight:600;margin:0 0 20px;">{event_title}</p>
            <div style="display:flex;gap:24px;">
              <div>
                <p style="color:#7fa8ff;font-size:12px;margin:0 0 4px;">Date</p>
                <p style="color:#f0f0ff;font-size:14px;font-weight:500;margin:0;">📅 {event_date}</p>
              </div>
              <div>
                <p style="color:#7fa8ff;font-size:12px;margin:0 0 4px;">Time</p>
                <p style="color:#f0f0ff;font-size:14px;font-weight:500;margin:0;">⏰ {event_time}</p>
              </div>
            </div>
          </div>
          <p style="color:rgba(255,255,255,0.5);font-size:13px;margin:28px 0 0;text-align:center;">Don't miss it — AuraCalendar has got your back!</p>
        </div>
        <div style="background:rgba(0,0,0,0.3);padding:20px;text-align:center;border-top:1px solid rgba(255,255,255,0.07);">
          <p style="color:rgba(255,255,255,0.25);font-size:11px;margin:0;">© 2026 AuraCalendar · This is an automated reminder · Please do not reply</p>
        </div>
      </div>
    </body>
    </html>
    """
    msg.attach(MIMEText(body, "html"))
    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.starttls()
    server.login(SENDER_EMAIL, SENDER_PASSWORD)
    server.sendmail(SENDER_EMAIL, to_email, msg.as_string())
    server.quit()

def check_reminders():
    conn = sqlite3.connect("calendar.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, name, email, title, event_date, event_time, reminder_minutes
        FROM events WHERE reminder_sent = 0
    """)
    events = cursor.fetchall()
    from datetime import datetime, timedelta
    now = datetime.now()
    for event in events:
        id, name, email, title, date, time, reminder_mins = event
        event_dt = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
        reminder_dt = event_dt - timedelta(minutes=int(reminder_mins))
        if now >= reminder_dt:
            try:
                send_email(email, name, title, date, time)
                cursor.execute("UPDATE events SET reminder_sent = 1 WHERE id = ?", (id,))
                conn.commit()
                print(f"Reminder sent for: {title}")
            except Exception as e:
                print(f"Email error: {e}")
    conn.close()

def run_scheduler():
    schedule.every(1).minutes.do(check_reminders)
    while True:
        schedule.run_pending()
        import time as t
        t.sleep(1)

def init_db():
    conn = sqlite3.connect("calendar.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            title TEXT NOT NULL,
            category TEXT NOT NULL,
            event_date TEXT NOT NULL,
            event_time TEXT NOT NULL,
            reminder_minutes INTEGER NOT NULL,
            notes TEXT,
            reminder_sent INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

init_db()

@app.route("/add_event", methods=["POST"])
def add_event():
    name = request.form.get("name")
    email = request.form.get("email")
    title = request.form.get("title")
    category = request.form.get("category")
    date = request.form.get("date")
    time = request.form.get("time")
    reminder = request.form.get("reminder_minutes")
    notes = request.form.get("notes")
    conn = sqlite3.connect("calendar.db")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO events 
        (name, email, title, category, event_date, event_time, reminder_minutes, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (name, email, title, category, date, time, reminder, notes))
    conn.commit()
    conn.close()
    return jsonify({"message": "Event saved successfully"})

@app.route("/get_events", methods=["GET"])
def get_events():
    email = request.args.get("email")
    conn = sqlite3.connect("calendar.db")
    cursor = conn.cursor()
    if email:
        cursor.execute("SELECT * FROM events WHERE email = ?", (email,))
    else:
        cursor.execute("SELECT * FROM events")
    rows = cursor.fetchall()
    conn.close()
    events = []
    for row in rows:
        events.append({
            "id": row[0],
            "name": row[1],
            "email": row[2],
            "title": row[3],
            "category": row[4],
            "date": row[5],
            "time": row[6],
            "reminder_minutes": row[7],
            "notes": row[8]
        })
    return jsonify(events)

scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
scheduler_thread.start()

if __name__ == "__main__":
    app.run(debug=True, port=5000)
