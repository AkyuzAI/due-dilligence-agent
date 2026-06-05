"""
Due Diligence Agent — Streamlit UI
Run with: streamlit run app.py
"""

import streamlit as st
import time
from utils.parsers import normalise_url, cache_key, risk_colour, sentiment_emoji
from agent.orchestrator import DueDiligenceAgent
from agent.report import DueDiligenceReport, export_pdf, RiskLevel

# ── Page config ───────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Due Diligence Agent",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────

st.markdown("""
<style>
  /* Global */
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
  html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

  /* Hide default Streamlit chrome */
  #MainMenu, footer, header { visibility: hidden; }

  /* Hero */
  .hero { text-align: center; padding: 2.5rem 0 1.5rem; }
  .hero h1 { font-size: 2.6rem; font-weight: 700; letter-spacing: -1px; margin-bottom: 0.3rem; }
  .hero p  { color: #888; font-size: 1.05rem; margin: 0; }

  /* Cards */
  .card {
    background: #16161e;
    border: 1px solid #2a2a3a;
    border-radius: 12px;
    padding: 1.25rem 1.5rem;
    margin-bottom: 1rem;
  }
  .card h3 { margin: 0 0 0.6rem; font-size: 1rem; font-weight: 600; color: #e0e0f0; }

  /* Risk badges */
  .badge {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 999px;
    font-size: 0.75rem;
    font-weight: 600;
    margin-right: 6px;
  }
  .badge-high   { background:#3d1219; color:#e63946; border:1px solid #e63946; }
  .badge-medium { background:#3d2b0a; color:#f4a261; border:1px solid #f4a261; }
  .badge-low    { background:#0d2b1a; color:#52b788; border:1px solid #52b788; }
  .badge-none   { background:#1e1e2e; color:#adb5bd; border:1px solid #adb5bd; }

  /* Confidence meter */
  .conf-score {
    font-size: 3rem;
    font-weight: 700;
    line-height: 1;
  }

  /* Source links */
  .source-item {
    font-size: 0.8rem;
    color: #7ba4e8;
    word-break: break-all;
    margin-bottom: 4px;
  }

  /* KV rows */
  .kv { display: flex; gap: 12px; margin-bottom: 6px; font-size: 0.9rem; }
  .kv-key { color: #888; min-width: 130px; }
  .kv-val { color: #e0e0f0; font-weight: 500; }

  /* Divider */
  .divider { border: none; border-top: 1px solid #2a2a3a; margin: 1rem 0; }

  /* Example buttons */
  .example-row { display:flex; gap:8px; flex-wrap:wrap; margin-top:8px; }
</style>
""", unsafe_allow_html=True)


# ── Sidebar ───────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("### ⚙️ Settings")
    depth = st.select_slider(
        "Research depth",
        options=["quick", "standard", "deep"],
        value="standard",
        help="Quick: 6 searches · Standard: 10 · Deep: 16",
    )

    st.markdown("---")
    st.markdown("### 🧪 Try an example")
    examples = ["Stripe", "Theranos", "Anthropic", "WeWork", "Mistral AI"]
    for ex in examples:
        if st.button(ex, use_container_width=True):
            st.session_state["company_input"] = ex

    st.markdown("---")
    st.markdown(
        "<small style='color:#555'>Built by Dylan Akyuz · "
        "[GitHub](https://github.com/AkyuzAI) · "
        "Powered by GPT-4o + Tavily</small>",
        unsafe_allow_html=True,
    )


# ── Hero ──────────────────────────────────────────────────────────────────

st.markdown("""
<div class="hero">
  <h1>🔍 Due Diligence Agent</h1>
  <p>Drop in a company name or URL. Get a structured AI-powered research report in minutes.</p>
</div>
""", unsafe_allow_html=True)


# ── Input ─────────────────────────────────────────────────────────────────

col1, col2 = st.columns([5, 1])
with col1:
    company_input = st.text_input(
        label="Company",
        placeholder="e.g. Stripe   or   https://stripe.com",
        value=st.session_state.get("company_input", ""),
        label_visibility="collapsed",
    )
with col2:
    run_button = st.button("Run Report →", type="primary", use_container_width=True)

