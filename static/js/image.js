define([
    'jquery',
    'knockout'
], function ($, ko) {
    function Image() {
        var self = this;

        self.hash = ko.observable();
        self.tag = ko.observable();
    };

    return Image;
});
