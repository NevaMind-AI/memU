import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import {
  Box,
  Typography,
  Card,
  CardContent,
  CardActions,
  Button,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Grid,
  CircularProgress,
  Alert,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  InputAdornment,
  Chip,
  Avatar,
  Fade,
  Divider,
  Stack,
  Badge,
  Tooltip
} from '@mui/material'
import {
  Visibility as VisibilityIcon,
  Delete as DeleteIcon,
  Search as SearchIcon,
  Chat as ChatIcon,
  Person as PersonIcon,
  SmartToy as AgentIcon,
  Schedule as TimeIcon,
  Clear as ClearIcon,
  TurnRight as TurnIcon,
  Description as SummaryIcon,
  Refresh as RefreshIcon,
  TrendingUp as TrendingIcon,
  FilterList as FilterIcon
} from '@mui/icons-material'
import { api } from '../api/client'

function ConversationCard({ conversation, onDelete }) {
  const formatDate = (dateString) => {
    if (!dateString) return '-'
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  const truncateSummary = (text, maxLength = 120) => {
    if (!text) return 'No summary available'
    return text.length > maxLength ? `${text.slice(0, maxLength)}...` : text
  }

  const getTurnCountColor = (turns) => {
    if (turns >= 20) return '#10b981'
    if (turns >= 10) return '#f59e0b'
    if (turns >= 5) return '#3b82f6'
    return '#64748b'
  }

  const getTurnCountGradient = (turns) => {
    if (turns >= 20) return 'linear-gradient(135deg, #10b981 0%, #059669 100%)'
    if (turns >= 10) return 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)'
    if (turns >= 5) return 'linear-gradient(135deg, #3b82f6 0%, #2563eb 100%)'
    return 'linear-gradient(135deg, #64748b 0%, #475569 100%)'
  }

  const turnCount = conversation.turn_count || 0

  return (
    <Fade in={true} timeout={300}>
      <Card
        sx={{
          height: '100%',
          display: 'flex',
          flexDirection: 'column',
          position: 'relative',
          transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
          '&:hover': {
            transform: 'translateY(-4px)',
            boxShadow: '0 20px 40px -10px rgba(0, 0, 0, 0.3)',
          }
        }}
      >
        {/* Turn Count Badge */}
        <Box
          sx={{
            position: 'absolute',
            top: 16,
            right: 16,
            zIndex: 2
          }}
        >
          <Avatar
            sx={{
              width: 40,
              height: 40,
              background: getTurnCountGradient(turnCount),
              fontSize: '0.75rem',
              fontWeight: 700,
              boxShadow: '0 4px 12px rgba(0, 0, 0, 0.2)',
              border: '2px solid rgba(255, 255, 255, 0.1)'
            }}
          >
            {turnCount}
          </Avatar>
        </Box>

        <CardContent sx={{ flex: 1, pt: 3, pb: 2 }}>
          {/* Header */}
          <Box sx={{ mb: 3, pr: 5 }}>
            <Stack direction="row" alignItems="center" spacing={2} sx={{ mb: 2 }}>
              <Avatar
                sx={{
                  width: 44,
                  height: 44,
                  background: 'linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%)',
                  boxShadow: '0 8px 25px -5px rgba(59, 130, 246, 0.4)'
                }}
              >
                <ChatIcon sx={{ fontSize: 22 }} />
              </Avatar>
              
              <Box sx={{ flex: 1, minWidth: 0 }}>
                <Typography
                  variant="h6"
                  sx={{
                    fontWeight: 600,
                    fontSize: '1.1rem',
                    color: '#f8fafc',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap',
                    fontFamily: 'monospace',
                    mb: 0.5
                  }}
                >
                  {conversation.conversation_id}
                </Typography>
                <Typography variant="caption" sx={{ color: '#94a3b8', fontWeight: 500 }}>
                  Conversation Instance
                </Typography>
              </Box>
            </Stack>
          </Box>

          {/* Agent and User Info */}
          <Grid container spacing={2} sx={{ mb: 3 }}>
            <Grid item xs={6}>
              <Box
                sx={{
                  p: 2,
                  borderRadius: 2,
                  background: 'linear-gradient(135deg, rgba(59, 130, 246, 0.1) 0%, rgba(29, 78, 216, 0.05) 100%)',
                  border: '1px solid rgba(59, 130, 246, 0.2)'
                }}
              >
                <Stack direction="row" alignItems="center" spacing={1.5}>
                  <AgentIcon sx={{ fontSize: 18, color: '#3b82f6' }} />
                  <Box>
                    <Typography variant="body2" sx={{ color: '#f8fafc', fontWeight: 500 }}>
                      {conversation.agent_id}
                    </Typography>
                    <Typography variant="caption" sx={{ color: '#94a3b8' }}>
                      Agent
                    </Typography>
                  </Box>
                </Stack>
              </Box>
            </Grid>
            
            <Grid item xs={6}>
              <Box
                sx={{
                  p: 2,
                  borderRadius: 2,
                  background: 'linear-gradient(135deg, rgba(16, 185, 129, 0.1) 0%, rgba(5, 150, 105, 0.05) 100%)',
                  border: '1px solid rgba(16, 185, 129, 0.2)'
                }}
              >
                <Stack direction="row" alignItems="center" spacing={1.5}>
                  <PersonIcon sx={{ fontSize: 18, color: '#10b981' }} />
                  <Box>
                    <Typography variant="body2" sx={{ color: '#f8fafc', fontWeight: 500 }}>
                      {conversation.user_id}
                    </Typography>
                    <Typography variant="caption" sx={{ color: '#94a3b8' }}>
                      User
                    </Typography>
                  </Box>
                </Stack>
              </Box>
            </Grid>
          </Grid>

          {/* Conversation Summary */}
          <Box
            sx={{
              p: 3,
              borderRadius: 2,
              background: 'linear-gradient(135deg, rgba(139, 92, 246, 0.1) 0%, rgba(124, 58, 237, 0.05) 100%)',
              border: '1px solid rgba(139, 92, 246, 0.2)',
              mb: 3
            }}
          >
            <Stack direction="row" alignItems="flex-start" spacing={2}>
              <SummaryIcon sx={{ fontSize: 18, color: '#8b5cf6', mt: 0.5, flexShrink: 0 }} />
              <Box sx={{ flex: 1, minWidth: 0 }}>
                <Typography
                  variant="caption"
                  sx={{
                    color: '#94a3b8',
                    fontWeight: 600,
                    textTransform: 'uppercase',
                    letterSpacing: '0.05em',
                    mb: 1,
                    display: 'block'
                  }}
                >
                  Summary
                </Typography>
                <Typography
                  variant="body2"
                  sx={{
                    color: '#e2e8f0',
                    lineHeight: 1.5,
                    fontStyle: conversation.summary ? 'normal' : 'italic'
                  }}
                >
                  {truncateSummary(conversation.summary)}
                </Typography>
              </Box>
            </Stack>
          </Box>

          {/* Turn Count Visualization */}
          <Box sx={{ mb: 3 }}>
            <Stack direction="row" alignItems="center" spacing={2} sx={{ mb: 2 }}>
              <TurnIcon sx={{ fontSize: 18, color: getTurnCountColor(turnCount) }} />
              <Typography
                variant="body2"
                sx={{
                  color: '#cbd5e1',
                  fontWeight: 500
                }}
              >
                Conversation Turns
              </Typography>
              <Chip
                label={`${turnCount} turns`}
                size="small"
                sx={{
                  backgroundColor: getTurnCountColor(turnCount),
                  color: '#ffffff',
                  fontWeight: 600,
                  fontSize: '0.75rem'
                }}
              />
            </Stack>
            
            {/* Progress Bar for Turns */}
            <Box
              sx={{
                height: 6,
                backgroundColor: '#334155',
                borderRadius: 3,
                overflow: 'hidden',
                position: 'relative'
              }}
            >
              <Box
                sx={{
                  height: '100%',
                  width: `${Math.min(100, (turnCount / 20) * 100)}%`,
                  background: getTurnCountGradient(turnCount),
                  transition: 'width 0.5s cubic-bezier(0.4, 0, 0.2, 1)'
                }}
              />
            </Box>
          </Box>

          {/* Timestamps */}
          <Stack spacing={1}>
            <Stack direction="row" alignItems="center" spacing={1.5}>
              <TimeIcon sx={{ fontSize: 14, color: '#10b981' }} />
              <Typography variant="caption" sx={{ color: '#cbd5e1' }}>
                Started: {formatDate(conversation.created_at)}
              </Typography>
            </Stack>
            <Stack direction="row" alignItems="center" spacing={1.5}>
              <TimeIcon sx={{ fontSize: 14, color: '#f59e0b' }} />
              <Typography variant="caption" sx={{ color: '#cbd5e1' }}>
                Last Activity: {formatDate(conversation.updated_at)}
              </Typography>
            </Stack>
          </Stack>
        </CardContent>

        <Divider sx={{ borderColor: '#334155' }} />

        <CardActions sx={{ justifyContent: 'space-between', px: 3, py: 2 }}>
          <Button
            component={Link}
            to={`/conversations/${conversation.conversation_id}`}
            variant="contained"
            size="small"
            startIcon={<VisibilityIcon />}
            sx={{
              background: 'linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%)',
              '&:hover': {
                background: 'linear-gradient(135deg, #2563eb 0%, #1e40af 100%)',
                transform: 'translateY(-1px)',
                boxShadow: '0 8px 25px -5px rgba(59, 130, 246, 0.4)'
              }
            }}
          >
            View Details
          </Button>
          
          <Tooltip title="Delete Conversation" placement="top">
            <IconButton
              size="small"
              onClick={() => onDelete(conversation)}
              sx={{ 
                color: '#ef4444',
                '&:hover': { 
                  backgroundColor: 'rgba(239, 68, 68, 0.1)',
                  color: '#f87171'
                }
              }}
            >
              <DeleteIcon />
            </IconButton>
          </Tooltip>
        </CardActions>
      </Card>
    </Fade>
  )
}

