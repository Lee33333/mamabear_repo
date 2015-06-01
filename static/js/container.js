define([
    'jquery',
    'knockout'
], function ($, ko) {
    function Container() {
        var self = this;
        self.id = ko.observable();
        self.image = ko.observable();
        self.host = ko.observable();
        self.status = ko.observable();
        self.command = ko.observable();
        self.state = ko.observable();
        self.startedAt = ko.observable();        
    };

    return Container;
});
