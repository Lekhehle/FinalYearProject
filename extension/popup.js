document.addEventListener('DOMContentLoaded', function() {
    const checkButton = document.getElementById('checkPage');
    const loadingDiv = document.getElementById('loading');
    const resultDiv = document.getElementById('result');

    // Get the last check result from storage
    chrome.storage.local.get(['lastCheck'], function(data) {
        if (data.lastCheck) {
            const { url, result, confidence, timestamp } = data.lastCheck;
            const resultClass = result.toLowerCase();
            resultDiv.className = `result ${resultClass}`;
            resultDiv.innerHTML = `
                <strong>Last Check Result:</strong>
                <div>URL: ${url}</div>
                <div>Status: ${result}</div>
                <div class="confidence">Confidence: ${(confidence * 100).toFixed(2)}%</div>
                <div class="timestamp">Checked at: ${new Date(timestamp).toLocaleTimeString()}</div>
            `;
        } else {
            resultDiv.innerHTML = 'Checking websites automatically...';
        }
    });

    checkButton.addEventListener('click', async () => {
        try {
            // Get the active tab
            resultDiv.innerHTML = 'Getting active tab...';
            const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
            const url = tab.url;

            if (!url || !url.startsWith('http')) {
                throw new Error('Please navigate to a valid webpage first');
            }

            // Show the URL being checked
            resultDiv.innerHTML = `Checking URL: ${url}`;

            // Show loading state
            loadingDiv.style.display = 'block';
            resultDiv.className = 'result';

            try {
                // Make request to your API
                console.log('Sending request to:', 'http://localhost:5000/predict');
                console.log('With URL:', url);

                const response = await fetch('http://localhost:5000/predict', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Accept': 'application/json'
                    },
                    body: JSON.stringify({ url: url })
                });

                console.log('Response status:', response.status);

                if (!response.ok) {
                    const errorText = await response.text();
                    console.error('Server error:', errorText);
                    throw new Error(`Server error (${response.status}). Make sure the Python backend is running.`);
                }

                const data = await response.json();
                console.log('Response data:', data);

                if (data.error) {
                    throw new Error(data.error);
                }

                // Hide loading state
                loadingDiv.style.display = 'none';

                // Display result
                const resultClass = data.result.toLowerCase();
                resultDiv.className = `result ${resultClass}`;
                resultDiv.innerHTML = `
                    <strong>Result:</strong> ${data.result}
                    <div class="confidence">Confidence: ${(data.confidence * 100).toFixed(2)}%</div>
                    ${data.note ? `<div class="note">${data.note}</div>` : ''}
                `;
            } catch (error) {
                console.error('API Error:', error);
                // Handle network or server errors
                loadingDiv.style.display = 'none';
                resultDiv.className = 'result phishing';
                if (error.message.includes('Failed to fetch')) {
                    resultDiv.innerHTML = 'Error: Could not connect to the server. Make sure the Python backend is running on localhost:5000';
                } else {
                    resultDiv.innerHTML = `Error: ${error.message || 'Could not analyze URL'}`;
                }
            }
        } catch (error) {
            console.error('Chrome API Error:', error);
            // Handle Chrome API errors
            loadingDiv.style.display = 'none';
            resultDiv.className = 'result phishing';
            resultDiv.innerHTML = `Error: ${error.message}`;
        }
    });
});
