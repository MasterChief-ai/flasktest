from flask import Flask, jsonify, request
import sqlite3
import hashlib
import os
import dotenv
import wraps

dotenv.load_dotenv()
API_TOKEN = os.getenv("API_TOKEN")

app = Flask(__name__)

def require_token(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get("Authorization")
        if token != f"Bearer {API_TOKEN}":
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated_function

def get_db_connection():
    conn = sqlite3.connect("products.db") #opens up a connection to the db or creats it if it doesn't exist.
    conn.row_factory = sqlite3.Row #This allows us to access columns by name instead of index
    return conn


@app.route("/init", methods=["GET"])
def init_db():
    conn = get_db_connection()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price REAL NOT NULL
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()
    return jsonify({"message": "Database initialized successfully"})

@app.route('/') #allows to connect a URL path to a function
def home():
    return jsonify({"message": "Welcome to the Deez Nuts!"})


@app.route("/products", methods=["GET"])
@require_token
def get_products():
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM products").fetchall()
    conn.close()
    return jsonify([dict(row) for row in rows])

@app.route("/products", methods=["POST"])
def add_product():
    data = request.get_json()
    name = data.get("name")
    price = data.get("price")
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO products (name, price) VALUES (?, ?)", (name, price))
    conn.commit()
    new_id = cursor.lastrowid
    
    new_product = {
        "id": new_id,
        "name": name,
        "price": price
    }
    conn.close()
    return jsonify({"message": "Product added successfully", "product": new_product}), 201

@app.route("/register", methods=["POST"])
def register():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")
    if not username or not password:
        return jsonify({"error": "Missing username or password"}), 400
    # Hash the password before storing it
    hashed_password = hashlib.sha256(password.encode()).hexdigest()
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed_password))
        conn.commit()
        conn.close()
        return jsonify({"message": "User registered successfully"}), 201
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({"error": "Username already exists"}), 409

@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")
    if not username or not password:
        return jsonify({"error": "Missing username or password"}), 400
    hashed_password = hashlib.sha256(password.encode()).hexdigest()
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, hashed_password)).fetchone()
    conn.close()
    if user:
        return jsonify({"message": "Login successful"}), 200
    else:
        return jsonify({"error": "Invalid Credentials"}), 401

if __name__ == '__main__': #this means that the code will only run if this file is executed directly, not if it is imported elsewhere
    with app.app_context():
        init_db()  # Initialize the database automatically
    app.run(debug=True)