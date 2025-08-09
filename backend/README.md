# Web Analyzer API

A FastAPI service that analyzes web pages and generates test cases using AI.

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set your OpenAI API key:
```bash
export OPENAI_API_KEY="your-api-key-here"
```

3. Install Playwright browsers:
```bash
playwright install chromium
```

## Running the Service

```bash
python start.py
```

Or directly:
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## API Usage

### Analyze Web Page

**POST** `/api/v1/analyze`

**Request Body:**
```json
{
  "url": "https://example.com",
  "extract_elements": ["forms", "links", "buttons", "inputs"],
  "test_types": ["functional", "validation", "negative", "positive", "error_handling"],
  "chunk_size": 2000
}
```

**Response:**
```json
{
  "url": "https://example.com",
  "test_cases": [...],
  "total_cases": 15,
  "element_counts": {
    "forms": 3,
    "links": 12
  }
}
```

## Configuration Options

- **extract_elements**: Choose from `["forms", "links", "buttons", "inputs"]`
- **test_types**: Choose from `["functional", "validation", "negative", "positive", "error_handling"]`
- **chunk_size**: Size of HTML chunks for analysis (default: 2000)
