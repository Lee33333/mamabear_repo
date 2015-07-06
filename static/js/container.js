define([
    'jquery',
    'knockout',
    'image'
], function ($, ko, Image) {
    function Container(page) {
        var self = this;
        self.id = ko.observable();
        self.image = ko.observable();
        self.host = ko.observable();
        self.status = ko.observable();
        self.command = ko.observable();
        self.state = ko.observable();
        self.startedAt = ko.observable();
        self.deployment = ko.observable();
        self.logs = ko.observable('');
        
        self.containerPath = ko.computed(function() {
            return '../mamabear/v1/container/'+self.id();
        });

        self.logPath = ko.computed(function() {
            return '../mamabear/v1/container/'+self.id()+'/logs';
        });
        
        self.deploymentPath = ko.computed(function() {
            if (self.deployment()) {
                return '#deployments/'+self.deployment().replace(':', '/');
            } else {
                return '#';
            }
        });
        
        self.new_image = function(data) {
            image = new Image();
            if (data) {
                if (data.hasOwnProperty('id')) {
                    image.hash(data.id);
                }                
                if (data.hasOwnProperty('tag')) {
                    image.tag(data.tag);
                }
            }
            return image;
        };

        self.refreshLogs = function() {
            self.getLogs(function() {});
        };
        
        self.getLogs = function(callback) {
            $.getJSON(self.logPath(), function (data) {
                if (data) {
                    self.logs(data.logs);
                    callback(self);
                } else {
                    callback(self);
                }
            });
        };
        
        self.get = function(callback) {
            $.getJSON(self.containerPath(), function (data) {
                if (data) {
                    self.image(self.new_image(data.image));
                    self.host(data.host);
                    self.status(data.status);
                    self.state(data.state);
                    self.command(data.command);
                    self.startedAt(data.started_at);
                    self.deployment(data.deployment);
                    self.getLogs(callback);
                } else {
                    callback(self);
                }
            });
        };
        
        if (page) {
            if (page.page.parentPage.id() == 'containers') {
                self.id(page.page.id());
                self.get(function(container) {});
            }
        }
    };

    return Container;
});
