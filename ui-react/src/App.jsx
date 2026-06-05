/**
 * App.jsx
 * LLM-R2 Dashboard — 3-column layout.
 * Dark/light mode via Tailwind `dark:` class on <html>.
 *
 * Color mapping (dark → light):
 *   bg-bg-primary   → bg-white
 *   bg-bg-card      → bg-lt-bg-card (#F6F8FA)
 *   bg-bg-code      → bg-lt-bg-code (#F6F8FA)
 *   bg-bg-border    → border-lt-bg-border (#D0D7DE)
 *   bg-bg-tab       → bg-lt-bg-tab (#EBEEF2)
 *   text-text-primary   → text-lt-text-primary (#1F2328)
 *   text-text-secondary → text-lt-text-secondary (#656D76)
 *   text-text-muted     → text-lt-text-muted (#8C959F)
 */

import { useState, useCallback } from "react";
import {
  Sparkles, Zap, Database, Download,
  Check, Send, Loader, AlertTriangle,
} from "./components/Icons.jsx";
import { DecisionCard } from "./components/DecisionCard.jsx";
import { MetricsPanel } from "./components/MetricsPanel.jsx";
import { ExportReportModal } from "./components/ExportReportModal.jsx";
import { ThemeToggle } from "./components/ThemeToggle.jsx";
import { mockAnalysisResult, KNOWLEDGE_BASE_RULES } from "./data/mockData.js";
import { useOptimizationStore } from "./store/useOptimizationStore.js";

/* ─────────────────────────────────────────────────────────────────────────
   DATABASE SCHEMA PANEL
   Conditional rendering driven by Zustand dbStatus.
───────────────────────────────────────────────────────────────────────── */
const MOCK_SCHEMA = {
  postgres_15: {
    tables: [
      {
        name: "orders",
        type: "table",
        expanded: true,
        columns: [
          { name: "id", type: "PK", dataType: "int", isPK: true, isFK: false },
          { name: "cust_id", type: "FK", dataType: "int", isPK: false, isFK: true },
          { name: "order_date", type: "", dataType: "date", isPK: false, isFK: false },
          { name: "status", type: "", dataType: "varchar", isPK: false, isFK: false },
          { name: "total_price", type: "", dataType: "numeric", isPK: false, isFK: false },
        ],
      },
      {
        name: "customers",
        type: "table",
        expanded: false,
        columns: [
          { name: "id", type: "PK", dataType: "int", isPK: true, isFK: false },
          { name: "name", type: "", dataType: "varchar", isPK: false, isFK: false },
          { name: "status", type: "", dataType: "varchar", isPK: false, isFK: false },
          { name: "mktsegment", type: "", dataType: "varchar", isPK: false, isFK: false },
          { name: "nation", type: "", dataType: "varchar", isPK: false, isFK: false },
        ],
      },
      {
        name: "lineitem",
        type: "table",
        expanded: false,
        columns: [
          { name: "id", type: "PK", dataType: "int", isPK: true, isFK: false },
          { name: "order_id", type: "FK", dataType: "int", isPK: false, isFK: true },
          { name: "part_id", type: "FK", dataType: "int", isPK: false, isFK: true },
          { name: "quantity", type: "", dataType: "int", isPK: false, isFK: false },
          { name: "unit_price", type: "", dataType: "numeric", isPK: false, isFK: false },
        ],
      },
      {
        name: "nation",
        type: "table",
        expanded: false,
        columns: [
          { name: "id", type: "PK", dataType: "int", isPK: true, isFK: false },
          { name: "name", type: "", dataType: "varchar", isPK: false, isFK: false },
          { name: "region", type: "", dataType: "varchar", isPK: false, isFK: false },
        ],
      },
    ],
  },
};

