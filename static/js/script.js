// Public catalogue logic

let allDrinks = [];
let currentCategory = '';

// DOM elements
const grid = document.getElementById('drinksGrid');
const loading = document.getElementById('loadingSpinner');
const empty = document.getElementById('emptyState');
const searchInput = document.getElementById('searchInput');
const clearBtn = document.getElementById('clearSearch');
const categoryFilters = document.getElementById('categoryFilters');

// Fetch and render drinks
async function fetchDrinks(search = '', category = '') {
    try {
        loading.style.display = 'flex';
        grid.innerHTML = '';
        empty.style.display = 'none';

        let url = '/api/drinks?';
        const params = new URLSearchParams();
        if (search) params.append('search', search);
        if (category) params.append('category', category);
        url += params.toString();

        const res = await fetch(url);
        if (!res.ok) throw new Error('Failed to fetch');
        const data = await res.json();
        allDrinks = data;
        renderDrinks(data);
    } catch (err) {
        console.error(err);
        grid.innerHTML = '<p style="text-align:center;color:#e74c3c;">Failed to load drinks. Please refresh.</p>';
    } finally {
        loading.style.display = 'none';
    }
}

function renderDrinks(drinks) {
    if (!drinks || drinks.length === 0) {
        empty.style.display = 'block';
        grid.innerHTML = '';
        return;
    }
    empty.style.display = 'none';
    grid.innerHTML = drinks.map(d => `
        <div class="drink-card">
            <div class="image-wrapper">
                <img src="${d.image_url || 'https://via.placeholder.com/300x200/1a120e/d4af37?text=No+Image'}" alt="${d.name}" loading="lazy" />
            </div>
            <div class="drink-info">
                <div class="drink-name">${d.name}</div>
                <div class="drink-price">Ksh ${Number(d.price).toFixed(2)}</div>
                <div class="drink-description">${d.description || ''}</div>
                <div class="drink-category-tag">${d.category_name || 'Uncategorized'}</div>
            </div>
        </div>
    `).join('');
}

// Fetch categories and render pills
async function fetchCategories() {
    try {
        const res = await fetch('/api/categories');
        if (!res.ok) throw new Error();
        const cats = await res.json();
        // Add "All" pill
        const allPill = document.createElement('div');
        allPill.className = 'category-pill active';
        allPill.dataset.category = '';
        allPill.textContent = 'All';
        categoryFilters.appendChild(allPill);

        cats.forEach(c => {
            const pill = document.createElement('div');
            pill.className = 'category-pill';
            pill.dataset.category = c.name;
            pill.textContent = c.name;
            categoryFilters.appendChild(pill);
        });

        // Click handler for pills
        document.querySelectorAll('.category-pill').forEach(pill => {
            pill.addEventListener('click', function() {
                document.querySelectorAll('.category-pill').forEach(p => p.classList.remove('active'));
                this.classList.add('active');
                currentCategory = this.dataset.category;
                applyFilters();
            });
        });
    } catch (err) {
        console.error('Failed to load categories');
    }
}

function applyFilters() {
    const search = searchInput.value.trim();
    fetchDrinks(search, currentCategory);
}

// Search events
searchInput.addEventListener('input', function() {
    clearBtn.classList.toggle('visible', this.value.length > 0);
    applyFilters();
});

clearBtn.addEventListener('click', function() {
    searchInput.value = '';
    clearBtn.classList.remove('visible');
    applyFilters();
});

// Initial load
fetchCategories();
fetchDrinks();