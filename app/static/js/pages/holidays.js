// ============================================================================
// HOLIDAYS PAGE
// ============================================================================
import { initTheme } from '../components/theme.js';

const btnOpenHolidays = document.getElementById("btn-open-holidays");
const viewHolidays = document.getElementById("view-holidays");
const backFromHolidays = document.getElementById("back-from-holidays");
const backToExcel = document.getElementById("back-to-excel");

const yearSelect = document.getElementById("holiday-year-select");
const statusBadge = document.getElementById("holiday-calendar-status-badge");
const holidaysTableBody = document.getElementById("holidays-table-body");

const btnCreateNextYear = document.getElementById("btn-create-next-year");
const btnAddHolidayRow = document.getElementById("btn-add-holiday-row");
const btnSaveHolidays = document.getElementById("btn-save-holidays");
const btnCancelHolidays = document.getElementById("btn-cancel-holidays");
const btnValidateCalendar = document.getElementById("btn-validate-calendar");
const btnReopenCalendar = document.getElementById("btn-reopen-calendar");

const holidayModal = document.getElementById("holiday-modal");
const modalHolidayTitle = document.getElementById("modal-holiday-title");
const modalClose = document.getElementById("modal-holiday-close");
const modalCancel = document.getElementById("btn-modal-cancel");
const modalSave = document.getElementById("btn-modal-save");

const nameInput = document.getElementById("holiday-name-input");
const typeSelect = document.getElementById("holiday-type-select");
const datesListContainer = document.getElementById("holiday-dates-list");
const btnAddDatePicker = document.getElementById("btn-add-date-picker");

let currentCalendar = null;
let originalCalendar = null;
let editingHolidayId = null;

// ============================================================================
// DEBUG
// ============================================================================

console.log("[HOLIDAYS] JavaScript chargé");

// ============================================================================
// TOAST
// ============================================================================

function showToast(message, type = "info") {
    const toast = document.getElementById("toast");
    const toastMsg = document.getElementById("toast-msg");

    if (toast && toastMsg) {
        toastMsg.textContent = message;
        toast.className = `toast show ${type}`;

        setTimeout(() => {
            toast.className = "toast";
        }, 4000);
    } else {
        alert(message);
    }
}

// ============================================================================
// CLONE
// ============================================================================

function cloneCalendar(calendar) {
    if (!calendar) {
        return null;
    }

    return JSON.parse(JSON.stringify(calendar));
}

// ============================================================================
// UNSAVED CHANGES
// ============================================================================

function hasUnsavedChanges() {
    if (!currentCalendar || !originalCalendar) {
        return false;
    }

    return (
        JSON.stringify(currentCalendar) !==
        JSON.stringify(originalCalendar)
    );
}

// ============================================================================
// LOAD YEARS
// ============================================================================

async function loadYearsList(selectYear = null) {
    try {
        const response = await fetch("/api/holidays/years", {
            method: "GET",
            credentials: "same-origin"
        });

        if (!response.ok) {
            throw new Error(
                `Erreur lors du chargement des années (${response.status}).`
            );
        }

        const data = await response.json();
        const years = Array.isArray(data.years) ? data.years : [];

        yearSelect.replaceChildren();

        years.forEach(item => {
            const option = document.createElement("option");

            option.value = String(item.year);

            option.textContent =
                `${item.year} (${item.status === "validated"
                    ? "Validé"
                    : "Brouillon"
                })`;

            yearSelect.appendChild(option);
        });

        if (years.length === 0) {
            currentCalendar = null;
            originalCalendar = null;
            renderCalendar();
            return;
        }

        const targetYear =
            selectYear !== null
                ? selectYear
                : years[years.length - 1].year;

        yearSelect.value = String(targetYear);

        await loadCalendarForYear(targetYear);

    } catch (error) {
        console.error("[HOLIDAYS] loadYearsList:", error);

        showToast(
            error.message || "Erreur lors du chargement des années.",
            "danger"
        );
    }
}

