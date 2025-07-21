var popups={}

const popup = class {
	constructor(options) {
		if (!options['id']) {
			console.error('Give your popup an ID')
		}
		const already_exists = popups[options['id']]
		if (already_exists) {
			console.error('creating a popup that already exists.')
		}
		this.size=options['size'] || null;
		if (!options['size'] || !['small', 'medium', 'large'].includes(options['size'])) {
			this.size='small';
		} 
		this.id = options['id'];
		this.ele = document.createElement('div');
		this.ele.id = this.id

		this.ele.classList.add('popup',`popup_${this.size}`);

		document.body.appendChild(this.ele);
		if (options['title']) {
			this.ele.dataset.title=options['title'];
		}

		this.show = this.show.bind(this);
		this.hide = this.hide.bind(this);
		this.destroy = this.destroy.bind(this);
		this.html_content = this.html_content.bind(this);
		this.append = this.append.bind(this);
		this.add_close = this.add_close.bind(this);

		this.add_close()
	}
	add_close() {
		let close = document.createElement('div');
		close.classList.add('popup_close');
		this.ele.appendChild(close);
		close.addEventListener('click',this.hide)
	}
	show() {
		let is_screen_block = document.getElementById('screen_block');
		if (!is_screen_block) {
			const sb = document.createElement('div');
			sb.id='screen_block';
			document.body.append(sb);
		} else {
			is_screen_block.style.display='block';
		}
		this.ele.style.display='block';
    }
	hide() {
		this.ele.style.display='none';
		let is_screen_block = document.getElementById('screen_block');
		if (is_screen_block) {
			is_screen_block.style.display='none';
		}
    }
	destroy() {
		this.ele.remove()
	}
	clear() {
		this.ele.innerHTML=null;
		this.add_close();
	}

	html_content(content) {
		this.ele.innerHTML=content;
		this.add_close()
	}

	append(element) {
		this.ele.appendChild(element);
	}

	append_html(content) {
		this.ele.innerHTML+=content;
	}
}