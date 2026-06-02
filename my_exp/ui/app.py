# -*- coding: utf-8 -*-
"""
my_exp.ui.app
============
LLM-R2-Enhanced v2.1 - Interactive SQL Optimization Advisor
Full workspace: Left panel (Schema + KB) + Main (Editor + Optimization)
"""
import sys as _sys
import os as _os
_sys.path.insert(0, _os.path.abspath(_os.path.join(_os.path.dirname(__file__), '../..')))

import streamlit as st
import pandas as pd
import json as _json
import time

from my_exp.core.rules import RULE_METADATA
from my_exp.dss.optimizer_pipeline import OptimizationPipeline
from my_exp.ui.schema_explorer import load_schema_data, render_schema_panel, get_connection, execute_query as _exec_query
from my_exp.ui.kb_directory import render_kb_tree, render_kb_summary, render_rule_detail
from my_exp.ui.flow_diagram import render_flow_diagram
from my_exp.ui.ast_viewer import render_ast_full

RULE_NAMES_VI = {k: v.get("name_vi", v.get("name", k)) for k, v in RULE_METADATA.items()}

T = {
    "APP_SUBTITLE": "Phan tich SQL | De xuat luat | Sinh candidates | So sanh plans",
    "APP_WELCOME": "Chao muong den voi LLM-R2",
    "APP_WELCOME_DESC": "Nhap SQL va nhan Optimize de bat dau toi uu hoa.",
    "APP_WELCOME_DB": "Ket noi PostgreSQL tu sidebar de su dung day du tinh nang.",
    "DB_CONN_TITLE": "Ket Noi Database",
    "DB_HOST": "Host", "DB_PORT": "Port", "DB_NAME": "Database",
    "DB_USER": "User", "DB_PASSWORD": "Password",
    "BTN_CONNECT": "Ket Noi", "BTN_DISCONNECT": "Ngat",
    "SCHEMA_TITLE": "Schema Explorer", "SCHEMA_VIEW": "Xem cau truc",
    "SCHEMA_NO_CONN": "Ket noi DB de xem schema",
    "KB_TITLE": "He Co So Tri Thuc",
    "SYS_STATUS": "Trang thai he thong",
    "SYS_LLM_READY": "San sang", "SYS_LLM_FALLBACK": "Fallback pattern-based",
    "SYS_MODE_LLM": "LLM", "SYS_MODE_PATTERN": "Pattern-based",
    "DB_CONNECTED": "Da ket noi", "DB_DISCONNECTED": "Chua ket noi",
    "SCHEMA_TABLES": "bang",
    "RESULTS_COLS": "Cot", "RESULTS_ROWS": "Dong", "RESULTS_TIME": "Thoi gian",
    "OPT_TITLE": "Phan Tich Chi Tiet Tung Buoc",
    "OPT_METHOD": "Phuong phap",
    "TAB_AST": "1. AST & Flow", "TAB_STEPS": "2. Chi Tiet Luat",
    "TAB_COMPARE": "3. So Sanh Plans", "TAB_JSON": "4. JSON Output",
    "TAB_TABLE": "5. Bang So Sanh",
    "STEPS_BUOC": "Buoc", "STEPS_LY_DO": "Ly do", "STEPS_LOI_ICH": "Loi ich",
    "STEPS_CANH_BAO": "Canh bao", "STEPS_CHI_TIET": "Chi tiet luat",
    "COMPARE_TITLE": "So Sanh Plans",
    "COMPARE_BEST": "Phien Ban Duoc Chon",
    "COMPARE_ORIG": "SQL Goc", "COMPARE_REW": "SQL Rewrite",
    "COMPARE_ORIG_COST": "Cost (Goc)", "COMPARE_REW_COST": "Cost (Rewrite)",
    "COMPARE_IMPROVE": "Cai tien", "COMPARE_CANDIDATES": "Tat Ca Candidates",
    "COMPARE_EQUIV": "Tuong duong", "COMPARE_NOT_EQUIV": "Khong tuong duong",
    "JSON_TITLE": "JSON Output Day Du", "JSON_DOWNLOAD": "Tai JSON",
    "TABLE_TITLE": "Bang So Sanh Candidates",
    "TABLE_NUM": "#", "TABLE_TYPE": "Loai", "TABLE_RULES": "Luat",
    "TABLE_CHANGED": "Da doi", "TABLE_EQUIV": "Tuong duong",
    "TABLE_COST_ORIG": "Cost(Goc)", "TABLE_COST_REW": "Cost(Rewrite)",
    "TABLE_IMPROVE": "Cai tien%", "TABLE_HIGHLIGHT": "Dong xanh la lua chon duoc de xuat boi he thong",
    "STATS_QUERY_ID": "Query ID", "STATS_COMPLEXITY": "Do phuc tap",
    "STATS_CANDIDATES": "Candidates", "STATS_CHANGED": "Da doi", "STATS_EQUIV": "Tuong duong",
    "EDITOR_PLACEHOLDER": "SQL Query:", "BTN_RUN": "Run Query", "BTN_OPTIMIZE": "Optimize",
    "BTN_CLEAR": "Clear", "BTN_EXPORT": "Export", "BTN_HISTORY": "Lich su",
    "BTN_USE_EXAMPLE": "Dung vi du nay",
    "HISTORY_TITLE": "Lich su query", "HISTORY_EMPTY": "(Trong)",
    "NO_DB_WARNING": "Ket noi database truoc (sidebar) de chay SQL.",
    "LANG_ORIGINAL": "Goc", "LANG_REWRITE": "Doi",
    "LANG_CO": "Co", "LANG_KHONG": "Khong",
    "LANG_DANG_CHAY": "Dang chay...",
    "LANG_DANG_PHAN_TICH": "Dang phan tich va toi uu hoa...",
    "EXAMPLES_TITLE": "Vi du nhanh",
    "SYS_STATUS_SHORT": "Trang thai he thong",
    "APP_SUBTITLE_SHORT": "Phan tich SQL | De xuat luat | Sinh candidates | So sanh plans",
    "ERR_NO_RESULT": "Query chay thanh cong nhung khong co ket qua.",
    "EXAMPLES": {
        "Predicate Pushdown": "SELECT a FROM (SELECT a, b, c FROM t) AS sub WHERE a > 10",
        "Subquery Unnesting": "SELECT c_name FROM customer WHERE c_custkey IN (SELECT o_custkey FROM orders);",
        "Multiple JOINs": "SELECT * FROM orders o JOIN lineitem l ON o.id=l.o_id JOIN nation n ON o.n_id=n.id",
        "Aggregation Pushdown": "SELECT sub.a, SUM(sub.b) FROM (SELECT a, b FROM t) AS sub GROUP BY sub.a",
        "Filter Into Join": "SELECT * FROM a JOIN b ON a.id = b.a_id WHERE b.status = 'ACTIVE'",
        "Limit Pushdown": "SELECT * FROM (SELECT * FROM orders ORDER BY o_totalprice DESC) AS sub LIMIT 10",
        "Projection Pruning": "SELECT c_name FROM (SELECT * FROM customer) AS sub",
        "Complex Mixed": "SELECT c_name, SUM(o_totalprice) FROM customer c JOIN orders o ON c.c_custkey = o.o_custkey WHERE c.c_mktsegment='AUTOMOBILE' AND c.c_custkey IN (SELECT o2.o_custkey FROM orders o2 WHERE o2.o_totalprice > 500000) GROUP BY c_name ORDER BY SUM(o_totalprice) DESC LIMIT 20",
    }
}

