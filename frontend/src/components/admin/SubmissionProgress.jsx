export function SubmissionProgress({ submitted = 0, pending = 0, overdue = 0, total = 0, progress = 0 }) {
  if (!total) return <p className="text-sm leading-relaxed text-ink-500">No required submissions yet. Add subject assignments to begin tracking completion.</p>
  const segments = [
    { label: 'Submitted', value: submitted, color: 'bg-brand-800' },
    { label: 'Pending', value: Math.max(0, pending - overdue), color: 'bg-ink-300' },
    { label: 'Overdue', value: overdue, color: 'bg-danger-500' },
  ]
  return <div>
    <div className="mb-4 flex flex-wrap items-baseline justify-between gap-2"><p className="text-sm text-ink-600"><strong className="font-semibold text-ink-900">{submitted} of {total}</strong> subjects submitted</p><span className="text-sm font-medium tabular-nums text-brand-900">{progress}% complete</span></div>
    <div className="flex h-2.5 overflow-hidden rounded-sm bg-ink-100" role="img" aria-label={segments.map(s => s.value + ' ' + s.label.toLowerCase()).join(', ')}>{segments.filter(s => s.value > 0).map(s => <div key={s.label} className={s.color} style={{width: (s.value / total * 100) + '%'}} />)}</div>
    <dl className="mt-4 flex flex-wrap gap-x-6 gap-y-2">{segments.map(s => <div key={s.label} className="flex items-center gap-2 text-xs"><span className={'size-2 rounded-sm ' + s.color} aria-hidden="true" /><dt className="text-ink-500">{s.label}</dt><dd className="font-semibold tabular-nums">{s.value}</dd></div>)}</dl>
  </div>
}
export default SubmissionProgress
