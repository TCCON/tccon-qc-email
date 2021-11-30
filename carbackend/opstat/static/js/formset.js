function updateElementIndex(el, prefix, ndx) {
    var id_regex = new RegExp('(' + prefix + '-\\d+)');
    var replacement = prefix + '-' + ndx;
    if ($(el).attr("for")) $(el).attr("for", $(el).attr("for").replace(id_regex, replacement));
    if (el.id) el.id = el.id.replace(id_regex, replacement);
    if (el.name) el.name = el.name.replace(id_regex, replacement);
}

function updateAllChildrenIndices(selector, prefix) {
    var forms = $(selector);
    $('#id_' + prefix + '-TOTAL_FORMS').val(forms.length);
    for (var i=0, formCount=forms.length; i<formCount; i++) {
        console.log(`Updating form ${i}`);

        $(forms.get(i)).find(':input').each(function() {
            updateElementIndex(this, prefix, i);
        });

        $(forms.get(i)).find('.line-number').each(function() {
            $(this).text(i+1);
        })
    }
}

function getFormIndex(form) {
    var t = form.find('.line-number').get(0).innerText;
    return parseInt(t) - 1;
}

function getFormByIndex(selector, index) {
    var forms = $(selector);
    return forms.get(index);
}

function cloneMore(selector, prefix) {
    // `selector` would be something like ".form-row:last", i.e. the last instance of an element with class "form-row"
    // Create a new element that includes data & events based on that
    const sel_last = `${selector}:last`
    var newElement = $(sel_last).clone(false);

    // The management form for a Django form set creates a hidden input that has an id attribute like
    // "id_creatorsForm-TOTAL_FORMS". It's value is the total number of forms in the formset.
    var total = $('#id_' + prefix + '-TOTAL_FORMS').val();

    // Place the new form after the one we cloned.
    $(sel_last).after(newElement);

    updateAllChildrenIndices(selector, prefix);


    // This part I think can be removed because I will just leave the buttons alone
//    var conditionRow = $('.form-row:not(:last)');
//    conditionRow.find('.btn.add-form-row')
//    .removeClass('btn-success').addClass('btn-danger')
//    .removeClass('add-form-row').addClass('remove-form-row')
//    .html('<span class="glyphicon glyphicon-minus" aria-hidden="true"></span>');
    return false;
}

function deleteForm(prefix, selector, btn) {
    // Find the hidden formset input that contains the total number of forms
    var total = parseInt($('#id_' + prefix + '-TOTAL_FORMS').val());
    console.log(`Total before deletion: ${total}`);

    // Don't let the last form be deleted
    if (total > 1){
        // Presumably the row we want to delete is the one closest to the button in the DOM (selector was originally
        // ".form-row")
        console.log(`Closest ${selector} to delete: ${btn.closest(selector)[0]}`);
        btn.closest(selector).remove();

        updateAllChildrenIndices(selector, prefix);
    }
    return false;
}

function moveForm(prefix, selector, btn, direction) {
    var nforms = $(selector).length;
    var form = btn.closest(selector);
    var curr_idx = getFormIndex(form);
    var tgt_idx = curr_idx + direction;

    console.log(`Moving form ${form[0]}`);

    // Check that we're not trying to more the first form up or the last form down
    if (tgt_idx < 0 || tgt_idx >= nforms) return false;

    if (direction < 0) {
        $(getFormByIndex(selector, tgt_idx)).before(form);
    } else {
        $(getFormByIndex(selector, tgt_idx)).after(form);
    }

    updateAllChildrenIndices(selector, prefix);

    return false;
}