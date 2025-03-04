# backend/api.py
from flask import Flask, request, jsonify
import sqlite3
import pandas as pd
from sklearn.linear_model import LinearRegression

app = Flask(__name__)

# Database connection
def get_db_connection():
    conn = sqlite3.connect('step_tracker.db')
    conn.row_factory = sqlite3.Row
    return conn

def create_table():
    conn = get_db_connection()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS steps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,  -- Removed UNIQUE constraint
            step_count INTEGER NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

create_table() 


# Upload step count data
@app.route('/upload', methods=['POST'])
def upload_data():
    data = request.json
    date = data['date']
    step_count = data['step_count']

    conn = get_db_connection()
    conn.execute('INSERT INTO steps (date, step_count) VALUES (?, ?)', (date, step_count))
    conn.commit()
    conn.close()

    return jsonify({"message": "Data uploaded successfully!"})

# Fetch historical data
@app.route('/data', methods=['GET'])
def fetch_data():
    conn = get_db_connection()
    data = conn.execute('SELECT * FROM steps').fetchall()
    conn.close()

    return jsonify([dict(row) for row in data])

# Generate predictions
@app.route('/predict', methods=['GET'])
def predict_steps():
    conn = get_db_connection()
    df = pd.read_sql_query('SELECT date, step_count FROM steps', conn)
    conn.close()

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