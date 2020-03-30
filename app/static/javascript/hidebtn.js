function show_hide() {
    var row = document.getElementsByName('row');
    var length = row.length;
    var toggle = document.getElementById('toggle');
    var btn_add = document.getElementsByName('btn_add')[0];
    
    if (row[0].style.visibility != 'hidden') {
        for (let i=0;i<length;i++) {
            var obj1 = document.getElementsByName('row')[i];
            obj1.style.visibility = 'hidden';
            btn_add.style.visibility = 'hidden';
            toggle.src = 'static/images/toggle_off.svg';
        }
    }
    else {
        for (let i=0;i<length;i++) {
            var obj1 = document.getElementsByName('row')[i];
            obj1.style.visibility = 'visible';
            btn_add.style.visibility = 'visible';
            toggle.src = 'static/images/toggle_on.svg';
        }        
    }
}