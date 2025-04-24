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

// Store information about tabs that are being checked
const pendingChecks = new Map();
// Store information about tabs that have been approved by the user
const approvedUrls = new Map(); // Map of tabId to approved URL

// Confidence threshold for determining phishing sites
const CONFIDENCE_THRESHOLD = 0.7;

// Function to check if a URL is phishing
async function checkUrl(url, tabId, isBeforeNavigate = false) {
    try {
        // Skip check if URL is already approved by user
        if (approvedUrls.has(tabId) && approvedUrls.get(tabId) === url) {
            console.log('URL already approved by user:', url);
            return { result: "Legitimate", confidence: 1.0 };
        }
        
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
        
        // Update popup with result
        chrome.storage.local.set({
            'lastCheck': {
                url: url,
                result: data.result,
                confidence: data.confidence,
                timestamp: new Date().toISOString()
            }
        });

        // Determine if the site is phishing based on both result and confidence
        let isPhishing = false;
        
        // If the API explicitly says it's phishing, trust that
        if (data.result === "Phishing") {
            isPhishing = true;
        }
        // Even if API says it's legitimate, if confidence is low, treat as phishing
        else if (data.confidence < CONFIDENCE_THRESHOLD) {
            isPhishing = true;
            console.log(`Low confidence (${data.confidence}), treating as phishing despite API result`);
            // Override the result for display purposes
            data.result = "Phishing";
        }

        // If it's a phishing site and we're checking before navigation, block it
        if (isPhishing && isBeforeNavigate) {
            // Redirect to warning page
            const warningUrl = chrome.runtime.getURL(
                `warning.html?url=${encodeURIComponent(url)}&confidence=${data.confidence}&tabId=${tabId}`
            );
            console.log('Redirecting to warning page:', warningUrl);
            chrome.tabs.update(tabId, { url: warningUrl });
            return null; // Navigation will be handled by the redirect
        } else if (!isBeforeNavigate) {
            // If we're checking after navigation, just show the banner
            await injectWarningBanner(tabId, data.result, data.confidence);
        }

        return data;
    } catch (error) {
        console.error('Error checking URL:', error);
        // In case of error, let the navigation proceed
        return { result: "Error", confidence: 0 };
    }
}

// Listen for when a navigation is about to occur
chrome.webNavigation.onBeforeNavigate.addListener(async (details) => {
    // Only check main frame navigations (not iframes, etc.)
    if (details.frameId === 0 && details.url.startsWith('http')) {
        console.log('Before navigate:', details.url, details.tabId);
        
        // Skip chrome-extension:// URLs
        if (details.url.startsWith('chrome-extension://')) {
            return;
        }
        
        // Store information about this navigation
        pendingChecks.set(details.tabId, {
            url: details.url,
            timestamp: Date.now()
        });
        
        // Check the URL before allowing navigation
        await checkUrl(details.url, details.tabId, true);
    }
});

// Listen for tab updates
chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
    // Clear per-tab approval if navigated away from approved URL
    const approvedUrl = approvedUrls.get(tabId);
    if (approvedUrl && tab.url && tab.url !== approvedUrl) {
        approvedUrls.delete(tabId);
        console.log('Cleared approved URL for tab', tabId);
    }
    console.log('Tab updated:', tabId, changeInfo.status, tab.url);
    
    // Skip chrome-extension:// URLs
    if (tab.url && tab.url.startsWith('chrome-extension://')) {
        return;
    }
    
    // Only check when the URL has finished loading
    if (changeInfo.status === 'complete' && tab.url && tab.url.startsWith('http')) {
        // Check if this tab was previously blocked and now allowed
        const pendingCheck = pendingChecks.get(tabId);
        if (pendingCheck && pendingCheck.url === tab.url) {
            // This URL was already checked during onBeforeNavigate
            pendingChecks.delete(tabId);
        } else {
            // This is a new navigation or the URL changed
            checkUrl(tab.url, tabId, false);
        }
    }
});

// Listen for tab activation (switching between tabs)
chrome.tabs.onActivated.addListener(async (activeInfo) => {
    console.log('Tab activated:', activeInfo.tabId);
    const tab = await chrome.tabs.get(activeInfo.tabId);
    
    // Skip chrome-extension:// URLs
    if (tab.url && tab.url.startsWith('chrome-extension://')) {
        return;
    }
    
    if (tab.url && tab.url.startsWith('http')) {
        checkUrl(tab.url, tab.id, false);
    }
});

// Listen for messages from the warning page
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    console.log('Received message:', message);
    
    if (message.action === 'goBack') {
        // Navigate back to safety
        chrome.tabs.goBack(parseInt(message.tabId));
    } 
    else if (message.action === 'proceed') {
        // Add URL to approved list
        approvedUrls.set(parseInt(message.tabId), message.url);
        
        // Navigate to the original URL
        chrome.tabs.update(parseInt(message.tabId), { url: message.url });
    } else if (message.action === 'reportSuccess') {
        chrome.notifications.create('', {
            type: 'basic',
            iconUrl: chrome.runtime.getURL('images/icon48.png'),
            title: 'Report Submitted',
            message: 'Report submitted successfully.',
            priority: 2
        });
    }
    
    return true;
});

// Initialize the extension
chrome.runtime.onInstalled.addListener(() => {
    console.log('Phishing URL Detector extension installed');
});
