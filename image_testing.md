# Image Integration Testing Playbook

## Rules for Test Agent

### Image Handling
- Always use base64-encoded images for all tests and requests
- Accepted formats: JPEG, PNG, WEBP only
- Do NOT use SVG, BMP, HEIC, or other formats
- Do NOT upload blank, solid-color, or uniform-variance images
- Every image must contain real visual features — objects, edges, textures, shadows
- If image is not PNG/JPEG/WEBP, transcode to PNG or JPEG before upload
- After any transformation, re-detect and update the MIME type
- For animated images (GIF, APNG, animated WEBP), extract first frame only
- Resize large images to reasonable bounds (avoid oversized payloads)

## Endpoints to Test

### POST /api/doc-extraction/extract
- Accepts multipart form upload OR JSON with image_base64
- Returns: doc_type (auto-detected), fields dict with confidence scores, overall_confidence
- Test with real passport/document images (transcode scanned PDFs to JPEG first)

### GET /api/doc-extraction/sample-docs
- Returns list of pre-loaded sample documents (no auth needed for demo)

### GET /api/doc-extraction/sample-docs/{id}/extraction
- Returns pre-computed mock extraction for demo (fast, no API call)

## Model
- Provider: openai
- Model: gpt-4o (vision-capable)
- Via Emergent LLM Key (EMERGENT_LLM_KEY)
