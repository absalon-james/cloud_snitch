angular.module('cloudSnitch').factory('typesService', ['cloudSnitchApi', function(cloudSnitchApi) {

    var service = {};
    service.types = [];
    service.typeMap = {};
    service.typesLoading = true;
    service.paths = {};
    service.pathsLoading = true;
    service.properties = {};

    service.glanceViews = {
        AptPackage: ['name', 'version'],
        Configfile: ['path'],
        Device: ['name'],
        Environment: ['account_number', 'name'],
        GitRemote: ['name'],
        GitRepo: ['path'],
        GitUntrackedFile: ['path'],
        GitUrl: ['url'],
        Host: ['hostname'],
        Interface: ['device'],
        Mount: ['mount'],
        NameServer: ['ip'],
        Partition: ['name'],
        PythonPackage: ['name', 'version'],
        Uservar: ['name', 'value'],
        Virtualenv: ['path'],
    }

    service.diffLabelView = {
        AptPackage: 'name',
        ConfigFile: 'name',
        Device: 'name',
        Environment: 'name',
        GitRemote: 'name',
        GitRepo: 'path',
        GitUntrackedFile: 'path',
        GitUrl: 'url',
        Host: 'hostname',
        Interface: 'device',
        Mount: 'mount',
        NameServer: 'ip',
        Partition: 'name',
        PythonPackage: 'name',
        Uservar: 'name',
        Virtualenv: 'path'
    };

    service.glanceProperties = function(label) {
        return service.glanceViews[label];
    };

    service.updateProperties = function() {
        service.properties = {};
        for (var i = 0; i < service.types.length; i++) {
            var props = [];
            var t = service.types[i];
            props.push(t.identity);
            for (var j = 0; j < t.static_properties.length; j++) {
                props.push(t.static_properties[j]);
            }
            for (var j = 0; j < t.state_properties.length; j++) {
                props.push(t.state_properties[j]);
            }
            service.properties[t.label] = props;
        }
    };

    service.updatePaths = function() {
        cloudSnitchApi.paths().then(function(result) {
            service.paths = result;
            service.pathsLoading = false;
        }, function(error) {
            // @TODO - Do something with errors.
            service.paths = {};
        });
    }

    service.updateTypes = function() {
        service.typeMap = {};
        cloudSnitchApi.types().then(function(result) {
            service.types = result;
            service.updateProperties();
            service.typesLoading = false;
            for (var i = 0; i < service.types.length; i++) {
                service.typeMap[service.types[i].label] = service.types[i];
            }
        }, function(error) {
            // @TODO - Do something with error
            service.types = [];
        });
    }

    service.path = function(label) {
        var p = [];
        var path = service.paths[label];
        for (var i = 0; i < path.length; i++) {
            p.push(path[i]);
        }
        p.push(label);
        return p;
    };

    service.identityProperty = function(label) {
        var prop = undefined;
        var type = service.typeMap[label];
        if (type !== undefined) {
            prop = type.identity;
        }
        return prop;
    };

    service.update = function() {
        service.updateTypes();
        service.updatePaths();
    };

    service.isLoading = function() {
        return service.typesLoading || service.pathsLoading;
    };

    service.update()
    return service;
}]);
