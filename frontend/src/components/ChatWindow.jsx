import { useEffect, useRef, useState } from 'react'
import { sendChatMessage, validateWorkbook } from '../api/client'
import MessageBubble from './MessageBubble'

const WELCOME_MESSAGE = {
  id: 'welcome',
  role: 'bot',
  text:
    "Hi, I'm the Address Validation Agent. Upload an Excel workbook of Legal, " +
    'Civic, or Rural address records and I’ll check them against the rule ' +
    'matrix, geocoding confidence, and Maximo dispatch readiness — read-only, ' +
    'nothing gets written or submitted automatically. After that, ask me ' +
    'follow-up questions like "why is row 3 red?" or try a what-if fix.',
}

export default function ChatWindow() {
  const [messages, setMessages] = useState([WELCOME_MESSAGE])
  const [isBusy, setIsBusy] = useState(false)
  const [selectedFile, setSelectedFile] = useState(null)
  const [textInput, setTextInput] = useState('')
  const [batchId, setBatchId] = useState(null)
  const llmHistoryRef = useRef([])
  const fileInputRef = useRef(null)
  const scrollRef = useRef(null)

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages])

  function handleFileChange(event) {
    setSelectedFile(event.target.files?.[0] ?? null)
  }

  function addMessage(message) {
    setMessages((prev) => [...prev, { id: `${message.role}-${Date.now()}-${Math.random()}`, ...message }])
  }

  async function handleUpload(file) {
    addMessage({ role: 'user', fileName: file.name, text: 'Please validate this batch.' })
    setSelectedFile(null)
    if (fileInputRef.current) fileInputRef.current.value = ''
    setIsBusy(true)
    llmHistoryRef.current = []

    try {
      const result = await validateWorkbook(file)
      setBatchId(result.batch.batchId)
      addMessage({ role: 'bot', text: result.chatMessage, batch: result.batch })
    } catch (error) {
      addMessage({ role: 'bot', text: `Sorry, I couldn't validate that file: ${error.message}`, isError: true })
    } finally {
      setIsBusy(false)
    }
  }

  async function handleTextMessage(text) {
    addMessage({ role: 'user', text })
    setTextInput('')

    if (!batchId) {
      addMessage({
        role: 'bot',
        text: 'Upload an Excel workbook first — I need a validated batch before I can answer questions about it.',
        isError: true,
      })
      return
    }

    setIsBusy(true)
    try {
      const result = await sendChatMessage(batchId, text, llmHistoryRef.current)
      llmHistoryRef.current = [
        ...llmHistoryRef.current,
        { role: 'user', content: text },
        { role: 'assistant', content: result.reply },
      ]
      addMessage({ role: 'bot', text: result.reply, updatedRecord: result.updatedRecord })
    } catch (error) {
      addMessage({ role: 'bot', text: `Sorry, something went wrong: ${error.message}`, isError: true })
    } finally {
      setIsBusy(false)
    }
  }

  async function handleSubmit(event) {
    event.preventDefault()
    if (isBusy) return

    if (selectedFile) {
      await handleUpload(selectedFile)
      return
    }
    if (textInput.trim()) {
      await handleTextMessage(textInput.trim())
    }
  }

  return (
    <div className="chat-window">
      <header className="chat-header">
        <h1>Address Validation Agent</h1>
        <p>Read-only advisory · synthetic data POC</p>
      </header>

      <div className="chat-messages" ref={scrollRef}>
        {messages.map((message) => (
          <MessageBubble key={message.id} message={message} />
        ))}
        {isBusy && (
          <div className="message-row message-row-bot">
            <div className="bubble bubble-bot bubble-typing">Thinking…</div>
          </div>
        )}
      </div>

      <form className="chat-input-bar" onSubmit={handleSubmit}>
        <input
          ref={fileInputRef}
          type="file"
          accept=".xlsx,.xls"
          className="chat-file-input"
          onChange={handleFileChange}
          disabled={isBusy}
        />
        <input
          type="text"
          className="chat-text-input"
          placeholder={batchId ? 'Ask about a row, e.g. "why is row 3 red?"' : 'Upload a workbook to get started…'}
          value={textInput}
          onChange={(e) => setTextInput(e.target.value)}
          disabled={isBusy || !!selectedFile}
        />
        <button type="submit" disabled={isBusy || (!selectedFile && !textInput.trim())}>
          {isBusy ? '…' : 'Send'}
        </button>
      </form>
    </div>
  )
}
