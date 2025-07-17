import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Box,
  Typography,
  Card,
  CardContent,
  CardActions,
  Button,
  Grid,
  CircularProgress,
  Alert,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Chip,
  Avatar,
  Fade,
  Tooltip,
  Divider,
  Stack,
  Badge,
  Tabs,
  Tab,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  LinearProgress,
  Paper
} from '@mui/material'
import {
  Visibility as VisibilityIcon,
  Delete as DeleteIcon,
  Edit as EditIcon,
  Download as DownloadIcon,
  Person as PersonIcon,
  Description as ProfileIcon,
  Event as EventIcon,
  Notifications as ReminderIcon,
  Star as ImportantIcon,
  Interests as InterestsIcon,
  School as StudyIcon,
  Analytics as AnalyzeIcon,
  Refresh as RefreshIcon,
  Add as AddIcon,
  CloudUpload as UploadIcon,
  FolderOpen as FolderIcon
} from '@mui/icons-material'
import { api } from '../api/client'

// Memory type configuration
const MEMORY_TYPES = {
  profile: { icon: ProfileIcon, color: '#3b82f6', label: 'Profile' },
  event: { icon: EventIcon, color: '#10b981', label: 'Events' },
  reminder: { icon: ReminderIcon, color: '#f59e0b', label: 'Reminders' },
  important_event: { icon: ImportantIcon, color: '#ef4444', label: 'Important Events' },
  interests: { icon: InterestsIcon, color: '#8b5cf6', label: 'Interests' },
  study: { icon: StudyIcon, color: '#06b6d4', label: 'Study' }
}

