// LinkAgent Content Script - Page Data Extraction
// Runs in the context of web pages to extract structured data

(function() {
  'use strict'

  // Listen for messages from background script
  chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
    if (msg.type === 'getPageContent') {
      const data = extractPageData()
      sendResponse(data)
    }
    if (msg.type === 'getElementInfo') {
      const info = getElementInfo(msg.selector)
      sendResponse(info)
    }
    return true
  })

  // Extract structured page data
  function extractPageData() {
    return {
      url: window.location.href,
      title: document.title,
      meta: extractMeta(),
      headings: extractHeadings(),
      links: extractLinks(),
      images: extractImages(),
      forms: extractForms(),
      text: extractText(),
      structuredData: extractStructuredData(),
      openGraph: extractOpenGraph(),
      timestamp: Date.now(),
    }
  }

  // Extract meta tags
  function extractMeta() {
    const metas = {}
    document.querySelectorAll('meta').forEach(meta => {
      const name = meta.getAttribute('name') || meta.getAttribute('property')
      const content = meta.getAttribute('content')
      if (name && content) metas[name] = content
    })
    return metas
  }

  // Extract headings hierarchy
  function extractHeadings() {
    const headings = []
    document.querySelectorAll('h1, h2, h3, h4, h5, h6').forEach(h => {
      headings.push({
        level: parseInt(h.tagName[1]),
        text: h.textContent.trim(),
        id: h.id || null,
      })
    })
    return headings
  }

  // Extract links
  function extractLinks() {
    const links = []
    document.querySelectorAll('a[href]').forEach(a => {
      links.push({
        href: a.href,
        text: a.textContent.trim().substring(0, 100),
        title: a.title || null,
        rel: a.rel || null,
      })
    })
    return links.slice(0, 100) // Limit to first 100
  }

  // Extract images
  function extractImages() {
    const images = []
    document.querySelectorAll('img').forEach(img => {
      images.push({
        src: img.src,
        alt: img.alt || '',
        width: img.naturalWidth,
        height: img.naturalHeight,
        loading: img.loading || null,
      })
    })
    return images.slice(0, 50) // Limit to first 50
  }

  // Extract forms
  function extractForms() {
    const forms = []
    document.querySelectorAll('form').forEach(form => {
      const fields = []
      form.querySelectorAll('input, select, textarea').forEach(field => {
        fields.push({
          type: field.type || field.tagName.toLowerCase(),
          name: field.name || null,
          id: field.id || null,
          placeholder: field.placeholder || null,
          required: field.required,
          value: field.type !== 'password' ? field.value : null,
        })
      })
      forms.push({
        action: form.action || null,
        method: form.method || 'GET',
        id: form.id || null,
        fields,
      })
    })
    return forms
  }

  // Extract main text content
  function extractText() {
    // Try to find main content area
    const main = document.querySelector('main, article, [role="main"], .content, .main')
    const target = main || document.body
    
    // Get text, removing scripts and styles
    const clone = target.cloneNode(true)
    clone.querySelectorAll('script, style, noscript, iframe').forEach(el => el.remove())
    
    return clone.textContent
      .replace(/\s+/g, ' ')
      .trim()
      .substring(0, 5000) // Limit to 5000 chars
  }

  // Extract JSON-LD structured data
  function extractStructuredData() {
    const data = []
    document.querySelectorAll('script[type="application/ld+json"]').forEach(script => {
      try {
        data.push(JSON.parse(script.textContent))
      } catch {}
    })
    return data
  }

  // Extract Open Graph data
  function extractOpenGraph() {
    const og = {}
    document.querySelectorAll('meta[property^="og:"]').forEach(meta => {
      const property = meta.getAttribute('property').replace('og:', '')
      og[property] = meta.getAttribute('content')
    })
    return og
  }

  // Get element info by selector
  function getElementInfo(selector) {
    try {
      const el = document.querySelector(selector)
      if (!el) return null
      const rect = el.getBoundingClientRect()
      return {
        tagName: el.tagName,
        id: el.id,
        className: el.className,
        text: el.textContent.trim().substring(0, 500),
        href: el.href || null,
        src: el.src || null,
        rect: {
          x: rect.x,
          y: rect.y,
          width: rect.width,
          height: rect.height,
        },
        attributes: Array.from(el.attributes).map(a => ({
          name: a.name,
          value: a.value,
        })),
      }
    } catch {
      return null
    }
  }

  console.log('LinkAgent content script loaded')
})()
