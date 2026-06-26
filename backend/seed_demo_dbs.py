"""
Seed script - creates demo SQLite databases for testing.
Run: python seed_demo_dbs.py
"""
import sqlite3
import os
import random
from datetime import datetime, timedelta

os.makedirs("demo_databases", exist_ok=True)

# ─── E-Commerce Database ──────────────────────────────────────────────────────
def seed_ecommerce():
    conn = sqlite3.connect("demo_databases/ecommerce.db")
    c = conn.cursor()
    c.executescript("""
    CREATE TABLE IF NOT EXISTS customers (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        city TEXT,
        country TEXT,
        joined_date DATE,
        total_spent REAL DEFAULT 0
    );
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        category TEXT,
        price REAL NOT NULL,
        stock INTEGER DEFAULT 0,
        rating REAL
    );
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY,
        customer_id INTEGER REFERENCES customers(id),
        order_date DATE,
        status TEXT DEFAULT 'pending',
        total_amount REAL,
        shipping_city TEXT
    );
    CREATE TABLE IF NOT EXISTS order_items (
        id INTEGER PRIMARY KEY,
        order_id INTEGER REFERENCES orders(id),
        product_id INTEGER REFERENCES products(id),
        quantity INTEGER,
        unit_price REAL
    );
    """)

    cities = ["Delhi", "Mumbai", "Bangalore", "Chennai", "Hyderabad", "Pune", "Kolkata"]
    customers = [
        (i, f"Customer {i}", f"customer{i}@email.com",
         random.choice(cities), "India",
         (datetime.now() - timedelta(days=random.randint(30, 1000))).strftime("%Y-%m-%d"),
         round(random.uniform(500, 50000), 2))
        for i in range(1, 51)
    ]
    c.executemany("INSERT OR IGNORE INTO customers VALUES (?,?,?,?,?,?,?)", customers)

    categories = ["Electronics", "Clothing", "Books", "Home", "Sports"]
    products = [
        (i, f"Product {i}", random.choice(categories),
         round(random.uniform(100, 5000), 2), random.randint(0, 200),
         round(random.uniform(3.0, 5.0), 1))
        for i in range(1, 31)
    ]
    c.executemany("INSERT OR IGNORE INTO products VALUES (?,?,?,?,?,?)", products)

    statuses = ["pending", "shipped", "delivered", "cancelled"]
    orders = [
        (i, random.randint(1, 50),
         (datetime.now() - timedelta(days=random.randint(1, 365))).strftime("%Y-%m-%d"),
         random.choice(statuses), round(random.uniform(200, 10000), 2),
         random.choice(cities))
        for i in range(1, 101)
    ]
    c.executemany("INSERT OR IGNORE INTO orders VALUES (?,?,?,?,?,?)", orders)

    items = [
        (i, random.randint(1, 100), random.randint(1, 30),
         random.randint(1, 5), round(random.uniform(100, 5000), 2))
        for i in range(1, 201)
    ]
    c.executemany("INSERT OR IGNORE INTO order_items VALUES (?,?,?,?,?)", items)

    conn.commit()
    conn.close()
    print("✓ Ecommerce DB seeded")


