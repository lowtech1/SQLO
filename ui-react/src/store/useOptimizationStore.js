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
  connectDB: async (params) => {
    set({ dbStatus: "connecting" });
    try {
      // Simulate connection delay — replace with real DB connection logic
      await new Promise((r) => setTimeout(r, 1500));
      set({ dbStatus: "connected", dbConnParams: params });
    } catch {
      set({ dbStatus: "disconnected" });
    }
  },
  disconnectDB: () => set({ dbStatus: "disconnected", dbConnParams: null }),
  dbConnParams: null,

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

  /* ── Analyze query ──────────────────────────────────── */
  analyzeQuery: async (sql, activeRules) => {
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
          if (errBody?.detail) serverMsg = errBody.detail;
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
