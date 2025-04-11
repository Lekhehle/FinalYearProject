// Function to inject warning banner into the webpage
async function injectWarningBanner(tabId, result, confidence) {
    const warningCSS = `
        .phishing-warning-banner {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            background-color: ${result === "Phishing" ? "#dc3545" : "#28a745"};
            color: white;
            padding: 15px;
            text-align: center;
            z-index: 999999;
            font-family: Arial, sans-serif;
            font-size: 16px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.2);
        }
        .phishing-warning-banner .confidence {
            font-size: 14px;
            margin-top: 5px;
        }
    `;

    const warningHTML = `
        <div class="phishing-warning-banner">
            <strong>${result === "Phishing" ? 
                "⚠️ Warning: This website might be a phishing attempt!" : 
                "✅ This website appears to be legitimate"}</strong>
            <div class="confidence">Confidence: ${(confidence * 100).toFixed(2)}%</div>
        </div>
    `;

    try {
        console.log('Injecting banner for tab:', tabId);
        
        // Inject CSS
        await chrome.scripting.insertCSS({
            target: { tabId: tabId },
            css: warningCSS
        });

        // Inject warning banner
        await chrome.scripting.executeScript({
            target: { tabId: tabId },
            func: (html) => {
                // Remove existing banner if any
                const existingBanner = document.querySelector('.phishing-warning-banner');
                if (existingBanner) {
                    existingBanner.remove();
                }
                // Add new banner
                const div = document.createElement('div');
                div.innerHTML = html;
                document.body.insertBefore(div.firstChild, document.body.firstChild);
            },
            args: [warningHTML]
        });
        
        console.log('Banner injected successfully');
    } catch (error) {
        console.error('Error injecting banner:', error);
    }
}

// Function to check if a URL is phishing
async function checkUrl(url, tabId) {
    try {
        console.log('Checking URL:', url, 'for tab:', tabId);
        
        const response = await fetch('http://localhost:5000/predict', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            body: JSON.stringify({ url: url })
        });

        if (!response.ok) {
            throw new Error(`Server error (${response.status})`);
        }

        const data = await response.json();
        console.log('API Response:', data);
        
        // Inject warning banner into the webpage
        await injectWarningBanner(tabId, data.result, data.confidence);

        // Update popup with result
        chrome.storage.local.set({
            'lastCheck': {
                url: url,
                result: data.result,
                confidence: data.confidence,
                timestamp: new Date().toISOString()
            }
        });

    } catch (error) {
        console.error('Error checking URL:', error);
    }
}

// Listen for tab updates
chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
    console.log('Tab updated:', tabId, changeInfo.status, tab.url);
    // Only check when the URL has finished loading
    if (changeInfo.status === 'complete' && tab.url && tab.url.startsWith('http')) {
        checkUrl(tab.url, tabId);
    }
});

// Listen for tab activation (switching between tabs)
chrome.tabs.onActivated.addListener(async (activeInfo) => {
    console.log('Tab activated:', activeInfo.tabId);
    const tab = await chrome.tabs.get(activeInfo.tabId);
    if (tab.url && tab.url.startsWith('http')) {
        checkUrl(tab.url, tab.id);
    }
});
