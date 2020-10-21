function fill_selectbox(target_selector, object, filter, selected) {

    var $select_box = $(target_selector);

    $.getJSON( "/api/?page=object_filter&object=" + object + "&" + filter, function( data ) {

        $select_box.empty();
        $select_box.val("");

        $.each( data, function (i, entry) {
            $select_box.append($("<option>").val(this.pk).text(this.fields.vendor + ' ' + this.fields.model + ' ' + this.fields.serial));
        } )

        $select_box.append($("<option>").val('').text(' - Не задан - '));

        if (selected && selected != "None") {

            $select_box.val(selected);
        }
    });

}

