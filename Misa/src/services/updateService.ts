// ========== updateService.ts ==========
// Misa AI v9.0.0 — Desktop Auto-Update Client Service
// Interacts with backend update routes: /api/updates/*

const DEFAULT_API_URL = "http://127.0.0.1:18420";
const API_BASE = (import.meta.env.VITE_API_URL || DEFAULT_API_URL).replace(/\/$/, "");

export type UpdateState =
  | "IDLE"
  | "CHECKING"
  | "UPDATE_AVAILABLE"
  | "UP_TO_DATE"
  | "DOWNLOADING"
  | "VERIFYING"
  | "STAGING"
  | "INSTALLING"
  | "RESTARTING"
  | "SUCCESS"
  | "FAILED"
  | "CANCELLED"
  | "ROLLED_BACK";

export interface UpdateArtifact {
  name: string;
  size_bytes: number;
  size_mb: number;
  sha256: string;
  signature: string;
  url: string;
}

export interface UpdateCheckResponse {
  ok?: boolean;
  update_available: boolean;
  current_version: string;
  target_version?: string;
  release_date?: string;
  mandatory?: boolean;
  minimum_supported_version?: string;
  release_notes?: string[];
  artifacts?: UpdateArtifact[];
  reason?: string;
  error?: string;
}

export interface UpdateStatusResponse {
  ok: boolean;
  state: UpdateState;
  data: {
    state: UpdateState;
    current_version?: string;
    target_version?: string;
    artifact_name?: string;
    download_progress?: number;
    updated_at?: number;
    error?: string;
    backup_path?: string;
  };
  audits: Array<{
    event: string;
    timestamp: number;
    details: Record<string, any>;
  }>;
}

export class UpdateService {
  public static async checkForUpdates(force: boolean = false, channel?: string): Promise<UpdateCheckResponse> {
    try {
      const params = new URLSearchParams();
      if (force) params.append("force", "true");
      if (channel) params.append("channel", channel);

      const res = await fetch(`${API_BASE}/api/updates/check?${params.toString()}`, {
        method: "GET",
        headers: { "Content-Type": "application/json" },
      });
      if (!res.ok) {
        return {
          update_available: false,
          current_version: "9.0.1",
          error: `Server javobi: HTTP ${res.status}`,
        };
      }
      return await res.json();
    } catch (e: any) {
      return {
        update_available: false,
        current_version: "9.0.1",
        error: e.message || String(e),
      };
    }
  }

  public static async getStatus(): Promise<UpdateStatusResponse | null> {
    try {
      const res = await fetch(`${API_BASE}/api/updates/status`, {
        method: "GET",
        headers: { "Content-Type": "application/json" },
      });
      if (!res.ok) return null;
      return await res.json();
    } catch {
      return null;
    }
  }

  public static async startDownload(artifact?: UpdateArtifact): Promise<{ ok: boolean; error?: string }> {
    try {
      const body = artifact ? { artifact } : {};
      const res = await fetch(`${API_BASE}/api/updates/download`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      return await res.json();
    } catch (e: any) {
      return { ok: false, error: e.message || String(e) };
    }
  }

  public static async applyUpdate(): Promise<{ ok: boolean; message?: string; error?: string }> {
    try {
      const res = await fetch(`${API_BASE}/api/updates/apply`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      });
      return await res.json();
    } catch (e: any) {
      return { ok: false, error: e.message || String(e) };
    }
  }

  public static async rollback(): Promise<{ ok: boolean; message?: string; error?: string }> {
    try {
      const res = await fetch(`${API_BASE}/api/updates/rollback`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      });
      return await res.json();
    } catch (e: any) {
      return { ok: false, error: e.message || String(e) };
    }
  }
}
