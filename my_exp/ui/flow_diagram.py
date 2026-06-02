"""
my_exp.ui.flow_diagram
=================
Optimization pipeline flow diagram — renders the 5-step optimization
pipeline as a visual diagram in Streamlit.
"""

import streamlit as st


def render_flow_diagram(sql: str, features: dict, recs: dict, candidates: list):
    """Render the full optimization pipeline as a visual flow diagram."""

    opps = features.get("optimization_opportunities", [])
    rec_list = recs.get("recommendations", [])

    # Colors
    COLORS = {
        "input": "#1e3a5f",
        "parse": "#2d4a6f",
        "analyze": "#4a1e5f",
        "recommend": "#5f1e2d",
        "output": "#1e5f4a",
        "arrow": "#888",
    }

    def node(title, subtitle, color, content=None):
        st.markdown(f"""
        <div style="
            background:{color};
            color:#fff;
            padding:16px 20px;
            border-radius:12px;
            margin:6px 0;
            text-align:center;
            box-shadow:0 2px 8px rgba(0,0,0,0.2);
        ">
            <b style="font-size:16px">{title}</b><br>
            <span style="font-size:12px;opacity:0.8">{subtitle}</span>
        </div>
        """, unsafe_allow_html=True)
        if content:
            with st.container():
                st.markdown(content)

    def arrow():
        st.markdown("""
        <div style="
            text-align:center;
            color:#888;
            font-size:20px;
            padding:2px 0;
        ">↓</div>
        """, unsafe_allow_html=True)

    # Step 1: Input
    node(
        "BUOC 1: INPUT",
        "SQL Query tu nguoi dung",
        COLORS["input"],
        f"```sql\n{sql[:200]}{'...' if len(sql) > 200 else ''}\n```",
    )
    arrow()

    # Step 2: Parse
    node(
        "BUOC 2: PARSE",
        "SQL → Cay AST (sqlglot)",
        COLORS["parse"],
    )
    arrow()

    # Step 3: Analyze
    complexity = features.get("complexity", {})
    node(
        "BUOC 3: ANALYZE",
        f"Do phuc tap: {complexity.get('level', 'N/A')} (score={complexity.get('score', 0)})",
        COLORS["analyze"],
    )

    # Show features
    feat_cols = st.columns(5)
    fc = [
        ("Bang", features.get("table_count", 0)),
        ("JOIN", features.get("join_count", 0)),
        ("Subquery", features.get("subquery_count", 0)),
        ("AGG", "Co" if features.get("has_aggregation") else "Khong"),
        ("GROUP BY", "Co" if features.get("has_group_by") else "Khong"),
    ]
    for i, (label, value) in enumerate(fc):
        with feat_cols[i]:
            st.metric(label, value)

    arrow()

    # Step 4: Rule Detection
    opp_labels = [o.get("rule", "?").replace("_", " ").title() for o in opps]
    opp_conf = [o.get("confidence", "?") for o in opps]

    node(
        "BUOC 4: DETECT",
        f"{len(opps)} co hoi duoc phat hien",
        COLORS["recommend"],
    )

    # Show detected opportunities as mini cards
    if opps:
        opp_cols = st.columns(min(len(opps), 4))
        for i, opp in enumerate(opps):
            rule = opp.get("rule", "?")
            conf = opp.get("confidence", "?")
            with opp_cols[i % 4]:
                conf_color = {"high": "green", "medium": "orange", "low": "blue"}.get(conf, "gray")
                st.markdown(
                    f":{conf_color}[**{rule.replace('_', ' ').title()}**]\n"
                    f"_{opp.get('estimated_benefit', '')}_",
                )

    arrow()

    # Step 5: Rule Recommendation
    rec_count = len(rec_list)
    node(
        "BUOC 5: RECOMMEND",
        f"{rec_count} luat duoc de xuat",
        COLORS["recommend"],
    )

    # Show recommended sequence
    for i, rec in enumerate(rec_list[:3], 1):
        rule = rec.get("rule", "?")
        priority = rec.get("priority", i)
        confidence = rec.get("confidence", "?")
        conf_color = {"Cao": "green", "Trung binh": "orange", "Thap": "blue"}.get(confidence, "gray")

        st.markdown(
            f"**P{priority}:** :{conf_color}[{confidence.upper()}] "
            f"**{rule.replace('_', ' ').title()}** — {rec.get('reason', '')}"
        )

    arrow()

    # Step 6: Rewrite Output
    changed = sum(1 for c in candidates if c.get("changed"))
    node(
        "BUOC 6: OUTPUT",
        f"{len(candidates)} candidates | {changed} da rewrite",
        COLORS["output"],
    )

    # Show candidates summary
    cand_cols = st.columns(min(len(candidates), 4))
    for i, c in enumerate(candidates[:4]):
        is_orig = c.get("is_original", False)
        changed = c.get("changed", False)
        badge = ":blue[GOC]" if is_orig else (":orange[DOI]" if changed else ":gray[--]")
        rules_str = ", ".join([r.replace("_", " ").title() for r in c.get("rules_applied", [])]) or "—"
        with cand_cols[i % 4]:
            st.caption(f"C#{i} {badge}: {rules_str}")


def render_compact_flow(sql: str, features: dict, recs: dict) -> str:
    """Render a compact single-line flow for inline display."""
    steps = [
        f"Input: {len(sql)} chars",
        f"Parse: {features.get('table_count', 0)} tables",
        f"Analyze: {len(features.get('optimization_opportunities', []))} opps",
        f"Recommend: {len(recs.get('recommendations', []))} rules",
    ]
    return " → ".join(steps)
