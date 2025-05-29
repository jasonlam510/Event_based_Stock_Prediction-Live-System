# Archived Extractor Scripts

## Overview
This directory contains archived content extraction scripts that were previously used in the pipeline. These scripts have been moved to archive as they are no longer actively used in the main codebase. The primary challenge was that Yahoo Finance RSS feed aggregates news from multiple sources, each with their own bot detection mechanisms and security measures. Additionally, we have shifted our strategy to use article titles directly with LLM analysis instead of attempting to extract full descriptions.

## Archived Files

### content_extractor.py
- **Original Location**: `src/pipeline/content_extractor.py`
- **Archived Date**: 2024-03-19
- **Functionality**: 
  - Extracted description from RSS item URLs
  - Used BeautifulSoup for HTML parsing
  - Stored extracted content in database
- **Dependencies**:
  - BeautifulSoup4
  - aiohttp
  - SQLAlchemy
- **Reason for Archive**: Replaced by new approach using article titles directly with LLM analysis. This eliminates the need for complex content extraction and bypassing bot detection mechanisms.

### yf_news_extractor.py
- **Original Location**: `src/pipeline/yf_news_extractor.py`
- **Archived Date**: 2024-03-19
- **Functionality**:
  - Yahoo Finance news article extraction
  - Attempted to extract full article descriptions
  - Custom parsing for various news sources
- **Dependencies**:
  - BeautifulSoup4
  - aiohttp
  - Selenium (for bot detection bypass attempts)
- **Reason for Archive**: Replaced by direct LLM analysis of article titles. This new approach is more efficient and avoids the complexities of content extraction from various news sources.

## Usage History
These extractors were part of the initial pipeline implementation for content extraction from RSS feeds. They have been archived as we have shifted our strategy to use article titles directly with LLM analysis, eliminating the need for complex content extraction and bypassing various news sources' security measures.

## New Approach
- Using article titles directly with LLM analysis
- Benefits:
  - No need to bypass bot detection
  - Faster processing
  - More reliable
  - Simpler architecture
  - Lower resource usage
  - No dependency on external content extraction

## Recovery
If needed, these scripts can be recovered from this archive directory. However, please note that they may not be compatible with the current database schema or pipeline architecture. The current system uses a more efficient approach of direct LLM analysis of article titles.

## Last Updated
2024-03-19 