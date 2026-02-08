const API_BASE = '/api/admin';

/* =========================================
   Global Utilities & State
   ========================================= */
let token = localStorage.getItem('admin_token');
let userRole = localStorage.getItem('admin_role') || 'admin';
let currentModalResolve = null; // For promise-based modal confirmation
let currentModalReject = null;

// Parse JWT to extract role
function parseJwtRole(token) {
    try {
        const payload = JSON.parse(atob(token.split('.')[1]));
        return payload.role || 'admin';
    } catch (e) {
        return 'admin';
    }
}

// Update role from token on load
if (token) {
    userRole = parseJwtRole(token);
    localStorage.setItem('admin_role', userRole);
}

// Toggle Body Scroll
const toggleBodyScroll = (lock) => {
    if (lock) document.body.classList.add('overflow-hidden');
    else document.body.classList.remove('overflow-hidden');
};

// Fetch Wrapper (Auto Logout on 401)
async function fetchAuth(url, options = {}) {
    if (!token) {
        window.location.href = '/admin/login';
        return;
    }

    const headers = {
        'Authorization': `Bearer ${token}`,
        ...options.headers
    };

    // Auto content-type for JSON
    if (options.body && typeof options.body === 'string' && !headers['Content-Type']) {
        headers['Content-Type'] = 'application/json';
    }

    const res = await fetch(url, { ...options, headers });

    if (res.status === 401) {
        localStorage.removeItem('admin_token');
        window.location.href = '/admin/login';
        throw new Error('Unauthorized');
    }

    return res;
}

/* =========================================
   Common Modal System
   ========================================= */
const modal = document.getElementById('common-modal');
const modalTitle = document.getElementById('modal-title');
const modalContent = document.getElementById('modal-content');
const modalInputContainer = document.getElementById('modal-input-container');
const modalInputLabel = document.getElementById('modal-input-label');
const modalInput = document.getElementById('modal-input');
const modalError = document.getElementById('modal-error');
const modalConfirmBtn = document.getElementById('modal-confirm-btn');

const modalCancelBtn = modal ? modal.querySelector('button[onclick="closeModal()"]') : null;

window.closeModal = () => {
    if (modal) modal.classList.add('hidden');
    toggleBodyScroll(false);
    if (currentModalReject) currentModalReject('Cancelled');
    resetModal();
};

function resetModal() {
    if (!modal) return; // Exit early if modal doesn't exist
    if (modalInput) modalInput.value = '';
    if (modalError) modalError.classList.add('hidden');
    if (modalInputContainer) modalInputContainer.classList.add('hidden');
    // Ensure cancel button is visible by default for next time
    if (modalCancelBtn) modalCancelBtn.classList.remove('hidden');
    currentModalResolve = null;
    currentModalReject = null;
}

// Generic Confirm Modal
// Usage: const confirmed = await showConfirmModal({ title: '...', message: '...', confirmText: 'Delete', isDanger: true, requireInput: true, inputLabel: 'Password' });
window.showConfirmModal = ({ title, message, confirmText = 'Confirm', isDanger = false, requireInput = false, inputLabel = '', inputType = 'text', hideCancel = false }) => {
    return new Promise((resolve, reject) => {
        resetModal();
        currentModalResolve = resolve;
        currentModalReject = reject;

        modalTitle.textContent = title;
        modalContent.innerHTML = message;
        modalConfirmBtn.textContent = confirmText;

        if (hideCancel && modalCancelBtn) {
            modalCancelBtn.classList.add('hidden');
        }

        // Danger Style
        if (isDanger) {
            modalConfirmBtn.className = 'px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg font-medium shadow-lg shadow-red-500/30 transition-all';
        } else {
            modalConfirmBtn.className = 'px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg font-medium shadow-lg shadow-indigo-500/30 transition-all';
        }

        // Input Field
        if (requireInput) {
            modalInputContainer.classList.remove('hidden');
            modalInputLabel.textContent = inputLabel;
            modalInput.type = inputType;
            setTimeout(() => modalInput.focus(), 100);
        }

        modal.classList.remove('hidden');
        toggleBodyScroll(true);
    });
};

window.showAlert = (message, title = 'Alert') => {
    return showConfirmModal({
        title: title,
        message: message,
        confirmText: 'OK',
        hideCancel: true
    });
};

if (modalConfirmBtn) {
    modalConfirmBtn.addEventListener('click', () => {
        const inputValue = modalInput.value;
        if (!modalInputContainer.classList.contains('hidden') && !inputValue) {
            modalError.textContent = 'This field is required';
            modalError.classList.remove('hidden');
            return;
        }
        if (currentModalResolve) currentModalResolve(inputValue || true);
        modal.classList.add('hidden');
        toggleBodyScroll(false);
        resetModal();
    });
}


/* =========================================
   Page Initializers
   ========================================= */
document.addEventListener('DOMContentLoaded', () => {
    const path = window.location.pathname;

    // Apply role-based menu visibility
    applyRoleBasedMenuVisibility();

    if (path.includes('/admin/login')) initLogin();
    else if (path === '/admin' || path === '/admin/') initDashboard();
    else if (path.includes('/admin/manage')) initManage();
    else if (path.includes('/admin/admin-users')) initAdminUsers();
    else if (path.includes('/admin/users')) initUsers();
    else if (path.includes('/admin/settings')) initSettings();
});

