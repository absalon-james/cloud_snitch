angular.module('cloudSnitch').factory('csrfService', [function() {
    var service = {};
    var name = '_cloud_snitch_csrf_cookie_';
    var cookieValue = null;

    service.getCookie = function() {
        if (cookieValue === null) {
            if (document.cookie && document.cookie !== '') {
                var cookies = document.cookie.split(';');
                for (var i = 0; i < cookies.length; i++) {
                    var cookie = jQuery.trim(cookies[i]);
                    // Does this cookie string begin with the name we want?
                    if (cookie.substring(0, name.length + 1) === (name + '=')) {
                        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                        break;
                    }
                }
            }
        }
        return cookieValue;
    };

    return service;
}]);

angular.module('cloudSnitch').factory('cloudSnitchApi', ['$http', '$q', 'timeService', 'csrfService', function($http, $q, timeService, csrfService) {

    var typesDeferred = $q.defer();
    var service = {};

    function convertTime(str) {
        var t = timeService.fromstr(str);
        t = timeService.milliseconds(t);
        return t
    }

    function makeHeaders() {
        var headers = {
            'Content-Type': 'application/json',
            'Accept-Type': 'application/json',
            'X-CSRFToken': csrfService.getCookie()
        }
        return headers;
    }

    service.types = function() {
        return $http({
            method: 'GET',
            url: '/api/models'
        }).then(function(resp) {
            // Success
            typesDeferred.resolve(resp.data);
            return typesDeferred.promise;
        }, function(resp) {
            // Error
            typesDeferred.reject(resp);
            return typesDeferred.promise;
        });
    };

    service.paths = function() {
        var defer = $q.defer();
        return $http({
            method: 'GET',
            url: '/api/paths'
        }).then(function(resp) {
            // Success
            defer.resolve(resp.data);
            return defer.promise;
        }, function(resp) {
            // Error
            defer.reject(resp);
            return defer.promise;
        });
    };

    service.times = function(model, identity, time) {
        var defer = $q.defer();
        var req = {
            model: model,
            identity: identity
        };

        if (time !== undefined) {
            time = convertTime(time);
            if (time > 0) {
                req.time = time;
            }
        }
        return $http({
            method: 'POST',
            url: '/api/objects/times/',
            headers: makeHeaders(),
            data: req
        }).then(function(resp) {
            defer.resolve(resp.data);
            return defer.promise;
        }, function(resp) {
            // Error @TODO Error handling
            defer.reject(resp);
            return defer.promise;
        });
    };

    /**
     * Params object:
       model: name of the model
       identity: id of the object
       time: time of the search
       filters: list of search filters
       count: How many items to return
       index: index of the first item
       orders: list of order by objects
     */
    service.searchSome = function(params) {
        var defer = $q.defer();
        var req = {
            model: params.model,
            pagesize: params.count,
        };

        // Check index
        if (!angular.isDefined(params.index)) {
            params.index = 1;
        }
        req.index = params.index;

        // Check identity
        if (angular.isDefined(params.identity) && params.identity != "") {
            req.identity = params.identity;
        }

        // Check time
        if (angular.isDefined(params.time)) {
            // Convert string time to timestamp
            var time = convertTime(params.time);
            if (time > 0) {
                req.time = time;
            }
        }

        // Filters
        if (angular.isDefined(params.filters)) {
            var apiFilters = [];
            angular.forEach(params.filters, function(item) {
                apiFilters.push({
                    model: item.model,
                    prop: item.property,
                    operator: item.operator,
                    value: item.value
                });
            });
            req.filters = apiFilters;
        }

        // Orders
        if (angular.isDefined(params.orders)) {
            var orders = [];
            angular.forEach(params.orders, function(item) {
                orders.push({
                    model: item.model,
                    prop: item.property,
                    direction: item.direction
                })
            });
            req.orders = orders;
        }

        return $http({
            method: 'POST',
            url: '/api/objects/search/',
            data: req,
            headers: makeHeaders(),
            }).then(function(resp) {
                defer.resolve(resp.data);
                return defer.promise;
            }, function(resp) {
                // @TODO - handle errors
                defer.reject(resp);
                return defer.promise;
        });
    };

    service.searchAll = function(model, identity, time, filters, sink) {

        var defer = $q.defer();
        var req = {
            model: model,
            page: 1,
            pagesize: 500
        };

        if (identity !== undefined && identity != "") {
            req.identity = identity;
        }

        if (time !== undefined) {
            // Convert string time to timestamp
            time = convertTime(time);
            if (time > 0) {
                req.time = time;
            }
        }

        if (filters !== undefined) {
            var apiFilters = [];
            angular.forEach(filters, function(item) {
                apiFilters.push({
                    model: item.model,
                    prop: item.property,
                    operator: item.operator,
                    value: item.value
                });
            });
            req.filters = apiFilters;
        }

        function more(page) {
            req.page = page
            return $http({
                method: 'POST',
                headers: makeHeaders(),
                url: '/api/objects/search/',
                data: req
            }).then(function(resp) {
                sink(resp.data);
                if (req.page * req.pagesize >= resp.data.count) {
                    defer.resolve({});
                    return defer.promise
                }
                else {
                    return more(page + 1);
                }
            }, function(resp) {
                // @TODO - handle errors
                defer.reject(resp);
                return defer.promise;
            });
        }

        return more(1);
    };



    service.searchAll = function(model, identity, time, filters, sink) {

        var defer = $q.defer();
        var req = {
            model: model,
            page: 1,
            pagesize: 500
        };

        if (identity !== undefined && identity != "") {
            req.identity = identity;
        }

        if (time !== undefined) {
            // Convert string time to timestamp
            time = convertTime(time);
            if (time > 0) {
                req.time = time;
            }
        }

        if (filters !== undefined) {
            var apiFilters = [];
            angular.forEach(filters, function(item) {
                apiFilters.push({
                    model: item.model,
                    prop: item.property,
                    operator: item.operator,
                    value: item.value
                });
            });
            req.filters = apiFilters;
        }

        function more(page) {
            req.page = page
            return $http({
                method: 'POST',
                headers: makeHeaders(),
                url: '/api/objects/search/',
                data: req
            }).then(function(resp) {
                sink(resp.data);
                if (req.page * req.pagesize >= resp.data.count) {
                    defer.resolve({});
                    return defer.promise
                }
                else {
                    return more(page + 1);
                }
            }, function(resp) {
                // @TODO - handle errors
                defer.reject(resp);
                return defer.promise;
            });
        }

        return more(1);
    };

    service.diffStructure = function(model, identity, leftTime, rightTime) {
        var req = {
            model: model,
            identity:identity,
            left_time: convertTime(leftTime),
            right_time: convertTime(rightTime)
        };
        var defer = $q.defer()
        return $http({
            method: 'POST',
            headers: makeHeaders(),
            url: '/api/objectdiffs/structure/',
            data: req
        }).then(function(resp) {
            // Success
            defer.resolve(resp.data);
            return defer.promise;
        }, function(resp) {
            // Error
            defer.reject(resp);
            return defer.promise;
        });
    };

    service.diffNodes = function(model, identity, leftTime, rightTime, offset, limit) {
        var req = {
            model: model,
            identity:identity,
            left_time: convertTime(leftTime),
            right_time: convertTime(rightTime),
            offset: offset,
            limit: limit
        };
        var defer = $q.defer()
        return $http({
            method: 'POST',
            headers: makeHeaders(),
            url: '/api/objectdiffs/nodes/',
            data: req
        }).then(function(resp) {
            // Success
            defer.resolve(resp.data);
            return defer.promise;
        }, function(resp) {
            // Error
            defer.reject(resp);
            return defer.promise;
        });
    };

    return service;
}]);
