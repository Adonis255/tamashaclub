import os
import uuid
import logging
from datetime import datetime
from flask import Flask, request, jsonify, render_template, session, url_for
from flask_cors import CORS
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv(dotenv_path='.env')

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder='static', template_folder='templates')
app.secret_key = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
CORS(app)

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

supabase = None
if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        logger.info("Supabase client initialized.")
    except Exception as e:
        logger.error(f"Supabase init failed: {e}")

ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'tamasha2025')
INACTIVITY_TIMEOUT = 300  # 5 minutes

# ---------- Helper functions ----------
def admin_required():
    if 'admin' not in session:
        return False
    last_activity = session.get('last_activity')
    if last_activity:
        last_time = datetime.fromisoformat(last_activity)
        if (datetime.now() - last_time).total_seconds() > INACTIVITY_TIMEOUT:
            session.clear()
            return False
    session['last_activity'] = datetime.now().isoformat()
    return True

def get_category_name(category_id):
    if supabase:
        try:
            result = supabase.table('categories').select('name').eq('id', category_id).execute()
            if result.data:
                return result.data[0]['name']
        except Exception as e:
            logger.error(f"Error getting category name: {e}")
    return "Uncategorized"

# ---------- Public routes ----------
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/drinks')
def get_drinks():
    search = request.args.get('search', '').strip().lower()
    category = request.args.get('category', '').strip()

    if not supabase:
        return jsonify([]), 500

    try:
        query = supabase.table('drinks').select('*, categories(name)')
        if category:
            query = query.eq('categories.name', category)
        if search:
            query = query.or_(f"name.ilike.%{search}%, description.ilike.%{search}%")
        data = query.execute().data
        for d in data:
            d['category_name'] = d.pop('categories', {}).get('name', 'Uncategorized')
        return jsonify(data)
    except Exception as e:
        logger.error(f"Supabase error in get_drinks: {e}")
        return jsonify([]), 500

@app.route('/api/categories')
def get_categories():
    if not supabase:
        return jsonify([]), 500
    try:
        # Only categories that have drinks
        data = supabase.table('categories').select('*').execute().data
        # Get drink category IDs
        drinks = supabase.table('drinks').select('category_id').execute().data
        cat_ids = set(d['category_id'] for d in drinks if d['category_id'])
        filtered = [c for c in data if c['id'] in cat_ids]
        return jsonify(filtered)
    except Exception as e:
        logger.error(f"Supabase error in get_categories: {e}")
        return jsonify([]), 500

# ---------- Admin routes ----------
@app.route('/admin')
def admin():
    if not admin_required():
        return render_template('admin.html', logged_in=False)
    return render_template('admin.html', logged_in=True)

@app.route('/admin/login', methods=['POST'])
def admin_login():
    data = request.get_json()
    password = data.get('password')
    if password == ADMIN_PASSWORD:
        session['admin'] = True
        session['last_activity'] = datetime.now().isoformat()
        return jsonify({'success': True})
    return jsonify({'success': False}), 401

@app.route('/admin/logout', methods=['POST'])
def admin_logout():
    session.clear()
    return jsonify({'success': True})

# ---------- File upload (unchanged) ----------
@app.route('/admin/upload-image', methods=['POST'])
def upload_image():
    if not admin_required():
        return jsonify({'error': 'Unauthorized'}), 401
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    if not supabase:
        return jsonify({'error': 'Supabase not configured'}), 500

    ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
    unique_name = f"{uuid.uuid4()}.{ext}"
    file_content = file.read()

    try:
        supabase.storage.from_('drink-images').upload(
            unique_name,
            file_content,
            file_options={"content-type": file.content_type}
        )
        public_url = supabase.storage.from_('drink-images').get_public_url(unique_name)
        return jsonify({'url': public_url})
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        return jsonify({'error': str(e)}), 500

# ---------- Admin CRUD (using Supabase) ----------
@app.route('/admin/drinks', methods=['GET'])
def admin_get_drinks():
    if not admin_required():
        return jsonify({'error': 'Unauthorized'}), 401
    if not supabase:
        return jsonify([]), 500
    try:
        response = supabase.table('drinks').select('*, categories(name)').execute()
        drinks = response.data
        for d in drinks:
            d['category_name'] = d.pop('categories', {}).get('name', 'Uncategorized')
        return jsonify(drinks)
    except Exception as e:
        logger.error(f"Admin get drinks error: {e}")
        return jsonify([]), 500