_DEFAULTS = {
    "sql": "", "result": None, "db_connected": False,
    "schema_data": None, "db_conn_params": None, "conn": None,
    "query_result": None, "query_history": [], "use_llm": False, "max_cands": 5,
}
for _k, _v in _DEFAULTS.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v


def _save_history(sql):
    hist = st.session_state.get("query_history", [])
    if sql and sql not in hist:
        hist.insert(0, sql)
        st.session_state.query_history = hist[:20]


# ================================================================
# LEFT PANEL
# ================================================================
def render_left_panel():
    st.markdown("### LLM-R2 Enhanced")
    st.markdown(T["APP_SUBTITLE"])
    st.markdown("---")

    with st.expander(T["DB_CONN_TITLE"], expanded=True):
        params = st.session_state.get("db_conn_params") or {}
        host = st.text_input(
            T["DB_HOST"],
            value=params.get("host", _os.getenv("POSTGRES_HOST", "localhost")),
            key="db_host",
        )
        port = st.number_input(
            T["DB_PORT"],
            value=params.get("port", int(_os.getenv("POSTGRES_PORT", "5432"))),
            min_value=1, max_value=65535, key="db_port",
        )
        dbname = st.text_input(
            T["DB_NAME"],
            value=params.get("dbname", _os.getenv("POSTGRES_DB", "tpch")),
            key="db_name",
        )
        user = st.text_input(
            T["DB_USER"],
            value=params.get("user", _os.getenv("POSTGRES_USER", "postgres")),
            key="db_user",
        )
        password = st.text_input(T["DB_PASSWORD"], value="", type="password", key="db_pass")
        cp = {"host": host, "port": port, "dbname": dbname, "user": user, "password": password}

        c1, c2 = st.columns(2)
        with c1:
            if st.button(T["BTN_CONNECT"], use_container_width=True):
                st.session_state.db_conn_params = cp
                st.session_state.db_connected = False
                try:
                    conn = get_connection(**cp)
                    st.session_state.conn = conn
                    st.session_state.db_connected = True
                    schema = load_schema_data(host, port, dbname, user, password)
                    st.session_state.schema_data = schema
                    st.success(T["DB_CONNECTED"] + " " + dbname)
                    st.rerun()
                except Exception as e:
                    st.error(str(e))
        with c2:
            if st.button(T["BTN_DISCONNECT"], use_container_width=True):
                st.session_state.db_connected = False
                st.session_state.schema_data = None
                if st.session_state.get("conn"):
                    try:
                        st.session_state.conn.close()
                    except Exception:
                        pass
                st.rerun()

    st.markdown("---")

    if st.session_state.get("db_connected") and st.session_state.get("schema_data"):
        schema = st.session_state.schema_data
        if schema.connected:
            st.markdown("### " + T["SCHEMA_TITLE"])
            st.markdown(schema.db_name + " — " + str(len(schema.tables)) + " " + T["SCHEMA_TABLES"])
            with st.expander(T["SCHEMA_VIEW"], expanded=True):
                render_schema_panel(schema, key_prefix="sidebar")
    else:
        st.info(T["SCHEMA_NO_CONN"])

    st.markdown("---")
    st.markdown("### " + T["KB_TITLE"])

    result = st.session_state.get("result")
    if result:
        features = result.get("analysis", {}).get("summary", {})
        recs = result.get("rule_recommendations", {})
        applicable = [o.get("rule") for o in features.get("optimization_opportunities", [])]
        recommended = [r.get("rule") for r in recs.get("recommendations", [])]
        render_kb_summary(applicable, recommended)
        render_kb_tree(applicable, recommended)
    else:
        render_kb_tree()

    st.markdown("---")
    with st.expander(T["SYS_STATUS"], expanded=False):
        connected = st.session_state.get("db_connected", False)
        st.markdown("**Database:** " + (T["DB_CONNECTED"] if connected else T["DB_DISCONNECTED"]))
        llm_ok = bool(_os.getenv("ANTHROPIC_API_KEY"))
        st.markdown("**LLM:** " + (T["SYS_LLM_READY"] if llm_ok else T["SYS_LLM_FALLBACK"]))
        st.markdown("**Mode:** " + (T["SYS_MODE_LLM"] if st.session_state.get("use_llm") else T["SYS_MODE_PATTERN"]))


