var transferButton = document.getElementById("transfer-files");
transferButton.addEventListener("click", function(e){
	var xhr = new XMLHttpRequest();
        var csrftoken = getCookie('csrftoken');
        xhr.open("POST", "/dummy/");
        xhr.setRequestHeader("X-CSRFToken", csrftoken);
        xhr.setRequestHeader('Content-type', 'application/x-www-form-urlencoded');
        xhr.onreadystatechange = function(){
                if(xhr.readyState === 4){
                        if(xhr.status === 200){
				console.log('cool, worked');
                        }
                        else{
                                console.log("Problem with DRIVE");
                        }
                }
        }
	var d={};
	var items = document.getElementsByClassName('file-selector');
	for(var i=0; i<items.length; i++){
		var item = items[i];
		if(item.checked){
			var fileId = item.getAttribute("value");
			var fileName = item.getAttribute("filename");
			d[fileId] = fileName;
		}
	}
	console.log(d);
        xhr.send("transfers="+JSON.stringify(d));
});


var selectAllCheckBoxes = document.getElementsByClassName("select-all-checkbox");

function checkChildren(e){
	var cbox = e.target;
	var cboxIsChecked = cbox.checked;
	var filetype = cbox.getAttribute("value");
	console.log(cbox);
	console.log(filetype);
	var parentDiv = document.getElementById(filetype +"-div");
	var childrenSelectors = parentDiv.getElementsByClassName("file-selector");
	for(var j=0; j<childrenSelectors.length; j++){
		childrenSelectors[j].checked = cboxIsChecked;
	}
}

for(var i=0; i<selectAllCheckBoxes.length; i++){
	var cbox = selectAllCheckBoxes[i];
	cbox.addEventListener("click", checkChildren);
}

