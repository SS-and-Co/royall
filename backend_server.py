"""
Royal Groceries - Backend Server
Handles OTP delivery (Email/SMS), Order notifications, and Admin alerts.

SETUP:
1. Enable 2-Step Verification on your Gmail account
2. Generate an App Password: Google Account > Security > App Passwords
3. Set environment variables or edit the config below:
   - ROYAL_SMTP_EMAIL=siddharths1003@gmail.com
   - ROYAL_SMTP_PASSWORD=your_16_char_app_password
   - ROYAL_TWILIO_SID=your_sid (optional, for SMS)
   - ROYAL_TWILIO_TOKEN=your_token (optional, for SMS)
   - ROYAL_TWILIO_PHONE=+1234567890 (optional, for SMS)

4. Run: python backend_server.py
"""

import http.server
import json
import urllib.request
import urllib.parse
import smtplib
import random
import string
import threading
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import base64
import os
import traceback

PORT = int(os.environ.get('ROYAL_PORT', 8000))

# ── Configuration ──────────────────────────────────────────
SMTP_SERVER = 'smtp.gmail.com'
SMTP_PORT = 587
SENDER_EMAIL = os.environ.get('ROYAL_SMTP_EMAIL', 'siddharths1003@gmail.com')
SENDER_PASSWORD = os.environ.get('ROYAL_SMTP_PASSWORD', 'vsekxaewjkzvhfpl')  # Gmail App Password
ADMIN_EMAIL = 'siddharths1003@gmail.com'

TWILIO_SID = os.environ.get('ROYAL_TWILIO_SID', '')
TWILIO_TOKEN = os.environ.get('ROYAL_TWILIO_TOKEN', '')
TWILIO_PHONE = os.environ.get('ROYAL_TWILIO_PHONE', '')

# OTP store: {identifier: {otp, timestamp}}
otp_store = {}
OTP_EXPIRY_SECONDS = 600

# ── Email Sender ───────────────────────────────────────────
def send_email(to_email, subject, html_body):
    if not SENDER_PASSWORD:
        print(f"[SIMULATE] Email to {to_email} | Subject: {subject}")
        print(f"[INFO] To send real emails, set ROYAL_SMTP_PASSWORD env var to your Gmail App Password")
        return True  # Return success so frontend works in dev mode

    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = f'Royal Groceries <{SENDER_EMAIL}>'
        msg['To'] = to_email
        msg.attach(MIMEText(html_body, 'html'))

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=10) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)

        print(f"[OK] Email sent to {to_email}")
        return True
    except smtplib.SMTPAuthenticationError:
        print(f"[FAIL] Gmail auth failed. Use a 16-char App Password, NOT your regular password.")
        print(f"       Go to: https://myaccount.google.com/apppasswords")
        return False
    except Exception as e:
        print(f"[FAIL] Email error: {e}")
        traceback.print_exc()
        return False


# ── SMS Sender (Twilio) ───────────────────────────────────
def send_sms(phone, message):
    if not TWILIO_SID or not TWILIO_TOKEN:
        print(f"[SIMULATE] SMS to {phone}: {message}")
        print(f"[INFO] To send real SMS, set ROYAL_TWILIO_SID, ROYAL_TWILIO_TOKEN, ROYAL_TWILIO_PHONE env vars")
        return True

    try:
        url = f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_SID}/Messages.json"
        payload = urllib.parse.urlencode({
            'To': phone, 'From': TWILIO_PHONE, 'Body': message
        }).encode('ascii')
        req = urllib.request.Request(url, data=payload)
        cred = base64.b64encode(f"{TWILIO_SID}:{TWILIO_TOKEN}".encode()).decode()
        req.add_header("Authorization", f"Basic {cred}")
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
        with urllib.request.urlopen(req, timeout=10) as resp:
            print(f"[OK] SMS sent to {phone}")
            return True
    except Exception as e:
        print(f"[FAIL] SMS error: {e}")
        return False


# ── Order Code Generator ──────────────────────────────────
def generate_order_code():
    digits = ''.join(random.choices(string.digits, k=4))
    letters = ''.join(random.choices(string.ascii_uppercase, k=2))
    return digits + letters


# ── OTP Management ────────────────────────────────────────
def store_otp(identifier, otp):
    otp_store[identifier] = {'otp': otp, 'time': time.time()}

def verify_stored_otp(identifier, otp):
    entry = otp_store.get(identifier)
    if not entry:
        return False
    if time.time() - entry['time'] > OTP_EXPIRY_SECONDS:
        del otp_store[identifier]
        return False
    if entry['otp'] == otp:
        del otp_store[identifier]
        return True
    return False

