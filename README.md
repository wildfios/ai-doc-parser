# AI-Powered Client Onboarding System

A production-grade Python system that extracts structured information from financial documents using OpenAI's Files and Responses APIs.

## 🎯 Overview

This system processes multiple financial documents (PDF, DOCX, etc.) by uploading them to OpenAI's file storage and using multimodal LLM capabilities to populate a complex client profile schema.

### Key Features

- **Multimodal Extraction**: Uses OpenAI Files API to process documents natively
- **Intelligent Aggregation**: Extracts and merges data from multiple files in a single pass
- **Conflict Resolution**: LLM automatically resolves conflicting information
- **Issue Detection**: Automatically identifies missing fields and flagged items
- **Robustness**: production-ready logging and error handling

## 🏗️ Architecture

```
Documents → OpenAI Files API → Extractor (Responses API) → Validator → Output
                                         ↓                    ↓
                                     Populated Schema      Final JSON
```

### Components

1. **config.py**: Centralized configuration management
2. **document_processor.py**: Uploads files to OpenAI and manages File IDs
3. **extractor.py**: Calls OpenAI Responses API to populate the schema from Files
4. **validator.py**: Validates structure, types, and logical consistency
5. **main.py**: Main orchestrator
6. **utils.py**: Helper utilities

## 🚀 Quick Start

### Installation

```bash
# Install dependencies
pip install -r requirements.txt
```

### Basic Usage

```bash
# Process all documents in input/ directory
python3 main.py --input input/ --output output/results.json 

# Process single document
python3 main.py --input input/1040.pdf --output output/results.json

# Enable debug logging
python3 main.py --input input/ --output output/results.json --debug
```

### Expected Output

The system generates a JSON file containing:

```json
{
  "client_profile": {
    /* populated schema */
  },
  "field_metadata": {
    /* presence/confidence info */
  },
  "issues_for_review": [
    /* list of issues flagged by LLM or Validator */
  ],
  "validation": {
    "is_valid": true,
    "statistics": { ... }
  },
  "processing_info": { ... }
}
```

## 🔧 Configuration

Edit `config.py` to customize:

- **API Settings**: Model selection (e.g., `gpt-4o-mini`), timeout
- **Validation**: Rules and thresholds

### Environment Variables

```bash
# API Key
export OPENAI_API_KEY="your-api-key-here"
```

## 🔐 Security

- **API Key Protection**: Never commit API keys
- **Data Privacy**: Documents are uploaded to OpenAI with 'assistants' purpose. Manage data retention policy via OpenAI dashboard.


