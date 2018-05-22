function PagedTableController() {
    var self = this;

    self.rowClick = function(index) {
        self.onRowClick({
            index: index
        });
    };

    self.sortChange = function(index) {
        self.onSortChange({
            sortColumnIndex: index
        });
    }
}

angular.module('cloudSnitch').component('pagedtable', {
    templateUrl: '/static/web/html/pagedtable.html',
    controller: PagedTableController,
    bindings: {
        thing: '<',
        sortColumn: '<',
        sortDirection: '<',
        titles: '<',
        records: '<',
        total: '<',
        onRowClick: '&',
        onSortChange: '&'
    }
});


function PagesController() {
    var self = this;

    self.$onInit = function() {
        // Convert nPages to odd number
        if (self.nPages % 2 == 0) {
            self.nPages = Math.max(self.nPages - 1, 1);
        }

        // Show first - default true
        if (!angular.isDefined(self.first)) {
            self.first = true;
        }

        // Show last - default true
        if (!angular.isDefined(self.last)) {
            self.last = true;
        }
    };

    self.totalPages = function() {
        return totalPages = Math.ceil(self.total / self.pagesize);
    };

    self.isCurrent = function(index) {
        return self.current == index + 1;
    }

    self.pageList = function() {
        var pages = [];
        var totalPages = self.totalPages();
        var length = Math.min(self.nPages, totalPages);
        var start = self.current - (Math.floor(length / 2));
        var stop = start + length - 1;

        if (start < 1) {
            var distance = 1 - start
            start += distance;
            stop += distance;
        }

        if (stop > totalPages) {
            var distance = stop - totalPages;
            start -= distance;
            stop -= distance;
        }

        for (var i = start; i <= stop; i++) {
            pages.push(i);
        }
        return pages;
    };

    self.pageChange = function(newPage) {
        if (self.current != newPage) {
            self.onPageChange({
                newPage: newPage,
                oldPage: self.current
            });
        }
    };

}

angular.module('cloudSnitch').component('pages', {
    templateUrl: '/static/web/html/pages.html',
    controller: PagesController,
    bindings: {
        total: '<',
        pagesize: '<',
        current: '<',
        nPages: '<',
        first: '<',
        last: '<',
        onPageChange: '&'
    }
});
