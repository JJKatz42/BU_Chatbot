let authorized = true;

checkAuthorization();

let currentResponseID = null

let thinkingInterval;

let lastFeedbackDiv = null; // Variable to keep track of the last feedback div

let schoolName = ''; // Initialize the variable
let logoText = '';
let profilePlaceholderText = '';

const bodyElement = document.querySelector('body');

function setBodyClassBasedOnDomain() {
    const domainToClassMap = {
        'calsearch.ai': 'cal',
        'busearch.com': 'bu'
            // Add more mappings here as needed
    };

    const currentDomain = window.location.hostname;
    const bodyClass = domainToClassMap[currentDomain];

    if (bodyClass) {
        document.body.className = bodyClass;
    }
}

document.addEventListener('DOMContentLoaded', setBodyClassBasedOnDomain);

// Check for class on the body element and update schoolName
if (bodyElement.classList.contains('cal')) {
    schoolName = 'cal';
    logoText = 'search.ai'
    profilePlaceholderText = "Regent's scholar. Pre-Haas track and hope to major in coloring and shapes. Expected graduation 2030."
    aboutText = `
    <h3>about <div class="logo"></div></h3>
    <p class="italic">version 1.0</p>
    <p>Welcome to calsearch.ai, an AI chatbot for university information.</p>

    <h3>features</h3>
    <ul>
    <li><p><span style="font-family: var(--bold-sans);">Knowledge 🧠</span> Calsearch is trained on over 300,000 berkeley.edu webpages.</p></li>
    <li><p><span style="font-family: var(--bold-sans);">Speed 🔍</span> Calsearch rapidly navigates wepages while building its answer, designed to save hours of Googling or days of waiting for a response from an advisor.</p></li>
    <li><p><span style="font-family: var(--bold-sans);">Improvement 📈</span> Calsearch gets regular knowledge updates and intelligence improvements.</p></li>
    <li><p><span style="font-family: var(--bold-sans);">Security and privacy 🔒</span> Calsearch <span style="text-decoration: underline;">never</span> sends information beyond our servers. We only collect what you tell us in the profile section.</p></li>
</ul>

<h3>what's coming</h3>
<ul>
<li><p><span style="font-family: var(--bold-sans); font-weight: bold;">Conversationality 💬</span> have an ongoing conversation with Calsearch instead of asking one question at a time.</p></li>
<li><p><span style="font-family: var(--bold-sans); font-weight: bold;">Course selection tools 🧑‍🏫</span> get personalized suggestions for the right courses to take and get help navigating the course selection process.</p></li>
</ul>


    <h3>our team</h3>
    <p>Calsearch is part of a larger group of university chatbots, with another working model at Boston University—<a href="https://app.busearch.com/" target="_blank" class="link">BUsearch</a>—and models in training at Columbia, Yale, UNC, Harvard, UMass Amherst, Emory, and others on the way. It is currently in beta as we develop more functionality.</p>
    <p>Calsearch was trained and designed by <a href="https://www.georgeflint.com/" target="_blank" class="link">George Flint, '26</a>, at Cal; BUsearch was trained and designed by Jonah Katz, '26, at BU.</p>

    <h3>join us</h3>
    <p>If you'd like to join our team, or help us port over to another university, contact us.</p>
`
} else if (bodyElement.classList.contains('bu')) {
    schoolName = 'bu';
    logoText = 'search.com'
    profilePlaceholderText = "I'm a CS major and Pell Grant student. I am expected to graduate with the class of 2027. "
    aboutText = `
    <h3>About BUsearch</h3>
    <p>Welcome to BUsearch, the informational chatbot designed to make relevant university information instantly accessible, ensuring swift and concise answers for every Boston University student.</p>

    <h3>Our Mission</h3>
    <p>At BUsearch, our mission is to empower every student at Boston University with instant access to essential information, ensuring a seamless and enriched campus experience. We believe in harnessing the power of technology to bridge the
        gap between students and the vast resources available at BU.</p>

    <h3>Our Product</h3>
    <p>BUsearch is an informational assistant custom-built for every BU student's day-to-day needs. Whether you're a freshman trying to navigate your way around campus, a senior looking for graduation details, or an international student seeking
        housing advice, BUsearch is here to assist.</p>

    <h3>Key Features</h3>
    <ul>
        <li>Instant Answers: No more waiting for appointments or sifting through web pages. Get immediate responses to your questions in just seconds.
        </li>
        <li>Comprehensive Database: From academic schedules to campus events, BUsearch covers a wide range of topics to cater to every student's needs.
        </li>
        <li>Continuous Learning: BUsearch evolves with every interaction, ensuring that the information provided is always up-to-date and relevant.
        </li>
        <li>Secure and Private: We prioritize your privacy. Rest assured, your interactions with BUsearch are confidential.
        </li>
    </ul>

    <h3>Our Team</h3>
    <p>We are a group of dedicated students across multiple universities, including Boston University, UC Berkeley, and Columbia, who are passionate about utilizing the newest technology to enhance the academic experience and streamline access
        to essential resources for students everywhere, starting with Boston University.</p>

    <h3>Join Us</h3>
    <p>We believe in the power of collaboration. If you have suggestions, feedback, or want to be a part of the team, please reach out.</p>
`
} else if (bodyElement.classList.contains('emory')) {
    schoolName = 'emory';
    logoText = 'search.com'
} else if (bodyElement.classList.contains('harvard')) {
    schoolName = 'harvard';
    logoText = 'search.com'
} else if (bodyElement.classList.contains('yale')) {
    schoolName = 'yale';
    logoText = 'search.com'
} else if (bodyElement.classList.contains('unc')) {
    schoolName = 'unc';
    logoText = 'search.com'
}