// Apply role-based menu visibility
function applyRoleBasedMenuVisibility() {
    if (!token) return;

    // Hide menus that require 'admin' role for 'view_admin' users
    if (userRole === 'view_admin') {
        document.querySelectorAll('[data-role="admin"]').forEach(el => {
            el.classList.add('hidden');
        });

        // Also hide voting configuration in settings page
        const votingConfig = document.getElementById('voting-config-section');
        if (votingConfig) votingConfig.classList.add('hidden');
    }
}


/* =========================================
   1. Login Logic
   ========================================= */
function initLogin() {
    const loginForm = document.getElementById('login-form');
    if (!loginForm) return;

    if (localStorage.getItem('admin_token')) {
        window.location.href = '/admin';
    }

    loginForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const username = document.getElementById('username').value;
        const password = document.getElementById('password').value;
        const errorEl = document.getElementById('login-error');

        try {
            const formData = new FormData();
            formData.append('username', username);
            formData.append('password', password);

            const res = await fetch(`${API_BASE}/token`, { method: 'POST', body: formData });
            if (!res.ok) throw new Error('Login failed');

            const data = await res.json();
            localStorage.setItem('admin_token', data.access_token);
            localStorage.setItem('admin_role', data.role || 'admin');
            window.location.href = '/admin';

        } catch (err) {
            errorEl.classList.remove('hidden');
            errorEl.textContent = "Invalid username or password";
        }
    });
}


/* =========================================
   2. Dashboard Logic
   ========================================= */
async function initDashboard() {
    const totalVotesEl = document.getElementById('total-votes');
    const totalUsersEl = document.getElementById('total-users');
    const totalCategoriesEl = document.getElementById('total-categories');
    const categoryGrid = document.getElementById('category-grid');

    if (!totalVotesEl) return;

    try {
        const res = await fetchAuth(`${API_BASE}/dashboard-stats`);
        const data = await res.json();

        // 1. Top Level Stats
        if (totalVotesEl) totalVotesEl.textContent = data.total_votes;
        if (totalUsersEl) totalUsersEl.textContent = data.total_users;
        if (totalCategoriesEl) totalCategoriesEl.textContent = data.total_categories;

        // 2. Category Grid
        if (categoryGrid) {
            categoryGrid.innerHTML = data.category_stats.map(renderDashboardCategory).join('');
        }
    } catch (err) { console.error(err); }
}

function renderDashboardCategory(category) {
    const cardsHTML = category.cards.map((card, index) => {
        const rank = index + 1;
        const isFirst = rank === 1 && card.votes > 0;
        const isSecond = rank === 2 && card.votes > 0;
        const isThird = rank === 3 && card.votes > 0;

        // Rank styling
        let rankBadge = '';
        let cardBg = '';
        let barColor = 'from-indigo-500 to-blue-600';

        if (isFirst) {
            rankBadge = '<span class="w-6 h-6 flex items-center justify-center bg-gradient-to-br from-yellow-400 to-amber-500 text-white text-xs font-black rounded-full shadow-lg shadow-amber-200">1</span>';
            cardBg = 'border-l-4 border-amber-400 bg-amber-50/50';
            barColor = 'from-amber-400 to-yellow-500';
        } else if (isSecond) {
            rankBadge = '<span class="w-6 h-6 flex items-center justify-center bg-gradient-to-br from-slate-300 to-slate-400 text-white text-xs font-black rounded-full shadow">2</span>';
            cardBg = 'border-l-4 border-slate-300 bg-slate-50/50';
            barColor = 'from-slate-400 to-slate-500';
        } else if (isThird) {
            rankBadge = '<span class="w-6 h-6 flex items-center justify-center bg-gradient-to-br from-orange-400 to-amber-600 text-white text-xs font-black rounded-full shadow">3</span>';
            cardBg = 'border-l-4 border-orange-300 bg-orange-50/30';
            barColor = 'from-orange-400 to-amber-500';
        } else {
            rankBadge = `<span class="w-6 h-6 flex items-center justify-center bg-slate-200 text-slate-600 text-xs font-bold rounded-full">${rank}</span>`;
        }

        // Card image (small thumbnail)
        const imageHTML = card.image_url
            ? `<img src="${card.image_url}" alt="${card.title}" class="w-10 h-10 md:w-12 md:h-12 rounded-lg object-cover border border-slate-200 flex-shrink-0">`
            : `<div class="w-10 h-10 md:w-12 md:h-12 rounded-lg bg-slate-100 flex items-center justify-center flex-shrink-0">
                <svg class="w-5 h-5 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"></path>
                </svg>
               </div>`;

        return `
            <div class="mb-3 last:mb-0 p-3 rounded-lg transition-all hover:scale-[1.02] ${cardBg}">
                <div class="flex items-center gap-3 mb-2">
                    ${rankBadge}
                    ${imageHTML}
                    <div class="flex-1 min-w-0">
                        <p class="text-sm font-semibold text-slate-800 truncate">${card.title}</p>
                        <p class="text-xs text-slate-500">${card.votes} votes</p>
                    </div>
                    <span class="text-sm font-black text-slate-900 flex-shrink-0">${card.percentage}%</span>
                </div>
                <div class="w-full bg-slate-100 rounded-full h-2 ml-9">
                    <div class="bg-gradient-to-r ${barColor} h-2 rounded-full transition-all duration-500" 
                         style="width: ${card.percentage}%"></div>
                </div>
            </div>
        `;
    }).join('');

    return `
        <div class="bg-white p-5 md:p-6 rounded-xl shadow-xl shadow-slate-200/50 border border-slate-100 flex flex-col h-full">
            <h3 class="text-base md:text-lg font-black text-slate-900 mb-4 border-b border-slate-100 pb-3 flex items-center justify-between">
                <span class="truncate">${category.name}</span>
                <span class="text-xs font-medium text-slate-400 ml-2 flex-shrink-0">${category.total_votes} votes</span>
            </h3>
            <div class="flex-1 overflow-y-auto max-h-[350px] custom-scrollbar pr-1 -mr-1">
                ${cardsHTML || '<p class="text-sm text-slate-400 text-center py-4">No cards in this category</p>'}
            </div>
        </div>
    `;
}


