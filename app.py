import streamlit as st
import hashlib
import json
import re
from datetime import datetime

import pdfplumber
from docx import Document

# ---------------- CONFIG ----------------

st.set_page_config(page_title="GenAI Legal Assistant", layout="wide")

st.title("GenAI-Powered Legal Assistant for SMEs")
st.caption("Understand contracts, identify risks, take action")

st.info(
"Confidentiality Notice: All analysis is performed locally. "
"This tool assists understanding and does not replace legal advice."
)

# ---------------- FILE READER ----------------

def read_contract(uploaded_file):
filename = uploaded_file.name.lower()

if filename.endswith(".txt"):
    return uploaded_file.read().decode("utf-8")

if filename.endswith(".pdf"):
    with pdfplumber.open(uploaded_file) as pdf:
        return "\n".join(page.extract_text() or "" for page in pdf.pages)

if filename.endswith(".docx"):
    doc = Document(uploaded_file)
    return "\n".join(p.text for p in doc.paragraphs)

raise ValueError("Unsupported file format")


#---------------- CLAUSE EXTRACTION ----------------

def extract_clauses(text):
raw_clauses = re.split(r"\n\s*\d+[.)]\s*", text)


clauses = []
for i, clause in enumerate(raw_clauses, start=1):
    cleaned = clause.strip()
    if len(cleaned) > 50:
        clauses.append({
            "id": f"Clause {i}",
            "title": "General",
            "text": cleaned
        })
return clauses


# ---------------- ENTITY EXTRACTION ----------------

def extract_entities(text):
return {
"dates": re.findall(r"\b\d{1,2}/\d{1,2}/\d{4}\b", text),
"amounts": re.findall(r"₹\s?\d+[,\d]*", text),
"jurisdiction": re.findall(r"India|Tamil Nadu|Karnataka|Delhi", text, re.IGNORECASE)
}

# --------------- RISK ENGINE ----------------

HIGH_RISK_TERMS = [
"penalty",
"indemnify",
"terminate at any time",
"non-compete",
"unlimited liability",
"exclusive"
]

MEDIUM_RISK_TERMS = [
"shall",
"must",
"binding",
"auto renew",
"lock-in",
"arbitration"
]

def assess_clause_risk(text):
content = text.lower()


if any(term in content for term in HIGH_RISK_TERMS):
    return "High"

if any(term in content for term in MEDIUM_RISK_TERMS):
    return "Medium"

return "Low"


def calculate_overall_risk(risks):
if "High" in risks:
return "High"
if "Medium" in risks:
return "Medium"
return "Low"

# ---------------- SUMMARIZER ----------------

def explain_clause(risk):
if risk == "High":
return (
"This clause may expose your business to significant legal or "
"financial risk. Consider renegotiating or limiting liability."
)

if risk == "Medium":
    return (
        "This clause creates obligations that should be clearly "
        "understood and managed."
    )

return "This clause is generally balanced and commonly used."


def generate_summary(clauses, entities, risk):
return (
f"Overall Contract Risk: {risk}\n\n"
f"Total Clauses Analyzed: {len(clauses)}\n"
f"Dates Identified: {', '.join(entities.get('dates', [])) or 'None'}\n"
f"Amounts Mentioned: {', '.join(entities.get('amounts', [])) or 'None'}\n\n"
"Recommendation:\n"
"Review high-risk clauses carefully and consult a legal professional "
"before signing."
)

# ---------------- AUDIT LOG ----------------

def save_audit(document_id):
log_entry = {
"document_id": document_id,
"timestamp": datetime.utcnow().isoformat(),
"action": "contract_analysis"
}


try:
    with open("audit.json", "a") as f:
        f.write(json.dumps(log_entry) + "\n")
except:
    pass

# ---------------- UI ----------------

uploaded_file = st.file_uploader(
"Upload a contract (PDF, DOCX, TXT)",
type=["pdf", "docx", "txt"]
)

if uploaded_file:
contract_text = read_contract(uploaded_file)

document_id = hashlib.sha256(contract_text.encode()).hexdigest()[:10]

clauses = extract_clauses(contract_text)
entities = extract_entities(contract_text)

results = []

for clause in clauses:
    risk = assess_clause_risk(clause["text"])
    explanation = explain_clause(risk)

    results.append({
        "id": clause["id"],
        "text": clause["text"],
        "risk": risk,
        "explanation": explanation
    })

overall_risk = calculate_overall_risk([c["risk"] for c in results])
summary = generate_summary(results, entities, overall_risk)

# -------- DISPLAY -------- #
st.subheader("Overall Contract Risk")
st.markdown(f"### {overall_risk}")

st.subheader("Contract Summary")
st.write(summary)

st.subheader("Clause Analysis")

for c in results:
    with st.expander(f"{c['id']} - {c['risk']} Risk"):
        st.write("Clause:")
        st.write(c["text"])
        st.write("Explanation:")
        st.write(c["explanation"])

# -------- AUDIT -------- #
save_audit(document_id)

# -------- DOWNLOAD -------- #
st.download_button(
    "Download Summary",
    summary,
    file_name="contract_summary.txt"
)