def cleanup_expired_otps():
    while True:
        time.sleep(60)
        now = time.time()
        expired = [k for k, v in otp_store.items() if now - v['time'] > OTP_EXPIRY_SECONDS]
        for k in expired:
            del otp_store[k]


# ── HTML Templates ─────────────────────────────────────────
def otp_email_html(otp):
    return f"""
    <div style="font-family:'Segoe UI',Arial,sans-serif;max-width:500px;margin:auto;padding:40px;
    background:linear-gradient(135deg,#0A192F,#172A45);border-radius:20px;color:#fff;
    border:1px solid rgba(58,123,213,0.3)">
    <h1 style="text-align:center;color:#3A7BD5;margin-bottom:10px">👑 Royal Groceries</h1>
    <p style="text-align:center;font-size:16px;color:#8892B0">Your verification code</p>
    <div style="text-align:center;font-size:42px;font-weight:bold;letter-spacing:12px;
    color:#3A7BD5;padding:25px;background:rgba(255,255,255,0.05);border-radius:16px;
    margin:25px 0;border:1px solid rgba(58,123,213,0.2)">{otp}</div>
    <p style="text-align:center;color:#8892B0;font-size:13px">
    This code expires in 10 minutes. Do not share it with anyone.</p>
    <hr style="border:none;border-top:1px solid rgba(255,255,255,0.1);margin:20px 0">
    <p style="text-align:center;color:#556;font-size:11px">Royal Groceries &bull; Premium Shopping Experience</p>
    </div>"""

def order_email_html(user, items, total, method, address, delivery_charge, code):
    rows = ''.join(f"""<tr>
    <td style="padding:12px;border-bottom:1px solid rgba(255,255,255,0.1);color:#E6F1FF">{it['name']}</td>
    <td style="padding:12px;border-bottom:1px solid rgba(255,255,255,0.1);color:#3A7BD5;
    text-align:right;font-weight:600">₹{it['price']}</td>
    <td style="padding:12px;border-bottom:1px solid rgba(255,255,255,0.1);text-align:center;
    color:#E6F1FF">{it.get('qty',1)}</td></tr>""" for it in items)

    if method == 'home':
        delivery_info = f"""<p><b>📍 Address:</b> {address}</p>
        <p><b>🚚 Delivery Charge:</b> ₹{delivery_charge}</p>"""
    else:
        delivery_info = "<p><b>🏪 Method:</b> Collect from Shop</p>"

    grand_total = total + delivery_charge
    return f"""
    <div style="font-family:'Segoe UI',Arial,sans-serif;max-width:600px;margin:auto;padding:40px;
    background:linear-gradient(135deg,#0A192F,#172A45);border-radius:20px;color:#fff;
    border:1px solid rgba(58,123,213,0.3)">
    <h1 style="text-align:center;color:#3A7BD5">👑 New Order - Royal</h1>
    <div style="background:rgba(255,255,255,0.05);padding:20px;border-radius:12px;margin:20px 0">
    <p><b>👤 Customer:</b> {user}</p>
    {delivery_info}
    <p><b>🔑 Order Code:</b> <span style="font-size:28px;color:#3A7BD5;font-weight:bold;
    letter-spacing:4px">{code}</span></p></div>
    <table style="width:100%;border-collapse:collapse;margin:20px 0">
    <tr style="background:rgba(58,123,213,0.15)">
    <th style="padding:12px;text-align:left;color:#3A7BD5;border-bottom:2px solid rgba(58,123,213,0.3)">Item</th>
    <th style="padding:12px;text-align:right;color:#3A7BD5;border-bottom:2px solid rgba(58,123,213,0.3)">Price</th>
    <th style="padding:12px;text-align:center;color:#3A7BD5;border-bottom:2px solid rgba(58,123,213,0.3)">Qty</th>
    </tr>{rows}</table>
    <div style="text-align:right;padding:20px;background:rgba(58,123,213,0.1);
    border-radius:12px;margin-top:10px">
    <span style="font-size:14px;color:#8892B0">Grand Total</span><br>
    <span style="font-size:32px;color:#3A7BD5;font-weight:bold">₹{grand_total}</span></div>
    </div>"""


