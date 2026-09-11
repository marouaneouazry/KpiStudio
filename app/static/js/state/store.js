/**
 * Application Workflow State Store (Phase 8A)
 * Simple reactive store maintaining persistent workflow session context across pages.
 */
const STORAGE_KEY = "mantis_kpi_workflow_state";

const DEFAULT_STATE = {
    workflowSessionId: null,
    fileName: null,
    startDate: "2026-06-01",
    endDate: "2026-06-30",
    mode: null,
    dateColumn: "Date de soumission",
    selectedFiliales: [],
    selectedSlas: [2, 5, 15],
    selectedCollabs: [],
};

class Store {
    constructor() {
        this.listeners = new Set();
        this.state = this._loadInitialState();
    }

    _loadInitialState() {
        try {
            const saved = sessionStorage.getItem(STORAGE_KEY);
            if (saved) {
                return { ...DEFAULT_STATE, ...JSON.parse(saved) };
            }
        } catch (e) {
            console.warn("[Store] Unable to load state from sessionStorage:", e);
        }
        return { ...DEFAULT_STATE };
    }

    _saveState() {
        try {
            sessionStorage.setItem(STORAGE_KEY, JSON.stringify(this.state));
        } catch (e) {
            console.warn("[Store] Unable to persist state to sessionStorage:", e);
        }
    }

    getState() {
        return { ...this.state };
    }

    setState(partialState) {
        this.state = {
            ...this.state,
            ...(typeof partialState === "function" ? partialState(this.state) : partialState),
        };
        this._saveState();
        this._notify();
    }

    clearState() {
        this.state = { ...DEFAULT_STATE };
        try {
            sessionStorage.removeItem(STORAGE_KEY);
        } catch (e) {
            // ignore
        }
        this._notify();
    }

    subscribe(listener) {
        this.listeners.add(listener);
        return () => this.listeners.delete(listener);
    }

    _notify() {
        const currentState = this.getState();
        this.listeners.forEach((listener) => {
            try {
                listener(currentState);
            } catch (err) {
                console.error("[Store Listener Error]:", err);
            }
        });
    }
}

export const store = new Store();
export default store;
