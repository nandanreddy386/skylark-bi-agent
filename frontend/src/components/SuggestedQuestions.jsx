/**
 * Suggested questions component — clickable question cards
 * that help users get started with the BI agent.
 */

const SUGGESTED_QUESTIONS = [
  {
    text: "How is our pipeline looking this quarter?",
    icon: "📊",
    category: "Sales",
  },
  {
    text: "Which sector has the highest pipeline value?",
    icon: "🏆",
    category: "Sales",
  },
  {
    text: "What are our biggest operational risks?",
    icon: "⚠️",
    category: "Operations",
  },
  {
    text: "Give me a leadership update.",
    icon: "📋",
    category: "Executive",
  },
  {
    text: "Which deals are expected to close soon?",
    icon: "🎯",
    category: "Sales",
  },
  {
    text: "How are our work orders performing?",
    icon: "🔧",
    category: "Operations",
  },
];

export default function SuggestedQuestions({ onSelect, disabled }) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 px-4">
      {SUGGESTED_QUESTIONS.map((q, i) => (
        <button
          key={i}
          onClick={() => onSelect(q.text)}
          disabled={disabled}
          className="group text-left p-4 rounded-xl bg-surface-800/40 border border-surface-700/40
                     hover:bg-surface-800/70 hover:border-primary-500/30 transition-all duration-200
                     disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
        >
          <div className="flex items-start gap-3">
            <span className="text-xl">{q.icon}</span>
            <div>
              <p className="text-sm text-surface-200 group-hover:text-surface-100 transition-colors leading-snug">
                {q.text}
              </p>
              <span className="text-xs text-surface-500 mt-1 inline-block">{q.category}</span>
            </div>
          </div>
        </button>
      ))}
    </div>
  );
}
