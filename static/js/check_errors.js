function check_errors(){
    let get_time_actions = document.getElementsByClassName('form-row card')
    let prev_action = null
    let action = null
    let div = null
    let error = false
    let additional_classes = " bg-danger text-white"
    for(let i=0; i < get_time_actions.length; i++){
        card_element = get_time_actions[i]
        action = card_element.getElementsByTagName('select')[0].value
        console.log(prev_action)
        if(prev_action){
            div = document.createElement("div");
            error = false
            if(prev_action == action){
                error = true
                div.innerHTML = "Error: Duplicate Time Actions"
            } else if (action == 'b' && prev_action != 'i'){
                error = true
                div.innerHTML = "Break started when employee is not clocked in"
            } else if (action == 'e' && prev_action != 'b'){
                error = true
                div.innerHTML = "Break ended when there was no break start"
            } else if (action == 'o' && prev_action == 'b'){
                error = true
                div.innerHTML = "Clocked out when break was not ended"
            } else if (action == 'i' && prev_action != 'o'){
                error = true
                div.innerHTML = "Clocked in when employee was not clocked out"
            }

            div.className = "font-weight-bold text-center"

            if(error){
                get_time_actions[i-1].className = get_time_actions[i-1].className + additional_classes
                card_element.className = card_element.className + additional_classes
                card_element.insertBefore(div, card_element.childNodes[0])
            }

            prev_action = action

        } else {
            prev_action = action
        }
    }
}

check_errors()
