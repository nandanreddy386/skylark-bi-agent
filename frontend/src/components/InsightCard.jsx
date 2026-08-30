/**
 * InsightCard component for rendering structured metrics summary cards.
 * Formats statistics into executive metric badges without raw [object Object] strings.
 */

export default function InsightCard({ metrics }) {
  if (!metrics || typeof metrics !== 'object' || Object.keys(metrics).length === 0) return null;

  const formatKey = (key) => {
    return key
      .replace(/_/g, ' ')
      .replace(/([A-Z])/g, ' $1')
      .replace(/^./, (str) => str.toUpperCase())
      .trim();
  };

  const renderValue = (val) => {
    if (val === null || val === undefined) return <span className="text-surface-500">-</span>;
    if (typeof val === 'boolean') return <span className="text-surface-200 font-semibold">{val ? 'Yes' : 'No'}</span>;
    if (typeof val === 'number') {
      if (Number.isInteger(val)) return <span className="text-surface-100 font-semibold">{val.toLocaleString()}</span>;
      return <span className="text-surface-100 font-semibold">{val.toFixed(1)}</span>;
    }
    if (typeof val === 'string') return <span className="text-surface-100 font-medium">{val}</span>;
    return null;
  };

  const renderSection = (title, data) => {
    if (!data || typeof data !== 'object') return null;

    // Filter primitive key-values (scalars) for clean badge display
    const primitiveEntries = Object.entries(data).filter(([_, v]) => {
      return v !== null && v !== undefined && typeof v !== 'object';
    });

    if (primitiveEntries.length === 0) return null;

    return (
      <div key={title} className="p-4 rounded-xl bg-surface-900/90 border border-surface-700/60 shadow-md">
        <h4 className="text-xs font-bold text-accent uppercase tracking-wider mb-3 pb-1 border-b border-surface-800">
          {formatKey(title)}
        </h4>
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3">
          {primitiveEntries.map(([k, v]) => (
            <div key={k} className="flex flex-col bg-surface-800/40 p-2.5 rounded-lg border border-surface-700/30">
              <span className="text-[11px] text-surface-400 font-medium truncate mb-1" title={formatKey(k)}>
                {formatKey(k)}
              </span>
              <div className="text-sm font-bold text-primary-300">
                {renderValue(v)}
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  };

  return (
    <div className="mt-4 space-y-3 w-full">
      <div className="flex items-center gap-2 mb-1">
        <span className="w-2 h-2 rounded-full bg-accent animate-ping"></span>
        <span className="text-xs uppercase tracking-wider font-bold text-surface-300">
          Executive Data Highlights
        </span>
      </div>
      <div className="grid grid-cols-1 gap-3 w-full">
        {Object.entries(metrics).map(([sectionKey, sectionData]) => renderSection(sectionKey, sectionData))}
      </div>
    </div>
  );
}
