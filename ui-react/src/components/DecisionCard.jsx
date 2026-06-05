/**
 * DecisionCard.jsx
 * Premium dark mode decision card for LLM reasoning.
 *
 * States: PENDING | APPROVED | REJECTED
 *
 * Design:
 *  - bg-[#111827] card with border-white/5, rounded-xl
 *  - Subtle glow border on approved (green-500/30)
 *  - Dimmed/grayscale on rejected
 *  - Grid code comparison with bg-[#0D1117] code panels
 */

import { useState } from "react";
import { Check, X, AlertTriangle, ChevronDown, ChevronUp } from "./Icons.jsx";
import { SqlCodeBlock } from "./SqlCodeBlock.jsx";

const RULE_LABELS = {
  predicate_pushdown: "Predicate Pushdown",
  projection_pruning: "Projection Pruning",
  join_reordering: "Join Reordering",
  subquery_unnesting: "Subquery Unnesting",
  aggregation_pushdown: "Aggregation Pushdown",
  redundant_join_elimination: "Redundant Join Elimination",
};

function getRuleLabel(rule) {
  return RULE_LABELS[rule] || rule.replace(/_/g, " ");
}

function fmtPct(n) {
  if (n === null || n === undefined) return "—";
  return n > 0 ? `+${n.toFixed(1)}%` : `${n.toFixed(1)}%`;
}

