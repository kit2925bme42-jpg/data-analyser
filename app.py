from flask import Flask, render_template, request, redirect, url_for
import sqlite3
import json
from datetime import datetime

app = Flask(__name__)

# ---------- MENU ----------
MENU = [
    {"id": 1, "name": "Spicy Chicken Burger", "price": 149},
    {"id": 2, "name": "Crispy Chicken Strips (3pcs)", "price": 129},
    {"id": 3, "name": "Popcorn Chicken (Large)", "price": 99},
    {"id": 4, "name": "French Fries", "price": 79},
    {"id": 5, "name": "Veg Zinger Burger", "price": 139},
    {"id": 6, "name": "Chicken Bucket (6pcs)", "price": 399},
    {"id": 7, "name": "Coleslaw (Side)", "price": 49},
    {"id": 8, "name": "Soft Drink (Pepsi)", "price": 40}
]

# ---------- DATABASE SETUP ----------
def init_db():
    conn = sqlite3.connect('rcb_orders.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS orders
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  order_time TEXT,
                  items_json TEXT,
                  total REAL)''')
    conn.commit()
    conn.close()

def save_order(order_items, grand_total):
    """Save an order to the database."""
    conn = sqlite3.connect('rcb_orders.db')
    c = conn.cursor()
    order_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    items_json = json.dumps(order_items)
    c.execute("INSERT INTO orders (order_time, items_json, total) VALUES (?,?,?)",
              (order_time, items_json, grand_total))
    conn.commit()
    conn.close()

def get_all_orders():
    """Fetch all orders from database."""
    conn = sqlite3.connect('rcb_orders.db')
    c = conn.cursor()
    c.execute("SELECT id, order_time, items_json, total FROM orders ORDER BY id")
    rows = c.fetchall()
    orders = []
    for row in rows:
        orders.append({
            "id": row[0],
            "order_time": row[1],
            "items": json.loads(row[2]),
            "total": row[3]
        })
    conn.close()
    return orders

def get_recent_orders(limit=5):
    """Fetch most recent orders."""
    conn = sqlite3.connect('rcb_orders.db')
    c = conn.cursor()
    c.execute("SELECT id, order_time, total FROM orders ORDER BY id DESC LIMIT ?", (limit,))
    rows = c.fetchall()
    recent = [{"id": r[0], "order_time": r[1], "total": r[2]} for r in rows]
    conn.close()
    return recent

def compute_analytics():
    """Analyze the dataset (all orders)."""
    orders = get_all_orders()
    if not orders:
        return {
            "total_orders": 0,
            "total_revenue": 0,
            "avg_order_value": 0,
            "total_items_sold": 0,
            "top_items": [],
            "item_revenue": {}
        }

    total_revenue = sum(o["total"] for o in orders)
    total_orders = len(orders)
    avg_order_value = total_revenue / total_orders if total_orders > 0 else 0

    # Item-level statistics
    item_qty = {}
    item_rev = {}
    for order in orders:
        for item in order["items"]:
            name = item["name"]
            qty = item["quantity"]
            subtotal = item["subtotal"]
            item_qty[name] = item_qty.get(name, 0) + qty
            item_rev[name] = item_rev.get(name, 0) + subtotal

    total_items_sold = sum(item_qty.values())
    # Top 3 items by quantity
    top_items = sorted(item_qty.items(), key=lambda x: x[1], reverse=True)[:3]

    return {
        "total_orders": total_orders,
        "total_revenue": round(total_revenue, 2),
        "avg_order_value": round(avg_order_value, 2),
        "total_items_sold": total_items_sold,
        "top_items": top_items,
        "item_revenue": {k: round(v, 2) for k, v in item_rev.items()}
    }

# ---------- FLASK ROUTES ----------
@app.route("/", methods=["GET", "POST"])
def index():
    error = None
    bill_details = None
    analytics = compute_analytics()
    recent_orders = get_recent_orders()

    if request.method == "POST":
        # Collect quantities from form
        order_items = []
        subtotal = 0

        for item in MENU:
            qty_str = request.form.get(f"qty_{item['id']}", "0")
            try:
                qty = int(qty_str)
            except ValueError:
                qty = 0

            if qty > 0:
                line_subtotal = qty * item["price"]
                subtotal += line_subtotal
                order_items.append({
                    "name": item["name"],
                    "quantity": qty,
                    "unit_price": item["price"],
                    "subtotal": line_subtotal
                })

        if not order_items:
            error = "Please select at least one item with quantity greater than 0."
        else:
            # Apply tax (5% GST)
            tax_rate = 0.05
            tax = subtotal * tax_rate
            grand_total = subtotal + tax

            # Create bill details for display
            bill_details = {
                "items": order_items,
                "subtotal": subtotal,
                "tax": round(tax, 2),
                "grand_total": round(grand_total, 2),
                "tax_rate": int(tax_rate * 100)
            }

            # Save order to database for analysis
            save_order(order_items, grand_total)

            # Re-fetch analytics after saving the new order
            analytics = compute_analytics()
            recent_orders = get_recent_orders()

    return render_template("index.html",
                           menu=MENU,
                           bill=bill_details,
                           analytics=analytics,
                           recent_orders=recent_orders,
                           error=error)

if __name__ == "__main__":
    init_db()
    app.run(debug=True)