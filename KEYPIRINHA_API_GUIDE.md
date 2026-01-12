# Keypirinha Plugin API - Comprehensive Guide

## Overview

This guide documents the Keypirinha Plugin API based on the official PythonLib source code and real plugin examples.

## Core Enums

### ItemCategory
Defines the type of content an item represents:
- `ERROR` (1): Error/warning message (suggestions only, cannot be in catalog)
- `KEYWORD` (10): Internal command or trigger
- `FILE` (20): File, directory, or executable path
- `CMDLINE` (30): Raw OS command line
- `URL` (40): Web URL or protocol address
- `EXPRESSION` (50): Evaluable expression (math, code)
- `REFERENCE` (60): Plugin-specific identifier
- `USER_BASE` (1000) to `USER_MAX` (0xFFFFFFFE): Custom plugin categories

### ItemArgsHint
Controls how items accept arguments:
- `FORBIDDEN` (0): Item does NOT accept arguments
- `ACCEPTED` (1): Item MAY accept arguments (optional)
- `REQUIRED` (2): Item MUST have arguments

### ItemHitHint
Controls history recording when item is executed:
- `KEEPALL` (0): Record item WITH arguments in history
- `IGNORE` (1): Do NOT record in history at all
- `NOARGS` (2): Record item WITHOUT arguments in history

**CRITICAL FOR NAVIGATION:**
- Use `KEEPALL` when you want the item to stay in the items_chain for multi-level navigation
- Use `IGNORE` for final actions (opening URLs, executing commands)
- Use `NOARGS` when you want to record the base item but not its arguments

## Plugin Lifecycle

### on_start()
Called once when plugin is initialized. Use for:
- Loading configuration
- Initializing cache
- Setting up resources
- One-time heavy operations

### on_catalog()
Called to build the initial catalog. May be called multiple times.
- Use `set_catalog()` to replace entire catalog
- Use `merge_catalog()` to add/update items
- Items in catalog are searchable globally

### on_suggest(user_input, items_chain)
**Most important method for dynamic plugins!**

Called when user types or selects an item.

**Parameters:**
- `user_input` (str): Current text the user has typed
- `items_chain` (list): Stack of selected items from your plugin

**items_chain behavior:**
- **Empty list**: User is at the top level (just typed your keyword)
- **Has items**: User has selected one or more items, now providing arguments or navigating deeper

**Example flow:**
```
1. User types "devdocs"
   → items_chain = []
   → Show list of docsets

2. User selects "python" docset
   → items_chain = [<python docset item>]
   → Show entries within python docset

3. User types "list"
   → items_chain = [<python docset item>]
   → user_input = "list"
   → Filter entries to show only those matching "list"
```

