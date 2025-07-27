import os
import json
import requests
import logging
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash

# Set up logging
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__, template_folder='views', static_folder='public')
app.secret_key = os.environ.get("SESSION_SECRET", "pixel_secret_key_for_development")

# File paths
USERS_FILE = 'users.json'

def load_users():
    """Load users from JSON file"""
    try:
        with open(USERS_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {"users": []}
    except json.JSONDecodeError:
        logging.error(f"Error decoding {USERS_FILE}")
        return {"users": []}

def save_users(users_data):
    """Save users to JSON file"""
    try:
        with open(USERS_FILE, 'w') as f:
            json.dump(users_data, f, indent=2)
    except Exception as e:
        logging.error(f"Error saving users: {e}")

def find_user(username):
    """Find user by username"""
    users_data = load_users()
    for user in users_data.get("users", []):
        if user["username"] == username:
            return user
    return None

@app.route('/')
def index():
    """Redirect to dashboard if logged in, otherwise to login"""
    if 'username' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Handle login"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        if not username or not password:
            flash('Please fill in all fields', 'error')
            return render_template('login.html')
        
        user = find_user(username)
        if user and check_password_hash(user['password_hash'], password):
            session['username'] = username
            flash('Welcome back, pixel warrior!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid credentials. Try again!', 'error')
    
    return render_template('login.html')

@app.route('/register', methods=['POST'])
def register():
    """Handle user registration"""
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '')
    
    if not username or not password:
        flash('Please fill in all fields', 'error')
        return redirect(url_for('login'))
    
    if len(username) < 3:
        flash('Username must be at least 3 characters', 'error')
        return redirect(url_for('login'))
    
    if len(password) < 6:
        flash('Password must be at least 6 characters', 'error')
        return redirect(url_for('login'))
    
    # Check if user already exists
    if find_user(username):
        flash('Username already exists', 'error')
        return redirect(url_for('login'))
    
    # Create new user
    users_data = load_users()
    new_user = {
        "username": username,
        "password_hash": generate_password_hash(password)
    }
    
    users_data["users"].append(new_user)
    save_users(users_data)
    
    session['username'] = username
    flash('Account created successfully! Welcome!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
def dashboard():
    """Dashboard page - requires login"""
    if 'username' not in session:
        flash('Please log in first', 'error')
        return redirect(url_for('login'))
    
    return render_template('dashboard.html', username=session['username'])

@app.route('/logout')
def logout():
    """Handle logout"""
    session.pop('username', None)
    flash('Logged out successfully', 'success')
    return redirect(url_for('login'))

@app.route('/api/send-like', methods=['POST'])
def send_like():
    """API endpoint to send likes"""
    if 'username' not in session:
        return jsonify({"error": "Not authenticated"}), 401
    
    data = request.get_json()
    uid = data.get('uid', '').strip()
    
    if not uid:
        return jsonify({"error": "UID is required"}), 400
    
    if not uid.isdigit() or len(uid) < 6:
        return jsonify({"error": "Invalid UID format"}), 400
    
    try:
        # Make request to like API
        api_key = os.environ.get("VORTEX_API_KEY", "p9R2tV5yB7uE1wK3jM5nQ7sP4vR6tY8")
        api_url = f"https://vortexapi.up.railway.app/like?uid={uid}&api_key={api_key}"
        
        response = requests.get(api_url, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            return jsonify({
                "success": True,
                "message": "Like sent successfully!",
                "data": result
            })
        elif response.status_code == 404:
            return jsonify({
                "success": False,
                "error": "Player not found"
            }), 404
        elif response.status_code == 429:
            return jsonify({
                "success": False,
                "error": "Rate limit exceeded. Please try again later."
            }), 429
        else:
            return jsonify({
                "success": False,
                "error": f"API returned status code: {response.status_code}"
            }), 500
            
    except requests.exceptions.Timeout:
        return jsonify({
            "success": False,
            "error": "Request timed out. Please try again."
        }), 500
    except requests.exceptions.RequestException as e:
        logging.error(f"API request error: {e}")
        return jsonify({
            "success": False,
            "error": "Failed to connect to API"
        }), 500

@app.route('/api/view-profile', methods=['POST'])
def view_profile():
    """API endpoint to view player profile"""
    if 'username' not in session:
        return jsonify({"error": "Not authenticated"}), 401
    
    data = request.get_json()
    uid = data.get('uid', '').strip()
    
    if not uid:
        return jsonify({"error": "UID is required"}), 400
    
    if not uid.isdigit() or len(uid) < 6:
        return jsonify({"error": "Invalid UID format"}), 400
    
    try:
        # Make request to profile API
        api_url = f"https://glob-info.vercel.app/info?uid={uid}"
        
        response = requests.get(api_url, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            return jsonify({
                "success": True,
                "data": result
            })
        elif response.status_code == 404:
            return jsonify({
                "success": False,
                "error": "Player not found"
            }), 404
        else:
            return jsonify({
                "success": False,
                "error": f"API returned status code: {response.status_code}"
            }), 500
            
    except requests.exceptions.Timeout:
        return jsonify({
            "success": False,
            "error": "Request timed out. Please try again."
        }), 500
    except requests.exceptions.RequestException as e:
        logging.error(f"Profile API request error: {e}")
        return jsonify({
            "success": False,
            "error": "Failed to connect to API"
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
