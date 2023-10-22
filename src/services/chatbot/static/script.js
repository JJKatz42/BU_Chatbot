let authorized = false;

checkAuthorization();

let currentResponseID = null

let thinkingInterval;

let lastFeedbackDiv = null; // Variable to keep track of the last feedback div

let schoolName = ''; // Initialize the variable
let logoText = '';
const bodyElement = document.querySelector('body');

// Check for class on the body element and update schoolName
if (bodyElement.classList.contains('cal')) {
    schoolName = 'cal';
    logoText = 'search.ai'
} else if (bodyElement.classList.contains('bu')) {
    schoolName = 'bu';
    logoText = 'search.com'
}

if (navigator.userAgent.includes('Safari') && !navigator.userAgent.includes('Chrome')) {
    document.body.classList.add('is-safari');
}

const originalWelcomeContent = `
  <div class="chat-response welcome input">
    <div class="logo-text">Welcome to </div><div class='logo large'></div>
    <p class="welcome-text">BUsearch is an informational chatbot for Boston University students.</p>
    <p class="welcome-text">To start searching, please <strong>log in using your BU email account</strong> above.
    </p>
`;

const loggedInWelcomeContent = `<div class="logo-text">Welcome to </div><div class='logo large'></div><div class="suggestions">
<div class="suggestion"></div>
<div class="suggestion"></div>
<div class="suggestion"></div>
<div class="suggestion"></div>
</div>`

const suggestions = [
    'How do I register for classes?',
    "What's the academic calendar for this semester?",
    'How do I get a parking pass?',
    'Tell me more about student housing options.',
    'Where is the financial aid office located?',
    'How do I reset my student portal password?',
    'What are the prerequisites for the course CS101?',
    'Is the Student Health Center open on weekends?',
    'How can I apply for a work-study job?',
    'Tell me about the procedures for grade appeals.',
    'Who should I contact for lost and found items?',
    'What are the deadlines for scholarship applications?',
    'Where can I find resources for international students?',
    'How do I reserve a study room in the library?',
    'What is the policy for late assignment submissions?',
    "What's the academic calendar for this year?",
    'How do I apply for on-campus housing?',
    'Tell me about study abroad options.',
    'What are the library hours?',
    'How can I join a student organization?',
    "What's the deadline for course registration?",
    'Where is the career center located?',
    'How do I get a parking pass?',
    'Tell me about meal plan options.',
    'What are some popular campus events?',
    'How do I get mental health support?',
    'What are the gym hours?',
    'How can I contact financial aid?',
    'Tell me about emergency services on campus.',
    'How do I get my transcripts?',
    "What's the process for academic advising?",
    'Where can I find a campus map?',
    'How can I report a maintenance issue?',
    'Tell me about the shuttle services.',
    'How do I set up university email on my phone?'
];

function updateLogoDivs() {
    let logoDivs = document.querySelectorAll('.logo');
    logoDivs.forEach(function(div) {
        if (div.classList.contains('long')) {
            div.innerHTML = `<span class="school-color">${schoolName}</span>${logoText}`;
        } else {
            div.innerHTML = `<span class="school-color">${schoolName}</span>search`;
        }
    });

    const suggestionElements = document.querySelectorAll('.suggestion');
    let selectedSuggestions = [];

    while (selectedSuggestions.length < suggestionElements.length) {
        const randomIndex = Math.floor(Math.random() * suggestions.length);
        const randomSuggestion = suggestions[randomIndex];
        if (!selectedSuggestions.includes(randomSuggestion)) {
            selectedSuggestions.push(randomSuggestion);
        }
    }

    suggestionElements.forEach((elem, index) => {
        elem.innerHTML = selectedSuggestions[index];
    });
}


function clearWelcomeMessage() {
    let welcomeChatResponse = document.querySelector('.chat-response.welcome');
    welcomeChatResponse.remove();
}

document.addEventListener('DOMContentLoaded', function() {
    updateLogoDivs();
    let chatSpaceContainer = document.querySelector('.chat-space-container');

    chatSpaceContainer.addEventListener('click', function(event) {
        if (event.target.classList.contains('suggestion')) {
            let suggestionText = event.target.innerHTML;
            let chatInput = document.querySelector('.chat-input');
            chatInput.value = suggestionText;
        }
    });
});

window.onload = function() {
    const chatInput = document.querySelector('.chat-input');
    const sendButton = document.querySelector('.send-button');

    if (chatInput && sendButton) {
        chatInput.addEventListener('input', function() {
            if (this.value.trim() !== '') {
                sendButton.classList.add('active');
            } else {
                sendButton.classList.remove('active');
            }
        });
    } else {
        console.log("error in input div activation");
    }
};


