import { useEffect, useState } from 'react'
import {
	generateQuiz,
	getBooks,
	getStudyNotes,
	searchBooks,
	submitQuiz,
} from './api'
import type {
	BookRecord,
	NotesResponse,
	QuizResponse,
	SearchResponse,
	QuizSubmitResponse,
} from './types'

type View = 'resources' | 'notes' | 'quiz'

const viewLabels: Record<View, string> = {
	resources: 'Resource Discovery',
	notes: 'Study Notes',
	quiz: 'Practice Quiz',
}

function errorText(error: unknown): string {
	return error instanceof Error
		? error.message
		: 'The request could not be completed.'
}

function pageLabel(book: BookRecord): string {
	const status = (book.access_status ?? '').toLowerCase()
	if (status.includes('full_text') || status.includes('digital')) {
		return 'Full text available'
	}
	if (status.includes('physical')) return 'Physical collection'
	return 'Catalogue record'
}

function pageNumber(page: number | null | undefined): string {
	return page == null ? 'Page not listed' : `Page ${page}`
}

function App() {
	const [activeView, setActiveView] = useState<View>('resources')
	const [books, setBooks] = useState<BookRecord[]>([])
	const [booksLoading, setBooksLoading] = useState(true)
	const [booksError, setBooksError] = useState('')
	const [resourceQuery, setResourceQuery] = useState('')
	const [selectedBook, setSelectedBook] = useState<BookRecord | null>(null)
	const [searchResults, setSearchResults] = useState<SearchResponse | null>(null)
	const [searchLoading, setSearchLoading] = useState(false)
	const [searchError, setSearchError] = useState('')

	const [notesQuery, setNotesQuery] = useState('')
	const [notes, setNotes] = useState<NotesResponse | null>(null)
	const [notesLoading, setNotesLoading] = useState(false)
	const [notesError, setNotesError] = useState('')

	const [quizTopic, setQuizTopic] = useState('')
	const [questionCount, setQuestionCount] = useState(5)
	const [quiz, setQuiz] = useState<QuizResponse | null>(null)
	const [answers, setAnswers] = useState<Record<string, string>>({})
	const [quizResults, setQuizResults] = useState<QuizSubmitResponse | null>(null)
	const [quizLoading, setQuizLoading] = useState(false)
	const [quizSubmitting, setQuizSubmitting] = useState(false)
	const [quizError, setQuizError] = useState('')

	useEffect(() => {
		let current = true
		getBooks()
			.then((response) => {
				if (current) setBooks(Array.isArray(response.books) ? response.books : [])
			})
			.catch((error: unknown) => {
				if (current) setBooksError(errorText(error))
			})
			.finally(() => {
				if (current) setBooksLoading(false)
			})
		return () => {
			current = false
		}
	}, [])

	const visibleBooks = books.filter((book) => {
		const query = resourceQuery.trim().toLocaleLowerCase()
		if (!query) return true
		return [book.title, book.author, book.edition, book.filename]
			.some((value) => value?.toLocaleLowerCase().includes(query))
	})

	async function handleResourceSearch(event: React.FormEvent<HTMLFormElement>) {
		event.preventDefault()
		setSearchResults(null)
		setSearchError('')
		if (!resourceQuery.trim()) return
		setSearchLoading(true)
		try {
			setSearchResults(await searchBooks({ query: resourceQuery }))
		} catch (error) {
			setSearchError(errorText(error))
		} finally {
			setSearchLoading(false)
		}
	}

	async function handleNotes(event: React.FormEvent<HTMLFormElement>) {
		event.preventDefault()
		setNotes(null)
		setNotesError('')
		setNotesLoading(true)
		try {
			setNotes(await getStudyNotes({ query: notesQuery }))
		} catch (error) {
			setNotesError(errorText(error))
		} finally {
			setNotesLoading(false)
		}
	}

	async function requestQuiz() {
		if (quizLoading || quizSubmitting) return
		setQuiz(null)
		setAnswers({})
		setQuizResults(null)
		setQuizError('')
		setQuizLoading(true)
		try {
			setQuiz(await generateQuiz({ topic: quizTopic, question_count: questionCount }))
		} catch (error) {
			setQuizError(errorText(error))
		} finally {
			setQuizLoading(false)
		}
	}

	async function handleGenerateQuiz(event: React.FormEvent<HTMLFormElement>) {
		event.preventDefault()
		await requestQuiz()
	}

	async function handleSubmitQuiz() {
		if (!quiz?.quiz_id || !quiz.questions.length || quizSubmitting || quizResults) return
		setQuizError('')
		setQuizSubmitting(true)
		try {
			const result = await submitQuiz({
				quiz_id: quiz.quiz_id,
				answers: quiz.questions
					.filter((question) => answers[question.question_id] !== undefined)
					.map((question) => ({
						question_id: question.question_id,
						selected_answer: answers[question.question_id],
					})),
			})
			setQuizResults(result)
		} catch (error) {
			setQuizError(errorText(error))
		} finally {
			setQuizSubmitting(false)
		}
	}

	const answeredCount = quiz?.questions.filter(
		(question) => answers[question.question_id] !== undefined,
	).length ?? 0
	const quizSourceById = new Map((quiz?.sources ?? []).map((source) => [source.chunk_id, source]))
	const resultsById = new Map((quizResults?.results ?? []).map((result) => [result.question_id, result]))

	return (
		<div className="app-shell">
			<aside className="sidebar">
				<a className="brand" href="#home" onClick={(event) => event.preventDefault()}>
					<span className="brand-icon">L</span>
					<span><strong>LibraLink</strong><small>Library study workspace</small></span>
				</a>
				<div className="sidebar-label">WORKSPACE</div>
				<nav aria-label="Main navigation">
					{(['resources', 'notes', 'quiz'] as const).map((view) => (
						<button
							className={`nav-item${activeView === view ? ' active' : ''}`}
							key={view}
							onClick={() => setActiveView(view)}
							type="button"
						>
							<span className="nav-icon" aria-hidden="true">{view === 'resources' ? 'B' : view === 'notes' ? 'N' : 'Q'}</span>
							{viewLabels[view]}
						</button>
					))}
				</nav>
				<div className="sidebar-divider" />
				<div className="library-link"><span aria-hidden="true">+</span> Library catalogue</div>
				<div className="sidebar-bottom">
					<div className="help-card">
						<span className="help-icon">i</span>
						<strong>Source-grounded study</strong>
						<p>Notes and practice questions are based on passages available to LibraLink.</p>
					</div>
					<div className="profile">
						<span className="avatar">S</span>
						<span><strong>Student workspace</strong><small>Local session</small></span>
					</div>
				</div>
			</aside>

			<main className="main-content">
				<header className="topbar">
					<div className="breadcrumb">Workspace <span>/</span> {viewLabels[activeView]}</div>
					<div className="prototype-pill"><span className="status-dot" /> Library study tools</div>
				</header>
				<div className="page-container">
					<div className="notice-banner">
						<span className="notice-symbol">i</span>
						<p>Study responses use retrieved library passages. Check the cited source for context and important details.</p>
					</div>

					<section className="welcome-section">
						<div>
							<div className="eyebrow">LIBRARY LEARNING, CONNECTED</div>
							<h1>Make your next<br /><span>study session count.</span></h1>
							<p className="welcome-description">Find resources, build source-linked notes, and check your understanding with practice questions.</p>
						</div>
						<div className="welcome-illustration" aria-hidden="true">
							<div className="illustration-circle circle-one" />
							<div className="illustration-circle circle-two" />
							<div className="book-stack">
								<div className="book book-back" />
								<div className="book book-middle" />
								<div className="book book-front">
									<span className="cover-small">LIBRARY STUDY</span>
									<div className="book-emblem">L</div>
									<div className="book-line" /><div className="book-line short" />
								</div>
							</div>
							<div className="floating-note note-one">Source linked</div>
							<div className="floating-note note-two">Keep learning</div>
						</div>
					</section>

					<nav className="section-tabs" aria-label="Study workspace views">
						{(['resources', 'notes', 'quiz'] as const).map((view) => (
							<button
								className={`tab${activeView === view ? ' active-tab' : ''}`}
								key={view}
								onClick={() => setActiveView(view)}
								type="button"
								aria-current={activeView === view ? 'page' : undefined}
							>
								<span aria-hidden="true">{view === 'resources' ? 'B' : view === 'notes' ? 'N' : 'Q'}</span>
								{viewLabels[view]}
								{view === 'resources' && <span className="tab-number">{books.length}</span>}
							</button>
						))}
					</nav>

					{activeView === 'resources' && (
						<>
							<section className="search-card">
								<div className="search-heading">
									<div><h2>Discover library resources</h2><p>Browse the available catalogue and narrow by title, author, or edition.</p></div>
									<span className="search-heading-icon" aria-hidden="true">⌕</span>
								</div>
								<form className="search-form" onSubmit={handleResourceSearch}>
									<span className="search-icon" aria-hidden="true">⌕</span>
									<input aria-label="Search catalogue" value={resourceQuery} onChange={(event) => setResourceQuery(event.target.value)} placeholder="Search books, topics, or authors..." />
									  {resourceQuery && <button className="clear-button" type="button" aria-label="Clear search" onClick={() => { setResourceQuery(''); setSearchResults(null); setSearchError('') }}>×</button>}
									  <button className="search-button" type="submit" disabled={searchLoading}>{searchLoading ? 'Searching...' : 'Search'} <span>→</span></button>
								</form>
								<div className="suggestions"><span>Explore:</span>{['statistics', 'data structures', 'machine learning'].map((term) => <button key={term} type="button" onClick={() => setResourceQuery(term)}>{term}</button>)}</div>
							</section>

							<section className="results-section">
								<div className="section-heading">
									<div><h2>Available resources</h2><p>{booksLoading ? 'Loading the library catalogue...' : `${visibleBooks.length} of ${books.length} catalogue records`}</p></div>
									<span className="sample-label">LIBRARY CATALOGUE</span>
								</div>
								{booksError && <div className="notes-warning" role="alert"><span>!</span><p>{booksError}</p></div>}
								{searchError && <div className="notes-warning" role="alert"><span>!</span><p>{searchError}</p></div>}
								{searchLoading && <div className="empty-state" role="status"><p>Searching indexed book passages...</p></div>}
								{searchResults && <section className="passage-results" aria-label="Passage search results">
									<div className="section-heading"><div><h2>Matching passages</h2><p>{searchResults.insufficient_evidence ? 'No sufficiently relevant passages found.' : `${searchResults.results.length} source passages for “${searchResults.query}”`}</p></div></div>
									{searchResults.message && <p className="book-description">{searchResults.message}</p>}
									{searchResults.results.map((result) => <article className="note-card" key={result.chunk_id || `${result.book_id}-${result.pdf_page_index}`}><span className="note-number" aria-hidden="true">↗</span><div className="note-content"><h3>{result.title || 'Library passage'}</h3><p className="book-author">{result.author || 'Author not listed'}{result.page_number != null ? ` · Page ${result.page_number}` : result.printed_page_label ? ` · Printed label ${result.printed_page_label}${result.printed_page_verified ? '' : ' (unverified)'}` : result.pdf_page_index != null ? ` · PDF page ${result.pdf_page_index + (result.pdf_page_base ?? 0)}` : ' · Page not listed'}</p><p>{result.excerpt || 'No excerpt is available for this passage.'}</p></div></article>)}
								</section>}
								{booksLoading ? <div className="empty-state"><p>Loading catalogue records...</p></div> : visibleBooks.length ? (
									<div className="resource-list">
										{visibleBooks.map((book, index) => {
											const accessClass = pageLabel(book) === 'Full text available' ? 'access-digital' : pageLabel(book) === 'Physical collection' ? 'access-physical' : 'access-catalogue'
											return (
												<article className="resource-card" key={book.book_id}>
													<div className={`resource-cover cover-${index % 3 + 1}`}><span className="cover-spine" /><span className="cover-small">LIBRARY RESOURCE</span><strong>{book.title}</strong><span className="cover-bottom">LIBRALINK</span></div>
													<div className="resource-details">
														<div className="resource-topline"><span className="category-tag">{book.format || book.edition || 'Catalogue record'}</span><span className={`access-tag ${accessClass}`}><span className="access-dot" />{pageLabel(book)}</span></div>
														<h3>{book.title}</h3>
														<p className="book-author">{book.author || 'Author not listed'}{book.edition ? ` · ${book.edition}` : ''}</p>
														{book.metadata_notes && <p className="book-description">{book.metadata_notes}</p>}
														<div className="resource-meta">{book.filename && <span>{book.filename}</span>}{book.call_number && <span>Call no. {book.call_number}</span>}{book.shelf_location && <span>{book.shelf_location}</span>}</div>
														<div className="resource-actions"><button className="primary-small" type="button" onClick={() => setSelectedBook(book)}>Resource details <span>→</span></button>{book.authorized_url && <a className="text-button" href={book.authorized_url} target="_blank" rel="noreferrer">Open access link</a>}</div>
													</div>
												</article>
											)
										})}
									</div>
								) : (
									  <div className="empty-state"><div className="empty-icon">⌕</div><h3>No matching catalogue records</h3><p>Try another title, author, or edition, or clear the search to browse the catalogue.</p><button className="show-more-button" type="button" onClick={() => setResourceQuery('')}>Clear search</button></div>
								)}
							</section>
						</>
					)}

					{activeView === 'notes' && (
						<section className="notes-section">
							<div className="section-heading"><div><h2>Study Notes</h2><p>Build a source-linked response from retrieved passages.</p></div></div>
							<section className="search-card">
								<form className="search-form" onSubmit={handleNotes}>
									<span className="search-icon" aria-hidden="true">⌕</span>
									<input aria-label="Study notes question" value={notesQuery} onChange={(event) => setNotesQuery(event.target.value)} placeholder="What would you like to study?" required maxLength={300} />
									<button className="search-button" type="submit" disabled={notesLoading}>{notesLoading ? 'Building notes...' : 'Generate notes'} <span>→</span></button>
								</form>
							</section>
							{notesError && <div className="notes-warning" role="alert"><span>!</span><p>{notesError}</p></div>}
							{notesLoading && <div className="empty-state" role="status"><p>Searching the indexed passages...</p></div>}
							{notes && !notes.answerable && <div className="empty-state" role="status"><div className="empty-icon">i</div><h3>No supported passages found</h3><p>{notes.message || 'The indexed collection did not provide enough evidence for this question.'}</p></div>}
							{notes?.answerable && (
								<div className="notes-list">
									{notes.title && <div className="section-heading"><h2>{notes.title}</h2></div>}
									{notes.message && <p className="book-description">{notes.message}</p>}
									{notes.sections.map((section, index) => (
										<article className="note-card" key={`${section.heading}-${index}`}>
											<span className="note-number">{String(index + 1).padStart(2, '0')}</span>
											<div className="note-content"><h3>{section.heading || 'Study note'}</h3><p>{section.content}</p>
												{(section.citations ?? []).map((citationId) => {
													const source = notes.sources.find((item) => item.chunk_id === citationId)
													return <div className="citation-chip" key={citationId}><span aria-hidden="true">↗</span><strong>{source?.title || 'Cited passage'}</strong><span>{source?.page_number != null ? pageNumber(source.page_number) : source?.printed_page_label ? `Printed label ${source.printed_page_label}${source.printed_page_verified ? '' : ' (unverified)'}` : source?.pdf_page_index != null ? `PDF page ${source.pdf_page_index + (source.pdf_page_base ?? 0)}` : 'Page not listed'}</span>{source?.excerpt && <span>{source.excerpt}</span>}</div>
												})}
											</div>
										</article>
									))}
									{notes.limitations?.length > 0 && <div className="notes-warning"><span>!</span><div>{notes.limitations.map((limitation) => <p key={limitation}>{limitation}</p>)}</div></div>}
									{notes.disclaimer && <p className="page-footer">{notes.disclaimer}</p>}
								</div>
							)}
						</section>
					)}

					{activeView === 'quiz' && (
						<section className="notes-section">
							<div className="section-heading"><div><h2>Practice Quiz</h2><p>Generate multiple-choice questions grounded in retrieved textbook passages.</p></div></div>
							<section className="search-card">
								<form className="search-form" onSubmit={handleGenerateQuiz}>
									<span className="search-icon" aria-hidden="true">Q</span>
									<input aria-label="Quiz topic" value={quizTopic} onChange={(event) => setQuizTopic(event.target.value)} placeholder="Enter a topic to practice..." required maxLength={300} />
									<label className="quiz-count-label">Questions<select aria-label="Question count" value={questionCount} onChange={(event) => setQuestionCount(Number(event.target.value))}><option value={3}>3</option><option value={5}>5</option><option value={10}>10</option></select></label>
									<button className="search-button" type="submit" disabled={quizLoading}>{quizLoading ? 'Generating...' : 'New quiz'} <span>→</span></button>
								</form>
							</section>
							{quizError && <div className="notes-warning" role="alert"><span>!</span><div><p>{quizError}</p><button className="text-button" type="button" onClick={() => void requestQuiz()} disabled={quizLoading}>Retry request</button></div></div>}
							{quizLoading && <div className="empty-state" role="status"><p>Retrieving passages and preparing questions...</p></div>}
							{quiz && !quiz.answerable && <div className="empty-state" role="status"><div className="empty-icon">i</div><h3>Quiz is unavailable</h3><p>{quiz.message || 'There is not enough source evidence to create a quiz.'}</p><button className="show-more-button" type="button" onClick={() => void requestQuiz()} disabled={quizLoading}>Retry generation</button></div>}
							{quiz?.answerable && quiz.questions.length > 0 && (
								<div className="quiz-content">
									{quiz.generated_by && <p className="book-description">Generated by {quiz.generated_by}. Answers stay hidden until submission.</p>}
									{quiz.questions.map((question, index) => {
										const result = resultsById.get(question.question_id)
										const source = question.source_chunk_id ? quizSourceById.get(question.source_chunk_id) : undefined
										return (
											<article className="note-card quiz-question" key={question.question_id}>
												<span className="note-number">{String(index + 1).padStart(2, '0')}</span>
												<div className="note-content"><h3>{question.question}</h3>
													<div className="quiz-options">{question.options.map((option) => <label className="quiz-option" key={option}><input type="radio" name={question.question_id} value={option} checked={answers[question.question_id] === option} disabled={!!quizResults} onChange={() => setAnswers((current) => ({ ...current, [question.question_id]: option }))} /><span>{option}</span></label>)}</div>
													{source && <div className="citation-chip"><span aria-hidden="true">↗</span><strong>{source.title || 'Source passage'}</strong><span>{pageNumber(question.source_page ?? source.page_number)}</span></div>}
													{result && <div className={`quiz-feedback ${result.is_correct ? 'correct' : 'incorrect'}`}><strong>{result.is_correct ? 'Correct' : result.answered ? 'Not quite' : 'Not answered'}</strong><p>Correct answer: {result.correct_answer}</p><p>{result.explanation}</p>{result.source_page != null && <small>{pageNumber(result.source_page)}</small>}</div>}
												</div>
											</article>
										)
									})}
									{!quizResults ? <div className="quiz-submit-row"><span>{answeredCount} of {quiz.questions.length} answered</span><button className="search-button" type="button" onClick={handleSubmitQuiz} disabled={quizSubmitting || answeredCount !== quiz.questions.length}>{quizSubmitting ? 'Submitting...' : 'Submit answers'} <span>→</span></button></div> : <div className="quiz-score"><strong>{quizResults.score} / {quizResults.total}</strong><span>{quizResults.percentage}% · {quizResults.correct_count} correct · {quizResults.wrong_count} incorrect</span></div>}
								</div>
							)}
							{quiz?.answerable && quiz.questions.length === 0 && <div className="empty-state"><h3>No valid questions returned</h3><p>{quiz.message || 'The retrieved evidence did not support valid questions.'}</p></div>}
						</section>
					)}

					<footer className="page-footer"><span>LibraLink · Library learning workspace</span><span>Use cited sources to verify important information.</span></footer>
				</div>
			</main>

			{selectedBook && <div className="modal-backdrop" role="presentation" onClick={() => setSelectedBook(null)}><section className="resource-modal" role="dialog" aria-modal="true" aria-labelledby="resource-modal-title" onClick={(event) => event.stopPropagation()}><button className="modal-close" type="button" aria-label="Close details" onClick={() => setSelectedBook(null)}>×</button><h2 id="resource-modal-title">{selectedBook.title}</h2><p className="modal-author">{selectedBook.author || 'Author not listed'}{selectedBook.edition ? ` · ${selectedBook.edition}` : ''}</p><div className="modal-status"><span className="access-dot dot-green" />{pageLabel(selectedBook)}</div><div className="modal-info"><div><small>Catalogue ID</small><strong>{selectedBook.book_id}</strong></div><div><small>Source file</small><strong>{selectedBook.filename || selectedBook.source_file_id || 'Not listed'}</strong></div><div><small>Call number</small><strong>{selectedBook.call_number || 'Not listed'}</strong></div><div><small>Location</small><strong>{selectedBook.shelf_location || 'Not listed'}</strong></div></div>{selectedBook.metadata_notes && <div className="access-message"><strong>Catalogue notes</strong><p>{selectedBook.metadata_notes}</p></div>}{selectedBook.authorized_url && <a className="primary-small modal-done" href={selectedBook.authorized_url} target="_blank" rel="noreferrer">Open authorized resource</a>}<button className="print-button modal-done" type="button" onClick={() => setSelectedBook(null)}>Done</button></section></div>}
		</div>
	)
}

export default App
