# Run it with your repos and author information
```
./git-stats.py /path/to/repo1 /path/to/repo2 --author "Your Name"
```

# Exclude specific files or directories
```
./git-stats.py /path/to/repos/* --author "Your Name" --exclude "composer.lock" "^vendor/" "package-lock.json" "^node_modules/"
```

# Only include recent commits
```
./git-stats.py /path/to/repos/* --author "Your Name" --since "1 month ago"
```

# Save chart to a file
```
./git-stats.py /path/to/repos/* --author "Your Name" --output contribution-chart.png
```

# Export statistics to CSV
```
./git-stats.py /path/to/repos/* --author "Your Name" --csv stats.csv
```