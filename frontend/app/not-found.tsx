/**
 * 404 Not Found — route-level not found page.
 */

import Link from "next/link";

export default function NotFound() {
  return (
    <div className="flex items-center justify-center h-64">
      <div className="text-center max-w-md">
        <p className="text-5xl font-bold text-gray-300 mb-3">404</p>
        <p className="text-sm font-medium text-gray-900 mb-1">Page not found</p>
        <p className="text-xs text-gray-500 mb-6">The page you&apos;re looking for doesn&apos;t exist or has been moved.</p>
        <Link
          href="/dashboard"
          className="inline-flex items-center gap-1.5 text-xs font-medium text-gold-600 hover:text-gold-700"
        >
          Go to Dashboard
        </Link>
      </div>
    </div>
  );
}
