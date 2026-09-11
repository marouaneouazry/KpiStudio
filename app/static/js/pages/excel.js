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
    const openHolidaysBtn = document.getElementById('btn-open-holidays');
    const dateColumnSelect = document.getElementById('date-column');
    const collabWrapper = document.getElementById('collab-wrapper');
    const btnAddCollab = document.getElementById('btn-add-collab');
    const btnGenerateExcel = document.getElementById('btn-generate-excel');
    const resultsWrapper = document.getElementById('results-excel-wrapper');
    const previewToggle = document.getElementById('preview-toggle');
    const previewContent = document.getElementById('preview-content');
    const previewChevron = document.getElementById('preview-chevron');
    const btnDownload = document.getElementById('btn-download');
    const btnCopy = document.getElementById('btn-copy');

    if (!state.workflowSessionId) {
        showToast(
            "Aucune session active. Veuillez d'abord importer un fichier.",
            "warning"
        );

        setTimeout(() => {
            window.location.href = '/studio';
        }, 1000);

        return;
    }

    if (activeFileNameElem) {
        activeFileNameElem.textContent =
            state.fileName || "Session active";
    }

    if (backToStudioBtn) {
        backToStudioBtn.addEventListener('click', () => {
            window.location.href = '/studio';
        });
    }

    if (openHolidaysBtn) {
        openHolidaysBtn.addEventListener('click', () => {
            window.location.href = '/holidays';
        });
    }

    const openSlaBtn = document.getElementById('btn-open-sla');
    const gotoSlaBtn = document.getElementById('btn-manage-sla');
    if (openSlaBtn) {
        openSlaBtn.addEventListener('click', () => {
            window.location.href = '/sla';
        });
    }
    if (gotoSlaBtn) {
        gotoSlaBtn.addEventListener('click', () => {
            window.location.href = '/sla';
        });
    }

    // -----------------------------------------------------------------------
    // QUICK ADD SLA SUBDOMAIN MODAL
    // -----------------------------------------------------------------------
    const btnQuickAddSla = document.getElementById('btn-quick-add-sla');
    const modalQuickAddSla = document.getElementById('modal-quick-add-sla');
    const btnCloseQuickSlaModal = document.getElementById('btn-close-quick-sla-modal');
    const btnCancelQuickSlaModal = document.getElementById('btn-cancel-quick-sla-modal');
    const formQuickAddSla = document.getElementById('form-quick-add-sla');
    const quickSlaDomainNameInput = document.getElementById('quick-sla-domain-name');
    const quickSlaCategorySelect = document.getElementById('quick-sla-category');

    function openQuickSlaModal() {
        if (!modalQuickAddSla) return;
        modalQuickAddSla.style.display = 'flex';
        if (quickSlaDomainNameInput) {
            quickSlaDomainNameInput.value = '';
            quickSlaDomainNameInput.focus();
        }
    }

    function closeQuickSlaModal() {
        if (!modalQuickAddSla) return;
        modalQuickAddSla.style.display = 'none';
    }

    if (btnQuickAddSla) {
        btnQuickAddSla.addEventListener('click', (e) => {
            e.preventDefault();
            openQuickSlaModal();
        });
    }

    if (btnCloseQuickSlaModal) {
        btnCloseQuickSlaModal.addEventListener('click', closeQuickSlaModal);
    }
    if (btnCancelQuickSlaModal) {
        btnCancelQuickSlaModal.addEventListener('click', closeQuickSlaModal);
    }

    if (modalQuickAddSla) {
        modalQuickAddSla.addEventListener('click', (e) => {
            if (e.target === modalQuickAddSla) {
                closeQuickSlaModal();
            }
        });
    }

    if (formQuickAddSla) {
        formQuickAddSla.addEventListener('submit', async (e) => {
            e.preventDefault();
            const name = quickSlaDomainNameInput ? quickSlaDomainNameInput.value.trim() : '';
            const sla = quickSlaCategorySelect ? quickSlaCategorySelect.value : '5';

            if (!name) {
                showToast("Veuillez saisir le nom du sous-domaine.", "warning");
                return;
            }

            try {
                const res = await apiClient.post('/api/sla-mapping', { name, sla });
                if (res.sla_mapping) {
                    updateSlaCounts(res.sla_mapping);
                }
                closeQuickSlaModal();
                showToast(res.message || "Sous-domaine ajouté avec succès !");
            } catch (err) {
                console.error("Erreur lors de l'ajout du sous-domaine SLA :", err);
                showToast(`Erreur : ${err.message}`, "danger");
            }
        });
    }

    function updateSlaCounts(mapping) {
        if (!mapping) return;
        const slaCount2 = document.getElementById('sla-count-2');
        const slaCount5 = document.getElementById('sla-count-5');
        const slaCount15 = document.getElementById('sla-count-15');

        if (slaCount2) slaCount2.textContent = `(${(mapping["2"] || []).length})`;
        if (slaCount5) slaCount5.textContent = `(${(mapping["5"] || []).length})`;
        if (slaCount15) slaCount15.textContent = `(${(mapping["15"] || []).length})`;
    }

    // -----------------------------------------------------------------------
    // SLA PILLS
    // -----------------------------------------------------------------------

    document
        .querySelectorAll('#sla-wrapper .sla-pill')
        .forEach(pill => {
            pill.addEventListener('click', (e) => {
                e.preventDefault();
                pill.classList.toggle('active');
            });
        });

    // -----------------------------------------------------------------------
    // PREVIEW ACCORDION
    // -----------------------------------------------------------------------

    if (previewToggle && previewContent) {
        previewToggle.addEventListener('click', () => {
            const isHidden =
                getComputedStyle(previewContent).display === 'none';

            previewContent.style.display =
                isHidden ? 'block' : 'none';

            if (previewChevron) {
                previewChevron.style.transform =
                    isHidden
                        ? 'rotate(180deg)'
                        : 'rotate(0deg)';
            }
        });
    }

    // -----------------------------------------------------------------------
    // COLLABORATOR
    // -----------------------------------------------------------------------

    function findCollabInput(name) {
        if (!collabWrapper) {
            return null;
        }

        return Array.from(
            collabWrapper.querySelectorAll(
                'input[type="checkbox"]'
            )
        ).find(
            input => input.value === name
        );
    }

    function addCollabCheckbox(
        name,
        checked = true
    ) {
        if (!collabWrapper || !name) {
            return;
        }

        const existingInput = findCollabInput(name);

        if (existingInput) {
            existingInput.checked = checked;
            return;
        }

        const label = document.createElement('label');
        label.className = 'chip-checkbox';

        const input = document.createElement('input');
        input.type = 'checkbox';
        input.value = name;
        input.checked = checked;

        const nameSpan = document.createElement('span');
        nameSpan.textContent = name;

        const deleteButton =
            document.createElement('button');

        deleteButton.type = 'button';
        deleteButton.className = 'collab-delete-btn';
        deleteButton.title =
            `Supprimer ${name}`;

        deleteButton.innerHTML =
            '<i class="ti ti-x"></i>';

        deleteButton.style.cssText = `
            margin-left: 6px;
            border: none;
            background: transparent;
            color: var(--danger-text, #ef4444);
            cursor: pointer;
            padding: 0;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            font-size: 14px;
        `;

        deleteButton.addEventListener(
            'click',
            async (event) => {
                event.preventDefault();
                event.stopPropagation();

                const confirmed = window.confirm(
                    `Voulez-vous vraiment supprimer le collaborateur "${name}" ?`
                );

                if (!confirmed) {
                    return;
                }

                try {
                    await apiClient.delete(
                        `/api/collaborators/${encodeURIComponent(name)}`
                    );

                    label.remove();

                    showToast(
                        "Collaborateur supprimé avec succès !"
                    );
                } catch (err) {
                    console.error(
                        "Erreur lors de la suppression du collaborateur :",
                        err
                    );

                    showToast(
                        `Erreur : ${err.message}`,
                        "danger"
                    );
                }
            }
        );

        label.appendChild(input);
        label.appendChild(nameSpan);
        label.appendChild(deleteButton);

        collabWrapper.insertBefore(
            label,
            btnAddCollab
        );
    }

    // -----------------------------------------------------------------------
    // ADD COLLABORATOR
    // -----------------------------------------------------------------------

    if (btnAddCollab) {
        btnAddCollab.addEventListener(
            'click',
            async () => {
                const name = prompt(
                    "Nom du collaborateur :"
                );

                if (!name || !name.trim()) {
                    return;
                }

                const cleanName = name.trim();

                try {
                    const data =
                        await apiClient.post(
                            '/api/collaborators',
                            {
                                name: cleanName
                            }
                        );

                    addCollabCheckbox(
                        cleanName,
                        true
                    );

                    showToast(
                        data.message ||
                        "Collaborateur ajouté avec succès !"
                    );

                } catch (err) {
                    console.error(
                        "Erreur lors de l'ajout du collaborateur :",
                        err
                    );

                    showToast(
                        `Erreur : ${err.message}`,
                        "danger"
                    );
                }
            }
        );
    }

    // -----------------------------------------------------------------------
    // FETCH CONFIG
    // -----------------------------------------------------------------------

    apiClient.get('/api/config')
        .then(data => {
            updateSlaCounts(data.sla_mapping);

            // Backend JSON is the only source of truth.
            const collaborators =
                data.collaborators || [];

            collaborators.forEach(name => {
                addCollabCheckbox(
                    name,
                    true
                );
            });
        })
        .catch(err => {
            console.error(
                "Erreur lors de la récupération de la configuration (/api/config) :",
                err
            );

            showToast(
                "Impossible de charger la configuration (SLA/collaborateurs).",
                "warning"
            );
        });

    let lastDownloadUrl = null;
    let lastStartDate = '';
    let lastEndDate = '';

    // -----------------------------------------------------------------------
    // GENERATE EXCEL
    // -----------------------------------------------------------------------

    if (btnGenerateExcel) {
        btnGenerateExcel.addEventListener(
            'click',
            async () => {
                const currentState =
                    store.getState();

                if (!currentState.workflowSessionId) {
                    showToast(
                        "Session expirée. Veuillez réimporter le fichier.",
                        "danger"
                    );

                    window.location.href =
                        '/studio';

                    return;
                }

                const startDate =
                    currentState.startDate ||
                    "2026-06-01";

                const endDate =
                    currentState.endDate ||
                    "2026-06-30";

                const dateColumn =
                    dateColumnSelect.value;

                const activeSlas =
                    Array.from(
                        document.querySelectorAll(
                            '#sla-wrapper .sla-pill.active'
                        )
                    ).map(
                        pill =>
                            parseInt(
                                pill.dataset.sla
                            )
                    );

                if (activeSlas.length === 0) {
                    showToast(
                        "Veuillez sélectionner au moins un SLA.",
                        "danger"
                    );

                    return;
                }

                const selectedCollabs =
                    Array.from(
                        document.querySelectorAll(
                            '#collab-wrapper input[type="checkbox"]:checked'
                        )
                    ).map(
                        cb => cb.value
                    );

                if (selectedCollabs.length === 0) {
                    showToast(
                        "Veuillez sélectionner au moins un collaborateur.",
                        "danger"
                    );

                    return;
                }

                const originalBtnContent =
                    btnGenerateExcel.innerHTML;

                btnGenerateExcel.disabled = true;

                btnGenerateExcel.innerHTML =
                    '<i class="ti ti-loader spin"></i> Calcul en cours...';

                const formData =
                    new FormData();

                formData.append(
                    "session_id",
                    currentState.workflowSessionId
                );

                formData.append(
                    "start_date",
                    startDate
                );

                formData.append(
                    "end_date",
                    endDate
                );

                formData.append(
                    "date_column",
                    dateColumn
                );

                formData.append(
                    "sla_groups",
                    JSON.stringify(
                        activeSlas
                    )
                );

                formData.append(
                    "collaborators",
                    JSON.stringify(
                        selectedCollabs
                    )
                );

                try {
                    const data =
                        await apiClient.post(
                            '/api/generate-report',
                            formData
                        );

                    const stats =
                        data.stats || {};

                    lastDownloadUrl =
                        data.download_url;

                    lastStartDate =
                        startDate;

                    lastEndDate =
                        endDate;

                    document.getElementById(
                        'kpi-sla-ap'
                    ).textContent =
                        stats.kpi_sla_ap ||
                        '0.0%';

                    document.getElementById(
                        'kpi-cloture-dans'
                    ).textContent =
                        stats.clotures_dans_delai ??
                        '-';

                    document.getElementById(
                        'kpi-cloture-hors'
                    ).textContent =
                        stats.clotures_hors_delai ??
                        '-';

                    document.getElementById(
                        'kpi-encours-dans'
                    ).textContent =
                        stats.en_cours_dans_delai ??
                        '-';

                    document.getElementById(
                        'kpi-encours-hors'
                    ).textContent =
                        stats.en_cours_hors_delai ??
                        '-';

                    const horsDelaiTickets =
                        stats.hors_delai_tickets ||
                        [];

                    const countElem =
                        document.getElementById(
                            'out-of-bound-count'
                        );

                    if (countElem) {
                        countElem.textContent =
                            horsDelaiTickets.length;
                    }

                    const tbody =
                        document.getElementById(
                            'out-of-bound-table-body'
                        );

                    if (tbody) {
                        tbody.innerHTML = '';

                        if (
                            horsDelaiTickets.length ===
                            0
                        ) {
                            tbody.innerHTML =
                                '<tr><td colspan="4" style="text-align:center; color: var(--text-muted);">Aucun ticket hors délai</td></tr>';
                        } else {
                            horsDelaiTickets.forEach(t => {
                                const tr = document.createElement('tr');

                                const tdId = document.createElement('td');
                                const strongId = document.createElement('strong');
                                strongId.textContent = `#${t.id}`;
                                tdId.appendChild(strongId);

                                const tdResume = document.createElement('td');
                                tdResume.textContent = t.resume || '';

                                const tdAssigne = document.createElement('td');
                                tdAssigne.textContent = t.assigne || '';

                                const tdStatut = document.createElement('td');
                                const spanStatut = document.createElement('span');
                                spanStatut.className = 'tag-delay';
                                spanStatut.textContent = t.statut || '';
                                tdStatut.appendChild(spanStatut);

                                tr.append(tdId, tdResume, tdAssigne, tdStatut);
                                tbody.appendChild(tr);
                            });
                        }
                    }

                    if (resultsWrapper) {
                        resultsWrapper.style.display =
                            'flex';
                    }

                    showToast(
                        "Calcul effectué avec succès !"
                    );

                } catch (err) {
                    console.error(
                        "Erreur lors du calcul Excel:",
                        err
                    );

                    showToast(
                        `Erreur : ${err.message}`,
                        "danger"
                    );

                } finally {
                    btnGenerateExcel.disabled =
                        false;

                    btnGenerateExcel.innerHTML =
                        originalBtnContent;
                }
            }
        );
    }

    // -----------------------------------------------------------------------
    // DOWNLOAD
    // -----------------------------------------------------------------------

    if (btnDownload) {
        btnDownload.addEventListener(
            'click',
            async () => {
                if (!lastDownloadUrl) {
                    showToast(
                        "Aucun rapport disponible à télécharger.",
                        "warning"
                    );

                    return;
                }

                try {
                    const blob =
                        await apiClient.get(
                            lastDownloadUrl
                        );

                    const url =
                        window.URL.createObjectURL(
                            blob
                        );

                    const a =
                        document.createElement('a');

                    a.href = url;

                    a.download =
                        `SLA du ${lastStartDate} au ${lastEndDate}.xlsx`;

                    document.body.appendChild(a);

                    a.click();

                    a.remove();

                    window.URL.revokeObjectURL(
                        url
                    );

                } catch (err) {
                    console.error(
                        "Erreur de téléchargement Excel:",
                        err
                    );

                    showToast(
                        `Erreur : ${err.message}`,
                        "danger"
                    );
                }
            }
        );
    }

    // -----------------------------------------------------------------------
    // COPY RESULTS
    // -----------------------------------------------------------------------

    if (btnCopy) {
        btnCopy.addEventListener(
            'click',
            () => {
                const slaAp =
                    document.getElementById(
                        'kpi-sla-ap'
                    ).textContent;

                const cDans =
                    document.getElementById(
                        'kpi-cloture-dans'
                    ).textContent;

                const cHors =
                    document.getElementById(
                        'kpi-cloture-hors'
                    ).textContent;

                const eDans =
                    document.getElementById(
                        'kpi-encours-dans'
                    ).textContent;

                const eHors =
                    document.getElementById(
                        'kpi-encours-hors'
                    ).textContent;

                const text =
                    `--- RÉSULTATS KPI SLA AP ---
• Taux SLA AP : ${slaAp}
• Clôturé (Dans délai) : ${cDans}
• Clôturé (Hors délai) : ${cHors}
• En cours (Dans délai) : ${eDans}
• En cours (Hors délai) : ${eHors}`;

                navigator.clipboard
                    .writeText(text)
                    .then(() => {
                        showToast(
                            "Résultats copiés dans le presse-papier !"
                        );
                    })
                    .catch(err => {
                        console.error(
                            "Erreur lors de la copie:",
                            err
                        );

                        showToast(
                            "Échec de la copie dans le presse-papier.",
                            "danger"
                        );
                    });
            }
        );
    }

    // -----------------------------------------------------------------------
    // USER PROFILE
    // -----------------------------------------------------------------------

    async function loadUserProfile() {
        try {
            const user =
                await apiClient.get(
                    '/api/auth/me'
                );

            const displayNameElem =
                document.getElementById(
                    'user-display-name'
                );

            if (user && displayNameElem) {
                const name =
                    user.display_name ||
                    user.username;

                displayNameElem.textContent =
                    name;
            }

        } catch (err) {
            if (err.status === 401) {
                window.location.href =
                    '/login';
            }
        }

        const logoutBtn =
            document.getElementById(
                'btn-logout'
            );

        if (logoutBtn) {
            logoutBtn.addEventListener(
                'click',
                async () => {
                    try {
                        await apiClient.post(
                            '/api/auth/logout'
                        );
                    } catch (e) {
                        console.error(
                            "Erreur lors de la déconnexion",
                            e
                        );
                    } finally {
                        window.location.href =
                            '/login';
                    }
                }
            );
        }
    }
});