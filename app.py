import streamlit as st
import pdfplumber
import re
import dateparser
from datetime import datetime, date

st.set_page_config(page_title="Visitor Work Licence Checker", page_icon="🛂")
st.title("🛂 Visitor Work Licence Checker")
st.write(
    "Upload a visitor work licence PDF. The app finds the **expiry date** in the "
    "document and compares it against today's date (the upload date)."
)

st.markdown(
    """
**Logic:**
- Days remaining = Expiry Date − Today's Date
- If less than **10 days** remain → ❌ **REJECTED**
- If **10 days or more** remain → ✅ **ACCEPTED**
"""
)

MIN_DAYS = 10

# Keywords that usually sit right next to the expiry date in these documents
EXPIRY_KEYWORDS = [
    "expiry date", "expiration date", "valid until", "valid till",
    "date of expiry", "licence expiry", "license expiry", "expires on", "expiry"
]

DATE_PATTERN = re.compile(
    r"(\d{1,2}[\/\-\.\s](?:\d{1,2}|[A-Za-z]{3,9})[\/\-\.\s]\d{2,4})"
)


def extract_text_from_pdf(uploaded_file):
    """Try normal text extraction first; fall back to OCR if no text found."""
    text = ""
    with pdfplumber.open(uploaded_file) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text() or ""
            text += page_text + "\n"

    if text.strip():
        return text, "text"

    # Fallback: OCR (only reached if PDF has no extractable text, e.g. scanned image)
    try:
        from pdf2image import convert_from_bytes
        import pytesseract
        uploaded_file.seek(0)
        images = convert_from_bytes(uploaded_file.read())
        ocr_text = ""
        for img in images:
            ocr_text += pytesseract.image_to_string(img) + "\n"
        return ocr_text, "ocr"
    except Exception as e:
        return "", f"ocr_failed: {e}"


def find_expiry_date(text):
    """Look for a date near an expiry-related keyword; fall back to any date found."""
    lower_text = text.lower()
    candidates = []

    for kw in EXPIRY_KEYWORDS:
        for match in re.finditer(re.escape(kw), lower_text):
            start = match.end()
            window = text[start:start + 60]  # look just after the keyword
            date_match = DATE_PATTERN.search(window)
            if date_match:
                candidates.append((kw, date_match.group(1)))

    if candidates:
        return candidates  # list of (keyword, raw_date_string)

    # Fallback: no keyword match, return all dates found in the document
    all_dates = DATE_PATTERN.findall(text)
    return [("(no keyword match — all dates found)", d) for d in all_dates]


uploaded_file = st.file_uploader("Upload visitor work licence (PDF)", type=["pdf"])

if uploaded_file:
    with st.spinner("Reading document..."):
        text, method = extract_text_from_pdf(uploaded_file)

    if not text.strip():
        st.error(
            "Could not extract any text from this PDF, even with OCR. "
            "The file may be corrupted or image quality too low."
        )
    else:
        if method == "ocr":
            st.info("This PDF had no selectable text — used OCR to read it.")

        candidates = find_expiry_date(text)

        if not candidates:
            st.error("No date-like values were found in this document at all.")
        else:
            st.subheader("Possible expiry dates found")
            options = [f"{kw}  →  {raw}" for kw, raw in candidates]
            choice = st.selectbox(
                "Select the correct expiry date (first match is usually right):",
                options,
            )
            raw_date_str = choice.split("→")[-1].strip()

            parsed_date = dateparser.parse(raw_date_str)

            if not parsed_date:
                st.error(f"Found the text '{raw_date_str}' but couldn't parse it as a date.")
            else:
                expiry_date = parsed_date.date()
                today = date.today()
                diff_days = (expiry_date - today).days

                st.divider()
                col1, col2, col3 = st.columns(3)
                col1.metric("Upload Date (today)", today.strftime("%d-%b-%Y"))
                col2.metric("Expiry Date", expiry_date.strftime("%d-%b-%Y"))
                col3.metric("Days Remaining", diff_days)

                if diff_days < MIN_DAYS:
                    st.error(f"❌ REJECTED — only {diff_days} day(s) of validity left (minimum required: {MIN_DAYS})")
                else:
                    st.success(f"✅ ACCEPTED — {diff_days} day(s) of validity remaining")

        with st.expander("View extracted document text (for verification)"):
            st.text(text)
