import apiClient from '../api/client.js';
import { showToast } from '../components/toast.js';
import { initTheme } from '../components/theme.js';

document.addEventListener('DOMContentLoaded', () => {
    initTheme();
    loadUserProfile();

    // DOM Elements
    const backToExcelBtn = document.getElementById('back-to-excel');
    const statTotal = document.getElementById('stat-total');
    const stat2j = document.getElementById('stat-2j');
    const stat5j = document.getElementById('stat-5j');
    const stat15j = document.getElementById('stat-15j');

    const tabCountAll = document.getElementById('tab-count-all');
    const tabCount2 = document.getElementById('tab-count-2');
    const tabCount5 = document.getElementById('tab-count-5');
    const tabCount15 = document.getElementById('tab-count-15');

    const filterTabs = document.querySelectorAll('.sla-tab-btn');
    const searchInput = document.getElementById('search-subdomain');
    const tableBody = document.getElementById('sla-table-body');

    // Create / Edit Modal Elements
    const btnOpenCreateModal = document.getElementById('btn-open-create-modal');
    const modalSla = document.getElementById('modal-sla');
    const modalSlaTitle = document.getElementById('modal-sla-title');
    const btnCloseModalSla = document.getElementById('btn-close-modal-sla');
    const btnCancelModalSla = document.getElementById('btn-cancel-modal-sla');
    const formSla = document.getElementById('form-sla');
    const modalSlaName = document.getElementById('modal-sla-name');
    const modalSlaCategory = document.getElementById('modal-sla-category');
    const slaEditOldName = document.getElementById('sla-edit-old-name');
    const slaEditOldCategory = document.getElementById('sla-edit-old-category');

    // Delete Modal Elements
    const modalDelete = document.getElementById('modal-delete');
    const btnCloseModalDelete = document.getElementById('btn-close-modal-delete');
    const btnCancelModalDelete = document.getElementById('btn-cancel-modal-delete');
    const btnConfirmDelete = document.getElementById('btn-confirm-delete');
    const deleteTargetText = document.getElementById('delete-target-text');

    // State
    let slaMapping = { "2": [], "5": [], "15": [] };
    let currentFilter = 'all';
    let currentSearch = '';
    let itemToDelete = null;

    // Navigation
    if (backToExcelBtn) {
        backToExcelBtn.addEventListener('click', () => {
            window.location.href = '/excel';
        });
    }

    // -----------------------------------------------------------------------
    // FETCH SLA MAPPING
    // -----------------------------------------------------------------------
    async function loadSlaMapping() {
        try {
            const data = await apiClient.get('/api/sla-mapping');
            slaMapping = {
                "2": Array.isArray(data["2"]) ? data["2"] : [],
                "5": Array.isArray(data["5"]) ? data["5"] : [],
                "15": Array.isArray(data["15"]) ? data["15"] : []
            };
            updateStats();
            renderTable();
        } catch (err) {
            console.error("Erreur chargement SLA mapping:", err);
            showToast(`Erreur de chargement : ${err.message}`, "danger");
            if (tableBody) {
                tableBody.innerHTML = `
                    <tr>
                        <td colspan="5" style="text-align: center; color: var(--danger-text); padding: 24px;">
                            <i class="ti ti-alert-triangle"></i> Impossible de charger le fichier SLA mapping.
                        </td>
                    </tr>
                `;
            }
        }
    }

    // -----------------------------------------------------------------------
    // STATS & TABS COUNT
    // -----------------------------------------------------------------------
    function updateStats() {
        const count2 = slaMapping["2"].length;
        const count5 = slaMapping["5"].length;
        const count15 = slaMapping["15"].length;
        const total = count2 + count5 + count15;

        if (statTotal) statTotal.textContent = total;
        if (stat2j) stat2j.textContent = count2;
        if (stat5j) stat5j.textContent = count5;
        if (stat15j) stat15j.textContent = count15;

        if (tabCountAll) tabCountAll.textContent = total;
        if (tabCount2) tabCount2.textContent = count2;
        if (tabCount5) tabCount5.textContent = count5;
        if (tabCount15) tabCount15.textContent = count15;
    }

    // -----------------------------------------------------------------------
    // RENDER TABLE
    // -----------------------------------------------------------------------
    function renderTable() {
        if (!tableBody) return;

        // Flatten mapping to array with items { name, sla }
        const allItems = [];
        ["2", "5", "15"].forEach(cat => {
            (slaMapping[cat] || []).forEach(name => {
                allItems.push({ name, sla: cat });
            });
        });

        // Filter by category
        let filtered = allItems;
        if (currentFilter !== 'all') {
            filtered = filtered.filter(item => item.sla === currentFilter);
        }

        // Filter by search query
        if (currentSearch) {
            const q = currentSearch.toLowerCase();
            filtered = filtered.filter(item => item.name.toLowerCase().includes(q));
        }

        // Sort alphabetically by name
        filtered.sort((a, b) => a.name.localeCompare(b.name, 'fr', { sensitivity: 'base' }));

        if (filtered.length === 0) {
            tableBody.innerHTML = `
                <tr>
                    <td colspan="5" style="text-align: center; color: var(--text-muted); padding: 32px 16px;">
                        <i class="ti ti-search-off" style="font-size: 24px; display: block; margin-bottom: 8px;"></i>
                        Aucun sous-domaine ne correspond à vos critères.
                    </td>
                </tr>
            `;
            return;
        }

        tableBody.innerHTML = '';
        filtered.forEach((item, index) => {
            const tr = document.createElement('tr');

            // Badge styling
            let badgeClass = 'badge-sla-5';
            let labelText = 'Standard (5 jours)';
            if (item.sla === '2') {
                badgeClass = 'badge-sla-2';
                labelText = 'Urgent (2 jours)';
            } else if (item.sla === '15') {
                badgeClass = 'badge-sla-15';
                labelText = 'Complexe (15 jours)';
            }

            tr.innerHTML = `
                <td style="text-align: center; color: var(--text-muted); font-size: 12px;">${index + 1}</td>
                <td>
                    <strong style="color: var(--text-main);">${escapeHtml(item.name)}</strong>
                </td>
                <td>
                    <span class="badge-sla ${badgeClass}">
                        <i class="ti ti-clock"></i> ${item.sla} jours
                    </span>
                </td>
                <td style="font-size: 13px; color: var(--text-muted);">${labelText}</td>
                <td style="text-align: right;">
                    <div style="display: flex; gap: 6px; justify-content: flex-end;">
                        <button class="btn-table-action btn-edit" title="Modifier" type="button">
                            <i class="ti ti-edit"></i> Modifier
                        </button>
                        <button class="btn-table-action delete btn-delete" title="Supprimer" type="button">
                            <i class="ti ti-trash"></i>
                        </button>
                    </div>
                </td>
            `;

            // Event Listeners for actions
            const editBtn = tr.querySelector('.btn-edit');
            const deleteBtn = tr.querySelector('.btn-delete');

            editBtn.addEventListener('click', () => openEditModal(item.name, item.sla));
            deleteBtn.addEventListener('click', () => openDeleteModal(item.name, item.sla));

            tableBody.appendChild(tr);
        });
    }

    function escapeHtml(str) {
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

    // -----------------------------------------------------------------------
    // FILTER & SEARCH HANDLERS
    // -----------------------------------------------------------------------
    filterTabs.forEach(tab => {
        tab.addEventListener('click', () => {
            filterTabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            currentFilter = tab.getAttribute('data-filter') || 'all';
            renderTable();
        });
    });

    if (searchInput) {
        searchInput.addEventListener('input', (e) => {
            currentSearch = e.target.value.trim();
            renderTable();
        });
    }

    // -----------------------------------------------------------------------
    // CREATE / EDIT MODAL
    // -----------------------------------------------------------------------
    function openCreateModal() {
        if (!modalSla) return;
        modalSlaTitle.innerHTML = `
            <i class="ti ti-plus" style="color: var(--primary);"></i>
            <span>Nouveau Sous-Domaine SLA</span>
        `;
        slaEditOldName.value = '';
        slaEditOldCategory.value = '';
        modalSlaName.value = '';
        modalSlaCategory.value = (currentFilter !== 'all') ? currentFilter : '5';
        modalSla.style.display = 'flex';
        modalSlaName.focus();
    }

    function openEditModal(name, sla) {
        if (!modalSla) return;
        modalSlaTitle.innerHTML = `
            <i class="ti ti-edit" style="color: var(--primary);"></i>
            <span>Modifier le Sous-Domaine</span>
        `;
        slaEditOldName.value = name;
        slaEditOldCategory.value = sla;
        modalSlaName.value = name;
        modalSlaCategory.value = sla;
        modalSla.style.display = 'flex';
        modalSlaName.focus();
    }

    function closeModalSla() {
        if (!modalSla) return;
        modalSla.style.display = 'none';
    }

    if (btnOpenCreateModal) {
        btnOpenCreateModal.addEventListener('click', openCreateModal);
    }
    if (btnCloseModalSla) {
        btnCloseModalSla.addEventListener('click', closeModalSla);
    }
    if (btnCancelModalSla) {
        btnCancelModalSla.addEventListener('click', closeModalSla);
    }
    if (modalSla) {
        modalSla.addEventListener('click', (e) => {
            if (e.target === modalSla) closeModalSla();
        });
    }

    if (formSla) {
        formSla.addEventListener('submit', async (e) => {
            e.preventDefault();
            const oldName = slaEditOldName.value;
            const oldCategory = slaEditOldCategory.value;
            const newName = modalSlaName.value.trim();
            const newCategory = modalSlaCategory.value;

            if (!newName) {
                showToast("Le nom du sous-domaine est requis.", "warning");
                return;
            }

            try {
                if (oldName) {
                    // Update
                    const res = await apiClient.put('/api/sla-mapping', {
                        old_name: oldName,
                        new_name: newName,
                        old_sla: oldCategory,
                        new_sla: newCategory
                    });
                    if (res.sla_mapping) {
                        slaMapping = res.sla_mapping;
                    }
                    showToast(res.message || "Sous-domaine mis à jour avec succès !");
                } else {
                    // Create
                    const res = await apiClient.post('/api/sla-mapping', {
                        name: newName,
                        sla: newCategory
                    });
                    if (res.sla_mapping) {
                        slaMapping = res.sla_mapping;
                    }
                    showToast(res.message || "Sous-domaine créé avec succès !");
                }

                updateStats();
                renderTable();
                closeModalSla();
            } catch (err) {
                console.error("Erreur enregistrement sous-domaine :", err);
                showToast(`Erreur : ${err.message}`, "danger");
            }
        });
    }

    // -----------------------------------------------------------------------
    // DELETE CONFIRMATION MODAL
    // -----------------------------------------------------------------------
    function openDeleteModal(name, sla) {
        itemToDelete = { name, sla };
        if (deleteTargetText) {
            deleteTargetText.innerHTML = `<strong>${escapeHtml(name)}</strong> (Catégorie : ${sla} jours)`;
        }
        if (modalDelete) {
            modalDelete.style.display = 'flex';
        }
    }

    function closeModalDelete() {
        itemToDelete = null;
        if (modalDelete) {
            modalDelete.style.display = 'none';
        }
    }

    if (btnCloseModalDelete) {
        btnCloseModalDelete.addEventListener('click', closeModalDelete);
    }
    if (btnCancelModalDelete) {
        btnCancelModalDelete.addEventListener('click', closeModalDelete);
    }
    if (modalDelete) {
        modalDelete.addEventListener('click', (e) => {
            if (e.target === modalDelete) closeModalDelete();
        });
    }

    if (btnConfirmDelete) {
        btnConfirmDelete.addEventListener('click', async () => {
            if (!itemToDelete) return;
            const { name, sla } = itemToDelete;

            try {
                const res = await apiClient.delete(`/api/sla-mapping/${encodeURIComponent(sla)}/${encodeURIComponent(name)}`);
                if (res.sla_mapping) {
                    slaMapping = res.sla_mapping;
                } else {
                    // Fallback local remove
                    if (slaMapping[sla]) {
                        slaMapping[sla] = slaMapping[sla].filter(n => n !== name);
                    }
                }
                showToast(res.message || "Sous-domaine supprimé avec succès !");
                updateStats();
                renderTable();
                closeModalDelete();
            } catch (err) {
                console.error("Erreur suppression sous-domaine :", err);
                showToast(`Erreur : ${err.message}`, "danger");
            }
        });
    }

    // -----------------------------------------------------------------------
    // USER PROFILE & LOGOUT
    // -----------------------------------------------------------------------
    async function loadUserProfile() {
        const userDisplayName = document.getElementById('user-display-name');
        const btnLogout = document.getElementById('btn-logout');

        if (btnLogout) {
            btnLogout.addEventListener('click', async () => {
                try {
                    await apiClient.post('/auth/logout');
                } catch (e) {
                    // Ignore error on logout
                }
                window.location.href = '/login';
            });
        }

        try {
            const user = await apiClient.get('/auth/me');
            if (userDisplayName && user && user.username) {
                userDisplayName.textContent = user.display_name || user.username;
            }
        } catch (e) {
            // Ignored if unauthenticated, router will redirect
        }
    }

    // Initial Load
    loadSlaMapping();
});
