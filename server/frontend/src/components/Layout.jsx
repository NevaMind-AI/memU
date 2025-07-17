import { useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import {
  AppBar,
  Box,
  CssBaseline,
  Drawer,
  IconButton,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Toolbar,
  Typography,
  Avatar,
  Divider,
  Chip,
  Badge,
  Stack
} from '@mui/material'
import {
  Dashboard as DashboardIcon,
  Chat as ChatIcon,
  Memory as MemoryIcon,
  History as HistoryIcon,
  Menu as MenuIcon,
  Settings as SettingsIcon,
  TrendingUp as TrendingIcon,
  Circle as StatusIcon,
  FolderOpen as FileMemoryIcon
} from '@mui/icons-material'

const drawerWidth = 280

const navigation = [
  { 
    title: 'Dashboard', 
    path: '/', 
    icon: DashboardIcon,
    description: 'System overview & analytics'
  },
  { 
    title: 'Conversations', 
    path: '/conversations', 
    icon: ChatIcon,
    description: 'Chat history & management'
  },
  { 
    title: 'Memories', 
    path: '/memories', 
    icon: MemoryIcon,
    description: 'Agent memory system'
  },
  { 
    title: 'File Memories', 
    path: '/file-memories', 
    icon: FileMemoryIcon,
    description: 'File-based memory management'
  },
  { 
    title: 'Operations', 
    path: '/memory-operations', 
    icon: HistoryIcon,
    description: 'System operations log'
  },
]

function Layout({ children }) {
  const [mobileOpen, setMobileOpen] = useState(false)
  const location = useLocation()

  const handleDrawerToggle = () => {
    setMobileOpen(!mobileOpen)
  }

  const getCurrentPageInfo = () => {
    const currentNav = navigation.find(nav => nav.path === location.pathname)
    return currentNav || { title: 'PersonaLab', description: 'AI Memory Management System' }
  }

  const currentPage = getCurrentPageInfo()

  const drawer = (
    <Box sx={{ 
      height: '100vh', 
      display: 'flex', 
      flexDirection: 'column',
      background: 'linear-gradient(180deg, #0f172a 0%, #1e293b 100%)',
      overflow: 'hidden'
    }}>
      {/* Brand Header */}
      <Box sx={{ p: 3, textAlign: 'center', borderBottom: '1px solid #334155' }}>
        <Avatar
          sx={{
            width: 56,
            height: 56,
            mx: 'auto',
            mb: 2,
            background: 'linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%)',
            fontSize: '1.5rem',
            fontWeight: 700,
            boxShadow: '0 10px 25px -5px rgba(99, 102, 241, 0.4)'
          }}
        >
          PL
        </Avatar>
        <Typography 
          variant="h6" 
          sx={{ 
            fontWeight: 700,
            color: '#f8fafc',
            mb: 0.5,
            fontSize: '1.25rem'
          }}
        >
          PersonaLab
        </Typography>
        <Typography 
          variant="caption" 
          sx={{ 
            color: '#94a3b8',
            display: 'block',
            fontWeight: 500,
            textTransform: 'uppercase',
            letterSpacing: '0.1em'
          }}
        >
          AI Memory Platform
        </Typography>
      </Box>
      
      {/* Navigation */}
      <Box sx={{ flex: 1, px: 2, py: 3, overflow: 'auto' }}>
        <Typography 
          variant="overline" 
          sx={{ 
            px: 2, 
            mb: 2, 
            display: 'block',
            color: '#64748b',
            fontWeight: 600
          }}
        >
          Navigation
        </Typography>
        
        <List sx={{ '& .MuiListItem-root': { px: 0 } }}>
          {navigation.map((item) => {
            const Icon = item.icon
            const isActive = location.pathname === item.path
            
            return (
              <ListItem key={item.title} sx={{ mb: 0.5 }}>
                <ListItemButton
                  component={Link}
                  to={item.path}
                  selected={isActive}
                  sx={{
                    borderRadius: 2,
                    py: 2,
                    px: 2,
                    mx: 1,
                    transition: 'all 0.2s cubic-bezier(0.4, 0, 0.2, 1)',
                    position: 'relative',
                    overflow: 'hidden',
                    '&.Mui-selected': {
                      backgroundColor: '#6366f1',
                      color: '#ffffff',
                      boxShadow: '0 8px 25px -5px rgba(99, 102, 241, 0.4)',
                      '&:hover': {
                        backgroundColor: '#5b5bd6',
                        boxShadow: '0 12px 35px -5px rgba(99, 102, 241, 0.5)',
                      },
                      '& .MuiListItemIcon-root': {
                        color: '#ffffff',
                      },
                      '&::before': {
                        content: '""',
                        position: 'absolute',
                        top: 0,
                        left: 0,
                        width: '4px',
                        height: '100%',
                        backgroundColor: '#ffffff',
                        borderRadius: '0 2px 2px 0',
                      }
                    },
                    '&:hover': {
                      backgroundColor: '#334155',
                    },
                  }}
                >
                  <ListItemIcon sx={{ minWidth: 44 }}>
                    <Icon sx={{ fontSize: 22 }} />
                  </ListItemIcon>
                  <Box sx={{ flex: 1 }}>
                    <ListItemText 
                      primary={item.title}
                      secondary={item.description}
                      primaryTypographyProps={{
                        fontWeight: isActive ? 600 : 500,
                        fontSize: '0.95rem'
                      }}
                      secondaryTypographyProps={{
                        fontSize: '0.75rem',
                        mt: 0.5,
                        color: isActive ? 'rgba(255,255,255,0.8)' : '#64748b'
                      }}
                    />
                  </Box>
                  {isActive && (
                    <Badge
                      variant="dot"
                      sx={{
                        '& .MuiBadge-dot': {
                          backgroundColor: '#ffffff',
                          width: 8,
                          height: 8,
                          borderRadius: '50%',
                          animation: 'pulse 2s infinite'
                        },
                        '@keyframes pulse': {
                          '0%': { opacity: 1 },
                          '50%': { opacity: 0.5 },
                          '100%': { opacity: 1 },
                        }
                      }}
                    />
                  )}
                </ListItemButton>
              </ListItem>
            )
          })}
        </List>
      </Box>

      {/* System Status - This section is being removed as it contains mock data */}
      {/*
      <Box sx={{ p: 3, mt: 'auto' }}>
        <Box 
          sx={{ 
            p: 3, 
            borderRadius: 3, 
            background: 'linear-gradient(135deg, rgba(16, 185, 129, 0.1) 0%, rgba(34, 197, 94, 0.05) 100%)',
            border: '1px solid rgba(16, 185, 129, 0.2)',
            backdropFilter: 'blur(10px)'
          }}
        >
          <Stack direction="row" alignItems="center" spacing={2} sx={{ mb: 2 }}>
            <StatusIcon 
              sx={{ 
                fontSize: 12, 
                color: '#10b981',
                animation: 'pulse 2s infinite'
              }} 
            />
            <Typography variant="caption" sx={{ 
              color: '#10b981',
              fontWeight: 600,
              textTransform: 'uppercase',
              letterSpacing: '0.1em'
            }}>
              System Status
            </Typography>
            <Chip 
              label="Operational" 
              size="small" 
              sx={{ 
                height: 20,
                ml: 'auto',
                color: '#10b981',
                backgroundColor: 'rgba(16, 185, 129, 0.1)',
                border: '1px solid rgba(16, 185, 129, 0.2)',
                fontWeight: 600
              }} 
            />
          </Stack>
          
          <Stack spacing={1}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <Typography variant="caption" sx={{ color: '#cbd5e1' }}>
                API Response Time
              </Typography>
              <Typography variant="caption" sx={{ color: '#f8fafc', fontWeight: 600 }}>
                12ms
              </Typography>
            </Box>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <Typography variant="caption" sx={{ color: '#cbd5e1' }}>
                Memory Usage
              </Typography>
              <Typography variant="caption" sx={{ color: '#f59e0b', fontWeight: 600 }}>
                68%
              </Typography>
            </Box>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <Typography variant="caption" sx={{ color: '#cbd5e1' }}>
                Active Sessions
              </Typography>
              <Typography variant="caption" sx={{ color: '#6366f1', fontWeight: 600 }}>
                12
              </Typography>
            </Box>
          </Stack>
        </Box>
      </Box>
      */}
    </Box>
  )

  return (
    <Box sx={{ display: 'flex', minHeight: '100vh' }}>
      <CssBaseline />
      
      {/* Top Navigation Bar */}
      <AppBar
        position="fixed"
        sx={{
          width: { sm: `calc(100% - ${drawerWidth}px)` },
          ml: { sm: `${drawerWidth}px` },
          zIndex: (theme) => theme.zIndex.drawer + 1
        }}
      >
        <Toolbar sx={{ justifyContent: 'space-between', py: 1 }}>
          <Stack direction="row" alignItems="center" spacing={2}>
            <IconButton
              color="inherit"
              aria-label="open drawer"
              edge="start"
              onClick={handleDrawerToggle}
              sx={{ 
                mr: 2, 
                display: { sm: 'none' },
                color: '#f8fafc'
              }}
            >
              <MenuIcon />
            </IconButton>
            
            <Box>
              <Typography 
                variant="h5" 
                component="div" 
                sx={{ 
                  fontWeight: 700,
                  color: '#f8fafc',
                  fontSize: '1.5rem',
                  lineHeight: 1.2
                }}
              >
                {currentPage.title}
              </Typography>
              <Typography 
                variant="caption" 
                sx={{ 
                  color: '#94a3b8',
                  display: 'block',
                  mt: -0.5,
                  fontWeight: 500
                }}
              >
                {currentPage.description}
              </Typography>
            </Box>
          </Stack>
          
          {/* Action Icons - Commented out as they are not yet functional */}
          {/*
          <Stack direction="row" alignItems="center" spacing={2}>
            <IconButton 
              sx={{ 
                color: '#cbd5e1',
                '&:hover': {
                  backgroundColor: 'rgba(99, 102, 241, 0.1)',
                  color: '#6366f1'
                }
              }}
            >
              <TrendingIcon />
            </IconButton>
            
            <IconButton 
              sx={{ 
                color: '#cbd5e1',
                '&:hover': {
                  backgroundColor: 'rgba(99, 102, 241, 0.1)',
                  color: '#6366f1'
                }
              }}
            >
              <SettingsIcon />
            </IconButton>
            
            <Avatar 
              sx={{ 
                width: 36, 
                height: 36,
                background: 'linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%)',
                cursor: 'pointer',
                transition: 'all 0.2s cubic-bezier(0.4, 0, 0.2, 1)',
                '&:hover': {
                  transform: 'scale(1.05)',
                  boxShadow: '0 8px 25px -5px rgba(99, 102, 241, 0.4)'
                }
              }}
            >
              A
            </Avatar>
          </Stack>
          */}
        </Toolbar>
      </AppBar>

      {/* Side Navigation */}
      <Box
        component="nav"
        sx={{ width: { sm: drawerWidth }, flexShrink: { sm: 0 } }}
      >
        {/* Mobile Drawer */}
        <Drawer
          variant="temporary"
          open={mobileOpen}
          onClose={handleDrawerToggle}
          ModalProps={{ keepMounted: true }}
          sx={{
            display: { xs: 'block', sm: 'none' },
            '& .MuiDrawer-paper': { 
              boxSizing: 'border-box', 
              width: drawerWidth,
              border: 'none',
              boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.25)'
            },
          }}
        >
          {drawer}
        </Drawer>
        
        {/* Desktop Drawer */}
        <Drawer
          variant="permanent"
          sx={{
            display: { xs: 'none', sm: 'block' },
            '& .MuiDrawer-paper': { 
              boxSizing: 'border-box', 
              width: drawerWidth,
              border: 'none',
              boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.25)',
              position: 'fixed',
              height: '100vh',
              overflow: 'hidden'
            },
          }}
          open
        >
          {drawer}
        </Drawer>
      </Box>
      
      {/* Main Content */}
      <Box
        component="main"
        sx={{ 
          flexGrow: 1, 
          minHeight: '100vh',
          ml: { sm: `${drawerWidth/2}px` },
          width: { sm: `calc(100% - ${drawerWidth}px)` }
        }}
      >
        <Toolbar />
        
        <Box sx={{ 
          pt: { xs: 2, sm: 3, md: 4 },
          pb: { xs: 2, sm: 3, md: 4 },
          px: 0,
          width: '100%',
          minHeight: 'calc(100vh - 64px)',
          position: 'relative'
        }}>
          {children}
        </Box>
        
        {/* Background Pattern Overlay */}
        <Box
          sx={{
            position: 'fixed',
            top: 0,
            left: { sm: `${drawerWidth}px` },
            right: 0,
            bottom: 0,
            background: 'radial-gradient(circle at 50% 50%, rgba(99, 102, 241, 0.03) 0%, transparent 50%)',
            pointerEvents: 'none',
            zIndex: -1
          }}
        />
      </Box>
    </Box>
  )
}

export default Layout 