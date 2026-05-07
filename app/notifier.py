import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

# ── Config (reads from environment variables on Railway) ──
SENDER_EMAIL     = os.environ.get("SENDER_EMAIL",     "rainbowalertsystem@gmail.com")
SENDER_PASSWORD  = os.environ.get("SENDER_PASSWORD",  "plioaikmxzcjyfad")
HEADOFFICE_EMAIL = os.environ.get("HEADOFFICE_EMAIL", "sahar.noman.javed@gmail.com")


# ── Send via Gmail SMTP ───────────────────────────────────
def _send_email(subject: str, html_body: str) -> dict:
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = SENDER_EMAIL
        msg["To"]      = HEADOFFICE_EMAIL
        msg.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, HEADOFFICE_EMAIL, msg.as_string())

        return {"status": "sent", "message": f"Alert sent to {HEADOFFICE_EMAIL}"}
    except smtplib.SMTPAuthenticationError:
        return {"status": "error", "message": "Gmail authentication failed. Check App Password."}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ── Build stock alert HTML ────────────────────────────────
def _build_stock_html(low_items: list) -> str:
    now = datetime.now().strftime("%d %b %Y, %I:%M %p")
    by_store = {}
    for item in low_items:
        s = item["store_name"]
        if s not in by_store:
            by_store[s] = []
        by_store[s].append(item)

    store_blocks = ""
    for store, items in sorted(by_store.items()):
        rows = ""
        for i in items:
            deficit = round(i["threshold"] - i["current_stock"], 2)
            rows += f"""
            <tr>
              <td style="padding:10px 14px;border-bottom:1px solid #f0f0f0">{i['item_name']}</td>
              <td style="padding:10px 14px;border-bottom:1px solid #f0f0f0">{i['category']}</td>
              <td style="padding:10px 14px;border-bottom:1px solid #f0f0f0;color:#c0392b;font-weight:700">{i['current_stock']}</td>
              <td style="padding:10px 14px;border-bottom:1px solid #f0f0f0">{i['threshold']}</td>
              <td style="padding:10px 14px;border-bottom:1px solid #f0f0f0;color:#e67e22;font-weight:600">+{deficit} needed</td>
            </tr>"""

        store_blocks += f"""
        <div style="margin-bottom:28px">
          <div style="background:#1a6b3c;color:white;padding:10px 16px;border-radius:8px 8px 0 0;font-weight:700">
            Store: {store} | {len(items)} low stock item{'s' if len(items)>1 else ''}
          </div>
          <table style="width:100%;border-collapse:collapse;background:white;border:1px solid #e0e0e0">
            <thead><tr style="background:#f8f9fa">
              <th style="padding:10px 14px;text-align:left;font-size:12px;color:#6c757d">Item</th>
              <th style="padding:10px 14px;text-align:left;font-size:12px;color:#6c757d">Category</th>
              <th style="padding:10px 14px;text-align:left;font-size:12px;color:#6c757d">Stock</th>
              <th style="padding:10px 14px;text-align:left;font-size:12px;color:#6c757d">Threshold</th>
              <th style="padding:10px 14px;text-align:left;font-size:12px;color:#6c757d">Deficit</th>
            </tr></thead>
            <tbody>{rows}</tbody>
          </table>
        </div>"""

    return f"""<!DOCTYPE html><html><body style="margin:0;padding:0;background:#f0f2f5;font-family:Arial,sans-serif">
      <div style="max-width:700px;margin:30px auto">
        <div style="background:#1a6b3c;padding:28px 32px;border-radius:12px 12px 0 0">
          <h1 style="margin:0;color:white;font-size:22px">Rainbow Grocery - Low Stock Alert</h1>
          <p style="margin:6px 0 0;color:rgba(255,255,255,0.75);font-size:14px">{now}</p>
        </div>
        <div style="background:#fdecea;padding:16px 32px">
          <span style="font-size:28px;font-weight:700;color:#c0392b">{len(low_items)}</span>
          <span style="font-size:12px;color:#6c757d;margin-left:8px">LOW STOCK ITEMS</span>
        </div>
        <div style="padding:24px 32px;background:white">{store_blocks}</div>
        <div style="background:#e8f5ee;padding:16px 32px;border-radius:0 0 12px 12px;text-align:center">
          <p style="margin:0;font-size:13px;color:#1a6b3c">Automated alert from Rainbow Inventory System</p>
        </div>
      </div></body></html>"""


