/* Strings and vars */
var UNSUPPORTED_FILE_MESSAGE = "File not supported.";
var EXAMPLE_FASTA = ">hg19_uc002ypa.3 range=chr21:33032335-33032384 strand=+\nGTCACCGGGCGGGCCCGGGCGCGGGGCGTGGGACCGAGGCCGCCGCGGGG"
var UNSUPPORTED_FILE_TYPES = /application.*|image.*/;
var EXAMPLE_RULES=[
		["xxxxxxxxxxxxXXXXXXXXNGG","NNNNNNNNNNNNNNNNNNNNNRG","2"],
		["xxxxxxxxxxxXXXXXXXXXNGG","NNNNNNNNNNNNNNNNNNNNNRG","2"],
		["xxxxxxxxxxXXXXXXXXXXNGG","NNNNNNNNNNNNNNNNNNNNNRG","2"],
		["gxxxxxxxxxXXXXXXXXXXNGG","NNNNNNNNNNNNNNNNNNNNNRG","2"],
		["xxxxxxxxxxxxXXXXXNGG","NNNNNNNNNNNNNNNNNNGG","2"],
                ["xxxxxxxxxxXXXXXXXXXXNNGRRT","NNNNNNNNNNNNNNNNNNNNNNGRRT","2"]];
var DEFAULT_RULE = EXAMPLE_RULES[2];



/* Adds example FASTA string to faPaste */
$(document).on("click", ".tooltip #example_button", function(){
	$("#faPaste").val(EXAMPLE_FASTA);
	return false;
} );


/* Loads example rules into text fields when user selects them! */
$(document).on("click", ".tooltip .example_rule", function() {
    var exampleNumber = $(this).attr("id").split("ex").pop();
    var selectedRule = EXAMPLE_RULES[exampleNumber];
    $("#rule").val(selectedRule[0]);
	$("#filter").val(selectedRule[1]);
	$("#mismatches").val(selectedRule[2]).trigger("chosen:updated");
	updateLengths();
    return false;
} );


/*
Stuff for rule and filter.
*/
function updateLengths() {
	var ruleLength = $("#rule").val().length;
	var filterLength = $("#filter").val().length;
	$("#rule_length").text(ruleLength+"nt");
	$("#filter_length").text(filterLength+"nt");
	if (filterLength == ruleLength) {
		$("#rule_length, #filter_length").css("color","green");
	} else {
		$("#rule_length, #filter_length").css("color","red");
	};
};

/* Clears faPaste */
$(document).on("click", "#clear_sequence", function() {
	$("#faPaste").val("");
	return false;
} );




$(document).on("input", "#rule", function() {
	while ($(this).val().length > $("#filter").val().length) {
		$("#filter").val(
			$("#filter").val().substring(0,this.selectionStart-1) + "N" + $("#filter").val().substring(this.selectionStart-1,$("#filter").val().length)
		)
	}
	while (  $(this).val().length < $("#filter").val().length) {
		$("#filter").val(
			$("#filter").val().substring(0,this.selectionStart) + $("#filter").val().substring(this.selectionStart+1,$("#filter").val().length)
		)
		}
	updateLengths();
} );

$(document).on("input", "#filter", function() {
	updateLengths();
} );





/* Listener for form "reset" button */
$(document).on("click", "#reset", function() {
	$("#faPaste").val("");
	$("#rule").val(DEFAULT_RULE[0]);
	$("#filter").val(DEFAULT_RULE[1]);
	$("#refGenome").val("").trigger("chosen:updated");
	$("#mismatches").val(DEFAULT_RULE[2]).trigger("chosen:updated");
	$("#jobName").val("");
	$("#email").val("");
	$(".col-4").text("");
	updateLengths();
	return false;
} );




/*
Runs at page load
*/
$(document).ready(function() {
	$("#refGenome").chosen({width: "25.5em"});
	
	$("#mismatches").chosen({width: "25.5em"});

	$(".helper").tooltip( {
		predelay:400, effect:"fade", fadeOutSpeed:100, position:"bottom right", offset:[-30, 0]
	} );
	
	// Load default rule on first page load
	if ($("#filter").val() == "" && $("#rule").val() == "") {
		$("#rule").val(DEFAULT_RULE[0]);
		$("#filter").val(DEFAULT_RULE[1]);
		$("#mismatches").val(DEFAULT_RULE[2]).trigger("chosen:updated");
	}
	updateLengths();
	
	

	/* Copies contents of user selected file to faPaste */
	$("#file-select").change(function(evt) {
		var files = evt.target.files;
		var file = files[0];
		if (!file.type.match(UNSUPPORTED_FILE_TYPES)) { 
			var reader = new FileReader();
			reader.onload = function() {
				$("#faPaste").val(this.result);
			}
			reader.readAsText(file);
		} else {
			$("#faPaste").val(UNSUPPORTED_FILE_MESSAGE);
		}
		$(this).wrap("<form>").closest("form").get(0).reset();
		$(this).unwrap();
		return false;
	} );

	/* Links pretty button clicks to ugly browser styled button */
	$( "#pretty_overlay" ).click(function() {
		document.getElementById("file-select").click();
	} );
	
} );
