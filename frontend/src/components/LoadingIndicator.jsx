/**
 * Loading indicator with animated dots and contextual message.
 */
export default function LoadingIndicator() {
  return (
    <div className="flex items-start gap-3 px-4 py-3">
      <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary-500 to-accent flex items-center justify-center flex-shrink-0 mt-0.5">
        <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
        </svg>
      </div>
      <div className="bg-surface-800/60 backdrop-blur-sm rounded-2xl rounded-tl-md px-5 py-4 border border-surface-700/50 max-w-lg">
        <div className="flex items-center gap-2">
          <div className="flex gap-1">
            <span className="w-2 h-2 bg-primary-400 rounded-full animate-pulse-glow" style={{ animationDelay: '0s' }}></span>
            <span className="w-2 h-2 bg-primary-400 rounded-full animate-pulse-glow" style={{ animationDelay: '0.3s' }}></span>
            <span className="w-2 h-2 bg-primary-400 rounded-full animate-pulse-glow" style={{ animationDelay: '0.6s' }}></span>
          </div>
          <span className="text-sm text-surface-300">Analyzing your data...</span>
        </div>
      </div>
    </div>
  );
}
