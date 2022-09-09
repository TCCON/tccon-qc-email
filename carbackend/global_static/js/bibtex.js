function changeFormType(bibtype) {
    console.log(`Received bibtype = ${bibtype}`);
    var elements = document.getElementsByClassName('bibtex-form');
    for(var i = 0; i < elements.length; i++) {
        console.log(`i = ${i}, id = ${elements[i].id}`);
        if (elements[i].id == `bibtex-form-${bibtype}`) {
            elements[i].style.display = "block";
        }else{
            elements[i].style.display = "none";
        }
    }
}