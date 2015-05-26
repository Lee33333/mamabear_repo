define([
    'jquery',
    'knockout'
], function ($, ko) {
    function Container() {
        var self = this;

        self.image = ko.observable();
        self.host = ko.observable();
        self.status = ko.observable();
        self.command = ko.observable();
    };

    return Container;
});