### on_execute(item, action)
Called when user presses Enter on an item (if it doesn't stay in chain).
- `item`: The CatalogItem that was selected
- `action`: Optional CatalogAction if user selected an action (via Tab menu)

## Multi-Level Navigation Pattern

### Pattern 1: Folder-Like Navigation (FileBrowser)

```python
def on_catalog(self):
    catalog = [
        self.create_item(
            category=kp.ItemCategory.KEYWORD,
            label="MyPlugin",
            short_desc="Browse items",
            target="myplugin",
            args_hint=kp.ItemArgsHint.ACCEPTED,
            hit_hint=kp.ItemHitHint.NOARGS)  # Don't keep keyword in chain
    ]
    self.set_catalog(catalog)

def on_suggest(self, user_input, items_chain):
    if not items_chain:
        # Top level - show categories
        suggestions = []
        for category in self.categories:
            suggestions.append(self.create_item(
                category=self.ITEMCAT_CATEGORY,
                label=category['name'],
                short_desc=category['desc'],
                target=category['id'],
                args_hint=kp.ItemArgsHint.ACCEPTED,  # Allow typing to filter
                hit_hint=kp.ItemHitHint.KEEPALL,     # KEEP in chain!
                loop_on_suggest=True))                # Keep suggesting!
        self.set_suggestions(suggestions, kp.Match.ANY, kp.Sort.NONE)

    elif items_chain[-1].category() == self.ITEMCAT_CATEGORY:
        # Second level - show items in category
        category_id = items_chain[-1].target()
        items = self.get_items_for_category(category_id)

        suggestions = []
        for item in items:
            # Filter by user_input
            if user_input and user_input.lower() not in item['name'].lower():
                continue

            suggestions.append(self.create_item(
                category=self.ITEMCAT_ITEM,
                label=item['name'],
                short_desc=item['desc'],
                target=item['url'],
                args_hint=kp.ItemArgsHint.FORBIDDEN,  # No more args
                hit_hint=kp.ItemHitHint.IGNORE))      # Execute and close

        self.set_suggestions(suggestions, kp.Match.ANY, kp.Sort.NONE)

def on_execute(self, item, action):
    if item.category() == self.ITEMCAT_ITEM:
        kpu.shell_execute(item.target())
```

### Pattern 2: Search with Arguments (WebSuggest)

```python
def on_catalog(self):
    catalog = []
    for engine in self.search_engines:
        catalog.append(self.create_item(
            category=self.ITEMCAT_ENGINE,
            label=engine['name'],
            short_desc=f"Search {engine['name']}",
            target=engine['id'],
            args_hint=kp.ItemArgsHint.REQUIRED,  # User MUST type search
            hit_hint=kp.ItemHitHint.NOARGS))     # Don't save the search terms
    self.set_catalog(catalog)

def on_suggest(self, user_input, items_chain):
    if not items_chain:
        return  # User hasn't selected an engine yet

    if items_chain[-1].category() == self.ITEMCAT_ENGINE:
        engine_id = items_chain[-1].target()

        if not user_input or len(user_input) < 2:
            # Not enough input yet
            return

        # Clone the engine item with the search terms
        suggestions = [items_chain[-1].clone()]
        suggestions[0].set_args(user_input, user_input)

        # Add search suggestions from API
        api_suggestions = self.get_search_suggestions(engine_id, user_input)
        for suggestion in api_suggestions:
            item = self.create_item(
                category=self.ITEMCAT_RESULT,
                label=suggestion,
                short_desc=f"Search for: {suggestion}",
                target=f"{engine_id}:{suggestion}",
                args_hint=kp.ItemArgsHint.FORBIDDEN,
                hit_hint=kp.ItemHitHint.IGNORE)
            suggestions.append(item)

        self.set_suggestions(suggestions, kp.Match.ANY, kp.Sort.NONE)

def on_execute(self, item, action):
    if item.category() == self.ITEMCAT_ENGINE:
        search_terms = item.raw_args()
        url = self.build_search_url(item.target(), search_terms)
        kpu.shell_execute(url)
    elif item.category() == self.ITEMCAT_RESULT:
        # Parse target to get engine and terms
        engine_id, terms = item.target().split(':', 1)
        url = self.build_search_url(engine_id, terms)
        kpu.shell_execute(url)
```

## Key Concepts

### loop_on_suggest Parameter

When creating an item with `loop_on_suggest=True`:
- After user selects the item, Keypirinha immediately calls `on_suggest()` again
- The item appears in `items_chain`
- Launcher stays open for continued interaction
- Perfect for navigation/browsing patterns

Without `loop_on_suggest` (default False):
- Item selection doesn't automatically trigger new suggestions
- User must type something to trigger `on_suggest()`

### The items_chain Stack

Think of `items_chain` as a breadcrumb trail:
```
User flow:
1. "devdocs" → items_chain=[]
2. Select "python" → items_chain=[python_item]
3. Select "list class" → items_chain=[python_item, list_item]
```

Always check `items_chain[-1]` to see what the user just selected.

### Match and Sort Methods

When calling `set_suggestions()`:

**Match methods:**
- `kp.Match.ANY`: Accept all items (you've already filtered)
- `kp.Match.FUZZY`: Let Keypirinha do fuzzy matching on labels

**Sort methods:**
- `kp.Sort.NONE`: Keep your order
- `kp.Sort.SCORE_DESC`: Sort by match score
- `kp.Sort.LABEL_ASC`: Alphabetical by label

Most plugins use: `set_suggestions(items, kp.Match.ANY, kp.Sort.NONE)`

## Network Operations

Use `keypirinha_net` module:

```python
import keypirinha_net as kpnet

# Create opener
opener = kpnet.build_urllib_opener()

# Optional: Add headers
opener.addheaders = [('User-Agent', 'MyPlugin/1.0')]

# Make request
try:
    with opener.open(url, timeout=30) as response:
        data = response.read()
        json_data = json.loads(data.decode('utf-8'))
except urllib.error.HTTPError as e:
    self.err(f"HTTP Error: {e.code} {e.reason}")
except urllib.error.URLError as e:
    self.err(f"URL Error: {e.reason}")
except Exception as e:
    self.err(f"Error: {e}")
```

## Configuration

```python
def on_start(self):
    self._load_settings()

def _load_settings(self):
    settings = self.load_settings()

    # Get values with fallbacks
    self.max_items = settings.get_int("max_items", "main", fallback=50)
    self.enable_feature = settings.get_bool("enable_feature", "main", fallback=True)
    self.api_key = settings.get("api_key", "main", fallback="")

    # Multi-line values
    self.preferred_items = settings.get_multiline("preferred_items", "main", fallback=[])

def on_events(self, flags):
    # Reload when config changes
    if flags & kp.Events.PACKCONFIG:
        self._load_settings()
        self.on_catalog()  # Rebuild catalog if needed
```

## Common Pitfalls

### ❌ Wrong: Using NOARGS for navigation
```python
# This WON'T work for multi-level navigation!
hit_hint=kp.ItemHitHint.NOARGS  # Item disappears from chain
```

### ✅ Correct: Using KEEPALL for navigation
```python
# This WILL work for multi-level navigation
hit_hint=kp.ItemHitHint.KEEPALL  # Item stays in chain
loop_on_suggest=True  # Keeps suggesting after selection
```

### ❌ Wrong: Not checking items_chain
```python
def on_suggest(self, user_input, items_chain):
    # This always shows top level, even after selection!
    self._show_top_level()
```

### ✅ Correct: Handling items_chain properly
```python
def on_suggest(self, user_input, items_chain):
    if not items_chain:
        self._show_top_level()
    elif items_chain[-1].category() == self.ITEMCAT_FOLDER:
        self._show_folder_contents(items_chain[-1])
```

### ❌ Wrong: Forgetting loop_on_suggest
```python
# User has to start typing to see next level
self.create_item(...,
    hit_hint=kp.ItemHitHint.KEEPALL)
    # Missing: loop_on_suggest=True
```

### ✅ Correct: Including loop_on_suggest
```python
# Next level appears immediately after selection
self.create_item(...,
    hit_hint=kp.ItemHitHint.KEEPALL,
    loop_on_suggest=True)
```

## Complete Example: Documentation Browser

```python
import keypirinha as kp
import keypirinha_util as kpu
import keypirinha_net as kpnet
import json

class DocBrowser(kp.Plugin):
    ITEMCAT_DOCSET = kp.ItemCategory.USER_BASE + 1
    ITEMCAT_ENTRY = kp.ItemCategory.USER_BASE + 2

    def on_catalog(self):
        catalog = [
            self.create_item(
                category=kp.ItemCategory.KEYWORD,
                label="Docs",
                short_desc="Browse documentation",
                target="docs",
                args_hint=kp.ItemArgsHint.ACCEPTED,
                hit_hint=kp.ItemHitHint.NOARGS)
        ]
        self.set_catalog(catalog)

    def on_suggest(self, user_input, items_chain):
        if not items_chain:
            # Show docsets
            docsets = self._get_docsets()
            suggestions = []
            for docset in docsets:
                if user_input and user_input.lower() not in docset['name'].lower():
                    continue
                suggestions.append(self.create_item(
                    category=self.ITEMCAT_DOCSET,
                    label=docset['name'],
                    short_desc=docset['desc'],
                    target=docset['id'],
                    args_hint=kp.ItemArgsHint.ACCEPTED,
                    hit_hint=kp.ItemHitHint.KEEPALL,
                    loop_on_suggest=True,
                    data_bag=json.dumps(docset)))
            self.set_suggestions(suggestions, kp.Match.ANY, kp.Sort.NONE)

        elif items_chain[-1].category() == self.ITEMCAT_DOCSET:
            # Show entries in docset
            docset_id = items_chain[-1].target()
            entries = self._get_entries(docset_id)

            suggestions = []
            for entry in entries:
                if user_input and user_input.lower() not in entry['name'].lower():
                    continue
                suggestions.append(self.create_item(
                    category=self.ITEMCAT_ENTRY,
                    label=entry['name'],
                    short_desc=entry['type'],
                    target=entry['url'],
                    args_hint=kp.ItemArgsHint.FORBIDDEN,
                    hit_hint=kp.ItemHitHint.IGNORE))
            self.set_suggestions(suggestions, kp.Match.ANY, kp.Sort.NONE)

    def on_execute(self, item, action):
        if item.category() == self.ITEMCAT_ENTRY:
            kpu.shell_execute(item.target())
```

## Summary

**For navigation (folders, categories, docsets):**
- `hit_hint=kp.ItemHitHint.KEEPALL`
- `loop_on_suggest=True`
- `args_hint=kp.ItemArgsHint.ACCEPTED`

**For final actions (URLs, commands):**
- `hit_hint=kp.ItemHitHint.IGNORE`
- `args_hint=kp.ItemArgsHint.FORBIDDEN`

**Always handle items_chain:**
- Check if empty (top level)
- Check category of last item (what level are we at?)
- Filter by user_input at each level
