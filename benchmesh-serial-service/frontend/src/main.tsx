import React from 'react'
import { createRoot } from 'react-dom/client'
import App from './ui/App'
import { DocsPage } from './ui/DocsPage'
import { MetricsPage } from './ui/MetricsPage'

// Simple routing: check URL path to determine which component to render
const path = window.location.pathname

const root = createRoot(document.getElementById('root')!)

// Render appropriate page based on URL path
if (path === '/ui/metrics' || path === '/ui/metrics/') {
  root.render(<MetricsPage />)
} else if (path === '/ui/docs' || path === '/ui/docs/') {
  root.render(<DocsPage />)
} else {
  root.render(<App />)
}
//root.render(<React.StrictMode><App /></React.StrictMode>)