import type {
  ApiError,
  BooksResponse,
  CheckInRequest,
  CheckInResponse,
  DemoCodeResponse,
  ExportNotesResponse,
  HealthResponse,
  NotesRequest,
  NotesResponse,
  SearchRequest,
  SearchResponse,
  TokenBalanceResponse,
  QuizRequest,
  QuizResponse,
  QuizSubmitRequest,
  QuizSubmitResponse,
} from './types'

const API_BASE = (
  import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8000'
).replace(/\/+$/, '')

export class ApiClientError extends Error {
  readonly kind: 'network' | 'timeout' | 'http' | 'response'
  readonly status?: number

  constructor(
    message: string,
    kind: 'network' | 'timeout' | 'http' | 'response',
    status?: number,
  ) {
    super(message)
    this.name = 'ApiClientError'
    this.kind = kind
    this.status = status
  }
}

// Common function for backend requests
async function request<T>(
  path: string,
  options: RequestInit = {},
  responseType: 'json' | 'blob' = 'json',
  timeoutMs = 15000,
): Promise<T> {
  const controller = new AbortController()
  const timeout = window.setTimeout(() => controller.abort(), timeoutMs)
  const relayAbort = () => controller.abort()
  options.signal?.addEventListener('abort', relayAbort, { once: true })

  try {
    let response: Response
    try {
      response = await fetch(`${API_BASE}${path}`, {
        ...options,
        signal: controller.signal,
        headers: {
          ...(options.body
            ? { 'Content-Type': 'application/json' }
            : {}),
          ...options.headers,
        },
      })
    } catch (error) {
      if (error instanceof DOMException && error.name === 'AbortError') {
        throw new ApiClientError(
          'The request timed out. Check the backend and try again.',
          'timeout',
        )
      }
      throw new ApiClientError(
        'Cannot reach the LibraLink backend. Check that it is running and that the API URL is correct.',
        'network',
      )
    }

    if (responseType === 'blob' && response.ok) {
      try {
        return await response.blob() as T
      } catch (error) {
        if (error instanceof DOMException && error.name === 'AbortError') {
          throw new ApiClientError(
            'The request timed out while reading the backend response.',
            'timeout',
          )
        }
        throw new ApiClientError(
          'The backend response could not be read.',
          'response',
          response.status,
        )
      }
    }

    let data: unknown
    try {
      data = await response.json()
    } catch (error) {
      if (error instanceof DOMException && error.name === 'AbortError') {
        throw new ApiClientError(
          'The request timed out while reading the backend response.',
          'timeout',
        )
      }
      throw new ApiClientError(
        'The backend returned an invalid or empty JSON response.',
        'response',
        response.status,
      )
    }

    if (!response.ok) {
      const payload = data && typeof data === 'object'
        ? data as Record<string, unknown>
        : {}
      const errorEnvelope = payload.error && typeof payload.error === 'object'
        ? payload.error as ApiError['error']
        : undefined
      const envelopeMessage = errorEnvelope?.message
      const detail = payload.detail
      const message =
        envelopeMessage ||
        (typeof detail === 'string'
          ? detail
          : response.status === 422
            ? 'The request was rejected. Check the required fields and values.'
            : `The backend returned HTTP ${response.status}.`)

      throw new ApiClientError(message, 'http', response.status)
    }

    return data as T
  } finally {
    window.clearTimeout(timeout)
    options.signal?.removeEventListener('abort', relayAbort)
  }
}

// Validate search and notes query
function validateQuery(query: string): string {
  const normalizedQuery = query.trim()

  if (normalizedQuery.length < 1 || normalizedQuery.length > 300) {
    throw new Error('Query must contain between 1 and 300 characters.')
  }

  return normalizedQuery
}

// Validate search result count
function validateTopK(topK?: number): number {
  const value = topK ?? 5

  if (!Number.isInteger(value) || value < 1 || value > 10) {
    throw new Error('top_k must be an integer between 1 and 10.')
  }

  return value
}

// GET /health
export function getHealth(): Promise<HealthResponse> {
  return request<HealthResponse>('/health')
}

// GET /api/books
export function getBooks(): Promise<BooksResponse> {
  return request<BooksResponse>('/api/books')
}

// POST /api/search
export function searchBooks(
  input: SearchRequest,
): Promise<SearchResponse> {
  const query = validateQuery(input.query)
  const top_k = validateTopK(input.top_k)

  return request<SearchResponse>('/api/search', {
    method: 'POST',
    body: JSON.stringify({ query, top_k }),
  })
}

// POST /api/notes
export function getStudyNotes(
  input: NotesRequest,
): Promise<NotesResponse> {
  const query = validateQuery(input.query)
  const top_k = validateTopK(input.top_k)

  return request<NotesResponse>('/api/notes', {
    method: 'POST',
    body: JSON.stringify({ query, top_k }),
  })
}

// GET /api/tokens/demo-code
export function getDemoCode(): Promise<DemoCodeResponse> {
  return request<DemoCodeResponse>('/api/tokens/demo-code')
}

// POST /api/tokens/check-in
export function checkIn(
  input: CheckInRequest,
): Promise<CheckInResponse> {
  if (!input.student_id.trim() || !input.code.trim()) {
    throw new Error('Student ID and check-in code are required.')
  }

  return request<CheckInResponse>('/api/tokens/check-in', {
    method: 'POST',
    body: JSON.stringify(input),
  })
}

// GET /api/tokens/{student_id}
export function getTokenBalance(
  studentId: string,
): Promise<TokenBalanceResponse> {
  if (!studentId.trim()) {
    throw new Error('Student ID is required.')
  }

  return request<TokenBalanceResponse>(
    `/api/tokens/${encodeURIComponent(studentId)}`,
  )
}

// POST /api/export/notes
export function exportNotes(
  notes: NotesResponse,
): Promise<ExportNotesResponse> {
  return request<ExportNotesResponse>(
    '/api/export/notes',
    {
      method: 'POST',
      body: JSON.stringify({ notes }),
    },
    'blob',
  )
}

// Validate quiz topic
function validateQuizTopic(topic: string): string {
  const normalizedTopic = topic.trim()

  if (normalizedTopic.length < 1 || normalizedTopic.length > 300) {
    throw new Error(
      'Quiz topic must contain between 1 and 300 characters.',
    )
  }

  return normalizedTopic
}

// POST /api/quiz
export function generateQuiz(
  input: QuizRequest,
): Promise<QuizResponse> {
  const topic = validateQuizTopic(input.topic)
  const question_count = input.question_count ?? 5

  if (
    !Number.isInteger(question_count) ||
    question_count < 1 ||
    question_count > 10
  ) {
    throw new Error(
      'Question count must be an integer between 1 and 10.',
    )
  }

  return request<QuizResponse>('/api/quiz', {
    method: 'POST',
    body: JSON.stringify({ topic, question_count }),
  }, 'json', 105000)
}

// POST /api/quiz/submit
export function submitQuiz(
  input: QuizSubmitRequest,
): Promise<QuizSubmitResponse> {
  return request<QuizSubmitResponse>('/api/quiz/submit', {
    method: 'POST',
    body: JSON.stringify(input),
  })
}
