
import { useMemo, useState } from 'react'
import type { FormEvent } from 'react'
import { getStudyNotes } from './api'
import type { NotesResponse, NotesSource } from './types'
import './App.css'

type Book = {
  id: number
  title: string
  author: string
  category: string
  year: string
  access: 'Digital text available' | 'Catalogue only' | 'Physical only'
  location: string
  description: string
  tags: string[]
}

const sampleBooks: Book[] = [
  {
    id: 1,
    title: 'Database System Concepts',
    author: 'Abraham Silberschatz, Henry F. Korth and S. Sudarshan',
    category: 'Computer Science',
    year: '2019',
    access: 'Digital text available',
    location: 'Computer Science · Database Systems',
    description:
      'An introduction to database architecture, relational models, SQL, transactions and database design.',
    tags: ['database', 'sql', 'transactions', 'relational model'],
  },
  {
    id: 2,
    title: 'Fundamentals of Data Science',
    author: 'Sample catalogue record',
    category: 'Data Science',
    year: '2023',
    access: 'Catalogue only',
    location: 'Data Science · General Collection',
    description:
      'A catalogue record for a book about data analysis, statistics and machine learning.',
    tags: ['data science', 'statistics', 'machine learning', 'analytics'],
  },
  {
    id: 3,
    title: 'Introduction to Algorithms',
    author: 'Thomas H. Cormen and others',
    category: 'Computer Science',
    year: '2009',
    access: 'Physical only',
    location: 'Shelf location not verified',
    description:
      'A reference on algorithm design, sorting, graph algorithms and computational complexity.',
    tags: ['algorithms', 'sorting', 'graphs', 'programming'],
  },
]

const sampleNotes = [
  {
    heading: 'Database fundamentals',
    text: 'A database organizes related information so it can be stored, retrieved and managed systematically.',
    source: 'Database System Concepts',
    page: 'Sample page — not verified',
  },
  {
    heading: 'Relational model',
    text: 'The relational model represents data using relations, commonly displayed as tables with rows and columns.',
    source: 'Database System Concepts',
    page: 'Sample page — not verified',
  },
  {
    heading: 'Transactions',
    text: 'A database transaction is a logical unit of work. Its correctness depends on the database system enforcing the required transaction properties.',
    source: 'Database System Concepts',
    page: 'Sample page — not verified',
  },
]

function getAccessStatusLabel(status: string): string {
  const labels: Record<string, string> = {
    digital_available: 'Digital text available',
    digital_full_text: 'Digital full text',
    licensed_link: 'Licensed link',
    metadata_only: 'Catalogue only',
    physical_only: 'Physical only',
    unknown: 'Access unknown',
  }

  return labels[status] ?? status.replaceAll('_', ' ')
}

function getVerifiedPage(source: NotesSource): string | null {
  if (source.printed_page_verified && source.printed_page_label) {
    return `Printed page ${source.printed_page_label}`
  }

  if (
    source.pdf_page_index !== null &&
    source.pdf_page_index !== undefined
  ) {
    return `PDF page ${source.pdf_page_index + (source.pdf_page_base ?? 0) + 1}`
  }

  return null
}

