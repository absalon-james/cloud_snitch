angular.module('cloudSnitch').factory('timeService', ['$interval', function($interval) {

    var utcOffset;
    var format = "YYYY-MM-DD HH:mm:ss";

    function updateOffset() {
        utcOffset = moment().utcOffset();
    }

    updateOffset();

    $interval(updateOffset, 60 * 1000);


    service = {};
    service.now = function() {
        return moment();
    };

    service.str = function(m) {
        return m.format(format);
    };

    service.fromstr = function(str) {
        return moment(str, format);
    };

    service.utc = function(m) {
        return moment(m.valueOf() - (utcOffset * 60000));
    };

    service.local = function(m) {
        return moment(m.valueOf() + (utcOffset * 60000));
    }

    service.milliseconds = function(m) {
        return m.valueOf();
    };

    service.fromMilliseconds = function(milliseconds) {
        return moment(milliseconds)
    };

    return service;
}]);
