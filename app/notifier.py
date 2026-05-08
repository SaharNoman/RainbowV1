import smtplib
import os
import urllib.request
import urllib.error
import json
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

# ── Config ────────────────────────────────────────────────
SENDER_EMAIL      = os.environ.get("SENDER_EMAIL",      "rainbowalertsystem@gmail.com")
SENDER_PASSWORD   = os.environ.get("SENDER_PASSWORD",   "plioaikmxzcjyfad")
HEADOFFICE_EMAIL  = os.environ.get("HEADOFFICE_EMAIL",  "sahar.noman.javed@gmail.com")
SENDGRID_API_KEY  = os.environ.get("SENDGRID_API_KEY", "")


# ── Send via SendGrid HTTPS API ───────────────────────────
def _send_via_sendgrid(subject: str, html_body: str) -> dict:
    try:
        payload = json.dumps({
            "personalizations": [{"to": [{"email": HEADOFFICE_EMAIL}]}],
            "from": {"email": SENDER_EMAIL, "name": "Rainbow Inventory"},
            "subject": subject,
            "content": [{"type": "text/html", "value": html_body}]
        }).encode("utf-8")

        req = urllib.request.Request(
            "https://api.sendgrid.com/v3/mail/send",
            data=payload,
            headers={
                "Authorization": f"Bearer {SENDGRID_API_KEY}",
                "Content-Type": "application/json"
            },
            method="POST"
        )
        with urllib.request.urlopen(req) as resp:
            print(f"[Email] SendGrid success: {resp.status}")
            return {"status": "sent", "message": f"Alert sent to {HEADOFFICE_EMAIL} via SendGrid"}
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        print(f"[Email] SendGrid error: {e.code} - {error_body}")
        return {"status": "error", "message": f"SendGrid error: {e.code} - {error_body}"}
    except Exception as e:
        print(f"[Email] SendGrid exception: {e}")
        return {"status": "error", "message": str(e)}