if (document.body.classList.contains('landing')) {
    document.getElementsByClassName("landing-about")[0].innerHTML = aboutText;
} else {
    document.getElementsByClassName("about-content")[0].innerHTML = aboutText;
}

if (navigator.userAgent.includes('Safari') && !navigator.userAgent.includes('Chrome')) {
    document.body.classList.add('is-safari');
}

const originalWelcomeContent = `

<div class="logo-text">Welcome to &nbsp;</div>
<div class="logo large"><span class="school-color">${schoolName}</span>search</div>
<p class="welcome-text">please login with your <strong>school email</strong> to start searching</p>
`;

const loggedInWelcomeContent = `<div class="logo-text">Welcome to&nbsp;</div>
<div class="logo large"><span class="school-color">${schoolName}</span>search</div>
<div class="suggestions-wrapper">
<div class="suggestions">
<div class="suggestion"></div>
<div class="suggestion"></div>
<div class="suggestion"></div>
<div class="suggestion"></div>
</div>
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

function detectAndFormatLists(inputText) {
    let outputText = '';
    const lines = inputText.split('\n');
    let inOrderedList = false;

    lines.forEach((line) => {
        const isListItem = line.match(/^\s*\d+\.\s+/);

        if (isListItem && !inOrderedList) {
            inOrderedList = true;
        } else if (!isListItem && inOrderedList) {
            inOrderedList = false;
        }

        if (isListItem) {
            outputText += `${line.replace(/^\s*\d+\.\s+/, '')}\n`;
        } else {
            outputText += `${line}\n`;
        }
    });

    return outputText;
}

function updateLogoDivs() {
    document.title = `${schoolName}search`
    let logoDivs = document.querySelectorAll('.logo');
    logoDivs.forEach(function(div) {
        if (div.classList.contains('long')) {
            div.innerHTML = `<span class="school-color">${schoolName}</span>${logoText}`;
        } else if (div.classList.contains('landing-logo')) {
            div.innerHTML = `Welcome&nbsp;to&nbsp;<span class="school-color">${schoolName}</span>${logoText}`;

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

if (!document.body.classList.contains('landing')) {
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
}
// BELOW: turns on active class of sendbutton if value in chatinput
// window.onload = function() {
//     const chatInput = document.querySelector('.chat-input');
//     const sendButton = document.querySelector('.send-button');

//     if (chatInput && sendButton) {
//         chatInput.addEventListener('input', function() {
//             if (this.value.trim() !== '') {
//                 sendButton.classList.add('active');
//             } else {
//                 sendButton.classList.remove('active');
//             }
//         });
//     } else {
//         console.log("error in input div activation");
//     }
// };

document.getElementById('loginBtn').addEventListener('click', function() {
    if (authorized) {
        // Logout logic
        // console.log("logout button clicked"); // Debugging line
        window.location.href = `/logout`;

        authorized = false;
        console.log("user is not authorized")
        console.log("User was authoirzed")
    } else {
        // Login logic
        // console.log("login button clicked"); // Debugging line
        window.location.href = `/login`;

        checkAuthorization('You Are Logged In!');
        console.log("user is not authorized")
        console.log("User was not authoirzed")
    }
});

document.addEventListener('keydown', closeSettingsWithEsc);

// document.getElementsByClassName('likeBtn').addEventListener('click', function() {
//     toggleActiveState(this, document.getElementById('dislikeBtn'));
//     sendFeedback(currentResponseID, true);
// });

// document.getElementsByClassName('dislikeBtn').addEventListener('click', function() {
//     toggleActiveState(this, document.getElementById('likeBtn'));
//     sendFeedback(currentResponseID, false);
// });

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

    // collectProfileInformation();

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
        event.preventDefault();
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
    userMsgDiv.innerHTML = `<p>${question}</p>`;
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
            if (!response.ok) {
                return response.text().then(err => {
                    throw new Error(err || 'network problem.');
                });
            }
            // Process the response as a stream
            const reader = response.body.getReader();
            const decoder = new TextDecoder('utf-8');
            let result = '';

            return reader.read().then(function processText({ done, value }) {
                if (done) {
                    handleCompleteResponse(result);
                    return;
                }

                const chunk = decoder.decode(value, { stream: true });
                result += chunk;

                if (result.length > 0 && document.querySelector('.loader')) {
                    // Remove loader when the first token is received
                    document.querySelector('.loader').remove();
                }

                // Process each line of the result
                const lines = result.split('\n');
                for (let i = 0; i < lines.length - 1; i++) {
                    const htmlContent = formatMarkdownToHTML(lines[i]); // Convert each line to HTML
                    botMsgDiv.innerHTML += htmlContent; // Append the HTML to the bot message div
                }

                // Keep the last incomplete line in result for further processing
                result = lines[lines.length - 1];

                return reader.read().then(processText);
            });
        })
        .catch(error => {
            console.error('Error:', error);
        })
        .finally(() => {
            sendButton.disabled = false;
            chatInput.value = '';
            updateLogoDivs();
        });

    function handleCompleteResponse(result) {
        if (result.trim()) {
            const htmlContent = formatMarkdownToHTML(result); // Convert any remaining content to HTML
            botMsgDiv.innerHTML += htmlContent;
        }
        currentResponseID = extractResponseID(result); // Assuming a function to extract ID from the result
        attachFeedbackButtons(botMsgDiv, result);
    }
}


function formatMarkdownToHTML(markdown) {
    // Initialize the HTML result
    let html = '';
    // Track whether we're inside a list or a table
    let inList = false;
    let inTable = false;

    // Split the markdown by newlines to process each line
    const lines = markdown.split('\n');
    lines.forEach((line) => {
        // Trim the line to remove leading/trailing spaces
        line = line.trim();

        // Check if the line is a header
        const headerMatch = line.match(/^(#{1,6})\s*(.*)$/);
        if (headerMatch) {
            const level = headerMatch[1].length; // Determine header level by number of hashes
            const content = headerMatch[2];
            html += `<h${level} class="response-header">${content}</h${level}>`;
            return;
        }

        // Check if the line is a table header or separator
        if (line.match(/^\|(.+)\|$/)) {
            if (!inTable) {
                html += '<table><thead><tr>';
                inTable = true;
            }
            const cells = line.split('|').slice(1, -1); // Remove leading and trailing empty strings from split
            if (line.match(/^\|[-:]+\|/)) {
                html += '</tr></thead><tbody>';
            } else {
                cells.forEach(cell => {
                    html += `<th>${cell.trim()}</th>`;
                });
                html += '</tr>';
            }
            return;
        } else if (inTable && !line.match(/^\|/)) {
            html += '</tbody></table>';
            inTable = false;
        }

        // Check if the line is a list item
        if (line.startsWith('- ')) {
            if (!inList) {
                // If not already in a list, start a new list
                html += '<ul>';
                inList = true;
            }
            // Add the list item
            html += `<li>${line.substring(2).trim()}</li>`;
        } else {
            // If we encounter a non-list line and were in a list, close the list
            if (inList) {
                html += '</ul>';
                inList = false;
            }

            // Treat non-empty lines as paragraphs
            if (line) {
                html += `<p>${line}</p>`;
            }
        }
    });

    // Close any unclosed list or table
    if (inList) {
        html += '</ul>';
    }
    if (inTable) {
        html += '</tbody></table>';
    }

    // Replace special markers and bold/italic conversions
    html = html
        .replace(/(\*\*\*|___)(.*?)\1/g, '<strong><em>$2</em></strong>') // Bold + Italic
        .replace(/(\*\*|__)(.*?)\1/g, '<strong>$2</strong>') // Bold
        .replace(/(\*|_)(.*?)\1/g, '<em>$2</em>') // Italic
        .replace(/!\[(.*?)\]\((.*?)\)/g, '<img alt="$1" src="$2" />') // Images
        .replace(/\[(.*?)\]\((.*?)\)/g, '<a href="$2" target="_blank" class="link">$1</a>'); // Links

    return html;
}

function attachFeedbackButtons(container, result) {
    currentResponseID = extractResponseID(result); // Assuming a function to extract ID from the result

    if (lastFeedbackDiv) {
        lastFeedbackDiv.style.display = 'none';
    }

    const feedbackDiv = document.createElement('div');
    feedbackDiv.className = 'feedback-buttons';
    feedbackDiv.innerHTML = `
        <button class="likeBtn" id="likeBtn-${currentResponseID}"></button>
        <button class="dislikeBtn" id="dislikeBtn-${currentResponseID}"></button>
    `;

    container.appendChild(feedbackDiv);
    lastFeedbackDiv = feedbackDiv;

    document.getElementById(`likeBtn-${currentResponseID}`).addEventListener('click', function() {
        toggleActiveState(this, document.getElementById(`dislikeBtn-${currentResponseID}`));
        sendFeedback(currentResponseID, true);
    });

    document.getElementById(`dislikeBtn-${currentResponseID}`).addEventListener('click', function() {
        toggleActiveState(this, document.getElementById(`likeBtn-${currentResponseID}`));
        sendFeedback(currentResponseID, false);
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

function collectCurrentProfileInformation() {
    fetch(`/current-profile-info`, {
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
            console.log("Data: ", data)
            document.getElementById('college').value = data.profile_info_dict['college']
            document.getElementById('major').value = data.profile_info_dict['major']
            document.getElementById('other').value = data.profile_info_dict['other']
        })
        .catch(error => {
            console.log(error)
            console.log("error caught in collectCurrentProfileInformation()");
        });
}

function collectProfileInformation() {
    var profileInfoDict = {
        'major': document.getElementById('major').value,
        'college': document.getElementById('college').value,
        'other': document.getElementById('other').value
    };
    sendProfileInformation(profileInfoDict);
}

/**
 * Send profile information to the server.
 * @param {dictionary} profile_info_dict - The type of feedback, either true or false
 */
function sendProfileInformation(profile_info_dict) {
    const requestData = {
        profile_info_dict: profile_info_dict
    };

    fetch(`/insert-profile-info`, {
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
            console.log(profile_info_dict)
                // if we want to add some UX notifier of profile information status,
                // we could do something here like saved at {last save date} -> unsaved -> saving... -> saved at {last save date}
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
            console.log("Data: ", data.is_authorized)
            let loginBtn = document.getElementById('loginBtn');
            let welcomeChatResponse = document.querySelector('.chat-response.welcome');
            let chatInput = document.querySelector('.chat-input');
            let sendButton = document.querySelector('.send-button');
            let chatInputContainer = document.querySelector('.chat-input-container');


            if (data.is_authorized === true) {
                console.log("user is authorized");
                loginBtn.textContent = "logout";
                console.log("Data: ", data.is_authorized);
                welcomeChatResponse.innerHTML = loggedInWelcomeContent;
                chatInput.classList.remove('disabled');
                sendButton.classList.remove('disabled');
                chatInputContainer.classList.remove('disabled');
                updateLogoDivs()
                    // collectProfileInformation()

                authorized = true;
            } else if (data.is_authorized === false) {
                console.log("user is not authorized");
                console.log("Data: ", data.is_authorized);
                loginBtn.textContent = "login";
                welcomeChatResponse.innerHTML = originalWelcomeContent;
                chatInput.classList.add('disabled');
                sendButton.classList.add('disabled');
                chatInputContainer.classList.add('disabled');
                updateLogoDivs()

                authorized = false;
            } else {
                console.log("user is not authorized");
                console.log("Data: ", data.is_authorized);
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
            console.log("error caught in checkAuthorization()");
            let loginBtn = document.getElementById('loginBtn');
            let welcomeChatResponse = document.querySelector('.chat-response.welcome');
            let chatInput = document.querySelector('.chat-input');
            let sendButton = document.querySelector('.send-button');
            let chatInputContainer = document.querySelector('.chat-input-container');

            console.log("user is not authorized");
            loginBtn.textContent = "login";
            if (!document.body.classList.contains('landing')) {
                welcomeChatResponse.innerHTML = originalWelcomeContent;
                chatInput.classList.add('disabled');
                sendButton.classList.add('disabled');
                chatInputContainer.classList.add('disabled');
            }

            updateLogoDivs()

            authorized = false;
        });
}


// Function to switch settings content
function switchSettingsContent(selectedTab) {
    // Hide all content sections
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
        textarea.style.height = '200px'
            // ########################################################
    } else {
        textarea.style.overflowY = 'hidden'; // Hide scroll
    }
    textarea.rows = lineCount;
}

// Usage
if (!document.body.classList.contains('landing')) {
    const textarea = document.getElementById('chatInput');
    textarea.addEventListener('input', () => autoGrowTextarea('chatInput'));
}

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

if (document.body.classList.contains('landing')) {
    function typeOutText(divId, textList, interval) {
        const divElement = document.getElementById(divId);
        let textIndex = 0;
        let charIndex = 0;
        let usedIndices = new Set();
        let deleting = false;

        function type() {
            if (usedIndices.size === textList.length) {
                usedIndices.clear();
            }

            if (!deleting && charIndex <= textList[textIndex].length) {
                divElement.innerHTML = textList[textIndex].substr(0, charIndex) + '<span class="cursor">|</span>';
                charIndex++;
            } else {
                deleting = true;
                divElement.innerHTML = textList[textIndex].substr(0, charIndex) + '<span class="cursor">|</span>';
                charIndex--;

                if (charIndex === 0) {
                    deleting = false;
                    usedIndices.add(textIndex);

                    while (usedIndices.has(textIndex)) {
                        textIndex = Math.floor(Math.random() * textList.length);
                    }
                }
            }

            setTimeout(type, interval);
        }

        type();
    }

    // Call the function
    typeOutText('suggestions', suggestions, 100);

    let toggled = false;
    document.addEventListener('DOMContentLoaded', function() {
        const aboutBtn = document.getElementById('aboutBtn');
        const landingContainer = document.querySelector('.landing-container');
        const navbarMenu = document.querySelector('.navbar-menu');
        const landingAboutContainer = document.querySelector('.landing-about-container');

        aboutBtn.addEventListener('click', function() {
            if (toggled) {
                aboutBtn.textContent = 'about';
                landingContainer.style.transform = 'translateX(0vw)';
                navbarMenu.style.width = '33vw';
                navbarMenu.style.transform = 'translateX(0vw)';
                landingAboutContainer.style.transform = 'translateX(66vw)';
            } else {
                aboutBtn.textContent = 'back';
                landingContainer.style.transform = 'translateX(-66vw)';
                navbarMenu.style.width = '34vw';
                navbarMenu.style.transform = 'translateX(-66vw)';
                landingAboutContainer.style.transform = 'translateX(0)';
            }
            toggled = !toggled;
        });
    });
}

function debug_function() {
    let welcomeChatResponse = document.querySelector('.chat-response.welcome');
    welcomeChatResponse.innerHTML = loggedInWelcomeContent;
    updateLogoDivs()

}

debug_function();

function updateBodyClassBasedOnDomain() {
    // Get the current URL of the page
    const url = window.location.hostname;

    // Check the domain and set the class name accordingly
    if (url.includes('calsearch.ai')) {
        document.body.className = 'cal';
    } else if (url.includes('busearch.com')) {
        document.body.className = 'bu';
    } else {
        document.body.className = 'bu';
    }
}

// Call the function when the page loads
// window.onload = updateBodyClassBasedOnDomain;