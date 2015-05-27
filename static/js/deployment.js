define([
    'jquery',
    'knockout',
    'pager',
    'app'
], function ($, ko, pager, App) {
    function Deployment(page) {        
        var self = this;
        
        self.appName = ko.observable();
        self.imageTag = ko.observable();
        self.environment = ko.observable();
        self.statusEndpoint = ko.observable();
        self.mappedPorts = ko.observableArray();
        self.mappedVolumes = ko.observableArray([]);
        self.hosts = ko.observableArray([]);
        self.containers = ko.observableArray([]);
        self.environmentVariables = ko.observable({});
        self.parent = ko.observable('');
        self.imageList = ko.observableArray([]);        
        
        self.envOptions = ko.observableArray([
            'test', 'prod'
        ]);

        self.deploymentPath = ko.computed(function() {
            return '../mamabear/v1/deployment/'+self.appName()+'/'+self.imageTag()+'/'+self.environment();
        });
        
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
                self.appName(newName);
                self.updateImageList(function() {});
            }
        });

        self.updateImageList = function(callback) {
            $.getJSON(self.appImagesPath(), function(data) {
                if (data) {
                    self.imageList.removeAll();
                    $.each(data[self.appName()]['images'], function(i, image) {
                        self.imageList.push(image.tag);
                    });
                    callback();
                }
            })
        };
        
        self.get = function(callback) {
            $.getJSON(self.deploymentPath(), function (data) {
                if (data) {
                    self.environment(data.environment);
                    self.imageTag(data.image_tag);
                    self.appName(data.app_name);
                    self.hosts(data.hosts);
                    self.containers(data.containers);
                    self.environmentVariables(data.environmentVariables);
                    if (data.hasOwnProperty('mapped_ports') && data.mapped_ports != '') {
                        self.mappedPorts(data.mapped_ports);
                    }
                    if (data.hasOwnProperty('mapped_volumes') && data.mapped_volumes != '') {
                        self.mappedVolumes(data.mapped_volumes);
                    }              
                    if (data.hasOwnProperty('status_endpoint') && data.status_endpoint !== '') {
                        self.statusEndpoint(data.status_endpoint);
                    }
                    if (data.hasOwnProperty('parent') && data.parent !== '') {
                        self.parent(data.parent);
                    }
                    self.updateImageList(function() {
                        callback(self);
                    });
                } else {
                    console.log("no deployment");
                }
            });
        };
        
        self.updateHosts = function(callback) {
            data = {
                'hosts': self.hosts()
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

        if (page) {
            if (page.page.parentPage.id() == 'deployments') {
                var appName = page.page.id();
                var imageTag = page.page.route[0];
                var environment = page.page.route[1];

                self.appName(appName);
                self.imageTag(imageTag);
                self.environment(environment);
                self.get(function(dep) {
                    console.log('got dep');
                });
            }
        }
    };

    return Deployment;
});
