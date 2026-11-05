// ========== multiAgentService.ts ==========
// Misa AI v9.0.0 — Native Multi-Agent Frontend Connector & Types
// Connects to native multi-agent endpoints at http://127.0.0.1:18420/api/multi-agent/*

import { backendService } from "./backendService";

const API_BASE = "http://127.0.0.1:18420";

export interface ModelPreference {
  tier: string;
  preferred_model?: string | null;
  fallback_enabled: boolean;
  temperature: number;
  max_tokens: number;
}

export interface PermissionProfile {
  category: "read" | "analyze" | "write" | "execute" | "admin";
  allowed_tools: string[];
  denied_tools: string[];
  requires_approval: boolean;
  read_only: boolean;
  allowed_paths: string[];
  can_delegate: boolean;
}

export interface ContextPolicy {
  max_context_tokens: number;
  include_user_profile: boolean;
  include_project_memory: boolean;
  shared_context_access: boolean;
  isolated_scratchpad: boolean;
}

export interface MemoryPolicy {
  retention_days: number;
  persist_history: boolean;
  private_memory: boolean;
  max_stored_tasks: number;
}

export interface ExecutionLimits {
  timeout_seconds: number;
  max_tokens: number;
  max_retries: number;
  max_delegation_depth: number;
  cost_budget_usd: number;
}

export interface MultiAgentAgent {
  agent_id: string;
  name: string;
  description: string;
  role: string;
  department: string;
  system_instructions: string;
  capabilities: string[];
  available_tools: string[];
  model_preference: ModelPreference;
  permission_profile: PermissionProfile;
  context_policy: ContextPolicy;
  memory_policy: MemoryPolicy;
  execution_limits: ExecutionLimits;
  status: "active" | "idle" | "busy" | "disabled" | "error";
  version: string;
  is_builtin: boolean;
  created_at: string;
  updated_at: string;
}

export interface MultiAgentTask {
  task_id: string;
  parent_task_id?: string | null;
  root_task_id?: string | null;
  title: string;
  description: string;
  assigned_agent_id: string;
  status: "pending" | "queued" | "running" | "reviewing" | "completed" | "failed" | "cancelled" | "waiting_for_approval" | "blocked";
  dependencies: string[];
  input_context?: Record<string, any>;
  output_result?: Record<string, any> | null;
  error_message?: string | null;
  depth: number;
  created_at: number;
  started_at?: number | null;
  completed_at?: number | null;
  tokens_used: number;
  cost_usd: number;
  requires_approval: boolean;
  approval_token?: string | null;
}

export interface MultiAgentOverview {
  total_agents: number;
  active_agents: number;
  disabled_agents: number;
  error_agents: number;
  departments: string[];
  total_capabilities: number;
  telemetry: {
    total_runs: number;
    total_tasks: number;
    completed_tasks: number;
    failed_tasks: number;
    cancelled_tasks: number;
    total_tokens: number;
    overall_success_rate: number;
    recent_runs: any[];
    agent_metrics: Record<string, any>;
  };
}

export interface MultiAgentMessage {
  message_id: string;
  conversation_id: string;
  task_id: string;
  sender_agent: string;
  recipient_agent: string;
  message_type: string;
  payload: Record<string, any>;
  correlation_id: string;
  timestamp: number;
}

export interface MultiAgentApproval {
  token: string;
  agent_id: string;
  agent_name: string;
  tool_name: string;
  arguments: Record<string, any>;
  created_at: number;
  expires_at: number;
  is_destructive: boolean;
}

export interface MultiAgentAuditRecord {
  timestamp: number;
  time_iso: string;
  agent_id: string;
  tool_name: string;
  arguments: Record<string, any>;
  allowed: boolean;
  reason: string;
  token?: string | null;
}

class MultiAgentService {
  public async getOverview(): Promise<MultiAgentOverview | null> {
    try {
      const res = await fetch(`${API_BASE}/api/multi-agent/overview`);
      if (!res.ok) return null;
      const json = await res.json();
      return json.ok ? json.data : null;
    } catch {
      return null;
    }
  }

  public async getAgents(department?: string, status?: string): Promise<MultiAgentAgent[]> {
    try {
      const params = new URLSearchParams();
      if (department) params.set("department", department);
      if (status) params.set("status", status);
      const url = `${API_BASE}/api/multi-agent/agents${params.toString() ? `?${params.toString()}` : ""}`;
      const res = await fetch(url);
      if (!res.ok) return [];
      const json = await res.json();
      return json.ok ? json.data : [];
    } catch {
      return [];
    }
  }

