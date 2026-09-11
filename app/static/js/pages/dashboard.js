import apiClient from '../api/client.js';
import { showToast } from '../components/toast.js';
import { initTheme } from '../components/theme.js';
import store from '../state/store.js';

document.addEventListener('DOMContentLoaded', () => {
    initTheme();
    loadUserProfile();

    const state = store.getState();
    const activeFileNameElem = document.getElementById('active-file-name');
    const backToStudioBtn = document.getElementById('back-to-studio');
    const filialesWrapper = document.getElementById('filiales-checkbox-wrapper');
    const btnSelectAll = document.getElementById('btn-select-all-filiales');
    const btnDeselectAll = document.getElementById('btn-deselect-all-filiales');
    const btnGenerateDashboard = document.getElementById('btn-generate-dashboard');
    const progressBox = document.getElementById('pptx-progress-box');
    const progressBarFill = document.getElementById('progress-bar-fill');
    const progressStatus = document.getElementById('progress-status');
    const progressPercent = document.getElementById('progress-percent');

    if (!state.workflowSessionId) {
        showToast("Aucune session active. Veuillez d'abord importer un fichier.", "warning");
        setTimeout(() => { window.location.href = '/studio'; }, 1000);
        return;
    }

    if (activeFileNameElem) {
        activeFileNameElem.textContent = state.fileName || "Session active";
    }

    if (backToStudioBtn) {
        backToStudioBtn.addEventListener('click', () => { window.location.href = '/studio'; });
    }

    // Populate filiales checkboxes
    const filialesList = state.selectedFiliales || [];
    if (filialesWrapper) {
        filialesWrapper.innerHTML = '';
        if (filialesList.length === 0) {
            filialesWrapper.innerHTML = '<span style="font-size: 12px; color: var(--text-muted);">Aucune filiale détectée.</span>';
        } else {
            filialesList.forEach(f => {
                const label = document.createElement('label');
                label.className = 'chip-checkbox';
                const input = document.createElement('input');
                input.type = 'checkbox';
                input.value = f;
                input.checked = true;
                label.appendChild(input);
                label.appendChild(document.createTextNode(f));
                filialesWrapper.appendChild(label);
            });
        }
    }

    if (btnSelectAll) {
        btnSelectAll.addEventListener('click', () => {
            document.querySelectorAll('#filiales-checkbox-wrapper input[type="checkbox"]').forEach(cb => cb.checked = true);
        });
    }

    if (btnDeselectAll) {
        btnDeselectAll.addEventListener('click', () => {
            document.querySelectorAll('#filiales-checkbox-wrapper input[type="checkbox"]').forEach(cb => cb.checked = false);
        });
    }

    function updateProgress(percent, text) {
        if (progressBarFill) progressBarFill.style.width = `${percent}%`;
        if (progressPercent) progressPercent.textContent = `${percent}%`;
        if (progressStatus) progressStatus.textContent = text;
    }

    if (btnGenerateDashboard) {
        btnGenerateDashboard.addEventListener('click', async () => {
            const currentState = store.getState();
            if (!currentState.workflowSessionId) {
                showToast("Session expirée. Veuillez réimporter le fichier.", "danger");
                window.location.href = '/studio';
                return;
            }

            const selectedFiliales = Array.from(
                document.querySelectorAll('#filiales-checkbox-wrapper input[type="checkbox"]:checked')
            ).map(cb => cb.value);

            if (selectedFiliales.length === 0) {
                showToast("Veuillez sélectionner au moins une filiale.", "danger");
                return;
            }

            const startDate = currentState.startDate || "2026-06-01";
            const endDate = currentState.endDate || "2026-06-30";

            btnGenerateDashboard.disabled = true;
            if (progressBox) progressBox.style.display = 'block';
            updateProgress(10, "Préparation des données...");

            const formData = new FormData();
            formData.append("session_id", currentState.workflowSessionId);
            formData.append("start_date", startDate);
            formData.append("end_date", endDate);
            selectedFiliales.forEach(filiale => {
                formData.append("filiales", filiale);
            });

            try {
                updateProgress(30, "Génération des présentations par le serveur...");
                const data = await apiClient.post('/api/generate-ppt', formData);
                const results = data.results || [];

                for (let i = 0; i < results.length; i++) {
                    const { filiale, download_url } = results[i];
                    const pct = 40 + Math.round(((i + 1) / results.length) * 50);
                    updateProgress(pct, `Téléchargement du dashboard ${filiale}...`);

                    const blob = await apiClient.get(download_url);
                    const downloadUrl = window.URL.createObjectURL(blob);
                    const filename = `Dashboard_${filiale}_${startDate}_${endDate}.pptx`;

                    const a = document.createElement('a');
                    a.href = downloadUrl;
                    a.download = filename;
                    document.body.appendChild(a);
                    a.click();
                    a.remove();
                    window.URL.revokeObjectURL(downloadUrl);
                }

                updateProgress(100, "Terminé avec succès !");
                showToast(`${results.length} présentation(s) téléchargée(s) avec succès !`);
            } catch (err) {
                console.error("Erreur lors de la génération PPT:", err);
                showToast(`Erreur : ${err.message}`, "danger");
                if (progressStatus) progressStatus.textContent = "Échec de la génération";
            } finally {
                btnGenerateDashboard.disabled = false;
                setTimeout(() => {
                    if (progressBox) progressBox.style.display = 'none';
                }, 3000);
            }
        });
    }

    async function loadUserProfile() {
        try {
            const user = await apiClient.get('/api/auth/me');
            const displayNameElem = document.getElementById('user-display-name');
            if (user && displayNameElem) {
                const name = user.display_name || user.username;
                displayNameElem.textContent = name;
            }
        } catch (err) {
            if (err.status === 401) window.location.href = '/login';
        }

        const logoutBtn = document.getElementById('btn-logout');
        if (logoutBtn) {
            logoutBtn.addEventListener('click', async () => {
                try { await apiClient.post('/api/auth/logout'); }
                catch (e) { console.error("Erreur lors de la déconnexion", e); }
                finally { window.location.href = '/login'; }
            });
        }
    }
});
