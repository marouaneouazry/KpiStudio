// ===========================================================================
// auth.js — Logique de la page de connexion LDAP
// ===========================================================================
(function () {
    const loginForm = document.getElementById('login-form');
    const usernameInput = document.getElementById('username');
    const passwordInput = document.getElementById('password');
    const btnLogin = document.getElementById('btn-login');
    const loginAlert = document.getElementById('login-alert');
    const alertMsg = document.getElementById('alert-msg');

    if (!loginForm) return;

    function showAlert(message) {
        alertMsg.textContent = message;
        loginAlert.style.display = 'flex';
    }

    function hideAlert() {
        loginAlert.style.display = 'none';
    }

    loginForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        hideAlert();

        const username = usernameInput.value.trim();
        const password = passwordInput.value;

        if (!username || !password) {
            showAlert("Veuillez saisir votre identifiant et votre mot de passe.");
            return;
        }

        btnLogin.disabled = true;
        btnLogin.innerHTML = `<i class="ti ti-loader-2 spin"></i> Connexion en cours...`;

        try {
            const response = await fetch('/api/auth/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ username, password })
            });

            const data = await response.json();

            if (!response.ok) {
                const errorMessage = data.detail || "Échec de l'authentification.";
                showAlert(errorMessage);
                return;
            }

            if (typeof showToast === 'function') {
                showToast("Connexion réussie ! Redirection...");
            }

            // Rediriger vers la page principale (Dashboard)
            setTimeout(() => {
                window.location.href = '/';
            }, 500);

        } catch (err) {
            console.error("Erreur réseau lors du login :", err);
            showAlert("Impossible de contacter le serveur d'authentification.");
        } finally {
            btnLogin.disabled = false;
            btnLogin.innerHTML = `<i class="ti ti-login"></i> Se connecter`;
        }
    });
})();
