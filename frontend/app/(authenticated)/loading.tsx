/**
 * Route loading boundary — shown during page transitions and data fetching.
 */

export default function RouteLoading() {
  return (
    <div className="flex items-center justify-center h-64">
      <div className="text-center">
        <div className="w-8 h-8 border-4 border-gold-400 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
        <p className="text-sm text-gray-500">Loading...</p>
      </div>
    </div>
  );
}
