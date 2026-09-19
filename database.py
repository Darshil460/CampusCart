import sqlite3

# Connect to database (creates it if it doesn't exist)
conn = sqlite3.connect("campus_cart.db")
cursor = conn.cursor()

# -----------------------------
# SHOPS TABLE
# -----------------------------
cursor.execute("""
CREATE TABLE IF NOT EXISTS shops (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
)
""")

# -----------------------------
# PRODUCTS TABLE
# -----------------------------
cursor.execute("""
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT NOT NULL
)
""")

# -----------------------------
# INVENTORY TABLE
# -----------------------------
cursor.execute("""
CREATE TABLE IF NOT EXISTS inventory (
    shop_id INTEGER,
    product_id INTEGER,
    stock INTEGER NOT NULL,
    price INTEGER NOT NULL,

    PRIMARY KEY (shop_id, product_id),

    FOREIGN KEY (shop_id) REFERENCES shops(id),
    FOREIGN KEY (product_id) REFERENCES products(id)
)
""")

# -----------------------------
# REQUESTS TABLE (NEW)
# -----------------------------
cursor.execute("""
CREATE TABLE IF NOT EXISTS requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    product_id INTEGER,
    shop_id INTEGER,

    custom_product TEXT,

    status TEXT DEFAULT 'Pending',
    requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (product_id) REFERENCES products(id),
    FOREIGN KEY (shop_id) REFERENCES shops(id)
)
""")
# -----------------------------
# CART TABLE
# -----------------------------
cursor.execute("""
CREATE TABLE IF NOT EXISTS cart (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    product_id INTEGER NOT NULL,
    shop_id INTEGER NOT NULL,

    quantity INTEGER DEFAULT 1,

    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (product_id) REFERENCES products(id),
    FOREIGN KEY (shop_id) REFERENCES shops(id)
)
""")
# =====================================================
# INSERT SHOPS
# =====================================================
shops = [
    (1, "Enzo"),
    (2, "Q-Block"),
    (3, "Balaji")
]

cursor.executemany(
    "INSERT OR IGNORE INTO shops VALUES (?, ?)",
    shops
)

# =====================================================
# INSERT PRODUCTS
# =====================================================
products = [
    (1, "Protein Bar", "Food"),
    (2, "Mirinda", "Beverage"),
    (3, "Sparkling Water - Cranberry", "Beverage"),
    (4, "Goli Soda", "Beverage"),
    (5, "Chicken Fried Roll", "Food"),
    (6, "Scientific Calculator", "Stationery"),
    (7, "Veg Puff", "Food"),
    (8, "Hand Wash", "Personal Care"),
    (9, "Shampoo", "Personal Care"),
    (10, "Notebook", "Stationery"),
    (11, "Pen", "Stationery"),
]

cursor.executemany(
    "INSERT OR IGNORE INTO products VALUES (?, ?, ?)",
    products
)

# =====================================================
# INSERT INVENTORY
# =====================================================
inventory = [

    # Enzo
    (1, 1, 10, 55),
    (1, 2, 10, 40),
    (1, 3, 10, 50),
    (1, 4, 10, 30),
    (1, 5, 10, 70),
    (1, 7, 10, 25),
    (1, 9, 10, 120),

    # Q-Block
    (2, 1, 0, 50),
    (2, 2, 10, 40),
    (2, 5, 10, 65),
    (2, 7, 0, 25),
    (2, 8, 10, 90),

    # Balaji
    (3, 1, 10, 52),
    (3, 2, 10, 42),
    (3, 6, 10, 450),
    (3, 10, 10, 60),
    (3, 11, 10, 10)
]

cursor.executemany(
    "INSERT OR IGNORE INTO inventory VALUES (?, ?, ?, ?)",
    inventory
)

# -----------------------------
# SALES TABLE
# -----------------------------
cursor.execute("""
CREATE TABLE IF NOT EXISTS sales (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    transaction_id TEXT NOT NULL,

    product_id INTEGER NOT NULL,
    shop_id INTEGER NOT NULL,

    quantity INTEGER NOT NULL,
    total_price REAL NOT NULL,

    purchased_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY(product_id) REFERENCES products(id),
    FOREIGN KEY(shop_id) REFERENCES shops(id)
)
""")

# Save changes
conn.commit()
conn.close()

print("Campus Cart database created/updated successfully!")