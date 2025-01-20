const Sample = class {
    constructor() {

    }
}

var new_workflow=null;
var new_container=null;

function newSamplePopup(projectid) {
    console.log('collecting info for new sample in ',projectid);
    if (!popups['newSample']) {
        popups['newSample'] = new popup({id:'newSample',title:`New sample in project ${projects[projectid].project_name}`,size:'large'});
    }
    popups['newSample'].clear();
    const name = new label_container({name:'Name:',input: new textbox({id:'new_sample_name'}).element, width:100})
    new_workflow = new dropdown({id:'new_sample_wf'})
    const workflow = new label_container({name:'Workflow:',input: new_workflow.element, width:100})
    var refactor=[]
    for (wf in workflows) {
        refactor.push(workflows[wf])
    }
    new_workflow.add_options({type:'dict',dict:refactor, keys:'wfid', values:'name'});
    new_container = new dropdown({id:'new_sample_container',value:1})
    const container = new label_container({name:'Container:',input: new_container.element, width:100})
    new_container.add_options({type:'dict',dict:containers, keys:'cid', values:'name'});

    const button_row = document.createElement('div');
    const project_id = document.createElement('input');
    project_id.type='hidden';
    project_id.id='project_id';
    project_id.value=projectid;
    button_row.innerHTML='<div id="pylims_popup_error"></div><div id="pylims_popup_success"></div>'
    button_row.classList.add('button_container')
    const save_button = document.createElement('button');
    save_button.textContent="Create";
    save_button.id='new_sample_create_button';
    save_button.addEventListener('click',createNewSample);
    const another_button = document.createElement('button');
    another_button.textContent="Create & Add Another";
    button_row.append(project_id);
    button_row.appendChild(save_button)
    button_row.appendChild(another_button)

    popups['newSample'].append(name)
    popups['newSample'].append(workflow)
    popups['newSample'].append(container)
    popups['newSample'].append(button_row)
    popups['newSample'].show();
}

const ws = new WebSocket('wss://' + window.location.host + '/ws/projects/');

ws.onmessage = function(event) {
	const data = JSON.parse(event.data);
	const message = data.message;
	console.log('websocket message:',message)
	
}
ws.onclose = function(event) {
    console.error("WebSocket is closed now.");
    const x = new popup({id:'ws_disconnect',title:'Connection Lost',unclosable:true});
    x.html_content('Your connection was interrupted. Reload the page to see current data.')
    x.show();
};

function sendMessage(type,msg,data) {
	ws.send(JSON.stringify({ 'message': {type: type, message: msg, data: data} }));
}

function createNewSample() {
    const name = document.getElementById('new_sample_name');
    const popuperror=document.getElementById('pylims_popup_error');
    popuperror.classList.add('localerror');
    popuperror.style.display='none';
    if (!name.value || name.value=='') {
        popuperror.innerHTML='Must specify a sample name';
        popuperror.style.display='block';
        return false
    }
    console.log(name.value,name.value.length)
    if (name.value.length < 5) {
        popuperror.innerHTML='Sample name must be longer than 5 characters';
        popuperror.style.display='block';
        return false
    }
    const workflow = new_workflow.value;
    if (!workflow) {
        popuperror.innerHTML='Must specify an initial workflow';
        popuperror.style.display='block';
        return false
    }
    const container = new_container.value;
    if (!container) {
        popuperror.innerHTML='Must specify an initial container';
        popuperror.style.display='block';
        return false
    }
    const project = document.getElementById('project_id').value;
    data={name:name.value,project,workflow,container}
	const pyoptions={data,csrf,urlprefix:'mod_samples',url:'create_new_sample',submit_id:'create_new_sample',submit_mode:'success',error_id:'pylims_popup_error',submit_id:'new_sample_create_button'}
	pylims_post(pyoptions).then(result => {
		console.log(result);
		sendMessage('create_sample','New Sample Created',{name:result['new_name'],id:result['new_id']});
	}).catch(error => {
		console.error(error);
	});
}