function Conversations() {
  const [conversations, setConversations] = useState([])
  const [filteredConversations, setFilteredConversations] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  
  // Filter states
  const [searchTerm, setSearchTerm] = useState('')
  const [agentFilter, setAgentFilter] = useState('')
  const [userFilter, setUserFilter] = useState('')
  
  // Filter options
  const [agents, setAgents] = useState([])
  const [users, setUsers] = useState([])
  
  // Delete dialog
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [conversationToDelete, setConversationToDelete] = useState(null)

  const fetchData = async () => {
    try {
      setLoading(true)
      setError(null)
      const response = await api.get('/api/conversations')
      setConversations(response.data)
      setFilteredConversations(response.data)
    } catch (err) {
      setError('Failed to fetch conversations')
      console.error('Fetch conversations error:', err)
    } finally {
      setLoading(false)
    }
  }

  const fetchFilters = async () => {
    try {
      // Extract unique agents and users from conversations
      const uniqueAgents = [...new Set(conversations.map(conv => conv.agent_id))].sort()
      const uniqueUsers = [...new Set(conversations.map(conv => conv.user_id))].sort()
      setAgents(uniqueAgents)
      setUsers(uniqueUsers)
    } catch (err) {
      console.error('Fetch filters error:', err)
    }
  }

  const handleFilterChange = (key, value) => {
    if (key === 'search') setSearchTerm(value)
    if (key === 'agent') setAgentFilter(value)
    if (key === 'user') setUserFilter(value)
  }

  const handleDelete = async (conversation) => {
    setConversationToDelete(conversation)
    setDeleteDialogOpen(true)
  }

  const confirmDelete = async () => {
    if (!conversationToDelete) return
    
    try {
      await api.delete(`/api/conversations/${conversationToDelete.conversation_id}`)
      await fetchData()
      setDeleteDialogOpen(false)
      setConversationToDelete(null)
    } catch (err) {
      console.error('Delete error:', err)
      setError('Failed to delete conversation')
    }
  }

  const clearFilters = () => {
    setSearchTerm('')
    setAgentFilter('')
    setUserFilter('')
  }

  const hasActiveFilters = searchTerm || agentFilter || userFilter

  // Filter conversations when filters change
  useEffect(() => {
    let filtered = conversations

    if (searchTerm) {
      filtered = filtered.filter(conversation =>
        conversation.conversation_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
        conversation.agent_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
        conversation.user_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
        (conversation.summary && conversation.summary.toLowerCase().includes(searchTerm.toLowerCase()))
      )
    }

    if (agentFilter) {
      filtered = filtered.filter(conversation => conversation.agent_id === agentFilter)
    }

    if (userFilter) {
      filtered = filtered.filter(conversation => conversation.user_id === userFilter)
    }

    setFilteredConversations(filtered)
  }, [conversations, searchTerm, agentFilter, userFilter])

  useEffect(() => {
    fetchData()
  }, [])

  useEffect(() => {
    fetchFilters()
  }, [conversations])

  if (loading) {
    return (
      <Box sx={{ 
        display: 'flex', 
        justifyContent: 'center', 
        alignItems: 'center', 
        minHeight: 400,
        flexDirection: 'column',
        gap: 2
      }}>
        <CircularProgress size={48} sx={{ color: '#3b82f6' }} />
        <Typography variant="body2" sx={{ color: '#94a3b8' }}>
          Loading conversation data...
        </Typography>
      </Box>
    )
  }

  return (
    <Box>
      {/* Header */}
      <Stack direction="row" alignItems="center" justifyContent="space-between" sx={{ mb: 4 }}>
        <Box>
          <Typography 
            variant="h4" 
            sx={{ 
              fontWeight: 700,
              color: '#f8fafc',
              mb: 1
            }}
          >
            Conversation Management
          </Typography>
          <Typography variant="body1" sx={{ color: '#94a3b8' }}>
            Monitor and manage agent conversations across the platform
          </Typography>
        </Box>
        
        <Stack direction="row" spacing={1}>
          <IconButton 
            onClick={fetchData}
            sx={{ 
              color: '#94a3b8',
              '&:hover': { 
                color: '#3b82f6',
                backgroundColor: 'rgba(59, 130, 246, 0.1)'
              }
            }}
          >
            <RefreshIcon />
          </IconButton>
          
          <Chip
            icon={<TrendingIcon />}
            label={`${conversations.length} Total`}
            sx={{
              background: 'linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%)',
              color: '#ffffff',
              fontWeight: 600
            }}
          />
        </Stack>
      </Stack>

      {error && (
        <Alert 
          severity="error" 
          sx={{ 
            mb: 3,
            borderRadius: 2,
            backgroundColor: '#1e293b',
            border: '1px solid #ef4444'
          }}
        >
          {error}
        </Alert>
      )}

      {/* Enhanced Filters */}
      <Card sx={{ mb: 4, background: 'linear-gradient(135deg, #1e293b 0%, #334155 100%)' }}>
        <CardContent sx={{ p: 3 }}>
          <Stack direction="row" alignItems="center" spacing={2} sx={{ mb: 3 }}>
            <FilterIcon sx={{ color: '#3b82f6' }} />
            <Typography variant="h6" sx={{ color: '#f8fafc', fontWeight: 600 }}>
              Search & Filter
            </Typography>
            {hasActiveFilters && (
              <Badge
                badgeContent={[searchTerm, agentFilter, userFilter].filter(Boolean).length}
                color="primary"
                sx={{
                  '& .MuiBadge-badge': {
                    backgroundColor: '#3b82f6',
                    color: '#ffffff'
                  }
                }}
              >
                <Chip
                  label="Active Filters"
                  size="small"
                  sx={{ backgroundColor: '#334155', color: '#e2e8f0' }}
                />
              </Badge>
            )}
          </Stack>
          
          <Grid container spacing={3} alignItems="center">
            <Grid item xs={12} md={5}>
              <TextField
                fullWidth
                placeholder="Search by ID, agent, user, or summary..."
                value={searchTerm}
                onChange={(e) => handleFilterChange('search', e.target.value)}
                InputProps={{
                  startAdornment: (
                    <InputAdornment position="start">
                      <SearchIcon sx={{ color: '#94a3b8' }} />
                    </InputAdornment>
                  ),
                }}
                size="small"
              />
            </Grid>
            
            <Grid item xs={12} md={2}>
              <FormControl fullWidth size="small">
                <InputLabel sx={{ color: '#94a3b8' }}>Agent</InputLabel>
                <Select
                  value={agentFilter}
                  label="Agent"
                  onChange={(e) => handleFilterChange('agent', e.target.value)}
                >
                  <MenuItem value="">All Agents</MenuItem>
                  {agents.map((agent) => (
                    <MenuItem key={agent} value={agent}>
                      {agent}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
            
            <Grid item xs={12} md={2}>
              <FormControl fullWidth size="small">
                <InputLabel sx={{ color: '#94a3b8' }}>User</InputLabel>
                <Select
                  value={userFilter}
                  label="User"
                  onChange={(e) => handleFilterChange('user', e.target.value)}
                >
                  <MenuItem value="">All Users</MenuItem>
                  {users.map((user) => (
                    <MenuItem key={user} value={user}>
                      {user}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
            
            <Grid item xs={12} md={3}>
              <Stack direction="row" spacing={1}>
                <Button
                  variant="outlined"
                  startIcon={<ClearIcon />}
                  onClick={clearFilters}
                  disabled={!hasActiveFilters}
                  size="small"
                  sx={{ flex: 1 }}
                >
                  Clear Filters
                </Button>
                
                <Chip
                  label={`${filteredConversations.length} Results`}
                  sx={{
                    backgroundColor: filteredConversations.length > 0 ? '#10b981' : '#64748b',
                    color: '#ffffff',
                    fontWeight: 600
                  }}
                />
              </Stack>
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      {/* Conversation Cards */}
      {filteredConversations.length === 0 ? (
        <Card sx={{ textAlign: 'center', py: 8 }}>
          <CardContent>
            <ChatIcon sx={{ fontSize: 80, color: '#475569', mb: 3 }} />
            <Typography variant="h5" sx={{ color: '#cbd5e1', mb: 2, fontWeight: 600 }}>
              {conversations.length === 0 ? 'No Conversations Found' : 'No Results Found'}
            </Typography>
            <Typography variant="body1" sx={{ color: '#94a3b8', mb: 3 }}>
              {conversations.length === 0 
                ? 'No conversations have been created yet. Start by initiating your first conversation.'
                : 'Try adjusting your search criteria or clearing the filters to see more results.'
              }
            </Typography>
            {hasActiveFilters && (
              <Button
                variant="contained"
                onClick={clearFilters}
                sx={{
                  background: 'linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%)',
                  '&:hover': {
                    background: 'linear-gradient(135deg, #2563eb 0%, #1e40af 100%)'
                  }
                }}
              >
                Clear All Filters
              </Button>
            )}
          </CardContent>
        </Card>
      ) : (
        <Grid container spacing={3}>
          {filteredConversations.map((conversation, index) => (
            <Grid item xs={12} sm={6} lg={4} xl={3} key={conversation.conversation_id}>
              <Fade in={true} timeout={300} style={{ transitionDelay: `${index * 50}ms` }}>
                <div>
                  <ConversationCard conversation={conversation} onDelete={handleDelete} />
                </div>
              </Fade>
            </Grid>
          ))}
        </Grid>
      )}

      {/* Enhanced Delete Confirmation Dialog */}
      <Dialog
        open={deleteDialogOpen}
        onClose={() => setDeleteDialogOpen(false)}
        maxWidth="sm"
        fullWidth
        PaperProps={{
          sx: {
            background: 'linear-gradient(135deg, #1e293b 0%, #334155 100%)',
            border: '1px solid #475569'
          }
        }}
      >
        <DialogTitle sx={{ 
          color: '#f8fafc', 
          fontWeight: 600,
          borderBottom: '1px solid #334155',
          pb: 2
        }}>
          <Stack direction="row" alignItems="center" spacing={2}>
            <Avatar sx={{ backgroundColor: '#ef4444', width: 40, height: 40 }}>
              <DeleteIcon />
            </Avatar>
            <Box>
              <Typography variant="h6" sx={{ color: '#f8fafc' }}>
                Delete Conversation
              </Typography>
              <Typography variant="caption" sx={{ color: '#94a3b8' }}>
                This action cannot be undone
              </Typography>
            </Box>
          </Stack>
        </DialogTitle>
        
        <DialogContent sx={{ pt: 3 }}>
          <Alert 
            severity="warning" 
            sx={{ 
              mb: 3,
              backgroundColor: 'rgba(245, 158, 11, 0.1)',
              border: '1px solid rgba(245, 158, 11, 0.3)',
              color: '#f8fafc'
            }}
          >
            This will permanently delete the conversation and all associated data.
          </Alert>
          
          <Typography sx={{ color: '#e2e8f0', mb: 2 }}>
            Are you sure you want to delete this conversation?
          </Typography>
          
          {conversationToDelete && (
            <Box 
              sx={{ 
                p: 3, 
                backgroundColor: '#0f172a', 
                borderRadius: 2,
                border: '1px solid #334155'
              }}
            >
              <Typography variant="caption" sx={{ color: '#94a3b8', display: 'block', mb: 1 }}>
                Conversation ID
              </Typography>
              <Typography sx={{ 
                color: '#f8fafc', 
                fontFamily: 'monospace',
                fontSize: '1.1rem',
                fontWeight: 600
              }}>
                {conversationToDelete.conversation_id}
              </Typography>
            </Box>
          )}
        </DialogContent>
        
        <DialogActions sx={{ p: 3, pt: 1 }}>
          <Button 
            onClick={() => setDeleteDialogOpen(false)}
            variant="outlined"
            sx={{ color: '#cbd5e1', borderColor: '#475569' }}
          >
            Cancel
          </Button>
          <Button 
            onClick={confirmDelete}
            variant="contained"
            color="error"
            sx={{
              background: 'linear-gradient(135deg, #ef4444 0%, #dc2626 100%)',
              '&:hover': {
                background: 'linear-gradient(135deg, #dc2626 0%, #b91c1c 100%)'
              }
            }}
          >
            Delete Conversation
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}

export default Conversations 