var Choose = angular.module('Choose', []);

Choose.controller('APIController', function APIController($scope, $http, $filter) {

	$scope.isLoading = false;

	$scope.get = function ($url)
	{

		$scope.isLoading = true;

		$http.get($url).then(function(value) {
			$scope.objects = value.data;
			$scope.isLoading = false;
		});
	}

    $scope.choose_object = function (object, object_repr)
    {
        $("#object_id").val(object.pk);
        $("#selected_object").html(object_repr);
        $scope.objects = "";
        $("#submit_button").prop('disabled', false);
        $("#filter").val("");
        $("#clear").show();

    }

    $scope.clear = function ()
    {
        $("#object_id").val("");
        $("#selected_object").html("");
        $scope.clients = "";
        $("#submit_button").prop('disabled', true);
    }

});