// ============================================================================
// LOAD CALENDAR
// ============================================================================

async function loadCalendarForYear(year) {
    try {
        const response = await fetch(
            `/api/holidays/${encodeURIComponent(year)}`,
            {
                method: "GET",
                credentials: "same-origin"
            }
        );

        if (!response.ok) {
            throw new Error(
                `Impossible de charger le calendrier ${year} (${response.status}).`
            );
        }

        const calendar = await response.json();

        currentCalendar = calendar;

        // Référence de la dernière version sauvegardée.
        originalCalendar = cloneCalendar(calendar);

        renderCalendar();

    } catch (error) {
        console.error("[HOLIDAYS] loadCalendarForYear:", error);

        showToast(
            error.message || "Erreur lors du chargement du calendrier.",
            "danger"
        );
    }
}

// ============================================================================
// RENDER
// ============================================================================

function renderCalendar() {
    if (!currentCalendar) {
        holidaysTableBody.replaceChildren();

        if (statusBadge) {
            statusBadge.textContent = "";
        }

        return;
    }

    const isDraft =
        currentCalendar.status === "draft";

    // ------------------------------------------------------------------------
    // STATUS
    // ------------------------------------------------------------------------

    if (currentCalendar.status === "validated") {
        statusBadge.textContent = "VALIDÉ";
        statusBadge.className =
            "badge-status status-validated";

        if (btnValidateCalendar) {
            btnValidateCalendar.style.display = "none";
        }

        if (btnReopenCalendar) {
            btnReopenCalendar.style.display = "inline-flex";
        }
    } else {
        statusBadge.textContent = "BROUILLON";
        statusBadge.className =
            "badge-status status-draft";

        if (btnValidateCalendar) {
            btnValidateCalendar.style.display = "inline-flex";
        }

        if (btnReopenCalendar) {
            btnReopenCalendar.style.display = "none";
        }
    }

    // Annuler disponible sur les brouillons.
    if (btnCancelHolidays) {
        btnCancelHolidays.style.display =
            isDraft ? "inline-flex" : "none";
    }

    // ------------------------------------------------------------------------
    // TABLE
    // ------------------------------------------------------------------------

    holidaysTableBody.replaceChildren();

    const holidays =
        Array.isArray(currentCalendar.holidays)
            ? currentCalendar.holidays
            : [];

    if (holidays.length === 0) {
        const row = document.createElement("tr");
        const cell = document.createElement("td");

        cell.colSpan = 5;
        cell.style.textAlign = "center";
        cell.style.padding = "24px";
        cell.style.color = "var(--text-muted)";
        cell.textContent =
            "Aucun jour férié configuré pour cette année.";

        row.appendChild(cell);
        holidaysTableBody.appendChild(row);

        return;
    }

    holidays.forEach(holiday => {
        const row = document.createElement("tr");

        // --------------------------------------------------------------------
        // TYPE
        // --------------------------------------------------------------------

        let typeLabel = "National";
        let typeClass = "type-national";

        if (holiday.type === "religious") {
            typeLabel = "Religieux";
            typeClass = "type-religious";
        } else if (holiday.type === "exceptional") {
            typeLabel = "Exceptionnel";
            typeClass = "type-exceptional";
        }

        const typeCell = document.createElement("td");

        const typeBadge = document.createElement("span");
        typeBadge.className = `type-badge ${typeClass}`;
        typeBadge.textContent = typeLabel;

        typeCell.appendChild(typeBadge);

        // --------------------------------------------------------------------
        // NAME
        // --------------------------------------------------------------------

        const nameCell = document.createElement("td");

        nameCell.style.fontWeight = "500";
        nameCell.textContent =
            holiday.name == null
                ? ""
                : String(holiday.name);

        // --------------------------------------------------------------------
        // DATES
        // --------------------------------------------------------------------

        const dateCell = document.createElement("td");

        const dates =
            Array.isArray(holiday.dates)
                ? holiday.dates
                : [];

        if (dates.length > 0) {
            const container =
                document.createElement("div");

            container.className =
                "date-chip-container";

            dates.forEach(dateValue => {
                const chip =
                    document.createElement("span");

                chip.className = "date-chip";

                const dateString =
                    String(dateValue);

                const parts =
                    dateString.split("-");

                const formattedDate =
                    parts.length === 3
                        ? `${parts[2]}/${parts[1]}/${parts[0]}`
                        : dateString;

                chip.appendChild(
                    document.createTextNode(
                        formattedDate
                    )
                );

                if (isDraft) {
                    chip.appendChild(
                        document.createTextNode(" ")
                    );

                    const removeIcon =
                        document.createElement("i");

                    removeIcon.className =
                        "ti ti-x date-chip-remove";

                    removeIcon.dataset.id =
                        String(holiday.id);

                    removeIcon.dataset.date =
                        dateString;

                    removeIcon.title =
                        "Supprimer la date";

                    chip.appendChild(removeIcon);
                }

                container.appendChild(chip);
            });

            dateCell.appendChild(container);

        } else {
            const empty = document.createElement("span");

            empty.style.color =
                "var(--danger-text)";

            empty.style.fontStyle =
                "italic";

            empty.style.fontSize =
                "12px";

            empty.textContent =
                "-- Aucune date (à compléter) --";

            dateCell.appendChild(empty);
        }

        // --------------------------------------------------------------------
        // STATUS
        // --------------------------------------------------------------------

        const statusCell =
            document.createElement("td");

        const status = document.createElement("span");

        const pending =
            holiday.status === "pending" ||
            dates.length === 0;

        status.className =
            pending
                ? "badge-status status-pending"
                : "badge-status status-validated";

        status.textContent =
            pending
                ? "À compléter"
                : "Validé";

        statusCell.appendChild(status);

        // --------------------------------------------------------------------
        // ACTIONS
        // --------------------------------------------------------------------

        const actionsCell =
            document.createElement("td");

        actionsCell.style.textAlign = "right";

        if (isDraft) {
            const wrapper =
                document.createElement("div");

            wrapper.style.display = "flex";
            wrapper.style.justifyContent = "flex-end";
            wrapper.style.gap = "6px";

            const editButton =
                document.createElement("button");

            editButton.type = "button";
            editButton.className =
                "btn-action-sm btn-edit-h";

            editButton.dataset.id =
                String(holiday.id);

            editButton.title = "Modifier";

            const editIcon =
                document.createElement("i");

            editIcon.className =
                "ti ti-edit";

            editButton.appendChild(editIcon);

            editButton.appendChild(
                document.createTextNode(" Modifier")
            );

            const deleteButton =
                document.createElement("button");

            deleteButton.type = "button";
            deleteButton.className =
                "btn-action-sm btn-delete-h";

            deleteButton.dataset.id =
                String(holiday.id);

            deleteButton.title = "Supprimer";

            const deleteIcon =
                document.createElement("i");

            deleteIcon.className =
                "ti ti-trash";

            deleteButton.appendChild(deleteIcon);

            deleteButton.appendChild(
                document.createTextNode(" Supprimer")
            );

            wrapper.appendChild(editButton);
            wrapper.appendChild(deleteButton);

            actionsCell.appendChild(wrapper);
        } else {
            const locked =
                document.createElement("span");

            locked.style.fontSize = "12px";
            locked.style.color =
                "var(--text-muted)";

            locked.textContent = "Verrouillé";

            actionsCell.appendChild(locked);
        }

        row.appendChild(typeCell);
        row.appendChild(nameCell);
        row.appendChild(dateCell);
        row.appendChild(statusCell);
        row.appendChild(actionsCell);

        holidaysTableBody.appendChild(row);
    });

    // ------------------------------------------------------------------------
    // DYNAMIC EVENTS
    // ------------------------------------------------------------------------

    if (isDraft) {
        document
            .querySelectorAll(".date-chip-remove")
            .forEach(icon => {
                icon.addEventListener(
                    "click",
                    event => {
                        removeDateFromHoliday(
                            event.currentTarget.dataset.id,
                            event.currentTarget.dataset.date
                        );
                    }
                );
            });

        document
            .querySelectorAll(".btn-edit-h")
            .forEach(button => {
                button.addEventListener(
                    "click",
                    event => {
                        openEditModal(
                            event.currentTarget.dataset.id
                        );
                    }
                );
            });

        document
            .querySelectorAll(".btn-delete-h")
            .forEach(button => {
                button.addEventListener(
                    "click",
                    event => {
                        deleteHoliday(
                            event.currentTarget.dataset.id
                        );
                    }
                );
            });
    }
}

