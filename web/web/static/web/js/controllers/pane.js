angular.module('cloudSnitch').controller('ResultsController', ['$scope', 'cloudSnitchApi', 'typesService', function($scope, cloudSnitchApi, typesService) {

    function dataPath() {
        var path = $scope.frame().path;
        if (path === undefined) {
            return [];
        }

        // moves last item to front of path (makes top-level first column)
        var sortedPath = path.slice(0)
        sortedPath.pop(sortedPath.unshift(sortedPath[sortedPath.length-1])-1)
        return sortedPath;
    }

    function recordColumns() {
        var columns = [];
        angular.forEach($scope.dataPath, function(model) {
            var props = typesService.glanceProperties(model);
            angular.forEach(props, function(prop) {
                columns.push({
                    model: model,
                    property: prop
                });
            });
        });
        return columns;
    }

    function recordHeaders() {
        var headers = [];

        angular.forEach($scope.dataPath, function(item) {
            var props = typesService.glanceProperties(item);
            for (var i = 0; i < props.length; i++) {
                var header = item + '.' + props[i];
                header = header.replace('.', ' ').replace('_', '' ).replace('-', '');
                headers.push(header);
            }
        });

        return headers;
    }

    function recordTable(records) {
        var rows = [];
        angular.forEach(records, function(record) {
            var row = [];
            angular.forEach($scope.dataPath, function(label) {
                var props = typesService.glanceProperties(label);
                for (var i = 0; i < props.length; i++) {
                    row.push(record[label][props[i]]);
                }
            });
            rows.push(row);
        });
        return rows;
    }


    $scope.busy = false;

    $scope.f = $scope.frame();

    if (!angular.isDefined($scope.f.ctx)) {
        $scope.f.ctx = {
            page: 1,
            pagesize: 15,
            sortColumnIndex: -1,
            sortDirection: 'asc'
        }
    }
    $scope.records = [];
    $scope.rows = [];
    $scope.count = 0;
    $scope.dataPath = dataPath();
    $scope.headers = recordHeaders();
    var columns = recordColumns();

    $scope.searchPage = function() {
        $scope.busy = true;
        var params = {
            model: $scope.paneObj.search.type,
            identity: $scope.paneObj.search.identity,
            time: $scope.paneObj.search.time,
            filters: $scope.paneObj.search.filters,
            index: ($scope.f.ctx.page - 1) * $scope.f.ctx.pagesize,
            count: $scope.f.ctx.pagesize
        }

        if ($scope.f.ctx.sortColumnIndex >= 0) {
            var sortIndex = $scope.f.ctx.sortColumnIndex;
            params.orders = [{
                model: columns[sortIndex].model,
                property: columns[sortIndex].property,
                direction: $scope.f.ctx.sortDirection
            }]
        }

        cloudSnitchApi.searchSome(params).then(function(data) {
            $scope.records = data.records;
            $scope.rows = recordTable(data.records);
            $scope.count = data.count;
            $scope.busy = false;
        }, function(resp) {
            console.log("error searching page.");
            $scope.busy = false;
        });
    };

    $scope.pageChange = function(newPage) {
        $scope.f.ctx.page = newPage;
        $scope.searchPage();
    };

    $scope.rowClick = function(index) {
        var record = $scope.records[index];
        $scope.details($scope.paneObj.search.type, record);
    }

    $scope.sortChange = function(index) {
        var newDirection;
        var oldIndex = $scope.f.ctx.sortColumnIndex;
        var oldDirection = $scope.f.ctx.sortDirection;

        if (oldIndex == index) {
            newDirection = (oldDirection == 'asc') ? 'desc' : 'asc';
        } else {
            newDirection = 'asc';
            $scope.f.ctx.page = 1;
        }

        $scope.f.ctx.sortColumnIndex = index;
        $scope.f.ctx.sortDirection = newDirection;
        $scope.searchPage();
    };

    $scope.searchPage();

}]);

/**
 * The pane controller covers searching.
 */
angular.module('cloudSnitch').controller('PaneController', ['$scope', 'cloudSnitchApi', 'typesService', function($scope, cloudSnitchApi, typesService) {

    $scope.paneObj = {};
    $scope.typesService = typesService;

    $scope.pagesize = 20;

    /**
     * Initialize the pane with a pane object from the parent controller.
     */
    $scope.init = function(paneObj) {
        $scope.paneObj = paneObj;
        $scope.updatePath();
    };

    $scope.frame = function() {
        var stackSize = $scope.paneObj.stack.length;
        return $scope.paneObj.stack[stackSize - 1];
    };

    /**
     * Create a default filter.
     */
    $scope.defaultFilter = function() {
        return {
            model: $scope.paneObj.search.type,
            property: null,
            operator: '=',
            value: null
        }
    };

    /**
     * Add another filter
     */
    $scope.addFilter = function() {
        $scope.paneObj.search.filters.push($scope.defaultFilter());
    };

    /**
     * Remove filter
     */
    $scope.removeFilter = function(filter) {
        var index = $scope.paneObj.search.filters.indexOf(filter)
        $scope.paneObj.search.filters.splice(index, 1);
    };

    $scope.updatePath = function() {
        $scope.path = typesService.path($scope.paneObj.search.type);
    };

    /**
     *
     */
    $scope.search = function() {
        var path = typesService.path($scope.paneObj.search.type);
        $scope.paneObj.stack.push({
            state: 'results',
            results: [],
            path: path
        });
    };

    $scope.details = function(type, record) {
        $scope.paneObj.stack.push({
            state: 'details',
            record: record,
            type: type,
            pager: {
                page: 1,
                sort: undefined,
                order: undefined,
            }
        });
        $scope.paneObj.loading = false;
    };

    $scope.identity = function($index) {
        var frame = $scope.paneObj.stack[$index];
        if (frame.state != 'details') {
            return undefined;
        }
        return frame.record[frame.type][typesService.identityProperty(frame.type)];
    };

    $scope.frameJump = function($index) {
        if ($index < $scope.paneObj.stack.length) {
            var numSplice = $scope.paneObj.stack.length - ($index + 1);
            $scope.paneObj.stack.splice($index + 1, numSplice);
        }
    };

    /**
     * Mark pane as deleted. The parent controller will remove it.
     */
    $scope.close = function() {
        $scope.paneObj.deleted = true;
        $scope.updatePanes();
    };

    $scope.back = function() {
        if ($scope.paneObj.stack.length > 1) {
            $scope.paneObj.stack.splice(-1, 1);
        }
    };
}]);
