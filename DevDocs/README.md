# Keypirinha Plugin: DevDocs

A [Keypirinha](http://keypirinha.com) plugin for searching and browsing documentation from [DevDocs.io](https://devdocs.io/).

![DevDocs Plugin Demo](screenshot.png)

## Description

DevDocs is a powerful documentation browser that aggregates documentation for hundreds of programming languages, frameworks, and libraries. This Keypirinha plugin brings DevDocs' extensive documentation collection right into your Keypirinha launcher, allowing you to quickly search and access documentation without leaving your keyboard.

### Features

- **Browse Documentation Sets**: Access over 500+ documentation sets including Python, JavaScript, React, Go, Rust, and many more
- **Fast Search**: Quickly search for documentation by name or alias
- **Entry Search**: Search within specific documentation sets for functions, classes, methods, and more
- **Smart Caching**: Automatically caches documentation lists and indexes for faster access
- **Preferred Docs**: Configure your frequently-used documentation sets to appear first
- **Direct Browser Access**: Opens documentation entries directly in your default browser
- **Lightweight**: Minimal resource usage with efficient caching

## Installation

### Manual Installation

1. Download the latest `DevDocs.keypirinha-package` file from the [releases page](../../releases)
2. Copy the file to one of the following locations:
   - **Portable mode**: `Keypirinha\portable\Profile\InstalledPackages`
   - **Installed mode**: `%APPDATA%\Keypirinha\InstalledPackages`
     (typically `C:\Users\%USERNAME%\AppData\Roaming\Keypirinha\InstalledPackages`)
3. Restart Keypirinha or reload the catalog (Ctrl+F5)

### From Source

1. Clone or download this repository
2. Copy the `DevDocs` folder to `%APPDATA%\Keypirinha\InstalledPackages\DevDocs`
3. Restart Keypirinha or reload the catalog (Ctrl+F5)

## Usage

### Basic Usage

1. Launch Keypirinha (default: `Alt+Space`)
2. Type `devdocs` to activate the plugin
3. Browse available documentation sets or start typing to search
4. Select a documentation set to view its contents
5. Search within the documentation or browse entries
6. Press `Enter` to open the documentation in your browser

### Search Examples

**Browse all documentation:**
```
devdocs
```

**Search for Python documentation:**
```
devdocs python
```

**Search for JavaScript (using alias):**
```
devdocs js
```

**Search for React entries:**
```
devdocs react > hooks
```

### Actions

When viewing documentation sets:
- **Enter**: Browse entries in the documentation
- **Alt+Home**: Open the documentation homepage in browser

When viewing entries:
- **Enter**: Open the entry in your browser
- **Ctrl+C**: Copy the documentation URL to clipboard

## Configuration

You can customize the plugin by editing the configuration file:

1. Open Keypirinha
2. Type `Keypirinha: Configure Package` and select `DevDocs`
3. Edit the settings in the `[main]` section

### Available Settings

```ini
[main]
# Cache duration in hours (default: 24)
# How long to keep cached documentation lists and indexes before refreshing
cache_duration = 24

# Maximum number of suggestions to show (default: 50)
# Limits the number of results displayed in the suggestion list
max_suggestions = 50

# Preferred documentation sets (comma-separated slugs)
# These will appear first in the documentation list
# Example: preferred_docs = python~3.12, javascript, react
preferred_docs =
```

### Setting Preferred Docs

To find documentation slugs for your preferred docs:

1. Launch DevDocs plugin (`devdocs`)
2. Search for the documentation you want
3. The slug is shown in the details (e.g., `python~3.12`, `javascript`, `react`)
4. Add them to the `preferred_docs` setting:

```ini
preferred_docs = python~3.12, javascript, react, go, rust
```

Preferred documentation sets will be marked with a ★ and appear at the top of the list.

## Cache Management

The plugin caches documentation data in Keypirinha's cache directory to improve performance:

- **Documentation List**: Cached for 24 hours (configurable)
- **Documentation Indexes**: Cached for 24 hours (configurable)
- **Location**: `%APPDATA%\Keypirinha\Cache\DevDocs\`

To clear the cache:
1. Close Keypirinha
2. Delete the cache folder: `%APPDATA%\Keypirinha\Cache\DevDocs\`
3. Restart Keypirinha

## Supported Documentation

DevDocs supports 500+ documentation sets across various categories:

- **Languages**: Python, JavaScript, TypeScript, Go, Rust, Ruby, PHP, Java, C++, C#, and many more
- **Web Frameworks**: React, Vue, Angular, Django, Flask, Express, Rails, Laravel
- **Libraries**: jQuery, Lodash, NumPy, Pandas, TensorFlow
- **Databases**: PostgreSQL, MySQL, MongoDB, Redis
- **Tools**: Git, Docker, Kubernetes, Ansible
- **And much more!**

For a complete list, visit [DevDocs.io](https://devdocs.io/).

## Development

### Building from Source

Requirements:
- Keypirinha SDK
- Python 3.x (included in SDK)

Build steps:
```bash
cd DevDocs
# On Windows:
make.cmd

# On Linux (for development):
python ../tools/lib/kpsdk/zipfile.py -c DevDocs.keypirinha-package src/
```

### Project Structure

```
DevDocs/
├── src/
│   ├── devdocs.py       # Main plugin code
│   └── devdocs.ini      # Configuration file
├── README.md            # This file
├── LICENSE              # MIT License
└── make.cmd             # Build script (Windows)
```

## API Reference

The plugin uses the DevDocs public API:

- **Documentation List**: `https://devdocs.io/docs/docs.json`
- **Documentation Index**: `https://devdocs.io/docs/{slug}/index.json`
- **Documentation URL**: `https://devdocs.io/{slug}/{path}`

## Troubleshooting

### Plugin doesn't appear in Keypirinha

- Ensure the plugin is installed in the correct directory
- Try reloading the catalog (Ctrl+F5)
- Check Keypirinha's console for errors (F2)

### Documentation list is empty

- Check your internet connection
- Clear the cache and try again
- Check Keypirinha's console for API errors (F2)

### Entries not loading

- The documentation index may be large; give it a moment to download
- Check the cache directory for any corrupted files
- Try clearing the cache and reloading

### Slow performance

- Reduce `max_suggestions` in the configuration
- Increase `cache_duration` to cache data longer
- Ensure your cache directory is on a fast drive

## Change Log

### v1.0.0 (2026-01-12)

- Initial release
- Browse and search 500+ documentation sets
- Search within documentation entries
- Smart caching system
- Preferred documentation configuration
- Multiple actions (open in browser, copy URL, open homepage)

## Credits

This plugin is inspired by the [Raycast DevDocs Extension](https://github.com/raycast/extensions/tree/main/extensions/devdocs) and uses the [DevDocs.io](https://devdocs.io/) API.

## License

This package is distributed under the terms of the MIT license.

## Contribute

Contributions are welcome! Here's how you can help:

1. Check for open issues or open a fresh issue to start a discussion around a feature idea or a bug
2. Fork this repository on GitHub to start making your changes
3. Send a pull request
4. Add yourself to the *Contributors* section below!

### Contributors

- Your Name Here - Creator and maintainer

## Support

If you encounter any issues or have suggestions:

1. Check the [Issues](../../issues) page
2. Create a new issue with a detailed description
3. Include Keypirinha's console output (F2) if reporting a bug

## Links

- [Keypirinha](http://keypirinha.com) - The launcher this plugin is built for
- [DevDocs.io](https://devdocs.io/) - The documentation service this plugin uses
- [Keypirinha SDK](https://github.com/Keypirinha/SDK) - Official SDK documentation
- [Keypirinha API](http://keypirinha.com/api.html) - Plugin API reference
