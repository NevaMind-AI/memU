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
  Divider
} from '@mui/material'
import {
  ArrowBack as ArrowBackIcon,
  Person as PersonIcon,
  SmartToy as BotIcon
} from '@mui/icons-material'
import { api } from '../api/client'

function MessageCard({ message }) {
  const isUser = message.role === 'user'
  const isAssistant = message.role === 'assistant'
  
  return (
    <Paper 
      sx={{ 
        p: 2, 
        mb: 2,
        backgroundColor: isUser ? 'primary.light' : 
                         isAssistant ? 'surface.main' : 'warning.light',
        color: isUser ? 'primary.contrastText' : 'text.primary'
      }}
    >
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
        {isUser ? <PersonIcon sx={{ mr: 1 }} /> : 
         isAssistant ? <BotIcon sx={{ mr: 1 }} /> : 
         <Typography sx={{ mr: 1 }}>🔧</Typography>}
        <Typography variant="subtitle2" sx={{ textTransform: 'capitalize' }}>
          {message.role}
        </Typography>
        <Typography variant="caption" sx={{ ml: 'auto' }}>
          #{message.message_index}
        </Typography>
      </Box>
      <Typography variant="body1" sx={{ whiteSpace: 'pre-wrap' }}>
        {message.content}
      </Typography>
      {message.created_at && (
        <Typography variant="caption" sx={{ mt: 1, display: 'block', opacity: 0.7 }}>
          {new Date(message.created_at).toLocaleString('zh-CN')}
        </Typography>
      )}
    </Paper>
  )
}

function ConversationDetail() {
  const { id } = useParams()
  const [conversation, setConversation] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    const fetchConversation = async () => {
      try {
        setLoading(true)
        setError(null)
        const response = await api.getConversationDetail(id)
        setConversation(response.data)
      } catch (err) {
        setError(err.message || 'Failed to get conversation details')
      } finally {
        setLoading(false)
      }
    }

    if (id) {
      fetchConversation()
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
          to="/conversations"
          startIcon={<ArrowBackIcon />}
          sx={{ mb: 2 }}
        >
          Back to Conversation List
        </Button>
        <Alert severity="error">{error}</Alert>
      </Box>
    )
  }

  if (!conversation) {
    return (
      <Box>
        <Button
          component={Link}
          to="/conversations"
          startIcon={<ArrowBackIcon />}
          sx={{ mb: 2 }}
        >
          Back to Conversation List
        </Button>
        <Alert severity="warning">Conversation not found</Alert>
      </Box>
    )
  }

  const formatDate = (dateString) => {
    if (!dateString) return '-'
    return new Date(dateString).toLocaleString('zh-CN')
  }

  return (
    <Box>
      <Button
        component={Link}
        to="/conversations"
        startIcon={<ArrowBackIcon />}
        sx={{ mb: 2 }}
      >
        Back to Conversation List
      </Button>

      <Typography variant="h4" component="h1" gutterBottom>
        Conversation Details
      </Typography>

      {/* Conversation Basic Information */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Grid container spacing={2}>
            <Grid item xs={12} md={6}>
              <Typography variant="subtitle2" color="textSecondary">
                Conversation ID
              </Typography>
              <Typography variant="body1" sx={{ fontFamily: 'monospace', mb: 2 }}>
                {conversation.conversation_id}
              </Typography>
              
              <Typography variant="subtitle2" color="textSecondary">
                Agent ID
              </Typography>
              <Chip 
                label={conversation.agent_id} 
                color="primary" 
                sx={{ mb: 2 }}
              />
              
              <Typography variant="subtitle2" color="textSecondary">
                User ID
              </Typography>
              <Chip 
                label={conversation.user_id} 
                color="secondary" 
                sx={{ mb: 2 }}
              />
            </Grid>
            
            <Grid item xs={12} md={6}>
              <Typography variant="subtitle2" color="textSecondary">
                Created Time
              </Typography>
              <Typography variant="body1" sx={{ mb: 2 }}>
                {formatDate(conversation.created_at)}
              </Typography>
              
              <Typography variant="subtitle2" color="textSecondary">
                Turn Count
              </Typography>
              <Typography variant="body1" sx={{ mb: 2 }}>
                {conversation.turn_count || 0}
              </Typography>
              
              {conversation.session_id && (
                <>
                  <Typography variant="subtitle2" color="textSecondary">
                    Session ID
                  </Typography>
                  <Typography variant="body1" sx={{ fontFamily: 'monospace', mb: 2 }}>
                    {conversation.session_id}
                  </Typography>
                </>
              )}
              
              {conversation.memory_id && (
                <>
                  <Typography variant="subtitle2" color="textSecondary">
                    Associated Memory ID
                  </Typography>
                  <Typography variant="body1" sx={{ fontFamily: 'monospace', mb: 2 }}>
                    {conversation.memory_id}
                  </Typography>
                </>
              )}
            </Grid>
          </Grid>
          
          {conversation.summary && (
            <>
              <Divider sx={{ my: 2 }} />
              <Typography variant="subtitle2" color="textSecondary">
                Conversation Summary
              </Typography>
              <Typography variant="body1" sx={{ mt: 1 }}>
                {conversation.summary}
              </Typography>
            </>
          )}
        </CardContent>
      </Card>

      {/* Conversation Messages */}
      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Conversation Messages ({conversation.messages?.length || 0} messages)
          </Typography>
          
          {conversation.messages && conversation.messages.length > 0 ? (
            <Box>
              {conversation.messages
                .sort((a, b) => a.message_index - b.message_index)
                .map((message) => (
                  <MessageCard key={message.message_id} message={message} />
                ))}
            </Box>
          ) : (
            <Alert severity="info">
              No message records found for this conversation
            </Alert>
          )}
        </CardContent>
      </Card>
    </Box>
  )
}

export default ConversationDetail 