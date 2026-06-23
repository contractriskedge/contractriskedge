"use client";

import { useQuery } from "@tanstack/react-query";
import type { SignatureRequest, SignatureStatus } from "../types";

// TODO: Replace with actual API client
const API_BASE = "/api/v1/signatures";

async function fetchSignatureRequests(status?: SignatureStatus): Promise<{ data: SignatureRequest[]; total: number }> {
  const params = new URLSearchParams();
  if (status) params.set("status", status);
  const qs = params.toString();
  const res = await fetch(`${API_BASE}${qs ? `?${qs}` : ""}`);
  if (!res.ok) throw new Error("Failed to fetch signature requests");
  return res.json();
}

async function fetchSignatureRequest(id: string): Promise<SignatureRequest> {
  const res = await fetch(`${API_BASE}/${id}`);
  if (!res.ok) throw new Error("Failed to fetch signature request");
  return res.json();
}

export function useSignatureRequests(status?: SignatureStatus) {
  return useQuery({
    queryKey: ["signature-requests", status],
    queryFn: () => fetchSignatureRequests(status),
    staleTime: 30_000,
  });
}

export function useSignatureRequest(id: string | null) {
  return useQuery({
    queryKey: ["signature-request", id],
    queryFn: () => fetchSignatureRequest(id!),
    enabled: !!id,
    staleTime: 15_000,
  });
}
