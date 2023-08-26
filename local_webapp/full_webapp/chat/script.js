const API_BASE_URL = "http://127.0.0.1:8000";

function sendQuestion() {
    const question = document.getElementById('question').value;
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
        credentials: 'include',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ question: question })
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
        const botMessage = document.createElement('div');
        botMessage.className = 'bot-message';
        botMessage.innerHTML = `<strong>Bot:</strong> ${data.response}`;
        chatMessagesDiv.appendChild(botMessage);

        // Remove the "thinking..." message
        const thinkingElem = document.querySelector('.thinking');
        if (thinkingElem) thinkingElem.remove();

        // Show feedback buttons
        const feedbackButtons = document.querySelector('.feedback-buttons');
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