function updateElementIndex(el, prefix, ndx) {
    var id_regex = new RegExp('(' + prefix + '-\\d+)');
    var replacement = prefix + '-' + ndx;
    if ($(el).attr("for")) $(el).attr("for", $(el).attr("for").replace(id_regex, replacement));
    if (el.id) el.id = el.id.replace(id_regex, replacement);
    if (el.name) el.name = el.name.replace(id_regex, replacement);
}

function cloneMore(selector, prefix) {
    // `selector` would be something like ".form-row:last", i.e. the last instance of an element with class "form-row"
    // Create a new element that includes data & events based on that
    var newElement = $(selector).clone(true);

    // The management form for a Django form set creates a hidden input that has an id attribute like
    // "id_creatorsForm-TOTAL_FORMS". It's value is the total number of forms in the formset.
    var total = $('#id_' + prefix + '-TOTAL_FORMS').val();

    // Get each input in the new form. These have attributes like name="contributorsForm-0-contributor_type" and
    // id="id_contributorsForm-0-contributor_type". We need to update the number in those to reflect its new position
    // in the formset. For the creators form, I could use 'input[type="text"]' as the selector, this won't work for
    // all forms.
    newElement.find('input[type="text"]').each(function() {
        console.log($(this).attr('name'));
        var name = $(this).attr('name').replace('-' + (total-1) + '-', '-' + total + '-');
        var id = 'id_' + name;
        $(this).attr({'name': name, 'id': id}).val('').removeAttr('checked');
    });

    // Then we need to make sure which inputs the labels are for (attached to) is updated as well.
    newElement.find('label').each(function() {
        var forValue = $(this).attr('for');
        if (forValue) {
          forValue = forValue.replace('-' + (total-1) + '-', '-' + total + '-');
          $(this).attr({'for': forValue});
        }
    });

    // Next we update the total number of forms in the formset, by changing the value of the hidden input we found
    // at the beginning
    total++;
    console.log(`Adding row: new total = ${total}`);
    console.log(`Selecting ${'#id_' + prefix + '-TOTAL_FORMS'}: ${$('#id_' + prefix + '-TOTAL_FORMS')}`);
    $('#id_' + prefix + '-TOTAL_FORMS').val(total);

    // Place the new form after the one we cloned.
    $(selector).after(newElement);

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

        // Find all the remaining forms and update their index in the name and id attributes, and keep the labels
        // in sync
        var forms = $(selector);
        $('#id_' + prefix + '-TOTAL_FORMS').val(forms.length);
        for (var i=0, formCount=forms.length; i<formCount; i++) {
            $(forms.get(i)).find(':input').each(function() {
                updateElementIndex(this, prefix, i);
            });
        }
    }
    return false;
}