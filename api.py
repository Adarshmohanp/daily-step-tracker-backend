from flask import Flask, request, jsonify
import sqlite3
import pandas as pd
from sklearn.linear_model import LinearRegression
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

# Database connection
def get_db_connection():
    conn = sqlite3.connect('step_tracker.db')
    conn.row_factory = sqlite3.Row
    return conn

def create_tables():
    conn = get_db_connection()
    try:
        # Create users table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        ''')
        # Create steps table with user_id as a foreign key
        conn.execute('''
            CREATE TABLE IF NOT EXISTS steps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                step_count INTEGER NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        conn.commit()
    except Exception as e:
        print(f"Error creating tables: {e}")
    finally:
        conn.close()

# Ensure tables are created when the app starts
create_tables()

# User registration
@app.route('/register', methods=['POST'])
def register():
    data = request.json
    username = data['username']
    password = generate_password_hash(data['password'])

    conn = get_db_connection()
    try:
        conn.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, password))
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({"message": "Username already exists!"}), 400
    conn.close()
    return jsonify({"message": "User registered successfully!"})

# User login
@app.route('/login', methods=['POST'])
def login():
    data = request.json
    username = data['username']
    password = data['password']

    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
    conn.close()

    if user and check_password_hash(user['password'], password):
        return jsonify({"message": "Login successful!", "user_id": user['id']})
    else:
        return jsonify({"message": "Invalid username or password!"}), 401

# Upload step count data
@app.route('/upload', methods=['POST'])
def upload_data():
    data = request.json
    user_id = data.get('user_id')
    date = data.get('date')
    step_count = data.get('step_count')

    if not user_id or not date or not step_count:
        return jsonify({"message": "Missing required fields!"}), 400

    conn = get_db_connection()
    try:
        conn.execute(
            'INSERT INTO steps (user_id, date, step_count) VALUES (?, ?, ?)',
            (user_id, date, step_count)
        )
        conn.commit()
        conn.close()
        return jsonify({"message": "Data uploaded successfully!"})
    except Exception as e:
        conn.close()
        return jsonify({"message": f"Failed to upload data: {str(e)}"}), 500

# Fetch historical data
@app.route('/data', methods=['GET'])
def fetch_data():
    user_id = request.args.get('user_id')
    conn = get_db_connection()
    data = conn.execute('SELECT * FROM steps WHERE user_id = ?', (user_id,)).fetchall()
    conn.close()

    return jsonify([dict(row) for row in data])

# Generate predictions
@app.route('/predict', methods=['GET'])
def predict_steps():
    user_id = request.args.get('user_id')
    conn = get_db_connection()
    df = pd.read_sql_query('SELECT date, step_count FROM steps WHERE user_id = ?', conn, params=(user_id,))
    conn.close()

    if df.empty:
        return jsonify({"predictions": []})

    df['days'] = (pd.to_datetime(df['date']) - pd.to_datetime(df['date']).min()).dt.days
    X = df[['days']]
    y = df['step_count']

    model = LinearRegression()
    model.fit(X, y)

    future_days = [[df['days'].max() + i] for i in range(1, 8)]
    future_steps = model.predict(future_days)

    return jsonify({"predictions": future_steps.tolist()})

# Run the Flask app
if __name__ == '__main__':
    app.run(debug=True)