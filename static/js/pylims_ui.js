const dropdown = class {
	constructor(options) {
		this.timeouts = null;
		if (!options.id) {
			options.id='NEWDROPDOWN'
		}
		this.id = options.id;
		this.element = document.createElement("pylims_dropdown");
		this.element.id = this.id;
		this.optionList = document.createElement("pylims_dropdown_options_list");
		this.element.appendChild(this.optionList);
		this.visible=false;
		this.value=options.value;
		this.add_options({type:'default',name:'Choose:', value:options.default});
		this.optionValues=[];
		//this.default = this.element.querySelector('pylims_dropdown_default');
		this.add_options = this.add_options.bind(this);
		this.dropdownhide = this.dropdownhide.bind(this);
        this.dropdownview = this.dropdownview.bind(this);
		this.changeSelect = this.changeSelect.bind(this);
		this.updateValue = this.updateValue.bind(this);
		this.element.addEventListener('click', this.dropdownview);
		if (options.display) {
			this.element.style.display=options.display;
		}
		if (options.target) {
			options.target.appendChild(this.element);
		} else {
			return this
		}
	}

	add_options(options) {
		// console.log('adding options to',this.id,this.optionList)
		if (options.type=='default') {
			this.default = document.createElement("pylims_dropdown_default");
			this.default.innerHTML = options.name;
			this.default.setAttribute('value',options.value);
			this.optionList.appendChild(this.default);
		} else if (options.type=='dict') {
			this.optionValues={}
			for (let x of options.dict) {
				// console.log(this.value,x[options.keys])
				if (x[options.keys]==this.value) {
					this.default.innerHTML=x[options.values];
				}
				this.optionValues[x[options.keys]]=x[options.values];
				//console.log('x',x)
				//console.log('options.keys',options.keys,x[options.keys])
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
		this.element.style.overflow='visible';
		this.optionList.addEventListener('mouseleave', this.dropdownhide);
		this.optionList.style.zIndex=300;
		clearTimeout(this.timeouts);
	}

	dropdownhide() {
		// console.log('drowndown hide',this)
		this.element.style.overflow='hidden';
		this.default.style.color=null;
		this.optionList.style.zIndex=200;
	}

	changeSelect(event) {
		event.stopPropagation();
		event.preventDefault();
		const value=event.target.getAttribute('value');
		this.value=value;
		this.element.setAttribute('value',value);
		this.default.innerHTML=event.target.textContent;
		this.element.style.overflow='hidden';
		this.default.style.color=null;
		const dropdownChangeEvent = new CustomEvent('dropdownchange', {
			detail: {
				id: this.parentid,
				value: this.value
			}
		});
		this.element.dispatchEvent(dropdownChangeEvent);
	}
	triggerSelection(event) {
		const dropdownChangeEvent = new CustomEvent('dropdownchange', {
			detail: {
				id: this.parentid,
				value: this.value
			}
		});
		this.element.dispatchEvent(dropdownChangeEvent);
	}

	updateValue(value) {
		this.value=value;
		this.element.setAttribute('value',value);
		this.default.innerHTML=this.optionValues[value]
		this.element.style.overflow='hidden';
		this.default.style.color=null;
	}

}

const textbox = class {
	constructor(options) {
		if (!options.id) {
			options.id='NEWTEXTBOX'
		}
		this.id = options.id;
		this.value="";
		this.element = document.createElement('input')
		this.element.id=options.id;
		this.element.type="text";
	}
	updateValue(value) {
		this.value=value;
		this.element.setAttribute('value',value);
		this.element.value=value
	}

}

const multitoggle = class {
	constructor(options) {
		if (!options.id) {
			options.id='NEWMULTITOGGLE';
		}
		this.value=null;
		if (options && options.value) {
			this.value=options.value;
		}
		this.element = document.createElement('multitoggle');
		this.id= options.id;
		this.element.id = options.id;
		this.options = [];
		this.optionKeys={};
		this.optionElements={}
		this.setOptions = this.setOptions.bind(this);
		this.addOptions = this.addOptions.bind(this);
		this.updateValue = this.updateValue.bind(this);
		this.style=null;
		if (options.style) {
			this.style=options.style;
			this.element.classList.add(this.style)
		}
		return this
	}
	setOptions(array) {
		this.element.innerHTML=null;
		this.addOptions(array);
	}
	addOptions(array) {
		var offsetLeft=null
		if (this.style) {
			const styles = getComputedStyle(document.body);
			const offsetLeftCheck = parseInt(styles.getPropertyValue(`--${this.style}-offset-left`).trim())
			if (offsetLeftCheck) {
				offsetLeft = offsetLeftCheck;
			}	
		}
		// console.log('Offset Left:',offsetLeft)
		for (let option of array) {
			this.options.push(option);
			this.optionKeys[option.value]=option;
			let thisoption = document.createElement('mtoption');
			thisoption.innerHTML = option.text;
			thisoption.dataset.value = option.value;
			thisoption.setAttribute('data-text',option.text);
			if (option.disabled) {
				thisoption.classList.add('mtdisabled');
			}
			if (option.selected) {
				thisoption.classList.add('mtselected');
			}
			if (this.style) {
				thisoption.classList.add(this.style)
			}
			this.element.appendChild(thisoption);
			this.optionElements[option.value]=thisoption;
			if (offsetLeft) {
				// console.log('found elements',Object.keys(this.optionElements).length)
				let thisleft = (Object.keys(this.optionElements).length*offsetLeft)+'px';
				// console.log('thisleft',thisleft)
				thisoption.style.left=thisleft;
				thisoption.style.zIndex=100-Object.keys(this.optionElements).length;
			}
			thisoption.addEventListener('click',(event) => {
				// console.log(event);
				this.updateValue(event.target.dataset.value)
				const multitoggleChangeEvent = new CustomEvent('multitogglechange', {
					detail: {
						id: this.parentid
					}
				});
				this.element.dispatchEvent(multitoggleChangeEvent);
			})
			if (option.value == this.value) {
				// console.log(this.parentid)
				this.updateValue(this.value);
			}
		}

	}
	updateValue(value) {
		this.value=value;
		// console.log('update value',value,this.optionElements[value])
		let mtwidth = this.optionElements[value].offsetWidth;
		let mtleft = this.optionElements[value].offsetLeft+1;
		// console.log(mtwidth,mtleft)
		this.element.style.setProperty('--multitoggle-selection-width', `${mtwidth}px`);
		this.element.style.setProperty('--multitoggle-selection-left', `${mtleft}px`);
		this.element.style.setProperty('--multitoggle-selection-display', '1');
		
	}
}

const content_container = class {
	constructor(id,target) {
		this.id = id;
		this.div = document.createElement("div");
		this.div.id = id;
		target.appendChild(this.div);
		this.element = document.getElementById(id);
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
		this.element.style.display='block';
		this.visible=true
	}
	
	hide() {
		this.element.style.display='none';
		this.visible=false
	}
	
	toggle() {
		const tstate=['none','block'];
		this.visible=!this.visible;
		this.element.style.display=tstate[this.visible*1];
	}
	
	clear() {
		this.element.innerHTML=null;
		this.initialized=false;
	}
	
	set(html) {
		this.element.innerHTML=html;
		this.initialized=true;
	}
	
	add(ele) {
		// console.log('add',ele)
		this.element.appendChild(ele);
		this.initialized=true;
	}
}

const pylims_setup_toggle = class {
	constructor(setval,parent) {
		this.element=document.createElement('div');
		this.element.className='tf_container'
		this.tfball=document.createElement('div');
		this.tfball.className='tf_ball'
		if (setval=='true') {
			this.tfball.classList.add('tf_true');
			this.state='true';
		} else {
			this.tfball.classList.add('tf_false');
			this.state='false';
		}
		this.element.appendChild(this.tfball);
		parent.appendChild(this.element)
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
		this.element =document.createElement('select');
		this.element.className='pylimsui_select';
		parent.append(this.element)
		this.value=value;
		
		for (let i=0;i<options.length;i++) {
			let option=document.createElement('option');
			option.value=i;
			option.text=options[i];
			if (i==value) {
				option.selected=true;
			}
			this.element.appendChild(option);
		}
		this.category=null;
		this.module=null;
		this.option=null;
	}
	
	select() {
		console.log('select',this.id);
		this.value=this.element.value;
		return this.value;
	}
}

const label_container = class {
	constructor(options) {
		const container = document.createElement('labelcontainer')
		const label_c = document.createElement('label')
		label_c.style.width=`${options.width}px`;
		label_c.textContent=options.name;
		container.appendChild(label_c)
		container.appendChild(options.input);
		return container
	}
}


