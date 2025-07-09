import { useState, useEffect } from 'react'
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
  CircularProgress,
  Alert
} from '@mui/material'
import { api } from '../api/client'

function MemoryOperations() {
  const [operations, setOperations] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [page, setPage] = useState(1)

  useEffect(() => {
    fetchData()
  }, [page])

  const fetchData = async () => {
    try {
      setLoading(true)
      setError(null)
      const params = {
        page,
        per_page: 50,
      }
      const response = await api.getMemoryOperations(params)
      setOperations(response.data)
    } catch (err) {
      setError(err.message || 'Failed to fetch operation records')
    } finally {
      setLoading(false)
    }
  }

  const formatDate = (dateString) => {
    if (!dateString) return '-'
    return new Date(dateString).toLocaleString('en-US')
  }

  const getOperationColor = (operationType) => {
    switch (operationType) {
      case 'CREATE':
        return 'success'
      case 'UPDATE':
        return 'warning'
      case 'DELETE':
        return 'error'
      default:
        return 'default'
    }
  }

  if (loading && operations.length === 0) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}>
        <CircularProgress />
      </Box>
    )
  }

  return (
    <Box>
      <Typography variant="h4" component="h1" gutterBottom>
        Memory Operation Records
      </Typography>

      <Typography variant="body2" color="textSecondary" sx={{ mb: 3 }}>
        Shows the history of memory creation, update, and delete operations
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      {/* Operation list */}
      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Timestamp</TableCell>
              <TableCell>Operation Type</TableCell>
              <TableCell>Memory ID</TableCell>
              <TableCell>Agent ID</TableCell>
              <TableCell>User ID</TableCell>
              <TableCell>Details</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {operations.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6} align="center">
                  {loading ? <CircularProgress size={24} /> : 'No data'}
                </TableCell>
              </TableRow>
            ) : (
              operations.map((operation) => (
                <TableRow key={operation.operation_id} hover>
                  <TableCell>
                    <Typography variant="body2">
                      {formatDate(operation.timestamp)}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Chip 
                      label={operation.operation_type} 
                      size="small" 
                      color={getOperationColor(operation.operation_type)}
                      variant="outlined"
                    />
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2" sx={{ fontFamily: 'monospace' }}>
                      {operation.memory_id.slice(0, 8)}...
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Chip 
                      label={operation.agent_id} 
                      size="small" 
                      color="primary"
                      variant="outlined"
                    />
                  </TableCell>
                  <TableCell>
                    <Chip 
                      label={operation.user_id} 
                      size="small" 
                      color="secondary"
                      variant="outlined"
                    />
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2" sx={{ maxWidth: 300 }}>
                      {operation.details}
                    </Typography>
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
          disabled={operations.length < 50}
          onClick={() => setPage(p => p + 1)}
        >
          Next Page
        </Button>
      </Box>

      {/* Operation Type Legend */}
      <Paper sx={{ p: 2, mt: 3 }}>
        <Typography variant="h6" gutterBottom>
          Operation Type Legend
        </Typography>
        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Chip label="CREATE" size="small" color="success" variant="outlined" />
            <Typography variant="body2">Memory Created</Typography>
          </Box>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Chip label="UPDATE" size="small" color="warning" variant="outlined" />
            <Typography variant="body2">Memory Updated</Typography>
          </Box>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Chip label="DELETE" size="small" color="error" variant="outlined" />
            <Typography variant="body2">Memory Deleted</Typography>
          </Box>
        </Box>
      </Paper>
    </Box>
  )
}

export default MemoryOperations 