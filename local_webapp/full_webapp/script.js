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

let currentResponseID = null;

function sendQuestion() {
    const question = document.getElementById('question').value;
    const BEARER_TOKEN = sessionStorage.getItem('BEARER_TOKEN');
    const sendButton = document.querySelector('button[onclick="sendQuestion()"]');
    const chatMessagesDiv = document.querySelector('.chat-messages');

    // Disable the send button
    sendButton.disabled = true;

    // Display user's question
    const userMessage = document.createElement('div');
    userMessage.className = 'user-message';
    userMessage.innerHTML = `<strong>You:</strong> ${question}`;
    chatMessagesDiv.appendChild(userMessage);

    // Show "thinking..." message for the bot
    const thinkingMessage = document.createElement('div');
    thinkingMessage.className = 'bot-message thinking';
    thinkingMessage.innerHTML = `<strong>Bot:</strong> thinking...`;
    chatMessagesDiv.appendChild(thinkingMessage);

    fetch(`${API_BASE_URL}/chat`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ Authorization: BEARER_TOKEN, question: question })
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
        currentResponseID = data.responseID; // Store the response ID
        const botMessage = document.createElement('div');
        botMessage.className = 'bot-message';
        botMessage.innerHTML = `<strong>Bot:</strong> ${data.response}`;
        chatMessagesDiv.appendChild(botMessage);

        // Remove the "thinking..." message
        const thinkingElem = document.querySelector('.thinking');
        if (thinkingElem) thinkingElem.remove();

        // Show feedback buttons
        const feedbackButtons = document.querySelector('.feedback-buttons');
        if (feedbackButtons) feedbackButtons.hidden = false;
    })
    .catch(error => {
        console.error('Error:', error);
        const errorMessage = document.createElement('div');
        errorMessage.className = 'bot-message';
        errorMessage.innerHTML = `<strong>Bot:</strong> Error: ${error.message}`;
        chatMessagesDiv.appendChild(errorMessage);
    })
    .finally(() => {
        // Re-enable the send button
        sendButton.disabled = false;
    });
}

document.getElementById('likeBtn').addEventListener('click', function() {
    toggleActiveState(this, document.getElementById('dislikeBtn'));
    sendFeedback(true);
});

document.getElementById('dislikeBtn').addEventListener('click', function() {
    toggleActiveState(this, document.getElementById('likeBtn'));
    sendFeedback(false);
});

function toggleActiveState(currentBtn, otherBtn) {
    if (currentBtn.classList.contains('active')) {
        currentBtn.classList.remove('active');
    } else {
        currentBtn.classList.add('active');
        otherBtn.classList.remove('active');
    }
}

function sendFeedback(liked) {
    const BEARER_TOKEN = sessionStorage.getItem('BEARER_TOKEN');

    fetch(`${API_BASE_URL}/feedback`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ Authorization: BEARER_TOKEN, responseID: currentResponseID, is_liked: liked })
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
        // Handle successful feedback submission (e.g., show a thank you message or hide the buttons)
    })
    .catch(error => {
        console.error('Error:', error);
    });
}
