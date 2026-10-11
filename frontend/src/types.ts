
export type AccessStatus =
  | 'digital_available'
  | 'digital_full_text'
  | 'full_text_available'
  | 'catalogue_only'
  | 'catalogue-only'
  | 'licensed_link'
  | 'metadata_only'
  | 'physical_only'
  | 'unknown'

export type ApiErrorCode =
  | 'validation_error'
  | 'llm_unavailable'
  | 'not_found'
  | 'rate_limited'
  | 'internal_error'

export interface ApiError {
  error: {
    code: ApiErrorCode
    message: string
  }
}

export interface HealthResponse {
  status: string
}

export interface BookRecord {
  book_id: string
  source_file_id?: string | null
  title: string
  author?: string | null
  edition?: string | null
  filename?: string | null
  format?: string | null
  access_status?: AccessStatus | string | null
  shelf_location?: string | null
  call_number?: string | null
  authorized_url?: string | null
  metadata_notes?: string | null
  ai_can_read_full_text?: boolean
  is_sample_data?: boolean
}

export interface SearchResult {
  chunk_id: string | null
  book_id: string | null
  source_file_id: string | null
  title: string | null
  author: string | null
  edition: string | null
  pdf_page_index: number | null
  page_number?: number | null
  pdf_page_base: number | null
  printed_page_label: string | null
  printed_page_verified: boolean
  section_heading: string | null
  excerpt: string | null
  score: number | null
  access_status: AccessStatus | string | null
  extraction_method: string | null
  corpus_version: string | null
  is_sample_data?: boolean
}

export interface SearchRequest {
  query: string
  top_k?: number
}

export interface SearchResponse {
  query: string
  results: SearchResult[]
  insufficient_evidence: boolean
  message: string | null
}

export interface NotesRequest {
  query: string
  top_k?: number
}

export interface NoteSection {
  heading: string
  content: string
  citations: string[]
  type?: string | null
}

export interface NotesSource {
  chunk_id: string
  book_id: string | null
  source_file_id: string | null
  title: string | null
  author: string | null
  edition: string | null
  pdf_page_index: number | null
  page_number?: number | null
  pdf_page_base: number | null
  printed_page_label: string | null
  printed_page_verified: boolean
  section_heading: string | null
  excerpt: string | null
  access_status: AccessStatus
  extraction_method: string | null
  corpus_version: string | null
  is_sample_data?: boolean
}

export interface NotesResponse {
  query: string
  answerable: boolean
  message: string | null
  title: string | null
  sections: NoteSection[]
  sources: NotesSource[]
  limitations: string[]
  disclaimer: string | null
  generated_by: string | null
}

export interface CheckInRequest {
  student_id: string
  code: string
}

export interface BooksResponse {
  books: BookRecord[]
}
export type DemoCodeResponse = unknown
export type CheckInResponse = unknown
export type TokenBalanceResponse = unknown
export type ExportNotesResponse = Blob

export interface QuizRequest {
  topic: string
  question_count?: number
}

export interface QuizQuestion {
  question_id: string
  question: string
  type: string
  options: string[]
  explanation?: string | null
  source_chunk_id?: string
  source_page?: number | null
}

export interface QuizSource {
  chunk_id: string
  book_id: string | null
  title: string | null
  page_number: number | null
  pdf_page_index: number | null
  extraction_method: string | null
}

export interface QuizResponse {
  quiz_id?: string | null
  topic: string
  answerable: boolean
  questions: QuizQuestion[]
  sources: QuizSource[]
  message: string | null
  generated_by: string | null
}

export interface QuizAnswer {
  question_id: string
  selected_answer: string
}

export interface QuizSubmitRequest {
  quiz_id: string
  answers: QuizAnswer[]
}

export interface QuizResultItem {
  question_id: string
  answered: boolean
  is_correct: boolean
  correct_answer: string
  explanation: string
  source_page?: number | null
}

export interface QuizSubmitResponse {
  success: boolean
  quiz_id: string
  score: number
  total: number
  percentage: number
  correct_count: number
  wrong_count: number
  results: QuizResultItem[]
}

