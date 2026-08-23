import RecordDetails, { RecordRow } from './RecordDetails'

const SOURCE_BADGE = {
  azure_openai: { label: 'Azure OpenAI', className: 'source-azure' },
  not_configured: { label: 'Azure OpenAI not configured', className: 'source-fallback' },
  azure_openai_error: { label: 'Azure OpenAI call failed', className: 'source-fallback-error' },
  no_batch: null,
}

export default function MessageBubble({ message }) {
  const { role, text, fileName, batch, updatedRecord, source, isError } = message
  const badge = source ? SOURCE_BADGE[source] : null

  return (
    <div className={`message-row message-row-${role}`}>
      <div className={`bubble bubble-${role} ${isError ? 'bubble-error' : ''}`}>
        {fileName && <div className="bubble-file">📎 {fileName}</div>}
        {badge && <div className={`source-badge ${badge.className}`}>{badge.label}</div>}
        {text && <div className="bubble-text">{text}</div>}
        {batch && <RecordDetails batch={batch} />}
        {updatedRecord && (
          <div className="record-details">
            <RecordRow record={updatedRecord} />
          </div>
        )}
      </div>
    </div>
  )
}
