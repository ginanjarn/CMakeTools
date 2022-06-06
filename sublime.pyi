import io
from typing import Any, Optional

class _LogWriter(io.TextIOBase):
    buf: Any = ...
    def __init__(self) -> None: ...
    def flush(self) -> None: ...
    def write(self, s: Any) -> None: ...

HOVER_TEXT: int
HOVER_GUTTER: int
HOVER_MARGIN: int
ENCODED_POSITION: int
TRANSIENT: int
FORCE_GROUP: int
SEMI_TRANSIENT: int
ADD_TO_SELECTION: int
REPLACE_MRU: int
CLEAR_TO_RIGHT: int
IGNORECASE: int
LITERAL: int
MONOSPACE_FONT: int
KEEP_OPEN_ON_FOCUS_LOST: int
WANT_EVENT: int
HTML: int
COOPERATE_WITH_AUTO_COMPLETE: int
HIDE_ON_MOUSE_MOVE: int
HIDE_ON_MOUSE_MOVE_AWAY: int
KEEP_ON_SELECTION_MODIFIED: int
HIDE_ON_CHARACTER_EVENT: int
DRAW_EMPTY: int
HIDE_ON_MINIMAP: int
DRAW_EMPTY_AS_OVERWRITE: int
PERSISTENT: int
DRAW_OUTLINED: int
DRAW_NO_FILL: int
DRAW_NO_OUTLINE: int
DRAW_SOLID_UNDERLINE: int
DRAW_STIPPLED_UNDERLINE: int
DRAW_SQUIGGLY_UNDERLINE: int
NO_UNDO: int
HIDDEN: int
OP_EQUAL: int
OP_NOT_EQUAL: int
OP_REGEX_MATCH: int
OP_NOT_REGEX_MATCH: int
OP_REGEX_CONTAINS: int
OP_NOT_REGEX_CONTAINS: int
CLASS_WORD_START: int
CLASS_WORD_END: int
CLASS_PUNCTUATION_START: int
CLASS_PUNCTUATION_END: int
CLASS_SUB_WORD_START: int
CLASS_SUB_WORD_END: int
CLASS_LINE_START: int
CLASS_LINE_END: int
CLASS_EMPTY_LINE: int
INHIBIT_WORD_COMPLETIONS: int
INHIBIT_EXPLICIT_COMPLETIONS: int
DYNAMIC_COMPLETIONS: int
INHIBIT_REORDER: int
DIALOG_CANCEL: int
DIALOG_YES: int
DIALOG_NO: int
UI_ELEMENT_SIDE_BAR: int
UI_ELEMENT_MINIMAP: int
UI_ELEMENT_TABS: int
UI_ELEMENT_STATUS_BAR: int
UI_ELEMENT_MENU: int
UI_ELEMENT_OPEN_FILES: int
LAYOUT_INLINE: int
LAYOUT_BELOW: int
LAYOUT_BLOCK: int
KIND_ID_AMBIGUOUS: int
KIND_ID_KEYWORD: int
KIND_ID_TYPE: int
KIND_ID_FUNCTION: int
KIND_ID_NAMESPACE: int
KIND_ID_NAVIGATION: int
KIND_ID_MARKUP: int
KIND_ID_VARIABLE: int
KIND_ID_SNIPPET: int
KIND_ID_COLOR_REDISH: int
KIND_ID_COLOR_ORANGISH: int
KIND_ID_COLOR_YELLOWISH: int
KIND_ID_COLOR_GREENISH: int
KIND_ID_COLOR_CYANISH: int
KIND_ID_COLOR_BLUISH: int
KIND_ID_COLOR_PURPLISH: int
KIND_ID_COLOR_PINKISH: int
KIND_ID_COLOR_DARK: int
KIND_ID_COLOR_LIGHT: int
KIND_AMBIGUOUS: Any
KIND_KEYWORD: Any
KIND_TYPE: Any
KIND_FUNCTION: Any
KIND_NAMESPACE: Any
KIND_NAVIGATION: Any
KIND_MARKUP: Any
KIND_VARIABLE: Any
KIND_SNIPPET: Any
SYMBOL_SOURCE_ANY: int
SYMBOL_SOURCE_INDEX: int
SYMBOL_SOURCE_OPEN_FILES: int
SYMBOL_TYPE_ANY: int
SYMBOL_TYPE_DEFINITION: int
SYMBOL_TYPE_REFERENCE: int
COMPLETION_FORMAT_TEXT: int
COMPLETION_FORMAT_SNIPPET: int
COMPLETION_FORMAT_COMMAND: int
COMPLETION_FLAG_KEEP_PREFIX: int

