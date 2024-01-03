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
		  method: "POST",})
		    .then((response) => {
			  return response.json()
		    })
		    .then((json) => {
			    var new_modified = json["modified_counter"]
			    if (lastModified == -1){
				    lastModified = new_modified;
			    }
			    if (new_modified != lastModified) {
				    document.location.reload();
			    }
		    });
      }
      heartbeat();


