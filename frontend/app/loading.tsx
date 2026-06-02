/**
 * Root loading boundary — shown during initial app bootstrap.
 */

export default function RootLoading() {
  return (
    <div className="min-h-screen bg-navy-900 flex items-center justify-center">
      <div className="text-center">
        <div className="w-10 h-10 border-4 border-gold-400 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
        <p className="text-sm text-gray-400">Loading ContractRiskEdge...</p>
      </div>
    </div>
  );
}
