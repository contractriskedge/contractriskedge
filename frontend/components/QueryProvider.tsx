/**
 * TanStack Query Provider — global configuration for all async state management.
 *
 * Features:
 * - Global retry policy with exponential backoff
 * - Stale-while-revalidate by default
 * - Network status tracking for stale-state recovery
 * - Background tab throttling (reduces polling when tab is hidden)
 * - RefetchOnFocus burst protection (debounced refocus handler)
 * - DevTools in development mode
 * - QueryClient with sensible defaults for async workflows
 *
 * Place this at the root of your app, wrapping all components that use hooks.
 *
 * Usage:
 *   // app/layout.tsx
 *   import { QueryProvider } from '@/components/QueryProvider';
 *
 *   export default function RootLayout({ children }) {
 *     return <QueryProvider>{children}</QueryProvider>;
 *   }
 */

"use client";

import React, { useState, useRef, useEffect } from "react";
import {
  QueryClient,
  QueryClientProvider,
  onlineManager,
  focusManager,
} from "@tanstack/react-query";
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";

// ── Configure online manager for stale-state recovery ──
// When the browser comes back online, automatically refetch all active queries
if (typeof window !== "undefined") {
  onlineManager.setEventListener((setOnline) => {
    const handleOnline = () => setOnline(true);
    const handleOffline = () => setOnline(false);

    window.addEventListener("online", handleOnline);
    window.addEventListener("offline", handleOffline);

    return () => {
      window.removeEventListener("online", handleOnline);
      window.removeEventListener("offline", handleOffline);
    };
  });

  // ── Background Tab Throttling ──────────────────────────────────
  //
  // When the tab is hidden (user switched to another tab), we mark
  // the focus as "offline" which pauses refetchOnWindowFocus and
  // refetchInterval (polling). When the tab becomes visible again,
  // we restore focus. This prevents:
  //
  // - 20+ tabs all polling simultaneously
  // - Burst of API calls on tab focus (refetch storm)
  // - Unnecessary network usage when user isn't looking
  //
  // Implementation uses a debounce on focus to prevent the "all
  // queries refetch at once" storm when returning to the tab.
  let focusDebounceTimer: ReturnType<typeof setTimeout> | null = null;

  focusManager.setEventListener((handleFocus) => {
    const handleVisibility = () => {
      if (document.hidden) {
        // Tab hidden → mark as unfocused (pauses polling + refetchOnFocus)
        handleFocus(false);
      } else {
        // Tab visible → debounce focus to prevent refetch storm
        if (focusDebounceTimer) clearTimeout(focusDebounceTimer);
        focusDebounceTimer = setTimeout(() => {
          handleFocus(true);
        }, 2000); // 2-second debounce — allows all queries to settle
      }
    };

    // Also handle window focus directly (user clicks back to the tab)
    const handleWindowFocus = () => {
      if (!document.hidden) {
        if (focusDebounceTimer) clearTimeout(focusDebounceTimer);
        focusDebounceTimer = setTimeout(() => {
          handleFocus(true);
        }, 2000);
      }
    };

    document.addEventListener("visibilitychange", handleVisibility);
    window.addEventListener("focus", handleWindowFocus);

    return () => {
      document.removeEventListener("visibilitychange", handleVisibility);
      window.removeEventListener("focus", handleWindowFocus);
      if (focusDebounceTimer) clearTimeout(focusDebounceTimer);
    };
  });
}

function makeQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        // ── Stale-while-revalidate ──
        // Data is considered fresh for 30s by default
        staleTime: 30 * 1000,
        // Keep data in cache for 5 minutes after last observer detaches
        gcTime: 5 * 60 * 1000,
        // Refetch when window regains focus (catches stale data)
        // Focus manager handles debouncing to prevent refetch storms
        refetchOnWindowFocus: true,
        // Refetch when network reconnects (stale-state recovery)
        refetchOnReconnect: true,
        // Don't refetch on mount if data is within staleTime
        refetchOnMount: true,
        // Retry failed queries with exponential backoff
        retry: (failureCount, error) => {
          // Don't retry 4xx errors (client errors)
          if (error instanceof Error && error.message.includes("4")) {
            // Be more specific: check status codes
            const statusMatch = error.message.match(/\b(4\d\d)\b/);
            if (statusMatch) {
              const status = parseInt(statusMatch[1], 10);
              if (status >= 400 && status < 500 && status !== 429) {
                return false; // Don't retry client errors (except 429)
              }
            }
          }
          // Retry up to 3 times for server errors
          return failureCount < 3;
        },
        // Exponential backoff: 1s, 2s, 4s
        retryDelay: (attemptIndex) =>
          Math.min(1000 * 2 ** attemptIndex, 10_000),
      },
      mutations: {
        retry: 1, // Mutations get one retry attempt
        retryDelay: 1000,
      },
    },
  });
}

let browserQueryClient: QueryClient | undefined;

function getQueryClient(): QueryClient {
  if (typeof window === "undefined") {
    // Server: always create a new QueryClient
    return makeQueryClient();
  }
  // Browser: reuse the same QueryClient across renders
  if (!browserQueryClient) {
    browserQueryClient = makeQueryClient();
  }
  return browserQueryClient;
}

interface QueryProviderProps {
  children: React.ReactNode;
}

export function QueryProvider({ children }: QueryProviderProps) {
  const [queryClient] = useState(getQueryClient);

  return (
    <QueryClientProvider client={queryClient}>
      {children}
      {process.env.NODE_ENV === "development" && (
        <ReactQueryDevtools initialIsOpen={false} />
      )}
    </QueryClientProvider>
  );
}
