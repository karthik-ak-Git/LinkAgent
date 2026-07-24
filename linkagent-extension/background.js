// LinkAgent Browser Bridge - Background Service Worker
// Connects real Chrome to LinkAgent for AI-powered browser automation

const HOST_NAME = 'com.linkagent.bridge'
const SKIP_URL = /^(chrome|chrome-extension|devtools|chrome-untrusted|edge|about):/i
const WS_PORT = 8765

/** @type {chrome.runtime.Port|null} */
let port = null
let hostConnected = false
const tabs = new Map()
const sessionToTab = new Map()

// ---- Keep-Alive Mechanism ----

let keepAliveInterval = null
const KEEP_ALIVE_INTERVAL_MS = 20000 // 20 seconds

function startKeepAlive() {
  if (keepAliveInterval) return
  keepAliveInterval = setInterval(() => {
    if (port) {
      try {
        port.postMessage({ method: 'keepAlive' })
      } catch (e) {
        console.warn('[LinkAgent] Keep-alive ping failed, reconnecting...')
        reconnect()
      }
    }
  }, KEEP_ALIVE_INTERVAL_MS)
}

function stopKeepAlive() {
  if (keepAliveInterval) {
    clearInterval(keepAliveInterval)
    keepAliveInterval = null
  }
}

// ---- Reconnection Logic ----

let reconnectTimer = null
let reconnectAttempts = 0
const MAX_RECONNECT_ATTEMPTS = 50
const BASE_DELAY = 500
const MAX_DELAY = 15000

function scheduleReconnect() {
  if (reconnectTimer) return
  if (reconnectAttempts >= MAX_RECONNECT_ATTEMPTS) {
    console.error('[LinkAgent] Max reconnect attempts reached')
    return
  }

  const delay = Math.min(BASE_DELAY * Math.pow(1.5, reconnectAttempts), MAX_DELAY)
  console.log(`[LinkAgent] Reconnecting in ${delay}ms (attempt ${reconnectAttempts + 1})`)

  reconnectTimer = setTimeout(() => {
    reconnectTimer = null
    reconnectAttempts++
    connectHost()
  }, delay)
}

function reconnect() {
  disconnectHost()
  scheduleReconnect()
}

function disconnectHost() {
  stopKeepAlive()
  if (port) {
    try {
      port.disconnect()
    } catch {}
    port = null
  }
  hostConnected = false
  notifyConnChange(false)
}

// ---- Native Messaging Transport ----

function connectHost() {
  if (port) return

  try {
    port = chrome.runtime.connectNative(HOST_NAME)
  } catch (e) {
    console.error('[LinkAgent] connectNative failed:', e)
    port = null
    hostConnected = false
    scheduleReconnect()
    return
  }

  port.onMessage.addListener((msg) => {
    reconnectAttempts = 0 // Reset on successful message
    onHostMessage(msg)
  })

  port.onDisconnect.addListener(() => {
    const lastError = chrome.runtime.lastError
    if (lastError) {
      console.warn('[LinkAgent] Port disconnected:', lastError.message)
    } else {
      console.log('[LinkAgent] Port disconnected (clean)')
    }
    void chrome.runtime.lastError

    port = null
    hostConnected = false
    notifyConnChange(false)
    stopKeepAlive()

    // Schedule reconnection
    scheduleReconnect()
  })

  // Send hello handshake
  postToHost({
    method: 'hello',
    version: chrome.runtime.getManifest().version,
    capabilities: ['pageData', 'screenshots', 'accessibilityTree'],
  })

  hostConnected = true
  notifyConnChange(true)
  startKeepAlive()
}

function postToHost(msg) {
  try {
    if (port) {
      port.postMessage(msg)
    }
  } catch (e) {
    console.warn('[LinkAgent] postToHost failed:', e.message)
    // port died; onDisconnect will reconnect
  }
}

// ---- Connection Notifications ----

