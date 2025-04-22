# Patient Data anonimization System - Installation and Setup Guide

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
2. Create a folder where you want to install the application - you can also do it manually :
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

## Running the Application

1. Make sure your virtual environment is activated (you should see `(venv)` at the beginning of your command prompt)
2. Run the application:
   ```
   python anonimize_gui.py
   ```
3. The application should open in a new window
