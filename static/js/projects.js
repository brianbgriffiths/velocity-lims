
var projects={}

const Project = class {
	constructor(options) {
		console.log('new project',options)
        for (let x in options) {
            this[x]=options[x];
        }
        this.samples_displayed=false
        this.element = document.createElement('project')
        this.samplecount_element=document.createElement('samplecount');
        this.samplecount_element.textContent = options['sample_count'];
        let newSample = document.createElement('newsample');
        newSample.innerHTML='<i class="fa-regular fa-vial"></i>+';
        this.element.appendChild(newSample);
        newSample.addEventListener('click',()=>{ newSamplePopup(this.pid); });     
        const project_name = document.createElement("projecttitle");
		project_name.textContent = this.project_name;
        this.element.appendChild(project_name)
        this.element.appendChild(this.samplecount_element);
        this.samplelist_element = document.createElement('samplelist');
        this.element.appendChild(this.samplelist_element);
        this.toggle_samples = this.toggle_samples.bind(this);
        this.samplecount_element.addEventListener('click',this.toggle_samples)
        

        
	}

    toggle_samples() {
        this.samples_displayed=!this.samples_displayed;
        if (this.samples_displayed) {
            console.log('show',this.samples,this)
            for (let sample of this.samples) {
                let s = document.createElement('sample');
                s.innerHTML='<i class="fa-light fa-vial-circle-check"></i> '+sample.specimen_name;
                this.samplelist_element.appendChild(s)
                let workflow_element = document.createElement('sampleworkflow');
                workflow_element.innerHTML = workflows[sample.workflow].name+'<i class="fa-regular fa-clock"></i>';
                s.appendChild(workflow_element)
            }
        } else {
            console.log('hide');
            this.samplelist_element.innerHTML=null;
        }
    }

    setSampleCount(val) {
        this.samplecount_element.innerHTML=val;
    }

}

function load_projects() {
	newproject.hide();
	projectlist.clear();
	if (mod_data['error']) {
		const load_error = document.createElement('div');
		load_error.classList.add('localerror');
		load_error.textContent=mod_data['error'];
		load_error.style.display='block';
		projectlist.add(load_error);
	}
	
	if (mod_data['projects']) {
		for (const project in mod_data['projects']) {
            const p = mod_data['projects'][project];
            projects[p.pid]=new Project(p)
			projectlist.add(projects[p.pid].element);
        }

	}
	projectlist.show();
}

function shareExperiment() {
	
}

function newExperiment() {
	if (!active_mods['experiments']) {
		const load_error = document.createElement('div');
		load_error.classList.add('localerror');
		load_error.textContent='Experiments Module not enabled';
		load_error.style.display='block';
		projectlist.add(load_error);
		return false;
	}
	window.location.href=`https://${window.location.hostname}/modules/experiments?new=${mod_data['projects'][0].pid}`;
}

