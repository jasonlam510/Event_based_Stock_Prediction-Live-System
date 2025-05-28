# Event-based Stock Prediction

This is the BSCCS Final Year Project 2024-2025 "Event-based Stock Prediction" supervised by [Prof ZHANG, Qingfu](https://scholars.cityu.edu.hk/en/persons/qingfu-zhang(a25373cf-62a1-4697-ad08-43678bcbf3f2).html)

# Architecture Diagram

![Architecture Diagram](doc/Architecture_Diagram.png)

# Project Structure

```
src/
├── config.py                # Configuration settings
├── main.py                 # Main application entry point
├── data/
│   ├── base_data.py        # Base data class
│   ├── stock.py           # Stock data handling
│   ├── yf_rss.py          # Yahoo Finance RSS data class
│   └── google_news.py     # Google News data handling
├── llm/
│   ├── gemini_news_analyzer.py  # Renamed from prompt.py
│   └── gemini_client.py        # Gemini API client
├── parsers/
│   ├── base.py            # Base parser interface
│   └── yahoo_finance.py   # Yahoo Finance specific parser
├── extractors/
│   ├── base.py           # Base extractor interface
│   └── yahoo_finance.py  # Yahoo Finance content extractor
└── utils/
    └── logger.py         # Logging utilities
```