/* =========================================
   3. Manage Logic (Categories & Cards)
   ========================================= */
async function initManage() {
    window.loadManageData = loadManageData; // Expose to global for button onclicks
    loadManageData();

    // Sortable Init
    // (Logic moved inside render to ensure elements exist)
}

async function loadManageData() {
    const container = document.getElementById('management-container');
    const select = document.getElementById('card-category-select');
    if (!container) return;

    try {
        const [catRes, statsRes] = await Promise.all([
            fetchAuth(`${API_BASE}/categories`),
            fetchAuth(`${API_BASE}/dashboard-stats`)
        ]);

        const categories = await catRes.json();
        const stats = await statsRes.json();

        // Populate Select
        if (select) {
            select.innerHTML = '';
            categories.forEach(cat => {
                const opt = document.createElement('option');
                opt.value = cat.id;
                opt.textContent = cat.name;
                select.appendChild(opt);
            });
        }

        renderManagement(container, categories, stats.category_stats);

    } catch (err) { console.error(err); }
}

function renderManagement(container, categories, categoryStats) {
    // 1. Capture current state (which categories are open)
    const openCategories = new Set();
    const existingCards = container.querySelectorAll('[id^="cat-content-"]');
    existingCards.forEach(el => {
        if (el.classList.contains('grid-rows-[1fr]')) {
            const id = el.id.replace('cat-content-', '');
            openCategories.add(parseInt(id)); // Assuming ID is int or matches loose equality
        }
    });

    container.innerHTML = '';

    categories.forEach(cat => {
        const catStats = categoryStats.find(c => c.id === cat.id);
        const cardCount = catStats ? catStats.cards.length : 0;
        const isOpen = openCategories.has(cat.id); // Check if previously open

        // Cards Grid
        let cardsPreview = '';
        if (catStats && catStats.cards.length > 0) {
            cardsPreview = '<div class="mt-6 grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-4">';
            catStats.cards.forEach(card => {
                const fullCard = cat.cards.find(c => c.id === card.id) || card; // ensure image_url exists
                cardsPreview += `
                    <div class="group relative bg-white rounded-xl border border-slate-200 hover:border-indigo-300 hover:shadow-md transition-all flex flex-col overflow-hidden">
                        <div class="relative w-full bg-slate-100" style="aspect-ratio: 269/268;">
                            <img src="${fullCard.image_url || '/static/placeholder.png'}" class="absolute inset-0 w-full h-full object-cover">
                            <div class="absolute top-2 right-2 flex space-x-1 opacity-100 sm:opacity-0 group-hover:opacity-100 transition-opacity duration-200">
                                <button onclick="openEditCardModal('${fullCard.id}', '${fullCard.title.replace(/'/g, "\\'")}', '${(fullCard.subtitle || '').replace(/'/g, "\\'")}', '${fullCard.image_url || ''}')" 
                                    class="p-2 bg-white/90 backdrop-blur-sm text-slate-500 hover:text-indigo-600 rounded-lg shadow-sm hover:shadow transition-colors" title="Edit">
                                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z"></path></svg>
                                </button>
                                <button onclick="deleteCard('${fullCard.id}')" 
                                    class="p-2 bg-white/90 backdrop-blur-sm text-slate-500 hover:text-red-600 rounded-lg shadow-sm hover:shadow transition-colors" title="Delete">
                                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path></svg>
                                </button>
                            </div>
                        </div>
                        <div class="p-4 flex flex-col flex-grow">
                             <h4 class="text-base font-bold text-slate-900 leading-tight mb-1 truncate" title="${fullCard.title}">${fullCard.title}</h4>
                             ${fullCard.subtitle ? `<p class="text-xs text-slate-500 truncate" title="${fullCard.subtitle}">${fullCard.subtitle}</p>` : '<p class="text-xs text-slate-300 italic">No subtitle</p>'}
                        </div>
                    </div>
                `;
            });
            cardsPreview += '</div>';
        } else {
            cardsPreview = `
                <div class="mt-4 p-8 border-2 border-dashed border-slate-200 rounded-xl flex flex-col items-center justify-center text-center">
                    <p class="text-slate-400 text-sm">No cards in this category yet.</p>
                    <button onclick="openCardModal('${cat.id}')" class="mt-2 text-indigo-600 text-sm font-medium hover:underline">Add one now</button>
                </div>
            `;
        }

        const uiCard = document.createElement('div');
        uiCard.className = 'bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden mb-6';
        uiCard.dataset.id = cat.id;

        // Apply open/closed state
        const gridState = isOpen ? 'grid-rows-[1fr]' : 'grid-rows-[0fr]';
        const chevronRotation = isOpen ? 'rotate(180deg)' : 'rotate(0deg)';
        const headerHover = isOpen ? 'text-indigo-700' : 'text-slate-900';

        uiCard.innerHTML = `
            <div class="p-3 md:p-6">
                <!-- Header -->
                <div class="flex items-center justify-between">
                    <div class="flex items-center gap-2 md:gap-3 group cursor-pointer flex-grow min-w-0" onclick="toggleAccordion('cat-content-${cat.id}', 'cat-chevron-${cat.id}')">
                        <div class="drag-handle p-1.5 md:p-2 text-slate-300 hover:text-slate-600 cursor-move hover:bg-slate-100 rounded-lg transition-colors flex-shrink-0" onclick="event.stopPropagation()">
                             <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 8h16M4 16h16"></path></svg>
                        </div>
                        <div class="p-1.5 md:p-2 bg-slate-50 rounded-lg group-hover:bg-slate-100 transition-colors flex-shrink-0">
                            <svg id="cat-chevron-${cat.id}" class="w-4 h-4 md:w-5 md:h-5 text-slate-400 transform transition-transform duration-300" 
                                 style="transform: ${chevronRotation}" 
                                 fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path></svg>
                        </div>
                        <div class="min-w-0 flex-grow">
                            <h3 class="text-base md:text-lg font-bold group-hover:text-indigo-700 transition-colors select-none truncate ${headerHover}">${cat.name}</h3>
                            <p class="text-xs text-slate-500 font-medium select-none truncate">${cardCount} Cards</p>
                        </div>
                    </div>
                    
                    <!-- Actions -->
                    <div class="flex items-center gap-1 md:gap-2 ml-2 flex-shrink-0">
                         <button onclick="openCardModal('${cat.id}')" class="hidden sm:inline-flex items-center px-3 py-1.5 bg-indigo-50 text-indigo-700 rounded-lg text-sm font-bold hover:bg-indigo-100 transition-colors border border-indigo-100">
                            <svg class="w-4 h-4 mr-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"></path></svg>
                            Add
                        </button>
                         <button onclick="openCardModal('${cat.id}')" class="sm:hidden p-1.5 md:p-2 bg-indigo-50 text-indigo-700 rounded-lg hover:bg-indigo-100">
                            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"></path></svg>
                        </button>
                        <div class="h-5 md:h-6 w-px bg-slate-200 mx-1 md:mx-2"></div>
                        <button onclick="openEditCategoryModal('${cat.id}', '${cat.name.replace(/'/g, "\\'")}')" class="p-1.5 md:p-2 text-slate-400 hover:text-indigo-600 hover:bg-slate-50 rounded-lg transition-colors" title="Edit">
                            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z"></path></svg>
                        </button>
                        <button onclick="deleteCategory('${cat.id}')" class="p-1.5 md:p-2 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors" title="Delete">
                            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path></svg>
                        </button>
                    </div>
                </div>

                <div id="cat-content-${cat.id}" class="grid transition-[grid-template-rows] duration-300 ease-out ${gridState}">
                    <div class="overflow-hidden">
                        ${cardsPreview}
                    </div>
                </div>
            </div>
        `;
        container.appendChild(uiCard);
    });

    // Init Sortable
    if (window.Sortable) {
        new Sortable(container, {
            animation: 150,
            handle: '.drag-handle',
            ghostClass: 'bg-indigo-50',
            onEnd: function (evt) {
                const order = [];
                Array.from(container.children).forEach(child => {
                    if (child.dataset.id) order.push(parseInt(child.dataset.id));
                });
                // Reorder API call
                fetchAuth(`${API_BASE}/categories/reorder`, {
                    method: 'PUT',
                    body: JSON.stringify({ items: order })
                }).catch(err => console.error('Reorder failed', err));
            }
        });
    }
}