@app.route('/admin/drinks', methods=['POST'])
def admin_add_drink():
    if not admin_required():
        return jsonify({'error': 'Unauthorized'}), 401
    if not supabase:
        return jsonify({'error': 'Supabase not configured'}), 500

    data = request.get_json()
    required = ['name', 'price', 'description', 'image_url', 'category_id']
    if not all(k in data for k in required):
        return jsonify({'error': 'Missing fields'}), 400

    # If image_url is empty, set placeholder
    if not data['image_url'] or data['image_url'].strip() == '':
        data['image_url'] = f"https://via.placeholder.com/400x300/1a120e/d4af37?text={data['name'][:10]}"

    try:
        result = supabase.table('drinks').insert(data).execute()
        return jsonify(result.data[0]), 201
    except Exception as e:
        logger.error(f"Add drink error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/admin/drinks/<int:drink_id>', methods=['PUT'])
def admin_edit_drink(drink_id):
    if not admin_required():
        return jsonify({'error': 'Unauthorized'}), 401
    if not supabase:
        return jsonify({'error': 'Supabase not configured'}), 500

    data = request.get_json()
    # Remove any fields that shouldn't be updated (like id)
    try:
        result = supabase.table('drinks').update(data).eq('id', drink_id).execute()
        if result.data:
            return jsonify(result.data[0])
        else:
            return jsonify({'error': 'Drink not found'}), 404
    except Exception as e:
        logger.error(f"Edit drink error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/admin/drinks/<int:drink_id>', methods=['DELETE'])
def admin_delete_drink(drink_id):
    if not admin_required():
        return jsonify({'error': 'Unauthorized'}), 401
    if not supabase:
        return jsonify({'error': 'Supabase not configured'}), 500

    try:
        # First delete the drink
        supabase.table('drinks').delete().eq('id', drink_id).execute()
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Delete drink error: {e}")
        return jsonify({'error': str(e)}), 500

# ---------- Admin CRUD for categories ----------
@app.route('/admin/categories', methods=['GET'])
def admin_get_categories():
    if not admin_required():
        return jsonify({'error': 'Unauthorized'}), 401
    if not supabase:
        return jsonify([]), 500
    try:
        response = supabase.table('categories').select('*').execute()
        return jsonify(response.data)
    except Exception as e:
        logger.error(f"Get categories error: {e}")
        return jsonify([]), 500

@app.route('/admin/categories', methods=['POST'])
def admin_add_category():
    if not admin_required():
        return jsonify({'error': 'Unauthorized'}), 401
    if not supabase:
        return jsonify({'error': 'Supabase not configured'}), 500

    data = request.get_json()
    if 'name' not in data:
        return jsonify({'error': 'Missing name'}), 400

    try:
        result = supabase.table('categories').insert(data).execute()
        return jsonify(result.data[0]), 201
    except Exception as e:
        logger.error(f"Add category error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/admin/categories/<int:cat_id>', methods=['PUT'])
def admin_edit_category(cat_id):
    if not admin_required():
        return jsonify({'error': 'Unauthorized'}), 401
    if not supabase:
        return jsonify({'error': 'Supabase not configured'}), 500

    data = request.get_json()
    try:
        result = supabase.table('categories').update(data).eq('id', cat_id).execute()
        if result.data:
            return jsonify(result.data[0])
        else:
            return jsonify({'error': 'Category not found'}), 404
    except Exception as e:
        logger.error(f"Edit category error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/admin/categories/<int:cat_id>', methods=['DELETE'])
def admin_delete_category(cat_id):
    if not admin_required():
        return jsonify({'error': 'Unauthorized'}), 401
    if not supabase:
        return jsonify({'error': 'Supabase not configured'}), 500

    try:
        # Optional: set category_id to NULL for drinks before deleting
        # supabase.table('drinks').update({'category_id': None}).eq('category_id', cat_id).execute()
        supabase.table('categories').delete().eq('id', cat_id).execute()
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Delete category error: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)