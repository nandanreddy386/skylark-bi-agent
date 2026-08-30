import InsightCard from './InsightCard';

/**
 * Enhanced parser for Markdown text including HTML table rendering for markdown tables.
 */
function renderMarkdown(text) {
  if (!text) return null;

  const lines = text.split('\n');
  const blocks = [];
  let currentList = [];
  let currentTable = [];

  const flushList = (key) => {
    if (currentList.length > 0) {
      blocks.push(
        <ul key={`ul-${key}`} className="list-disc pl-5 my-2.5 space-y-1.5 text-surface-200">
          {currentList.map((item, idx) => (
            <li key={idx} dangerouslySetInnerHTML={{ __html: formatInline(item) }} />
          ))}
        </ul>
      );
      currentList = [];
    }
  };

  const flushTable = (key) => {
    if (currentTable.length > 0) {
      // Parse header, divider, rows
      const headerRow = currentTable[0];
      const dataRows = currentTable.filter((r, idx) => idx > 0 && !r.includes('---'));

      const parseCells = (rowStr) =>
        rowStr
          .split('|')
          .map((c) => c.trim())
          .filter((c, idx, arr) => idx > 0 && idx < arr.length);

      const headers = parseCells(headerRow);

      blocks.push(
        <div key={`tbl-${key}`} className="my-3 overflow-x-auto rounded-xl border border-surface-700/60 shadow-lg">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="bg-surface-800/90 text-primary-300 border-b border-surface-700">
                {headers.map((h, i) => (
                  <th key={i} className="px-4 py-2.5 font-bold uppercase tracking-wider">
                    {h.replace(/\*\*/g, '')}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-800/60">
              {dataRows.map((rowStr, rIdx) => {
                const cells = parseCells(rowStr);
                return (
                  <tr key={rIdx} className="hover:bg-surface-800/40 transition-colors bg-surface-900/40">
                    {cells.map((cell, cIdx) => (
                      <td
                        key={cIdx}
                        className="px-4 py-2.5 text-surface-200"
                        dangerouslySetInnerHTML={{ __html: formatInline(cell) }}
                      />
                    ))}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      );
      currentTable = [];
    }
  };

  const formatInline = (str) => {
    if (!str) return '';
    return str
      .replace(/\*\*(.*?)\*\*/g, '<strong className="font-semibold text-surface-100">$1</strong>')
      .replace(/\*(.*?)\*/g, '<em className="text-primary-300">$1</em>')
      .replace(/`([^`]+)`/g, '<code className="bg-surface-800 px-1.5 py-0.5 rounded text-accent font-mono">$1</code>');
  };

  lines.forEach((line, idx) => {
    const trimmed = line.strip ? line.strip() : line.trim();

    // Check if table row
    if (trimmed.startsWith('|') && trimmed.endsWith('|')) {
      flushList(idx);
      currentTable.push(trimmed);
      return;
    } else {
      flushTable(idx);
    }

    if (!trimmed) {
      flushList(idx);
      return;
    }

    if (trimmed.startsWith('# ')) {
      flushList(idx);
      blocks.push(
        <h1 key={idx} className="text-xl font-bold text-primary-300 mt-4 mb-2 pb-1 border-b border-surface-700/50">
          {trimmed.substring(2)}
        </h1>
      );
    } else if (trimmed.startsWith('## ')) {
      flushList(idx);
      blocks.push(
        <h2 key={idx} className="text-lg font-semibold text-primary-400 mt-3.5 mb-2">
          {trimmed.substring(3)}
        </h2>
      );
    } else if (trimmed.startsWith('### ')) {
      flushList(idx);
      blocks.push(
        <h3 key={idx} className="text-base font-semibold text-surface-200 mt-3 mb-1.5">
          {trimmed.substring(4)}
        </h3>
      );
    } else if (trimmed.startsWith('* ') || trimmed.startsWith('- ')) {
      currentList.push(trimmed.substring(2));
    } else {
      flushList(idx);
      blocks.push(
        <p key={idx} className="my-1.5 leading-relaxed text-surface-200 text-sm" dangerouslySetInnerHTML={{ __html: formatInline(trimmed) }} />
      );
    }
  });

  flushList('end');
  flushTable('end');
  return blocks;
}

export default function Message({ message }) {
  const isUser = message.role === 'user';

  return (
    <div className={`flex items-start gap-3 w-full py-2 ${isUser ? 'justify-end' : 'justify-start'}`}>
      {/* Assistant Avatar */}
      {!isUser && (
        <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-primary-500 to-accent flex items-center justify-center flex-shrink-0 shadow-lg mt-1">
          <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
          </svg>
        </div>
      )}

      {/* Message Bubble - Full width for Assistant */}
      <div className={`${
        isUser
          ? 'max-w-xl bg-gradient-to-r from-primary-600 to-primary-700 text-white rounded-2xl rounded-tr-xs px-5 py-3.5 shadow-md'
          : 'w-full max-w-full bg-surface-900/90 text-surface-100 rounded-2xl rounded-tl-xs border border-surface-700/60 p-5 shadow-xl backdrop-blur-md'
      }`}>
        {/* Content */}
        <div className="markdown-content w-full">
          {renderMarkdown(message.content)}
        </div>

        {/* Assumptions */}
        {message.assumptions && message.assumptions.length > 0 && (
          <div className="mt-4 p-3 rounded-xl bg-primary-950/40 border border-primary-500/30 text-xs text-primary-300">
            <span className="font-semibold block mb-1 flex items-center gap-1.5 text-accent">
              <span>💡</span> Analysis Scope & Assumptions:
            </span>
            <ul className="list-disc pl-4 space-y-1 text-surface-300">
              {message.assumptions.map((item, idx) => (
                <li key={idx}>{item}</li>
              ))}
            </ul>
          </div>
        )}

        {/* Structured Insight Cards */}
        {message.metrics && <InsightCard metrics={message.metrics} />}

        {/* Data Quality Notes */}
        {message.dataQualityNotes && message.dataQualityNotes.length > 0 && (
          <div className="mt-3 p-3.5 rounded-xl bg-amber-950/40 border border-amber-500/30 text-xs text-amber-300">
            <span className="font-semibold block mb-1.5 flex items-center gap-1.5 text-amber-300">
              <span>⚠️</span> Data Quality & Source Context:
            </span>
            <ul className="list-disc pl-5 space-y-1 text-amber-200/90">
              {Array.from(new Set(message.dataQualityNotes)).map((note, idx) => (
                <li key={idx}>{note}</li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {/* User Avatar */}
      {isUser && (
        <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-purple-500 to-indigo-600 flex items-center justify-center flex-shrink-0 shadow-lg mt-1">
          <span className="text-xs font-bold text-white">YOU</span>
        </div>
      )}
    </div>
  );
}
