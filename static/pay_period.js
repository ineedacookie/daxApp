function formatDate(date) {
    var d = new Date(date),
        month = '' + (d.getMonth() + 1),
        day = '' + d.getDate(),
        year = d.getFullYear();

    if (month.length < 2)
        month = '0' + month;
    if (day.length < 2)
        day = '0' + day;

    return [year, month, day].join('-');
}

function lastday(y,m){
    return new Date(y, m+1, 0)
}


function get_current_pay_period(period_type, period_begin_date, current_date = new Date()) {
    period_begin_date = new Date(period_begin_date)
    let current_period_begin_date = null
    let current_period_end_date = null
    if(period_type == 'w'){
        /* Weekly pay period */
        let current_day = current_date.getDay()
        let period_day = period_begin_date.getDay()
        if (current_day < period_day){
            adjust_day = (current_day + 1)}
        else{
            adjust_day = (current_day - period_day)}
        current_period_begin_date = new Date(current_date.getFullYear(), current_date.getMonth(), current_date.getDate() - adjust_day)
        current_period_end_date = new Date(current_period_begin_date.getFullYear(), current_period_begin_date.getMonth(), current_period_begin_date.getDate() + 6)}
    else if (period_type == 'b'){
        /* bi-weekly pay period */
        let days_passed = Math.abs(period_begin_date.getTime() - current_date.getTime())/(1000*60*60*24)
        let remainder_days = days_passed%14
        current_period_begin_date = new Date(current_date.getFullYear(), current_date.getMonth(), current_date.getDate() - remainder_days + 1)
        current_period_end_date = new Date(current_period_begin_date.getFullYear(), current_period_begin_date.getMonth(), current_period_begin_date.getDate() + 13)}
    else if (period_type == 's'){
        /* Semi monthly pay period currently not friendly other periods only works for 1-15 and 16- end*/
        let day_of_month = period_begin_date.getDate()
        let end_day_of_period = day_of_month + 14
        if (current_date.getDate() > end_day_of_period){
            current_period_begin_date = new Date(current_date.getFullYear(), current_date.getMonth(), 16)
            current_period_end_date = lastday(current_date.getFullYear(), current_date.getMonth())}
        else{
            current_period_begin_date = new Date(current_date.getFullYear(), current_date.getMonth(), 1)
            current_period_end_date = new Date(current_date.getFullYear(), current_date.getMonth(), 15)}}
    else{
        /* Monthly pay period */
        current_period_begin_date = new Date(current_date.getFullYear(), current_date.getMonth(), 1)
        current_period_end_date = lastday(current_date.getFullYear(), current_date.getMonth())}


    beg_date_field.value = formatDate(current_period_begin_date)
    end_date_field.value = formatDate(current_period_end_date)
    pay_period = [current_period_begin_date, current_period_end_date]
    return pay_period;
}

function prev_pay_period(period_type, period_begin_date) {
    if (!pay_period){
        get_current_pay_period(period_type, period_begin_date, new Date(beg_date_field.value))
    }
    period_begin_date = new Date(period_begin_date)
    let current_period_begin_date = null
    let current_period_end_date = null
    if (period_type == 'w'){
        /* Weekly pay period */
        current_period_begin_date = new Date(pay_period[0].getFullYear(), pay_period[0].getMonth(), pay_period[0].getDate() - 7)
        current_period_end_date = new Date(pay_period[1].getFullYear(), pay_period[1].getMonth(), pay_period[1].getDate() - 7)}
    else if (period_type == 'b'){
        /* bi-weekly pay period */
        current_period_begin_date = new Date(pay_period[0].getFullYear(), pay_period[0].getMonth(), pay_period[0].getDate() - 14)
        current_period_end_date = new Date(pay_period[1].getFullYear(), pay_period[1].getMonth(), pay_period[1].getDate() - 14)}
    else if (period_type == 's'){
        /* Semi monthly pay period currently not friendly other periods only works for 1-15 and 16- end*/
        if (pay_period[0].getDate() == 1){
            current_period_begin_date = new Date(pay_period[0].getFullYear(), pay_period[0].getMonth() - 1, 16)
            current_period_end_date = lastday(pay_period[1].getFullYear(), pay_period[1].getMonth() -1)}
        else{
            current_period_begin_date = new Date(pay_period[0].getFullYear(), pay_period[0].getMonth(), 1)
            current_period_end_date = new Date(pay_period[0].getFullYear(), pay_period[0].getMonth(), 15)}}
    else{
        /* Monthly pay period */
        current_period_begin_date = new Date(pay_period[0].getFullYear(), pay_period[0].getMonth() - 1, 1)
        current_period_end_date = lastday(pay_period[1].getFullYear(), pay_period[1].getMonth() -1)}

    beg_date_field.value = formatDate(current_period_begin_date)
    end_date_field.value = formatDate(current_period_end_date)
    pay_period = [current_period_begin_date, current_period_end_date]
    return pay_period;
}

function next_pay_period(period_type, period_begin_date) {
    if (!pay_period){
        get_current_pay_period(period_type, period_begin_date, new Date(beg_date_field.value))
    }
    period_begin_date = new Date(period_begin_date)
    let current_period_begin_date = null
    let current_period_end_date = null
    if (period_type == 'w'){
        /* Weekly pay period */
        current_period_begin_date = new Date(pay_period[0].getFullYear(), pay_period[0].getMonth(), pay_period[0].getDate() + 7)
        current_period_end_date = new Date(pay_period[1].getFullYear(), pay_period[1].getMonth(), pay_period[1].getDate() + 7)}
    else if (period_type == 'b'){
        /* bi-weekly pay period */
        current_period_begin_date = new Date(pay_period[0].getFullYear(), pay_period[0].getMonth(), pay_period[0].getDate() + 14)
        current_period_end_date = new Date(pay_period[1].getFullYear(), pay_period[1].getMonth(), pay_period[1].getDate() + 14)}
    else if (period_type == 's'){
        /* Semi monthly pay period currently not friendly other periods only works for 1-15 and 16- end*/
        if (pay_period[0].getDate() == 1){
            current_period_begin_date = new Date(pay_period[0].getFullYear(), pay_period[0].getMonth(), 16)
            current_period_end_date = lastday(pay_period[1].getFullYear(), pay_period[1].getMonth())}
        else{
            current_period_begin_date = new Date(pay_period[0].getFullYear(), pay_period[0].getMonth() + 1, 1)
            current_period_end_date = new Date(pay_period[0].getFullYear(), pay_period[0].getMonth() + 1, 15)}}
    else{
        /* Monthly pay period */
        current_period_begin_date = new Date(pay_period[0].getFullYear(), pay_period[0].getMonth() + 1, 1)
        current_period_end_date = lastday(pay_period[1].getFullYear(), pay_period[1].getMonth() + 1)}

    beg_date_field.value = formatDate(current_period_begin_date)
    end_date_field.value = formatDate(current_period_end_date)
    pay_period = [current_period_begin_date, current_period_end_date]
    return pay_period;
}