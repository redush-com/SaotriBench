# Text Processor

## Problem
Implement a function that processes and normalizes text according to rules.

## Input
- `text`: a string to process
- `options`: optional dict of processing options (may be None)

## Output
- Processed text (string or dict depending on mode)

## Example
```python
process_text("  hello   world  ")  # "hello world"
```

## Notes
- Requirements become stricter in later phases
- New processing rules may be introduced
- Processing rules may interact with each other
