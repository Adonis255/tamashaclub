import os
import uuid
from datetime import datetime
from flask import Flask, request, jsonify, render_template, session, url_for
from flask_cors import CORS
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv(dotenv_path='.env')

print("SUPABASE_URL =", os.getenv('SUPABASE_URL'))
print("SUPABASE_KEY =", os.getenv('SUPABASE_KEY')[:10] + "..." if os.getenv('SUPABASE_KEY') else "None")

app = Flask(__name__, static_folder='static', template_folder='templates')
app.secret_key = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
CORS(app)

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

# Initialize Supabase client
supabase = None
if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    except:
        supabase = None

ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'tamasha2025')
INACTIVITY_TIMEOUT = 300

# ---------- Local upload folder (fallback) ----------
UPLOAD_FOLDER = os.path.join('static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ---------- In-memory mock data ----------
mock_drinks = [
    {"id": 1, "name": "Gordon's London Dry Gin", "price": 2800, "description": "Crisp, classic London dry gin with juniper and citrus notes.", "image_url": "https://cdn.shopify.com/s/files/1/0279/5286/6392/products/gordons-gin.jpg", "category_name": "Gin", "category_id": 1},
    {"id": 2, "name": "Johnnie Walker Black Label", "price": 4500, "description": "Smooth, smoky blended Scotch whisky with rich character.", "image_url": "https://cdn.shopify.com/s/files/1/0279/5286/6392/products/johnnie-walker-black-label.jpg", "category_name": "Whisky", "category_id": 2},
    {"id": 3, "name": "Absolut Vodka", "price": 3200, "description": "Clean, smooth Swedish vodka with a subtle grain character.", "image_url": "https://cdn.shopify.com/s/files/1/0279/5286/6392/products/absolut-vodka.jpg", "category_name": "Vodka", "category_id": 3},
    {"id": 4, "name": "Bacardi Superior Rum", "price": 3000, "description": "Light and smooth white rum, perfect for cocktails.", "image_url": "https://cdn.shopify.com/s/files/1/0279/5286/6392/products/bacardi-rum.jpg", "category_name": "Rum", "category_id": 4},
]
mock_categories = [
    {"id": 1, "name": "Gin"},
    {"id": 2, "name": "Whisky"},
    {"id": 3, "name": "Vodka"},
    {"id": 4, "name": "Rum"},
    {"id": 5, "name": "Tequila"},
    {"id": 6, "name": "Liqueur"},
]
next_drink_id = 5
next_cat_id = 7

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

# ---------- Public routes ----------
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/drinks')
def get_drinks():
    search = request.args.get('search', '').strip().lower()
    category = request.args.get('category', '').strip()

    if supabase:
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
            print("Supabase error, using mock data:", e)

    filtered = mock_drinks
    if category:
        filtered = [d for d in filtered if d['category_name'].lower() == category.lower()]
    if search:
        filtered = [d for d in filtered if search in d['name'].lower() or search in d['description'].lower()]
    return jsonify(filtered)

@app.route('/api/categories')
def get_categories():
    if supabase:
        try:
            data = supabase.table('categories').select('*').execute().data
            # only categories that have drinks
            drink_cat_ids = set(d['category_id'] for d in mock_drinks)
            filtered = [c for c in data if c['id'] in drink_cat_ids]
            return jsonify(filtered)
        except Exception as e:
            print("Supabase error, using mock categories:", e)
    drink_cat_ids = set(d['category_id'] for d in mock_drinks)
    filtered = [c for c in mock_categories if c['id'] in drink_cat_ids]
    return jsonify(filtered)

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

# ---------- File upload: Supabase Storage with local fallback ----------
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
        # Upload to Supabase Storage
        supabase.storage.from_('drink-images').upload(
            unique_name,
            file_content,
            file_options={"content-type": file.content_type}
        )
        public_url = supabase.storage.from_('drink-images').get_public_url(unique_name)
        return jsonify({'url': public_url})
    except Exception as e:
        print("Supabase upload failed:", e)
        return jsonify({'error': str(e)}), 500
    
# ---------- Admin CRUD (unchanged) ----------
@app.route('/admin/drinks', methods=['GET'])
def admin_get_drinks():
    if not admin_required():
        return jsonify({'error': 'Unauthorized'}), 401
    if supabase:
        try:
            response = supabase.table('drinks').select('*, categories(name)').execute()
            drinks = response.data
            for d in drinks:
                d['category_name'] = d.pop('categories', {}).get('name', 'Uncategorized')
            return jsonify(drinks)
        except Exception as e:
            print("Supabase error in admin get drinks:", e)
    return jsonify(mock_drinks)

@app.route('/admin/drinks', methods=['POST'])
def admin_add_drink():
    if not admin_required():
        return jsonify({'error': 'Unauthorized'}), 401
    data = request.get_json()
    required = ['name', 'price', 'description', 'image_url', 'category_id']
    if not all(k in data for k in required):
        return jsonify({'error': 'Missing fields'}), 400

    global next_drink_id, mock_drinks
    cat_name = "Uncategorized"
    for c in mock_categories:
        if c['id'] == data['category_id']:
            cat_name = c['name']
            break

    if not data['image_url'] or data['image_url'].strip() == '':
        data['image_url'] = f"https://via.placeholder.com/400x300/1a120e/d4af37?text={data['name'][:10]}"

    new_drink = {
        "id": next_drink_id,
        "name": data['name'],
        "price": data['price'],
        "description": data['description'],
        "image_url": data['image_url'],
        "category_id": data['category_id'],
        "category_name": cat_name
    }
    mock_drinks.append(new_drink)
    next_drink_id += 1

    if supabase:
        try:
            result = supabase.table('drinks').insert(data).execute()
            return jsonify(result.data[0]), 201
        except Exception as e:
            print("Supabase insert failed, but mock added:", e)
    return jsonify(new_drink), 201

@app.route('/admin/drinks/<int:drink_id>', methods=['PUT'])
def admin_edit_drink(drink_id):
    if not admin_required():
        return jsonify({'error': 'Unauthorized'}), 401
    data = request.get_json()
    for d in mock_drinks:
        if d['id'] == drink_id:
            d.update(data)
            for c in mock_categories:
                if c['id'] == data.get('category_id', d['category_id']):
                    d['category_name'] = c['name']
                    break
            break
    if supabase:
        try:
            result = supabase.table('drinks').update(data).eq('id', drink_id).execute()
            return jsonify(result.data[0])
        except Exception as e:
            print("Supabase update failed, but mock updated:", e)
    return jsonify({"id": drink_id, **data}), 200

@app.route('/admin/drinks/<int:drink_id>', methods=['DELETE'])
def admin_delete_drink(drink_id):
    if not admin_required():
        return jsonify({'error': 'Unauthorized'}), 401
    global mock_drinks
    mock_drinks = [d for d in mock_drinks if d['id'] != drink_id]
    if supabase:
        try:
            supabase.table('drinks').delete().eq('id', drink_id).execute()
        except Exception as e:
            print("Supabase delete failed, but mock deleted:", e)
    return jsonify({'success': True})

@app.route('/admin/categories', methods=['GET'])
def admin_get_categories():
    if not admin_required():
        return jsonify({'error': 'Unauthorized'}), 401
    if supabase:
        try:
            response = supabase.table('categories').select('*').execute()
            return jsonify(response.data)
        except Exception as e:
            print("Supabase error in admin get categories:", e)
    return jsonify(mock_categories)

@app.route('/admin/categories', methods=['POST'])
def admin_add_category():
    if not admin_required():
        return jsonify({'error': 'Unauthorized'}), 401
    data = request.get_json()
    if 'name' not in data:
        return jsonify({'error': 'Missing name'}), 400
    global next_cat_id, mock_categories
    new_cat = {"id": next_cat_id, "name": data['name']}
    mock_categories.append(new_cat)
    next_cat_id += 1
    if supabase:
        try:
            result = supabase.table('categories').insert(data).execute()
            return jsonify(result.data[0]), 201
        except Exception as e:
            print("Supabase insert category failed, but mock added:", e)
    return jsonify(new_cat), 201

@app.route('/admin/categories/<int:cat_id>', methods=['PUT'])
def admin_edit_category(cat_id):
    if not admin_required():
        return jsonify({'error': 'Unauthorized'}), 401
    data = request.get_json()
    for c in mock_categories:
        if c['id'] == cat_id:
            c.update(data)
            break
    if supabase:
        try:
            result = supabase.table('categories').update(data).eq('id', cat_id).execute()
            return jsonify(result.data[0])
        except Exception as e:
            print("Supabase update category failed, but mock updated:", e)
    return jsonify({"id": cat_id, **data}), 200

@app.route('/admin/categories/<int:cat_id>', methods=['DELETE'])
def admin_delete_category(cat_id):
    if not admin_required():
        return jsonify({'error': 'Unauthorized'}), 401
    global mock_categories
    mock_categories = [c for c in mock_categories if c['id'] != cat_id]
    if supabase:
        try:
            supabase.table('categories').delete().eq('id', cat_id).execute()
        except Exception as e:
            print("Supabase delete category failed, but mock deleted:", e)
    return jsonify({'success': True})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)