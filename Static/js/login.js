//LOGIN FORM API
const loginForm = document.querySelector('.login-fields');
const loginError = document.getElementById('login-error');
const loginButton = loginForm.querySelector('button[type="submit"]');

async function submitLogin(event) {
    event.preventDefault();
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
            loginError.textContent = result.message || 'Unable to sign in.';
            loginError.hidden = false;
            return;
        }

        window.location.assign(result.redirect_url);
    } catch {
        loginError.textContent = 'Could not reach the sign-in service. Please try again.';
        loginError.hidden = false;
    } finally {
        loginButton.disabled = false;
    }
}

loginForm.addEventListener('submit', submitLogin);