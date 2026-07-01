/**
 * MetricsPanel.jsx
 * Premium dark mode performance metrics for the right sidebar.
 * Reads from the new AnalysisResult schema:
 *   - data.metrics         (top-level, post-adapter)
 *   - best candidate's plan_comparison (original + rewritten)
 *   - data.recommendation  (best_candidate_id, best_rules)
 */

import { Zap, Copy, Play } from "./Icons.jsx";
import { SqlCodeBlock } from "./SqlCodeBlock.jsx";
import { ExplainTree } from "./ExplainTree.jsx";
import { useState } from "react";

/** A single metric cell in the 2x2 grid. */
function MetricCell({ label, orig, opt, unit = "", imp = "—", improved = true }) {
  const max = Math.max(orig || 0, opt || 0);
  const origW = max > 0 ? Math.max(4, ((orig || 0) / max) * 100) : 50;
  const optW = max > 0 ? Math.max(4, ((opt || 0) / max) * 100) : 50;

  return (
    <div className="rounded-xl p-4 surface-card border border-themed">
      <div className="flex items-center justify-between mb-3">
        <span className="text-[9px] font-semibold text-gray-500 uppercase tracking-widest leading-tight">
          {label}
        </span>
        <span className={`text-[11px] font-bold px-1.5 py-0.5 rounded-md ${improved ? "badge-green" : "badge-red"}`}>
          {imp}
        </span>
      </div>

      <div className="space-y-1.5">
        {/* Original bar */}
        <div className="flex items-center gap-2">
          <span className="text-[8px] text-gray-600 w-6 text-right shrink-0 font-medium">Orig</span>
          <div className="flex-1 h-3.5 surface-tab rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full flex items-center justify-end pr-1.5 transition-all duration-700 ${improved ? "bg-green-500/30" : "bg-red-500/30"
                }`}
              style={{ width: `${origW}%` }}
            >
              {origW > 22 && (
                <span className="text-[8px] font-mono font-bold text-gray-400 leading-none">
                  {orig}{unit}
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Optimized bar */}
        <div className="flex items-center gap-2">
          <span className="text-[8px] w-6 text-right shrink-0 font-medium">Opt</span>
          <div className="flex-1 h-3.5 surface-tab rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full flex items-center justify-end pr-1.5 transition-all duration-700 ${improved ? "bg-green-500/50" : "bg-red-500/50"
                }`}
              style={{ width: `${optW}%` }}
            >
              {optW > 22 && (
                <span className={`text-[8px] font-mono font-bold leading-none ${improved ? "text-green-400/80" : "text-red-400/80"
                  }`}>
                  {opt}{unit}
                </span>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

/** MetricsPanel — right sidebar */
export function MetricsPanel({ data, decisions }) {
  const [copied, setCopied] = useState(false);
  const [rightTab, setRightTab] = useState("metrics");

  // Find the best candidate by recommendation.best_candidate_id
  const best = data?.candidates?.find(
    (c) => c.id === data?.recommendation?.best_candidate_id
  );

  // Plan comparison metrics (nested under plan_comparison.original/rewritten)
  const origMetrics = best?.plan_comparison?.original?.metrics;
  const rewMetrics = best?.plan_comparison?.rewritten?.metrics;
  const comp = best?.plan_comparison?.comparison;

  // Top-level metrics from the adapter
  const topMetrics = data?.metrics;

  // Display SQL — best candidate's rewritten SQL, fallback to original_sql
  const displaySql = best?.sql || data?.original_sql || "";

  // Applied rules from recommendation.best_rules
  const appliedRules = data?.recommendation?.best_rules || [];

  const handleCopy = () => {
    navigator.clipboard.writeText(displaySql).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  const fmt = (n) => {
    if (n === null || n === undefined) return "—";
    // n is already the correct sign after backend inversion:
    //   negative = improvement (opt < orig), positive = degradation (opt > orig)
    return n > 0 ? `+${n.toFixed(1)}%` : `${n.toFixed(1)}%`;
  };

  const totalCostImp = comp?.cost_improvement_pct ?? 0;

  return (
    <aside className="flex-1 min-h-0 flex flex-col surface-primary border-l border-themed">

      {/* ── Optimized SQL Panel ───────────────────────────────── */}
      <div className="px-4 pt-5 pb-4 border-b border-themed">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <svg width="13" height="13" viewBox="0 0 16 16" fill="none"
              stroke="#60a5fa" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
              <rect x="3" y="7.5" width="10" height="7" rx="1.5" />
              <path d="M5.5 7.5 V5 a2.5 2.5 0 0 1 5 0 V7.5" />
            </svg>
            <h3 className="text-[11px] font-semibold text-themed-secondary uppercase tracking-widest">
              Final Optimized SQL
            </h3>
          </div>
        </div>

        {/* SQL block */}
        <div className="rounded-xl overflow-hidden border border-themed mb-3">
          <div className="flex items-center justify-between px-3 py-2 surface-code border-b border-themed">
            <span className="text-[9px] font-mono text-themed-secondary">optimized.sql</span>
            <span className="text-[9px] text-themed-secondary">Read-only</span>
          </div>
          <div className="max-h-[280px] overflow-y-auto">
            <SqlCodeBlock code={displaySql} />
          </div>
        </div>

        {/* Action buttons */}
        <div className="flex gap-2">
          <button
            onClick={handleCopy}
            className={`
              flex-1 flex items-center justify-center gap-2
              px-3 py-2.5 rounded-xl text-[12px] font-medium
              transition-all duration-200
              ${copied
                ? "bg-green-500 text-white border border-green-500 shadow-lg"
                : "surface-card border border-themed text-themed-primary hover:text-themed-active surface-hover hover:border-themed-active"
              }
            `}
          >
            <Copy size={13} />
            {copied ? "Copied!" : "Copy SQL"}
          </button>
          <button className="
            flex-1 flex items-center justify-center gap-2
            px-3 py-2.5 rounded-xl text-[12px] font-medium
            bg-green-500 hover:bg-green-400 text-white
            transition-all shadow-lg
          ">
            <Play size={13} />
            Execute
          </button>
        </div>
      </div>

      {/* ── EXPLAIN Tree ─────────────────────────────────────── */}
      {data?.explain_plan && (
        <div className="px-4 pt-4 pb-4 border-b border-themed">
          <div className="flex items-center gap-2 mb-3">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none"
              stroke="currentColor" className="text-blue-500" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M9 3H5a2 2 0 0 0-2 2v4m6-6h10a2 2 0 0 1 2 2v4M9 3v18m0 0h10a2 2 0 0 0 2-2V9M9 21H5a2 2 0 0 1-2-2V9m0 0h18" />
            </svg>
            <h3 className="text-[11px] font-semibold text-themed-secondary uppercase tracking-widest">
              Execution Plan
            </h3>
          </div>
          <div className="rounded-xl overflow-hidden border border-themed">
            <ExplainTree planData={data.explain_plan} />
          </div>
        </div>
      )}

      {/* ── Metrics Dashboard ─────────────────────────────────── */}
      <div className="flex-1 min-h-0 overflow-y-auto px-4 py-4">
        <div className="flex items-center gap-2 mb-4">
          <Zap size={13} className="text-purple-400" />
          <h3 className="text-[11px] font-semibold text-gray-400 uppercase tracking-widest">
            Performance Metrics
          </h3>
        </div>

        {(origMetrics || rewMetrics || topMetrics) ? (
          <div className="space-y-4">
            {/* 2x2 Grid */}
            <div className="grid grid-cols-2 gap-3">
              <MetricCell
                label="Execution Time"
                orig={origMetrics?.estimated_time_ms ?? topMetrics?.execution_time_ms}
                opt={rewMetrics?.estimated_time_ms ?? topMetrics?.execution_time_ms}
                unit="ms"
                imp={fmt(origMetrics?.estimated_time_ms && rewMetrics?.estimated_time_ms
                  ? ((origMetrics.estimated_time_ms - rewMetrics.estimated_time_ms) / origMetrics.estimated_time_ms) * 100
                  : null)}
                improved={(rewMetrics?.estimated_time_ms ?? Infinity) <= (origMetrics?.estimated_time_ms ?? 0)}
              />
              <MetricCell
                label="Planner Cost"
                orig={origMetrics?.total_cost ?? topMetrics?.total_cost}
                opt={rewMetrics?.total_cost ?? topMetrics?.total_cost}
                unit=""
                imp={fmt(comp?.cost_improvement_pct)}
                improved={(rewMetrics?.total_cost ?? Infinity) <= (origMetrics?.total_cost ?? 0)}
              />
              <MetricCell
                label="I/O Cost"
                orig={origMetrics?.io_cost ?? topMetrics?.io_cost}
                opt={rewMetrics?.io_cost ?? topMetrics?.io_cost}
                unit=""
                imp={fmt(comp?.io_improvement_pct)}
                improved={(rewMetrics?.io_cost ?? Infinity) <= (origMetrics?.io_cost ?? 0)}
              />
              <MetricCell
                label="CPU Cost"
                orig={origMetrics?.cpu_cost ?? topMetrics?.cpu_cost}
                opt={rewMetrics?.cpu_cost ?? topMetrics?.cpu_cost}
                unit=""
                imp={fmt(comp?.cpu_improvement_pct)}
                improved={(rewMetrics?.cpu_cost ?? Infinity) <= (origMetrics?.cpu_cost ?? 0)}
              />
            </div>

            {/* Summary bar */}
            <div className="rounded-xl p-4 surface-card border border-themed">
              <div className="flex items-center justify-between mb-3">
                <span className="text-[10px] font-medium text-gray-400 uppercase tracking-widest">
                  Total Improvement
                </span>
                <span className={`text-[16px] font-bold font-mono ${totalCostImp > 0 ? "text-green-400" : "text-red-400"}`}>
                  {fmt(totalCostImp)}
                </span>
              </div>
              <div className="h-2.5 surface-tab rounded-full overflow-hidden">
                <div
                  className="h-full rounded-full transition-all duration-700"
                  style={{
                    width: `${Math.min(100, Math.max(4,
                      ((rewMetrics?.total_cost ?? topMetrics?.total_cost ?? 0) /
                        (origMetrics?.total_cost ?? topMetrics?.total_cost ?? 1)) * 100
                    ))}%`,
                    background: totalCostImp <= 0
                      ? "linear-gradient(to right, rgba(34,197,94,0.4), rgba(34,197,94,0.7))"
                      : "linear-gradient(to right, rgba(239,68,68,0.4), rgba(239,68,68,0.7))",
                  }}
                />
              </div>
              <div className="flex justify-between mt-2">
                <span className="text-[9px] text-gray-600 font-mono">
                  {rewMetrics?.total_cost ?? topMetrics?.total_cost ?? 0} opt
                </span>
                <span className="text-[9px] text-gray-600 font-mono">
                  {origMetrics?.total_cost ?? topMetrics?.total_cost ?? 0} orig
                </span>
              </div>
            </div>

            {/* Applied Rules */}
            <div className="rounded-xl p-4 surface-card border border-themed">
              <div className="text-[9px] font-semibold text-gray-500 uppercase tracking-widest mb-3">
                Applied Rules
              </div>
              <div className="flex flex-wrap gap-1.5 mb-3">
                {appliedRules.map((r, i) => (
                  <span key={i} className="text-[9px] px-2 py-0.5 rounded-md badge-purple">
                    {r.replace(/_/g, " ")}
                  </span>
                ))}
                {appliedRules.length === 0 && (
                  <span className="text-[9px] text-gray-600 italic">No rules applied</span>
                )}
              </div>
              {best?.semantic_check?.equivalent && (
                <div className="flex items-center gap-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-green-400 shrink-0" />
                  <span className="text-[10px] text-green-400/70">Semantically equivalent</span>
                </div>
              )}
            </div>
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center py-16 text-center">
            <Zap size={28} className="text-gray-700 mb-3" />
            <p className="text-[12px] text-gray-600 mb-1">No metrics available.</p>
            <p className="text-[11px] text-gray-700">Run Analyze Query first.</p>
          </div>
        )}
      </div>
    </aside>
  );
}

export default MetricsPanel;
