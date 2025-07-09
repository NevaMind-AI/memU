import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import {
  Box,
  Typography,
  Card,
  CardContent,
  CardActions,
  Button,
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
  TextField,
  InputAdornment,
  Chip,
  Avatar,
  Fade,
  Tooltip,
  Divider,
  Stack,
  Badge
} from '@mui/material'
import {
  Visibility as VisibilityIcon,
  Delete as DeleteIcon,
  Search as SearchIcon,
  Memory as MemoryIcon,
  Person as PersonIcon,
  SmartToy as AgentIcon,
  Event as EventIcon,
  Description as ProfileIcon,
  Schedule as TimeIcon,
  Clear as ClearIcon,
  FilterList as FilterIcon,
  Refresh as RefreshIcon,
  TrendingUp as TrendingIcon
} from '@mui/icons-material'
import { api } from '../api/client'

function MemoryCard({ memory, onDelete }) {
  const formatDate = (dateString) => {
    if (!dateString) return '-'
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  const getMemoryScore = (memory) => {
    const eventCount = memory.event_count || 0
    const profileLength = memory.profile_length || 0
    return Math.min(100, Math.round((eventCount * 10 + profileLength / 10) / 2))
  }

  const getScoreColor = (score) => {
    if (score >= 80) return '#10b981'
    if (score >= 60) return '#f59e0b'
    if (score >= 40) return '#ef4444'
    return '#64748b'
  }

  const getScoreGradient = (score) => {
    if (score >= 80) return 'linear-gradient(135deg, #10b981 0%, #059669 100%)'
    if (score >= 60) return 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)'
    if (score >= 40) return 'linear-gradient(135deg, #ef4444 0%, #dc2626 100%)'
    return 'linear-gradient(135deg, #64748b 0%, #475569 100%)'
  }

  const score = getMemoryScore(memory)

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
        {/* Score Badge */}
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
              background: getScoreGradient(score),
              fontSize: '0.875rem',
              fontWeight: 700,
              boxShadow: '0 4px 12px rgba(0, 0, 0, 0.2)',
              border: '2px solid rgba(255, 255, 255, 0.1)'
            }}
          >
            {score}
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
                  background: 'linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%)',
                  boxShadow: '0 8px 25px -5px rgba(99, 102, 241, 0.4)'
                }}
              >
                <MemoryIcon sx={{ fontSize: 22 }} />
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
                  {memory.memory_id}
                </Typography>
                <Typography variant="caption" sx={{ color: '#94a3b8', fontWeight: 500 }}>
                  Memory Instance
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
                  background: 'linear-gradient(135deg, rgba(99, 102, 241, 0.1) 0%, rgba(139, 92, 246, 0.05) 100%)',
                  border: '1px solid rgba(99, 102, 241, 0.2)'
                }}
              >
                <Stack direction="row" alignItems="center" spacing={1.5}>
                  <AgentIcon sx={{ fontSize: 18, color: '#6366f1' }} />
                  <Box>
                    <Typography variant="body2" sx={{ color: '#f8fafc', fontWeight: 500 }}>
                      {memory.agent_id}
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
                      {memory.user_id}
                    </Typography>
                    <Typography variant="caption" sx={{ color: '#94a3b8' }}>
                      User
                    </Typography>
                  </Box>
                </Stack>
              </Box>
            </Grid>
          </Grid>

          {/* Stats */}
          <Grid container spacing={2} sx={{ mb: 3 }}>
            <Grid item xs={6}>
              <Stack alignItems="center" spacing={1}>
                <Stack direction="row" alignItems="center" spacing={1}>
                  <EventIcon sx={{ fontSize: 16, color: '#f59e0b' }} />
                  <Typography variant="caption" sx={{ color: '#94a3b8', fontWeight: 500 }}>
                    Events
                  </Typography>
                </Stack>
                <Typography variant="h6" sx={{ fontWeight: 600, color: '#f8fafc' }}>
                  {memory.event_count || 0}
                </Typography>
              </Stack>
            </Grid>
            
            <Grid item xs={6}>
              <Stack alignItems="center" spacing={1}>
                <Stack direction="row" alignItems="center" spacing={1}>
                  <ProfileIcon sx={{ fontSize: 16, color: '#3b82f6' }} />
                  <Typography variant="caption" sx={{ color: '#94a3b8', fontWeight: 500 }}>
                    Profile Size
                  </Typography>
                </Stack>
                <Typography variant="h6" sx={{ fontWeight: 600, color: '#f8fafc' }}>
                  {memory.profile_length || 0}
                </Typography>
              </Stack>
            </Grid>
          </Grid>

          {/* Timestamps */}
          <Stack spacing={1}>
            <Stack direction="row" alignItems="center" spacing={1.5}>
              <TimeIcon sx={{ fontSize: 14, color: '#10b981' }} />
              <Typography variant="caption" sx={{ color: '#cbd5e1' }}>
                Created: {formatDate(memory.created_at)}
              </Typography>
            </Stack>
            <Stack direction="row" alignItems="center" spacing={1.5}>
              <TimeIcon sx={{ fontSize: 14, color: '#f59e0b' }} />
              <Typography variant="caption" sx={{ color: '#cbd5e1' }}>
                Updated: {formatDate(memory.updated_at)}
              </Typography>
            </Stack>
          </Stack>
        </CardContent>

        <Divider sx={{ borderColor: '#334155' }} />

        <CardActions sx={{ justifyContent: 'space-between', px: 3, py: 2 }}>
          <Button
            component={Link}
            to={`/memories/${memory.memory_id}`}
            variant="contained"
            size="small"
            startIcon={<VisibilityIcon />}
            sx={{
              background: 'linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%)',
              '&:hover': {
                background: 'linear-gradient(135deg, #5b5bd6 0%, #7c3aed 100%)',
                transform: 'translateY(-1px)',
                boxShadow: '0 8px 25px -5px rgba(99, 102, 241, 0.4)'
              }
            }}
          >
            View Details
          </Button>
          
          <Tooltip title="Delete Memory" placement="top">
            <IconButton
              size="small"
              onClick={() => onDelete(memory)}
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