// ============================================================================
// ANNULER
// ============================================================================

if (btnCancelHolidays) {
    btnCancelHolidays.addEventListener(
        "click",
        () => {
            console.log("[HOLIDAYS] Annuler cliqué");

            if (!currentCalendar) {
                showToast(
                    "Aucun calendrier chargé.",
                    "warning"
                );
                return;
            }

            if (!originalCalendar) {
                showToast(
                    "Aucune version sauvegardée disponible.",
                    "warning"
                );
                return;
            }

            if (!hasUnsavedChanges()) {
                showToast(
                    "Aucune modification à annuler.",
                    "info"
                );
                return;
            }

            const confirmed =
                window.confirm(
                    "Voulez-vous vraiment annuler toutes les modifications non enregistrées ?"
                );

            if (!confirmed) {
                return;
            }

            currentCalendar =
                cloneCalendar(originalCalendar);

            closeModal();
            renderCalendar();

            showToast(
                "Les modifications ont été annulées.",
                "success"
            );
        }
    );
}

// ============================================================================
// SUPPRIMER UNE DATE
// ============================================================================

function removeDateFromHoliday(
    holidayId,
    dateStr
) {
    if (!currentCalendar) {
        return;
    }

    const holiday =
        currentCalendar.holidays.find(
            item =>
                String(item.id) ===
                String(holidayId)
        );

    if (!holiday) {
        return;
    }

    holiday.dates =
        holiday.dates.filter(
            date => date !== dateStr
        );

    if (
        holiday.type === "religious" &&
        holiday.dates.length === 0
    ) {
        holiday.status = "pending";
    }

    renderCalendar();
}

