function pylims_post(options) {
	console.log('pylims post with following options:',options);
	let success_element = document.getElementById(options.success_id);
	let error_element = document.getElementById(options.error_id);
	if (success_element) {
		success_element.style.display='none';
	}
	if (error_element) {
		error_element.style.display='none';
	}
	return new Promise((resolve, reject) => {
		if (!options.data) {
			pylims_request_error({error:'no data',error_id:options.error_id})
			reject("pylims.post did not complete");
		} if (!options.url) {
			pylims_request_error({error:'no url',error_id:options.error_id})
			reject("pylims.post did not complete");
		} if (!options.csrf) {
			pylims_request_error({error:'no csrf token',error_id:options.error_id})
			reject("pylims.post did not complete");
		}
		if (options.submit_id) {
			var submitbutton = document.getElementById(options.submit_id);
		}
		if (options.submit_id && options.submit_mode && (options.submit_mode=='success' || options.submit_mode=='save')) {
			submitbutton.disabled = true;
		}
		fetch(`/${options.urlprefix}/${options.url}/`, {
		  method: "POST",
		  headers: {
			"Content-Type": "application/json",
			'X-CSRFToken': options.csrf
		  },
		  body: JSON.stringify(options.data)
		})
		  .then(response => {
			// Check if the request was successful (status code 2xx)
			if (!response.ok) {
				const statusCode = response.status;
				throw new Error(`Pylims error: ${statusCode} /${options.urlprefix}/${options.url}/`);
			}	
			return response.json();
		  })
		  .then(data => {
			console.log("Response:", data)
			clear_msg_elements();
			var error_element=null;
			var success_element=null;
			if (options.error_id && document.getElementById(options.error_id)) {
				error_element = document.getElementById(options.error_id);
			} else if (document.getElementById('pylims_request_error')) {
				error_element = document.getElementById('pylims_request_error');
				//console.log('found default error element');
			}
			
			if (options.success_id && document.getElementById(options.success_id)) {
				success_element = document.getElementById(options.success_id);
			} else if (document.getElementById('pylims_request_success')) {
				success_element = document.getElementById('pylims_request_success');
				//console.log('found default success element');
			}
			
			if (options.submit_id) {
				var submitbutton = document.getElementById(options.submit_id);
			}
			if (data.error && error_element) {
				error_element.textContent=data.error;
				error_element.style.display='block';
				submitbutton.disabled = false;
				reject("pylims.post did not complete");
			} else if (error_element) {
				error_element.style.display='none';
			}
			
			if (data.status && data.status=='success' && !data.msg_success && success_element) {
				success_element.textContent='Successful';
				success_element.style.display='block';
				resolve(data);
			} else if (data.status && data.status=='success' && data.msg_success && success_element) {
				success_element.textContent=data.msg_success;
				success_element.style.display='block';
				resolve(data);
			} else if (data.status && data.status=='success') {
				resolve(data);
			} else if (success_element) {
				success_element.style.display='none';
				submitbutton.disabled = false;
				reject("pylims.post did not complete");
			} else {
				console.error('unknown status')
			}
			
			if (options.submit_mode=='save') {
				submitbutton.disabled = false;
			}
			
		  })
		  .catch(servererror => {
			// Handle errors
			console.error("Server Error:", servererror);
			clear_msg_elements();
			var error_element=null;
			if (options.error_id && document.getElementById(options.error_id)) {
				error_element = document.getElementById(options.error_id);
			} else if (document.getElementById('pylims_request_error')) {
				error_element = document.getElementById('pylims_request_error');
				console.log('found default error element');
			}
			if (error_element) {
				error_element.textContent=servererror;
				error_element.style.display='block';
				submitbutton.disabled = false;
			}
			if (options.submit_mode=='save') {
				submitbutton.disabled = false;
			}
			reject("pylims.post did not complete");
		  });
	});
}

function pylims_request_error(options) {
	if (options.error_id) {
		const error = document.getElementById(options.error_id);
		error.textContent=options.error;
		error.style.display='block';
	}
}

function clear_msg_elements(show_unsaved=false) {
	let success_element = document.getElementById('pylims_request_success');
	let error_element = document.getElementById('pylims_request_error');
	let unsaved_element = document.getElementById('pylims_unsaved_changes');
	if (unsaved_element && show_unsaved==true) {
		unsaved_element.style.display='block';
	} else if (unsaved_element) {
		unsaved_element.style.display='none';
	}
	if (success_element) {
		success_element.style.display='none';
	}
	if (error_element) {
		error_element.style.display='none';
	}
}

function gen_msg_elements(ele) {
	var error = document.createElement("div");
	error.id='pylims_request_error';
	var success = document.createElement("div");
	success.id='pylims_request_success';
	var unsaved = document.createElement("div");
	unsaved.id='pylims_unsaved_changes';
	unsaved.textContent='Unsaved changes';
	ele.append(unsaved)
	ele.append(error)
	ele.append(success);
}

function gen_save_button(ele) {
	// Create the button element for Save
	
}