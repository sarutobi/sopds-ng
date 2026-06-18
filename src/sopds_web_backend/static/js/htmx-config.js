// htmx Django CSRF integration
document.body.addEventListener('htmx:configRequest', function(evt) {
    var csrfToken = document.querySelector('[name=csrfmiddlewaretoken]');
    if (csrfToken) {
        evt.detail.headers['X-CSRFToken'] = csrfToken.value;
    }
});

// Reinitialize Foundation plugins after htmx content swap
document.body.addEventListener('htmx:afterSwap', function(evt) {
    if (typeof jQuery !== 'undefined' && typeof jQuery().foundation === 'function') {
        jQuery(evt.detail.target).foundation();
    }
});
