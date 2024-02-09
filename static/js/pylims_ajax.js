export function pylims_ajax(options) {
	const createbutton = document.getElementById('create_button');
	createbutton.disabled = true;
	fetch("/create_account/", {
	  method: "POST",
	  headers: {
		"Content-Type": "application/json",
		'X-CSRFToken': '{{ csrf_token }}'
	  },
	  body: JSON.stringify(data)
	})
	  .then(response => {
		// Check if the request was successful (status code 2xx)
		if (!response.ok) {
		  throw new Error("Network response was not ok");
		}	
		return response.json();
	  })
	  .then(data => {
		console.log("Response:", data);
		const error = document.getElementById('account_creation_error');
		const success = document.getElementById('account_creation_success');
		const createbutton = document.getElementById('create_button');
		if (data.error) {
			error.textContent=data.error;
			error.style.display='block';
			createbutton.disabled = false;
		} else {
			error.style.display='none';
		}
		if (data.status && data.status=='success') {
			success.textContent='Account created';
			success.style.display='block';
		} else {
			success.style.display='none';
			createbutton.disabled = false;
		}
	  })
	  .catch(error => {
		// Handle errors
		console.error("Error:", error);
	  });
}