# ================================================================
# MAIN WORKSPACE
# ================================================================
def render_main_workspace():
    st.markdown("""
    <div style="background:linear-gradient(135deg,#1e3a5f,#2d4a6f);color:#fff;padding:16px 20px;border-radius:10px;margin-bottom:16px">
    <h2 style="margin:0">LLM-R2: Interactive SQL Optimization Workspace</h2>
    <p style="margin:4px 0 0;color:#ccc;font-size:13px">""" + T["APP_SUBTITLE"] + """</p>
    </div>
    """, unsafe_allow_html=True)

    tcol1, tcol2, tcol3, tcol4 = st.columns([1, 1, 1, 2])
    conn = st.session_state.get("conn")
    db_connected = st.session_state.get("db_connected", False)

    with tcol1:
        run_btn = st.button(T["BTN_RUN"], type="primary", use_container_width=True)
    with tcol2:
        opt_btn = st.button(T["BTN_OPTIMIZE"], use_container_width=True)
    with tcol3:
        if st.button(T["BTN_CLEAR"], use_container_width=True):
            st.session_state.sql = ""
            st.session_state.result = None
            st.session_state.query_result = None
            st.rerun()
    with tcol4:
        llm_chk = st.checkbox("LLM Mode", value=st.session_state.get("use_llm", False), key="llm_chk")
        st.session_state.use_llm = llm_chk

    sql = st.text_area(
        T["EDITOR_PLACEHOLDER"],
        value=st.session_state.get("sql", ""),
        height=200,
        placeholder="SELECT * FROM orders WHERE o_totalprice > 100000",
        key="main_sql",
    )
    st.session_state.sql = sql

    hist = st.session_state.get("query_history", [])
    if hist:
        selected = st.selectbox(
            T["HISTORY_TITLE"],
            [T["HISTORY_EMPTY"]] + hist,
            key="hist_sel",
        )
        if selected and selected != T["HISTORY_EMPTY"]:
            st.session_state.sql = selected
            st.rerun()

    if run_btn and sql.strip():
        st.session_state.query_result = None
        if conn and db_connected:
            with st.spinner(T["LANG_DANG_CHAY"]):
                t0 = time.time()
                qr = _exec_query(conn, sql)
                qr["elapsed_sec"] = round(time.time() - t0, 3)
                st.session_state.query_result = qr
                _save_history(sql)
        else:
            st.warning(T["NO_DB_WARNING"])

    qr = st.session_state.get("query_result")
    if qr:
        st.markdown("#### " + T["RESULTS_TITLE"])
        m1, m2, m3 = st.columns(3)
        with m1:
            st.metric(T["RESULTS_COLS"], len(qr.get("columns", [])))
        with m2:
            st.metric(T["RESULTS_ROWS"], "{:,}".format(qr.get("total_rows", 0)))
        with m3:
            st.metric(T["RESULTS_TIME"], "{:.3f}s".format(qr.get("elapsed_sec", 0)))
        if qr.get("success"):
            if qr.get("columns"):
                df = pd.DataFrame(qr.get("rows", []), columns=qr.get("columns", []))
                st.dataframe(df, use_container_width=True, hide_index=True, height=250)
            else:
                st.info(T["ERR_NO_RESULT"])
        else:
            st.error(qr.get("error", "Unknown error"))

    st.markdown("---")

    if opt_btn and sql.strip():
        st.session_state.result = None
        with st.spinner(T["LANG_DANG_PHAN_TICH"]):
            pipeline = OptimizationPipeline(
                use_llm=st.session_state.get("use_llm", False) and bool(_os.getenv("ANTHROPIC_API_KEY")),
                dbname=st.session_state.get("db_conn_params", {}).get("dbname"),
            )
            result = pipeline.run_full(sql.strip(), max_candidates=st.session_state.get("max_cands", 5))
            st.session_state.result = result
            _save_history(sql)

    result = st.session_state.get("result")
    if result:
        _render_optimization_output(result, sql)
    else:
        _render_welcome()


