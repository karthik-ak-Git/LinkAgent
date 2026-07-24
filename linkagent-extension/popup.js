// LinkAgent Popup Script

document.addEventListener('DOMContentLoaded', async () => {
  const bridgeStatus = document.getElementById('bridgeStatus')
  const tabCount = document.getElementById('tabCount')
  const currentPage = document.getElementById('currentPage')
  const extractBtn = document.getElementById('extractBtn')
  const screenshotBtn = document.getElementById('screenshotBtn')

  // Get status from background
  chrome.runtime.sendMessage({ type: 'la-status' }, (response) => {
    if (response) {
      const dot = bridgeStatus.querySelector('.dot')
      if (response.connected) {
        dot.className = 'dot green'
        bridgeStatus.innerHTML = '<span class="dot green"></span>Connected'
      } else {
        dot.className = 'dot red'
        bridgeStatus.innerHTML = '<span class="dot red"></span>Disconnected'
      }
      tabCount.textContent = response.tabCount || 0
    }
  })

  // Get current tab info
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true })
  if (tab) {
    currentPage.textContent = tab.title || tab.url || '-'
    currentPage.title = tab.url || ''
  }

  // Extract page data
  extractBtn.addEventListener('click', async () => {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true })
    if (!tab) return

    try {
      const response = await chrome.tabs.sendMessage(tab.id, { type: 'getPageContent' })
      console.log('Extracted data:', response)
      
      // Copy to clipboard
      await navigator.clipboard.writeText(JSON.stringify(response, null, 2))
      extractBtn.textContent = 'Copied to Clipboard!'
      setTimeout(() => {
        extractBtn.textContent = 'Extract Page Data'
      }, 2000)
    } catch (e) {
      console.error('Extract error:', e)
      extractBtn.textContent = 'Error - Try Again'
      setTimeout(() => {
        extractBtn.textContent = 'Extract Page Data'
      }, 2000)
    }
  })

  // Take screenshot
  screenshotBtn.addEventListener('click', async () => {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true })
    if (!tab) return

    try {
      // Use chrome.debugger to take screenshot
      const dataUrl = await new Promise((resolve, reject) => {
        chrome.debugger.attach({ tabId: tab.id }, '1.3', () => {
          if (chrome.runtime.lastError) {
            reject(chrome.runtime.lastError)
            return
          }
          chrome.debugger.sendCommand({ tabId: tab.id }, 'Page.captureScreenshot', { format: 'png' }, (result) => {
            chrome.debugger.detach({ tabId: tab.id }, () => {})
            if (result) {
              resolve('data:image/png;base64,' + result.data)
            } else {
              reject(new Error('No screenshot data'))
            }
          })
        })
      })

      // Download the screenshot
      const link = document.createElement('a')
      link.href = dataUrl
      link.download = `linkagent-screenshot-${Date.now()}.png`
      link.click()
      
      screenshotBtn.textContent = 'Screenshot Saved!'
      setTimeout(() => {
        screenshotBtn.textContent = 'Take Screenshot'
      }, 2000)
    } catch (e) {
      console.error('Screenshot error:', e)
      screenshotBtn.textContent = 'Error - Try Again'
      setTimeout(() => {
        screenshotBtn.textContent = 'Take Screenshot'
      }, 2000)
    }
  })
})
