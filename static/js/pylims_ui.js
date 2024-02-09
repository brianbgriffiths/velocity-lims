class pylimsUI {
  constructor() {
    // You can initialize properties or perform setup here
  }

  // Example method
	create_toggle(value) {
		const tf=document.createElement('div');
		tf.className='tf_container'
		const tfball=document.createElement('div');
		tfball.className='tf_ball'
		if (value=='true') {
			tfball.classList.add('tf_true');
			tf.dataset.state='true';
		} else {
			tfball.classList.add('tf_false');
			tf.dataset.state='false';
		}
		tf.appendChild(tfball);
		return tf
	}
	toggle(id)  {
		console.log('toggle',id);
		const tf=document.getElementById(id);
		const cat=tf.dataset.cat;
		const mod=tf.dataset.mod;
		const opt=tf.dataset.opt;
		
		console.log(tf)
		const tfball = tf.querySelector('.tf_ball');
		if (tf.dataset.state=="true") {
			console.log('toggle to false');
			tf.dataset.state="false";
			tfball.classList.add('tf_false');
			tfball.classList.remove('tf_true');
			return 'false'
		} else {
			console.log('toggle to true');
			tf.dataset.state="true";
			tfball.classList.add('tf_true');
			tfball.classList.remove('tf_false');
			return 'true';
		}
	}
	create_select(options,value) {
		const select=document.createElement('select');
		select.className='pylimsui_select';
		for (let i=0;i<options.length;i++) {
			let option=document.createElement('option');
			option.value=i;
			option.text=options[i];
			if (i==value) {
				option.selected=true;
			}
			select.appendChild(option);
		}
		return select;
	}
	select(id) {
		console.log('select',id);
		const select=document.getElementById(id);
		const value=select.value;
		return value;
	}
}

// Export the Example class
export default pylimsUI;