def version(): ...
def platform(): ...
def arch(): ...
def channel(): ...
def executable_path(): ...
def executable_hash(): ...
def packages_path(): ...
def installed_packages_path(): ...
def cache_path(): ...
def status_message(msg: Any) -> None: ...
def error_message(msg: Any) -> None: ...
def message_dialog(msg: Any) -> None: ...
def ok_cancel_dialog(msg: Any, ok_title: str = ..., title: str = ...): ...
def yes_no_cancel_dialog(msg: Any, yes_title: str = ..., no_title: str = ..., title: str = ...): ...
def open_dialog(callback: Any, file_types: Any = ..., directory: Optional[Any] = ..., multi_select: bool = ..., allow_folders: bool = ...): ...
def save_dialog(callback: Any, file_types: Any = ..., directory: Optional[Any] = ..., name: Optional[Any] = ..., extension: Optional[Any] = ...) -> None: ...
def select_folder_dialog(callback: Any, directory: Optional[Any] = ..., multi_select: bool = ...): ...
def run_command(cmd: Any, args: Optional[Any] = ...) -> None: ...
def format_command(cmd: Any, args: Optional[Any] = ...): ...
def html_format_command(cmd: Any, args: Optional[Any] = ...): ...
def command_url(cmd: Any, args: Optional[Any] = ...): ...
def get_clipboard_async(callback: Any, size_limit: int = ...) -> None: ...
def get_clipboard(size_limit: int = ...): ...
def set_clipboard(text: Any): ...
def log_commands(flag: Optional[Any] = ...) -> None: ...
def get_log_commands(): ...
def log_input(flag: Optional[Any] = ...) -> None: ...
def get_log_input(): ...
def log_fps(flag: Optional[Any] = ...) -> None: ...
def get_log_fps(): ...
def log_result_regex(flag: Optional[Any] = ...) -> None: ...
def get_log_result_regex(): ...
def log_indexing(flag: Optional[Any] = ...) -> None: ...
def get_log_indexing(): ...
def log_build_systems(flag: Optional[Any] = ...) -> None: ...
def get_log_build_systems(): ...
def log_control_tree(flag: Optional[Any] = ...) -> None: ...
def get_log_control_tree(): ...
def ui_info(): ...
def score_selector(scope_name: Any, selector: Any): ...
def load_resource(name: Any): ...
def load_binary_resource(name: Any): ...
def find_resources(pattern: Any): ...
def encode_value(val: Any, pretty: bool = ...): ...
def decode_value(data: Any): ...
def expand_variables(val: Any, variables: Any): ...
def load_settings(base_name: Any): ...
def save_settings(base_name: Any) -> None: ...
def set_timeout(f: Any, timeout_ms: int = ...) -> None: ...
def set_timeout_async(f: Any, timeout_ms: int = ...) -> None: ...
def active_window(): ...
def windows(): ...
def get_macro(): ...

