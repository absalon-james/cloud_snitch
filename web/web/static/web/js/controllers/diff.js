/**
 * The details controller covers displaying object details.
 */
angular.module('cloudSnitch').controller('DiffController', ['$scope', '$interval', '$window', 'cloudSnitchApi', 'typesService', 'timeService', function($scope, $interval, $window, cloudSnitchApi, typesService, timeService) {

    $scope.frame = undefined;
    $scope.nodeMap = undefined;
    $scope.nodes = undefined;
    $scope.nodeCount = 0;
    $scope.state = 'loadingStructure';

    $scope.detailNode = undefined;
    $scope.detailNodeType = undefined;
    $scope.detailNodeId = undefined;

    var pollStructure;
    var pollNodes;

    var pollInterval = 3000;
    var nodePageSize = 500;
    var nodeOffset = 0;

    var margin = {
        top: 20,
        bottom: 20,
        right: 250,
        left: 250
    }

    var tree;
    var root;

    var nodeRadius = 10;

    var svg = undefined;
    var g = undefined;

    /**
     * Stop controller from polling for structure.
     */
    function stopPolling() {
        if (angular.isDefined(pollStructure)) {
            $interval.cancel(pollStructure);
            pollStructure = undefined;
        }
    };

    /**
     * Stop controller for polling for nodes.
     */
    function stopPollingNodes() {
        if (angular.isDefined(pollNodes)) {
            $interval.cancel(pollNodes);
            pollNodes = undefined;
        }
    }

    /**
     * Comparison function for sorting siblings in diff tree.
     */
    function siblingCompare(a, b) {
        var d = a.data.model.localeCompare(b.data.model);
        if (d == 0) {
            d = a.data.id.localeCompare(b.data.id);
        }
        return d;
    }

    /**
     * Compute label of a node.
     */
    function label(d) {
        var index = $scope.nodeMap[d.data.model][d.data.id];
        var node = $scope.nodes[index];
        var label = d.data.model + ": ";
        var labelProp = typesService.diffLabelView[d.data.model];
        if (node && angular.isDefined(labelProp))
            label += nodeProp(node, labelProp);
        else
            label += d.data.id;
        return label;
    }

    /**
     * Compute size of svg and the tree.
     */
    function sizeTree() {
        var p = svg.select(function() {
            return this.parentNode;
        });
        svg.attr('width', 1);
        svg.attr('height', 1);

        var pNode = p.node();
        var rect = pNode.getBoundingClientRect();
        var style = window.getComputedStyle(pNode);
        var paddingLeft = parseInt(style.getPropertyValue('padding-left'));
        var paddingRight = parseInt(style.getPropertyValue('padding-right'));
        var paddingTop = parseInt(style.getPropertyValue('padding-top'));
        var paddingBottom = parseInt(style.getPropertyValue('padding-bottom'));

        var svgHeight = rect.height - paddingTop - paddingBottom;
        var svgWidth = rect.width - paddingLeft - paddingRight;
        svg.attr('height', svgHeight);
        svg.attr('width', svgWidth);

        var sizeX = svgWidth - margin.right - margin.left;
        var sizeY = svgHeight - margin.bottom - margin.top;
        return {x: sizeX, y: sizeY};
    }

    /**
     * Offset the tree containing "g" element by margin.
     */
    function translateTree() {
        g.attr('transform', 'translate(' + margin.left + ',' + margin.top + ')');
    }

    /**
     * Render the tree.
     */
    function render() {
        // Get the svg element
        if (!angular.isDefined(svg)) { svg = d3.select('svg#diff'); }

        // Make a svg g element if not defined.
        if (!angular.isDefined(g)) { g = svg.append('g'); }
        g.html('');

        // Start the tree
        tree = d3.tree();

        // Calculate size svg should be.
        // Calcule size tree should be including margin.
        s = sizeTree();
        tree.size([s.y, s.x]);

        // Offset tree for margin
        translateTree();

        // Make the data heirarchy
        if (!angular.isDefined(root)) {
            root = d3.hierarchy($scope.frame);
            root.sort(siblingCompare);
        }

        // Pass heirarchy to tree
        tree(root);

        var link = g.selectAll(".link")
            .data(tree(root).links())
            .enter().append('path')
                .attr('class', 'link')
                .attr('d', d3.linkHorizontal().x(function(d) { return d.y; }).y(function(d) { return d.x; }));

        var node = g.selectAll(".node")
            .data(root.descendants())
            .enter().append("g")
                .attr("class", function(d) {
                    var classes = 'node';
                    if (d.children)
                        classes += ' node--internal';
                    else
                        classes += ' node--leaf';

                    switch (d.data.side) {
                        case 'left':
                            classes += ' removed';
                            break;
                        case 'right':
                            classes += ' added';
                            break;
                        default:
                            classes += ' unchanged';
                            break;
                    }
                    return classes;
                })
                .attr("transform", function(d) {
                    return "translate(" + d.y + "," + d.x + ")";
                });

        node.on('click', nodeClickHandler);

        node.append("circle")
            .attr("r", nodeRadius)
            .attr("fill", function(d) {
                var fill = 'url(';
                switch (d.data.side) {
                    case 'left':
                        fill += '#removedGradient';
                        break;
                    case 'right':
                        fill += '#addedGradient';
                        break;
                    default:
                        fill += '#unchangedGradient';
                }
                fill += ')';
                return fill;
            });
        node.append("text")
            .attr("dy", 3)
            .attr("x", function(d) { return d.children ? -15: 15})
            .style("text-anchor", function(d) { return d.children ? "end": "start"; })
            .text(label);
    }

    function nodeProp(node, prop) {
        if (angular.isDefined(node.both[prop])) { return node.both[prop]; }
        if (angular.isDefined(node.right[prop])) { return node.right[prop]; }
        if (angular.isDefined(node.left[prop])) { return node.left[prop]; }
        return "";
    }

    function updateLabels() {
        if (!angular.isDefined(tree) || !angular.isDefined(root)) { return; }

        var node = g.selectAll(".node")
        node.selectAll("text").text(label);
    };

    function getNodes() {
        var offset = nodeOffset;
        cloudSnitchApi.diffNodes($scope.diff.type, $scope.diff.id, $scope.diff.leftTime, $scope.diff.rightTime, offset, nodePageSize)
        .then(function(result) {
            // Check if the diff tree is finished
            if (!angular.isDefined(result.nodes)) { return; }

            // Check if this is a redundant request.
            if (nodeOffset > offset) { return; }

            // Update the nodes array.
            for (var i = 0; i < result.nodes.length; i++) {
                $scope.nodes[offset + i] = result.nodes[i];
            }

            // Update node offset for next polling
            nodeOffset += result.nodes.length;

            // Check if this is the last request
            if (result.nodes.length < nodePageSize) {
                stopPollingNodes();
                // Update labels
                updateLabels();
                $scope.state = 'done';
            }
        }, function(resp) {
            stopPollingNodes();
            $scope.state = 'error';
        });
    }

    function nodeClickHandler(d) {
        var index = $scope.nodeMap[d.data.model][d.data.id];
        if (angular.isDefined(index) && $scope.nodes[index]) {
            $scope.$apply(function() {
                $scope.detailNodeType = d.data.model;
                $scope.detailNode = $scope.nodes[index];
                $scope.detailNodeId = d.data.id;
            });
        }
    }

    $scope.humanState = function() {
        switch ($scope.state) {
            case 'empty':
                return 'No meaningful differences.';
            case 'error':
                return 'Error loading diff';
            case 'loadingStructure':
                return 'Loading Structure';
            case 'loadingNodes':
                return 'Loading Nodes';
            case 'done':
                return 'Done';
            default:
                return 'Unknown';
        }
    };

    $scope.detailProps = function() {
        var props = [];
        angular.forEach($scope.detailNode.left, function(value, key) {
            props.push(key);
        });
        angular.forEach($scope.detailNode.right, function(value, key) {
            props.push(key);
        });
        angular.forEach($scope.detailNode.both, function(value, key) {
            props.push(key);
        });
        props = props.filter(function(value, index, self) {
            return self.indexOf(value) === index;
        });
        props.sort();
        return props;
    }

    $scope.detailProp = function(prop, side) {
        var r = {
            val: '',
            css: ''
        }
        if (angular.isDefined($scope.detailNode.both[prop])) {
            r.val = $scope.detailNode.both[prop];
        }
        else {
            r.val = $scope.detailNode[side][prop] || '';
            if (side == 'left')
                r.css = 'diffLeft';
            else
                r.css = 'diffRight';
        }
        return r;
    };

    $scope.closeDetail = function () {
        $scope.detailNode = undefined;
        $scope.detailNodeType = undefined;
        $scope.detailNodeId = undefined;
    }

    function getStructure() {
        cloudSnitchApi.diffStructure($scope.diff.type, $scope.diff.id, $scope.diff.leftTime, $scope.diff.rightTime)
        .then(function(result) {

            if (!angular.isDefined(result.frame)) {
                return;
            }

            stopPolling();

            if (result.frame !== null) {
                $scope.state = 'loadingNodes';
                $scope.frame = result.frame;
                $scope.nodeMap = result.nodemap;
                $scope.nodeCount = result.nodecount;
                $scope.nodes = new Array($scope.nodeCount);
                pollNodes = $interval(getNodes, pollInterval);
                render();
            } else {
                $scope.state = 'empty'
                $scope.frame = null;
                $scope.nodeMap = null;
                $scope.nodeCount = 0;
                $scope.nodes = [];
            }
        }, function(resp) {
            stopPolling();
            $scope.state = 'error'
        });
    }

    $scope.update = function() {
        $scope.frame = undefined;
        $scope.nodeMap = undefined;
        $scope.nodes = undefined;
        $scope.nodeCount = 0;
        $scope.state = 'loadingStructure';
        pollStructure = $interval(getStructure, pollInterval);
    };

    $scope.$watch('diff', function(newVal) {
        $scope.update();
    });

    $scope.$on('$destroy', function() {
        stopPolling();
        stopPollingNodes();
    });

    angular.element($window).bind('resize', function() {
        if ($scope.state != 'loadingStructure') {
            render();
            updateLabels();
        }
    });

}]);
