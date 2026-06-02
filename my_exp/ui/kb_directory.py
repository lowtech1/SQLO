"""
my_exp.ui.kb_directory
=====================
KB Directory viewer — renders the Knowledge Base rules as an interactive
tree in Streamlit, with real-time applicability status.
"""

import streamlit as st
from my_exp.core.rules import RULE_METADATA


RULE_ORDER = [
    ("KB-001", "predicate_pushdown", "Predicate Pushdown", "Day Dieu Kien Loc Xuong"),
    ("KB-002", "projection_pruning", "Projection Pruning", "Loai Bo Cot Thua"),
    ("KB-003", "join_reordering", "Join Reordering", "Doi Thu Tu JOIN"),
    ("KB-004", "subquery_unnesting", "Subquery Unnesting", "Chuyen Subquery Thanh JOIN"),
    ("KB-005", "aggregation_pushdown", "Aggregation Pushdown", "Day Phep Tong Hop Xuong"),
    ("KB-006", "redundant_join_elimination", "Redundant Join Elimination", "Loai Bo JOIN Du Thua"),
]

RULE_DESCRIPTIONS = {
    "predicate_pushdown": {
        "benefit": "High - Giam so dong trung gian theo selectivity",
        "risk": "Low",
        "trigger": "WHERE tren subquery trong FROM",
        "safety": ["Khong DISTINCT", "Khong GROUP BY", "Khong aggregate"],
    },
    "projection_pruning": {
        "benefit": "Medium - Giam I/O bandwidth",
        "risk": "Low",
        "trigger": "SELECT * hoac cot thua",
        "safety": ["Cot bo khong trong WHERE", "Cot bo khong trong GROUP BY"],
    },
    "join_reordering": {
        "benefit": "High - Giam intermediate rows theo tich",
        "risk": "Medium",
        "trigger": "2+ INNER JOINs",
        "safety": ["Chi INNER JOIN", "Khong LEFT/RIGHT/FULL JOIN"],
    },
    "subquery_unnesting": {
        "benefit": "High - Nested Loop O(n*m) -> Hash Join O(n+m)",
        "risk": "Medium",
        "trigger": "IN (SELECT) hoac EXISTS (SELECT)",
        "safety": ["Khong correlated", "Khong NOT IN", "Chi 1 bang trong subquery"],
    },
    "aggregation_pushdown": {
        "benefit": "High - Giam rows truoc khi aggregate",
        "risk": "Medium",
        "trigger": "GROUP BY tren subquery",
        "safety": ["Khong HAVING", "Khong DISTINCT aggregate"],
    },
    "redundant_join_elimination": {
        "benefit": "Medium - Loai bo hash join cost",
        "risk": "Low",
        "trigger": "JOIN ma bang khong duoc tham chieu",
        "safety": ["Khong OUTER JOIN", "Bang JOIN thuc su khong duoc dung"],
    },
}


def render_kb_header():
    """Render KB header with legend."""
    st.markdown("### He Co So Tri Thuc")
    st.markdown("**6 Luuat Toi Uu Hoa**")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(":green[●] Ap dung")
    with c2:
        st.markdown(":blue[●] Co san")
    with c3:
        st.markdown(":gray[●] Khong ap dung")


