from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
import os
import re
# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8')

app = Flask(__name__)
CORS(app)

# Database configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'database': os.getenv('DB_NAME', 'calculator_db'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', 'sobyv2005'),
    'port': os.getenv('DB_PORT', '5432')
}

def get_db_connection():
    """Create and return a database connection"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        print(f"Database connection error: {e}")
        return None

def init_db():
    """Initialize the database and create tables if they don't exist"""
    conn = get_db_connection()
    if conn:
        try:
            cur = conn.cursor()
            cur.execute('''
                CREATE TABLE IF NOT EXISTS calculations (
                    id SERIAL PRIMARY KEY,
                    expression VARCHAR(255) NOT NULL,
                    result VARCHAR(255) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()
            cur.close()
            print("Database initialized successfully")
        except Exception as e:
            print(f"Error initializing database: {e}")
        finally:
            conn.close()

def safe_eval(expression):
    """Safely evaluate mathematical expressions"""
    # Remove any characters that aren't numbers, operators, or decimal points
    allowed_chars = re.compile(r'^[0-9+\-*/.() ]+$')
    
    if not allowed_chars.match(expression):
        raise ValueError("Invalid characters in expression")
    
    # Replace division by zero check
    try:
        result = eval(expression, {"__builtins__": {}}, {})
        return result
    except ZeroDivisionError:
        raise ValueError("Division by zero")
    except Exception as e:
        raise ValueError(f"Invalid expression: {str(e)}")

@app.route('/')
def index():
    """Serve the HTML frontend"""
    with open('index.html', 'r', encoding='utf-8') as f:

        return f.read()

@app.route('/api/calculate', methods=['POST'])
def calculate():
    """Calculate the result of an expression and save to database"""
    try:
        data = request.get_json()
        expression = data.get('expression', '')
        
        if not expression:
            return jsonify({'error': 'No expression provided'}), 400
        
        # Calculate the result
        result = safe_eval(expression)
        
        # Save to database
        conn = get_db_connection()
        if conn:
            try:
                cur = conn.cursor()
                cur.execute(
                    'INSERT INTO calculations (expression, result) VALUES (%s, %s)',
                    (expression, str(result))
                )
                conn.commit()
                cur.close()
            except Exception as e:
                print(f"Error saving to database: {e}")
            finally:
                conn.close()
        
        return jsonify({
            'expression': expression,
            'result': result
        })
    
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': 'Calculation error'}), 500

@app.route('/api/history', methods=['GET'])
def get_history():
    """Get calculation history from database"""
    try:
        conn = get_db_connection()
        if conn:
            try:
                cur = conn.cursor(cursor_factory=RealDictCursor)
                cur.execute(
                    'SELECT id, expression, result, created_at FROM calculations ORDER BY created_at DESC LIMIT 10'
                )
                history = cur.fetchall()
                cur.close()
                
                # Convert datetime to string for JSON serialization
                for item in history:
                    if 'created_at' in item:
                        item['created_at'] = item['created_at'].isoformat()
                
                return jsonify({'history': history})
            except Exception as e:
                print(f"Error fetching history: {e}")
                return jsonify({'history': []})
            finally:
                conn.close()
        else:
            return jsonify({'history': []})
    
    except Exception as e:
        return jsonify({'error': 'Error fetching history'}), 500

@app.route('/api/history', methods=['DELETE'])
def clear_history():
    """Clear all calculation history"""
    try:
        conn = get_db_connection()
        if conn:
            try:
                cur = conn.cursor()
                cur.execute('DELETE FROM calculations')
                conn.commit()
                cur.close()
                return jsonify({'message': 'History cleared successfully'})
            except Exception as e:
                print(f"Error clearing history: {e}")
                return jsonify({'error': 'Error clearing history'}), 500
            finally:
                conn.close()
    except Exception as e:
        return jsonify({'error': 'Error clearing history'}), 500

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)