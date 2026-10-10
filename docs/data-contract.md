# LibraLink Data Contract

## 1. BookRecord

Fields:
- id
- title
- author
- edition
- format
- access_status
- shelf_location
- call_number
- authorized_url
- source_file_id
- metadata_notes
- ai_can_read_full_text
- is_sample_data

## 2. SearchResult

Fields:
- chunk_id
- book_id
- source_file_id
- title
- author
- edition
- pdf_page_index
- pdf_page_base
- printed_page_label
- printed_page_verified
- section_heading
- excerpt
- score
- access_status
- extraction_method
- corpus_version

## 3. NotesResponse

Fields:
- query
- answerable
- message
- title
- sections
- sources
- limitations
- disclaimer
- generated_by

## 4. Citation Rules

1. Every citation must reference a retrieved chunk ID.
2. The application resolves chunk IDs against stored records.
3. PDF page indices are zero-based.
4. Printed page labels must never be guessed.
5. Catalogue-only records are not full-text evidence.
6. Physical-only records must not be represented as digitally readable.
7. Unsupported topics must produce an insufficient-evidence response.
8. Sample records must be identified as demo data.