  public async getAgent(agentId: string): Promise<MultiAgentAgent | null> {
    try {
      const res = await fetch(`${API_BASE}/api/multi-agent/agents/${encodeURIComponent(agentId)}`);
      if (!res.ok) return null;
      const json = await res.json();
      return json.ok ? json.data : null;
    } catch {
      return null;
    }
  }

  public async updateAgent(agentId: string, updates: Partial<MultiAgentAgent>): Promise<MultiAgentAgent | null> {
    try {
      const res = await fetch(`${API_BASE}/api/multi-agent/agents/${encodeURIComponent(agentId)}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(updates),
      });
      if (!res.ok) return null;
      const json = await res.json();
      return json.ok ? json.data : null;
    } catch {
      return null;
    }
  }

  public async enableAgent(agentId: string): Promise<boolean> {
    try {
      const res = await fetch(`${API_BASE}/api/multi-agent/agents/${encodeURIComponent(agentId)}/enable`, {
        method: "POST",
      });
      return res.ok;
    } catch {
      return false;
    }
  }

  public async disableAgent(agentId: string): Promise<boolean> {
    try {
      const res = await fetch(`${API_BASE}/api/multi-agent/agents/${encodeURIComponent(agentId)}/disable`, {
        method: "POST",
      });
      return res.ok;
    } catch {
      return false;
    }
  }

  public async planGoal(query: string, context?: any): Promise<{ tasks: MultiAgentTask[]; agents_involved: string[] } | null> {
    try {
      const res = await fetch(`${API_BASE}/api/multi-agent/plan`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query, context }),
      });
      if (!res.ok) return null;
      const json = await res.json();
      return json.ok ? json.data : null;
    } catch {
      return null;
    }
  }

  public async executeGoal(query: string, context?: any): Promise<any> {
    try {
      const res = await fetch(`${API_BASE}/api/multi-agent/execute`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query, context }),
      });
      if (!res.ok) throw new Error("HTTP " + res.status);
      return await res.json();
    } catch (e: any) {
      return { ok: false, error: e?.message || "Multi-Agent execution failed." };
    }
  }

  public async cancelRun(runId: string): Promise<boolean> {
    try {
      const res = await fetch(`${API_BASE}/api/multi-agent/cancel`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ run_id: runId }),
      });
      return res.ok;
    } catch {
      return false;
    }
  }

  public async getMessages(conversationId?: string, taskId?: string): Promise<MultiAgentMessage[]> {
    try {
      const params = new URLSearchParams();
      if (conversationId) params.set("conversation_id", conversationId);
      if (taskId) params.set("task_id", taskId);
      const url = `${API_BASE}/api/multi-agent/messages${params.toString() ? `?${params.toString()}` : ""}`;
      const res = await fetch(url);
      if (!res.ok) return [];
      const json = await res.json();
      return json.ok ? json.data : [];
    } catch {
      return [];
    }
  }

  public async getApprovals(): Promise<MultiAgentApproval[]> {
    try {
      const res = await fetch(`${API_BASE}/api/multi-agent/approvals`);
      if (!res.ok) return [];
      const json = await res.json();
      return json.ok ? json.data : [];
    } catch {
      return [];
    }
  }

  public async approveOperation(token: string): Promise<{ ok: boolean; message: string }> {
    try {
      const res = await fetch(`${API_BASE}/api/multi-agent/approvals/${encodeURIComponent(token)}/approve`, {
        method: "POST",
      });
      const json = await res.json();
      return { ok: res.ok && json.ok, message: json.message || "Approved" };
    } catch (e: any) {
      return { ok: false, message: e.message };
    }
  }

  public async rejectOperation(token: string, reason?: string): Promise<{ ok: boolean; message: string }> {
    try {
      const res = await fetch(`${API_BASE}/api/multi-agent/approvals/${encodeURIComponent(token)}/reject`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ reason: reason || "Declined by user" }),
      });
      const json = await res.json();
      return { ok: res.ok && json.ok, message: json.message || "Rejected" };
    } catch (e: any) {
      return { ok: false, message: e.message };
    }
  }

  public async getAudit(limit: number = 100): Promise<MultiAgentAuditRecord[]> {
    try {
      const res = await fetch(`${API_BASE}/api/multi-agent/audit?limit=${limit}`);
      if (!res.ok) return [];
      const json = await res.json();
      return json.ok ? json.data : [];
    } catch {
      return [];
    }
  }

  public onEvent(callback: (event: any) => void): () => void {
    return backendService.subscribe((msg: any) => {
      if (msg && msg.type === "multi_agent_event" && msg.data) {
        callback(msg.data);
      }
    });
  }
}

export const multiAgentService = new MultiAgentService();
