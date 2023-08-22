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
    const chatBox = document.querySelector('.chat-box');
    const BEARER_TOKEN = sessionStorage.getItem('BEARER_TOKEN');
    const sendButton = document.querySelector('button[onclick="sendQuestion()"]');

    // Append user message to chat box
    const userMessage = document.createElement('div');
    userMessage.className = 'user-message';
    userMessage.innerText = question;
    chatBox.appendChild(userMessage);

    // Append "thinking..." bot message
    const thinkingMessage = document.createElement('div');
    thinkingMessage.className = 'bot-message';
    thinkingMessage.innerText = 'thinking...';
    chatBox.appendChild(thinkingMessage);

    // Disable the send button
    sendButton.disabled = true;

    fetch(`${API_BASE_URL}/chat`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({Authorization: BEARER_TOKEN, question: question })
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
        thinkingMessage.innerText = data.response; // Update the bot's message
        document.querySelector('.feedback-buttons').hidden = false; // Show feedback buttons
    })
    .catch(error => {
        console.error('Error:', error);
        thinkingMessage.innerText = `Error: ${error.message}`; // Update the bot's message with error
    })
    .finally(() => {
        // Re-enable the send button
        sendButton.disabled = false;
        // Scroll to the bottom of the chat box
        chatBox.scrollTop = chatBox.scrollHeight;
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
