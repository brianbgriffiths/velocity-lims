console.log('mod',mod,'options',options)
const main = document.getElementById('automations');
const edit_window = document.getElementById('edit_window');
const edit_docked = document.getElementById('edit_docked');
const edit_maximize = document.getElementById('edit_maximize');
const edit_windowed = document.getElementById('edit_windowed');
const edit_minimize = document.getElementById('edit_minimize');
const new_step = document.getElementById('new_step');
const step_list = document.getElementById('step_list');
function add_new_step() {
	const new_step_input = document.getElementById('new_step_input')

	console.log('setting',new_step)
	new_step.style.height='35px';
	setTimeout(function() {
		new_step_input.focus();
	},1000);
}

function edit_step(id) {
    const edit_content = document.getElementById('edit_content');
	const title = document.getElementById('edit_header_title');
    
    title.innerHTML=null;
    let step_name = document.createElement('input')
    step_name.type = 'text';
    step_name.value = steps[id].name;
    title.appendChild(step_name)
}

var opened_window = null;
function edit_window_open() {
	automation_container_maximize();
	edit_window_minimize();
	opened_window = window.open('https://local.pylims.com/modules/automations/fullscreen_editor/', 'fullScreenEditor', 'width=800,height=600,scrollbars=yes,resizable=yes');
	window.addEventListener('message', function(event) {
		if (event.data === 'closeWindow') {
			console.log('closing external window');
			edit_window_dock();
			automation_container_dock();
		}
	});
}

function undock() {
	window.opener.postMessage('closeWindow', '*');
            // Close the new window
            window.close();
}

const step = class {
	constructor(id,name,type=null,status=null,version=null) {
		this.element = document.createElement('div')
		this.id = id;
		this.name = name;
		this.element.id = id
		this.element.classList.add('step_container');
		this.element.innerHTML = this.name;
        if (step_list) {
		    step_list.appendChild(this.element);
        }
		this.element.addEventListener('click', this.editStep);
	}

	editStep(event) {
		ws.send(JSON.stringify({ 'message': {type: 'edit_step', message: 'editing step', data:{id:this.id} } }));
	}
}

function automation_container_maximize() {
	main.classList.add('automations_maximized');
	// let acs = document.querySelectorAll('.automation_container')
	let autocon = document.getElementById('automation_container');
	autocon.classList.add('automation_container_maximized')
}

function automation_container_dock() {
	main.classList.remove('automations_maximized');
	// let acs = document.querySelectorAll('.automation_container')
	let autocon = document.getElementById('automation_container');
	autocon.classList.remove('automation_container_maximized');
}

function edit_window_maximize() {
	edit_docked.style.display='block';
	edit_maximize.style.display='none';
	edit_minimize.style.display='block';
	edit_window.classList.remove(...edit_window.classList);
	edit_window.classList.add('center-border','edit_window_maximized');
}
function edit_window_dock() {
	edit_docked.style.display='none';
	edit_maximize.style.display='block';
	edit_minimize.style.display='block';
	edit_window.classList.remove(...edit_window.classList);
	edit_window.classList.add('center-border');
    automation_container_dock();
}
function edit_window_minimize() {
	edit_docked.style.display='block';
	edit_maximize.style.display='block';
	edit_minimize.style.display='none';
	edit_window.classList.remove(...edit_window.classList);
	edit_window.classList.add('center-border','edit_window_minimized');
	automation_container_maximize();
}

function create_new_step() {
	clear_msg_elements();
	const new_step_name = document.getElementById('new_step_input').value;
	if (!new_step_name || new_step_name.length<3) {
		pylims_request_error({error_id:'pylims_request_error',error:'New Step name must be longer than...that.'})
		return false;
	}
	data={new_step_name}
	const pyoptions={data,csrf,urlprefix,url:'create_new_step',submit_id:'create_new_step',submit_mode:'success'}
	pylims_post(pyoptions).then(result => {
		new_step.style.height='0px';
		console.log(result);
		sendMessage('create_step','New Step Created',{name:result['new_name'],id:result['new_id']});
	}).catch(error => {
		console.error(error);
	});
}

var steps={}

function step_created(id,name) {
	console.log('adding step',id,name)
	steps[id] = new step(id,name);
}

const ws = new WebSocket('wss://' + window.location.host + '/ws/automation/');

ws.onmessage = function(event) {
	const data = JSON.parse(event.data);
	const message = data.message;
	console.log('websocket message:',message)
	if (message.type=='create_step') {
		step_created(message.data.id,message.data.name)
	} else if (message.type=='edit_step' && message.data.op_id==user.userid) {
		edit_step(message.data.id)
	}
};

function sendMessage(type,msg,data) {
	ws.send(JSON.stringify({ 'message': {type: type, message: msg, data: data} }));
}

function populate_step_list(data) {
	for (let s of data) {
		steps[s.asid] = new step(s.asid, s.name, s.type, s.status, s.version)
	}
}

