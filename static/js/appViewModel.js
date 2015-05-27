define([
    'jquery',
    'knockout',
    'knockoutamdhelpers',
    'pager',
    'datatables',
    'app',
    'deployment',
    'host'
], function ($, ko, knockoutamdhelpers, pager, datatables, App, Deployment, Host) {
    $(function () {
        function AppViewModel() {
            var self = this;
            self.hostsPath = '../mamabear/v1/host';
            self.appsPath = '../mamabear/v1/app';
            self.deploymentsPath = '../mamabear/v1/deployment';

            self.app = ko.observable(new App());
            self.deployment = ko.observable(new Deployment());
            self.host = ko.observable(new Host());
            self.page = ko.observable();
            
            self.appsList = ko.observableArray([]);
            self.hostsList = ko.observableArray([]);
            self.hostTable = ko.observable();
            self.appsTable = ko.observable();
            self.deploymentsTable = ko.observable();
                        
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

            self.setPage = function(page) {
                self.page(page);
            }
            
            self.getHost = function(page) {
                h = new Host();
                h.hostname(page.page.id());
                self.host(h);
                h.get(function(host) {
                });
            };
            
            self.redrawHostTable = function(page) {
                if (self.hostTable()) {
                    self.hostTable().draw();
                }
            }

            self.redrawAppsTable = function(page) {
                if (self.appsTable()) {
                    self.appsTable().draw();
                }
            }

            self.redrawDeploymentsTable = function(page) {
                if (self.deploymentsTable()) {
                    self.deploymentsTable().draw();
                }
            }
            
            self.bindDeployments = function(page) {
                self.deploymentsTable($('#deployments_table').DataTable({
                    'processing': true,
                    'serverSide': true,
                    'ajax': function(data, callback, settings) {
                        params = {
                            'limit': data.length,
                            'offset': data.start,
                            'order': data.order[0].dir
                        }
                        if (data.search && data.search.value !== '') {
                            params['app_name'] = data.search.value;
                        }                        
                        $.ajax({
                            type: 'GET',
                            data: params,
                            url: self.deploymentsPath
                        }).done(function(json) {
                            result = $.map(json.hits, function(row, i) {
                                row.deployment = row.app_name+':'+row.image_tag+'/'+row.environment;
                                return row;
                            });
                            callback({'draw': data.draw, 'data':result, 'recordsTotal': json.total, 'recordsFiltered': json.total});
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
                            callback({'draw': data.draw, 'data':json.hits, 'recordsTotal': json.total, 'recordsFiltered': json.total});
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

            self.bindApps = function(page) {
                self.appsTable($('#apps_table').DataTable({
                    'processing': true,
                    'serverSide': true,
                    'ajax':  function(data, callback, settings) {
                        params = {};
                        if (data.search && data.search.value !== '') {
                            params['name'] = data.search.value;
                        }
                        $.ajax({
                            type: 'GET',
                            data: params,
                            url: self.appsPath
                        }).done(function(json) {
                            callback({'draw': data.draw, 'data':json.hits, 'recordsTotal': json.total, 'recordsFiltered': json.total});
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

        ko.amdTemplateEngine.defaultPath = "../templates";
        ko.amdTemplateEngine.defaultSuffix = ".html";
        
        viewModel = new AppViewModel();
        pager.extendWithPage(viewModel);
        ko.applyBindings(viewModel);
        pager.start('deployments/all');
    });
});
