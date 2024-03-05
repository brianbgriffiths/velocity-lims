const dropdown = class {
	constructor(id,target,defaultvalue=null) {
		this.timeouts = null;
		this.id = id;
		this.dropdown = document.createElement("pylims_dropdown");
		this.dropdown.id = id;
		target.appendChild(this.dropdown);
		this.ele = document.getElementById(id);
		this.optionList = document.createElement("pylims_dropdown_options_list");
		this.ele.appendChild(this.optionList);
		this.visible=false;
		this.value=defaultvalue;
		this.add_options({type:'default'});
		this.default = this.ele.querySelector('pylims_dropdown_default');
		this.add_options = this.add_options.bind(this);
		this.dropdownhide = this.dropdownhide.bind(this);
        this.dropdownview = this.dropdownview.bind(this);
		this.changeSelect = this.changeSelect.bind(this);
		this.ele.addEventListener('click', this.dropdownview);
	}

	add_options(options) {
		// console.log('adding options to',this.id,this.optionList)
		if (options.type=='default') {
			const ddoption = document.createElement("pylims_dropdown_default");
			ddoption.innerHTML = 'none';
			ddoption.setAttribute('value',0);
			this.optionList.appendChild(ddoption);
		} else if (options.type=='dict') {
			// console.log(options.dict)
			for (let x of options.dict) {
				console.log('x',x)
				console.log('options.keys',options.keys,x[options.keys])
				const ddoption = document.createElement("pylims_dropdown_option");
				ddoption.setAttribute("value", x[options.keys]);
				if (options.img) {
					const ddimage = document.createElement("img");
					ddimage.src=x[options.img];
					ddoption.appendChild(ddimage);
				}
				ddoption.innerHTML += x[options.values];
				this.optionList.appendChild(ddoption);
				
				ddoption.addEventListener('click', this.changeSelect);
			}
		}
	}
		
	dropdownview() {
		// console.log('viewing',this)
		this.default.style.color='#9e9e9e';
		this.ele.style.overflow='visible';
		this.optionList.addEventListener('mouseleave', this.dropdownhide);
		this.optionList.style.zIndex=300;
		clearTimeout(this.timeouts);
	}

	dropdownhide() {
		// console.log('drowndown hide',this)
		this.ele.style.overflow='hidden';
		this.default.style.color=null;
		this.optionList.style.zIndex=200;
	}

	changeSelect(event) {
		event.stopPropagation();
		event.preventDefault();
		const value=event.target.getAttribute('value');
		this.value=value;
		this.ele.setAttribute('value',value);
		this.default.innerHTML=event.target.textContent;
		this.ele.style.overflow='hidden';
		this.default.style.color=null;
		const dropdownChangeEvent = new CustomEvent('dropdownchange');
		this.ele.dispatchEvent(dropdownChangeEvent);
	}

}

const content_container = class {
	constructor(id,target) {
		this.id = id;
		this.div = document.createElement("div");
		this.div.id = id;
		target.appendChild(this.div);
		this.ele = document.getElementById(id);
		this.visible=true;
		this.show = this.show.bind(this);
		this.hide = this.hide.bind(this);
        this.toggle = this.toggle.bind(this);
		this.clear = this.clear.bind(this);
		this.set = this.set.bind(this);
		this.add = this.add.bind(this);
		console.log('created container',id);
		this.initialized=false;
	}
	
	show() {
		this.ele.style.display='block';
		this.visible=true
	}
	
	hide() {
		this.ele.style.display='none';
		this.visible=false
	}
	
	toggle() {
		const tstate=['none','block'];
		this.visible=!this.visible;
		this.ele.style.display=tstate[this.visible*1];
	}
	
	clear() {
		this.ele.innerHTML=null;
		this.initialized=false;
	}
	
	set(html) {
		this.ele.innerHTML=html;
		this.initialized=true;
	}
	
	add(ele) {
		console.log('add',ele)
		this.ele.appendChild(ele);
		this.initialized=true;
	}
}

const pylims_setup_toggle = class {
	constructor(setval,parent) {
		this.ele=document.createElement('div');
		this.ele.className='tf_container'
		this.tfball=document.createElement('div');
		this.tfball.className='tf_ball'
		if (setval=='true') {
			this.tfball.classList.add('tf_true');
			this.state='true';
		} else {
			this.tfball.classList.add('tf_false');
			this.state='false';
		}
		this.ele.appendChild(this.tfball);
		parent.appendChild(this.ele)
		this.category=null;
		this.module=null;
		this.option=null;
		this.toggle = this.toggle.bind(this);
	}

	toggle(id)  {
		console.log('toggle',id);
		if (this.state=="true") {
			console.log('toggle to false');
			this.state="false";
			this.tfball.classList.add('tf_false');
			this.tfball.classList.remove('tf_true');
			return 'false'
		} else {
			console.log('toggle to true');
			this.state="true";
			this.tfball.classList.add('tf_true');
			this.tfball.classList.remove('tf_false');
			return 'true';
		}
	}
}
const pylims_setup_select = class {
	constructor(options,value,parent) {
		this.ele =document.createElement('select');
		this.ele.className='pylimsui_select';
		parent.append(this.ele)
		this.value=value;
		
		for (let i=0;i<options.length;i++) {
			let option=document.createElement('option');
			option.value=i;
			option.text=options[i];
			if (i==value) {
				option.selected=true;
			}
			this.ele.appendChild(option);
		}
		this.category=null;
		this.module=null;
		this.option=null;
	}
	
	select() {
		console.log('select',this.id);
		this.value=this.ele.value;
		return this.value;
	}
}


