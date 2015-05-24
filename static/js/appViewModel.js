define([
    'jquery',
    'knockout',
    'pager'
], function ($, ko, pager) {
    $(function () {
        function AppViewModel() {
            var self = this;
        }

        viewModel = new AppViewModel();
        pager.extendWithPage(viewModel);
        ko.applyBindings(viewModel);
        pager.start('deployments');
    });
});
