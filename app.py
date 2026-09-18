from flask import Flask, render_template
import sqlite3

app = Flask(__name__)


# Connect to database
def get_db_connection():
    conn = sqlite3.connect("campus_cart.db")
    conn.row_factory = sqlite3.Row
    return conn


@app.route("/")
def home():
    conn = get_db_connection()

    rows = conn.execute("""
        SELECT
            products.id,
            products.name AS product_name,
            products.category,
            shops.name AS shop_name,
            inventory.price,
            inventory.stock
        FROM products
        LEFT JOIN inventory
            ON products.id = inventory.product_id
        LEFT JOIN shops
            ON inventory.shop_id = shops.id
        ORDER BY products.id, shops.id
    """).fetchall()

    conn.close()

    # Group rows by product
    products = {}

    for row in rows:
        product_id = row["id"]

        if product_id not in products:
            products[product_id] = {
                "product_name": row["product_name"],
                "category": row["category"],
                "shops": []
            }

        if row["shop_name"] is not None:
            products[product_id]["shops"].append({
                "shop_name": row["shop_name"],
                "price": row["price"],
                "stock": row["stock"]
            })

    return render_template(
        "index.html",
        products=products.values()
    )


if __name__ == "__main__":
    app.run(debug=True)