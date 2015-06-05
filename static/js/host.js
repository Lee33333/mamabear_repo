define([
    'jquery',
    'knockout',    
    'pager',
    'container',
    'image'
], function ($, ko, pager, Container, Image) {
    function Host(page) {
        var self = this;
        var apiPath = '../mamabear/v1/host';
        
        self.hostname = ko.observable();
        self.alias = ko.observable();
        self.port = ko.observable();
        self.asgName = ko.observable();
        self.containers = ko.observableArray([]);
        self.status = ko.observable();

        self.deletePath = ko.computed(function() {
            return apiPath+'/'+self.alias();
        });
        
        self.hostPath = ko.computed(function() {
            return apiPath+'?hostname='+self.hostname();
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
        
        self.new_container = function(data) {
            container = new Container();
            if (data) {
                container.id(data.id);
                container.image(self.new_image(data.image));
                container.host(self);
                container.status(data.status);
                container.command(data.command);
                container.state(data.state);
            }
            return container;
        };

        self.deleteHost = function() {
            $.ajax({
                type: 'DELETE',
                url: self.deletePath()
            }).done(function(json) {
                pager.navigate('#deployments/all');
            }).fail(function() {
                console.log("Failed deleting host");
            });
        };
        
        self.create = function() {
            data = {
                'host': {
                    'hostname': self.hostname(),
                    'alias': self.alias(),
                    'port': self.port()
                }
            };
            $.ajax({
                type: 'POST',
                data: ko.toJSON(data),
                url: apiPath,
                contentType: 'application/json'
            }).done(function(json) {
                self.get(function(h) {
                    pager.navigate('#hosts/all');
                });                
            }).fail(function() {
                console.log("Failed creating host");
            });
        };
        
        self.get = function(callback) {
            $.getJSON(self.hostPath(), function(data) {
                if (data && data.hits.length > 0) {
                    hostData = data.hits[0];
                    self.hostname(hostData.hostname);
                    self.alias(hostData.alias);
                    if (hostData.hasOwnProperty('port')) {
                        self.port(hostData.port);
                    }
                    if (hostData.hasOwnProperty('status')) {
                        self.status(hostData.status);
                    }
                    if (hostData.hasOwnProperty('asg_name')) {
                        self.asgName(hostData.asg_name);
                    }
                    if (hostData.hasOwnProperty('containers')) {
                        $.each(hostData.containers, function(i, container) {
                            self.containers.push(self.new_container(container));
                        });
                    }
                    callback(self);
                } else {
                    console.log("Failed fetching host");
                }
            });
        };

        if (page) {
            if (page.page.parentPage.id() == 'hosts') {
                self.hostname(page.page.id());
                self.get(function(host) {
                    $('#host-containers').DataTable();
                });
            }
        }
    };

    return Host;
});
