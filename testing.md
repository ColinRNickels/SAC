# Testing Guide (Local PC)

Use these steps on macOS, Linux, or Windows (PowerShell) to run a local test instance.

## 1) Install prerequisites
- Python 3.10+ (check with `python --version`)
- Git

## 2) Clone and install
```bash
git clone <YOUR_REPO_URL> SAC
cd SAC
python -m venv .venv
```
Activate the venv:
- macOS/Linux: `source .venv/bin/activate`
- Windows PowerShell: `.venv\\Scripts\\Activate.ps1`

Install dependencies:
```bash
pip install -r requirements.txt
```

## 3) Run the app
```bash
export SAC_ADMIN_TOKEN=change-me
python -m sac.app
```
On Windows PowerShell:
```powershell
$env:SAC_ADMIN_TOKEN = "change-me"
python -m sac.app
```
Open:
- Kiosk: http://localhost:5000/
- Admin: http://localhost:5000/admin

Use the same token in the Admin Access form.

## 4) Reset data between tests
Stop the server and delete the SQLite database:
```bash
rm sac/kiosk.db
```
On Windows PowerShell:
```powershell
Remove-Item sac\\kiosk.db
```
