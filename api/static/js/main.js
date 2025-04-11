// DOM Elements
const urlForm = document.getElementById('urlForm');
const urlInput = document.getElementById('urlInput');
const urlError = document.getElementById('urlError');
const checkButton = document.getElementById('checkButton');
const spinner = checkButton.querySelector('.spinner-border');
const resultSection = document.getElementById('resultSection');
const resultBadge = document.getElementById('resultBadge');
const resultUrl = document.getElementById('resultUrl');
const confidenceBar = document.getElementById('confidenceBar');
const warningMessage = document.getElementById('warningMessage');

// Display result
function displayResult(data) {
    resultUrl.textContent = data.url;
    resultBadge.textContent = data.result;
    resultBadge.className = `badge ${data.result === 'Legitimate' ? 'bg-success' : 'bg-danger'} me-2`;

    confidenceBar.style.width = `${data.confidence * 100}%`;
    confidenceBar.className = `progress-bar ${data.result === 'Legitimate' ? 'bg-success' : 'bg-danger'}`;
    confidenceBar.textContent = `${Math.round(data.confidence * 100)}%`;

    resultSection.classList.remove('d-none');

    // Show warning message if the site is flagged as phishing
    if (data.result === 'Phishing') {
        warningMessage.classList.remove('d-none');
    } else {
        warningMessage.classList.add('d-none');
    }
}

// Handle form submission
urlForm.addEventListener('submit', async (e) => {
    e.preventDefault();

    const url = urlInput.value.trim();

    // Reset error state
    urlError.textContent = '';
    urlInput.classList.remove('is-invalid');

    // Basic URL validation
    try {
        new URL(url);
    } catch {
        urlError.textContent = 'Please enter a valid URL';
        urlInput.classList.add('is-invalid');
        return;
    }

    // Show loading state
    spinner.classList.remove('d-none');
    checkButton.disabled = true;

    try {
        const response = await fetch('/predict', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ url })
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        displayResult(data);
        
    } catch (error) {
        urlError.textContent = 'Error checking URL. Please try again.';
        console.error('Error:', error);
    } finally {
        spinner.classList.add('d-none');
        checkButton.disabled = false;
    }
});