# ── Build sales alert HTML ────────────────────────────────
def _build_sales_html(low_items: list, month: str) -> str:
    now = datetime.now().strftime("%d %b %Y, %I:%M %p")
    by_store = {}
    for item in low_items:
        s = item["store_name"]
        if s not in by_store:
            by_store[s] = []
        by_store[s].append(item)

    store_blocks = ""
    for store, items in sorted(by_store.items()):
        rows = ""
        for i in items:
            rows += f"""
            <tr>
              <td style="padding:10px 14px;border-bottom:1px solid #f0f0f0">{i['article_name']}</td>
              <td style="padding:10px 14px;border-bottom:1px solid #f0f0f0">{i['category']}</td>
              <td style="padding:10px 14px;border-bottom:1px solid #f0f0f0;color:#c0392b;font-weight:700">{i['quantity']}</td>
              <td style="padding:10px 14px;border-bottom:1px solid #f0f0f0">{i['threshold']}</td>
              <td style="padding:10px 14px;border-bottom:1px solid #f0f0f0;color:#e67e22;font-weight:600">+{i['deficit']} needed</td>
            </tr>"""

        store_blocks += f"""
        <div style="margin-bottom:28px">
          <div style="background:#1a5fa8;color:white;padding:10px 16px;border-radius:8px 8px 0 0;font-weight:700">
            Store: {store} | {len(items)} low sales item{'s' if len(items)>1 else ''}
          </div>
          <table style="width:100%;border-collapse:collapse;background:white;border:1px solid #e0e0e0">
            <thead><tr style="background:#f8f9fa">
              <th style="padding:10px 14px;text-align:left;font-size:12px;color:#6c757d">Article</th>
              <th style="padding:10px 14px;text-align:left;font-size:12px;color:#6c757d">Category</th>
              <th style="padding:10px 14px;text-align:left;font-size:12px;color:#6c757d">Qty Sold</th>
              <th style="padding:10px 14px;text-align:left;font-size:12px;color:#6c757d">Threshold</th>
              <th style="padding:10px 14px;text-align:left;font-size:12px;color:#6c757d">Deficit</th>
            </tr></thead>
            <tbody>{rows}</tbody>
          </table>
        </div>"""

    return f"""<!DOCTYPE html><html><body style="margin:0;padding:0;background:#f0f2f5;font-family:Arial,sans-serif">
      <div style="max-width:700px;margin:30px auto">
        <div style="background:#1a5fa8;padding:28px 32px;border-radius:12px 12px 0 0">
          <h1 style="margin:0;color:white;font-size:22px">Rainbow Grocery - Low Sales Alert</h1>
          <p style="margin:6px 0 0;color:rgba(255,255,255,0.75);font-size:14px">{now} - {month}</p>
        </div>
        <div style="background:#e8f0fb;padding:16px 32px">
          <span style="font-size:28px;font-weight:700;color:#1a5fa8">{len(low_items)}</span>
          <span style="font-size:12px;color:#6c757d;margin-left:8px">LOW SALES ITEMS</span>
        </div>
        <div style="padding:24px 32px;background:white">{store_blocks}</div>
        <div style="background:#e8f0fb;padding:16px 32px;border-radius:0 0 12px 12px;text-align:center">
          <p style="margin:0;font-size:13px;color:#1a5fa8">Automated alert from Rainbow Inventory System</p>
        </div>
      </div></body></html>"""


# ── Public functions ──────────────────────────────────────
def send_low_stock_email(low_items: list) -> dict:
    if not low_items:
        return {"status": "skipped", "message": "No low stock items", "items_reported": 0}
    subject = f"Low Stock Alert - {len(low_items)} items need reorder ({datetime.now().strftime('%d %b %Y')})"
    result  = _send_email(subject, _build_stock_html(low_items))
    result["items_reported"] = len(low_items)
    return result


def send_low_sales_email(low_items: list, month: str) -> dict:
    if not low_items:
        return {"status": "skipped", "message": "No low sales items", "items_reported": 0}
    subject = f"Low Sales Alert - {len(low_items)} items below threshold ({month})"
    result  = _send_email(subject, _build_sales_html(low_items, month))
    result["items_reported"] = len(low_items)
    return result