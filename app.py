from flask import Flask, render_template, redirect, url_for, flash
import sqlite3

app = Flask(__name__)

# Needed for flash messages
app.secret_key = "campus_cart_secret_key"


def get_db_connection():
    conn = sqlite3.connect("campus_cart.db")
    conn.row_factory = sqlite3.Row
    return conn


@app.route("/")
def home():

    conn = get_db_connection()

    rows = conn.execute("""
        SELECT
            products.id AS product_id,
            products.name AS product_name,
            products.category,
            shops.id AS shop_id,
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

    products = {}

    for row in rows:

        product_id = row["product_id"]

        if product_id not in products:
            products[product_id] = {
                "product_name": row["product_name"],
                "category": row["category"],
                "shops": []
            }

        if row["shop_name"] is not None:
            products[product_id]["shops"].append({
                "shop_name": row["shop_name"],
                "shop_id": row["shop_id"],
                "price": row["price"],
                "stock": row["stock"],
                "product_id": row["product_id"]
            })

    return render_template(
        "index.html",
        products=products.values()
    )


@app.route("/request/<int:product_id>/<int:shop_id>")
def request_item(product_id, shop_id):

    conn = get_db_connection()

    # Prevent duplicate pending requests
    existing = conn.execute("""
        SELECT *
        FROM requests
        WHERE product_id = ?
        AND shop_id = ?
        AND status = 'Pending'
    """, (product_id, shop_id)).fetchone()

    if existing is None:

        conn.execute("""
            INSERT INTO requests(product_id, shop_id)
            VALUES (?, ?)
        """, (product_id, shop_id))

        conn.commit()

        flash("Request submitted successfully!")

    else:
        flash("Request already submitted.")

    conn.close()

    return redirect(url_for("home"))


if __name__ == "__main__":
    app.run(debug=True)