const API_BASE_URL = "http://127.0.0.1:8000";

document.getElementById('loginBtn').addEventListener('click', function() {
    // Start the OAuth2 flow by redirecting to the /login endpoint
    window.location.href = `${API_BASE_URL}/login`;
});

fetch(`${API_BASE_URL}/auth/callback`, {
    method: 'GET',
    credentials: 'include'  // Important to include cookies in cross-origin requests
})
.then(response => response.json())
.then(data => {
    console.log(data.message);  // "Cookie has been set!"
});
