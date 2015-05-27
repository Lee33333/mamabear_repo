define([
    'jquery',
    'knockout',
    'pager',
    'image',
    'deployment',
    'host',
    'container'
], function ($, ko, pager, Image, Deployment, Host, Container) {
    
    function App(page) {

        var self = this;
        var api_path = '../mamabear/v1/app';
               
        self.name = ko.observable();
        self.deployments = ko.observableArray([]);
        self.images = ko.observableArray([]);
        self.status = ko.observable('new');
                
        self.imageList = ko.computed(function() {
            return $.map(self.images(), function(image, i) {
                return image.tag();
            });
        });
        
        self.imagesPath = ko.computed(function() {
            return api_path+'/'+self.name()+'/images';
        });
        
        self.deploymentsPath = ko.computed(function() {
            return api_path+'/'+self.name()+'/deployments';
        });

        self.new_image = function(data) {
            image = new Image();
            if (data) {
                image.hash(data.id);
                image.tag(data.tag);
            }
            return image;
        };

        self.new_container = function(data) {            
            container = new Container();
            if (data) {
                container.image(self.new_image(data.image));
                container.host(self.new_host({'hostname': data.host}));
                container.status(data.status);
                container.command(data.command);
            }
            return container;
        };

        self.new_host = function(data) {            
            host = new Host();
            if (data) {
                host.hostname(data.hostname);
                if (data.hasOwnProperty('port')) {
                    host.port(data.port);
                }
                if (data.hasOwnProperty('asg_name')) {
                    host.asgName(data.asg_name);
                }
                if (data.hasOwnProperty('containers')) {
                    $.each(data.containers, function(i, container) {
                        host.containers.push(self.new_container(container));
                    });
                }
            }
            return host;
        };
        
        self.new_deployment = function(data) {
            deployment = new Deployment();
            deployment.appName(data.app_name);
            deployment.imageTag(data.image_tag);
            deployment.environment(data.environment);
            deployment.statusEndpoint(data.status_endpoint);
            deployment.environmentVariables(data.environment_variables);
            
            $.each(data.mapped_ports, function(i, mapped) {
                deployment.mappedPorts.push(mapped);
            });

            $.each(data.mapped_volumes, function(i, mapped) {
                deployment.mappedVolumes.push(mapped);
            });

            $.each(data.hosts, function(i, host) {
                deployment.hosts.push(self.new_host({'hostname':host}));
            });

            $.each(data.containers, function(i, container) {
                deployment.containers.push(self.new_container(container));
            });
            
            return deployment;
        };

        self.create = function() {
            console.log('creating new app');
            self.status('loading');
            data = {
                'app': {
                    'name': self.name()
                }
            };
            $.ajax({
                type: 'POST',
                data: ko.toJSON(data),
                url: api_path,
                contentType: 'application/json'
            }).done(function(json) {
                console.log(json);
                self.get(function(a) {
                    self.status('ok');
                    pager.navigate('#apps/all');
                });                
            }).fail(function() {
                console.log("Failed creating app");
            });
        };
        
        // Can we do the callback twice?
        self.get = function(callback) {
            self.status('loading');
            
            // Get App images
            $.getJSON(self.imagesPath(), function (data) {
                if (data) {
                    self.images.removeAll();                    
                    $.each(data[self.name()]['images'], function(i, image) {
                        self.images.push(self.new_image(image));
                    });
                    self.status('images ok');
                    callback(self);
                } else {
                    self.status('error');                    
                }
            });

            // Get App deployments
            $.getJSON(self.deploymentsPath(), function (data) {
                if (data) {
                    self.deployments.removeAll();                    
                    $.each(data[self.name()]['deployments'], function(i, deployment) {
                        self.deployments.push(self.new_deployment(deployment));
                    });
                    self.status('deployments ok');
                    callback(self);
                } else {
                    self.status('error');
                }
            });            
        };

        // Initialize from page
        if (page) {
            if (page.page.parentPage.id() == 'apps') {
                var appName = page.page.id();
                self.name(appName);
                self.get(function(app) {
                    console.log('got app'); 
                });
            }
        } 
    }

    return App;
});