function Memories() {
  const [memories, setMemories] = useState([])
  const [filteredMemories, setFilteredMemories] = useState([])
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
  const [memoryToDelete, setMemoryToDelete] = useState(null)

  const fetchData = async () => {
    try {
      setLoading(true)
      setError(null)
      const response = await api.get('/api/memories')
      setMemories(response.data)
      setFilteredMemories(response.data)
    } catch (err) {
      setError('Failed to fetch memories')
      console.error('Fetch memories error:', err)
    } finally {
      setLoading(false)
    }
  }

  const fetchFilters = async () => {
    try {
      const [agentsRes, usersRes] = await Promise.all([
        api.getAgents(),
        api.getUsers()
      ])
      setAgents(agentsRes.data)
      setUsers(usersRes.data)
    } catch (err) {
      console.error('Fetch filters error:', err)
    }
  }

  const handleFilterChange = (key, value) => {
    if (key === 'search') setSearchTerm(value)
    if (key === 'agent') setAgentFilter(value)
    if (key === 'user') setUserFilter(value)
  }

  const handleDelete = async (memory) => {
    setMemoryToDelete(memory)
    setDeleteDialogOpen(true)
  }

  const confirmDelete = async () => {
    if (!memoryToDelete) return
    
    try {
      await api.delete(`/api/memories/${memoryToDelete.memory_id}`)
      await fetchData()
      setDeleteDialogOpen(false)
      setMemoryToDelete(null)
    } catch (err) {
      console.error('Delete error:', err)
      setError('Failed to delete memory')
    }
  }

  const clearFilters = () => {
    setSearchTerm('')
    setAgentFilter('')
    setUserFilter('')
  }

  const hasActiveFilters = searchTerm || agentFilter || userFilter

  // Filter memories when filters change
  useEffect(() => {
    let filtered = memories

    if (searchTerm) {
      filtered = filtered.filter(memory =>
        memory.memory_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
        memory.agent_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
        memory.user_id.toLowerCase().includes(searchTerm.toLowerCase())
      )
    }

    if (agentFilter) {
      filtered = filtered.filter(memory => memory.agent_id === agentFilter)
    }

    if (userFilter) {
      filtered = filtered.filter(memory => memory.user_id === userFilter)
    }

    setFilteredMemories(filtered)
  }, [memories, searchTerm, agentFilter, userFilter])

  useEffect(() => {
    fetchData()
    fetchFilters()
  }, [])

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
        <CircularProgress size={48} sx={{ color: '#6366f1' }} />
        <Typography variant="body2" sx={{ color: '#94a3b8' }}>
          Loading memory data...
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
            Memory Management
          </Typography>
          <Typography variant="body1" sx={{ color: '#94a3b8' }}>
            Explore and manage agent memories across the system
          </Typography>
        </Box>
        
        <Stack direction="row" spacing={1}>
          <IconButton 
            onClick={fetchData}
            sx={{ 
              color: '#94a3b8',
              '&:hover': { 
                color: '#6366f1',
                backgroundColor: 'rgba(99, 102, 241, 0.1)'
              }
            }}
          >
            <RefreshIcon />
          </IconButton>
          
          <Chip
            icon={<TrendingIcon />}
            label={`${memories.length} Total`}
            sx={{
              background: 'linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%)',
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
            <FilterIcon sx={{ color: '#6366f1' }} />
            <Typography variant="h6" sx={{ color: '#f8fafc', fontWeight: 600 }}>
              Search & Filter
            </Typography>
            {hasActiveFilters && (
              <Badge
                badgeContent={[searchTerm, agentFilter, userFilter].filter(Boolean).length}
                color="primary"
                sx={{
                  '& .MuiBadge-badge': {
                    backgroundColor: '#6366f1',
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
                placeholder="Search by memory ID, agent, or user..."
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
                  label={`${filteredMemories.length} Results`}
                  sx={{
                    backgroundColor: filteredMemories.length > 0 ? '#10b981' : '#64748b',
                    color: '#ffffff',
                    fontWeight: 600
                  }}
                />
              </Stack>
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      {/* Memory Cards */}
      {filteredMemories.length === 0 ? (
        <Card sx={{ textAlign: 'center', py: 8 }}>
          <CardContent>
            <MemoryIcon sx={{ fontSize: 80, color: '#475569', mb: 3 }} />
            <Typography variant="h5" sx={{ color: '#cbd5e1', mb: 2, fontWeight: 600 }}>
              {memories.length === 0 ? 'No Memories Found' : 'No Results Found'}
            </Typography>
            <Typography variant="body1" sx={{ color: '#94a3b8', mb: 3 }}>
              {memories.length === 0 
                ? 'No memories have been created yet. Start by creating your first memory instance.'
                : 'Try adjusting your search criteria or clearing the filters to see more results.'
              }
            </Typography>
            {hasActiveFilters && (
              <Button
                variant="contained"
                onClick={clearFilters}
                sx={{
                  background: 'linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%)',
                  '&:hover': {
                    background: 'linear-gradient(135deg, #5b5bd6 0%, #7c3aed 100%)'
                  }
                }}
              >
                Clear All Filters
              </Button>
            )}
          </CardContent>
        </Card>
      ) : (
        <Box
          sx={{
            display: 'grid',
            gap: 3,
            width: '100%',
            gridTemplateColumns: {
              xs: 'repeat(auto-fit, minmax(300px, 1fr))',
              sm: 'repeat(auto-fit, minmax(300px, 1fr))',
              md: 'repeat(auto-fit, minmax(320px, 1fr))',
              lg: 'repeat(auto-fit, minmax(340px, 1fr))',
              xl: 'repeat(auto-fit, minmax(360px, 1fr))'
            },
            overflowX: 'hidden'
          }}
        >
          {filteredMemories.map((memory, index) => (
            <Fade key={memory.memory_id} in={true} timeout={300} style={{ transitionDelay: `${index * 50}ms` }}>
              <div>
                <MemoryCard memory={memory} onDelete={handleDelete} />
              </div>
            </Fade>
          ))}
        </Box>
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
                Delete Memory
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
            This will permanently delete the memory and all associated data.
          </Alert>
          
          <Typography sx={{ color: '#e2e8f0', mb: 2 }}>
            Are you sure you want to delete this memory instance?
          </Typography>
          
          {memoryToDelete && (
            <Box 
              sx={{ 
                p: 3, 
                backgroundColor: '#0f172a', 
                borderRadius: 2,
                border: '1px solid #334155'
              }}
            >
              <Typography variant="caption" sx={{ color: '#94a3b8', display: 'block', mb: 1 }}>
                Memory ID
              </Typography>
              <Typography sx={{ 
                color: '#f8fafc', 
                fontFamily: 'monospace',
                fontSize: '1.1rem',
                fontWeight: 600
              }}>
                {memoryToDelete.memory_id}
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
            Delete Memory
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}

export default Memories 