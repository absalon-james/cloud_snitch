/**
 * Controller for the multiple panes.
 */
angular.module('cloudSnitch').controller('PanesController', ['$scope', 'timeService', 'typesService', function($scope, timeService, typesService) {
    $scope.panes = [];
    $scope.numPanes = 0;
    $scope.maxPanes = 2;
    $scope.diff = undefined;

    /**
     * Add a pane
     */
    $scope.addPane = function() {
        if ($scope.numPanes + 1 > $scope.maxPanes) {
            return true;
        }

        $scope.panes.push({
            search: {
                type: 'Environment',
                identity: '',
                time: timeService.str(timeService.now()),
                filters: [],
                properties: [],
            },
            loading: false,
            stack: [{ state: 'search' }],
            deleted: false
        });

        $scope.numPanes++;
    };

    /**
     * Look for pane updates
     */
    $scope.updatePanes = function() {
        for (var i = $scope.panes.length - 1; i >= 0; i--) {
            if ($scope.panes[i].deleted) {
              $scope.panes.splice(i, 1);
              $scope.numPanes--;
            }
        }
    };

    /**
     * Copy a pane
     */
    $scope.copyPane = function(srcPane) {
        if ($scope.panes.length < $scope.maxPanes) {
            $scope.panes.push(angular.copy(srcPane));
            $scope.numPanes++;
        }
    };

    $scope.diffable = function() {
        if ($scope.panes.length == 2) {
            var stackSize = $scope.panes[0].stack.length;
            var a = $scope.panes[0].stack[stackSize - 1];

            stackSize = $scope.panes[1].stack.length;
            var b = $scope.panes[1].stack[stackSize - 1];

            if (a.state != 'details' || b.state != 'details') {
                return false
            }

            if (a.type != b.type) {
                return false
            }

            var aId = a.record[a.type][typesService.identityProperty(a.type)];
            var bId = b.record[b.type][typesService.identityProperty(b.type)];
            if (aId != bId) {
                return false
            }

            return true;
        }
        return false;
    };

    $scope.showDiff = function() {
        var stackSize = $scope.panes[0].stack.length;
        var a = $scope.panes[0].stack[stackSize - 1];

        stackSize = $scope.panes[1].stack.length;
        var b = $scope.panes[1].stack[stackSize - 1];

        $scope.diff = {
            type: a.type,
            id: a.record[a.type][typesService.identityProperty(a.type)],
            leftTime: a.time,
            rightTime: b.time
        }
    };

    $scope.closeDiff = function() {
        $scope.diff = undefined;
    }

    // Start with one pane.
    $scope.addPane();
}]);
