/**
 * ReasoningColumn.jsx
 * ColumnCenter — LLM Reasoning & Recommendations
 *
 * Full column width for standalone preview.
 * Inside the full dashboard, this occupies the center column (1fr).
 *
 * Features:
 * - Scrollable feed of DecisionCards
 * - Global header with LLM status badge
 * - Summary stats bar
 * - Filter by rule type
 * - Approved count badge
 */

import { useState, useMemo } from "react";
import { Sparkles, Loader, Filter, Zap } from "./Icons.jsx";
import { DecisionCard } from "./DecisionCard.jsx";
import { mockAnalysisResult } from "../data/mockData.js";

/** Filter chip */
function FilterChip({ label, active, onClick }) {
  return (
    <button
      onClick={onClick}
      className={`
        flex items-center gap-1.5 px-3 py-1.5 rounded-full text-[11px] font-semibold
        border transition-all duration-150 cursor-pointer
        ${
          active
            ? "bg-accent-blue text-white border-accent-blue shadow-md shadow-blue-500/20"
            : "bg-bg-card text-text-secondary border-bg-border hover:border-accent-blue/50 hover:text-accent-blue"
        }
      `}
    >
      {label}
    </button>
  );
}

/** Stats pill */
function StatsPill({ label, value, color = "blue" }) {
  const colors = {
    blue: "text-accent-blue bg-accent-blue/10 border-accent-blue/20",
    green: "text-green-400 bg-green-500/10 border-green-500/20",
    purple: "text-purple-300 bg-accent-purple/10 border-accent-purple/20",
    yellow: "text-yellow-400 bg-yellow-500/10 border-yellow-500/20",
    red: "text-accent-red bg-red-500/10 border-red-500/20",
  };
  return (
    <div className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border text-[11px] font-semibold ${colors[color] || colors.blue}`}>
      <span>{label}</span>
      <span className="font-bold">{value}</span>
    </div>
  );
}

/** Method badge */
function MethodBadge({ method }) {
  const config = {
    llm: { label: "LLM", cls: "text-purple-300 bg-accent-purple/10 border-accent-purple/20" },
    pattern: { label: "Pattern", cls: "text-blue-300 bg-accent-blue/10 border-accent-blue/20" },
    hybrid: { label: "Hybrid", cls: "text-yellow-300 bg-yellow-500/10 border-yellow-500/20" },
  };
  const cfg = config[method] || config.pattern;
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider border ${cfg.cls}`}>
      <Sparkles size={9} />
      {cfg.label}
    </span>
  );
}

/** Empty state */
function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center py-24 text-center">
      <div className="w-16 h-16 rounded-2xl bg-bg-card border border-bg-border flex items-center justify-center mb-4">
        <Sparkles size={28} className="text-text-muted" />
      </div>
      <h3 className="text-text-secondary font-semibold text-base mb-2">
        Chua co recommendations
      </h3>
      <p className="text-text-muted text-sm max-w-xs">
        Nhap mot cau SQL va click Analyze Query de nhan gop y toi uu hoa tu LLM.
      </p>
    </div>
  );
}

/**
 * ReasoningColumn
 *
 * @param {Object} props
 * @param {Object} props.data  - AnalysisResult from backend (or mock)
 * @param {string} props.title - Column title override
 */
