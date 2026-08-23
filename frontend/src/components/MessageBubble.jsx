import RecordDetails, { RecordRow } from './RecordDetails'

export default function MessageBubble({ message }) {
  const { role, text, fileName, batch, updatedRecord, isError } = message

  return (
    <div className={`message-row message-row-${role}`}>
      <div className={`bubble bubble-${role} ${isError ? 'bubble-error' : ''}`}>
        {fileName && <div className="bubble-file">📎 {fileName}</div>}
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