// Helpers
window.toggleAccordion = (contentId, chevronId) => {
    const content = document.getElementById(contentId);
    const chevron = document.getElementById(chevronId);
    if (!content) return;

    // Toggle grid state
    if (content.classList.contains('grid-rows-[0fr]')) {
        content.classList.remove('grid-rows-[0fr]');
        content.classList.add('grid-rows-[1fr]');
        chevron.style.transform = 'rotate(180deg)';
    } else {
        content.classList.remove('grid-rows-[1fr]');
        content.classList.add('grid-rows-[0fr]');
        chevron.style.transform = 'rotate(0deg)';
    }
};

// -- Delete Category using Common Modal --
window.deleteCategory = async (id) => {
    try {
        const checkRes = await fetchAuth(`${API_BASE}/categories/${id}/dependencies`);
        const stats = await checkRes.json();

        const cardCount = stats.card_count || 0;
        const voteCount = stats.vote_count || 0;
        const isDirty = cardCount > 0 || voteCount > 0;

        let message = "Are you sure you want to delete this empty category?";
        let requireInput = false;

        if (isDirty) {
            message = `
                <div class="text-slate-600">
                    <p class="mb-2">This category contains:</p>
                    <ul class="list-disc list-inside text-sm mb-4">
                        ${cardCount > 0 ? `<li><b>${cardCount}</b> Cards</li>` : ''}
                        ${voteCount > 0 ? `<li><b>${voteCount}</b> Votes</li>` : ''}
                    </ul>
                    <p class="text-sm font-bold text-red-600">Enter Admin Password to confirm permanent deletion.</p>
                </div>
            `;
            requireInput = true;
        }

        const passwordOrConfirm = await showConfirmModal({
            title: 'Delete Category',
            message: message,
            confirmText: 'Delete Category',
            isDanger: true,
            requireInput: requireInput,
            inputLabel: 'Admin Password',
            inputType: 'password'
        });

        if (passwordOrConfirm) {
            const body = requireInput ? { password: passwordOrConfirm } : {};
            const res = await fetchAuth(`${API_BASE}/categories/${id}`, {
                method: 'DELETE',
                body: JSON.stringify(body)
            });

            if (res.ok) {
                loadManageData();
            } else {
                const err = await res.json();
                await showAlert(`Error: ${err.detail}`, 'Error');
            }
        }
    } catch (err) {
        if (err !== 'Cancelled') console.error(err);
    }
};

