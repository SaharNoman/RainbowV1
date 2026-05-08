import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

SENDER_EMAIL     = os.environ.get("SENDER_EMAIL",     "rainbowalertsystem@gmail.com")
SENDER_PASSWORD  = os.environ.get("SENDER_PASSWORD",  "plioaikmxzcjyfad")
HEADOFFICE_EMAIL = os.environ.get("HEADOFFICE_EMAIL", "sahar.noman.javed@gmail.com")

def _send_email(subject: str, html_body: str) -> dict:
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = SENDER_EMAIL
        msg["To"]      = HEADOFFICE_EMAIL
        msg.attach(MIMEText(html_body, "html"))
        sent = False
        last_error = None

        try:
            with smtplib.SMTP("smtp.gmail.com", 587, timeout=30) as server:
                server.ehlo()
                server.starttls()
                server.login(SENDER_EMAIL, SENDER_PASSWORD)
                server.sendmail(SENDER_EMAIL, HEADOFFICE_EMAIL, msg.as_string())
                sent = True
                print("[Email] Sent via port 587")
        except Exception as e:
            last_error = str(e)
            print(f"[Email] Port 587 failed: {e}")

        if not sent:
            try:
                with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as server:
                    server.login(SENDER_EMAIL, SENDER_PASSWORD)
                    server.sendmail(SENDER_EMAIL, HEADOFFICE_EMAIL, msg.as_string())
                    sent = True
                    print("[Email] Sent via port 465")
            except Exception as e:
                last_error = str(e)
                print(f"[Email] Port 465 failed: {e}")

        if sent:
            return {"status": "sent", "message": f"Alert sent to {HEADOFFICE_EMAIL}"}
        return {"status": "error", "message": f"Both ports failed: {last_error}"}

    except Exception as e:
        return {"status": "error", "message": str(e)}

def _build_stock_html(low_items):
    now = datetime.now().strftime("%d %b %Y, %I:%M %p")
    by_store = {}
    for item in low_items:
        by_store.setdefault(item["store_name"], []).append(item)
    store_blocks = ""
    for store, items in sorted(by_store.items()):
        rows = "".join(f"<tr><td style='padding:8px'>{i['item_name']}</td><td style='padding:8px'>{i['store_name']}</td><td style='padding:8px;color:red'>{i['current_stock']}</td><td style='padding:8px'>{i['threshold']}</td></tr>" for i in items)
        store_blocks += f"<h3 style='color:#1a6b3c'>Store: {store} — {len(items)} items</h3><table border='1' style='width:100%;border-collapse:collapse'><tr><th>Item</th><th>Store</th><th>Stock</th><th>Threshold</th></tr>{rows}</table><br>"
    return f"<html><body style='font-family:Arial'><h2 style='color:#1a6b3c'>Low Stock Alert — {now}</h2><p>{len(low_items)} items below threshold</p>{store_blocks}</body></html>"

def _build_sales_html(low_items, month):
    now = datetime.now().strftime("%d %b %Y, %I:%M %p")
    by_store = {}
    for item in low_items:
        by_store.setdefault(item["store_name"], []).append(item)
    store_blocks = ""
    for store, items in sorted(by_store.items()):
        rows = "".join(f"<tr><td style='padding:8px'>{i['article_name']}</td><td style='padding:8px'>{i['store_name']}</td><td style='padding:8px;color:red'>{i['quantity']}</td><td style='padding:8px'>{i['threshold']}</td></tr>" for i in items)
        store_blocks += f"<h3 style='color:#1a5fa8'>Store: {store} — {len(items)} items</h3><table border='1' style='width:100%;border-collapse:collapse'><tr><th>Article</th><th>Store</th><th>Qty Sold</th><th>Threshold</th></tr>{rows}</table><br>"
    return f"<html><body style='font-family:Arial'><h2 style='color:#1a5fa8'>Low Sales Alert — {month} — {now}</h2><p>{len(low_items)} items below sales threshold</p>{store_blocks}</body></html>"

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