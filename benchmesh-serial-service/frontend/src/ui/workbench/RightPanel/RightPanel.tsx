/**
 * RightPanel - Documentation and API Reference panel (overlays main content)
 *
 * Tabs:
 * - Documentation: User guides, getting started, configuration
 * - API Reference: Swagger UI for API documentation
 */

import React, { useState, useEffect } from 'react';
import { VscClose, VscBook, VscSymbolMethod } from 'react-icons/vsc';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import SwaggerUI from 'swagger-ui-react';
import 'swagger-ui-react/swagger-ui.css';
import './right-panel.css';

type TabType = 'documentation' | 'api-reference';

interface DocPage {
  id: string;
  title: string;
  file: string;
}

// Documentation pages (excluding API Reference which has its own tab)
const DOC_PAGES: DocPage[] = [
  { id: 'home', title: 'Home', file: 'Home.md' },
  { id: 'getting-started', title: 'Getting Started', file: 'Getting-Started.md' },
  { id: 'configuration', title: 'Configuration', file: 'Configuration.md' },
  { id: 'automation', title: 'Automation & Node-RED', file: 'Automation.md' },
];

interface RightPanelProps {
  apiBase: string;
  onClose: () => void;
}

export const RightPanel: React.FC<RightPanelProps> = ({ apiBase, onClose }) => {
  const [activeTab, setActiveTab] = useState<TabType>('documentation');
  const [activePage, setActivePage] = useState('home');
  const [markdownContent, setMarkdownContent] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);

  const tabs = [
    { id: 'documentation', label: 'Documentation', icon: VscBook },
    { id: 'api-reference', label: 'API Reference', icon: VscSymbolMethod },
  ] as const;

  // Load markdown files
  useEffect(() => {
    async function loadDocs() {
      const content: Record<string, string> = {};
      for (const page of DOC_PAGES) {
        try {
          const response = await fetch(`/ui/docs/${page.file}`);
          content[page.id] = await response.text();
        } catch (e) {
          content[page.id] = `# Error\n\nFailed to load documentation for ${page.title}`;
        }
      }
      setMarkdownContent(content);
      setLoading(false);
    }
    loadDocs();
  }, []);

  // Scroll to top when page changes
  useEffect(() => {
    const content = document.querySelector('.right-panel__content');
    if (content) {
      content.scrollTop = 0;
    }
  }, [activePage]);

  const currentPage = DOC_PAGES.find(p => p.id === activePage) || DOC_PAGES[0];

  return (
    <div className="right-panel" data-testid="right-panel">
      <div className="right-panel__tabs">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          return (
            <button
              key={tab.id}
              className={`right-panel__tab ${activeTab === tab.id ? 'right-panel__tab--active' : ''}`}
              onClick={() => setActiveTab(tab.id as TabType)}
              data-testid={`right-panel-tab-${tab.id}`}
            >
              <Icon size={16} />
              <span>{tab.label}</span>
            </button>
          );
        })}
        <div className="right-panel__spacer" />
        <button
          className="right-panel__close"
          onClick={onClose}
          title="Close panel"
          aria-label="Close panel"
        >
          <VscClose size={16} />
        </button>
      </div>

      <div className="right-panel__content">
        {activeTab === 'documentation' && (
          <div className="right-panel__docs">
            <div className="right-panel__docs-sidebar">
              <nav className="right-panel__docs-nav">
                {DOC_PAGES.map(page => (
                  <button
                    key={page.id}
                    className={`right-panel__docs-nav-item ${activePage === page.id ? 'right-panel__docs-nav-item--active' : ''}`}
                    onClick={() => setActivePage(page.id)}
                  >
                    {page.title}
                  </button>
                ))}
              </nav>
            </div>
            <div className="right-panel__docs-content">
              {loading ? (
                <div className="right-panel__loading">
                  Loading documentation...
                </div>
              ) : (
                <div className="right-panel__markdown">
                  <ReactMarkdown
                    remarkPlugins={[remarkGfm]}
                    components={{
                      // Custom rendering for links to handle internal doc navigation
                      a: ({ node, href, children, ...props }) => {
                        // Check if it's an internal doc link
                        const docPage = DOC_PAGES.find(p =>
                          p.title === href || p.id === href
                        );
                        if (docPage) {
                          return (
                            <a
                              {...props}
                              href="#"
                              onClick={(e) => {
                                e.preventDefault();
                                setActivePage(docPage.id);
                              }}
                            >
                              {children}
                            </a>
                          );
                        }
                        // External link
                        return <a href={href} target="_blank" rel="noopener noreferrer" {...props}>{children}</a>;
                      },
                      // Style code blocks
                      code: ({ node, inline, className, children, ...props }: any) => {
                        if (inline) {
                          return <code className="inline-code" {...props}>{children}</code>;
                        }
                        return <code className={className} {...props}>{children}</code>;
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
        )}
        {activeTab === 'api-reference' && (
          <div className="right-panel__api">
            <SwaggerUI url={`${apiBase}/openapi.json`} />
          </div>
        )}
      </div>
    </div>
  );
};
