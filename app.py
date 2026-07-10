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
# DESIGN SYSTEM — clean compliance-desk aesthetic
# Palette: light neutral surface, single restrained blue accent, semantic
# green/red only for the verdict badge. Data shown in a monospace tile grid,
# the way document/identity-verification tools present structured fields.
# ---------------------------------------------------------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=IBM+Plex+Mono:wght@400;500;600&display=swap');

:root{
  --bg:#F5F6F8;
  --surface:#FFFFFF;
  --border:#E3E6EB;
  --text-primary:#101828;
  --text-secondary:#667085;
  --accent:#2955D9;
  --accent-soft:#EEF2FF;
  --success-bg:#ECFDF3; --success-border:#ABEFC6; --success-text:#067647;
  --error-bg:#FEF3F2; --error-border:#FDA29B; --error-text:#B42318;
}

html, body, [class*="css"] { font-family:'Inter', sans-serif; }
.stApp{ background: var(--bg); }
.block-container{ padding-top: 2.2rem; max-width: 720px; }

/* ---------- Top bar ---------- */
.topbar{ display:flex; align-items:center; gap:.7rem; margin-bottom:.3rem; }
.topbar-icon{
  width:36px; height:36px; border-radius:8px; background:var(--accent);
  display:flex; align-items:center; justify-content:center; font-size:18px;
  flex-shrink:0;
}
.topbar-title{ font-size:1.28rem; font-weight:700; color:var(--text-primary); line-height:1.2; }
.topbar-sub{ font-size:.82rem; color:var(--text-secondary); margin-top:1px; }
.hairline{ height:1px; background:var(--border); margin: 1.1rem 0 1.5rem 0; }

/* ---------- Step indicator ---------- */
.steps{ display:flex; align-items:center; margin-bottom:1.7rem; }
.step{ display:flex; align-items:center; gap:.5rem; }
.step-num{
  width:22px; height:22px; border-radius:50%; background:var(--surface);
  border:1.5px solid var(--border); color:var(--text-secondary);
  font-size:.72rem; font-weight:700; display:flex; align-items:center; justify-content:center;
}
.step-num.active{ background:var(--accent); border-color:var(--accent); color:#fff; }
.step-label{ font-size:.78rem; color:var(--text-secondary); font-weight:500; }
.step-label.active{ color:var(--text-primary); font-weight:600; }
.step-line{ flex:1; height:1px; background:var(--border); margin:0 .8rem; }

/* ---------- Cards ---------- */
.card{
  background:var(--surface); border:1px solid var(--border); border-radius:10px;
  padding:1.3rem 1.4rem; margin-bottom:1.2rem;
}
.card-label{
  font-size:.68rem; font-weight:700; letter-spacing:.06em; text-transform:uppercase;
  color:var(--text-secondary); margin-bottom:.7rem;
}
.rule-item{ display:flex; gap:.55rem; padding:.3rem 0; font-size:.88rem; color:var(--text-primary); }
.rule-item .dot{ color:var(--accent); font-weight:700; }

/* ---------- File uploader ---------- */
[data-testid="stFileUploader"]{
  background:var(--surface); border:1.5px dashed var(--border); border-radius:10px;
  padding:1rem 1.1rem;
}
[data-testid="stFileUploaderDropzone"]{ background:transparent !important; }
[data-testid="stFileUploader"] section{ background:transparent; }

/* ---------- Selectbox ---------- */
div[data-baseweb="select"] > div{
  background:var(--surface) !important; border-color:var(--border) !important;
  border-radius:8px !important; color:var(--text-primary) !important;
}

/* ---------- Verdict badge ---------- */
.badge{
  display:inline-flex; align-items:center; gap:.4rem;
  padding:.42rem .95rem; border-radius:100px; font-size:.85rem; font-weight:700;
  border:1px solid; margin-bottom:1rem;
}
.badge.ok{ background:var(--success-bg); border-color:var(--success-border); color:var(--success-text); }
.badge.no{ background:var(--error-bg); border-color:var(--error-border); color:var(--error-text); }

/* ---------- Data tile grid ---------- */
.tile-grid{ display:grid; grid-template-columns:1fr 1fr; gap:.7rem; }
.tile{
  background:#FAFBFC; border:1px solid var(--border); border-radius:8px;
  padding:.75rem .9rem;
}
.tile-label{
  font-size:.66rem; font-weight:600; letter-spacing:.05em; text-transform:uppercase;
  color:var(--text-secondary); margin-bottom:.28rem;
}
.tile-value{
  font-family:'IBM Plex Mono', monospace; font-size:.98rem; font-weight:600; color:var(--text-primary);
}
.tile.highlight{ background:var(--accent-soft); border-color:#C7D5FA; }
.tile.highlight .tile-value{ color:var(--accent); }

[data-testid="stExpander"]{ border:1px solid var(--border) !important; border-radius:8px !important; background:var(--surface) !important; }
</style>
""", unsafe_allow_html=True)


def render_steps(active: int):
    labels = ["Upload", "Extract", "Verify"]
    html = '<div class="steps">'
    for i, label in enumerate(labels, start=1):
        is_active = i <= active
        html += f'<div class="step"><div class="step-num{" active" if is_active else ""}">{i}</div>' \
                f'<div class="step-label{" active" if is_active else ""}">{label}</div></div>'
        if i < len(labels):
            html += '<div class="step-line"></div>'
    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)


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
st.markdown("""
<div class="topbar">
  <div class="topbar-icon">🛂</div>
  <div>
    <div class="topbar-title">Visitor Work Licence Checker</div>
    <div class="topbar-sub">Automated expiry verification from uploaded PDF</div>
  </div>
</div>
<div class="hairline"></div>
""", unsafe_allow_html=True)

step = 1

st.markdown(f"""
<div class="card">
  <div class="card-label">Verification Rule</div>
  <div class="rule-item"><span class="dot">→</span> Days remaining = Expiry Date − Upload Date</div>
  <div class="rule-item"><span class="dot">→</span> Fewer than {MIN_DAYS} days remaining: <b>Rejected</b></div>
  <div class="rule-item"><span class="dot">→</span> {MIN_DAYS} days or more remaining: <b>Accepted</b></div>
</div>
""", unsafe_allow_html=True)

uploaded_file = st.file_uploader("Upload visitor work licence (PDF)", type=["pdf"])

if uploaded_file:
    step = 2
    render_steps(step)

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
                step = 3
                expiry_date = parsed_date.date()
                today = date.today()
                diff_days = (expiry_date - today).days
                accepted = diff_days >= MIN_DAYS
                badge_class = "ok" if accepted else "no"
                badge_icon = "✓" if accepted else "✕"
                badge_text = "ACCEPTED" if accepted else "REJECTED"

                st.markdown(f'<span class="badge {badge_class}">{badge_icon} {badge_text}</span>', unsafe_allow_html=True)

                st.markdown(f"""
                <div class="card" style="margin-top:0;">
                  <div class="tile-grid">
                    <div class="tile"><div class="tile-label">Upload Date</div><div class="tile-value">{today.strftime('%d %b %Y')}</div></div>
                    <div class="tile"><div class="tile-label">Expiry Date</div><div class="tile-value">{expiry_date.strftime('%d %b %Y')}</div></div>
                    <div class="tile highlight"><div class="tile-label">Days Remaining</div><div class="tile-value">{diff_days}</div></div>
                    <div class="tile"><div class="tile-label">Minimum Required</div><div class="tile-value">{MIN_DAYS} days</div></div>
                  </div>
                </div>
                """, unsafe_allow_html=True)

        with st.expander("View extracted document text (for verification)"):
            st.text(text)
