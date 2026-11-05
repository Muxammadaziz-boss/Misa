// ========== workspaceService.ts ==========
// Misa AI v9.0.0 — Native Workspace & Autonomy Frontend Client
// Connects to local workspace endpoints at http://127.0.0.1:18420/api/workspace/*

import { backendService } from "./backendService";

const API_BASE = "http://127.0.0.1:18420";

export type WorkspaceMode = "observe" | "supervised" | "controlled_autonomy";

export interface WorkspaceConfig {
  workspace_id: string;
  name: string;
  root_path: string;
  permitted_paths: string[];
  mode: WorkspaceMode;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  settings?: Record<string, any>;
}

export interface FileItem {
  name: string;
  path: string;
  is_dir: boolean;
  size_bytes: number;
  modified_time: number;
  extension: string;
}

export interface CommandExecution {
  command_id: string;
  command: string;
  cwd: string;
  status: "started" | "running" | "completed" | "failed" | "cancelled" | "waiting_for_approval";
  exit_code?: number | null;
  stdout: string;
  stderr: string;
  started_at: number;
  completed_at?: number | null;
  duration_seconds: number;
  pid?: number | null;
  executed_by: string;
  error_message?: string | null;
}

export interface ProjectMap {
  root_path: string;
  primary_language: string;
  languages: Record<string, number>;
  frameworks: string[];
  entrypoints: string[];
  important_modules: string[];
  api_endpoints: string[];
  dependencies: Record<string, string>;
  test_framework?: string | null;
  build_system?: string | null;
  scanned_at: number;
}

export interface ActivityEvent {
  event_id: string;
  tool_name: string;
  operation: string;
  agent_id: string;
  status: "running" | "completed" | "failed" | "cancelled" | "waiting_for_approval";
  started_at: number;
  duration_seconds: number;
  output_preview: string;
  error?: string | null;
}

class WorkspaceService {
  public async getWorkspace(): Promise<{ active: WorkspaceConfig | null; list: WorkspaceConfig[] }> {
    try {
      const res = await fetch(`${API_BASE}/api/workspace`);
      if (!res.ok) return { active: null, list: [] };
      const json = await res.json();
      return {
        active: json.data?.active_workspace || null,
        list: json.data?.workspaces || [],
      };
    } catch {
      return { active: null, list: [] };
    }
  }

