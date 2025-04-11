# Phishing URL Detector Chrome Extension

This Chrome extension helps detect potential phishing URLs using machine learning.

## Setup Instructions

1. Make sure the Python API server is running:
   ```bash
   cd api
   python app.py
   ```

2. Load the extension in Chrome:
   - Open Chrome and go to `chrome://extensions/`
   - Enable "Developer mode" in the top right
   - Click "Load unpacked"
   - Select the `extension` folder

3. Usage:
   - Click the extension icon in your Chrome toolbar
   - Click "Check Current Page" to analyze the current URL
   - The result will show whether the URL is legitimate or potentially phishing

## Requirements
- Chrome browser
- Python backend server running on localhost:5000

## Note
Make sure to keep the Python backend server running while using the extension.
