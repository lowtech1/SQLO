/**
 * ExplainTree.jsx
 * Renders PostgreSQL EXPLAIN ANALYZE JSON as an interactive, color-coded tree.
 * Collapsible nodes, per-node metrics (cost, rows, time), bottleneck highlighting.
 */

import { useState } from "react";

/* ─── Color mapping per node type ─────────────────────────────────────────── */
const NODE_COLORS = {
  "Seq Scan":                   { bg: "bg-red-500/15",    border: "border-red-500/40",   text: "text-red-400",    dot: "bg-red-400",    badge: "badge-red" },
  "Parallel Seq Scan":          { bg: "bg-red-500/15",    border: "border-red-500/40",   text: "text-red-400",    dot: "bg-red-400",    badge: "badge-red" },
  "Index Scan":                 { bg: "bg-green-500/15",  border: "border-green-500/40", text: "text-green-400",  dot: "bg-green-400",  badge: "badge-green" },
  "Index Only Scan":            { bg: "bg-green-500/15",  border: "border-green-500/40", text: "text-green-400",  dot: "bg-green-400",  badge: "badge-green" },
  "Bitmap Index Scan":          { bg: "bg-green-500/10",  border: "border-green-500/30", text: "text-green-400/80",dot: "bg-green-400",  badge: "badge-green" },
  "Bitmap Heap Scan":           { bg: "bg-orange-500/15", border: "border-orange-500/40",text: "text-orange-400", dot: "bg-orange-400", badge: "badge-yellow" },
  "Hash Join":                  { bg: "bg-purple-500/15", border: "border-purple-500/40",text: "text-purple-400",dot: "bg-purple-400", badge: "badge-purple" },
  "Merge Join":                 { bg: "bg-purple-500/15", border: "border-purple-500/40",text: "text-purple-400",dot: "bg-purple-400", badge: "badge-purple" },
  "Nested Loop":                { bg: "bg-purple-500/15", border: "border-purple-500/40",text: "text-purple-400",dot: "bg-purple-400", badge: "badge-purple" },
  "Aggregate":                  { bg: "bg-blue-500/15",   border: "border-blue-500/40",   text: "text-blue-400",   dot: "bg-blue-400",   badge: "badge-blue" },
  "Hash":                       { bg: "bg-blue-500/10",   border: "border-blue-500/30",   text: "text-blue-400/80", dot: "bg-blue-400",   badge: "badge-blue" },
  "Sort":                       { bg: "bg-yellow-500/15", border: "border-yellow-500/40", text: "text-yellow-400",  dot: "bg-yellow-400", badge: "badge-yellow" },
  "Gather Merge":               { bg: "bg-gray-500/15",  border: "border-gray-500/40",   text: "text-gray-400",   dot: "bg-gray-400",   badge: "badge-gray" },
  "Gather":                     { bg: "bg-gray-500/15",  border: "border-gray-500/40",   text: "text-gray-400",   dot: "bg-gray-400",   badge: "badge-gray" },
  "Materialize":                { bg: "bg-gray-500/10",  border: "border-gray-500/30",   text: "text-gray-400/80",dot: "bg-gray-400",   badge: "badge-gray" },
  "Memoize":                    { bg: "bg-gray-500/10",  border: "border-gray-500/30",   text: "text-gray-400/80",dot: "bg-gray-400",   badge: "badge-gray" },
  "Result":                     { bg: "bg-gray-500/10",  border: "border-gray-500/30",   text: "text-gray-400/80",dot: "bg-gray-400",   badge: "badge-gray" },
  "CTE Scan":                   { bg: "bg-pink-500/15",  border: "border-pink-500/40",   text: "text-pink-400",   dot: "bg-pink-400",   badge: "badge-purple" },
  "Subquery Scan":              { bg: "bg-indigo-500/15",border: "border-indigo-500/40", text: "text-indigo-400", dot: "bg-indigo-400", badge: "badge-purple" },
  "Function Scan":              { bg: "bg-cyan-500/15",  border: "border-cyan-500/40",   text: "text-cyan-400",   dot: "bg-cyan-400",   badge: "badge-blue" },
  "Values Scan":                { bg: "bg-cyan-500/10",  border: "border-cyan-500/30",   text: "text-cyan-400/80",dot: "bg-cyan-400",   badge: "badge-blue" },
  "Tid Scan":                   { bg: "bg-cyan-500/10",  border: "border-cyan-500/30",   text: "text-cyan-400/80",dot: "bg-cyan-400",   badge: "badge-blue" },
  "Limit":                      { bg: "bg-teal-500/15",  border: "border-teal-500/40",   text: "text-teal-400",   dot: "bg-teal-400",   badge: "badge-green" },
  "WindowAgg":                  { bg: "bg-blue-500/15",   border: "border-blue-500/40",   text: "text-blue-400",   dot: "bg-blue-400",   badge: "badge-blue" },
  "Unique":                     { bg: "bg-gray-500/10",  border: "border-gray-500/30",   text: "text-gray-400/80",dot: "bg-gray-400",   badge: "badge-gray" },
  "SetOp":                      { bg: "bg-gray-500/10",  border: "border-gray-500/30",   text: "text-gray-400/80",dot: "bg-gray-400",   badge: "badge-gray" },
  "Append":                     { bg: "bg-orange-500/10",border: "border-orange-500/30",text: "text-orange-400/80",dot:"bg-orange-400",badge: "badge-yellow" },
  "Seq":                        { bg: "bg-red-500/15",   border: "border-red-500/40",   text: "text-red-400",    dot: "bg-red-400",    badge: "badge-red" },
};