// ============================================================================
// SUPPRIMER UNE FÊTE
// ============================================================================

function deleteHoliday(holidayId) {
    if (!currentCalendar) {
        return;
    }

    const confirmed =
        window.confirm(
            "Voulez-vous vraiment supprimer cette fête ?"
        );

    if (!confirmed) {
        return;
    }

    currentCalendar.holidays =
        currentCalendar.holidays.filter(
            item =>
                String(item.id) !==
                String(holidayId)
        );

    renderCalendar();
}

// ============================================================================
// MODAL
// ============================================================================

function openEditModal(holidayId = null) {
    editingHolidayId =
        holidayId;

    datesListContainer.replaceChildren();

    if (holidayId !== null) {
        const holiday =
            currentCalendar.holidays.find(
                item =>
                    String(item.id) ===
                    String(holidayId)
            );

        if (!holiday) {
            return;
        }

        modalHolidayTitle.textContent =
            "Éditer le jour férié / la fête";

        nameInput.value =
            holiday.name || "";

        typeSelect.value =
            holiday.type || "national";

        if (
            Array.isArray(holiday.dates) &&
            holiday.dates.length > 0
        ) {
            holiday.dates.forEach(
                date =>
                    addDatePickerInput(date)
            );
        } else {
            addDatePickerInput();
        }

    } else {
        modalHolidayTitle.textContent =
            "Ajouter un jour férié / une fête";

        nameInput.value = "";
        typeSelect.value = "national";

        addDatePickerInput();
    }

    holidayModal.style.display = "flex";

    setTimeout(() => {
        nameInput.focus();
    }, 50);
}

