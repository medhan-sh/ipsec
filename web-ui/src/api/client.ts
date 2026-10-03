import {
  CaptureItem,
  FindingsDocument,
  SystemStatus,
} from "./types";
import goldenMock from "../mocks/golden.mock.json";
import richMock from "../mocks/rich.mock.json";
import emptyMock from "../mocks/empty.mock.json";

export const IS_MOCK_MODE = import.meta.env.VITE_USE_MOCKS === "1";

export interface ApiResponse<T> {
  data: T;
  source: "real" | "mock";
}

export async function fetchStatus(): Promise<ApiResponse<SystemStatus>> {
  if (IS_MOCK_MODE) {
    return {
      data: {
        analyzer: "0.1.0",
        analyzer_version: "0.1.0",
        tshark: {
          available: true,
          version: "4.4.18",
          error: null,
        },
        rules: 15,
        rules_count: 15,
        captures: 3,
        captures_count: 3,
        network: "none",
      },
      source: "mock",
    };
  }

  const res = await fetch("/api/status");
  if (!res.ok) {
    throw new Error(`Failed to fetch status: HTTP ${res.status}`);
  }
  const data = await res.json();
  return { data, source: "real" };
}

export async function fetchCaptures(): Promise<ApiResponse<CaptureItem[]>> {
  if (IS_MOCK_MODE) {
    return {
      data: [
        {
          name: "corp_perimeter_eval_2026.pcapng",
          size: 1462272,
          modified: new Date(Date.now() - 3600000).toISOString(),
          has_findings: true,
          has_report: true,
          severity_counts: {
            critical: 1,
            high: 4,
            medium: 4,
            low: 2,
            info: 1,
          },
        },
        {
          name: "golden_fixture.pcap",
          size: 524288,
          modified: new Date(Date.now() - 86400000).toISOString(),
          has_findings: true,
          has_report: true,
          severity_counts: {
            critical: 0,
            high: 0,
            medium: 0,
            low: 0,
            info: 0,
          },
        },
        {
          name: "empty_sample.pcap",
          size: 1024,
          modified: new Date(Date.now() - 172800000).toISOString(),
          has_findings: false,
          has_report: false,
          severity_counts: {
            critical: 0,
            high: 0,
            medium: 0,
            low: 0,
            info: 0,
          },
        },
      ],
      source: "mock",
    };
  }

  const res = await fetch("/api/captures");
  if (!res.ok) {
    throw new Error(`Failed to fetch captures: HTTP ${res.status}`);
  }
  const data = await res.json();
  return { data, source: "real" };
}

export async function fetchFindings(captureName: string): Promise<ApiResponse<FindingsDocument>> {
  if (IS_MOCK_MODE) {
    if (captureName.includes("golden")) {
      return { data: goldenMock as unknown as FindingsDocument, source: "mock" };
    }
    if (captureName.includes("empty")) {
      return { data: emptyMock as unknown as FindingsDocument, source: "mock" };
    }
    return { data: richMock as unknown as FindingsDocument, source: "mock" };
  }

  const res = await fetch(`/api/findings/${encodeURIComponent(captureName)}`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ message: `HTTP ${res.status}` }));
    throw new Error(err.message || `Findings not found for ${captureName}`);
  }
  const data = await res.json();
  return { data, source: "real" };
}

export async function runAnalyze(captureName: string): Promise<{
  success: boolean;
  duration: number;
  findings?: FindingsDocument;
  message?: string;
  source: "real" | "mock";
}> {
  if (IS_MOCK_MODE) {
    // Simulate brief synchronous delay matching instrument feel
    await new Promise((r) => setTimeout(r, 600));
    return {
      success: true,
      duration: 1.84,
      findings: richMock as unknown as FindingsDocument,
      source: "mock",
    };
  }

  const res = await fetch("/api/analyze", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ capture: captureName }),
  });

  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.message || `Analysis failed: HTTP ${res.status}`);
  }
  return { ...data, source: "real" };
}

export async function uploadCapture(
  file: File,
  overwrite: boolean = false
): Promise<{ message: string; name: string; size: number }> {
  const url = `/api/upload?name=${encodeURIComponent(file.name)}${overwrite ? "&overwrite=1" : ""}`;
  const res = await fetch(url, {
    method: "PUT",
    headers: {
      "Content-Length": String(file.size),
    },
    body: file,
  });

  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.message || `Upload failed: HTTP ${res.status}`);
  }
  return data;
}
