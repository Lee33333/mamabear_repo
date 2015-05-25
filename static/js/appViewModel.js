define([
    'jquery',
    'knockout',
    'pager',
    'datatables'
], function ($, ko, pager, datatables) {
    $(function () {
        function AppViewModel() {
            var self = this;
            self.hostsPath = '../mamabear/v1/host';
            self.appsPath = '../mamabear/v1/app';

            self.bindDeployments = function(page) {
                $('#deployments_table').DataTable();
            }

            self.bindHosts = function(page) {
                $('#hosts_table').DataTable({
                    'ajax':  function(data, callback, settings) {
                        $.ajax({
                            type: 'GET',
                            data: data,
                            url: self.hostsPath
                        }).done(function(json) {
                            // FIXME - map data, don't duplicate hits
                            json.data = json.hits
                            callback(json);
                        }).fail(function() {
                            console.log("Failed gettings hosts");
                        })
                    },                    
                    'columns': [
                        {'data': 'hostname'},
                        {'data': 'port'}
                    ]
                });
            }

            self.bindApps = function(page) {
                $('#apps_table').DataTable({
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
                    ]
                });
            }
        }

        viewModel = new AppViewModel();
        pager.extendWithPage(viewModel);
        ko.applyBindings(viewModel);
        pager.start('deployments');
        
    });
});