function SchemaTableRow({ table }) {
  const [expanded, setExpanded] = useState(table.expanded);

  return (
    <div className="mb-1.5">
      {/* Table header */}
      <button
        onClick={() => setExpanded((v) => !v)}
        className="
          w-full flex items-center gap-2 px-2.5 py-2 rounded-lg
          bg-[#161B22] hover:bg-[#1E242C]
          transition-colors duration-150 group
        "
      >
        {/* Grid icon */}
        <svg width="11" height="11" viewBox="0 0 16 16" fill="none"
          stroke="#3B82F6" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"
          className="shrink-0">
          <rect x="2" y="2" width="12" height="12" rx="2" />
          <line x1="2" y1="6" x2="14" y2="6" />
          <line x1="2" y1="10" x2="14" y2="10" />
          <line x1="6" y1="2" x2="6" y2="14" />
        </svg>

        <span className="text-[12px] font-semibold font-mono text-[#E6EDF3]">{table.name}</span>

        <span className="ml-auto text-[9px] font-mono text-[#484F58] mr-1">
          {table.columns.length} cols
        </span>

        {/* Chevron */}
        {expanded ? (
          <svg width="11" height="11" viewBox="0 0 16 16" fill="none"
            stroke="#484F58" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
            className="shrink-0">
            <polyline points="4,10 8,6 12,10" />
          </svg>
        ) : (
          <svg width="11" height="11" viewBox="0 0 16 16" fill="none"
            stroke="#484F58" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
            className="shrink-0">
            <polyline points="4,6 8,10 12,6" />
          </svg>
        )}
      </button>

      {/* Column list — dark panel */}
      {expanded && (
        <div className="rounded-lg bg-[#0D1117] border border-[#30363D] overflow-hidden mt-0.5">
          {table.columns.map((col, i) => (
            <div
              key={col.name}
              className={`
                flex items-center gap-2.5 px-3 py-1.5
                hover:bg-[#1E242C] transition-colors duration-100
                ${i < table.columns.length - 1 ? "border-b border-[#21262D]" : ""}
              `}
            >
              {/* PK / FK indicator */}
              {col.isPK ? (
                <span className="text-[9px] font-mono font-bold text-yellow-400 bg-yellow-400/10 px-1 py-0.5 rounded shrink-0 w-5 text-center">
                  PK
                </span>
              ) : col.isFK ? (
                <span className="text-[9px] font-mono font-bold text-blue-400 bg-blue-400/10 px-1 py-0.5 rounded shrink-0 w-5 text-center">
                  FK
                </span>
              ) : (
                <span className="w-5 shrink-0" />
              )}

              {/* Column name */}
              <span className="text-[11px] font-mono text-[#E6EDF3] w-28 shrink-0">
                {col.name}
              </span>

              {/* Data type — readable muted color */}
              <span className="ml-auto text-[10px] font-mono text-[#60A5FA] shrink-0">
                {col.dataType}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function DatabaseSchemaPanel() {
  const { dbStatus, connectDB, disconnectDB } = useOptimizationStore();
  const [connectionMethod, setConnectionMethod] = useState("live");
  const [dbConn, setDbConn] = useState({
    host: "localhost", port: "5432", dbname: "tpch", user: "postgres", password: "",
  });

  const isConnected = dbStatus === "connected";
  const isConnecting = dbStatus === "connecting";

  /* ── BLOCK A: Setup View (NOT connected) ── */
  if (!isConnected) {
    const mockSchema = MOCK_SCHEMA.postgres_15;

    return (
      <div className="mt-1 space-y-3">
        {/* Toggle: Live Connection vs Upload File */}
        <div className="flex items-center gap-3 p-1 rounded-lg
          dark:bg-bg-primary bg-gray-100 border
          dark:border-bg-border border-gray-200">
          {["live", "upload"].map((method) => (
            <button
              key={method}
              onClick={() => setConnectionMethod(method)}
              className={`
                flex-1 flex items-center justify-center gap-2
                px-3 py-2 rounded-md text-[11px] font-semibold
                transition-all duration-200
                ${connectionMethod === method
                  ? "dark:bg-bg-card dark:text-text-primary dark:shadow-sm bg-white text-gray-800 shadow-sm"
                  : "dark:text-text-muted text-gray-400 hover:dark:text-text-secondary"
                }
              `}
            >
              {method === "live" ? (
                <>
                  <svg width="11" height="11" viewBox="0 0 16 16" fill="none"
                    stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"
                    className={connectionMethod === method ? "dark:text-accent-blue text-blue-500" : ""}>
                    <rect x="2" y="2" width="5" height="5" rx="1" />
                    <rect x="9" y="2" width="5" height="5" rx="1" />
                    <rect x="2" y="9" width="5" height="5" rx="1" />
                    <line x1="11.5" y1="5.5" x2="14.5" y2="5.5" />
                    <line x1="13" y1="4" x2="13" y2="7" />
                    <rect x="9" y="9" width="5" height="5" rx="1" />
                  </svg>
                  Live Connection
                </>
              ) : (
                <>
                  <svg width="11" height="11" viewBox="0 0 16 16" fill="none"
                    stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"
                    className={connectionMethod === method ? "dark:text-accent-blue text-blue-500" : ""}>
                    <path d="M9 2H4a2 2 0 0 0-2 2v8a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2V6z" />
                    <polyline points="9,2 9,6 13,6" />
                  </svg>
                  Upload File
                </>
              )}
            </button>
          ))}
        </div>

        {/* Warning badge */}
        <div className="
          flex items-center gap-2 px-3 py-2.5 rounded-lg
          dark:bg-orange-500/10 dark:border dark:border-orange-500/20 dark:text-orange-400
          bg-orange-50 border border-orange-200 text-orange-700
        ">
          <svg width="12" height="12" viewBox="0 0 16 16" fill="currentColor"
            className="shrink-0">
            <path d="M8.22 1.75a.75.75 0 0 0-1.5 0v5.69L4.53 9.96a.75.75 0 1 0 1.06 1.06l2.8-2.8V12a.75.75 0 0 0 1.5 0V7.41l2.8 2.8a.75.75 0 0 0 1.06-1.06l-2.69-2.52V1.75z"/>
            <path d="M8 14a2 2 0 1 1 0-4 2 2 0 0 1 0 4z"/>
          </svg>
          <span className="text-[11px] font-semibold">No active connection</span>
        </div>

        {/* ── Live Connection form ── */}
        {connectionMethod === "live" && (
          <div className="space-y-2">
            {[
              { key: "host", label: "Host", ph: "e.g. localhost" },
              { key: "port", label: "Port", ph: "e.g. 5432" },
              { key: "dbname", label: "Database Name", ph: "e.g. tpch" },
              { key: "user", label: "Username", ph: "postgres" },
              { key: "password", label: "Password", ph: "••••••", type: "password" },
            ].map((field) => (
              <div key={field.key}>
                <label className="
                  block text-[10px] font-semibold
                  dark:text-text-muted text-gray-500
                  uppercase tracking-wider mb-1
                ">
                  {field.label}
                </label>
                <input
                  type={field.type || "text"}
                  value={dbConn[field.key]}
                  onChange={(e) => setDbConn((p) => ({ ...p, [field.key]: e.target.value }))}
                  placeholder={field.ph}
                  className="
                    w-full px-3 py-2 rounded-lg
                    dark:bg-bg-code dark:border dark:border-bg-border
                    dark:text-text-primary dark:placeholder:text-text-muted
                    dark:focus:border-accent-blue/50
                    bg-white border border-lt-bg-border
                    text-[12px] text-lt-text-primary placeholder:text-lt-text-muted
                    focus:outline-none focus:border-accent-blue/50
                  "
                />
              </div>
            ))}

            <div className="flex gap-2 pt-1">
              <button className="
                flex-1 px-3 py-2 rounded-lg text-[11px] font-semibold
                dark:bg-bg-tab dark:border dark:border-bg-border dark:hover:bg-bg-border
                dark:text-text-secondary
                bg-gray-100 border border-lt-bg-border hover:bg-gray-200
                text-lt-text-secondary transition-colors
              ">
                Test Connection
              </button>
              <button
                onClick={() => connectDB(dbConn)}
                disabled={isConnecting}
                className="
                  flex-1 flex items-center justify-center gap-2
                  px-3 py-2 rounded-lg text-[11px] font-semibold
                  dark:bg-accent-blue dark:hover:bg-blue-500 dark:text-white
                  dark:disabled:bg-accent-blue/40 dark:disabled:cursor-not-allowed
                  bg-accent-blue hover:bg-blue-600 text-white
                  disabled:opacity-50 disabled:cursor-not-allowed
                  transition-colors
                "
              >
                {isConnecting ? (
                  <>
                    <svg className="animate-spin" width="11" height="11" viewBox="0 0 24 24" fill="none"
                      stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
                      <path d="M21 12a9 9 0 1 1-6.219-8.56" />
                    </svg>
                    Connecting...
                  </>
                ) : (
                  "Connect"
                )}
              </button>
            </div>
          </div>
        )}

        {/* ── Upload File dropzone ── */}
        {connectionMethod === "upload" && (
          <label className="
            flex flex-col items-center justify-center gap-2.5
            px-4 py-8 rounded-lg
            dark:border-2 dark:border-dashed dark:border-bg-border
            dark:hover:border-accent-blue/50 dark:hover:bg-accent-blue/5
            border-2 border-dashed border-lt-bg-border
            hover:border-accent-blue/50 hover:bg-blue-50
            cursor-pointer transition-all duration-150
          ">
            <div className="
              w-10 h-10 rounded-xl
              dark:bg-bg-tab dark:border dark:border-bg-border
              bg-gray-100 border border-gray-200
              flex items-center justify-center
            ">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none"
                stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"
                className="dark:text-text-muted text-gray-400">
                <polyline points="16,16 12,12 8,16" />
                <line x1="12" y1="12" x2="12" y2="21" />
                <path d="M20.39 18.39A5 5 0 0 0 18 9h-1.26A8 8 0 1 0 3 16.3" />
              </svg>
            </div>
            <div className="text-center">
              <p className="text-[12px] font-semibold dark:text-text-secondary text-lt-text-secondary">
                Drag &amp; drop schema file here
              </p>
              <p className="text-[10px] dark:text-text-muted text-lt-text-muted mt-0.5">
                or click to browse
              </p>
            </div>
            <span className="
              text-[9px] font-semibold px-2 py-0.5 rounded
              dark:bg-bg-tab dark:text-text-muted
              bg-gray-100 text-gray-400
            ">
              Supports .sql or .json
            </span>
            <input type="file" accept=".sql,.json" className="sr-only" />
          </label>
        )}
      </div>
    );
  }

  /* ── BLOCK B: Schema Tree View (connected) ── */
  const schema = MOCK_SCHEMA.postgres_15;

  return (
    <div className="mt-1">
      {/* ── Sleek single-line connection header ── */}
      <div className="flex items-center justify-between px-1 mb-3">
        {/* Left: glowing dot + db name */}
        <div className="flex items-center gap-2">
          {/* Pulsing green dot */}
          <span className="relative flex h-2 w-2 shrink-0">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full dark:bg-green-400 bg-green-500 opacity-75" />
            <span className="relative inline-flex rounded-full h-2 w-2 dark:bg-green-400 bg-green-500" />
          </span>
          <span className="text-[12px] font-semibold font-mono dark:text-[#E6EDF3] text-gray-200">
            postgres_15
          </span>
        </div>

        {/* Right: minimal power/unplug icon button */}
        <button
          onClick={disconnectDB}
          title="Disconnect"
          className="
            p-1.5 rounded-md
            dark:text-[#484F58] dark:hover:text-red-400 dark:hover:bg-red-400/10
            text-gray-500 hover:text-red-500 hover:bg-red-500/10
            transition-all duration-150
          "
        >
          {/* Power icon */}
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none"
            stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M18.36 6.64a9 9 0 1 1-12.73 0" />
            <line x1="12" y1="2" x2="12" y2="12" />
          </svg>
        </button>
      </div>

      {/* Table count */}
      <div className="flex items-center justify-between mb-2 px-1">
        <span className="text-[10px] font-semibold dark:text-[#484F58] text-gray-500 uppercase tracking-wider">
          Tables
        </span>
        <span className="text-[9px] font-mono dark:text-[#484F58] text-gray-500">
          {schema.tables.length}
        </span>
      </div>

      {/* Schema tree */}
      <div>
        {schema.tables.map((table) => (
          <SchemaTableRow key={table.name} table={table} />
        ))}
      </div>
    </div>
  );
}

/* ─────────────────────────────────────────────────────────────────────────
   LEFT SIDEBAR
───────────────────────────────────────────────────────────────────────── */
function LeftSidebar({ sql, onSqlChange, onAnalyze, isAnalyzing, activeRules, onToggleRule }) {
  const [leftTab, setLeftTab] = useState("rules");

  const activeCount = activeRules.filter(Boolean).length;

  return (
    <aside className="
      flex-1 min-h-0 flex flex-col
      bg-[#0B0F19]
      border-r border-white/5
    ">

      {/* Tab Switcher */}
      <div className="flex border-b border-white/5">
        {[
          { key: "rules", label: "Optimization Rules" },
          { key: "schema", label: "Database Schema" },
        ].map((tab) => (
          <button
            key={tab.key}
            onClick={() => setLeftTab(tab.key)}
            className={`
              flex-1 px-4 py-3 text-[11px] font-semibold
              border-b-2 transition-all duration-150
              ${leftTab === tab.key
                ? "text-purple-400 border-purple-400/50 hover:text-purple-300"
                : "text-gray-500 border-transparent hover:text-gray-300 hover:bg-white/5"
              }
            `}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* SQL Input — flex-1 to absorb freed vertical space */}
      <div className="flex-1 min-h-0 flex flex-col px-4 pt-4 pb-3 gap-3">
        <div className="flex items-center justify-between shrink-0">
          <h3 className="text-[11px] font-semibold text-gray-400 uppercase tracking-widest">
            Raw SQL
          </h3>
          <DatabaseStatusBadge />
        </div>

        <textarea
          value={sql}
          onChange={(e) => onSqlChange(e.target.value)}
          placeholder="SELECT * FROM orders WHERE..."
          spellCheck={false}
          className="
            flex-1 w-full p-3 rounded-xl min-h-0
            bg-[#0D1117] border border-white/5
            text-[12px] font-mono text-gray-200
            placeholder:text-gray-600 placeholder:text-[11px]
            focus:outline-none focus:border-purple-500/30 focus:ring-1 focus:ring-purple-500/20
            resize-none transition-all duration-200
          "
        />

        <button
          onClick={onAnalyze}
          disabled={isAnalyzing || !sql.trim()}
          className={`
            w-full flex items-center justify-center gap-2
            px-4 py-2.5 rounded-xl text-[12px] font-semibold shrink-0
            transition-all duration-200
            disabled:opacity-40 disabled:cursor-not-allowed
            ${isAnalyzing
              ? "bg-purple-500/10 text-purple-400 border border-purple-500/20"
              : "bg-purple-500 hover:bg-purple-400 text-white shadow-lg shadow-purple-500/20 active:scale-[0.98]"
            }
          `}
        >
          {isAnalyzing ? (
            <><Loader size={14} />Analyzing...</>
          ) : (
            <><Send size={14} />Analyze Query</>
          )}
        </button>
      </div>

      {/* ── Rules Panel — shrink-0 so SQL section takes priority ── */}
      {leftTab === "rules" && (
        <div className="shrink-0 px-4 pb-4 max-h-[220px] overflow-y-auto">
          <div className="flex items-center justify-between mb-3 mt-1">
            <span className="text-[11px] font-semibold text-gray-400 uppercase tracking-widest">
              Active Rules
            </span>
            <span className="badge-green px-2 py-0.5 rounded-md text-[10px] font-bold">
              {activeCount}/6
            </span>
          </div>

          <div className="space-y-1">
            {KNOWLEDGE_BASE_RULES.map((rule, idx) => (
              <label
                key={rule.id}
                className={`
                  flex items-center gap-2 px-2 py-1.5 rounded-lg
                  cursor-pointer transition-all duration-150 group
                  ${activeRules[idx]
                    ? "bg-[#111827] border border-green-500/20 hover:border-green-500/40"
                    : "bg-[#0D1117] border border-white/5 hover:border-white/10"
                  }
                `}
              >
                <input
                  type="checkbox"
                  checked={!!activeRules[idx]}
                  onChange={() => onToggleRule(idx)}
                  className="sr-only"
                />
                <div className={`
                  w-3.5 h-3.5 rounded flex items-center justify-center shrink-0
                  transition-all duration-150
                  ${activeRules[idx]
                    ? "bg-green-500 border border-green-500"
                    : "border-2 border-gray-600 group-hover:border-gray-400"
                  }
                `}>
                  {activeRules[idx] && <Check size={8} className="text-white" />}
                </div>

                <span className="flex-1 min-w-0 text-[10px] font-semibold text-gray-200 leading-tight truncate">
                  {rule.name}
                </span>

                <span className={`
                  text-[8px] font-bold px-1 py-0.5 rounded shrink-0
                  ${rule.benefit.includes("High")
                    ? "badge-green"
                    : "badge-yellow"
                  }
                `}>
                  {rule.benefit.includes("High") ? "High" : "Med"}
                </span>
              </label>
            ))}
          </div>
        </div>
      )}

      {/* ── Schema Panel ─────────────────────────── */}
      {leftTab === "schema" && (
        <div className="flex-1 min-h-0 overflow-y-auto px-4 pb-4">
          <DatabaseSchemaPanel />
        </div>
      )}
    </aside>
  );
}

/* ── Database status badge helper (used in SQL input header) ── */
function DatabaseStatusBadge() {
  const dbStatus = useOptimizationStore((s) => s.dbStatus);
  const isConnected = dbStatus === "connected";

  return (
    <span className={`
      flex items-center gap-1.5 text-[10px] font-semibold px-2 py-0.5 rounded-full border
      ${isConnected
        ? "dark:text-green-400 dark:bg-green-500/10 dark:border-green-500/20 text-green-600 bg-green-50 border-green-200"
        : "dark:text-text-muted dark:bg-text-muted/5 dark:border-text-muted/20 text-lt-text-muted bg-lt-bg-tab border-lt-bg-border"
      }
    `}>
      <span className={`
        w-1.5 h-1.5 rounded-full
        ${isConnected ? "dark:bg-green-400 bg-green-500" : "dark:bg-text-muted bg-lt-text-muted"}
      `} />
      {isConnected ? "postgres_15" : "No connection"}
    </span>
  );
}

/* ─────────────────────────────────────────────────────────────────────────
   CENTER COLUMN — LLM REASONING & RECOMMENDATIONS
───────────────────────────────────────────────────────────────────────── */
function CenterColumn({ data, isAnalyzing, decisions, onApprove, onReject }) {
  const [ruleFilter, setRuleFilter] = useState("all");

  const ruleKeys = [...new Set(
    (data?.rule_recommendations?.recommendations || []).map((r) => r.rule)
  )];
  const allCandidates = (data?.candidates || []).filter((c) => !c.is_original);
  const candidates = ruleFilter === "all"
    ? allCandidates
    : allCandidates.filter((c) => c.rules_applied.includes(ruleFilter));

  const approvedCount = Object.values(decisions).filter((v) => v === "approved").length;
  const rejectedCount = Object.values(decisions).filter((v) => v === "rejected").length;
  const pendingCount = allCandidates.length - approvedCount - rejectedCount;
  const best = data?.candidates?.find((c) => c.id === data?.recommendation?.best_candidate_id);

  const RULE_DISPLAY_NAMES = {
    predicate_pushdown: "Predicate Pushdown",
    projection_pruning: "Projection Pruning",
    join_reordering: "Join Reordering",
    subquery_unnesting: "Subquery Unnesting",
    aggregation_pushdown: "Aggregation Pushdown",
    redundant_join_elimination: "Redundant Join Elimination",
  };

  return (
    <section className="
      flex-1 flex flex-col min-h-0
      bg-[#0B0F19]
      border-x border-white/5
    ">
      {/* Header */}
      <div className="flex-shrink-0 px-6 py-5 border-b border-white/5">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className="
              w-9 h-9 rounded-xl flex items-center justify-center shrink-0
              bg-purple-500/10 border border-purple-500/20
            ">
              <Sparkles size={18} className="text-purple-400" />
            </div>
            <div>
              <h2 className="text-[14px] font-semibold text-gray-100 leading-tight">
                LLM Reasoning &amp; Recommendations
              </h2>
              <p className="text-[11px] text-gray-500 mt-0.5">
                AI-powered SQL optimization analysis
              </p>
            </div>
          </div>

          <span className="
            inline-flex items-center gap-1 px-2.5 py-1 rounded-full
            text-[10px] font-medium badge-purple
          ">
            <Sparkles size={9} />
            {data?.rule_recommendations?.method === "llm" ? "LLM" : "Pattern"}
          </span>
        </div>

        {/* Overall analysis */}
        {data?.rule_recommendations?.overall_analysis && (
          <blockquote className="
            text-[12px] text-gray-400 leading-relaxed
            border-l-2 border-purple-500/40 pl-3 mb-4 italic
          ">
            {data.rule_recommendations.overall_analysis}
          </blockquote>
        )}

        {/* Stats */}
        <div className="flex items-center gap-2 flex-wrap">
          {[
            { label: "Candidates", value: allCandidates.length, cls: "text-gray-400" },
            { label: "Approved", value: approvedCount, cls: "text-green-400" },
            { label: "Rejected", value: rejectedCount, cls: "text-red-400" },
            { label: "Pending", value: pendingCount, cls: "text-yellow-400" },
            ...(best ? [{ label: "Best", value: `${best.plan_comparison?.comparison?.cost_improvement_pct?.toFixed(1)}%`, cls: "text-green-400" }] : []),
          ].map((s) => (
            <span key={s.label} className={`
              inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg
              text-[11px] font-medium bg-[#111827] border border-white/5 ${s.cls}
            `}>
              {s.label}
              <span className="font-semibold">{s.value}</span>
            </span>
          ))}
        </div>

        {/* Filter bar */}
        {ruleKeys.length > 0 && (
          <div className="flex items-center gap-1.5 mt-3 pt-3 border-t border-white/5 flex-wrap">
            <span className="text-[10px] text-gray-500 font-medium uppercase tracking-wider mr-1">
              Filter:
            </span>
            {["All", ...ruleKeys.map((r) => RULE_DISPLAY_NAMES[r] || r)].map((label, idx) => {
              const key = idx === 0 ? "all" : ruleKeys[idx - 1];
              const active = ruleFilter === key || (key === "all" && ruleFilter === "all");
              return (
                <button
                  key={key}
                  onClick={() => setRuleFilter(key)}
                  className={`
                    px-2.5 py-1 rounded-full text-[10px] font-medium
                    transition-all duration-150
                    ${active
                      ? "bg-purple-500/15 text-purple-300 border border-purple-500/30"
                      : "text-gray-500 hover:text-gray-300 hover:bg-white/5 border border-transparent"
                    }
                  `}
                >
                  {label}
                </button>
              );
            })}
          </div>
        )}
      </div>

      {/* Card Feed */}
      <main className="flex-1 min-h-0 overflow-y-auto px-6 pt-5 pb-24">
        {isAnalyzing ? (
          <div className="flex flex-col items-center justify-center py-24 gap-4">
            <Loader size={32} className="text-purple-400 animate-spin" />
            <p className="text-gray-400 text-sm">Analyzing and optimizing SQL...</p>
            <p className="text-gray-600 text-[11px]">
              Using LLM to analyze query structure and recommend optimization rules.
            </p>
          </div>
        ) : candidates.length === 0 && allCandidates.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-24 text-center">
            <div className="w-14 h-14 rounded-2xl bg-[#111827] border border-white/5 flex items-center justify-center mb-4">
              <Sparkles size={26} className="text-gray-600" />
            </div>
            <h3 className="text-gray-300 font-semibold text-[14px] mb-2">
              No recommendations yet
            </h3>
            <p className="text-gray-600 text-[12px] max-w-xs leading-relaxed">
              Enter a SQL query and click Analyze Query to receive optimization recommendations.
            </p>
          </div>
        ) : candidates.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 text-center">
            <p className="text-gray-500 text-sm mb-3">No candidates match the current filter.</p>
            <button
              onClick={() => setRuleFilter("all")}
              className="text-purple-400 text-[12px] hover:text-purple-300 underline underline-offset-2 transition-colors"
            >
              Clear filter
            </button>
          </div>
        ) : (
          candidates.map((candidate, i) => (
            <DecisionCard
              key={candidate.id}
              candidate={candidate}
              originalSql={data.original_sql}
              onApprove={onApprove}
              onReject={onReject}
              index={i + 1}
            />
          ))
        )}
      </main>

      {/* Approved footer */}
      {approvedCount > 0 && (
        <footer className="flex-shrink-0 px-6 py-3 border-t border-green-500/10 bg-green-500/5">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="w-5 h-5 rounded-full bg-green-500/15 flex items-center justify-center">
                <span className="text-green-400 text-[10px] font-bold">{approvedCount}</span>
              </div>
              <span className="text-[12px] text-green-400 font-medium">
                {approvedCount} optimization{approvedCount > 1 ? "s" : ""} approved
              </span>
            </div>
            {best && (
              <span className="text-[11px] text-gray-400">
                Expected:{" "}
                <span className="text-green-400 font-semibold">
                  {best.plan_comparison?.comparison?.cost_improvement_pct?.toFixed(1)}%
                </span>
              </span>
            )}
          </div>
        </footer>
      )}
    </section>
  );
}

/* ─────────────────────────────────────────────────────────────────────────
   TOP HEADER
───────────────────────────────────────────────────────────────────────── */
function TopHeader({ onExport }) {
  return (
    <header className="
      h-[52px] shrink-0 flex items-center justify-between px-5
      bg-[#0B0F19] border-b border-white/5
    ">
      {/* Left group */}
      <div className="flex items-center gap-3">
        <div className="
          w-8 h-8 rounded-lg shrink-0
          bg-purple-500/10 border border-purple-500/20
          flex items-center justify-center
        ">
          <Zap size={16} className="text-purple-400" />
        </div>
        <div className="flex items-center gap-2">
          <h1 className="text-[13px] font-semibold text-gray-100 leading-tight">
            AI Database Decision Support
          </h1>
          <span className="text-[10px] text-gray-600 hidden sm:inline">
            LLM-R2 Enhanced
          </span>
        </div>
      </div>

      {/* Right group */}
      <div className="flex items-center gap-2">
        <ThemeToggle />
        <span className="
          inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full
          text-[10px] font-medium shrink-0 badge-green
        ">
          <span className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse shrink-0" />
          System Online
        </span>
        <button
          onClick={onExport}
          className="
            flex items-center gap-2 px-3 py-1.5 rounded-lg
            text-[12px] font-medium shrink-0
            bg-[#111827] border border-white/10
            text-gray-300 hover:text-white hover:bg-[#1a2234] hover:border-white/20
            transition-all duration-150
          "
        >
          <Download size={13} />
          <span className="hidden sm:inline">Export Report</span>
        </button>
      </div>
    </header>
  );
}

/* ─────────────────────────────────────────────────────────────────────────
   APP ROOT
───────────────────────────────────────────────────────────────────────── */
export default function App() {
  const [sql, setSql] = useState(mockAnalysisResult.original_sql);
  const [activeRules, setActiveRules] = useState(
    KNOWLEDGE_BASE_RULES.map(() => true)
  );

  // ── Store slices ───────────────────────────────────────────
  const { isAnalyzing, error, data, decisions, openExportModal, analyzeQuery, setDecision } =
    useOptimizationStore();

  // Initialise with mock data so the dashboard isn't blank on first load
  const displayData = data ?? mockAnalysisResult;
  const displayDecisions = Object.keys(decisions).length > 0
    ? decisions
    : Object.fromEntries(
        mockAnalysisResult.candidates
          .filter((c) => !c.is_original)
          .map((c) => [c.id, "pending"])
      );

  const handleAnalyze = useCallback(() => {
    analyzeQuery(sql, activeRules);
  }, [sql, activeRules, analyzeQuery]);

  const handleApprove = useCallback((id) => {
    setDecision(id, "approved");
  }, [setDecision]);

  const handleReject = useCallback((id) => {
    setDecision(id, "rejected");
  }, [setDecision]);

  const handleToggleRule = useCallback((idx) => {
    setActiveRules((prev) => {
      const next = [...prev];
      next[idx] = !next[idx];
      return next;
    });
  }, []);

  return (
    <div className="flex flex-col h-screen w-full overflow-hidden dark:bg-bg-primary bg-white">
      {/* ── Header: fixed height, never grows or shrinks ── */}
      <TopHeader onExport={openExportModal} />

      {/* ── Main workspace: EXACT remaining space, no overflow ── */}
      <div className="flex-1 min-h-0 w-full overflow-hidden px-4 pb-4 pt-2">

        {/* ── 3-column locked grid: each column stops at bottom boundary ── */}
        <div className="h-full w-full grid grid-cols-[380px_minmax(0,1fr)_380px] gap-6">

          {/* Left column — locked to grid height, internal scroll */}
          <div className="h-full overflow-y-auto flex flex-col relative">
            <LeftSidebar
              sql={sql}
              onSqlChange={setSql}
              onAnalyze={handleAnalyze}
              isAnalyzing={isAnalyzing}
              activeRules={activeRules}
              onToggleRule={handleToggleRule}
            />
          </div>

          {/* Center column — locked to grid height, internal scroll */}
          <div className="h-full overflow-y-auto flex flex-col relative">
            <CenterColumn
              data={displayData}
              isAnalyzing={isAnalyzing}
              decisions={displayDecisions}
              onApprove={handleApprove}
              onReject={handleReject}
            />
          </div>

          {/* Right column — locked to grid height, internal scroll */}
          <div className="h-full overflow-y-auto flex flex-col relative">
            <MetricsPanel data={displayData} decisions={displayDecisions} />
          </div>

        </div>
      </div>

      <ExportReportModal data={displayData} />
    </div>
  );
}
