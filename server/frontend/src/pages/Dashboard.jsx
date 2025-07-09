import { useState, useEffect } from 'react'
import {
  Grid,
  Card,
  CardContent,
  Typography,
  Box,
  CircularProgress,
  Alert,
  LinearProgress,
  Avatar,
  Fade,
  Stack,
  Chip,
  IconButton,
  Divider
} from '@mui/material'
import {
  Chat as ChatIcon,
  Memory as MemoryIcon,
  Person as PersonIcon,
  SmartToy as AgentIcon,
  TrendingUp as TrendingUpIcon,
  Schedule as ScheduleIcon,
  Event as EventIcon,
  Update as UpdateIcon,
  Refresh as RefreshIcon,
  CheckCircle as CheckIcon,
  Warning as WarningIcon,
  Speed as SpeedIcon
} from '@mui/icons-material'
import { api } from '../api/client'

function MetricCard({ title, value, subtitle, icon: Icon, color = 'primary', delay = 0 }) {
  const getGradient = (color) => {
    switch (color) {
      case 'primary':
        return { from: '#6366f1', to: '#8b5cf6', shadow: 'rgba(99, 102, 241, 0.4)' }
      case 'secondary':
        return { from: '#10b981', to: '#34d399', shadow: 'rgba(16, 185, 129, 0.4)' }
      case 'warning':
        return { from: '#f59e0b', to: '#fbbf24', shadow: 'rgba(245, 158, 11, 0.4)' }
      case 'info':
        return { from: '#3b82f6', to: '#60a5fa', shadow: 'rgba(59, 130, 246, 0.4)' }
      default:
        return { from: '#64748b', to: '#94a3b8', shadow: 'rgba(100, 116, 139, 0.4)' }
    }
  }

  const getTextColor = (color) => {
    return '#ffffff';
  }
  
  const gradient = getGradient(color)
  const textColor = getTextColor(color)
  
  return (
    <Fade in={true} timeout={800} style={{ transitionDelay: `${delay}ms` }}>
      <Card sx={{ 
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        position: 'relative',
        overflow: 'hidden',
        background: `linear-gradient(135deg, ${gradient.from} 0%, ${gradient.to} 100%)`,
        color: textColor,
        boxShadow: `0 10px 25px -5px ${gradient.shadow}, 0 4px 6px -2px rgba(0, 0, 0, 0.05)`
      }}>
        {/* Decorative elements */}
        <Box sx={{
          position: 'absolute',
          top: -20,
          right: -20,
          width: 100,
          height: 100,
          borderRadius: '50%',
          background: 'rgba(255, 255, 255, 0.05)',
          transform: 'rotate(45deg)'
        }} />
        <Box sx={{
          position: 'absolute',
          bottom: -30,
          left: -15,
          width: 80,
          height: 80,
          borderRadius: '50%',
          background: 'rgba(255, 255, 255, 0.05)',
        }} />

        <CardContent sx={{ position: 'relative', zIndex: 1, flex: 1, display: 'flex', flexDirection: 'column' }}>
          <Stack direction="row" alignItems="flex-start" justifyContent="space-between">
            <Box>
              <Typography sx={{ 
                fontWeight: 500,
                mb: 1,
                textTransform: 'uppercase',
                letterSpacing: '0.05em',
                fontSize: '0.8rem',
                color: 'rgba(255,255,255,0.8)'
              }}>
                {title}
              </Typography>
              <Typography variant="h4" sx={{ 
                fontWeight: 700,
                color: '#ffffff'
              }}>
                {value}
              </Typography>
            </Box>
            
            <Avatar sx={{ 
              backgroundColor: 'rgba(255, 255, 255, 0.2)',
              color: '#ffffff',
              width: 48,
              height: 48
            }}>
              <Icon sx={{ fontSize: 28 }} />
            </Avatar>
          </Stack>
          
          <Box sx={{ mt: 'auto', pt: 2 }}>
            <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.8)' }}>
              {subtitle}
            </Typography>
          </Box>
        </CardContent>
      </Card>
    </Fade>
  )
}

