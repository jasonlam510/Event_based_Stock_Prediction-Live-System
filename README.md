# Event-based Stock Prediction

This is the BSCCS Final Year Project 2024-2025 "Event-based Stock Prediction" supervised by [Prof ZHANG, Qingfu](https://scholars.cityu.edu.hk/en/persons/qingfu-zhang(a25373cf-62a1-4697-ad08-43678bcbf3f2).html)

# Architecture Diagram

![Architecture Diagram](doc/Architecture_Diagram.png)


# Pipeline Trigger Logic

```
[RSS Fetcher]
      ↓
[Description Extractor]
      ↓
[LLM Processor]
      ↓                        ↘
[LLM Output Queue]         [Stock Fetcher runs separately on schedule]
      ↓                        ↓
      [Combiner → Local AI Model]

```

# Useful postgre command
```
select count(*) from analysis_results;
select count(*) from extracted_content;
select count(*) from rss_items;
DROP TABLE IF EXISTS analysis_results CASCADE;
DROP TABLE IF EXISTS extracted_content CASCADE;
DROP TABLE IF EXISTS rss_items CASCADE;
```