function addDatePickerInput(value = "") {
    const container =
        document.createElement("div");

    container.style.display = "flex";
    container.style.alignItems = "center";
    container.style.gap = "8px";

    const input =
        document.createElement("input");

    input.type = "date";
    input.className =
        "form-date-input";

    input.value = value;

    input.style.padding = "6px 10px";
    input.style.borderRadius =
        "var(--radius-sm)";
    input.style.border =
        "1px solid var(--border)";
    input.style.fontSize = "13px";

    const removeButton =
        document.createElement("button");

    removeButton.type = "button";
    removeButton.className =
        "btn-text-sm";

    removeButton.style.color =
        "var(--danger-text)";

    removeButton.title =
        "Supprimer cette date";

    const icon =
        document.createElement("i");

    icon.className = "ti ti-x";

    removeButton.appendChild(icon);

    removeButton.addEventListener(
        "click",
        () => {
            container.remove();
        }
    );

    container.appendChild(input);
    container.appendChild(removeButton);

    datesListContainer.appendChild(
        container
    );
}

function closeModal() {
    if (holidayModal) {
        holidayModal.style.display = "none";
    }

    editingHolidayId = null;
}

// ============================================================================
// MODAL EVENTS
// ============================================================================

if (btnAddDatePicker) {
    btnAddDatePicker.addEventListener(
        "click",
        () => {
            addDatePickerInput();
        }
    );
}

if (modalClose) {
    modalClose.addEventListener(
        "click",
        closeModal
    );
}

if (modalCancel) {
    modalCancel.addEventListener(
        "click",
        closeModal
    );
}

document.addEventListener(
    "keydown",
    event => {
        if (
            event.key === "Escape" &&
            holidayModal &&
            holidayModal.style.display === "flex"
        ) {
            closeModal();
        }
    }
);

if (holidayModal) {
    holidayModal.addEventListener(
        "click",
        event => {
            if (
                event.target ===
                holidayModal
            ) {
                closeModal();
            }
        }
    );
}

// ============================================================================
// SAVE MODAL
// ============================================================================

if (modalSave) {
    modalSave.addEventListener(
        "click",
        () => {
            const name =
                nameInput.value.trim();

            const type =
                typeSelect.value;

            if (!name) {
                showToast(
                    "Veuillez saisir un nom de fête.",
                    "warning"
                );
                return;
            }

            const dateInputs =
                datesListContainer.querySelectorAll(
                    "input[type='date']"
                );

            const dates = [];

            dateInputs.forEach(input => {
                if (input.value) {
                    dates.push(input.value);
                }
            });

            if (editingHolidayId !== null) {
                const holiday =
                    currentCalendar.holidays.find(
                        item =>
                            String(item.id) ===
                            String(editingHolidayId)
                    );

                if (!holiday) {
                    return;
                }

                holiday.name = name;
                holiday.type = type;

                holiday.dates =
                    Array.from(
                        new Set(dates)
                    ).sort();

                holiday.status =
                    (
                        type === "religious" &&
                        holiday.dates.length === 0
                    )
                        ? "pending"
                        : "validated";

            } else {
                const newHoliday = {
                    id:
                        `h_${currentCalendar.year}_${Date.now()}`,
                    name,
                    type,
                    status:
                        (
                            type === "religious" &&
                            dates.length === 0
                        )
                            ? "pending"
                            : "validated",
                    dates:
                        Array.from(
                            new Set(dates)
                        ).sort()
                };

                currentCalendar.holidays.push(
                    newHoliday
                );
            }

            closeModal();
            renderCalendar();
        }
    );
}

// ============================================================================
// AJOUTER UNE FÊTE
// ============================================================================

if (btnAddHolidayRow) {
    btnAddHolidayRow.addEventListener(
        "click",
        () => {
            openEditModal();
        }
    );
}

// ============================================================================
// CRÉER ANNÉE SUIVANTE
// ============================================================================

