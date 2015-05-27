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
        self.port = ko.observable();
        self.asgName = ko.observable();
        self.containers = ko.observableArray([]);
        self.status = ko.observable('ok');
        
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
                container.image(self.new_image(data.image));
                container.host(self);
                container.status(data.status);
                container.command(data.command);
            }
            return container;
        };
        
        self.create = function() {
            console.log("creating host");
            self.status('loading');
            // ignore other fields for now
            data = {
                'host': {
                    'hostname': self.hostname(),
                    'port': self.port()
                }
            };
            $.ajax({
                type: 'POST',
                data: ko.toJSON(data),
                url: apiPath,
                contentType: 'application/json'
            }).done(function(json) {
                console.log(json);
                self.get(function(h) {
                    self.status('ok');
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
                    if (hostData.hasOwnProperty('port')) {
                        self.port(hostData.port);
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
                    console.log('got host');
                });
            }
        }
    };

    return Host;
});
