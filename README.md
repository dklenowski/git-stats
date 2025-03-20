# Git Stats

A tool for analyzing git contribution statistics across multiple repositories.

## Features

- Analyze contributions by a specific author across multiple git repositories
- Filter by date range
- Exclude specific file patterns
- Ignore specific commits (useful for large moves/renames that skew statistics)
- Generate visualization charts
- Export data to CSV

## Installation

### Requirements
- Python 3.6 or higher
- Git

### Install Dependencies
Install the required Python packages using pip:

```bash
pip install matplotlib numpy pyyaml
```

## Configuration

The program uses a YAML configuration file (default: `git-stats-config.yaml`).

### Setup Configuration
1. Copy the example configuration file:
```bash
cp git-stats-config.yaml.example git-stats-config.yaml
```

2. Edit the configuration file with your information

### Configuration Options

- `root_dir`: Root directory to recursively search for git repositories (alternative to listing repos)
- `repos`: List of specific repository paths to analyze
- `author`: Author name or email to filter commits by
- `exclude_patterns`: Regex patterns for files to exclude
- `ignore_commits`: List of commit hashes to exclude from statistics
- `since`: Only consider commits more recent than this date (e.g., "2023-01-01" or "1 month ago")
- `output_file`: Path to save the chart image
- `csv_file`: Path to export statistics as CSV

## Usage

### Using the configuration file

```bash
./git-stats.py
```

### Specify a different configuration file

```bash
./git-stats.py --config my-config.yaml
```

### Command-line Arguments

All configuration options can be overridden via command-line arguments:

```bash
./git-stats.py --author "Your Name" --output chart.png --csv stats.csv
```

### Available Arguments

- `--config`: Path to YAML configuration file
- `--author`: Author name/email to filter commits
- `--exclude`: Patterns for files to exclude
- `--since`: Only consider commits more recent than this date
- `--output`: Save chart to specified file
- `--csv`: Export statistics to CSV file
- `--ignore-commits`: List of commit hashes to ignore
- `--root-dir`: Root directory to search for git repositories

### Specify repositories directly

```bash
./git-stats.py /path/to/repo1 /path/to/repo2
```

## Output

The script produces:
1. Terminal output with statistics for each repository
2. A visualization chart saved to the specified output file
3. A CSV file with detailed statistics (if configured)