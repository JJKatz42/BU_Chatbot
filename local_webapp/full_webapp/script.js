const API_BASE_URL = "https://busearch-wbtak2vipq-ue.a.run.app";

document.getElementById('loginBtn').addEventListener('click', function() {
    // Start the OAuth2 flow by redirecting to the /login endpoint
    window.location.href = `${API_BASE_URL}/login`;
});

// Extract JWT token from URL if present
const urlParams = new URLSearchParams(window.location.search);
const jwt_token = urlParams.get('token');
if (jwt_token) {
    sessionStorage.setItem('BEARER_TOKEN', jwt_token);
    document.querySelector('.login-container').hidden = true;
    document.querySelector('.chat-container').hidden = false;
}

function sendQuestion() {
    const question = document.getElementById('question').value;
    const BEARER_TOKEN = sessionStorage.getItem('BEARER_TOKEN');

    fetch(`${API_BASE_URL}/chat`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ question: question, Authorization: BEARER_TOKEN })
    })
    .then(response => {
        if (!response.ok) {
            return response.json().then(err => {
                throw new Error(err.error || 'Network response was not ok');
            });
        }
        return response.json();
    })
    .then(data => {
        const responseDiv = document.getElementById('response');
        responseDiv.innerHTML = data.response;
    })
    .catch(error => {
        console.error('Error:', error);
        const responseDiv = document.getElementById('response');
        responseDiv.innerHTML = error.message;
    });
}
