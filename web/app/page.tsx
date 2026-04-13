"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { WorkbenchHeader } from "@/components/workbench-header";
import { RunControls } from "@/components/run-controls";
import { CurrentRunSelector } from "@/components/current-run-selector";
import { RunStatusPanel } from "@/components/run-status-panel";
import { SummaryCards } from "@/components/summary-cards";
import { ResultToggle } from "@/components/result-toggle";
import { LeadsTable } from "@/components/leads-table";
import { LeadDetailPanel } from "@/components/lead-detail-panel";
import { FeishuTestPanel } from "@/components/feishu-test-panel";
import {
  fetchHealth,
  fetchRunDetail,
  fetchRunsList,
  startRun,
  testFeishuCreateTable,
} from "@/lib/api";
import type { RunDetailResponse, RunListItem, UILeadRecord, TestCreateTableResponse } from "@/lib/types";
import { mapBackendLeadToUiRecord } from "@/lib/ui-mapper";

export default function Page() {
  const [backendOk, setBackendOk] = useState<boolean | null>(null);
  const [maxLeads, setMaxLeads] = useState(10);
  const [useLlmQueries, setUseLlmQueries] = useState(true);
  const [useLlmActions, setUseLlmActions] = useState(true);
  const [outputFeishu, setOutputFeishu] = useState(true);
  const [starting, setStarting] = useState(false);
  const [runs, setRuns] = useState<RunListItem[]>([]);
  const [currentRunId, setCurrentRunId] = useState<string | null>(null);
  const [runDetail, setRunDetail] = useState<RunDetailResponse | null>(null);
  const [apiError, setApiError] = useState<string | null>(null);
  const [selected, setSelected] = useState<UILeadRecord | null>(null);
  const [resultsOpen, setResultsOpen] = useState(false);
  const [feishuTestResult, setFeishuTestResult] = useState<TestCreateTableResponse | null>(null);
  const [feishuTesting, setFeishuTesting] = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const checkHealth = useCallback(async () => {
    try {
      const h = await fetchHealth();
      setBackendOk(Boolean(h.ok));
      setApiError(null);
    } catch {
      setBackendOk(false);
    }
  }, []);

  const loadRuns = useCallback(async () => {
    try {
      const list = await fetchRunsList();
      setRuns(list);
      setApiError(null);
    } catch (e) {
      setApiError(e instanceof Error ? e.message : String(e));
    }
  }, []);

  const loadRun = useCallback(async (id: string) => {
    try {
      const d = await fetchRunDetail(id);
      setRunDetail(d);
      setApiError(null);
      return d;
    } catch (e) {
      setApiError(e instanceof Error ? e.message : String(e));
      return null;
    }
  }, []);

  useEffect(() => {
    void checkHealth();
    const h = setInterval(() => void checkHealth(), 30000);
    return () => clearInterval(h);
  }, [checkHealth]);

  useEffect(() => {
    void loadRuns();
  }, [loadRuns]);

  useEffect(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
    if (!currentRunId) return;

    const tick = () => {
      void loadRun(currentRunId).then((d) => {
        if (!d) return;
        if (d.status === "completed" || d.status === "failed") {
          if (pollRef.current) {
            clearInterval(pollRef.current);
            pollRef.current = null;
          }
        }
      });
    };

    void tick();
    pollRef.current = setInterval(tick, 2500);

    return () => {
      if (pollRef.current) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
    };
  }, [currentRunId, loadRun]);

  const uiRows = useMemo(() => {
    const raw = runDetail?.leads ?? [];
    return raw.map((l) => mapBackendLeadToUiRecord(l));
  }, [runDetail?.leads]);

  const manualSearchCount = useMemo(
    () =>
      uiRows.filter((r) => r.搜索处理状态 === "高符合度，需人工搜索").length,
    [uiRows]
  );

  const handleStart = async () => {
    setStarting(true);
    setApiError(null);
    try {
      const started = await startRun({
        max_leads: maxLeads,
        use_llm_queries: useLlmQueries,
        use_llm_actions: useLlmActions,
        output_feishu: outputFeishu,
      });
      const { run_id } = started;
      setCurrentRunId(run_id);
      setSelected(null);
      setResultsOpen(false);
      await loadRuns();
      await loadRun(run_id);
    } catch (e) {
      setApiError(e instanceof Error ? e.message : String(e));
    } finally {
      setStarting(false);
    }
  };

  const handleRunChange = (id: string) => {
    if (!id) {
      setCurrentRunId(null);
      setRunDetail(null);
      setSelected(null);
      setResultsOpen(false);
      return;
    }
    setCurrentRunId(id);
    setSelected(null);
    setResultsOpen(false);
  };

  const closeResults = () => {
    setResultsOpen(false);
    setSelected(null);
  };

  const openResults = () => setResultsOpen(true);

  const handleTestFeishu = async () => {
    setFeishuTesting(true);
    setFeishuTestResult(null);
    setApiError(null);
    try {
      const result = await testFeishuCreateTable();
      setFeishuTestResult(result);
    } catch (e) {
      setApiError(e instanceof Error ? e.message : String(e));
    } finally {
      setFeishuTesting(false);
    }
  };

  const displayRun: RunDetailResponse | null =
    runDetail && currentRunId && runDetail.run_id === currentRunId
      ? runDetail
      : null;

  return (
    <div className="flex min-h-screen flex-col bg-gradient-to-b from-background via-background to-muted/30">
      <WorkbenchHeader backendOnline={backendOk} />
      <main className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-6 px-4 py-6 sm:px-6">
        {apiError ? (
          <p className="rounded-xl border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive">
            {apiError}
          </p>
        ) : null}

        <RunControls
          maxLeads={maxLeads}
          onMaxLeadsChange={setMaxLeads}
          useLlmQueries={useLlmQueries}
          onUseLlmQueries={setUseLlmQueries}
          useLlmActions={useLlmActions}
          onUseLlmActions={setUseLlmActions}
          outputFeishu={outputFeishu}
          onOutputFeishu={setOutputFeishu}
          onStart={handleStart}
          onRefreshRuns={loadRuns}
          starting={starting}
        />

        <FeishuTestPanel
          result={feishuTestResult}
          loading={feishuTesting}
          onTest={handleTestFeishu}
        />

        <CurrentRunSelector
          runs={runs}
          currentRunId={currentRunId}
          onChange={handleRunChange}
        />

        <RunStatusPanel run={displayRun} />

        <SummaryCards
          summary={displayRun?.summary}
          manualSearchHintCount={manualSearchCount}
        />

        <ResultToggle open={resultsOpen} onOpen={openResults} onClose={closeResults}>
          <div className="space-y-4">
            <LeadsTable rows={uiRows} selected={selected} onSelect={setSelected} />
            <LeadDetailPanel lead={selected} />
          </div>
        </ResultToggle>
      </main>
    </div>
  );
}
