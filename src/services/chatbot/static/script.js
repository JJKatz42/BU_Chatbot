
let currentResponseID = null

let thinkingInterval;

let lastFeedbackDiv = null; // Variable to keep track of the last feedback div


document.getElementById('loginBtn').addEventListener('click', function() {
    // Start the OAuth2 flow by redirecting to the /login endpoint
    console.log("Login button clicked"); // Debugging line
    window.location.href = `/login`
});

// Attach click event listeners to sidebar tabs
document.querySelectorAll('.settings-sidebar-tab').forEach(tab => {
    tab.addEventListener('click', function() {
        console.log("Tab clicked"); // Debugging line
        const selectedTab = this.getAttribute('data-tab');
        switchSettingsContent(selectedTab);
    });
});

document.addEventListener('keydown', closeSettingsWithEsc);

document.getElementsByClassName('likeBtn').addEventListener('click', function() {
    toggleActiveState(this, document.getElementById('dislikeBtn'));
    sendFeedback(currentResponseID, true);
});

document.getElementsByClassName('dislikeBtn').addEventListener('click', function() {
    toggleActiveState(this, document.getElementById('likeBtn'));
    sendFeedback(currentResponseID, false);
});

function makeUrlsClickable(str) {
    // Use a regular expression to match URLs
    const urlPattern = /https?:\/\/[^\s]+/g;

    // Replace URLs in the string with anchor tags
    return str.replace(urlPattern, function(url) {
        return `<a href="${url}" target="_blank">${url}</a>`;
    });
}


function animateThinking(thinkingMsgDiv) {
    let counter = 0;
    let dots = '';
    thinkingInterval = setInterval(() => {
        if (counter < 3) {
            dots += ' .';
            counter++;
        } else {
            dots = '';
            counter = 0;
        }
        thinkingMsgDiv.innerHTML = `<strong>BUsearch:</strong> thinking${dots}`;
    }, 500);
}

function stopThinkingAnimation() {
    clearInterval(thinkingInterval);
}


function openSettings(tab) {
    const settingsPopup = document.getElementById('settingsPopup');
    const overlay = document.getElementById('overlay');

    // Show the popup and overlay
    settingsPopup.style.display = 'block';
    overlay.style.display = 'block';

    // Switch to the tab specified in the argument
    if (tab) {
        switchSettingsContent(tab);
    }
}

function closeSettings() {
    const settingsPopup = document.getElementById('settingsPopup');
    const overlay = document.getElementById('overlay');
    settingsPopup.style.display = 'none';
    overlay.style.display = 'none';
}

function closeSettingsWithEsc(event) {
    if (event.key === 'Escape') {
        closeSettings();
    }
}

function toggleDarkMode() {
    document.body.classList.toggle('dark-mode');
}

function handleEnter(event) {
    if (event.key === 'Enter') {
        sendMessage();
    }
}

function toggleActiveState(currentBtn, otherBtn) {
    if (currentBtn.classList.contains('active')) {
        currentBtn.classList.remove('active');
    } else {
        currentBtn.classList.add('active');
        otherBtn.classList.remove('active');
    }
}


function sendMessage() {

    let element = document.querySelector('.chat-response.welcome');
    element.style.display = 'none';

    const chatInput = document.getElementById('chatInput');
    const question = chatInput.value.trim();
    // Create the request payload
    const requestData = {
        question: question
    };

    const sendButton = document.querySelector('button[onclick="sendMessage()"]');
    const chatSpace = document.querySelector('.chat-space-container');

    // Clear the chat input
    chatInput.value = '';

    // Disable the send button
    sendButton.disabled = true;

    // Create and show user's question in chat
    const userMsgDiv = document.createElement('div');
    userMsgDiv.className = 'chat-response input';
    userMsgDiv.innerHTML = "<strong>You:</strong> " + question;
    chatSpace.insertBefore(userMsgDiv, chatSpace.firstChild);

    // Create and show "thinking..." message from BUsearch
    const thinkingMsgDiv = document.createElement('div');
    thinkingMsgDiv.className = 'chat-response';
    thinkingMsgDiv.innerHTML = "<strong>BUsearch:</strong> thinking";
    chatSpace.insertBefore(thinkingMsgDiv, chatSpace.firstChild);

    // Start animating the "thinking..." message
    animateThinking(thinkingMsgDiv);

    fetch(`/chat`, {
            method: 'POST',
            credentials: 'include',
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify(requestData)
        })
        .then(response => {
            stopThinkingAnimation()
            if (!response.ok) {
                return response.json().then(err => {
                    throw new Error(err.error || 'network problem.');
                });
            }
            return response.json();
        })
        .then(data => {
            stopThinkingAnimation()
            currentResponseID = data.responseID;

            // Replace "thinking..." with actual response
            // let responseText = makeUrlsClickable(data.response);

            thinkingMsgDiv.innerHTML = `${data.response}`;

            if (lastFeedbackDiv) {
                lastFeedbackDiv.style.display = 'none';
            }

            const feedbackDiv = document.createElement('div');
            feedbackDiv.className = 'feedback-buttons';
            feedbackDiv.innerHTML = `
                <button class="likeBtn" id="likeBtn-${currentResponseID}"></button>
                <button class="dislikeBtn" id="dislikeBtn-${currentResponseID}"></button>
            `;

            // Append feedback buttons to the BUsearch response div
            thinkingMsgDiv.appendChild(feedbackDiv);

            // Update the last feedback button container
            lastFeedbackDiv = feedbackDiv;

            // Attach event listeners to the newly created buttons
            document.getElementById(`likeBtn-${currentResponseID}`).addEventListener('click', function() {
                toggleActiveState(this, document.getElementById(`dislikeBtn-${currentResponseID}`));
                sendFeedback(currentResponseID, true);
            });

            document.getElementById(`dislikeBtn-${currentResponseID}`).addEventListener('click', function() {
                toggleActiveState(this, document.getElementById(`likeBtn-${currentResponseID}`));
                sendFeedback(currentResponseID, false);
            });
        })
        .catch(error => {
            stopThinkingAnimation()
            console.error('Error:', error);
            thinkingMsgDiv.innerHTML = "<strong>BUsearch:</strong> there was an error. Please reload and try again."

            // Replace "thinking..." with error message
            // thinkingMsgDiv.innerHTML = "<strong>BUsearch:</strong> Please log in using you BU email.";
        })
        .finally(() => {
            stopThinkingAnimation()
            // Re-enable the send button
            sendButton.disabled = false;
        });
}

/**
 * Send feedback to the server.
 * @param {string} responseID - The unique ID of the BUsearch's response.
 * @param {boolean} isLiked - The type of feedback, either true or false
 */
function sendFeedback(responseID, isLiked) {
    const requestData = {
        responseID: responseID,
        is_liked: isLiked
    };

    fetch(`/feedback`, {
            method: 'POST',
            credentials: 'include',
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify(requestData)
        })
        .then(response => {
            if (!response.ok) {
                return response.json().then(err => {
                    throw new Error(err.error || 'Network response was not ok');
                });
            }
            return response.json();
        })
        .catch(error => {
            console.error('Error:', error);
        });
}


// Function to switch settings content
function switchSettingsContent(selectedTab) {
    // Hide all content sections
    console.log("Switching to tab: ", selectedTab);
    const contentSections = document.querySelectorAll('.settings-content');
    contentSections.forEach(section => {
        section.style.display = 'none';
    });

    // Show the selected content section
    const selectedContent = document.querySelector(`[data-content="${selectedTab}"]`);
    if (selectedContent) {
        selectedContent.style.display = 'block';
    }
}