# ================================================================
# OPTIMIZATION OUTPUT
# ================================================================
def _render_optimization_output(result, sql):
    features = result.get("analysis", {}).get("summary", {})
    recs = result.get("rule_recommendations", {})
    candidates = result.get("candidates", [])
    recommendation = result.get("recommendation", {})

    s1, s2, s3, s4, s5 = st.columns(5)
    with s1:
        st.metric(T["STATS_QUERY_ID"], result.get("query_id", "?"))
    with s2:
        st.metric(T["STATS_COMPLEXITY"], features.get("complexity", {}).get("level", "?"))
    with s3:
        st.metric(T["STATS_CANDIDATES"], len(candidates))
    with s4:
        changed = sum(1 for c in candidates if c.get("changed"))
        st.metric(T["STATS_CHANGED"], changed)
    with s5:
        eq_cnt = sum(1 for c in candidates if (c.get("semantic_check") or {}).get("equivalent") is True)
        st.metric(T["STATS_EQUIV"], "{}/{}".format(eq_cnt, len(candidates)))

    tabs = st.tabs([
        T["TAB_AST"], T["TAB_STEPS"], T["TAB_COMPARE"], T["TAB_JSON"], T["TAB_TABLE"],
    ])

    with tabs[0]:
        st.markdown("#### " + T["OPT_TITLE"])
        render_flow_diagram(sql, features, recs, candidates)
        st.markdown("---")
        st.markdown("#### AST Tree")
        render_ast_full(sql, max_depth=5)

    with tabs[1]:
        _render_steps_detail(recs)

    with tabs[2]:
        _render_compare(result, candidates, recommendation)

    with tabs[3]:
        _render_json_output(result, sql, features, recs, candidates, recommendation)

    with tabs[4]:
        _render_comparison_table(candidates, recommendation)


