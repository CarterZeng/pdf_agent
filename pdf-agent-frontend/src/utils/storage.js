export function saveChatHistory(messages) {
  try {
    localStorage.setItem('chat_history', JSON.stringify(messages))
  } catch (e) {
    console.error('Failed to save chat history:', e)
  }
}

export function loadChatHistory() {
  try {
    const history = localStorage.getItem('chat_history')
    return history ? JSON.parse(history) : []
  } catch (e) {
    console.error('Failed to load chat history:', e)
    return []
  }
}

export function clearChatHistory() {
  try {
    localStorage.removeItem('chat_history')
  } catch (e) {
    console.error('Failed to clear chat history:', e)
  }
}

export function exportChatHistory(messages) {
  const dataStr = JSON.stringify(messages, null, 2)
  const dataBlob = new Blob([dataStr], { type: 'application/json' })
  const url = URL.createObjectURL(dataBlob)
  const link = document.createElement('a')
  link.href = url
  link.download = `chat_history_${new Date().toISOString().slice(0, 10)}.json`
  link.click()
  URL.revokeObjectURL(url)
}

export function importChatHistory(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = (e) => {
      try {
        const messages = JSON.parse(e.target.result)
        resolve(messages)
      } catch (error) {
        reject(new Error('Invalid JSON file'))
      }
    }
    reader.onerror = () => {
      reject(new Error('Failed to read file'))
    }
    reader.readAsText(file)
  })
}