function ProgressCard({ title, progress, description, color = 'primary', delay = 0 }) {
  const getColor = (color) => {
    const colors = {
      primary: '#6366f1',
      secondary: '#10b981',
      warning: '#f59e0b',
      error: '#ef4444',
      info: '#3b82f6',
    }
    return colors[color] || colors.primary
  }

  return (
    <Fade in={true} timeout={600} style={{ transitionDelay: `${delay}ms` }}>
      <Card sx={{ height: '100%' }}>
        <CardContent sx={{ p: 3 }}>
          <Stack spacing={3}>
            <Stack direction="row" alignItems="center" justifyContent="space-between">
              <Typography
                variant="h6"
                sx={{
                  fontWeight: 600,
                  color: '#f8fafc'
                }}
              >
                {title}
              </Typography>
              
              <Chip
                label={`${progress}%`}
                size="small"
                sx={{
                  backgroundColor: getColor(color),
                  color: '#ffffff',
                  fontWeight: 600
                }}
              />
            </Stack>
            
            <Typography
              variant="body2"
              sx={{ color: '#cbd5e1' }}
            >
              {description}
            </Typography>
            
            <Box>
              <LinearProgress
                variant="determinate"
                value={progress}
                sx={{
                  height: 8,
                  borderRadius: 4,
                  backgroundColor: '#334155',
                  '& .MuiLinearProgress-bar': {
                    backgroundColor: getColor(color),
                    borderRadius: 4,
                    background: `linear-gradient(90deg, ${getColor(color)} 0%, ${getColor(color)}dd 100%)`
                  }
                }}
              />
              
              <Stack direction="row" justifyContent="space-between" sx={{ mt: 1 }}>
                <Typography variant="caption" sx={{ color: '#94a3b8' }}>
                  Current Usage
                </Typography>
                <Typography variant="caption" sx={{ color: '#94a3b8' }}>
                  Target: 100%
                </Typography>
              </Stack>
            </Box>
          </Stack>
        </CardContent>
      </Card>
    </Fade>
  )
}

function ActivityCard({ title, activities, delay = 0 }) {
  const getActivityIcon = (status) => {
    switch (status) {
      case 'success': return <CheckIcon sx={{ fontSize: 16, color: '#10b981' }} />
      case 'warning': return <WarningIcon sx={{ fontSize: 16, color: '#f59e0b' }} />
      case 'error': return <WarningIcon sx={{ fontSize: 16, color: '#ef4444' }} />
      default: return <EventIcon sx={{ fontSize: 16, color: '#6366f1' }} />
    }
  }

  return (
    <Fade in={true} timeout={600} style={{ transitionDelay: `${delay}ms` }}>
      <Card sx={{ height: '100%' }}>
        <CardContent sx={{ p: 3 }}>
          <Stack direction="row" alignItems="center" justifyContent="space-between" sx={{ mb: 3 }}>
            <Typography
              variant="h6"
              sx={{
                fontWeight: 600,
                color: '#f8fafc'
              }}
            >
              {title}
            </Typography>
            
            <IconButton 
              size="small"
              sx={{ 
                color: '#94a3b8',
                '&:hover': { color: '#6366f1' }
              }}
            >
              <RefreshIcon fontSize="small" />
            </IconButton>
          </Stack>
          
          <Stack spacing={2} sx={{ maxHeight: 280, overflow: 'auto' }}>
            {activities.map((activity, index) => (
              <Box key={index}>
                <Stack direction="row" alignItems="flex-start" spacing={2}>
                  <Box sx={{ mt: 0.5 }}>
                    {getActivityIcon(activity.status)}
                  </Box>
                  
                  <Box sx={{ flex: 1, minWidth: 0 }}>
                    <Typography
                      variant="body2"
                      sx={{
                        color: '#e2e8f0',
                        fontWeight: 500,
                        lineHeight: 1.4
                      }}
                    >
                      {activity.message}
                    </Typography>
                    
                    <Typography
                      variant="caption"
                      sx={{
                        color: '#94a3b8',
                        display: 'block',
                        mt: 0.5
                      }}
                    >
                      {activity.time}
                    </Typography>
                  </Box>
                </Stack>
                
                {index < activities.length - 1 && (
                  <Divider sx={{ mt: 2, borderColor: '#334155' }} />
                )}
              </Box>
            ))}
          </Stack>
        </CardContent>
      </Card>
    </Fade>
  )
}