if (btnCreateNextYear) {
    btnCreateNextYear.addEventListener(
        "click",
        async () => {
            try {
                if (hasUnsavedChanges()) {
                    const confirmed =
                        window.confirm(
                            "Vous avez des modifications non enregistrées. Continuer va les annuler. Continuer ?"
                        );

                    if (!confirmed) {
                        return;
                    }
                }

                const response =
                    await fetch(
                        "/api/holidays/create-next",
                        {
                            method: "POST",
                            credentials: "same-origin",
                            headers: {
                                "Content-Type":
                                    "application/json"
                            },
                            body:
                                JSON.stringify({
                                    from_year:
                                        currentCalendar
                                            ? currentCalendar.year
                                            : null
                                })
                        }
                    );

                if (!response.ok) {
                    const errorData =
                        await response.json();

                    throw new Error(
                        errorData.detail ||
                        "Erreur lors de la création."
                    );
                }

                const newCalendar =
                    await response.json();

                currentCalendar =
                    newCalendar;

                originalCalendar =
                    cloneCalendar(
                        newCalendar
                    );

                let option =
                    yearSelect.querySelector(
                        `option[value="${newCalendar.year}"]`
                    );

                if (!option) {
                    option =
                        document.createElement(
                            "option"
                        );

                    option.value =
                        String(
                            newCalendar.year
                        );

                    option.textContent =
                        `${newCalendar.year} (Brouillon non enregistré)`;

                    yearSelect.appendChild(
                        option
                    );
                }

                yearSelect.value =
                    String(
                        newCalendar.year
                    );

                renderCalendar();

                showToast(
                    `Brouillon ${newCalendar.year} généré en mémoire. Cliquez sur Enregistrer pour le persister.`,
                    "info"
                );

            } catch (error) {
                console.error(
                    "[HOLIDAYS] create-next:",
                    error
                );

                showToast(
                    error.message ||
                    "Erreur lors de la création.",
                    "danger"
                );
            }
        }
    );
}

// ============================================================================
// ENREGISTRER — IMPORTANT
// ============================================================================

if (btnSaveHolidays) {
    btnSaveHolidays.addEventListener(
        "click",
        async () => {
            console.log(
                "[HOLIDAYS] Enregistrer cliqué"
            );

            if (!currentCalendar) {
                showToast(
                    "Aucun calendrier chargé.",
                    "warning"
                );
                return;
            }

            try {
                btnSaveHolidays.disabled = true;

                const response =
                    await fetch(
                        `/api/holidays/${encodeURIComponent(currentCalendar.year)}`,
                        {
                            method: "PUT",
                            credentials: "same-origin",
                            headers: {
                                "Content-Type":
                                    "application/json"
                            },
                            body:
                                JSON.stringify(
                                    currentCalendar
                                )
                        }
                    );

                const responseText =
                    await response.text();

                let data = null;

                try {
                    data =
                        responseText
                            ? JSON.parse(
                                responseText
                            )
                            : null;
                } catch {
                    data = null;
                }

                if (!response.ok) {
                    throw new Error(
                        data?.detail ||
                        `Erreur lors de l'enregistrement (${response.status}).`
                    );
                }

                // La version renvoyée par le serveur
                // devient la nouvelle référence.
                currentCalendar =
                    data || currentCalendar;

                originalCalendar =
                    cloneCalendar(
                        currentCalendar
                    );

                renderCalendar();

                showToast(
                    `Calendrier ${currentCalendar.year} enregistré avec succès.`,
                    "success"
                );

            } catch (error) {
                console.error(
                    "[HOLIDAYS] SAVE ERROR:",
                    error
                );

                showToast(
                    error.message ||
                    "Erreur lors de l'enregistrement.",
                    "danger"
                );

            } finally {
                btnSaveHolidays.disabled =
                    false;
            }
        }
    );
}

// ============================================================================
// VALIDER
// ============================================================================