// -- Delete Card using Common Modal --
window.deleteCard = async (id) => {
    try {
        const checkRes = await fetchAuth(`${API_BASE}/cards/${id}/dependencies`);
        const stats = await checkRes.json();

        let message = "Are you sure you want to delete this card?";
        let requireInput = false;

        if (stats.vote_count > 0) {
            message = `
                <div class="text-slate-600">
                    <p class="mb-2">This card has <b>${stats.vote_count} Votes</b>.</p>
                    <p class="text-sm font-bold text-red-600">Enter Admin Password to confirm permanent deletion.</p>
                </div>
            `;
            requireInput = true;
        }

        const passwordOrConfirm = await showConfirmModal({
            title: 'Delete Card',
            message: message,
            confirmText: 'Delete Card',
            isDanger: true,
            requireInput: requireInput,
            inputLabel: 'Admin Password',
            inputType: 'password'
        });

        if (passwordOrConfirm) {
            const body = requireInput ? { password: passwordOrConfirm } : {};
            const res = await fetchAuth(`${API_BASE}/cards/${id}`, { method: 'DELETE', body: JSON.stringify(body) });
            if (res.ok) loadManageData();
            else {
                const err = await res.json();
                await showAlert(`Error: ${err.detail}`, 'Error');
            }
        }
    } catch (err) { if (err !== 'Cancelled') console.error(err); }
};

// -- Other Modals (Create/Edit) --
// Kept simple for now (still using specific modals in HTML if present)
// But defined here to make manage.html work
window.openCategoryModal = () => { document.getElementById('category-modal').classList.remove('hidden'); toggleBodyScroll(true); };
window.closeCategoryModal = () => { document.getElementById('category-modal').classList.add('hidden'); toggleBodyScroll(false); };

window.submitCategory = async () => {
    const name = document.getElementById('new-cat-name').value;
    if (!name) return;
    try {
        const res = await fetchAuth(`${API_BASE}/categories`, { method: 'POST', body: JSON.stringify({ name }) });
        if (res.ok) {
            closeCategoryModal();
            loadManageData();
            document.getElementById('new-cat-name').value = '';
        } else {
            const err = await res.json();
            await showAlert(err.detail || 'Failed to create category', 'Creation Error');
        }
    } catch (e) {
        console.error(e);
    }
};

window.openCardModal = (catId) => {
    document.getElementById('card-modal').classList.remove('hidden');
    document.getElementById('card-category-select').value = catId;
    toggleBodyScroll(true);
};
window.closeCardModal = () => {
    document.getElementById('card-modal').classList.add('hidden');
    toggleBodyScroll(false);
    // clear inputs
    document.getElementById('card-title').value = '';
    document.getElementById('card-subtitle').value = '';
    document.getElementById('card-image-file').value = '';
    document.getElementById('subtitle-preview').innerHTML = '';
};
if (document.getElementById('card-subtitle')) {
    document.getElementById('card-subtitle').addEventListener('input', (e) => {
        document.getElementById('subtitle-preview').innerHTML = `Preview: <span class="font-semibold">${e.target.value.split('//').join('<br>')}</span>`;
    });
}
window.submitCard = async () => {
    const catId = document.getElementById('card-category-select').value;
    const title = document.getElementById('card-title').value;
    const subtitle = document.getElementById('card-subtitle').value;
    const file = document.getElementById('card-image-file').files[0];

    if (!title || !file) return;

    try {
        const formData = new FormData();
        formData.append('file', file);
        const upRes = await fetchAuth(`${API_BASE}/upload`, { method: 'POST', body: formData });
        const upData = await upRes.json();

        const res = await fetchAuth(`${API_BASE}/cards?category_id=${catId}`, {
            method: 'POST',
            body: JSON.stringify({ title, subtitle, image_url: upData.url })
        });
        if (res.ok) { closeCardModal(); loadManageData(); }
    } catch (err) { console.error(err); await showAlert('Failed to create card', 'Error'); }
};

// Edit Category
window.openEditCategoryModal = (id, name) => {
    document.getElementById('edit-cat-id').value = id;
    document.getElementById('edit-cat-name').value = name;
    document.getElementById('edit-category-modal').classList.remove('hidden');
};
window.closeEditCategoryModal = () => { document.getElementById('edit-category-modal').classList.add('hidden'); };
window.submitEditCategory = async () => {
    const id = document.getElementById('edit-cat-id').value;
    const name = document.getElementById('edit-cat-name').value;
    const res = await fetchAuth(`${API_BASE}/categories/${id}`, { method: 'PUT', body: JSON.stringify({ name }) });
    if (res.ok) { closeEditCategoryModal(); loadManageData(); }
};

