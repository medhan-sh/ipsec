import React, { createContext, useContext, useReducer, useEffect, ReactNode } from "react";
import {
  CaptureItem,
  FindingsDocument,
  SystemStatus,
} from "../api/types";
import {
  fetchCaptures,
  fetchFindings,
  fetchStatus,
  runAnalyze,
  IS_MOCK_MODE,
} from "../api/client";

export type RunStatus = "idle" | "running" | "success" | "error";
export type DataSource = "real" | "mock";

export interface AppState {
  selectedCapture: string | null;
  runStatus: RunStatus;
  runError: string | null;
  loadedDocument: FindingsDocument | null;
  dataSource: DataSource;
  statusPayload: SystemStatus | null;
  captures: CaptureItem[];
  isLoadingCaptures: boolean;
  activeFilter: string;
}

type AppAction =
  | { type: "SET_SELECTED_CAPTURE"; payload: string | null }
  | { type: "SET_RUN_STATUS"; payload: { status: RunStatus; error?: string } }
  | { type: "SET_LOADED_DOCUMENT"; payload: { doc: FindingsDocument | null; source: DataSource } }
  | { type: "SET_STATUS_PAYLOAD"; payload: SystemStatus }
  | { type: "SET_CAPTURES"; payload: CaptureItem[] }
  | { type: "SET_LOADING_CAPTURES"; payload: boolean }
  | { type: "SET_ACTIVE_FILTER"; payload: string };

const initialState: AppState = {
  selectedCapture: null,
  runStatus: "idle",
  runError: null,
  loadedDocument: null,
  dataSource: IS_MOCK_MODE ? "mock" : "real",
  statusPayload: null,
  captures: [],
  isLoadingCaptures: false,
  activeFilter: "",
};

function appReducer(state: AppState, action: AppAction): AppState {
  switch (action.type) {
    case "SET_SELECTED_CAPTURE":
      return { ...state, selectedCapture: action.payload };
    case "SET_RUN_STATUS":
      return {
        ...state,
        runStatus: action.payload.status,
        runError: action.payload.error ?? null,
      };
    case "SET_LOADED_DOCUMENT":
      return {
        ...state,
        loadedDocument: action.payload.doc,
        dataSource: action.payload.source,
      };
    case "SET_STATUS_PAYLOAD":
      return { ...state, statusPayload: action.payload };
    case "SET_CAPTURES":
      return { ...state, captures: action.payload };
    case "SET_LOADING_CAPTURES":
      return { ...state, isLoadingCaptures: action.payload };
    case "SET_ACTIVE_FILTER":
      return { ...state, activeFilter: action.payload };
    default:
      return state;
  }
}

interface AppContextValue {
  state: AppState;
  selectCapture: (name: string | null) => Promise<void>;
  refreshCaptures: () => Promise<void>;
  analyzeSelected: () => Promise<void>;
  setFilter: (query: string) => void;
  loadSampleData: () => void;
}

const AppContext = createContext<AppContextValue | null>(null);

export const AppProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [state, dispatch] = useReducer(appReducer, initialState);

  const refreshCaptures = async () => {
    dispatch({ type: "SET_LOADING_CAPTURES", payload: true });
    try {
      const { data } = await fetchCaptures();
      dispatch({ type: "SET_CAPTURES", payload: data });
    } catch (e) {
      console.error("[Umbra Store] Failed to refresh captures:", e);
    } finally {
      dispatch({ type: "SET_LOADING_CAPTURES", payload: false });
    }
  };

  const selectCapture = async (name: string | null) => {
    dispatch({ type: "SET_SELECTED_CAPTURE", payload: name });
    if (!name) {
      dispatch({ type: "SET_LOADED_DOCUMENT", payload: { doc: null, source: state.dataSource } });
      return;
    }

    try {
      const { data, source } = await fetchFindings(name);
      dispatch({ type: "SET_LOADED_DOCUMENT", payload: { doc: data, source } });
    } catch (e) {
      // Capture may not be analyzed yet
      dispatch({ type: "SET_LOADED_DOCUMENT", payload: { doc: null, source: state.dataSource } });
    }
  };

  const analyzeSelected = async () => {
    if (!state.selectedCapture) return;
    dispatch({ type: "SET_RUN_STATUS", payload: { status: "running" } });
    try {
      const res = await runAnalyze(state.selectedCapture);
      if (res.findings) {
        dispatch({
          type: "SET_LOADED_DOCUMENT",
          payload: { doc: res.findings, source: res.source },
        });
      }
      dispatch({ type: "SET_RUN_STATUS", payload: { status: "success" } });
      await refreshCaptures();
    } catch (e: any) {
      dispatch({
        type: "SET_RUN_STATUS",
        payload: { status: "error", error: e.message || "Analysis failed" },
      });
    }
  };

  const setFilter = (query: string) => {
    dispatch({ type: "SET_ACTIVE_FILTER", payload: query });
  };

  const loadSampleData = async () => {
    await selectCapture("corp_perimeter_eval_2026.pcapng");
  };

  useEffect(() => {
    fetchStatus()
      .then(({ data }) => dispatch({ type: "SET_STATUS_PAYLOAD", payload: data }))
      .catch((err) => console.warn("[Umbra Store] Initial status fetch failed:", err));

    refreshCaptures();
  }, []);

  return (
    <AppContext.Provider
      value={{
        state,
        selectCapture,
        refreshCaptures,
        analyzeSelected,
        setFilter,
        loadSampleData,
      }}
    >
      {children}
    </AppContext.Provider>
  );
};

export function useAppStore(): AppContextValue {
  const ctx = useContext(AppContext);
  if (!ctx) {
    throw new Error("useAppStore must be used within an AppProvider");
  }
  return ctx;
}
