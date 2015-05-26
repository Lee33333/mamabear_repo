define([
    'jquery',
    'knockout',
    'pager',
    'datatables',
    'app',
    'deployment',
    'host'
], function ($, ko, pager, datatables, App, Deployment, Host) {
    $(function () {
        function AppViewModel() {
            var self = this;
            self.hostsPath = '../mamabear/v1/host';
            self.appsPath = '../mamabear/v1/app';
            self.deploymentsPath = '../mamabear/v1/deployment';

            self.app = ko.observable(new App());
            self.deployment = ko.observable(new Deployment());
            self.host = ko.observable(new Host());
            
            self.appsList = ko.observableArray([]);
            self.hostsList = ko.observableArray([]);
            self.hostTable = ko.observable();
            self.appsTable = ko.observable();
            self.deploymentsTable = ko.observable();
            
            
            self.getApp = function(page) {
                var a = new App();
                a.name(page.page.id());
                self.app(a);
                a.get(function(app) {
                });
            };

            self.updateLists = function() {
                self.updateAppsList();
                self.updateHostsList();
            };
            
            self.updateAppsList = function() {
                $.getJSON(self.appsPath, function(data) {
                    if (data) {
                        self.appsList.removeAll();
                        return $.each(data.hits, function(i, hit) {
                            self.appsList.push(hit.name);
                        });
                    } else {
                        console.log("Error listing apps");
                    }
                });
            };

            self.updateHostsList = function() {
                $.getJSON(self.hostsPath, function(data) {
                    if (data) {
                        self.hostsList.removeAll();
                        return $.each(data.hits, function(i, hit) {
                            self.hostsList.push(hit.hostname);
                        });
                    } else {
                        console.log("Error listing hosts");
                    }
                });
            };
            
            self.getDeployment = function(page) {
                // deployments/<app>/<image_tag>/<environment>
                var appName = page.page.id();
                var imageTag = page.page.route[0];
                var environment = page.page.route[1];
                var a = new App();
                a.name(appName);
                self.app(a);
                a.get(function(app) {
                    var d = $.grep(app.deployments(), function(deployment) {
                        return (deployment.imageTag() === imageTag && deployment.environment() === environment);
                    });
                    if (d.length > 0) {
                        self.deployment(d[0]);
                    }
                });                
            };
            
            self.getHost = function(page) {
                h = new Host();
                h.hostname(page.page.id());
                self.host(h);
                h.get(function(host) {
                });
            };

            // FIXME - serverside
            self.bindDeployments = function(page) {
                self.deploymentsTable($('#deployments_table').DataTable({
                    'ajax': function(data, callback, settings) {
                        $.ajax({
                            type: 'GET',
                            data: data,
                            url: self.deploymentsPath
                        }).done(function(json) {
                            data = $.map(json.hits, function(row, i) {
                                row.deployment = row.app_name+':'+row.image_tag+'/'+row.environment;
                                return row;
                            });
                            callback({'data':data});
                        }).fail(function() {
                            console.log("Failed getting deployments");
                        })
                    },
                    'columns': [
                        {'data': 'deployment'},
                        {'data': 'app_name'},
                        {'data': 'image_tag'},
                        {'data': 'environment'},
                        {'data': 'status_endpoint'}
                    ],
                    'columnDefs': [
                        {
                            'targets':0, 'render': function(data,type,row) {
                                return '<a href="#deployments/'+row.app_name+'/'+row.image_tag+'/'+row.environment+'">'+data+'</a>';
                            }
                        },
                        {'targets':1, 'render': function(data,type,row) {return '<a href="#apps/'+data+'">'+data+'</a>';}}
                    ]
                }));
            }

            self.redrawHostTable = function(page) {
                self.hostTable().draw();
            }

            self.redrawAppsTable = function(page) {
                self.appsTable().draw();
            }

            self.redrawDeploymentsTable = function(page) {
                self.deploymentsTable().draw();
            }
            
            self.bindHosts = function(page) {
                self.hostTable($('#hosts_table').DataTable({
                    'processing': true,
                    'serverSide': true,
                    'ajax':  function(data, callback, settings) {
                        params = {}
                        if (data.search && data.search.value !== '') {
                            params['hostname'] = data.search.value;
                        }
                        $.ajax({
                            type: 'GET',
                            data: params,
                            url: self.hostsPath
                        }).done(function(json) {
                            callback({'data': json.hits});
                        }).fail(function() {
                            console.log("Failed gettings hosts");
                        })
                    },                    
                    'columns': [
                        {'data': 'hostname'},
                        {'data': 'port'},
                        {'data': 'container_count'}
                    ],
                    'columnDefs': [
                        {'targets':0, 'render': function(data,type,row) {return '<a href="#hosts/'+data+'">'+data+'</a>';}}
                    ]
                }));
            }

            // FIXME - serverside
            self.bindApps = function(page) {
                self.appsTable($('#apps_table').DataTable({
                    'ajax':  function(data, callback, settings) {
                        $.ajax({
                            type: 'GET',
                            data: data,
                            url: self.appsPath
                        }).done(function(json) {
                            // FIXME - map data, don't duplicate hits
                            json.data = json.hits
                            callback(json);
                        }).fail(function() {
                            console.log("Failed gettings apps");
                        })
                    },                    
                    'columns': [
                        {'data': 'name'},
                        {'data': 'image_count'},
                        {'data': 'container_count'}
                    ],
                    'columnDefs': [
                        {'targets':0, 'render': function(data,type,row) {return '<a href="#apps/'+data+'">'+data+'</a>';}}
                    ]
                }));                
            }
        }

        viewModel = new AppViewModel();
        pager.extendWithPage(viewModel);
        ko.applyBindings(viewModel);
        pager.start('deployments/all');        
    });
});