# ── Send via Gmail SMTP (local fallback) ──────────────────
def _send_via_gmail(subject: str, html_body: str) -> dict:
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = SENDER_EMAIL
        msg["To"]      = HEADOFFICE_EMAIL
        msg.attach(MIMEText(html_body, "html"))
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as server:
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, HEADOFFICE_EMAIL, msg.as_string())
        return {"status": "sent", "message": f"Alert sent to {HEADOFFICE_EMAIL} via Gmail"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ── Smart send ────────────────────────────────────────────
def _send_email(subject: str, html_body: str) -> dict:
    # Try SendGrid first (works on Railway)
    result = _send_via_sendgrid(subject, html_body)
    if result["status"] == "sent":
        return result
    # Fallback to Gmail (works locally)
    print("[Email] SendGrid failed, trying Gmail...")
    return _send_via_gmail(subject, html_body)


# ── Build stock HTML ──────────────────────────────────────
def _build_stock_html(low_items):
    now = datetime.now().strftime("%d %b %Y, %I:%M %p")
    by_store = {}
    for item in low_items:
        by_store.setdefault(item["store_name"], []).append(item)
    store_blocks = ""
    for store, items in sorted(by_store.items()):
        rows = "".join(f"<tr><td style='padding:8px;border-bottom:1px solid #eee'>{i['item_name']}</td><td style='padding:8px;border-bottom:1px solid #eee'>{i['category']}</td><td style='padding:8px;border-bottom:1px solid #eee;color:#c0392b;font-weight:bold'>{i['current_stock']}</td><td style='padding:8px;border-bottom:1px solid #eee'>{i['threshold']}</td><td style='padding:8px;border-bottom:1px solid #eee;color:#e67e22'>+{round(i['threshold']-i['current_stock'],2)}</td></tr>" for i in items)
        store_blocks += f"<div style='margin-bottom:20px'><div style='background:#1a6b3c;color:white;padding:10px 16px;font-weight:bold'>Store: {store} — {len(items)} item(s)</div><table style='width:100%;border-collapse:collapse;border:1px solid #ddd'><tr style='background:#f8f9fa'><th style='padding:8px;text-align:left'>Item</th><th style='padding:8px;text-align:left'>Category</th><th style='padding:8px;text-align:left'>Stock</th><th style='padding:8px;text-align:left'>Threshold</th><th style='padding:8px;text-align:left'>Deficit</th></tr>{rows}</table></div>"
    return f"<html><body style='font-family:Arial;padding:20px'><div style='max-width:700px;margin:auto'><div style='background:#1a6b3c;padding:20px;border-radius:8px 8px 0 0'><h1 style='color:white;margin:0'>Rainbow Grocery - Low Stock Alert</h1><p style='color:rgba(255,255,255,0.8);margin:5px 0 0'>{now}</p></div><div style='background:#fdecea;padding:15px 20px'><span style='font-size:24px;font-weight:bold;color:#c0392b'>{len(low_items)}</span> <span style='color:#666'>Low Stock Items</span></div><div style='padding:20px;background:white'>{store_blocks}</div><div style='background:#e8f5ee;padding:15px;text-align:center;border-radius:0 0 8px 8px'><p style='margin:0;color:#1a6b3c;font-size:13px'>Automated alert from Rainbow Inventory System</p></div></div></body></html>"


# ── Build sales HTML ──────────────────────────────────────
def _build_sales_html(low_items, month):
    now = datetime.now().strftime("%d %b %Y, %I:%M %p")
    by_store = {}
    for item in low_items:
        by_store.setdefault(item["store_name"], []).append(item)
    store_blocks = ""
    for store, items in sorted(by_store.items()):
        rows = "".join(f"<tr><td style='padding:8px;border-bottom:1px solid #eee'>{i['article_name']}</td><td style='padding:8px;border-bottom:1px solid #eee'>{i['category']}</td><td style='padding:8px;border-bottom:1px solid #eee;color:#c0392b;font-weight:bold'>{i['quantity']}</td><td style='padding:8px;border-bottom:1px solid #eee'>{i['threshold']}</td><td style='padding:8px;border-bottom:1px solid #eee;color:#e67e22'>+{i['deficit']}</td></tr>" for i in items)
        store_blocks += f"<div style='margin-bottom:20px'><div style='background:#1a5fa8;color:white;padding:10px 16px;font-weight:bold'>Store: {store} — {len(items)} item(s)</div><table style='width:100%;border-collapse:collapse;border:1px solid #ddd'><tr style='background:#f8f9fa'><th style='padding:8px;text-align:left'>Article</th><th style='padding:8px;text-align:left'>Category</th><th style='padding:8px;text-align:left'>Qty Sold</th><th style='padding:8px;text-align:left'>Threshold</th><th style='padding:8px;text-align:left'>Deficit</th></tr>{rows}</table></div>"
    return f"<html><body style='font-family:Arial;padding:20px'><div style='max-width:700px;margin:auto'><div style='background:#1a5fa8;padding:20px;border-radius:8px 8px 0 0'><h1 style='color:white;margin:0'>Rainbow Grocery - Low Sales Alert</h1><p style='color:rgba(255,255,255,0.8);margin:5px 0 0'>{now} — {month}</p></div><div style='background:#e8f0fb;padding:15px 20px'><span style='font-size:24px;font-weight:bold;color:#1a5fa8'>{len(low_items)}</span> <span style='color:#666'>Low Sales Items</span></div><div style='padding:20px;background:white'>{store_blocks}</div><div style='background:#e8f0fb;padding:15px;text-align:center;border-radius:0 0 8px 8px'><p style='margin:0;color:#1a5fa8;font-size:13px'>Automated alert from Rainbow Inventory System</p></div></div></body></html>"


# ── Public functions ──────────────────────────────────────
def send_low_stock_email(low_items):
    if not low_items:
        return {"status": "skipped", "message": "No low stock items", "items_reported": 0}
    result = _send_email(f"Low Stock Alert - {len(low_items)} items ({datetime.now().strftime('%d %b %Y')})", _build_stock_html(low_items))
    result["items_reported"] = len(low_items)
    return result

def send_low_sales_email(low_items, month):
    if not low_items:
        return {"status": "skipped", "message": "No low sales items", "items_reported": 0}
    result = _send_email(f"Low Sales Alert - {len(low_items)} items ({month})", _build_sales_html(low_items, month))
    result["items_reported"] = len(low_items)
    return result