function SystemHealthCard({ delay = 0 }) {
  const healthMetrics = [
    { label: 'API Response Time', value: '< 50ms', status: 'success', icon: SpeedIcon },
    { label: 'Database Connection', value: 'Healthy', status: 'success', icon: CheckIcon },
    { label: 'Memory Usage', value: '68%', status: 'warning', icon: MemoryIcon },
    { label: 'Active Sessions', value: '12', status: 'info', icon: PersonIcon }
  ]

  const getStatusColor = (status) => {
    switch (status) {
      case 'success': return '#10b981'
      case 'warning': return '#f59e0b'
      case 'error': return '#ef4444'
      default: return '#6366f1'
    }
  }

  return (
    <Fade in={true} timeout={600} style={{ transitionDelay: `${delay}ms` }}>
      <Card sx={{ height: '100%' }}>
        <CardContent sx={{ p: 3 }}>
          <Stack spacing={3}>
            <Typography
              variant="h6"
              sx={{
                fontWeight: 600,
                color: '#f8fafc'
              }}
            >
              System Health
            </Typography>
            
            <Box
              sx={{
                p: 3,
                borderRadius: 2,
                background: 'linear-gradient(135deg, rgba(16, 185, 129, 0.1) 0%, rgba(34, 197, 94, 0.05) 100%)',
                border: '1px solid rgba(16, 185, 129, 0.2)'
              }}
            >
              <Stack direction="row" alignItems="center" spacing={2}>
                <CheckIcon sx={{ color: '#10b981', fontSize: 20 }} />
                <Typography
                  variant="body2"
                  sx={{
                    color: '#f8fafc',
                    fontWeight: 600
                  }}
                >
                  All Systems Operational
                </Typography>
              </Stack>
            </Box>
            
            <Stack spacing={2}>
              {healthMetrics.map((metric, index) => {
                const Icon = metric.icon
                return (
                  <Stack key={index} direction="row" alignItems="center" justifyContent="space-between">
                    <Stack direction="row" alignItems="center" spacing={2}>
                      <Icon sx={{ fontSize: 18, color: getStatusColor(metric.status) }} />
                      <Typography variant="body2" sx={{ color: '#cbd5e1' }}>
                        {metric.label}
                      </Typography>
                    </Stack>
                    
                    <Typography
                      variant="body2"
                      sx={{
                        color: getStatusColor(metric.status),
                        fontWeight: 600
                      }}
                    >
                      {metric.value}
                    </Typography>
                  </Stack>
                )
              })}
            </Stack>
          </Stack>
        </CardContent>
      </Card>
    </Fade>
  )
}

function Dashboard() {
  const [stats, setStats] = useState({
    memories: 0,
    conversations: 0,
    agents: 0,
    users: 0
  })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetchStats = async () => {
    try {
      setLoading(true)
      setError(null)
      const [memoriesRes, conversationsRes, agentsRes, usersRes] = await Promise.all([
        api.getMemories(),
        api.getConversations(),
        api.getAgents(),
        api.getUsers()
      ])
      
      setStats({
        memories: memoriesRes.data.length,
        conversations: conversationsRes.data.length,
        agents: agentsRes.data.length,
        users: usersRes.data.length
      })
    } catch (err) {
      setError('Failed to fetch dashboard data')
      console.error('Dashboard error:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchStats()
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
          Loading dashboard data...
        </Typography>
      </Box>
    )
  }

  if (error) {
    return (
      <Alert 
        severity="error" 
        sx={{ 
          borderRadius: 2,
          backgroundColor: '#1e293b',
          border: '1px solid #ef4444'
        }}
      >
        {error}
      </Alert>
    )
  }

  return (
    <Box>
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
            Dashboard Overview
          </Typography>
          <Typography variant="body1" sx={{ color: '#94a3b8' }}>
            Monitor your PersonaLab system performance and activity
          </Typography>
        </Box>
        
        <IconButton 
          onClick={fetchStats}
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
      </Stack>

      <Grid container spacing={3}>
        {/* Main Metrics */}
        <Grid item xs={12} sm={6} md={3}>
          <MetricCard
            title="Total Memories"
            value={stats.memories}
            subtitle="Active memory instances"
            icon={MemoryIcon}
            color="primary"
            delay={0}
          />
        </Grid>
        
        <Grid item xs={12} sm={6} md={3}>
          <MetricCard
            title="Conversations"
            value={stats.conversations}
            subtitle="Chat interactions logged"
            icon={ChatIcon}
            color="secondary"
            delay={100}
          />
        </Grid>
        
        <Grid item xs={12} sm={6} md={3}>
          <MetricCard
            title="Active Agents"
            value={stats.agents}
            subtitle="AI agents deployed"
            icon={AgentIcon}
            color="warning"
            delay={200}
          />
        </Grid>
        
        <Grid item xs={12} sm={6} md={3}>
          <MetricCard
            title="Total Users"
            value={stats.users}
            subtitle="Registered users"
            icon={PersonIcon}
            color="info"
            delay={300}
          />
        </Grid>

        {/* Performance Metrics & Activity are commented out as they use mock data */}

      </Grid>
    </Box>
  )
}

export default Dashboard 