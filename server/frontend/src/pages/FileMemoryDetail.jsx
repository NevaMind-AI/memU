import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  Box,
  Typography,
  Card,
  CardContent,
  Button,
  CircularProgress,
  Alert,
  TextField,
  Stack,
  Chip,
  Paper,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Divider
} from '@mui/material'
import {
  ArrowBack as BackIcon,
  Edit as EditIcon,
  Save as SaveIcon,
  Download as DownloadIcon,
  Cancel as CancelIcon,
  ContentCopy as CopyIcon,
  Description as ProfileIcon,
  Event as EventIcon,
  Notifications as ReminderIcon,
  Star as ImportantIcon,
  Interests as InterestsIcon,
  School as StudyIcon
} from '@mui/icons-material'
import { api } from '../api/client'

// Memory type configuration
const MEMORY_TYPES = {
  profile: { icon: ProfileIcon, color: '#3b82f6', label: 'Profile', description: 'Character profile information' },
  event: { icon: EventIcon, color: '#10b981', label: 'Events', description: 'Character event records' },
  reminder: { icon: ReminderIcon, color: '#f59e0b', label: 'Reminders', description: 'Important reminders and todo items' },
  important_event: { icon: ImportantIcon, color: '#ef4444', label: 'Important Events', description: 'Significant life events and milestones' },
  interests: { icon: InterestsIcon, color: '#8b5cf6', label: 'Interests', description: 'Hobbies, interests, and preferences' },
  study: { icon: StudyIcon, color: '#06b6d4', label: 'Study', description: 'Learning goals, courses, and educational content' }
}

