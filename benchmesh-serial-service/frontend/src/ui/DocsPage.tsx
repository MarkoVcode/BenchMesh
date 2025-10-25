import React, { useState, useEffect, useMemo } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import SwaggerUI from 'swagger-ui-react'
import 'swagger-ui-react/swagger-ui.css'

interface DocPage {
  id: string
  title: string
  file: string
  isSwagger?: boolean
}

const DOC_PAGES: DocPage[] = [
  { id: 'home', title: 'Home', file: 'Home.md' },
  { id: 'getting-started', title: 'Getting Started', file: 'Getting-Started.md' },
  { id: 'configuration', title: 'Configuration', file: 'Configuration.md' },
  { id: 'automation', title: 'Automation & Node-RED', file: 'Automation.md' },
  { id: 'api-reference', title: 'API Reference', file: 'API-Reference.md', isSwagger: true },
]

/**
 * Standalone documentation page component for Electron help menu.
 * Displays documentation without modal wrapper as a full page view.
 */
export function DocsPage() {
  const [activePage, setActivePage] = useState('home')
  const [markdownContent, setMarkdownContent] = useState<Record<string, string>>({})
  const [loading, setLoading] = useState(true)
  const currentPage = DOC_PAGES.find(p => p.id === activePage) || DOC_PAGES[0]

  // Determine API base URL
  const apiBase = useMemo(() => {
    return `${window.location.protocol}//${window.location.hostname}:57666`
  }, [])

  // Load markdown files
  useEffect(() => {
    async function loadDocs() {
      const content: Record<string, string> = {}
      for (const page of DOC_PAGES) {
        if (!page.isSwagger) {
          try {
            const response = await fetch(`/ui/docs/${page.file}`)
            content[page.id] = await response.text()
          } catch (e) {
            content[page.id] = `# Error\n\nFailed to load documentation for ${page.title}`
          }
        }
      }
      setMarkdownContent(content)
      setLoading(false)
    }
    loadDocs()
  }, [])

  // Scroll to top when page changes
  useEffect(() => {
    const content = document.querySelector('.docs-page-content')
    if (content) {
      content.scrollTop = 0
    }
  }, [activePage])

  return (
    <div className="docs-page">
      <div className="docs-page-header">
        <h1>📚 BenchMesh Documentation</h1>
      </div>

      <div className="docs-page-body">
        <div className="docs-sidebar">
          <nav className="docs-nav">
            {DOC_PAGES.map(page => (
              <button
                key={page.id}
                className={`docs-nav-item ${activePage === page.id ? 'active' : ''}`}
                onClick={() => setActivePage(page.id)}
              >
                {page.title}
              </button>
            ))}
          </nav>
        </div>

        <div className="docs-page-content">
          {loading ? (
            <div style={{ textAlign: 'center', padding: '40px', color: 'var(--text-1)' }}>
              Loading documentation...
            </div>
          ) : currentPage.isSwagger ? (
            <div className="docs-swagger-wrapper">
              <div className="docs-api-intro">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {markdownContent[currentPage.id] || ''}
                </ReactMarkdown>
              </div>
              <div className="docs-swagger-container">
                <SwaggerUI url={`${apiBase}/openapi.json`} />
              </div>
            </div>
          ) : (
            <div className="docs-markdown">
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                  // Custom rendering for links to handle internal doc navigation
                  a: ({ node, href, children, ...props }) => {
                    // Check if it's an internal doc link
                    const docPage = DOC_PAGES.find(p =>
                      p.title === href || p.id === href
                    )
                    if (docPage) {
                      return (
                        <a
                          {...props}
                          href="#"
                          onClick={(e) => {
                            e.preventDefault()
                            setActivePage(docPage.id)
                          }}
                        >
                          {children}
                        </a>
                      )
                    }
                    // External link
                    return <a href={href} target="_blank" rel="noopener noreferrer" {...props}>{children}</a>
                  },
                  // Style code blocks
                  code: ({ node, inline, className, children, ...props }: any) => {
                    if (inline) {
                      return <code className="inline-code" {...props}>{children}</code>
                    }
                    return <code className={className} {...props}>{children}</code>
                  },
                  // Style tables
                  table: ({ node, ...props }) => (
                    <div className="table-wrapper">
                      <table {...props} />
                    </div>
                  ),
                }}
              >
                {markdownContent[currentPage.id] || '# Loading...\n\nPlease wait...'}
              </ReactMarkdown>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
