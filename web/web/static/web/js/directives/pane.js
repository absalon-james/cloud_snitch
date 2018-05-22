angular.module('cloudSnitch').directive('pane', function() {
    return {
        templateUrl: '/static/web/html/pane.html'
    };
});

angular.module('cloudSnitch').directive('addpanebox', function() {
    return {
        templateUrl: '/static/web/html/addpanebox.html'
    };
});

angular.module('cloudSnitch').directive('panetopctrl', function() {
    return {
          templateUrl: '/static/web/html/panetopctrl.html'
    };
});
