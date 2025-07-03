import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import {
  Box,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
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
  DialogActions
} from '@mui/material'
import {
  Visibility as VisibilityIcon,
  Delete as DeleteIcon
} from '@mui/icons-material'
import { api } from '../api/client'

function Conversations() {
  const [conversations, setConversations] = useState([])
  const [agents, setAgents] = useState([])
  const [users, setUsers] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [page, setPage] = useState(1)
  const [filters, setFilters] = useState({
    agent_id: '',
    user_id: '',
  })
  const [deleteDialog, setDeleteDialog] = useState({ open: false, conversation: null })

  useEffect(() => {
    fetchData()
  }, [page, filters])

  useEffect(() => {
    fetchFilters()
  }, [])

  const fetchData = async () => {
    try {
      setLoading(true)
      setError(null)
      const params = {
        page,
        per_page: 20,
        ...filters
      }
      const response = await api.getConversations(params)
      setConversations(response.data)
    } catch (err) {
      setError(err.message || 'Failed to get conversation list')
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
      console.error('Failed to get filter options:', err)
    }
  }

  const handleFilterChange = (key, value) => {
    setFilters(prev => ({ ...prev, [key]: value }))
    setPage(1) // reset to first page
  }

  const handleDelete = async (conversation) => {
    try {
      await api.deleteConversation(conversation.conversation_id)
      setDeleteDialog({ open: false, conversation: null })
      fetchData() // reload data
    } catch (err) {
      console.error('Failed to delete conversation:', err)
      alert('Delete failed: ' + (err.message || 'Unknown error'))
    }
  }

  const formatDate = (dateString) => {
    if (!dateString) return '-'
    return new Date(dateString).toLocaleString('zh-CN')
  }

  if (loading && conversations.length === 0) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}>
        <CircularProgress />
      </Box>
    )
  }

  return (
    <Box>
      <Typography variant="h4" component="h1" gutterBottom>
        Conversation Management
      </Typography>

      {/* Filter */}
      <Paper sx={{ p: 2, mb: 3 }}>
        <Grid container spacing={2} alignItems="center">
          <Grid item xs={12} md={4}>
            <FormControl fullWidth>
              <InputLabel>Agent</InputLabel>
              <Select
                value={filters.agent_id}
                onChange={(e) => handleFilterChange('agent_id', e.target.value)}
                label="Agent"
              >
                <MenuItem value="">All</MenuItem>
                {agents.map(agent => (
                  <MenuItem key={agent} value={agent}>{agent}</MenuItem>
                ))}
              </Select>
            </FormControl>
          </Grid>
          <Grid item xs={12} md={4}>
            <FormControl fullWidth>
              <InputLabel>User</InputLabel>
              <Select
                value={filters.user_id}
                onChange={(e) => handleFilterChange('user_id', e.target.value)}
                label="User"
              >
                <MenuItem value="">All</MenuItem>
                {users.map(user => (
                  <MenuItem key={user} value={user}>{user}</MenuItem>
                ))}
              </Select>
            </FormControl>
          </Grid>
          <Grid item xs={12} md={4}>
            <Button
              variant="outlined"
              onClick={() => {
                setFilters({ agent_id: '', user_id: '' })
                setPage(1)
              }}
            >
              Reset Filter
            </Button>
          </Grid>
        </Grid>
      </Paper>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      {/* Conversation List */}
      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Conversation ID</TableCell>
              <TableCell>Agent ID</TableCell>
              <TableCell>User ID</TableCell>
              <TableCell>Created Time</TableCell>
              <TableCell>Turn Count</TableCell>
              <TableCell>Summary</TableCell>
              <TableCell>Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {conversations.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} align="center">
                  {loading ? <CircularProgress size={24} /> : 'No data'}
                </TableCell>
              </TableRow>
            ) : (
              conversations.map((conversation) => (
                <TableRow key={conversation.conversation_id} hover>
                  <TableCell>
                    <Typography variant="body2" sx={{ fontFamily: 'monospace' }}>
                      {conversation.conversation_id.slice(0, 8)}...
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Chip 
                      label={conversation.agent_id} 
                      size="small" 
                      color="primary"
                      variant="outlined"
                    />
                  </TableCell>
                  <TableCell>
                    <Chip 
                      label={conversation.user_id} 
                      size="small" 
                      color="secondary"
                      variant="outlined"
                    />
                  </TableCell>
                  <TableCell>{formatDate(conversation.created_at)}</TableCell>
                  <TableCell>
                    <Chip 
                      label={conversation.turn_count || 0} 
                      size="small"
                    />
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2" sx={{ maxWidth: 200 }}>
                      {conversation.summary ? 
                        (conversation.summary.length > 50 ? 
                          conversation.summary.slice(0, 50) + '...' : 
                          conversation.summary
                        ) : '-'
                      }
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <IconButton
                      component={Link}
                      to={`/conversations/${conversation.conversation_id}`}
                      color="primary"
                      size="small"
                    >
                      <VisibilityIcon />
                    </IconButton>
                    <IconButton
                      onClick={() => setDeleteDialog({ open: true, conversation })}
                      color="error"
                      size="small"
                    >
                      <DeleteIcon />
                    </IconButton>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </TableContainer>

      {/* Pagination */}
      <Box sx={{ display: 'flex', justifyContent: 'center', mt: 3 }}>
        <Button
          disabled={page === 1}
          onClick={() => setPage(p => p - 1)}
          sx={{ mr: 2 }}
        >
          Previous Page
        </Button>
        <Typography sx={{ alignSelf: 'center', mx: 2 }}>
          Page {page}
        </Typography>
        <Button
          disabled={conversations.length < 20}
          onClick={() => setPage(p => p + 1)}
        >
          Next Page
        </Button>
      </Box>

      {/* Delete Confirmation Dialog */}
      <Dialog
        open={deleteDialog.open}
        onClose={() => setDeleteDialog({ open: false, conversation: null })}
      >
        <DialogTitle>Confirm Delete</DialogTitle>
        <DialogContent>
          Are you sure you want to delete conversation {deleteDialog.conversation?.conversation_id.slice(0, 8)}... ?
          This operation cannot be undone.
        </DialogContent>
        <DialogActions>
          <Button 
            onClick={() => setDeleteDialog({ open: false, conversation: null })}
          >
            Cancel
          </Button>
          <Button 
            onClick={() => handleDelete(deleteDialog.conversation)}
            color="error"
            variant="contained"
          >
            Delete
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}

export default Conversations 