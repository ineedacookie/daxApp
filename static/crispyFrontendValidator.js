/** A function to be called when the form's action buttons are ready to be used */
function formIsReady() {
	$("#undo-btn").click(function(){
		$(".delete-on-form-sub").remove()
		$("form#content").trigger("reset").find(".form-control, .form-check-input").change().removeClass('is-invalid')
		$(this).add("form#content :submit").prop("disabled",true)
	})
	$("form#content").attr("novalidate",true)
	 .submit(function(event) {
		let check=this.checkValidity(),
		 theForm=$(this);
		$(".delete-on-form-sub").remove()
		theForm.find(".is-invalid").removeClass("is-invalid")
		if (!check) {
			theForm.find(".form-control:invalid, .form-check-input:invalid").map(function() {
				$(this).addClass('is-invalid').after(
					$('<span class="invalid-feedback delete-on-form-sub" style="font-weight:bold"></span>')
					 .text(this.validationMessage)//We want to make sure that we use html escaping (and to use tools provided by imported libs, such as jQuery)
				)
		  }).first().focus();
		}else $("#undo-btn, form#content :submit").prop("disabled",true)
		return check;
	}).find(":input").on("change keyup",function(event){
		$("#undo-btn, form#content :submit").prop("disabled",false)
	});
	$("#undo-btn, form#content :submit").prop("disabled",true)//Just in case we didn't disable them to begin with.
}