st.caption("Enter a company name or website URL. The agent will research it across news, financials, legal records, and more.")


# ── Rate limit guard ──────────────────────────────────────────────────────

if "last_run" not in st.session_state:
    st.session_state["last_run"] = 0
if "report_cache" not in st.session_state:
    st.session_state["report_cache"] = {}


# ── Run the agent ─────────────────────────────────────────────────────────

if run_button and company_input.strip():

    # Simple rate limit: 30s between runs
    elapsed = time.time() - st.session_state["last_run"]
    if elapsed < 30:
        st.warning(f"Please wait {int(30 - elapsed)}s before running another report.")
        st.stop()

    company_name, company_url = normalise_url(company_input.strip())
    ck = cache_key(company_name, depth)

    # Check cache
    if ck in st.session_state["report_cache"]:
        st.info("Showing cached report. Clear cache in sidebar to re-run.")
        report: DueDiligenceReport = st.session_state["report_cache"][ck]
    else:
        # Live agent run
        status_placeholder = st.empty()
        steps = []

        def on_status(emoji: str, msg: str):
            steps.append(f"{emoji} {msg}")
            with status_placeholder.container():
                with st.status("🤖 Agent is researching...", expanded=True) as s:
                    for step in steps:
                        st.write(step)

        try:
            agent  = DueDiligenceAgent(depth=depth)
            report = agent.run(company_name, on_status=on_status)
            st.session_state["report_cache"][ck]  = report
            st.session_state["last_run"] = time.time()
            status_placeholder.empty()
        except Exception as e:
            st.error(f"Agent error: {e}")
            st.stop()

    # ── Render report ─────────────────────────────────────────────────────
    st.markdown("---")

    # Header row
    hc1, hc2, hc3 = st.columns([3, 1, 1])
    with hc1:
        snap = report.company_snapshot
        st.markdown(f"## {snap.name}")
        st.caption(f"{snap.industry}  ·  {snap.headquarters or 'HQ unknown'}  ·  {snap.founded or 'Founded unknown'}")
        if snap.website:
            st.markdown(f"🌐 [{snap.website}]({snap.website})")
    with hc2:
        score = report.confidence.score
        colour = "#52b788" if score >= 70 else "#f4a261" if score >= 40 else "#e63946"
        st.markdown(
            f"<div style='text-align:center'>"
            f"<div style='color:{colour}; font-size:2.8rem; font-weight:700; line-height:1'>{score}</div>"
            f"<div style='color:#888; font-size:0.8rem; margin-top:4px'>Confidence / 100</div>"
            f"</div>",
            unsafe_allow_html=True,
        )
    with hc3:
        sent = report.sentiment.overall.value
        st.markdown(
            f"<div style='text-align:center'>"
            f"<div style='font-size:2.2rem; line-height:1'>{sentiment_emoji(sent)}</div>"
            f"<div style='color:#888; font-size:0.8rem; margin-top:4px'>{sent} sentiment</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

    st.markdown("<hr class='divider'>", unsafe_allow_html=True)

    # Risk flags — shown prominently at the top
    if report.risk_flags:
        high_flags = [f for f in report.risk_flags if f.level == RiskLevel.HIGH]
        if high_flags:
            with st.container():
                st.markdown("#### ⚑ High-Priority Risk Flags")
                for flag in high_flags:
                    st.markdown(
                        f"<div class='card'>"
                        f"<span class='badge badge-high'>HIGH</span>"
                        f"<strong>{flag.category}</strong> — {flag.description}"
                        f"{'<br><small style=\"color:#555\">Source: ' + flag.source + '</small>' if flag.source else ''}"
                        f"</div>",
                        unsafe_allow_html=True,
                    )

    # Main content — 2 columns
    left, right = st.columns([3, 2])

    with left:

        with st.expander("🏢 Company Snapshot", expanded=True):
            st.write(snap.business_description)
            if snap.size_estimate:
                st.markdown(f"**Size:** {snap.size_estimate}")

        with st.expander("💼 Business Model", expanded=True):
            st.write(report.business_model)

        with st.expander("💰 Funding & Financials", expanded=True):
            f = report.funding_financials
            cols = st.columns(2)
            with cols[0]:
                st.metric("Total Raised", f.total_raised or "Unknown")
                st.metric("Valuation",    f.valuation    or "Unknown")
            with cols[1]:
                st.metric("Last Round",   f.last_round   or "Unknown")
            if f.known_investors:
                st.markdown("**Known investors:** " + " · ".join(f.known_investors))
            if f.revenue_signals:
                st.caption(f.revenue_signals)
            if f.financial_health_note:
                st.info(f.financial_health_note)

        with st.expander("🗺️ Market Position"):
            m = report.market_position
            st.markdown(f"**Target market:** {m.target_market}")
            if m.key_competitors:
                st.markdown("**Competitors:** " + "  ·  ".join(m.key_competitors))
            if m.differentiation:
                st.markdown(f"**Differentiation:** {m.differentiation}")
            if m.competitive_moat:
                st.markdown(f"**Moat:** {m.competitive_moat}")
            if m.market_size_signal:
                st.caption(f"Market size signal: {m.market_size_signal}")

    with right:

        with st.expander("⚑ All Risk Flags", expanded=True):
            if report.risk_flags:
                for flag in report.risk_flags:
                    level_class = f"badge-{flag.level.value.lower()}"
                    st.markdown(
                        f"<div class='card'>"
                        f"<span class='badge {level_class}'>{flag.level.value.upper()}</span> "
                        f"<strong>{flag.category}</strong><br>"
                        f"<span style='font-size:0.9rem;color:#ccc'>{flag.description}</span>"
                        f"{'<br><small style=\"color:#555\">📎 ' + flag.source + '</small>' if flag.source else ''}"
                        f"</div>",
                        unsafe_allow_html=True,
                    )
            else:
                st.success("No significant risk flags identified.")

        with st.expander("📰 Sentiment & News"):
            sent = report.sentiment
            st.markdown(
                f"**News tone:** {sentiment_emoji(sent.news_tone.value)} {sent.news_tone.value}"
            )
            if sent.employee_signals:
                st.markdown(f"**Employee signals:** {sent.employee_signals}")
            if sent.recent_headlines:
                st.markdown("**Recent headlines:**")
                for h in sent.recent_headlines:
                    st.markdown(f"- {h}")

        with st.expander("📊 Confidence Breakdown"):
            conf = report.confidence
            st.progress(conf.score / 100)
            st.markdown(f"**Data found:** {conf.data_richness}")
            st.markdown(f"**Gaps:** {conf.data_gaps}")
            if conf.caveat:
                st.caption(conf.caveat)

        with st.expander("🔗 Sources"):
            for src in report.sources:
                st.markdown(
                    f"<div class='source-item'>• <a href='{src}' target='_blank'>{src}</a></div>",
                    unsafe_allow_html=True,
                )

    # ── Export ────────────────────────────────────────────────────────────
    st.markdown("---")
    ec1, ec2, ec3 = st.columns([2, 2, 4])
    with ec1:
        try:
            pdf_bytes = export_pdf(report)
            st.download_button(
                label="⬇️ Download PDF Report",
                data=pdf_bytes,
                file_name=f"{snap.name.replace(' ', '_')}_due_diligence.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
        except Exception as e:
            st.caption(f"PDF export error: {e}")
    with ec2:
        if st.button("🗑️ Clear Cache & Re-run", use_container_width=True):
            ck = cache_key(company_name, depth)
            st.session_state["report_cache"].pop(ck, None)
            st.rerun()

    # Disclaimer
    st.caption(report.disclaimer)


# ── Empty state ───────────────────────────────────────────────────────────
elif not run_button:
    st.markdown("""
    <div style='text-align:center; padding: 3rem 0; color:#555'>
      <div style='font-size:3rem'>🏢</div>
      <p style='margin-top:1rem'>Enter a company above to generate a due diligence report.</p>
      <p style='font-size:0.85rem'>The agent will search news, financials, legal records, and more —
      then synthesise everything into a structured report with risk flags and a confidence score.</p>
    </div>
    """, unsafe_allow_html=True)
