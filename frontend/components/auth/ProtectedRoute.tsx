/**
 * ProtectedRoute — Route guard that checks user permissions before rendering children.
 *
 * If the user lacks the required permission:
 *   - Shows an "Access Denied" message with the missing permission name
 *   - Does NOT redirect (avoids flash-of-wrong-content)
 *
 * Usage:
 *   <ProtectedRoute permission="contracts:read">
 *     <ReviewDashboard />
 *   </ProtectedRoute>
 *
 *   <ProtectedRoute permission={["contracts:read", "workflows:read"]} requireAll={false}>
 *     <ReviewQueue />
 *   </ProtectedRoute>
 */

"use client";

import React from "react";
import { ShieldAlert, Lock } from "lucide-react";
import { useAuth } from "@/components/auth/AuthProvider";

interface ProtectedRouteProps {
  /** Single permission or array of permissions to check */
  permission: string | string[];
  /** If true (default), ALL permissions in the array must be present. If false, ANY is sufficient. */
  requireAll?: boolean;
  /** Optional fallback content when permission is denied. Defaults to Access Denied message. */
  fallback?: React.ReactNode;
  children: React.ReactNode;
}

export function ProtectedRoute({
  permission,
  requireAll = true,
  fallback,
  children,
}: ProtectedRouteProps) {
  const { hasPermission, isLoading } = useAuth();

  // During loading, show nothing to avoid flash
  if (isLoading) return null;

  const permissions = Array.isArray(permission) ? permission : [permission];
  const hasAccess = requireAll
    ? permissions.every((p) => hasPermission(p))
    : permissions.some((p) => hasPermission(p));

  if (!hasAccess) {
    if (fallback) return <>{fallback}</>;

    return (
      <div className="flex flex-col items-center justify-center py-20">
        <div className="w-16 h-16 rounded-2xl bg-amber-50 dark:bg-amber-900/20 flex items-center justify-center mb-4">
          <Lock className="w-8 h-8 text-amber-500" />
        </div>
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
          Access Denied
        </h2>
        <p className="text-sm text-gray-500 dark:text-gray-400 text-center max-w-md mb-4">
          You do not have the required permissions to access this section.
        </p>
        <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-gray-100 dark:bg-gray-800 text-xs text-gray-600 dark:text-gray-400 font-mono">
          <ShieldAlert className="w-3.5 h-3.5" />
          Required: {permissions.join(", ")}
        </div>
      </div>
    );
  }

  return <>{children}</>;
}