class Window:
    window_id: Any = ...
    settings_object: Any = ...
    template_settings_object: Any = ...
    def __init__(self, id: Any) -> None: ...
    def __hash__(self) -> Any: ...
    def __eq__(self, other: Any) -> Any: ...
    def __bool__(self): ...
    def id(self): ...
    def is_valid(self): ...
    def hwnd(self): ...
    def active_sheet(self): ...
    def active_view(self): ...
    def new_html_sheet(self, name: Any, contents: Any, flags: int = ..., group: int = ...): ...
    def run_command(self, cmd: Any, args: Optional[Any] = ...) -> None: ...
    def new_file(self, flags: int = ..., syntax: str = ...): ...
    def open_file(self, fname: Any, flags: int = ..., group: int = ...): ...
    def find_open_file(self, fname: Any): ...
    def num_groups(self): ...
    def active_group(self): ...
    def focus_group(self, idx: Any) -> None: ...
    def focus_sheet(self, sheet: Any) -> None: ...
    def focus_view(self, view: Any) -> None: ...
    def select_sheets(self, sheets: Any) -> None: ...
    def bring_to_front(self) -> None: ...
    def get_sheet_index(self, sheet: Any): ...
    def get_view_index(self, view: Any): ...
    def set_sheet_index(self, sheet: Any, group: Any, idx: Any) -> None: ...
    def set_view_index(self, view: Any, group: Any, idx: Any) -> None: ...
    def sheets(self): ...
    def views(self, *, include_transient: bool = ...): ...
    def selected_sheets(self): ...
    def selected_sheets_in_group(self, group: Any): ...
    def active_sheet_in_group(self, group: Any): ...
    def active_view_in_group(self, group: Any): ...
    def sheets_in_group(self, group: Any): ...
    def views_in_group(self, group: Any): ...
    def transient_sheet_in_group(self, group: Any): ...
    def transient_view_in_group(self, group: Any): ...
    def layout(self): ...
    def get_layout(self): ...
    def set_layout(self, layout: Any) -> None: ...
    def create_output_panel(self, name: Any, unlisted: bool = ...): ...
    def find_output_panel(self, name: Any): ...
    def destroy_output_panel(self, name: Any) -> None: ...
    def active_panel(self): ...
    def panels(self): ...
    def get_output_panel(self, name: Any): ...
    def show_input_panel(self, caption: Any, initial_text: Any, on_done: Any, on_change: Any, on_cancel: Any): ...
    def show_quick_panel(self, items: Any, on_select: Any, flags: int = ..., selected_index: int = ..., on_highlight: Optional[Any] = ..., placeholder: Optional[Any] = ...) -> None: ...
    def is_sidebar_visible(self): ...
    def set_sidebar_visible(self, flag: Any) -> None: ...
    def is_minimap_visible(self): ...
    def set_minimap_visible(self, flag: Any) -> None: ...
    def is_status_bar_visible(self): ...
    def set_status_bar_visible(self, flag: Any) -> None: ...
    def get_tabs_visible(self): ...
    def set_tabs_visible(self, flag: Any) -> None: ...
    def is_menu_visible(self): ...
    def set_menu_visible(self, flag: Any) -> None: ...
    def folders(self): ...
    def project_file_name(self): ...
    def project_data(self): ...
    def set_project_data(self, v: Any) -> None: ...
    def workspace_file_name(self): ...
    def settings(self): ...
    def template_settings(self): ...
    def symbol_locations(self, sym: Any, source: Any = ..., type: Any = ..., kind_id: Any = ..., kind_letter: str = ...): ...
    def lookup_symbol_in_index(self, sym: Any): ...
    def lookup_symbol_in_open_files(self, sym: Any): ...
    def lookup_references_in_index(self, sym: Any): ...
    def lookup_references_in_open_files(self, sym: Any): ...
    def extract_variables(self): ...
    def status_message(self, msg: Any) -> None: ...

class Edit:
    edit_token: Any = ...
    def __init__(self, token: Any) -> None: ...

class Region:
    a: Any = ...
    b: Any = ...
    xpos: Any = ...
    def __init__(self, a: Any, b: Optional[Any] = ..., xpos: int = ...) -> None: ...
    def __len__(self): ...
    def __eq__(self, rhs: Any) -> Any: ...
    def __lt__(self, rhs: Any) -> Any: ...
    def to_tuple(self): ...
    def empty(self): ...
    def begin(self): ...
    def end(self): ...
    def size(self): ...
    def contains(self, x: Any): ...
    def cover(self, rhs: Any): ...
    def intersection(self, rhs: Any): ...
    def intersects(self, rhs: Any): ...

class HistoricPosition:
    pt: Any = ...
    row: Any = ...
    col: Any = ...
    col_utf16: Any = ...
    col_utf8: Any = ...
    def __init__(self, pt: Any, row: Any, col: Any, col_utf16: Any, col_utf8: Any) -> None: ...

