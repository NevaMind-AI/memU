import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import {
  Box,
  Typography,
  Card,
  CardContent,
  Grid,
  Chip,
  CircularProgress,
  Alert,
  Button,
  Paper,
  Divider,
  Accordion,
  AccordionSummary,
  AccordionDetails
} from '@mui/material'
import {
  ArrowBack as ArrowBackIcon,
  ExpandMore as ExpandMoreIcon
} from '@mui/icons-material'
import { api } from '../api/client'

function MemoryDetail() {
  const { id } = useParams()
  const [memory, setMemory] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    const fetchMemory = async () => {
      try {
        setLoading(true)
        setError(null)
        const response = await api.getMemoryDetail(id)
        setMemory(response.data)
      } catch (err) {
        setError(err.message || 'Failed to get memory details')
      } finally {
        setLoading(false)
      }
    }

    if (id) {
      fetchMemory()
    }
  }, [id])

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}>
        <CircularProgress />
      </Box>
    )
  }

  if (error) {
    return (
      <Box>
        <Button
          component={Link}
          to="/memories"
          startIcon={<ArrowBackIcon />}
          sx={{ mb: 2 }}
        >
          Back to Memory List
        </Button>
        <Alert severity="error">{error}</Alert>
      </Box>
    )
  }

  if (!memory) {
    return (
      <Box>
        <Button
          component={Link}
          to="/memories"
          startIcon={<ArrowBackIcon />}
          sx={{ mb: 2 }}
        >
          Back to Memory List
        </Button>
        <Alert severity="warning">Memory not found</Alert>
      </Box>
    )
  }

  const formatDate = (dateString) => {
    if (!dateString) return '-'
    return new Date(dateString).toLocaleString('en-US')
  }

  const formatJson = (obj) => {
    if (!obj) return ''
    try {
      return JSON.stringify(obj, null, 2)
    } catch (e) {
      return String(obj)
    }
  }

  return (
    <Box>
      <Button
        component={Link}
        to="/memories"
        startIcon={<ArrowBackIcon />}
        sx={{ mb: 2 }}
      >
        Back to Memory List
      </Button>

      <Typography variant="h4" component="h1" gutterBottom>
        Memory Details
      </Typography>

      {/* Memory Basic Information */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Grid container spacing={2}>
            <Grid item xs={12} md={6}>
              <Typography variant="subtitle2" color="textSecondary">
                Memory ID
              </Typography>
              <Typography variant="body1" sx={{ fontFamily: 'monospace', mb: 2 }}>
                {memory.memory_id}
              </Typography>
              
              <Typography variant="subtitle2" color="textSecondary">
                Agent ID
              </Typography>
              <Chip 
                label={memory.agent_id} 
                color="primary" 
                sx={{ mb: 2 }}
              />
              
              <Typography variant="subtitle2" color="textSecondary">
                User ID
              </Typography>
              <Chip 
                label={memory.user_id} 
                color="secondary" 
                sx={{ mb: 2 }}
              />
            </Grid>
            
            <Grid item xs={12} md={6}>
              <Typography variant="subtitle2" color="textSecondary">
                Created Time
              </Typography>
              <Typography variant="body1" sx={{ mb: 2 }}>
                {formatDate(memory.created_at)}
              </Typography>
              
              <Typography variant="subtitle2" color="textSecondary">
                Updated Time
              </Typography>
              <Typography variant="body1" sx={{ mb: 2 }}>
                {formatDate(memory.updated_at)}
              </Typography>
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      {/* Memory Content */}
      <Box sx={{ mb: 3 }}>
        {/* Profile Content */}
        <Accordion defaultExpanded>
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Typography variant="h6">
              Profile Content {memory.profile_content && `(${memory.profile_content.length} chars)`}
            </Typography>
          </AccordionSummary>
          <AccordionDetails>
            <Paper sx={{ p: 2, backgroundColor: 'grey.50' }}>
              <Typography 
                variant="body2" 
                component="pre" 
                sx={{ 
                  whiteSpace: 'pre-wrap',
                  wordBreak: 'break-word',
                  fontFamily: 'monospace'
                }}
              >
                {memory.profile_content || 'No Profile content'}
              </Typography>
            </Paper>
          </AccordionDetails>
        </Accordion>

        {/* Event Content */}
        <Accordion>
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Typography variant="h6">
              Event Content
            </Typography>
          </AccordionSummary>
          <AccordionDetails>
            <Paper sx={{ p: 2, backgroundColor: 'grey.50' }}>
              <Typography 
                variant="body2" 
                component="pre" 
                sx={{ 
                  whiteSpace: 'pre-wrap',
                  wordBreak: 'break-word',
                  fontFamily: 'monospace'
                }}
              >
                {memory.event_content || 'No Event content'}
              </Typography>
            </Paper>
          </AccordionDetails>
        </Accordion>

        {/* Mind Content */}
        <Accordion>
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Typography variant="h6">
              Mind Content
            </Typography>
          </AccordionSummary>
          <AccordionDetails>
            <Paper sx={{ p: 2, backgroundColor: 'grey.50' }}>
              <Typography 
                variant="body2" 
                component="pre" 
                sx={{ 
                  whiteSpace: 'pre-wrap',
                  wordBreak: 'break-word',
                  fontFamily: 'monospace'
                }}
              >
                {memory.mind_content || 'No Mind content'}
              </Typography>
            </Paper>
          </AccordionDetails>
        </Accordion>

        {/* Mind Metadata */}
        {memory.mind_metadata && (
          <Accordion>
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
              <Typography variant="h6">
                Mind Metadata
              </Typography>
            </AccordionSummary>
            <AccordionDetails>
              <Paper sx={{ p: 2, backgroundColor: 'grey.50' }}>
                <Typography 
                  variant="body2" 
                  component="pre" 
                  sx={{ 
                    whiteSpace: 'pre-wrap',
                    wordBreak: 'break-word',
                    fontFamily: 'monospace'
                  }}
                >
                  {formatJson(memory.mind_metadata)}
                </Typography>
              </Paper>
            </AccordionDetails>
          </Accordion>
        )}
      </Box>

      {/* Statistics */}
      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Statistics
          </Typography>
          <Grid container spacing={2}>
            <Grid item xs={6} md={3}>
              <Typography variant="subtitle2" color="textSecondary">
                Profile Length
              </Typography>
              <Typography variant="h6">
                {memory.profile_content ? memory.profile_content.length : 0}
              </Typography>
            </Grid>
            <Grid item xs={6} md={3}>
              <Typography variant="subtitle2" color="textSecondary">
                Event Length
              </Typography>
              <Typography variant="h6">
                {memory.event_content ? memory.event_content.length : 0}
              </Typography>
            </Grid>
            <Grid item xs={6} md={3}>
              <Typography variant="subtitle2" color="textSecondary">
                Mind Length
              </Typography>
              <Typography variant="h6">
                {memory.mind_content ? memory.mind_content.length : 0}
              </Typography>
            </Grid>
            <Grid item xs={6} md={3}>
              <Typography variant="subtitle2" color="textSecondary">
                Metadata Field Count
              </Typography>
              <Typography variant="h6">
                {memory.mind_metadata ? Object.keys(memory.mind_metadata).length : 0}
              </Typography>
            </Grid>
          </Grid>
        </CardContent>
      </Card>
    </Box>
  )
}

export default MemoryDetail 