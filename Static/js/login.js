//LOGIN FORM API
const loginForm = document.querySelector('.login-fields');
const loginError = document.getElementById('login-error');
const loginButton = loginForm.querySelector('button[type="submit"]');
let loginErrorTimer;

function showLoginError(message) {
    window.clearTimeout(loginErrorTimer);
    loginError.textContent = message;
    loginError.hidden = false;
    loginErrorTimer = window.setTimeout(() => {
        loginError.hidden = true;
    }, 6000);
}

async function submitLogin(event) {
    event.preventDefault();
    window.clearTimeout(loginErrorTimer);
    loginError.hidden = true;
    loginButton.disabled = true;

    try {
        const response = await fetch(loginForm.dataset.apiUrl, {
            method: 'POST',
            credentials: 'same-origin',
            headers: {
                'Accept': 'application/json',
                'Content-Type': 'application/json',
                'X-CSRFToken': loginForm.elements.csrfmiddlewaretoken.value,
            },
            body: JSON.stringify({
                username: loginForm.elements.username.value,
                role: loginForm.elements.role.value,
                password: loginForm.elements.password.value,
            }),
        });
        const result = await response.json();

        if (!response.ok) {
            showLoginError(result.message || 'Unable to sign in.');
            return;
        }

        window.location.assign(result.redirect_url);
    } catch {
        showLoginError('Could not reach the sign-in service. Please try again.');
    } finally {
        loginButton.disabled = false;
    }
}

loginForm.addEventListener('submit', submitLogin);