class TextChange:
    a: Any = ...
    b: Any = ...
    len_utf16: Any = ...
    len_utf8: Any = ...
    str: Any = ...
    def __init__(self, pa: Any, pb: Any, len_utf16: Any, len_utf8: Any, s: Any) -> None: ...

class Selection:
    view_id: Any = ...
    def __init__(self, id: Any) -> None: ...
    def __len__(self): ...
    def __getitem__(self, index: Any): ...
    def __delitem__(self, index: Any) -> None: ...
    def __eq__(self, rhs: Any) -> Any: ...
    def __lt__(self, rhs: Any) -> Any: ...
    def __bool__(self): ...
    def is_valid(self): ...
    def clear(self) -> None: ...
    def add(self, x: Any) -> None: ...
    def add_all(self, regions: Any) -> None: ...
    def subtract(self, region: Any) -> None: ...
    def contains(self, region: Any): ...

def make_sheet(sheet_id: Any): ...

class Sheet:
    sheet_id: Any = ...
    def __init__(self, id: Any) -> None: ...
    def __hash__(self) -> Any: ...
    def __eq__(self, other: Any) -> Any: ...
    def id(self): ...
    def window(self): ...
    def view(self): ...
    def file_name(self): ...
    def is_semi_transient(self): ...
    def is_transient(self): ...
    def group(self): ...
    def close(self): ...

class TextSheet(Sheet):
    def set_name(self, name: Any) -> None: ...

class ImageSheet(Sheet): ...

class HtmlSheet(Sheet):
    def set_name(self, name: Any) -> None: ...
    def set_contents(self, contents: Any) -> None: ...

