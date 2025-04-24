document.addEventListener('DOMContentLoaded', () => {
  const params = new URLSearchParams(window.location.search);
  const urlInput = document.getElementById('reportUrl');
  const descInput = document.getElementById('reportDescription');
  const screenshotInput = document.getElementById('screenshotInput');
  const screenshotName = document.getElementById('screenshotName');
  const submitBtn = document.getElementById('submitReport');
  const statusDiv = document.getElementById('status');
  const backBtn = document.getElementById('backBtn');
  backBtn.addEventListener('click', () => window.history.back());

  // Pre-fill URL
  const reportUrl = params.get('url') || '';
  urlInput.value = reportUrl;

  let screenshotData = null;
  screenshotInput.addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (file) {
      // Show file name instead of preview
      screenshotName.textContent = file.name;
      screenshotName.style.display = 'inline';
      const reader = new FileReader();
      reader.onload = (ev) => {
        screenshotData = ev.target.result.split(',')[1];
      };
      reader.readAsDataURL(file);
    }
  });

  submitBtn.addEventListener('click', async () => {
    const description = descInput.value.trim();
    if (!description) {
      statusDiv.textContent = 'Please enter a description.';
      return;
    }
    statusDiv.textContent = 'Submitting...';
    try {
      const resp = await fetch('http://localhost:5000/report', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: reportUrl, description, screenshot: screenshotData })
      });
      const result = await resp.json();
      if (resp.ok) {
        statusDiv.textContent = `Report submitted! ID: ${result.report_id}`;
        // Trigger desktop notification via background script
        chrome.runtime.sendMessage({ action: 'reportSuccess', reportId: result.report_id });
      } else {
        statusDiv.textContent = `Error: ${result.error}`;
      }
    } catch (err) {
      console.error('Report submission failed:', err);
      statusDiv.textContent = 'Network error';
    }
  });
});
