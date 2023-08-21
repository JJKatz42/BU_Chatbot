const API_BASE_URL = "https://busearch-wbtak2vipq-ue.a.run.app";
const BEARER_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJlbWFpbCI6Impqa2F0ekBidS5lZHUifQ._PYi4cxWBGHa7cL90K4RNrDXC_AApqkbyCzfUwNfrx8";
            // 'Authorization': `${BEARER_TOKEN}`
function sendQuestion() {
    const question = document.getElementById('question').value;

    fetch(`${API_BASE_URL}/chat`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
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