export function DecisionCard({ candidate, originalSql, onApprove, onReject, index = 1 }) {
  const [status, setStatus] = useState("pending");
  const [isExpanded, setIsExpanded] = useState(false);

  const isApproved = status === "approved";
  const isRejected = status === "rejected";
  const isOriginal = candidate.is_original || false;
  const isPending = status === "pending";

  const appliedRules = (candidate.rules_applied || []).map(getRuleLabel);
  const semanticDetails = candidate.semantic_check?.details || null;

  const cardBorder = isApproved
    ? "border-green-500/30 shadow-lg shadow-green-500/5"
    : isRejected
    ? "border-red-500/15 opacity-50"
    : "border-white/5";

  const cardBg = isRejected ? "opacity-50" : "";

  const handleApprove = () => {
    setStatus("approved");
    onApprove?.(candidate.id);
  };

  const handleReject = () => {
    setStatus("rejected");
    onReject?.(candidate.id);
  };

  const conf = candidate.confidence ?? "Medium";
  const confCls =
    conf === "High"
    ? "badge-green"
    : conf === "Low"
    ? "badge-red"
    : "badge-yellow";

  const improvementPct = candidate.plan_comparison?.comparison?.cost_improvement_pct ?? 0;
  const hasImprovement = improvementPct < 0;

  return (
    <article
      className={`
        rounded-xl p-5 mb-4
        bg-[#111827] border ${cardBorder} ${cardBg}
        transition-all duration-300
        shadow-lg shadow-black/20
      `}
    >
      {/* ── Header ─────────────────────────────────────────────────── */}
      <div className="flex flex-row justify-between items-start gap-4 w-full mb-3">

        {/* Left: ID + rule badges — flex-wrap so badges flow naturally */}
        <div className="flex flex-row flex-wrap items-center gap-2 flex-1 min-w-0">
          <span className="text-[10px] font-mono text-gray-600 shrink-0">#{index}</span>

          {appliedRules.length > 0 ? (
            appliedRules.map((label, i) => (
              <span
                key={i}
                className="inline-flex items-center gap-1.5 px-2 py-1 rounded-full text-[9px] font-bold uppercase tracking-wider badge-purple shrink-0"
              >
                <svg width="5" height="5" viewBox="0 0 8 8" fill="currentColor" className="shrink-0">
                  <circle cx="4" cy="4" r="3" />
                </svg>
                {label.toUpperCase()}
              </span>
            ))
          ) : (
            <span className="inline-flex items-center px-2 py-1 rounded-full text-[9px] font-bold uppercase tracking-wider text-gray-500 bg-white/5 border border-white/5 shrink-0">
              ORIGINAL QUERY
            </span>
          )}

          {appliedRules.length > 0 && (
            <span className="text-[9px] text-gray-500 font-medium shrink-0">
              — applied: {appliedRules.join(", ")}
            </span>
          )}
        </div>

        {/* Right: stacked metrics — shrink-0 keeps them from being squished */}
        <div className="flex flex-col items-end gap-1 shrink-0">
          <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded ${confCls}`}>
            {conf.toUpperCase()}
          </span>
          {!isOriginal && (
            <span className={`
              text-[10px] font-bold px-2 py-0.5 rounded
              ${hasImprovement ? "badge-green" : "badge-red"}
            `}>
              {fmtPct(improvementPct)}
            </span>
          )}
        </div>
      </div>

      {/* ── Reasoning ──────────────────────────────────────────────── */}
      <div
        className={`
          relative rounded-xl p-4 mb-4 text-[12px] leading-relaxed
          border-l-4
          ${isApproved
            ? "border-green-500/50 bg-green-500/[0.03]"
            : isRejected
            ? "border-red-500/50 bg-red-500/[0.03]"
            : "border-purple-500/40 bg-purple-500/[0.03]"
          }
        `}
      >
        <p className={isRejected ? "text-gray-500" : "text-gray-400"}>
          {semanticDetails || "No description available."}
        </p>

        {candidate.warning && (
          <div className="mt-2.5 flex items-start gap-2 text-[11px] text-yellow-400/80">
            <AlertTriangle size={11} className="shrink-0 mt-0.5" />
            <span>{candidate.warning}</span>
          </div>
        )}
      </div>

      {/* ── Expand / Collapse Toggle ─────────────────────────────── */}
      {!isOriginal && (
        <div className="mb-4">
          <button
            onClick={() => setIsExpanded((v) => !v)}
            className="
              w-full flex items-center justify-between
              px-3 py-2.5 rounded-xl
              bg-[#0D1117] border border-white/5
              text-[11px] font-medium text-gray-400
              hover:text-gray-200 hover:border-white/10
              transition-all duration-200
            "
          >
            <span className="flex items-center gap-2">
              <svg width="12" height="12" viewBox="0 0 16 16" fill="none"
                stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                <rect x="3" y="7.5" width="10" height="7" rx="1.5" />
                <path d="M5.5 7.5 V5 a2.5 2.5 0 0 1 5 0 V7.5" />
              </svg>
              {isExpanded ? "Collapse Code Comparison" : "Expand Code Comparison"}
            </span>
            <span className="text-gray-600">
              {isExpanded ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
            </span>
          </button>
        </div>
      )}

      {/* ── Code Comparison — stacked by default, side-by-side on 2xl+ ── */}
      {!isOriginal && isExpanded && (
        <div className="mb-4">
          {/*
            flex-col  → vertical stack (mobile / default)
            2xl:flex-row → side-by-side on very large screens
          */}
          <div className="flex flex-col 2xl:flex-row items-stretch gap-4 w-full">

            {/* BEFORE */}
            <div className="flex-1 min-w-0 w-full rounded-xl overflow-hidden border border-white/5 flex flex-col">
              <div className="flex items-center justify-between px-3 py-1.5 shrink-0 bg-[#0D1117]">
                <span className="text-[9px] font-mono text-gray-500">original.sql</span>
                <span className="text-[9px] font-bold px-1.5 py-0.5 rounded badge-red">
                  BEFORE
                </span>
              </div>
              <div className="flex-1 min-w-0 w-full">
                <SqlCodeBlock code={originalSql} />
              </div>
            </div>

            {/* Arrow — rotate-90 when stacked, rotate-0 on 2xl+ */}
            <div className="flex items-center justify-center self-center 2xl:self-auto">
              <div className="w-8 h-8 rounded-full bg-purple-500/10 border border-purple-500/20 flex items-center justify-center rotate-90 2xl:rotate-0">
                <svg width="13" height="13" viewBox="0 0 16 16" fill="none"
                  stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
                  className="text-purple-400">
                  <line x1="2" y1="8" x2="14" y2="8" />
                  <polyline points="9,3 14,8 9,13" />
                </svg>
              </div>
            </div>

            {/* AFTER */}
            <div className={`
              flex-1 min-w-0 w-full rounded-xl overflow-hidden border flex flex-col
              ${isApproved ? "border-green-500/30" : "border-white/5"}
            `}>
              <div className={`
                flex items-center justify-between px-3 py-1.5 shrink-0 bg-[#0D1117]
                ${isApproved ? "border-b border-green-500/30" : "border-b border-white/5"}
              `}>
                <span className="text-[9px] font-mono text-gray-500">optimized.sql</span>
                <span className="text-[9px] font-bold px-1.5 py-0.5 rounded badge-green flex items-center gap-1">
                  {isApproved && <Check size={8} />}
                  AFTER
                </span>
              </div>
              <div className="flex-1 min-w-0 w-full">
                <SqlCodeBlock code={candidate.sql} />
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── Original query single block ──────────────────────────── */}
      {isOriginal && (
        <div className="mb-4">
          <div className="rounded-xl overflow-hidden border border-white/5 flex flex-col">
            <div className="flex items-center justify-between px-3 py-1.5 shrink-0 bg-[#0D1117]">
              <span className="text-[9px] font-mono text-gray-500">original.sql</span>
              <span className="text-[9px] font-bold px-1.5 py-0.5 rounded badge-red">BEFORE</span>
            </div>
            <div className="flex-1 overflow-x-auto">
              <SqlCodeBlock code={candidate.sql} />
            </div>
          </div>
        </div>
      )}

      {/* ── Footer Actions ─────────────────────────────────────────── */}
      {isOriginal ? (
        <div className="flex items-end justify-end pt-3 border-t border-white/5">
          <span className="text-[11px] text-gray-600 italic">
            Baseline query — no actions available
          </span>
        </div>
      ) : (
        <div className="flex items-center justify-between pt-3 border-t border-white/5">
          <div className="flex items-center gap-2">
            {isApproved && (
              <span className="inline-flex items-center gap-1.5 text-[11px] font-medium px-3 py-1.5 rounded-lg badge-green">
                <Check size={11} />
                Approved
              </span>
            )}
            {isRejected && (
              <span className="inline-flex items-center gap-1.5 text-[11px] font-medium px-3 py-1.5 rounded-lg badge-red">
                <X size={11} />
                Rejected
              </span>
            )}
          </div>

          <div className="flex items-center gap-2">
            <button
              disabled={!isPending}
              onClick={handleReject}
              className={`
                flex items-center gap-1.5 px-4 py-2
                rounded-xl text-[12px] font-medium
                transition-all duration-200
                disabled:cursor-not-allowed disabled:opacity-30
                ${isRejected
                  ? "text-red-400 bg-red-500/10 border border-red-500/20"
                  : "text-gray-400 hover:text-red-400 hover:bg-red-500/10 border border-white/10 hover:border-red-500/20"
                }
              `}
            >
              <X size={13} />
              Reject
            </button>
            <button
              disabled={!isPending}
              onClick={handleApprove}
              className={`
                flex items-center gap-1.5 px-5 py-2
                rounded-xl text-[12px] font-semibold
                transition-all duration-200
                disabled:cursor-not-allowed disabled:opacity-30
                ${isApproved
                  ? "bg-green-500 text-white shadow-lg shadow-green-500/25"
                  : "bg-green-500/10 text-green-400 border border-green-500/20 hover:bg-green-500 hover:text-white hover:shadow-lg hover:shadow-green-500/25"
                }
              `}
            >
              <Check size={13} />
              {isApproved ? "Approved" : "Approve"}
            </button>
          </div>
        </div>
      )}
    </article>
  );
}

export default DecisionCard;
