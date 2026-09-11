/**
 * Toast Notification Component (Phase 8A)
 * Provides a clean notification system with fallback global window binding for legacy compatibility.
 */
export function showToast(message, type = "info") {
    const toast = document.getElementById("toast");
    const toastMsg = document.getElementById("toast-msg");
    
    if (!toast || !toastMsg) {
        console.log(`[Toast ${type.toUpperCase()}] ${message}`);
        return;
    }

    toastMsg.textContent = message;
    toast.className = `toast show ${type}`;

    if (window._toastTimeout) {
        clearTimeout(window._toastTimeout);
    }

    window._toastTimeout = setTimeout(() => {
        toast.className = "toast";
    }, 3500);
}

// Preserve window global wrapper for backward compatibility with legacy scripts
if (typeof window !== "undefined") {
    window.showToast = showToast;
}
