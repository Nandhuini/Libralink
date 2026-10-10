
export type AccessStatus =
  | 'digital_available'
  | 'digital_full_text'
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
  id: string
  title: string
  author: string | null
  edition: string | null
  format: string | null
  access_status: AccessStatus
  shelf_location: string | null
  call_number: string | null
  authorized_url: string | null
  source_file_id: string | null
  metadata_notes: string | null
  ai_can_read_full_text: boolean
  is_sample_data: boolean
}

export interface SearchResult {
  chunk_id: string
  book_id: string
  source_file_id: string | null
  title: string
  author: string | null
  edition: string | null
  pdf_page_index: number | null
  pdf_page_base: number | null
  printed_page_label: string | null
  printed_page_verified: boolean
  section_heading: string | null
  excerpt: string | null
  score: number | null
  access_status: AccessStatus
  extraction_method: string | null
  corpus_version: string | null
  is_sample_data?: boolean
}

export interface SearchRequest {
  query: string
  top_k?: number
}

export interface SearchResponse {
  results: SearchResult[]
  message?: string
  answerable?: boolean
}

export interface NotesRequest {
  query: string
  top_k?: number
}

export interface NoteSection {
  heading: string
  content: string
  citations: string[]
}

export interface NotesSource {
  chunk_id: string
  book_id: string
  source_file_id: string | null
  title: string
  author: string | null
  edition: string | null
  pdf_page_index: number | null
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

export type BooksResponse = BookRecord[]
export type DemoCodeResponse = unknown
export type CheckInResponse = unknown
export type TokenBalanceResponse = unknown
export type ExportNotesResponse = unknown