# ── HTTP Handler ───────────────────────────────────────────
class RoyalHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        print(f"[{self.log_date_time_string()}] {format % args}")

    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS, GET')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def respond_json(self, data, code=200):
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))

    def do_POST(self):
        try:
            length = int(self.headers.get('Content-Length', 0))
            body = json.loads(self.rfile.read(length).decode('utf-8')) if length else {}
        except Exception:
            self.respond_json({"status": "error", "message": "Invalid JSON"}, 400)
            return

        # ── Send OTP ──
        if self.path == '/send-otp':
            identifier = body.get('identifier', '').strip()
            otp = body.get('otp', '')
            if not identifier or not otp:
                self.respond_json({"status": "error", "message": "Missing identifier or otp"})
                return

            store_otp(identifier, otp)

            if '@' in identifier:
                ok = send_email(identifier, "Royal Groceries - Your OTP Code", otp_email_html(otp))
            else:
                ok = send_sms(identifier, f"Your Royal Groceries OTP is: {otp}. Valid for 10 minutes.")

            self.respond_json({
                "status": "success" if ok else "error",
                "message": "OTP sent" if ok else "Failed to send OTP",
                "devOtp": otp if not SENDER_PASSWORD else None  # Show OTP in dev mode only
            })

        # ── Verify OTP (server-side verification) ──
        elif self.path == '/verify-otp':
            identifier = body.get('identifier', '').strip()
            otp = body.get('otp', '')
            valid = verify_stored_otp(identifier, otp)
            self.respond_json({
                "status": "success" if valid else "error",
                "message": "OTP verified" if valid else "Invalid or expired OTP"
            })

        # ── Send Order to Admin ──
        elif self.path == '/send-order':
            user = body.get('user', 'Unknown')
            items = body.get('items', [])
            total = body.get('total', 0)
            method = body.get('method', 'shop')
            address = body.get('address', '')
            delivery_charge = body.get('deliveryCharge', 0)
            code = generate_order_code()

            html = order_email_html(user, items, total, method, address, delivery_charge, code)
            ok = send_email(ADMIN_EMAIL, f"New Order [{code}] - Royal Groceries", html)

            self.respond_json({
                "status": "success" if ok else "error",
                "code": code,
                "message": "Order placed" if ok else "Order saved but email failed"
            })

        # ── Admin Notification ──
        elif self.path == '/notify-admin':
            subject = body.get('subject', 'Royal Admin Notification')
            message = body.get('message', '')
            html = f"""<div style="font-family:'Segoe UI',Arial;max-width:500px;margin:auto;padding:30px;
            background:linear-gradient(135deg,#0A192F,#172A45);border-radius:16px;color:#fff">
            <h1 style="text-align:center;color:#3A7BD5">👑 Royal Admin Alert</h1>
            <div style="background:rgba(255,255,255,0.05);padding:20px;border-radius:8px;
            margin:15px 0"><p style="color:#E6F1FF">{message}</p></div></div>"""
            ok = send_email(ADMIN_EMAIL, subject, html)
            self.respond_json({"status": "success" if ok else "error"})

        # ── Health Check ──
        elif self.path == '/health':
            self.respond_json({
                "status": "ok",
                "smtp_configured": bool(SENDER_PASSWORD),
                "twilio_configured": bool(TWILIO_SID),
                "admin_email": ADMIN_EMAIL
            })

        else:
            self.respond_json({"status": "error", "message": "Not found"}, 404)


# ── Server Start ───────────────────────────────────────────
def run(port=PORT):
    import sys, io
    # Force UTF-8 output on Windows to handle special chars
    if sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

    # Start OTP cleanup thread
    cleanup_thread = threading.Thread(target=cleanup_expired_otps, daemon=True)
    cleanup_thread.start()

    server = http.server.ThreadingHTTPServer(('', port), RoyalHandler)
    server.daemon_threads = True

    print(f"\n{'='*55}")
    print(f"  [ROYAL] ROYAL GROCERIES - Backend Server")
    print(f"{'='*55}")
    print(f"  URL:    http://127.0.0.1:{port}")
    print(f"  Admin:  {ADMIN_EMAIL}")
    print(f"  Mode:   Multi-threaded")
    print(f"{'='*55}")
    if SENDER_PASSWORD:
        print(f"  [OK] SMTP: Configured (real emails will be sent)")
    else:
        print(f"  [!!] SMTP: NOT configured (emails simulated)")
        print(f"       Set ROYAL_SMTP_PASSWORD env var")
        print(f"       OTP will be shown in console & returned to frontend")
    if TWILIO_SID:
        print(f"  [OK] Twilio: Configured (real SMS will be sent)")
    else:
        print(f"  [!!] Twilio: NOT configured (SMS simulated)")
    print(f"{'='*55}")
    print(f"  Endpoints:")
    print(f"    POST /send-otp     - Send OTP via email/SMS")
    print(f"    POST /verify-otp   - Verify OTP server-side")
    print(f"    POST /send-order   - Send order to admin email")
    print(f"    POST /notify-admin - Send admin notification")
    print(f"    POST /health       - Health check")
    print(f"{'='*55}\n")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[INFO] Server shutting down...")
        server.shutdown()

if __name__ == "__main__":
    run()
