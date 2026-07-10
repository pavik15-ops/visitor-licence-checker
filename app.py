import streamlit as st
import pdfplumber
import re
import dateparser
from datetime import date

st.set_page_config(page_title="Visitor Work Licence Checker", page_icon="🛂", layout="centered")

MIN_DAYS = 10

EXPIRY_KEYWORDS = [
    "expiry date", "expiration date", "valid until", "valid till",
    "date of expiry", "licence expiry", "license expiry", "expires on", "expiry"
]
DATE_PATTERN = re.compile(r"(\d{1,2}[\/\-\.\s](?:\d{1,2}|[A-Za-z]{3,9})[\/\-\.\s]\d{2,4})")


# ---------------------------------------------------------------------------
# DESIGN SYSTEM — "Customs Desk"
# Palette: ink navy background, aged paper cards, brass/gold rule lines,
# and a rubber-stamp signature element for the verdict (green ink = accepted,
# red ink = rejected) — the visual language of an actual document checkpoint.
# ---------------------------------------------------------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700;900&family=IBM+Plex+Mono:wght@400;500;600;700&family=Inter:wght@400;500;600&display=swap');

:root{
  --ink-900:#0B1A2B;
  --ink-800:#132A44;
  --ink-700:#1C3A5C;
  --paper:#F4EFE1;
  --paper-line:#D9CFAE;
  --gold:#B9903F;
  --gold-light:#E4C27A;
  --text-light:#EDE7D6;
  --text-muted:#8FA0B5;
  --stamp-green:#1F6E4A;
  --stamp-red:#9C3B31;
}

