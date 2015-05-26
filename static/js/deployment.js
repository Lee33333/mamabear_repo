define([
    'jquery',
    'knockout',
    'pager',
    'app'
], function ($, ko, pager, App) {
    function Deployment() {
        var self = this;
        
        self.appName = ko.observable();
        self.imageTag = ko.observable();
        self.environment = ko.observable();
        self.statusEndpoint = ko.observable();
        self.mappedPorts = ko.observableArray([]);
        self.mappedVolumes = ko.observableArray([]);
        self.hosts = ko.observableArray([]);
        self.containers = ko.observableArray([]);
        self.environmentVariables = ko.observable();
        self.parent = ko.observable();
        self.imageList = ko.observableArray([]);
        
        self.envOptions = ko.observableArray([
            'test', 'prod'
        ]);
        
        self.apiPath = ko.computed(function() {
            return '../mamabear/v1/app/'+self.appName()+'/deployments';
        });

        self.appImagesPath = ko.computed(function() {
            return '../mamabear/v1/app/'+self.appName()+'/images';
        });

        self.hostsPath = ko.computed(function() {
            return self.apiPath()+'/'+self.imageTag()+'/'+self.environment();
        });
        
        self.appName.subscribe(function (newName) {
            if (newName) {
                $.getJSON(self.appImagesPath(), function(data) {
                    if (data) {
                        self.imageList.removeAll();
                        $.each(data[newName]['images'], function(image, i) {
                            self.imageList.push(image);
                        });
                    }
                })
            }
        });
        
        self.updateHosts = function(callback) {
            data = {
                'hosts': $.map(self.hosts(), function(host, i) {
                    return host.hostname();
                })
            };
            $.ajax({
                type: 'PUT',
                data: data,
                url: self.hostsPath()
            }).done(function(json) {
                callback(json);
            }).fail(function() {
                console.log("failed updating deployment hosts");
            });
        };
        
        self.create = function() {
            data = {
                'deployment': {
                    'app_name': self.appName(),
                    'image_tag': self.imageTag(),
                    'environment': self.environment(),
                    'hosts': self.hosts(),
                    'status_endpoint': self.statusEndpoint()
                }
            };

            if (self.mappedPorts() && self.mappedPorts().length > 0) {
                data['deployment']['mapped_ports'] = self.mappedPorts();
            }
            if (self.mappedVolumes() && self.mappedVolumes().length > 0) {
                data['deployment']['mapped_volumes'] = self.mappedVolumes();
            }
            if (self.environmentVariables()) {
                data['deployment']['environment_variables'] = self.environmentVariables();
            }
            
            if (self.parent()) {
                data['deployment']['parent'] = self.parent();
            };

            console.log(data);
            $.ajax({
                type: 'POST',
                data: ko.toJSON(data),
                url: self.apiPath(),
                contentType: 'application/json'
            }).done(function(json) {
                console.log(json);
                pager.navigate('#deployments/all');
            }).fail(function(json) {
                console.log(json);
                console.log("Failed creating deployment");
            });
        };
    };

    return Deployment;
});
