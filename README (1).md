# Visitor Work Licence Checker

A Streamlit web app that reads an uploaded visitor work licence PDF, finds its
**expiry date**, and decides ACCEPTED / REJECTED based on how many days of
validity remain from today.

## Logic
```
diff_days = (expiry_date - today's_date).days

if diff_days < 10:
    REJECTED
else:
    ACCEPTED
```

## How to run locally

1. Install Python 3.9+ if you don't have it.
2. Install Tesseract OCR (only needed for scanned/image PDFs):
   - Windows: https://github.com/UB-Mannheim/tesseract/wiki
   - Mac: `brew install tesseract`
   - Linux: `sudo apt install tesseract-ocr poppler-utils`
3. Install Python dependencies:
   ```
   pip install -r requirements.txt
   ```
4. Run the app:
   ```
   streamlit run app.py
   ```
5. It opens in your browser at `http://localhost:8501`. Upload a PDF and test it.

## Deploying for free (so others can use it too)

1. Push this folder to a GitHub repo.
2. Go to https://share.streamlit.io (Streamlit Community Cloud), sign in with GitHub.
3. Click "New app", pick your repo, set the main file to `app.py`, and deploy.
4. It also needs `packages.txt` with:
   ```
   tesseract-ocr
   poppler-utils
   ```
   (add this file if you want OCR to work on the deployed/cloud version — Community
   Cloud runs on Linux, so these apt packages get installed automatically.)

## Notes / things to double check with real documents

- The app looks for keywords like "expiry date", "valid until", "valid till" etc.
  right next to a date. If your real licence PDFs phrase it differently, open
  `app.py` and add the exact phrase used to the `EXPIRY_KEYWORDS` list.
- If a document has multiple matching dates, the app lets you pick the correct
  one from a dropdown before calculating.
- The "10 days" cutoff and the direction of comparison (expiry date minus
  today) are hardcoded — easy to change in `app.py` if your real rule differs.