function FileMemories() {
  const navigate = useNavigate()
  const [characters, setCharacters] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [selectedCharacter, setSelectedCharacter] = useState(null)
  const [characterDetails, setCharacterDetails] = useState(null)
  const [detailsLoading, setDetailsLoading] = useState(false)
  const [currentTab, setCurrentTab] = useState(0)
  const [systemInfo, setSystemInfo] = useState(null)

  // Dialog states
  const [analyzeDialog, setAnalyzeDialog] = useState(false)
  const [analyzeData, setAnalyzeData] = useState({ character: '', conversation: '', date: '' })
  const [analyzing, setAnalyzing] = useState(false)

  useEffect(() => {
    loadCharacters()
    loadSystemInfo()
  }, [])

  const loadCharacters = async () => {
    try {
      setLoading(true)
      const response = await api.get('/api/file-memory/characters')
      setCharacters(response.data)
    } catch (err) {
      setError('Failed to load characters')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const loadSystemInfo = async () => {
    try {
      const response = await api.get('/api/file-memory/system/info')
      setSystemInfo(response.data)
    } catch (err) {
      console.error('Failed to load system info:', err)
    }
  }

  const loadCharacterDetails = async (characterName) => {
    try {
      setDetailsLoading(true)
      const response = await api.get(`/api/file-memory/characters/${characterName}/summary`)
      setCharacterDetails(response.data)
    } catch (err) {
      setError(`Failed to load details for ${characterName}`)
      console.error(err)
    } finally {
      setDetailsLoading(false)
    }
  }

  const handleCharacterSelect = (character) => {
    setSelectedCharacter(character)
    setCharacterDetails(null)
    loadCharacterDetails(character)
  }

  const handleAnalyzeConversation = async () => {
    try {
      setAnalyzing(true)
      const response = await api.post('/api/file-memory/analyze-conversation', {
        character_name: analyzeData.character,
        conversation: analyzeData.conversation,
        session_date: analyzeData.date || new Date().toISOString().split('T')[0]
      })

      if (response.data.success) {
        setAnalyzeDialog(false)
        setAnalyzeData({ character: '', conversation: '', date: '' })
        // Refresh character list and details
        await loadCharacters()
        if (selectedCharacter) {
          await loadCharacterDetails(selectedCharacter)
        }
        alert('Conversation analyzed successfully!')
      } else {
        alert(`Analysis failed: ${response.data.error}`)
      }
    } catch (err) {
      alert('Failed to analyze conversation')
      console.error(err)
    } finally {
      setAnalyzing(false)
    }
  }

  const handleDeleteCharacter = async (character) => {
    if (!confirm(`Are you sure you want to delete all memory files for ${character}?`)) {
      return
    }

    try {
      await api.delete(`/api/file-memory/characters/${character}`)
      await loadCharacters()
      if (selectedCharacter === character) {
        setSelectedCharacter(null)
        setCharacterDetails(null)
      }
      alert(`Deleted all memory files for ${character}`)
    } catch (err) {
      alert('Failed to delete character')
      console.error(err)
    }
  }

  const handleDownloadFile = async (character, memoryType) => {
    try {
      const response = await api.get(
        `/api/file-memory/characters/${character}/files/${memoryType}/download`,
        { responseType: 'blob' }
      )
      
      const url = window.URL.createObjectURL(new Blob([response.data]))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', `${character}_${memoryType}.md`)
      document.body.appendChild(link)
      link.click()
      link.remove()
    } catch (err) {
      alert('Failed to download file')
      console.error(err)
    }
  }

  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 B'
    const k = 1024
    const sizes = ['B', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  const getCharacterScore = (details) => {
    if (!details) return 0
    const fileCount = details.total_files
    const totalSize = details.total_size
    return Math.min(100, Math.round((fileCount * 15) + (totalSize / 100)))
  }

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    )
  }

  return (
    <Box sx={{ p: 3 }}>
      {/* Header */}
      <Box sx={{ mb: 3, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Typography variant="h4" component="h1" fontWeight="bold">
          📁 File-based Memory Management
        </Typography>
        <Stack direction="row" spacing={2}>
          <Button
            variant="contained"
            startIcon={<AnalyzeIcon />}
            onClick={() => setAnalyzeDialog(true)}
            disabled={!systemInfo?.analysis_enabled}
          >
            Analyze Conversation
          </Button>
          <Button
            variant="outlined"
            startIcon={<RefreshIcon />}
            onClick={loadCharacters}
          >
            Refresh
          </Button>
        </Stack>
      </Box>

      {/* System Info */}
      {systemInfo && (
        <Paper sx={{ p: 2, mb: 3, bgcolor: 'info.light', color: 'info.contrastText' }}>
          <Typography variant="h6" gutterBottom>
            📊 System Status
          </Typography>
          <Grid container spacing={2}>
            <Grid item xs={12} sm={3}>
              <Typography variant="body2">
                <FolderIcon sx={{ mr: 1, verticalAlign: 'middle' }} />
                Memory Directory: {systemInfo.memory_directory}
              </Typography>
            </Grid>
            <Grid item xs={12} sm={3}>
              <Typography variant="body2">
                👥 Characters: {systemInfo.total_characters}
              </Typography>
            </Grid>
            <Grid item xs={12} sm={3}>
              <Typography variant="body2">
                📄 Total Files: {systemInfo.total_files}
              </Typography>
            </Grid>
            <Grid item xs={12} sm={3}>
              <Typography variant="body2">
                💾 Total Size: {formatFileSize(systemInfo.total_size_bytes)}
              </Typography>
            </Grid>
          </Grid>
        </Paper>
      )}

      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      <Grid container spacing={3}>
        {/* Character List */}
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Characters ({characters.length})
              </Typography>
              <Stack spacing={1}>
                {characters.map((character) => (
                  <Card
                    key={character}
                    sx={{
                      cursor: 'pointer',
                      border: selectedCharacter === character ? 2 : 1,
                      borderColor: selectedCharacter === character ? 'primary.main' : 'divider',
                      '&:hover': { borderColor: 'primary.main' }
                    }}
                    onClick={() => handleCharacterSelect(character)}
                  >
                    <CardContent sx={{ py: 1 }}>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <Typography variant="body1" fontWeight="medium">
                          <PersonIcon sx={{ mr: 1, verticalAlign: 'middle' }} />
                          {character}
                        </Typography>
                        <IconButton
                          size="small"
                          onClick={(e) => {
                            e.stopPropagation()
                            handleDeleteCharacter(character)
                          }}
                        >
                          <DeleteIcon fontSize="small" />
                        </IconButton>
                      </Box>
                    </CardContent>
                  </Card>
                ))}
                {characters.length === 0 && (
                  <Typography variant="body2" color="text.secondary" textAlign="center" py={2}>
                    No characters found. Start by analyzing a conversation.
                  </Typography>
                )}
              </Stack>
            </CardContent>
          </Card>
        </Grid>

        {/* Character Details */}
        <Grid item xs={12} md={8}>
          {selectedCharacter ? (
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                  <Typography variant="h6">
                    Memory Files for {selectedCharacter}
                  </Typography>
                  {characterDetails && (
                    <Chip
                      label={`Score: ${getCharacterScore(characterDetails)}%`}
                      color="primary"
                      variant="outlined"
                    />
                  )}
                </Box>

                {detailsLoading ? (
                  <Box display="flex" justifyContent="center" py={4}>
                    <CircularProgress />
                  </Box>
                ) : characterDetails ? (
                  <Grid container spacing={2}>
                    {Object.entries(MEMORY_TYPES).map(([type, config]) => {
                      const fileInfo = characterDetails.file_details[type]
                      const IconComponent = config.icon

                      return (
                        <Grid item xs={12} sm={6} md={4} key={type}>
                          <Card
                            sx={{
                              height: '100%',
                              border: 1,
                              borderColor: fileInfo.has_content ? config.color : 'divider',
                              backgroundColor: fileInfo.has_content ? `${config.color}10` : 'background.paper'
                            }}
                          >
                            <CardContent>
                              <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                                <IconComponent
                                  sx={{ color: config.color, mr: 1 }}
                                  fontSize="small"
                                />
                                <Typography variant="body1" fontWeight="medium">
                                  {config.label}
                                </Typography>
                              </Box>
                              
                              <Typography variant="body2" color="text.secondary" gutterBottom>
                                {fileInfo.has_content ? (
                                  <>
                                    Size: {formatFileSize(fileInfo.file_size)}
                                    <br />
                                    Modified: {fileInfo.last_modified 
                                      ? new Date(fileInfo.last_modified).toLocaleDateString()
                                      : 'Unknown'
                                    }
                                  </>
                                ) : (
                                  'No content'
                                )}
                              </Typography>

                              {fileInfo.content_preview && (
                                <Typography
                                  variant="caption"
                                  display="block"
                                  sx={{
                                    mt: 1,
                                    p: 1,
                                    bgcolor: 'background.default',
                                    borderRadius: 1,
                                    fontFamily: 'monospace',
                                    maxHeight: '60px',
                                    overflow: 'hidden'
                                  }}
                                >
                                  {fileInfo.content_preview}
                                </Typography>
                              )}
                            </CardContent>
                            
                            {fileInfo.has_content && (
                              <CardActions sx={{ pt: 0 }}>
                                <Button
                                  size="small"
                                  startIcon={<VisibilityIcon />}
                                  onClick={() => navigate(`/file-memory/${selectedCharacter}/${type}`)}
                                >
                                  View
                                </Button>
                                <Button
                                  size="small"
                                  startIcon={<DownloadIcon />}
                                  onClick={() => handleDownloadFile(selectedCharacter, type)}
                                >
                                  Download
                                </Button>
                              </CardActions>
                            )}
                          </Card>
                        </Grid>
                      )
                    })}
                  </Grid>
                ) : (
                  <Typography variant="body2" color="text.secondary">
                    Failed to load character details
                  </Typography>
                )}
              </CardContent>
            </Card>
          ) : (
            <Card>
              <CardContent>
                <Box textAlign="center" py={4}>
                  <FolderIcon sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
                  <Typography variant="h6" color="text.secondary" gutterBottom>
                    Select a Character
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Choose a character from the list to view their memory files
                  </Typography>
                </Box>
              </CardContent>
            </Card>
          )}
        </Grid>
      </Grid>

      {/* Analyze Conversation Dialog */}
      <Dialog open={analyzeDialog} onClose={() => setAnalyzeDialog(false)} maxWidth="md" fullWidth>
        <DialogTitle>
          <AnalyzeIcon sx={{ mr: 1, verticalAlign: 'middle' }} />
          Analyze Conversation
        </DialogTitle>
        <DialogContent>
          <Stack spacing={3} sx={{ mt: 1 }}>
            <FormControl fullWidth>
              <InputLabel>Character</InputLabel>
              <Select
                value={analyzeData.character}
                onChange={(e) => setAnalyzeData(prev => ({ ...prev, character: e.target.value }))}
                label="Character"
              >
                {characters.map((char) => (
                  <MenuItem key={char} value={char}>{char}</MenuItem>
                ))}
                <MenuItem value="new">+ New Character</MenuItem>
              </Select>
            </FormControl>

            {analyzeData.character === 'new' && (
              <TextField
                fullWidth
                label="New Character Name"
                value={analyzeData.newCharacter || ''}
                onChange={(e) => setAnalyzeData(prev => ({ ...prev, newCharacter: e.target.value }))}
              />
            )}

            <TextField
              fullWidth
              label="Session Date"
              type="date"
              value={analyzeData.date}
              onChange={(e) => setAnalyzeData(prev => ({ ...prev, date: e.target.value }))}
              InputLabelProps={{ shrink: true }}
            />

            <TextField
              fullWidth
              multiline
              rows={8}
              label="Conversation"
              placeholder="Paste the conversation content here..."
              value={analyzeData.conversation}
              onChange={(e) => setAnalyzeData(prev => ({ ...prev, conversation: e.target.value }))}
            />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setAnalyzeDialog(false)}>Cancel</Button>
          <Button
            variant="contained"
            onClick={handleAnalyzeConversation}
            disabled={!analyzeData.character || !analyzeData.conversation || analyzing}
            startIcon={analyzing ? <CircularProgress size={16} /> : <AnalyzeIcon />}
          >
            {analyzing ? 'Analyzing...' : 'Analyze'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}

export default FileMemories 