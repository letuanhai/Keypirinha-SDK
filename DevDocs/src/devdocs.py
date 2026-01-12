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

    def __init__(self):
        super().__init__()
        self._cache_dir = None
        self._docs_list = []
        self._preferred_docs = []
        self._cache_duration = 86400  # 24 hours
        self._max_suggestions = 50
        self._current_doc_index = {}

    def on_start(self):
        """Initialize the plugin"""
        self._cache_dir = self.get_package_cache_path(True)
        self._load_settings()
        self._load_docs_list()

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
                label="DevDocs",
                short_desc="Search documentation on DevDocs.io",
                target="devdocs",
                args_hint=kp.ItemArgsHint.ACCEPTED,
                hit_hint=kp.ItemHitHint.NOARGS)
        ]
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

        # Load preferred docs (comma-separated slugs)
        preferred = settings.get("preferred_docs", "main", fallback="")
        self._preferred_docs = [slug.strip() for slug in preferred.split(",") if slug.strip()]

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

        # Sort docs: preferred first, then by name
        def sort_key(doc):
            is_preferred = doc['slug'] in self._preferred_docs
            return (not is_preferred, doc['name'].lower())

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
            if doc['slug'] in self._preferred_docs:
                short_desc = f"★ {short_desc}"

            suggestions.append(self.create_item(
                category=self.ITEMCAT_DOC,
                label=label,
                short_desc=short_desc,
                target=doc['slug'],
                args_hint=kp.ItemArgsHint.ACCEPTED,
                hit_hint=kp.ItemHitHint.KEEPALL,
                loop_on_suggest=True,
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
