/**
 * Directive for validating date time for use with the time service.
 */
angular.module('cloudSnitch').directive('dateTime', function() {
    var format = 'YYYY-MM-DD HH:mm:ss';
    return {
        require: 'ngModel',
        link: function(scope, elm, attrs, ctrl) {
            ctrl.$validators.dateTime = function(modelValue, viewValue) {
                return moment(viewValue, format).isValid();
            };
        }
    }
});

