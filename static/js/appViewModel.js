define([
    'jquery',
    'knockout',
    'pager',
    'fuelux'
], function ($, ko, pager, fuelux) {
    $(function () {
        function AppViewModel() {
            var self = this;

            self.hostsPath = '../mamabear/v1/host';
            self.appsPath = '../mamabear/v1/app';
            
            self.hosts = function(options, callback) {
                var offset = (options.pageIndex)*options.pageSize;
                var urlParams = {
                    hostname: options.search
                };
                $.ajax({
                    type: 'GET',
                    data: urlParams,
                    url: self.hostsPath
                }).done(function(json) {
                    callback({
                        items: json.hits,
                        count: json.total,
                        start: offset + 1,
                        end: offset + json.hits.length,
                        pages: Math.ceil(json.total/options.pageSize),
                        page: options.pageIndex,
                        columns: [
                            {property: 'hostname', label: 'Host', sortable: true},
                            {property: 'port', label: 'Port', sortable: false}
                        ]
                    });
                }).fail(function() {
                    console.log("Failed fetching hosts");
                });
            };

            self.apps = function(options, callback) {
                var offset = (options.pageIndex)*options.pageSize;
                var urlParams = {
                    name: options.search
                };
                $.ajax({
                    type: 'GET',
                    data: urlParams,
                    url: self.appsPath
                }).done(function(json) {
                    callback({
                        items: json.hits,
                        count: json.total,
                        start: offset + 1,
                        end: offset + json.hits.length,
                        pages: Math.ceil(json.total/options.pageSize),
                        page: options.pageIndex,
                        columns: [
                            {property: 'name', label: 'App Name', sortable: true},
                            {property: 'image_count', label: 'Total Images', sortable: true},
                            {property: 'container_count', label: 'Running Containers', sortable: true}
                        ]
                    });
                }).fail(function() {
                    console.log("Failed fetching apps");
                });
            };

            self.deployments = function(options, callback) {
                // FIXME - need api endpoint for list all deployments
                callback({
                    items: [
                        {'image_tag':'1','app_name':'sagebear','environment':'prod'},
                        {'image_tag':'2','app_name':'sagebear','environment':'test'},
                        {'image_tag':'34','app_name':'carebear','environment':'test'}
                    ],
                    count: 3,
                    start: 1,
                    end: 4,
                    pages: 1,
                    page: options.pageIndex,
                    columns: [
                        {property: 'app_name', label: 'App Name', sortable: true},
                        {property: 'image_tag', label: 'Image Tag', sortable: true},                        
                        {property: 'environment', label: 'Environment', sortable: true}
                    ]
                });
            };

            self.bindHostsRepeater = function () {
                $('#hosts_table').repeater({ dataSource: viewModel.hosts });
            };

            self.bindAppsRepeater = function () {
                $('#apps_table').repeater({ dataSource: viewModel.apps });
            }

            self.bindDeploymentsRepeater = function () {
                $('#deployments_table').repeater({ dataSource: viewModel.deployments });
            }
        }

        viewModel = new AppViewModel();
        pager.extendWithPage(viewModel);
        ko.applyBindings(viewModel);
        pager.start('deployments');        
    });
});