const DEFAULT_COLOR = { bg: "bg-gray-500/15", border: "border-gray-500/40", text: "text-gray-400", dot: "bg-gray-400", badge: "badge-gray" };

function getNodeColors(nodeType) {
  // Try exact match first
  if (NODE_COLORS[nodeType]) return NODE_COLORS[nodeType];
  // Try partial match
  for (const [key, val] of Object.entries(NODE_COLORS)) {
    if (nodeType.includes(key) || key.includes(nodeType)) return val;
  }
  return DEFAULT_COLOR;
}

/* ─── Helpers ─────────────────────────────────────────────────────────────── */
function fmt(n) {
  if (n === null || n === undefined) return "—";
  return Number(n).toLocaleString("en-US", { maximumFractionDigits: 1 });
}

function fmtMs(n) {
  if (n === null || n === undefined) return "—";
  return `${Number(n).toFixed(2)}ms`;
}

function isBottleneck(node) {
  const type = node["Node Type"] || "";
  const cost = node["Total Cost"] || 0;
  const rows = node["Plan Rows"] || 0;
  // Seq scans on potentially large tables are bottlenecks
  if (type.includes("Seq Scan") && (rows > 10000 || cost > 5000)) return true;
  // Very high cost relative to siblings
  if (cost > 50000 && (type.includes("Join") || type.includes("Aggregate"))) return true;
  return false;
}

