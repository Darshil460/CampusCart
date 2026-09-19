import sqlite3


# Connect to the database

connection = sqlite3.connect("campus_cart.db")

cursor = connection.cursor()


# Get product, shop and stock

cursor.execute("""
    SELECT
        products.name,
        shops.name,
        inventory.stock

    FROM inventory

    JOIN products
        ON inventory.product_id = products.id

    JOIN shops
        ON inventory.shop_id = shops.id
""")

cursor.execute("PRAGMA table_info(sales)")
print(cursor.fetchall())
# Get all results

rows = cursor.fetchall()


# Display the results

for product, shop, stock in rows:

    if stock > 0:

        print(f"{product} | {shop} | {stock} available")

    else:

        print(f"{product} | {shop} | OUT OF STOCK")


# Close the connection

connection.close()