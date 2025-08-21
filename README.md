# S3 Object Search Tool

![Tests](https://github.com/avanrossum/search_s3/actions/workflows/tests.yml/badge.svg)
![Python Version](https://img.shields.io/badge/python-3.11+-blue.svg)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)

A powerful Python script for searching S3 objects across multiple buckets with flexible filtering and output options.

## Features

- Search for objects containing specific terms in their keys
- Support for regex patterns in all search and filter operations
- Filter buckets by inclusion/exclusion patterns
- Multiple output formats (table, stacked, raw, CSV)
- Streaming output for immediate results
- Human-readable file sizes
- Cross-platform compatibility

## Requirements

- Python 3.6+
- AWS credentials configured (via AWS CLI, environment variables, or IAM roles)
- Required permissions: `s3:ListBucket`, `s3:ListObjectsV2`

## Installation

1. Ensure you have AWS credentials configured:
   ```bash
   aws configure
   ```

2. Download the script:
   ```bash
   # Clone the repository
   git clone https://github.com/avanrossum/search_s3.git
   cd search_s3
   chmod +x search_s3.py
   
   # Or download directly
   # wget https://raw.githubusercontent.com/avanrossum/search_s3/main/search_s3.py
   # chmod +x search_s3.py
   ```

## Basic Usage

### Required Arguments

The search term is required and can be provided as a positional argument or flag. By default, it performs literal substring matching:

```bash
# Positional argument
./search_s3.py "search-term"

# Flag format
./search_s3.py --term "search-term"
./search_s3.py -t "search-term"
```

### Regex Support

Enable regex pattern matching for more powerful searches:

```bash
# Case-sensitive regex
./search_s3.py --regex -t "config\.(json|yaml|yml)$"

# Case-insensitive regex
./search_s3.py --regex-ignore-case -t "backup.*202[34]"

# Regex with bucket filtering
./search_s3.py --regex -t "\.log$" -b "prod.*"
```

### Optional Bucket Filtering

Filter buckets by inclusion pattern:

```bash
# Search only buckets containing "gridpane"
./search_s3.py "foobar" "gridpane"

# Using flags
./search_s3.py --term "foobar" --bucket "gridpane"
./search_s3.py -t "foobar" -b "gridpane"
```

## Advanced Filtering

### Regex Patterns

The script supports three modes of pattern matching:

1. **Literal mode (default)**: Simple substring matching
2. **Regex mode (`--regex`)**: Case-sensitive regex patterns
3. **Regex ignore-case mode (`--regex-ignore-case`)**: Case-insensitive regex patterns

#### Common Regex Examples

```bash
# Find files with specific extensions
./search_s3.py --regex -t "\.(log|txt|csv)$"

# Find files from specific date ranges
./search_s3.py --regex -t "202[34]-[01][0-9]-[0-3][0-9]"

# Find files in specific directories
./search_s3.py --regex -t "^config/.*\.json$"

# Case-insensitive search
./search_s3.py --regex-ignore-case -t "backup.*\.(zip|tar|gz)$"

# Complex patterns
./search_s3.py --regex -t "(prod|staging)/.*\.(log|error)$"
```

### Exclusion Filters

Exclude objects or buckets containing specific terms:

```bash
# Exclude objects with "backup" in the key
./search_s3.py -t "config" -te "backup"

# Exclude buckets with "archive" in the name
./search_s3.py -t "data" -be "archive"

# Combine inclusion and exclusion
./search_s3.py -t "foobar" -b "gridpane" -te "temp" -be "archive"

# Regex exclusions
./search_s3.py --regex -t "\.log$" -te "\.(tmp|temp)$" -be "archive.*"
```

### Multiple Exclusions

You can use multiple exclusion filters:

```bash
# Exclude multiple terms from object keys
./search_s3.py -t "config" -te "backup" -te "temp" -te "cache"

# Exclude multiple bucket patterns
./search_s3.py -t "data" -be "archive" -be "old" -be "deprecated"

# Regex exclusions
./search_s3.py --regex -t "\.log$" -te "\.(tmp|temp)$" -be "archive.*"
```

## Output Formats

### 1. Table Format (Default)

Clean, aligned table output with no truncation:

```bash
./search_s3.py "foobar"
```

Example output:
```
Bucket                                                    Key                                    Size       Modified              Class
gridpane-backups-58s48ra6-d31e-4ffe-6326-6421ad5ca95b   snapshots/foobar-com/10481      550B       2025-06-20T00:00:10+00:00 STANDARD
gridpane-backups-58s48ra6-d31e-4ffe-6326-6421ad5ca95b   snapshots/foobar-com/11231      550B       2025-07-20T00:00:10+00:00 STANDARD
```

### 2. Stacked Format

One object per section with clear separation:

```bash
./search_s3.py "foobar" --stacked
```

Example output:
```
=== Object 1 ===
Bucket:     gridpane-backups-58s48ra6-531e-4ffe-1233-6421ad5ca95b
Key:        snapshots/foobar-com/10481
Size:       550B
Modified:   2025-06-20T00:00:10+00:00
Class:      STANDARD

=== Object 2 ===
Bucket:     gridpane-backups-58s48ra6-531e-4ffe-1233-6421ad5ca95b
Key:        snapshots/foobar-com/11231
Size:       550B
Modified:   2025-07-20T00:00:10+00:00
Class:      STANDARD
```

### 3. Raw Format

Tab-separated output for easy copy-paste:

```bash
./search_s3.py "foobar" --raw
```

Example output:
```
Bucket	Key	Size	LastModified	StorageClass
gridpane-backups-58s48ra6-g31e-4ffe-7895-6421ad5ca95b	snapshots/foobar-com/10481	550B	2025-06-20T00:00:10+00:00	STANDARD
```

### 4. CSV Format

Comma-separated values for spreadsheet import:

```bash
# Output to terminal
./search_s3.py "foobar" --csv

# Save to file
./search_s3.py "foobar" --csv --csv-file results.csv
```

Example output:
```csv
Bucket,Key,Size,LastModified,StorageClass
gridpane-backups-58s48ra6-a31e-4ffe-1548-6421ad5ca95b,snapshots/foobar-com/10481,550B,2025-06-20T00:00:10+00:00,STANDARD
```

## Performance Characteristics

- **Table format**: Collects all results first for proper column sizing
- **Stacked format**: Streams results as they're found
- **Raw format**: Streams results as they're found
- **CSV format**: Streams results as they're found

## Real-World Examples

### Find Configuration Files

```bash
# Find all config files but exclude backups and temp files
./search_s3.py -t "config" -te "backup" -te "temp" --stacked

# Find config files using regex (more precise)
./search_s3.py --regex -t "config\.(json|yaml|yml|conf)$" -te "\.(bak|tmp)$" --stacked
```

### Search Specific Project

```bash
# Search for project files in specific bucket pattern
./search_s3.py -t "myproject" -b "production" -be "archive" --csv --csv-file project_files.csv
```

### Backup Analysis

```bash
# Find all backup files from last month
./search_s3.py -t "backup" -b "gridpane" -te "old" --raw
```

### Data Migration Planning

```bash
# Find all data files for migration planning
./search_s3.py -t "data" -be "archive" -be "deprecated" --csv --csv-file migration_data.csv

# Find specific data file types using regex
./search_s3.py --regex -t "\.(csv|json|parquet)$" -be "archive.*" --csv --csv-file data_files.csv
```

## Command Line Options

| Option | Short | Description |
|--------|-------|-------------|
| `--term` | `-t` | Search term or regex pattern (case-sensitive) |
| `--bucket` | `-b` | Include buckets matching this term or regex |
| `--term-excluding` | `-te` | Exclude objects with keys matching this term or regex |
| `--bucket-excluding` | `-be` | Exclude buckets matching this term or regex |
| `--regex` | | Treat all patterns as regex (case-sensitive) |
| `--regex-ignore-case` | | Treat all patterns as regex (case-insensitive) |
| `--raw` | | Output tab-separated data |
| `--stacked` | | Output in stacked format |
| `--csv` | | Output in CSV format |
| `--csv-file` | | Specify CSV output file |

## Error Handling

- Missing search term: Shows error message with usage instructions
- No results found: Displays "No results found." message
- AWS errors: Standard AWS SDK error messages
- File write errors: Clear error messages for CSV file operations

## Tips and Best Practices

1. **Use bucket filtering** to improve performance when searching large numbers of buckets
2. **Combine inclusion and exclusion** filters for precise results
3. **Use stacked format** for detailed inspection of individual objects
4. **Use CSV format** for data analysis and reporting
5. **Use raw format** for quick copy-paste operations
6. **Streaming formats** (stacked, raw, CSV) provide immediate feedback for long searches

## Troubleshooting

### Common Issues

1. **No results found**: Check your search term and bucket filters
2. **Permission denied**: Ensure AWS credentials have S3 list permissions
3. **CSV file not created**: Check write permissions in the target directory
4. **Slow performance**: Use bucket filtering to reduce search scope

### Debug Mode

For troubleshooting, you can add verbose output by modifying the script to include debug prints.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contributing

[Add contribution guidelines here]