function FileMemoryDetail() {
  const { character, memoryType } = useParams()
  const navigate = useNavigate()
  
  const [fileContent, setFileContent] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [editing, setEditing] = useState(false)
  const [editContent, setEditContent] = useState('')
  const [saving, setSaving] = useState(false)
  const [saveDialog, setSaveDialog] = useState(false)

  const memoryConfig = MEMORY_TYPES[memoryType]
  const IconComponent = memoryConfig?.icon || ProfileIcon

  useEffect(() => {
    if (character && memoryType) {
      loadFileContent()
    }
  }, [character, memoryType])

  const loadFileContent = async () => {
    try {
      setLoading(true)
      setError(null)
      const response = await api.get(`/api/file-memory/characters/${character}/files/${memoryType}`)
      setFileContent(response.data)
      setEditContent(response.data.content)
    } catch (err) {
      if (err.response?.status === 404) {
        setError('File not found')
      } else {
        setError('Failed to load file content')
      }
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const handleSave = async () => {
    try {
      setSaving(true)
      await api.put(`/api/file-memory/characters/${character}/files/${memoryType}`, {
        character_name: character,
        memory_type: memoryType,
        content: editContent,
        append: false
      })
      
      setEditing(false)
      setSaveDialog(false)
      await loadFileContent() // Reload to get updated file info
      alert('File saved successfully!')
    } catch (err) {
      alert('Failed to save file')
      console.error(err)
    } finally {
      setSaving(false)
    }
  }

  const handleDownload = async () => {
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

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(fileContent?.content || '')
      alert('Content copied to clipboard!')
    } catch (err) {
      alert('Failed to copy content')
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

  const formatDate = (dateString) => {
    if (!dateString) return 'Unknown'
    return new Date(dateString).toLocaleString()
  }

  const startEditing = () => {
    setEditing(true)
    setEditContent(fileContent?.content || '')
  }

  const cancelEditing = () => {
    setEditing(false)
    setEditContent(fileContent?.content || '')
  }

  const confirmSave = () => {
    setSaveDialog(true)
  }

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    )
  }

  if (!memoryConfig) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="error">
          Invalid memory type: {memoryType}
        </Alert>
      </Box>
    )
  }

  return (
    <Box sx={{ p: 3 }}>
      {/* Header */}
      <Box sx={{ mb: 3 }}>
        <Button
          startIcon={<BackIcon />}
          onClick={() => navigate('/file-memories')}
          sx={{ mb: 2 }}
        >
          Back to File Memories
        </Button>

        <Card sx={{ border: 1, borderColor: memoryConfig.color }}>
          <CardContent>
            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <Box sx={{ display: 'flex', alignItems: 'center' }}>
                <IconComponent 
                  sx={{ 
                    color: memoryConfig.color, 
                    mr: 2, 
                    fontSize: 32 
                  }} 
                />
                <Box>
                  <Typography variant="h5" fontWeight="bold">
                    {character} - {memoryConfig.label}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    {memoryConfig.description}
                  </Typography>
                </Box>
              </Box>

              <Stack direction="row" spacing={1}>
                {fileContent && (
                  <>
                    <Chip 
                      label={formatFileSize(fileContent.file_size)} 
                      variant="outlined" 
                      size="small"
                    />
                    <Chip 
                      label={`Modified: ${formatDate(fileContent.last_modified)}`} 
                      variant="outlined" 
                      size="small"
                    />
                  </>
                )}
              </Stack>
            </Box>
          </CardContent>
        </Card>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      {/* Content */}
      {fileContent ? (
        <Card>
          <CardContent>
            {/* Toolbar */}
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
              <Typography variant="h6">
                File Content
              </Typography>
              
              <Stack direction="row" spacing={1}>
                {!editing ? (
                  <>
                    <Button
                      startIcon={<EditIcon />}
                      onClick={startEditing}
                      variant="outlined"
                    >
                      Edit
                    </Button>
                    <Button
                      startIcon={<CopyIcon />}
                      onClick={handleCopy}
                      variant="outlined"
                    >
                      Copy
                    </Button>
                    <Button
                      startIcon={<DownloadIcon />}
                      onClick={handleDownload}
                      variant="outlined"
                    >
                      Download
                    </Button>
                  </>
                ) : (
                  <>
                    <Button
                      startIcon={<SaveIcon />}
                      onClick={confirmSave}
                      variant="contained"
                      disabled={saving}
                    >
                      Save
                    </Button>
                    <Button
                      startIcon={<CancelIcon />}
                      onClick={cancelEditing}
                      variant="outlined"
                      disabled={saving}
                    >
                      Cancel
                    </Button>
                  </>
                )}
              </Stack>
            </Box>

            <Divider sx={{ mb: 3 }} />

            {/* Content Display/Editor */}
            {editing ? (
              <TextField
                fullWidth
                multiline
                rows={20}
                value={editContent}
                onChange={(e) => setEditContent(e.target.value)}
                variant="outlined"
                placeholder={`Enter ${memoryConfig.label.toLowerCase()} content here...`}
                sx={{
                  '& .MuiInputBase-root': {
                    fontFamily: 'Monaco, Menlo, "Ubuntu Mono", monospace',
                    fontSize: '14px',
                    lineHeight: 1.5
                  }
                }}
              />
            ) : (
              <Paper
                variant="outlined"
                sx={{
                  p: 3,
                  minHeight: '400px',
                  backgroundColor: 'background.default',
                  fontFamily: 'Monaco, Menlo, "Ubuntu Mono", monospace',
                  fontSize: '14px',
                  lineHeight: 1.6,
                  whiteSpace: 'pre-wrap',
                  overflow: 'auto'
                }}
              >
                {fileContent.content || (
                  <Typography color="text.secondary" fontStyle="italic">
                    No content available
                  </Typography>
                )}
              </Paper>
            )}

            {/* File Statistics */}
            {fileContent.content && (
              <Box sx={{ mt: 3, pt: 2, borderTop: 1, borderColor: 'divider' }}>
                <Stack direction="row" spacing={3}>
                  <Typography variant="body2" color="text.secondary">
                    Lines: {fileContent.content.split('\n').length}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Characters: {fileContent.content.length}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Words: {fileContent.content.split(/\s+/).filter(word => word.length > 0).length}
                  </Typography>
                </Stack>
              </Box>
            )}
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardContent>
            <Box textAlign="center" py={4}>
              <IconComponent sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
              <Typography variant="h6" color="text.secondary" gutterBottom>
                No Content Available
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
                This {memoryConfig.label.toLowerCase()} file is empty or doesn't exist yet.
              </Typography>
              <Button
                variant="contained"
                startIcon={<EditIcon />}
                onClick={startEditing}
              >
                Create Content
              </Button>
            </Box>
          </CardContent>
        </Card>
      )}

      {/* Save Confirmation Dialog */}
      <Dialog open={saveDialog} onClose={() => setSaveDialog(false)}>
        <DialogTitle>Confirm Save</DialogTitle>
        <DialogContent>
          <Typography>
            Are you sure you want to save the changes to {character}'s {memoryConfig.label.toLowerCase()} file?
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
            This will overwrite the existing content.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setSaveDialog(false)} disabled={saving}>
            Cancel
          </Button>
          <Button 
            onClick={handleSave} 
            variant="contained"
            disabled={saving}
            startIcon={saving ? <CircularProgress size={16} /> : <SaveIcon />}
          >
            {saving ? 'Saving...' : 'Save'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}

export default FileMemoryDetail 