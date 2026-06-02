"""
my_exp.ui.components
====================
Reusable Streamlit UI components for the SQL Optimization Advisor.
"""

import streamlit as st
import json
from typing import Optional


def sql_input_widget(key: str = "sql_input", default: str = "") -> str:
    """SQL input text area."""
    return st.text_area(
        "Nhap cau lenh SQL:",
        value=default,
        height=150,
        placeholder="SELECT * FROM orders WHERE o_totalprice > 100000",
        key=key,
    )


def rule_card(rule_name: str, meta: dict, recommendation: dict = None, expanded: bool = False):
    """
    Render a rule card with metadata and recommendation.
    """
    color_map = {
        "high": "green",
        "medium": "orange",
        "low": "blue",
        "safe": "green",
        "risk": "red",
    }

    benefit_color = color_map.get(meta.get("expected_benefit", "medium"), "gray")
    risk_color = color_map.get(meta.get("risk_level", "low"), "gray")

    rule_display_name = meta.get("name_vi", meta.get("name", rule_name))

    with st.expander(f"**{rule_display_name}**", expanded=expanded):
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**Category:** `{meta.get('category', 'N/A')}`")
            st.markdown(f"**Benefit:** :{benefit_color}[{meta.get('expected_benefit', 'N/A').upper()}]")
        with col2:
            st.markdown(f"**Risk:** :{risk_color}[{meta.get('risk_level', 'N/A').upper()}]")
            st.markdown(f"**Priority:** #{recommendation.get('priority', '?') if recommendation else '?'}")

        st.markdown("---")

        if recommendation:
            st.markdown(f"**Ly do chon:** {recommendation.get('reason', 'N/A')}")
            st.markdown(f"**Loi ich:** {recommendation.get('expected_benefit', 'N/A')}")
            if recommendation.get('warning'):
                st.warning(f"**Canh bao:** {recommendation.get('warning')}")
            st.markdown(f"**Muc do tu van:** {recommendation.get('confidence', 'N/A')}")
        else:
            st.markdown(f"**Mo ta:** {meta.get('description', 'Khong co mo ta')}")

        # Safety checks
        safety = meta.get('safety_checks', [])
        if safety:
            with st.expander("Chi tiet kiem tra an toan"):
                for check in safety:
                    st.markdown(f"- {check}")


def candidate_card(candidate: dict, index: int = 0, show_sql: bool = True):
    """
    Render a rewrite candidate card.
    """
    is_original = candidate.get("is_original", False)
    rules_applied = candidate.get("rules_applied", [])
    changed = candidate.get("changed", False)

    # Header
    if is_original:
        header = f"**Candidate #{index}: SQL Goc**"
        badge = ":blue[SQL Goc]"
    elif rules_applied:
        rules_str = " + ".join([r.replace("_", " ").title() for r in rules_applied])
        header = f"**Candidate #{index}: {rules_str}**"
        badge = ":orange[Da Rewrite]" if changed else ":blue[Khong doi]"
    else:
        header = f"**Candidate #{index}**"
        badge = ":gray[Unknown]"

    with st.container():
        st.markdown(f"{header} {badge}")

        if show_sql:
            st.code(candidate.get("sql", ""), language="sql", wrap_lines=True)

        # Plan comparison
        plan = candidate.get("plan_comparison") or {}
        if plan and "error" not in plan:
            comp = plan.get("comparison")
            if comp:
                verdict_color = {
                    "better": "green",
                    "worse": "red",
                    "similar": "gray",
                }.get(comp.get("verdict", ""), "gray")

                m1 = plan.get("original", {}).get("metrics") or {}
                m2 = plan.get("rewritten", {}).get("metrics") or {}

                c1, c2, c3 = st.columns(3)
                with c1:
                    st.metric("Cost (Original)", f"{m1.get('total_cost', 0):.1f}")
                with c2:
                    st.metric("Cost (Rewrite)", f"{m2.get('total_cost', 0):.1f}")
                with c3:
                    pct = comp.get("cost_improvement_pct", 0)
                    delta = f"{pct:+.1f}%"
                    st.metric("Improvement", delta, delta_color="normal" if pct > 0 else "inverse")

        # Semantic check
        sem = candidate.get("semantic_check") or {}
        if sem:
            eq = sem.get("equivalent")
            conf = sem.get("confidence", 0)
            if eq is True:
                st.success(f"Semantic Equivalent (confidence: {conf:.0%})")
            elif eq is False:
                st.error(f"Not Equivalent: {sem.get('error', 'Unknown error')}")
            else:
                st.info(f"Semantic check: {sem.get('error', 'No data')}")

        st.markdown("---")


