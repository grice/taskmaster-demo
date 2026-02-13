/**
 * @mention autocomplete for textareas.
 * Attach to any textarea by adding the class "mention-input".
 */
(function() {
    var dropdown = null;
    var activeTextarea = null;
    var mentionStart = -1;
    var activeIndex = 0;
    var items = [];

    function createDropdown() {
        dropdown = document.createElement('div');
        dropdown.className = 'mention-dropdown';
        document.body.appendChild(dropdown);
    }

    function hideDropdown() {
        if (dropdown) dropdown.style.display = 'none';
        mentionStart = -1;
        activeIndex = 0;
        items = [];
    }

    function showDropdown(results, textarea) {
        if (!dropdown) createDropdown();
        items = results;
        activeIndex = 0;

        if (results.length === 0) {
            hideDropdown();
            return;
        }

        dropdown.innerHTML = results.map(function(p, i) {
            return '<div class="mention-item' + (i === 0 ? ' active' : '') + '" data-index="' + i + '">' +
                   '<strong>' + escapeHtml(p.name) + '</strong>' +
                   '</div>';
        }).join('');

        // Position below the cursor in the textarea
        var rect = textarea.getBoundingClientRect();
        var lineHeight = parseInt(getComputedStyle(textarea).lineHeight) || 20;
        dropdown.style.top = (rect.top + window.scrollY + lineHeight + 24) + 'px';
        dropdown.style.left = rect.left + 'px';
        dropdown.style.width = Math.max(rect.width, 200) + 'px';
        dropdown.style.display = 'block';

        // Click handlers
        dropdown.querySelectorAll('.mention-item').forEach(function(item) {
            item.addEventListener('mousedown', function(e) {
                e.preventDefault();
                selectItem(parseInt(item.getAttribute('data-index')));
            });
        });
    }

    function selectItem(index) {
        if (!activeTextarea || mentionStart === -1 || index >= items.length) return;
        var person = items[index];
        var ta = activeTextarea;
        var before = ta.value.substring(0, mentionStart);
        var after = ta.value.substring(ta.selectionStart);
        var insert = '@"' + person.name + '" ';
        ta.value = before + insert + after;
        ta.selectionStart = ta.selectionEnd = before.length + insert.length;
        ta.focus();
        hideDropdown();
    }

    function escapeHtml(text) {
        var div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    function fetchPeople(query) {
        fetch('/people/search.json?q=' + encodeURIComponent(query))
            .then(function(r) { return r.json(); })
            .then(function(results) {
                showDropdown(results, activeTextarea);
            });
    }

    document.addEventListener('input', function(e) {
        var ta = e.target;
        if (!ta.matches || !ta.matches('textarea.mention-input')) return;
        activeTextarea = ta;

        var pos = ta.selectionStart;
        var text = ta.value.substring(0, pos);

        // Find the last @ that isn't inside quotes already completed
        var atIndex = text.lastIndexOf('@');
        if (atIndex === -1 || (atIndex > 0 && text[atIndex - 1] !== ' ' && text[atIndex - 1] !== '\n' && atIndex !== 0)) {
            // @ must be at start or preceded by whitespace
            if (atIndex > 0 && text[atIndex - 1] !== ' ' && text[atIndex - 1] !== '\n') {
                hideDropdown();
                return;
            }
        }

        if (atIndex === -1) {
            hideDropdown();
            return;
        }

        var query = text.substring(atIndex + 1);
        // If user already closed quotes, stop suggesting
        if (query.indexOf('"') !== -1 && query.lastIndexOf('"') > query.indexOf('"')) {
            hideDropdown();
            return;
        }
        // Strip leading quote if present
        query = query.replace(/^"/, '');

        if (query.length === 0) {
            // Show all people on bare @
            mentionStart = atIndex;
            fetchPeople('');
        } else if (query.length >= 1) {
            mentionStart = atIndex;
            fetchPeople(query);
        } else {
            hideDropdown();
        }
    });

    document.addEventListener('keydown', function(e) {
        if (!dropdown || dropdown.style.display === 'none') return;
        if (!e.target.matches || !e.target.matches('textarea.mention-input')) return;

        if (e.key === 'ArrowDown') {
            e.preventDefault();
            activeIndex = Math.min(activeIndex + 1, items.length - 1);
            updateActive();
        } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            activeIndex = Math.max(activeIndex - 1, 0);
            updateActive();
        } else if (e.key === 'Enter' || e.key === 'Tab') {
            if (items.length > 0) {
                e.preventDefault();
                selectItem(activeIndex);
            }
        } else if (e.key === 'Escape') {
            hideDropdown();
        }
    });

    function updateActive() {
        if (!dropdown) return;
        dropdown.querySelectorAll('.mention-item').forEach(function(item, i) {
            item.classList.toggle('active', i === activeIndex);
        });
    }

    // Hide on click outside
    document.addEventListener('click', function(e) {
        if (dropdown && !dropdown.contains(e.target)) {
            hideDropdown();
        }
    });
})();
