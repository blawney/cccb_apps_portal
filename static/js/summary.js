var analyzeButton = document.getElementById("start-analysis");
var pkField = document.getElementById("pk-field");

analyzeButton.addEventListener("click", function(e){
	e.target.disabled = true;
	var pk = pkField.value;
	window.location.assign("/analysis/do-analysis/" + pk + "/")
});
