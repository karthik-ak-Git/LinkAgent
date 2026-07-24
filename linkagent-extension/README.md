# LinkAgent Browser Bridge

A Chrome extension that connects your real browser to LinkAgent for AI-powered automation.

## Features

- **Real Chrome Automation** - Drives your actual logged-in Chrome, no headless browsers
- **Page Data Extraction** - Extracts structured data, links, images, forms, and text
- **Accessibility Tree** - Full accessibility tree for AI agents
- **Screenshots** - Capture page screenshots
- **MCP Integration** - Works with Claude Code, Cursor, and other AI agents
- **Real-time Communication** - Native messaging for fast, reliable connection

## Installation

### Load as Unpacked Extension

1. Open Chrome and go to `chrome://extensions/`
2. Enable "Developer mode" (toggle in top right)
3. Click "Load unpacked"
4. Select the `linkagent-extension` folder
5. Pin the extension to your toolbar

### Register Native Messaging Host

Run the registration script to connect the extension to the CLI:

```powershell
# Windows
.\register-host.ps1
```

## Usage

### Basic Commands

```bash
# Open a URL
linkagent open "https://linkedin.com/feed"

# Take a screenshot
linkagent screenshot

# Extract page data
linkagent extract

# Get accessibility tree
linkagent snapshot
```

### MCP Server

Start the MCP server for AI agent integration:

```bash
linkagent mcp
```

This exposes tools like:
- `open_url` - Navigate to a URL
- `take_screenshot` - Capture page screenshot
- `extract_data` - Extract structured page data
- `get_accessibility_tree` - Get accessibility tree
- `click_element` - Click an element
- `type_text` - Type text into a field

## Architecture

```
┌─────────────────────────────────────────┐
│           Your Real Chrome              │
│  ┌─────────────────────────────────┐   │
│  │    LinkAgent Extension          │   │
│  │  • Content scripts              │   │
│  │  • Background service worker    │   │
│  │  • Native messaging bridge      │   │
│  └─────────────────────────────────┘   │
└─────────────────────────────────────────┘
                    │
                    │ Native Messaging
                    ▼
┌─────────────────────────────────────────┐
│        LinkAgent CLI / MCP Server       │
│  • CDP command routing                  │
│  • Page data extraction                 │
│  • AI agent integration                 │
└─────────────────────────────────────────┘
                    │
                    │ MCP Protocol
                    ▼
┌─────────────────────────────────────────┐
│           Your AI Agent                 │
│  • Claude Code / Cursor / Codex        │
│  • Custom applications                  │
└─────────────────────────────────────────┘
```

## Permissions

- `debugger` - Attach to tabs for CDP commands
- `tabs` - Query and manage tabs
- `nativeMessaging` - Communicate with local CLI
- `storage` - Store settings
- `activeTab` - Access current tab
- `scripting` - Inject content scripts

## Development

### File Structure

```
linkagent-extension/
├── manifest.json          # Extension manifest
├── background.js          # Service worker
├── content.js             # Content script
├── popup.html             # Popup UI
├── popup.js               # Popup logic
├── options.html           # Settings page
├── options.js             # Settings logic
├── native-host.json       # Native messaging manifest
└── icons/                 # Extension icons
```

### Building

This is a plain JavaScript extension (no build step required). Just load it unpacked.

## License

MIT
