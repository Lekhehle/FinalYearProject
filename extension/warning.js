document.addEventListener('DOMContentLoaded', function() {
    const urlDisplay = document.getElementById('suspiciousUrl');
    const backButton = document.getElementById('backButton');
    const proceedButton = document.getElementById('proceedButton');
    
    // Get URL and confidence from URL parameters
    const urlParams = new URLSearchParams(window.location.search);
    const suspiciousUrl = urlParams.get('url');
    const tabId = urlParams.get('tabId');
    
    // Display the suspicious URL
    if (suspiciousUrl) {
        urlDisplay.textContent = suspiciousUrl;
    }
    
    // Go back to safety (previous page)
    backButton.addEventListener('click', function() {
        chrome.runtime.sendMessage({ action: 'goBack', tabId: tabId });
    });
    
    // Proceed to the website despite warning
    proceedButton.addEventListener('click', function() {
        chrome.runtime.sendMessage({ 
            action: 'proceed', 
            url: suspiciousUrl,
            tabId: tabId
        });
    });
});