export function ReasoningColumn({ data = mockAnalysisResult, title }) {
  // Filter state
  const [ruleFilter, setRuleFilter] = useState("all"); // 'all' | rule_key
  const [statusFilter, setStatusFilter] = useState("all"); // 'all' | 'approved' | 'rejected' | 'pending'

  // Local decision state — maps candidate.id -> status
  const [decisions, setDecisions] = useState(() => {
    // Initialize all candidates as 'pending' except originals
    const init = {};
    if (data?.candidates) {
      data.candidates.forEach((c) => {
        if (!c.is_original) {
          init[c.id] = "pending";
        }
      });
    }
    return init;
  });

  // Callback when card is approved
  const handleApprove = (id) => {
    setDecisions((prev) => ({ ...prev, [id]: "approved" }));
  };

  // Callback when card is rejected
  const handleReject = (id) => {
    setDecisions((prev) => ({ ...prev, [id]: "rejected" }));
  };

  // Get unique rule keys from recommendations
  const ruleKeys = useMemo(() => {
    if (!data?.rule_recommendations?.recommendations) return [];
    return [...new Set(data.rule_recommendations.recommendations.map((r) => r.rule))];
  }, [data]);

  // Filter candidates
  const filteredCandidates = useMemo(() => {
    if (!data?.candidates) return [];

    return data.candidates.filter((c) => {
      // Exclude original from card list (show separately if needed)
      if (c.is_original) return false;

      // Rule filter
      if (ruleFilter !== "all") {
        if (!c.rules_applied.includes(ruleFilter)) return false;
      }

      // Status filter
      if (statusFilter !== "all") {
        if (decisions[c.id] !== statusFilter) return false;
      }

      return true;
    });
  }, [data, ruleFilter, statusFilter, decisions]);

  // Counts
  const totalCandidates = data?.candidates?.filter((c) => !c.is_original).length || 0;
  const approvedCount = Object.values(decisions).filter((v) => v === "approved").length;
  const rejectedCount = Object.values(decisions).filter((v) => v === "rejected").length;
  const pendingCount = totalCandidates - approvedCount - rejectedCount;

  // Best candidate
  const bestCandidate = data?.candidates?.find(
    (c) => c.id === data.recommendation?.best_candidate_id
  );

  return (
    <div className="
      flex flex-col h-screen bg-bg-primary
      border-l border-r border-bg-border
    ">
      {/* ── Column Header ────────────────────────────────────────────── */}
      <header className="
        flex-shrink-0 px-6 py-4
        border-b border-bg-border
        bg-bg-primary
      ">
        {/* Title row */}
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className="
              w-9 h-9 rounded-xl flex items-center justify-center
              bg-accent-purple/15 border border-accent-purple/25
            ">
              <Sparkles size={18} className="text-purple-300" />
            </div>
            <div>
              <h1 className="text-[15px] font-bold text-text-primary leading-tight">
                {title || "LLM Reasoning & Recommendations"}
              </h1>
              <p className="text-[11px] text-text-muted mt-0.5">
                AI-powered SQL optimization analysis
              </p>
            </div>
          </div>

          {/* Right: method badge */}
          <MethodBadge method={data?.rule_recommendations?.method || "pattern"} />
        </div>

        {/* Overall analysis summary */}
        {data?.rule_recommendations?.overall_analysis && (
          <blockquote className="
            text-[12px] text-text-secondary leading-relaxed
            border-l-2 border-accent-purple/40 pl-3
            mb-4 italic
          ">
            {data.rule_recommendations.overall_analysis}
          </blockquote>
        )}

        {/* Stats row */}
        <div className="flex items-center gap-2 flex-wrap">
          <StatsPill
            label="Candidates"
            value={totalCandidates}
            color="blue"
          />
          <StatsPill
            label="Approved"
            value={approvedCount}
            color="green"
          />
          <StatsPill
            label="Rejected"
            value={rejectedCount}
            color="red"
          />
          <StatsPill
            label="Pending"
            value={pendingCount}
            color="yellow"
          />
          {bestCandidate && (
            <StatsPill
              label="Best Cost"
              value={`${bestCandidate.plan_comparison?.comparison?.cost_improvement_pct?.toFixed(1) || 0}%`}
              color="green"
            />
          )}
          {data?.query_id && (
            <StatsPill
              label="Query ID"
              value={data.query_id}
              color="purple"
            />
          )}
        </div>

        {/* Filter bar */}
        <div className="mt-3 pt-3 border-t border-bg-border">
          <div className="flex items-center gap-2 flex-wrap">
            <div className="flex items-center gap-1.5 text-[10px] text-text-muted">
              <Filter size={11} />
              <span className="font-semibold uppercase tracking-wider">Filter:</span>
            </div>

            <FilterChip
              label="All"
              active={ruleFilter === "all"}
              onClick={() => setRuleFilter("all")}
            />

            {ruleKeys.map((rule) => {
              const names = {
                projection_pruning: "Proj. Prune",
                join_reordering: "Join Reorder",
                predicate_pushdown: "Predicate",
                subquery_unnesting: "Subquery",
                aggregation_pushdown: "Agg. Push",
                redundant_join_elimination: "Redundant",
              };
              return (
                <FilterChip
                  key={rule}
                  label={names[rule] || rule}
                  active={ruleFilter === rule}
                  onClick={() => setRuleFilter(ruleFilter === rule ? "all" : rule)}
                />
              );
            })}
          </div>
        </div>
      </header>

      {/* ── Scrollable Card Feed ───────────────────────────────────── */}
      <main className="flex-1 overflow-y-auto px-6 py-5 custom-scrollbar">
        {/* Empty state */}
        {filteredCandidates.length === 0 && totalCandidates === 0 && (
          <EmptyState />
        )}

        {/* No filtered results */}
        {totalCandidates > 0 && filteredCandidates.length === 0 && (
          <div className="flex flex-col items-center justify-center py-16 text-center">
            <div className="text-text-muted text-sm mb-2">No candidates match the current filter</div>
            <button
              onClick={() => { setRuleFilter("all"); setStatusFilter("all"); }}
              className="text-accent-blue text-xs hover:underline"
            >
              Clear filters
            </button>
          </div>
        )}

        {/* Decision cards */}
        {filteredCandidates.map((candidate, i) => (
          <DecisionCard
            key={candidate.id}
            candidate={candidate}
            originalSql={data.original_sql}
            metrics={candidate.plan_comparison?.comparison}
            onApprove={handleApprove}
            onReject={handleReject}
            index={i + 1}
          />
        ))}
      </main>

      {/* ── Footer: Approved Summary ──────────────────────────────── */}
      {approvedCount > 0 && (
        <footer className="
          flex-shrink-0 px-6 py-4
          border-t border-green-500/20
          bg-green-500/5
        ">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="w-5 h-5 rounded-full bg-green-500/20 flex items-center justify-center">
                <span className="text-green-400 text-[10px] font-bold">
                  {approvedCount}
                </span>
              </div>
              <span className="text-[12px] text-green-400 font-semibold">
                {approvedCount} optimization{approvedCount > 1 ? "s" : ""} approved
              </span>
            </div>
            <div className="flex items-center gap-2">
              {bestCandidate && approvedCount > 0 && (
                <span className="text-[11px] text-text-secondary">
                  Expected improvement:{" "}
                  <span className="text-green-400 font-bold">
                    {bestCandidate.plan_comparison?.comparison?.cost_improvement_pct?.toFixed(1) || 0}%
                  </span>
                </span>
              )}
            </div>
          </div>
        </footer>
      )}
    </div>
  );
}

export default ReasoningColumn;
