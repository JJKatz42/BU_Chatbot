const jwt_token = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJlbWFpbCI6Impqa2F0ekBidS5lZHUifQ._PYi4cxWBGHa7cL90K4RNrDXC_AApqkbyCzfUwNfrx8';
const urlParams = new URLSearchParams(window.location.search);

const API_BASE_URL = "https://busearch-wbtak2vipq-ue.a.run.app";

let currentResponseID = null

document.getElementById('loginBtn').addEventListener('click', function() {
    // Start the OAuth2 flow by redirecting to the /login endpoint
    console.log("Login button clicked"); // Debugging line
    window.location.href = API_BASE_URL + `/login`;
});

let thinkingInterval;

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

async function fetchPageTitle(url) {
    // Fetch the HTML content of the page (this won't work in all environments due to CORS)
    const response = await fetch(url);
    const text = await response.text();

    // Extract the title tag from the HTML
    const titleMatch = text.match(/<title>(.*?)<\/title>/);
    return titleMatch ? titleMatch[1] : url;
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
                "Content-Type": "application/json"
            },
            body: JSON.stringify(requestData)
        })
        .then(response => {
            if (!response.ok) {
                return response.json().then(err => {
                    throw new Error(err.error || 'network problem.');
                });
            }
            return response.json();
        })
        .then(data => {
            currentResponseID = data.responseID;

            // Replace "thinking..." with actual response
            const responseText = data.response;

            // Detect URLs in the response text
            const urlRegex = /(https?:\/\/[^\s]+)/g;
            let modifiedResponseText = responseText;

            const urls = responseText.match(urlRegex);
            if (urls) {
                for (const url of urls) {
                    const title = fetchPageTitle(url); // Fetch the title (may not work due to CORS)
                    modifiedResponseText = modifiedResponseText.replace(url, `<a href="${url}" target="_blank">${title}</a>`);
                }
            }

            thinkingMsgDiv.innerHTML = `<strong>BUsearch:</strong> ${modifiedResponseText}`;


            // Create feedback buttons
            const feedbackDiv = document.createElement('div');
            feedbackDiv.className = 'feedback-buttons';
            feedbackDiv.innerHTML = `
                <button class="likeBtn" id="likeBtn-${currentResponseID}"></button>
                <button class="dislikeBtn" id="dislikeBtn-${currentResponseID}"></button>
            `;

            // Append feedback buttons to the BUsearch response div
            thinkingMsgDiv.appendChild(feedbackDiv);

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
            console.error('Error:', error);

            // Replace "thinking..." with error message
            thinkingMsgDiv.innerHTML = "<strong>BUsearch:</strong> Please log in using you BU email.";
        })
        .finally(() => {
            // Re-enable the send button
            sendButton.disabled = false;
        });
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

/**
 * Send feedback to the server.
 * @param {string} responseID - The unique ID of the BUsearch's response.
 * @param {boolean} isLiked - The type of feedback, either true or false
 */
function sendFeedback(responseID, isLiked) {

    fetch(`/feedback`, {
            method: 'POST',
            credentials: 'include',
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                responseID: responseID,
                is_liked: isLiked
            })
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

// Attach click event listeners to sidebar tabs
document.querySelectorAll('.settings-sidebar-tab').forEach(tab => {
    tab.addEventListener('click', function() {
        console.log("Tab clicked"); // Debugging line
        const selectedTab = this.getAttribute('data-tab');
        switchSettingsContent(selectedTab);
    });
});


document.addEventListener('keydown', closeSettingsWithEsc);

document.getElementById('likeBtn').addEventListener('click', function() {
    toggleActiveState(this, document.getElementById('dislikeBtn'));
    sendFeedback(currentResponseID, true);
});

document.getElementById('dislikeBtn').addEventListener('click', function() {
    toggleActiveState(this, document.getElementById('likeBtn'));
    sendFeedback(currentResponseID, false);
});