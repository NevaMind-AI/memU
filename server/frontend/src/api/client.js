import axios from 'axios'

const API_BASE_URL = 'http://localhost:8000'

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// API helper functions
export const api = {
  // System statistics
  getStats: () => apiClient.get('/api/stats'),

  // Conversations
  getConversations: (params = {}) => apiClient.get('/api/conversations', { params }),
  getConversationDetail: (id) => apiClient.get(`/api/conversations/${id}`),
  deleteConversation: (id) => apiClient.delete(`/api/conversations/${id}`),

  // Memories
  getMemories: (params = {}) => apiClient.get('/api/memories', { params }),
  getMemoryDetail: (id) => apiClient.get(`/api/memories/${id}`),
  deleteMemory: (id) => apiClient.delete(`/api/memories/${id}`),

  // Memory operation records
  getMemoryOperations: (params = {}) => apiClient.get('/api/memory-operations', { params }),

  // Get agents and users list
  getAgents: () => apiClient.get('/api/agents'),
  getUsers: () => apiClient.get('/api/users'),
}

export default apiClient 