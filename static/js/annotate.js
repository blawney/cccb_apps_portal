var addNewSampleBtn = document.getElementById("add-new-sample-button");
var container = document.getElementById("add-sample-panel-inner");
var sampleEntryDialog = document.getElementById("sample-entry-box");
var addSampleDialogBtn = document.getElementById("add-sample-dialog-btn");
var cancelSampleDialogBtn = document.getElementById("cancel-sample-dialog-btn");
var goToSummaryBtn = document.getElementById("go-to-summary-btn");

// Prevent the drag/drop from doing anything if it's dropped off-target
window.addEventListener("dragover", function(e){
    e = e || event;
    e.preventDefault();
});
window.addEventListener("drop", function(e){
    e = e || event;
    e.preventDefault(); 
});

// shows the 'add sample' dialog
addNewSampleBtn.addEventListener("click", function(e){
        sampleEntryDialog.style.display = "block";
        document.getElementById("main-container").classList.add("blur");
});

// closes out the add sample dialog with no action
cancelSampleDialogBtn.addEventListener("click", function(e){
        sampleEntryDialog.style.display = "none";
        document.getElementById("main-container").classList.remove("blur");	
});

// called when the new sample is added, as button is clicked
// makes ajax call to server
addSampleDialogBtn.addEventListener("click", function(e){

	sampleEntryDialog.style.display = "none";
	document.getElementById("main-container").classList.remove("blur");
	var sampleEntry = document.getElementById("sample-entry-input");
	var samplename = sampleEntry.value;
	sampleEntry.value = ""; 

	var metaEntry = document.getElementById("sample-meta-input");
	var sampleMeta = metaEntry.value;
	metaEntry.value = ""; 

	//upload to db
	var pk = document.getElementById("pk-field").value;
	var xhr = new XMLHttpRequest();
	var csrftoken = getCookie('csrftoken');
	xhr.open("POST", "/analysis/create-sample/" + pk + "/");
	xhr.setRequestHeader("X-CSRFToken", csrftoken);
	xhr.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded');
	xhr.onreadystatechange = function(){
		if(xhr.readyState === 4){
				if(xhr.status === 200){
					addNewSampleBox(samplename);
				}
				else{
					alert("There was a problem creating the sample.  Try again.");
				}
		}
	}
	xhr.send("name="+samplename + "&metadata=" + sampleMeta);
});


// Creates and adds the dialog box for creating a new sample
addNewSampleBox = function(samplename){
	var outer = document.createElement("div");
	var inner1 = document.createElement("div");
	var inner2 = document.createElement("div");
	var inner3 = document.createElement("div");

	inner3.textContent = "x";
	inner3.className = "rm-sample";

	inner3.addEventListener("click", rmSample);


	outer.className = "sample-box";
	outer.setAttribute("samplename", samplename);
	inner1.className = "rp-div";
	inner2.className = "background-name";

	inner2.textContent = samplename;

	inner1.appendChild(inner3);
	inner1.appendChild(inner2);
	outer.appendChild(inner1);

	container.appendChild(outer);

	outer.addEventListener("dragover", dragOverFunc);
	outer.addEventListener("dragenter", dragEnterFunc);
	outer.addEventListener("drop", dropFunc);        
};

// function to remove sample.  Calls the back-end to remove the association between the removed sample and any files that were previously linked to it.
rmSample = function(e){
	var target = e.target;
	var parent = target.parentElement;
	var grandParent = parent.parentElement;
	var greatGrandParent = grandParent.parentElement;

	//check that the sample box is empty.  Not going to allow users to remove samples that have files assigned to them
	var enclosedSampleTags = grandParent.querySelectorAll('.sample-display');

	if (enclosedSampleTags.length > 0){
		alert('You cannot remove a sample that has files assigned.  Remove the assigned files and try again.');
		return;
	}

	greatGrandParent.removeChild(grandParent);

	var pk = document.getElementById("pk-field").value;
	var samplename = grandParent.getAttribute("samplename");
	var xhr = new XMLHttpRequest();
	var csrftoken = getCookie('csrftoken');
	xhr.open("POST", "/analysis/remove-sample/" + pk + "/");
	xhr.setRequestHeader("X-CSRFToken", csrftoken);
	xhr.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded');
	xhr.onreadystatechange = function(){
		if(xhr.readyState === 4){
				if(xhr.status === 200){
					console.log('successfully removed sample');
				}
				else{
					alert("Did not succeed in removing the sample.  Refresh the page and try again.");
				}
		}
	}
	xhr.send("samplename="+samplename);	
	
};

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
	checkAllAssigned();
};

dragLeaveFunc =  function(e){
	e.preventDefault();
	e.stopPropagation();
};

dropTargets = document.getElementsByClassName("sample-box");
for(var i=0; i<dropTargets.length; i++){
	var a = dropTargets[i];
	a.addEventListener("dragover", dragOverFunc);
	a.addEventListener("dragenter", dragEnterFunc);
	a.addEventListener("drop", dropFunc);        
}

draggableElements = document.getElementsByClassName("sample-display");
for(var i=0; i<draggableElements.length; i++){
	var a = draggableElements[i];
	a.addEventListener("dragstart", dragStartFunc);            
	a.addEventListener("dragend", dragEndFunc);
}

checkAllAssigned = function(){
	var proceedPanel =  document.getElementById("proceed-to-summary-panel");
	var filesPanel =  document.getElementById("existing-files-panel");
	var wrapper =  document.getElementById("existing-files-wrapper");
	if (wrapper.children.length === 0){
		filesPanel.style.display = 'none';
		proceedPanel.style.display = 'block';
	}
}
// end section on drag/drop functionality


// As we proceed to the next page, map the files to the samples by scanning through the UI 
// and extracting out the associations via the element's attributes
goToSummaryBtn.addEventListener("click", function(e){
	var sampleBoxes = document.getElementsByClassName("sample-box");
	var sampleToFileMapping = {};
	for(var i=0; i<sampleBoxes.length; i++){
		var box = sampleBoxes[i];
		var samplename = box.getAttribute("samplename");
		sampleToFileMapping[samplename] = []; 
		var descendants =  box.querySelectorAll(".sample-display");
		for(var j=0; j<descendants.length; j++){
			var attr = descendants[j].getAttribute("filename");
			sampleToFileMapping[samplename].push(attr);
		}
	}
	createMappings(JSON.stringify(sampleToFileMapping));
});

// Sends the request to the backend, and forwards onto the next page
createMappings = function(jsonStr){

	var pk = document.getElementById("pk-field").value;

	var xhr = new XMLHttpRequest();
	var csrftoken = getCookie('csrftoken');
	xhr.open("POST", "/analysis/map-files/" + pk + "/");
	xhr.setRequestHeader("X-CSRFToken", csrftoken);

	xhr.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded');
	xhr.onreadystatechange = function(){
		if(xhr.readyState === 4){
			if(xhr.status === 200){
				window.location.assign("/analysis/summary/" + pk + "/");
			}
		}
	}
	xhr.send("mapping="+jsonStr);
};

document.addEventListener("DOMContentLoaded", function () {
	checkAllAssigned();
	var sampleBoxes = document.getElementsByClassName('rm-sample');
	for (var i = 0; i < sampleBoxes.length; i++) {
	    sampleBoxes[i].addEventListener('click', rmSample, false);
	}	
}, false);
