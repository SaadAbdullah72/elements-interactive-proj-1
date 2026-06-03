# Medical Prescription Checker - Frontend

This is a React-based frontend for the Medical Prescription Checker API. It provides a chat-like interface to check prescriptions against a medical database.

## Tech Stack

- **React**: For building the user interface.
- **Tailwind CSS**: For utility-first styling.
- **Axios**: For making API calls to the FastAPI backend.
- **React Icons**: For status icons (✅, ⚠️, ❌).
- **Framer Motion**: For smooth animations.

## Setup and Installation

1.  **Navigate to the frontend directory:**
    ```bash
    cd frontend
    ```

2.  **Install dependencies:**
    Make sure you have [Node.js](https://nodejs.org/) and `npm` (or `yarn`) installed.
    ```bash
    npm install
    ```

3.  **Start the backend server:**
    In a separate terminal, navigate to the root project directory and run the FastAPI server:
    ```bash
    # From C:\Users\Computer\Desktop\opencl\
    uvicorn main:app --reload
    ```
    The backend is currently hosted at `http://8000-izlfj7gl7597sycoftln2-b2401b06.us2.manus.computer/`.

4.  **Start the frontend development server:**
    ```bash
    npm start
    ```
    This will open the application in your browser, usually at `http://localhost:3000`.

## How to Use

1.  Expand the "Patient Details" panel at the top of the page.
2.  Fill in the patient's information (disease, medication, age, etc.).
3.  In the chat input box at the bottom, type `check` and press Enter.
4.  The result of the prescription check will appear as a styled message in the chat window.