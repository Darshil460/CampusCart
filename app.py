from flask import (
    Flask,
    render_template,
    redirect,
    url_for,
    flash,
    request,
    jsonify
)

import sqlite3
import qrcode
import json
import uuid
import os   

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
            # Product image mapping
            product_images = {
                "Protein Bar": "protein_bar.png",
                "Mirinda": "mirinda.png",
                "Sparkling Water - Cranberry": "sparkling_water.png",
                "Goli Soda": "goli_soda.png",
                "Chicken Fried Roll": "chicken_roll.png",
                "Scientific Calculator": "calculator.png",
                "Veg Puff": "veg_puff.png",
                "Hand Wash": "hand_wash.png",
                "Shampoo": "shampoo.png",
                "Notebook": "notebook.png",
                "Pen": "pen.png",
                "Lays": "lays.png",
                "Diet Coke": "diet_coke.png"
            }

            for product in products.values():
                product["image"] = product_images.get(
                    product["product_name"],
                    "default.png"
                )
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
        cart.shop_id,
        cart.product_id,
        products.name AS product_name,
        shops.name AS shop_name,
        inventory.price,
        cart.quantity

    FROM cart

    JOIN products
        ON cart.product_id = products.id

    JOIN shops
        ON cart.shop_id = shops.id

    JOIN inventory
        ON inventory.product_id = cart.product_id
       AND inventory.shop_id = cart.shop_id