function notifyConnChange(connected) {
  // Notifications disabled - check popup or logs instead
  console.log(`[LinkAgent] Connection state: ${connected ? 'connected' : 'disconnected'}`)
}

// ---- Page Data Extraction ----

async function extractPageData(tabId) {
  try {
    const tab = await chrome.tabs.get(tabId)
    if (!tab || !tab.url) return null

    const accessibilityTree = await getAccessibilityTree(tabId)

    let pageContent = null
    try {
      pageContent = await chrome.tabs.sendMessage(tabId, { type: 'getPageContent' })
    } catch {
      // Content script might not be injected yet
    }

    return {
      url: tab.url,
      title: tab.title,
      timestamp: Date.now(),
      accessibilityTree,
      content: pageContent,
    }
  } catch (e) {
    console.error('[LinkAgent] extractPageData error:', e)
    return null
  }
}

async function getAccessibilityTree(tabId) {
  try {
    const result = await chrome.debugger.sendCommand(
      { tabId },
      'Accessibility.getFullAXTree',
      { depth: -1 }
    )
    return result.nodes || []
  } catch {
    return []
  }
}

async function takeScreenshot(tabId, format = 'png') {
  try {
    const dataUrl = await chrome.debugger.sendCommand(
      { tabId },
      'Page.captureScreenshot',
      { format }
    )
    return dataUrl.data
  } catch {
    return null
  }
}

// ---- CDP Command Handling ----

async function onHostMessage(msg) {
  if (!msg || typeof msg !== 'object') return

  // Handle keepAlive pong
  if (msg.method === 'pong' || msg.method === 'keepAlive') return

  if (msg.method === 'ping') {
    postToHost({ method: 'pong' })
    return
  }

  if (typeof msg.id !== 'undefined' && msg.method === 'forwardCDPCommand') {
    try {
      const result = await handleForwardCdpCommand(msg)
      postToHost({ id: msg.id, result })
    } catch (err) {
      postToHost({ id: msg.id, error: err instanceof Error ? err.message : String(err) })
    }
  }
}

async function handleForwardCdpCommand(msg) {
  const method = String(msg?.params?.method || '')
  const params = msg?.params?.params || undefined
  const sessionId = typeof msg?.params?.sessionId === 'string' ? msg.params.sessionId : undefined

  // Custom LinkAgent commands
  if (method === 'LinkAgent.extractPageData') {
    const tabId = tabIdFromSession(sessionId)
    if (!tabId) throw new Error('No tab for session')
    return await extractPageData(tabId)
  }

  if (method === 'LinkAgent.screenshot') {
    const tabId = tabIdFromSession(sessionId)
    if (!tabId) throw new Error('No tab for session')
    const format = params?.format || 'png'
    return await takeScreenshot(tabId, format)
  }

  // Standard CDP commands
  let tabId
  if (sessionId) {
    tabId = tabIdFromSession(sessionId) ?? tabForSession(sessionId)
  } else if (typeof params?.targetId === 'string') {
    tabId = tabForTarget(params.targetId)
  } else {
    tabId = anyConnectedTab()
  }
  if (tabId == null) throw new Error(`no attached tab for ${method}`)

  return await chrome.debugger.sendCommand({ tabId }, method, params)
}

function tabIdFromSession(sessionId) {
  const m = /^cb-tab-(\d+)$/.exec(sessionId || '')
  return m ? Number(m[1]) : null
}

function tabForSession(sessionId) {
  return sessionToTab.get(sessionId) ?? null
}

function tabForTarget(targetId) {
  for (const [tabId, t] of tabs.entries()) if (t.targetId === targetId) return tabId
  return null
}

function anyConnectedTab() {
  const it = tabs.keys().next()
  return it.done ? null : it.value
}

// ---- Tab Management ----

