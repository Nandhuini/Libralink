
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
} from './types'

// Backend URL can be configured through frontend/.env.local.
// Local development default: http://localhost:8000
const API_BASE = (
  import.meta.env.VITE_API_BASE || 'http://localhost:8000'
).replace(/\/+$/, '')

// Common function for sending requests to the backend.
async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  let response: Response

  try {
    response = await fetch(`${API_BASE}${path}`, {
      ...options,
      headers: {
        ...(options.body
          ? { 'Content-Type': 'application/json' }
          : {}),
        ...options.headers,
      },
    })
  } catch {
    throw new Error(
      'Cannot connect to the LibraLink backend. Check whether the server is running.',
    )
  }

  const data: unknown = await response.json().catch(() => null)

  if (!response.ok) {
    const apiError = data as ApiError | null

    throw new Error(
      apiError?.error?.message ||
        `Request failed with status ${response.status}.`,
    )
  }

  return data as T
}

// Validate query length according to the API contract.
function validateQuery(query: string): string {
  const normalizedQuery = query.trim()

  if (normalizedQuery.length < 1 || normalizedQuery.length > 300) {
    throw new Error('Query must contain between 1 and 300 characters.')
  }

  return normalizedQuery
}

// Validate top_k according to the API contract.
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
  notes: unknown,
): Promise<ExportNotesResponse> {
  return request<ExportNotesResponse>('/api/export/notes', {
    method: 'POST',
    body: JSON.stringify(notes),
  })
}
