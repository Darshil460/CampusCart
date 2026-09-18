from flask import Flask, render_template, redirect, url_for, flash, request
import sqlite3

app = Flask(__name__)
app.secret_key = "campus_cart_secret_key"


# ---------------------------------------------------
# DATABASE CONNECTION
# ---------------------------------------------------
def get_db_connection():
    conn = sqlite3.connect("campus_cart.db")
    conn.row_factory = sqlite3.Row
    return conn


# ---------------------------------------------------
# HOME PAGE
# ---------------------------------------------------
@app.route("/")
def home():

    conn = get_db_connection()

    # Products + inventory
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

    # Current shopping list quantities
    cart_rows = conn.execute("""
        SELECT product_id, shop_id, quantity
        FROM cart
    """).fetchall()

    conn.close()

    cart = {}
    for row in cart_rows:
        cart[(row["product_id"], row["shop_id"])] = row["quantity"]

    products = {}

    for row in rows:

        product_id = row["product_id"]

        if product_id not in products:
            products[product_id] = {
                "product_name": row["product_name"],
                "category": row["category"],
                "shops": []
            }

        quantity = cart.get((row["product_id"], row["shop_id"]), 0)

        if row["shop_name"] is not None:
            products[product_id]["shops"].append({
                "product_id": row["product_id"],
                "shop_id": row["shop_id"],
                "shop_name": row["shop_name"],
                "price": row["price"],
                "stock": row["stock"],
                "quantity": quantity
            })

    # Cheapest available shop first
    for product in products.values():
        product["shops"].sort(
            key=lambda shop: (
                shop["stock"] == 0,
                shop["price"]
            )
        )

    return render_template(
        "index.html",
        products=products.values()
    )


# ---------------------------------------------------
# HOMEPAGE + BUTTON
# ---------------------------------------------------
@app.route("/cart/increase/<int:product_id>/<int:shop_id>")
def increase_cart(product_id, shop_id):

    conn = get_db_connection()

    existing = conn.execute("""
        SELECT quantity
        FROM cart
        WHERE product_id = ? AND shop_id = ?
    """, (product_id, shop_id)).fetchone()

    if existing:

        conn.execute("""
            UPDATE cart
            SET quantity = quantity + 1
            WHERE product_id = ? AND shop_id = ?
        """, (product_id, shop_id))

    else:

        conn.execute("""
            INSERT INTO cart(product_id, shop_id, quantity)
            VALUES (?, ?, 1)
        """, (product_id, shop_id))

    conn.commit()
    conn.close()

    return redirect(url_for("home"))


# ---------------------------------------------------
# HOMEPAGE - BUTTON
# ---------------------------------------------------
@app.route("/cart/decrease/<int:product_id>/<int:shop_id>")
def decrease_cart(product_id, shop_id):

    conn = get_db_connection()

    row = conn.execute("""
        SELECT quantity
        FROM cart
        WHERE product_id = ? AND shop_id = ?
    """, (product_id, shop_id)).fetchone()

    if row:

        if row["quantity"] > 1:

            conn.execute("""
                UPDATE cart
                SET quantity = quantity - 1
                WHERE product_id = ? AND shop_id = ?
            """, (product_id, shop_id))

        else:

            conn.execute("""
                DELETE FROM cart
                WHERE product_id = ? AND shop_id = ?
            """, (product_id, shop_id))

    conn.commit()
    conn.close()

    return redirect(url_for("home"))


# ---------------------------------------------------
# REQUEST OUT OF STOCK ITEM
# ---------------------------------------------------
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


# ---------------------------------------------------
# REQUEST PRODUCT NOT IN CATALOGUE
# ---------------------------------------------------
@app.route("/request_custom", methods=["POST"])
def request_custom():

    product_name = request.form["product_name"].strip()

    if product_name == "":
        flash("Please enter a product name.")
        return redirect(url_for("home"))

    conn = get_db_connection()

    conn.execute("""
        INSERT INTO requests(custom_product)
        VALUES (?)
    """, (product_name,))

    conn.commit()
    conn.close()

    flash(f'"{product_name}" has been requested successfully!')

    return redirect(url_for("home"))


# ---------------------------------------------------
# MY SHOPPING LIST PAGE
# ---------------------------------------------------
@app.route("/list")
def shopping_list():

    conn = get_db_connection()

    rows = conn.execute("""
        SELECT
            cart.product_id,
            cart.shop_id,
            cart.quantity,
            inventory.price,
            products.name AS product_name,
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

    shops = {}

    for row in rows:

        shop_name = row["shop_name"]

        if shop_name not in shops:
            shops[shop_name] = {
                "items": [],
                "total": 0
            }

        subtotal = row["price"] * row["quantity"]

        shops[shop_name]["items"].append({
            "product_id": row["product_id"],
            "shop_id": row["shop_id"],
            "product_name": row["product_name"],
            "price": row["price"],
            "quantity": row["quantity"],
            "subtotal": subtotal
        })

        shops[shop_name]["total"] += subtotal

    grand_total = sum(shop["total"] for shop in shops.values())

    return render_template(
        "list.html",
        shops=shops,
        grand_total=grand_total
    )


# ---------------------------------------------------
# LIST PAGE + BUTTON
# ---------------------------------------------------
@app.route("/list/increase/<int:product_id>/<int:shop_id>")
def list_increase(product_id, shop_id):

    conn = get_db_connection()

    conn.execute("""
        UPDATE cart
        SET quantity = quantity + 1
        WHERE product_id = ? AND shop_id = ?
    """, (product_id, shop_id))

    conn.commit()
    conn.close()

    return redirect(url_for("shopping_list"))


# ---------------------------------------------------
# LIST PAGE - BUTTON
# ---------------------------------------------------
@app.route("/list/decrease/<int:product_id>/<int:shop_id>")
def list_decrease(product_id, shop_id):

    conn = get_db_connection()

    row = conn.execute("""
        SELECT quantity
        FROM cart
        WHERE product_id = ? AND shop_id = ?
    """, (product_id, shop_id)).fetchone()

    if row:

        if row["quantity"] > 1:

            conn.execute("""
                UPDATE cart
                SET quantity = quantity - 1
                WHERE product_id = ? AND shop_id = ?
            """, (product_id, shop_id))

        else:

            conn.execute("""
                DELETE FROM cart
                WHERE product_id = ? AND shop_id = ?
            """, (product_id, shop_id))

    conn.commit()
    conn.close()

    return redirect(url_for("shopping_list"))


# ---------------------------------------------------
# REMOVE ITEM COMPLETELY FROM LIST
# ---------------------------------------------------
@app.route("/list/remove/<int:product_id>/<int:shop_id>")
def remove_item(product_id, shop_id):

    conn = get_db_connection()

    conn.execute("""
        DELETE FROM cart
        WHERE product_id = ? AND shop_id = ?
    """, (product_id, shop_id))

    conn.commit()
    conn.close()

    return redirect(url_for("shopping_list"))


# ---------------------------------------------------
# RUN APP
# ---------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True)