class View:
    view_id: Any = ...
    selection: Any = ...
    settings_object: Any = ...
    def __init__(self, id: Any) -> None: ...
    def __len__(self): ...
    def __hash__(self, other: Any) -> Any: ...
    def __eq__(self, other: Any) -> Any: ...
    def __bool__(self): ...
    def id(self): ...
    def buffer_id(self): ...
    def buffer(self): ...
    def sheet_id(self): ...
    def sheet(self): ...
    def element(self): ...
    def is_valid(self): ...
    def is_primary(self): ...
    def window(self): ...
    def clones(self): ...
    def file_name(self): ...
    def close(self): ...
    def retarget(self, new_fname: Any) -> None: ...
    def name(self): ...
    def set_name(self, name: Any) -> None: ...
    def reset_reference_document(self) -> None: ...
    def set_reference_document(self, reference: Any) -> None: ...
    def is_loading(self): ...
    def is_dirty(self): ...
    def is_read_only(self): ...
    def set_read_only(self, read_only: Any): ...
    def is_scratch(self): ...
    def set_scratch(self, scratch: Any): ...
    def encoding(self): ...
    def set_encoding(self, encoding_name: Any): ...
    def line_endings(self): ...
    def set_line_endings(self, line_ending_name: Any): ...
    def size(self): ...
    def begin_edit(self, edit_token: Any, cmd: Any, args: Optional[Any] = ...): ...
    def end_edit(self, edit: Any) -> None: ...
    def is_in_edit(self): ...
    def insert(self, edit: Any, pt: Any, text: Any): ...
    def erase(self, edit: Any, r: Any) -> None: ...
    def replace(self, edit: Any, r: Any, text: Any) -> None: ...
    def change_count(self): ...
    def change_id(self): ...
    def transform_region_from(self, r: Any, when: Any): ...
    def run_command(self, cmd: Any, args: Optional[Any] = ...) -> None: ...
    def sel(self): ...
    def substr(self, x: Any): ...
    def find(self, pattern: Any, start_pt: Any, flags: int = ...): ...
    def find_all(self, pattern: Any, flags: int = ..., fmt: Optional[Any] = ..., extractions: Optional[Any] = ...): ...
    def settings(self): ...
    def meta_info(self, key: Any, pt: Any): ...
    def extract_tokens_with_scopes(self, r: Any): ...
    def extract_scope(self, pt: Any): ...
    def scope_name(self, pt: Any): ...
    def context_backtrace(self, pt: Any): ...
    def match_selector(self, pt: Any, selector: Any): ...
    def score_selector(self, pt: Any, selector: Any): ...
    def find_by_selector(self, selector: Any): ...
    def style(self): ...
    def style_for_scope(self, scope: Any): ...
    def indented_region(self, pt: Any): ...
    def indentation_level(self, pt: Any): ...
    def has_non_empty_selection_region(self): ...
    def lines(self, r: Any): ...
    def split_by_newlines(self, r: Any): ...
    def line(self, x: Any): ...
    def full_line(self, x: Any): ...
    def word(self, x: Any): ...
    def classify(self, pt: Any): ...
    def find_by_class(self, pt: Any, forward: Any, classes: Any, separators: str = ...): ...
    def expand_by_class(self, x: Any, classes: Any, separators: str = ...): ...
    def rowcol(self, tp: Any): ...
    def rowcol_utf8(self, tp: Any): ...
    def rowcol_utf16(self, tp: Any): ...
    def text_point(self, row: Any, col: Any, *, clamp_column: bool = ...): ...
    def text_point_utf8(self, row: Any, col_utf8: Any, *, clamp_column: bool = ...): ...
    def text_point_utf16(self, row: Any, col_utf16: Any, *, clamp_column: bool = ...): ...
    def visible_region(self): ...
    def show(self, x: Any, show_surrounds: bool = ..., keep_to_left: bool = ..., animate: bool = ...): ...
    def show_at_center(self, x: Any): ...
    def viewport_position(self): ...
    def set_viewport_position(self, xy: Any, animate: bool = ...): ...
    def viewport_extent(self): ...
    def layout_extent(self): ...
    def text_to_layout(self, tp: Any): ...
    def text_to_window(self, tp: Any): ...
    def layout_to_text(self, xy: Any): ...
    def layout_to_window(self, xy: Any): ...
    def window_to_layout(self, xy: Any): ...
    def window_to_text(self, xy: Any): ...
    def line_height(self): ...
    def em_width(self): ...
    def is_folded(self, sr: Any): ...
    def folded_regions(self): ...
    def fold(self, x: Any): ...
    def unfold(self, x: Any): ...
    def add_regions(self, key: Any, regions: Any, scope: str = ..., icon: str = ..., flags: int = ..., annotations: Any = ..., annotation_color: str = ..., on_navigate: Optional[Any] = ..., on_close: Optional[Any] = ...) -> None: ...
    def get_regions(self, key: Any): ...
    def erase_regions(self, key: Any) -> None: ...
    def add_phantom(self, key: Any, region: Any, content: Any, layout: Any, on_navigate: Optional[Any] = ...): ...
    def erase_phantoms(self, key: Any) -> None: ...
    def erase_phantom_by_id(self, pid: Any) -> None: ...
    def query_phantom(self, pid: Any): ...
    def query_phantoms(self, pids: Any): ...
    def assign_syntax(self, syntax: Any) -> None: ...
    def set_syntax_file(self, syntax_file: Any) -> None: ...
    def syntax(self): ...
    def symbols(self): ...
    def get_symbols(self): ...
    def indexed_symbols(self): ...
    def indexed_references(self): ...
    def symbol_regions(self): ...
    def indexed_symbol_regions(self, type: Any = ...): ...
    def set_status(self, key: Any, value: Any) -> None: ...
    def get_status(self, key: Any): ...
    def erase_status(self, key: Any) -> None: ...
    def extract_completions(self, prefix: Any, tp: int = ...): ...
    def find_all_results(self): ...
    def find_all_results_with_text(self): ...
    def command_history(self, delta: Any, modifying_only: bool = ...): ...
    def overwrite_status(self): ...
    def set_overwrite_status(self, value: Any) -> None: ...
    def show_popup_menu(self, items: Any, on_select: Any, flags: int = ...): ...
    def show_popup(self, content: Any, flags: int = ..., location: int = ..., max_width: int = ..., max_height: int = ..., on_navigate: Optional[Any] = ..., on_hide: Optional[Any] = ...) -> None: ...
    def update_popup(self, content: Any) -> None: ...
    def is_popup_visible(self): ...
    def hide_popup(self) -> None: ...
    def is_auto_complete_visible(self): ...
    def preserve_auto_complete_on_focus_lost(self) -> None: ...
    def export_to_html(self, regions: Optional[Any] = ..., minihtml: bool = ..., enclosing_tags: bool = ..., font_size: bool = ..., font_family: bool = ...): ...

