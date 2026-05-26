/**
 * ErrorBoundary — catches React rendering errors and logs them with structured context.
 *
 * Features:
 * - Catches unhandled render errors
 * - Logs error with component stack and timestamp
 * - Shows user-friendly fallback UI
 * - Supports retry
 * - Tracks error frequency for alerting
 *
 * Usage:
 *   <ErrorBoundary>
 *     <ReviewWorkspace reviewId="..." />
 *   </ErrorBoundary>
 */

"use client";

import React from "react";
import { AlertTriangle, RefreshCw } from "lucide-react";

interface ErrorBoundaryProps {
  children: React.ReactNode;
  fallback?: React.ReactNode;
  onError?: (error: Error, errorInfo: React.ErrorInfo) => void;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
  errorInfo: React.ErrorInfo | null;
}

export class ErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error: Error): Partial<ErrorBoundaryState> {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo): void {
    this.setState({ errorInfo });

    // Structured error logging
    const errorPayload = {
      type: "react_render_error",
      error: {
        name: error.name,
        message: error.message,
        stack: error.stack?.split("\n").slice(0, 5).join("\n"),
      },
      componentStack: errorInfo.componentStack?.split("\n").slice(0, 5).join("\n"),
      timestamp: new Date().toISOString(),
      url: typeof window !== "undefined" ? window.location.href : "",
      userAgent: typeof navigator !== "undefined" ? navigator.userAgent : "",
    };

    // Log to console with structured format
    console.error("[ErrorBoundary]", JSON.stringify(errorPayload, null, 2));

    // Call custom onError handler
    this.props.onError?.(error, errorInfo);

    // Could send to external error tracking here
    // e.g., Sentry.captureException(error, { extra: errorPayload });
  }

  handleRetry = () => {
    this.setState({ hasError: false, error: null, errorInfo: null });
  };

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div className="flex min-h-[400px] items-center justify-center">
          <div className="mx-auto max-w-md text-center">
            <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-red-100 dark:bg-red-900/30">
              <AlertTriangle className="h-6 w-6 text-red-600 dark:text-red-400" />
            </div>
            <h3 className="mb-2 text-lg font-semibold text-gray-900 dark:text-gray-100">
              Something went wrong
            </h3>
            <p className="mb-1 text-sm text-gray-500 dark:text-gray-400">
              An unexpected error occurred while rendering this section.
            </p>
            {process.env.NODE_ENV === "development" && this.state.error && (
              <details className="mb-4 text-left">
                <summary className="cursor-pointer text-xs text-gray-400 hover:text-gray-600 dark:hover:text-gray-300">
                  Error details
                </summary>
                <pre className="mt-2 max-h-32 overflow-auto rounded bg-gray-100 p-2 text-xs text-red-600 dark:bg-gray-800 dark:text-red-400">
                  {this.state.error.name}: {this.state.error.message}
                  {"\n"}
                  {this.state.errorInfo?.componentStack}
                </pre>
              </details>
            )}
            <button
              onClick={this.handleRetry}
              className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 dark:focus:ring-offset-gray-900"
            >
              <RefreshCw className="h-4 w-4" />
              Try Again
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

/**
 * useErrorHandler — hook for catching async errors in components.
 *
 * Usage:
 *   const { error, handleError, clearError } = useErrorHandler();
 *
 *   try {
 *     await riskyOperation();
 *   } catch (err) {
 *     handleError(err);
 *   }
 */
export function useErrorHandler() {
  const [error, setError] = React.useState<Error | null>(null);

  const handleError = React.useCallback((err: unknown) => {
    const error = err instanceof Error ? err : new Error(String(err));
    setError(error);

    console.error("[useErrorHandler]", JSON.stringify({
      type: "async_error",
      error: { name: error.name, message: error.message },
      timestamp: new Date().toISOString(),
    }));
  }, []);

  const clearError = React.useCallback(() => setError(null), []);

  return { error, handleError, clearError };
}
