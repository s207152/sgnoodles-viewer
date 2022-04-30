# SDGO SGNoodles

## Prerequisites
1. Python 3.10+
2. pipenv

## Dev
1. Open VSCode as admin or open a terminal with admin privelege
2. Install dependencies
   ```powershell
   pipenv install
   ```
3. Run the app
   ```powershell
   # open a shell with dependencies
   pipenv shell
   # run the app
   py main.py
   ```

## Build
```powershell
pyinstaller -w --uac-admin --add-data ".\TaipeiSansTCBeta-Regular.ttf;." -n sgnoodles-viewer main.py
```
Look at `dist/sgnoodles-viewer`, and should be able to be distrubuted.