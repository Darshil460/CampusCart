from flask import Flask, render_template, redirect, url_for, flash
import sqlite3

app = Flask(__name__)
app.secret_key = "campus_cart_secret_key"


# -----------------------------------
# DATABASE CONNECTION
# -----------------------------------
def get_db_connection():
    conn = sqlite3.connect("campus_cart.db")
    conn.row_factory = sqlite3.Row
    return conn


# -----------------------------------
# HOME PAGE
# -----------------------------------
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
            inventory.stock,

            COALESCE(cart.quantity, 0) AS quantity,
            cart.id AS cart_id

        FROM products

        LEFT JOIN inventory
            ON products.id = inventory.product_id

        LEFT JOIN shops
            ON inventory.shop_id = shops.id

        LEFT JOIN cart
            ON cart.product_id = products.id
           AND cart.shop_id = shops.id

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
                "product_id": row["product_id"],

                # NEW FOR COUNTER
                "quantity": row["quantity"],
                "cart_id": row["cart_id"]
            })

    return render_template(
        "index.html",
        products=products.values()
    )


# -----------------------------------
# ADD ITEM TO CART
# -----------------------------------
@app.route("/add/<int:product_id>/<int:shop_id>")
def add_to_list(product_id, shop_id):

    conn = get_db_connection()

    existing = conn.execute("""
        SELECT *
        FROM cart
        WHERE product_id = ?
        AND shop_id = ?
    """, (product_id, shop_id)).fetchone()

    if existing:

        conn.execute("""
            UPDATE cart
            SET quantity = quantity + 1
            WHERE id = ?
        """, (existing["id"],))

        flash("Quantity Updated!")

    else:

        conn.execute("""
            INSERT INTO cart(product_id, shop_id, quantity)
            VALUES (?, ?, 1)
        """, (product_id, shop_id))

        flash("Added to Shopping List!")

    conn.commit()
    conn.close()

    return redirect(url_for("home"))


# -----------------------------------
# SHOPPING LIST PAGE
# -----------------------------------
@app.route("/list")
def shopping_list():

    conn = get_db_connection()

    rows = conn.execute("""
        SELECT
            cart.id AS cart_id,
            cart.quantity,

            products.name AS product_name,

            inventory.price,

            shops.name AS shop_name

        FROM cart

        JOIN products
            ON cart.product_id = products.id

        JOIN shops
            ON cart.shop_id = shops.id

        JOIN inventory
            ON inventory.product_id = cart.product_id
           AND inventory.shop_id = cart.shop_id

        ORDER BY shops.name, products.name
    """).fetchall()

    conn.close()

    grouped_cart = {}
    grand_total = 0

    for row in rows:

        shop = row["shop_name"]

        if shop not in grouped_cart:
            grouped_cart[shop] = {
                "items": [],
                "store_total": 0
            }

        total_price = row["price"] * row["quantity"]

        grouped_cart[shop]["items"].append({
            "cart_id": row["cart_id"],
            "product_name": row["product_name"],
            "price": row["price"],
            "quantity": row["quantity"],
            "total_price": total_price
        })

        grouped_cart[shop]["store_total"] += total_price
        grand_total += total_price

    return render_template(
        "list.html",
        grouped_cart=grouped_cart,
        grand_total=grand_total
    )


# -----------------------------------
# INCREASE QUANTITY
# -----------------------------------
@app.route("/increase/<int:cart_id>")
def increase(cart_id):

    conn = get_db_connection()

    conn.execute("""
        UPDATE cart
        SET quantity = quantity + 1
        WHERE id = ?
    """, (cart_id,))

    conn.commit()
    conn.close()

    return redirect(url_for("home"))


# -----------------------------------
# DECREASE QUANTITY
# -----------------------------------
@app.route("/decrease/<int:cart_id>")
def decrease(cart_id):

    conn = get_db_connection()

    item = conn.execute("""
        SELECT quantity
        FROM cart
        WHERE id = ?
    """, (cart_id,)).fetchone()

    if item["quantity"] > 1:

        conn.execute("""
            UPDATE cart
            SET quantity = quantity - 1
            WHERE id = ?
        """, (cart_id,))

    else:

        conn.execute("""
            DELETE FROM cart
            WHERE id = ?
        """, (cart_id,))

    conn.commit()
    conn.close()

    return redirect(url_for("home"))


# -----------------------------------
# REMOVE ITEM FROM SHOPPING LIST
# -----------------------------------
@app.route("/remove/<int:cart_id>")
def remove(cart_id):

    conn = get_db_connection()

    conn.execute("""
        DELETE FROM cart
        WHERE id = ?
    """, (cart_id,))

    conn.commit()
    conn.close()

    flash("Item removed from Shopping List.")

    return redirect(url_for("shopping_list"))


# -----------------------------------
# REQUEST OUT OF STOCK ITEM
# -----------------------------------
@app.route("/request/<int:product_id>/<int:shop_id>")
def request_item(product_id, shop_id):

    conn = get_db_connection()

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


# -----------------------------------
# RUN APP
# -----------------------------------
if __name__ == "__main__":
    app.run(debug=True)