def plan_tree_view(plan: dict, prefix: str = "", depth: int = 0):
    """
    Render execution plan as a tree view.
    """
    if not plan or depth > 10:
        return

    def node_info(n: dict) -> str:
        parts = []
        if n.get("Node Type"):
            parts.append(n["Node Type"])
        if n.get("Operation"):
            parts.append(n["Operation"])
        if n.get("Total Cost"):
            parts.append(f"cost={n['Total Cost']:.1f}")
        if n.get("Execution Time"):
            parts.append(f"time={n['Execution Time']:.2f}ms")
        if n.get("Plan Rows"):
            parts.append(f"rows={n['Plan Rows']}")
        return " | ".join(parts)

    if isinstance(plan, dict):
        indent = "  " * depth
        info = node_info(plan)
        st.markdown(f"{indent}{prefix}{info}")

        for i, child in enumerate(plan.get("Plans", [])):
            child_prefix = "├─ " if i < len(plan["Plans"]) - 1 else "└─ "
            plan_tree_view(child, prefix + child_prefix, depth + 1)


def summary_table(candidates: list, recommendation: dict = None):
    """
    Render a summary comparison table of all candidates.
    """
    rows = []
    for i, c in enumerate(candidates):
        sem = c.get("semantic_check") or {}
        plan = c.get("plan_comparison") or {}
        comp = plan.get("comparison") if plan else None
        m1 = plan.get("original", {}).get("metrics") if plan else None
        m2 = plan.get("rewritten", {}).get("metrics") if plan else None

        rows.append({
            "#": i,
            "Type": "Original" if c.get("is_original") else "Rewrite",
            "Rules": ", ".join(c.get("rules_applied", [])) or "—",
            "Changed": "Yes" if c.get("changed") else "No",
            "Semantic": "Yes" if sem.get("equivalent") else ("No" if "equivalent" in sem else "—"),
            "Cost Orig": f"{m1.get('total_cost', 0):.0f}" if m1 else "—",
            "Cost Rew": f"{m2.get('total_cost', 0):.0f}" if m2 else "—",
            "Improve%": f"{comp.get('cost_improvement_pct', 0):+.1f}%" if comp else "—",
            "Verdict": comp.get("verdict_vi", "—") if comp else "—",
        })

    if rows:
        import pandas as pd
        df = pd.DataFrame(rows)

        # Highlight recommended row
        if recommendation:
            rec_id = recommendation.get("best_candidate_id")
            if rec_id is not None:
                def highlight_row(row):
                    if row["#"] == rec_id:
                        return ["background-color: #d4edda"] * len(row)
                    return [""] * len(row)
                st.dataframe(
                    df.style.apply(highlight_row, axis=1),
                    use_container_width=True,
                    hide_index=True,
                )
                st.caption(":green[Ghi chu: Dong duoc to sang la lua chon duoc de xuat boi he thong]")
            else:
                st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.dataframe(df, use_container_width=True, hide_index=True)


def rule_kb_browser():
    """
    Render the Knowledge Base browser page.
    """
    from my_exp.core.rules import RULE_METADATA

    st.markdown("## He Co So Tri Thuc (Knowledge Base)")
    st.markdown("---")

    categories = {
        "filter_optimization": "Toi Uu Loc (Filter)",
        "join_optimization": "Toi Uu JOIN",
        "aggregation_optimization": "Toi Uu Tong Hop (Aggregation)",
        "io_optimization": "Toi Uu I/O",
        "sort_optimization": "Toi Uu Sort",
    }

    tabs = st.tabs(list(categories.values()))

    for tab_idx, (cat_key, cat_name) in enumerate(categories.items()):
        with tabs[tab_idx]:
            rules_in_cat = {
                name: meta for name, meta in RULE_METADATA.items()
                if meta.get("category") == cat_key
            }

            if not rules_in_cat:
                st.info(f"Khong co quy tac trong danh muc '{cat_name}'")
                continue

            for rule_name, meta in rules_in_cat.items():
                with st.expander(f"**{meta.get('name_vi', rule_name)}**", expanded=False):
                    c1, c2 = st.columns([1, 1])
                    with c1:
                        st.markdown(f"**Ten:** `{meta.get('name', rule_name)}`")
                        st.markdown(f"**ID:** `{meta.get('id', '?')}`")
                        st.markdown(f"**Expected Benefit:** `{meta.get('expected_benefit', 'N/A')}`")
                        st.markdown(f"**Risk Level:** `{meta.get('risk_level', 'N/A')}`")

                    with c2:
                        benefit = meta.get("benefit_formula", meta.get("benefit", "Khong co"))
                        st.markdown(f"**Cong thuc loi ich:**\n```\n{benefit}\n```")

                    # Trigger patterns
                    triggers = meta.get("trigger_keywords", [])
                    if triggers:
                        st.markdown("**Trigger Keywords:**")
                        cols = st.columns(min(len(triggers), 3))
                        for i, t in enumerate(triggers):
                            with cols[i % 3]:
                                st.code(t, language="text")

                    # Example
                    example = meta.get("example", {})
                    if example:
                        st.markdown("**Vi du:**")
                        col_in, col_out = st.columns(2)
                        with col_in:
                            st.markdown("Input:")
                            st.code(example.get("input", ""), language="sql")
                        with col_out:
                            st.markdown("Output:")
                            st.code(example.get("output", ""), language="sql")


def json_viewer(data: dict, label: str = "Chi tiet (JSON)"):
    """Render a JSON viewer."""
    with st.expander(label):
        st.json(data, expanded=False)
