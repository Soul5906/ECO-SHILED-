# 2. Installation Guide — Windows 10/11

## Before starting
Install:
1. **Python 3.10+** and enable “Add Python to PATH”.
2. **Node.js 18+**, preferably Node.js 20 LTS.
3. **VS Code** (recommended).
4. A ZIP extraction utility if needed.

Verify installations in PowerShell:
```powershell
py --version
node --version
npm --version
```
If a command is not found, close and reopen the terminal after installing the software.

## Extract and open
1. Extract the project ZIP into a normal folder, such as `Documents\\ECO-SHIELD`.
2. Open VS Code.
3. Select **File → Open Folder** and choose the extracted folder.
4. Open **Terminal → New Terminal**.

## Start the backend
Run from the project root:
```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
uvicorn app.main:app --reload
```
Keep this terminal running.

### If PowerShell blocks activation
Use the virtual-environment executables directly:
```powershell
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```
This avoids changing the PowerShell execution policy.

### Verify backend
Open:
- `http://127.0.0.1:8000/api/health`
- `http://127.0.0.1:8000/docs`

The health response should report `status: ok`.

## Start the frontend
Open a **second terminal** in VS Code. From the project root:
```powershell
cd frontend
npm install
npm run dev
```
Open the URL printed by Vite, usually `http://localhost:5173`.

## Stop services
Click the terminal running the service and press `Ctrl+C`.

## Start again later
Use two terminals:
- Backend terminal: activate `.venv` if required, then run `uvicorn app.main:app --reload`.
- Frontend terminal: run `npm run dev`.

## Common problems
- **`py` not found:** install Python and enable PATH, or try `python --version`.
- **`npm` not found:** install Node.js, reopen VS Code, and retry.
- **Port already in use:** stop the old server or choose another port.
- **Frontend says backend disconnected:** check that the backend is running at `127.0.0.1:8000`.
- **Package install errors:** check internet access, versions, and copy the full terminal error into your debugging assistant.