async function attachTab(tabId) {
  const existing = tabs.get(tabId)
  if (existing) return existing

  const dbg = { tabId }
  try {
    await chrome.debugger.attach(dbg, '1.3')
  } catch (e) {
    const msg = String((e && e.message) || e)
    if (!/already attached|already being debugged/i.test(msg)) throw e
  }

  await chrome.debugger.sendCommand(dbg, 'Page.enable').catch(() => {})

  const info = await chrome.debugger.sendCommand(dbg, 'Target.getTargetInfo')
  const targetInfo = info?.targetInfo
  const targetId = String(targetInfo?.targetId || '')
  if (!targetId) throw new Error('attachTab: no targetId')

  const sessionId = `cb-tab-${tabId}`
  const entry = { sessionId, targetId }
  tabs.set(tabId, entry)
  sessionToTab.set(sessionId, tabId)

  postToHost({
    method: 'forwardCDPEvent',
    params: {
      sessionId,
      method: 'Target.attachedToTarget',
      params: { sessionId, targetInfo: { ...targetInfo, attached: true } },
    },
  })

  return entry
}

function detachTab(tabId, notify) {
  const entry = tabs.get(tabId)
  if (!entry) return
  tabs.delete(tabId)
  sessionToTab.delete(entry.sessionId)
  if (notify) {
    postToHost({
      method: 'forwardCDPEvent',
      params: {
        sessionId: entry.sessionId,
        method: 'Target.detachedFromTarget',
        params: { sessionId: entry.sessionId },
      },
    })
  }
}

function eligible(tab) {
  return !!tab && !!tab.id && typeof tab.url === 'string' && !SKIP_URL.test(tab.url)
}

// ---- Tab Lifecycle ----

chrome.tabs.onCreated.addListener((tab) =>
  void (async () => {
    if (!port || !tab || tab.id == null) return
    if (typeof tab.url === 'string' && tab.url && SKIP_URL.test(tab.url)) return
    try {
      await attachTab(tab.id)
    } catch {}
  })()
)

chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) =>
  void (async () => {
    if (changeInfo.status === 'complete' && eligible(tab) && !tabs.has(tabId) && port) {
      try {
        await attachTab(tabId)
      } catch {}
    }
  })()
)

chrome.tabs.onRemoved.addListener((tabId) =>
  void (async () => {
    detachTab(tabId, true)
  })()
)

chrome.debugger.onDetach.addListener((source, reason) =>
  void (async () => {
    const tabId = source.tabId
    if (!tabId) return
    detachTab(tabId, true)
    if (reason === 'canceled_by_user' || reason === 'replaced_with_devtools') return
    if (!port) return

    // Retry attach with backoff
    for (let i = 0; i < 6; i++) {
      await new Promise((r) => setTimeout(r, 250 + i * 200))
      if (tabs.has(tabId)) return
      const tab = await chrome.tabs.get(tabId).catch(() => null)
      if (!tab || !eligible(tab)) return
      try {
        await attachTab(tabId)
        return
      } catch {}
    }
  })()
)

chrome.debugger.onEvent.addListener((source, method, params) =>
  void (() => {
    const tabId = source.tabId
    if (!tabId) return
    const entry = tabs.get(tabId)
    if (!entry) return
    postToHost({
      method: 'forwardCDPEvent',
      params: { sessionId: entry.sessionId, method, params },
    })
  })()
)

// ---- Bootstrap ----

chrome.runtime.onInstalled.addListener(() => {
  console.log('[LinkAgent] Extension installed/updated')
  connectHost()
})

chrome.runtime.onStartup.addListener(() => {
  console.log('[LinkAgent] Chrome started')
  connectHost()
})

chrome.idle.setDetectionInterval(15)
chrome.idle.onStateChanged.addListener((state) => {
  if (state === 'active' && !port) {
    console.log('[LinkAgent] Browser became active, reconnecting...')
    connectHost()
  }
})

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (msg && msg.type === 'la-status') {
    if (!port) {
      try { connectHost() } catch {}
    }
    sendResponse({ connected: hostConnected, tabCount: tabs.size })
  }
  return true
})

// Initial connection
console.log('[LinkAgent] Service worker starting...')
connectHost()
