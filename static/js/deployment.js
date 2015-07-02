define([
    'jquery',
    'knockout',
    'pager',
    'container',
    'image',
    'ko_editable',
    'select2',
    'knockoutamdhelpers'
], function ($, ko, pager, Container, Image, ko_editable, select2, knockoutamdhelpers) {
    function Deployment(page) {        
        var self = this;
        
        self.id = ko.observable();
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
        self.parent = ko.observable();
        self.imageList = ko.observableArray([]);        

        self.environmentVariablesString = ko.observable('');
        self.mappedPortsString = ko.observable('');
        self.mappedVolumesString = ko.observable('');

        self.mappedPortToAdd = ko.observable("");
        self.mappedVolumeToAdd = ko.observable("");
        self.envVarToAdd = ko.observable("");
        self.linkToAdd = ko.observable("");
        self.volumeToAdd = ko.observable("");
        self.hostToAdd = ko.observable("");

        self.editingMappedPorts = ko.observable(false);
        self.editMappedPorts = function() {self.editingMappedPorts(!self.editingMappedPorts());};

        self.editingMappedVolumes = ko.observable(false);
        self.editMappedVolumes = function() {self.editingMappedVolumes(!self.editingMappedVolumes());};

        self.editingEnvVars = ko.observable(false);
        self.editEnvVars = function() {self.editingEnvVars(!self.editingEnvVars());};

        self.editingLinks = ko.observable(false);
        self.editLinks = function() {self.editingLinks(!self.editingLinks());};

        self.editingVolumes = ko.observable(false);
        self.editVolumes = function() {self.editingVolumes(!self.editingVolumes());};

        self.editingHosts = ko.observable(false);
        self.editHosts = function() {self.editingHosts(!self.editingHosts());};

        self.launch = function() {
            $.ajax({
                url: self.runPath()
            }).done(function(json) {
                console.log("Deployment launched");
            }).fail(function() {
                console.log("Failed to run deployment");
            });
        };
        
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
                'environment_variables': self.environmentVariables(),
                'parent': self.parent()
            };

            if (self.hosts() && self.hosts().length > 0) {
                s['hosts'] = $.unique($.map(self.hosts(), function(host, i) {
                    return host.hostname;
                }));
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
                s['links'] = $.unique(s['links']);
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
                s['volumes'] = $.unique(s['volumes']);
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

        self.runPath = ko.computed(function() {
            return self.deploymentPath()+'/run';
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
                self.updateImageList();
            }
        }, null, "afterChange");

        self.updateImageList = ko.computed(function() {
            if (self.appName()) {
                var appName = self.appName();
                $.getJSON(self.appImagesPath(), function(data) {
                    if (data) {
                        self.imageList.removeAll();
                        $.each(data[appName]['images'], function(i, image) {
                            self.imageList.push(image.tag);
                        });
                    }
                });
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

        self.bindUpdateSelects = function(page) {
            var hostBindArgs = {
                ajax: {
                    url: '../mamabear/v1/host',
                    dataType: 'json',
                    delay: 250,
                    processResults: function(data, pg) {
                        return {
                            results: $.map(data.hits, function(hit, i) {
                                return {'text': hit.alias, 'id': hit.hostname};
                            })
                        }
                    }
                },
                minimumInputLength: 0
            };
            var imageBindArgs = {
                ajax: {
                    url: '../mamabear/v1/image',
                    dataType: 'json',
                    delay: 250,
                    data: function(params) {
                        var splits = params.term.split(':');
                        var r = {};
                        var app_name = splits[0];
                        r.app_name = splits[0];
                        if (splits.length > 1) {
                            r.image_tag = splits[1];
                        }                                
                        return r;
                    },
                    processResults: function(data, pg) {
                        return {
                            results: $.map(data.hits, function(hit, i) {
                                return {'text': hit.app_name + ':' + hit.tag, 'id': hit.id};
                            })
                        }
                    }
                },
                minimumInputLength: 1
            };

            $('#inputDeploymentHosts').select2(hostBindArgs);
            $('#inputDeploymentHosts').on('select2:select', function(e) {
                var newHost = {
                    'hostname': e.params.data.id,
                    'alias': e.params.data.text 
                };                
                if (self.hosts().indexOf(newHost) == -1) {
                    self.hosts.push(newHost);
                    self.updateHosts();
                }
                $('#inputDeploymentHosts').val(null).trigger('change');
            });

            $('#inputLinkedApp').select2(imageBindArgs);
            $('#inputLinkedApp').on('select2:select', function(e) {
                var linkedApp = e.params.data.text;
                if (self.links().indexOf(linkedApp) == -1) {
                    self.links.push(linkedApp);
                    self.updateLinks();
                }
                
                $('#inputLinkedApp').val(null).trigger('change');
            });

            $('#inputLinkedVolume').select2(imageBindArgs);
            $('#inputLinkedVolume').on('select2:select', function(e) {
                var linkedVolume = e.params.data.text;
                if (self.volumes().indexOf(linkedVolume) == -1) {
                    self.volumes.push(linkedVolume);
                    self.updateVolumes();
                }

                $('#inputLinkedVolume').val(null).trigger('change');
            });
            
            self.mappedPorts.subscribe(function (newName) {                
                if (newName) {
                    console.log(newName);
                    $("#hideMappedPorts").show();
                }
            });
            
            self.mappedVolumes.subscribe(function (newName) {
                if (newName) {
                    $("#hideMappedVolumes").toggle();}
            });
            self.environmentVariables.subscribe(function (newName) {
                if (newName) {
                    $("#hideEnvVars").toggle();}
            });
            self.hosts.subscribe(function (newName) {
                if (newName) {
                    $("#hideConfigHosts").toggle();}
            });
            self.links.subscribe(function (newName) {
                if (newName) {
                    $("#hideLinkedApps").toggle();}
            });
            self.volumes.subscribe(function (newName) {
                if (newName) {
                    $("#hideLinkedVolumes").toggle();}
            });
            self.statusEndpoint.subscribe(function (newName) {
                if (newName) {
                    $("#hideStatusEndpoint").toggle();}
            });
            self.statusPort.subscribe(function (newName) {
                if (newName) {
                    $("#hideStatusPort").toggle();}
            });
            $('#launchButton').click(function() {
                $('#hideStatusPort').hide();
                $('#hideStatusEndpoint').hide();
                $("#hideLinkedVolumes").hide();
                $("#hideLinkedApps").hide();
                $("#hideConfigHosts").hide();
                $("#hideEnvVars").hide();
                $("#hideMappedVolumes").hide();
                $("#hideMappedPorts").hide();
            });
        };
        
        self.addMappedPort = function() {
            if (self.mappedPortToAdd() != "") {
                self.mappedPorts.push(this.mappedPortToAdd()); // Adds the item. Writing to the "items" observableArray causes any associated UI to update.
                self.mappedPortToAdd("");
            }
            data = {
                'deployment': {"mapped_ports": self.mappedPorts()}
            };
            self.putToDeployment(data);
        };
        self.removeMappedPort = function(mappedPort) {
            self.mappedPorts.remove(mappedPort);
            data = {
                'deployment': {"mapped_ports": self.mappedPorts()}
            };
            self.putToDeployment(data);
        };

        self.addMappedVolume = function() {
            if (self.mappedVolumeToAdd() != "") {
                self.mappedVolumes.push(this.mappedVolumeToAdd()); // Adds the item. Writing to the "items" observableArray causes any associated UI to update.
                self.mappedVolumeToAdd("");
            }
            data = {
                'deployment': {"mapped_volumes": self.mappedVolumes()}
            };
            self.putToDeployment(data);
        };
        self.removeMappedVolume = function(mappedVolume) {
            self.mappedVolumes.remove(mappedVolume);
            data = {
                'deployment': {"mapped_volumes": self.mappedVolumes()}
            };
            self.putToDeployment(data);
        };

        self.removeHost = function(host) {
            self.hosts.remove(host);
            self.updateHosts();
        };
        
        self.removeLink = function(link) {
            self.links.remove(link);
            self.updateLinks();
        };

        self.removeVolume = function(volume) {
            self.volumes.remove(volume);
            self.updateVolumes();
        };

        self.updateHosts = function() {
            if (self.hosts() && self.hosts().length > 0) {
                var hosts = [];
                $.each(self.hosts(), function(i, host) {
                    hosts.push(host.hostname);
                });
            }  else {
                var hosts = []
            }
            data = {
                'deployment': {'hosts': hosts}
            };
            self.putToDeployment(data);
        };
        
        self.updateLinks = function() {
            if (self.links() && self.links().length > 0) {
                var the_links = [];
                $.each(self.links(), function(i, link) {
                    if (link.includes(':')) {
                        var pair = link.split(':');
                        the_links.push({
                            'app_name': pair[0],
                            'image_tag': pair[1]
                        });
                    }
                });
            } else { 
                var the_links = []
            }
            data = {
                'deployment': {"links": the_links}
            };
            self.putToDeployment(data);
        }
        
        self.updateVolumes = function() {
            var data = {};
            if (self.links() && self.links().length > 0) {
                var the_volumes = [];
                $.each(self.volumes(), function(i, volume) {
                    if (volume.includes(':')) {
                        var pair = volume.split(':');
                        the_volumes.push({
                            'app_name': pair[0],
                            'image_tag': pair[1]
                        });
                    }
                });
            } else { 
                var the_volumes = []
            }
            data = {
                'deployment': {"volumes": the_volumes}
            };
            self.putToDeployment(data);
            };        

         self.addEnvVar = function() {
            if (self.envVarToAdd() != "") {
            var newEnvVar = this.envVarToAdd(); // foo=bar            
            var pair = newEnvVar.split('=');
            newEnvVar = {"key": pair[0], "value": pair[1] }
            self.environmentVariables()[newEnvVar.key] = newEnvVar.value; // Adds the item. Writing to the "items" observableArray causes any associated UI to update.
            self.envVarToAdd("");
            console.log(this.environmentVariables());
            data = {'deployment': {"environment_variables": self.environmentVariables()}};
            console.log(data);

            self.putToDeployment(data);
            self.environmentVariables.valueHasMutated();
        }
        };

        self.removeEnvVar = function(envVar) {
            name = envVar.name;
            delete self.environmentVariables()[name];
            
            console.log("deleting");
            console.log(self.environmentVariables());

            data = {'deployment': {"environment_variables": self.environmentVariables()}};

            self.putToDeployment(data);
            self.environmentVariables.valueHasMutated();
        };


        self.updateDeployment = function(params) {
            if (params.name === 'statusEndpoint' ) {
                var the_name = 'status_endpoint';
            } else if (params.name === 'statusPort') {
                var the_name = 'status_port';
            } 
            var dep_data = {
            };
            dep_data[the_name] = params.value;
            data = {
                'deployment': dep_data
            };
            self.putToDeployment(data);

        };

        self.putToDeployment = function(data) {
            var targetUrl = '../mamabear/v1/deployment/'+self.appName()+'/'+self.imageTag()+'/'+self.environment();
             $.ajax({
                 type: 'PUT',
                 data: ko.toJSON(data),
                 url: targetUrl,
                 contentType:'application/json'
             }).done(function(json) {
                console.log(json);
             }).fail(function(json) {
                console.log("Failed updating deployment");
                //add alert message here
             });
        };
        
        self.deleteDeployment = function() {
            $.ajax({
                type: 'DELETE',
                url: self.deploymentPath()
            }).done(function(json) {
                pager.navigate('/');
            }).fail(function() {
                console.log("Failed deleting deployment");
            });
        };
        
        self.get = function(callback) {
            $.getJSON(self.deploymentPath(), function (data) {
                if (data) {
                    self.environment(data.environment);
                    self.imageTag(data.image_tag);
                    self.appName(data.app_name);
                    self.hosts(data.hosts);
                    self.id(data.id);
                    
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
                    callback(self);
                } else {
                    console.log("no deployment");
                    callback(self);
                }
            });
        };
                
        self.create = function() {
            data = {
                'deployment': self.serialize()
            };
            $.ajax({
                type: 'POST',
                data: ko.toJSON(data),
                url: self.apiPath(),
                contentType: 'application/json'
            }).done(function(json) {
                pager.navigate('#deployments/all');
            }).fail(function(json) {
                console.log("Failed creating deployment");
                $('.alert').removeClass('hidden');
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
