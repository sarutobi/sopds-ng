// htmx Django CSRF integration
document.body.addEventListener('htmx:configRequest', function(evt) {
    var csrfToken = document.querySelector('[name=csrfmiddlewaretoken]');
    if (csrfToken) {
        evt.detail.headers['X-CSRFToken'] = csrfToken.value;
    }
});

// Reinitialize Foundation plugins after htmx content swap
document.body.addEventListener('htmx:afterSwap', function(evt) {
    if (typeof Foundation !== 'undefined' && Foundation.reInit) {
        Foundation.reInit(evt.detail.target);
    } else if (typeof Foundation !== 'undefined') {
        // Fallback: try to re-init common plugins
        jQuery(document).foundation();
    }
});