function newProject() {
	projectlist.hide();
	if (newproject.initialized) {
		newproject.show();
		return;
	}
	
	const header_group = document.createElement("div");
	header_group.textContent = 'Group';
	header_group.classList.add('h1');
	newproject.add(header_group);
	
	const content_project = document.createElement("div");
	content_project.classList.add('indented');
	newproject.add(content_project);
	
	const indv_container = document.createElement("div");
	var radio = document.createElement("input");
    radio.setAttribute("type", "radio");
	radio.checked=true;
	radio.name="new_project";
	radio.value='self';
	indv_label = document.createTextNode("Private Project");
	const indv_value = document.createElement("input");
	indv_value.type='hidden';
	indv_value.value='self';
	indv_value.id='self_project';
	
    indv_container.appendChild(radio);
	indv_container.appendChild(indv_label);
	indv_container.classList.add("project");
	content_project.appendChild(indv_container);
	indv_container.appendChild(indv_value);
	
	if (active_mods['teams'] && mod_data['teams']) {
		console.log(mod_data['teams'])
		const team_container = document.createElement("div");
		team_container.classList.add("project");
		const team_radio = document.createElement("input");
		team_radio.name="new_project";
		team_radio.setAttribute("type", "radio");
		team_radio.value='teams';
		const team_label = document.createTextNode("Team Project");
		const team_select = document.createElement("select");
		
		team_container.appendChild(team_radio);
		team_container.appendChild(team_label);
		content_project.appendChild(team_container);
		
		if (mod_data['teams']) {
			console.log('teams',mod_data['teams'])
			var dd = new dropdown('teams_project',team_container);
			dd.add_options({type:'dict',dict:mod_data['teams'], keys:'teamid', values:'team_name', img:'team_image'});
			dd.ele.addEventListener('dropdownchange', function() { team_radio.checked=true; });
		}	
	}
	
	if (active_mods['departments'] && mod_data['departments']) {
		const departments_container = document.createElement("div");
		departments_container.classList.add("project");
		const departments_radio = document.createElement("input");
		departments_radio.name="new_project";
		departments_radio.setAttribute("type", "radio");
		departments_radio.value='departments';
		const departments_label = document.createTextNode("Department Project");
		const departments_select = document.createElement("select");
		
		departments_container.appendChild(departments_radio);
		departments_container.appendChild(departments_label);
		content_project.appendChild(departments_container);
		
		if (mod_data['departments']) {
			console.log('departments',mod_data['departments'])
			var dd = new dropdown('departments_project',departments_container)
			dd.add_options({type:'dict',dict:mod_data['departments'], keys:'deptid', values:'dept_name', img:'dept_image'});
			dd.ele.addEventListener('dropdownchange', function() { departments_radio.checked=true; });
		}	
	}
	const header_settings = document.createElement("div");
	header_settings.textContent = 'Settings';
	header_settings.classList.add('h1');
	newproject.add(header_settings);
	
	const content_settings = document.createElement("div");
	content_settings.classList.add('indented');
	newproject.add(content_settings);
	
	var new_project_name = document.createElement("input");
	new_project_name.type='text';
	new_project_name.id='new_project_name';
	new_project_name.placeholder='New Project Name';
	new_project_name.style.width='100%';
	content_settings.appendChild(new_project_name);
	
	
	
	const button_container = document.createElement("div");
	button_container.classList.add('button_container');
	newproject.add(button_container);
	gen_msg_elements(button_container)
	var cancel_project_button = document.createElement("button");
	cancel_project_button.innerHTML='Nevermind';
	cancel_project_button.id='create_project_cancel';
	button_container.appendChild(cancel_project_button);
	cancel_project_button.addEventListener('click',function() { projectlist.show(); newproject.hide(); });

	var create_project_button = document.createElement("button");
	create_project_button.innerHTML='<i class="fa-regular fa-folder-plus"></i> Create Project';
	create_project_button.id='create_project_button';
	button_container.appendChild(create_project_button);
	create_project_button.addEventListener('click',createProject);
	
	newproject.show();
}

function createProject() {
	let data={}
	data['type']=document.querySelector('input[name=new_project]:checked').value;
	data['id']=document.getElementById(data['type']+'_project').getAttribute('value');
	data['name']=document.getElementById('new_project_name').value;
	if (!data['id']) {
		localerror('You chose '+data['type']+' project type, but did not choose a valid option.');
		return false;
	}
	if (!data['name']) {
		localerror('Create a project name, even if it\'s a placeholder.');
		return false;
	}
	const pyoptions={data,csrf,urlprefix,url:'ajax_create_project',submit_mode:'success', submit_id:'create_project_button'}
	pylims_post(pyoptions).then(result => {
		console.log('pylims.post result x',result.data);
		
	}).catch(error => {
        console.error(error);
    });
}

function localerror(msg) {
	error_element = document.getElementById('pylims_request_error');
	error_element.textContent=msg;
	error_element.style.display='block';
}

