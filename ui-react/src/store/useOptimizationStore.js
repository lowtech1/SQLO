/**
 * useOptimizationStore.js
 * Zustand store for LLM-R2 dashboard state.
 *
 * Manages:
 *  - Export modal visibility
 *  - Analysis loading state + error
 *  - Analysis result data (populated by analyzeQuery)
 *  - Rule execution (candidate approval/rejection)
 */

import { create } from "zustand";
import { mockAnalysisResult } from "../data/mockData.js";

export const useOptimizationStore = create((set, get) => ({
  /* ── Database connection ─────────────────────────────── */
  dbStatus: "disconnected", // 'disconnected' | 'connecting' | 'connected'
  dbError: null,
  schema: null, // live schema from backend
  dbConnParams: null,

  connectDB: async (params) => {
    set({ dbStatus: "connecting", dbError: null });
    try {
      // Call backend to test connection and fetch schema in one step
      const resp = await fetch("/api/v1/connect", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(params),
      });
      const data = await resp.json();
      if (!resp.ok) {
        throw new Error(data.detail || `Connection failed (${resp.status})`);
      }
      set({
        dbStatus: "connected",
        dbConnParams: params,
        schema: data.schema || null,
      });
    } catch (err) {
      set({ dbStatus: "disconnected", dbError: err.message });
    }
  },

  disconnectDB: () => set({ dbStatus: "disconnected", dbConnParams: null, schema: null, dbError: null }),

  /* ── Export modal ─────────────────────────────────────── */
  isExportModalOpen: false,
  openExportModal: () => set({ isExportModalOpen: true }),
  closeExportModal: () => set({ isExportModalOpen: false }),

  /* ── Analysis state ─────────────────────────────────── */
  isAnalyzing: false,
  error: null,
  data: null,

  /* ── Decisions (candidateId → approved | rejected | pending) ── */
  decisions: {},

  /* ── Analyze query — requires DB connection ─────────── */
  analyzeQuery: async (sql, activeRules) => {
    const { dbStatus } = get();
    if (dbStatus !== "connected") {
      set({ error: "Connect to a database first before analyzing queries." });
      return;
    }
    set({ isAnalyzing: true, error: null, data: null });

    try {
      // ── Real API call ──────────────────────────────────────────────
      const response = await fetch("/api/v1/optimize", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ raw_sql: sql, active_rules: activeRules }),
      });

      // If the server returned a structured error body, surface it
      if (!response.ok) {
        let serverMsg = `Server error: ${response.status}`;
        try {
          const errBody = await response.json();
          if (errBody?.detail) {
            const d = errBody.detail;
            // detail can be: string, Pydantic error object, or array of errors
            if (typeof d === 'string') {
              serverMsg = d;
            } else if (Array.isArray(d)) {
              // Array of Pydantic errors: extract human-readable messages
              serverMsg = d.map(e => typeof e === 'string' ? e : e?.msg || e?.type || JSON.stringify(e)).join('; ');
            } else {
              serverMsg = d?.msg || d?.detail || JSON.stringify(d);
            }
          }
          // Also check for top-level error fields
          if (!serverMsg || serverMsg.startsWith('Server error:')) {
            if (errBody?.error) serverMsg = typeof errBody.error === 'string' ? errBody.error : errBody.error?.message || JSON.stringify(errBody.error);
            if (errBody?.traceback) {
              // Truncate traceback to last meaningful line
              const lines = errBody.traceback.trim().split('\n').filter(l => l.trim());
              serverMsg = lines[lines.length - 1]?.trim() || serverMsg;
            }
          }
        } catch (_) {}
        throw new Error(serverMsg);
      }

      const result = await response.json();
      // ───────────────────────────────────────────────────────────────

      // Initialise decision state for every non-original candidate
      const decisions = {};
      (result.candidates || []).forEach((c) => {
        if (!c.is_original) decisions[c.id] = "pending";
      });

      set({ isAnalyzing: false, data: result, decisions });
    } catch (err) {
      const message = err instanceof Error ? err.message : "Unknown error occurred";
      set({ isAnalyzing: false, error: message });
    }
  },

  /* ── Decision actions ────────────────────────────────── */
  setDecision: (candidateId, decision) =>
    set((state) => ({
      decisions: { ...state.decisions, [candidateId]: decision },
    })),

  resetDecisions: () =>
    set((state) => {
      const decisions = {};
      (state.data?.candidates || []).forEach((c) => {
        if (!c.is_original) decisions[c.id] = "pending";
      });
      return { decisions };
    }),
}));
