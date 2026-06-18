function inlineEdit() {
    return {
        editingId: null,
        editField: null,
        editValue: '',
        originalValue: '',

        init() {
            // Event delegation for inline-edit clicks on table cells
            const table = document.querySelector('#result_list');
            if (!table) return;

            table.addEventListener('click', (e) => {
                const cell = e.target.closest('td.field-title');
                if (!cell) return;
                const pk = cell.closest('tr').dataset.pk;
                if (!pk) return;

                const textEl = cell.querySelector('.inline-edit-text');
                if (!textEl) return;

                this.originalValue = textEl.textContent.trim();
                this.startEdit(parseInt(pk), 'title', this.originalValue);
            });
        },

        startEdit(id, field, value) {
            this.editingId = id;
            this.editField = field;
            this.editValue = value;
            // Focus input after render
            this.$nextTick(() => {
                const input = document.querySelector('.inline-edit-input');
                if (input) input.focus();
            });
        },

        saveEdit() {
            if (!this.editingId || !this.editField) return;

            const formData = new FormData();
            formData.append('field', this.editField);
            formData.append('value', this.editValue);
            const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]');
            if (csrfToken) {
                formData.append('csrfmiddlewaretoken', csrfToken.value);
            }

            fetch(`/admin/opds_catalog/book/${this.editingId}/inline-save/`, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                },
            }).then(response => {
                if (response.ok) {
                    this.editingId = null;
                    this.editField = null;
                    window.location.reload();
                } else {
                    alert('Save failed');
                }
            }).catch(() => {
                alert('Save failed');
            });
        },

        cancelEdit() {
            this.editingId = null;
            this.editField = null;
        },
    };
}
