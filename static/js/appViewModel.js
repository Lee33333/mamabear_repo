define([
    'jquery',
    'knockout',
    'knockoutamdhelpers',
    'pager',
    'datatables',
    'select2',
    'app',
    'deployment',
    'host'
], function ($, ko, knockoutamdhelpers, pager, datatables, select2, App, Deployment, Host) {
    $(function () {
        function AppViewModel() {
            var self = this;
            self.hostsPath = '../mamabear/v1/host';
            self.appsPath = '../mamabear/v1/app';
            self.imagesPath = '../mamabear/v1/image';
            self.deploymentsPath = '../mamabear/v1/deployment';

            self.app = ko.observable(new App());
            self.deployment = ko.observable(new Deployment());
            self.host = ko.observable(new Host());
            self.page = ko.observable();
            
            self.hostTable = ko.observable();
            self.appsTable = ko.observable();
            self.deploymentsTable = ko.observable();
                                    
            self.bindSelects = function(page) {
                var appBindArgs = {
                    ajax: {
                        url: self.appsPath,
                        dataType: 'json',
                        delay: 250,
                        processResults: function(data, pg) {
                            return {
                                results: $.map(data.hits, function(hit, i) {
                                    return {'text': hit.name, 'id': hit.name};
                                })
                            }
                        }
                    },
                    minimumInputLength: 0
                };
                
                var hostBindArgs = {
                    ajax: {
                        url: self.hostsPath,
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

                // var parentBindArgs = {
                //     ajax:{
                //         url. self.????,
                //         dataType: 'json',
                //         delay: 250,
                //         data: function(params)
                //         {   

                //         };
                //     }
                //     minimumInputLength: 1
                // };
                
                var imageBindArgs = {
                    ajax: {
                        url: self.imagesPath,
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
                                    return {'text': hit.app_name+':'+hit.tag, 'id': hit.id};
                                })
                            };
                        }
                    },
                    minimumInputLength: 1
                };
                $('#inputAppName').select2(appBindArgs);
                $('#inputAppName').on('select2:select', function(e) {
                    self.deployment().appName(e.params.data.text);
                });
                $('#inputHosts').select2(hostBindArgs);
                $('#inputHosts').on('select2:select', function(e) {
                    self.deployment().hosts.push({
                        'hostname': e.params.data.id,
                        'alias': e.params.data.text
                    });
                });
                $('#inputAppLinks').select2(imageBindArgs);
                $('#inputAppLinks').on('select2:select', function(e) {
                    self.deployment().links.push(e.params.data.text);
                });
                $('#inputAppVolumes').select2(imageBindArgs);
                $('#inputAppVolumes').on('select2:select', function(e) {
                    self.deployment().volumes.push(e.params.data.text);
                });
            //     $('#inputParent').select2(parentBindArgs);
            //     $('#inputParent').on('select2:select', function(e) {
            //         self.deployment().parent(e.params.data.id);
            //         var text = e.params.data.text; // appname:imagetag/environment

            //         self.deployment().appName()
            //         // imagetag
            //         // environment
            //         self.deployment().get(function(data) {});

            //     //input parent...
            //     });

            // }
            
            self.setPage = function(page) {
                self.page(page);
            }

            self.reset = function() {
                self.app(new App());
                self.host(new Host());
                self.deployment(new Deployment());
                $('#inputAppName').val(null).trigger("change");
                $('#inputHosts').val(null).trigger("change");
                $('#inputAppLinks').val(null).trigger("change");
                $('#inputAppVolumes').val(null).trigger("change");
            };
            
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
                            var result = $.map(json.hits, function(row, i) {
                                row.deployment = row.app_name+':'+row.image_tag+'/'+row.environment;
                                row.up_containers = 0;
                                row.host_count = 0;
                                $.each(row.containers, function(i, container) {
                                    if (container.status === 'up') {
                                        row.up_containers += 1;
                                    }
                                });
                                $.each(row.hosts, function(i, host) {
                                    row.host_count += 1;
                                });
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
                        {'data': 'up_containers'},
                        {'data': 'host_count'}
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
                            var result = $.map(json.hits, function(row, i) {
                                row.up_containers = 0;
                                $.each(row.containers, function(i, container) {
                                    if (container.status === 'up') {
                                        row.up_containers += 1;
                                    }
                                });
                                return row;
                            });
                            callback({'draw': data.draw, 'data':result, 'recordsTotal': json.total, 'recordsFiltered': json.total});
                        }).fail(function() {
                            console.log("Failed gettings hosts");
                        })
                    },                    
                    'columns': [
                        {'data': 'hostname'},
                        {'data': 'alias'},
                        {'data': 'port'},
                        {'data': 'status'},
                        {'data': 'up_containers'}
                    ],
                    'columnDefs': [
                        {'targets':0, 'render': function(data,type,row) {return '<a href="#hosts/'+data+'">'+data+'</a>';}},
                        {'targets':3, 'render': function(data,type,row) {
                            switch (data) {
                                case 'up':
                                    return '<h4 class="text-success"><strong>'+data+'</strong></h4>';
                                case 'down':
                                    return '<h4 class="text-danger"><strong>'+data+'</strong></h4>';                                
                            };
                        }}
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
                            var result = $.map(json.hits, function(row, i) {
                                row.image_count = 0;
                                $.each(row.images, function(i, image) {
                                    row.image_count += 1;
                                });
                                
                                row.deployment_count = 0;
                                row.up_containers = 0;
                                $.each(row.deployments, function(i, deployment) {
                                    row.deployment_count += 1;
                                    $.each(deployment.containers, function(j, container) {
                                        if (container.status === 'up') {
                                            row.up_containers += 1;
                                        }
                                    });
                                });                                
                                return row;
                            });
                            callback({'draw': data.draw, 'data':result, 'recordsTotal': json.total, 'recordsFiltered': json.total});
                        }).fail(function() {
                            console.log("Failed gettings apps");
                        })
                    },                    
                    'columns': [
                        {'data': 'name'},
                        {'data': 'image_count'},
                        {'data': 'deployment_count'},
                        {'data': 'up_containers'}
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
        pager.start();
    });
});