def _render_steps_detail(recs):
    st.markdown("#### " + T["OPT_TITLE"])
    st.markdown("**" + T["OPT_METHOD"] + ":** " + recs.get("method", "pattern").upper())
    for i, rec in enumerate(recs.get("recommendations", [])):
        rule = rec.get("rule", "?")
        priority = rec.get("priority", i + 1)
        confidence = rec.get("confidence", "?")
        reason = rec.get("reason", "")
        benefit = rec.get("expected_benefit", "")
        warning = rec.get("warning")
        conf_color = {"Cao": "green", "Trung binh": "orange", "Thap": "blue"}.get(confidence, "gray")
        conf_html = {"Cao": "color:green", "Trung binh": "color:orange", "Thap": "color:#17a2b8"}.get(confidence, "color:#888")
        st.markdown(
            "<div style='border:1px solid #ddd;padding:12px;border-radius:8px;margin:8px 0'>"
            "<b>{} {}:</b> <b>{}</b> "
            "<span style='{}'>[{}]</span>"
            "<br><b>{}:</b> {}"
            "<br><b>{}:</b> {}"
            "</div>".format(
                T["STEPS_BUOC"], priority,
                RULE_NAMES_VI.get(rule, rule),
                conf_html, confidence.upper(),
                T["STEPS_LY_DO"], reason,
                T["STEPS_LOI_ICH"], benefit,
            ),
            unsafe_allow_html=True,
        )
        if warning:
            st.warning(T["STEPS_CANH_BAO"] + ": " + warning)
        with st.expander(T["STEPS_CHI_TIET"]):
            render_rule_detail(rule)


def _render_compare(result, candidates, recommendation):
    st.markdown("#### " + T["COMPARE_TITLE"])
    if recommendation and "error" not in recommendation:
        best = recommendation
        if not best.get("is_original"):
            rules_str = ", ".join([RULE_NAMES_VI.get(r, r) for r in best.get("best_rules", [])])
            st.success("{} #{}: {}".format(T["COMPARE_BEST"], best.get("best_candidate_id", "?"), rules_str))
            st.code(best.get("best_sql", ""), language="sql")
            if best.get("improvement_pct") is not None:
                st.metric(T["COMPARE_IMPROVE"], "{:+.1f}%".format(best["improvement_pct"]))
            eq = best.get("semantic_equivalent")
            if eq is True:
                st.success(T["COMPARE_EQUIV"])
            elif eq is False:
                st.error(T["COMPARE_NOT_EQUIV"])

    st.markdown("---")
    st.markdown("#### " + T["COMPARE_CANDIDATES"])
    for i, c in enumerate(candidates):
        rules_str = ", ".join([RULE_NAMES_VI.get(r, r) for r in c.get("rules_applied", [])]) or T["LANG_ORIGINAL"]
        badge = "[GOC]" if c.get("is_original") else ("[DOI]" if c.get("changed") else "[--]")
        with st.expander("Candidate #{} {}: {}".format(i, badge, rules_str)):
            if c.get("changed"):
                st.code(c.get("sql", ""), language="sql")
            sem = c.get("semantic_check") or {}
            eq = sem.get("equivalent")
            if eq is True:
                st.success(T["COMPARE_EQUIV"])
            elif eq is False:
                st.error("{}: {}".format(T["COMPARE_NOT_EQUIV"], sem.get("error", "")))
            plan = c.get("plan_comparison") or {}
            comp = plan.get("comparison") if plan else None
            if comp:
                m1, m2, m3 = st.columns(3)
                orig_cost = plan.get("original", {}).get("metrics", {}).get("total_cost", 0)
                rew_cost = plan.get("rewritten", {}).get("metrics", {}).get("total_cost", 0)
                pct = comp.get("cost_improvement_pct", 0)
                with m1:
                    st.metric(T["COMPARE_ORIG_COST"], "{:.0f}".format(orig_cost))
                with m2:
                    st.metric(T["COMPARE_REW_COST"], "{:.0f}".format(rew_cost))
                with m3:
                    st.metric(T["COMPARE_IMPROVE"], "{:+.1f}%".format(pct))


