<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Tamasha Admin</title>
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;600;700&family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet" />
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css" />
    <link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}" />
</head>
<body>
    <header class="club-header admin-header">
        <div class="header-content">
            <div class="logo-icon"><i class="fas fa-crown"></i></div>
            <h1 class="club-name"><span class="highlight">Tamasha</span> Admin</h1>
        </div>
        <div class="header-accent"></div>
    </header>

    <div class="admin-container" id="adminContainer">
        <!-- Login form -->
        <div id="loginSection" class="login-section">
            <div class="login-card">
                <h2><i class="fas fa-lock"></i> Admin Access</h2>
                <p>Enter the club's admin password to manage the catalogue.</p>
                <div class="login-form">
                    <input type="password" id="adminPassword" placeholder="Password" />
                    <button id="loginBtn"><i class="fas fa-sign-in-alt"></i> Login</button>
                    <div id="loginError" class="error-message"></div>
                </div>
            </div>
        </div>

        <!-- Dashboard -->
        <div id="dashboardSection" style="display: none;">
            <div class="admin-toolbar">
                <h2><i class="fas fa-glass-martini-alt"></i> Drink Manager</h2>
                <button id="logoutBtn" class="logout-btn"><i class="fas fa-sign-out-alt"></i> Logout</button>
            </div>

            <!-- Add / Edit Drink Form -->
            <div class="admin-form card">
                <h3 id="formTitle">Add New Drink</h3>
                <form id="drinkForm">
                    <input type="hidden" id="editDrinkId" />
                    <div class="form-group">
                        <label>Name</label>
                        <input type="text" id="drinkName" required />
                    </div>
                    <div class="form-group">
                        <label>Price (Kshs)</label>
                        <input type="number" step="0.01" id="drinkPrice" required />
                    </div>
                    <div class="form-group">
                        <label>Description</label>
                        <textarea id="drinkDescription" rows="2"></textarea>
                    </div>
                    <div class="form-group">
                        <label>Upload Image (file)</label>
                        <div style="display:flex; gap:0.5rem; flex-wrap:wrap;">
                            <input type="file" id="drinkImageFile" accept="image/*" style="flex:1;" />
                            <button type="button" id="uploadImageBtn" class="btn-secondary">Upload</button>
                        </div>
                    </div>
                    <div class="form-group">
                        <label>Image URL (or use upload above)</label>
                        <input type="url" id="drinkImageUrl" placeholder="https://example.com/image.jpg" />
                    </div>
                    <div class="form-group">
                        <label>Category</label>
                        <select id="drinkCategory"></select>
                    </div>
                    <button type="submit" id="submitDrinkBtn" class="btn-primary"><i class="fas fa-save"></i> Save Drink</button>
                    <button type="button" id="cancelEditBtn" class="btn-secondary" style="display: none;">Cancel</button>
                </form>
            </div>

            <!-- Category Manager -->
            <div class="category-manager card">
                <h3>Manage Categories</h3>
                <div class="category-list" id="categoryList"></div>
                <div class="category-add">
                    <input type="text" id="newCategoryName" placeholder="New category name" />
                    <button id="addCategoryBtn"><i class="fas fa-plus"></i> Add</button>
                </div>
            </div>

            <!-- Drinks Table -->
            <div class="drinks-table-wrapper card">
                <h3>Current Drinks</h3>
                <div id="drinksTableContainer">
                    <table id="drinksTable">
                        <thead><tr><th>Image</th><th>Name</th><th>Price</th><th>Category</th><th>Actions</th></tr></thead>
                        <tbody id="drinksTableBody"></tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>

    <footer class="club-footer">
        <div class="footer-content"><p>&copy; 2026 Tamasha Club. All rights reserved.</p></div>
    </footer>

    <div class="helpline">
        <a href="tel:+254700123456" class="helpline-btn"><i class="fas fa-phone-alt"></i><span>+254 700 123 456</span></a>
    </div>

    <script src="{{ url_for('static', filename='js/admin.js') }}"></script>
</body>
</html>