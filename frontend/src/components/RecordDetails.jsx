const STATUS_STYLE = {
  GREEN: { emoji: '🟢', label: 'Ready' },
  AMBER: { emoji: '🟠', label: 'Needs review' },
  RED: { emoji: '🔴', label: 'Blocked' },
}

function componentIssues(component) {
  if (!component) return []
  return [
    ...component.errors.map((issue) => ({ ...issue, kind: 'error' })),
    ...component.warnings.map((issue) => ({ ...issue, kind: 'warning' })),
  ]
}

export function RecordRow({ record }) {
  const status = STATUS_STYLE[record.finalStatus]
  const issues = [
    ...componentIssues(record.ruleValidation).map((i) => ({ ...i, source: 'Rule check' })),
    ...componentIssues(record.geocodeValidation).map((i) => ({ ...i, source: 'Geocoding' })),
    ...componentIssues(record.preDispatchValidation).map((i) => ({ ...i, source: 'Maximo readiness' })),
  ]

  return (
    <details className="record-row" open={record.finalStatus !== 'GREEN'}>
      <summary>
        <span className={`status-chip status-${record.finalStatus.toLowerCase()}`}>
          {status.emoji} {status.label}
        </span>
        <span className="record-label">
          Row {record.rowId ?? '—'}
          {record.servicePointKey ? ` · ${record.servicePointKey}` : ''}
        </span>
        <span className="record-combo">{record.addressCombination ?? 'unknown combination'}</span>
      </summary>

      {record.appliedUpdates && (
        <p className="record-whatif">
          What-if: {Object.entries(record.appliedUpdates).map(([field, value]) => `${field} = "${value}"`).join(', ')}
        </p>
      )}

      {record.aiExplanation && <p className="record-explanation">{record.aiExplanation}</p>}

      {issues.length > 0 && (
        <ul className="issue-list">
          {issues.map((issue, idx) => (
            <li key={idx} className={`issue issue-${issue.kind}`}>
              <span className="issue-source">{issue.source}</span>
              {issue.fieldName && <span className="issue-field">{issue.fieldName}</span>}
              <span className="issue-message">{issue.message}</span>
            </li>
          ))}
        </ul>
      )}
    </details>
  )
}

export default function RecordDetails({ batch }) {
  if (!batch || !batch.results?.length) return null

  return (
    <div className="record-details">
      {batch.results.map((record) => (
        <RecordRow key={`${record.rowId}-${record.objectId}`} record={record} />
      ))}
    </div>
  )
}