function App() {
  const [query, setQuery] = useState('')
  const [submittedQuery, setSubmittedQuery] = useState('')
  const [activeTab, setActiveTab] = useState<'search' | 'notes'>('search')
  const [selectedBook, setSelectedBook] = useState<Book | null>(null)
  const [showAllBooks, setShowAllBooks] = useState(false)

  const [notesQuery, setNotesQuery] = useState('')
  const [notesResponse, setNotesResponse] = useState<NotesResponse | null>(null)
  const [notesLoading, setNotesLoading] = useState(false)
  const [notesError, setNotesError] = useState('')
  const [expandedSource, setExpandedSource] = useState<string | null>(null)

  const filteredBooks = useMemo(() => {
    const normalizedQuery = submittedQuery.trim().toLowerCase()

    if (!normalizedQuery) return sampleBooks

    const words = normalizedQuery.split(/\s+/)

    return sampleBooks.filter((book) => {
      const searchableText = [
        book.title,
        book.author,
        book.category,
        book.description,
        ...book.tags,
      ]
        .join(' ')
        .toLowerCase()

      return words.some((word) => searchableText.includes(word))
    })
  }, [submittedQuery])

  const visibleBooks = showAllBooks
    ? filteredBooks
    : filteredBooks.slice(0, 3)

  async function handleGenerateNotes(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()

    const normalizedQuery = notesQuery.trim()

    if (!normalizedQuery) {
      setNotesError('Enter a topic before generating study notes.')
      setNotesResponse(null)
      return
    }

    if (normalizedQuery.length > 300) {
      setNotesError('Your topic must be 300 characters or fewer.')
      setNotesResponse(null)
      return
    }

    setNotesLoading(true)
    setNotesError('')
    setNotesResponse(null)
    setExpandedSource(null)

    try {
      const response = await getStudyNotes({
        query: normalizedQuery,
        top_k: 5,
      })

      setNotesResponse(response)
    } catch (error) {
      setNotesError(
        error instanceof Error
          ? error.message
          : 'Unable to generate study notes. Please try again.',
      )
    } finally {
      setNotesLoading(false)
    }
  }

  function handleSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setSubmittedQuery(query.trim())
    setSelectedBook(null)
    setShowAllBooks(false)
    setActiveTab('search')
  }

  function resetSearch() {
    setQuery('')
    setSubmittedQuery('')
    setSelectedBook(null)
    setShowAllBooks(false)
    setActiveTab('search')
  }

  function exploreNotes(book?: Book) {
    if (book) {
      setNotesQuery(book.title)
    } else if (submittedQuery) {
      setNotesQuery(submittedQuery)
    }

    setNotesResponse(null)
    setNotesError('')
    setActiveTab('notes')
    setSelectedBook(null)
  }

  function renderSource(source: NotesSource) {
    const page = getVerifiedPage(source)
    const isExpanded = expandedSource === source.chunk_id

    return (
      <article className="citation-chip" key={source.chunk_id}>
        <button
          type="button"
          className="citation-source-button"
          onClick={() =>
            setExpandedSource(isExpanded ? null : source.chunk_id)
          }
          aria-expanded={isExpanded}
        >
          <span aria-hidden="true">▤</span>
          <span>
            {source.title}
            {page ? ` · ${page}` : ' · Page not verified'}
          </span>
          <span className="source-expand-indicator">
            {isExpanded ? '−' : '+'}
          </span>
        </button>

        {isExpanded && (
          <div className="source-details">
            <h4>{source.title}</h4>

            {source.author && <p>Author: {source.author}</p>}
            {source.edition && <p>Edition: {source.edition}</p>}
            {source.section_heading && (
              <p>Section: {source.section_heading}</p>
            )}

            <p>
              Access status: {getAccessStatusLabel(source.access_status)}
            </p>

            {source.is_sample_data && (
              <p className="source-sample-warning">
                Demo source record — verify against the original material.
              </p>
            )}

            {source.excerpt ? (
              <blockquote>{source.excerpt}</blockquote>
            ) : (
              <p>No source excerpt was provided.</p>
            )}

            {!source.printed_page_verified && (
              <p className="source-page-warning">
                The printed page number has not been verified.
              </p>
            )}
          </div>
        )}
      </article>
    )
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <a
          className="brand"
          href="#"
          onClick={(event) => {
            event.preventDefault()
            resetSearch()
          }}
        >
          <span className="brand-icon">L</span>
          <span>
            <strong>LibraLink</strong>
            <small>Library research companion</small>
          </span>
        </a>

        <div className="sidebar-label">WORKSPACE</div>

        <button
          className={`nav-item ${activeTab === 'search' ? 'active' : ''}`}
          onClick={() => setActiveTab('search')}
        >
          <span className="nav-icon">⌕</span>
          Find resources
        </button>

        <button
          className={`nav-item ${activeTab === 'notes' ? 'active' : ''}`}
          onClick={() => setActiveTab('notes')}
        >
          <span className="nav-icon">▤</span>
          Study notes
          <span className="nav-count">
            {notesResponse?.sections.length ?? 3}
          </span>
        </button>

        <div className="sidebar-divider" />

        <div className="sidebar-label">YOUR LIBRARY</div>
        <div className="library-link"><span>▧</span>Computer Science</div>
        <div className="library-link"><span>▧</span>Data Science</div>
        <div className="library-link"><span>▧</span>General Collection</div>

        <div className="sidebar-bottom">
          <div className="help-card">
            <span className="help-icon">i</span>
            <strong>Research with confidence</strong>
            <p>Always verify your study notes against the original source.</p>
          </div>

          <div className="profile">
            <div className="avatar">S</div>
            <div>
              <strong>Student workspace</strong>
              <small>Prototype account</small>
            </div>
            <span className="profile-menu">•••</span>
          </div>
        </div>
      </aside>

      <main className="main-content">
        <header className="topbar">
          <div className="breadcrumb">
            Workspace <span>/</span>{' '}
            {activeTab === 'search' ? 'Find resources' : 'Study notes'}
          </div>
          <div className="prototype-pill">
            <span className="status-dot" />
            Prototype mode
          </div>
        </header>

        <div className="page-container">
          <div className="notice-banner">
            <span className="notice-symbol">i</span>
            <p>
              <strong>Prototype data notice.</strong> Verify every claim
              against the original source. Notes from the backend are displayed
              only when the API returns them.
            </p>
          </div>

          <section className="welcome-section">
            <div>
              <div className="eyebrow">YOUR ACADEMIC LIBRARY</div>
              <h1>
                From a topic to the
                <br />
                <span>right page.</span>
              </h1>
              <p className="welcome-description">
                Discover library resources, explore relevant material and keep
                your research connected to its sources.
              </p>
            </div>

            <div className="welcome-illustration" aria-hidden="true">
              <div className="illustration-circle circle-one" />
              <div className="illustration-circle circle-two" />
              <div className="book-stack">
                <div className="book book-back" />
                <div className="book book-middle" />
                <div className="book book-front">
                  <span>LIBRARY</span>
                  <div className="book-line" />
                  <div className="book-line short" />
                  <div className="book-emblem">L</div>
                </div>
              </div>
              <div className="floating-note note-one">Source verified</div>
              <div className="floating-note note-two">Study smarter</div>
            </div>
          </section>

          <section className="search-card">
            <div className="search-heading">
              <div>
                <h2>What are you researching?</h2>
                <p>Search by topic, concept, subject or book title.</p>
              </div>
              <span className="search-heading-icon">⌕</span>
            </div>

            <form className="search-form" onSubmit={handleSearch}>
              <span className="search-icon">⌕</span>
              <input
                aria-label="Search library resources"
                placeholder="e.g. database transactions, machine learning..."
                value={query}
                onChange={(event) => setQuery(event.target.value)}
              />

              {query && (
                <button
                  className="clear-button"
                  type="button"
                  onClick={() => setQuery('')}
                  aria-label="Clear search"
                >
                  ×
                </button>
              )}

              <button className="search-button" type="submit">
                Search resources <span>→</span>
              </button>
            </form>

            <div className="suggestions">
              <span>Try:</span>
              {['Database design', 'Algorithms', 'Data science'].map(
                (suggestion) => (
                  <button
                    key={suggestion}
                    type="button"
                    onClick={() => {
                      setQuery(suggestion)
                      setSubmittedQuery(suggestion)
                      setSelectedBook(null)
                      setShowAllBooks(false)
                      setActiveTab('search')
                    }}
                  >
                    {suggestion}
                  </button>
                ),
              )}
            </div>
          </section>

          <div className="section-tabs">
            <button
              className={activeTab === 'search' ? 'tab active-tab' : 'tab'}
              onClick={() => setActiveTab('search')}
            >
              <span>▦</span> Resource discovery
            </button>

            <button
              className={activeTab === 'notes' ? 'tab active-tab' : 'tab'}
              onClick={() => setActiveTab('notes')}
            >
              <span>▤</span> Study notes
              <span className="tab-number">
                {notesResponse?.sections.length ?? 3}
              </span>
            </button>
          </div>

          {activeTab === 'search' ? (
            <section className="results-section">
              <div className="section-heading">
                <div>
                  <h2>
                    {submittedQuery
                      ? `Results for "${submittedQuery}"`
                      : 'Explore library resources'}
                  </h2>
                  <p>
                    {filteredBooks.length} sample{' '}
                    {filteredBooks.length === 1 ? 'resource' : 'resources'}{' '}
                    available in this preview
                  </p>
                </div>
                <span className="sample-label">SAMPLE CATALOGUE DATA</span>
              </div>

              {visibleBooks.length > 0 ? (
                <div className="resource-list">
                  {visibleBooks.map((book) => (
                    <article className="resource-card" key={book.id}>
                      <div className={`resource-cover cover-${book.id}`}>
                        <div className="cover-spine" />
                        <span className="cover-small">
                          {book.category.toUpperCase()}
                        </span>
                        <strong>{book.title}</strong>
                        <span className="cover-bottom">LIBRALINK</span>
                      </div>

                      <div className="resource-details">
                        <div className="resource-topline">
                          <span className="category-tag">{book.category}</span>
                          <span
                            className={`access-tag ${
                              book.access === 'Digital text available'
                                ? 'access-digital'
                                : book.access === 'Physical only'
                                  ? 'access-physical'
                                  : 'access-catalogue'
                            }`}
                          >
                            <span className="access-dot" />
                            {book.access}
                          </span>
                        </div>

                        <h3>{book.title}</h3>
                        <p className="book-author">{book.author}</p>
                        <p className="book-description">{book.description}</p>

                        <div className="resource-meta">
                          <span>▧ {book.year}</span>
                          <span>⌖ {book.location}</span>
                        </div>

                        <div className="resource-actions">
                          <button
                            className="primary-small"
                            onClick={() => setSelectedBook(book)}
                          >
                            View resource <span>→</span>
                          </button>
                          <button
                            className="text-button"
                            onClick={() => exploreNotes(book)}
                          >
                            Explore study notes
                          </button>
                        </div>
                      </div>
                    </article>
                  ))}
                </div>
              ) : (
                <div className="empty-state">
                  <div className="empty-icon">⌕</div>
                  <h3>No matching sample resources</h3>
                  <p>
                    Try a broader topic or clear your search to browse the
                    sample catalogue.
                  </p>
                  <button className="primary-small" onClick={resetSearch}>
                    Show all resources
                  </button>
                </div>
              )}

              {filteredBooks.length > 3 && !showAllBooks && (
                <button
                  className="show-more-button"
                  onClick={() => setShowAllBooks(true)}
                >
                  Show all resources
                </button>
              )}
            </section>
          ) : (
            <section className="notes-section">
              <div className="section-heading">
                <div>
                  <h2>Study notes</h2>
                  <p>
                    Generate notes from accessible source passages when the
                    backend is available.
                  </p>
                </div>
                <span className="sample-label">
                  {notesResponse ? 'API RESPONSE' : 'DEMO CONTENT'}
                </span>
              </div>

              <form
                className="search-form notes-query-form"
                onSubmit={handleGenerateNotes}
              >
                <span className="search-icon">⌕</span>
                <input
                  aria-label="Topic for study notes"
                  placeholder="Enter a topic, e.g. binary search trees"
                  value={notesQuery}
                  maxLength={300}
                  onChange={(event) => setNotesQuery(event.target.value)}
                />
                <button
                  className="search-button"
                  type="submit"
                  disabled={notesLoading}
                >
                  {notesLoading ? 'Generating…' : 'Generate notes'}
                  {!notesLoading && <span>→</span>}
                </button>
              </form>

              {notesLoading && (
                <div className="empty-state" role="status" aria-live="polite">
                  <h3>Preparing your study notes</h3>
                  <p>
                    Searching accessible passages and checking citations.
                    This may take a moment.
                  </p>
                </div>
              )}

              {notesError && (
                <div className="notes-warning" role="alert">
                  <span>!</span>
                  <p>
                    <strong>Unable to retrieve study notes.</strong>{' '}
                    {notesError}
                    <br />
                    The sample notes below are demonstration content, not the
                    answer to your query.
                  </p>
                </div>
              )}

              {notesResponse && !notesResponse.answerable && (
                <div className="notes-warning" role="status">
                  <span>!</span>
                  <p>
                    <strong>
                      {notesResponse.title || 'Study notes unavailable'}
                    </strong>
                    <br />
                    {notesResponse.message ||
                      'There is not enough accessible evidence to answer this question.'}
                    {notesResponse.generated_by === 'gemini' &&
                      ' The AI service may be unavailable.'}
                  </p>
                </div>
              )}

              {notesResponse?.answerable && (
                <>
                  <div className="notice-banner notes-response-banner">
                    <span className="notice-symbol">i</span>
                    <p>
                      <strong>Source-grounded response.</strong> These notes
                      use the passages returned by the backend. Check the
                      cited sources before relying on them.
                    </p>
                  </div>

                  {notesResponse.title && <h3>{notesResponse.title}</h3>}
                  {notesResponse.message && <p>{notesResponse.message}</p>}

                  {notesResponse.sections.length > 0 ? (
                    <div className="notes-list">
                      {notesResponse.sections.map((note, index) => (
                        <article
                          className="note-card"
                          key={`${note.heading}-${index}`}
                        >
                          <div className="note-number">
                            {String(index + 1).padStart(2, '0')}
                          </div>

                          <div className="note-content">
                            <h3>{note.heading}</h3>
                            <p>{note.content}</p>

                            {note.citations.length > 0 && (
                              <div className="citation-list">
                                <strong>Sources</strong>
                                {note.citations.map((chunkId) => {
                                  const source = notesResponse.sources.find(
                                    (item) => item.chunk_id === chunkId,
                                  )

                                  return source ? (
                                    <div key={chunkId}>
                                      {renderSource(source)}
                                    </div>
                                  ) : (
                                    <span
                                      className="citation-chip"
                                      key={chunkId}
                                    >
                                      Citation reference: {chunkId} — source
                                      details unavailable
                                    </span>
                                  )
                                })}
                              </div>
                            )}
                          </div>
                        </article>
                      ))}
                    </div>
                  ) : (
                    <div className="empty-state">
                      <h3>No supported note sections</h3>
                      <p>
                        The API returned no note sections. No answer will be
                        displayed as if it were verified.
                      </p>
                    </div>
                  )}
                </>
              )}

              {!notesLoading && !notesResponse && (
                <>
                  <div className="notes-warning">
                    <span>!</span>
                    <p>
                      <strong>
                        These are not AI-generated or source-verified notes.
                      </strong>{' '}
                      They are placeholders for the prototype. Page references
                      have not been verified.
                    </p>
                  </div>

                  <div className="notes-list">
                    {sampleNotes.map((note, index) => (
                      <article className="note-card" key={note.heading}>
                        <div className="note-number">
                          {String(index + 1).padStart(2, '0')}
                        </div>
                        <div className="note-content">
                          <h3>{note.heading}</h3>
                          <p>{note.text}</p>
                          <div className="citation-chip">
                            <span>▤</span>
                            <span>
                              {note.source} · {note.page}
                            </span>
                            <span className="unverified-label">Unverified</span>
                          </div>
                        </div>
                      </article>
                    ))}
                  </div>
                </>
              )}

              {notesResponse?.limitations &&
                notesResponse.limitations.length > 0 && (
                  <div className="notes-warning">
                    <span>i</span>
                    <div>
                      <strong>Response limitations</strong>
                      <ul>
                        {notesResponse.limitations.map((limitation, index) => (
                          <li key={`${limitation}-${index}`}>{limitation}</li>
                        ))}
                      </ul>
                    </div>
                  </div>
                )}

              {notesResponse?.disclaimer && (
                <p className="notes-disclaimer">
                  {notesResponse.disclaimer}
                </p>
              )}

              {notesResponse?.sources.some((source) => source.is_sample_data) && (
                <p className="notes-disclaimer">
                  This response contains demo source records. Verify the
                  original material before relying on it.
                </p>
              )}

              <button className="print-button" onClick={() => window.print()}>
                Print study notes ↗
              </button>
            </section>
          )}

          {selectedBook && (
            <div
              className="modal-backdrop"
              onClick={() => setSelectedBook(null)}
              role="presentation"
            >
              <section
                className="resource-modal"
                role="dialog"
                aria-modal="true"
                aria-labelledby="modal-title"
                onClick={(event) => event.stopPropagation()}
              >
                <button
                  className="modal-close"
                  aria-label="Close resource details"
                  onClick={() => setSelectedBook(null)}
                >
                  ×
                </button>

                <div className="eyebrow">RESOURCE DETAILS</div>
                <h2 id="modal-title">{selectedBook.title}</h2>
                <p className="modal-author">{selectedBook.author}</p>

                <div className="modal-status">
                  <span
                    className={`access-dot ${
                      selectedBook.access === 'Digital text available'
                        ? 'dot-green'
                        : 'dot-orange'
                    }`}
                  />
                  {selectedBook.access}
                </div>

                <p>{selectedBook.description}</p>

                <div className="modal-info">
                  <div>
                    <small>Category</small>
                    <strong>{selectedBook.category}</strong>
                  </div>
                  <div>
                    <small>Year</small>
                    <strong>{selectedBook.year}</strong>
                  </div>
                  <div>
                    <small>Location</small>
                    <strong>{selectedBook.location}</strong>
                  </div>
                </div>

                {selectedBook.access === 'Physical only' ? (
                  <div className="access-message">
                    <strong>Physical resource</strong>
                    <p>
                      AI has not read this book. A verified shelf or call number
                      is not available in this sample record.
                    </p>
                  </div>
                ) : selectedBook.access === 'Catalogue only' ? (
                  <div className="access-message">
                    <strong>Catalogue record only</strong>
                    <p>No full text is available to the AI in this preview.</p>
                  </div>
                ) : (
                  <div className="access-message">
                    <strong>Text availability is a sample status</strong>
                    <p>
                      This preview does not contain verified source passages,
                      page numbers or an authorized library link.
                    </p>
                  </div>
                )}

                <button
                  className="primary-small modal-done"
                  onClick={() => setSelectedBook(null)}
                >
                  Close details
                </button>
              </section>
            </div>
          )}

          <footer className="page-footer">
            <span>LibraLink · Library research companion</span>
            <span>
              Prototype with sample data · Verify sources before use
            </span>
          </footer>
        </div>
      </main>
    </div>
  )
}

export default App