# ─── University Database ──────────────────────────────────────────────────────
def seed_university():
    conn = sqlite3.connect("demo_databases/university.db")
    c = conn.cursor()
    c.executescript("""
    CREATE TABLE IF NOT EXISTS departments (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        head_professor TEXT
    );
    CREATE TABLE IF NOT EXISTS professors (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        department_id INTEGER REFERENCES departments(id),
        email TEXT,
        salary REAL
    );
    CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        email TEXT UNIQUE,
        department_id INTEGER REFERENCES departments(id),
        enrollment_year INTEGER,
        cgpa REAL
    );
    CREATE TABLE IF NOT EXISTS courses (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        code TEXT UNIQUE,
        department_id INTEGER REFERENCES departments(id),
        credits INTEGER,
        professor_id INTEGER REFERENCES professors(id)
    );
    CREATE TABLE IF NOT EXISTS enrollments (
        id INTEGER PRIMARY KEY,
        student_id INTEGER REFERENCES students(id),
        course_id INTEGER REFERENCES courses(id),
        grade TEXT,
        semester TEXT
    );
    """)

    depts = [(1, "Computer Science", "Dr. Sharma"), (2, "Mathematics", "Dr. Gupta"),
             (3, "Physics", "Dr. Verma"), (4, "Electronics", "Dr. Singh")]
    c.executemany("INSERT OR IGNORE INTO departments VALUES (?,?,?)", depts)

    professors = [(i, f"Prof. {['Sharma','Gupta','Verma','Singh','Kumar'][i%5]} {i}",
                   (i % 4) + 1, f"prof{i}@university.edu",
                   round(random.uniform(60000, 120000), 2)) for i in range(1, 16)]
    c.executemany("INSERT OR IGNORE INTO professors VALUES (?,?,?,?,?)", professors)

    students = [(i, f"Student {i}", f"student{i}@uni.edu",
                 (i % 4) + 1, random.choice([2021, 2022, 2023, 2024]),
                 round(random.uniform(5.0, 10.0), 2)) for i in range(1, 101)]
    c.executemany("INSERT OR IGNORE INTO students VALUES (?,?,?,?,?,?)", students)

    courses = [(i, f"Course {i}", f"CS{100+i}", (i % 4) + 1,
                random.choice([2, 3, 4]), random.randint(1, 15)) for i in range(1, 21)]
    c.executemany("INSERT OR IGNORE INTO courses VALUES (?,?,?,?,?,?)", courses)

    grades = ["A", "A+", "B", "B+", "C", "C+", "D", "F"]
    semesters = ["2023-ODD", "2023-EVEN", "2024-ODD"]
    enrollments = [(i, random.randint(1, 100), random.randint(1, 20),
                    random.choice(grades), random.choice(semesters)) for i in range(1, 301)]
    c.executemany("INSERT OR IGNORE INTO enrollments VALUES (?,?,?,?,?)", enrollments)

    conn.commit()
    conn.close()
    print("✓ University DB seeded")


# ─── HR Database ─────────────────────────────────────────────────────────────
def seed_hr():
    conn = sqlite3.connect("demo_databases/hr.db")
    c = conn.cursor()
    c.executescript("""
    CREATE TABLE IF NOT EXISTS departments (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        budget REAL
    );
    CREATE TABLE IF NOT EXISTS employees (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        email TEXT UNIQUE,
        department_id INTEGER REFERENCES departments(id),
        designation TEXT,
        salary REAL,
        join_date DATE,
        manager_id INTEGER REFERENCES employees(id),
        is_active INTEGER DEFAULT 1
    );
    CREATE TABLE IF NOT EXISTS attendance (
        id INTEGER PRIMARY KEY,
        employee_id INTEGER REFERENCES employees(id),
        date DATE,
        status TEXT,
        hours_worked REAL
    );
    CREATE TABLE IF NOT EXISTS performance_reviews (
        id INTEGER PRIMARY KEY,
        employee_id INTEGER REFERENCES employees(id),
        review_date DATE,
        rating INTEGER,
        comments TEXT
    );
    """)

    depts = [(1,"Engineering",5000000),(2,"Marketing",2000000),
             (3,"Sales",3000000),(4,"HR",1000000),(5,"Finance",2500000)]
    c.executemany("INSERT OR IGNORE INTO departments VALUES (?,?,?)", depts)

    designations = ["Junior Engineer","Senior Engineer","Manager","Director","VP","Intern"]
    employees = [(i, f"Employee {i}", f"emp{i}@company.com",
                  (i % 5) + 1, random.choice(designations),
                  round(random.uniform(30000, 200000), 2),
                  (datetime.now() - timedelta(days=random.randint(30, 3650))).strftime("%Y-%m-%d"),
                  random.randint(1, 10) if i > 10 else None, 1)
                 for i in range(1, 61)]
    c.executemany("INSERT OR IGNORE INTO employees VALUES (?,?,?,?,?,?,?,?,?)", employees)

    att_statuses = ["present","absent","half-day","leave"]
    attendance = [(i, random.randint(1, 60),
                   (datetime.now() - timedelta(days=random.randint(0, 90))).strftime("%Y-%m-%d"),
                   random.choice(att_statuses), round(random.uniform(0, 9), 1))
                  for i in range(1, 501)]
    c.executemany("INSERT OR IGNORE INTO attendance VALUES (?,?,?,?,?)", attendance)

    reviews = [(i, random.randint(1, 60),
                (datetime.now() - timedelta(days=random.randint(0, 365))).strftime("%Y-%m-%d"),
                random.randint(1, 5), "Performance review comment")
               for i in range(1, 121)]
    c.executemany("INSERT OR IGNORE INTO performance_reviews VALUES (?,?,?,?,?)", reviews)

    conn.commit()
    conn.close()
    print("✓ HR DB seeded")


if __name__ == "__main__":
    seed_ecommerce()
    seed_university()
    seed_hr()
    print("\nAll demo databases seeded successfully!")