if (btnValidateCalendar) {
    btnValidateCalendar.addEventListener(
        "click",
        async () => {
            if (!currentCalendar) {
                return;
            }

            try {
                // Première étape : sauvegarder.
                const saveResponse =
                    await fetch(
                        `/api/holidays/${encodeURIComponent(currentCalendar.year)}`,
                        {
                            method: "PUT",
                            credentials: "same-origin",
                            headers: {
                                "Content-Type":
                                    "application/json"
                            },
                            body:
                                JSON.stringify(
                                    currentCalendar
                                )
                        }
                    );

                if (!saveResponse.ok) {
                    const errorData =
                        await saveResponse.json();

                    throw new Error(
                        errorData.detail ||
                        "Erreur lors de l'enregistrement."
                    );
                }

                // Deuxième étape : valider.
                const validateResponse =
                    await fetch(
                        `/api/holidays/${encodeURIComponent(currentCalendar.year)}/validate`,
                        {
                            method: "POST",
                            credentials: "same-origin"
                        }
                    );

                if (!validateResponse.ok) {
                    const errorData =
                        await validateResponse.json();

                    throw new Error(
                        errorData.detail ||
                        "Échec de la validation."
                    );
                }

                currentCalendar =
                    await validateResponse.json();

                originalCalendar =
                    cloneCalendar(
                        currentCalendar
                    );

                renderCalendar();

                showToast(
                    `Calendrier ${currentCalendar.year} validé avec succès !`,
                    "success"
                );

            } catch (error) {
                console.error(
                    "[HOLIDAYS] validate:",
                    error
                );

                showToast(
                    error.message ||
                    "Erreur lors de la validation.",
                    "danger"
                );
            }
        }
    );
}

// ============================================================================
// ROUVRIR
// ============================================================================

if (btnReopenCalendar) {
    btnReopenCalendar.addEventListener(
        "click",
        async () => {
            if (!currentCalendar) {
                return;
            }

            try {
                const response =
                    await fetch(
                        `/api/holidays/${encodeURIComponent(currentCalendar.year)}/reopen`,
                        {
                            method: "POST",
                            credentials: "same-origin"
                        }
                    );

                if (!response.ok) {
                    const errorData =
                        await response.json();

                    throw new Error(
                        errorData.detail ||
                        "Erreur lors de la réouverture."
                    );
                }

                currentCalendar =
                    await response.json();

                originalCalendar =
                    cloneCalendar(
                        currentCalendar
                    );

                renderCalendar();

                showToast(
                    `Calendrier ${currentCalendar.year} repassé en brouillon.`,
                    "info"
                );

            } catch (error) {
                console.error(
                    "[HOLIDAYS] reopen:",
                    error
                );

                showToast(
                    error.message ||
                    "Erreur lors de la réouverture.",
                    "danger"
                );
            }
        }
    );
}

// ============================================================================
// NAVIGATION BACK
// ============================================================================

if (backToExcel) {
    backToExcel.addEventListener(
        "click",
        () => {
            if (hasUnsavedChanges()) {
                const confirmed =
                    window.confirm(
                        "Vous avez des modifications non enregistrées. Quitter cette page les annulera. Continuer ?"
                    );

                if (!confirmed) {
                    return;
                }
            }

            window.location.href = "/excel";
        }
    );
}

if (backFromHolidays) {
    backFromHolidays.addEventListener(
        "click",
        () => {
            if (hasUnsavedChanges()) {
                const confirmed =
                    window.confirm(
                        "Vous avez des modifications non enregistrées. Quitter cette page les annulera. Continuer ?"
                    );

                if (!confirmed) {
                    return;
                }
            }

            document
                .querySelectorAll(".step-view")
                .forEach(view =>
                    view.classList.remove(
                        "active"
                    )
                );

            const stepExcel =
                document.getElementById(
                    "step-3-excel"
                );

            if (stepExcel) {
                stepExcel.classList.add(
                    "active"
                );
            }

            const appCard =
                document.querySelector(
                    ".app-card"
                );

            if (appCard) {
                appCard.classList.remove(
                    "wide-view"
                );
            }
        }
    );
}

// ============================================================================
// INITIALISATION
// ============================================================================

loadYearsList();