def _render_json_output(result, sql, features, recs, candidates, recommendation):
    st.markdown("#### " + T["JSON_TITLE"])
    json_out = {
        "query_id": result.get("query_id"),
        "original_sql": sql,
        "thought_process": {
            "ast_analysis": "SQL co {} bang, {} JOINs, {} subqueries. Do phuc tap: {}.".format(
                features.get("table_count", 0),
                features.get("join_count", 0),
                features.get("subquery_count", 0),
                features.get("complexity", {}).get("level", "?"),
            ),
            "conflict_resolution": "Don gian hoa truoc, giam kich thuoc giua, cua cung la cuoi. SUBQUERY_UNNESTING truoc de mo duong. JOIN_REORDERING sau unnest. PROJECTION_PRUNING cuoi cung.",
        },
        "optimization_sequence": [
            {
                "step": i + 1,
                "rule_name": RULE_NAMES_VI.get(rec.get("rule", "?"), rec.get("rule", "?")),
                "trigger_reason": rec.get("reason", ""),
                "why_this_order": rec.get("reason", ""),
                "expected_benefit": rec.get("expected_benefit", ""),
            }
            for i, rec in enumerate(recs.get("recommendations", []))
        ],
        "candidates": [
            {
                "id": c.get("id"),
                "rules_applied": c.get("rules_applied", []),
                "sql": c.get("sql", ""),
                "semantic_equivalent": (c.get("semantic_check") or {}).get("equivalent"),
                "changed": c.get("changed", False),
            }
            for c in candidates
        ],
        "confidence_score": (recommendation or {}).get("confidence", 0.95),
    }
    jstr = _json.dumps(json_out, indent=2, ensure_ascii=False)
    st.code(jstr, language="json")
    st.download_button(
        T["JSON_DOWNLOAD"],
        data=jstr,
        file_name="optimization_{}.json".format(result.get("query_id", "output")),
        mime="application/json",
        use_container_width=True,
    )


def _render_comparison_table(candidates, recommendation):
    st.markdown("#### " + T["TABLE_TITLE"])
    rows = []
    for i, c in enumerate(candidates):
        sem = c.get("semantic_check") or {}
        plan = c.get("plan_comparison") or {}
        comp = plan.get("comparison") if plan else None
        m_orig = plan.get("original", {}).get("metrics") if plan else None
        m_rew = plan.get("rewritten", {}).get("metrics") if plan else None
        eq = sem.get("equivalent")
        rows.append({
            "#": i,
            T["TABLE_TYPE"]: T["LANG_ORIGINAL"] if c.get("is_original") else T["LANG_REWRITE"],
            T["TABLE_RULES"]: ", ".join([RULE_NAMES_VI.get(r, r) for r in c.get("rules_applied", [])]) or "—",
            T["TABLE_CHANGED"]: T["LANG_CO"] if c.get("changed") else T["LANG_KHONG"],
            T["TABLE_EQUIV"]: T["LANG_CO"] if eq is True else (T["LANG_KHONG"] if eq is False else "—"),
            T["TABLE_COST_ORIG"]: "{:.0f}".format(m_orig.get("total_cost", 0)) if m_orig else "—",
            T["TABLE_COST_REW"]: "{:.0f}".format(m_rew.get("total_cost", 0)) if m_rew else "—",
            T["TABLE_IMPROVE"]: "{:+.1f}%".format(comp.get("cost_improvement_pct", 0)) if comp else "—",
        })
    if rows:
        df = pd.DataFrame(rows)
        rec_id = (recommendation or {}).get("best_candidate_id")
        if rec_id is not None:
            def _hl(row):
                return ["background-color:#d4edda"] * len(row) if row["#"] == rec_id else [""] * len(row)
            st.dataframe(df.style.apply(_hl, axis=1), use_container_width=True, hide_index=True)
            st.caption(T["TABLE_HIGHLIGHT"])
        else:
            st.dataframe(df, use_container_width=True, hide_index=True)


def _render_welcome():
    st.markdown("""
    <div style="text-align:center;padding:40px 20px;color:#666">
    <h3>""" + T["APP_WELCOME"] + """</h3>
    <p>Nhap SQL va nhan <b>Optimize</b> de bat dau toi uu hoa.</p>
    <p>""" + T["APP_WELCOME_DB"] + """</p>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("### " + T["EXAMPLES_TITLE"])
    ex = T["EXAMPLES"]
    for i, (name, example_sql) in enumerate(ex.items()):
        with st.columns(2)[i % 2]:
            with st.expander(name):
                st.code(example_sql, language="sql")
                if st.button(T["BTN_USE_EXAMPLE"] + " \"" + name + "\"", key="ex_" + str(i)):
                    st.session_state.sql = example_sql
                    st.rerun()


# ================================================================
# LAYOUT
# ================================================================
left_col, main_col = st.columns([280, 1])
with left_col:
    render_left_panel()
with main_col:
    render_main_workspace()
