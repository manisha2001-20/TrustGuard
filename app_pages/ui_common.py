"""Shared UI helpers, caching and styling for the TrustGuard Streamlit app."""
from __future__ import annotations

import streamlit as st

from config.settings import load_settings
from database.db import Database
from llm.ollama_client import list_models

STATUS_COLORS = {
    "SUPPORTED": "#10b981", "CONTRADICTED": "#f43f5e", "INSUFFICIENT_EVIDENCE": "#f59e0b",
    "VERIFICATION_ERROR": "#8b5cf6", "SAFE": "#10b981", "REVIEW": "#f59e0b", "BLOCK": "#f43f5e",
    "RELEASED": "#10b981", "WITHHELD": "#f43f5e", "NOT_VERIFIED": "#f59e0b",
}
STATUS_LABEL = {
    "NOT_VERIFIED": "NOT VERIFIED",
    "SUPPORTED": "SUPPORTED", "CONTRADICTED": "CONTRADICTED",
    "INSUFFICIENT_EVIDENCE": "INSUFFICIENT EVIDENCE", "VERIFICATION_ERROR": "VERIFICATION ERROR",
}

CSS = """
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

  /* ---- Wormhole-style shell: deep space background with slow-drifting colour glows ---- */
  html, body, [class*="css"], .stApp, .stMarkdown, button, input, textarea, select {
    font-family: 'Inter', system-ui, -apple-system, 'Segoe UI', sans-serif !important;
  }
  .stApp {background:#0b0a1a; color:#ece9ff;}
  .stApp::before {
    content:""; position:fixed; inset:-20%; z-index:0; pointer-events:none;
    background:
      radial-gradient(40% 35% at 20% 15%, rgba(139,92,246,.35), transparent 70%),
      radial-gradient(35% 30% at 85% 20%, rgba(236,72,153,.25), transparent 70%),
      radial-gradient(45% 40% at 60% 95%, rgba(59,130,246,.25), transparent 70%);
    filter: blur(40px); animation: tg-drift 22s ease-in-out infinite alternate;
  }
  @keyframes tg-drift {
    0%   {transform: translate3d(0,0,0) scale(1);}
    100% {transform: translate3d(-4%,3%,0) scale(1.08);}
  }
  @media (prefers-reduced-motion: reduce) {.stApp::before {animation:none;}}
  [data-testid="stAppViewContainer"], [data-testid="stHeader"] {background: transparent !important;}
  [data-testid="stAppViewContainer"] > .main, .main .block-container {position:relative; z-index:1;}
  .main .block-container {max-width: 1100px; padding-top: 2.2rem;}

  /* ---- sidebar: frosted glass ---- */
  [data-testid="stSidebar"] {
    background: rgba(18,16,40,.72) !important; backdrop-filter: blur(18px);
    border-right: 1px solid rgba(255,255,255,.08);
  }

  /* ---- headings ---- */
  .tg-title {font-size: 2.3rem; font-weight: 800; letter-spacing:-0.02em; margin-bottom: 0;
             background: linear-gradient(90deg,#ffffff 0%,#c4b5fd 45%,#f9a8d4 100%);
             -webkit-background-clip:text; background-clip:text; color:transparent;}
  .tg-sub {color: #a8a3c7; margin-top: 0.25rem; font-size: 1rem;}

  /* ---- glass cards ---- */
  .tg-card, .tg-answer, .tg-withheld, .tg-evidence,
  [data-testid="stExpander"], [data-testid="stForm"], [data-testid="stMetric"] {
    background: rgba(255,255,255,.05) !important; border:1px solid rgba(255,255,255,.10) !important;
    backdrop-filter: blur(14px); box-shadow: 0 10px 40px rgba(0,0,0,.35);
  }
  .tg-card {border-radius:18px; padding:16px 18px; margin-bottom:14px; color:#ece9ff;}
  .tg-card, .tg-card * {color:#ece9ff;}
  [data-testid="stExpander"], [data-testid="stForm"] {border-radius:18px !important;}
  [data-testid="stMetric"] {border-radius:16px; padding:12px 16px;}

  .tg-answer {border-radius:18px; padding:18px 20px; font-size:1.03rem; color:#e7fff5;
              border-color: rgba(16,185,129,.45) !important;
              box-shadow: 0 0 0 1px rgba(16,185,129,.15), 0 10px 40px rgba(16,185,129,.12);}
  .tg-withheld {border-radius:18px; padding:18px 20px; color:#ffe4ea;
                border-color: rgba(244,63,94,.45) !important;
                box-shadow: 0 0 0 1px rgba(244,63,94,.15), 0 10px 40px rgba(244,63,94,.12);}
  .tg-evidence {border-left:3px solid #a78bfa !important; padding:10px 14px; border-radius:12px;
                margin:8px 0; font-size:0.9rem; color:#ddd8ff;}
  .tg-contra {border-left:3px solid #f43f5e !important; background: rgba(244,63,94,.07) !important;}
  .tg-cite, .tg-evidence .tg-cite {color:#c4b5fd; font-size:0.8rem; font-weight:600;}
  .tg-claim {font-size:0.98rem; margin:4px 0 6px 0; color:#ece9ff;}

  /* ---- pills ---- */
  .tg-badge {display:inline-block; padding: 4px 14px; border-radius: 999px; color:#fff;
             font-weight:600; font-size:0.8rem; letter-spacing:0.03em;
             box-shadow: 0 4px 18px rgba(0,0,0,.35);}
  .tg-sig {display:inline-block; font-size:0.72rem; padding:2px 9px; border-radius:999px; margin:2px 4px 2px 0;
           border:1px solid rgba(255,255,255,.15); color:#d6d2f5; background: rgba(255,255,255,.04);}
  .tg-sig-pass {background: rgba(16,185,129,.14); border-color: rgba(16,185,129,.45); color:#a7f3d0;}
  .tg-sig-fail {background: rgba(244,63,94,.14);  border-color: rgba(244,63,94,.45);  color:#fecdd3;}

  /* ---- inputs & buttons: big rounded, glowing gradient CTA ---- */
  .stTextInput input, .stTextArea textarea, .stNumberInput input,
  [data-baseweb="select"] > div {
    background: rgba(255,255,255,.06) !important; border:1px solid rgba(255,255,255,.12) !important;
    border-radius: 14px !important; color:#ece9ff !important;
  }
  .stTextArea textarea:focus, .stTextInput input:focus {
    border-color:#a78bfa !important; box-shadow: 0 0 0 3px rgba(167,139,250,.25) !important;
  }
  /* all buttons: pill shape; secondary ones (e.g. Remove) stay quiet glass, red on hover */
  .stButton > button, .stDownloadButton > button, [data-testid="stFormSubmitButton"] > button {
    border-radius:999px !important; padding:.55rem 1.4rem !important; font-weight:600 !important;
    color:#ece9ff !important; background: rgba(255,255,255,.06) !important;
    border:1px solid rgba(255,255,255,.16) !important; transition: all .15s ease;
  }
  .stButton > button[kind="secondary"]:hover {
    border-color: rgba(244,63,94,.6) !important; color:#fecdd3 !important; background: rgba(244,63,94,.10) !important;
  }
  /* primary actions (Verify, Ingest) + downloads: the glowing gradient CTA */
  .stButton > button[kind="primary"], .stDownloadButton > button, [data-testid="stFormSubmitButton"] > button {
    border:0 !important; color:#fff !important;
    background: linear-gradient(90deg,#7c3aed 0%,#db2777 100%) !important;
    box-shadow: 0 8px 28px rgba(124,58,237,.40);
  }
  .stButton > button[kind="primary"]:hover, .stDownloadButton > button:hover,
  [data-testid="stFormSubmitButton"] > button:hover {
    transform: translateY(-1px); box-shadow: 0 12px 34px rgba(219,39,119,.45);
  }
  [data-testid="stFileUploaderDropzone"] {
    background: rgba(255,255,255,.04) !important; border: 2px dashed rgba(167,139,250,.45) !important;
    border-radius: 20px !important;
  }
  [data-testid="stAlert"] {border-radius:14px; backdrop-filter: blur(10px);}
  [data-testid="stDataFrame"], [data-testid="stTable"] {border-radius:14px; overflow:hidden;}
  hr {border-color: rgba(255,255,255,.08) !important;}
</style>
"""


@st.cache_resource
def get_db() -> Database:
    settings = load_settings()
    return Database(settings.path("db_path"))


@st.cache_resource
def get_base_settings():
    return load_settings()


@st.cache_data(ttl=10)
def available_models(base_url: str) -> list[str]:
    return list_models(base_url)


def badge(text: str, status: str) -> str:
    color = STATUS_COLORS.get(status, "#5a6b7b")
    return f'<span class="tg-badge" style="background:{color}">{text}</span>'


def header(title: str, subtitle: str):
    st.markdown(CSS, unsafe_allow_html=True)
    st.markdown(f'<div class="tg-title">{title}</div><div class="tg-sub">{subtitle}</div>', unsafe_allow_html=True)
    st.write("")


def signal_chips(signals: list[dict]) -> str:
    chips = []
    for s in signals:
        passed = s.get("passed")
        cls = "tg-sig" + ("" if passed is None else (" tg-sig-pass" if passed else " tg-sig-fail"))
        mark = "–" if passed is None else ("pass" if passed else "FAIL")
        chips.append(f'<span class="{cls}" title="{s.get("detail","")}">{s["name"]}: {mark}</span>')
    return "".join(chips)
