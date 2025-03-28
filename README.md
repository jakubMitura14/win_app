# Patient Audio Recording System - Installation and Setup Guide

This guide will help you set up and run the Patient Audio Recording System on Windows.

## Prerequisites

### 1. Install Python 3.10 or later

1. Download Python from [python.org](https://www.python.org/downloads/)
2. Run the installer
3. **IMPORTANT**: Check the box that says "Add Python to PATH" during installation
4. Click "Install Now" and wait for the installation to complete
5. Verify installation by opening Command Prompt (search for "cmd" in Windows search) and typing:
   ```
   python --version
   ```
   You should see a version number like "Python 3.10.x" or higher

### 2. Install Git

1. Download Git from [git-scm.com](https://git-scm.com/download/win)
2. Run the installer with default options
3. After installation, verify Git is installed by opening Command Prompt and typing:
   ```
   git --version
   ```
   You should see a version number like "git version 2.x.x"

## Application Setup

### 1. Clone the Repository

1. Open Command Prompt (search for "cmd" in the Windows start menu)
2. Create a folder where you want to install the application:
   ```
   mkdir C:\Users\YourUsername\Documents\PatientApp
   cd C:\Users\YourUsername\Documents\PatientApp
   ```
   (Replace "YourUsername" with your actual Windows username)
   
3. Clone the repository:
   ```
   git clone https://github.com/jakubMitura14/win_app.git
   ```
   
4. Change to the application directory:
   ```
   cd win_app
   ```

### 2. Create a Virtual Environment (recommended - you can skip it)

1. Create a virtual environment:
   ```
   python -m venv venv
   ```
   
2. Activate the virtual environment:
   ```
   venv\Scripts\activate
   ```
   
   You should see `(venv)` at the beginning of your command prompt.

### 3. Install Required Packages

1. Update pip to the latest version first:
   ```
   python -m pip install --upgrade pip
   ```

2. Install the required packages with **specific versions**:
   ```
   pip install -r requirements.txt
   ```


3. Make sure you have microphone permissions enabled in Windows:
   - Go to Windows Settings
   - Select Privacy & Security
   - Click on Microphone in the App permissions section
   - Ensure microphone access is turned on

## Running the Application

1. Make sure your virtual environment is activated (you should see `(venv)` at the beginning of your command prompt)
2. Run the application:
   ```
   python main_app.py
   ```
3. The application should open in a new window

## Using the Application

### Navigating the Interface

The application has a scrollable interface:
- Search functionality is always visible at the top
- Use the mouse wheel or scrollbar to access all fields and controls
- All patient notes and recording controls can be accessed by scrolling down

### Initial Setup
1. Set a database folder path:
   - Click the "Browse" button and select a folder
   - Or type a path directly in the field (e.g., C:\PatientData)
   - The folder will be created if it doesn't exist

2. Enter patient information:
   - Fill in name and surname fields (optional)
   - The date field is automatically filled with today's date
   - You can modify any of these fields as needed

3. Generate or Enter a Patient ID:
   - Click "Generate ID" to automatically create an ID
   - You can edit the suggested ID if needed

### Using the Search Feature
1. Click on the search field to see all patients in the database
2. Use the radio buttons to select how to search:
   - ID: Search only by patient ID
   - Name/Surname: Search by patient name or surname
   - All Fields: Search across all patient information
3. Click on any patient in the results to load their data

### Working with Patient Notes
- Four text areas are available for detailed patient notes:
  - Initial Description
  - Scintigraphy
  - FDG PET
  - Additional Notes
- All text areas have expanded height for easier data entry

### Recording Audio
1. Scroll down to access the recording controls
2. The "Recording Prefix" field defaults to "USG"
3. You can change this prefix to categorize your recordings
4. Click "Start Recording" to begin
5. Click "Stop Recording" to finish
6. Recordings are saved in the patient's folder

### Saving Patient Data
1. Data is automatically saved every 4 seconds
2. You can also click the "Save Patient Data" button to save immediately
3. All data is stored in a JSON file in the patient's folder

## Troubleshooting

### Version Compatibility Issues
If you encounter errors like:
- "unexpected keyword argument 'scroll'"
- "colors enum is deprecated"

These are typically caused by version mismatches. Try the following:
1. Make sure you've installed the exact versions specified above
2. Update your code if using newer Flet versions (changing lowercase "colors" to uppercase "Colors")
3. Reinstall packages if needed

### If Some Fields Are Not Visible
- Make sure to scroll down to see all fields and controls
- You can resize the window to make more content visible
- If the application appears cut off, try restarting it

For help or to report issues, please visit the GitHub repository:
https://github.com/jakubMitura14/win_app
