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


async function regenerateTextCitation(bibtype, url) {
    console.log(`Regenerating text citation for ${bibtype}`);
    var form = document.getElementById(`form-${bibtype}`);
    var data = new FormData(form);
    var dataObj = Object.fromEntries(data.entries());
    delete dataObj.csrfmiddlewaretoken; // don't use the CSRF token in a get request!

    let query = new URL(url);
    Object.keys(dataObj).forEach(key => query.searchParams.append(key, dataObj[key]));
    let response = await fetch(query);
    let result = await response.json();
    console.log(result);

    var citation_textarea = document.getElementById(`${bibtype}-text-citation`);
    citation_textarea.value = result.text;

    unlockSubmitButton(bibtype);
}

function unlockSubmitButton(bibtype) {
    var submit_button = document.getElementById(`submit-${bibtype}`);
    submit_button.disabled = false;
}

function lockSubmitButton(bibtype) {
    var submit_button = document.getElementById(`submit-${bibtype}`);
    submit_button.disabled = true;
}