  public async connectWorkspace(path: string, name?: string, mode: WorkspaceMode = "supervised"): Promise<WorkspaceConfig | null> {
    try {
      const res = await fetch(`${API_BASE}/api/workspace/connect`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ path, name, mode }),
      });
      if (!res.ok) return null;
      const json = await res.json();
      return json.data || null;
    } catch {
      return null;
    }
  }

  public async disconnectWorkspace(workspaceId: string): Promise<boolean> {
    try {
      const res = await fetch(`${API_BASE}/api/workspace/disconnect`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ workspace_id: workspaceId }),
      });
      return res.ok;
    } catch {
      return false;
    }
  }

  public async selectWorkspace(workspaceId: string): Promise<boolean> {
    try {
      const res = await fetch(`${API_BASE}/api/workspace/select`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ workspace_id: workspaceId }),
      });
      return res.ok;
    } catch {
      return false;
    }
  }

  public async updateMode(workspaceId: string, mode: WorkspaceMode): Promise<WorkspaceConfig | null> {
    try {
      const res = await fetch(`${API_BASE}/api/workspace/mode`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ workspace_id: workspaceId, mode }),
      });
      if (!res.ok) return null;
      const json = await res.json();
      return json.data || null;
    } catch {
      return null;
    }
  }

  public async getTree(maxDepth: number = 3): Promise<string> {
    try {
      const res = await fetch(`${API_BASE}/api/workspace/tree?max_depth=${maxDepth}`);
      if (!res.ok) return "";
      const json = await res.json();
      return json.data?.tree || "";
    } catch {
      return "";
    }
  }

  public async getFiles(path: string = "", maxDepth: number = 1): Promise<FileItem[]> {
    try {
      const params = new URLSearchParams();
      if (path) params.set("path", path);
      params.set("max_depth", String(maxDepth));
      const res = await fetch(`${API_BASE}/api/workspace/files?${params.toString()}`);
      if (!res.ok) return [];
      const json = await res.json();
      return json.data || [];
    } catch {
      return [];
    }
  }

  public async readFile(path: string, startLine?: number, endLine?: number): Promise<any> {
    try {
      const params = new URLSearchParams({ path });
      if (startLine !== undefined) params.set("start_line", String(startLine));
      if (endLine !== undefined) params.set("end_line", String(endLine));
      const res = await fetch(`${API_BASE}/api/workspace/file/read?${params.toString()}`);
      if (!res.ok) throw new Error("HTTP " + res.status);
      const json = await res.json();
      return json.data;
    } catch (e: any) {
      return { content: `Error reading file: ${e?.message || e}`, path };
    }
  }

  public async createFile(path: string, content: string): Promise<any> {
    try {
      const res = await fetch(`${API_BASE}/api/workspace/file/create`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ path, content }),
      });
      return await res.json();
    } catch (e: any) {
      return { ok: false, error: e?.message };
    }
  }

  public async modifyFile(path: string, content: string): Promise<any> {
    try {
      const res = await fetch(`${API_BASE}/api/workspace/file/modify`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ path, content }),
      });
      return await res.json();
    } catch (e: any) {
      return { ok: false, error: e?.message };
    }
  }

  public async search(query: string, mode: "content" | "files" = "content"): Promise<any[]> {
    try {
      const params = new URLSearchParams({ query, mode });
      const res = await fetch(`${API_BASE}/api/workspace/search?${params.toString()}`);
      if (!res.ok) return [];
      const json = await res.json();
      return json.data || [];
    } catch {
      return [];
    }
  }

  public async runCommand(command: string, cwd?: string, timeout: number = 60): Promise<CommandExecution | null> {
    try {
      const res = await fetch(`${API_BASE}/api/workspace/command/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ command, cwd, timeout }),
      });
      const json = await res.json();
      return json.data || null;
    } catch {
      return null;
    }
  }

  public async getGitStatus(): Promise<any> {
    try {
      const res = await fetch(`${API_BASE}/api/workspace/git/status`);
      if (!res.ok) return null;
      const json = await res.json();
      return json.data || null;
    } catch {
      return null;
    }
  }

  public async getGitDiff(cached: boolean = false, filePath?: string): Promise<string> {
    try {
      const params = new URLSearchParams();
      if (cached) params.set("cached", "true");
      if (filePath) params.set("file_path", filePath);
      const res = await fetch(`${API_BASE}/api/workspace/git/diff?${params.toString()}`);
      if (!res.ok) return "";
      const json = await res.json();
      return json.data?.diff || "";
    } catch {
      return "";
    }
  }

  public async getProjectAnalysis(): Promise<ProjectMap | null> {
    try {
      const res = await fetch(`${API_BASE}/api/workspace/project/analysis`);
      if (!res.ok) return null;
      const json = await res.json();
      return json.data || null;
    } catch {
      return null;
    }
  }

  public async runTests(command?: string): Promise<CommandExecution | null> {
    try {
      const res = await fetch(`${API_BASE}/api/workspace/project/tests`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ command }),
      });
      const json = await res.json();
      return json.data || null;
    } catch {
      return null;
    }
  }

  public async runBuild(command?: string): Promise<CommandExecution | null> {
    try {
      const res = await fetch(`${API_BASE}/api/workspace/project/build`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ command }),
      });
      const json = await res.json();
      return json.data || null;
    } catch {
      return null;
    }
  }

  public async getRecentActivity(limit: number = 50): Promise<ActivityEvent[]> {
    try {
      const res = await fetch(`${API_BASE}/api/workspace/activity?limit=${limit}`);
      if (!res.ok) return [];
      const json = await res.json();
      return json.data || [];
    } catch {
      return [];
    }
  }

  public async executeAutonomousWorkflow(prompt: string): Promise<any> {
    try {
      const res = await fetch(`${API_BASE}/api/workspace/workflow/execute`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt }),
      });
      return await res.json();
    } catch (e: any) {
      return { ok: false, error: e?.message };
    }
  }

  public onActivity(callback: (act: ActivityEvent) => void): () => void {
    return backendService.subscribe((msg: any) => {
      if (msg && msg.type === "workspace_activity" && msg.data) {
        callback(msg.data);
      }
    });
  }
}

export const workspaceService = new WorkspaceService();
