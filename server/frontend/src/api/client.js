import axios from 'axios'

const API_BASE_URL = 'http://localhost:8000'

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor for logging
apiClient.interceptors.request.use(
  (config) => {
    console.log(`API Request: ${config.method?.toUpperCase()} ${config.url}`)
    return config
  },
  (error) => {
    console.error('API Request Error:', error)
    return Promise.reject(error)
  }
)

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => {
    console.log(`API Response: ${response.status} ${response.config.url}`)
    return response
  },
  (error) => {
    console.error('API Response Error:', error.response?.status, error.response?.data || error.message)
    return Promise.reject(error)
  }
)

// Main API object with both direct axios methods and specific API methods
export const api = {
  // Direct axios methods
  get: (url, config) => apiClient.get(url, config),
  post: (url, data, config) => apiClient.post(url, data, config),
  put: (url, data, config) => apiClient.put(url, data, config),
  patch: (url, data, config) => apiClient.patch(url, data, config),
  delete: (url, config) => apiClient.delete(url, config),

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
  
  // Additional endpoints for filters
  // Use existing backend endpoints (global agents/users)
  getMemoryAgents: () => apiClient.get('/api/agents'),
  getMemoryUsers: () => apiClient.get('/api/users'),
  // Conversation-specific agent/user lists can reuse global lists or be implemented later
  getConversationAgents: () => apiClient.get('/api/agents'),
  getConversationUsers: () => apiClient.get('/api/users'),
}

// Export both the main api object and the raw axios client
export default apiClient 