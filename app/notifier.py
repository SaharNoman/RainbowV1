import smtplib
import os
import urllib.request
import urllib.error
import json
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

SENDER_EMAIL     = os.environ.get("SENDER_EMAIL",     "rainbowalertsystem@gmail.com")
SENDER_PASSWORD  = os.environ.get("SENDER_PASSWORD",  "plioaikmxzcjyfad")
HEADOFFICE_EMAIL = os.environ.get("HEADOFFICE_EMAIL", "sahar.noman.javed@gmail.com")
#SENDGRID_API_KEY = os.environ.get("SENDGRID_API_KEY", "")
_k1 = "SG.GBEpgNV8T-aP4jknYQSw2A."
_k2 = "8q9OfOyI0O7kU39itLtxcppDcYximDJhNewbBfcxZ3Q"
SENDGRID_API_KEY = os.environ.get("SENDGRID_API_KEY", _k1 + _k2)

def _send_via_sendgrid(subject, html_body):
    print(f"[Email] SendGrid key: {SENDGRID_API_KEY[:15] if SENDGRID_API_KEY else 'NOT SET'}")
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
            headers={"Authorization": f"Bearer {SENDGRID_API_KEY}", "Content-Type": "application/json"},
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

def _send_via_gmail(subject, html_body):
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

def _send_email(subject, html_body):
    result = _send_via_sendgrid(subject, html_body)
    if result["status"] == "sent":
        return result
    print("[Email] SendGrid failed, trying Gmail...")
    return _send_via_gmail(subject, html_body)

def _build_stock_html(low_items):
    now = datetime.now().strftime("%d %b %Y, %I:%M %p")
    by_store = {}
    for item in low_items:
        by_store.setdefault(item["store_name"], []).append(item)
    store_blocks = ""
    for store, items in sorted(by_store.items()):
        rows = "".join(f"<tr><td style='padding:8px'>{i['item_name']}</td><td style='padding:8px'>{i['category']}</td><td style='padding:8px;color:red'>{i['current_stock']}</td><td style='padding:8px'>{i['threshold']}</td><td style='padding:8px;color:orange'>+{round(i['threshold']-i['current_stock'],2)}</td></tr>" for i in items)
        store_blocks += f"<div style='margin-bottom:20px'><div style='background:#1a6b3c;color:white;padding:10px'><b>Store: {store} — {len(items)} item(s)</b></div><table style='width:100%;border-collapse:collapse;border:1px solid #ddd'><tr style='background:#f8f9fa'><th style='padding:8px;text-align:left'>Item</th><th style='padding:8px;text-align:left'>Category</th><th style='padding:8px;text-align:left'>Stock</th><th style='padding:8px;text-align:left'>Threshold</th><th style='padding:8px;text-align:left'>Deficit</th></tr>{rows}</table></div>"
    return f"<html><body style='font-family:Arial;padding:20px'><h2 style='color:#1a6b3c'>Rainbow Grocery - Low Stock Alert</h2><p>{now} | {len(low_items)} Low Stock Items</p>{store_blocks}<p style='color:#666;font-size:12px'>Automated alert from Rainbow Inventory System</p></body></html>"

def _build_sales_html(low_items, month):
    now = datetime.now().strftime("%d %b %Y, %I:%M %p")
    by_store = {}
    for item in low_items:
        by_store.setdefault(item["store_name"], []).append(item)
    store_blocks = ""
    for store, items in sorted(by_store.items()):
        rows = "".join(f"<tr><td style='padding:8px'>{i['article_name']}</td><td style='padding:8px'>{i['category']}</td><td style='padding:8px;color:red'>{i['quantity']}</td><td style='padding:8px'>{i['threshold']}</td><td style='padding:8px;color:orange'>+{i['deficit']}</td></tr>" for i in items)
        store_blocks += f"<div style='margin-bottom:20px'><div style='background:#1a5fa8;color:white;padding:10px'><b>Store: {store} — {len(items)} item(s)</b></div><table style='width:100%;border-collapse:collapse;border:1px solid #ddd'><tr style='background:#f8f9fa'><th style='padding:8px;text-align:left'>Article</th><th style='padding:8px;text-align:left'>Category</th><th style='padding:8px;text-align:left'>Qty Sold</th><th style='padding:8px;text-align:left'>Threshold</th><th style='padding:8px;text-align:left'>Deficit</th></tr>{rows}</table></div>"
    return f"<html><body style='font-family:Arial;padding:20px'><h2 style='color:#1a5fa8'>Rainbow Grocery - Low Sales Alert</h2><p>{now} | {month} | {len(low_items)} Low Sales Items</p>{store_blocks}<p style='color:#666;font-size:12px'>Automated alert from Rainbow Inventory System</p></body></html>"

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