// Edit Card
window.openEditCardModal = (id, title, subtitle, img) => {
    document.getElementById('edit-card-id').value = id;
    document.getElementById('edit-card-title').value = title;
    document.getElementById('edit-card-subtitle').value = subtitle;
    document.getElementById('edit-card-image-preview').src = img;
    document.getElementById('edit-card-modal').classList.remove('hidden');
};
window.closeEditCardModal = () => { document.getElementById('edit-card-modal').classList.add('hidden'); };
window.submitEditCard = async () => {
    const id = document.getElementById('edit-card-id').value;
    const title = document.getElementById('edit-card-title').value;
    const subtitle = document.getElementById('edit-card-subtitle').value;
    let imageUrl = document.getElementById('edit-card-image-preview').src;
    const file = document.getElementById('edit-card-image-file').files[0];

    if (file) {
        const fd = new FormData(); fd.append('file', file);
        const upRes = await fetchAuth(`${API_BASE}/upload`, { method: 'POST', body: fd });
        imageUrl = (await upRes.json()).url;
    }

    const res = await fetchAuth(`${API_BASE}/cards/${id}`, { method: 'PUT', body: JSON.stringify({ title, subtitle, image_url: imageUrl }) });
    if (res.ok) { closeEditCardModal(); loadManageData(); }
};


/* =========================================
   4. Users Logic
   ========================================= */
let usersPage = 1;
let usersSearch = '';

async function initUsers() {
    window.loadUsers = loadUsers;
    window.changePage = (p) => { if (p > 0) { usersPage = p; loadUsers(); } };
    window.deleteUser = deleteUser; // Expose

    loadUsers();

    const searchInput = document.getElementById('search-input');
    if (searchInput) {
        let timer;
        searchInput.addEventListener('input', (e) => {
            clearTimeout(timer);
            timer = setTimeout(() => {
                usersSearch = e.target.value;
                usersPage = 1;
                loadUsers();
            }, 300);
        });
    }
}

async function loadUsers() {
    const tableBody = document.getElementById('users-table-body');
    const paginationControls = document.getElementById('pagination-controls');
    if (!tableBody) return;

    try {
        const query = new URLSearchParams({ page: usersPage, limit: 10, search: usersSearch });
        const res = await fetchAuth(`${API_BASE}/users?${query}`);
        const data = await res.json();

        // Render Table
        if (data.users.length === 0) {
            tableBody.innerHTML = `<tr><td colspan="5" class="px-6 py-8 text-center text-slate-400">No users found.</td></tr>`;
        } else {
            tableBody.innerHTML = data.users.map(user => `
                <tr class="hover:bg-slate-50 transition-colors group">
                    <td class="px-6 py-4 font-mono text-xs text-slate-400">#${user.id}</td>
                    <td class="px-6 py-4 font-medium text-slate-900">${user.name}</td>
                    <td class="px-6 py-4 text-slate-600">${user.phone}</td>
                    <td class="px-6 py-4 text-slate-600">${user.email}</td>
                    <td class="px-6 py-4 text-right">
                        <button onclick="deleteUser(${user.id}, '${user.name.replace(/'/g, "\\'")}')" 
                            class="text-slate-400 hover:text-red-600 transition-colors p-1 rounded hover:bg-red-50">
                            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path></svg>
                        </button>
                    </td>
                </tr>
            `).join('');
        }

        // Pagination
        const totalPages = Math.ceil(data.total / data.limit);
        paginationControls.innerHTML = `
            <p class="text-sm text-slate-500">Showing page ${data.page} of ${totalPages} (${data.total} users)</p>
            <div class="flex gap-2">
                <button onclick="changePage(${data.page - 1})" ${data.page === 1 ? 'disabled' : ''} class="px-3 py-1 rounded border disabled:opacity-50">Prev</button>
                <button onclick="changePage(${data.page + 1})" ${data.page >= totalPages ? 'disabled' : ''} class="px-3 py-1 rounded border disabled:opacity-50">Next</button>
            </div>
        `;

    } catch (err) { console.error(err); }
}

async function deleteUser(id, name) {
    try {
        const password = await showConfirmModal({
            title: 'Confirm User Deletion',
            message: `Are you sure you want to delete <b class="text-slate-700">${name}</b>? This will also remove all their votes.`,
            confirmText: 'Delete User',
            isDanger: true,
            requireInput: true,
            inputLabel: 'Admin Password',
            inputType: 'password'
        });

        if (password) {
            const res = await fetchAuth(`${API_BASE}/users/${id}`, {
                method: 'DELETE',
                body: JSON.stringify({ password })
            });
            if (res.ok) loadUsers();
            else {
                const err = await res.json();
                await showAlert(`Error: ${err.detail}`, 'Error');
            }
        }
    } catch (err) { if (err !== 'Cancelled') console.error(err); }
}


/* =========================================
   5. Settings Logic
   ========================================= */
