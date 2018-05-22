// Truncates strings for use in breadcrumbs

angular.module('cloudSnitch').filter('truncate', function() {
	return function(input_string, maxchars=16, omission="...") {
		if (input_string.length > maxchars) {
			output = input_string.substr(0,8) + omission + input_string.substr(-8,8)
		} else {
			output = input_string;
		}
		return output;
	}
});