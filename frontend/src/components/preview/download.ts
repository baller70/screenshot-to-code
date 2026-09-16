import { HTTP_BACKEND_URL } from "../../config";
import { normalizeBabelCdn } from "../../lib/babelCdn";

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

function downloadJson(payload: unknown, filename: string) {
  downloadBlob(
    new Blob([JSON.stringify(payload, null, 2)], {
      type: "application/json",
    }),
    filename
  );
}

function filenameFromContentDisposition(contentDisposition: string | null) {
  const match = contentDisposition?.match(/filename="?([^"]+)"?/i);
  return match?.[1] ?? "screenshot-to-code-export.zip";
}

export const downloadCode = async (code: string) => {
  try {
    const response = await fetch(`${HTTP_BACKEND_URL}/api/export`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        code,
        baseUrl: window.location.href,
      }),
    });

    if (!response.ok) {
      throw new Error(`Export failed with status ${response.status}`);
    }

    const blob = await response.blob();
    downloadBlob(
      blob,
      filenameFromContentDisposition(response.headers.get("Content-Disposition"))
    );
  } catch (error) {
    console.warn("Falling back to downloading index.html", error);
    downloadBlob(
      new Blob([normalizeBabelCdn(code)], { type: "text/html" }),
      "index.html"
    );
  }
};

export const downloadGeneratedApp = async (
  code: string,
  appName = "generated-website",
  backendAdapter = "fixture"
) => {
  const response = await fetch(`${HTTP_BACKEND_URL}/api/export/generated-app`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      code: normalizeBabelCdn(code),
      appName,
      backendAdapter,
    }),
  });

  if (!response.ok) {
    throw new Error(`Generated app export failed with status ${response.status}`);
  }

  const blob = await response.blob();
  downloadBlob(
    blob,
    filenameFromContentDisposition(response.headers.get("Content-Disposition"))
  );
};

export const downloadGeneratedAppReport = async (
  code: string,
  appName = "generated-website"
) => {
  const response = await fetch(`${HTTP_BACKEND_URL}/api/generated-app/repair-loop`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      code: normalizeBabelCdn(code),
      attempt: 1,
    }),
  });

  if (!response.ok) {
    throw new Error(`Generated app report failed with status ${response.status}`);
  }

  const report = await response.json();
  await fetch(`${HTTP_BACKEND_URL}/api/generated-app/history`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      appName,
      score: report.score ?? 0,
      shouldRepair: report.shouldRepair ?? true,
      summary: report.shouldRepair ? "Repair recommended" : "Ready",
      report,
    }),
  }).catch((error) => {
    console.warn("Could not save generated app report history", error);
  });

  downloadJson(report, "generated-app-report.json");
};
