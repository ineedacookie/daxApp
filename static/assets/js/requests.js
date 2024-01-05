function submit_update_widget(url, additional_data, widget_id){
        let serialized_array = $(widget_id + ' :input').serializeArray();
        serialized_array = serialized_array.concat(additional_data)
        $.ajax({
            type:'POST',
            url:url,
            data:serialized_array,
            success:function(response){
                $(widget_id).html($(response).find(widget_id).html());
                }
            })
        return false;
    }

function invite_employees_submit_form(url, additional_data, widget_id) {
    let emails = $('#emails').val(); // Get selected email values as an array
    let emailString = emails.join(','); // Convert array to comma-separated string

    // Add the email string to the additional data
    additional_data.push({ name: 'emails', value: emailString });

    // Serialize the form data and concatenate with additional data
    let serialize_array = $(widget_id).serializeArray().concat(additional_data);

    // Prevent the form from submitting
    event.preventDefault();

    // Make the AJAX request
    $.ajax({
        type: 'POST',
        url: url,
        data: serialize_array,
        success: function () {
            // Hide the modal and clear the email field
            $('#addEmployeeModal').modal('hide');
            $('#emails').val(null).trigger('change');
        },
        error: function () {
            // Display an error message above the field
            $('#invite_error_message').text("Something went wrong with one or more of the emails provided. Please double-check the emails entered.");
        }
    });
}


function load_main_content(url, main_id){
        $.ajax({
            type:'GET',
            url:url,
            success:function(response){
                $(main_id).html($(response).find(main_id).html());
                }
            })
        return false;
    }