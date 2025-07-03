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

function Memories() {
  const [memories, setMemories] = useState([])
  const [agents, setAgents] = useState([])
  const [users, setUsers] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [page, setPage] = useState(1)
  const [filters, setFilters] = useState({
    agent_id: '',
    user_id: '',
  })
  const [deleteDialog, setDeleteDialog] = useState({ open: false, memory: null })

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
      const response = await api.getMemories(params)
      setMemories(response.data)
    } catch (err) {
      setError(err.message || 'Failed to fetch memory list')
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

  const handleDelete = async (memory) => {
    try {
      await api.deleteMemory(memory.memory_id)
      setDeleteDialog({ open: false, memory: null })
      fetchData() // reload data
    } catch (err) {
      console.error('Failed to delete memory:', err)
      alert('Delete failed: ' + (err.message || 'Unknown error'))
    }
  }

  const formatDate = (dateString) => {
    if (!dateString) return '-'
    return new Date(dateString).toLocaleString('en-US')
  }

  if (loading && memories.length === 0) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}>
        <CircularProgress />
      </Box>
    )
  }

  return (
    <Box>
      <Typography variant="h4" component="h1" gutterBottom>
        Memory Management
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

      {/* Memory List */}
      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Memory ID</TableCell>
              <TableCell>Agent ID</TableCell>
              <TableCell>User ID</TableCell>
              <TableCell>Created Time</TableCell>
              <TableCell>Updated Time</TableCell>
              <TableCell>Event Count</TableCell>
              <TableCell>Profile Length</TableCell>
              <TableCell>Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {memories.length === 0 ? (
              <TableRow>
                <TableCell colSpan={8} align="center">
                  {loading ? <CircularProgress size={24} /> : 'No data'}
                </TableCell>
              </TableRow>
            ) : (
              memories.map((memory) => (
                <TableRow key={memory.memory_id} hover>
                  <TableCell>
                    <Typography variant="body2" sx={{ fontFamily: 'monospace' }}>
                      {memory.memory_id.slice(0, 8)}...
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Chip 
                      label={memory.agent_id} 
                      size="small" 
                      color="primary"
                      variant="outlined"
                    />
                  </TableCell>
                  <TableCell>
                    <Chip 
                      label={memory.user_id} 
                      size="small" 
                      color="secondary"
                      variant="outlined"
                    />
                  </TableCell>
                  <TableCell>{formatDate(memory.created_at)}</TableCell>
                  <TableCell>{formatDate(memory.updated_at)}</TableCell>
                  <TableCell>
                    <Chip 
                      label={memory.event_count || 0} 
                      size="small"
                      color="info"
                    />
                  </TableCell>
                  <TableCell>
                    <Chip 
                      label={memory.profile_content ? memory.profile_content.length : 0} 
                      size="small"
                      color="success"
                    />
                  </TableCell>
                  <TableCell>
                    <IconButton
                      component={Link}
                      to={`/memories/${memory.memory_id}`}
                      color="primary"
                      size="small"
                    >
                      <VisibilityIcon />
                    </IconButton>
                    <IconButton
                      onClick={() => setDeleteDialog({ open: true, memory })}
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
          disabled={memories.length < 20}
          onClick={() => setPage(p => p + 1)}
        >
          Next Page
        </Button>
      </Box>

      {/* Delete Confirmation Dialog */}
      <Dialog
        open={deleteDialog.open}
        onClose={() => setDeleteDialog({ open: false, memory: null })}
      >
        <DialogTitle>Confirm Delete</DialogTitle>
        <DialogContent>
           Are you sure you want to delete memory {deleteDialog.memory?.memory_id.slice(0, 8)}... ?
           This action cannot be undone.
        </DialogContent>
        <DialogActions>
          <Button 
            onClick={() => setDeleteDialog({ open: false, memory: null })}
          >
            Cancel
          </Button>
          <Button 
            onClick={() => handleDelete(deleteDialog.memory)}
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

export default Memories 