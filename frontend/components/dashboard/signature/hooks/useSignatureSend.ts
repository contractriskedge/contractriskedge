"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

// TODO: Replace with actual API client
const API_BASE = "/api/v1/signatures";

interface SendForSignatureData {
  emailSubject?: string;
  emailBody?: string;
}

export function useSignatureSend(requestId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: SendForSignatureData) => {
      const res = await fetch(`${API_BASE}/${requestId}/send`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      });
      if (!res.ok) throw new Error("Failed to send for signature");
      return res.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["signature-requests"] });
      queryClient.invalidateQueries({ queryKey: ["signature-request", requestId] });
    },
  });
}

export function useSignatureVoid(requestId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (reason: string) => {
      const res = await fetch(`${API_BASE}/${requestId}/void`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ reason }),
      });
      if (!res.ok) throw new Error("Failed to void signature request");
      return res.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["signature-requests"] });
      queryClient.invalidateQueries({ queryKey: ["signature-request", requestId] });
    },
  });
}