""").fetchall()

    conn.close()

    grouped_cart = {}
    grand_total = 0

    for row in rows:

        shop = row["shop_name"]

        if shop not in grouped_cart:
            grouped_cart[shop] = {
            "shop_id": row["shop_id"],  
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


@app.route("/generate_qr/<int:shop_id>")
def generate_qr(shop_id):

    conn = get_db_connection()

    # Read only THIS shop's cart items
    rows = conn.execute("""
        SELECT
            cart.product_id,
            cart.shop_id,
            cart.quantity,

            products.name AS product_name,
            shops.name AS shop_name,

            inventory.price

        FROM cart

        JOIN products
            ON cart.product_id = products.id

        JOIN shops
            ON cart.shop_id = shops.id

        JOIN inventory
            ON inventory.product_id = cart.product_id
           AND inventory.shop_id = cart.shop_id

        WHERE cart.shop_id = ?

    """, (shop_id,)).fetchall()

    conn.close()

    if len(rows) == 0:
        flash("No items found for this shop.")
        return redirect(url_for("shopping_list"))

    transaction_id = "CC-" + uuid.uuid4().hex[:8].upper()

    shop_name = rows[0]["shop_name"]

    qr_items = []
    display_items = []
    grand_total = 0

    for row in rows:

        total = row["price"] * row["quantity"]
        grand_total += total

        qr_items.append({
            "product_id": row["product_id"],
            "product_name": row["product_name"],   # NEW
            "quantity": row["quantity"]
        })

        display_items.append({
            "product_name": row["product_name"],
            "quantity": row["quantity"],
            "price": row["price"],
            "total": total
        })

    payload = {
        "transaction_id": transaction_id,
        "shop_id": shop_id,
        "shop_name": shop_name,
        "items": qr_items
    }

    qr = qrcode.make(json.dumps(payload))

    os.makedirs("static/qrcodes", exist_ok=True)

    filename = transaction_id + ".png"

    qr.save(os.path.join("static", "qrcodes", filename))

    return render_template(
        "qr.html",
        transaction_id=transaction_id,
        shop_name=shop_name,
        shop_id=shop_id,
        qr_image=filename,
        items=display_items,
        grand_total=grand_total
    )

    conn = get_db_connection()

    # Read everything currently in the shopping cart
    rows = conn.execute("""
        SELECT
            cart.product_id,
            cart.shop_id,
            cart.quantity,

            products.name AS product_name,
            shops.name AS shop_name,

            inventory.price

        FROM cart

        JOIN products
            ON cart.product_id = products.id

        JOIN shops
            ON cart.shop_id = shops.id

        JOIN inventory
            ON inventory.product_id = cart.product_id
           AND inventory.shop_id = cart.shop_id
    """).fetchall()

    conn.close()

    # Empty cart protection
    if len(rows) == 0:
        flash("Your shopping list is empty.")
        return redirect(url_for("shopping_list"))

    transaction_id = "CC-" + uuid.uuid4().hex[:8].upper()

    qr_items = []
    display_items = []

    grand_total = 0

    for row in rows:

        total = row["price"] * row["quantity"]
        grand_total += total

        qr_items.append({
            "product_id": row["product_id"],
            "shop_id": row["shop_id"],
            "quantity": row["quantity"]
        })

        display_items.append({
            "product_name": row["product_name"],
            "shop_name": row["shop_name"],
            "quantity": row["quantity"],
            "price": row["price"],
            "total": total
        })

    payload = {
        "transaction_id": transaction_id,
        "items": qr_items
    }

    # Make QR image
    qr = qrcode.make(json.dumps(payload))

    os.makedirs("static/qrcodes", exist_ok=True)

    qr_filename = f"{transaction_id}.png"

    qr_path = os.path.join("static", "qrcodes", qr_filename)

    qr.save(qr_path)

    return render_template(
        "qr.html",
        transaction_id=transaction_id,
        qr_image=qr_filename,
        items=display_items,
        grand_total=grand_total
    )

@app.route("/shopkeeper")
def shopkeeper():
    return render_template("shopkeeper.html")


@app.route("/scanner")
def scanner():
    return render_template("scanner.html")


@app.route("/confirm_purchase", methods=["POST"])
def confirm_purchase():

    data = request.get_json()

    transaction_id = data["transaction_id"]
    shop_id = data["shop_id"]
    items = data["items"]

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        for item in items:

            product_id = item["product_id"]
            quantity = item["quantity"]

            inventory = cursor.execute("""
                SELECT price, stock
                FROM inventory
                WHERE product_id=? AND shop_id=?
            """, (product_id, shop_id)).fetchone()

            if inventory is None:
                raise Exception("Inventory item not found.")

            price = inventory["price"]
            stock = inventory["stock"]

            if stock < quantity:
                raise Exception("Not enough stock available.")

            cursor.execute("""
                UPDATE inventory
                SET stock = stock - ?
                WHERE product_id=? AND shop_id=?
            """, (quantity, product_id, shop_id))

            cursor.execute("""
                INSERT INTO sales
                (transaction_id, product_id, shop_id, quantity, total_price)
                VALUES (?, ?, ?, ?, ?)
            """, 
            (
                transaction_id,
                product_id,
                shop_id,
                quantity,
                price * quantity
            ))

        cursor.execute("""
            DELETE FROM cart
            WHERE shop_id = ?
            """, (shop_id,))

        conn.commit()

        return jsonify({
            "success": True,
            "message": "Purchase completed successfully! 🎉"
        })

    except Exception as e:
        conn.rollback()

        return jsonify({
            "success": False,
            "message": str(e)
        }), 400

    finally:
        conn.close()



@app.route("/inventory/<int:shop_id>")
def inventory(shop_id):

            conn = get_db_connection()

            shop = conn.execute(
                "SELECT * FROM shops WHERE id=?",
                (shop_id,)
            ).fetchone()

            shops = conn.execute(
                "SELECT * FROM shops"
            ).fetchall()

            inventory = conn.execute("""
                SELECT
                    inventory.product_id,
                    inventory.price,
                    inventory.stock,

                    products.name AS product_name,
                    products.category

                FROM inventory

                JOIN products
                    ON inventory.product_id = products.id

                WHERE inventory.shop_id = ?

                ORDER BY products.category, products.name
            """, (shop_id,)).fetchall()

            conn.close()

            return render_template(
                "inventory.html",
                shop=shop,
                shops=shops,
                inventory=inventory
            )


@app.route("/update_stock", methods=["POST"])
def update_stock():

    shop_id = request.form["shop_id"]
    product_id = request.form["product_id"]
    stock = request.form["stock"]

    conn = get_db_connection()

    conn.execute("""
        UPDATE inventory
        SET stock = ?
        WHERE shop_id=? AND product_id=?
    """, (stock, shop_id, product_id))

    conn.commit()
    conn.close()

    flash("Stock updated successfully.")

    return redirect(url_for("inventory", shop_id=shop_id))



@app.route("/update_price", methods=["POST"])
def update_price():

    shop_id = request.form["shop_id"]
    product_id = request.form["product_id"]
    price = request.form["price"]

    conn = get_db_connection()

    conn.execute("""
        UPDATE inventory
        SET price = ?
        WHERE shop_id=? AND product_id=?
    """, (price, shop_id, product_id))

    conn.commit()
    conn.close()

    flash("Price updated successfully.")

    return redirect(url_for("inventory", shop_id=shop_id))

@app.route("/requests/<int:shop_id>")
def requests_page(shop_id):

    conn = get_db_connection()

    shop = conn.execute(
        "SELECT * FROM shops WHERE id=?",
        (shop_id,)
    ).fetchone()

    shops = conn.execute(
        "SELECT * FROM shops"
    ).fetchall()

    requests = conn.execute("""
        SELECT
            requests.shop_id,
            requests.product_id,
            COUNT(*) AS request_count,

            shops.name AS shop_name,
            products.name AS product_name,
            products.category

        FROM requests

        JOIN shops
            ON requests.shop_id = shops.id

        JOIN products
            ON requests.product_id = products.id

        WHERE requests.shop_id = ?

        GROUP BY requests.shop_id, requests.product_id

        ORDER BY request_count DESC
    """, (shop_id,)).fetchall()

    conn.close()

    return render_template(
        "requests.html",
        requests=requests,
        shop=shop,
        shops=shops
    )

@app.route("/fulfill_request", methods=["POST"])
def fulfill_request():

    shop_id = request.form["shop_id"]
    product_id = request.form["product_id"]

    conn = get_db_connection()

    # Delete all requests for this product from this shop
    conn.execute("""
        DELETE FROM requests
        WHERE shop_id = ? AND product_id = ?
    """, (shop_id, product_id))

    conn.commit()
    conn.close()

    flash("Request marked as fulfilled.")

    return redirect(
    url_for("requests_page", shop_id=shop_id)
    )



# -----------------------------------
# RUN APP
# -----------------------------------
if __name__ == "__main__":
    app.run(debug=True)