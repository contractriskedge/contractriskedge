/**
 * Obligation Helpers API service — search endpoints for the Create Obligation modal dropdowns.
 *
 * Provides searchable lookups for:
 * - Clause references (from clause_library + recent usage)
 * - Users (from admin_users)
 * - Departments (from admin_users + obligations)
 * - Business units (from admin_users + obligations)
 */

"use client";

import { api } from "@/services/api/client";

// ── Clause Reference ──────────────────────────────────────────────

export interface ClauseReferenceItem {
  id: string;
  type: "clause_library" | "recent";
  label: string;
  detail: string;
  value: string;
}

export interface ClauseReferenceResponse {
  data: ClauseReferenceItem[];
  total: number;
}

export async function searchClauseReferences(q?: string): Promise<ClauseReferenceResponse> {
  const searchParams = new URLSearchParams();
  if (q) searchParams.set("q", q);
  const qs = searchParams.toString();
  return api.get<ClauseReferenceResponse>(`/obligation-helpers/clause-references${qs ? `?${qs}` : ""}`);
}

// ── Users ─────────────────────────────────────────────────────────

export interface UserItem {
  id: string;
  name: string;
  email: string;
  role: string;
  department: string | null;
  business_unit: string | null;
}

export interface UserResponse {
  data: UserItem[];
  total: number;
}

export async function searchUsers(q?: string): Promise<UserResponse> {
  const searchParams = new URLSearchParams();
  if (q) searchParams.set("q", q);
  const qs = searchParams.toString();
  return api.get<UserResponse>(`/obligation-helpers/users${qs ? `?${qs}` : ""}`);
}

// ── Departments ───────────────────────────────────────────────────

export interface SelectOption {
  value: string;
  label: string;
  source: string;
}

export interface SelectOptionResponse {
  data: SelectOption[];
  total: number;
}

export async function searchDepartments(q?: string): Promise<SelectOptionResponse> {
  const searchParams = new URLSearchParams();
  if (q) searchParams.set("q", q);
  const qs = searchParams.toString();
  return api.get<SelectOptionResponse>(`/obligation-helpers/departments${qs ? `?${qs}` : ""}`);
}

// ── Business Units ────────────────────────────────────────────────

export async function searchBusinessUnits(q?: string): Promise<SelectOptionResponse> {
  const searchParams = new URLSearchParams();
  if (q) searchParams.set("q", q);
  const qs = searchParams.toString();
  return api.get<SelectOptionResponse>(`/obligation-helpers/business-units${qs ? `?${qs}` : ""}`);
}