document.getElementById('loginBtn').addEventListener('click', function() {
    if (authorized) {
        // Logout logic
        console.log("logout button clicked"); // Debugging line
        window.location.href = `/logout`;

        authorized = false;
        console.log("user is not authorized")
    } else {
        // Login logic
        console.log("login button clicked"); // Debugging line
        window.location.href = `/login`;

        checkAuthorization('You Are Logged In!');
        console.log("user is not authorized")
    }
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
    if (element) {
        element.style.display = 'none';
        clearWelcomeMessage();
    }

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
    userMsgDiv.innerHTML = `<p><strong style="margin-right:10px">you:</strong>${question}</p>`;
    chatSpace.insertBefore(userMsgDiv, chatSpace.firstChild);

    const botMsgDiv = document.createElement('div');
    botMsgDiv.className = 'chat-response';
    botMsgDiv.innerHTML = `
    <div class="logo-container">
        <p>
            <div class="logo">
            </div>
            <strong>:</strong>
        </p>
    </div>
    <div class="loader"> 
        <div class="dot"></div>
        <div class="dot"></div>
        <div class="dot"></div>
        <div class="dot"></div>
        <div class="dot"></div>
    </div>`;
    chatSpace.insertBefore(botMsgDiv, chatSpace.firstChild);
    // Update logo divs
    updateLogoDivs();

    fetch(`/chat`, {
            method: 'POST',
            credentials: 'include',
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify(requestData)
        })
        .then(response => {
            document.querySelector('.loader').remove();
            if (!response.ok) {
                return response.json().then(err => {
                    throw new Error(err.error || 'network problem.');
                });
            }
            return response.json();
        })
        .then(data => {

            console.log("Data: ", data)
            currentResponseID = data.responseID;
            botMsgDiv.innerHTML = `<div class="logo-container"><div class="logo"></div><strong>:</strong></div>${data.response}`;

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
            botMsgDiv.appendChild(feedbackDiv);

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
            console.error('Error:', error);
        })
        .finally(() => {
            sendButton.disabled = false;
            updateLogoDivs();
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

function checkAuthorization() {
    fetch(`/is-authorized`, {
            method: 'GET',
            credentials: 'include',
            headers: {
                "Content-Type": "application/json"
            }
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
            let loginBtn = document.getElementById('loginBtn');
            let welcomeChatResponse = document.querySelector('.chat-response.welcome');
            let chatInput = document.querySelector('.chat-input');
            let sendButton = document.querySelector('.send-button');
            let chatInputContainer = document.querySelector('.chat-input-container');

            if (data.is_authorized === true) {
                console.log("user is authorized");
                loginBtn.textContent = "logout";
                welcomeChatResponse.innerHTML = loggedInWelcomeContent;
                chatInput.classList.remove('disabled');
                sendButton.classList.remove('disabled');
                chatInputContainer.classList.remove('disabled');
                updateLogoDivs()

                authorized = true;
            } else if (data.is_authorized === false) {
                console.log("user is not authorized");
                loginBtn.textContent = "login";
                welcomeChatResponse.innerHTML = originalWelcomeContent;
                chatInput.classList.add('disabled');
                sendButton.classList.add('disabled');
                chatInputContainer.classList.add('disabled');
                updateLogoDivs()

                authorized = false;
            } else {
                console.log("user is not authorized");
                loginBtn.textContent = "login";
                welcomeChatResponse.innerHTML = originalWelcomeContent;
                chatInput.classList.add('disabled');
                sendButton.classList.add('disabled');
                chatInputContainer.classList.add('disabled');
                updateLogoDivs()

                authorized = false;
            }
        })
        .catch(error => {
            console.log(error)
            console.log("BUG (catch)!!!!!");
            let loginBtn = document.getElementById('loginBtn');
            let welcomeChatResponse = document.querySelector('.chat-response.welcome');
            let chatInput = document.querySelector('.chat-input');
            let sendButton = document.querySelector('.send-button');
            let chatInputContainer = document.querySelector('.chat-input-container');

            console.log("User is not authorized");
            loginBtn.textContent = "login";
            welcomeChatResponse.innerHTML = originalWelcomeContent;
            chatInput.classList.add('disabled');
            sendButton.classList.add('disabled');
            chatInputContainer.classList.add('disabled');

            authorized = false;
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

function autoGrowTextarea(id) {
    const textarea = document.getElementById(id);
    let lineCount = textarea.value.split('\n').length;

    if (lineCount > 6) { // Cap at 6 lines
        lineCount = 6;
        textarea.style.overflowY = 'scroll'; // Enable scroll
    } else {
        textarea.style.overflowY = 'hidden'; // Hide scroll
    }
    textarea.rows = lineCount;
}

// Usage
const textarea = document.getElementById('chatInput');
textarea.addEventListener('input', () => autoGrowTextarea('chatInput'));

// Your existing function
function switchSettingsContent(selectedTab) {
    const contentSections = document.querySelectorAll('.settings-content');
    contentSections.forEach(section => {
        section.style.display = 'none';
    });

    const selectedContent = document.querySelector(`[data-content="${selectedTab}"]`);
    if (selectedContent) {
        selectedContent.style.display = 'block';
    }
}