def render_kb_tree(applicable_rules=None, recommended_rules=None, key_prefix="kb"):
    """Render the KB directory as a collapsible tree."""
    applicable = set(applicable_rules or [])
    recommended = set(recommended_rules or [])

    for kb_id, rule_key, rule_name_en, rule_name_vi in RULE_ORDER:
        desc = RULE_DESCRIPTIONS.get(rule_key, {})
        meta = RULE_METADATA.get(rule_key, {})

        is_applicable = rule_key in applicable
        is_recommended = rule_key in recommended

        if is_recommended:
            icon = "[OK]"
            status_color = "green"
            status_text = "Recommended"
        elif is_applicable:
            icon = "[+]"
            status_color = "blue"
            status_text = "Co san"
        else:
            icon = "[-]"
            status_color = "gray"
            status_text = "Khong ap dung"

        benefit = desc.get("benefit", meta.get("expected_benefit", "N/A"))
        risk = desc.get("risk", meta.get("risk_level", "N/A"))

        benefit_color = "green" if "High" in benefit else ("orange" if "Medium" in benefit else "gray")
        risk_color = "green" if risk == "Low" else ("orange" if risk == "Medium" else "gray")

        header = icon + " **" + rule_name_vi + "** `[" + kb_id + "]` [" + status_text + "]"

        with st.expander(header, expanded=False):
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**Benefit:** [" + benefit + "]")
            with c2:
                st.markdown("**Risk:** [" + risk + "]")

            # Description using plain string concatenation
            rule_desc = meta.get("description", "")
            if not rule_desc:
                rule_desc = desc.get("trigger", "")
            st.markdown("**" + rule_name_en + "** -- " + rule_desc)

            st.markdown("---")
            st.markdown("**Trigger:** " + desc.get("trigger", "N/A"))

            safety = desc.get("safety", [])
            if safety:
                st.markdown("**Safety checks:**")
                for s in safety:
                    st.markdown("  - " + s)

            order_hints = {
                "predicate_pushdown": "Thu tu: 2 (sau subquery unnest)",
                "projection_pruning": "Thu tu: 6 (cuoi cung)",
                "join_reordering": "Thu tu: 3 (sau unnest)",
                "subquery_unnesting": "Thu tu: 1 (truoc tien, mo duong)",
                "aggregation_pushdown": "Thu tu: 4 (truoc join)",
                "redundant_join_elimination": "Thu tu: 5 (truoc cuoi)",
            }
            if rule_key in order_hints:
                st.info("**Thu tu toi uu:** " + order_hints[rule_key])

            example = meta.get("example", {})
            if example:
                st.markdown("**Vi du:**")
                c_in, c_out = st.columns(2)
                with c_in:
                    st.markdown("Input:")
                    st.code(example.get("input", ""), language="sql")
                with c_out:
                    st.markdown("Output:")
                    st.code(example.get("output", ""), language="sql")


def render_kb_summary(applicable_rules=None, recommended_rules=None):
    """Render a compact summary of KB status."""
    applicable = set(applicable_rules or [])
    recommended = set(recommended_rules or [])
    total = len(RULE_ORDER)
    app_count = len(applicable)
    rec_count = len(recommended)

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Tong luat", total)
    with c2:
        st.metric("Co the ap dung", app_count)
    with c3:
        st.metric("Duoc de xuat", rec_count)

    if total > 0:
        st.progress(app_count / total, text=str(app_count) + "/" + str(total) + " luat co the ap dung")


def render_rule_detail(rule_key):
    """Render detailed view of a single rule."""
    meta = RULE_METADATA.get(rule_key, {})
    desc = RULE_DESCRIPTIONS.get(rule_key, {})

    if not meta:
        st.error("Khong tim thay luat: " + str(rule_key))
        return

    st.markdown("## " + str(meta.get("name_vi", rule_key)))
    st.markdown("**" + str(meta.get("name", rule_key)) + "** -- `" + str(meta.get("category", "")) + "`")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**ID:** `" + str(meta.get("id", "?")) + "`")
        st.markdown("**Benefit:** " + desc.get("benefit", "N/A"))
    with c2:
        st.markdown("**Risk:** " + desc.get("risk", "N/A"))
        st.markdown("**Category:** " + meta.get("category", "N/A"))

    st.markdown("---")
    rule_desc = meta.get("description", "")
    if not rule_desc:
        rule_desc = desc.get("trigger", "")
    st.markdown("**Mo ta:** " + rule_desc)

    st.markdown("### Dieu kien an toan")
    preconditions = meta.get("preconditions", [])
    if not preconditions:
        preconditions = desc.get("safety", [])
    for p in preconditions:
        st.markdown("- " + str(p))

    formula = meta.get("benefit_formula", "")
    if formula:
        st.markdown("### Cong thuc loi ich")
        st.code(formula, language="text")

    example = meta.get("example", {})
    if example:
        st.markdown("### Vi du")
        c_in, c_out = st.columns(2)
        with c_in:
            st.markdown("**Input SQL:**")
            st.code(example.get("input", ""), language="sql")
        with c_out:
            st.markdown("**Output SQL:**")
            st.code(example.get("output", ""), language="sql")
            why = example.get("why", "")
            if why:
                st.caption("Why: " + why)