async function initSettings() {
    const passwordForm = document.getElementById('password-form');
    const votingToggle = document.getElementById('voting-toggle');
    const votingStatus = document.getElementById('voting-status');
    const pollCountToggle = document.getElementById('poll-count-toggle');
    const pollCountStatus = document.getElementById('poll-count-status');

    if (!votingToggle) return;

    // Load current settings
    try {
        const res = await fetchAuth(`${API_BASE}/settings`);
        const data = await res.json();

        votingToggle.checked = data.voting_enabled;
        updateVotingStatus(data.voting_enabled);

        if (pollCountToggle) {
            pollCountToggle.checked = data.show_poll_count;
            updatePollCountStatus(data.show_poll_count);
        }
    } catch (err) { console.error(err); }

    // Password Form Submit
    if (passwordForm) {
        passwordForm.addEventListener('submit', async (e) => {
            e.preventDefault();

            const currentPassword = document.getElementById('current-password').value;
            const newPassword = document.getElementById('new-password').value;
            const confirmPassword = document.getElementById('confirm-password').value;

            // Client-side validation
            if (newPassword.length < 6) {
                await showAlert('New password must be at least 6 characters', 'Validation Error');
                return;
            }
            if (newPassword !== confirmPassword) {
                await showAlert('New passwords do not match', 'Validation Error');
                return;
            }

            try {
                const res = await fetchAuth(`${API_BASE}/password`, {
                    method: 'PUT',
                    body: JSON.stringify({
                        current_password: currentPassword,
                        new_password: newPassword,
                        confirm_password: confirmPassword
                    })
                });

                if (res.ok) {
                    await showAlert('Password changed successfully!', 'Success');
                    passwordForm.reset();
                } else {
                    const err = await res.json();
                    await showAlert(`Error: ${err.detail}`, 'Error');
                }
            } catch (err) { console.error(err); }
        });
    }

    // Voting Toggle
    votingToggle.addEventListener('change', async () => {
        const enabled = votingToggle.checked;
        const action = enabled ? 'enable' : 'disable';

        try {
            const password = await showConfirmModal({
                title: `${enabled ? 'Enable' : 'Disable'} Voting`,
                message: `Are you sure you want to <b>${action}</b> vote submissions?`,
                confirmText: `${enabled ? 'Enable' : 'Disable'} Voting`,
                isDanger: !enabled,
                requireInput: true,
                inputLabel: 'Admin Password',
                inputType: 'password'
            });

            if (password) {
                const res = await fetchAuth(`${API_BASE}/settings`, {
                    method: 'PUT',
                    body: JSON.stringify({
                        voting_enabled: enabled,
                        show_poll_count: pollCountToggle ? pollCountToggle.checked : false,
                        password: password
                    })
                });

                if (res.ok) {
                    updateVotingStatus(enabled);
                    await showAlert(`Voting has been ${action}d successfully!`, 'Success');
                } else {
                    votingToggle.checked = !enabled; // Revert
                    const err = await res.json();
                    await showAlert(`Error: ${err.detail}`, 'Error');
                }
            } else {
                votingToggle.checked = !enabled; // Revert if cancelled
            }
        } catch (err) {
            votingToggle.checked = !enabled; // Revert
            if (err !== 'Cancelled') console.error(err);
        }
    });

    // Poll Count Toggle
    if (pollCountToggle) {
        pollCountToggle.addEventListener('change', async () => {
            const enabled = pollCountToggle.checked;
            const action = enabled ? 'show' : 'hide';

            try {
                const password = await showConfirmModal({
                    title: `${enabled ? 'Show' : 'Hide'} Poll Count`,
                    message: `Are you sure you want to <b>${action}</b> the poll count on the voting page?`,
                    confirmText: `${enabled ? 'Show' : 'Hide'} Poll Count`,
                    isDanger: !enabled,
                    requireInput: true,
                    inputLabel: 'Admin Password',
                    inputType: 'password'
                });

                if (password) {
                    const res = await fetchAuth(`${API_BASE}/settings`, {
                        method: 'PUT',
                        body: JSON.stringify({
                            voting_enabled: votingToggle.checked,
                            show_poll_count: enabled,
                            password: password
                        })
                    });

                    if (res.ok) {
                        updatePollCountStatus(enabled);
                        await showAlert(`Poll count is now ${enabled ? 'visible' : 'hidden'}!`, 'Success');
                    } else {
                        pollCountToggle.checked = !enabled; // Revert
                        const err = await res.json();
                        await showAlert(`Error: ${err.detail}`, 'Error');
                    }
                } else {
                    pollCountToggle.checked = !enabled; // Revert if cancelled
                }
            } catch (err) {
                pollCountToggle.checked = !enabled; // Revert
                if (err !== 'Cancelled') console.error(err);
            }
        });
    }

    function updateVotingStatus(enabled) {
        if (votingStatus) {
            votingStatus.innerHTML = enabled
                ? '<span class="text-emerald-600 font-medium">✓ Voting is currently OPEN</span>'
                : '<span class="text-red-600 font-medium">✗ Voting is currently CLOSED</span>';
        }
    }

    function updatePollCountStatus(enabled) {
        if (pollCountStatus) {
            pollCountStatus.innerHTML = enabled
                ? '<span class="text-emerald-600 font-medium">✓ Poll count is visible to users</span>'
                : '<span class="text-slate-500 font-medium">Poll count is hidden from users</span>';
        }
    }
}


