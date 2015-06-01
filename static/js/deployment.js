define([
    'jquery',
    'knockout',
    'pager',
    'container',
    'image'
], function ($, ko, pager, Container, Image) {
    function Deployment(page) {        
        var self = this;
        
        self.appName = ko.observable();
        self.imageTag = ko.observable();
        self.environment = ko.observable();
        self.statusEndpoint = ko.observable();
        self.statusPort = ko.observable();
        self.mappedPorts = ko.observableArray([]);
        self.mappedVolumes = ko.observableArray([]);
        self.hosts = ko.observableArray([]);
        self.links = ko.observableArray([]);
        self.volumes = ko.observableArray([]);
        self.containers = ko.observableArray([]);
        self.environmentVariables = ko.observable({});
        self.parent = ko.observable('');
        self.imageList = ko.observableArray([]);        

        self.environmentVariablesString = ko.observable('');
        self.mappedPortsString = ko.observable('');
        self.mappedVolumesString = ko.observable('');

        self.envVarList = ko.computed(function() {
            var result = [];
            for (var key in self.environmentVariables()) {
                result.push({
                    'name': key,
                    'value': self.environmentVariables()[key]
                });
            }
            return result;
        });
        
        self.upContainers = ko.computed(function() {
            var result = 0;
            $.each(self.containers(), function(i, container) {
                if (container.status() === 'up') {
                    result += 1;
                }
            });
            return result;
        });
        
        self.serialize = ko.computed(function() {
            var s = {
                'environment': self.environment(),
                'app_name': self.appName(),
                'image_tag': self.imageTag(),
                'status_endpoint': self.statusEndpoint(),
                'status_port': self.statusPort(),
                'mapped_ports': self.mappedPorts(),
                'mapped_volumes': self.mappedVolumes(),
                'environment_variables': self.environmentVariables()
            };

            if (self.hosts() && self.hosts().length > 0) {
                s['hosts'] = self.hosts();
            }
            
            if (self.links() && self.links().length > 0) {
                s['links'] = [];
                $.each(self.links(), function(i, link) {
                    if (link.includes(':')) {
                        var pair = link.split(':');
                        s['links'].push({
                            'app_name': pair[0],
                            'image_tag': pair[1]
                        });
                    }
                });
            }
            
            if (self.volumes() && self.volumes().length > 0) {
                s['volumes'] = [];
                $.each(self.volumes(), function(i, volume) {
                    if (volume.includes(':')) {
                        var pair = volume.split(':');
                        s['volumes'].push({
                            'app_name': pair[0],
                            'image_tag': pair[1]
                        });
                    }
                });
            }
            
            if (self.environmentVariablesString() && self.environmentVariablesString() !== '') {                
                $.each(self.environmentVariablesString().split(','), function(i, kv) {
                    var pair = kv.split('=');
                    s['environment_variables'][$.trim(pair[0])] = $.trim(pair[1]);
                });                
            }            
            if (self.mappedPortsString() && self.mappedPortsString() !== '') {
                $.each(self.mappedPortsString().split(','), function(i, mapped) {
                    s['mapped_ports'].push(mapped);
                });
                s['mapped_ports'] = $.unique(s['mapped_ports']);
            }
            if (self.mappedVolumesString() && self.mappedVolumesString() !== '') {
                $.each(self.mappedVolumesString().split(','), function(i, mapped) {
                    s['mapped_volumes'].push(mapped);
                });
                s['mapped_volumes'] = $.unique(s['mapped_volumes']);
            }
            return s;
        });
        
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

        self.updateImageList = function() {
            $.getJSON(self.appImagesPath(), function(data) {
                if (data) {
                    self.imageList.removeAll();
                    $.each(data[self.appName()]['images'], function(i, image) {
                        self.imageList.push(image.tag);
                    });
                }
            })
        };

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
                container.host(data.host);
                container.status(data.status);
                container.command(data.command);
                container.state(data.state);
            }
            return container;
        };

        
        self.get = function(callback) {
            $.getJSON(self.deploymentPath(), function (data) {
                if (data) {
                    self.environment(data.environment);
                    self.imageTag(data.image_tag);
                    self.appName(data.app_name);
                    self.hosts(data.hosts);
                    
                    console.log(data);
                    self.containers.removeAll();
                    $.each(data.containers, function(i, container) {
                        self.containers.push(self.new_container(container));
                    });

                    self.environmentVariables(data.environment_variables);
                    if (data.hasOwnProperty('mapped_ports') && data.mapped_ports != '') {
                        self.mappedPorts(data.mapped_ports);
                    }
                    if (data.hasOwnProperty('mapped_volumes') && data.mapped_volumes != '') {
                        self.mappedVolumes(data.mapped_volumes);
                    }              
                    if (data.hasOwnProperty('status_endpoint') && data.status_endpoint !== '') {
                        self.statusEndpoint(data.status_endpoint);
                    }
                    if (data.hasOwnProperty('status_port') && data.status_port !== '') {
                        self.statusPort(data.status_port);
                    }
                    if (data.hasOwnProperty('links')) {
                        $.each(data.links, function(i, link) {
                            self.links.push(link.app_name+':'+link.tag);
                        });
                    }
                    if (data.hasOwnProperty('volumes')) {
                        $.each(data.volumes, function(i, volume) {
                            self.volumes.push(volume.app_name+':'+volume.tag);
                        });
                    }
                    if (data.hasOwnProperty('parent') && data.parent !== '') {
                        self.parent(data.parent);
                    }
                    self.updateImageList();
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
                'deployment': self.serialize()
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
                    $('#deployment-containers').DataTable();
                });
            }
        }
    };

    return Deployment;
});