class Buffer:
    buffer_id: Any = ...
    def __init__(self, id: Any) -> None: ...
    def __hash__(self) -> Any: ...
    def __eq__(self, other: Any) -> Any: ...
    def id(self): ...
    def file_name(self): ...
    def views(self): ...
    def primary_view(self): ...

class Settings:
    settings_id: Any = ...
    def __init__(self, id: Any) -> None: ...
    def get(self, key: Any, default: Optional[Any] = ...): ...
    def has(self, key: Any): ...
    def set(self, key: Any, value: Any) -> None: ...
    def erase(self, key: Any) -> None: ...
    def add_on_change(self, tag: Any, callback: Any) -> None: ...
    def clear_on_change(self, tag: Any) -> None: ...

class Phantom:
    region: Any = ...
    content: Any = ...
    layout: Any = ...
    on_navigate: Any = ...
    id: Any = ...
    def __init__(self, region: Any, content: Any, layout: Any, on_navigate: Optional[Any] = ...) -> None: ...
    def __eq__(self, rhs: Any) -> Any: ...
    def to_tuple(self): ...

class PhantomSet:
    view: Any = ...
    key: Any = ...
    phantoms: Any = ...
    def __init__(self, view: Any, key: str = ...) -> None: ...
    def __del__(self) -> None: ...
    def update(self, new_phantoms: Any) -> None: ...

class Html:
    data: Any = ...
    def __init__(self, data: Any) -> None: ...

class CompletionList:
    target: Any = ...
    completions: Any = ...
    flags: Any = ...
    def __init__(self, completions: Optional[Any] = ..., flags: int = ...) -> None: ...
    def set_completions(self, completions: Any, flags: int = ...) -> None: ...

class CompletionItem:
    trigger: Any = ...
    annotation: Any = ...
    completion: Any = ...
    completion_format: Any = ...
    kind: Any = ...
    details: Any = ...
    flags: int = ...
    def __init__(self, trigger: Any, annotation: str = ..., completion: str = ..., completion_format: Any = ..., kind: Any = ..., details: str = ...) -> None: ...
    def __eq__(self, rhs: Any) -> Any: ...
    @classmethod
    def snippet_completion(cls, trigger: Any, snippet: Any, annotation: str = ..., kind: Any = ..., details: str = ...): ...
    @classmethod
    def command_completion(cls, trigger: Any, command: Any, args: Any = ..., annotation: str = ..., kind: Any = ..., details: str = ...): ...

def list_syntaxes(): ...
def syntax_from_path(path: Any): ...
def find_syntax_by_name(name: Any): ...
def find_syntax_by_scope(scope: Any): ...
def find_syntax_for_file(path: Any, first_line: str = ...): ...

class Syntax:
    path: Any = ...
    name: Any = ...
    hidden: Any = ...
    scope: Any = ...
    def __init__(self, path: Any, name: Any, hidden: Any, scope: Any) -> None: ...
    def __eq__(self, other: Any) -> Any: ...

class QuickPanelItem:
    trigger: Any = ...
    details: Any = ...
    annotation: Any = ...
    kind: Any = ...
    def __init__(self, trigger: Any, details: str = ..., annotation: str = ..., kind: Any = ...) -> None: ...

class ListInputItem:
    text: Any = ...
    value: Any = ...
    details: Any = ...
    annotation: Any = ...
    kind: Any = ...
    def __init__(self, text: Any, value: Any, details: str = ..., annotation: str = ..., kind: Any = ...) -> None: ...

class SymbolRegion:
    name: Any = ...
    region: Any = ...
    syntax: Any = ...
    type: Any = ...
    kind: Any = ...
    def __init__(self, name: Any, region: Any, syntax: Any, type: Any, kind: Any) -> None: ...

class SymbolLocation:
    path: Any = ...
    display_name: Any = ...
    row: Any = ...
    col: Any = ...
    syntax: Any = ...
    type: Any = ...
    kind: Any = ...
    def __init__(self, path: Any, display_name: Any, row: Any, col: Any, syntax: Any, type: Any, kind: Any) -> None: ...
    def path_encoded_position(self): ...