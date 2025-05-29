# Archived Files

This directory contains files that have been archived as part of the project's evolution to an event-driven architecture.

## Data Layer (`data/`)

### `yf_rss.py`
- **Original Location**: `src/data/yf_rss.py`
- **Archived Date**: March 2024
- **Reason**: Replaced by event-driven architecture
- **Replacement**: `src/pipeline/rss_fetcher.py`
- **Changes**:
  - Old implementation used a synchronous, batch-based approach
  - New implementation uses an event-driven pipeline with async/await
  - Better error handling and retry mechanisms
  - Improved separation of concerns with dedicated worker classes

## Architecture Changes

The project has moved from a batch-based processing model to an event-driven architecture with the following improvements:

1. **Modular Workers**:
   - Each component is now a dedicated worker class
   - Workers communicate through queues
   - Better error isolation and recovery

2. **Pipeline Components**:
   - `rss_fetcher.py`: Fetches RSS feeds asynchronously
   - `llm_analyzer.py`: Analyzes content using LLM
   - `content_backfill_worker.py`: Handles missed items
   - `orchestrator.py`: Coordinates the pipeline

3. **Benefits**:
   - Improved scalability
   - Better error handling
   - More maintainable codebase
   - Easier to add new features 