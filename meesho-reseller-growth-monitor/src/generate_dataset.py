import csv
import os
import random
import sqlite3
from datetime import date, timedelta

SEED = 42

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")

RESELLER_FIELDS = ["reseller_id", "reseller_name", "city", "region", "join_date"]
ORDER_FIELDS = [
    "order_id", "reseller_id", "category", "product_name", "quantity",
    "unit_price", "order_date", "month", "status",
]
ORDERS_PER_MONTH = 300
RESELLERS_PER_REGION = 6


regions = {
    "North": ["Delhi", "Jaipur", "Lucknow"],
    "South": ["Bengaluru", "Chennai", "Hyderabad"],
    "East": ["Kolkata", "Patna", "Bhubaneswar"],
    "West": ["Mumbai", "Pune", "Ahmedabad"]
}

categories = [
    "Ethnic Wear",
    "Western Wear",
    "Kids Wear",
    "Home & Kitchen",
    "Beauty & Personal Care"
]

price_ranges = {
    "Ethnic Wear": (400, 2500),
    "Western Wear": (500, 2200),
    "Kids Wear": (300, 1800),
    "Home & Kitchen": (200, 3000),
    "Beauty & Personal Care": (150, 2000)
}

products = {
    "Ethnic Wear": [
        "Cotton Kurti", "Printed Kurta Set", "Anarkali Dress",
        "Designer Saree", "Cotton Saree", "Festive Lehenga"
    ],
    "Western Wear": [
        "Denim Jeans", "Casual Top", "Crop Top",
        "Women Dress", "Oversized T-Shirt", "Formal Shirt"
    ],
    "Kids Wear": [
        "Kids T-Shirt", "Kids Jeans", "Girls Frock",
        "Boys Kurta", "Kids Shorts", "Kids Party Dress"
    ],
    "Home & Kitchen": [
        "Storage Container Set", "Kitchen Organizer", "Bedsheet Set",
        "Wall Decor", "Cookware Set", "Cushion Cover Set"
    ],
    "Beauty & Personal Care": [
        "Face Wash", "Moisturizer", "Lipstick",
        "Hair Serum", "Body Lotion", "Makeup Kit"
    ]
}

statuses = ["Delivered", "Returned", "Cancelled", "Pending"]
status_weights = [0.70, 0.15, 0.10, 0.05]

category_weights = {
    "April": {
        "Ethnic Wear": 0.20,
        "Western Wear": 0.24,
        "Kids Wear": 0.20,
        "Home & Kitchen": 0.20,
        "Beauty & Personal Care": 0.16
    },
    "May": {
        "Ethnic Wear": 0.34,
        "Western Wear": 0.20,
        "Kids Wear": 0.16,
        "Home & Kitchen": 0.14,
        "Beauty & Personal Care": 0.16
    },
    "June": {
        "Ethnic Wear": 0.18,
        "Western Wear": 0.22,
        "Kids Wear": 0.20,
        "Home & Kitchen": 0.22,
        "Beauty & Personal Care": 0.18
    }
}

months = [
    ("April", date(2026, 4, 1), date(2026, 4, 30)),
    ("May", date(2026, 5, 1), date(2026, 5, 31)),
    ("June", date(2026, 6, 1), date(2026, 6, 30))
]


def build_resellers(rng):
    resellers = []
    number = 1

    for region, cities in regions.items():
        for i in range(RESELLERS_PER_REGION):
            city = cities[i % len(cities)]

            resellers.append({
                "reseller_id": f"R{number:03d}",
                "reseller_name": f"Reseller {number}",
                "city": city,
                "region": region,
                "join_date": (
                    date(2026, 1, 1) +
                    timedelta(days=rng.randint(0, 80))
                ).isoformat()
            })

            number += 1

    return resellers


def build_orders(rng, resellers):
    # The last reseller (R024) is given no orders on purpose.
    zero_order_reseller = resellers[-1]["reseller_id"]
    active_resellers = [
        r for r in resellers if r["reseller_id"] != zero_order_reseller
    ]

    orders = []
    order_number = 1

    for month, start_date, end_date in months:

        cats = list(category_weights[month].keys())
        weights = list(category_weights[month].values())

        for _ in range(ORDERS_PER_MONTH):

            reseller = rng.choice(active_resellers)

            category = rng.choices(cats, weights=weights, k=1)[0]

            product = rng.choice(products[category])

            quantity = rng.randint(1, 5)

            low, high = price_ranges[category]
            unit_price = rng.randint(low, high)

            order_date = start_date + timedelta(
                days=rng.randint(0, (end_date - start_date).days)
            )

            status = rng.choices(statuses, weights=status_weights, k=1)[0]

            orders.append({
                "order_id": f"O{order_number:04d}",
                "reseller_id": reseller["reseller_id"],
                "category": category,
                "product_name": product,
                "quantity": quantity,
                "unit_price": unit_price,
                "order_date": order_date.isoformat(),
                "month": month,
                "status": status
            })

            order_number += 1

    return orders


def write_csv_files(resellers, orders, reseller_file, orders_file):
    with open(reseller_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=RESELLER_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(resellers)

    with open(orders_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=ORDER_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(orders)


def build_database(resellers, orders, db_file):
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()

    cursor.execute("DROP TABLE IF EXISTS orders")
    cursor.execute("DROP TABLE IF EXISTS resellers")

    cursor.execute("""
        CREATE TABLE resellers (
            reseller_id TEXT PRIMARY KEY,
            reseller_name TEXT NOT NULL,
            city TEXT NOT NULL,
            region TEXT NOT NULL,
            join_date TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE orders (
            order_id TEXT PRIMARY KEY,
            reseller_id TEXT NOT NULL,
            category TEXT NOT NULL,
            product_name TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            unit_price REAL NOT NULL,
            order_date TEXT NOT NULL,
            month TEXT NOT NULL,
            status TEXT NOT NULL,
            FOREIGN KEY (reseller_id) REFERENCES resellers(reseller_id)
        )
    """)

    for r in resellers:
        cursor.execute(
            "INSERT INTO resellers VALUES (?, ?, ?, ?, ?)",
            tuple(r[field] for field in RESELLER_FIELDS),
        )

    for o in orders:
        cursor.execute(
            "INSERT INTO orders VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            tuple(o[field] for field in ORDER_FIELDS),
        )

    conn.commit()
    conn.close()


def generate_data(output_dir=DATA_DIR, verbose=True):

    rng = random.Random(SEED)

    os.makedirs(output_dir, exist_ok=True)

    reseller_file = os.path.join(output_dir, "resellers.csv")
    orders_file = os.path.join(output_dir, "orders.csv")
    db_file = os.path.join(output_dir, "meesho_reseller.db")

    resellers = build_resellers(rng)
    orders = build_orders(rng, resellers)

    write_csv_files(resellers, orders, reseller_file, orders_file)
    build_database(resellers, orders, db_file)

    if verbose:
        print(f"Created {len(resellers)} resellers and {len(orders)} orders.")
        print(f"Files saved in: {output_dir}")

    return {"resellers": len(resellers), "orders": len(orders)}


if __name__ == "__main__":
    generate_data()
