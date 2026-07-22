# LinkedIn MCP Server - Project Root

## Structure
```
D:\Linkedin-job\
├── OPTIMIZATION_PLAN.md          # This project's optimization plan
├── AUTH_COOKIE_ARCHITECTURE.md   # Cookie/fingerprint architecture (to be created)
├── AGENT_INTEGRATION_GUIDE.md    # Agent integration guide (to be created)
├── README.md                     # This file
├── config/                       # Configuration files
├── docs/                         # Documentation
├── scripts/                      # Utility scripts
├── tests/                        # Integration tests
└── linkedin-mcp-server/          # Main MCP server (existing)
```

## Quick Start
```bash
cd linkedin-mcp-server
pip install -e .
python -m linkedin_mcp_server.server
```

## Optimization Plan
See `OPTIMIZATION_PLAN.md` for the 8-phase transformation plan.