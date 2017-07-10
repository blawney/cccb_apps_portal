//var container = document.getElementById("add-sample-panel-inner");
var groupBoxes = document.getElementsByClassName("group-box");

// Prevent the drag/drop from doing anything if it's dropped off-target
window.addEventListener("dragover", function(e){
    e = e || event;
    e.preventDefault();
});
window.addEventListener("drop", function(e){
    e = e || event;
    e.preventDefault(); 
});


// some functions for handling the drag/drop
dragStartFunc = function(e){
	e.dataTransfer.setData("text", e.target.id);
	e.dataTransfer.effectAllowed = "move";  
};

dragEndFunc = function(e){
    //e.dataTransfer.clearData();
};

dragEnterFunc = function(e){
    e.preventDefault();
    e.stopPropagation();
};

dragOverFunc =  function(e){
    e.preventDefault();
    e.stopPropagation();
};

dropFunc = function(e){
	e.preventDefault();
	var id = e.dataTransfer.getData("text");
	e.target.appendChild(document.getElementById(id));
	e.stopPropagation();

	// now check if there is at least one sample in each grouping
	var allGroupsHaveSamples = true; 
	for(i=0; i<groupBoxes.length; i++){
		var currentBox = groupBoxes[i];
		var children = currentBox.getElementsByClassName("sample-display");
		if (children.length == 0){
			allGroupsHaveSamples = false;
		}
	}
	if(allGroupsHaveSamples){
		document.getElementById("start-dge-panel").style.display = "inline-block";
	}else{
		document.getElementById("start-dge-panel").style.display = "none";
	}
};

dragLeaveFunc =  function(e){
	e.preventDefault();
	e.stopPropagation();
};


var sampleArea = document.getElementById("existing-samples-wrapper");
sampleArea.addEventListener("dragover", dragOverFunc);
sampleArea.addEventListener("dragenter", dragEnterFunc);
sampleArea.addEventListener("drop", dropFunc);


for(var i=0; i<groupBoxes.length; i++){
	var a = groupBoxes[i];
	a.addEventListener("dragover", dragOverFunc);
	a.addEventListener("dragenter", dragEnterFunc);
	a.addEventListener("drop", dropFunc);        
}

var draggableElements = document.getElementsByClassName("sample-display");
for(var i=0; i<draggableElements.length; i++){
	var a = draggableElements[i];
	a.addEventListener("dragstart", dragStartFunc);            
	a.addEventListener("dragend", dragEndFunc);
}



onGroupNameEditClick = function(e){
	var target = e.target;
	target.style.display = "none";
	var parent = target.parentElement;
	var inputBox = parent.getElementsByClassName("group-name-input")[0];
	var groupNameDisplay = parent.getElementsByClassName("group-name")[0];
	groupNameDisplay.style.display = "none";
	inputBox.style.display = "inline-block";
	var groupName = groupNameDisplay.textContent;
	inputBox.value = groupName;
	inputBox.focus();
}

onGroupNameEditKeyUp = function(e){
        if (e.which == 13){
                e.target.blur();
        }
}

onGroupNameEditBlur = function(e){

	var target = e.target;
        var newName = target.value;
	if (newName.length == 0){
		target.focus();
		return;
	}
	var parent = target.parentElement;
	var editIcon = parent.getElementsByClassName("group-name-edit")[0];
	var groupNameDisplay = parent.getElementsByClassName("group-name")[0];
	var assocGroupBox = parent.getElementsByClassName("group-box")[0];
        editIcon.style.display = "inline";
        target.style.display = "none";
        groupNameDisplay.textContent = newName;
	assocGroupBox.setAttribute("groupName", newName);
        groupNameDisplay.style.display = "inline";
}

// add event to the pencil/edit icons
var editGroupNameIcons = document.getElementsByClassName("group-name-edit");
for(var i=0; i<editGroupNameIcons.length; i++){
	var el = editGroupNameIcons[i];
	el.addEventListener("click", onGroupNameEditClick);
}


// add events to the input boxes
var editGroupNameInputs = document.getElementsByClassName("group-name-input");
for(var i=0; i<editGroupNameIcons.length; i++){
	var el = editGroupNameInputs[i];
	el.addEventListener("keyup", onGroupNameEditKeyUp);
	el.addEventListener("blur", onGroupNameEditBlur);
}


// Sends the request to the backend
startAnalysis = function(jsonStr){

        var pk = document.getElementById("pk-field").value;

        var xhr = new XMLHttpRequest();
        var csrftoken = getCookie('csrftoken');
        xhr.open("POST", "/rnaseq/run/" + pk + "/");
        xhr.setRequestHeader("X-CSRFToken", csrftoken);

        xhr.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded');
        xhr.onreadystatechange = function(){
                if(xhr.readyState === 4){
                        if(xhr.status === 200){
                                window.location.assign("/analysis/home");
                        }
                }
        }
	console.log(jsonStr)
        xhr.send("info="+jsonStr);
};

isValid = function (box) {
	var val = box.value;
	var match = val.replace(/[0-9]+\.?[0-9]*?/g, '');
	if (match != ''){
		return false;
	}else{
		return true;
	}
}


// for sending info to start the job:
startAnalysisBtn = document.getElementById("start-dge-button");
startAnalysisBtn.addEventListener("click", function(e){
	
	var positiveInputs = document.getElementsByClassName("positive-number-input");
        for(var i=0; i<positiveInputs.length; i++){
		var x = positiveInputs[i];
		if (!isValid(x)){
			alert('Check your numbers.  Log2 Fold-Change values should be greater than zero, and p-values should be between 0 and 1');	
			return;
		}
	}
	
        var groupToSampleMapping = {};
        for(var i=0; i<groupBoxes.length; i++){
                var box = groupBoxes[i];
                var groupName = box.getAttribute("groupName");
                groupToSampleMapping[groupName] = []; 
                var descendants =  box.querySelectorAll(".sample-display");
                for(var j=0; j<descendants.length; j++){
                        var pk = descendants[j].getAttribute("pk");
                        groupToSampleMapping[groupName].push(pk);
                }
        }
	var info = {}
	info["contrast_name"] = document.getElementById("contrast-name-input").value;
	info["mapping"] = groupToSampleMapping;
	info["l2fc_threshold"] = document.getElementById("lfc_input").value;
	info["pval_threshold"] = document.getElementById("pval_input").value;
        startAnalysis(JSON.stringify(info));
});