/* =========================================
   6. Admin Users Management Logic
   ========================================= */
async function initAdminUsers() {
    loadAdminUsers();
}

async function loadAdminUsers() {
    const tableBody = document.getElementById('admins-table-body');
    if (!tableBody) return;

    try {
        const res = await fetchAuth(`${API_BASE}/admins`);
        const admins = await res.json();

        if (admins.length === 0) {
            tableBody.innerHTML = `<tr><td colspan="4" class="px-6 py-8 text-center text-slate-400">No admin users found.</td></tr>`;
        } else {
            tableBody.innerHTML = admins.map(admin => `
                <tr class="hover:bg-slate-50 transition-colors group">
                    <td class="px-6 py-4 font-mono text-xs text-slate-400">#${admin.id}</td>
                    <td class="px-6 py-4 font-medium text-slate-900">${admin.username}</td>
                    <td class="px-6 py-4">
                        <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${admin.role === 'admin' ? 'bg-indigo-100 text-indigo-700' : 'bg-slate-100 text-slate-600'}">
                            ${admin.role === 'admin' ? 'Full Admin' : 'View Only'}
                        </span>
                    </td>
                    <td class="px-6 py-4 text-right">
                        <div class="flex justify-end gap-2">
                            <button onclick="openEditAdminModal(${admin.id}, '${admin.username.replace(/'/g, "\\'")}', '${admin.role}')" 
                                class="text-slate-400 hover:text-indigo-600 transition-colors p-1 rounded hover:bg-indigo-50">
                                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z"></path></svg>
                            </button>
                            <button onclick="deleteAdmin(${admin.id}, '${admin.username.replace(/'/g, "\\'")}')" 
                                class="text-slate-400 hover:text-red-600 transition-colors p-1 rounded hover:bg-red-50">
                                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path></svg>
                            </button>
                        </div>
                    </td>
                </tr>
            `).join('');
        }
    } catch (err) { console.error(err); }
}

// Create Admin Modal
window.openCreateAdminModal = () => {
    document.getElementById('create-admin-modal').classList.remove('hidden');
    toggleBodyScroll(true);
};

window.closeCreateAdminModal = () => {
    document.getElementById('create-admin-modal').classList.add('hidden');
    toggleBodyScroll(false);
    document.getElementById('new-admin-username').value = '';
    document.getElementById('new-admin-password').value = '';
    document.getElementById('new-admin-role').value = 'admin';
};

window.submitCreateAdmin = async () => {
    const username = document.getElementById('new-admin-username').value;
    const password = document.getElementById('new-admin-password').value;
    const role = document.getElementById('new-admin-role').value;

    if (!username || !password) {
        await showAlert('Please fill in all fields', 'Error');
        return;
    }

    try {
        const res = await fetchAuth(`${API_BASE}/admins`, {
            method: 'POST',
            body: JSON.stringify({ username, password, role })
        });

        if (res.ok) {
            closeCreateAdminModal();
            loadAdminUsers();
            await showAlert('Admin user created successfully!', 'Success');
        } else {
            const err = await res.json();
            await showAlert(`Error: ${err.detail}`, 'Error');
        }
    } catch (err) { console.error(err); }
};

// Edit Admin Modal
window.openEditAdminModal = (id, username, role) => {
    document.getElementById('edit-admin-id').value = id;
    document.getElementById('edit-admin-username').value = username;
    document.getElementById('edit-admin-role').value = role;
    document.getElementById('edit-admin-password').value = '';
    document.getElementById('edit-admin-modal').classList.remove('hidden');
    toggleBodyScroll(true);
};

window.closeEditAdminModal = () => {
    document.getElementById('edit-admin-modal').classList.add('hidden');
    toggleBodyScroll(false);
};

window.submitEditAdmin = async () => {
    const id = document.getElementById('edit-admin-id').value;
    const role = document.getElementById('edit-admin-role').value;
    const newPassword = document.getElementById('edit-admin-password').value;

    const updateData = { role };
    if (newPassword) {
        updateData.new_password = newPassword;
    }

    try {
        const res = await fetchAuth(`${API_BASE}/admins/${id}`, {
            method: 'PUT',
            body: JSON.stringify(updateData)
        });

        if (res.ok) {
            closeEditAdminModal();
            loadAdminUsers();
            await showAlert('Admin user updated successfully!', 'Success');
        } else {
            const err = await res.json();
            await showAlert(`Error: ${err.detail}`, 'Error');
        }
    } catch (err) { console.error(err); }
};

// Delete Admin
window.deleteAdmin = async (id, username) => {
    try {
        const password = await showConfirmModal({
            title: 'Delete Admin User',
            message: `Are you sure you want to delete <b class="text-slate-700">${username}</b>? This action cannot be undone.`,
            confirmText: 'Delete Admin',
            isDanger: true,
            requireInput: true,
            inputLabel: 'Your Admin Password',
            inputType: 'password'
        });

        if (password) {
            const res = await fetchAuth(`${API_BASE}/admins/${id}`, {
                method: 'DELETE',
                body: JSON.stringify({ password })
            });

            if (res.ok) {
                loadAdminUsers();
                await showAlert('Admin user deleted successfully!', 'Success');
            } else {
                const err = await res.json();
                await showAlert(`Error: ${err.detail}`, 'Error');
            }
        }
    } catch (err) { if (err !== 'Cancelled') console.error(err); }
};

