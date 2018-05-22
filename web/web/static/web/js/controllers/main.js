/**
 * Main controller. Holds various app wide things.
 */
angular.module('cloudSnitch').controller('MainController', ['$scope', 'typesService', function($scope, typesService) {
    $scope.types = [];
    $scope.typesService = typesService;
    $scope.ready = false;

    $scope.$watch('typesService.isLoading()', function(isLoading) {
        if (!isLoading) {
            $scope.ready = true;
        }
    });

    // @TODO - Retrieve available operators from api
    $scope.operators = [
        '=',
        '<',
        '<=',
        '>',
        '>=',
        '<>',
        'CONTAINS',
        'STARTS WITH',
        'ENDS WITH'
    ];
}]);
