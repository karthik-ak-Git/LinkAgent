// LinkAgent Options Script

const DEFAULT_SETTINGS = {
  wsPort: 8765,
  autoExtract: false,
  maxLinks: 100,
  maxImages: 50,
  maxTextLength: 5000,
  mcpServerPath: 'linkagent-mcp-server',
  autoStartMcp: false,
}

document.addEventListener('DOMContentLoaded', async () => {
  const wsPort = document.getElementById('wsPort')
  const autoExtract = document.getElementById('autoExtract')
  const maxLinks = document.getElementById('maxLinks')
  const maxImages = document.getElementById('maxImages')
  const maxTextLength = document.getElementById('maxTextLength')
  const mcpServerPath = document.getElementById('mcpServerPath')
  const autoStartMcp = document.getElementById('autoStartMcp')
  const saveBtn = document.getElementById('saveBtn')
  const resetBtn = document.getElementById('resetBtn')
  const status = document.getElementById('status')

  // Load saved settings
  const saved = await chrome.storage.sync.get('linkagent_settings')
  const settings = saved.linkagent_settings || DEFAULT_SETTINGS

  // Populate fields
  wsPort.value = settings.wsPort
  autoExtract.checked = settings.autoExtract
  maxLinks.value = settings.maxLinks
  maxImages.value = settings.maxImages
  maxTextLength.value = settings.maxTextLength
  mcpServerPath.value = settings.mcpServerPath
  autoStartMcp.checked = settings.autoStartMcp

  // Save settings
  saveBtn.addEventListener('click', async () => {
    const newSettings = {
      wsPort: parseInt(wsPort.value) || DEFAULT_SETTINGS.wsPort,
      autoExtract: autoExtract.checked,
      maxLinks: parseInt(maxLinks.value) || DEFAULT_SETTINGS.maxLinks,
      maxImages: parseInt(maxImages.value) || DEFAULT_SETTINGS.maxImages,
      maxTextLength: parseInt(maxTextLength.value) || DEFAULT_SETTINGS.maxTextLength,
      mcpServerPath: mcpServerPath.value || DEFAULT_SETTINGS.mcpServerPath,
      autoStartMcp: autoStartMcp.checked,
    }

    await chrome.storage.sync.set({ linkagent_settings: newSettings })
    showStatus('Settings saved successfully!', 'success')
  })

  // Reset to defaults
  resetBtn.addEventListener('click', async () => {
    await chrome.storage.sync.set({ linkagent_settings: DEFAULT_SETTINGS })
    wsPort.value = DEFAULT_SETTINGS.wsPort
    autoExtract.checked = DEFAULT_SETTINGS.autoExtract
    maxLinks.value = DEFAULT_SETTINGS.maxLinks
    maxImages.value = DEFAULT_SETTINGS.maxImages
    maxTextLength.value = DEFAULT_SETTINGS.maxTextLength
    mcpServerPath.value = DEFAULT_SETTINGS.mcpServerPath
    autoStartMcp.checked = DEFAULT_SETTINGS.autoStartMcp
    showStatus('Settings reset to defaults', 'info')
  })

  function showStatus(message, type) {
    status.textContent = message
    status.style.color = type === 'success' ? '#22c55e' : type === 'error' ? '#ef4444' : '#667eea'
    setTimeout(() => {
      status.textContent = ''
    }, 3000)
  }
})
