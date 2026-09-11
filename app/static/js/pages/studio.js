import apiClient from '../api/client.js';
import { showToast } from '../components/toast.js';
import { initTheme } from '../components/theme.js';
import store from '../state/store.js';

document.addEventListener('DOMContentLoaded', () => {
    initTheme();
    loadUserProfile();

    const step1 = document.getElementById('step-1');
    const step2 = document.getElementById('step-2');
    const dot1 = document.getElementById('dot-1');
    const dot2 = document.getElementById('dot-2');
    const headerSubtitle = document.getElementById('header-subtitle');

    const uploadZone = document.getElementById('upload-zone');
    const fileInput = document.getElementById('file-input');
    const browseTrigger = document.getElementById('browse-trigger');
    const fileNameDisplay = document.getElementById('file-name');
    const uploadSubtext = document.getElementById('upload-subtext');
    const uploadIcon = document.getElementById('upload-icon');
    const fileSelectedBanner = document.getElementById('file-selected-banner');
    const activeFileDisplayName = document.getElementById('active-file-display-name');
    const btnChangeFile = document.getElementById('btn-change-file');

    const btnToStep2 = document.getElementById('btn-to-step-2');
    const backToStep1 = document.getElementById('back-to-step-1');
    const startDateInput = document.getElementById('start-date');
    const endDateInput = document.getElementById('end-date');
    const chooseExcelBtn = document.getElementById('choose-excel');
    const choosePptxBtn = document.getElementById('choose-pptx');

    // Restore state from store if present
    const initialState = store.getState();
    if (initialState.startDate) startDateInput.value = initialState.startDate;
    if (initialState.endDate) endDateInput.value = initialState.endDate;
    if (initialState.workflowSessionId && initialState.fileName) {
        showSelectedFileState(initialState.fileName);
    }

    function resetUploadZoneText() {
        if (fileNameDisplay) {
            fileNameDisplay.innerHTML = `Déposez votre fichier Excel ici ou <span id="browse-trigger" style="color:var(--primary); cursor:pointer; text-decoration:underline;">Parcourir</span>`;
            const newBrowseTrigger = document.getElementById('browse-trigger');
            if (newBrowseTrigger) {
                newBrowseTrigger.addEventListener('click', triggerFilePicker);
            }
        }
        if (uploadSubtext) {
            uploadSubtext.textContent = `.xlsx · .xlsm · Feuille RUN+MON`;
        }
    }

    function showSelectedFileState(name) {
        resetUploadZoneText();
        if (activeFileDisplayName) activeFileDisplayName.textContent = name;
        if (fileSelectedBanner) fileSelectedBanner.style.display = 'flex';
        if (btnToStep2) btnToStep2.disabled = false;
    }

    function triggerFilePicker(e) {
        if (e) e.stopPropagation();
        if (fileInput) fileInput.click();
    }

    if (uploadZone) {
        uploadZone.addEventListener('click', (e) => {
            // Avoid double firing if browseTrigger clicked
            if (e.target !== browseTrigger) {
                triggerFilePicker();
            }
        });
        uploadZone.addEventListener('dragover', (e) => { e.preventDefault(); uploadZone.classList.add('dragover'); });
        uploadZone.addEventListener('dragleave', () => uploadZone.classList.remove('dragover'));
        uploadZone.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadZone.classList.remove('dragover');
            if (e.dataTransfer.files.length) handleFile(e.dataTransfer.files[0]);
        });
    }

    if (browseTrigger) {
        browseTrigger.addEventListener('click', triggerFilePicker);
    }

    if (btnChangeFile) {
        btnChangeFile.addEventListener('click', triggerFilePicker);
    }

    if (fileInput) {
        fileInput.addEventListener('change', (e) => {
            if (e.target.files.length) handleFile(e.target.files[0]);
        });
    }

    async function handleFile(file) {
        const validExtensions = ['.xlsx', '.xlsm'];
        const fileExt = file.name.substring(file.name.lastIndexOf('.')).toLowerCase();

        if (!validExtensions.includes(fileExt)) {
            showToast("Erreur : veuillez choisir un fichier Excel valide (.xlsx ou .xlsm)", "danger");
            return;
        }

        if (fileNameDisplay) fileNameDisplay.innerHTML = `Importation en cours...`;
        if (uploadSubtext) uploadSubtext.textContent = "Création de la session sur le serveur...";

        const formData = new FormData();
        formData.append("file", file);

        try {
            const data = await apiClient.post('/api/upload-session', formData);
            store.setState({
                workflowSessionId: data.session_id,
                fileName: data.file_name,
                selectedFiliales: data.filiales || [],
            });

            if (uploadIcon) {
                uploadIcon.className = 'ti ti-cloud-upload';
                uploadIcon.style.color = 'var(--primary)';
            }
            showSelectedFileState(data.file_name);
            showToast("Fichier importé avec succès !");
        } catch (err) {
            console.error("Erreur lors de la création de session d'upload:", err);
            resetUploadZoneText();
            showToast(`Erreur : ${err.message}`, "danger");
        }
    }

    function goToStep2() {
        const current = store.getState();
        if (!current.workflowSessionId) {
            showToast("Veuillez d'abord importer un fichier Excel valide.", "warning");
            return;
        }
        step1.style.display = 'none';
        step2.style.display = 'block';
        dot1.classList.remove('active');
        dot2.classList.add('active');
        if (headerSubtitle) headerSubtitle.textContent = "Étape 2 sur 2 - Paramètres";
    }

    function goToStep1() {
        step2.style.display = 'none';
        step1.style.display = 'block';
        dot2.classList.remove('active');
        dot1.classList.add('active');
        if (headerSubtitle) headerSubtitle.textContent = "Étape 1 sur 2 - Importation";
    }

    if (btnToStep2) btnToStep2.addEventListener('click', goToStep2);
    if (backToStep1) backToStep1.addEventListener('click', goToStep1);

    function validateStep2AndNavigate(mode) {
        const current = store.getState();
        if (!current.workflowSessionId) {
            showToast("Session invalide. Veuillez réimporter votre fichier.", "danger");
            goToStep1();
            return;
        }

        const start = startDateInput.value;
        const end = endDateInput.value;
        if (!start || !end) {
            showToast("Veuillez sélectionner la période de début et de fin.", "warning");
            return;
        }

        store.setState({ startDate: start, endDate: end, mode: mode });
        window.location.href = mode === 'excel' ? '/excel' : '/dashboard';
    }

    if (chooseExcelBtn) {
        chooseExcelBtn.addEventListener('click', () => validateStep2AndNavigate('excel'));
    }

    if (choosePptxBtn) {
        choosePptxBtn.addEventListener('click', () => validateStep2AndNavigate('pptx'));
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
            if (err.status === 401) {
                window.location.href = '/login';
            }
        }

        const logoutBtn = document.getElementById('btn-logout');
        if (logoutBtn) {
            logoutBtn.addEventListener('click', async () => {
                try {
                    await apiClient.post('/api/auth/logout');
                } catch (e) {
                    console.error("Erreur lors de la déconnexion", e);
                } finally {
                    window.location.href = '/login';
                }
            });
        }
    }
});
