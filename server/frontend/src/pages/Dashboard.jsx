import { useState, useEffect } from 'react'
import {
  Grid,
  Card,
  CardContent,
  Typography,
  Box,
  CircularProgress,
  Alert
} from '@mui/material'
import {
  Chat as ChatIcon,
  Memory as MemoryIcon,
  Person as PersonIcon,
  SmartToy as AgentIcon
} from '@mui/icons-material'
import { api } from '../api/client'

function StatsCard({ title, value, subtitle, icon: Icon, color = 'primary' }) {
  return (
    <Card sx={{ height: '100%' }}>
      <CardContent>
        <Box sx={{ display: 'flex', alignItems: 'center' }}>
          <Box sx={{ flex: 1 }}>
            <Typography color="textSecondary" gutterBottom variant="overline">
              {title}
            </Typography>
            <Typography variant="h4" component="h2">
              {value}
            </Typography>
            <Typography color="textSecondary" variant="body2">
              {subtitle}
            </Typography>
          </Box>
          <Box sx={{ ml: 2 }}>
            <Icon sx={{ fontSize: 48, color: `${color}.main` }} />
          </Box>
        </Box>
      </CardContent>
    </Card>
  )
}

function Dashboard() {
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    const fetchStats = async () => {
      try {
        setLoading(true)
        setError(null)
        const response = await api.getStats()
        setStats(response.data)
      } catch (err) {
        setError(err.message || 'Failed to fetch statistics')
      } finally {
        setLoading(false)
      }
    }

    fetchStats()
  }, [])

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}>
        <CircularProgress />
      </Box>
    )
  }

  if (error) {
    return (
      <Alert severity="error" sx={{ mt: 2 }}>
        {error}
      </Alert>
    )
  }

  if (!stats) {
    return (
      <Alert severity="warning" sx={{ mt: 2 }}>
        No statistics available
      </Alert>
    )
  }

  return (
    <Box>
      <Typography variant="h4" component="h1" gutterBottom>
        System Overview
      </Typography>
      
      <Grid container spacing={3}>
        {/* Conversation Statistics */}
        <Grid item xs={12} sm={6} md={3}>
          <StatsCard
            title="Total Conversations"
            value={stats.conversations.total}
            subtitle={`Today: ${stats.conversations.today} | This Week: ${stats.conversations.this_week}`}
            icon={ChatIcon}
            color="primary"
          />
        </Grid>

        {/* Memory Statistics */}
        <Grid item xs={12} sm={6} md={3}>
          <StatsCard
            title="Total Memories"
            value={stats.memories.total}
            subtitle={`Updated Today: ${stats.memories.updated_today} | This Week: ${stats.memories.updated_this_week}`}
            icon={MemoryIcon}
            color="secondary"
          />
        </Grid>

        {/* Agent Count */}
        <Grid item xs={12} sm={6} md={3}>
          <StatsCard
            title="Agent Count"
            value={stats.agents.total}
            subtitle={`Active Today: ${stats.agents.active_today}`}
            icon={AgentIcon}
            color="success"
          />
        </Grid>

        {/* User Count */}
        <Grid item xs={12} sm={6} md={3}>
          <StatsCard
            title="User Count"
            value={stats.users.total}
            subtitle={`Active Today: ${stats.users.active_today}`}
            icon={PersonIcon}
            color="warning"
          />
        </Grid>
      </Grid>

      {/* Conversation Statistics Detail */}
      <Grid container spacing={3} sx={{ mt: 2 }}>
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Conversation Statistics Detail
              </Typography>
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                <Typography variant="body2">
                  Total Conversations: <strong>{stats.conversations.total}</strong>
                </Typography>
                <Typography variant="body2">
                  Today Conversations: <strong>{stats.conversations.today}</strong>
                </Typography>
                <Typography variant="body2">
                  Conversations This Week: <strong>{stats.conversations.this_week}</strong>
                </Typography>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Memory Statistics Detail
              </Typography>
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                <Typography variant="body2">
                  Total Memories: <strong>{stats.memories.total}</strong>
                </Typography>
                <Typography variant="body2">
                  Updated Today: <strong>{stats.memories.updated_today}</strong>
                </Typography>
                <Typography variant="body2">
                  Updated This Week: <strong>{stats.memories.updated_this_week}</strong>
                </Typography>
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  )
}

export default Dashboard 