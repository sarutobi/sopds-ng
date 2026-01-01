import $ from 'jquery';
import 'what-input';

window.jQuery = $;
require('foundation-sites');

// Add search field validator
Foundation.Abide.defaults.validators["SearchLenghtValidator"] = function ($el, required, parent) {
        return $el.val().length >= 3;
};

$(document).foundation();
