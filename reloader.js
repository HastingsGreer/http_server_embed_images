var interval = 100;
var lastModified = -1;

function heartbeat() {
  if (document.body) {
    checkForChanges();
  }
  setTimeout(heartbeat, interval);
}

function checkForChanges() {
  fetch("/lastModified", {
    method: "POST",
  })
    .then((response) => {
      return response.json();
    })
    .then((json) => {
	    console.log(json)
      var new_modified = json["modified_counter"];
      if (lastModified == -1) {
        lastModified = new_modified;
      }
      if (new_modified != lastModified) {
	if (json["goto_path"]){
		window.location.href = json["goto_path"];
		return;
	}
        document.location.reload();
      }
    });
}
heartbeat();
