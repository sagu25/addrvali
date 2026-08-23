const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

export async function validateWorkbook(file) {
  const formData = new FormData()
  formData.append('file', file)

  const response = await fetch(`${API_BASE_URL}/api/chat/validate`, {
    method: 'POST',
    body: formData,
  })

  if (!response.ok) {
    let detail = `Request failed with status ${response.status}`
    try {
      const body = await response.json()
      detail = body.detail || detail
    } catch {
      // response body wasn't JSON, keep the generic message
    }
    throw new Error(detail)
  }

  return response.json()
}

export async function sendChatMessage(batchId, message, history = []) {
  const response = await fetch(`${API_BASE_URL}/api/chat/message`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ batchId, message, history }),
  })

  if (!response.ok) {
    let detail = `Request failed with status ${response.status}`
    try {
      const body = await response.json()
      detail = body.detail || detail
    } catch {
      // response body wasn't JSON, keep the generic message
    }
    throw new Error(detail)
  }

  return response.json()
}