html, body, [class*="css"]  { font-family: 'Inter', sans-serif; }
.stApp{
  background:
    radial-gradient(circle at 15% 0%, #16304C 0%, transparent 45%),
    radial-gradient(circle at 85% 100%, #16304C 0%, transparent 45%),
    var(--ink-900);
}
.block-container{ padding-top: 2.5rem; max-width: 760px; }

/* ---------- Header ---------- */
.doc-eyebrow{
  font-family:'IBM Plex Mono', monospace;
  letter-spacing:.28em; text-transform:uppercase;
  font-size:.72rem; color: var(--gold-light);
  text-align:center; margin-bottom:.4rem;
}
.doc-title{
  font-family:'Playfair Display', serif; font-weight:900;
  font-size:2.6rem; color: var(--text-light);
  text-align:center; letter-spacing:.01em; margin:0;
}
.doc-rule{
  width:120px; height:2px; margin:1.1rem auto 1.6rem auto;
  background: linear-gradient(90deg, transparent, var(--gold), transparent);
}

/* ---------- Rule / logic notice ---------- */
.notice{
  border:1px dashed var(--gold);
  border-radius:2px;
  background: rgba(185,144,63,0.06);
  padding: 1.1rem 1.4rem;
  margin-bottom: 1.8rem;
}
.notice-label{
  font-family:'IBM Plex Mono', monospace; font-size:.68rem;
  letter-spacing:.22em; text-transform:uppercase;
  color:var(--gold-light); margin-bottom:.55rem;
}
.notice ul{ margin:0; padding-left:1.1rem; color:var(--text-light); font-size:.92rem; line-height:1.65;}
.notice b{ color:var(--gold-light); }

/* ---------- Upload zone ---------- */
[data-testid="stFileUploader"]{
  background: var(--paper);
  border-radius: 4px;
  padding: 1.1rem 1.2rem 1.3rem 1.2rem;
  border: 1px solid var(--paper-line);
}
[data-testid="stFileUploaderDropzone"]{
  background: transparent !important;
}
[data-testid="stFileUploader"] section{ background: transparent; }
[data-testid="stFileUploader"] label p{
  font-family:'IBM Plex Mono', monospace !important;
  color:#4A3F27 !important; font-size:.78rem !important;
  letter-spacing:.08em; text-transform:uppercase;
}

/* ---------- Selectbox ---------- */
div[data-baseweb="select"] > div{
  background: var(--ink-800) !important;
  border-color: var(--gold) !important;
  color: var(--text-light) !important;
}

/* ---------- Passport data card ---------- */
.data-card{
  background: var(--ink-800);
  border: 1px solid var(--ink-700);
  border-left: 3px solid var(--gold);
  border-radius: 3px;
  padding: 1.3rem 1.5rem;
  margin-top: .5rem;
}
.data-row{
  display:flex; justify-content:space-between; align-items:baseline;
  padding: .5rem 0; border-bottom: 1px solid rgba(255,255,255,0.06);
  font-family:'IBM Plex Mono', monospace;
}
.data-row:last-child{ border-bottom:none; }
.data-label{ color: var(--text-muted); font-size:.72rem; letter-spacing:.14em; text-transform:uppercase; }
.data-value{ color: var(--text-light); font-size:.95rem; font-weight:600; }

.stamp-wrap{ display:flex; justify-content:center; margin: 1.6rem 0 .4rem 0; }

.verdict-caption{
  text-align:center; font-family:'IBM Plex Mono', monospace;
  font-size:.78rem; letter-spacing:.1em; color: var(--text-muted); margin-top:.3rem;
}

/* ---------- Misc ---------- */
[data-testid="stExpander"]{
  border: 1px solid var(--ink-700) !important; border-radius:3px !important;
  background: var(--ink-800) !important;
}
</style>
""", unsafe_allow_html=True)


def stamp_svg(status_word: str, sub_text: str, color: str) -> str:
    return f"""
    <svg width="230" height="230" viewBox="0 0 230 230" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <filter id="rough"><feTurbulence type="fractalNoise" baseFrequency="0.85" numOctaves="2" result="n"/>
          <feDisplacementMap in="SourceGraphic" in2="n" scale="2.4"/></filter>
        <path id="circlePath" d="M 115,115 m -80,0 a 80,80 0 1,1 160,0 a 80,80 0 1,1 -160,0" />
      </defs>
      <g filter="url(#rough)" transform="rotate(-9 115 115)" opacity="0.92">
        <circle cx="115" cy="115" r="98" fill="none" stroke="{color}" stroke-width="4"/>
        <circle cx="115" cy="115" r="86" fill="none" stroke="{color}" stroke-width="1.5"/>
        <text font-family="'IBM Plex Mono', monospace" font-size="15.5" font-weight="700" letter-spacing="5" fill="{color}">
          <textPath href="#circlePath" startOffset="50%" text-anchor="middle">• VISITOR WORK LICENCE •</textPath>
        </text>
        <text x="115" y="122" font-family="'Playfair Display', serif" font-size="27" font-weight="900"
              fill="{color}" text-anchor="middle">{status_word}</text>
        <text x="115" y="145" font-family="'IBM Plex Mono', monospace" font-size="10.5" letter-spacing="2"
              fill="{color}" text-anchor="middle">{sub_text}</text>
      </g>
    </svg>
    """


def extract_text_from_pdf(uploaded_file):
    text = ""
    with pdfplumber.open(uploaded_file) as pdf:
        for page in pdf.pages:
            text += (page.extract_text() or "") + "\n"
    if text.strip():
        return text, "text"
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
    lower_text = text.lower()
    candidates = []
    for kw in EXPIRY_KEYWORDS:
        for match in re.finditer(re.escape(kw), lower_text):
            window = text[match.end():match.end() + 60]
            date_match = DATE_PATTERN.search(window)
            if date_match:
                candidates.append((kw, date_match.group(1)))
    if candidates:
        return candidates
    all_dates = DATE_PATTERN.findall(text)
    return [("(no keyword match — all dates found)", d) for d in all_dates]


# ---------------------------------------------------------------------------
# LAYOUT
# ---------------------------------------------------------------------------
st.markdown('<div class="doc-eyebrow">Document Verification Desk</div>', unsafe_allow_html=True)
st.markdown('<h1 class="doc-title">Visitor Work Licence</h1>', unsafe_allow_html=True)
st.markdown('<div class="doc-rule"></div>', unsafe_allow_html=True)

st.markdown(f"""
<div class="notice">
  <div class="notice-label">Verification Rule</div>
  <ul>
    <li>Validity remaining = <b>Expiry Date − Upload Date</b></li>
    <li>Less than <b>{MIN_DAYS} days</b> remaining → <b>Rejected</b></li>
    <li><b>{MIN_DAYS} days or more</b> remaining → <b>Accepted</b></li>
  </ul>
</div>
""", unsafe_allow_html=True)

uploaded_file = st.file_uploader("Upload visitor work licence (PDF)", type=["pdf"], label_visibility="collapsed")

if uploaded_file:
    with st.spinner("Reading document..."):
        text, method = extract_text_from_pdf(uploaded_file)

    if not text.strip():
        st.error("Could not extract any text from this PDF, even with OCR.")
    else:
        if method == "ocr":
            st.info("This PDF had no selectable text — used OCR to read it.")

        candidates = find_expiry_date(text)

        if not candidates:
            st.error("No date-like values were found in this document.")
        else:
            options = [f"{kw}  →  {raw}" for kw, raw in candidates]
            choice = st.selectbox("Select the correct expiry date:", options)
            raw_date_str = choice.split("→")[-1].strip()
            parsed_date = dateparser.parse(raw_date_str)

            if not parsed_date:
                st.error(f"Found '{raw_date_str}' but couldn't parse it as a date.")
            else:
                expiry_date = parsed_date.date()
                today = date.today()
                diff_days = (expiry_date - today).days
                accepted = diff_days >= MIN_DAYS
                color = "#1F6E4A" if accepted else "#9C3B31"
                status_word = "ACCEPTED" if accepted else "REJECTED"
                sub_text = f"{diff_days} DAYS REMAINING" if diff_days >= 0 else f"EXPIRED {abs(diff_days)} DAYS AGO"

                st.markdown(f"""
                <div class="data-card">
                  <div class="data-row"><span class="data-label">Upload Date</span><span class="data-value">{today.strftime('%d %b %Y')}</span></div>
                  <div class="data-row"><span class="data-label">Expiry Date</span><span class="data-value">{expiry_date.strftime('%d %b %Y')}</span></div>
                  <div class="data-row"><span class="data-label">Days Remaining</span><span class="data-value">{diff_days}</span></div>
                  <div class="data-row"><span class="data-label">Minimum Required</span><span class="data-value">{MIN_DAYS} days</span></div>
                </div>
                """, unsafe_allow_html=True)

                st.markdown(f'<div class="stamp-wrap">{stamp_svg(status_word, sub_text, color)}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="verdict-caption">Status determined against today — {today.strftime("%d %b %Y")}</div>', unsafe_allow_html=True)

        with st.expander("View extracted document text (for verification)"):
            st.text(text)