/* ─── Single plan node ────────────────────────────────────────────────────── */
function PlanNode({ node, depth = 0, totalCost = 1 }) {
  const [open, setOpen] = useState(depth < 2); // auto-expand first 2 levels
  const type = node["Node Type"] || "Unknown";
  const colors = getNodeColors(type);
  const cost = node["Total Cost"] || 0;
  const rows = node["Plan Rows"] || 0;
  const actualTime = node["Actual Total Time"];
  const actualRows = node["Actual Rows"];
  const rel = node["Relation Name"];
  const filter = node["Filter"];
  const joinType = node["Join Type"];
  const strategy = node["Strategy"];
  const parentRel = node["Parent Relationship"];
  const costPct = totalCost > 0 ? Math.min(100, (cost / totalCost) * 100) : 0;
  const bottleneck = isBottleneck(node);

  const childPlans = node["Plans"] || [];
  const hasChildren = childPlans.length > 0;

  return (
    <div className="select-none">
      {/* Node row */}
      <div
        onClick={hasChildren ? () => setOpen((v) => !v) : undefined}
        className={`
          flex items-center gap-2 px-3 py-1.5 rounded-lg mb-0.5
          border transition-all duration-150 cursor-pointer
          ${colors.bg} ${colors.border}
          ${hasChildren ? "hover:opacity-90" : "cursor-default"}
          ${bottleneck ? "ring-1 ring-red-500/50" : ""}
        `}
        style={{ marginLeft: depth * 18 }}
      >
        {/* Expand chevron */}
        {hasChildren ? (
          <span className={`${colors.text} text-[10px] w-4 text-center shrink-0 transition-transform duration-150 ${open ? "rotate-90" : ""}`}>
            ▶
          </span>
        ) : (
          <span className="w-4 shrink-0" />
        )}

        {/* Node type dot */}
        <span className={`w-2 h-2 rounded-full shrink-0 ${colors.dot} ${bottleneck ? "animate-pulse" : ""}`} />

        {/* Node type name */}
        <span className={`text-[11px] font-semibold shrink-0 ${colors.text}`}>
          {type}
        </span>

        {/* Bottleneck badge */}
        {bottleneck && (
          <span className="text-[8px] font-bold px-1.5 py-0.5 rounded badge-red shrink-0">
            SLOW
          </span>
        )}

        {/* Relation name */}
        {rel && (
          <span className="text-[10px] font-mono text-gray-500 truncate max-w-[140px]">
            on {rel}
          </span>
        )}

        {/* Join type */}
        {joinType && joinType !== "Inner" && (
          <span className="text-[9px] font-bold px-1 py-0.5 rounded bg-orange-500/20 text-orange-400 shrink-0">
            {joinType}
          </span>
        )}

        {/* Strategy */}
        {strategy && (
          <span className="text-[9px] text-gray-500 shrink-0">
            [{strategy}]
          </span>
        )}

        {/* Parent relationship */}
        {parentRel && parentRel !== "Outer" && (
          <span className="text-[9px] text-gray-600 italic shrink-0">
            {parentRel}
          </span>
        )}

        {/* Spacer */}
        <div className="flex-1" />

        {/* Metrics */}
        <div className="flex items-center gap-3 shrink-0">
          {/* Cost bar */}
          <div className="flex items-center gap-1.5">
            <div className="w-16 h-1.5 bg-gray-700 rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full transition-all duration-500 ${
                  bottleneck ? "bg-red-400" : costPct > 50 ? "bg-orange-400" : "bg-blue-400"
                }`}
                style={{ width: `${costPct}%` }}
              />
            </div>
            <span className="text-[9px] font-mono text-gray-500 w-14 text-right">
              {costPct.toFixed(0)}% · {fmt(cost)}
            </span>
          </div>

          {/* Rows */}
          {rows > 0 && (
            <span className="text-[9px] font-mono text-gray-500 w-16 text-right">
              {fmt(rows)} rows
            </span>
          )}

          {/* Actual time */}
          {actualTime !== undefined && actualTime !== null && (
            <span className="text-[9px] font-mono text-green-400/80 w-20 text-right">
              {fmtMs(actualTime)}
            </span>
          )}
        </div>
      </div>

      {/* Filter annotation */}
      {filter && (
        <div
          className="text-[9px] font-mono text-gray-500 mb-0.5 leading-tight"
          style={{ marginLeft: depth * 18 + 32 }}
        >
          Filter: <span className="text-yellow-400/70">{filter.length > 80 ? filter.slice(0, 80) + "..." : filter}</span>
        </div>
      )}

      {/* Child nodes */}
      {hasChildren && open && (
        <div className="mt-0.5">
          {childPlans.map((child, i) => (
            <PlanNode
              key={i}
              node={child}
              depth={depth + 1}
              totalCost={totalCost}
            />
          ))}
        </div>
      )}
    </div>
  );
}

/* ─── Top-level summary bar ────────────────────────────────────────────────── */
function PlanSummary({ plan }) {
  const totalCost = plan["Total Cost"] || 0;
  const planRows = plan["Plan Rows"] || 0;
  const totalTime = plan["Actual Total Time"];
  const sharedHit = plan["Shared Hit Blocks"] || 0;
  const sharedRead = plan["Shared Read Blocks"] || 0;
  const totalBuffers = sharedHit + sharedRead;
  const cacheHitPct = totalBuffers > 0 ? ((sharedHit / totalBuffers) * 100).toFixed(1) : null;

  return (
    <div className="flex flex-wrap items-center gap-3 px-4 py-2.5 rounded-lg bg-[#0D1117] border border-white/5 mb-3">
      <div className="flex items-center gap-1.5">
        <span className="text-[9px] font-semibold text-gray-500 uppercase">Cost</span>
        <span className="text-[12px] font-bold font-mono text-white">{fmt(totalCost)}</span>
      </div>
      <div className="w-px h-4 bg-white/10" />
      <div className="flex items-center gap-1.5">
        <span className="text-[9px] font-semibold text-gray-500 uppercase">Rows</span>
        <span className="text-[12px] font-bold font-mono text-white">{fmt(planRows)}</span>
      </div>
      {totalTime !== undefined && totalTime !== null && (
        <>
          <div className="w-px h-4 bg-white/10" />
          <div className="flex items-center gap-1.5">
            <span className="text-[9px] font-semibold text-gray-500 uppercase">Time</span>
            <span className="text-[12px] font-bold font-mono text-green-400">{fmtMs(totalTime)}</span>
          </div>
        </>
      )}
      {totalBuffers > 0 && (
        <>
          <div className="w-px h-4 bg-white/10" />
          <div className="flex items-center gap-1.5">
            <span className="text-[9px] font-semibold text-gray-500 uppercase">Buffers</span>
            <span className="text-[10px] font-mono">
              <span className="text-blue-400">{fmt(sharedHit)} hit</span>
              {" · "}
              <span className="text-orange-400">{fmt(sharedRead)} read</span>
            </span>
            {cacheHitPct && (
              <span className="text-[9px] font-semibold text-gray-500">({cacheHitPct}% hit)</span>
            )}
          </div>
        </>
      )}
    </div>
  );
}

/* ─── Legend ──────────────────────────────────────────────────────────────── */
const LEGEND_ITEMS = [
  { color: "bg-red-400", label: "Seq Scan" },
  { color: "bg-green-400", label: "Index Scan" },
  { color: "bg-purple-400", label: "Join" },
  { color: "bg-blue-400", label: "Aggregate" },
  { color: "bg-yellow-400", label: "Sort" },
  { color: "bg-gray-400", label: "Other" },
];

function Legend() {
  return (
    <div className="flex flex-wrap items-center gap-3 px-4 py-2 mb-3">
      {LEGEND_ITEMS.map((item) => (
        <div key={item.label} className="flex items-center gap-1.5">
          <span className={`w-2 h-2 rounded-full ${item.color}`} />
          <span className="text-[9px] text-gray-500">{item.label}</span>
        </div>
      ))}
    </div>
  );
}

/* ─── Main component ───────────────────────────────────────────────────────── */
export function ExplainTree({ planData }) {
  if (!planData) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center">
        <svg width="32" height="32" viewBox="0 0 24 24" fill="none"
          stroke="#374151" strokeWidth="1.5" className="mb-3">
          <path d="M9 3H5a2 2 0 0 0-2 2v4m6-6h10a2 2 0 0 1 2 2v4M9 3v18m0 0h10a2 2 0 0 0 2-2V9M9 21H5a2 2 0 0 1-2-2V9m0 0h18" />
        </svg>
        <p className="text-[12px] text-gray-600">No execution plan available.</p>
        <p className="text-[11px] text-gray-700 mt-1">Run Analyze Query to see the EXPLAIN tree.</p>
      </div>
    );
  }

  // planData is the full EXPLAIN JSON array; plan is the first element's Plan object
  const plan = planData?.Plan || planData;

  return (
    <div className="flex flex-col min-h-0">
      <PlanSummary plan={plan} />
      <Legend />
      <div className="flex-1 overflow-y-auto max-h-[420px] pr-1">
        <PlanNode node={plan} depth={0} totalCost={plan["Total Cost"] || 1} />
      </div>
    </div>
  );
}

export default ExplainTree;
