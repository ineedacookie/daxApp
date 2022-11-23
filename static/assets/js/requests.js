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