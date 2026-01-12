# Keypirinha launcher (keypirinha.com)

import keypirinha as kp
import keypirinha_util as kpu
import keypirinha_net as kpnet

import json
import os
import time
import traceback
import urllib.parse
import urllib.error

class DevDocs(kp.Plugin):
    """
    Search and browse documentation from DevDocs.io

    This plugin provides quick access to programming documentation from DevDocs.io.
    You can browse available documentation sets, search within them, and open
    documentation entries directly in your browser.

    Features:
    - Browse all available documentation sets
    - Search documentation by name or alias
    - Search entries within specific documentation sets
    - Cache documentation data for faster access
    - Store preferred documentation sets
    """

    ITEMCAT_MAIN = kp.ItemCategory.USER_BASE + 1
    ITEMCAT_DOC = kp.ItemCategory.USER_BASE + 2
    ITEMCAT_ENTRY = kp.ItemCategory.USER_BASE + 3

    API_BASE_URL = "https://devdocs.io"
    DOCS_LIST_URL = "https://devdocs.io/docs/docs.json"
    ICON_CDN_URL = "https://cdn.jsdelivr.net/gh/freeCodeCamp/devdocs@main/public/icons/docs/{slug}/16@2x.png"

    def __init__(self):
        super().__init__()
        self._cache_dir = None
        self._docs_list = []
        self._favorite_docs = []
        self._cache_duration = 86400  # 24 hours
        self._max_suggestions = 50
        self._current_doc_index = {}
        self._icon_handles = {}  # Cache for loaded icons
        self._default_icon = None
        self._plugin_label = "DevDocs"
        self._catalog_favorites = False

    def on_start(self):
        """Initialize the plugin"""
        self._cache_dir = self.get_package_cache_path(True)
        self._load_settings()
        self._load_docs_list()

        # Load default icon (documentation icon from Windows shell32.dll)
        self._default_icon = self.load_icon(["@shell32.dll,171"])

        # Preload indexes for favorite docsets
        self._preload_favorite_indexes()

        # Set up actions for entries only (not for docsets)
        self.set_actions(self.ITEMCAT_ENTRY, [
            self.create_action(
                name="copy_url",
                label="Copy URL",
                short_desc="Copy the documentation URL to clipboard")])

    def on_catalog(self):
        """Build the initial catalog"""
        catalog = [
            self.create_item(
                category=kp.ItemCategory.KEYWORD,
                label=self._plugin_label,
                short_desc="Search documentation on DevDocs.io",
                target="devdocs",
                args_hint=kp.ItemArgsHint.ACCEPTED,
                hit_hint=kp.ItemHitHint.NOARGS,
                icon_handle=self._default_icon)
        ]

        # Add favorite docsets to main catalog if enabled
        if self._catalog_favorites and self._favorite_docs:
            for doc_slug in self._favorite_docs:
                # Find the doc in the docs list
                doc = self._find_doc_by_slug(doc_slug)
                if not doc:
                    continue

                # Load the doc index
                cache_file = os.path.join(self._cache_dir, f"{doc_slug}_index.json")
                if not os.path.exists(cache_file):
                    continue

                try:
                    with open(cache_file, 'r', encoding='utf-8') as f:
                        doc_index = json.load(f)
                except Exception as e:
                    self.warn(f"Failed to load index for {doc_slug}: {e}")
                    continue

                entries = doc_index.get('entries', [])
                if not entries:
                    continue

                # Get icon for this docset
                docset_icon = self._get_icon_for_docset(doc_slug)

                # Add entries to catalog
                for entry in entries:
                    url = f"{self.API_BASE_URL}/{doc_slug}/{entry['path']}"
                    catalog.append(self.create_item(
                        category=self.ITEMCAT_ENTRY,
                        label=f"{self._plugin_label}-{doc['name']}: {entry['name']}",
                        short_desc=entry.get('type', ''),
                        target=url,
                        args_hint=kp.ItemArgsHint.FORBIDDEN,
                        hit_hint=kp.ItemHitHint.IGNORE,
                        icon_handle=docset_icon,
                        data_bag=json.dumps(entry)))

        self.set_catalog(catalog)

    def on_suggest(self, user_input, items_chain):
        """Provide suggestions based on user input"""
        if not items_chain:
            return

        current_item = items_chain[-1]

        # If we're at the main DevDocs keyword
        if current_item.category() == kp.ItemCategory.KEYWORD:
            self._suggest_docs(user_input)
        # If we've selected a doc, show its entries
        elif current_item.category() == self.ITEMCAT_DOC:
            self._suggest_entries(user_input, current_item)

    def on_execute(self, item, action):
        """Execute the selected item"""
        if item.category() == self.ITEMCAT_ENTRY:
            if action and action.name() == "copy_url":
                # Copy URL to clipboard
                kpu.set_clipboard(item.target())
            else:
                # Open the documentation entry
                kpu.shell_execute(item.target())

    def on_events(self, flags):
        """Handle plugin events"""
        if flags & kp.Events.PACKCONFIG:
            self._load_settings()
            self._load_docs_list()
            self.on_catalog()

    def _load_settings(self):
        """Load plugin settings from config file"""
        settings = self.load_settings()

        # Load cache duration (in hours)
        cache_hours = settings.get_int("cache_duration", "main", fallback=24)
        self._cache_duration = cache_hours * 3600

        # Load max suggestions
        self._max_suggestions = settings.get_int("max_suggestions", "main", fallback=50)

        # Load plugin label
        self._plugin_label = settings.get("plugin_label", "main", fallback="DevDocs")

        # Load favorite docs (comma-separated slugs)
        favorite = settings.get("favorite_docs", "main", fallback="")
        self._favorite_docs = [slug.strip() for slug in favorite.split(",") if slug.strip()]

        # Load catalog_favorites option
        self._catalog_favorites = settings.get_bool("catalog_favorites", "main", fallback=False)

    def _load_docs_list(self):
        """Load the list of available documentation sets"""
        cache_file = os.path.join(self._cache_dir, "docs_list.json")

        # Check if cache exists and is fresh
        if os.path.exists(cache_file):
            file_age = time.time() - os.path.getmtime(cache_file)
            if file_age < self._cache_duration:
                try:
                    with open(cache_file, 'r', encoding='utf-8') as f:
                        self._docs_list = json.load(f)
                    self.dbg(f"Loaded {len(self._docs_list)} docs from cache")
                    return
                except Exception as e:
                    self.warn(f"Failed to load docs cache: {e}")

        # Fetch fresh data
        try:
            self.info("Fetching documentation list from DevDocs...")
            opener = kpnet.build_urllib_opener()
            with opener.open(self.DOCS_LIST_URL, timeout=10) as response:
                data = response.read()
                self._docs_list = json.loads(data.decode('utf-8'))

            # Save to cache
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(self._docs_list, f, ensure_ascii=False, indent=2)

            self.info(f"Loaded {len(self._docs_list)} documentation sets")
        except Exception as e:
            self.err(f"Failed to fetch docs list: {e}")
            self._docs_list = []

    def _suggest_docs(self, user_input):
        """Suggest documentation sets based on user input"""
        if not self._docs_list:
            self.set_suggestions([
                self.create_error_item(
                    label="No documentation sets available",
                    short_desc="Failed to load documentation list from DevDocs")
            ])
            return

        suggestions = []
        search_terms = user_input.lower().split()

        # Sort docs: favorite first, then by name
        def sort_key(doc):
            is_favorite = doc['slug'] in self._favorite_docs
            return (not is_favorite, doc['name'].lower())

        sorted_docs = sorted(self._docs_list, key=sort_key)

        # Filter and create suggestions
        for doc in sorted_docs:
            if len(suggestions) >= self._max_suggestions:
                break

            # Check if doc matches search terms
            if search_terms:
                searchable_text = f"{doc['name']} {doc.get('slug', '')}".lower()
                if doc.get('aliases'):
                    searchable_text += f" {' '.join(doc['aliases'])}"

                if not all(term in searchable_text for term in search_terms):
                    continue

            # Create suggestion item
            label = doc['name']
            if doc.get('version'):
                label += f" {doc['version']}"

            short_desc = f"{doc['type']}"
            if doc['slug'] in self._favorite_docs:
                short_desc = f"★ {short_desc}"

            # Try to load icon for this docset
            icon_handle = self._get_icon_for_docset(doc['slug'])

            suggestions.append(self.create_item(
                category=self.ITEMCAT_DOC,
                label=label,
                short_desc=short_desc,
                target=doc['slug'],
                args_hint=kp.ItemArgsHint.ACCEPTED,
                hit_hint=kp.ItemHitHint.KEEPALL,
                loop_on_suggest=True,
                icon_handle=icon_handle,
                data_bag=json.dumps(doc)))

        if not suggestions and user_input:
            suggestions.append(self.create_error_item(
                label="No matching documentation found",
                short_desc=f"Try a different search term"))

        self.set_suggestions(suggestions, kp.Match.ANY, kp.Sort.NONE)

    def _suggest_entries(self, user_input, doc_item):
        """Suggest entries from a specific documentation set"""
        doc_slug = doc_item.target()

        # Show loading message while fetching
        cache_file = os.path.join(self._cache_dir, f"{doc_slug}_index.json")
        needs_download = not os.path.exists(cache_file)
        if needs_download or (os.path.exists(cache_file) and
                              time.time() - os.path.getmtime(cache_file) >= self._cache_duration):
            # Show loading indicator
            self.set_suggestions([
                self.create_item(
                    category=kp.ItemCategory.REFERENCE,
                    label="Loading documentation index...",
                    short_desc=f"Fetching entries for {doc_slug}",
                    target="loading",
                    args_hint=kp.ItemArgsHint.FORBIDDEN,
                    hit_hint=kp.ItemHitHint.IGNORE)
            ])

        # Load the documentation index
        if not self._load_doc_index(doc_slug):
            self.set_suggestions([
                self.create_error_item(
                    label="Failed to load documentation",
                    short_desc="Could not fetch the documentation index. Check your internet connection.")
            ])
            return

        entries = self._current_doc_index.get('entries', [])

        if not entries:
            self.set_suggestions([
                self.create_error_item(
                    label="No entries found",
                    short_desc="This documentation set appears to be empty")
            ])
            return

        # Get the icon for this docset (will be used for all entries)
        docset_icon = self._get_icon_for_docset(doc_slug)

        suggestions = []
        search_terms = user_input.lower().split() if user_input else []

        # Filter entries
        for entry in entries:
            if len(suggestions) >= self._max_suggestions:
                break

            # Check if entry matches search terms
            if search_terms:
                searchable_text = f"{entry['name']} {entry.get('type', '')}".lower()
                if not all(term in searchable_text for term in search_terms):
                    continue

            # Create suggestion item
            url = f"{self.API_BASE_URL}/{doc_slug}/{entry['path']}"

            suggestions.append(self.create_item(
                category=self.ITEMCAT_ENTRY,
                label=entry['name'],
                short_desc=entry.get('type', ''),
                target=url,
                args_hint=kp.ItemArgsHint.FORBIDDEN,
                hit_hint=kp.ItemHitHint.IGNORE,
                icon_handle=docset_icon,
                data_bag=json.dumps(entry)))

        if not suggestions:
            if user_input:
                suggestions.append(self.create_error_item(
                    label="No matching entries found",
                    short_desc=f"Try a different search term"))
            else:
                # Show first few entries as examples
                for entry in entries[:self._max_suggestions]:
                    url = f"{self.API_BASE_URL}/{doc_slug}/{entry['path']}"
                    suggestions.append(self.create_item(
                        category=self.ITEMCAT_ENTRY,
                        label=entry['name'],
                        short_desc=entry.get('type', ''),
                        target=url,
                        args_hint=kp.ItemArgsHint.FORBIDDEN,
                        hit_hint=kp.ItemHitHint.IGNORE,
                        icon_handle=docset_icon,
                        data_bag=json.dumps(entry)))

        self.set_suggestions(suggestions, kp.Match.ANY, kp.Sort.NONE)

    def _load_doc_index(self, doc_slug):
        """Load the index for a specific documentation set"""
        cache_file = os.path.join(self._cache_dir, f"{doc_slug}_index.json")

        # Check if cache exists and is fresh
        if os.path.exists(cache_file):
            file_age = time.time() - os.path.getmtime(cache_file)
            if file_age < self._cache_duration:
                try:
                    with open(cache_file, 'r', encoding='utf-8') as f:
                        self._current_doc_index = json.load(f)
                    self.dbg(f"Loaded {len(self._current_doc_index.get('entries', []))} entries for {doc_slug} from cache")
                    return True
                except Exception as e:
                    self.warn(f"Failed to load index cache for {doc_slug}: {e}")

        # Fetch fresh data
        try:
            url = f"{self.API_BASE_URL}/docs/{doc_slug}/index.json"
            self.info(f"Fetching index for {doc_slug} from {url}...")

            opener = kpnet.build_urllib_opener()
            opener.addheaders = [('User-Agent', 'Keypirinha-DevDocs-Plugin')]

            with opener.open(url, timeout=30) as response:
                data = response.read()
                self._current_doc_index = json.loads(data.decode('utf-8'))

            # Save to cache
            os.makedirs(self._cache_dir, exist_ok=True)
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(self._current_doc_index, f, ensure_ascii=False, indent=2)

            entries_count = len(self._current_doc_index.get('entries', []))
            self.info(f"Successfully loaded {entries_count} entries for {doc_slug}")
            return True
        except urllib.error.HTTPError as e:
            self.err(f"HTTP Error fetching {doc_slug}: {e.code} {e.reason}")
            self._current_doc_index = {}
            return False
        except urllib.error.URLError as e:
            self.err(f"URL Error fetching {doc_slug}: {e.reason}")
            self._current_doc_index = {}
            return False
        except Exception as e:
            self.err(f"Failed to fetch index for {doc_slug}: {e}")
            self.err(traceback.format_exc())
            self._current_doc_index = {}
            return False

    def _find_doc_by_slug(self, slug):
        """Find a documentation set by its slug"""
        for doc in self._docs_list:
            if doc['slug'] == slug:
                return doc
        return None

    def _preload_favorite_indexes(self):
        """Preload indexes for favorite documentation sets"""
        if not self._favorite_docs:
            return

        for doc_slug in self._favorite_docs:
            # Check if already cached
            cache_file = os.path.join(self._cache_dir, f"{doc_slug}_index.json")
            if os.path.exists(cache_file):
                file_age = time.time() - os.path.getmtime(cache_file)
                if file_age < self._cache_duration:
                    self.dbg(f"Index for {doc_slug} already cached")
                    continue

            # Check if we should terminate before downloading
            if self.should_terminate(0):
                self.dbg("Terminating - skipping favorite index preload")
                return

            # Download the index
            self.info(f"Preloading index for favorite docset: {doc_slug}")
            try:
                url = f"{self.API_BASE_URL}/docs/{doc_slug}/index.json"
                opener = kpnet.build_urllib_opener()
                opener.addheaders = [('User-Agent', 'Keypirinha-DevDocs-Plugin')]

                with opener.open(url, timeout=30) as response:
                    data = response.read()
                    doc_index = json.loads(data.decode('utf-8'))

                # Check again after download
                if self.should_terminate(0):
                    self.dbg("Terminating during favorite index download")
                    return

                # Save to cache
                os.makedirs(self._cache_dir, exist_ok=True)
                with open(cache_file, 'w', encoding='utf-8') as f:
                    json.dump(doc_index, f, ensure_ascii=False, indent=2)

                self.info(f"Preloaded {len(doc_index.get('entries', []))} entries for {doc_slug}")

            except Exception as e:
                self.warn(f"Failed to preload index for {doc_slug}: {e}")

    def _get_icon_for_docset(self, doc_slug):
        """Load or download icon for a documentation set"""
        # Check if already loaded
        if doc_slug in self._icon_handles:
            return self._icon_handles[doc_slug]

        # Extract base slug (remove version part after ~)
        base_slug = doc_slug.split('~')[0]

        # Icon cache file path
        icons_dir = os.path.join(self._cache_dir, "icons")
        os.makedirs(icons_dir, exist_ok=True)
        icon_file = os.path.join(icons_dir, f"{base_slug}.png")

        # Try to load from cache first
        if os.path.exists(icon_file):
            try:
                icon_handle = self.load_icon([f"cache://{self.package_full_name()}/icons/{base_slug}.png"])
                if icon_handle:
                    self._icon_handles[doc_slug] = icon_handle
                    return icon_handle
            except Exception as e:
                self.dbg(f"Failed to load cached icon for {doc_slug}: {e}")

        # Check if we should terminate before downloading
        if self.should_terminate(0):
            self.dbg(f"Skipping icon download for {doc_slug} - terminating")
            return None

        # Download icon
        try:
            url = self.ICON_CDN_URL.format(slug=base_slug)
            self.dbg(f"Downloading icon for {doc_slug} from {url}")

            opener = kpnet.build_urllib_opener()
            with opener.open(url, timeout=5) as response:
                icon_data = response.read()

            # Check again after download
            if self.should_terminate(0):
                self.dbg(f"Terminating during icon download for {doc_slug}")
                return None

            # Save to cache
            with open(icon_file, 'wb') as f:
                f.write(icon_data)

            # Load the icon
            icon_handle = self.load_icon([f"cache://{self.package_full_name()}/icons/{base_slug}.png"])
            if icon_handle:
                self._icon_handles[doc_slug] = icon_handle
                self.dbg(f"Successfully loaded icon for {doc_slug}")
                return icon_handle

        except Exception as e:
            self.dbg(f"Failed to download icon for {doc_slug}: {e}")

        # Return None if icon loading failed (will use default)
        return None
