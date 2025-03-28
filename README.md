# win_app
for internal use
# Patient Audio Recording System Installation Guide

This guide will help you set up the Patient Audio Recording System on your Windows computer.

## Prerequisites

### 1. Install Python

1. Download Python from the official website: https://www.python.org/downloads/windows/
   - Choose Python 3.10 or newer
   - During installation, make sure to check "Add Python to PATH"

2. Verify installation by opening Command Prompt and typing:
   ```
   python --version
   ```
   You should see the Python version displayed.

### 2. Install Git

1. Download Git from: https://git-scm.com/download/win
2. Install using the default options
3. Verify installation by opening Command Prompt and typing:
   ```
   git --version
   ```

## Setup Application

### 1. Clone the Repository

1. Open Command Prompt
2. Navigate to a folder where you want to store the application
3. Run the following command:
   ```
   git clone https://github.com/jakubMitura14/win_app.git
   ```
4. Change directory to the cloned repository:
   ```
   cd win_app
   ```

### 2. Create and Activate Virtual Environment (Recommended)

1. Create a virtual environment:
   ```
   python -m venv venv
   ```
2. Activate the virtual environment:
   ```
   venv\Scripts\activate
   ```

### 3. Install Required Packages

1. Install the required packages:
   ```
   pip install flet flet-audio-recorder
   ```

### 4. Audio Requirements for Windows

On Windows, the audio recorder uses the system's built-in audio recording capabilities, so no additional software is needed.

## Running the Application

1. Make sure you're in the win_app directory and your virtual environment is activated
2. Run the application:
   ```
   python main_app.py
   ```

## Using the Application

1. **Set Database Folder Path**: First, specify where patient data will be stored by clicking "Browse" or typing the path directly.

2. **Enter Patient Information**:
   - Fill in the patient's name and surname
   - The date will default to today but can be changed
   - Click "Generate ID" to create a unique patient ID

3. **Add Patient Notes**:
   - Initial Description
   - Scintigraphy
   - FDG PET

4. **Record Audio**:
   - Make sure a patient ID is generated first
   - Click "Start Recording" to begin
   - Click "Stop Recording" when finished
   - Multiple recordings can be made for the same patient

5. **Search for Patients**:
   - Use the search bar at the top right to find existing patients
   - Search by name, surname, ID, or date
   - Click on a patient from the results to load their data

6. **Auto-Save Feature**:
   - The application automatically saves data every 4 seconds
   - No need to manually save

## Troubleshooting

1. **Microphone Access**: Make sure your application has permission to access the microphone in Windows settings
2. **Database Path**: Ensure the path for the database exists and is writable
3. **Python Version**: If you encounter issues, verify you're using Python 3.10 or newer
